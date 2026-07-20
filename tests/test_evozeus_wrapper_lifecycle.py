import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.evozeus_wrapper_bootstrap import (
    build_evolution_section,
    build_status_section,
    build_wrapper_section,
    copy_templates,
    inject_evolution_method,
)
from scripts.evozeus_wrapper_lifecycle import (
    CODEX_START_HOOK_SCRIPT,
    LEGACY_TARGET_WRAPPER_MANIFEST,
    TARGET_CHANGELOG,
    TARGET_FEEDBACK_POLICY,
    TARGET_MIGRATIONS_README,
    TARGET_ONBOARDING_GUIDE,
    TARGET_PREFLIGHT_SCRIPT,
    TARGET_WRAPPER_MANIFEST,
    apply_reinstall,
    build_onboarding_contract,
    build_wrapper_manifest,
    classify_pr_permission,
    classify_wrapper_upgrade,
    classify_integration_mode,
    detect_target_architecture,
    diagnose_environment,
    diagnose_skill,
    diagnose_source_contract,
    load_wrapper_manifest,
    migrate_target_layout,
    plan_feedback_audit,
    plan_harness_upgrade,
    plan_target_layout_migration,
    path_kind,
    plan_reinstall,
    plan_transform_action,
    repo_from_remote,
    skill_name_from_skill_md,
    stage_label,
    write_wrapper_manifest,
    wrapper_manifest_status,
)
from scripts.evozeus_wrapper_global_hook import (
    GLOBAL_DISPATCHER_COMMAND,
    apply_global_hook_install,
    apply_global_hook_uninstall,
    plan_global_hook_install,
    read_global_hook_status,
    record_global_hook_trust,
)
from scripts.evozeus_wrapper_preflight import (
    check_onboarding_contract,
    check_integration_contract,
    load_wrapper_manifest as load_preflight_manifest,
    referenced_runtime_files,
    root_entry_path as preflight_root_entry_path,
)


