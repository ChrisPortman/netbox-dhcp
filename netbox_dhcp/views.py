from netbox.views import generic
from . import models, tables


class DhcpLeaseView(generic.ObjectView):
    queryset = models.DhcpLease.objects.order_by("lease_time").all()


class DhcpLeaseListView(generic.ObjectListView):
    queryset = models.DhcpLease.objects.order_by("lease_time").all()
    table = tables.DhcpLeaseTable


class DhcpLeaseDeleteView(generic.ObjectDeleteView):
    queryset = models.DhcpLease.objects.order_by("lease_time").all()
