"""Shared presentation values; canonical evidence and assessment stay unchanged."""
from datetime import datetime, timezone
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

