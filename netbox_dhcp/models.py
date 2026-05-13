import logging
from datetime import datetime, timedelta
from typing import Any

from dcim.models import (
    Device,
    DeviceRole,
    DeviceType,
    Interface,
    Location,
    MACAddress,
    Platform,
    Site,
)
from netbox.models.features import JobsMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.http import Http404

# from django.db.models import Model
from django.urls import reverse
from django.utils import timezone
from extras.models import ConfigContextModel
from ipam.choices import IPAddressStatusChoices, PrefixStatusChoices
from ipam.models import IPAddress as IPAMIPAddress
from ipam.models import Prefix
from netaddr import IPAddress
from tenancy.models import Tenant
from virtualization.models import Cluster, VirtualMachine, VMInterface

from netbox.models import NetBoxModel
from netbox.plugins.utils import get_plugin_config

logger = logging.getLogger('netbox_dhcp')

class DhcpLeaseExpireTime(models.DateTimeField):
    def pre_save(self, model_instance: 'DhcpLease', add: bool) -> Any:
        lease_time: int = get_plugin_config("netbox_dhcp", "max_lease_time")
        value = timezone.now() + timedelta(seconds=lease_time)
        setattr(model_instance, self.attname, value)
        return value


class DhcpLeaseIPAddress(models.OneToOneField):
    def pre_save(self, model_instance: 'DhcpLease', add: bool) -> Any:
        if not add:
            logger.info("updating lease for %s", model_instance.mac_address)
            return super().pre_save(model_instance, add)

        logger.info("creating new lease for %s", model_instance.mac_address)
        value = self.new_lease(model_instance)
        if value is None:
            raise Http404("No suitable lease available for this request")

        setattr(model_instance, self.attname, value)

        return value

    def new_lease(self, data: 'DhcpLease') -> IPAMIPAddress | None:
        '''
        New leases are resolved accoding to the following priority:

        1. Use the ip associated with the interface that has the supplied MAC
        2. Use the ip associated with the parent interface of the one with the supplied MAC (bonds)
        3. Use an IP address from the subnet containing the receiving ip that is taged for DHCP Dynamic allocation that is not associated with any other lease
        4. Use an IP address from the subnet containing the receiving ip that is taged for DHCP Dynamic allocation that is not associated with any other non-expired lease
        5. Fail to provide a lease.

        For options 1 and 2, validate the the IP addresses are in the same subnet as the receiving IP.
        '''

        interface: Interface |VMInterface | None = None
        ip: IPAMIPAddress | None = None

        receiving_ip = data.receiving_ip
        logger.info("dhcp lease requested for mac: %s, from network with: %s", data.mac_address, receiving_ip)

        for mac_address in MACAddress.objects.filter(mac_address=data.mac_address):
            interface = mac_address.assigned_object

            if interface is not None:
                ip = self.resolve_interface_ip(data, interface) or self.resolve_device_ip(data, interface)

            if ip is None:
                ip = self.resolve_dynamic_ip(data)

            if ip is None:
                continue

            if receiving_ip not in ip.address:
                continue

            return ip.pk

        # The mac address is completely unknown
        ip = self.resolve_dynamic_ip(data)
        if ip is not None:
            if receiving_ip not in ip.address:
                return None
            return ip.pk

        return None

    def resolve_interface_ip(self, data: 'DhcpLease', interface: Interface | VMInterface) -> IPAMIPAddress | None:
        ip_addresses = interface.ip_addresses.all()
        if list(ip_addresses):
            for ip in ip_addresses:
                if data.receiving_ip in ip.address:
                    return ip

        if isinstance(interface, (Interface,)):
            if interface.lag:
                if interface.lag.mac_address != data.mac_address:
                    raise Http404("LAG members that do not share the LAG mac do not get leases")

                ip = self.resolve_interface_ip(data, interface.lag)
                if ip:
                    return ip

        if interface.parent:
            ip = self.resolve_interface_ip(data, interface.parent)
            if ip:
                return ip

        return None

    def resolve_device_ip(self, data: 'DhcpLease', interface: Interface | VMInterface) -> IPAMIPAddress | None:
        """ If the MAC address resolved an interface, and the corresponding device
        has a primary_ip in the correct network, use it
        """
        device = getattr(interface, "device", getattr(interface, "virtual_machine", None))
        if device is None:
            return None

        ip = device.primary_ip
        if ip is None:
            return None

        if data.receiving_ip not in ip.address:
            return None

        return ip

    def resolve_dynamic_ip(self, data: 'DhcpLease') -> IPAMIPAddress | None:
        receiving_ip = data.receiving_ip
        prefixes = Prefix.objects.filter(prefix__net_contains=receiving_ip)
        if not list(prefixes):
            return None

        prefixes = [p for p in prefixes if p.mask_length is not None]
        prefixes = sorted(prefixes, key=lambda p: p.mask_length or 0, reverse=True)
        prefix = prefixes[0]

        # ips = prefix.get_child_ips()
        never_leased = []
        previously_leased = []

        for ip in dhcp_addresses_for_prefix(prefix):
            try:
                lease = ip.lease
            except ObjectDoesNotExist:
                never_leased.append(ip)
                continue

            if lease.is_current():
                continue

            previously_leased.append(lease)

        if never_leased:
            return never_leased[0]

        if previously_leased:
            previously_leased.sort(key=lambda l: l.expire_time, reverse=True)
            return previously_leased[0].ip_address


