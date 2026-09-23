"""The rehearsal firewall must not alter the production port/default policy."""
import pytest
from ops.multihost_rehearsal import rules


@pytest.mark.parametrize('node', [1, 2])
def test_rehearsal_egress_is_bounded_to_peer_test_ports(node):
    rows = rules(node)
    assert rows[-1] == ['-j', 'DROP']
    incoming = rows[2]
    assert incoming[:4] == ['-i', 'admirra0', '-s', f'10.77.0.{3-node}']
    outgoing = rows[3]
    assert outgoing[:4] == ['-i', f'admrtest{node}', '-d', f'10.77.0.{3-node}']
    assert outgoing[-3:] == ['26379' if node == 1 else '25432,18081', '-j', 'ACCEPT']
    assert not any('0.0.0.0/0' in row for row in rows)
