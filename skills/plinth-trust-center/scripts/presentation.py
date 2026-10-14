"""Shared presentation values; canonical evidence and assessment stay unchanged."""
from datetime import datetime, timezone
import html
import re
from urllib.parse import quote
from trust_center_records import Records

def utc_date(value: str) -> str:
    """A recorded moment's UTC calendar date; never infer dates from source notes."""
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return moment.astimezone(timezone.utc).strftime("%d %b %Y").lstrip("0")


def cutoff_text(value: str) -> str:
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return moment.astimezone(timezone.utc).strftime("%d %b %Y, %H:%M UTC").lstrip("0")


def executive_counts(records: Records) -> dict[str, int]:
    counts = Records.counts(list(records.checks.values()))
    return {"Applicable checks assessed": counts["applies"] - counts["not-assessed"],
            "EVIDENCED": counts["evidenced"], "PARTIAL": counts["partial"],
            "MISSING": counts["missing"], "CONTRADICTORY": counts["contradictory"],
            "NOT_ASSESSED": counts["not-assessed"],
            "Applicability unresolved": counts["applicability-unresolved"]}


def source_reference_entries(records: Records) -> list[dict]:
    """One bibliography view shared by HTML and Markdown, bound to cited acquisitions."""
    cited: dict[str, set[str]] = {}
    for observation in records.observations.values():
        for support in observation.get("supports", []):
            acquisition = records.acquisitions[support["acquisition_id"]]
            if acquisition["outcome"] == "ACQUIRED":
                cited.setdefault(acquisition["source_id"], set()).add(acquisition["acquisition_id"])
    entries = []
    for sid, source in records.sources.items():
        if sid not in cited or source.get("disposition", "IN_SCOPE") not in {"IN_SCOPE", "SUPERSEDED"}:
            continue
        dates = sorted({datetime.fromisoformat(records.acquisitions[aid]["retrieved_at"].replace("Z", "+00:00"))
                        .astimezone(timezone.utc).date() for aid in cited[sid]
                        if records.acquisitions[aid].get("retrieved_at")})
        url = source.get("url")
        entries.append({"source_id": sid, "title": source["title"], "publisher": source.get("publisher"),
                        "url": url if url and re.match(r"https?://", url, re.I) else None,
                        "published": utc_date(source["publication_date"]) if source.get("publication_date") else None,
                        "captured": [day.strftime("%d %b %Y").lstrip("0") for day in dates],
                        "limitation": next(iter(source.get("stated_limitations", [])), None),
                        "superseded_by": source.get("superseded_by_source_id") if source.get("disposition") == "SUPERSEDED" else None})
    return entries


def render_source_references_html(entries: list[dict]) -> str:
    esc = html.escape
    items = []
    for entry in entries:
        sid = esc(entry["source_id"], quote=True)
        title = esc(entry["title"])
        if entry["url"]:
            title = f'<a href="{esc(entry["url"], quote=True)}" rel="noopener noreferrer">{title}</a>'
        publisher = f' — {esc(entry["publisher"])}' if entry["publisher"] else ""
        dates = (["Published: " + entry["published"]] if entry["published"] else [])
        if entry["captured"]:
            dates.append("Captured: " + ", ".join(entry["captured"]))
        details = f'<span class="source-reference-detail">{esc(" · ".join(dates))}</span>' if dates else ""
        limitation = f'<p class="source-reference-note">{esc(entry["limitation"])}</p>' if entry["limitation"] else ""
        successor = (f'<span class="source-reference-detail">Superseded by '
                     f'<a href="#source-{esc(entry["superseded_by"], quote=True)}">{esc(entry["superseded_by"])}</a></span>'
                     if entry["superseded_by"] else "")
        items.append(f'<li data-reference-source="{sid}">{title}{publisher} '
                     f'<a class="source-reference-detail" href="#source-{sid}">Full source record ↗</a>'
                     f'{details}{successor}{limitation}</li>')
    return ('<h3>Source references</h3><p>Documents supporting observations. Dates are UTC calendar dates and distinguish publication from cited captures. '
            'The full registry also retains uncited and excluded records.</p><ul class="source-reference-list">'
            + "".join(items) + '</ul>' if items else '<h3>Source references</h3><p>No acquired source supports an observation.</p>')


def markdown_text(value: str) -> str:
    return re.sub(r"([\\`*_{}\[\]<>|])", r"\\\1", value).replace("\n", " ")


def render_source_references_md(entries: list[dict]) -> str:
    lines = ["## Source references", "",
             "Documents supporting observations. Dates are UTC calendar dates and distinguish publication from cited captures.", ""]
    for entry in entries:
        title = markdown_text(entry["title"])
        if entry["url"]:
            # Angle-delimited destinations keep parentheses from ending Markdown links.
            url = quote(entry["url"], safe=":/?#@!$&'()*+,;=%")
            title = f"[{title}](<{url}>)"
        publisher = " — " + markdown_text(entry["publisher"]) if entry["publisher"] else ""
        sid = markdown_text(entry["source_id"])
        anchor = quote(entry["source_id"], safe="-._~")
        lines.append(f"- {title}{publisher}. [Full source record: {sid}](index.html#source-{anchor}).")
        dates = (["Published: " + entry["published"]] if entry["published"] else [])
        if entry["captured"]:
            dates.append("Captured: " + ", ".join(entry["captured"]))
        if dates:
            lines.append("  " + " · ".join(dates) + ".")
        if entry["superseded_by"]:
            successor = entry["superseded_by"]
            lines.append(f"  Superseded by [{markdown_text(successor)}](index.html#source-{quote(successor, safe='-._~')}).")
        if entry["limitation"]:
            lines.append("  " + markdown_text(entry["limitation"]))
        lines.append("")
    if not entries:
        lines += ["No acquired source supports an observation.", ""]
    return "\n".join(lines)

