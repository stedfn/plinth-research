"""Shared, stdlib-only views of one run's accepted records for the Trust Center scripts.

Both ``prefill_shell.py`` and ``check_morphed_html.py`` read the same three files:
a run's accepted ``assessment.json`` and ``documentary-evidence.json``, and the
pinned ``inputs/catalogue.json``. ``plinth verify`` is what proves those records
are valid; this module only proves the three files belong together, and indexes
them for rendering and checking.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ASSESSMENT_SCHEMA = "plinth.assessment/1"
EVIDENCE_SCHEMA = "plinth.evidence/1"

# Catalogue pillar_id -> the key the v0.3 interface uses in ids, CSS classes and
# data-pillar ("checks-governance", "pillar-governance").
DOM_PILLAR = {
    "control": "control",
    "backing": "backing",
    "economics": "economics",
    "governance_compliance": "governance",
    "continuity": "continuity",
}
# Catalogue pillar_id -> the pillar panel's heading id. The v0.3 interface kept
# its original ids, so Assets & Backing is still "pillar-reserves".
PILLAR_HEADING = {
    "control": "pillar-control",
    "backing": "pillar-reserves",
    "economics": "pillar-economics",
    "governance_compliance": "pillar-governance-compliance",
    "continuity": "pillar-continuity",
}
# Every spelling a page may use in data-pillar, mapped to the catalogue pillar_id.
PILLAR_ALIASES = {
    **{dom: pillar for pillar, dom in DOM_PILLAR.items()},
    **{pillar: pillar for pillar in DOM_PILLAR},
    "governance-compliance": "governance_compliance",
}
# Source research_posture -> the interface's data-evidence-class styling hook.
EVIDENCE_CLASS = {
    "self_attestation": "issuer_declared",
    "commissioned_research": "third_party_authored",
    "independent_assurance": "third_party_authored",
    "rating": "third_party_authored",
    "unaffiliated_research": "third_party_authored",
}


class RecordError(ValueError):
    """The assessment, evidence and catalogue files do not belong together."""


@dataclass(frozen=True)
class Inputs:
    assessment: dict
    evidence: dict
    catalogue: dict


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path, label: str) -> tuple[bytes, dict]:
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise RecordError(f"cannot read {label} {path}: {exc}") from exc
    try:
        value = json.loads(raw)
    except ValueError as exc:
        raise RecordError(f"{label} {path} is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise RecordError(f"{label} {path} is not a JSON object")
    return raw, value


def load_inputs(assessment_path, evidence_path, catalogue_path) -> Inputs:
    """Read the three files and prove they describe one run against one catalogue."""
    assessment_raw, assessment = _read_json(assessment_path, "assessment")
    evidence_raw, evidence = _read_json(evidence_path, "evidence")
    catalogue_raw, catalogue = _read_json(catalogue_path, "catalogue")

    if assessment.get("schema_version") != ASSESSMENT_SCHEMA:
        raise RecordError(f"assessment schema_version is {assessment.get('schema_version')!r}, "
                          f"expected {ASSESSMENT_SCHEMA!r}")
    if evidence.get("schema_version") != EVIDENCE_SCHEMA:
        raise RecordError(f"evidence schema_version is {evidence.get('schema_version')!r}, "
                          f"expected {EVIDENCE_SCHEMA!r}")
    meta = assessment.get("meta") or {}
    if meta.get("catalogue_sha256") != sha256(catalogue_raw):
        raise RecordError("assessment meta.catalogue_sha256 does not match the catalogue file; "
                          "pass the catalogue the run was assessed against")
    if meta.get("evidence_pack_sha256") != sha256(evidence_raw):
        raise RecordError("assessment meta.evidence_pack_sha256 does not match the evidence file; "
                          "pass the accepted documentary-evidence.json of the same run")
    run_id = (evidence.get("campaign") or {}).get("run_id")
    if meta.get("campaign_run_id") != run_id:
        raise RecordError(f"assessment belongs to run {meta.get('campaign_run_id')!r} "
                          f"but the evidence belongs to run {run_id!r}")
    expected = [check["check_id"] for check in catalogue["checks"]]
    actual = [check.get("check_id") for check in assessment.get("checks", [])]
    if actual != expected:
        raise RecordError("assessment checks are not exactly the catalogue's checks in catalogue order")
    return Inputs(assessment=assessment, evidence=evidence, catalogue=catalogue)


def payload_text(inputs: Inputs) -> str:
    """The embedded payload: both accepted records, with every '<' escaped.

    The escape keeps an archived quote such as ``</script>`` from ending the
    script element early; ``json.loads`` returns the identical records.
    """
    text = json.dumps({"assessment": inputs.assessment, "evidence": inputs.evidence},
                      ensure_ascii=False, separators=(",", ":"))
    return text.replace("<", "\\u003c")


def badge_class(value: str) -> str:
    """Interface badge class for an applicability, coverage or outcome value."""
    return value.lower().replace("_", "-")


class Records:
    """Indexes over one run's accepted records and the catalogue."""

    def __init__(self, inputs: Inputs) -> None:
        catalogue = inputs.catalogue
        self.framework_version = catalogue["framework_version"]
        self.check_order = [check["check_id"] for check in catalogue["checks"]]
        self.question = {check["check_id"]: check["question"] for check in catalogue["checks"]}
        self.pillar_of = {check["check_id"]: check["pillar_id"] for check in catalogue["checks"]}
        self.pillar_ids = [pillar["pillar_id"] for pillar in catalogue["pillars"]]
        self.pillar_label = {pillar["pillar_id"]: pillar["display_label"] for pillar in catalogue["pillars"]}
        self.gap_fields = list(catalogue["gap_contract"]["fields"])
        self.gap_labels = dict(catalogue["gap_contract"]["display_labels"])

        self.checks = {check["check_id"]: check for check in inputs.assessment["checks"]}
        evidence = inputs.evidence
        self.campaign = evidence["campaign"]
        self.sources = {source["source_id"]: source for source in evidence.get("sources", [])}
        self.acquisitions = {item["acquisition_id"]: item for item in evidence.get("acquisitions", [])}
        self.artifacts = {item["sha256"]: item for item in evidence.get("artifacts", [])}
        self.locators = {item["locator_id"]: item for item in evidence.get("locator_catalog", [])}
        self.observations = {item["observation_id"]: item for item in evidence.get("observations", [])}
        self.routes = list(evidence.get("routes", []))

        self.acquisitions_by_source: dict[str, list[dict]] = defaultdict(list)
        self.sources_by_artifact: dict[str, list[str]] = defaultdict(list)
        for acquisition in evidence.get("acquisitions", []):
            self.acquisitions_by_source[acquisition["source_id"]].append(acquisition)
            artifact = acquisition.get("artifact_sha256")
            if artifact and acquisition["source_id"] not in self.sources_by_artifact[artifact]:
                self.sources_by_artifact[artifact].append(acquisition["source_id"])
        self.observations_by_locator: dict[str, list[str]] = defaultdict(list)
        for observation in evidence.get("observations", []):
            for support in observation.get("supports", []):
                self.observations_by_locator[support["locator_id"]].append(observation["observation_id"])

    def checks_in(self, pillar_id: str) -> list[dict]:
        return [self.checks[cid] for cid in self.check_order if self.pillar_of[cid] == pillar_id]

    @staticmethod
    def cited_observation_ids(check: dict) -> list[str]:
        """Every observation a check cites, in first-citation order."""
        cited = list(check.get("applicability_observation_ids", []))
        cited += check.get("finding_observation_ids", [])
        if check.get("gap"):
            cited += check["gap"].get("evidence_observation_ids", [])
        if check.get("contradiction"):
            cited += check["contradiction"].get("conflicting_observation_ids", [])
        return list(dict.fromkeys(cited))

    def observation_sources(self, observation_id: str, _seen: frozenset = frozenset()) -> set[str]:
        """Sources behind an observation, following derivation lineage to its parents."""
        if observation_id in _seen or observation_id not in self.observations:
            return set()
        observation = self.observations[observation_id]
        found = set()
        for support in observation.get("supports", []):
            acquisition = self.acquisitions.get(support["acquisition_id"])
            if acquisition:
                found.add(acquisition["source_id"])
        for parent in observation.get("parent_observation_ids", []):
            found |= self.observation_sources(parent, _seen | {observation_id})
        return found

    def pillar_observation_ids(self, pillar_id: str) -> list[str]:
        cited: list[str] = []
        for check in self.checks_in(pillar_id):
            cited += self.cited_observation_ids(check)
        return list(dict.fromkeys(cited))

    def pillar_sources(self, pillar_id: str) -> set[str]:
        found: set[str] = set()
        for observation_id in self.pillar_observation_ids(pillar_id):
            found |= self.observation_sources(observation_id)
        return found

    @staticmethod
    def counts(checks: list[dict]) -> dict[str, int]:
        def applicability(value):
            return sum(check["applicability"] == value for check in checks)

        def coverage(value):
            return sum(check.get("coverage") == value for check in checks)

        return {
            "total": len(checks),
            "applies": applicability("APPLIES"),
            "applicability-unresolved": applicability("UNRESOLVED"),
            "does-not-apply": applicability("DOES_NOT_APPLY"),
            "applicable-not-fully-answered": sum(
                check["applicability"] == "APPLIES" and check.get("coverage") != "EVIDENCED"
                for check in checks),
            "evidenced": coverage("EVIDENCED"),
            "partial": coverage("PARTIAL"),
            "missing": coverage("MISSING"),
            "contradictory": coverage("CONTRADICTORY"),
            "not-assessed": coverage("NOT_ASSESSED"),
        }

    def metrics(self) -> dict[str, int]:
        """The four figures the Executive framework strip shows."""
        counts = self.counts([self.checks[cid] for cid in self.check_order])
        return {key: counts[key] for key in
                ("total", "applies", "applicability-unresolved", "applicable-not-fully-answered")}

    @staticmethod
    def result(check: dict) -> str:
        """A check's one-word result: coverage when it applies, else applicability."""
        if check["applicability"] == "APPLIES":
            return check["coverage"]
        return check["applicability"]
