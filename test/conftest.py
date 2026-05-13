import os
import subprocess
import time

import pytest
import requests

NETBOX_URL = os.environ.get("NETBOX_URL", "http://localhost:8000")
NETBOX_API = f"{NETBOX_URL}/api"
NETBOX_DHCP_API = f"{NETBOX_API}/plugins/dhcp/leases/"
NETBOX_TIMEOUT = 300

USERNAME = "dhcp"
API_TOKEN = "nbt_Ohje7giet3uT.215e4324a3a621a5ea1619d6c08c6d3b90bf19c9"

DOCKER_BIN = "/usr/bin/docker"
DOCKER_DIR = os.path.join(os.path.dirname(__file__), "integration")


@pytest.fixture(scope="session")
def netbox_service():
    result = subprocess.run(
        [DOCKER_BIN, "compose", "up", "-d"],
        cwd=DOCKER_DIR,
        capture_output=True,
    )
    try:
        result.check_returncode()
    except:
        print(result.stdout)
        print(result.stderr)
        raise

    yield

    result = subprocess.run([DOCKER_BIN, "compose", "down"], cwd=DOCKER_DIR)
    result.check_returncode()


@pytest.fixture
def api_client(netbox_service) -> requests.Session:
    client = requests.Session()
    client.headers.update(
        {
            "Authorization": f"Bearer {API_TOKEN}",
            "Accept": "application/json; indent=4",
        }
    )

    for _ in range(NETBOX_TIMEOUT):
        try:
            resp = client.get(f"{NETBOX_API}/status/")
        except:
            time.sleep(1)
            continue

        if resp.status_code == 200:
            break

        print(resp.json())
        time.sleep(1)
    else:
        raise Exception(f"Netbox did not become available within {NETBOX_TIMEOUT} seconds")

    resp = client.get(NETBOX_DHCP_API)
    resp.raise_for_status()

    existing_leases = resp.json()["results"]
    for lease in existing_leases:
        del_resp = client.delete(lease["url"])
        del_resp.raise_for_status()

    return client
