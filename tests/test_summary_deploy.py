import unittest

from ops.performance.deploy import mount_config


class MountConfigTests(unittest.TestCase):
    def test_mount_order_is_not_configuration_drift(self):
        a = {"Destination": "/app/secrets", "Source": "/private/secrets", "RW": False}
        b = {"Destination": "/app/uploads", "Source": "/data/uploads", "RW": True}
        self.assertEqual(mount_config({"Mounts": [a, b]}), mount_config({"Mounts": [b, a]}))
        changed = {**a, "RW": True}
        self.assertNotEqual(mount_config({"Mounts": [a, b]}), mount_config({"Mounts": [changed, b]}))
        changed = {**a, "Source": "/different/secrets"}
        self.assertNotEqual(mount_config({"Mounts": [a, b]}), mount_config({"Mounts": [changed, b]}))


    def test_duplicate_mount_destinations_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Duplicate"):
            mount_config({"Mounts": [{"Destination": "/app"}, {"Destination": "/app"}]})
