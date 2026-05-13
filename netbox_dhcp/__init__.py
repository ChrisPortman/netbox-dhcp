from netbox.plugins import PluginConfig


class NetBoxDHCPConfig(PluginConfig):
    name = 'netbox_dhcp'
    verbose_name = ' NetBox DHCP'
    description = 'Manage DHCP Leases'
    version = '0.1'
    base_url = 'dhcp'
    required_settings = []
    default_settings = {
        # The key within config context data that contains
        # dhcp options
        'context_key': 'dhcp',
        # The maximum lease time.  Actual lease time may be shorter
        # based on client's request (TODO: requested lease time not implemented)
        'max_lease_time': 3600,
        # Fields listed here will only be included if the device or
        # virtual machine has an existing deployment (using the netbox-deployment
        # plugin)
        'include_on_deployment': [
            'boot_server',
            'boot_file',
        ],
    }


config = NetBoxDHCPConfig
