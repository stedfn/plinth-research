#!/usr/bin/env python3
"""Fill the mechanical parts of a Trust Center from one run's accepted records.

Usage::

    python3 prefill_shell.py --product "Example Fund" \\
        --assessment RUN/assessment.json --evidence RUN/documentary-evidence.json \\
        --catalogue inputs/catalogue.json --out trust-centers/example/index.html

It copies the v0.3 shell and fills every region marked ``data-fill``:

- the canonical check, observation, source and locator records;
- the pillar check registers, evidence requests and methodology counts;
- the Executive framework figures and open-evidence partition;
- the embedded payload.

It also sets ``{{PRODUCT}}`` everywhere and marks pillars whose checks cite no
observations. Everything else stays a ``{{PLACEHOLDER}}`` for the author: the
narrative, the citations inside it, and the Executive synthesis. Run
``check_morphed_html.py`` once those are written.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from trust_center_records import (  # noqa: E402
    EVIDENCE_CLASS,
    PILLAR_ALIASES,
    PILLAR_HEADING,
    RecordError,
    Records,
    badge_class,
    load_inputs,
    payload_text,
)

from presentation import (utc_date, cutoff_text, executive_counts, source_reference_entries,
                          render_source_references_html, render_source_references_md)

DEFAULT_SHELL = Path(__file__).resolve().parent.parent / "assets" / "v0.3-two-mode-shell.html"
EXECUTIVE_FRAGMENT = DEFAULT_SHELL.with_name("executive-questions12.html")
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
             "param", "source", "track", "wbr"}
PLACEHOLDER_RE = re.compile(r"\{\{[A-Z][A-Z0-9_ &,./:'-]*\}\}")


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


# ---------------------------------------------------------------------------
# locating elements by attribute, with exact offsets into the source text
# ---------------------------------------------------------------------------
class _Locator(HTMLParser):
    def __init__(self, text: str, attribute: str) -> None:
        super().__init__(convert_charrefs=True)
        self.text = text
        self.attribute = attribute
        self.line_starts = [0] + [i + 1 for i, ch in enumerate(text) if ch == "\n"]
        self.stack: list[dict] = []
        self.found: list[dict] = []

    def _offset(self) -> int:
        line, column = self.getpos()
        return self.line_starts[line - 1] + column

    def handle_starttag(self, tag, attrs):
        start = self._offset()
        raw = self.get_starttag_text()
        node = {"tag": tag, "attrs": dict(attrs), "start": start, "inner_start": start + len(raw),
                "raw_start": raw}
        if tag in VOID_TAGS:
            return
        self.stack.append(node)

    def handle_endtag(self, tag):
        start = self._offset()
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                node = self.stack[i]
                del self.stack[i:]
                if self.attribute in node["attrs"]:
                    node["inner_end"] = start
                    node["end"] = self.text.index(">", start) + 1
                    self.found.append(node)
                return


def elements_with(text: str, attribute: str) -> list[dict]:
    locator = _Locator(text, attribute)
    locator.feed(text)
    locator.close()
    return sorted(locator.found, key=lambda node: node["start"])


def without_fill(raw_start: str) -> str:
    return re.sub(r'\s+data-fill="[^"]*"', "", raw_start)


def executive_shell(shell: str) -> str:
    """Insert the only supported Executive layout, or accept a complete custom one."""
    if 'data-exec-block=' in shell:
        raise RecordError("six-block shells are no longer supported; use the twelve-question shell")
    views = [n for n in elements_with(shell, "id") if n["attrs"]["id"] == "v3-executive"]
    if len(views) != 1:
        raise RecordError("the shell must have one #v3-executive")
    view = views[0]
    layout = view["attrs"].get("data-executive-layout")
    if layout not in (None, "questions12"):
        raise RecordError("the shell's Executive layout must be questions12")
    slots = elements_with(shell, "data-executive-slot")
    if slots:
        if len(slots) != 1 or not (view["inner_start"] <= slots[0]["start"] < view["inner_end"]):
            raise RecordError("the shell must have exactly one Executive slot inside #v3-executive")
        if re.search(r'id=[\"\']q\d+[\"\']', shell):
            raise RecordError("the shell contains both an Executive slot and question cards")
        slot = slots[0]
        shell = shell[:slot["start"]] + EXECUTIVE_FRAGMENT.read_text(encoding="utf-8") + shell[slot["end"]:]
    elif layout != "questions12" or re.findall(r'<article\b[^>]*\bid="q(\d+)"', shell) != [str(n) for n in range(1, 13)]:
        raise RecordError("custom shells need an Executive slot or twelve ordered questions12 cards")
    if layout is None:
        shell = shell[:view["start"]] + view["raw_start"][:-1] + ' data-executive-layout="questions12">' + shell[view["inner_start"]:]
    return shell




# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------
def links(prefix: str, ids: list[str]) -> str:
    if not ids:
        return "None"
    return ", ".join(f'<a href="#{prefix}-{esc(i)}">{esc(i)}</a>' for i in ids)


def fact_list(rows: list[tuple[str, str]]) -> str:
    items = "".join(f"<li><strong>{esc(label)}:</strong> {value}</li>" for label, value in rows)
    return f'<ul class="fact-list">{items}</ul>'


def badge(value: str) -> str:
    return f'<span class="record-badge {esc(badge_class(value))}">{esc(value)}</span>'


def time_text(observation: dict) -> str:
    parts = []
    if observation.get("observation_time"):
        parts.append(f"observed {observation['observation_time']}")
    start, end = observation.get("effective_period_start"), observation.get("effective_period_end")
    if start and end:
        parts.append(f"effective {start} to {end}")
    elif start:
        parts.append(f"effective from {start}")
    elif end:
        parts.append(f"effective until {end}")
    if observation.get("evidence_as_of"):
        parts.append(f"evidence as of {observation['evidence_as_of']}")
    return esc("; ".join(parts)) if parts else "No observation, effective or as-of time recorded"


def render_check(records: Records, check: dict) -> str:
    cid = check["check_id"]
    applicability = check["applicability"]
    coverage = check.get("coverage")
    badges = badge(applicability) + (badge(coverage) if coverage else "")
    rows = [
        ("Pillar", esc(records.pillar_label[records.pillar_of[cid]])),
        ("Applicability", esc(applicability)),
        ("Applicability basis", esc(check["applicability_basis"])),
        ("Applicability observations", links("observation", check.get("applicability_observation_ids", []))),
        ("Coverage", esc(coverage) if coverage else "None: applicability is unresolved"),
        ("Coverage basis", esc(check["coverage_basis"]) if check.get("coverage_basis") else "None recorded"),
        ("Finding observations", links("observation", check.get("finding_observation_ids", []))),
        ("Exclusions", esc("; ".join(check.get("exclusions", []))) or "None"),
    ]
    body = fact_list(rows) + f"<p><strong>Finding.</strong> {esc(check['finding'])}</p>"
    contradiction = check.get("contradiction")
    if contradiction:
        body += "<h4>Contradiction</h4>" + fact_list([
            ("Conflicting observations", links("observation", contradiction["conflicting_observation_ids"])),
            ("Conflict basis", esc(contradiction["conflict_basis"])),
            ("Precedence considered", esc("; ".join(contradiction["precedence_considered"]))),
        ])
    gap = check.get("gap")
    if gap:
        rows = [(records.gap_labels[name], esc(gap[name])) for name in records.gap_fields]
        rows.append(("Evidence observations", links("observation", gap.get("evidence_observation_ids", []))))
        body += "<h4>Gap contract</h4>" + fact_list(rows)
    return (
        f'<details class="record check-record" id="check-{esc(cid)}" data-origin="canonical" '
        f'data-record-type="check" data-record-id="{esc(cid)}" data-applicability="{esc(applicability)}" '
        f'data-coverage="{esc(coverage or "")}"><summary><span class="record-title">'
        f'<span class="record-kicker">check</span>{esc(cid)} — {esc(records.question[cid])}</span>'
        f'<span class="record-badges">{badges}</span></summary><div class="record-body">{body}</div></details>'
    )


def render_observation(records: Records, observation: dict) -> str:
    oid = observation["observation_id"]
    supports = []
    for support in observation.get("supports", []):
        acquisition = records.acquisitions.get(support["acquisition_id"], {})
        source_id = acquisition.get("source_id", "")
        title = records.sources.get(source_id, {}).get("title", source_id)
        supports.append(
            f'<a href="#source-{esc(source_id)}">{esc(title)}</a> '
            f'(acquisition {esc(support["acquisition_id"])}, locator '
            f'<a href="#locator-{esc(support["locator_id"])}">{esc(support["locator_id"])}</a>)')
    rows = [("Subject", esc(observation["subject"]))]
    if observation.get("value") is not None:
        unit = f" {observation['unit']}" if observation.get("unit") else ""
        rows.append(("Value", esc(f"{observation['value']}{unit}")))
    rows += [
        ("Time", time_text(observation)),
        ("Supported by", "; ".join(supports) if supports else "No direct source; derived from parents"),
        ("Parents", links("observation", observation.get("parent_observation_ids", []))),
        ("Derivation", esc(f"{observation['derivation_rule_id']} version {observation['derivation_rule_version']}")
         if observation.get("derivation_rule_id") else "None"),
    ]
    if observation.get("qualifications"):
        rows.append(("Qualifications", esc("; ".join(observation["qualifications"]))))
    if observation.get("authority_limitations"):
        rows.append(("Authority limitations", esc("; ".join(observation["authority_limitations"]))))
    return (
        f'<details class="record observation-record" id="observation-{esc(oid)}" data-origin="canonical" '
        f'data-record-type="observation" data-record-id="{esc(oid)}"><summary><span class="record-title">'
        f'<span class="record-kicker">observation</span>{esc(oid)}</span></summary>'
        f'<div class="record-body"><p>{esc(observation["proposition"])}</p>{fact_list(rows)}</div></details>'
    )


def source_state(records: Records, source: dict) -> str | None:
    if source.get("disposition", "IN_SCOPE") != "IN_SCOPE":
        return source["disposition"]
    attempts = records.acquisitions_by_source.get(source["source_id"], [])
    if any(attempt["outcome"] == "ACQUIRED" for attempt in attempts):
        return None
    return attempts[-1]["outcome"] if attempts else "NO_ACQUISITION"


def url_text(url: str) -> str:
    if re.match(r"https?://", url, re.I):
        return f'<a href="{esc(url)}" rel="noopener noreferrer">{esc(url)}</a>'
    return f"{esc(url)} (not linked: not an http(s) URL)"


def render_source(records: Records, source: dict) -> str:
    sid = source["source_id"]
    attempts = records.acquisitions_by_source.get(sid, [])
    outcomes = list(dict.fromkeys(attempt["outcome"] for attempt in attempts))
    badges = "".join(badge(outcome) for outcome in outcomes)
    if source.get("disposition", "IN_SCOPE") != "IN_SCOPE":
        badges += badge(source["disposition"])
    if not attempts:
        badges += '<span class="record-badge">NO ACQUISITION</span>'
    rows = [("Author / publisher", esc(f"{source.get('author') or '—'} / {source.get('publisher') or '—'}"))]
    for label, key in (("Commissioner or funder", "commissioner_or_funder"),
                       ("Relationship to subject", "relationship_to_subject"),
                       ("Research posture", "research_posture")):
        if source.get(key):
            rows.append((label, esc(source[key])))
    rows.append(("Source type", esc(source["source_type"])))
    if source.get("url"):
        rows.append(("URL", url_text(source["url"])))
    if source.get("publication_date"):
        rows.append(("Published (UTC date)", esc(utc_date(source["publication_date"]))))
    disposition = source.get("disposition", "IN_SCOPE")
    if disposition == "EXCLUDED":
        disposition_text = f"EXCLUDED: {esc(source.get('excluded_reason') or 'no reason recorded')}"
    elif disposition == "SUPERSEDED" and source.get("superseded_by_source_id"):
        disposition_text = f"SUPERSEDED by {links('source', [source['superseded_by_source_id']])}"
    else:
        disposition_text = esc(disposition)
    rows.append(("Disposition", disposition_text))
    if source.get("stated_methodology_scope"):
        rows.append(("Methodology scope", esc(source["stated_methodology_scope"])))
    if source.get("stated_limitations"):
        rows.append(("Stated limitations", esc("; ".join(source["stated_limitations"]))))
    if source.get("notes"):
        rows.append(("Notes", esc(source["notes"])))
    if attempts:
        items = []
        for attempt in attempts:
            parts = [attempt["acquisition_mode"], attempt["outcome"], f"attempted {utc_date(attempt['attempted_at'])}"]
            if attempt.get("retrieved_at"):
                parts.append(f"retrieved {utc_date(attempt['retrieved_at'])}")
            if attempt.get("failure_reason"):
                parts.append(f"failure: {attempt['failure_reason']}")
            if attempt.get("artifact_sha256"):
                parts.append(f"artifact sha256 {attempt['artifact_sha256'][:16]}…")
            items.append(f"<li>{esc(attempt['acquisition_id'])}: {esc(', '.join(parts))}</li>")
        rows.append(("Acquisitions (UTC dates)", f'<ul class="fact-list">{"".join(items)}</ul>'))
    else:
        rows.append(("Acquisitions", "None recorded"))
    state = source_state(records, source)
    evidence_class = EVIDENCE_CLASS.get(source.get("research_posture") or "")
    hooks = (f' data-state="{esc(state)}"' if state else "") + \
            (f' data-evidence-class="{esc(evidence_class)}"' if evidence_class else "")
    return (
        f'<details class="record source-record" id="source-{esc(sid)}" data-origin="canonical" '
        f'data-record-type="source" data-record-id="{esc(sid)}"{hooks}><summary><span class="record-title">'
        f'<span class="record-kicker">source</span>{esc(sid)} — {esc(source["title"])}</span>'
        f'<span class="record-badges">{badges}</span></summary>'
        f'<div class="record-body">{fact_list(rows)}</div></details>'
    )


def render_locator(records: Records, locator: dict) -> str:
    lid = locator["locator_id"]
    artifact = records.artifacts.get(locator["artifact_sha256"], {})
    where = []
    for label, key in (("page", "page"), ("section", "section"), ("heading", "heading"),
                       ("selector", "selector"), ("field", "field_path")):
        if locator.get(key) is not None:
            where.append(f"{label} {locator[key]}")
    if locator.get("char_start") is not None:
        where.append(f"characters {locator['char_start']}–{locator.get('char_end')}")
    rows = [
        ("Sources", links("source", records.sources_by_artifact.get(locator["artifact_sha256"], []))),
        ("Artifact", esc(f"sha256 {locator['artifact_sha256'][:16]}… "
                         f"({artifact.get('media_type', 'unknown type')}, {artifact.get('filename', 'unknown file')})")),
        ("Location", esc(f"{locator['locator_type']}: " + ("; ".join(where) or "whole artifact"))),
    ]
    if locator.get("quoted_text"):
        rows.append(("Quoted text", esc(locator["quoted_text"])))
    rows.append(("Used by observations", links("observation", records.observations_by_locator.get(lid, []))))
    return (
        f'<details class="record locator-record" id="locator-{esc(lid)}"><summary><span class="record-title">'
        f'<span class="record-kicker">locator</span>{esc(lid)}</span><span class="record-badges">'
        f'<span class="record-badge">{esc(locator["locator_type"])}</span></span></summary>'
        f'<div class="record-body">{fact_list(rows)}</div></details>'
    )


def render_pillar_rows(records: Records, pillar: str) -> str:
    rows = []
    for check in records.checks_in(pillar):
        cid = check["check_id"]
        rows.append(f'<tr><td><a href="#check-{esc(cid)}">{esc(cid)}</a></td><td>{esc(records.question[cid])}</td>'
                    f'<td>{badge(records.result(check))}</td></tr>')
    return "\n".join(rows)


def render_requests(records: Records) -> str:
    parts = []
    for pillar in records.pillar_ids:
        gaps = [check for check in records.checks_in(pillar) if check.get("gap")]
        if not gaps:
            continue
        parts.append(f'<h3 class="subsection-title">{esc(records.pillar_label[pillar])}</h3>')
        for check in gaps:
            cid, gap = check["check_id"], check["gap"]
            parts.append(
                f'<article class="evidence-request" id="request-{esc(cid)}"><span class="mono">{esc(cid)}</span>'
                f'<h3>{esc(gap["question"])}</h3><p>{esc(gap["what_would_close_it"])}</p>'
                f'<p class="small"><a href="#check-{esc(cid)}">Open the complete six-field gap and lineage</a></p>'
                f'</article>')
    return "\n".join(parts) or '<p class="panel-note">No check has an open evidence gap.</p>'


def open_summary(counts: dict[str, int]) -> str:
    applies, incomplete = counts["applies"], counts["applicable-not-fully-answered"]
    parts = [f"{incomplete} of {applies} applicable questions remain less than completely evidenced"
             if applies else "No question currently applies"]
    if counts["applicability-unresolved"]:
        parts.append(f"applicability is unresolved for {counts['applicability-unresolved']}")
    if counts["does-not-apply"]:
        parts.append(f"{counts['does-not-apply']} do not apply")
    return "; ".join(parts) + "."


def id_range(check_ids: list[str]) -> str:
    if len(check_ids) == 1:
        return check_ids[0]
    return f"{check_ids[0]}–{check_ids[-1].rsplit('-', 1)[1]}"


def render_distribution(records: Records) -> str:
    columns = [("Checks", "total"), ("Applies", "applies"), ("Applicability unresolved", "applicability-unresolved"),
               ("Does not apply", "does-not-apply"), ("Evidenced", "evidenced"), ("Partial", "partial"),
               ("Missing", "missing"), ("Contradictory", "contradictory"), ("Not assessed", "not-assessed")]
    head = "<thead><tr><th>Pillar</th>" + "".join(f"<th>{label}</th>" for label, _ in columns) + "</tr></thead>"
    rows = []
    for pillar in records.pillar_ids:
        counts = Records.counts(records.checks_in(pillar))
        rows.append(f"<tr><th>{esc(records.pillar_label[pillar])}</th>"
                    + "".join(f"<td>{counts[key]}</td>" for _, key in columns) + "</tr>")
    counts = Records.counts([records.checks[cid] for cid in records.check_order])
    rows.append("<tr><th>Total</th>" + "".join(f"<td>{counts[key]}</td>" for _, key in columns) + "</tr>")
    return head + "<tbody>" + "".join(rows) + "</tbody>"


# ---------------------------------------------------------------------------
# filling
# ---------------------------------------------------------------------------
def fill(shell: str, records: Records, payload: str, product: str) -> tuple[str, list[str]]:
    shell = executive_shell(shell)
    notes: list[str] = []
    edits: list[tuple[int, int, str]] = []
    counts = {pillar: Records.counts(records.checks_in(pillar)) for pillar in records.pillar_ids}
    metrics = records.metrics()

    for node in elements_with(shell, "data-fill"):
        region = node["attrs"]["data-fill"]
        start_tag = without_fill(node["raw_start"])
        inner = shell[node["inner_start"]:node["inner_end"]]
        kind, _, arg = region.partition(":")
        if kind == "snapshot-date":
            inner = "Fixed evidence snapshot · " + esc(utc_date(records.campaign["cutoff"]))
        elif kind == "cutoff":
            inner = "Evidence cutoff: " + esc(cutoff_text(records.campaign["cutoff"]))
        elif kind == "declared-scope":
            inner = ("Declared scope: public evidence only" if records.campaign["bounded_public_evidence"]
                     else "Declared scope: not limited to public evidence")
        elif kind == "executive-coverage":
            inner = "".join(f'<span class="coverage-count" data-coverage-count="{esc(label)}" '
                            f'data-value="{value}">{esc(label)}: {value}</span>'
                            for label, value in executive_counts(records).items())
        elif kind == "framework-strip":
            def cell(match):
                value = metrics[match.group("metric")]
                return f'{match.group("open")}{value}{match.group("mid")}{value}{match.group("close")}'
            inner = re.sub(
                r'(?P<open><div class="framework-cell" data-metric="(?P<metric>[^"]+)" data-value=")\{\{VALUE\}\}'
                r'(?P<mid>"><div class="framework-n">)\{\{VALUE\}\}(?P<close></div>)', cell, inner)
        elif kind == "open-row":
            pillar = PILLAR_ALIASES[node["attrs"]["data-pillar"]]
            ids = [check["check_id"] for check in records.checks_in(pillar)]
            start_tag = start_tag.replace('data-check-ids="{{CHECK_IDS}}"', f'data-check-ids="{" ".join(ids)}"')
            inner = inner.replace("{{OPEN SUMMARY}}", esc(open_summary(counts[pillar])))
            inner = inner.replace("{{CHECK ID RANGE}}", esc(id_range(ids)))
        elif kind == "pillar-count":
            inner = inner.replace("{{CHECK COUNT}}", str(len(records.checks_in(arg))))
        elif kind == "pillar-table":
            inner = "\n" + render_pillar_rows(records, arg) + "\n"
        elif kind == "evidence-requests":
            inner = "\n" + render_requests(records) + "\n"
        elif kind == "source-count":
            inner = f"{len(records.sources)} source records"
        elif kind == "source-references":
            inner = render_source_references_html(source_reference_entries(records))
        elif kind == "source-records":
            inner = "\n" + "\n".join(render_source(records, s) for s in records.sources.values()) + "\n"
        elif kind == "locator-records":
            inner = "\n" + "\n".join(render_locator(records, loc) for loc in records.locators.values()) + "\n"
        elif kind == "observation-records":
            inner = "\n" + "\n".join(render_observation(records, o) for o in records.observations.values()) + "\n"
        elif kind == "check-records":
            inner = "\n" + "\n".join(render_check(records, records.checks[cid]) for cid in records.check_order) + "\n"
        elif kind == "methodology-distribution":
            inner = render_distribution(records)
        elif kind == "technical-index":
            inner = (inner.replace("{{LOCATOR COUNT}}", str(len(records.locators)))
                          .replace("{{OBSERVATION COUNT}}", str(len(records.observations)))
                          .replace("{{CHECK COUNT}}", str(len(records.checks))))
        elif kind == "footer-counts":
            inner = (f"{len(records.checks)} checks · {len(records.observations)} observations · "
                     f"{len(records.sources)} source records")
        else:
            raise RecordError(f"the shell has an unknown data-fill region {region!r}")
        edits.append((node["start"], node["end"], start_tag + inner + f"</{node['tag']}>"))

    for pillar, heading in PILLAR_HEADING.items():
        if records.pillar_sources(pillar):
            continue
        sections = [node for node in elements_with(shell, "aria-labelledby")
                    if node["tag"] == "section" and node["attrs"]["aria-labelledby"] == heading]
        if len(sections) != 1:
            raise RecordError(f"the shell has no pillar section for {heading}")
        section = sections[0]
        start_tag = re.sub(r'\s+data-pillar-sources="[^"]*"', "", section["raw_start"])
        edits.append((section["start"], section["inner_start"],
                      start_tag[:-1] + ' data-pillar-sources="none">'))
        notes.append(f"{records.pillar_label[pillar]} cites no observations: it is marked "
                     "data-pillar-sources=\"none\"; leave its citation slots empty")

    for start, end, replacement in sorted(edits, key=lambda edit: edit[0], reverse=True):
        shell = shell[:start] + replacement + shell[end:]

    payload_marker = '<script type="application/json" id="plinth-research-state">{{ACCEPTED_RECORDS}}</script>'
    if shell.count(payload_marker) != 1:
        raise RecordError("the shell's payload placeholder was not found exactly once")
    shell = shell.replace(payload_marker,
                          f'<script type="application/json" id="plinth-research-state">{payload}</script>')
    shell = shell.replace("{{SNAPSHOT LABEL}}", "Fixed evidence snapshot · " + esc(utc_date(records.campaign["cutoff"])))
    shell = shell.replace("{{CAMPAIGN BOUNDARY}}", esc("Evidence cutoff: " + cutoff_text(records.campaign["cutoff"]) + "; " + records.campaign["declared_scope_note"]))
    shell = shell.replace("{{METHODOLOGY_CAMPAIGN_BOUNDARY}}", esc("Evidence cutoff: " + cutoff_text(records.campaign["cutoff"]) + "; " + records.campaign["declared_scope_note"]))
    shell = shell.replace("{{PRODUCT}}", esc(product))
    return shell, notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--product", required=True, help="product name shown in the title, brand and sidebar")
    parser.add_argument("--assessment", type=Path, required=True, help="the run's accepted assessment.json")
    parser.add_argument("--evidence", type=Path, required=True,
                        help="the run's accepted documentary-evidence.json")
    parser.add_argument("--catalogue", type=Path, required=True, help="inputs/catalogue.json")
    parser.add_argument("--out", type=Path, required=True, help="where to write the prefilled page")
    parser.add_argument("--shell", type=Path, default=DEFAULT_SHELL, help="the v0.3 shell (default: bundled)")
    parser.add_argument("--force", action="store_true", help="overwrite --out if it exists")
    parser.add_argument("--source-references-md", type=Path,
                        help="also write the same cited-source list as a Markdown report section")
    args = parser.parse_args(argv)
    for target in (args.out, args.source_references_md):
        if target and target.exists() and not args.force:
            print(f"FAIL: {target} exists; pass --force to overwrite", file=sys.stderr)
            return 1
    if args.source_references_md and args.source_references_md.resolve() == args.out.resolve():
        print("FAIL: HTML and Markdown outputs must be different paths", file=sys.stderr)
        return 1
    try:
        inputs = load_inputs(args.assessment, args.evidence, args.catalogue)
        page, notes = fill(args.shell.read_text(encoding="utf-8"), Records(inputs), payload_text(inputs),
                           args.product)
    except (RecordError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page, encoding="utf-8")
    if args.source_references_md:
        args.source_references_md.parent.mkdir(parents=True, exist_ok=True)
        args.source_references_md.write_text(render_source_references_md(source_reference_entries(Records(inputs))),
                                            encoding="utf-8")
    remaining = sorted(set(PLACEHOLDER_RE.findall(
        re.sub(r'<script type="application/json" id="plinth-research-state">.*?</script>', "", page, flags=re.S))))
    print(f"wrote {args.out}")
    for note in notes:
        print(f"note: {note}")
    print(f"{len(remaining)} placeholder kinds remain for the author: {', '.join(remaining)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
