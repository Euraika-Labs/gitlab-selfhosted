#!/usr/bin/env python3
"""Validate and package the Kimi plugin using only the Python standard library."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def validate_plugin() -> tuple[str, str]:
    manifest_path = ROOT / "kimi.plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    name = manifest["name"]
    version = manifest["version"]
    if not name or not version:
        raise ValueError("Plugin name and version are required")
    if manifest.get("skills") != "./skills/":
        raise ValueError("Expected a directory-based skills component")

    skill = ROOT / "skills" / name / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    if not text.startswith("---\n") or f"name: {name}\n" not in text or "description:" not in text:
        raise ValueError(f"Invalid skill frontmatter: {skill}")
    if "TODO" in text:
        raise ValueError(f"Unresolved TODO in {skill}")

    for relative in ("kimi.plugin.json", "skills", "locales"):
        path = ROOT / relative
        if not path.exists():
            raise ValueError(f"Missing required plugin component: {relative}")
    return name, version


def package_files():
    for directory in ("skills", "locales"):
        for path in sorted((ROOT / directory).rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Symlinks are not allowed in the package: {path}")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}:
                yield path
    yield ROOT / "kimi.plugin.json"
    if (ROOT / "icon.svg").is_file():
        yield ROOT / "icon.svg"


def build() -> None:
    name, version = validate_plugin()
    DIST.mkdir(exist_ok=True)
    artifact = DIST / f"{name}-{version}.zip"
    with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in package_files():
            relative = path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())

    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    checksum = DIST / "SHA256SUMS"
    checksum.write_text(f"{digest}  {artifact.name}\n", encoding="utf-8")
    print(f"Built {artifact.relative_to(ROOT)}")
    print(f"SHA-256 {digest}")


if __name__ == "__main__":
    build()
