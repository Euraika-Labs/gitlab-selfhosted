#!/usr/bin/env python3
"""Small, dependency-free GitLab API v4 client for Kimi."""

from __future__ import annotations

import argparse
import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_GITLAB_URL = "https://git.euraika.net"
MAX_BODY_CHARS = 12_000


class GitLabError(RuntimeError):
    pass


def pick(data: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: data[field] for field in fields if field in data}


def person(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not data:
        return None
    return pick(data, ("id", "username", "name", "web_url"))


def people(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return [person(item) for item in (items or []) if item]


def project_summary(data: dict[str, Any], detailed: bool = False) -> dict[str, Any]:
    fields = [
        "id", "name", "path", "path_with_namespace", "description", "web_url",
        "default_branch", "visibility", "archived", "empty_repo", "last_activity_at",
    ]
    if detailed:
        fields.extend(("http_url_to_repo", "ssh_url_to_repo", "open_issues_count", "created_at"))
    result = pick(data, tuple(fields))
    if isinstance(result.get("description"), str):
        result["description"] = truncate(result["description"])
    return result


def issue_summary(data: dict[str, Any], detailed: bool = False) -> dict[str, Any]:
    fields = [
        "id", "iid", "title", "state", "web_url", "labels", "milestone",
        "created_at", "updated_at", "closed_at", "due_date", "user_notes_count",
    ]
    if detailed:
        fields.extend(("description", "confidential", "discussion_locked", "task_completion_status"))
    result = pick(data, tuple(fields))
    result["author"] = person(data.get("author"))
    result["assignees"] = people(data.get("assignees"))
    if isinstance(result.get("milestone"), dict):
        result["milestone"] = pick(result["milestone"], ("id", "iid", "title", "due_date", "state"))
    if isinstance(result.get("description"), str):
        result["description"] = truncate(result["description"])
    return result


def merge_request_summary(data: dict[str, Any], detailed: bool = False) -> dict[str, Any]:
    fields = [
        "id", "iid", "title", "state", "draft", "web_url", "source_branch",
        "target_branch", "labels", "merge_status", "detailed_merge_status",
        "has_conflicts", "blocking_discussions_resolved", "user_notes_count",
        "created_at", "updated_at", "merged_at", "closed_at",
    ]
    if detailed:
        fields.extend(("description", "sha", "merge_commit_sha", "squash_commit_sha"))
    result = pick(data, tuple(fields))
    result["author"] = person(data.get("author"))
    result["assignees"] = people(data.get("assignees"))
    result["reviewers"] = people(data.get("reviewers"))
    result["merged_by"] = person(data.get("merged_by"))
    if isinstance(result.get("description"), str):
        result["description"] = truncate(result["description"])
    return result


def pipeline_summary(data: dict[str, Any], detailed: bool = False) -> dict[str, Any]:
    fields = [
        "id", "iid", "project_id", "status", "source", "ref", "sha", "web_url",
        "created_at", "updated_at",
    ]
    if detailed:
        fields.extend(("before_sha", "tag", "yaml_errors", "started_at", "finished_at", "duration", "queued_duration"))
    result = pick(data, tuple(fields))
    if detailed:
        result["user"] = person(data.get("user"))
    return result


def job_summary(data: dict[str, Any]) -> dict[str, Any]:
    result = pick(data, (
        "id", "name", "stage", "status", "ref", "tag", "allow_failure", "web_url",
        "created_at", "started_at", "finished_at", "duration", "queued_duration",
    ))
    result["user"] = person(data.get("user"))
    return result


def truncate(value: str, maximum: int = MAX_BODY_CHARS) -> str:
    if len(value) <= maximum:
        return value
    return value[:maximum] + f"\n… [truncated {len(value) - maximum} characters]"


def project_ref(project: str | int) -> str:
    return urllib.parse.quote(str(project), safe="")


class GitLabClient:
    def __init__(self, base_url: str, token: str | None, timeout: float = 20.0, ca_bundle: str | None = None):
        base_url = base_url.strip().rstrip("/")
        parsed = urllib.parse.urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise GitLabError("GitLab URL must be an absolute http:// or https:// URL.")
        if parsed.username or parsed.password:
            raise GitLabError("Do not put credentials in the GitLab URL; use GITLAB_TOKEN instead.")
        self.base_url = base_url
        self.token = token
        self.timeout = timeout
        self.ssl_context = ssl.create_default_context(cafile=ca_bundle) if ca_bundle else None

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        query = ""
        if params:
            clean_params = {key: value for key, value in params.items() if value is not None}
            query = "?" + urllib.parse.urlencode(clean_params, doseq=True)
        url = f"{self.base_url}/api/v4/{path.lstrip('/')}{query}"
        headers = {"Accept": "application/json", "User-Agent": "kimi-gitlab-selfhosted/0.1"}
        if self.token:
            headers["PRIVATE-TOKEN"] = self.token
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout, context=self.ssl_context) as response:
                raw = response.read()
                if not raw:
                    return None
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")
            detail = raw
            try:
                parsed = json.loads(raw)
                detail = parsed.get("message") or parsed.get("error") or raw
            except (json.JSONDecodeError, AttributeError):
                pass
            raise GitLabError(f"GitLab returned HTTP {error.code}: {truncate(str(detail), 2_000)}") from None
        except urllib.error.URLError as error:
            raise GitLabError(f"Could not reach GitLab: {error.reason}") from None
        except TimeoutError:
            raise GitLabError(f"GitLab request timed out after {self.timeout:g} seconds.") from None
        except json.JSONDecodeError:
            raise GitLabError("GitLab returned a response that was not valid JSON.") from None


def add_project_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", required=True, help="Numeric project ID or full group/project path")


def add_limit_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--limit", type=int, default=20, help="Results to return, 1–100 (default: 20)")


def require_confirmation(args: argparse.Namespace) -> None:
    if not args.confirm:
        raise GitLabError("This action changes GitLab data. Ask the user to confirm, then rerun with --confirm.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("GITLAB_URL", DEFAULT_GITLAB_URL), help="GitLab base URL; defaults to GITLAB_URL or https://git.euraika.net")
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("GITLAB_TIMEOUT", "20")), help="Request timeout in seconds")
    parser.add_argument("--ca-bundle", default=os.environ.get("GITLAB_CA_BUNDLE"), help="Optional custom CA certificate bundle; defaults to GITLAB_CA_BUNDLE")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("config", help="Show non-secret connection configuration")
    subparsers.add_parser("whoami", help="Show the authenticated GitLab user")

    command = subparsers.add_parser("list-projects", help="List accessible projects")
    command.add_argument("--search")
    command.add_argument("--membership", action="store_true", help="Only projects the current user belongs to")
    add_limit_argument(command)

    command = subparsers.add_parser("get-project", help="Get one project")
    add_project_argument(command)

    command = subparsers.add_parser("list-branches", help="List repository branches")
    add_project_argument(command)
    command.add_argument("--search")
    add_limit_argument(command)

    command = subparsers.add_parser("list-tree", help="List files and directories in a repository")
    add_project_argument(command)
    command.add_argument("--path", default="", help="Directory path inside the repository")
    command.add_argument("--ref", help="Branch, tag, or commit SHA")
    command.add_argument("--recursive", action="store_true")
    add_limit_argument(command)

    command = subparsers.add_parser("get-file", help="Read a text file from a repository")
    add_project_argument(command)
    command.add_argument("--file-path", required=True)
    command.add_argument("--ref", required=True, help="Branch, tag, or commit SHA")
    command.add_argument("--max-chars", type=int, default=20_000)

    command = subparsers.add_parser("list-issues", help="List project issues")
    add_project_argument(command)
    command.add_argument("--state", choices=("opened", "closed", "all"), default="opened")
    command.add_argument("--search")
    command.add_argument("--labels", help="Comma-separated label names")
    add_limit_argument(command)

    command = subparsers.add_parser("get-issue", help="Get one project issue")
    add_project_argument(command)
    command.add_argument("--iid", required=True, type=int)

    command = subparsers.add_parser("create-issue", help="Create an issue; requires explicit confirmation")
    add_project_argument(command)
    command.add_argument("--title", required=True)
    command.add_argument("--description", default="")
    command.add_argument("--labels")
    command.add_argument("--assignee-id", type=int)
    command.add_argument("--confirm", action="store_true")

    command = subparsers.add_parser("list-merge-requests", help="List project merge requests")
    add_project_argument(command)
    command.add_argument("--state", choices=("opened", "closed", "merged", "all"), default="opened")
    command.add_argument("--search")
    command.add_argument("--source-branch")
    command.add_argument("--target-branch")
    add_limit_argument(command)

    command = subparsers.add_parser("get-merge-request", help="Get one merge request")
    add_project_argument(command)
    command.add_argument("--iid", required=True, type=int)

    command = subparsers.add_parser("create-merge-request", help="Create a merge request; requires explicit confirmation")
    add_project_argument(command)
    command.add_argument("--source-branch", required=True)
    command.add_argument("--target-branch", required=True)
    command.add_argument("--title", required=True)
    command.add_argument("--description", default="")
    command.add_argument("--draft", action="store_true")
    command.add_argument("--confirm", action="store_true")

    command = subparsers.add_parser("list-pipelines", help="List project pipelines")
    add_project_argument(command)
    command.add_argument("--ref")
    command.add_argument("--status", choices=("created", "waiting_for_resource", "preparing", "pending", "running", "success", "failed", "canceled", "skipped", "manual", "scheduled"))
    add_limit_argument(command)

    command = subparsers.add_parser("get-pipeline", help="Get one pipeline")
    add_project_argument(command)
    command.add_argument("--pipeline-id", required=True, type=int)

    command = subparsers.add_parser("list-pipeline-jobs", help="List jobs in a pipeline")
    add_project_argument(command)
    command.add_argument("--pipeline-id", required=True, type=int)
    add_limit_argument(command)

    for name, help_text in (("retry-pipeline", "Retry a pipeline"), ("cancel-pipeline", "Cancel a pipeline")):
        command = subparsers.add_parser(name, help=f"{help_text}; requires explicit confirmation")
        add_project_argument(command)
        command.add_argument("--pipeline-id", required=True, type=int)
        command.add_argument("--confirm", action="store_true")

    return parser


