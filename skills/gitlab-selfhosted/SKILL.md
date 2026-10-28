---
name: gitlab-selfhosted
description: Use when the user asks about a self-hosted GitLab instance, especially git.euraika.net, including projects, repository files and branches, issues, merge requests, pipelines, or pipeline jobs. Supports a configurable GitLab URL and token-based API access.
---

# GitLab Self-Hosted

Use the bundled dependency-free Python client to work with GitLab API v4. The default instance is `https://git.euraika.net`.

## Configuration

- `GITLAB_URL`: optional base URL override. It defaults to `https://git.euraika.net`; the CLI also accepts `--url`.
- `GITLAB_TOKEN`: personal, project, or group access token. Keep it in the environment; never put it in command arguments, URLs, files, logs, or responses. Read-only work normally needs `read_api`; confirmed writes need `api`.
- `GITLAB_CA_BUNDLE`: optional path to a PEM CA bundle for a private certificate authority.
- `GITLAB_TIMEOUT`: optional request timeout in seconds; defaults to `20`.

If authentication fails, ask the user to configure `GITLAB_TOKEN`. Do not request that they paste the token into chat. To verify configuration without exposing the token, run `config`; use `whoami` to verify authentication.

## Running the client

Resolve `SCRIPT` to `scripts/gitlab_api.py` beside this SKILL.md, then invoke it with `python3`. The following examples document agent usage:

```bash
python3 "$SCRIPT" config
python3 "$SCRIPT" whoami
python3 "$SCRIPT" --url "https://git.example.com" list-projects --membership --limit 20
python3 "$SCRIPT" get-project --project "group/project"
python3 "$SCRIPT" list-branches --project "group/project"
python3 "$SCRIPT" list-tree --project "group/project" --path "src" --ref main
python3 "$SCRIPT" get-file --project "group/project" --file-path "README.md" --ref main
python3 "$SCRIPT" list-issues --project "group/project" --state opened
python3 "$SCRIPT" get-issue --project "group/project" --iid 42
python3 "$SCRIPT" list-merge-requests --project "group/project" --state opened
python3 "$SCRIPT" get-merge-request --project "group/project" --iid 17
python3 "$SCRIPT" list-pipelines --project "group/project" --ref main
python3 "$SCRIPT" get-pipeline --project "group/project" --pipeline-id 100
python3 "$SCRIPT" list-pipeline-jobs --project "group/project" --pipeline-id 100
```

A project can be its numeric ID or its full `group/project` path. Output is compact JSON with large descriptions truncated. List commands return at most 100 items and default to 20; ask before making additional requests for exhaustive history.

## Write safety

Creating issues or merge requests and retrying or canceling pipelines changes GitLab state. Before any such action, explain the exact project and change, then obtain explicit user confirmation. Only after confirmation, rerun the command with `--confirm`. Never infer confirmation for bulk, destructive, or ambiguous actions.

```bash
python3 "$SCRIPT" create-issue --project "group/project" --title "Bug title" --description "Details" --confirm
python3 "$SCRIPT" create-merge-request --project "group/project" --source-branch feature --target-branch main --title "Change title" --description "Details" --confirm
python3 "$SCRIPT" retry-pipeline --project "group/project" --pipeline-id 100 --confirm
python3 "$SCRIPT" cancel-pipeline --project "group/project" --pipeline-id 100 --confirm
```

## Response behavior

- Confirm the configured instance with `config` when the user mentions a different GitLab host or when connection behavior is unclear.
- Summarize results in natural language and include relevant GitLab `web_url` links.
- For repository analysis, fetch only the files needed rather than recursively downloading the repository.
- Report HTTP and TLS errors accurately; never claim an operation succeeded without successful JSON output.
