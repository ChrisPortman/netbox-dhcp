from netbox.plugins import PluginMenuItem

from netbox.plugins import PluginMenu

active_leases = PluginMenuItem(link='plugins:netbox_dhcp:dhcplease_list', link_text='Active Leases')

menu = PluginMenu(label='DHCP', groups=(('Leases', (active_leases,)),), icon_class='mdi mdi-ip-network-outline')
