"""Exercise the real viewer with optional and explicitly selected preview surfaces."""

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
  PLAN: input.plan, DIAGRAMS: [], location: {hash: input.hash || ''},
  history: {replaceState(_state, _unused, hash) { context.location.hash = hash; }},
  document: {
    documentElement: {dataset: {}}, querySelector: element,
    addEventListener(name, handler) {
      if (!events.has(name)) events.set(name, []);
      events.get(name).push(handler);
    }
  },
  addEventListener() {}, scrollTo() {}, setTimeout() {}, clearTimeout() {}
};
context.window = context;
vm.createContext(context);
if (input.prototype) vm.runInContext(input.prototype, context);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), context);
const app = () => element('#app').innerHTML;
const tabIds = () => [...element('.review-tabs').innerHTML.matchAll(/data-view="([^"]+)"/g)].map(x => x[1]);
const coreTabs = ['overview', 'model', 'flow', 'diagrams'];
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

    def run_viewer(self, assertions, prototype=None, plan=None, initial_hash=""):
        payload = {"plan": plan or self.plan, "prototype": prototype, "hash": initial_hash,
                   "assertions": assertions}
        result = subprocess.run(
            [self.node, "-e", HARNESS, str(PACKAGE / "assets/viewer/viewer.js")],
            input=json.dumps(payload), capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_plan_without_prototype_has_only_document_tabs(self):
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
assert.equal(context.location.hash, '#diagrams');
""")

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
assert.deepEqual(tabIds(), [...coreTabs, 'worker', 'ops', 'business']);
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
            plan=json.loads((fixture / "plan.json").read_text()))


if __name__ == "__main__":
    unittest.main()
