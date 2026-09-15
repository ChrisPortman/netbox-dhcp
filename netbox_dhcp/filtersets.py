from django.utils.translation import gettext as _
from utilities.filters import (
    MultiValueCharFilter,
    MultiValueDateTimeFilter,
    MultiValueMACAddressFilter,
)

from netbox.filtersets import NetBoxModelFilterSet

from .models import DhcpLease


class DhcpLeaseFilterSet(
    NetBoxModelFilterSet,
):
    mac_address = MultiValueMACAddressFilter(
        field_name='mac_address',
        label=_('MAC address'),
    )

    client_id = MultiValueCharFilter(
        field_name='client_id',
        label=_('Client ID'),
    )

    hosthame = MultiValueCharFilter(
        field_name='hostname',
        label=_('Hostname'),
    )

    lease_time = MultiValueDateTimeFilter(
        field_name='lease_time',
        label=_('Lease Time'),
    )

    expire_time = MultiValueDateTimeFilter(
        field_name='expire_time',
        label=_('Expire Time'),
    )

    class Meta:
        model = DhcpLease
        fields = []
