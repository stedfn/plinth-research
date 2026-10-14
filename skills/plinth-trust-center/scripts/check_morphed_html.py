#!/usr/bin/env python3
"""Checker for a Plinth v0.3 two-mode Trust Center built from compiler-accepted records.

Usage::

    python3 check_morphed_html.py OUTPUT.html --reference SHELL.html \\
        --assessment RUN/assessment.json --evidence RUN/documentary-evidence.json \\
        --catalogue inputs/catalogue.json

It proves the page embeds exactly the run's accepted records, marks and
displays every canonical record faithfully, and keeps the v0.3 interface
structure. It does not prove the records themselves are valid: run
``plinth verify`` for that first. Exit 0 prints PASS; exit 1 prints the first
failure.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from trust_center_records import (  # noqa: E402
    PILLAR_ALIASES,
    Inputs,
    RecordError,
    Records,
    load_inputs,
)
from executive_questions import QUESTIONS, GROUPS, LABELS
from presentation import executive_counts

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
ROLE_PILLAR = {
    "control": "control",
    "backing": "backing",
    "economics": "economics",
    "governance-compliance": "governance_compliance",
    "continuity": "continuity",
}
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
REQUIRED_IDS = {
    "v3-executive", "executive", "v3-analyst", "analyst-main",
    "pillar-control", "pillar-reserves", "pillar-economics",
    "pillar-governance-compliance", "pillar-continuity", "chain-of-title",
    "gaps-title", "sources-title", "methodology-title", "technical-appendix",
    "plinth-research-state",
}
REQUIRED_CLASSES = {
    "v3-top", "mode-tabs", "v3-view", "executive-main", "kiid-main",
    "grid", "card", "q", "bound", "evidence", "pill", "disclosure-cue",
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
PAYLOAD_RE = re.compile(
    r'<script\s+type="application/json"\s+id="plinth-research-state">(.*?)</script>', re.S
)
PLACEHOLDER_RE = re.compile(r"\{\{[A-Z][A-Z0-9_ &,./:'-]*\}\}")
SAFE_HREF_RE = re.compile(r"^(#|https?://)", re.I)


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
    return normalized(" ".join(parts))


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


class Index(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("document", {})
        self.stack = [self.root]
        self.ids: Counter[str] = Counter()
        self.fragments: list[str] = []
        self.classes: set[str] = set()
        self.records: list[Element] = []
        self.mode_values: list[str] = []
        self.remote_runtime: list[str] = []
        self.hrefs: list[str] = []
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
        if "href" in values:
            self.hrefs.append(values["href"])
        href = values.get("href", "")
        if tag == "a" and href.startswith("#") and len(href) > 1:
            self.fragments.append(href[1:])
        if values.get("data-record-type"):
            self.records.append(element)
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


def find_placeholders(raw_html: str) -> list[str]:
    """Unfilled shell placeholders outside the payload, which may quote anything."""
    outside = PAYLOAD_RE.sub("", raw_html)
    return sorted(set(PLACEHOLDER_RE.findall(outside)))


def check_payload(raw_payload: str, inputs: Inputs) -> None:
    """The payload is exactly the accepted records, escaped so it cannot end early."""
    if "<" in raw_payload:
        fail("embedded payload contains an unescaped '<'; write every '<' as \\u003c")
    try:
        payload = json.loads(raw_payload)
    except ValueError as exc:
        fail(f"embedded payload is not valid JSON: {exc}")
    if not isinstance(payload, dict) or set(payload) != {"assessment", "evidence"}:
        keys = sorted(payload) if isinstance(payload, dict) else type(payload).__name__
        fail(f"embedded payload must have exactly the keys assessment and evidence; found {keys}")
    if payload["assessment"] != inputs.assessment:
        fail("embedded assessment differs from the accepted assessment.json")
    if payload["evidence"] != inputs.evidence:
        fail("embedded evidence differs from the accepted documentary-evidence.json")


def require_exposed(element: Element, description: str) -> None:
    """Supporting disclosures may collapse; framework accounting must remain exposed."""
    node = element
    while node:
        if node.tag == "details" and "open" not in node.attrs:
            fail(f"{description} must not be inside a closed disclosure")
        if "hidden" in node.attrs:
            fail(f"{description} must remain visible")
        node = node.parent


def check_executive(index: Index, records: Records, warnings: list[str]) -> Element:
    view = element_by_id(index, "v3-executive")
    if view.attrs.get("data-executive-layout") != "questions12":
        fail("Executive layout must be questions12")
    if any("data-executive-slot" in e.attrs for e in walk(index.root)):
        fail("unfinished Executive insertion slot")
    executive = element_by_id(index, "executive")
    if any("data-exec-block" in e.attrs or "exec-block" in classes(e) for e in walk(view)):
        fail("legacy six-block Executive components are not supported")
    if descendants_with_class(executive, "analyst-sidebar"):
        fail("Executive must not contain the Analyst sidebar")
    if any(e.attrs.get("data-record-type") for e in walk(view)):
        fail("Executive must not expose canonical record cards")
    forbidden = {"claim-source", "record-badge", "state", "pillar-checks"}
    if any(classes(e) & forbidden or "data-evidence-class" in e.attrs for e in walk(view)):
        fail("Executive exposes Analyst evidence machinery")
    groups = descendants_with_class(executive, "grp")
    if [g.attrs.get("data-question-group") for g in groups] != [g[0] for g in GROUPS]:
        fail("Executive must contain the five ordered question groups")
    cards = descendants_with_class(executive, "q")
    if [card.attrs.get("id") for card in cards] != [f"q{n}" for n, _, _ in QUESTIONS]:
        fail("Executive must contain exactly twelve ordered question cards")
    for group, (_, title, first, last) in zip(groups, GROUPS):
        if [c.attrs.get("id") for c in descendants_with_class(group, "q")] != [f"q{n}" for n in range(first, last + 1)]:
            fail("Executive question grouping differs")
        if visible_text(element_by_id(index, f"group-{group.attrs['data-question-group']}")) != title:
            fail("Executive question group heading differs")
    for card, (number, title, mapping) in zip(cards, QUESTIONS):
        heading = element_by_id(index, f"title-{number}")
        numbers = descendants_with_class(heading, "q-n")
        if normalized(" ".join(heading.text)) != title or len(numbers) != 1 or visible_text(numbers[0]) != f"QUESTION {number:02}":
            fail(f"Q{number} question heading differs")
        answers = descendants_with_class(card, "q-a")
        boundaries = descendants_with_class(card, "bound")
        disclosures = descendants_with_class(card, "evidence")
        if len(answers) != 1 or not visible_text(answers[0]):
            fail(f"Q{number} requires a non-empty answer")
        if len(boundaries) != 1 or not visible_text(boundaries[0]):
            fail(f"Q{number} requires an unresolved evidence boundary")
        if len(disclosures) != 1 or disclosures[0].tag != "details":
            fail(f"Q{number} requires a Basis & limitations disclosure")
        label = card.attrs.get("data-evidence-label")
        if label not in LABELS:
            fail(f"Q{number} has an unknown documentary answer label")
        observation_ids = card.attrs.get("data-observation-ids", "").split()
        if label == "source-described" and not observation_ids:
            fail(f"Q{number} Source-described requires supporting observation IDs")
        summary = [e for e in disclosures[0].children if e.tag == "summary"]
        if len(summary) != 1 or not all(t in visible_text(summary[0]) for t in ("Basis & limitations", "Expand", "Collapse")):
            fail(f"Q{number} disclosure requires clear Expand / Collapse cues")
        pills = descendants_with_class(summary[0], "pill")
        expected_text, expected_class = LABELS[label]
        if len(pills) != 1 or visible_text(pills[0]) != expected_text or expected_class not in classes(pills[0]):
            fail(f"Q{number} answer label and disclosure styling disagree")
        # The index reflects the authored answer category, not a compiler coverage state.
        index_links = [e for e in descendants_with_class(executive, "card") if e.attrs.get("href") == f"#q{number}"]
        if len(index_links) != 1:
            fail(f"Q{number} must have one question-index card")
        labels = descendants_with_class(index_links[0], "index-status")
        if len(labels) != 1 or visible_text(labels[0]) != expected_text or expected_class not in classes(labels[0]):
            fail(f"Q{number} answer label and question index disagree")
        cited = set(card.attrs.get("data-check-ids", "").split())
        if not cited:
            fail(f"Q{number} must name supporting check IDs")
        outside = sorted(cited - set(mapping) - (cited - set(records.checks)))
        if outside:
            warnings.append(f"Q{number} cites checks outside its default mapping: {outside}; justify in review.md")
        links = {e.attrs.get("href") for e in walk(disclosures[0]) if e.tag == "a"}
        if any(f"#observation-{oid}" not in links for oid in observation_ids):
            fail(f"Q{number} disclosure must link every supporting observation")
    paths = [e for e in walk(cards[0]) if "data-claim-path" in e.attrs]
    if len(paths) != 1 or not visible_text(paths[0]):
        fail("Q1 requires a non-empty holder-to-asset claim path")
    require_exposed(paths[0], "claim path")
    sequence = ["executive-orientation", "q1", "q5", "executive-value-movement", "q7", "q12",
                "executive-open", "executive-coverage", "scope"]
    order = [e.attrs.get("id") for e in walk(executive)]
    positions = [order.index(value) if value in order else -1 for value in sequence]
    if -1 in positions or positions != sorted(positions):
        fail("Executive must retain orientation, claim, value movement, unresolved, coverage and technical order")
    for name in ("framework-strip", "open-row", "coverage-counts"):
        for e in descendants_with_class(executive, name):
            require_exposed(e, name)
    actual_counts = {e.attrs["data-coverage-count"]: e.attrs.get("data-value")
                     for e in walk(executive) if "data-coverage-count" in e.attrs}
    expected_counts = {key: str(value) for key, value in executive_counts(records).items()}
    if actual_counts != expected_counts:
        fail("Executive coverage counts differ from the accepted assessment")
    for e in walk(executive):
        if "data-coverage-count" in e.attrs and visible_text(e) != f"{e.attrs['data-coverage-count']}: {e.attrs.get('data-value')}":
            fail("Executive coverage count display differs")
    if "Publication approval pending" not in visible_text(executive):
        fail("Executive must disclose pending publication approval")
    return executive


def check_document(raw_html: str, reference_html: str, inputs: Inputs,
                   warnings: list[str] | None = None) -> str:
    """Raise AssertionError on the first failure; return the PASS summary.

    Non-fatal findings are appended to ``warnings``.
    """
    warnings = [] if warnings is None else warnings
    records = Records(inputs)
    if any(check.get("coverage") == "MISSING" for check in records.checks.values()):
        fail("MISSING coverage is disabled; use NOT_ASSESSED for unfinished work")

    leftover = find_placeholders(raw_html)
    if leftover:
        fail(f"unfilled placeholders remain: {leftover[:8]}")
    if "data-fill=" in raw_html:
        fail("unfilled prefill region (data-fill); run scripts/prefill_shell.py")
    if "data-materiality" in raw_html:
        fail("internal materiality appears in a data-materiality attribute")

    index = Index()
    index.feed(raw_html)

    duplicate_ids = sorted(value for value, count in index.ids.items() if count != 1)
    if duplicate_ids:
        fail(f"duplicate DOM IDs: {duplicate_ids[:10]}")
    missing_links = sorted(set(index.fragments) - set(index.ids))
    if missing_links:
        fail(f"unresolved internal links: {missing_links[:12]}")
    unsafe = sorted({href for href in index.hrefs if not SAFE_HREF_RE.match(href)})
    if unsafe:
        fail(f"links must be #fragments or http(s) URLs: {unsafe[:5]}")
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

    executive = check_executive(index, records, warnings)

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
        check_pillar_sources(role, panel, records, warnings)

    payload_match = PAYLOAD_RE.search(raw_html)
    if not payload_match:
        fail("missing inert #plinth-research-state payload")
    check_payload(payload_match.group(1), inputs)

    check_markers(index, records)

    known_checks = set(records.check_order)
    for element in walk(index.root):
        for name, known, kind in (("data-check-ids", known_checks, "check"),
                                  ("data-observation-ids", set(records.observations), "observation")):
            if name in element.attrs:
                unknown = sorted(set(element.attrs[name].split()) - known)
                if unknown:
                    fail(f"{name} names unknown {kind} IDs: {unknown[:5]}")

    expected_metrics = records.metrics()
    actual_metrics = {
        key: int(value)
        for key, value in re.findall(
            r'class="framework-cell"\s+data-metric="([^"]+)"\s+data-value="(\d+)"',
            raw_html,
        )
    }
    if actual_metrics != expected_metrics:
        fail(f"Executive framework strip differs from assessment: {actual_metrics} != {expected_metrics}")
    for cell in descendants_with_class(executive, "framework-cell"):
        shown = [visible_text(child) for child in cell.children if "framework-n" in classes(child)]
        if shown != [cell.attrs.get("data-value")]:
            fail(f"framework figure shown for {cell.attrs.get('data-metric')} is {shown}, "
                 f"expected {cell.attrs.get('data-value')}")

    expected_by_pillar = {pillar: {check_id for check_id in records.check_order
                                   if records.pillar_of[check_id] == pillar}
                          for pillar in records.pillar_ids}
    open_rows = descendants_with_class(element_by_id(index, "executive-open"), "open-row")
    if len(open_rows) != len(records.pillar_ids):
        fail(f"Executive must contain {len(records.pillar_ids)} open-evidence groups")
    seen: list[str] = []
    for row in open_rows:
        pillar = PILLAR_ALIASES.get(row.attrs.get("data-pillar", ""))
        members = row.attrs.get("data-check-ids", "").split()
        if pillar is None or set(members) != expected_by_pillar[pillar]:
            fail(f"open-evidence group differs for {row.attrs.get('data-pillar')}")
        seen.extend(members)
    if sorted(seen) != sorted(known_checks):
        fail("open-evidence groups must partition every catalogue check exactly once")

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
    reference_vars = v03_vars(reference_html)
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

    return (
        f"PASS: v0.3 two-mode interface; 12 Executive questions; {len(PANEL_ROLE_ORDER)} Analyst panels; "
        f"{len(records.checks)} checks; {len(records.observations)} observations; "
        f"{len(records.sources)} sources"
    )


def check_pillar_sources(role: str, panel: Element, records: Records, warnings: list[str]) -> None:
    """A pillar must cite at least one source behind its own checks, or be marked as having none."""
    pillar = ROLE_PILLAR[role]
    expected = records.pillar_sources(pillar)
    section = next((child for child in panel.children if child.tag == "section"), panel)
    marked_none = section.attrs.get("data-pillar-sources") == "none"
    cited = [element.attrs.get("href", "")[len("#source-"):]
             for element in descendants_with_class(panel, "claim-source")
             if element.tag == "a" and element.attrs.get("href", "").startswith("#source-")
             and visible_text(element)]
    if not expected:
        if not marked_none:
            fail(f"{role} cites no observations, so its section must carry data-pillar-sources=\"none\"")
        if cited:
            fail(f"{role} cites no observations but links sources: {sorted(set(cited))[:5]}")
        return
    if marked_none:
        fail(f"{role} cites observations, so it must not be marked data-pillar-sources=\"none\"")
    if not set(cited) & expected:
        fail(f"{role} links no source that supports its own checks; expected one of {sorted(expected)[:5]}")
    unrelated = sorted(set(cited) - expected)
    if unrelated:
        warnings.append(f"{role} also links sources that support none of its checks: {unrelated[:5]}")


def check_markers(index: Index, records: Records) -> None:
    """Every canonical record is marked once, faithfully, and shows its key text."""
    markers: dict[tuple[str, str], Element] = {}
    for element in index.records:
        key = (element.attrs.get("data-record-type", ""), element.attrs.get("data-record-id", ""))
        if key in markers:
            fail(f"canonical DOM record marker is duplicated: {key}")
        markers[key] = element
    known = {("check", cid) for cid in records.check_order}
    known |= {("observation", oid) for oid in records.observations}
    known |= {("source", sid) for sid in records.sources}
    stray = sorted(set(markers) - known)
    if stray:
        fail(f"canonical markers name records the run does not have: {stray[:5]}")

    for check_id in records.check_order:
        check = records.checks[check_id]
        marker = markers.get(("check", check_id))
        expected = {
            "data-origin": "canonical",
            "data-applicability": check["applicability"],
            "data-coverage": check.get("coverage") or "",
        }
        if marker is None or any(marker.attrs.get(name) != value for name, value in expected.items()):
            fail(f"check marker mismatch: {check_id}")
        shown = visible_text(marker)
        if normalized(check["finding"]) not in shown:
            fail(f"check {check_id} does not show its accepted finding")
        if check.get("gap") and normalized(check["gap"]["question"]) not in shown:
            fail(f"check {check_id} does not show its gap question")
    for observation_id, observation in records.observations.items():
        marker = markers.get(("observation", observation_id))
        if marker is None or marker.attrs.get("data-origin") != "canonical":
            fail(f"missing canonical observation marker: {observation_id}")
        if normalized(observation["proposition"]) not in visible_text(marker):
            fail(f"observation {observation_id} does not show its accepted proposition")
    for source_id, source in records.sources.items():
        marker = markers.get(("source", source_id))
        if marker is None or marker.attrs.get("data-origin") != "canonical":
            fail(f"missing canonical source marker: {source_id}")
        if normalized(source["title"]) not in visible_text(marker):
            fail(f"source {source_id} does not show its title")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("html", type=Path, help="the Trust Center HTML to check")
    parser.add_argument("--reference", type=Path, required=True,
                        help="the shell the page was built from (assets/v0.3-two-mode-shell.html)")
    parser.add_argument("--assessment", type=Path, required=True, help="the run's accepted assessment.json")
    parser.add_argument("--evidence", type=Path, required=True,
                        help="the run's accepted documentary-evidence.json")
    parser.add_argument("--catalogue", type=Path, required=True, help="inputs/catalogue.json")
    args = parser.parse_args(argv)
    warnings: list[str] = []
    try:
        inputs = load_inputs(args.assessment, args.evidence, args.catalogue)
        summary = check_document(args.html.read_text(encoding="utf-8"),
                                 args.reference.read_text(encoding="utf-8"), inputs, warnings)
    except (AssertionError, RecordError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    for warning in warnings:
        print(f"WARN: {warning}", file=sys.stderr)
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