def execute(args: argparse.Namespace, client: GitLabClient) -> Any:
    command = args.command
    if command == "config":
        return {
            "gitlab_url": client.base_url,
            "api_base": f"{client.base_url}/api/v4",
            "token_configured": bool(client.token),
            "custom_ca_bundle": bool(args.ca_bundle),
        }
    if command == "whoami":
        return pick(client.request("GET", "user"), ("id", "username", "name", "state", "web_url", "is_admin"))
    if command == "list-projects":
        data = client.request("GET", "projects", {"search": args.search, "membership": str(args.membership).lower(), "simple": "true", "per_page": args.limit})
        return [project_summary(item) for item in data]
    if command == "get-project":
        return project_summary(client.request("GET", f"projects/{project_ref(args.project)}"), detailed=True)

    project = project_ref(args.project) if hasattr(args, "project") else None

    if command == "list-branches":
        data = client.request("GET", f"projects/{project}/repository/branches", {"search": args.search, "per_page": args.limit})
        return [pick(item, ("name", "merged", "protected", "default", "web_url")) for item in data]
    if command == "list-tree":
        data = client.request("GET", f"projects/{project}/repository/tree", {"path": args.path, "ref": args.ref, "recursive": str(args.recursive).lower(), "per_page": args.limit})
        return [pick(item, ("id", "name", "type", "path", "mode")) for item in data]
    if command == "get-file":
        encoded_path = urllib.parse.quote(args.file_path, safe="")
        data = client.request("GET", f"projects/{project}/repository/files/{encoded_path}", {"ref": args.ref})
        result = pick(data, ("file_name", "file_path", "size", "encoding", "ref", "blob_id", "commit_id", "last_commit_id"))
        try:
            content = base64.b64decode(data["content"]).decode("utf-8")
            result["content"] = truncate(content, args.max_chars)
        except (KeyError, ValueError, UnicodeDecodeError) as error:
            raise GitLabError(f"Could not decode repository file as UTF-8 text: {error}") from None
        return result
    if command == "list-issues":
        data = client.request("GET", f"projects/{project}/issues", {"state": args.state, "search": args.search, "labels": args.labels, "per_page": args.limit})
        return [issue_summary(item) for item in data]
    if command == "get-issue":
        return issue_summary(client.request("GET", f"projects/{project}/issues/{args.iid}"), detailed=True)
    if command == "create-issue":
        require_confirmation(args)
        payload = {"title": args.title, "description": args.description, "labels": args.labels, "assignee_id": args.assignee_id}
        payload = {key: value for key, value in payload.items() if value is not None}
        return issue_summary(client.request("POST", f"projects/{project}/issues", payload=payload), detailed=True)
    if command == "list-merge-requests":
        data = client.request("GET", f"projects/{project}/merge_requests", {"state": args.state, "search": args.search, "source_branch": args.source_branch, "target_branch": args.target_branch, "per_page": args.limit})
        return [merge_request_summary(item) for item in data]
    if command == "get-merge-request":
        return merge_request_summary(client.request("GET", f"projects/{project}/merge_requests/{args.iid}"), detailed=True)
    if command == "create-merge-request":
        require_confirmation(args)
        title = f"Draft: {args.title}" if args.draft and not args.title.startswith(("Draft:", "draft:")) else args.title
        payload = {"source_branch": args.source_branch, "target_branch": args.target_branch, "title": title, "description": args.description}
        return merge_request_summary(client.request("POST", f"projects/{project}/merge_requests", payload=payload), detailed=True)
    if command == "list-pipelines":
        data = client.request("GET", f"projects/{project}/pipelines", {"ref": args.ref, "status": args.status, "per_page": args.limit})
        return [pipeline_summary(item) for item in data]
    if command == "get-pipeline":
        return pipeline_summary(client.request("GET", f"projects/{project}/pipelines/{args.pipeline_id}"), detailed=True)
    if command == "list-pipeline-jobs":
        data = client.request("GET", f"projects/{project}/pipelines/{args.pipeline_id}/jobs", {"per_page": args.limit})
        return [job_summary(item) for item in data]
    if command in {"retry-pipeline", "cancel-pipeline"}:
        require_confirmation(args)
        action = "retry" if command == "retry-pipeline" else "cancel"
        return pipeline_summary(client.request("POST", f"projects/{project}/pipelines/{args.pipeline_id}/{action}"), detailed=True)
    raise GitLabError(f"Unsupported command: {command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "limit") and not 1 <= args.limit <= 100:
        parser.error("--limit must be between 1 and 100")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    try:
        client = GitLabClient(args.url, os.environ.get("GITLAB_TOKEN"), args.timeout, args.ca_bundle)
        result = execute(args, client)
    except GitLabError as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
