from pathlib import Path
import tempfile
import unittest

from scripts.evozeus_wrapper_lifecycle import (
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


if __name__ == "__main__":
    unittest.main()
