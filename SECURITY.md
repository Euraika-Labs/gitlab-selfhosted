# Security Policy

## Supported Versions

| Version | Supported |
| --- | --- |
| 0.1.x | Yes |
| Earlier versions | No |

Security fixes are applied to the latest release on `main` and released as appropriate.

## Reporting a Vulnerability

Do not disclose suspected vulnerabilities in public issues or pull requests. Contact the Euraika-Labs maintainers through the private contact options on the [Euraika-Labs GitHub organization profile](https://github.com/Euraika-Labs), or use GitHub's private vulnerability reporting if it is available on this repository.

Include:

- The affected version and operating environment.
- A concise description of the impact.
- Reproduction steps using non-sensitive mock data.
- Any proposed mitigation, if known.

Remove GitLab tokens, cookies, private repository data, and personal information from all reports. Maintainers will acknowledge reports as soon as practical, assess severity, coordinate a fix, and keep reporters informed of release and disclosure plans.

## Credential Safety

This plugin reads `GITLAB_TOKEN` from the process environment and sends it only to the configured GitLab API endpoint in the `PRIVATE-TOKEN` header. Users should grant the minimum necessary token scope, use `read_api` where possible, rotate exposed tokens immediately, and avoid untrusted GitLab base URLs.