def create_complete_legacy_target(target: Path) -> str:
    replacements = {
        "CURRENT_VERSION": "v1.2.3",
        "REPO_NAME": "MetaInFLow/legacy-skill",
        "VISIBILITY": "private",
        "WRAPPER_VERSION": "v0.6.0",
    }
    status = build_status_section(replacements).replace(
        "harness upgrade-check --target <this-skill-repo> --json",
        "harness upgrade-check --target <this-skill-repo> --latest-version <wrapper-version> --json",
    )
    wrapper = build_wrapper_section(replacements).replace(
        "harness upgrade-check --target <this-skill-repo> --json",
        "harness upgrade-check --target <this-skill-repo> --latest-version <wrapper-version> --json",
    )
    business = (
        "## Business Logic\n\n"
        "PRESERVE-BUSINESS-BYTES https://example.test/tree/main/docs\n\n"
    )
    skill_text = (
        '---\nname: "legacy-skill"\n---\n\n'
        + status.rstrip()
        + "\n\n"
        + business
        + build_evolution_section(replacements).rstrip()
        + "\n\n"
        + wrapper.rstrip()
        + "\n"
    )
    (target / "SKILL.md").write_text(skill_text, encoding="utf-8")

    legacy = target / ".evozeus_evoinfra"
    legacy.mkdir(parents=True)
    legacy_manifest = {
        "wrapper_repo": "MetaInFLow/EvoZeus-wrapper",
        "wrapper_version": "v0.6.0",
        "canonical_repo": "MetaInFLow/legacy-skill",
        "managed_files": [],
        "install_links": [],
        "integration": {"mode": "prompt_runtime_check", "native_host_hook_installed": False},
    }
    (legacy / "wrapper.json").write_text(
        json.dumps(legacy_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (legacy / "feedback-policy.json").write_text(
        '{"management_mode":"manual","audit_rule":".evozeus_evoinfra/audit-rule.md"}\n',
        encoding="utf-8",
    )
    (legacy / "audit-rule.md").write_text("# Feedback Audit Rule\n\nPreserve evidence.\n", encoding="utf-8")

    fixture_files = {
        "CHANGELOG.md": "# Changelog\n\n## [v1.2.3] - 2026-07-01\n\n- Existing release.\n",
        "WRAPPER.md": "# Legacy Wrapper\n\nRead `.evozeus_evoinfra/wrapper.json`.\n",
        "docs/index.md": "# Legacy Dashboard\n\nRead `../CHANGELOG.md`.\n",
        "docs/_config.yml": 'title: "Legacy Skill"\n',
        "docs/design-doc-template.md": "# Design Doc\n\n## Related issue\n\n## Verification plan\n",
        "docs/designs/README.md": "# Designs\n\nStore design docs here.\n",
        "docs/wrapper-migrations/README.md": "# Wrapper Migrations\n\nRecord migrations here.\n",
        "scripts/evozeus_wrapper_preflight.py": Path("scripts/evozeus_wrapper_preflight.py").read_text(
            encoding="utf-8"
        ),
        ".github/ISSUE_TEMPLATE/config.yml": (
            "blank_issues_enabled: false\ncontact_links:\n"
            "  - name: Read the Skill dashboard\n"
            "    url: \"https://github.com/MetaInFLow/legacy-skill/tree/main/docs\"\n"
            "    about: Check status first.\n"
        ),
        ".github/ISSUE_TEMPLATE/skill-feedback.yml": Path(
            "templates/target/.github/ISSUE_TEMPLATE/skill-feedback.yml"
        ).read_text(encoding="utf-8"),
        ".github/pull_request_template.md": Path(
            "templates/target/.github/pull_request_template.md"
        ).read_text(encoding="utf-8"),
        ".github/workflows/evozeus-wrapper-preflight.yml": Path(
            "templates/target/.github/workflows/evozeus-wrapper-preflight.yml"
        ).read_text(encoding="utf-8"),
    }
    for rel, content in fixture_files.items():
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (target / "scripts/evozeus_wrapper_preflight.py").chmod(0o755)
    return business


class LifecycleBasicsTest(unittest.TestCase):
    def test_repo_from_remote_supports_https_and_ssh(self):
        self.assertEqual(repo_from_remote("https://github.com/MetaInFLow/EvoZeus.git"), "MetaInFLow/EvoZeus")
        self.assertEqual(repo_from_remote("git@github.com:MetaInFLow/EvoZeus-wrapper.git"), "MetaInFLow/EvoZeus-wrapper")
        self.assertIsNone(repo_from_remote("https://example.com/MetaInFLow/EvoZeus.git"))

    def test_stage_label_uses_five_stage_contract(self):
        self.assertEqual(stage_label("environment"), "[1/5] Environment Diagnosis")
        self.assertEqual(stage_label("target_skill"), "[2/5] Target Skill Diagnosis")
        self.assertEqual(stage_label("transform"), "[3/5] Target Skill Transform")
        self.assertEqual(stage_label("publish"), "[4/5] Publish & Reinstall")
        self.assertEqual(stage_label("loop"), "[5/5] Continuous Evolution Loop")

    def test_path_kind_distinguishes_missing_directory_file_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = root / "missing"
            directory = root / "dir"
            directory.mkdir()
            file_path = root / "file.txt"
            file_path.write_text("x", encoding="utf-8")
            link = root / "link"
            link.symlink_to(directory)

            self.assertEqual(path_kind(missing), "missing")
            self.assertEqual(path_kind(directory), "directory")
            self.assertEqual(path_kind(file_path), "file")
            self.assertEqual(path_kind(link), "symlink")

    def test_skill_name_from_skill_md_reads_frontmatter_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "SKILL.md"
            skill.write_text('---\nname: "resume-screening"\n---\n# Body\n', encoding="utf-8")
            self.assertEqual(skill_name_from_skill_md(skill), "resume-screening")

            no_name = Path(tmp) / "NO_NAME.md"
            no_name.write_text("# Body\n", encoding="utf-8")
            self.assertIsNone(skill_name_from_skill_md(no_name))

    def test_status_assessment_is_documented_as_a_skill(self):
        skill = Path("skills/status-assessment/SKILL.md")
        text = skill.read_text(encoding="utf-8")
        self.assertIn("name: evozeus-wrapper-status-assessment", text)
        self.assertIn("The CLI scripts provide facts. This Skill provides judgment", text)
        self.assertIn("Do not move user-facing assessment logic into Python scripts.", text)

    def test_evolution_surface_diagnosis_is_documented_as_a_skill(self):
        skill = Path("skills/evolution-surface-diagnosis/SKILL.md")
        text = skill.read_text(encoding="utf-8")
        self.assertIn("name: evozeus-wrapper-evolution-surface-diagnosis", text)
        self.assertIn("The CLI scripts collect facts. This Skill makes the judgment.", text)
        self.assertIn("Do not treat `evolution_surface.candidates` as final placement.", text)

    def test_root_skill_is_thin_and_routes_to_using_skill(self):
        root = Path("SKILL.md")
        text = root.read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 60)
        self.assertIn("skills/using-evozeus-wrapper/SKILL.md", text)
        self.assertIn("This root Skill is only the wrapper entrypoint", text)

    def test_using_evozeus_wrapper_is_operating_skill(self):
        skill = Path("skills/using-evozeus-wrapper/SKILL.md")
        text = skill.read_text(encoding="utf-8")
        self.assertIn("name: using-evozeus-wrapper", text)
        self.assertIn("Use this Skill as the operating guide for EvoZeus-wrapper.", text)
        self.assertIn("Do not treat script-produced `evolution_surface.candidates` as final placement.", text)
        self.assertNotIn("TODO", text)

    def test_codex_hook_template_uses_official_project_hooks_location(self):
        hooks_path = Path("templates/target/.codex/hooks.json")
        hooks = json.loads(hooks_path.read_text(encoding="utf-8"))

        session_start = hooks["hooks"]["SessionStart"][0]
        handler = session_start["hooks"][0]

        self.assertEqual(session_start["matcher"], "startup|resume")
        self.assertEqual(handler["type"], "command")
        self.assertIn(
            "$(git rev-parse --show-toplevel)/.evozeus-wrapper/hooks/evozeus_wrapper_start_check.py",
            handler["command"],
        )
        self.assertEqual(handler["statusMessage"], "Checking EvoZeus wrapper harness")
        self.assertFalse(Path("templates/target/hooks/hooks-codex.json").exists())

    def test_pages_workflow_keeps_validation_active_when_deployment_is_disabled(self):
        workflow = Path("templates/target/.github/workflows/evozeus-wrapper-preflight.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("  validation:\n", workflow)
        self.assertIn("preflight.py maintainer", workflow)
        self.assertIn("Report Pages deployment mode", workflow)
        self.assertIn("needs: validation", workflow)
        self.assertIn("vars.EVOZEUS_PAGES_ENABLED == 'true'", workflow)
        self.assertIn('\".evozeus-wrapper/**\"', workflow)

    def test_copy_templates_consolidates_wrapper_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            replacements = {
                "DATE": "2026-07-18",
                "INITIAL_VERSION": "v0.1.0",
                "CURRENT_VERSION": "v0.1.0",
                "REPO_NAME": "MetaInFLow/skill",
                "REPO_URL": "https://github.com/MetaInFLow/skill",
                "SKILL_NAME": "skill",
                "VISIBILITY": "private",
                "WRAPPER_VERSION": "v0.8.0",
            }

            copy_templates(target, replacements, force=False)

            self.assertTrue((target / ".evozeus-wrapper/CHANGELOG.md").is_file())
            self.assertTrue((target / ".evozeus-wrapper/WRAPPER.md").is_file())
            self.assertTrue((target / TARGET_PREFLIGHT_SCRIPT).is_file())
            self.assertTrue((target / CODEX_START_HOOK_SCRIPT).is_file())
            self.assertTrue((target / ".evozeus-wrapper/docs/index.md").is_file())
            self.assertTrue((target / TARGET_ONBOARDING_GUIDE).is_file())
            self.assertTrue((target / ".codex/hooks.json").is_file())
            self.assertTrue((target / ".github/ISSUE_TEMPLATE/skill-feedback.yml").is_file())
            self.assertFalse((target / "CHANGELOG.md").exists())
            self.assertFalse((target / "WRAPPER.md").exists())
            self.assertFalse((target / "docs").exists())
            self.assertFalse((target / "scripts").exists())

    def test_consolidated_bootstrap_output_passes_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            (target / "SKILL.md").write_text(
                '---\nname: "skill"\n---\n# Skill\n\nRun the business flow.\n',
                encoding="utf-8",
            )
            replacements = {
                "DATE": "2026-07-18",
                "INITIAL_VERSION": "v0.1.0",
                "CURRENT_VERSION": "v0.1.0",
                "REPO_NAME": "MetaInFLow/skill",
                "REPO_URL": "https://github.com/MetaInFLow/skill",
                "SKILL_NAME": "skill",
                "VISIBILITY": "private",
                "WRAPPER_VERSION": "v0.8.0",
            }
            copy_templates(target, replacements, force=False)
            inject_evolution_method(target, replacements)
            write_wrapper_manifest(
                target,
                build_wrapper_manifest(
                    "MetaInFLow/skill",
                    "v0.8.0",
                    [
                        TARGET_CHANGELOG,
                        ".evozeus-wrapper/WRAPPER.md",
                        ".codex/hooks.json",
                        CODEX_START_HOOK_SCRIPT,
                    ],
                    [],
                ),
            )

            result = subprocess.run(
                [sys.executable, str(target / TARGET_PREFLIGHT_SCRIPT), "structure", "--target", str(target)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            skill_text = (target / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("## EvoZeus-wrapper 状态检查", skill_text)
            self.assertIn("## 自进化方法", skill_text)
            self.assertIn(TARGET_WRAPPER_MANIFEST, skill_text)

    def test_preflight_rejects_legacy_layout_until_migrated(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            legacy = target / LEGACY_TARGET_WRAPPER_MANIFEST
            legacy.parent.mkdir(parents=True)
            legacy.write_text('{"canonical_repo":"MetaInFLow/skill"}\n', encoding="utf-8")

            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                load_preflight_manifest(target)

    def test_bootstrap_status_language_is_runtime_safe(self):
        checked_files = [
            Path("scripts/evozeus_wrapper_bootstrap.py"),
            Path("templates/target/WRAPPER.md"),
            Path("templates/target/docs/index.md"),
        ]
        blocked_phrases = [
            "Continue to the target Skill's main flow only after all three are OK.",
            "全部 OK 后",
            "只有检查结果为 OK",
            "才继续进入目标 Skill 原本主链路",
            "才继续进入下方原 Skill 流程",
        ]

        for path in checked_files:
            text = path.read_text(encoding="utf-8")
            self.assertIn("runtime-only install", text)
            for phrase in blocked_phrases:
                self.assertNotIn(phrase, text)

    def test_generated_upgrade_guidance_uses_authoritative_latest_lookup(self):
        replacements = {
            "CURRENT_VERSION": "v0.1.0",
            "REPO_NAME": "MetaInFLow/skill",
            "VISIBILITY": "private",
            "WRAPPER_VERSION": "v0.8.0",
        }

        text = build_status_section(replacements) + build_wrapper_section(replacements)

        self.assertIn("harness upgrade-check --target <this-skill-repo> --json", text)
        self.assertNotIn("--latest-version <wrapper-version>", text)
        self.assertIn("Skill 入口 preflight", text)
        self.assertIn("repo_maintenance_hook", text)
        self.assertIn("global_session_dispatcher", text)
        self.assertIn("SkillInvoke", text)

    def test_preflight_root_entry_path_uses_manifest_instruction_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "hooked-skill-system"
            target.mkdir()
            (target / ".codex-plugin").mkdir()
            (target / ".codex-plugin" / "plugin.json").write_text(
                '{"skills":"./skills/","hooks":"./hooks/hooks-codex.json"}',
                encoding="utf-8",
            )
            (target / "hooks").mkdir()
            (target / "hooks" / "hooks-codex.json").write_text(
                '{"hooks":{"session-start":"skills/session-bootstrap/SKILL.md"}}',
                encoding="utf-8",
            )
            skill_dir = target / "skills" / "session-bootstrap"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                '---\nname: "session-bootstrap"\n---\n# Session Bootstrap\nUse at session start to load skills.\n',
                encoding="utf-8",
            )
            write_wrapper_manifest(
                target,
                build_wrapper_manifest(
                    "MetaInFLow/hooked-skill-system",
                    "v0.1.0",
                    [],
                    [],
                    instruction_surface="skills/session-bootstrap/SKILL.md",
                ),
            )

            entry = preflight_root_entry_path(target)

            self.assertEqual(str(entry.relative_to(target)), "skills/session-bootstrap/SKILL.md")

    def test_runtime_reference_parser_excludes_command_arguments(self):
        text = "Run `scripts/research_search.py --plan path/to/plan.json --out output.jsonl`."

        self.assertEqual(referenced_runtime_files(text), ["scripts/research_search.py"])

    def test_write_wrapper_manifest_uses_target_evoinfra_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()

            write_wrapper_manifest(
                target,
                build_wrapper_manifest("MetaInFLow/skill", "v0.6.0", [], []),
            )

            self.assertTrue((target / TARGET_WRAPPER_MANIFEST).is_file())
            self.assertFalse((target / LEGACY_TARGET_WRAPPER_MANIFEST).exists())

    def test_load_wrapper_manifest_detects_legacy_manifest_for_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            legacy_path = target / LEGACY_TARGET_WRAPPER_MANIFEST
            legacy_path.parent.mkdir()
            legacy_path.write_text(
                '{"canonical_repo":"MetaInFLow/skill","wrapper_version":"v0.5.0"}\n',
                encoding="utf-8",
            )

            manifest = load_wrapper_manifest(target, allow_legacy=True)
            status = wrapper_manifest_status(target)

            self.assertEqual(manifest["canonical_repo"], "MetaInFLow/skill")
            self.assertTrue(status["legacy_manifest_detected"])
            self.assertTrue(status["migration_required"])
            self.assertEqual(status["manifest_source"], "legacy_evoinfra")
            with self.assertRaises(ValueError):
                load_wrapper_manifest(target)

    def test_load_wrapper_manifest_rejects_conflicting_current_and_legacy_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            current_path = target / TARGET_WRAPPER_MANIFEST
            legacy_path = target / LEGACY_TARGET_WRAPPER_MANIFEST
            current_path.parent.mkdir()
            legacy_path.parent.mkdir()
            current_path.write_text(
                '{"canonical_repo":"MetaInFLow/skill","wrapper_version":"v0.6.0"}\n',
                encoding="utf-8",
            )
            legacy_path.write_text(
                '{"canonical_repo":"MetaInFLow/skill","wrapper_version":"v0.5.0"}\n',
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_wrapper_manifest(target)

    def test_migrate_target_layout_moves_legacy_files_and_rewrites_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            create_complete_legacy_target(target)
            old_legacy_dir = target / ".evozeus_evoinfra"
            legacy_dir = target / ".evozeus"
            old_legacy_dir.rename(legacy_dir)
            legacy_manifest = json.loads((legacy_dir / "wrapper.json").read_text(encoding="utf-8"))
            legacy_manifest["wrapper_version"] = "v0.5.0"
            (legacy_dir / "wrapper.json").write_text(
                json.dumps(legacy_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            (legacy_dir / "feedback-policy.json").write_text(
                '{"audit_rule":".evozeus/audit-rule.md"}\n',
                encoding="utf-8",
            )
            skill_path = target / "SKILL.md"
            skill_path.write_text(
                skill_path.read_text(encoding="utf-8").replace(".evozeus-wrapper", ".evozeus"),
                encoding="utf-8",
            )

            report = migrate_target_layout(target, latest_version="v0.9.1", today=date(2026, 7, 18))
            manifest = load_wrapper_manifest(target)
            skill_text = (target / "SKILL.md").read_text(encoding="utf-8")
            policy = (target / TARGET_FEEDBACK_POLICY).read_text(encoding="utf-8")

            self.assertIn(
                "move .evozeus/wrapper.json -> .evozeus-wrapper/wrapper.json",
                report["actions"],
            )
            self.assertFalse((target / ".evozeus").exists())
            self.assertTrue((target / TARGET_WRAPPER_MANIFEST).is_file())
            self.assertEqual(manifest["wrapper_version"], "v0.9.1")
            self.assertEqual(manifest["layout_version"], 2)
            self.assertIn(TARGET_PREFLIGHT_SCRIPT, manifest["managed_files"])
            self.assertIn(TARGET_ONBOARDING_GUIDE, manifest["managed_files"])
            self.assertTrue((target / TARGET_ONBOARDING_GUIDE).is_file())
            self.assertEqual(manifest["onboarding"]["installation"]["mode"], "canonical_repo_symlink")
            self.assertFalse(manifest["onboarding"]["generated_child_skills"]["hooks_inherited"])
            self.assertIn(TARGET_WRAPPER_MANIFEST, skill_text)
            self.assertIn(".evozeus-wrapper/policies/audit-rule.md", policy)
            self.assertTrue(
                (target / ".evozeus-wrapper/docs/migrations/2026-07-18-layout-v1-to-v2.md").is_file()
            )
            self.assertIn(
                'TARGET_EVOINFRA_DIR = ".evozeus-wrapper"',
                (target / TARGET_PREFLIGHT_SCRIPT).read_text(encoding="utf-8"),
            )
            self.assertIn(
                "source: ./.evozeus-wrapper/docs",
                (target / ".github/workflows/evozeus-wrapper-preflight.yml").read_text(encoding="utf-8"),
            )
            self.assertFalse(wrapper_manifest_status(target)["migration_required"])

    def test_migrate_layout_produces_complete_scoped_hook_harness(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "legacy-skill"
            target.mkdir()
            business = create_complete_legacy_target(target)
            before = (target / "SKILL.md").read_text(encoding="utf-8")
            before_business = before.split("## Business Logic", 1)[1].split("## 自进化方法", 1)[0]

            report = migrate_target_layout(
                target,
                latest_version="v0.9.1",
                today=date(2026, 7, 18),
            )
            manifest = load_wrapper_manifest(target)
            skill_text = (target / "SKILL.md").read_text(encoding="utf-8")
            after_business = skill_text.split("## Business Logic", 1)[1].split("## 自进化方法", 1)[0]
            hooks = json.loads((target / ".codex/hooks.json").read_text(encoding="utf-8"))

            self.assertTrue(report["writes"])
            self.assertEqual(before_business, after_business)
            self.assertIn(business.strip(), skill_text)
            self.assertIn("v0.9.1", skill_text.split("## Business Logic", 1)[0])
            self.assertNotIn("--latest-version <wrapper-version>", skill_text)
            self.assertIn("v0.6.0 -> v0.9.1", skill_text)
            self.assertEqual(manifest["integration"]["mode"], "prompt_runtime_check")
            self.assertFalse(manifest["integration"]["native_skill_invocation_hook_installed"])
            self.assertTrue(
                manifest["integration"]["capabilities"]["repo_maintenance_hook"]["installed"]
            )
            self.assertEqual(manifest["hook_registration"]["codex"]["event"], "SessionStart")
            self.assertIn("SessionStart", hooks["hooks"])
            self.assertIn(
                "/tree/main/.evozeus-wrapper/docs",
                (target / ".github/ISSUE_TEMPLATE/config.yml").read_text(encoding="utf-8"),
            )

            for command in ("structure", "maintainer", "runtime"):
                result = subprocess.run(
                    [sys.executable, str(target / TARGET_PREFLIGHT_SCRIPT), command, "--target", str(target)],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

            hook_env = {**os.environ, "EVOZEUS_WRAPPER_LATEST_VERSION": "v0.9.1"}
            hook_result = subprocess.run(
                [sys.executable, str(target / CODEX_START_HOOK_SCRIPT)],
                input=json.dumps({"hook_event_name": "SessionStart", "source": "startup"}),
                text=True,
                capture_output=True,
                cwd=target,
                env=hook_env,
                check=False,
            )
            hook_payload = json.loads(hook_result.stdout)
            self.assertEqual(hook_result.returncode, 0)
            self.assertTrue(hook_payload["continue"])
            self.assertIn("current", hook_payload["systemMessage"])

    def test_migrate_layout_blocks_invalid_codex_hooks_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "legacy-skill"
            target.mkdir()
            create_complete_legacy_target(target)
            hooks_path = target / ".codex/hooks.json"
            hooks_path.parent.mkdir(parents=True)
            hooks_path.write_text("{not-json\n", encoding="utf-8")

            plan = plan_target_layout_migration(target, latest_version="v0.9.1")

            self.assertFalse(plan["can_apply"])
            self.assertTrue(any("hooks.json" in conflict for conflict in plan["conflicts"]))
            with self.assertRaises(ValueError):
                migrate_target_layout(target, latest_version="v0.9.1")
            self.assertTrue((target / LEGACY_TARGET_WRAPPER_MANIFEST).is_file())
            self.assertFalse((target / TARGET_WRAPPER_MANIFEST).exists())

    def test_migrate_layout_preserves_custom_session_start_hook_when_merging(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "legacy-skill"
            target.mkdir()
            create_complete_legacy_target(target)
            hooks_path = target / ".codex/hooks.json"
            hooks_path.parent.mkdir(parents=True)
            hooks_path.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "SessionStart": [
                                {
                                    "matcher": "startup",
                                    "hooks": [{"type": "command", "command": "python3 custom.py"}],
                                }
                            ]
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            migrate_target_layout(target, latest_version="v0.9.1", today=date(2026, 7, 18))
            hooks = json.loads(hooks_path.read_text(encoding="utf-8"))["hooks"]["SessionStart"]
            commands = [hook["command"] for entry in hooks for hook in entry.get("hooks", [])]

            self.assertIn("python3 custom.py", commands)
            self.assertTrue(any("evozeus_wrapper_start_check.py" in command for command in commands))

    def test_migrate_layout_repairs_incomplete_existing_v2_harness(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "legacy-skill"
            target.mkdir()
            create_complete_legacy_target(target)
            migrate_target_layout(target, latest_version="v0.9.0", today=date(2026, 7, 17))

            (target / ".codex/hooks.json").unlink()
            manifest_path = target / TARGET_WRAPPER_MANIFEST
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["wrapper_version"] = "v0.9.0"
            manifest["integration"] = {
                "mode": "prompt_runtime_check",
                "native_host_hook_installed": False,
            }
            manifest.pop("dashboard", None)
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            plan = plan_target_layout_migration(target, latest_version="v0.9.1", today=date(2026, 7, 18))
            report = migrate_target_layout(target, latest_version="v0.9.1", today=date(2026, 7, 18))
            repaired = load_wrapper_manifest(target)

            self.assertTrue(plan["migration_required"])
            self.assertEqual(plan["from_layout"], "consolidated-v2")
            self.assertTrue(report["writes"])
            self.assertTrue((target / ".codex/hooks.json").is_file())
            self.assertEqual(repaired["wrapper_version"], "v0.9.1")
            self.assertEqual(repaired["integration"]["mode"], "prompt_runtime_check")
            self.assertTrue(
                repaired["integration"]["capabilities"]["repo_maintenance_hook"]["installed"]
            )
            self.assertEqual(repaired["dashboard"]["deployment_mode"], "opt_in_github_pages")
            self.assertTrue(
                (target / ".evozeus-wrapper/docs/migrations/2026-07-18-v0.9.0-to-v0.9.1.md").is_file()
            )

    def test_layout_migration_conflict_stops_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            legacy_manifest = target / LEGACY_TARGET_WRAPPER_MANIFEST
            legacy_manifest.parent.mkdir(parents=True)
            legacy_manifest.write_text(
                '{"canonical_repo":"MetaInFLow/skill","wrapper_version":"v0.7.0"}\n',
                encoding="utf-8",
            )
            (target / "WRAPPER.md").write_text("legacy wrapper\n", encoding="utf-8")
            destination = target / ".evozeus-wrapper/WRAPPER.md"
            destination.parent.mkdir(parents=True)
            destination.write_text("different new wrapper\n", encoding="utf-8")

            plan = plan_target_layout_migration(target, latest_version="v0.8.0")

            self.assertFalse(plan["can_apply"])
            self.assertTrue(plan["conflicts"])
            with self.assertRaises(ValueError):
                migrate_target_layout(target, latest_version="v0.8.0")
            self.assertTrue((target / "WRAPPER.md").is_file())
            self.assertEqual(destination.read_text(encoding="utf-8"), "different new wrapper\n")
            self.assertFalse((target / TARGET_WRAPPER_MANIFEST).exists())

    def test_layout_migration_is_idempotent_for_layout_v2(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            write_wrapper_manifest(
                target,
                build_wrapper_manifest("MetaInFLow/skill", "v0.8.0", [], []),
            )
            (target / "CHANGELOG.md").write_text(
                "# Business changelog not owned by wrapper\n",
                encoding="utf-8",
            )

            plan = plan_target_layout_migration(target, latest_version="v0.8.0")
            result = migrate_target_layout(target, latest_version="v0.8.0")

            self.assertFalse(plan["migration_required"])
            self.assertEqual(plan["moves"], [])
            self.assertFalse(result["writes"])
            self.assertTrue((target / "CHANGELOG.md").is_file())

    def test_plan_feedback_audit_captures_wrapper_defect(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            write_wrapper_manifest(
                target,
                build_wrapper_manifest("MetaInFLow/skill", "v0.6.0", [], []),
            )
            policy_path = target / TARGET_FEEDBACK_POLICY
            policy_path.parent.mkdir(parents=True, exist_ok=True)
            policy_path.write_text(
                '{"management_mode":"semi_managed","audit_rule":".evozeus-wrapper/policies/audit-rule.md"}\n',
                encoding="utf-8",
            )

            report = plan_feedback_audit(
                target=target,
                user_input="这个 wrapper 没有自动 issue 回收，有问题",
            )

            self.assertTrue(report["should_capture"])
            self.assertEqual(report["route"], "wrapper")
            self.assertEqual(report["issue_repo"], "MetaInFLow/EvoZeus-wrapper")
            self.assertEqual(report["policy_path"], TARGET_FEEDBACK_POLICY)
            self.assertIn("gh issue create --repo MetaInFLow/EvoZeus-wrapper", report["issue_create_command"])

    def test_preflight_rejects_native_hook_mode_without_hook_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "wrapped-skill"
            target.mkdir()
            manifest = {"integration": {"mode": "native_host_hook"}}

            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                check_integration_contract(target, manifest)

    def test_preflight_rejects_plugin_lifecycle_hook_as_native_skill_invocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "wrapped-skill"
            target.mkdir()
            (target / ".claude-plugin").mkdir()
            (target / ".claude-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
            (target / "hooks").mkdir()
            (target / "hooks" / "hooks.json").write_text("{}", encoding="utf-8")
            manifest = {"integration": {"mode": "native_host_hook"}}

            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                check_integration_contract(target, manifest)

    def test_preflight_rejects_native_codex_project_hook_without_invocation_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "wrapped-skill"
            target.mkdir()
            (target / ".codex").mkdir(parents=True)
            (target / ".codex" / "hooks.json").write_text('{"hooks":{}}', encoding="utf-8")
            hook_script = target / CODEX_START_HOOK_SCRIPT
            hook_script.parent.mkdir(parents=True)
            hook_script.write_text(
                "#!/usr/bin/env python3\n",
                encoding="utf-8",
            )
            manifest = {"integration": {"mode": "native_host_hook"}}

            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                check_integration_contract(target, manifest)

    def test_project_hook_is_repo_maintenance_not_skill_invocation(self):
        integration = classify_integration_mode(
            target_kind="single_skill",
            root_entry="SKILL.md",
            hook_files=[".codex/hooks.json", CODEX_START_HOOK_SCRIPT],
            plugin_manifests=[],
            skill_entries=[],
        )

        self.assertEqual(integration["mode"], "prompt_runtime_check")
        self.assertFalse(integration["native_skill_invocation_hook_installed"])
        self.assertTrue(integration["capabilities"]["repo_maintenance_hook"]["installed"])
        self.assertFalse(
            integration["capabilities"]["repo_maintenance_hook"]["covers_skill_invocation"]
        )

    def test_preflight_rejects_native_invocation_claim_backed_only_by_project_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "wrapped-skill"
            target.mkdir()
            (target / ".codex").mkdir()
            (target / ".codex" / "hooks.json").write_text('{"hooks":{}}', encoding="utf-8")
            hook_script = target / CODEX_START_HOOK_SCRIPT
            hook_script.parent.mkdir(parents=True)
            hook_script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
            manifest = {
                "integration": {
                    "mode": "native_host_hook",
                    "native_host_hook_installed": True,
                }
            }

            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                check_integration_contract(target, manifest)

    def test_preflight_rejects_project_registration_that_claims_invocation_coverage(self):
        manifest = build_wrapper_manifest(
            "MetaInFLow/skill",
            "v0.10.0",
            [".codex/hooks.json", CODEX_START_HOOK_SCRIPT],
            [],
        )
        manifest["hook_registration"]["codex"]["covers_skill_invocation"] = True

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                check_integration_contract(target, manifest)


class EnvironmentDiagnosisTest(unittest.TestCase):
    def test_diagnose_environment_reports_home_and_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            evozeus_home = home / ".evozeus"
            evozeus_home.mkdir()
            (evozeus_home / "runtime").mkdir()
            (evozeus_home / ".projects").mkdir()

            def runner(args, cwd=None):
                return {"returncode": 0, "stdout": "", "stderr": ""}

            report = diagnose_environment(home=home, runner=runner)
            self.assertEqual(report["stage"], "environment_diagnosis")
            self.assertEqual(report["next_action"], "continue_to_target_repo_diagnosis")
            self.assertEqual(report["evozeus_home"]["exists"], True)
            self.assertEqual(report["evozeus_home"]["required_action"], "none")
            self.assertEqual(report["evozeus_home"]["runtime_exists"], True)
            self.assertEqual(report["evozeus_home"]["projects_exists"], True)
            self.assertEqual(report["mother_repo"]["remote"], "MetaInFLow/EvoZeus")
            self.assertEqual(report["dependencies"]["git"], "ok")
            self.assertEqual(report["dependencies"]["gh"], "ok")
            self.assertEqual(report["dependencies"]["gh_auth"], "ok")

    def test_diagnose_environment_reports_missing_home_and_failed_auth(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)

            def runner(args, cwd=None):
                if args[:3] == ["gh", "auth", "status"]:
                    return {"returncode": 1, "stdout": "", "stderr": "not logged in"}
                return {"returncode": 0, "stdout": "", "stderr": ""}

            report = diagnose_environment(home=home, runner=runner)
            self.assertEqual(report["next_action"], "install_evozeus")
            self.assertEqual(report["evozeus_home"]["exists"], False)
            self.assertEqual(report["evozeus_home"]["required_action"], "install_evozeus")
            self.assertEqual(report["dependencies"]["git"], "ok")
            self.assertEqual(report["dependencies"]["gh"], "ok")
            self.assertEqual(report["dependencies"]["gh_auth"], "failed")


class TargetSkillDiagnosisTest(unittest.TestCase):
    def test_diagnose_skill_reports_target_repo_install_and_missing_harness(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            target = Path(tmp) / "resume-screening"
            target.mkdir()
            skill_text = '---\nname: "resume-screening"\n---\n# Resume Screening\n'
            (target / "SKILL.md").write_text(skill_text, encoding="utf-8")

            codex_install = home / ".codex" / "skills" / "resume-screening"
            codex_install.mkdir(parents=True)
            (codex_install / "SKILL.md").write_text(skill_text, encoding="utf-8")

            projects_pointer = home / ".evozeus" / ".projects" / "MetaInFLow" / "resume-screening"
            projects_pointer.mkdir(parents=True)

            def runner(args, cwd=None):
                return {"returncode": 0, "stdout": "", "stderr": ""}

            report = diagnose_skill(
                target=target,
                repo="MetaInFLow/resume-screening",
                skill_name=None,
                home=home,
                runner=runner,
            )

            self.assertEqual(report["stage"], "target_skill_diagnosis")
            self.assertEqual(report["skill"]["name"], "resume-screening")
            self.assertEqual(report["skill"]["target_kind"], "single_skill")
            self.assertEqual(report["skill"]["root_entry"], "SKILL.md")
            self.assertEqual(report["skill"]["has_skill_md"], True)
            self.assertEqual(report["repo"]["name"], "MetaInFLow/resume-screening")
            self.assertEqual(report["repo"]["exists_on_github"], True)
            self.assertEqual(report["repo"]["projects_pointer"], str(projects_pointer.resolve()))
            self.assertEqual(report["harness"]["state"], "missing")
            self.assertEqual(len(report["installs"]), 1)
            self.assertEqual(report["installs"][0]["path"], str(codex_install.resolve()))
            self.assertEqual(report["installs"][0]["kind"], "directory")
            self.assertEqual(report["installs"][0]["matches_target_skill_md"], True)

    def test_diagnose_skill_marks_scattered_harness_as_migration_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            target = Path(tmp) / "skill"
            target.mkdir()
            (target / "SKILL.md").write_text('---\nname: "skill"\n---\n', encoding="utf-8")
            (target / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")

            report = diagnose_skill(target=target, repo=None, skill_name=None, home=home)
            self.assertEqual(report["harness"]["state"], "migration_required")
            self.assertIn("CHANGELOG.md", report["harness"]["legacy_files"])

    def test_diagnose_skill_preserves_existing_repo_latest_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            target = Path(tmp) / "skill"
            target.mkdir()
            (target / "SKILL.md").write_text('---\nname: "skill"\n---\n', encoding="utf-8")

            def runner(args, cwd=None):
                if args[:3] == ["gh", "repo", "view"]:
                    return {"returncode": 0, "stdout": "", "stderr": ""}
                if args[:3] == ["gh", "release", "view"]:
                    return {
                        "returncode": 0,
                        "stdout": '{"tagName":"v0.9.6","url":"https://github.com/o/r/releases/tag/v0.9.6","publishedAt":"2026-06-26T17:57:14Z"}',
                        "stderr": "",
                    }
                return {"returncode": 1, "stdout": "", "stderr": ""}

            report = diagnose_skill(target=target, repo="o/r", skill_name=None, home=home, runner=runner)

            self.assertEqual(report["repo"]["latest_release"]["tag"], "v0.9.6")
            self.assertEqual(report["version"]["status"], "adopt_existing_release")
            self.assertEqual(report["version"]["current_tag"], "v0.9.6")
            self.assertFalse(report["version"]["requires_owner_choice"])

    def test_diagnose_skill_uses_changelog_when_existing_repo_has_no_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            target = Path(tmp) / "skill"
            target.mkdir()
            (target / "SKILL.md").write_text('---\nname: "skill"\n---\n', encoding="utf-8")
            (target / "CHANGELOG.md").write_text("# Changelog\n\n## [v0.3.0] - 2026-06-27\n", encoding="utf-8")

            def runner(args, cwd=None):
                if args[:3] == ["gh", "repo", "view"]:
                    return {"returncode": 0, "stdout": "", "stderr": ""}
                if args[:3] == ["gh", "release", "view"]:
                    return {"returncode": 1, "stdout": "", "stderr": "release not found"}
                return {"returncode": 1, "stdout": "", "stderr": ""}

            report = diagnose_skill(target=target, repo="o/r", skill_name=None, home=home, runner=runner)

            self.assertEqual(report["version"]["status"], "github_release_missing_create_from_changelog")
            self.assertEqual(report["version"]["current_tag"], "v0.3.0")
            self.assertFalse(report["version"]["requires_owner_choice"])

    def test_detect_target_architecture_recognizes_agents_root_runtime_skill_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sales-office-runtime-kit"
            target.mkdir()
            (target / "AGENTS.md").write_text("# Runtime Instructions\n", encoding="utf-8")
            for dirname in ["runtime", "agents", "automation", "skills"]:
                (target / dirname).mkdir()
            for skill_name in ["sales-coach", "sales-crm-sync"]:
                skill_dir = target / "skills" / skill_name
                skill_dir.mkdir()
                (skill_dir / "SKILL.md").write_text(
                    f'---\nname: "{skill_name}"\n---\n# {skill_name}\n',
                    encoding="utf-8",
                )

            architecture = detect_target_architecture(target)

            self.assertEqual(architecture["target_kind"], "runtime_skill_bundle")
            self.assertEqual(architecture["root_entry"], "AGENTS.md")
            self.assertEqual(architecture["skill_inventory"]["count"], 2)
            self.assertEqual(architecture["architecture_style"], "managed_runtime_skill_bundle")
            self.assertEqual(architecture["evolution_surface"]["status"], "needs_skill_diagnosis")
            self.assertIsNone(architecture["evolution_surface"]["instruction_placement"])
            self.assertIn(
                "AGENTS.md",
                [candidate["path"] for candidate in architecture["evolution_surface"]["candidates"]],
            )

    def test_detect_target_architecture_recognizes_hook_loaded_control_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "hooked-skill-system"
            target.mkdir()
            (target / ".codex-plugin").mkdir()
            (target / ".codex-plugin" / "plugin.json").write_text(
                '{"skills":"./skills/","hooks":"./hooks/hooks-codex.json"}',
                encoding="utf-8",
            )
            (target / "hooks").mkdir()
            (target / "hooks" / "hooks-codex.json").write_text(
                '{"hooks":{"session-start":"skills/session-bootstrap/SKILL.md"}}',
                encoding="utf-8",
            )
            (target / "hooks" / "session-start-codex").write_text(
                "#!/usr/bin/env bash\n# Load skills/session-bootstrap/SKILL.md at session start.\n",
                encoding="utf-8",
            )
            skill_dir = target / "skills" / "session-bootstrap"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                '---\nname: "session-bootstrap"\n---\n# Session Bootstrap\nUse at session start to load skills and route skill usage.\n',
                encoding="utf-8",
            )

            architecture = detect_target_architecture(target)

            self.assertEqual(architecture["target_kind"], "hooked_skill_bundle")
            self.assertEqual(architecture["architecture_style"], "plugin_hook_controlled_skill_system")
            self.assertEqual(architecture["evolution_surface"]["status"], "needs_skill_diagnosis")
            self.assertIsNone(architecture["evolution_surface"]["instruction_placement"])
            self.assertIn(
                "skills/session-bootstrap/SKILL.md",
                [candidate["path"] for candidate in architecture["evolution_surface"]["candidates"]],
            )
            self.assertIn("hooks/hooks-codex.json", architecture["evolution_surface"]["controller_files"])
            self.assertIn(".codex-plugin/plugin.json", architecture["plugin_manifests"])
            self.assertIn(
                "evolution surface diagnosis result",
                architecture["component_gaps"]["missing_concepts"],
            )
            self.assertEqual(architecture["integration"]["mode"], "bootstrap_skill")
            self.assertFalse(architecture["integration"]["native_skill_invocation_hook_installed"])
            self.assertTrue(
                architecture["integration"]["capabilities"]["plugin_lifecycle_hook"]["installed"]
            )

    def test_detect_target_architecture_marks_single_skill_as_prompt_runtime_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "single-skill"
            target.mkdir()
            (target / "SKILL.md").write_text('---\nname: "single-skill"\n---\n', encoding="utf-8")

            architecture = detect_target_architecture(target)

            self.assertEqual(architecture["target_kind"], "single_skill")
            self.assertEqual(architecture["integration"]["mode"], "prompt_runtime_check")
            self.assertFalse(architecture["integration"]["native_host_hook_installed"])

    def test_codex_plugin_with_empty_hooks_is_not_native_host_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "codex-plugin"
            target.mkdir()
            (target / ".codex-plugin").mkdir()
            (target / ".codex-plugin" / "plugin.json").write_text(
                '{"skills":"./skills/","hooks":{}}',
                encoding="utf-8",
            )
            skill_dir = target / "skills" / "using-example"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                '---\nname: "using-example"\n---\n# Bootstrap\nUse when starting a session.\n',
                encoding="utf-8",
            )

            architecture = detect_target_architecture(target)

            self.assertEqual(architecture["target_kind"], "skill_bundle")
            self.assertEqual(architecture["integration"]["mode"], "bootstrap_skill")
            self.assertFalse(architecture["integration"]["native_host_hook_installed"])

    def test_diagnose_skill_accepts_agents_root_runtime_skill_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            target = Path(tmp) / "sales-office-runtime-kit"
            target.mkdir()
            (target / "AGENTS.md").write_text("# Sales Office Runtime Instructions\n", encoding="utf-8")
            for dirname in ["runtime", "agents", "automation", "skills"]:
                (target / dirname).mkdir()
            skill_dir = target / "skills" / "sales-coach"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text('---\nname: "sales-coach"\n---\n', encoding="utf-8")
            apply_global_hook_install(home=home, wrapper_root=Path.cwd(), approve=True)

            def runner(args, cwd=None):
                if args[:3] == ["gh", "repo", "view"]:
                    return {
                        "returncode": 0,
                        "stdout": (
                            '{"nameWithOwner":"MetaInFLow/sales-office-runtime-kit",'
                            '"url":"https://github.com/MetaInFLow/sales-office-runtime-kit",'
                            '"visibility":"PRIVATE","viewerPermission":"WRITE",'
                            '"defaultBranchRef":{"name":"main"}}'
                        ),
                        "stderr": "",
                    }
                if args[:3] == ["gh", "release", "view"]:
                    return {"returncode": 1, "stdout": "", "stderr": "release not found"}
                return {"returncode": 1, "stdout": "", "stderr": ""}

            report = diagnose_skill(
                target=target,
                repo="MetaInFLow/sales-office-runtime-kit",
                skill_name=None,
                home=home,
                runner=runner,
            )

            self.assertEqual(report["skill"]["target_kind"], "runtime_skill_bundle")
            self.assertEqual(report["skill"]["root_entry"], "AGENTS.md")
            self.assertFalse(report["skill"]["has_skill_md"])
            self.assertIsNone(report["skill"]["evolution_surface"]["instruction_placement"])
            self.assertEqual(report["skill"]["skill_inventory"]["count"], 1)
            self.assertEqual(report["repo"]["access"]["viewer_permission"], "WRITE")
            self.assertTrue(report["repo"]["access"]["can_write"])
            self.assertEqual(report["publication"]["visibility"], "PRIVATE")
            self.assertEqual(report["version"]["status"], "missing_version_requires_owner_choice")
            global_capability = report["skill"]["integration"]["capabilities"][
                "global_session_dispatcher"
            ]
            self.assertTrue(global_capability["installed"])
            self.assertEqual(global_capability["trust_status"], "pending_review")
            self.assertFalse(global_capability["native_enforced"])

    def test_classify_integration_mode_names_manual_command_as_non_runtime_integration(self):
        integration = classify_integration_mode(
            target_kind="single_skill",
            root_entry="SKILL.md",
            hook_files=[],
            plugin_manifests=[],
            skill_entries=[],
        )

        self.assertEqual(integration["mode"], "prompt_runtime_check")
        self.assertEqual(integration["manual_wrapper_command"], "not_runtime_integration")
        self.assertIn("prompt", integration["description"])


class WrapperManifestTest(unittest.TestCase):
    def test_write_and_load_wrapper_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            manifest = build_wrapper_manifest(
                repo="MetaInFLow/resume-screening",
                wrapper_version="v0.2.0",
                managed_files=["WRAPPER.md", "scripts/evozeus_wrapper_preflight.py"],
                install_links=["/Users/anthonyf/.codex/skills/resume-screening"],
            )

            action = write_wrapper_manifest(target, manifest)
            loaded = load_wrapper_manifest(target)

            self.assertIn("write", action)
            self.assertEqual(loaded["wrapper_repo"], "MetaInFLow/EvoZeus-wrapper")
            self.assertEqual(loaded["wrapper_version"], "v0.2.0")
            self.assertEqual(loaded["canonical_repo"], "MetaInFLow/resume-screening")
            self.assertEqual(loaded["managed_files"], ["WRAPPER.md", "scripts/evozeus_wrapper_preflight.py"])
            self.assertEqual(loaded["install_links"], ["/Users/anthonyf/.codex/skills/resume-screening"])
            self.assertEqual(loaded["integration"]["mode"], "prompt_runtime_check")
            self.assertFalse(loaded["integration"]["native_host_hook_installed"])
            self.assertEqual(loaded["hook_registration"]["codex"]["config_file"], ".codex/hooks.json")
            self.assertEqual(
                loaded["hook_registration"]["codex"]["hook_script"],
                CODEX_START_HOOK_SCRIPT,
            )
            self.assertEqual(loaded["layout_version"], 2)
            self.assertEqual(loaded["dashboard"]["deployment_mode"], "opt_in_github_pages")
            self.assertEqual(loaded["dashboard"]["enablement_variable"], "EVOZEUS_PAGES_ENABLED")
            self.assertEqual(loaded["onboarding"]["installation"]["mode"], "canonical_repo_symlink")
            self.assertFalse(loaded["onboarding"]["initialization"]["required"])
            self.assertFalse(loaded["onboarding"]["generated_child_skills"]["hooks_inherited"])

    def test_onboarding_contract_records_target_initialization_and_child_skill_lifecycle(self):
        onboarding = build_onboarding_contract(
            repo="MetaInFLow/factory-skill",
            skill_name="factory-skill",
            init_command="python3 scripts/init_company.py --company <name>",
            init_verification="python3 scripts/verify_company.py --company <name>",
            generates_child_skills=True,
        )
        manifest = build_wrapper_manifest(
            "MetaInFLow/factory-skill",
            "v0.9.0",
            [TARGET_ONBOARDING_GUIDE],
            [],
            onboarding=onboarding,
        )

        self.assertTrue(manifest["onboarding"]["initialization"]["required"])
        self.assertEqual(manifest["onboarding"]["initialization"]["owner"], "target_skill")
        self.assertIn("init_company.py", manifest["onboarding"]["initialization"]["command"])
        invocation = manifest["onboarding"]["invocation"]
        self.assertEqual(invocation["mode"], "host_skill_discovery")
        self.assertEqual(invocation["owner"], "target_skill")
        self.assertIn("factory-skill", invocation["instruction"])
        self.assertIn("consumer-project smoke test", invocation["verification"])
        children = manifest["onboarding"]["generated_child_skills"]
        self.assertTrue(children["supported"])
        self.assertFalse(children["hooks_inherited"])
        self.assertEqual(children["attachment"], "separate_wrapper_lifecycle")
        self.assertEqual(children["trust_review"], "/hooks")
        self.assertIn("consumer-project smoke test", children["verification"])

    def test_onboarding_contract_rejects_incomplete_required_initialization(self):
        with self.assertRaisesRegex(ValueError, "command and verification"):
            build_onboarding_contract(
                repo="MetaInFLow/factory-skill",
                skill_name="factory-skill",
                init_command="python3 scripts/init_company.py",
            )

    def test_preflight_rejects_invalid_onboarding_contract(self):
        manifest = build_wrapper_manifest("MetaInFLow/skill", "v0.9.0", [], [])
        manifest["onboarding"]["initialization"] = {
            "required": True,
            "owner": "target_skill",
            "command": None,
            "verification": None,
        }
        manifest["onboarding"]["generated_child_skills"]["hooks_inherited"] = True

        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            check_onboarding_contract(manifest)

    def test_build_wrapper_manifest_records_codex_hook_registration_for_complete_harness(self):
        manifest = build_wrapper_manifest(
            "MetaInFLow/skill",
            "v0.7.0",
            [".evozeus-wrapper/WRAPPER.md", ".codex/hooks.json", CODEX_START_HOOK_SCRIPT],
            [],
        )

        self.assertEqual(manifest["integration"]["mode"], "prompt_runtime_check")
        self.assertFalse(manifest["integration"]["native_skill_invocation_hook_installed"])
        self.assertTrue(manifest["integration"]["codex_project_hook"])
        self.assertTrue(
            manifest["integration"]["capabilities"]["repo_maintenance_hook"]["installed"]
        )
        self.assertEqual(manifest["hook_registration"]["codex"]["event"], "SessionStart")
        self.assertEqual(manifest["hook_registration"]["codex"]["matcher"], "startup|resume")
        self.assertEqual(
            manifest["hook_registration"]["codex"]["capability"],
            "repo_maintenance_hook",
        )
        self.assertEqual(
            manifest["hook_registration"]["codex"]["scope"],
            "canonical_repository",
        )
        self.assertFalse(
            manifest["hook_registration"]["codex"]["covers_skill_invocation"]
        )
        self.assertEqual(
            manifest["hook_registration"]["codex"]["trust_status"],
            "pending_review",
        )

    def test_write_wrapper_manifest_skips_existing_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            first = build_wrapper_manifest("MetaInFLow/a", "v0.1.0", ["WRAPPER.md"], [])
            second = build_wrapper_manifest("MetaInFLow/b", "v0.2.0", ["WRAPPER.md"], [])

            write_wrapper_manifest(target, first)
            action = write_wrapper_manifest(target, second)
            loaded = load_wrapper_manifest(target)

            self.assertIn("skip existing", action)
            self.assertEqual(loaded["canonical_repo"], "MetaInFLow/a")


class SourceContractTest(unittest.TestCase):
    def test_source_contract_passes_for_manifest_pointer_and_runtime_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            target = Path(tmp) / "canonical"
            target.mkdir()
            (target / "SKILL.md").write_text('---\nname: "skill"\n---\n', encoding="utf-8")
            write_wrapper_manifest(
                target,
                build_wrapper_manifest("MetaInFLow/skill", "v0.1.0", ["WRAPPER.md"], []),
            )

            pointer = home / ".evozeus" / ".projects" / "MetaInFLow" / "skill"
            pointer.parent.mkdir(parents=True)
            pointer.symlink_to(target)
            install = home / ".codex" / "skills" / "skill"
            install.parent.mkdir(parents=True)
            install.symlink_to(target)

            def runner(args, cwd=None):
                if len(args) >= 4 and args[0] == "git" and args[3] == "rev-parse":
                    return {"returncode": 0, "stdout": str(target) + "\n", "stderr": ""}
                if len(args) >= 4 and args[0] == "git" and args[3] == "remote":
                    return {"returncode": 0, "stdout": "https://github.com/MetaInFLow/skill.git\n", "stderr": ""}
                return {"returncode": 1, "stdout": "", "stderr": ""}

            report = diagnose_source_contract(
                target=target,
                requested_repo=None,
                skill_name="skill",
                home=home,
                installs=[
                    {
                        "path": str(install),
                        "kind": "symlink",
                        "resolved_path": str(target.resolve()),
                    }
                ],
                runner=runner,
            )

            self.assertTrue(report["managed"])
            self.assertEqual(report["status"], "ok")
            self.assertEqual(report["canonical_repo"], "MetaInFLow/skill")
            self.assertEqual(report["projects_pointer"]["resolved_path"], str(target.resolve()))
            self.assertEqual(report["runtime_installs"][0]["source_contract"], "runtime_pointer_ok")

    def test_source_contract_errors_when_project_pointer_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            target = Path(tmp) / "canonical"
            target.mkdir()
            (target / "SKILL.md").write_text('---\nname: "skill"\n---\n', encoding="utf-8")
            write_wrapper_manifest(
                target,
                build_wrapper_manifest("MetaInFLow/skill", "v0.1.0", ["WRAPPER.md"], []),
            )

            def runner(args, cwd=None):
                if len(args) >= 4 and args[0] == "git" and args[3] == "rev-parse":
                    return {"returncode": 0, "stdout": str(target) + "\n", "stderr": ""}
                return {"returncode": 1, "stdout": "", "stderr": ""}

            report = diagnose_source_contract(
                target=target,
                requested_repo=None,
                skill_name="skill",
                home=home,
                installs=[],
                runner=runner,
            )

            self.assertEqual(report["status"], "error")
            self.assertTrue(any("project pointer is missing" in error for error in report["errors"]))

    def test_source_contract_warns_for_runtime_real_directory_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            target = Path(tmp) / "canonical"
            target.mkdir()
            (target / "SKILL.md").write_text('---\nname: "skill"\n---\n', encoding="utf-8")
            write_wrapper_manifest(
                target,
                build_wrapper_manifest("MetaInFLow/skill", "v0.1.0", ["WRAPPER.md"], []),
            )
            pointer = home / ".evozeus" / ".projects" / "MetaInFLow" / "skill"
            pointer.parent.mkdir(parents=True)
            pointer.symlink_to(target)
            install = home / ".codex" / "skills" / "skill"
            install.mkdir(parents=True)

            def runner(args, cwd=None):
                if len(args) >= 4 and args[0] == "git" and args[3] == "rev-parse":
                    return {"returncode": 0, "stdout": str(target) + "\n", "stderr": ""}
                if len(args) >= 4 and args[0] == "git" and args[3] == "remote":
                    return {"returncode": 0, "stdout": "https://github.com/MetaInFLow/skill.git\n", "stderr": ""}
                return {"returncode": 1, "stdout": "", "stderr": ""}

            report = diagnose_source_contract(
                target=target,
                requested_repo=None,
                skill_name="skill",
                home=home,
                installs=[
                    {
                        "path": str(install),
                        "kind": "directory",
                        "resolved_path": str(install.resolve()),
                    }
                ],
                runner=runner,
            )

            self.assertEqual(report["status"], "warning")
            self.assertEqual(report["runtime_installs"][0]["source_contract"], "runtime_real_directory_warning")
            self.assertTrue(any("real directory" in warning for warning in report["warnings"]))


class TransformPlanningTest(unittest.TestCase):
    def test_plan_transform_action_maps_diagnosis_to_mode(self):
        self.assertEqual(plan_transform_action("migration_required", True), "migrate_layout")
        self.assertEqual(plan_transform_action("missing", False), "bootstrap")
        self.assertEqual(plan_transform_action("missing", True), "adopt")
        self.assertEqual(plan_transform_action("partial", False), "repair")
        self.assertEqual(plan_transform_action("partial", True), "repair")
        self.assertEqual(plan_transform_action("complete", False), "verify")
        self.assertEqual(plan_transform_action("complete", True), "verify")
        self.assertEqual(plan_transform_action("missing", None), "needs_repo_check")


class ReinstallPlanningTest(unittest.TestCase):
    def test_plan_reinstall_creates_symlink_when_install_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            canonical = Path(tmp) / "repo"
            canonical.mkdir()
            (canonical / "SKILL.md").write_text("same", encoding="utf-8")

            plan = plan_reinstall("skill", canonical, home, ["codex"])

            self.assertEqual(plan["stage"], "publish_reinstall")
            self.assertEqual(plan["actions"][0]["action"], "create_symlink")
            self.assertEqual(plan["runtime_skill_installation"]["status"], "planned")
            self.assertEqual(plan["runtime_hook_installation"]["status"], "not_installed")
            self.assertEqual(
                plan["runtime_hook_installation"]["scope"],
                "all_registered_wrapped_skills",
            )

    def test_plan_reinstall_detects_already_linked_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            canonical = Path(tmp) / "repo"
            canonical.mkdir()
            (canonical / "SKILL.md").write_text("same", encoding="utf-8")
            install = home / ".codex" / "skills" / "skill"
            install.parent.mkdir(parents=True)
            install.symlink_to(canonical)

            plan = plan_reinstall("skill", canonical, home, ["codex"])

            self.assertEqual(plan["actions"][0]["action"], "already_linked")

    def test_plan_reinstall_archives_identical_real_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            canonical = Path(tmp) / "repo"
            canonical.mkdir()
            (canonical / "SKILL.md").write_text("same", encoding="utf-8")
            install = home / ".codex" / "skills" / "skill"
            install.mkdir(parents=True)
            (install / "SKILL.md").write_text("same", encoding="utf-8")

            plan = plan_reinstall("skill", canonical, home, ["codex"])

            self.assertEqual(plan["actions"][0]["action"], "archive_then_symlink")

    def test_plan_reinstall_requires_confirmation_for_different_real_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            canonical = Path(tmp) / "repo"
            canonical.mkdir()
            (canonical / "SKILL.md").write_text("canonical", encoding="utf-8")
            install = home / ".codex" / "skills" / "skill"
            install.mkdir(parents=True)
            (install / "SKILL.md").write_text("local edits", encoding="utf-8")

            plan = plan_reinstall("skill", canonical, home, ["codex"])

            self.assertEqual(plan["actions"][0]["action"], "needs_user_confirmation")

    def test_apply_reinstall_creates_missing_runtime_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            canonical = Path(tmp) / "repo"
            canonical.mkdir()
            (canonical / "SKILL.md").write_text("canonical", encoding="utf-8")

            report = apply_reinstall("skill", canonical, home, ["codex"])
            install = home / ".codex" / "skills" / "skill"

            self.assertEqual(report["status"], "applied")
            self.assertTrue(report["writes"])
            self.assertTrue(install.is_symlink())
            self.assertEqual(install.resolve(), canonical.resolve())
            self.assertEqual(report["actions"][0]["result"], "created_symlink")

    def test_apply_reinstall_relinks_wrong_runtime_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            canonical = Path(tmp) / "repo"
            old = Path(tmp) / "old"
            canonical.mkdir()
            old.mkdir()
            (canonical / "SKILL.md").write_text("canonical", encoding="utf-8")
            install = home / ".codex" / "skills" / "skill"
            install.parent.mkdir(parents=True)
            install.symlink_to(old)

            report = apply_reinstall("skill", canonical, home, ["codex"])

            self.assertEqual(report["status"], "applied")
            self.assertEqual(report["actions"][0]["result"], "relinked_symlink")
            self.assertEqual(install.resolve(), canonical.resolve())

    def test_apply_reinstall_prevalidates_all_actions_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            canonical = Path(tmp) / "repo"
            canonical.mkdir()
            (canonical / "SKILL.md").write_text("canonical", encoding="utf-8")
            agents_install = home / ".agents" / "skills" / "skill"
            agents_install.mkdir(parents=True)
            (agents_install / "SKILL.md").write_text("local edits", encoding="utf-8")

            report = apply_reinstall("skill", canonical, home, ["codex", "agents"])

            self.assertEqual(report["status"], "blocked")
            self.assertFalse(report["writes"])
            self.assertFalse((home / ".codex" / "skills" / "skill").exists())
            self.assertTrue(agents_install.is_dir())
            self.assertFalse((home / ".evozeus" / "archives").exists())

    def test_apply_reinstall_archives_real_directory_after_explicit_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            canonical = Path(tmp) / "repo"
            canonical.mkdir()
            (canonical / "SKILL.md").write_text("canonical", encoding="utf-8")
            install = home / ".codex" / "skills" / "skill"
            install.mkdir(parents=True)
            (install / "SKILL.md").write_text("canonical", encoding="utf-8")

            report = apply_reinstall(
                "skill",
                canonical,
                home,
                ["codex"],
                approve_archive=True,
                archive_id="20260718T120000000000Z",
            )
            archived = Path(report["actions"][0]["archive_path"])

            self.assertEqual(report["status"], "applied")
            self.assertTrue(install.is_symlink())
            self.assertEqual(install.resolve(), canonical.resolve())
            self.assertTrue(archived.is_dir())
            self.assertEqual((archived / "SKILL.md").read_text(encoding="utf-8"), "canonical")
            self.assertTrue(
                archived.is_relative_to(home.resolve() / ".evozeus" / "archives" / "runtime-installs")
            )

    def test_apply_reinstall_requires_approval_for_different_real_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            canonical = Path(tmp) / "repo"
            canonical.mkdir()
            (canonical / "SKILL.md").write_text("canonical", encoding="utf-8")
            install = home / ".codex" / "skills" / "skill"
            install.mkdir(parents=True)
            (install / "SKILL.md").write_text("local edits", encoding="utf-8")

            blocked = apply_reinstall("skill", canonical, home, ["codex"])
            applied = apply_reinstall(
                "skill",
                canonical,
                home,
                ["codex"],
                approve_archive=True,
                archive_id="20260718T120000000000Z",
            )

            self.assertEqual(blocked["status"], "blocked")
            self.assertFalse(blocked["writes"])
            self.assertEqual(applied["status"], "applied")
            archived = Path(applied["actions"][0]["archive_path"])
            self.assertEqual((archived / "SKILL.md").read_text(encoding="utf-8"), "local edits")

    def test_apply_reinstall_requires_canonical_skill_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            missing = root / "missing"
            without_skill = root / "repo"
            without_skill.mkdir()

            with self.assertRaisesRegex(ValueError, "canonical path must be an existing directory"):
                apply_reinstall("skill", missing, home, ["codex"])
            with self.assertRaisesRegex(ValueError, "canonical path must contain SKILL.md"):
                apply_reinstall("skill", without_skill, home, ["codex"])

            self.assertFalse(home.exists())


class GlobalHookLifecycleTest(unittest.TestCase):
    def test_global_hook_plan_blocks_invalid_existing_hooks_json_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            hooks_path = home / ".codex" / "hooks.json"
            hooks_path.parent.mkdir(parents=True)
            hooks_path.write_text("{not-json\n", encoding="utf-8")

            plan = plan_global_hook_install(home=home, wrapper_root=Path.cwd())

            self.assertEqual(plan["status"], "blocked")
            self.assertFalse(plan["writes"])
            self.assertTrue(plan["errors"])
            self.assertEqual(hooks_path.read_text(encoding="utf-8"), "{not-json\n")

    def test_global_hook_install_preserves_unrelated_hooks_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            hooks_path = home / ".codex" / "hooks.json"
            hooks_path.parent.mkdir(parents=True)
            unrelated = {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "shell",
                            "hooks": [{"type": "command", "command": "python3 unrelated.py"}],
                        }
                    ]
                }
            }
            hooks_path.write_text(json.dumps(unrelated), encoding="utf-8")

            first = apply_global_hook_install(home=home, wrapper_root=Path.cwd(), approve=True)
            second = apply_global_hook_install(home=home, wrapper_root=Path.cwd(), approve=True)
            merged = json.loads(hooks_path.read_text(encoding="utf-8"))
            session_commands = [
                handler["command"]
                for entry in merged["hooks"]["SessionStart"]
                for handler in entry["hooks"]
            ]

            self.assertEqual(first["status"], "installed")
            self.assertEqual(second["status"], "already_installed")
            self.assertEqual(session_commands.count(GLOBAL_DISPATCHER_COMMAND), 1)
            self.assertIn("PreToolUse", merged["hooks"])
            self.assertEqual(read_global_hook_status(home)["trust_status"], "pending_review")

    def test_global_hook_uninstall_removes_only_evozeus_registration(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            apply_global_hook_install(home=home, wrapper_root=Path.cwd(), approve=True)
            hooks_path = home / ".codex" / "hooks.json"
            hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
            hooks["hooks"]["SessionStart"].append(
                {
                    "matcher": "startup",
                    "hooks": [{"type": "command", "command": "python3 keep.py"}],
                }
            )
            hooks_path.write_text(json.dumps(hooks), encoding="utf-8")

            report = apply_global_hook_uninstall(home=home, approve=True)
            remaining = json.loads(hooks_path.read_text(encoding="utf-8"))
            commands = [
                handler["command"]
                for entry in remaining["hooks"]["SessionStart"]
                for handler in entry["hooks"]
            ]

            self.assertEqual(report["status"], "uninstalled")
            self.assertNotIn(GLOBAL_DISPATCHER_COMMAND, commands)
            self.assertIn("python3 keep.py", commands)

    def test_global_hook_install_rolls_back_when_a_write_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            hooks_path = home / ".codex" / "hooks.json"
            hooks_path.parent.mkdir(parents=True)
            original_hooks = '{"hooks":{"PreToolUse":[]}}\n'
            hooks_path.write_text(original_hooks, encoding="utf-8")

            from scripts import evozeus_wrapper_global_hook as global_hook

            original_write = global_hook._atomic_write
            calls = 0

            def fail_second_write(path, data):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("synthetic write failure")
                return original_write(path, data)

            with patch(
                "scripts.evozeus_wrapper_global_hook._atomic_write",
                side_effect=fail_second_write,
            ), self.assertRaisesRegex(OSError, "synthetic write failure"):
                apply_global_hook_install(home=home, wrapper_root=Path.cwd(), approve=True)

            self.assertEqual(hooks_path.read_text(encoding="utf-8"), original_hooks)
            self.assertFalse((home / ".evozeus/hooks/evozeus_wrapper_dispatcher.py").exists())
            self.assertFalse((home / ".evozeus/hooks/state.json").exists())

    def test_global_hook_trust_is_recorded_separately_after_explicit_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            apply_global_hook_install(home=home, wrapper_root=Path.cwd(), approve=True)

            pending = read_global_hook_status(home)
            recorded = record_global_hook_trust(home, status="trusted", approve=True)
            trusted = read_global_hook_status(home)

            self.assertEqual(pending["trust_status"], "pending_review")
            self.assertEqual(recorded["status"], "trusted")
            self.assertEqual(trusted["trust_status"], "trusted")

    def test_global_hook_cli_plans_and_installs_with_explicit_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            environment = {**os.environ, "HOME": str(home)}

            plan = subprocess.run(
                [
                    sys.executable,
                    "scripts/evozeus_wrapper.py",
                    "hook",
                    "global",
                    "plan",
                    "--json",
                ],
                text=True,
                capture_output=True,
                env=environment,
                check=False,
            )
            install = subprocess.run(
                [
                    sys.executable,
                    "scripts/evozeus_wrapper.py",
                    "hook",
                    "global",
                    "install",
                    "--approve",
                    "--json",
                ],
                text=True,
                capture_output=True,
                env=environment,
                check=False,
            )

            self.assertEqual(plan.returncode, 0, plan.stderr)
            self.assertEqual(json.loads(plan.stdout)["status"], "planned")
            self.assertEqual(install.returncode, 0, install.stderr)
            self.assertEqual(json.loads(install.stdout)["status"], "installed")
            self.assertTrue((home / ".codex/hooks.json").is_file())


class GlobalDispatcherTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        template = Path("templates/global/evozeus_wrapper_dispatcher.py").resolve()
        spec = importlib.util.spec_from_file_location("evozeus_wrapper_global_dispatcher", template)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(cls.module)

    def create_wrapped_target(self, home: Path, name: str, version: str) -> Path:
        target = home.parent / f"canonical-{name}"
        target.mkdir()
        manifest = target / ".evozeus-wrapper" / "wrapper.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            json.dumps(
                {
                    "canonical_repo": f"MetaInFLow/{name}",
                    "wrapper_version": version,
                }
            ),
            encoding="utf-8",
        )
        pointer = home / ".evozeus" / ".projects" / "MetaInFLow" / name
        pointer.parent.mkdir(parents=True, exist_ok=True)
        pointer.symlink_to(target)
        return target

    def test_dispatcher_blocks_with_aggregate_count_when_targets_are_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            self.create_wrapped_target(home, "private-skill-a", "v0.9.1")
            self.create_wrapped_target(home, "private-skill-b", "v0.8.0")

            payload = self.module.evaluate_session_start(
                home=home,
                latest_resolver=lambda: {
                    "version": "v0.10.0",
                    "source": "test",
                    "error": None,
                },
            )
            serialized = json.dumps(payload, ensure_ascii=False)

            self.assertFalse(payload["continue"])
            self.assertIn("2 个 EvoZeus harness 落后", payload["stopReason"])
            self.assertNotIn("private-skill", serialized)
            self.assertNotIn(str(home), serialized)

    def test_dispatcher_allows_when_all_targets_are_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            self.create_wrapped_target(home, "current-skill", "v0.10.0")

            payload = self.module.evaluate_session_start(
                home=home,
                latest_resolver=lambda: {
                    "version": "v0.10.0",
                    "source": "test",
                    "error": None,
                },
            )

            self.assertTrue(payload["continue"])
            self.assertIn("current", payload["systemMessage"])

    def test_dispatcher_uses_cached_latest_when_remote_lookup_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            cache = home / ".evozeus/cache/evozeus-wrapper-latest.json"
            cache.parent.mkdir(parents=True)
            cache.write_text(
                json.dumps({"version": "v0.10.0", "checked_at_epoch": 1000}),
                encoding="utf-8",
            )

            resolution = self.module.resolve_latest_version(
                home=home,
                now_epoch=5000,
                environment={},
                fetcher=lambda: {"version": None, "url": None, "error": "offline"},
            )

            self.assertEqual(resolution["version"], "v0.10.0")
            self.assertEqual(resolution["source"], "stale_cache")

    def test_dispatcher_warns_and_allows_when_latest_is_unknown_without_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            self.create_wrapped_target(home, "offline-skill", "v0.9.1")

            payload = self.module.evaluate_session_start(
                home=home,
                latest_resolver=lambda: {
                    "version": None,
                    "source": "unavailable",
                    "error": "offline",
                },
            )

            self.assertTrue(payload["continue"])
            self.assertIn("unavailable", payload["systemMessage"])

    def test_dispatcher_blocks_deterministic_manifest_mismatch_without_private_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            target = self.create_wrapped_target(home, "mismatch-skill", "v0.10.0")
            manifest = target / ".evozeus-wrapper/wrapper.json"
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["canonical_repo"] = "MetaInFLow/something-else"
            manifest.write_text(json.dumps(data), encoding="utf-8")

            payload = self.module.evaluate_session_start(
                home=home,
                latest_resolver=lambda: {
                    "version": "v0.10.0",
                    "source": "test",
                    "error": None,
                },
            )
            serialized = json.dumps(payload, ensure_ascii=False)

            self.assertFalse(payload["continue"])
            self.assertIn("本地 harness 注册异常", payload["stopReason"])
            self.assertNotIn("mismatch-skill", serialized)

    def test_installed_dispatcher_runs_from_consumer_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            consumer = Path(tmp) / "consumer-workspace"
            consumer.mkdir()
            self.create_wrapped_target(home, "consumer-skill", "v0.9.1")
            apply_global_hook_install(home=home, wrapper_root=Path.cwd(), approve=True)
            dispatcher = home / ".evozeus/hooks/evozeus_wrapper_dispatcher.py"

            result = subprocess.run(
                [sys.executable, str(dispatcher)],
                input=json.dumps(
                    {
                        "hook_event_name": "SessionStart",
                        "source": "startup",
                        "cwd": str(consumer),
                    }
                ),
                text=True,
                capture_output=True,
                cwd=consumer,
                env={
                    **os.environ,
                    "HOME": str(home),
                    "EVOZEUS_WRAPPER_LATEST_VERSION": "v0.10.0",
                },
                check=False,
            )
            payload = json.loads(result.stdout)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(payload["continue"])
            self.assertIn("1 个 EvoZeus harness 落后", payload["stopReason"])


class EvolutionAndUpgradePlanningTest(unittest.TestCase):
    def test_classify_pr_permission(self):
        self.assertEqual(classify_pr_permission(write=True, fork=True), "direct_pr")
        self.assertEqual(classify_pr_permission(write=False, fork=True), "fork_pr")
        self.assertEqual(classify_pr_permission(write=False, fork=False), "local_patch")

    def test_classify_wrapper_upgrade(self):
        self.assertEqual(classify_wrapper_upgrade("v0.1.0", "v0.1.0", managed_dirty=False), "up_to_date")
        self.assertEqual(classify_wrapper_upgrade("v0.1.0", "v0.1.1", managed_dirty=False), "auto_pr")
        self.assertEqual(classify_wrapper_upgrade("v0.1.0", "v0.2.0", managed_dirty=True), "needs_merge_review")
        self.assertEqual(classify_wrapper_upgrade("v0.1.0", "v1.0.0", managed_dirty=False), "requires_confirmation")
        self.assertEqual(classify_wrapper_upgrade("v0.2.0", "v0.1.0", managed_dirty=False), "local_ahead")

    def test_plan_harness_upgrade_reports_latest_unknown_instead_of_self_comparing(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            write_wrapper_manifest(
                target,
                build_wrapper_manifest("MetaInFLow/skill", "v0.6.0", [], []),
            )

            with patch(
                "scripts.evozeus_wrapper_lifecycle.read_latest_release",
                return_value={"exists": False, "tag": None, "error": "offline"},
            ):
                plan = plan_harness_upgrade(target=target)

            self.assertEqual(plan["current_version"], "v0.6.0")
            self.assertIsNone(plan["latest_version"])
            self.assertEqual(plan["latest_source"], "unavailable")
            self.assertEqual(plan["upgrade_status"], "latest_unknown")

    def test_plan_harness_upgrade_resolves_authoritative_github_latest_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            write_wrapper_manifest(
                target,
                build_wrapper_manifest("MetaInFLow/skill", "v0.6.0", [], []),
            )

            with patch(
                "scripts.evozeus_wrapper_lifecycle.read_latest_release",
                return_value={"exists": True, "tag": "v0.8.0", "url": "https://example.test/v0.8.0"},
            ):
                plan = plan_harness_upgrade(target=target)

            self.assertEqual(plan["latest_version"], "v0.8.0")
            self.assertEqual(plan["latest_source"], "github_latest_release")
            self.assertIsNone(plan["latest_lookup_error"])
            self.assertEqual(plan["upgrade_status"], "auto_pr")

    def test_plan_harness_upgrade_reports_lookup_error_when_github_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            write_wrapper_manifest(
                target,
                build_wrapper_manifest("MetaInFLow/skill", "v0.8.0", [], []),
            )

            with patch(
                "scripts.evozeus_wrapper_lifecycle.read_latest_release",
                return_value={"exists": False, "tag": None, "error": "network unavailable"},
            ):
                plan = plan_harness_upgrade(target=target)

            self.assertIsNone(plan["latest_version"])
            self.assertEqual(plan["latest_source"], "unavailable")
            self.assertEqual(plan["latest_lookup_error"], "network unavailable")
            self.assertEqual(plan["upgrade_status"], "latest_unknown")

    def test_plan_harness_upgrade_reports_up_to_date_only_from_authoritative_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            write_wrapper_manifest(
                target,
                build_wrapper_manifest("MetaInFLow/skill", "v0.8.0", [], []),
            )

            with patch(
                "scripts.evozeus_wrapper_lifecycle.read_latest_release",
                return_value={"exists": True, "tag": "v0.8.0", "url": "https://example.test/v0.8.0"},
            ):
                plan = plan_harness_upgrade(target=target)

            self.assertEqual(plan["latest_source"], "github_latest_release")
            self.assertEqual(plan["upgrade_status"], "up_to_date")

    def test_plan_harness_upgrade_reports_local_ahead_of_authoritative_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            write_wrapper_manifest(
                target,
                build_wrapper_manifest("MetaInFLow/skill", "v0.9.0", [], []),
            )

            with patch(
                "scripts.evozeus_wrapper_lifecycle.read_latest_release",
                return_value={"exists": True, "tag": "v0.8.0", "url": "https://example.test/v0.8.0"},
            ):
                plan = plan_harness_upgrade(target=target)

            self.assertEqual(plan["latest_source"], "github_latest_release")
            self.assertEqual(plan["upgrade_status"], "local_ahead")

    def test_plan_harness_upgrade_prioritizes_required_layout_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            legacy_manifest = target / LEGACY_TARGET_WRAPPER_MANIFEST
            legacy_manifest.parent.mkdir(parents=True)
            legacy_manifest.write_text(
                '{"canonical_repo":"MetaInFLow/skill","wrapper_version":"v0.7.0"}\n',
                encoding="utf-8",
            )

            plan = plan_harness_upgrade(target=target, latest_version="v0.7.0")

            self.assertTrue(plan["migration_required"])
            self.assertEqual(plan["upgrade_status"], "up_to_date")
            self.assertEqual(plan["recommended_action"], "migrate_layout")

    def test_plan_harness_upgrade_returns_append_only_migration_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            (target / "SKILL.md").write_text('---\nname: "skill"\n---\n', encoding="utf-8")
            write_wrapper_manifest(
                target,
                build_wrapper_manifest("MetaInFLow/skill", "v0.1.1", ["WRAPPER.md"], []),
            )

            plan = plan_harness_upgrade(
                target=target,
                latest_version="v0.2.0",
                managed_dirty=False,
                today=date(2026, 6, 27),
            )

            self.assertEqual(plan["upgrade_status"], "auto_pr")
            self.assertEqual(plan["current_version"], "v0.1.1")
            self.assertEqual(plan["latest_version"], "v0.2.0")
            self.assertEqual(plan["target_infra_dir"], ".evozeus-wrapper")
            self.assertEqual(plan["legacy_infra_dir"], ".evozeus_evoinfra")
            self.assertEqual(plan["oldest_infra_dir"], ".evozeus")
            self.assertEqual(plan["manifest_path"], TARGET_WRAPPER_MANIFEST)
            self.assertFalse(plan["legacy_manifest_detected"])
            self.assertFalse(plan["migration_required"])
            self.assertTrue(plan["append_only"])
            self.assertTrue(plan["status_check_first"])
            self.assertFalse(plan["requires_confirmation"])
            self.assertEqual(
                plan["migration"]["doc_path"],
                ".evozeus-wrapper/docs/migrations/2026-06-27-v0.1.1-to-v0.2.0.md",
            )
            self.assertEqual(plan["integration"]["mode"], "prompt_runtime_check")
            self.assertFalse(plan["integration"]["native_host_hook_installed"])
            self.assertIn("SKILL.md EvoZeus-wrapper status check section (front matter prelude)", plan["planned_files"])
            self.assertIn("SKILL.md EvoZeus-wrapper section or migration note (append only)", plan["planned_files"])
            self.assertIn(TARGET_MIGRATIONS_README, plan["planned_files"])
            self.assertIn(TARGET_WRAPPER_MANIFEST, plan["planned_files"])
            self.assertIn(".codex/hooks.json", plan["planned_files"])
            self.assertIn(CODEX_START_HOOK_SCRIPT, plan["planned_files"])

    def test_plan_harness_upgrade_requires_repair_when_manifest_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()

            plan = plan_harness_upgrade(
                target=target,
                latest_version="v0.2.0",
                today=date(2026, 6, 27),
            )

            self.assertEqual(plan["upgrade_status"], "missing_manifest")
            self.assertTrue(plan["requires_confirmation"])
            self.assertEqual(plan["recommended_action"], "repair_or_adopt_before_upgrade")
            self.assertEqual(plan["migration"]["from_wrapper_version"], None)
            self.assertEqual(
                plan["migration"]["doc_path"],
                ".evozeus-wrapper/docs/migrations/2026-06-27-unknown-to-v0.2.0.md",
            )

    def test_plan_harness_upgrade_uses_agents_root_entry_for_runtime_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "kit"
            target.mkdir()
            (target / "AGENTS.md").write_text("# Runtime\n", encoding="utf-8")
            (target / "skills").mkdir()
            skill_dir = target / "skills" / "sales-coach"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text('---\nname: "sales-coach"\n---\n', encoding="utf-8")

            plan = plan_harness_upgrade(
                target=target,
                latest_version="v0.2.0",
                today=date(2026, 6, 27),
            )

            self.assertIn(
                "AGENTS.md EvoZeus-wrapper status check section (instruction surface prelude)",
                plan["planned_files"],
            )
            self.assertIn("AGENTS.md", plan["evolution_surface_policy"])
            self.assertNotIn("SKILL.md EvoZeus-wrapper status check section (front matter prelude)", plan["planned_files"])

    def test_plan_harness_upgrade_uses_hook_loaded_control_skill_for_plugin_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "hooked-skill-system"
            target.mkdir()
            (target / ".codex-plugin").mkdir()
            (target / ".codex-plugin" / "plugin.json").write_text(
                '{"skills":"./skills/","hooks":"./hooks/hooks-codex.json"}',
                encoding="utf-8",
            )
            (target / "hooks").mkdir()
            (target / "hooks" / "hooks-codex.json").write_text(
                '{"hooks":{"session-start":"skills/session-bootstrap/SKILL.md"}}',
                encoding="utf-8",
            )
            skill_dir = target / "skills" / "session-bootstrap"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                '---\nname: "session-bootstrap"\n---\n# Session Bootstrap\nUse at session start to load skills and route skill usage.\n',
                encoding="utf-8",
            )

            plan = plan_harness_upgrade(
                target=target,
                latest_version="v0.2.0",
                today=date(2026, 6, 27),
                instruction_surface="skills/session-bootstrap/SKILL.md",
            )

            self.assertIn(
                "skills/session-bootstrap/SKILL.md EvoZeus-wrapper status check section (instruction surface prelude)",
                plan["planned_files"],
            )
            self.assertIn("skills/session-bootstrap/SKILL.md", plan["evolution_surface_policy"])

    def test_codex_session_start_hook_adapter_reads_target_evoinfra_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            write_wrapper_manifest(
                target,
                build_wrapper_manifest("MetaInFLow/skill", "v0.6.0", ["WRAPPER.md"], []),
            )
            hook_dir = (target / CODEX_START_HOOK_SCRIPT).parent
            hook_dir.mkdir(parents=True)
            template = Path("templates/target/.codex/hooks/evozeus_wrapper_start_check.py").read_text(
                encoding="utf-8"
            )
            adapter = target / CODEX_START_HOOK_SCRIPT
            adapter.write_text(template.replace("{{WRAPPER_VERSION}}", "v0.7.0"), encoding="utf-8")

            advisory = subprocess.run(
                [sys.executable, str(adapter)],
                input=json.dumps({"hook_event_name": "SessionStart", "source": "startup"}),
                text=True,
                capture_output=True,
                cwd=target,
                env={**os.environ, "EVOZEUS_WRAPPER_LATEST_VERSION": "v0.7.0"},
                check=False,
            )
            advisory_payload = json.loads(advisory.stdout)

            self.assertEqual(advisory.returncode, 0)
            self.assertTrue(advisory_payload["continue"])
            self.assertIn("non-breaking upgrade", advisory_payload["systemMessage"])
            self.assertIn(
                "capability=repo_maintenance_hook",
                advisory_payload["hookSpecificOutput"]["additionalContext"],
            )
            self.assertIn(
                "scope=canonical_repository",
                advisory_payload["hookSpecificOutput"]["additionalContext"],
            )

            strict_env = {
                **os.environ,
                "EVOZEUS_WRAPPER_HOOK_ENFORCEMENT": "strict",
                "EVOZEUS_WRAPPER_LATEST_VERSION": "v0.7.0",
            }
            strict = subprocess.run(
                [sys.executable, str(adapter)],
                input=json.dumps({"hook_event_name": "SessionStart", "source": "startup"}),
                text=True,
                capture_output=True,
                cwd=target,
                env=strict_env,
                check=False,
            )
            strict_payload = json.loads(strict.stdout)

            self.assertEqual(strict.returncode, 0)
            self.assertFalse(strict_payload["continue"])
            self.assertIn("wrapper harness", strict_payload["stopReason"])

    def test_codex_hook_resolves_latest_release_after_install(self):
        template_path = Path("templates/target/.codex/hooks/evozeus_wrapper_start_check.py").resolve()
        spec = importlib.util.spec_from_file_location("evozeus_wrapper_hook_template", template_path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        result = module.resolve_latest_version(
            current="v0.7.0",
            environment={},
            fetcher=lambda: {
                "version": "v0.8.0",
                "url": "https://example.test/v0.8.0",
                "error": None,
            },
        )

        self.assertEqual(result["version"], "v0.8.0")
        self.assertEqual(result["source"], "github_latest_release")
        self.assertIsNone(result["error"])

    def test_codex_hook_reports_latest_unknown_when_remote_lookup_fails(self):
        template_path = Path("templates/target/.codex/hooks/evozeus_wrapper_start_check.py").resolve()
        spec = importlib.util.spec_from_file_location("evozeus_wrapper_hook_template_offline", template_path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        result = module.resolve_latest_version(
            current="v0.8.0",
            environment={},
            fetcher=lambda: {"version": None, "url": None, "error": "offline"},
        )

        self.assertIsNone(result["version"])
        self.assertEqual(result["source"], "unavailable")
        self.assertEqual(result["error"], "offline")

    def test_codex_project_hook_reuses_fresh_global_dispatcher_cache(self):
        template_path = Path("templates/target/.codex/hooks/evozeus_wrapper_start_check.py").resolve()
        spec = importlib.util.spec_from_file_location("evozeus_wrapper_hook_template_cache", template_path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            cache = home / ".evozeus/cache/evozeus-wrapper-latest.json"
            cache.parent.mkdir(parents=True)
            cache.write_text(
                json.dumps({"version": "v0.10.0", "checked_at_epoch": 1000}),
                encoding="utf-8",
            )

            result = module.resolve_latest_version(
                current="v0.9.1",
                environment={},
                fetcher=lambda: self.fail("fresh global cache should avoid another remote lookup"),
                home=home,
                now_epoch=1100,
            )

        self.assertEqual(result["version"], "v0.10.0")
        self.assertEqual(result["source"], "global_dispatcher_cache")


if __name__ == "__main__":
    unittest.main()
