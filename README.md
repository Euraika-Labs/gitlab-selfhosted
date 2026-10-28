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

## Configuration

| Variable | Required | Description |
| --- | --- | --- |
| `GITLAB_URL` | No | GitLab base URL. Defaults to `https://git.euraika.net`. |
| `GITLAB_TOKEN` | For private data | GitLab personal, project, or group access token. Use `read_api` for read-only access or `api` for confirmed writes. |
| `GITLAB_CA_BUNDLE` | No | Path to a PEM CA bundle for a private certificate authority. |
| `GITLAB_TIMEOUT` | No | Request timeout in seconds. Defaults to `20`. |

Keep tokens in the environment. Never place them in command arguments, URLs, source files, logs, or chat messages.

After installation and configuration, ask Kimi naturally, for example:

- “List my accessible GitLab projects.”
- “Show the open merge requests for group/my-project.”
- “Read README.md from the main branch.”
- “List the latest pipelines and their failed jobs.”

## Development

Requires Python 3.9 or later; the client and tests use only the Python standard library.

```bash
python3 -m unittest discover -s tests -v
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
