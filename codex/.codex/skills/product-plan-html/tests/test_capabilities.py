import importlib.util
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "capabilities.py"
SPEC = importlib.util.spec_from_file_location("capabilities", MODULE_PATH)
capabilities = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capabilities)


def write_skill(root, name, frontmatter_name=None):
    path = root / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nname: {frontmatter_name or name}\ndescription: Test guidance.\n---\n\n# Test\nVerified body.\n")
    return path


class CapabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.codex = self.home / ".codex"
        self.home_patch = patch.object(Path, "home", return_value=self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)
        self.cwd_patch = patch.object(Path, "cwd", return_value=self.home / "workspace")
        self.cwd_patch.start()
        self.addCleanup(self.cwd_patch.stop)
        self.env_patch = patch.dict(os.environ, {"CODEX_HOME": str(self.codex)}, clear=False)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def selected(self, result, name):
        return next(item for item in result["skills"] if item["name"].split(":")[-1] == name)

    def test_all_detected_through_custom_root_and_symlinks(self):
        actual = self.home / "catalog" / "pstack-plugin" / "skills"
        for _, name, scope, _ in capabilities.TARGETS:
            if scope:
                write_skill(actual, name)
        custom = self.home / "shared"
        custom.mkdir()
        (custom / "pstack").symlink_to(actual, target_is_directory=True)
        for name in ["traba-design", "relay-design"]:
            write_skill(custom, name)
        result = capabilities.discover([custom], tool_names=["mcp__cua_repl__js"])
        self.assertFalse(result["fallbacks"])
        self.assertEqual(len(result["read"]), 4)
        self.assertEqual(set(result["read"]), {
            item["path"] for item in result["skills"]
            if item["name"] in capabilities.CORE_READ_NAMES
        })
        idempotence = self.selected(result, "principle-make-operations-idempotent")
        self.assertFalse(idempotence["fallback"])
        self.assertNotIn(idempotence["path"], result["read"])
        self.assertTrue(result["tools"]["browser"]["available"])
        for item in result["skills"]:
            self.assertTrue(Path(item["path"]).is_file())
            self.assertEqual(item["source"], "configured-root")

    def test_missing_optional_principles_do_not_add_default_fallback_reads(self):
        root = self.home / "core-only"
        for _, name, scope, _ in capabilities.TARGETS:
            if name in capabilities.CORE_READ_NAMES:
                write_skill(root / "pstack" if scope else root, name)
        result = capabilities.discover([root])
        self.assertEqual(len(result["read"]), 4)
        self.assertEqual({item["name"] for item in result["fallbacks"]}, {
            "principle-build-the-lever", "principle-model-the-domain",
            "principle-make-operations-idempotent",
        })
        self.assertTrue(all(not item["fallback"] for item in result["skills"]
                            if item["path"] in result["read"]))
        for fallback in result["fallbacks"]:
            self.assertNotIn(fallback["path"], result["read"])
            self.assertTrue(Path(fallback["path"]).is_file())
            self.assertIn("No verified installed pstack", fallback["reason"])

    def test_all_missing_use_three_verified_fallbacks(self):
        result = capabilities.discover()
        self.assertEqual(len(result["fallbacks"]), 7)
        self.assertEqual(len(result["read"]), 3)
        self.assertTrue(all(Path(path).is_file() for path in result["read"]))
        self.assertFalse(result["tools"]["browser"]["available"])

    def test_partial_detection_keeps_available_guidance(self):
        root = self.home / "partial"
        path = write_skill(root, "traba-design")
        result = capabilities.discover([root])
        design = self.selected(result, "traba-design")
        self.assertEqual(design["path"], str(path.resolve()))
        self.assertFalse(design["fallback"])
        self.assertEqual(len(result["fallbacks"]), 6)

    def test_broken_symlink_and_unrelated_architect_are_not_pstack(self):
        root = self.home / "custom"
        root.mkdir()
        (root / "broken").symlink_to(self.home / "absent", target_is_directory=True)
        write_skill(root, "architect")
        result = capabilities.discover([root])
        self.assertTrue(self.selected(result, "architect")["fallback"])

    def test_default_installed_detection_prefers_active_over_new_plugin(self):
        old = self.codex / "plugins" / "cache" / "publisher" / "pstack-plugin" / "0.2.0" / "skills"
        new = self.codex / "plugins" / "cache" / "publisher" / "pstack-plugin" / "9.0.0" / "skills"
        old_path = write_skill(old, "architect")
        write_skill(new, "architect")
        active = self.codex / "skills"
        active.mkdir(parents=True)
        (active / "architect").symlink_to(old_path.parent, target_is_directory=True)
        write_skill(active, "traba-design")
        result = capabilities.discover()
        architecture = self.selected(result, "architect")
        self.assertEqual(architecture["path"], str(old_path.resolve()))
        self.assertEqual(architecture["source"], "active-skills")
        self.assertFalse(self.selected(result, "traba-design")["fallback"])

    def test_plugin_cache_picks_latest_version_deterministically(self):
        base = self.codex / "plugins" / "cache" / "publisher" / "pstack-plugin"
        write_skill(base / "0.9.0" / "skills", "architect")
        expected = write_skill(base / "0.10.0" / "skills", "architect")
        result = capabilities.discover()
        self.assertEqual(self.selected(result, "architect")["path"], str(expected.resolve()))

    def test_project_roots_are_discovered_nearest_first(self):
        repo = self.home / "workspace"
        nested = repo / "apps" / "worker"
        root_design = write_skill(repo / ".claude" / "skills", "traba-design")
        nearest_design = write_skill(nested / ".codex" / "skills", "traba-design")
        root_relay = write_skill(repo / ".claude" / "skills", "relay-design")
        with patch.object(Path, "cwd", return_value=nested / "src"):
            result = capabilities.discover()
        self.assertEqual(self.selected(result, "traba-design")["path"], str(nearest_design.resolve()))
        self.assertNotEqual(self.selected(result, "traba-design")["path"], str(root_design.resolve()))
        self.assertEqual(self.selected(result, "relay-design")["path"], str(root_relay.resolve()))
        self.assertEqual(self.selected(result, "traba-design")["source"], "project-skills")

    def test_plugin_vendor_skill_files_are_ignored(self):
        plugin = self.codex / "plugins" / "cache" / "publisher" / "pstack-plugin" / "1.0.0"
        expected = write_skill(plugin / "skills", "architect")
        write_skill(plugin / "node_modules" / "rogue-package", "relay-design")
        result = capabilities.discover()
        self.assertEqual(self.selected(result, "architect")["path"], str(expected.resolve()))
        self.assertTrue(self.selected(result, "relay-design")["fallback"])

    def test_cursor_plugin_commit_layout_uses_manifest_version(self):
        base = self.home / ".cursor" / "plugins" / "cache" / "cursor-public" / "pstack"
        for commit, version in [("zz-older", "0.9.0"), ("aa-newer", "0.10.0")]:
            plugin = base / commit
            write_skill(plugin / "skills", "architect")
            manifest = plugin / ".cursor-plugin" / "plugin.json"
            manifest.parent.mkdir()
            manifest.write_text(json.dumps({"name": "pstack", "version": version}))
        with patch.object(capabilities.sys, "argv", [str(self.home / ".cursor" / "skills" / "product-plan-html" / "scripts" / "plan.py")]):
            result = capabilities.discover()
        architecture = self.selected(result, "architect")
        self.assertEqual(result["platform"]["name"], "cursor")
        self.assertEqual(architecture["path"], str((base / "aa-newer" / "skills" / "architect" / "SKILL.md").resolve()))
        self.assertEqual(architecture["source"], "plugin-cache")

    def test_grok_uses_verified_native_pstack_plugin_not_unrelated_local_copy(self):
        write_skill(self.home / ".grok" / "skills", "architect")
        expected = write_skill(self.home / ".grok" / "installed-plugins" / "plugins-git-pstack-test" / "pstack" / "skills", "architect")
        write_skill(self.codex / "plugins" / "cache" / "publisher" / "pstack-plugin" / "9.0.0" / "skills", "architect")
        with patch.object(capabilities.sys, "argv", [str(self.home / ".grok" / "skills" / "product-plan-html" / "scripts" / "plan.py")]):
            result = capabilities.discover()
        self.assertEqual(result["platform"]["name"], "grok")
        self.assertEqual(self.selected(result, "architect")["path"], str(expected.resolve()))
        self.assertFalse(self.selected(result, "architect")["fallback"])

    def test_host_user_guidance_and_nearest_cursor_project_take_precedence(self):
        repo = self.home / "workspace"
        expected = write_skill(self.home / ".claude" / "skills", "relay-design")
        write_skill(self.codex / "skills", "relay-design")
        project = write_skill(repo / ".cursor" / "skills", "traba-design")
        with patch.object(capabilities.sys, "argv", [str(self.home / ".claude" / "skills" / "product-plan-html" / "scripts" / "plan.py")]):
            result = capabilities.discover()
        self.assertEqual(self.selected(result, "relay-design")["path"], str(expected.resolve()))
        self.assertEqual(self.selected(result, "traba-design")["path"], str(project.resolve()))

    def test_claude_plugin_cache_supported_but_uninstalled_marketplace_ignored(self):
        installed = self.home / ".claude" / "plugins" / "cache" / "team" / "pstack" / "1.0.0" / "skills"
        expected = write_skill(installed, "architect")
        write_skill(self.home / ".claude" / "plugins" / "marketplaces" / "team" / "plugins" / "pstack" / "skills", "relay-design")
        result = capabilities.discover()
        self.assertEqual(self.selected(result, "architect")["path"], str(expected.resolve()))
        self.assertTrue(self.selected(result, "relay-design")["fallback"])

    def test_non_cua_browser_actions_require_actual_session_catalog(self):
        result = capabilities.discover(standalone=True, tool_names=[
            "mcp__playwright__browser_navigate", "mcp__playwright__browser_snapshot",
            "mcp__codex_app__open_in_codex", "web__search_query", "browser-install",
        ])
        self.assertEqual(result["tools"]["browser"]["tools"], [
            "mcp__playwright__browser_navigate", "mcp__playwright__browser_snapshot",
        ])
        self.assertTrue(result["tools"]["browser"]["available"])
        self.assertFalse(capabilities.discover(standalone=True)["tools"]["browser"]["available"])

    def test_standalone_suppresses_only_external_guidance_discovery(self):
        root = self.home / "available"
        write_skill(root, "traba-design")
        result = capabilities.discover([root], standalone=True, tool_names=["mcp__codex_app__open_in_codex"])
        self.assertEqual(len(result["fallbacks"]), 7)
        self.assertEqual(result["roots_searched"], [])
        self.assertTrue(result["tools"]["python"]["available"])
        self.assertFalse(result["tools"]["browser"]["available"])

    def test_runtime_and_viz_discovery_without_path_install(self):
        runtime = self.home / ".cache" / "codex-runtimes" / "test-runtime"
        node = runtime / "dependencies" / "node" / "bin" / "node"
        node.parent.mkdir(parents=True)
        node.write_text("test executable")
        node.chmod(0o755)
        package = runtime / "dependencies" / "node" / "node_modules" / "@viz-js" / "viz"
        (package / "dist").mkdir(parents=True)
        (package / "package.json").write_text(json.dumps({"name": "@viz-js/viz", "version": "3.0.0"}))
        (package / "dist" / "viz.js").write_text("export {}")
        with patch.object(capabilities.shutil, "which", return_value=None):
            result = capabilities.discover(standalone=True)
        self.assertEqual(result["tools"]["node"]["path"], str(node.resolve()))
        with patch.object(capabilities, "PACKAGE_ROOT", self.home / "no-vendor"):
            viz = capabilities._viz(result["tools"]["node"])
        self.assertTrue(viz["available"])
        self.assertEqual(viz["version"], "3.0.0")

    def test_verified_bundled_viz_is_usable_without_installed_node_package(self):
        package = self.home / "standalone-package"
        vendor = package / "assets" / "vendor"
        vendor.mkdir(parents=True)
        entry = vendor / "viz.js"
        entry.write_text("export const instance = async () => ({});")
        (vendor / "vendor.json").write_text(json.dumps({
            "name": "@viz-js/viz", "version": "3.25.0",
            "sha256": hashlib.sha256(entry.read_bytes()).hexdigest(),
        }))
        with patch.object(capabilities, "PACKAGE_ROOT", package):
            viz = capabilities._viz({"path": None})
        self.assertTrue(viz["available"])
        self.assertEqual(viz["source"], "bundled-asset")
        self.assertEqual(viz["path"], str(entry.resolve()))
        entry.write_text("corrupted bundle")
        with patch.object(capabilities, "PACKAGE_ROOT", package):
            corrupted = capabilities._viz({"path": None})
        self.assertFalse(corrupted["available"])


if __name__ == "__main__":
    unittest.main()
