"""Exercise the real viewer with only the content and preview surfaces a plan needs."""

from pathlib import Path
import json
import subprocess
import sys
import unittest


PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / "scripts"))
from build import resolve_node


HARNESS = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const elements = new Map();
const events = new Map();
const element = selector => {
  if (!elements.has(selector)) elements.set(selector, {
    innerHTML: '', hidden: false, style: {}, dataset: {}, value: '',
    querySelectorAll() { return []; },
    addEventListener(name, handler) { this[name] = handler; }
  });
  return elements.get(selector);
};
const context = {
  PLAN: input.plan, DIAGRAMS: input.diagrams || [], location: {hash: input.hash || ''},
  history: {replaceState(_state, _unused, hash) { context.location.hash = hash; }},
  document: {
    documentElement: {dataset: {}}, querySelector: element,
    addEventListener(name, handler) {
      if (!events.has(name)) events.set(name, []);
      events.get(name).push(handler);
    }
  },
  addEventListener(name, handler) {
    if (!events.has(name)) events.set(name, []);
    events.get(name).push(handler);
  }, scrollTo() {}, setTimeout() {}, clearTimeout() {}
};
context.window = context;
vm.createContext(context);
if (input.prototype) vm.runInContext(input.prototype, context);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), context);
const app = () => element('#app').innerHTML;
const tabIds = () => [...element('.review-tabs').innerHTML.matchAll(/data-view="([^"]+)"/g)].map(x => x[1]);
const coreTabs = ['overview', 'model', 'flow'];
const click = dataset => {
  const button = {dataset, closest(selector) { return selector === 'button' ? this : null; }};
  for (const handler of events.get('click') || []) handler({target: button});
};
const navigate = id => click({view: id});
eval(input.assertions);
"""


class ViewerSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.node = resolve_node()
        except ValueError as exc:
            raise unittest.SkipTest(str(exc))
        cls.plan = {
            "document": {"title": "API reconciliation plan"},
            "tables": [{"name": "sync_events", "purpose": "Record a reconciliation.",
                        "fields": [{"name": "id", "type": "uuid PK", "rule": "Stable ID.", "relation": ""}],
                        "constraints": [], "relationships": ""}],
            "flows": [{"id": "reconcile", "title": "Reconcile", "summary": "Persist one result.",
                       "steps": [["Reconcile", "Input", "Read current record", "Write result", "Emit result"]]}],
            "existing": [], "decisions": [], "questions": [], "sources": [],
        }

    def run_viewer(self, assertions, prototype=None, plan=None, initial_hash="", diagrams=None):
        payload = {"plan": plan if plan is not None else self.plan, "prototype": prototype,
                   "hash": initial_hash, "diagrams": diagrams or [], "assertions": assertions}
        result = subprocess.run(
            [self.node, "-e", HARNESS, str(PACKAGE / "assets/viewer/viewer.js")],
            input=json.dumps(payload), capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_plan_without_prototype_has_only_populated_document_tabs(self):
        self.run_viewer(r"""
assert.deepEqual(tabIds(), coreTabs);
assert.equal(element('#scenario-bar').hidden, true);
assert.equal(element('[data-action="reset"]').hidden, true);
assert.equal(element('#scenario').innerHTML, '');
assert.doesNotMatch(app(), /connected surfaces|preview surfaces|data-view="overview"/);
assert.equal((app().match(/class="metric"/g) || []).length, 2);
for (const id of coreTabs) {
  navigate(id);
  assert.equal(context.location.hash, '#' + id);
  assert.equal(element('#scenario-bar').hidden, true);
}
navigate('worker');
assert.equal(context.location.hash, '#flow');
""")

    def test_short_memo_omits_technical_tabs_metrics_and_empty_cards(self):
        self.run_viewer(r"""
