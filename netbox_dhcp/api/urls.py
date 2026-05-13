from netbox.api.routers import NetBoxRouter
from . import views

app_name = 'netbox_dhcp'

router = NetBoxRouter()
router.register('leases', views.DhcpLeaseViewSet)

urlpatterns = router.urls
