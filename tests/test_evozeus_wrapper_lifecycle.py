from pathlib import Path
import tempfile
import unittest

from scripts.evozeus_wrapper_lifecycle import (
    diagnose_environment,
    diagnose_skill,
    path_kind,
    repo_from_remote,
    skill_name_from_skill_md,
    stage_label,
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


if __name__ == "__main__":
    unittest.main()