def dhcp_addresses_for_prefix(prefix: Prefix) -> list[IPAMIPAddress]:
    # ips = prefix.get_child_ips()
    prefix_mask_len = prefix.mask_length
    ips = IPAMIPAddress.objects.filter(
        address__net_contained_or_equal=prefix.prefix,
        status=IPAddressStatusChoices.STATUS_DHCP,
    )

    if prefix_mask_len is not None:
        ips = ips.filter(address__net_mask_length=prefix_mask_len)

    return list(ips)


class DhcpLease(ConfigContextModel, NetBoxModel, JobsMixin):
    mac_address = models.CharField(max_length=20, db_index=True)
    hostname = models.CharField(max_length=100, blank=True, null=True)
    client_id = models.CharField(max_length=100)
    receiving_ip = models.GenericIPAddressField()
    requested_ip = models.GenericIPAddressField(null=True, blank=True)

    lease_time = models.DateTimeField(auto_now=True)
    expire_time = DhcpLeaseExpireTime(blank=True)
    ip_address = DhcpLeaseIPAddress(
        to="ipam.IPAddress",
        on_delete=models.CASCADE,
        related_name='lease',
        blank=True,
    )
    acknowledged = models.BooleanField(default=False)

    class Meta:
        verbose_name = "DHCP Lease"
        verbose_name_plural = "DHCP Leases"

    def get_dhcp_context(self):
        ctx = self.get_config_context().get(
            get_plugin_config("netbox_dhcp", "context_key"),
            {},
        )

        if not isinstance(ctx, (dict,)):
            ctx = {}

        is_deploying = False
        target = self.device or self.virtual_machine
        if target:
            if hasattr(target, "deployment"):
                is_deploying = True

        if not is_deploying:
            for f in get_plugin_config("netbox_dhcp", "include_on_deployment", []):
                ctx.pop(f, None)

        return ctx

    def get_absolute_url(self):
        return reverse('plugins:netbox_dhcp:dhcplease', args=[self.pk])

    def is_current(self):
        # A lease is current if:
        # - it is acknowledged AND the expire_time is in the future; OR
        # - it is not acknowledged AND the lease_time is less that 10 seconds ago.
        # This gives clients 10 seconds to request an offered IP address.
        now = timezone.now()
        if not self.acknowledged:
            return self.lease_time + timedelta(seconds=10) < now

        return self.expire_time > now

    def is_on_same_network_as(self, ip: IPAddress):
        return ip in self.ip_address.address

    def gateway(self) -> IPAddress | None:
        cidr = self.ip_address.address.cidr
        prefix = Prefix.objects.filter(prefix=cidr, vrf=self.ip_address.vrf).first()
        if prefix:
            gateway = IPAMIPAddress.objects.filter(
                address__net_host_contained=str(prefix.prefix),
                vrf=self.ip_address.vrf,
                tags__name__in=["Gateway"],
            ).first()

            if gateway is not None:
                return gateway.address.ip

        return None

    @property
    def local_context_data(self) -> dict | None:
        if self.device:
            return self.device.local_context_data
        if self.virtual_machine:
            return self.virtual_machine.local_context_data
        return None

    @property
    def interface(self) -> Interface | VMInterface | None:
        if hasattr(self, "ip_address") and self.ip_address is not None:
            return self.ip_address.assigned_object
        return None

    @property
    def device(self) -> Device | None:
        if self.interface is None:
            return None

        return getattr(self.interface, "device", None)

    @property
    def virtual_machine(self) -> VirtualMachine | None:
        interface = self.interface
        if interface is None:
            return None

        return getattr(interface, "virtual_machine", None)

    @property
    def role(self) -> DeviceRole | None:
        if self.device:
            return self.device.role
        if self.virtual_machine:
            return self.virtual_machine.role
        return None

    @property
    def device_type(self) -> DeviceType | None:
        if self.device is not None:
            return self.device.device_type
        return None

    @property
    def location(self) -> Location | None:
        if self.device is not None:
            return self.device.location
        return None

    @property
    def cluster(self) -> Cluster | None:
        if self.virtual_machine is None:
            return None
        return self.virtual_machine.cluster

    @property
    def tenant(self) -> Tenant | None:
        if self.device:
            return self.device.tenant
        if self.virtual_machine:
            return self.virtual_machine.tenant
        return self.ip_address.tenant

    @property
    def site(self) -> Site | None:
        if self.device:
            return self.device.site
        if self.virtual_machine:
            return self.virtual_machine.site

        prefix = Prefix.objects.filter(
            prefix=self.ip_address.address.cidr,
            vrf=self.ip_address.vrf,
            status=PrefixStatusChoices.STATUS_ACTIVE,
        ).first()

        if prefix is None:
            return None

        prefixes = [prefix] + list(prefix.get_parents())
        for p in prefixes:
            scope = p.scope
            if isinstance(scope, Site):
                return scope

        return None

    @property
    def platform(self) -> Platform | None:
        if self.device:
            return self.device.platform
        if self.virtual_machine:
            return self.virtual_machine.platform
        return None

    def __str__(self):
        return f"Lease for {self.mac_address}"
