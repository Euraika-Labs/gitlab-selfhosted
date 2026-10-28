#!/usr/bin/env python3
import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PLUGIN_ROOT / "skills" / "gitlab-selfhosted" / "scripts" / "gitlab_api.py"
SPEC = importlib.util.spec_from_file_location("gitlab_api", SCRIPT)
gitlab_api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gitlab_api)


class MockGitLabHandler(BaseHTTPRequestHandler):
    requests = []

    def log_message(self, *_args):
        pass

    def send_json(self, value, status=200):
        body = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def record(self, payload=None):
        type(self).requests.append({
            "method": self.command,
            "path": self.path,
            "token": self.headers.get("PRIVATE-TOKEN"),
            "payload": payload,
        })

    def do_GET(self):
        self.record()
        if self.path.startswith("/api/v4/projects?"):
            self.send_json([{"id": 42, "name": "Demo", "path_with_namespace": "group/demo", "web_url": "https://git.example/group/demo", "extra": "omitted"}])
        elif self.path.startswith("/api/v4/projects/group%2Fdemo/issues/7"):
            self.send_json({"id": 70, "iid": 7, "title": "A bug", "state": "opened", "description": "Details", "author": {"id": 1, "username": "bert", "extra": "omitted"}})
        elif self.path.startswith("/api/v4/projects/42/repository/files/README.md?"):
            self.send_json({"file_name": "README.md", "file_path": "README.md", "ref": "main", "content": base64.b64encode("Hello GitLab\n".encode()).decode()})
        elif self.path.startswith("/api/v4/projects/42/pipelines?"):
            self.send_json([{"id": 99, "iid": 4, "status": "success", "ref": "main", "web_url": "https://git.example/pipelines/99"}])
        else:
            self.send_json({"message": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        self.record(payload)
        if self.path == "/api/v4/projects/group%2Fdemo/issues":
            self.send_json({"id": 71, "iid": 8, "title": payload["title"], "description": payload["description"], "state": "opened"}, 201)
        elif self.path == "/api/v4/projects/group%2Fdemo/merge_requests":
            self.send_json({"id": 81, "iid": 3, "title": payload["title"], "state": "opened", "source_branch": payload["source_branch"], "target_branch": payload["target_branch"]}, 201)
        elif self.path == "/api/v4/projects/42/pipelines/99/retry":
            self.send_json({"id": 100, "status": "running", "ref": "main"}, 201)
        else:
            self.send_json({"message": "not found"}, 404)


class GitLabCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MockGitLabHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=5)
        cls.server.server_close()

    def setUp(self):
        MockGitLabHandler.requests = []

    def run_cli(self, *args, token="test-token"):
        env = os.environ.copy()
        if token is None:
            env.pop("GITLAB_TOKEN", None)
        else:
            env["GITLAB_TOKEN"] = token
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--url", self.url, *args],
            text=True,
            capture_output=True,
            env=env,
            timeout=10,
            check=False,
        )

    def test_config_uses_requested_url_without_exposing_token(self):
        result = self.run_cli("config")
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads(result.stdout)
        self.assertEqual(config["gitlab_url"], self.url)
        self.assertTrue(config["token_configured"])
        self.assertNotIn("test-token", result.stdout)

    def test_list_projects_sends_token_and_compacts_results(self):
        result = self.run_cli("list-projects", "--membership", "--limit", "5")
        self.assertEqual(result.returncode, 0, result.stderr)
        projects = json.loads(result.stdout)
        self.assertEqual(projects[0]["path_with_namespace"], "group/demo")
        self.assertNotIn("extra", projects[0])
        request = MockGitLabHandler.requests[0]
        self.assertEqual(request["token"], "test-token")
        self.assertIn("membership=true", request["path"])
        self.assertIn("per_page=5", request["path"])

    def test_project_path_is_url_encoded(self):
        result = self.run_cli("get-issue", "--project", "group/demo", "--iid", "7")
        self.assertEqual(result.returncode, 0, result.stderr)
        issue = json.loads(result.stdout)
        self.assertEqual(issue["iid"], 7)
        self.assertEqual(issue["author"]["username"], "bert")
        self.assertNotIn("extra", issue["author"])
        self.assertIn("/projects/group%2Fdemo/issues/7", MockGitLabHandler.requests[0]["path"])

    def test_repository_file_is_decoded(self):
        result = self.run_cli("get-file", "--project", "42", "--file-path", "README.md", "--ref", "main")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["content"], "Hello GitLab\n")

    def test_pipelines_can_be_filtered(self):
        result = self.run_cli("list-pipelines", "--project", "42", "--ref", "main", "--status", "success")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)[0]["id"], 99)
        path = MockGitLabHandler.requests[0]["path"]
        self.assertIn("ref=main", path)
        self.assertIn("status=success", path)

    def test_create_issue_requires_confirmation(self):
        result = self.run_cli("create-issue", "--project", "group/demo", "--title", "New bug")
        self.assertEqual(result.returncode, 1)
        self.assertIn("confirm", result.stderr)
        self.assertEqual(MockGitLabHandler.requests, [])

    def test_confirmed_create_issue_posts_json(self):
        result = self.run_cli("create-issue", "--project", "group/demo", "--title", "New bug", "--description", "Reproduction", "--confirm")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["iid"], 8)
        request = MockGitLabHandler.requests[0]
        self.assertEqual(request["method"], "POST")
        self.assertEqual(request["payload"]["description"], "Reproduction")

    def test_draft_merge_request_title(self):
        result = self.run_cli("create-merge-request", "--project", "group/demo", "--source-branch", "feature", "--target-branch", "main", "--title", "Add feature", "--draft", "--confirm")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(MockGitLabHandler.requests[0]["payload"]["title"], "Draft: Add feature")

    def test_retry_pipeline_requires_confirmation(self):
        result = self.run_cli("retry-pipeline", "--project", "42", "--pipeline-id", "99")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(MockGitLabHandler.requests, [])

    def test_confirmed_retry_pipeline(self):
        result = self.run_cli("retry-pipeline", "--project", "42", "--pipeline-id", "99", "--confirm")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "running")

    def test_http_errors_are_compact_json(self):
        result = self.run_cli("get-project", "--project", "missing")
        self.assertEqual(result.returncode, 1)
        error = json.loads(result.stderr)
        self.assertIn("HTTP 404", error["error"])
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_url_returns_json_error(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--url", "not-a-url", "config"],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("absolute", json.loads(result.stderr)["error"])
        self.assertNotIn("Traceback", result.stderr)

    def test_default_url_is_euraika(self):
        parser = gitlab_api.build_parser()
        args = parser.parse_args(["config"])
        self.assertEqual(args.url, "https://git.euraika.net")


if __name__ == "__main__":
    unittest.main()
