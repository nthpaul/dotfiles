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
from validate import validate


class CommandTests(unittest.TestCase):
    def test_default_scaffold_is_editable_portable_html(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "memo"
            result = plan.scaffold(destination)
            html = (destination / "preview.html").read_text()
            self.assertEqual(result["format"], "html")
            self.assertEqual({file.name for file in destination.iterdir()}, {"preview.html"})
            self.assertIn("data:font/ttf;base64,", html)
            self.assertNotIn("{{FONT_FACES}}", html)
            self.assertNotIn("window.PLAN", html)
            self.assertTrue(validate(destination)["ok"])

    def test_structured_scaffold_is_neutral(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "structured"
            result = plan.scaffold(destination, structured=True)
            import json
            authored = json.loads((destination / "plan.json").read_text())
            self.assertEqual(result["format"], "structured")
            self.assertEqual(set(authored), {"document", "summary"})
            self.assertEqual({file.name for file in destination.iterdir()}, {"plan.json"})

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

    def test_tailored_html_can_publish_without_a_model_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            html = Path(directory) / "memo.html"
            html.write_text("<!doctype html><html><head><title>Pilot decision</title></head>"
                            "<body><h1>Use the weekly export</h1><p>Review after four weeks.</p></body></html>")
            def relay(arguments, check):
                if arguments[2] == "get":
                    shutil.copyfile(html, arguments[-1])
            with patch("plan.subprocess.run", side_effect=relay):
                result = plan.publish(html, "/paul/example/memo.html", "relay")
            self.assertEqual(Path(result["readback"]).read_bytes(), html.read_bytes())

    def test_tailored_validation_checks_only_actual_portability(self):
        with tempfile.TemporaryDirectory() as directory:
            html = Path(directory) / "memo.html"
            content = "<!doctype html><html><head><title>Decision</title></head><body>{}</body></html>"
            html.write_text(content.format("<p>A short recommendation with no scripts or downloads.</p>"))
            report = validate(html)
            self.assertTrue(report["ok"], report)
            self.assertEqual(report["counts"], {"downloads": 0, "inlineScripts": 0})
            for external in ("<img src='chart.png'>", "<script src='https://cdn.example/test.js'></script>",
                             "<img srcset='small.png 1x, large.png 2x'>",
                             "<style>p{background:url(image.png)}</style>",
                             "<a download='notes.md' href='notes.md'>Notes</a>"):
                with self.subTest(external=external):
                    html.write_text(content.format(external))
                    self.assertFalse(validate(html)["ok"])
            html.write_text(content.format("<img alt='Illustrative' srcset='data:image/png;base64,AAAA 1x, data:image/png;base64,BBBB 2x'>"))
            self.assertTrue(validate(html)["ok"])

    def test_tailored_script_globals_do_not_select_the_structured_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            html = Path(directory) / "memo.html"
            html.write_text("<!doctype html><html><head><title>Decision</title></head>"
                            "<body><h1>Review the pilot</h1>"
                            "<script>window.PLAN = {recommendation:'Weekly export'};</script>"
                            "<script>window.DIAGRAMS = [];</script></body></html>")
            report = validate(html)
            self.assertTrue(report["ok"], report)
            self.assertEqual(report["counts"], {"downloads": 0, "inlineScripts": 2})


if __name__ == "__main__":
    unittest.main()
