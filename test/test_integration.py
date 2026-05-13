import netaddr
import requests
import time

from datetime import datetime, timedelta

from .conftest import NETBOX_API, NETBOX_DHCP_API

class TestAPIIntegration:
    def test_netbox_available(self, api_client: requests.Session) -> None:
        for _ in range(120):
            resp = api_client.get(f"{NETBOX_API}/status/")
            if resp.status_code == 200:
                return

            time.sleep(1)

        assert False, "Netbox did not come online within 120 secs"

    def test_get_lease_for_unknown_mac(self, api_client: requests.Session) -> None:
        '''Test that a DHCP request with a MAC not associated with any interface gets
        an IP address designated for DHCP according to its status from the correct subnet
        '''

        mac = "02:01:01:01:01:01"
        data = {
            "mac_address": mac,
            "hostname": "random",
            "client_id": f"01:{mac}",
            "receiving_ip": "172.19.0.254",
        }

        resp = api_client.post(NETBOX_DHCP_API, json=data)

        assert resp.status_code == 201, resp.text
        lease = resp.json()
        assert lease.get("ip_address", None) is not None, "did not get an IP address"
        leased_ip = netaddr.IPNetwork(lease["ip_address"]["address"])
        lease_range = netaddr.IPRange("172.19.0.100", "172.19.0.109")
        assert leased_ip.ip in lease_range, f"expected a ip tagged dhcp, got {leased_ip}"

    def test_get_lease_basic_interface_no_ip(self, api_client: requests.Session) -> None:
        '''Test that a DHCP request with a MAC associated with an interface with NO IP gets
        an IP address designated for DHCP according to its status from the correct subnet
        '''

        mac = "01:00:00:00:00:02"
        data = {
            "mac_address": mac,
            "hostname": "random",
            "client_id": f"01:{mac}",
            "receiving_ip": "172.19.0.254",
        }

        resp = api_client.post(NETBOX_DHCP_API, json=data)

        assert resp.status_code == 201, resp.text
        lease = resp.json()
        assert lease.get("ip_address", None) is not None, "did not get an IP address"
        leased_ip = netaddr.IPNetwork(lease["ip_address"]["address"])
        lease_range = netaddr.IPRange("172.19.0.100", "172.19.0.109")
        assert leased_ip.ip in lease_range, f"expected a ip tagged dhcp, got {leased_ip}"

    def test_get_lease_basic_interface_with_ip(self, api_client: requests.Session) -> None:
        '''Test that a DHCP request with a MAC address configured on an interface with an IP
        address, returns the interfaces IP Address.
        '''

        mac = "01:00:00:00:00:01"
        data = {
            "mac_address": mac,
            "hostname": "random",
            "client_id": f"01:{mac}",
            "receiving_ip": "172.19.0.254",
        }

        resp = api_client.post(NETBOX_DHCP_API, json=data)

        assert resp.status_code == 201, resp.text
        lease = resp.json()
        assert lease.get("ip_address", None) is not None, "did not get an IP address"
        assert lease["ip_address"]["address"] == "172.19.0.10/24"

    def test_get_lease_lag_interface_with_ip(self, api_client: requests.Session) -> None:
        '''Test that a DHCP request with a MAC address configured on a LAG interface with an IP
        address, returns the interfaces IP Address.
        '''

        mac = "01:00:00:00:00:03"
        data = {
            "mac_address": mac,
            "hostname": "random",
            "client_id": f"01:{mac}",
            "receiving_ip": "172.19.0.254",
        }

        resp = api_client.post(NETBOX_DHCP_API, json=data)

        assert resp.status_code == 201, resp.text
        lease = resp.json()
        assert lease.get("ip_address", None) is not None, "did not get an IP address"
        assert lease["ip_address"]["address"] == "172.19.0.11/24"

    def test_get_lease_lag_member_no_ip(self, api_client: requests.Session) -> None:
        '''Test that a DHCP request with a MAC address of a LAG member with where the LAG
        has a different MAC address is ignored.
        '''

        mac = "01:00:00:00:00:04"
        data = {
            "mac_address": mac,
            "hostname": "random",
            "client_id": f"01:{mac}",
            "receiving_ip": "172.19.0.254",
        }

        resp = api_client.post(NETBOX_DHCP_API, json=data)

        assert resp.status_code == 404, "Request should have been ignored"

    def test_dhcp_lifecycle(self, api_client) -> None:
        '''Test the typical workflow of a DHCP server using this backend'''

        mac = "02:01:01:01:01:01"
        data = {
            "mac_address": mac,
            "hostname": "random",
            "client_id": f"01:{mac}",
            "receiving_ip": "172.19.0.254",
        }

        resp = api_client.post(NETBOX_DHCP_API, json=data)

        # Handle a discover
        assert resp.status_code == 201, f"DISCOVER FAILED: {resp.text}"
        lease = resp.json()
        assert lease.get("ip_address", None) is not None, "did not get an IP address"
        assert lease["acknowledged"] is False, "Lease after discover should not be acknowledged"
        leased_ip = netaddr.IPNetwork(lease["ip_address"]["address"])
        lease_range = netaddr.IPRange("172.19.0.100", "172.19.0.109")
        assert leased_ip.ip in lease_range, f"expected a ip tagged dhcp, got {leased_ip}"

        # Handle a request
        existing_lease_resp = api_client.get(NETBOX_DHCP_API, params={"mac_address": mac})
        assert existing_lease_resp.status_code == 200, f"REQUEST FAILED: {existing_lease_resp.text}"
        existing_lease = existing_lease_resp.json()["results"][0]
        existing_lease["acknowledged"] = True

        put_resp = api_client.put(existing_lease["url"], json=existing_lease)
        assert put_resp.status_code == 200, f"REQUEST FAILED: {put_resp.text}"
        requested_lease = put_resp.json()
        assert requested_lease["acknowledged"] is True, "Lease after request should be acknowledged"

        # Handle a renew
        time.sleep(1)
        existing_lease_resp = api_client.get(NETBOX_DHCP_API, params={"mac_address": mac})
        assert existing_lease_resp.status_code == 200, f"REQUEST FAILED: {existing_lease_resp.text}"
        existing_lease = existing_lease_resp.json()["results"][0]
        put_resp = api_client.put(existing_lease["url"], json=existing_lease)
        assert put_resp.status_code == 200, f"REQUEST FAILED: {put_resp.text}"
        renewed_lease = put_resp.json()

        original_expire = datetime.fromisoformat(requested_lease["expire_time"])
        renewed_expire = datetime.fromisoformat(renewed_lease["expire_time"])
        expire_diff = renewed_expire - original_expire
        assert timedelta(seconds=0) < expire_diff < timedelta(seconds=2), "RENEW: expire time not updated"

        # Handle a release
        existing_lease_resp = api_client.get(NETBOX_DHCP_API, params={"mac_address": mac})
        assert existing_lease_resp.status_code == 200, f"REQUEST FAILED: {existing_lease_resp.text}"
        existing_lease = existing_lease_resp.json()["results"][0]
        release_resp = api_client.delete(existing_lease["url"])
        assert release_resp.status_code == 204
