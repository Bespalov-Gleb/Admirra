"""No network/kernel changes: peer policy and idempotent command plan."""
import base64
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import add_api2_peer as peer

KEY1 = base64.b64encode(b"a" * 32).decode()
KEY2 = base64.b64encode(b"b" * 32).decode()
CONFIG = ("[Interface]\nAddress = 10.78.0.3/32\nPrivateKey = synthetic-test-only\n"
          f"\n[Peer]\nPublicKey = {KEY1}\nAllowedIPs = 10.78.0.1/32\n"
          "Endpoint = 91.221.68.90:51821\nPersistentKeepalive = 25\n")


class PeerTests(unittest.TestCase):
    def test_preserves_existing_config_and_is_idempotent(self):
        candidate, old_peers = peer.plan(CONFIG, KEY2)
        self.assertTrue(candidate.startswith(CONFIG))
        self.assertEqual(len(old_peers), 1)
        self.assertEqual(peer.plan(candidate, KEY2)[0], candidate)
        self.assertEqual(candidate.count("[Peer]"), 2)

    def test_rejects_invalid_key_or_wrong_host(self):
        for config, key in ((CONFIG, "not-a-key"), (CONFIG, KEY1),
                            (CONFIG.replace("10.78.0.3", "10.78.0.2"), KEY2),
                            (CONFIG.replace("PrivateKey", "SaveConfig = true\nPrivateKey"), KEY2)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                peer.plan(config, key)

    def test_rejects_address_takeover(self):
        candidate, _ = peer.plan(CONFIG, KEY2)
        for altered in (candidate.replace(KEY2, base64.b64encode(b"c" * 32).decode()),
                        candidate.replace("91.221.68.94", "91.221.68.95"),
                        CONFIG.replace("10.78.0.1/32", "10.78.0.0/24")):
            with self.assertRaises(ValueError):
                peer.plan(altered, KEY2)

    def test_apply_preserves_peer_and_persists_private_backup(self):
        live = {KEY1: "10.78.0.1/32"}
        routes = []

        def run(*command):
            if command == ("wg", "show", "admirraai", "allowed-ips"):
                return "\n".join(f"{key}\t{address}" for key, address in live.items())
            if command == ("ip", "-j", "route"):
                import json
                return json.dumps(routes)
            if command[:3] == ("wg", "set", "admirraai"):
                self.assertEqual(command[4], KEY2)
                live[KEY2] = "10.78.0.2/32"
                return ""
            if command == ("ip", "route", "add", "10.78.0.2/32", "dev", "admirraai"):
                routes.append({"dst": "10.78.0.2", "dev": "admirraai"})
                return ""
            self.fail(f"Unexpected command {command}")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "admirraai.conf").write_text(CONFIG)
            with patch.object(peer, "ROOT", root), patch.object(peer, "run", side_effect=run) as calls:
                peer.apply(KEY2)
                peer.apply(KEY2)
            self.assertEqual(live[KEY1], "10.78.0.1/32")
            backup = root / "admirraai.before-api2.conf"
            self.assertEqual(backup.read_text(), CONFIG)
            self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
            self.assertEqual((root / "admirraai.conf").stat().st_mode & 0o777, 0o600)
            self.assertEqual(len(routes), 1)
            self.assertFalse(any("restart" in call.args for call in calls.call_args_list))

    def test_runtime_drift_has_no_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "admirraai.conf"
            config.write_text(CONFIG)
            with patch.object(peer, "ROOT", root), patch.object(peer, "run", return_value=""):
                with self.assertRaises(ValueError):
                    peer.apply(KEY2)
            self.assertEqual(config.read_text(), CONFIG)
            self.assertFalse((root / "admirraai.before-api2.conf").exists())


if __name__ == "__main__":
    unittest.main()
