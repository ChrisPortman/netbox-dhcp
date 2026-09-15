from django.utils.translation import gettext as _
from utilities.filters import (
    MultiValueCharFilter,
    MultiValueDateTimeFilter,
    MultiValueMACAddressFilter,
)
from utilities.filtersets import register_filterset

from netbox.filtersets import NetBoxModelFilterSet

from .models import DhcpLease


@register_filterset
class DhcpLeaseFilterSet(
    NetBoxModelFilterSet,
):
    mac_address = MultiValueMACAddressFilter(
        field_name='mac_address',
        label=_('MAC address'),
    )

    class Meta:
        model = DhcpLease
        fields = ['client_id', 'hostname', 'lease_time', 'expire_time']
