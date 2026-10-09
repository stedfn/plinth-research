#!/usr/bin/env python3
"""Focused structural checker for the Plinth v0.3 two-mode Trust Center."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path


PANEL_ROLE_ORDER = [
    "control",
    "backing",
    "economics",
    "governance-compliance",
    "continuity",
    "claim-structure",
    "legal-structure",
    "quantity-boundaries",
    "gaps",
    "requests",
    "sources",
    "technical-state",
    "methodology",
    "technical-appendix",
]
PILLAR_ROLES = PANEL_ROLE_ORDER[:5]
PANEL_HEADING_ROLES = {
    "pillar-control": "control",
    "pillar-reserves": "backing",
    "pillar-economics": "economics",
    "pillar-governance-compliance": "governance-compliance",
    "pillar-continuity": "continuity",
    "chain-of-title": "claim-structure",
    "legal-structure": "legal-structure",
    "supply-by-chain": "quantity-boundaries",
    "gaps-title": "gaps",
    "requests-title": "requests",
    "sources-title": "sources",
    "changes-title": "technical-state",
    "methodology-title": "methodology",
    "technical-appendix": "technical-appendix",
}
PILLAR_ALIASES = {
    "control": "control",
    "backing": "backing",
    "economics": "economics",
    "governance": "gov",
    "governance-compliance": "gov",
    "continuity": "continuity",
}
REQUIRED_IDS = {
    "v3-executive", "executive", "v3-analyst", "analyst-main",
    "pillar-control", "pillar-reserves", "pillar-economics",
    "pillar-governance-compliance", "pillar-continuity", "chain-of-title",
    "gaps-title", "sources-title", "methodology-title", "technical-appendix",
    "plinth-research-state",
}
REQUIRED_CLASSES = {
    "v3-top", "mode-tabs", "v3-view", "executive-main", "exec-block",
    "facts", "claim-track", "service-branch", "flow", "pill",
    "framework-strip", "open-groups", "analyst-layout", "analyst-sidebar",
    "mobile-analyst-nav", "analyst-main", "panel", "evidence-boundary-pair",
    "pillar-checks", "record", "ai-dock",
}
V03_THEME_VARS = {
    "cream", "cream-2", "panel", "ink", "ink-2", "ink-3", "muted",
    "hint", "line", "line-2", "green", "green-soft", "amber",
    "amber-soft", "rust", "rust-soft", "blue", "blue-soft", "violet",
    "violet-soft", "top-h",
}


def fail(message: str) -> None:
    raise AssertionError(message)


@dataclass
class Element:
    tag: str
    attrs: dict[str, str]
    parent: "Element | None" = None
    children: list["Element"] = field(default_factory=list)
    text: list[str] = field(default_factory=list)


VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


def classes(element: Element) -> set[str]:
    return set(element.attrs.get("class", "").split())


def walk(element: Element):
    for child in element.children:
        yield child
        yield from walk(child)


def descendants_with_class(element: Element, class_name: str) -> list[Element]:
    return [child for child in walk(element) if class_name in classes(child)]


def visible_text(element: Element) -> str:
    if element.tag in {"script", "style", "noscript", "template"}:
        return ""
    parts = list(element.text)
    for child in element.children:
        parts.append(visible_text(child))
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def collect_sources(value: object) -> list[dict]:
    found: list[dict] = []
    if isinstance(value, dict):
        sources = value.get("sources")
        if isinstance(sources, list) and all(isinstance(item, dict) for item in sources):
            found.extend(sources)
        for child in value.values():
            found.extend(collect_sources(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(collect_sources(child))
    return found


class Index(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("document", {})
        self.stack = [self.root]
        self.ids: Counter[str] = Counter()
        self.fragments: list[str] = []
        self.classes: set[str] = set()
        self.records: list[dict[str, str]] = []
        self.mode_values: list[str] = []
        self.remote_runtime: list[str] = []
        self.has_noscript = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        element = Element(tag, values, self.stack[-1])
        self.stack[-1].children.append(element)
        if tag not in VOID_TAGS:
            self.stack.append(element)
        if values.get("id"):
            self.ids[values["id"]] += 1
        self.classes.update(values.get("class", "").split())
        href = values.get("href", "")
        if tag == "a" and href.startswith("#") and len(href) > 1:
            self.fragments.append(href[1:])
        if values.get("data-record-type"):
            self.records.append(values)
        if values.get("data-mode"):
            self.mode_values.append(values["data-mode"])
        runtime_attr = {
            "script": "src", "link": "href", "img": "src",
            "iframe": "src", "object": "data",
        }.get(tag)
        if runtime_attr and re.match(r"https?://", values.get(runtime_attr, ""), re.I):
            self.remote_runtime.append(f"{tag}[{runtime_attr}]={values[runtime_attr]}")
        if tag == "noscript":
            self.has_noscript = True

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        for offset in range(len(self.stack) - 1, 0, -1):
            if self.stack[offset].tag == tag:
                del self.stack[offset:]
                return

    def handle_data(self, data: str) -> None:
        self.stack[-1].text.append(data)


def element_by_id(index: Index, value: str) -> Element:
    matches = [element for element in walk(index.root) if element.attrs.get("id") == value]
    if len(matches) != 1:
        fail(f"expected one element with id={value}; found {len(matches)}")
    return matches[0]


def panel_role(panel: Element) -> str:
    declared = panel.attrs.get("data-panel-role")
    if declared:
        return declared
    sections = [child for child in panel.children if child.tag == "section"]
    if len(sections) != 1:
        fail("each Analyst panel must contain one direct section")
    role = PANEL_HEADING_ROLES.get(sections[0].attrs.get("aria-labelledby", ""))
    if not role:
        fail("Analyst panel has no recognized role")
    return role


def v03_vars(raw_html: str) -> dict[str, str]:
    style = re.search(r'<style id="v03-skin">(.*?)</style>', raw_html, re.S)
    if not style:
        return {}
    root = re.search(r":root\s*\{(.*?)\}", style.group(1), re.S)
    if not root:
        return {}
    return {
        name: re.sub(r"\s+", " ", value.strip())
        for name, value in re.findall(r"--([\w-]+)\s*:\s*([^;]+);", root.group(1))
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path)
    parser.add_argument("--reference", type=Path, required=True)
    args = parser.parse_args()

    raw_html = args.html.read_text(encoding="utf-8")
    reference = args.reference.read_text(encoding="utf-8")
    index = Index()
    index.feed(raw_html)

    duplicate_ids = sorted(value for value, count in index.ids.items() if count != 1)
    if duplicate_ids:
        fail(f"duplicate DOM IDs: {duplicate_ids[:10]}")
    missing_links = sorted(set(index.fragments) - set(index.ids))
    if missing_links:
        fail(f"unresolved internal links: {missing_links[:12]}")
    if index.remote_runtime:
        fail(f"remote runtime assets found: {index.remote_runtime}")
    if not index.has_noscript:
        fail("missing JavaScript-disabled fallback")
    if Counter(index.mode_values) != Counter({"executive": 1, "analyst": 1}):
        fail(f"expected exactly two mode controls: {index.mode_values}")
    if not re.search(r"\.mode-tabs\s*\{[^}]*width\s*:\s*\d+px", raw_html, re.S):
        fail("mode selector must retain a fixed desktop width")

    missing_ids = sorted(REQUIRED_IDS - set(index.ids))
    missing_classes = sorted(REQUIRED_CLASSES - index.classes)
    if missing_ids:
        fail(f"required interface IDs missing: {missing_ids}")
    if missing_classes:
        fail(f"required interface components missing: {missing_classes}")

    executive = element_by_id(index, "executive")
    if descendants_with_class(executive, "analyst-sidebar") or any(
        element.tag in {"aside", "nav"} for element in walk(executive)
    ):
        fail("Executive must not contain a sidebar or navigation rail")
    blocks = [element for element in executive.children if "exec-block" in classes(element)]
    if [block.attrs.get("data-exec-block") for block in blocks] != ["1", "2", "3", "4", "5", "6"]:
        fail("Executive must contain exactly six ordered blocks")
    if any(element.attrs.get("data-record-type") for element in walk(executive)):
        fail("Executive must not expose canonical record cards")
    forbidden_exec_classes = {"claim-source", "record-badge", "state", "chip", "pillar-checks"}
    visible_forbidden = sorted(
        name for name in forbidden_exec_classes if descendants_with_class(executive, name)
    )
    if visible_forbidden:
        fail(f"Executive exposes Analyst evidence machinery: {visible_forbidden}")
    if len([element for element in walk(blocks[3]) if "pill" in classes(element)]) != 5:
        fail("Executive must contain five pillar conclusions")

    analyst_main = element_by_id(index, "analyst-main")
    panels = [
        element for element in descendants_with_class(analyst_main, "panel")
        if element.attrs.get("data-mode-panel") == "analyst"
    ]
    roles = [panel_role(panel) for panel in panels]
    if roles != PANEL_ROLE_ORDER:
        fail(f"Analyst panel order differs: {roles}")
    panels_by_role = dict(zip(roles, panels))
    for role in PILLAR_ROLES:
        panel = panels_by_role[role]
        if len(descendants_with_class(panel, "evidence-boundary-pair")) != 1:
            fail(f"{role} must contain one evidence boundary pair")
        registers = descendants_with_class(panel, "pillar-checks")
        if len(registers) != 1 or registers[0].tag != "details" or "open" in registers[0].attrs:
            fail(f"{role} must contain one collapsed check register")
        source_links = [
            element for element in descendants_with_class(panel, "claim-source")
            if element.tag == "a"
            and element.attrs.get("href", "").startswith("#source-")
            and visible_text(element)
        ]
        if not source_links:
            fail(f"{role} has no named source links")

    payload_match = re.search(
        r'<script\s+type="application/json"\s+id="plinth-research-state">(.*?)</script>',
        raw_html,
        re.S,
    )
    if not payload_match:
        fail("missing inert #plinth-research-state payload")
    if "internal_materiality" in payload_match.group(1):
        fail("internal materiality appears in public embedded state")
    payload = json.loads(payload_match.group(1))
    assessment = payload.get("assessment")
    if not isinstance(assessment, dict):
        fail("embedded payload must contain assessment")
    checks = assessment.get("checks")
    observations = assessment.get("observations")
    if not isinstance(checks, list) or len(checks) != 63 or not isinstance(observations, list):
        fail("embedded assessment must contain 63 checks and observations[]")
    source_value = assessment.get("sources")
    if isinstance(source_value, list) and all(isinstance(item, dict) for item in source_value):
        sources = source_value
    else:
        sources = collect_sources(payload.get("source_manifest", payload.get("source_manifests", {})))

    record_index = {
        (record.get("data-record-type"), record.get("data-record-id")): record
        for record in index.records
    }
    if len(record_index) != len(index.records):
        fail("canonical DOM record markers are duplicated")
    for check in checks:
        marker = record_index.get(("check", check.get("id")))
        expected = {
            "data-origin": "canonical",
            "data-applicability": check.get("applicability") or "",
            "data-coverage": check.get("coverage") or "",
            "data-search-completed": str(check.get("search_completed")).lower(),
        }
        if not marker or any(marker.get(field) != value for field, value in expected.items()):
            fail(f"check marker mismatch: {check.get('id')}")
    for observation in observations:
        marker = record_index.get(("observation", observation.get("id")))
        if not marker or marker.get("data-origin") != "canonical":
            fail(f"missing canonical observation marker: {observation.get('id')}")
    for source in sources:
        marker = record_index.get(("source", source.get("source_id")))
        if not marker or marker.get("data-origin") != "canonical":
            fail(f"missing canonical source marker: {source.get('source_id')}")

    total = len(checks)
    applies = sum(check.get("applicability") == "APPLIES" for check in checks)
    unresolved = sum(check.get("applicability") == "UNRESOLVED" for check in checks)
    incomplete = sum(
        check.get("applicability") == "APPLIES" and check.get("coverage") != "EVIDENCED"
        for check in checks
    )
    expected_metrics = {
        "total": total,
        "applies": applies,
        "applicability-unresolved": unresolved,
        "applicable-not-fully-answered": incomplete,
    }
    actual_metrics = {
        key: int(value)
        for key, value in re.findall(
            r'class="framework-cell"\s+data-metric="([^"]+)"\s+data-value="(\d+)"',
            raw_html,
        )
    }
    if actual_metrics != expected_metrics:
        fail(f"Executive framework strip differs from assessment: {actual_metrics} != {expected_metrics}")

    expected_by_pillar: dict[str, set[str]] = defaultdict(set)
    for check in checks:
        expected_by_pillar[check.get("pillar", "")].add(check.get("id"))
    open_rows = descendants_with_class(blocks[4], "open-row")
    if len(open_rows) != 5:
        fail("Executive must contain five open-evidence groups")
    seen: list[str] = []
    for row in open_rows:
        canonical_pillar = PILLAR_ALIASES.get(row.attrs.get("data-pillar", ""))
        members = row.attrs.get("data-check-ids", "").split()
        if canonical_pillar is None or set(members) != expected_by_pillar[canonical_pillar]:
            fail(f"open-evidence group differs for {row.attrs.get('data-pillar')}")
        seen.extend(members)
    check_ids = {check.get("id") for check in checks}
    if len(seen) != 63 or len(set(seen)) != 63 or set(seen) != check_ids:
        fail("open-evidence groups must partition all 63 checks exactly once")

    analyst = element_by_id(index, "v3-analyst")
    ai_dock = descendants_with_class(analyst, "ai-dock")
    if len(ai_dock) != 1 or "static preview" not in visible_text(ai_dock[0]).lower():
        fail("Ask Plinth must appear once in Analyst and be labelled Static preview")
    if descendants_with_class(element_by_id(index, "v3-executive"), "ai-dock"):
        fail("Ask Plinth must not appear in Executive")
    if "window.print" in raw_html:
        fail("promoted print functionality is not part of the v0.3 shell")
    if re.search(
        r'class="[^"]*\b(?:materiality|score|ranking|traffic-light|overall-status)\b',
        raw_html,
        re.I,
    ):
        fail("public materiality, score, ranking, or aggregate-status component found")

    output_vars = v03_vars(raw_html)
    reference_vars = v03_vars(reference)
    for name in V03_THEME_VARS:
        if output_vars.get(name) != reference_vars.get(name):
            fail(f"v0.3 theme variable differs from reference: --{name}")
    if not re.search(
        r"\.analyst-main\s+\.claim-citations\s*\{[^}]*row-gap",
        raw_html,
        re.S,
    ):
        fail("wrapped source-pill row spacing is missing")
    if "@media print" not in raw_html or "@media(max-width:" not in raw_html.replace(" ", ""):
        fail("responsive or print rules are absent")

    print(
        f"PASS: v0.3 two-mode interface; 6 Executive blocks; 14 Analyst panels; "
        f"{len(checks)} checks; {len(observations)} observations; {len(sources)} sources"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
