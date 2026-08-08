import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase


class ApplicationStartupTests(SimpleTestCase):
    def test_system_check_does_not_access_database_during_app_initialization(self):
        project_dir = Path(__file__).resolve().parents[2]

        result = subprocess.run(
            [sys.executable, "-W", "default", "manage.py", "check"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        output = result.stdout + result.stderr

        self.assertEqual(result.returncode, 0, output)
        self.assertNotIn("Accessing the database during app initialization", output)
        self.assertNotIn("Warning: Could not create user groups", output)