assert.deepEqual(tabIds(), ['overview']);
assert.match(app(), /Keep the existing approval experience/);
assert.match(app(), /Confirm with two users/);
assert.doesNotMatch(app(), /class="metric"|class="card|Data model|Logic &amp; data flow|Diagrams|Reuse|Net new|Architecture choices|Decisions to settle|Build sequence|Evidence|Sources|Architecture proposal/);
assert.doesNotMatch(app(), /<p><\/p>|No flows|data-model\.json|diagrams\.md/);
assert.equal(element('#scenario-bar').hidden, true);
context.location.hash = '#model';
for (const handler of events.get('hashchange') || []) handler();
assert.equal(context.location.hash, '#overview');
assert.match(app(), /Keep the existing approval experience/);
""", plan={"document": {"title": "Approval decision"}, "summary": {
            "decision": "Keep the existing approval experience", "nextAction": "Confirm with two users"}},
            initial_hash="#diagrams")

    def test_overview_only_includes_authored_cards_and_sources(self):
        self.run_viewer(r"""
assert.deepEqual(tabIds(), ['overview']);
assert.match(app(), /Keep current review UI/);
assert.match(app(), /Interview transcript/);
assert.match(app(), /https:\/\/example.com\/interview/);
assert.match(app(), /<h3>Reuse<\/h3>/);
assert.match(app(), /<h3>Sources<\/h3>/);
assert.doesNotMatch(app(), /Net new|Build sequence|Decisions to settle|Evidence|Proposed behavior|Architecture choices/);
assert.equal((app().match(/class="card(?: |")/g) || []).length, 2);
""", plan={"document": {"title": "Approval decision"},
            "summary": {"reuse": ["Keep current review UI"]},
            "sources": [["Interview transcript", "https://example.com/interview"]]})

    def test_existing_reuse_alone_does_not_force_schema(self):
        self.run_viewer(r"""
assert.deepEqual(tabIds(), ['overview']);
assert.match(app(), /Existing tables and services/);
assert.match(app(), /Current search service/);
assert.doesNotMatch(app(), /Data model|data-model\.json|new tables|References|<th>Change<\/th>/);
""", plan={"document": {"title": "Search refinement"},
            "existing": [{"name": "Current search service", "why": "The index is already sufficient."}]})

    def test_client_journey_uses_authored_columns_and_ownership(self):
        self.run_viewer(r"""
assert.deepEqual(tabIds(), ['overview', 'flow']);
navigate('flow');
assert.match(app(), /Browser interaction/);
assert.match(app(), /class="eyebrow">Action/);
assert.match(app(), /class="eyebrow">Visible result/);
assert.match(app(), /--flow-columns:2/);
assert.doesNotMatch(app(), /Backend owns state|class="eyebrow">Write|Database|Data model|No flows|flow-tabs/);
""", plan={"document": {"title": "Search refinement"}, "flows": [{
            "id": "filter", "title": "Filter current results", "owner": "Browser interaction",
            "columns": ["Step", "Action", "Visible result"],
            "steps": [["Choose a filter", "Select availability", "The list narrows"],
                      ["Clear a filter", "Remove the selection", "All results return"]]}]})

    def test_blank_default_write_column_is_omitted(self):
        self.run_viewer(r"""
navigate('flow');
assert.match(app(), /class="eyebrow">Input/);
assert.match(app(), /class="eyebrow">Read \/ decide/);
assert.match(app(), /class="eyebrow">Output \/ next action/);
assert.match(app(), /--flow-columns:3/);
assert.doesNotMatch(app(), /class="eyebrow">Write|Backend owns state/);
""", plan={"document": {"title": "Local filter"}, "flows": [{
            "id": "filter", "title": "Filter", "steps": [
                ["Select", "User selection", "Read loaded results", "", "Filtered results"]]}]})

    def test_flow_notes_can_exist_without_step_tables(self):
        self.run_viewer(r"""
assert.deepEqual(tabIds(), ['overview', 'flow']);
navigate('flow');
assert.match(app(), /Selection → visible results/);
assert.match(app(), /Available results/);
assert.doesNotMatch(app(), /No flows|flow-tabs|Backend owns state|flow-step/);
""", plan={"document": {"title": "Search", "flowContract": "Selection → visible results",
            "flowNotes": [{"title": "Available results", "text": "Use already loaded results."}]}})

    def test_schema_omits_blank_optional_columns_and_unselected_diagrams(self):
        self.run_viewer(r"""
