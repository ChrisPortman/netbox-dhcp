from django.utils.translation import gettext as _
from netbox.filtersets import NetBoxModelFilterSet
from utilities.filters import MultiValueMACAddressFilter

from .models import DhcpLease


class DhcpLeaseFilterSet(
    NetBoxModelFilterSet,
):
    mac_address = MultiValueMACAddressFilter(
        field_name='mac_address',
        label=_('MAC address'),
    )

    class Meta:
        model = DhcpLease
        fields = []
