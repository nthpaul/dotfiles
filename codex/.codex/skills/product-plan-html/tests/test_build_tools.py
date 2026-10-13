"""Exercise portable builds and source-preservation boundaries with a small new plan."""

from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET


PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / "scripts"))
from build import build, load_diagrams, resolve_node
from validate import check_plan, validate


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
            "schemaDiagrams": ["model", "model-full"],
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

    def test_table_extensions_render_existing_storage_and_correct_counts(self):
        self.plan["tables"][0]["storage"] = "extension"
        for new_count in (0, 1):
            with self.subTest(new_tables=new_count):
                if new_count:
                    self.plan["tables"].append({"name": "events", "purpose": "New event log.",
                        "fields": [{"name": "id", "type": "uuid PK", "rule": "Stable event ID.", "relation": ""}],
                        "constraints": [], "relationships": ""})
                self.save_plan()
                result = self.build()
                self.assertEqual(result["counts"]["newTables"], new_count)
                self.assertEqual(result["counts"]["extendedTables"], 1)
                for diagram_id in ("model", "model-full"):
                    dot = (self.out / f"diagrams/{diagram_id}.dot").read_text()
                    self.assertIn('BGCOLOR="#edf8f3">requests · existing · proposed extension', dot)
                    self.assertNotIn("requests · new", dot)
                    mermaid = (self.out / f"diagrams/{diagram_id}.mmd").read_text()
                    self.assertIn("requests: existing · proposed extension", mermaid)
                    svg = (self.out / f"diagrams/{diagram_id}.svg").read_text()
                    self.assertIn("requests · existing · proposed extension", svg)
                manifest = json.loads((self.out / "diagrams/manifest.json").read_text())
                self.assertIn(f"{new_count} new {'table' if new_count == 1 else 'tables'} and 1 extended existing table", manifest[0]["description"])
                self.assertIn("Existing table · proposed extension.", (self.out / "build-plan.md").read_text())
                script = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const elements = new Map();
