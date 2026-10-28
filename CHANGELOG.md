# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-10-28

### Added

- Primary GitLab API access through an authenticated `glab` CLI and its operating-system credential store.
- Automatic fallback to direct API access with `GITLAB_TOKEN` when `glab` is unavailable or not authenticated for the selected host.
- `GITLAB_BACKEND` and `--backend` overrides for `auto`, `glab`, and `urllib` modes.
- Non-secret backend diagnostics and isolated tests for glab authentication, host selection, JSON request bodies, and fallback behavior.
- User and contributor documentation for glab installation, login, server selection, and fallback configuration.

### Verified

- Thirty mock-backed integration tests pass with 55% runtime coverage.
- Live read-only authentication and project retrieval succeed against `https://git.euraika.net` using the existing glab Keychain login.

## [0.1.1] - 2026-10-28

### Added

- Official GitLab logomark for the plugin details page and install package.
- Cobertura coverage reporting through GitHub Code Quality.
- Pull-request thresholds for code quality and coverage.

### Changed

- Clarified non-JSON GitLab error handling.
- Updated GitHub Actions to Node.js 24 and Ubuntu 24.04.
- Documented environment-based PAT and GitLab URL configuration.

## [0.1.0] - 2026-10-28

### Added

- Configurable GitLab API v4 access, defaulting to `https://git.euraika.net`.
- Project, branch, repository tree, and text-file operations.
- Issue and merge-request listing, details, and confirmed creation.
- Pipeline and job listing, pipeline details, and confirmed retry or cancellation.
- Environment-based token handling, optional custom CA bundles, compact JSON output, and write-operation safeguards.
- English and Simplified Chinese marketplace metadata.
- Mock-GitLab integration tests and reproducible ZIP packaging with SHA-256 checksums.
- GitHub Actions test and build workflow.

[0.2.0]: https://github.com/Euraika-Labs/gitlab-selfhosted/releases/tag/v0.2.0
[0.1.1]: https://github.com/Euraika-Labs/gitlab-selfhosted/releases/tag/v0.1.1
[0.1.0]: https://github.com/Euraika-Labs/gitlab-selfhosted/releases/tag/v0.1.0
