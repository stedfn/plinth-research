#!/usr/bin/env python3
"""Check a Plinth v0.2 assessment against the versioned framework catalogue."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


CHECK_HEADING = re.compile(r"^### (PF-[A-Z]+-\d{3}) — (.+)$", re.MULTILINE)
APPLICABILITY = {"APPLIES", "DOES_NOT_APPLY", "UNRESOLVED"}
APPLIES_COVERAGE = {"EVIDENCED", "PARTIAL", "MISSING", "NOT_ASSESSED", "CONTRADICTORY"}
GAP_KEYS = {
    "question",
    "what_is_known",
    "what_remains_unresolved",
    "what_this_means",
    "what_would_close_it",
    "evidence",
}


def fail(message: str) -> None:
    raise AssertionError(message)


def nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def check_cycle(observations: dict[str, dict]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(obs_id: str) -> None:
        if obs_id in visiting:
            fail(f"derived-observation cycle contains {obs_id}")
        if obs_id in visited:
            return
        visiting.add(obs_id)
        for parent in observations[obs_id].get("parent_observation_ids", []):
            if parent not in observations:
                fail(f"unknown parent observation {parent} referenced by {obs_id}")
            visit(parent)
        visiting.remove(obs_id)
        visited.add(obs_id)

    for obs_id in observations:
        visit(obs_id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("framework", type=Path)
    parser.add_argument("assessment", type=Path)
    args = parser.parse_args()

    framework_text = args.framework.read_text(encoding="utf-8")
    catalogue = CHECK_HEADING.findall(framework_text)
    if len(catalogue) != 63:
        fail(f"framework must expose exactly 63 check headings; found {len(catalogue)}")
    catalogue_ids = [item[0] for item in catalogue]
    if len(set(catalogue_ids)) != len(catalogue_ids):
        fail("framework contains duplicate check IDs")

    assessment = json.loads(args.assessment.read_text(encoding="utf-8"))
    checks = assessment.get("checks")
    observations_raw = assessment.get("observations")
    if not isinstance(checks, list) or not isinstance(observations_raw, list):
        fail("assessment must contain checks[] and observations[]")

    check_ids = [record.get("id") for record in checks]
    if Counter(check_ids) != Counter(catalogue_ids):
        missing = sorted(set(catalogue_ids) - set(check_ids))
        extra = sorted(set(check_ids) - set(catalogue_ids))
        fail(f"assessment check population differs from framework; missing={missing}, extra={extra}")

    questions = dict(catalogue)
    observation_ids = [record.get("id") for record in observations_raw]
    if any(not nonempty_text(obs_id) for obs_id in observation_ids):
        fail("every observation must have a non-empty ID")
    if len(set(observation_ids)) != len(observation_ids):
        fail("observation IDs must be unique")
    observations = {record["id"]: record for record in observations_raw}

    required_observation_fields = {
        "statement",
        "subject_scope",
        "observed_at_or_effective_period",
        "acquisition_mode",
    }
    for obs_id, record in observations.items():
        for field in required_observation_fields:
            if not nonempty_text(record.get(field)):
                fail(f"{obs_id} lacks {field}")
        source_refs = record.get("source_refs")
        if not isinstance(source_refs, list):
            fail(f"{obs_id} source_refs must be a list")
        for source_ref in source_refs:
            if not nonempty_text(source_ref.get("source_id")) or not nonempty_text(source_ref.get("locator_id")):
                fail(f"{obs_id} contains an incomplete source reference")
        parents = record.get("parent_observation_ids", [])
        if not isinstance(parents, list):
            fail(f"{obs_id} parent_observation_ids must be a list")
        if parents and not nonempty_text(record.get("derivation")):
            fail(f"derived observation {obs_id} lacks a derivation explanation")

    check_cycle(observations)

    for record in checks:
        check_id = record["id"]
        if record.get("question") != questions[check_id]:
            fail(f"question differs from framework for {check_id}")
        applicability = record.get("applicability")
        coverage = record.get("coverage")
        if applicability not in APPLICABILITY:
            fail(f"invalid applicability for {check_id}: {applicability}")
        if not nonempty_text(record.get("finding")):
            fail(f"{check_id} lacks a neutral finding")

        obs_refs = record.get("observation_ids")
        if not isinstance(obs_refs, list):
            fail(f"{check_id} observation_ids must be a list")
        unknown = sorted(set(obs_refs) - set(observations))
        if unknown:
            fail(f"{check_id} references unknown observations: {unknown}")

        if not isinstance(record.get("searched_routes"), list):
            fail(f"{check_id} searched_routes must be a list")
        if not isinstance(record.get("search_completed"), bool):
            fail(f"{check_id} search_completed must be boolean")

        needs_gap = False
        if applicability == "APPLIES":
            if coverage not in APPLIES_COVERAGE:
                fail(f"invalid coverage for applicable {check_id}: {coverage}")
            needs_gap = coverage != "EVIDENCED"
            if coverage == "MISSING" and not record["search_completed"]:
                fail(f"{check_id} uses MISSING without a completed search")
        elif applicability == "DOES_NOT_APPLY":
            if coverage != "NOT_APPLICABLE" or not obs_refs:
                fail(f"{check_id} DOES_NOT_APPLY requires NOT_APPLICABLE and positive observations")
        else:
            if coverage is not None:
                fail(f"{check_id} UNRESOLVED applicability requires null coverage")
            needs_gap = True

        gap = record.get("gap")
        if needs_gap:
            legacy_gap = isinstance(gap, dict) and set(gap) == GAP_KEYS
            lossless_gap = isinstance(gap, dict) and set(gap) == GAP_KEYS | {"evidence_observation_ids"}
            if not legacy_gap and not lossless_gap:
                fail(f"{check_id} requires the exact six-field gap contract")
            for field in GAP_KEYS - {"evidence"}:
                if not nonempty_text(gap.get(field)):
                    fail(f"{check_id} gap field {field} is empty")
            evidence_refs = gap["evidence"] if legacy_gap else gap["evidence_observation_ids"]
            if lossless_gap and not nonempty_text(gap["evidence"]):
                fail(f"{check_id} canonical gap evidence prose is empty")
            if not isinstance(evidence_refs, list):
                fail(f"{check_id} gap evidence must be a list")
            unknown_gap_refs = sorted(set(evidence_refs) - set(observations))
            if unknown_gap_refs:
                fail(f"{check_id} gap references unknown observations: {unknown_gap_refs}")
        elif gap is not None and not isinstance(gap, dict):
            fail(f"{check_id} gap must be null or an object")

    print(
        f"PASS: {len(checks)} framework checks; "
        f"{len(observations)} observations; applicability, coverage, gaps, and lineage valid"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
