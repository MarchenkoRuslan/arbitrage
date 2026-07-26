from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def iter_markdown_files() -> list[Path]:
    files = list(ROOT.glob("**/*.md"))
    # Skip package metadata if generated in editable installs.
    return [p for p in files if "arbitrage.egg-info" not in p.parts]


def github_anchor_slug(raw_heading: str) -> str:
    heading = raw_heading.strip().lower()
    heading = re.sub(r"`", "", heading)
    heading = re.sub(r"[^\w\- ]", "", heading)
    heading = re.sub(r"\s+", "-", heading)
    heading = re.sub(r"-+", "-", heading)
    return heading.strip("-")


def extract_anchors(md_file: Path) -> set[str]:
    text = md_file.read_text(encoding="utf-8")
    anchors: set[str] = set()
    in_fence = False

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        match = HEADING_RE.match(stripped)
        if not match:
            continue

        heading_text = match.group(2)
        # Drop optional closing ATX markers: "## Title ##".
        heading_text = re.sub(r"\s+#+\s*$", "", heading_text).strip()
        slug = github_anchor_slug(heading_text)
        if slug:
            anchors.add(slug)

    return anchors


def should_skip_target(target: str) -> bool:
    lowered = target.lower()
    return lowered.startswith(("http://", "https://", "mailto:", "tel:"))


def normalize_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    # Drop optional title, e.g. path "Title".
    if " " in target and not target.startswith("#"):
        first, *_ = target.split(" ", 1)
        target = first
    return target


def check_file_links(md_file: Path, anchor_map: dict[Path, set[str]]) -> list[str]:
    errors: list[str] = []
    text = md_file.read_text(encoding="utf-8")
    lines = text.splitlines()

    for idx, line in enumerate(lines, start=1):
        for match in LINK_RE.finditer(line):
            target = normalize_target(match.group(1))
            if not target or should_skip_target(target):
                continue

            path_part, _, fragment = target.partition("#")
            if path_part:
                resolved = (md_file.parent / unquote(path_part)).resolve()
            else:
                resolved = md_file.resolve()

            if not resolved.exists():
                rel_md = md_file.relative_to(ROOT).as_posix()
                errors.append(f"{rel_md}:{idx} -> missing target: {target}")
                continue

            if fragment and resolved.suffix.lower() == ".md":
                decoded_fragment = unquote(fragment).strip().lower()
                anchors = anchor_map.get(resolved, set())
                if decoded_fragment not in anchors:
                    rel_md = md_file.relative_to(ROOT).as_posix()
                    rel_target = resolved.relative_to(ROOT).as_posix()
                    errors.append(
                        f"{rel_md}:{idx} -> missing anchor '#{decoded_fragment}' in {rel_target}"
                    )

    return errors


def main() -> int:
    markdown_files = iter_markdown_files()
    anchor_map = {md.resolve(): extract_anchors(md) for md in markdown_files}

    all_errors: list[str] = []
    for md_file in markdown_files:
        all_errors.extend(check_file_links(md_file, anchor_map))

    if all_errors:
        print("Broken markdown links found:")
        for err in all_errors:
            print(f"- {err}")
        return 1

    print("Markdown link check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

