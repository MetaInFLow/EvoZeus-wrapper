from pathlib import Path
import tempfile
import unittest

from scripts.evozeus_wrapper_lifecycle import (
    build_wrapper_manifest,
    classify_pr_permission,
    classify_wrapper_upgrade,
    diagnose_environment,
    diagnose_skill,
    diagnose_source_contract,
    load_wrapper_manifest,
    path_kind,
    plan_reinstall,
    plan_transform_action,
    repo_from_remote,
    skill_name_from_skill_md,
    stage_label,
    write_wrapper_manifest,
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
            self.assertEqual(report["evozeus_home"]["exists"], True)
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
            self.assertEqual(report["evozeus_home"]["exists"], False)
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


if __name__ == "__main__":
    unittest.main()
