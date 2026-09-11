import base64
import pytest
from ops.provision_private_link import configuration

KEY = base64.b64encode(b"0" * 32).decode()


def test_link_has_only_one_host_route_and_no_dns_nat_or_firewall():
    config = configuration("10.77.0.1", "10.77.0.2", "91.221.68.94", KEY, KEY)
    assert "Address = 10.77.0.1/32" in config
    assert "AllowedIPs = 10.77.0.2/32" in config
    for forbidden in ("0.0.0.0/0", "DNS", "PostUp", "PostDown", "iptables", "SaveConfig"):
        assert forbidden not in config


@pytest.mark.parametrize("local,peer,endpoint", [
    ("10.77.0.1", "10.77.0.1", "91.221.68.94"),
    ("91.221.68.90", "10.77.0.2", "91.221.68.94"),
    ("10.77.0.1", "10.77.0.2", "127.0.0.1"),
])
def test_refuses_invalid_addresses(local, peer, endpoint):
    with pytest.raises(ValueError):
        configuration(local, peer, endpoint, KEY, KEY)
