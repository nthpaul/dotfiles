"""Exercise portable builds and source-preservation boundaries with a small new plan."""

from pathlib import Path
import hashlib
import json
import re
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET


PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / "scripts"))
from build import build, resolve_node
from validate import validate


class BuildToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.node = resolve_node()
        except ValueError as exc:
            raise unittest.SkipTest(str(exc))

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="product-plan-build-tools-")
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.out = self.root / "output"
        self.plan = {
            "document": {"title": "Request review", "date": "Draft", "sources": [["Requirements", "https://example.com/requirements"]]},
            "tables": [{"name": "requests", "purpose": "One owned request awaiting review.",
                        "fields": [{"name": "id", "type": "uuid PK", "rule": "Stable request ID.", "relation": ""},
                                   {"name": "workerId", "type": "text FK", "rule": "Owner.", "relation": "workers.id", "unique": True},
                                   {"name": "status", "type": "enum", "rule": "PENDING or APPROVED.", "relation": ""},
                                   {"name": "createdAt", "type": "timestamptz", "rule": "Server creation time.", "relation": ""}],
                        "constraints": ["Only a pending request may be approved."], "relationships": "workers 1:0..1 requests."}],
            "referenceTables": [{"name": "workers", "fields": [{"name": "id", "type": "text PK"}]}],
            "existing": [], "decisions": ["Review state has one owner."], "questions": [], "sources": [],
            "flows": [{"id": "review", "title": "Review request", "summary": "An authorized approval changes one request.",
                       "steps": [["Approve", "Request and authenticated actor", "Check ownership and current state", "Set APPROVED", "Updated request"]]}],
        }
        self.save_plan()

    def tearDown(self):
        self.temporary.cleanup()

    def save_plan(self):
        (self.project / "plan.json").write_text(json.dumps(self.plan), encoding="utf-8")

    def build(self):
        return build(self.project, self.out, self.node)

    def output_hashes(self):
        return {str(path.relative_to(self.out)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.out.rglob("*") if path.is_file()}

    def test_generated_schema_and_structured_flow_share_declared_inputs(self):
        diagrams = [{"id": "review", "title": "Review", "description": "One authorized transition.",
                     "nodes": [{"id": "input", "label": "Request + actor", "kind": "input"},
                               {"id": "check", "label": "Authorized?", "kind": "decision"},
                               {"id": "save", "label": "Persist approval", "kind": "state"}],
                     "edges": [{"from": "input", "to": "check"}, {"from": "check", "to": "save", "label": "Yes"}]}]
        (self.project / "diagrams.json").write_text(json.dumps(diagrams), encoding="utf-8")
        result = self.build()
        self.assertTrue(result["ok"])
        self.assertEqual(result["counts"]["diagrams"], 3)
        manifest = json.loads((self.out / "diagrams/manifest.json").read_text())
        self.assertEqual([row["id"] for row in manifest], ["model", "model-full", "review"])
        schema = (self.out / "diagrams/model-full.dot").read_text()
        self.assertIn('"workers" -> "requests"', schema)
        self.assertIn("1 → 0..1 · workerId", schema)
        self.assertIn("workers · existing · referenced columns", schema)
        self.assertRegex(schema, r'<TD WIDTH="\d+" ALIGN="LEFT">id</TD><TD WIDTH="\d+" ALIGN="LEFT">text PK</TD>')
        schema_mermaid = (self.out / "diagrams/model-full.mmd").read_text()
        self.assertIn('text id PK "existing · referenced columns"', schema_mermaid)
        self.assertNotIn("unknown id", schema_mermaid)
        schema_svg = (self.out / "diagrams/model-full.svg").read_text()
        self.assertIn("existing · referenced columns", schema_svg)
        self.assertIn(">text PK</text>", schema_svg)
        for field in self.plan["tables"][0]["fields"]:
            self.assertIn(field["name"], schema)
        flow_dot = (self.out / "diagrams/review.dot").read_text()
        flow_mermaid = (self.out / "diagrams/review.mmd").read_text()
        self.assertIn('"check" -> "save" [label="Yes"]', flow_dot)
        self.assertIn('check -->|"Yes"| save', flow_mermaid)

    def test_schema_only_plan_and_copied_standalone_html(self):
        self.plan["document"]["title"] = "Literal </SCRIPT> and \u2028\u2029"
        self.save_plan()
        (self.project / "prototype.js").write_text('window.TEST_LITERAL = "</ScRiPt>\u2028\u2029";\n', encoding="utf-8")
        result = self.build()
        self.assertEqual(result["counts"]["diagrams"], 2)
        single = self.root / "single.html"
        shutil.copyfile(self.out / "preview.html", single)
        shutil.rmtree(self.out)
        shutil.rmtree(self.project)
        report = validate(single)
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["counts"]["fields"], 4)
        self.assertEqual(report["counts"]["relations"], 1)
        self.assertEqual(report["counts"]["inlineScripts"], 4)

    def test_existing_column_without_declared_type_stays_unknown(self):
        self.plan["referenceTables"][0]["fields"] = ["id"]
        self.save_plan()
        self.build()
        mermaid = (self.out / "diagrams/model-full.mmd").read_text()
        self.assertIn('unknown id "existing · referenced columns"', mermaid)
        self.assertNotIn("unknown id PK", mermaid)

    def test_certification_captions_and_authored_markdown(self):
        self.plan = json.loads((PACKAGE / "tests/fixtures/equipment-certification-plan.json").read_text())
        self.save_plan()
        self.build()
        dot = (self.out / "diagrams/model-full.dot").read_text()
        svg = ET.fromstring((self.out / "diagrams/model-full.svg").read_text())
        namespace = {"svg": "http://www.w3.org/2000/svg"}
        for caption, minimum in [
            ("equipment_certification_submissions · new", 284),
            ("equipment_certification_review_events · new", 297),
            ("Worker · existing · referenced columns", 247),
        ]:
            match = re.search(r'<TD WIDTH="(\d+)" COLSPAN="2" ALIGN="LEFT" BGCOLOR="[^"]+">' + re.escape(caption), dot)
            self.assertIsNotNone(match, caption)
            self.assertGreaterEqual(int(match.group(1)), minimum)
            node = next(node for node in svg.findall(".//svg:g[@class='node']", namespace)
                        if any(text.text == caption for text in node.findall("svg:text", namespace)))
            text = next(text for text in node.findall("svg:text", namespace) if text.text == caption)
            header = next(polygon for polygon in node.findall("svg:polygon", namespace)
                          if polygon.get("fill") in ("#e6ccff", "#edf8f3"))
            edges = [float(point.split(",")[0]) for point in header.get("points").split()]
            self.assertEqual(text.get("text-anchor"), "start")
            self.assertAlmostEqual(float(text.get("x")) - min(edges), 6)
            self.assertGreaterEqual(max(edges) - float(text.get("x")), minimum - 20)
        self.assertIn("1 → 0..N · workerId", dot)
        markdown = (self.out / "build-plan.md").read_text()
        summary = self.plan["summary"]
        for key in ("decision", "nextAction", "evidence"):
            self.assertIn(summary[key], markdown)
        for key in ("reuse", "netNew", "buildSequence"):
            for value in summary[key]:
                self.assertIn(value, markdown)
        for key in ("modelIntro", "modelConventionsTitle", "notStored", "flowContract", "diagramNote"):
            self.assertIn(self.plan["document"][key], markdown)
        for note in self.plan["document"]["flowNotes"]:
            self.assertIn(note["title"], markdown)
            self.assertIn(note["text"], markdown)
        self.assertLess(markdown.index(summary["decision"]), markdown.index("## Source requirements"))
        self.assertLess(markdown.index(summary["nextAction"]), markdown.index("## Source requirements"))

    def test_malformed_javascript_preserves_previous_build(self):
        self.build()
        original = self.output_hashes()
        (self.project / "prototype.js").write_text("window.DEMO = { malformed: ; };\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "prototype.js"):
            self.build()
        self.assertEqual(self.output_hashes(), original)

    def test_invalid_foreign_key_preserves_existing_build(self):
        self.build()
        original = self.output_hashes()
        self.plan["tables"][0]["fields"][1]["relation"] = "missing_table.id"
        self.save_plan()
        with self.assertRaisesRegex(ValueError, "undeclared relation target"):
            self.build()
        self.assertEqual(self.output_hashes(), original)

    def test_output_boundaries_preserve_source_and_unrelated_files(self):
        original = (self.project / "plan.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "overwrite"):
            build(self.project, self.project, self.node)
        self.assertEqual((self.project / "plan.json").read_bytes(), original)
        self.out.mkdir()
        sentinel = self.out / "keep.txt"
        sentinel.write_text("unrelated", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Refusing to replace"):
            self.build()
        self.assertEqual(sentinel.read_text(), "unrelated")

    def test_input_symlink_cannot_escape_project(self):
        outside = self.root / "outside.js"
        outside.write_text("window.OUTSIDE = true;", encoding="utf-8")
        try:
            (self.project / "prototype.js").symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"Symlinks unavailable: {exc}")
        with self.assertRaisesRegex(ValueError, "escapes artifact directory"):
            self.build()
        self.assertFalse(self.out.exists())
        self.assertEqual(outside.read_text(), "window.OUTSIDE = true;")


if __name__ == "__main__":
    unittest.main()