assert.deepEqual(tabIds(), ['overview', 'model']);
navigate('model');
assert.match(app(), /<th>Field<\/th><th>Type<\/th>/);
assert.match(app(), /data-model\.json/);
assert.doesNotMatch(app(), /How it works|References|Relationships|model-notes|Data conventions|Calendar dates|every field|Existing tables and services|diagram-panel/);
""", plan={"document": {"title": "Stored identifier"}, "tables": [{
            "name": "requests", "purpose": "Keep one identifier.",
            "fields": [{"name": "id", "type": "uuid PK"}]}]})

    def test_single_diagram_does_not_force_a_model_or_flow_section(self):
        self.run_viewer(r"""
assert.deepEqual(tabIds(), ['overview', 'diagrams']);
navigate('diagrams');
assert.match(app(), /Access boundary/);
assert.match(app(), /diagrams\.md/);
assert.doesNotMatch(app(), /flow-tabs|all fields|foreign keys|New table \/ logic|Existing table \/ service|Data model/);
""", plan={"document": {"title": "Permissions"}}, diagrams=[{
            "id": "access", "title": "Access boundary", "svg": '<svg viewBox="0 0 100 100"></svg>',
            "mermaid": "flowchart LR\n user --> approved"}])

    def test_empty_surface_list_omits_preview_controls_even_with_scenarios(self):
        self.run_viewer(r"""
assert.deepEqual(tabIds(), coreTabs);
assert.equal(element('#scenario-bar').hidden, true);
assert.doesNotMatch(app(), /connected surfaces|preview surfaces/);
assert.equal((app().match(/class="metric"/g) || []).length, 2);
navigate('model');
assert.equal(element('#scenario-bar').hidden, true);
""", prototype="""
window.PROTOTYPE = {
  surfaces: [], scenarios: [{id: 'draft', label: 'Draft'}],
  render() { throw new Error('No preview may render without a declared surface.'); }
};
""")

    def test_one_custom_surface_needs_no_scenarios_or_traba_app_defaults(self):
        self.run_viewer(r"""
assert.deepEqual(tabIds(), [...coreTabs, 'api-explorer']);
assert.match(element('.review-tabs').innerHTML, /API explorer/);
assert.equal((app().match(/class="metric"/g) || []).length, 3);
navigate('api-explorer');
assert.equal(context.location.hash, '#api-explorer');
assert.equal(app(), '<article>Request inspector</article>');
assert.equal(element('#scenario-bar').hidden, true);
assert.equal(element('[data-action="reset"]').hidden, true);
assert.equal(element('#scenario').innerHTML, '');
click({action: 'reset'});
navigate('overview');
assert.match(app(), /API reconciliation plan/);
assert.doesNotMatch(element('.review-tabs').innerHTML, /Worker app|Ops console|Business console/);
""", prototype="""
window.PROTOTYPE = {
  surfaces: [{id: 'api-explorer', label: 'API explorer'}],
  render(id) {
    if (id !== 'api-explorer') throw new Error('Unexpected preview: ' + id);
    return '<article>Request inspector</article>';
  }
};
""")

    def test_multiple_custom_surfaces_share_state_and_navigate_in_declared_order(self):
        self.run_viewer(r"""
