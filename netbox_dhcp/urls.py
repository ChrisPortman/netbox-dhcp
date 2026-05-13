from django.urls import path
from . import views

urlpatterns = (
    path('leases/', views.DhcpLeaseListView.as_view(), name='dhcplease_list'),
    path('leases/<int:pk>/', views.DhcpLeaseView.as_view(), name='dhcplease'),
    path('leases/<int:pk>/delete/', views.DhcpLeaseDeleteView.as_view(), name='dhcplease_delete'),
)
