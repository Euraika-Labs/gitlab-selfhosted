## Summary

Describe the change and link any related issue.

## Verification

Describe the tests and build checks performed, including their results.

## Impact and risk

Note any changes to authentication, GitLab write operations, configuration, packaging, or backwards compatibility.

## Checklist

- [ ] I have followed the Code of Conduct and contributing guide.
- [ ] I have added or updated tests for behavior changes.
- [ ] I have updated relevant documentation and localized copy.
- [ ] `python3 -m unittest discover -s tests -v` passes.
- [ ] `python3 scripts/build_plugin.py` succeeds.
- [ ] This change contains no tokens, private data, generated build artifacts, or unrelated changes.
- [ ] GitLab write operations still require explicit user confirmation.
