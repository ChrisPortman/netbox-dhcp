from datetime import datetime, timezone, timedelta
from netaddr import IPAddress, EUI

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from netbox.api.serializers import NetBoxModelSerializer
from dcim.fields import mac_unix_expanded_uppercase
from ipam.api.serializers import IPAddressSerializer

from ..models import DhcpLease
from ..jobs import CheckLeaseAcknowledgedJob


class DhcpLeaseSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:netbox_dhcp-api:dhcplease-detail')

    ip_address = IPAddressSerializer(read_only=True)
    gateway = serializers.IPAddressField(read_only=True)
    options = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DhcpLease
        fields = (
            'id',
            'url',
            'mac_address',
            'hostname',
            'client_id',
            'receiving_ip',
            'requested_ip',
            'acknowledged',
            'lease_time',
            'expire_time',
            'ip_address',
            'gateway',
            'options',
            'tags',
            'custom_fields',
            'created',
            'last_updated',
        )
        read_only_fields = [
            'lease_time',
            'expire_time',
            'ip_address',
            'options',
            'gateway',
        ]

    def create(self, validated_data):
        instance = super().create(validated_data)
        check_ack_time = datetime.now(tz=timezone.utc) + timedelta(seconds=10)
        return instance

#       CheckLeaseAcknowledgedJob.enqueue_once(
#           instance=instance,
#           schedule_at=check_ack_time,
#           user=self.context["request"].user,
#       )

#       return instance

    @extend_schema_field(serializers.JSONField(allow_null=True))
    def get_options(self, obj):
        return obj.get_dhcp_context()

    def validate_mac_address(self, value):
        return str(EUI(value, version=48, dialect=mac_unix_expanded_uppercase))

    def validate_receiving_ip(self, value):
        return str(IPAddress(value))

    def validate_requested_ip(self, value):
        if value:
            return str(IPAddress(value))
