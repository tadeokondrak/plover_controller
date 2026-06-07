import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from plover_controller.profiles import (
    BUILTIN_PROFILES,
    delete_profile,
    is_builtin,
    list_profile_names,
    load_builtin_profile,
    load_profile,
    load_user_profiles,
    save_profile,
    export_profile,
    import_profile,
)
from plover_controller.config import Mappings


class TestBuiltinProfiles(unittest.TestCase):
    def test_builtin_profiles_exist(self):
        self.assertGreater(len(BUILTIN_PROFILES), 0)

    def test_all_builtins_load(self):
        for name in BUILTIN_PROFILES:
            mapping = load_builtin_profile(name)
            self.assertIsNotNone(mapping, f"Built-in profile '{name}' failed to load")
            self.assertGreater(len(mapping), 0)

    def test_all_builtins_parse(self):
        for name in BUILTIN_PROFILES:
            mapping = load_builtin_profile(name)
            m = Mappings.parse(mapping)
            self.assertGreater(
                len(m.unordered_mappings) + len(m.ordered_mappings), 0,
                f"Built-in profile '{name}' has no mappings"
            )

    def test_nonexistent_builtin_returns_none(self):
        self.assertIsNone(load_builtin_profile("Nonexistent Controller"))

    def test_is_builtin(self):
        for name in BUILTIN_PROFILES:
            self.assertTrue(is_builtin(name))
        self.assertFalse(is_builtin("My Custom Profile"))


class TestUserProfiles(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._profiles_path = Path(self._tmpdir.name) / "controller_profiles.json"
        self._patcher = patch(
            "plover_controller.profiles.get_profiles_path",
            return_value=self._profiles_path,
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        self._tmpdir.cleanup()

    def test_load_empty(self):
        profiles = load_user_profiles()
        self.assertEqual(profiles, {})

    def test_save_and_load(self):
        save_profile("test", "a -> -S")
        profiles = load_user_profiles()
        self.assertIn("test", profiles)
        self.assertEqual(profiles["test"], "a -> -S")

    def test_save_overwrites(self):
        save_profile("test", "a -> -S")
        save_profile("test", "b -> -Z")
        profiles = load_user_profiles()
        self.assertEqual(profiles["test"], "b -> -Z")

    def test_delete_user_profile(self):
        save_profile("test", "a -> -S")
        result = delete_profile("test")
        self.assertTrue(result)
        profiles = load_user_profiles()
        self.assertNotIn("test", profiles)

    def test_delete_nonexistent(self):
        result = delete_profile("nope")
        self.assertFalse(result)

    def test_cannot_delete_builtin(self):
        for name in BUILTIN_PROFILES:
            result = delete_profile(name)
            self.assertFalse(result)

    def test_load_profile_user(self):
        save_profile("custom", "x -> -T")
        mapping = load_profile("custom")
        self.assertEqual(mapping, "x -> -T")

    def test_load_profile_builtin(self):
        for name in BUILTIN_PROFILES:
            mapping = load_profile(name)
            self.assertIsNotNone(mapping)

    def test_load_profile_nonexistent(self):
        self.assertIsNone(load_profile("doesn't exist"))

    def test_list_profile_names(self):
        save_profile("my_profile", "a -> -S")
        names = list_profile_names()
        self.assertIn("my_profile", names)
        for builtin in BUILTIN_PROFILES:
            self.assertIn(builtin, names)

    def test_profiles_file_format(self):
        save_profile("test", "a -> -S")
        with open(self._profiles_path, "r") as f:
            data = json.load(f)
        self.assertIn("version", data)
        self.assertIn("profiles", data)
        self.assertIn("test", data["profiles"])

    def test_export_profile(self):
        save_profile("test", "a -> -S\nb -> -Z")
        export_path = Path(self._tmpdir.name) / "exported.txt"
        result = export_profile("test", export_path)
        self.assertTrue(result)
        with open(export_path, "r") as f:
            content = f.read()
        self.assertEqual(content, "a -> -S\nb -> -Z")

    def test_export_nonexistent(self):
        export_path = Path(self._tmpdir.name) / "exported.txt"
        result = export_profile("nope", export_path)
        self.assertFalse(result)

    def test_import_profile(self):
        import_path = Path(self._tmpdir.name) / "my_mapping.txt"
        with open(import_path, "w") as f:
            f.write("x -> -T\ny -> -D")
        name, mapping = import_profile(import_path)
        self.assertEqual(name, "my_mapping")
        self.assertEqual(mapping, "x -> -T\ny -> -D")


if __name__ == "__main__":
    unittest.main()
