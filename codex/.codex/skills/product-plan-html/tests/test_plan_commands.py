from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import plan


class CommandTests(unittest.TestCase):
    def test_scaffold_preserves_existing_user_files(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "project"
            destination.mkdir()
            original = destination / "notes.txt"
            original.write_text("Keep this")
            with self.assertRaisesRegex(ValueError, "empty"):
                plan.scaffold(destination)
            self.assertEqual(original.read_text(), "Keep this")

    def test_archive_contains_portable_sources_and_licenses(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "skill.zip"
            result = plan.package(archive)
            with zipfile.ZipFile(archive) as content:
                names = content.namelist()
                self.assertEqual(result["files"], len(names))
                for name in ["SKILL.md", "scripts/plan.py", "assets/vendor/viz.js",
                             "assets/vendor/package.json", "assets/vendor/LICENSE-viz.txt",
                             "assets/viewer/fonts/OFL.txt", "references/fallbacks/architecture.md"]:
                    self.assertIn("product-plan-html/" + name, names)
                self.assertFalse(any("__pycache__" in name for name in names))
                self.assertFalse(any(name.startswith("/") or ".." in Path(name).parts for name in names))
                self.assertEqual(content.read("product-plan-html/assets/vendor/viz.js"),
                                 (ROOT / "assets/vendor/viz.js").read_bytes())

    def test_publication_verifies_actual_readback_with_mocked_transport(self):
        with tempfile.TemporaryDirectory() as directory:
            html = Path(directory) / "preview.html"
            html.write_text("<html>Illustrative transport fixture</html>")
            calls = []
            def relay(arguments, check):
                calls.append(arguments)
                if arguments[2] == "get":
                    shutil.copyfile(html, arguments[-1])
            with patch("validate.validate", return_value={"ok": True}), patch("plan.subprocess.run", side_effect=relay):
                result = plan.publish(html, "/paul/example/plan.html", "relay")
            self.assertEqual([call[2] for call in calls], ["put", "get"])
            self.assertEqual(Path(result["readback"]).read_bytes(), html.read_bytes())
            self.assertEqual(result["url"], "https://relay.traba.work/library/paul/example/plan.html")
            def mismatch(arguments, check):
                if arguments[2] == "get":
                    Path(arguments[-1]).write_text("Different content")
            with patch("validate.validate", return_value={"ok": True}), patch("plan.subprocess.run", side_effect=mismatch):
                with self.assertRaisesRegex(ValueError, "readback differs"):
                    plan.publish(html, "/paul/example/plan.html", "relay")


if __name__ == "__main__":
    unittest.main()
