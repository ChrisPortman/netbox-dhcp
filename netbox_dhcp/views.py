from netbox.object_actions import BulkDelete
from netbox.views import generic

from . import models, tables


class DhcpLeaseView(generic.ObjectView):
    queryset = models.DhcpLease.objects.order_by("lease_time").all()


class DhcpLeaseListView(generic.ObjectListView):
    queryset = models.DhcpLease.objects.order_by("lease_time").all()
    table = tables.DhcpLeaseTable
    actions = (BulkDelete,)


class DhcpLeaseDeleteView(generic.ObjectDeleteView):
    queryset = models.DhcpLease.objects.order_by("lease_time").all()


class DhcpLeaseBulkDeleteView(generic.BulkDeleteView):
    queryset = models.DhcpLease.objects.all()
    table = tables.DhcpLeaseTable
