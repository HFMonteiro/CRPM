from __future__ import annotations

import re
from pathlib import Path

from crpm.pages import PAGE_REGISTRY

ROOT = Path(__file__).resolve().parents[1]


def test_readme_screenshot_paths_exist() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    screenshot_paths = re.findall(r"\]\((docs/screenshots/[^)]+)\)", readme)

    assert screenshot_paths
    for relative_path in screenshot_paths:
        assert (ROOT / relative_path).is_file(), relative_path


def test_readme_mentions_canonical_page_names() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for page_name in PAGE_REGISTRY:
        assert page_name in readme


def test_agents_md_stays_local_only() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert re.search(r"(?m)^AGENTS\.md$", gitignore)