assert.deepEqual(tabIds(), [...coreTabs, 'dispatch-board', 'customer-kiosk']);
navigate('dispatch-board');
assert.equal(app(), '<p>dispatch-board: 0 deliveries</p>');
assert.equal(element('#scenario-bar').hidden, true);
click({action: 'add-delivery'});
assert.equal(app(), '<p>dispatch-board: 1 deliveries</p>');
navigate('customer-kiosk');
assert.equal(app(), '<p>customer-kiosk: 1 deliveries</p>');
navigate('dispatch-board');
assert.equal(app(), '<p>dispatch-board: 1 deliveries</p>');
navigate('not-requested');
assert.equal(context.location.hash, '#dispatch-board');
""", prototype="""
window.demoDeliveries = 0;
window.PROTOTYPE = {
  surfaces: [{id: 'dispatch-board', label: 'Dispatch board'}, {id: 'customer-kiosk', label: 'Customer kiosk'}],
  render(id) { return '<p>' + id + ': ' + window.demoDeliveries + ' deliveries</p>'; }
};
document.addEventListener('click', event => {
  if (event.target.dataset.action === 'add-delivery') {
    window.demoDeliveries++;
    window.PlanDocument.render();
  }
});
""", initial_hash="#dispatch-board")

    def test_custom_surface_ids_do_not_collide_with_object_properties(self):
        self.run_viewer(r"""
assert.deepEqual(tabIds(), [...coreTabs, 'constructor', 'toString', '__proto__']);
for (const id of ['constructor', 'toString', '__proto__']) {
  navigate(id);
  assert.equal(app(), '<p>Custom surface: ' + id + '</p>');
}
""", prototype="""
window.PROTOTYPE = {
  surfaces: [{id: 'constructor', label: 'Constructor'}, {id: 'toString', label: 'Serialization'},
             {id: '__proto__', label: 'Prototype inspector'}],
  render(id) { return '<p>Custom surface: ' + id + '</p>'; }
};
""")

    def test_custom_scenarios_work_without_a_reset_action(self):
        self.run_viewer(r"""
navigate('review-tool');
assert.equal(app(), '<p>Pending review</p>');
assert.equal(element('#scenario-bar').hidden, false);
assert.equal(element('[data-action="reset"]').hidden, true);
assert.match(element('#scenario').innerHTML, /value="approved"/);
element('#scenario').change({target: {value: 'approved'}});
assert.equal(app(), '<p>Approved</p>');
assert.match(element('#scenario-status').innerHTML, /Approved/);
navigate('model');
assert.equal(element('#scenario-bar').hidden, true);
navigate('review-tool');
assert.equal(app(), '<p>Approved</p>');
""", prototype="""
let selected = 'Pending review';
window.PROTOTYPE = {
  surfaces: [{id: 'review-tool', label: 'Review tool'}],
  scenarios: [{id: 'pending', label: 'Pending review'}, {id: 'approved', label: 'Approved'}],
  initialScenario: 'pending',
  selectScenario(id) {
    selected = id === 'approved' ? 'Approved' : 'Pending review';
    window.PlanDocument.render();
  },
  status() { return {label: selected, tone: 'green'}; },
  render() { return '<p>' + selected + '</p>'; }
};
""")

    def test_explicit_original_fixture_keeps_three_requested_apps_and_scenarios(self):
        fixture = PACKAGE / "assets/examples/injury-rtw"
        self.run_viewer(r"""
assert.deepEqual(tabIds(), [...coreTabs, 'diagrams', 'worker', 'ops', 'business']);
for (const [id, marker] of [['worker', 'Recovery, one step at a time'], ['ops', 'Injury & recovery'], ['business', 'Warehouse A']]) {
  navigate(id);
  assert.match(app(), new RegExp(marker));
  assert.equal(element('#scenario-bar').hidden, false);
  assert.equal(element('[data-action="reset"]').hidden, false);
}
element('#scenario').change({target: {value: 'cleared'}});
assert.match(element('#scenario-status').innerHTML, /Booking available/);
navigate('worker');
assert.match(app(), /You’re cleared to return/);
navigate('flow');
assert.equal(element('#scenario-bar').hidden, true);
""", prototype=(fixture / "prototype.js").read_text(),
            plan=json.loads((fixture / "plan.json").read_text()),
            diagrams=[dict(d, svg='<svg viewBox="0 0 100 100"></svg>')
                      for d in json.loads((fixture / "diagrams.json").read_text())])


if __name__ == "__main__":
    unittest.main()
