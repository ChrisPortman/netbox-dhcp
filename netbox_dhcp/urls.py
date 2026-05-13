from django.urls import path

from . import views

urlpatterns = (
    path('leases/', views.DhcpLeaseListView.as_view(), name='dhcplease_list'),
    path('leases/delete', views.DhcpLeaseBulkDeleteView.as_view(), name='dhcplease_bulk_delete'),
    path('leases/<int:pk>/', views.DhcpLeaseView.as_view(), name='dhcplease'),
    path('leases/<int:pk>/delete/', views.DhcpLeaseDeleteView.as_view(), name='dhcplease_delete'),
)
