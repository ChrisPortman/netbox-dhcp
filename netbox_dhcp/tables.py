import django_tables2 as tables

from netbox.tables import NetBoxTable
from netbox.tables import columns
from .models import DhcpLease

class DhcpLeaseTable(NetBoxTable):

    ip_address = tables.Column(linkify=True)
    actions = columns.ActionsColumn(actions=("delete",))

    class Meta(NetBoxTable.Meta):
        model = DhcpLease
        fields = ('pk', 'id', 'mac_address', 'hostname', 'client_id', 'ip_address', 'lease_time', 'expire_time', 'actions')
        default_columns = ('mac_address', 'hostname', 'client_id', 'ip_address', 'expire_time')
