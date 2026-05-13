from netbox.api.viewsets import NetBoxModelViewSet

from .. import models
from .. import filtersets
from .serializers import DhcpLeaseSerializer


class DhcpLeaseViewSet(NetBoxModelViewSet):
    queryset = models.DhcpLease.objects.order_by("lease_time").prefetch_related('tags', 'ip_address')
    filterset_class = filtersets.DhcpLeaseFilterSet
    serializer_class = DhcpLeaseSerializer
