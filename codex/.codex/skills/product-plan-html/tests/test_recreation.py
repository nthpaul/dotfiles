from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "assets" / "examples" / "injury-rtw"
CORE_KEYS = ("tables", "existing", "flows", "decisions", "questions", "sources")
SVG_NS = {"svg": "http://www.w3.org/2000/svg"}


def digest(value):
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode()).hexdigest()


def run_build(project, output):
    command = [sys.executable, str(ROOT / "scripts" / "build.py"), str(project), "--out", str(output)]
    if os.environ.get("PRODUCT_PLAN_NODE"):
        command += ["--node", os.environ["PRODUCT_PLAN_NODE"]]
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        raise AssertionError(f"Build failed:\n{result.stdout}\n{result.stderr}")
    return result


class InlineScripts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.scripts = []
        self.active = None
        self.external_assets = []

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == "script":
            self.active = []
            if attributes.get("src"):
                self.external_assets.append(attributes["src"])
        if tag == "link" and attributes.get("rel") == "stylesheet":
            self.external_assets.append(attributes.get("href"))

    def handle_data(self, data):
        if self.active is not None:
            self.active.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.active is not None:
            self.scripts.append("".join(self.active))
            self.active = None


class RecreationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory(prefix="product-plan-recreation-")
        cls.output = Path(cls.workspace.name) / "first"
        cls.plan = json.loads((FIXTURE / "plan.json").read_text())
        cls.manifest = json.loads((FIXTURE / "fixture-manifest.json").read_text())
        run_build(FIXTURE, cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    def test_original_model_and_diagram_sources_are_preserved(self):
        core = {key: self.plan[key] for key in CORE_KEYS}
        self.assertEqual(digest(core), self.manifest["source"]["portableCorePlanSha256"])
        generated = json.loads((self.output / "data-model.json").read_text())
        self.assertEqual({key: generated[key] for key in CORE_KEYS}, core)
        diagrams = json.loads((FIXTURE / "diagrams.json").read_text())
        self.assertEqual(len(diagrams), 8)
        self.assertEqual(
            {diagram["id"]: hashlib.sha256(diagram["dot"].encode()).hexdigest() for diagram in diagrams},
            self.manifest["source"]["canonicalDotSha256"],
        )
        self.assertFalse(any("svg" in diagram for diagram in diagrams))
        self.assertFalse(list(FIXTURE.glob("*.html")))
        self.assertFalse(list(FIXTURE.glob("*.svg")))

    def test_full_schema_svg_preserves_every_table_field_and_foreign_key(self):
        tree = ElementTree.parse(self.output / "diagrams" / "model-full.svg")
        groups = tree.findall(".//svg:g[@class='node']", SVG_NS)
        nodes = {group.find("svg:title", SVG_NS).text: group for group in groups}
        self.assertEqual(len(nodes), self.manifest["expected"]["fullSchemaNodes"])
        edges = {
            group.find("svg:title", SVG_NS).text
            for group in tree.findall(".//svg:g[@class='edge']", SVG_NS)
        }
        field_count = 0
        relation_count = 0
        for table in self.plan["tables"]:
            texts = [text.text or "" for text in nodes[table["name"]].findall(".//svg:text", SVG_NS)]
            for field in table["fields"]:
                field_count += 1
                self.assertTrue(
                    any(text in (field["name"], field["name"] + " ?") for text in texts),
                    (table["name"], field["name"]),
                )
                if field["relation"]:
                    relation_count += 1
                    parent = field["relation"].split(".")[0]
                    self.assertIn(f"{parent}->{table['name']}:{field['name']}", edges)
        self.assertEqual(field_count, 124)
        self.assertEqual(relation_count, 28)
        for diagram in json.loads((FIXTURE / "diagrams.json").read_text()):
            root = ElementTree.parse(self.output / "diagrams" / f"{diagram['id']}.svg").getroot()
            self.assertTrue(root.attrib.get("viewBox"), diagram["id"])

    def test_markdown_includes_previously_manual_sources_and_diagrams(self):
        markdown = (self.output / "build-plan.md").read_text()
        self.assertIn(self.plan["document"]["sourceUrl"], markdown)
        for table in self.plan["tables"]:
            self.assertIn(table["name"], markdown)
            for field in table["fields"]:
                self.assertIn(field["name"], markdown)
        for diagram in json.loads((FIXTURE / "diagrams.json").read_text()):
            self.assertIn(diagram["title"], markdown)
            self.assertIn(diagram["mermaid"].strip(), markdown)

    def test_rebuild_is_deterministic_and_preview_is_portable(self):
        second = Path(self.workspace.name) / "second"
        run_build(FIXTURE, second)
        for first in self.output.rglob("*"):
            if not first.is_file():
                continue
            relative = first.relative_to(self.output)
            other = second / relative
            self.assertTrue(other.exists(), str(relative))
            self.assertEqual(first.read_bytes(), other.read_bytes(), str(relative))
        parser = InlineScripts()
        html = (self.output / "preview.html").read_text()
        parser.feed(html)
        self.assertEqual(parser.external_assets, [])
        self.assertNotIn("/Users/ple/", html)
        self.assertIn("data:font/ttf;base64,", html)

    def test_literal_closing_script_does_not_escape_json_or_prototype(self):
        project = Path(self.workspace.name) / "closing-script"
        shutil.copytree(FIXTURE, project)
        plan = json.loads((project / "plan.json").read_text())
        marker = "</script><script>window.__escapedOutsideArtifact = true</script>"
        plan["document"]["title"] = marker
        plan["questions"].append(marker)
        (project / "plan.json").write_text(json.dumps(plan))
        with (project / "prototype.js").open("a") as handle:
            handle.write("\nconst closingScriptFixture = " + json.dumps(marker) + ";\n")
        output = Path(self.workspace.name) / "closing-script-output"
        run_build(project, output)
        baseline = InlineScripts()
        baseline.feed((self.output / "preview.html").read_text())
        parser = InlineScripts()
        html = (output / "preview.html").read_text()
        parser.feed(html)
        self.assertEqual(len(parser.scripts), len(baseline.scripts))
        self.assertNotIn(marker, html)
        self.assertTrue(any("closingScriptFixture" in script for script in parser.scripts))
        self.assertEqual(json.loads((output / "data-model.json").read_text())["questions"][-1], marker)

    def test_connected_prototype_scenarios_and_handoffs(self):
        spec = importlib.util.spec_from_file_location("product_plan_capabilities", ROOT / "scripts" / "capabilities.py")
        capabilities = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(capabilities)
        node = os.environ.get("PRODUCT_PLAN_NODE") or capabilities.discover(standalone=True)["tools"]["node"]["path"]
        self.assertTrue(node, "Node is required to verify connected prototype interactions")
        script = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const plan = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const expected = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const handlers = {};
const elements = new Map();
const context = {
  console, Date, setTimeout: () => 1, clearTimeout: () => {},
  PLAN: plan, PlanDocument: {render() {}},
  document: {
    querySelector(selector) {
      if (!elements.has(selector)) elements.set(selector, {value:'',style:{},textContent:'',innerHTML:'',close(){},showModal(){}});
      return elements.get(selector);
    },
    addEventListener(type, handler) { (handlers[type] ||= []).push(handler); }
  },
  FormData: class {
    constructor(form) { this.values = form.values; }
    get(key) { return this.values[key] ?? null; }
    getAll(key) { const value = this.values[key]; return value == null ? [] : Array.isArray(value) ? value : [value]; }
  }
};
context.window = context;
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), context);
const prototype = context.PROTOTYPE;
assert.equal(elements.size, 0, 'Loading script must not initialize scenario or touch the DOM');
prototype.init();
for (const item of expected.scenarioAssertions) {
  prototype.selectScenario(item.scenario);
  assert.equal(prototype.status().tone, item.bookingTone, item.scenario);
  assert.equal(prototype.status().label, item.statusLabel, item.scenario);
}
function click(action, extra = {}) {
  const button = {disabled:false,dataset:{action,...extra}};
  const event = {target:{closest:() => button}};
  for (const handler of handlers.click) handler(event);
}
function submit(id, values = {}) {
  const event = {preventDefault(){},target:{id,values,dataset:{}}};
  for (const handler of handlers.submit) handler(event);
}
prototype.selectScenario('reported');
click('sample-file');
submit('note-form', {clearanceType:'FULL',visitDate:'2026-10-08'});
assert.ok(prototype.render('ops').includes('Pending review'));
click('approve');
assert.equal(prototype.status().tone, 'green');
assert.ok(prototype.render('business').includes('No new absence or return notice'));
click('preview-clearance');
click('send-notice',{kind:'clearance'});
assert.ok(prototype.render('business').includes('is cleared to return'));
assert.ok(prototype.render('business').includes('Cancelled'));
assert.ok(prototype.render('business').includes('Worker remains booked'));
for (const scenario of ['multiple','suspended']) {
  prototype.selectScenario(scenario);
  click('approve');
  assert.equal(prototype.status().tone, 'orange');
  assert.match(prototype.render('ops'), /data-action="preview-clearance" disabled/);
}
prototype.selectScenario('illness');
click('sample-illness');
submit('illness-form',{expectedDate:'2026-10-20',workerNote:'',extraShift:['1']});
assert.equal(prototype.status().tone, 'green');
submit('consent-form');
assert.ok(prototype.render('business').includes('View authorized document'));
click('convert');
click('confirm-convert');
assert.equal(prototype.status().tone, 'orange');
assert.ok(!prototype.render('business').includes('View authorized document'));
console.log('Seven scenario contracts and connected approval/notice/consent/conversion handoffs verified.');
"""
        completed = subprocess.run(
            [node, "-e", script, str(FIXTURE / "plan.json"), str(FIXTURE / "prototype.js"), str(FIXTURE / "fixture-manifest.json")],
            capture_output=True, text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