const context = {
  PLAN: JSON.parse(fs.readFileSync(process.argv[1], 'utf8')), DIAGRAMS: [],
  location: {hash: ''}, history: {replaceState() {}},
  document: {
    documentElement: {dataset: {}}, addEventListener() {},
    querySelector(selector) {
      if (!elements.has(selector)) elements.set(selector, {innerHTML:'',addEventListener(){},querySelectorAll(){return [];}});
      return elements.get(selector);
    }
  }, addEventListener() {}, scrollTo() {}
};
context.window = context;
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), context);
const overview = elements.get('#app').innerHTML;
if (process.argv[3] === '0') assert.ok(!overview.includes('<h3>new tables</h3>'));
else assert.ok(overview.includes(`<div class="metric">${process.argv[3]}</div><h3>new tables</h3>`));
assert.ok(overview.includes('<div class="metric">1</div><h3>existing tables extended</h3>'));
context.PlanDocument.setView('model');
assert.ok(elements.get('#app').innerHTML.includes('<span class="badge green">Existing · proposed extension</span>'));
"""
                subprocess.run([self.node, "-e", script, str(self.out / "data-model.json"),
                                str(self.out / "viewer.js"), str(new_count)], check=True, capture_output=True, text=True)

    def test_table_storage_defaults_new_and_rejects_unknown_values(self):
        report = check_plan(self.plan)
        self.assertEqual(report["counts"]["newTables"], 1)
        self.assertEqual(report["counts"]["extendedTables"], 0)
        for value in ("existing", None, ["extension"]):
            with self.subTest(storage=value):
                self.plan["tables"][0]["storage"] = value
                report = check_plan(self.plan)
                self.assertFalse(report["ok"])
                self.assertIn("requests.storage must be new or extension", report["errors"])

    def test_certification_captions_and_authored_markdown(self):
        self.plan = json.loads((PACKAGE / "tests/fixtures/equipment-certification-plan.json").read_text())
        self.plan["schemaDiagrams"] = ["model-full"]
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

    def test_tables_do_not_implicitly_select_schema_diagrams(self):
        self.plan.pop("schemaDiagrams")
        self.save_plan()
        result = self.build()
        self.assertEqual(result["counts"]["diagrams"], 0)
        self.assertEqual(result["counts"]["downloads"], 2)
        self.assertFalse((self.out / "diagrams.md").exists())
        self.assertFalse((self.out / "diagrams/model.svg").exists())
        self.assertNotIn("## Diagrams", (self.out / "build-plan.md").read_text())

    def test_selected_schema_view_and_authored_diagrams_remain_distinct(self):
        self.plan["schemaDiagrams"] = ["model-full"]
        self.save_plan()
        self.build()
        manifest = json.loads((self.out / "diagrams/manifest.json").read_text())
        self.assertEqual([diagram["id"] for diagram in manifest], ["model-full"])
        self.assertFalse((self.out / "diagrams/model.svg").exists())
        self.plan.pop("schemaDiagrams")
        self.save_plan()
        authored = [{"id": "model", "title": "Selected concept", "nodes": [{"id": "concept", "label": "One concept"}]}]
        (self.project / "diagrams.json").write_text(json.dumps(authored), encoding="utf-8")
        self.build()
        manifest = json.loads((self.out / "diagrams/manifest.json").read_text())
        self.assertEqual([diagram["id"] for diagram in manifest], ["model"])
        self.assertEqual(manifest[0]["title"], "Selected concept")
        self.assertFalse((self.out / "diagrams/model-full.svg").exists())

    def test_schema_selection_rejects_no_tables_and_authored_id_collisions(self):
        with self.assertRaisesRegex(ValueError, "require tables"):
            load_diagrams(self.project, {"schemaDiagrams": ["model"]})
        authored = [{"id": "model", "nodes": [{"id": "concept", "label": "One concept"}]}]
        (self.project / "diagrams.json").write_text(json.dumps(authored), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "conflict with authored"):
            load_diagrams(self.project, self.plan)

    def test_custom_flow_columns_and_blank_legacy_columns_export_only_content(self):
        self.plan = {"document": {"title": "Filter journey"}, "flows": [{
            "id": "filter", "title": "Filter locally", "columns": ["Step", "Interaction", "Visible result"],
            "steps": [["Choose", "Select a filter", "Show matching rows"], ["Clear", "Clear the filter", "Show all rows"]]}]}
        self.save_plan()
        self.build()
        markdown = (self.out / "build-plan.md").read_text()
        self.assertIn("| Step | Interaction | Visible result |", markdown)
        self.assertIn("| Choose | Select a filter | Show matching rows |", markdown)
        self.assertNotIn("Writes", markdown)
        self.plan["flows"][0].pop("columns")
        self.plan["flows"][0]["steps"] = [["Choose", "Filter", "Match rows", "", "Visible rows"]]
        self.save_plan()
        self.build()
        markdown = (self.out / "build-plan.md").read_text()
        self.assertIn("| Step | Input | Reads / decision | Output / next action |", markdown)
        self.assertNotIn("Writes", markdown)

    def test_diagramless_custom_prototype_checks_syntax_without_rendering(self):
        self.plan = {"document": {"title": "Interaction note"}}
        self.save_plan()
        (self.project / "prototype.js").write_text("window.PROTOTYPE = {};\n", encoding="utf-8")
        with mock.patch("build.subprocess.run", wraps=subprocess.run) as commands:
            result = self.build()
        self.assertTrue(result["ok"])
        self.assertFalse(any("render-diagrams.mjs" in " ".join(call.args[0]) for call in commands.call_args_list))
        self.assertTrue(json.loads((self.out / "build-info.json").read_text())["javascriptSyntaxChecked"])
        (self.project / "prototype.js").write_text("window.PROTOTYPE = {broken: ;};\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "prototype.js syntax check"):
            self.build()

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


class DiagramlessBuildToolsTests(unittest.TestCase):
    def test_reuse_columns_and_flow_ownership_export_only_authored_content(self):
        with tempfile.TemporaryDirectory(prefix="product-plan-optional-detail-") as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            cases = [({"name": "Existing directory"}, "| Table / service |", "| Existing directory |"),
                     ({"name": "Existing directory", "change": "Reuse without changes"},
                      "| Table / service | Change |", "| Existing directory | Reuse without changes |")]
            for existing, header, row in cases:
                for owner in (None, "Browser owns presentation state"):
                    with self.subTest(existing=existing, owner=owner):
                        flow = {"id": "filter", "title": "Filter locally", "columns": ["Step", "Result"],
                                "steps": [["Choose filter", "Show matching rows"]]}
                        if owner is not None:
                            flow["owner"] = owner
                        plan = {"document": {"title": "Directory filtering"}, "existing": [existing], "flows": [flow]}
                        (project / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
                        result = build(project, root / "output")
                        self.assertTrue(result["ok"])
                        markdown = (root / "output/build-plan.md").read_text()
                        self.assertIn(header, markdown)
                        self.assertIn(row, markdown)
                        self.assertNotIn("| Why |", markdown)
                        if "change" not in existing:
                            self.assertNotIn("| Change |", markdown)
                        if owner is None:
                            self.assertNotIn("Owner:", markdown)
                        else:
                            self.assertIn("Owner: " + owner, markdown)

    def test_omitting_downloads_preserves_authored_text_resembling_links(self):
        with tempfile.TemporaryDirectory(prefix="product-plan-authored-text-") as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            decision = "A source contains <a href='diagrams.md'>diagram notes</a>; choose content according to the task."
            plan = {"document": {"title": "Source interpretation"}, "summary": {"decision": decision}}
            (project / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
            result = build(project, root / "output")
            self.assertTrue(result["ok"])
            self.assertIn(decision, (root / "output/preview.html").read_text())
            self.assertEqual(result["counts"]["diagrams"], 0)

    def test_decision_memo_omits_technical_exports_and_requires_no_node(self):
        with tempfile.TemporaryDirectory(prefix="product-plan-decision-memo-") as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            plan = {"document": {"title": "Keep the existing process"},
                    "summary": {"decision": "Use the existing review queue.", "nextAction": "Confirm the owner."}}
            (project / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
            for authored_diagrams in (None, []):
                with self.subTest(diagrams=authored_diagrams):
                    if authored_diagrams is not None:
                        (project / "diagrams.json").write_text(json.dumps(authored_diagrams), encoding="utf-8")
                    out = root / "output"
                    with mock.patch("build.resolve_node", side_effect=AssertionError("Node must not be needed")):
                        result = build(project, out)
                    self.assertTrue(result["ok"])
                    self.assertEqual(result["counts"]["tables"], 0)
                    self.assertEqual(result["counts"]["flows"], 0)
                    self.assertEqual(result["counts"]["diagrams"], 0)
                    self.assertEqual(result["counts"]["downloads"], 1)
                    self.assertFalse((out / "diagrams.md").exists())
                    self.assertEqual(json.loads((out / "diagrams/manifest.json").read_text()), [])
                    self.assertFalse(json.loads((out / "build-info.json").read_text())["javascriptSyntaxChecked"])
                    markdown = (out / "build-plan.md").read_text()
                    self.assertIn(plan["summary"]["decision"], markdown)
                    self.assertIn(plan["summary"]["nextAction"], markdown)
                    for heading in ("## Diagrams", "## Data model", "## Existing tables", "## Logic and data flow", "## Source requirements"):
                        self.assertNotIn(heading, markdown)
                    html = out / "preview.html"
                    self.assertTrue(validate(html)["ok"])


if __name__ == "__main__":
    unittest.main()
