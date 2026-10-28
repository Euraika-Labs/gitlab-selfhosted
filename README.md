# GitLab Self-Hosted for Kimi

A dependency-free Kimi plugin for working with self-hosted GitLab instances. It defaults to `https://git.euraika.net` and supports repositories, issues, merge requests, pipelines, and pipeline jobs through GitLab API v4.

## Features

- List and inspect projects, branches, repository trees, and text files.
- List, inspect, and create issues.
- List, inspect, and create merge requests, including drafts.
- List and inspect pipelines and jobs, or retry and cancel pipelines.
- Require explicit confirmation for every operation that changes GitLab state.
- Configure a custom GitLab URL, access token, request timeout, and CA bundle.
- Return compact JSON without exposing the access token.

## Installation

Download the versioned plugin ZIP from [GitHub Releases](https://github.com/Euraika-Labs/gitlab-selfhosted/releases), or send the public repository URL to Kimi's Plugin Builder to import it. After import, open **GitLab Self-Hosted** on the **Personal** tab and click **＋** to install. No client restart is required.

To propose the plugin for Kimi's official marketplace, the maintainer can open its personal-plugin details page, click **✉️**, select **Apply for official marketplace publication**, and submit contact details for Kimi's review team.

## Authentication and server selection

The recommended connection uses the [GitLab CLI](https://gitlab.com/gitlab-org/cli) with its operating-system credential store. Install `glab`, then authenticate once for your server:

```bash
glab auth login --hostname git.euraika.net
glab auth status --hostname git.euraika.net
```

The login flow asks for your GitLab URL and PAT as appropriate. Use `read_api` for read-only work or `api` for confirmed writes. No `GITLAB_TOKEN` environment variable is needed when `glab` is authenticated.

The client defaults to `https://git.euraika.net` and uses this order:

1. **`glab` backend:** used when `glab` is installed and authenticated for the selected hostname.
2. **Direct API fallback:** used when `glab` is unavailable or not authenticated. Configure `GITLAB_TOKEN` in Kimi Work's process environment.

| Variable | Required | Description |
| --- | --- | --- |
| `GITLAB_URL` | No | Selects the GitLab base URL for either backend. Defaults to `https://git.euraika.net`. |
| `GITLAB_TOKEN` | Fallback only | GitLab personal, project, or group access token for direct API access. |
| `GITLAB_BACKEND` | No | `auto` (default), `glab`, or `urllib` (direct API). |
| `GITLAB_CA_BUNDLE` | No | PEM CA bundle for direct API access. Setting this makes `auto` prefer the direct backend. |
| `GITLAB_TIMEOUT` | No | Request timeout in seconds. Defaults to `20`. |

Keep tokens in the environment or the `glab` credential store. Never place them in command arguments, URLs, source files, logs, or chat messages.

**The plugin details page does not provide PAT or server-URL input fields.** Authentication is handled by `glab` or the process environment instead. The direct fallback sends `GITLAB_TOKEN` in GitLab's `PRIVATE-TOKEN` header.

After installation and configuration, ask Kimi naturally, for example:

- “List my accessible GitLab projects.”
- “Show the open merge requests for group/my-project.”
- “Read README.md from the main branch.”
- “List the latest pipelines and their failed jobs.”

## Development

Python 3.9 or later is required. Runtime has no Python package dependencies; `glab` is optional but recommended. Tests and coverage use `requirements-dev.txt`.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m coverage run --source=skills -m unittest discover -s tests -v
.venv/bin/python -m coverage xml -o coverage.xml
python3 scripts/build_plugin.py
```

The build validates the manifest and bundled skills, then creates a versioned plugin ZIP and SHA-256 checksum under `dist/`.

## Repository layout

- `kimi.plugin.json` — Kimi plugin manifest.
- `skills/gitlab-selfhosted/SKILL.md` — agent workflow and safety instructions.
- `skills/gitlab-selfhosted/scripts/gitlab_api.py` — GitLab API client.
- `locales/` — localized marketplace copy.
- `tests/` — local mock-GitLab integration tests.
- `.github/workflows/build.yml` — CI test and package build.

## Community

- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Contributing guide](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Changelog](CHANGELOG.md)

## License

[MIT](LICENSE)
