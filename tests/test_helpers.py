#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "gitlab-selfhosted" / "scripts" / "gitlab_api.py"
SPEC = importlib.util.spec_from_file_location("gitlab_api_helpers", SCRIPT)
gitlab_api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gitlab_api)


class HelperTests(unittest.TestCase):
    def test_project_summary_detailed(self):
        result = gitlab_api.project_summary({
            "id": 42,
            "name": "Demo",
            "description": "Project description",
            "http_url_to_repo": "https://git.example/group/demo.git",
            "open_issues_count": 3,
        }, detailed=True)
        self.assertEqual(result["id"], 42)
        self.assertEqual(result["open_issues_count"], 3)
        self.assertIn("http_url_to_repo", result)

    def test_issue_summary_nested_fields(self):
        result = gitlab_api.issue_summary({
            "iid": 7,
            "title": "Bug",
            "description": "Details",
            "author": {"id": 1, "username": "bert"},
            "assignees": [{"id": 2, "username": "reviewer"}],
            "milestone": {"id": 3, "title": "v1", "state": "active"},
        }, detailed=True)
        self.assertEqual(result["author"]["username"], "bert")
        self.assertEqual(result["assignees"][0]["id"], 2)
        self.assertEqual(result["milestone"]["title"], "v1")

    def test_merge_request_summary_nested_fields(self):
        result = gitlab_api.merge_request_summary({
            "iid": 9,
            "description": "Improvement",
            "author": {"id": 1, "username": "bert"},
            "assignees": [{"id": 2, "username": "assignee"}],
            "reviewers": [{"id": 3, "username": "reviewer"}],
            "merged_by": {"id": 4, "username": "maintainer"},
        }, detailed=True)
        self.assertEqual(result["reviewers"][0]["username"], "reviewer")
        self.assertEqual(result["merged_by"]["username"], "maintainer")
        self.assertEqual(result["description"], "Improvement")

    def test_pipeline_and_job_summaries(self):
        pipeline = gitlab_api.pipeline_summary({"id": 10, "status": "success", "user": {"id": 1, "username": "bert"}}, detailed=True)
        job = gitlab_api.job_summary({"id": 11, "name": "test", "user": {"id": 1, "username": "bert"}})
        self.assertEqual(pipeline["user"]["username"], "bert")
        self.assertEqual(job["user"]["username"], "bert")

    def test_truncate_behavior(self):
        self.assertEqual(gitlab_api.truncate("short"), "short")
        result = gitlab_api.truncate("abcdefgh", maximum=4)
        self.assertTrue(result.startswith("abcd"))
        self.assertIn("truncated 4 characters", result)

    def test_project_ref_encodes_full_path(self):
        self.assertEqual(gitlab_api.project_ref("group/demo"), "group%2Fdemo")

    def test_confirmation_guard(self):
        class Args:
            confirm = False
        with self.assertRaises(gitlab_api.GitLabError):
            gitlab_api.require_confirmation(Args())
        Args.confirm = True
        self.assertIsNone(gitlab_api.require_confirmation(Args()))

    def test_custom_ca_prefers_direct_backend(self):
        client = gitlab_api.GitLabClient("https://git.example.test", None, ca_bundle=gitlab_api.ssl.get_default_verify_paths().cafile, backend="auto")
        self.assertEqual(client.backend, "urllib")

    def test_default_backend_is_auto(self):
        args = gitlab_api.build_parser().parse_args(["config"])
        self.assertEqual(args.backend, "auto")


if __name__ == "__main__":
    unittest.main()
