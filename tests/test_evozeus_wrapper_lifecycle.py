import contextlib
import io
import json
from datetime import date
from pathlib import Path
import tempfile
import unittest

from scripts.evozeus_wrapper_lifecycle import (
    LEGACY_TARGET_WRAPPER_MANIFEST,
    TARGET_WRAPPER_MANIFEST,
    build_wrapper_manifest,
    classify_pr_permission,
    classify_wrapper_upgrade,
    classify_integration_mode,
    detect_target_architecture,
    diagnose_environment,
    diagnose_skill,
    diagnose_source_contract,
    load_wrapper_manifest,
    migrate_target_infra_dir,
    plan_feedback_audit,
    plan_harness_upgrade,
    path_kind,
    plan_reinstall,
    plan_transform_action,
    repo_from_remote,
    skill_name_from_skill_md,
    stage_label,
    write_wrapper_manifest,
    wrapper_manifest_status,
)
from scripts.evozeus_wrapper_preflight import (
    check_integration_contract,
    root_entry_path as preflight_root_entry_path,
)


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

    def test_load_wrapper_manifest_falls_back_to_legacy_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            legacy_path = target / LEGACY_TARGET_WRAPPER_MANIFEST
            legacy_path.parent.mkdir()
            legacy_path.write_text(
                '{"canonical_repo":"MetaInFLow/skill","wrapper_version":"v0.5.0"}\n',
                encoding="utf-8",
            )

            manifest = load_wrapper_manifest(target)
            status = wrapper_manifest_status(target)

            self.assertEqual(manifest["canonical_repo"], "MetaInFLow/skill")
            self.assertTrue(status["legacy_manifest_detected"])
            self.assertTrue(status["migration_required"])
            self.assertEqual(status["manifest_source"], "legacy")

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

    def test_migrate_target_infra_dir_moves_legacy_files_and_rewrites_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            (target / "SKILL.md").write_text(
                "Read `.evozeus/wrapper.json` and `.evozeus/feedback-policy.json`.\n",
                encoding="utf-8",
            )
            legacy_dir = target / ".evozeus"
            legacy_dir.mkdir()
            (legacy_dir / "wrapper.json").write_text(
                json.dumps(
                    {
                        "canonical_repo": "MetaInFLow/skill",
                        "wrapper_version": "v0.5.0",
                        "managed_files": [
                            ".evozeus/wrapper.json",
                            ".evozeus/feedback-policy.json",
                            ".evozeus/audit-rule.md",
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (legacy_dir / "feedback-policy.json").write_text(
                '{"audit_rule":".evozeus/audit-rule.md"}\n',
                encoding="utf-8",
            )
            (legacy_dir / "audit-rule.md").write_text("# Rule\n", encoding="utf-8")

            report = migrate_target_infra_dir(target, latest_version="v0.6.0")
            manifest = load_wrapper_manifest(target)
            skill_text = (target / "SKILL.md").read_text(encoding="utf-8")
            policy = (target / ".evozeus_evoinfra" / "feedback-policy.json").read_text(encoding="utf-8")

            self.assertIn("move .evozeus/ -> .evozeus_evoinfra/", report["actions"])
            self.assertFalse((target / ".evozeus").exists())
            self.assertTrue((target / TARGET_WRAPPER_MANIFEST).is_file())
            self.assertEqual(manifest["wrapper_version"], "v0.6.0")
            self.assertIn(".evozeus_evoinfra/wrapper.json", manifest["managed_files"])
            self.assertIn(".evozeus_evoinfra/wrapper.json", skill_text)
            self.assertIn(".evozeus_evoinfra/audit-rule.md", policy)

    def test_plan_feedback_audit_captures_wrapper_defect(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skill"
            target.mkdir()
            write_wrapper_manifest(
                target,
                build_wrapper_manifest("MetaInFLow/skill", "v0.6.0", [], []),
            )
            policy_path = target / ".evozeus_evoinfra" / "feedback-policy.json"
            policy_path.write_text(
                '{"management_mode":"semi_managed","audit_rule":".evozeus_evoinfra/audit-rule.md"}\n',
                encoding="utf-8",
            )

            report = plan_feedback_audit(
                target=target,
                user_input="这个 wrapper 没有自动 issue 回收，有问题",
            )

            self.assertTrue(report["should_capture"])
            self.assertEqual(report["route"], "wrapper")
            self.assertEqual(report["issue_repo"], "MetaInFLow/EvoZeus-wrapper")
            self.assertEqual(report["policy_path"], ".evozeus_evoinfra/feedback-policy.json")
            self.assertIn("gh issue create --repo MetaInFLow/EvoZeus-wrapper", report["issue_create_command"])

    def test_preflight_rejects_native_hook_mode_without_hook_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "wrapped-skill"
            target.mkdir()
            manifest = {"integration": {"mode": "native_host_hook"}}

            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                check_integration_contract(target, manifest)

    def test_preflight_accepts_native_hook_mode_with_hook_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "wrapped-skill"
            target.mkdir()
            (target / ".claude-plugin").mkdir()
            (target / ".claude-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
            (target / "hooks").mkdir()
            (target / "hooks" / "hooks.json").write_text("{}", encoding="utf-8")
            manifest = {"integration": {"mode": "native_host_hook"}}

            with contextlib.redirect_stdout(io.StringIO()):
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

    def test_diagnose_skill_marks_partial_harness_when_some_wrapper_files_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            target = Path(tmp) / "skill"
            target.mkdir()
            (target / "SKILL.md").write_text('---\nname: "skill"\n---\n', encoding="utf-8")
            (target / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")

            report = diagnose_skill(target=target, repo=None, skill_name=None, home=home)
            self.assertEqual(report["harness"]["state"], "partial")
            self.assertIn("CHANGELOG.md", report["harness"]["present_files"])

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
            self.assertEqual(architecture["integration"]["mode"], "native_host_hook")
            self.assertTrue(architecture["integration"]["native_host_hook_installed"])

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
            self.assertEqual(plan["target_infra_dir"], ".evozeus_evoinfra")
            self.assertEqual(plan["legacy_infra_dir"], ".evozeus")
            self.assertEqual(plan["manifest_path"], ".evozeus_evoinfra/wrapper.json")
            self.assertFalse(plan["legacy_manifest_detected"])
            self.assertFalse(plan["migration_required"])
            self.assertTrue(plan["append_only"])
            self.assertTrue(plan["status_check_first"])
            self.assertFalse(plan["requires_confirmation"])
            self.assertEqual(
                plan["migration"]["doc_path"],
                "docs/wrapper-migrations/2026-06-27-v0.1.1-to-v0.2.0.md",
            )
            self.assertEqual(plan["integration"]["mode"], "prompt_runtime_check")
            self.assertFalse(plan["integration"]["native_host_hook_installed"])
            self.assertIn("SKILL.md EvoZeus-wrapper status check section (front matter prelude)", plan["planned_files"])
            self.assertIn("SKILL.md EvoZeus-wrapper section or migration note (append only)", plan["planned_files"])
            self.assertIn("docs/wrapper-migrations/README.md", plan["planned_files"])
            self.assertIn(".evozeus_evoinfra/wrapper.json", plan["planned_files"])

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
                "docs/wrapper-migrations/2026-06-27-unknown-to-v0.2.0.md",
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


if __name__ == "__main__":
    unittest.main()
