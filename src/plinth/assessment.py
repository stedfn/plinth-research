"""C5 policy and the deterministic, same-host assessment handoff packet.

The caller validates accepted evidence against its run before invoking these
functions. C2 remains the definition of record validity; C5 adds acceptance
policy without changing those models. No LLM is executed here.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from . import catalogue as cat
from .archive import LoadedRun
from .models import Assessment, EvidencePack, Issue, canonical_sha256
from .validate import issue, validate_assessment, validate_assessment_against_pack
from .vocab import Coverage

PACKET_NAME = "assessment-packet.json"
PROPOSED_ASSESSMENT_NAME = "proposed-assessment.json"
ISSUES_NAME = "proposed-assessment.issues.json"
ACCEPTED_ASSESSMENT_NAME = "assessment.json"
PROMPT_PATH = cat.PROJECT_ROOT / "prompts" / "assessment.md"


def canonical_check_order(catalogue: dict) -> list[str]:
    return [check["check_id"] for check in catalogue["checks"]]


def assess_assessment_for_run(
    raw: object, *, run: LoadedRun, pack: EvidencePack, catalogue: dict,
) -> tuple[Assessment | None, tuple[Issue, ...]]:
    """Compose C2 validation and X7–X11; a constructed model is not a verdict."""
    assessment, problems = validate_assessment(raw)
    if assessment is None:
        return None, problems
    found = list(validate_assessment_against_pack(assessment, pack))
    # A run pins bytes, not catalogue validity. Check the small structure C5
    # consumes before indexing it; full source reconstruction remains packet-only.
    framework_version = catalogue.get("framework_version")
    checks = catalogue.get("checks")
    if (
        not isinstance(framework_version, str) or not framework_version.strip()
        or not isinstance(checks, list) or len(checks) != cat.TOTAL_CHECKS
        or any(
            not isinstance(check, dict)
            or any(not isinstance(check.get(key), str) or not check[key].strip()
                   for key in ("check_id", "question"))
            for check in checks
        )
    ):
        found.append(issue("invalid_catalogue", "pinned catalogue must contain a nonempty "
                           "framework_version and 63 check objects with string check_id and "
                           "question fields; run: plinth catalogue verify"))
        return assessment, tuple(found)
    if len({check["check_id"] for check in checks}) != len(checks):
        found.append(issue("invalid_catalogue", "pinned catalogue has duplicate check IDs; "
                           "run: plinth catalogue verify"))
        return assessment, tuple(found)
    if assessment.meta.catalogue_sha256 != run.manifest.catalogue_sha256:
        found.append(issue("X7", "catalogue_sha256 differs from the run manifest",
                           "meta", "catalogue_sha256"))
    if assessment.meta.framework_version != framework_version:
        found.append(issue("X8", "framework_version differs from the catalogue",
                           "meta", "framework_version"))
    expected = canonical_check_order(catalogue)
    actual = [check.check_id for check in assessment.checks]
    actual_ids = set(actual)
    expected_ids = set(expected)
    for check_id in expected:
        if check_id not in actual_ids:
            found.append(issue("X9", f"missing catalogue check {check_id}", "checks"))
    for index, check_id in enumerate(actual):
        if check_id not in expected_ids:
            found.append(issue("X9", f"unexpected check {check_id}", "checks", index, "check_id"))
    if actual != expected:
        found.append(issue("X9", "checks must appear exactly once in canonical catalogue order",
                           "checks"))
    questions = {check["check_id"]: check["question"] for check in catalogue["checks"]}
    for index, check in enumerate(assessment.checks):
        if (check.gap is not None and check.check_id in questions
                and check.gap.question != questions[check.check_id]):
            found.append(issue("X10", "gap.question must exactly equal the catalogue question",
                               "checks", index, "gap", "question"))
        if check.coverage is Coverage.MISSING:
            found.append(issue("X11", "MISSING is disabled until route completion is trustworthy; "
                               "use NOT_ASSESSED for unfinished routes or activities",
                               "checks", index, "coverage"))
    return assessment, tuple(found)


def build_assessment_packet(*, run: LoadedRun, pack: EvidencePack, catalogue: dict) -> dict:
    """Build a derived packet after full catalogue reconstruction and verification.

    No wall-clock timestamp: identical pinned inputs yield identical bytes.
    ``generated_at`` is chosen by the assessor, bounded below by the pack.
    """
    failures = cat.verify(catalogue, cat.INPUTS_DIR)
    if failures:
        raise cat.BuildError("; ".join(failure.render() for failure in failures))

    def pin(path: Path) -> dict:
        return {"path": str(path.resolve()),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    prompt = PROMPT_PATH.read_bytes()
    return {
        "schema_version": "plinth.assessment-packet/1",
        "run_id": run.manifest.campaign.run_id,
        "campaign": run.manifest.campaign.model_dump(mode="json"),
        "prompt": {"text": prompt.decode("utf-8"),
                   "sha256": hashlib.sha256(prompt).hexdigest()},
        "inputs": {
            "framework": pin(cat.INPUTS_DIR / cat.FRAMEWORK_MD),
            "output_contract": pin(cat.INPUTS_DIR / cat.OUTPUT_CONTRACT_MD),
            "catalogue": pin(cat.CATALOGUE_PATH),
            "evidence_pack": pin(run.accepted_pack_path),
        },
        "check_order": canonical_check_order(catalogue),
        "checks": [{key: check[key] for key in ("check_id", "pillar_id", "question", "fields")}
                   for check in catalogue["checks"]],
        "assessment_json_schema": Assessment.model_json_schema(),
        "assessment_meta": {
            "campaign_run_id": run.manifest.campaign.run_id,
            "framework_version": catalogue["framework_version"],
            "catalogue_sha256": run.manifest.catalogue_sha256,
            "evidence_pack_sha256": canonical_sha256(pack),
        },
        "generated_at_not_before": pack.model_dump(mode="json")["generated_at"],
        "missing_coverage_enabled": False,
        "output_path": str((run.root / PROPOSED_ASSESSMENT_NAME).resolve()),
    }
