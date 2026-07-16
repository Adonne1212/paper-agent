import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def test_relative_markdown_links_exist() -> None:
    missing: list[str] = []
    for document in ROOT.rglob("*.md"):
        if any(part.startswith(".release-") for part in document.parts):
            continue
        text = document.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(text):
            clean = target.split("#", 1)[0].strip()
            if not clean or clean.startswith(("http://", "https://", "mailto:")):
                continue
            path = (document.parent / clean).resolve()
            if not path.exists():
                missing.append(f"{document.relative_to(ROOT)} -> {target}")
    assert not missing, "Missing local links:\n" + "\n".join(missing)
