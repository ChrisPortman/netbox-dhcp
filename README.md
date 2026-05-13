# Netbox DHCP Lease Manager Plugin

## Introduction

Netbox natively stores a great deal of information about the environments network layout.  Most
notably:

* Details of IP Prefixes and where they're used (sites, vlans etc)
* Roles of specific IP addresses - one of the out of the box roles that can be assigned to an IP
  address is "DHCP", indicating that the IP address is assigned via a DHCP service.
* What device/virtual machine interfaces an IP address is assigned to.
* Other details about network configuration.

Based on this information, it makes sense that a DHCP service should be able to leverage this
information directly as well.

Using the above information, this plugin provides:

* Business logic that determines what IP address should be issued to a DHCP client based on details
  available in a typical DHCP request.
* Business logic that may provide mandatory and optional DHCP option values.
* State persistence of lease information - what IP addresses have been leased out and when they will
  expire etc.
* An API that may be consumed by a DHCP server to access lease details and business logic.

This plugin does **NOT** provide:

* A DHCP server capable of trading DHCP messages with a DHCP client (see [RSDHCP](https://github.com/ChrisPortman/rsdhcp)).

## Installation

Installation will vary based on how you have deployed Netbox.  If you are running it natively,
probably within a virtual environment, installation is just a case of `pip install <path to
plugin>`.

If you are using the Docker stack provided by the Netbox community, see their documentation on how
to integrate plugins.

Once installed, you need to provide the following configuration within the broader Netbox
Configuration:

```python
PLUGINS=[
    # Enable the plugin
    "netbox_dhcp",
]

PLUGIN_CONFIG={
    "netbox_dhcp": {
        # The top level key in config context that contains DHCP options (default: 'dhcp')
        "context_key": "dhcp",

        # If you are use the netbox_deployment plugin, the following list represents context
        # keys that will only be returned if the device has a deployment active.
        # Has no effect if not using the netbox_deployment plugin.
        # (default: [])
        "include_on_deployment": [
            "key1",
            "key2",
        ],
    },
}
```

## How a Lease is Determined

When the API receives a POST request to the lease endpoint, it is expected to contain at a minimum:

* MAC address of the requester.
* The IP address that received the request.  Typically this will be the IP address of the DHCP
  server itself or the IP address in the `giaddr` field of the request indicating that it has been
  proxied.

The POST will attempt to create a new lease based on the following rules:

1. If the MAC address is configured on a device or virtual machine interface which has an IP address
   assigned to it and that IP address is in the same prefix as the receiving IP address.  Issue a
   lease for this the IP address of the interface.
1. If the prefix containing the receiving IP address includes any IP addresses with the role `DHCP`
   and there exists one of those addresses not presently assigned to an active lease, Issue one of
   these addresses.

### DHCP Options

**NOTE:** The following examples show specifying DHCP options according to the way [RSDHCP](https://github.com/ChrisPortman/rsdhcp)
expects to receive them at the time of writing.  If you have some other DHCP service that has been
integrated into this plugin, it may expect different representation.  Refer to the DHCP server docs
for the correct details on how to represent DHCP options.

A small number of DHCP options are required for a client to be able to successfully setup
networking:

**Mandatory**

* *Subnet Mask*: the IP address in the lease API response payload is in CIDR notation (e.g.
  `10.1.1.1/24`) based on the prefix.  It is for the DHCP server to derive the subnet mask option
  value from this.

**Practically Mandatory**

* *Default Gateway*: If the prefix containing the issued IP address contains an IP carrying the
  `Gateway` tag, it is included in the API response payload.

**Other Options**

Netbox provides a feature called "Context Data" which is a somewhat hierarchical
specification of data that is available as an attribute on various objects (see [Netbox Context Data
Docs](https://docs.netbox.dev/en/stable/features/context-data/)).

Using this feature, the user may specify config context on different objects to build up additional
data that will be provided to the API client (DHCP server) which it may use to populate additional
DHCP options.  The exact schema for the context data is an implementation detail left to the end
user based on what their DHCP server expects.  An example may look like:

```json
{
    "dhcp": {
        "dns_servers": ["8.8.8.8", "8.8.1.1"],
        "domain_name": "example.io",
        "boot_server": "tftp.example.id",
        "boot_file": "boot.iso",
    }
}
```

**Note**: The example represents an entire Context Data representation of which the `dhcp`
key is relevant.  There may be other top level keys that exist that are not relevant.  Additionally,
the key `dhcp` could be something else entirely depending on what the DHCP server expects.

The example includes an approach for specifying random options based on the DHCP option number.  The
API client (DHCP Server) may have logic for dealing nicely with commonly used options (e.g.
`dns_servers`) but then a catch all for other less used options.

The Netbox logic is to collect the Context Data from a range of objects and then combine them based
on a priority set by the administrator.  As they are hashes/dicts/tables, keys that exist on
multiple configuration data items will be overridden by the one that has the highest priority.  The
exception to this is that Context Data that is specified directly on a Device of Virtual Machine
always has priority.

Using combinations of Context Data specified across Site, Location, Regions etc, the administrator
can build out a somewhat hierarchical design of DHCP options that will be available to DHCP clients.

## As a User...

The plugin provides a UI integrated into the broader Netbox UI that allows the user to see what
active leases exist and their details.  The user may also delete a lease as needed with the result
being that the end client will not be able to renew that lease.  When the lease expires on the
client, it will need to start from scratch.

To access the UI, see the *Plugins* section of the Netbox sidebar.

## Development

*TLDR;*

```console
git clone git@github.com:ChrisPortman/netbox-dhcp.git
cd netbox-dhcp/
git submodule update --init --recursive
python3 -m venv .venv
. .venv/bin/activate
python -m pip install requirements.dev.txt
```

The plugin code needs to import many definitions from the Netbox code base.  Netbox is a collection
of Django Apps, and are not installable as python modules (i.e. no `pip install dcim`).  To assist
your editors LSP (import resolution, code completion etc), the Netbox source code is included as a
sub module and the `pyproject.toml` includes configuration for `pyright` (common LSP used by VSCode,
Neovim etc) so that it will find imports from within the Netbox code base.

## Testing

There is an integration framework that starts a Docker compose stack that includes Netbox with the
plugin installed and some canned data that allows for testing the various elements of the business
logic involved in IP lease resolution.

```console
cd test/
pytest -vv
```

Unit testing is on the TODO list.
