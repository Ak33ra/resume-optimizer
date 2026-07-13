import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.privacy_check import pii_kinds, protected_path, scan_outgoing


class PrivacyCheckTests(unittest.TestCase):
    def test_protected_paths_allow_only_templates(self):
        self.assertTrue(protected_path("resumes/acme_resume.tex"))
        self.assertTrue(protected_path("outputs/acme_resume.pdf"))
        self.assertTrue(protected_path("job_targets.csv"))
        self.assertTrue(protected_path("job_descriptions/acme_backend.md"))
        self.assertFalse(protected_path("resumes/README.md"))
        self.assertFalse(protected_path("source_material/EXPERIENCE.example.md"))
        self.assertFalse(protected_path("job_descriptions/JOB_DESCRIPTION.example.md"))

    def test_pii_detection_ignores_documented_placeholders(self):
        self.assertEqual(pii_kinds(b"you@example.com 123-456-7890"), set())
        self.assertEqual(pii_kinds(b"candidate@private.dev (212) 555-0199"), set())
        email = b"applicant" + b"@" + b"confidential.dev"
        phone = b"646" + b"-555-0298"
        self.assertEqual(pii_kinds(email + b" " + phone), {"email", "phone"})

    def test_outgoing_scan_catches_pii_added_then_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            (root / "README.md").write_text("baseline\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
            baseline = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            private_email = "applicant" + "@" + "confidential.dev"
            (root / "notes.md").write_text(private_email + "\n", encoding="utf-8")
            subprocess.run(["git", "add", "notes.md"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "add private note"], cwd=root, check=True)
            os.unlink(root / "notes.md")
            subprocess.run(["git", "add", "-u"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "remove private note"], cwd=root, check=True)
            tip = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()

            previous = os.getcwd()
            try:
                os.chdir(root)
                problems = scan_outgoing(tip, baseline)
            finally:
                os.chdir(previous)
            self.assertTrue(any("possible email in notes.md" in problem for problem in problems))

    def test_pre_push_exception_is_scoped_to_attested_remote_and_url(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            (root / "README.md").write_text("baseline\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
            baseline = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            private_email = "applicant" + "@" + "confidential.dev"
            (root / "notes.md").write_text(private_email + "\n", encoding="utf-8")
            subprocess.run(["git", "add", "notes.md"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "private"], cwd=root, check=True)
            tip = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()

            source_root = Path(__file__).resolve().parents[1]
            (root / "scripts" / "hooks").mkdir(parents=True)
            shutil.copy2(source_root / "scripts" / "privacy_check.py", root / "scripts" / "privacy_check.py")
            hook = root / "scripts" / "hooks" / "pre-push"
            shutil.copy2(source_root / "scripts" / "hooks" / "pre-push", hook)
            hook.chmod(0o755)
            url = "git@github.com:example/attested-private.git"
            subprocess.run(["git", "remote", "add", "origin", url], cwd=root, check=True)
            push_line = f"refs/heads/main {tip} refs/heads/main {baseline}\n"

            subprocess.run(["git", "config", "resumeopt.allowPII", "true"], cwd=root, check=True)
            unscoped = subprocess.run(
                [str(hook), "origin", url], cwd=root, input=push_line, text=True, capture_output=True
            )
            self.assertEqual(unscoped.returncode, 1)

            subprocess.run(["git", "config", "resumeopt.privateRemote", "origin"], cwd=root, check=True)
            subprocess.run(["git", "config", "resumeopt.privatePushUrl", url], cwd=root, check=True)
            scoped = subprocess.run(
                [str(hook), "origin", url], cwd=root, input=push_line, text=True, capture_output=True
            )
            self.assertEqual(scoped.returncode, 0, scoped.stderr)


if __name__ == "__main__":
    unittest.main()
