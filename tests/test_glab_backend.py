#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PLUGIN_ROOT / "skills" / "gitlab-selfhosted" / "scripts" / "gitlab_api.py"


class GlabBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.log = root / "calls.jsonl"
        self.glab = root / "glab"
        self.glab.write_text(self.mock_glab_source(), encoding="utf-8")
        self.glab.chmod(0o755)
        self.env = os.environ.copy()
        self.env["PATH"] = str(root) + os.pathsep + self.env.get("PATH", "")
        self.env["MOCK_GLAB_LOG"] = str(self.log)
        self.env["MOCK_GLAB_AUTH"] = "0"
        self.env.pop("GITLAB_TOKEN", None)

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def mock_glab_source():
        return f"""#!/usr/bin/env python3
import json
import os
import sys

entry = {{"args": sys.argv[1:], "stdin": sys.stdin.read() if "--input" in sys.argv else None}}
with open(os.environ["MOCK_GLAB_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps(entry) + "\\n")
if sys.argv[1:3] == ["auth", "status"]:
    raise SystemExit(int(os.environ.get("MOCK_GLAB_AUTH", "0")))
if sys.argv[1] != "api":
    raise SystemExit(2)
endpoint = sys.argv[sys.argv.index("--method") + 2]
if endpoint == "user":
    print(json.dumps({{"id": 1, "username": "bert", "name": "Bert"}}))
elif endpoint.startswith("projects?"):
    print(json.dumps([{{"id": 42, "name": "Demo", "path_with_namespace": "group/demo"}}]))
elif endpoint == "projects/group%2Fdemo/issues":
    payload = json.loads(entry["stdin"])
    print(json.dumps({{"id": 71, "iid": 8, "title": payload["title"], "description": payload["description"], "state": "opened"}}), end="")
else:
    print(json.dumps({{"message": "not found"}}))
    raise SystemExit(1)
"""

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def api_calls(self):
        return [call for call in self.calls() if call["args"] and call["args"][0] == "api"]

    def run_cli(self, *args, backend="glab"):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--url", "https://git.example.test", "--backend", backend, *args],
            text=True,
            capture_output=True,
            env=self.env,
            timeout=10,
            check=False,
        )

    def test_config_uses_glab_without_environment_token(self):
        result = self.run_cli("config")
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads(result.stdout)
        self.assertEqual(config["backend"], "glab")
        self.assertEqual(config["authentication"], "glab")
        self.assertTrue(config["token_configured"])
        self.assertNotIn("test-token", result.stdout)

    def test_whoami_uses_configured_hostname(self):
        result = self.run_cli("whoami")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["username"], "bert")
        args = self.api_calls()[0]["args"]
        self.assertEqual(args[args.index("--hostname") + 1], "git.example.test")
        self.assertEqual(args[-1], "user")

    def test_list_projects_forwards_query_parameters(self):
        result = self.run_cli("list-projects", "--membership", "--limit", "5")
        self.assertEqual(result.returncode, 0, result.stderr)
        endpoint = self.api_calls()[0]["args"][-1]
        self.assertIn("membership=true", endpoint)
        self.assertIn("per_page=5", endpoint)
        self.assertNotIn("PRIVATE-TOKEN", self.api_calls()[0]["args"])

    def test_create_issue_sends_json_via_stdin(self):
        result = self.run_cli("create-issue", "--project", "group/demo", "--title", "New bug", "--description", "Reproduction", "--confirm")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["iid"], 8)
        call = self.api_calls()[0]
        self.assertEqual(call["args"][call["args"].index("--method") + 1], "POST")
        self.assertEqual(json.loads(call["stdin"])["description"], "Reproduction")

    def test_auto_selects_authenticated_glab(self):
        result = self.run_cli("config", backend="auto")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["backend"], "glab")

    def test_auto_falls_back_to_environment_authentication(self):
        self.env["MOCK_GLAB_AUTH"] = "1"
        self.env["GITLAB_TOKEN"] = "test-token"
        result = self.run_cli("config", backend="auto")
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads(result.stdout)
        self.assertEqual(config["backend"], "urllib")
        self.assertEqual(config["authentication"], "environment")
        self.assertNotIn("test-token", result.stdout)

    def test_forced_glab_requires_hostname_authentication(self):
        self.env["MOCK_GLAB_AUTH"] = "1"
        result = self.run_cli("config")
        self.assertEqual(result.returncode, 1)
        self.assertIn("glab auth login --hostname git.example.test", result.stderr)
        self.assertEqual(self.api_calls(), [])

    def test_glab_errors_are_compact_json(self):
        result = self.run_cli("get-project", "--project", "missing")
        self.assertEqual(result.returncode, 1)
        error = json.loads(result.stderr)
        self.assertIn("glab API request failed", error["error"])
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
