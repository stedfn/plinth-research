"""Gates for the evidence and assessment models.

One happy-path fixture pair, understandable end to end, plus one mutation per
rule. Lifecycle states are reached by mutation rather than baked into the
sample: a fixture carrying every legal combination would be unreadable and would
still not prove that the illegal ones are rejected.

Two sources rather than one, because a single-source pack cannot express "a
locator belonging to the other source's artifact" -- the mutation that proves
``P3``.

Each mutation asserts **the target code is present**, not that it is the only
error. One field change can legitimately trip two invariants, and "and no other
error" assertions turn every future rule into a broken test.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from plinth.catalogue import GAP_RULES
from plinth.models import (
    LOCATOR_REQUIRED_FIELDS,
    Assessment,
    CheckAssessment,
    EvidencePack,
    Issue,
    canonical_bytes,
    canonical_sha256,
)
from plinth.validate import (
    escape_token,
    pointer,
    validate_assessment,
    validate_assessment_against_pack,
    validate_pack,
)
from plinth.vocab import Applicability, Coverage, LocatorType

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PACK_JSON = FIXTURES / "pack-ousg-backing-006.json"
ASSESSMENT_JSON = FIXTURES / "assessment-ousg-backing-006.json"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pack_document() -> dict:
    return json.loads(PACK_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def assessment_document() -> dict:
    return json.loads(ASSESSMENT_JSON.read_text(encoding="utf-8"))


@pytest.fixture
def pack_doc(pack_document: dict) -> dict:
    return copy.deepcopy(pack_document)


@pytest.fixture
def assessment_doc(assessment_document: dict) -> dict:
    return copy.deepcopy(assessment_document)


def codes(issues) -> list[str]:
    return sorted({issue.code for issue in issues})


def rendered(issues) -> str:
    return "\n".join(issue.render() for issue in issues)


def assert_code(issues, code: str) -> None:
    assert code in codes(issues), f"expected {code}; got:\n{rendered(issues) or '  (no issues)'}"


def assert_clean(issues) -> None:
    assert not issues, f"expected no issues; got:\n{rendered(issues)}"


def pack_issues(document: object):
    return validate_pack(document)[1]


def assessment_issues(document: object):
    return validate_assessment(document)[1]


def cross_issues(pack_doc: dict, assessment_doc: dict, *, repin: bool = True):
    """Validate both artifacts and cross-check them.

    ``repin`` recomputes ``meta.evidence_pack_sha256`` so that a test about a
    route or an observation is not also a test about ``X4``. The two X4 tests
    turn it off, because the digest is the thing they are about.
    """
    pack, problems = validate_pack(pack_doc)
    assert_clean(problems)
    if repin:
        assessment_doc["meta"]["evidence_pack_sha256"] = canonical_sha256(pack)
    assessment, problems = validate_assessment(assessment_doc)
    assert_clean(problems)
    return validate_assessment_against_pack(assessment, pack)


def only_check(assessment_doc: dict) -> dict:
    return assessment_doc["checks"][0]


def observation(pack_doc: dict, observation_id: str) -> dict:
    return next(o for o in pack_doc["observations"] if o["observation_id"] == observation_id)


def source(pack_doc: dict, source_id: str) -> dict:
    return next(s for s in pack_doc["sources"] if s["source_id"] == source_id)


def acquisition(pack_doc: dict, acquisition_id: str) -> dict:
    return next(
        a for a in pack_doc["acquisitions"] if a["acquisition_id"] == acquisition_id
    )


def locator(pack_doc: dict, locator_id: str) -> dict:
    return next(loc for loc in pack_doc["locator_catalog"] if loc["locator_id"] == locator_id)


def route(pack_doc: dict, route_id: str) -> dict:
    return next(r for r in pack_doc["routes"] if r["route_id"] == route_id)


# --------------------------------------------------------------------------
# happy path
# --------------------------------------------------------------------------


def test_fixture_pack_validates(pack_doc: dict) -> None:
    pack, issues = validate_pack(pack_doc)
    assert_clean(issues)
    assert isinstance(pack, EvidencePack)
    assert pack.schema_version == "plinth.evidence/1"
    assert len(pack.observations) == 3


def test_fixture_assessment_validates(assessment_doc: dict) -> None:
    assessment, issues = validate_assessment(assessment_doc)
    assert_clean(issues)
    assert isinstance(assessment, Assessment)
    assert assessment.checks[0].check_id == "PF-BACKING-006"


def test_fixture_assessment_matches_its_pack(pack_doc: dict, assessment_doc: dict) -> None:
    assert_clean(cross_issues(pack_doc, assessment_doc, repin=False))


def test_committed_pack_digest_is_pinned(pack_doc: dict, assessment_doc: dict) -> None:
    """The fixture's own digest pins the canonical form against silent drift.

    If ``canonical_bytes`` ever changes what it emits, this fails with the value
    to paste back into the fixture rather than with an unexplained X4 failure
    somewhere else.
    """
    pack, _ = validate_pack(pack_doc)
    digest = canonical_sha256(pack)
    assert assessment_doc["meta"]["evidence_pack_sha256"] == digest, (
        "the canonical form of the pack fixture changed; update "
        f"assessment-ousg-backing-006.json meta.evidence_pack_sha256 to {digest}"
    )


# --------------------------------------------------------------------------
# base configuration
# --------------------------------------------------------------------------


def test_unknown_key_is_rejected_with_its_path(pack_doc: dict) -> None:
    pack_doc["campaign"]["confidence_score"] = 0.9
    issues = pack_issues(pack_doc)
    assert_code(issues, "extra_forbidden")
    assert any(i.pointer == "/campaign/confidence_score" for i in issues), rendered(issues)


def test_stringified_bool_is_rejected(pack_doc: dict) -> None:
    pack_doc["campaign"]["bounded_public_evidence"] = "true"
    issues = pack_issues(pack_doc)
    assert_code(issues, "bool_type")
    assert any(i.pointer == "/campaign/bounded_public_evidence" for i in issues)


def test_stringified_int_is_rejected(pack_doc: dict) -> None:
    pack_doc["artifacts"][0]["byte_length"] = "418233"
    assert_code(pack_issues(pack_doc), "int_type")


def test_bogus_check_id_is_rejected(assessment_doc: dict) -> None:
    only_check(assessment_doc)["check_id"] = "PF-BOGUS-999"
    issues = assessment_issues(assessment_doc)
    assert_code(issues, "string_pattern_mismatch")
    assert any(i.pointer == "/checks/0/check_id" for i in issues)


def test_observation_value_must_be_a_scalar(pack_doc: dict) -> None:
    """A container here would stay mutable inside a shallow-frozen record."""
    observation(pack_doc, "OBS_CUSTODY_002")["value"] = {"amount": 1}
    issues = pack_issues(pack_doc)
    assert_code(issues, "scalar_value")
    assert any(i.pointer == "/observations/1/value" for i in issues), rendered(issues)


@pytest.mark.parametrize("value", [None, "one relationship", 1, "42000000.00", True])
def test_observation_value_accepts_every_exact_json_scalar(
    pack_doc: dict, value: object
) -> None:
    target = observation(pack_doc, "OBS_CUSTODY_002")
    target["value"] = value
    if value is None:
        target.pop("unit")
    assert_clean(pack_issues(pack_doc))


def test_naive_datetime_is_rejected(pack_doc: dict) -> None:
    pack_doc["campaign"]["cutoff"] = "2026-09-01T00:00:00"
    assert_code(pack_issues(pack_doc), "timezone_aware")


def test_offset_datetimes_normalize_to_utc(pack_doc: dict) -> None:
    pack_doc["campaign"]["cutoff"] = "2026-08-31T20:00:00-04:00"
    pack, issues = validate_pack(pack_doc)
    assert_clean(issues)
    assert pack.campaign.cutoff.isoformat() == "2026-09-01T00:00:00+00:00"


def test_models_are_frozen(pack_doc: dict) -> None:
    pack, _ = validate_pack(pack_doc)
    with pytest.raises(Exception):
        pack.campaign.subject = "something else"


# --------------------------------------------------------------------------
# malformed input
# --------------------------------------------------------------------------


def test_top_level_array_is_an_issue_not_an_exception() -> None:
    assert_code(pack_issues("[]"), "not_an_object")


def test_invalid_utf8_is_an_issue_not_an_exception() -> None:
    assert_code(pack_issues(b"{\xff}"), "invalid_utf8")


def test_truncated_json_is_an_issue_not_an_exception(pack_doc: dict) -> None:
    truncated = json.dumps(pack_doc)[: len(json.dumps(pack_doc)) // 2]
    assert_code(pack_issues(truncated), "invalid_json")


def test_empty_document_reports_missing_fields() -> None:
    pack, issues = validate_pack({})
    assert pack is None
    assert_code(issues, "missing")


# --------------------------------------------------------------------------
# pointers
# --------------------------------------------------------------------------


def test_pointer_escapes_rfc_6901_reserved_characters() -> None:
    assert pointer("a/b", "c~d", 2) == "/a~1b/c~0d/2"
    assert escape_token("~/") == "~0~1"
    assert pointer() == ""


def test_unknown_key_pointer_is_escaped(pack_doc: dict) -> None:
    pack_doc["campaign"]["m~/x"] = 1
    issues = pack_issues(pack_doc)
    assert any(i.pointer == "/campaign/m~0~1x" for i in issues), rendered(issues)


def test_issue_renders_the_whole_document_readably() -> None:
    assert Issue(pointer="", code="not_an_object", message="nope").render().endswith(
        "<document>: nope"
    )


# --------------------------------------------------------------------------
# Source -- S1, S2
# --------------------------------------------------------------------------


def test_s1_excluded_source_states_its_reason(pack_doc: dict) -> None:
    source(pack_doc, "src-ondo-docs")["disposition"] = "EXCLUDED"
    assert_code(pack_issues(pack_doc), "S1")


def test_s2_superseded_source_names_its_successor(pack_doc: dict) -> None:
    source(pack_doc, "src-ondo-docs")["disposition"] = "SUPERSEDED"
    assert_code(pack_issues(pack_doc), "S2")


def test_s2_source_cannot_supersede_itself(pack_doc: dict) -> None:
    target = source(pack_doc, "src-ondo-docs")
    target["disposition"] = "SUPERSEDED"
    target["superseded_by_source_id"] = "src-ondo-docs"
    assert_code(pack_issues(pack_doc), "S2")


# --------------------------------------------------------------------------
# Acquisition -- A1..A4
# --------------------------------------------------------------------------


def test_a1_acquired_needs_an_artifact(pack_doc: dict) -> None:
    acquisition(pack_doc, "acq-ondo-docs").pop("artifact_sha256")
    assert_code(pack_issues(pack_doc), "A1")


def test_a1_acquired_needs_a_retrieval_time(pack_doc: dict) -> None:
    acquisition(pack_doc, "acq-ondo-docs").pop("retrieved_at")
    assert_code(pack_issues(pack_doc), "A1")


def test_a1_blocked_acquisition_carries_no_artifact(pack_doc: dict) -> None:
    target = acquisition(pack_doc, "acq-ondo-docs")
    target["outcome"] = "ACCESS_BLOCKED"
    target["failure_reason"] = "The document is behind an account wall."
    target.pop("retrieved_at")
    assert_code(pack_issues(pack_doc), "A1")


def test_a2_retrieval_cannot_precede_the_attempt(pack_doc: dict) -> None:
    acquisition(pack_doc, "acq-ondo-docs")["retrieved_at"] = "2026-09-02T08:00:00Z"
    assert_code(pack_issues(pack_doc), "A2")


def test_a3_failed_acquisition_states_why(pack_doc: dict) -> None:
    target = acquisition(pack_doc, "acq-ondo-docs")
    target["outcome"] = "NOT_FOUND"
    target.pop("artifact_sha256")
    target.pop("retrieved_at")
    assert_code(pack_issues(pack_doc), "A3")


def test_a4_manual_upload_names_its_operator(pack_doc: dict) -> None:
    acquisition(pack_doc, "acq-ondo-docs")["acquisition_mode"] = "MANUAL_UPLOAD"
    assert_code(pack_issues(pack_doc), "A4")


# --------------------------------------------------------------------------
# Artifact and Locator -- AR1, L1, L2
# --------------------------------------------------------------------------


def test_ar1_extracted_text_names_its_tool(pack_doc: dict) -> None:
    pack_doc["artifacts"][0].pop("text_extraction_tool")
    assert_code(pack_issues(pack_doc), "AR1")


def test_ar1_named_tool_produces_a_digest(pack_doc: dict) -> None:
    pack_doc["artifacts"][0].pop("text_sha256")
    assert_code(pack_issues(pack_doc), "AR1")


def test_l1_declared_type_carries_its_address(pack_doc: dict) -> None:
    locator(pack_doc, "loc-custodian-balance").pop("page")
    assert_code(pack_issues(pack_doc), "L1")


def test_l1_text_span_needs_both_offsets(pack_doc: dict) -> None:
    target = locator(pack_doc, "loc-custodian-balance")
    target.pop("page")
    target["locator_type"] = "text_span"
    target["char_start"] = 100
    issues = pack_issues(pack_doc)
    assert_code(issues, "L1")
    assert "char_end" in rendered(issues)


def test_l2_page_numbering_starts_at_one(pack_doc: dict) -> None:
    locator(pack_doc, "loc-custodian-balance")["page"] = 0
    assert_code(pack_issues(pack_doc), "L2")


def test_l2_span_must_be_non_empty(pack_doc: dict) -> None:
    target = locator(pack_doc, "loc-custodian-balance")
    target.pop("page")
    target["locator_type"] = "text_span"
    target["char_start"] = 100
    target["char_end"] = 100
    assert_code(pack_issues(pack_doc), "L2")


def test_l2_offsets_start_at_zero(pack_doc: dict) -> None:
    target = locator(pack_doc, "loc-custodian-balance")
    target.pop("page")
    target["locator_type"] = "text_span"
    target["char_start"] = -1
    target["char_end"] = 10
    assert_code(pack_issues(pack_doc), "L2")


# --------------------------------------------------------------------------
# Observation -- O1..O5
# --------------------------------------------------------------------------


def test_o1_observation_must_trace_somewhere(pack_doc: dict) -> None:
    observation(pack_doc, "OBS_CUSTODY_001")["supports"] = []
    assert_code(pack_issues(pack_doc), "O1")


def test_o2_derivation_needs_a_versioned_rule(pack_doc: dict) -> None:
    observation(pack_doc, "OBS_CUSTODY_003").pop("derivation_rule_id")
    assert_code(pack_issues(pack_doc), "O2")


def test_o2_rule_without_parents_derives_from_nothing(pack_doc: dict) -> None:
    target = observation(pack_doc, "OBS_CUSTODY_001")
    target["derivation_rule_id"] = "custody-relationship-count"
    target["derivation_rule_version"] = "1"
    assert_code(pack_issues(pack_doc), "O2")


def test_o3_observation_cannot_derive_from_itself(pack_doc: dict) -> None:
    observation(pack_doc, "OBS_CUSTODY_003")["parent_observation_ids"] = ["OBS_CUSTODY_003"]
    assert_code(pack_issues(pack_doc), "O3")


def test_o4_effective_period_is_ordered(pack_doc: dict) -> None:
    observation(pack_doc, "OBS_CUSTODY_003")["effective_period_end"] = "2026-08-30T00:00:00Z"
    assert_code(pack_issues(pack_doc), "O4")


def test_o5_unit_requires_a_value(pack_doc: dict) -> None:
    observation(pack_doc, "OBS_CUSTODY_002").pop("value")
    assert_code(pack_issues(pack_doc), "O5")


# --------------------------------------------------------------------------
# Route -- R1
# --------------------------------------------------------------------------


def test_r1_incomplete_route_states_its_limitation(pack_doc: dict) -> None:
    route(pack_doc, "route-custodian-records")["status"] = "BLOCKED"
    assert_code(pack_issues(pack_doc), "R1")


# --------------------------------------------------------------------------
# pack graph -- P1..P6
# --------------------------------------------------------------------------


def test_p1_duplicate_id_names_both_indices(pack_doc: dict) -> None:
    pack_doc["sources"].append(copy.deepcopy(source(pack_doc, "src-ondo-docs")))
    issues = pack_issues(pack_doc)
    assert_code(issues, "P1")
    duplicate = next(i for i in issues if i.code == "P1")
    assert duplicate.pointer == "/sources/2/source_id"
    assert "/sources/0/source_id" in duplicate.message


@pytest.mark.parametrize(
    ("mutate", "expected_pointer"),
    [
        pytest.param(
            lambda d: acquisition(d, "acq-ondo-docs").__setitem__("source_id", "src-nowhere"),
            "/acquisitions/0/source_id",
            id="acquisition-source",
        ),
        pytest.param(
            lambda d: observation(d, "OBS_CUSTODY_001")["supports"][0].__setitem__(
                "locator_id", "loc-nowhere"
            ),
            "/observations/0/supports/0/locator_id",
            id="support-locator",
        ),
        pytest.param(
            lambda d: observation(d, "OBS_CUSTODY_001")["supports"][0].__setitem__(
                "acquisition_id", "acq-nowhere"
            ),
            "/observations/0/supports/0/acquisition_id",
            id="support-acquisition",
        ),
        pytest.param(
            lambda d: observation(d, "OBS_CUSTODY_003").__setitem__(
                "parent_observation_ids", ["OBS_CUSTODY_001", "OBS_NOWHERE"]
            ),
            "/observations/2/parent_observation_ids/1",
            id="observation-parent",
        ),
        pytest.param(
            lambda d: locator(d, "loc-custodian-balance").__setitem__(
                "artifact_sha256", "9" * 64
            ),
            "/locator_catalog/1/artifact_sha256",
            id="locator-artifact",
        ),
        pytest.param(
            lambda d: acquisition(d, "acq-ondo-docs").__setitem__("artifact_sha256", "9" * 64),
            "/acquisitions/0/artifact_sha256",
            id="acquisition-artifact",
        ),
        pytest.param(
            lambda d: route(d, "route-issuer-documentation").__setitem__(
                "source_ids", ["src-nowhere"]
            ),
            "/routes/0/source_ids/0",
            id="route-source",
        ),
        pytest.param(
            lambda d: source(d, "src-ondo-docs").update(
                {"disposition": "SUPERSEDED", "superseded_by_source_id": "src-nowhere"}
            ),
            "/sources/0/superseded_by_source_id",
            id="source-successor",
        ),
    ],
)
def test_p2_every_edge_resolves(pack_doc: dict, mutate, expected_pointer: str) -> None:
    mutate(pack_doc)
    issues = pack_issues(pack_doc)
    assert_code(issues, "P2")
    assert any(i.code == "P2" and i.pointer == expected_pointer for i in issues), rendered(issues)


def test_p3_acquisition_and_locator_must_name_the_same_artifact(pack_doc: dict) -> None:
    """The support cites a locator inside the *other* source's artifact."""
    observation(pack_doc, "OBS_CUSTODY_001")["supports"][0]["locator_id"] = "loc-custodian-balance"
    issues = pack_issues(pack_doc)
    assert_code(issues, "P3")
    assert any(i.pointer == "/observations/0/supports/0/locator_id" for i in issues)


def test_p3_catches_a_swapped_artifact_on_the_acquisition(pack_doc: dict) -> None:
    target = acquisition(pack_doc, "acq-ondo-docs")
    target["artifact_sha256"] = "2" * 64
    assert_code(pack_issues(pack_doc), "P3")


@pytest.mark.parametrize("outcome", ["ACCESS_BLOCKED", "FAILED", "NOT_FOUND"])
def test_p4_support_cannot_cite_a_failed_acquisition(pack_doc: dict, outcome: str) -> None:
    target = acquisition(pack_doc, "acq-ondo-docs")
    target["outcome"] = outcome
    target["failure_reason"] = "The document could not be obtained."
    target.pop("artifact_sha256")
    target.pop("retrieved_at")
    assert_code(pack_issues(pack_doc), "P4")


def test_p4_support_cannot_cite_an_excluded_source(pack_doc: dict) -> None:
    """The acquisition succeeded; the campaign then excluded the source.

    This is the half that opens as soon as exclusion lives on the source, and
    an outcome-only check would miss it entirely.
    """
    target = source(pack_doc, "src-ondo-docs")
    target["disposition"] = "EXCLUDED"
    target["excluded_reason"] = "Superseded marketing material outside the declared scope."
    issues = pack_issues(pack_doc)
    assert_code(issues, "P4")
    assert "EXCLUDED" in rendered(issues)


def test_p4_superseded_source_still_supports_a_dated_observation(pack_doc: dict) -> None:
    """A superseded document remains authoritative for an explicitly dated fact."""
    target = source(pack_doc, "src-ondo-docs")
    target["disposition"] = "SUPERSEDED"
    target["superseded_by_source_id"] = "src-custodian-statement"
    assert_clean(pack_issues(pack_doc))


def test_p5_lineage_cycle_is_reported_with_its_path(pack_doc: dict) -> None:
    first = observation(pack_doc, "OBS_CUSTODY_001")
    first["parent_observation_ids"] = ["OBS_CUSTODY_003"]
    first["derivation_rule_id"] = "custody-relationship-count"
    first["derivation_rule_version"] = "1"
    issues = pack_issues(pack_doc)
    assert_code(issues, "P5")
    message = next(i for i in issues if i.code == "P5").message
    assert "OBS_CUSTODY_001" in message and "OBS_CUSTODY_003" in message
    assert message.split(": ")[1].split(" -> ")[0] == message.split(" -> ")[-1]


def test_p5_dangling_parent_is_not_reported_as_a_cycle(pack_doc: dict) -> None:
    observation(pack_doc, "OBS_CUSTODY_003")["parent_observation_ids"] = ["OBS_NOWHERE"]
    issues = pack_issues(pack_doc)
    assert_code(issues, "P2")
    assert "P5" not in codes(issues), rendered(issues)


def test_p6_pack_cannot_predate_its_own_cutoff(pack_doc: dict) -> None:
    pack_doc["generated_at"] = "2026-08-01T00:00:00Z"
    assert_code(pack_issues(pack_doc), "P6")


def test_p6_acquisition_cannot_postdate_the_pack(pack_doc: dict) -> None:
    target = acquisition(pack_doc, "acq-ondo-docs")
    target["attempted_at"] = "2026-09-03T00:00:00Z"
    target["retrieved_at"] = "2026-09-03T00:00:04Z"
    assert_code(pack_issues(pack_doc), "P6")


def test_p7_an_undeclared_acquisition_mode_is_rejected(pack_doc: dict) -> None:
    """Section 2.5: a campaign declares which access paths it will attempt.

    Without this the declaration constrained nothing, which also meant
    ``run.json``'s pre-registration of the campaign proved less than it looked
    like it did.
    """
    acquisition(pack_doc, "acq-ondo-docs")["acquisition_mode"] = "MANUAL_UPLOAD"
    acquisition(pack_doc, "acq-ondo-docs")["operator"] = "someone"
    issues = pack_issues(pack_doc)
    assert_code(issues, "P7")
    assert any(i.pointer == "/acquisitions/0/acquisition_mode" for i in issues), rendered(issues)


def test_p7_a_declared_mode_need_not_be_used(pack_doc: dict) -> None:
    """The campaign declares intent; an unattempted path is a route status, not an error."""
    pack_doc["campaign"]["declared_acquisition_modes"] = [
        "HTTP_DOWNLOAD",
        "BROWSER_CAPTURE",
        "MANUAL_UPLOAD",
    ]
    assert_clean(pack_issues(pack_doc))


def test_p8_a_source_url_carrying_credentials_is_rejected(pack_doc: dict) -> None:
    """``Source.url`` is model-authored and lands verbatim in a hashed artifact."""
    pack_doc["sources"][0]["url"] = "https://user:hunter2@example.invalid/ousg/docs"
    issues = pack_issues(pack_doc)
    assert_code(issues, "P8")
    assert any(i.pointer == "/sources/0/url" for i in issues), rendered(issues)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.invalid/f?api_key=SECRET",
        "https://example.invalid/f?ACCESS_TOKEN=SECRET",
        "https://example.invalid/f?api%5Fkey=SECRET",
        # A blank value still counts: the rule is that this URL is an
        # authenticated request, not that a live secret is sitting in it.
        "https://example.invalid/f?api_key=",
        "https://example.invalid/f?cik=1850391&auth_token=SECRET",
        "https://example.invalid/f?secret=SECRET",
    ],
    ids=["api_key", "case-folded", "percent-decoded", "blank-value", "second-pair", "secret"],
)
def test_p8_a_credential_query_parameter_is_rejected(pack_doc: dict, url: str) -> None:
    """Closes the gap the C3 plan recorded: query strings were unchecked.

    ``api%5Fkey`` is the decoding case -- without it, percent-encoding the
    parameter name walks a credential straight past the list.
    """
    pack_doc["sources"][0]["url"] = url
    issues = pack_issues(pack_doc)
    assert_code(issues, "P8")
    assert any(i.pointer == "/sources/0/url" for i in issues), rendered(issues)


@pytest.mark.parametrize(
    "url",
    [
        # Bare `key` and `token` are on archive's *redaction* list and not on
        # this one: P8 rejects, so a false positive stops work, and both name
        # public resources often enough to matter.
        "https://example.invalid/f?key=reserves-2026",
        "https://example.invalid/f?token=OUSG",
        # The two the refused *value-shape* heuristic destroyed. P8 never looks
        # at a value or a path segment, so neither can be touched by it.
        "https://example.invalid/Archives/edgar/data/1850391/ondo-20231231.htm",
        "https://example.invalid/docs/OUSG_Prospectus_2024.pdf",
        "https://example.invalid/f?cik=000185039124000004",
        # Not a URL at all; P8 is about credentials, not URL syntax.
        "see the attached printout",
    ],
)
def test_p8_leaves_provenance_alone(pack_doc: dict, url: str) -> None:
    pack_doc["sources"][0]["url"] = url
    assert_clean(pack_issues(pack_doc))


def test_p8_does_not_rewrite_the_url_it_rejects(pack_doc: dict) -> None:
    """Editing a source record would make it say something its author did not write."""
    rejected = "https://example.invalid/f?api_key=SECRET"
    pack_doc["sources"][0]["url"] = rejected
    pack, issues = validate_pack(pack_doc)
    assert_code(issues, "P8")
    assert pack.sources[0].url == rejected


def test_p8_does_not_rewrite_the_url_it_rejects(pack_doc: dict) -> None:
    """Editing a source record would make it say something its author did not write."""
    pack_doc["sources"][0]["url"] = "https://user:hunter2@example.invalid/ousg/docs"
    pack, issues = validate_pack(pack_doc)
    assert_code(issues, "P8")
    assert pack.sources[0].url == "https://user:hunter2@example.invalid/ousg/docs"


# --------------------------------------------------------------------------
# check states -- K1..K9, G1, G2, AS1
# --------------------------------------------------------------------------


def test_k2_unresolved_carries_no_coverage(assessment_doc: dict) -> None:
    check = only_check(assessment_doc)
    check["applicability"] = "UNRESOLVED"
    assert_code(assessment_issues(assessment_doc), "K2")


def test_k3_applies_cannot_be_not_applicable(assessment_doc: dict) -> None:
    only_check(assessment_doc)["coverage"] = "NOT_APPLICABLE"
    assert_code(assessment_issues(assessment_doc), "K3")


def test_k3_applies_needs_a_coverage(assessment_doc: dict) -> None:
    only_check(assessment_doc).pop("coverage")
    assert_code(assessment_issues(assessment_doc), "K3")


def test_k1_does_not_apply_needs_not_applicable(assessment_doc: dict) -> None:
    only_check(assessment_doc)["applicability"] = "DOES_NOT_APPLY"
    assert_code(assessment_issues(assessment_doc), "K1")


def test_k4_applies_cites_its_structural_facts(assessment_doc: dict) -> None:
    only_check(assessment_doc)["applicability_observation_ids"] = []
    assert_code(assessment_issues(assessment_doc), "K4")


def test_k4_does_not_apply_also_needs_positive_basis(assessment_doc: dict) -> None:
    check = only_check(assessment_doc)
    check.update(
        {
            "applicability": "DOES_NOT_APPLY",
            "coverage": "NOT_APPLICABLE",
            "applicability_observation_ids": [],
            "finding_observation_ids": [],
        }
    )
    check.pop("gap")
    assert_code(assessment_issues(assessment_doc), "K4")


def test_k4_unresolved_is_exempt(assessment_doc: dict) -> None:
    """Not having the facts is exactly what UNRESOLVED records."""
    check = only_check(assessment_doc)
    check.update(
        {
            "applicability": "UNRESOLVED",
            "applicability_observation_ids": [],
            "finding_observation_ids": [],
        }
    )
    check.pop("coverage")
    assert_clean(assessment_issues(assessment_doc))


def test_k5_not_assessed_names_the_unfinished_activity(assessment_doc: dict) -> None:
    check = only_check(assessment_doc)
    check["coverage"] = "NOT_ASSESSED"
    check.pop("coverage_basis")
    assert_code(assessment_issues(assessment_doc), "K5")


@pytest.mark.parametrize("coverage", ["EVIDENCED", "PARTIAL", "CONTRADICTORY"])
def test_k6_evidence_backed_coverage_cites_observations(
    assessment_doc: dict, coverage: str
) -> None:
    check = only_check(assessment_doc)
    check["coverage"] = coverage
    check["finding_observation_ids"] = []
    assert_code(assessment_issues(assessment_doc), "K6")


def test_k7_contradictory_needs_a_contradiction(assessment_doc: dict) -> None:
    only_check(assessment_doc)["coverage"] = "CONTRADICTORY"
    assert_code(assessment_issues(assessment_doc), "K7")


def test_k7_contradiction_needs_the_status(assessment_doc: dict) -> None:
    only_check(assessment_doc)["contradiction"] = {
        "conflicting_observation_ids": ["OBS_CUSTODY_002", "OBS_CUSTODY_003"],
        "conflict_basis": "The two balances disagree for the same account and date.",
        "precedence_considered": ["Neither record supersedes the other."],
    }
    assert_code(assessment_issues(assessment_doc), "K7")


def test_contradiction_needs_at_least_two_observations(assessment_doc: dict) -> None:
    check = only_check(assessment_doc)
    check["coverage"] = "CONTRADICTORY"
    check["contradiction"] = {
        "conflicting_observation_ids": ["OBS_CUSTODY_002"],
        "conflict_basis": "The two balances disagree for the same account and date.",
        "precedence_considered": ["Neither record supersedes the other."],
    }
    assert_code(assessment_issues(assessment_doc), "too_short")


def test_k9_conflict_is_drawn_from_the_finding(assessment_doc: dict) -> None:
    check = only_check(assessment_doc)
    check["coverage"] = "CONTRADICTORY"
    check["contradiction"] = {
        "conflicting_observation_ids": ["OBS_CUSTODY_002", "OBS_CUSTODY_001"],
        "conflict_basis": "The two records disagree for the same account and date.",
        "precedence_considered": ["Neither record supersedes the other."],
    }
    assert_code(assessment_issues(assessment_doc), "K9")


def test_k8_gap_is_required_where_the_catalogue_says_so(assessment_doc: dict) -> None:
    only_check(assessment_doc).pop("gap")
    assert_code(assessment_issues(assessment_doc), "K8")


def test_k8_gap_is_forbidden_where_the_catalogue_says_so(assessment_doc: dict) -> None:
    check = only_check(assessment_doc)
    check.update({"applicability": "DOES_NOT_APPLY", "coverage": "NOT_APPLICABLE"})
    check["finding_observation_ids"] = []
    assert_code(assessment_issues(assessment_doc), "K8")


@pytest.mark.parametrize(
    ("applicability", "coverage", "gap_required"),
    [pytest.param(*rule, id=f"{rule[0]}-{rule[1]}") for rule in GAP_RULES],
)
def test_k8_matches_every_catalogue_gap_rule(
    assessment_doc: dict,
    applicability: Applicability,
    coverage: Coverage | None,
    gap_required: bool,
) -> None:
    """All seven legal (applicability, coverage) pairs, driven off C1's own table.

    Both directions per row: the required arrangement validates, and the
    opposite one raises K8. Anything the catalogue calls illegal is rejected by
    K1-K3 and never reaches this rule.
    """
    check = only_check(assessment_doc)
    check["applicability"] = str(applicability)
    if coverage is None:
        check.pop("coverage")
        check.pop("coverage_basis")
    else:
        check["coverage"] = str(coverage)
    # Keep the other rules satisfied so K8 is the only thing under test.
    if coverage not in (Coverage.EVIDENCED, Coverage.PARTIAL, Coverage.CONTRADICTORY):
        check["finding_observation_ids"] = []
    if coverage is Coverage.CONTRADICTORY:
        check["finding_observation_ids"] = ["OBS_CUSTODY_002", "OBS_CUSTODY_003"]
        check["contradiction"] = {
            "conflicting_observation_ids": ["OBS_CUSTODY_002", "OBS_CUSTODY_003"],
            "conflict_basis": "The two records disagree for the same account and date.",
            "precedence_considered": ["Neither record supersedes the other."],
        }
    if applicability is Applicability.UNRESOLVED:
        check["applicability_observation_ids"] = []

    with_gap = copy.deepcopy(assessment_doc)
    without_gap = copy.deepcopy(assessment_doc)
    only_check(without_gap).pop("gap")

    legal, illegal = (with_gap, without_gap) if gap_required else (without_gap, with_gap)
    assert_clean(assessment_issues(legal))
    assert_code(assessment_issues(illegal), "K8")


def test_k8_cannot_consult_materiality(assessment_doc: dict) -> None:
    """Section 2.10: materiality "cannot determine whether an applicable gap is shown".

    The model has no materiality field at all, so the rule has no access to it
    even in principle -- there is no leak surface to police.
    """
    assert "materiality" not in CheckAssessment.model_fields
    assert "pillar_id" not in CheckAssessment.model_fields
    only_check(assessment_doc)["materiality"] = "HIGH"
    assert_code(assessment_issues(assessment_doc), "extra_forbidden")


def test_g1_rejects_the_bare_placeholder(assessment_doc: dict) -> None:
    only_check(assessment_doc)["gap"]["what_remains_unresolved"] = "Insufficient evidence."
    assert_code(assessment_issues(assessment_doc), "G1")


@pytest.mark.parametrize(
    "text",
    ["No evidence", "  unknown  ", "UNCLEAR!", "not enough evidence."],
)
def test_g1_placeholders_are_matched_loosely(assessment_doc: dict, text: str) -> None:
    only_check(assessment_doc)["gap"]["what_remains_unresolved"] = text
    assert_code(assessment_issues(assessment_doc), "G1")


def test_g1_allows_a_specific_sentence_containing_the_phrase(assessment_doc: dict) -> None:
    only_check(assessment_doc)["gap"]["what_remains_unresolved"] = (
        "Insufficient evidence covers holdings outside the single named account."
    )
    assert_clean(assessment_issues(assessment_doc))


def test_g2_partial_gap_cites_its_evidence(assessment_doc: dict) -> None:
    only_check(assessment_doc)["gap"]["evidence_observation_ids"] = []
    assert_code(assessment_issues(assessment_doc), "G2")


def test_g2_is_conditional_on_coverage(assessment_doc: dict) -> None:
    """A completed campaign that found nothing has nothing to cite.

    Requiring a citation here would force a fabricated "nothing was found"
    observation, which is the non-discovery-as-fact move the framework forbids.
    """
    check = only_check(assessment_doc)
    check["coverage"] = "MISSING"
    check["finding_observation_ids"] = []
    check["gap"]["evidence_observation_ids"] = []
    assert_clean(assessment_issues(assessment_doc))


def test_as1_one_answer_per_check(assessment_doc: dict) -> None:
    assessment_doc["checks"].append(copy.deepcopy(only_check(assessment_doc)))
    issues = assessment_issues(assessment_doc)
    assert_code(issues, "AS1")
    assert "checks[0]" in rendered(issues) and "checks[1]" in rendered(issues)


def test_a_one_check_assessment_is_legal(assessment_doc: dict) -> None:
    """63-check completeness is campaign policy, enforced at C5 ingestion."""
    assessment, issues = validate_assessment(assessment_doc)
    assert_clean(issues)
    assert len(assessment.checks) == 1


# --------------------------------------------------------------------------
# assessment against pack -- X1..X6
# --------------------------------------------------------------------------


def test_x1_citations_must_exist_in_the_pack(pack_doc: dict, assessment_doc: dict) -> None:
    only_check(assessment_doc)["finding_observation_ids"] = ["OBS_NOWHERE"]
    issues = cross_issues(pack_doc, assessment_doc)
    assert_code(issues, "X1")
    assert any(i.pointer == "/checks/0/finding_observation_ids/0" for i in issues)


def test_x1_covers_gap_citations(pack_doc: dict, assessment_doc: dict) -> None:
    only_check(assessment_doc)["gap"]["evidence_observation_ids"] = ["OBS_NOWHERE"]
    issues = cross_issues(pack_doc, assessment_doc)
    assert_code(issues, "X1")
    assert any(i.pointer == "/checks/0/gap/evidence_observation_ids/0" for i in issues)


def test_x1_covers_applicability_citations(pack_doc: dict, assessment_doc: dict) -> None:
    """K4 makes these ids mandatory; X1 is the only thing making them real."""
    only_check(assessment_doc)["applicability_observation_ids"] = ["OBS_NOWHERE"]
    issues = cross_issues(pack_doc, assessment_doc)
    assert_code(issues, "X1")
    assert any(i.pointer == "/checks/0/applicability_observation_ids/0" for i in issues)


def set_missing(assessment_doc: dict) -> None:
    check = only_check(assessment_doc)
    check["coverage"] = "MISSING"
    check["finding_observation_ids"] = []
    check["gap"]["evidence_observation_ids"] = []


def test_x2_missing_with_all_required_routes_completed_passes(
    pack_doc: dict, assessment_doc: dict
) -> None:
    set_missing(assessment_doc)
    assert_clean(cross_issues(pack_doc, assessment_doc))


def test_x2_missing_with_no_declared_route_is_rejected(
    pack_doc: dict, assessment_doc: dict
) -> None:
    """The vacuous-truth case: "every required route completed" is true of none."""
    for declared in pack_doc["routes"]:
        declared["required_for_check_ids"] = []
    set_missing(assessment_doc)
    issues = cross_issues(pack_doc, assessment_doc)
    assert_code(issues, "X2")
    assert "no route declares" in rendered(issues)


def test_x2_missing_with_a_blocked_required_route_is_rejected(
    pack_doc: dict, assessment_doc: dict
) -> None:
    blocked = route(pack_doc, "route-custodian-records")
    blocked["status"] = "BLOCKED"
    blocked["limitation"] = "The custodian portal requires an account."
    set_missing(assessment_doc)
    issues = cross_issues(pack_doc, assessment_doc)
    assert_code(issues, "X2")
    assert "route-custodian-records" in rendered(issues)


def set_not_assessed(assessment_doc: dict) -> None:
    check = only_check(assessment_doc)
    check["coverage"] = "NOT_ASSESSED"
    check["coverage_basis"] = "The declared cost scenario was not completed."
    check["finding_observation_ids"] = []
    check["gap"]["evidence_observation_ids"] = []


def test_not_assessed_is_legal_with_every_required_route_completed(
    pack_doc: dict, assessment_doc: dict
) -> None:
    """PF-ECONOMICS-011: "failure to select or complete a scenario is NOT_ASSESSED".

    A cost scenario is an assessment activity, not an acquisition route, so a
    campaign can retrieve every fee document and still not finish the work. The
    mirror of X2 would reject this and push the campaign toward the stronger
    MISSING claim, so there is deliberately no such rule. See the deferred list.
    """
    set_not_assessed(assessment_doc)
    assert_clean(cross_issues(pack_doc, assessment_doc))


def test_not_assessed_is_legal_with_an_unfinished_route(
    pack_doc: dict, assessment_doc: dict
) -> None:
    blocked = route(pack_doc, "route-custodian-records")
    blocked["status"] = "BLOCKED"
    blocked["limitation"] = "The custodian portal requires an account."
    set_not_assessed(assessment_doc)
    assert_clean(cross_issues(pack_doc, assessment_doc))


def test_not_assessed_still_names_the_unfinished_activity(assessment_doc: dict) -> None:
    """K5 is the only thing left holding NOT_ASSESSED to account, so it has to hold."""
    set_not_assessed(assessment_doc)
    only_check(assessment_doc).pop("coverage_basis")
    assert_code(assessment_issues(assessment_doc), "K5")


def test_x4_survives_a_whitespace_only_reformat(pack_doc: dict, assessment_doc: dict) -> None:
    """The pin is on the canonical form, so formatting is not semantics."""
    reformatted = json.dumps(pack_doc, indent=7, separators=(" ,", " : "))
    assert reformatted != PACK_JSON.read_text(encoding="utf-8")
    assert_clean(cross_issues(json.loads(reformatted), assessment_doc, repin=False))


def test_x4_survives_an_equivalent_timezone_spelling(
    pack_doc: dict, assessment_doc: dict
) -> None:
    pack_doc["campaign"]["cutoff"] = "2026-08-31T20:00:00-04:00"
    assert_clean(cross_issues(pack_doc, assessment_doc, repin=False))


def test_x4_fails_on_a_changed_proposition(pack_doc: dict, assessment_doc: dict) -> None:
    observation(pack_doc, "OBS_CUSTODY_002")["proposition"] = (
        "The named custodian account held a closing balance of USD 41,000,000.00 "
        "on 31 August 2026."
    )
    issues = cross_issues(pack_doc, assessment_doc, repin=False)
    assert_code(issues, "X4")
    assert any(i.pointer == "/meta/evidence_pack_sha256" for i in issues)


def test_x5_run_ids_must_agree(pack_doc: dict, assessment_doc: dict) -> None:
    assessment_doc["meta"]["campaign_run_id"] = "ousg-2026-01-01"
    assert_code(cross_issues(pack_doc, assessment_doc), "X5")


def test_x6_assessment_cannot_predate_its_evidence(
    pack_doc: dict, assessment_doc: dict
) -> None:
    assessment_doc["meta"]["generated_at"] = "2026-09-02T09:00:00Z"
    assert_code(cross_issues(pack_doc, assessment_doc), "X6")


# --------------------------------------------------------------------------
# entry-point contract
# --------------------------------------------------------------------------


def test_schema_version_is_required(pack_doc: dict) -> None:
    """An artifact that does not say what it is gives a later verifier nothing to
    dispatch on."""
    pack_doc.pop("schema_version")
    issues = pack_issues(pack_doc)
    assert_code(issues, "missing")
    assert any(i.pointer == "/schema_version" for i in issues)


def test_wrong_schema_version_is_rejected(pack_doc: dict) -> None:
    pack_doc["schema_version"] = "plinth.evidence/2"
    assert_code(pack_issues(pack_doc), "literal_error")


def test_a_graph_invalid_pack_is_still_returned(pack_doc: dict) -> None:
    """A non-``None`` model is not a verdict.

    The pack is returned whenever it *constructed*, so a caller can inspect one
    that failed a graph rule. Validity is the empty issue tuple, and nothing
    else.
    """
    acquisition(pack_doc, "acq-ondo-docs")["source_id"] = "src-nowhere"
    pack, issues = validate_pack(pack_doc)
    assert isinstance(pack, EvidencePack)
    assert_code(issues, "P2")


def test_shape_failure_returns_no_model(pack_doc: dict) -> None:
    """Graph rules cannot run on a pack that did not construct, which is why the
    entry points promise all *discoverable* issues rather than all issues."""
    pack_doc["campaign"]["bounded_public_evidence"] = "true"
    pack, issues = validate_pack(pack_doc)
    assert pack is None
    assert issues


def test_g1_hyphenated_placeholder_is_still_a_placeholder(assessment_doc: dict) -> None:
    only_check(assessment_doc)["gap"]["what_remains_unresolved"] = "No-evidence"
    assert_code(assessment_issues(assessment_doc), "G1")


def test_r1_skipped_route_with_a_limitation_is_legal(pack_doc: dict) -> None:
    skipped = route(pack_doc, "route-custodian-records")
    skipped["status"] = "SKIPPED"
    skipped["limitation"] = "Deferred to a campaign with private access."
    assert_clean(pack_issues(pack_doc))


# --------------------------------------------------------------------------
# scalar values that survive JSON but not an exact digest
# --------------------------------------------------------------------------
#
# Every case below arrives through `json.loads` of a document a model could
# plausibly emit, passes a naive type check, and then either loses information
# or breaks `canonical_bytes` -- the function X4's pin is computed from.


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(json.loads("0.07"), id="ordinary-decimal-literal"),
        pytest.param(0.07, id="pre-parsed-python-float"),
        pytest.param(json.loads("1e-400"), id="underflow-to-zero"),
        pytest.param(json.loads("42000000.250000000000001"), id="excess-precision"),
        pytest.param(json.loads("1e400"), id="overflow-to-inf"),
        pytest.param(json.loads("NaN"), id="nan"),
    ],
)
def test_float_observation_value_is_rejected(pack_doc: dict, value: object) -> None:
    """No float reaches the digest, however it was spelled.

    The two high-precision literals from the review reach validation as the
    *same* Python float, so as rejection tests they would be one test wearing
    two hats; only one is kept here and the collision itself is asserted below.
    """
    observation(pack_doc, "OBS_CUSTODY_002")["value"] = value
    issues = pack_issues(pack_doc)
    assert_code(issues, "scalar_value")
    assert any(i.pointer == "/observations/1/value" for i in issues), rendered(issues)


def test_floats_would_have_collided_in_the_pin() -> None:
    """Why floats are refused rather than range-checked.

    Two distinct submitted decimals become one Python float during parsing, and
    the three non-finite values all serialize to `null`. Either way two different
    propositions produce identical canonical bytes, so X4 -- the only thing
    binding an assessment to one specific evidence pack -- cannot tell them
    apart. No precision limit recovers digits `json.loads` already discarded,
    which is why the type is refused instead of policed.
    """
    import math

    from pydantic import BaseModel

    assert json.loads("42000000.250000000000001") == json.loads("42000000.25")
    assert json.loads("1e-400") == 0.0

    class Unguarded(BaseModel):
        value: Any

    dumped = [
        Unguarded(value=v).model_dump(mode="json")["value"]
        for v in (math.inf, -math.inf, math.nan)
    ]
    assert dumped == [None, None, None]


def test_exact_decimals_round_trip_as_strings(pack_doc: dict) -> None:
    """The replacement for floats: a quoted decimal survives byte-identically."""
    first, _ = validate_pack(pack_doc)
    again, issues = validate_pack(canonical_bytes(first))
    assert_clean(issues)
    assert canonical_bytes(again) == canonical_bytes(first)
    assert again.observations[1].value == "42000000.00"


def test_changing_an_exact_decimal_breaks_the_pin(
    pack_doc: dict, assessment_doc: dict
) -> None:
    """A decimal string is binding content, not formatting -- X4 must notice."""
    observation(pack_doc, "OBS_CUSTODY_002")["value"] = "42000000.01"
    assert_code(cross_issues(pack_doc, assessment_doc, repin=False), "X4")


def test_integer_values_still_round_trip(pack_doc: dict) -> None:
    """Integers are exact, so they stay a native JSON type rather than a string."""
    pack, issues = validate_pack(pack_doc)
    assert_clean(issues)
    assert pack.observations[2].value == 1
    assert json.loads(canonical_bytes(pack))["observations"][2]["value"] == 1


def test_unpaired_surrogate_observation_value_is_rejected(pack_doc: dict) -> None:
    """A "\\ud800" escape survives json.loads but cannot be encoded as UTF-8."""
    observation(pack_doc, "OBS_CUSTODY_002")["value"] = json.loads(r'"\ud800"')
    issues = pack_issues(pack_doc)
    assert_code(issues, "scalar_value")
    assert any(i.pointer == "/observations/1/value" for i in issues), rendered(issues)
    assert "surrogate" in rendered(issues)


def test_typed_string_fields_already_reject_surrogates(pack_doc: dict) -> None:
    """Pydantic covers every declared string; only the Any-typed value needed a rule."""
    observation(pack_doc, "OBS_CUSTODY_002")["proposition"] = json.loads(r'"bad \ud800 text"')
    assert_code(pack_issues(pack_doc), "string_unicode")


def test_every_validating_pack_can_be_serialized(pack_doc: dict) -> None:
    """The contract these rules protect: a pack that validates has canonical bytes.

    Without them `validate_pack` returned a clean pack whose `canonical_bytes`
    raised `UnicodeEncodeError` -- an exception on a path documented to return
    Issues instead.
    """
    for bad in [json.loads(r'"\ud800"'), json.loads("1e400"), json.loads("NaN")]:
        document = copy.deepcopy(pack_doc)
        document["observations"][1]["value"] = bad
        pack, issues = validate_pack(document)
        assert pack is None and issues, f"{bad!r} validated"
    pack, issues = validate_pack(pack_doc)
    assert_clean(issues)
    assert canonical_bytes(pack)


# --------------------------------------------------------------------------
# input integrity -- what json.loads loses before pydantic runs
# --------------------------------------------------------------------------


def test_duplicate_top_level_key_is_rejected(pack_doc: dict) -> None:
    """`json.loads` keeps the last value for a repeated key and says nothing.

    That is a silent drop of submitted content, and it happens during parsing,
    so `extra="forbid"` never sees the shadowed value.
    """
    raw = json.dumps(pack_doc)
    doubled = raw.replace('{"schema_version"', '{"generated_at": "2020-01-01T00:00:00Z", "schema_version"', 1)
    issues = pack_issues(doubled)
    assert_code(issues, "invalid_json")
    assert "generated_at" in rendered(issues)


def test_duplicate_nested_key_is_rejected(pack_doc: dict) -> None:
    """The hook has to fire at any depth, not just on the top-level object."""
    raw = json.dumps(pack_doc)
    doubled = raw.replace('{"run_id"', '{"cutoff": "2020-01-01T00:00:00Z", "run_id"', 1)
    issues = pack_issues(doubled)
    assert_code(issues, "invalid_json")
    assert "cutoff" in rendered(issues)


def test_duplicate_key_never_silently_wins(pack_doc: dict) -> None:
    """The behaviour being prevented, asserted directly on the stdlib."""
    assert json.loads('{"a": 1, "a": 2}') == {"a": 2}
    assert_code(pack_issues('{"a": 1, "a": 2}'), "invalid_json")


def test_oversized_integer_literal_is_rejected_without_raising() -> None:
    """CPython's 4300-digit conversion limit raises a bare `ValueError`.

    `json.JSONDecodeError` subclasses `ValueError`, so widening the clause
    catches this too rather than letting it escape an entry point documented to
    return Issues.
    """
    document = '{"schema_version": "plinth.evidence/1", "generated_at": ' + "9" * 5000 + "}"
    pack, issues = validate_pack(document)
    assert pack is None
    assert_code(issues, "invalid_json")


def test_datetime_at_the_edge_of_the_range_is_rejected_with_its_pointer(
    pack_doc: dict,
) -> None:
    """`datetime.max` at a negative offset has no UTC form; `astimezone` raises."""
    from datetime import datetime, timedelta, timezone

    pack_doc["campaign"]["cutoff"] = datetime.max.replace(
        tzinfo=timezone(timedelta(hours=-14))
    ).isoformat()
    pack, issues = validate_pack(pack_doc)
    assert pack is None
    assert_code(issues, "datetime_range")
    assert any(i.pointer == "/campaign/cutoff" for i in issues), rendered(issues)


# --------------------------------------------------------------------------
# text that must not be normalized
# --------------------------------------------------------------------------


def test_issue_pointer_preserves_trailing_whitespace() -> None:
    """A pointer to a key with trailing space must still name that key."""
    assert Issue(pointer="/a/b ", code="c", message="m").pointer == "/a/b "
    assert Issue(pointer="", code="c", message="m").pointer == ""


def test_issue_pointer_still_escapes_reserved_characters() -> None:
    assert Issue(pointer=pointer("m~/x "), code="c", message="m").pointer == "/m~0~1x "


def test_quoted_text_preserves_surrounding_whitespace(pack_doc: dict) -> None:
    """C3 matches this against archived bytes; a stripped copy will not be found."""
    locator(pack_doc, "loc-custodian-balance")["quoted_text"] = "  Closing balance  "
    pack, issues = validate_pack(pack_doc)
    assert_clean(issues)
    assert pack.locator_catalog[1].quoted_text == "  Closing balance  "


def test_quoted_text_still_rejects_the_empty_string(pack_doc: dict) -> None:
    """Turning off stripping must not also turn off the emptiness rule."""
    locator(pack_doc, "loc-custodian-balance")["quoted_text"] = ""
    assert_code(pack_issues(pack_doc), "string_too_short")


def test_domain_prose_is_still_stripped(pack_doc: dict) -> None:
    """The exemption is two fields wide, not a policy change."""
    pack_doc["campaign"]["subject"] = "  OUSG  "
    pack, issues = validate_pack(pack_doc)
    assert_clean(issues)
    assert pack.campaign.subject == "OUSG"


# --------------------------------------------------------------------------
# CN1 -- a conflict needs two different observations
# --------------------------------------------------------------------------


def contradictory(assessment_doc: dict, conflicting: list[str]) -> None:
    check = only_check(assessment_doc)
    check["coverage"] = "CONTRADICTORY"
    check["finding_observation_ids"] = ["OBS_CUSTODY_002", "OBS_CUSTODY_003"]
    check["contradiction"] = {
        "conflicting_observation_ids": conflicting,
        "conflict_basis": "The two records disagree for the same account and date.",
        "precedence_considered": ["Neither record supersedes the other."],
    }


def test_cn1_same_observation_twice_is_not_a_conflict(assessment_doc: dict) -> None:
    """min_length counts entries, not distinct ones, and K9's subset test passes."""
    contradictory(assessment_doc, ["OBS_CUSTODY_002", "OBS_CUSTODY_002"])
    assert_code(assessment_issues(assessment_doc), "CN1")


def test_cn1_two_distinct_observations_are_a_conflict(assessment_doc: dict) -> None:
    contradictory(assessment_doc, ["OBS_CUSTODY_002", "OBS_CUSTODY_003"])
    assert_clean(assessment_issues(assessment_doc))


# --------------------------------------------------------------------------
# P6 -- every acquisition moment is bounded by pack generation
# --------------------------------------------------------------------------


def test_p6_retrieval_cannot_postdate_the_pack(pack_doc: dict) -> None:
    """A2 orders retrieval after its attempt but leaves it unbounded above."""
    acquisition(pack_doc, "acq-ondo-docs")["retrieved_at"] = "2030-01-01T00:00:00Z"
    issues = pack_issues(pack_doc)
    assert_code(issues, "P6")
    assert any(i.pointer == "/acquisitions/0/retrieved_at" for i in issues), rendered(issues)


def test_p6_archival_cannot_postdate_the_pack(pack_doc: dict) -> None:
    pack_doc["artifacts"][0]["archived_at"] = "2030-01-01T00:00:00Z"
    issues = pack_issues(pack_doc)
    assert_code(issues, "P6")
    assert any(i.pointer == "/artifacts/0/archived_at" for i in issues), rendered(issues)


def test_p6_late_evidence_cannot_reach_an_assessment(
    pack_doc: dict, assessment_doc: dict
) -> None:
    """The whole point: an assessment must not rest on bytes that had not arrived."""
    acquisition(pack_doc, "acq-ondo-docs")["retrieved_at"] = "2030-01-01T00:00:00Z"
    pack_doc["artifacts"][0]["archived_at"] = "2030-01-01T00:00:00Z"
    _, issues = validate_pack(pack_doc)
    assert_code(issues, "P6")


# --------------------------------------------------------------------------
# the normalization contract
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("item", "mutate"),
    [
        pytest.param(
            "1 whitespace",
            lambda d: d["campaign"].__setitem__("subject", "  OUSG  "),
            id="whitespace",
        ),
        pytest.param(
            "2 timezone offset",
            lambda d: d["campaign"].__setitem__("cutoff", "2026-08-31T20:00:00-04:00"),
            id="timezone-offset",
        ),
        pytest.param(
            "3 datetime spelling",
            lambda d: d["campaign"].__setitem__("cutoff", "2026-09-01T00:00:00.000Z"),
            id="datetime-spelling",
        ),
        pytest.param(
            "5 explicit default",
            lambda d: source(d, "src-ondo-docs").__setitem__("disposition", "IN_SCOPE"),
            id="explicit-default",
        ),
    ],
)
def test_digest_binds_the_normalized_model_not_the_document(
    pack_doc: dict, item: str, mutate, pack_document: dict
) -> None:
    """Each numbered erasure in `canonical_bytes`'s contract, asserted.

    The docstring is what a stdlib-only verifier will be built against in C3, so
    a claim there that quietly stopped being true would be discovered by someone
    reimplementing it, not by us. These are byte-different submissions that must
    hash identically.
    """
    reference, issues = validate_pack(copy.deepcopy(pack_document))
    assert_clean(issues)
    mutate(pack_doc)
    mutated, issues = validate_pack(pack_doc)
    assert_clean(issues)
    assert canonical_bytes(mutated) == canonical_bytes(reference), item


def test_digest_ignores_key_order_and_indentation(pack_doc: dict) -> None:
    """Item 6, which needs a re-serialized document rather than a field edit."""
    reference, _ = validate_pack(copy.deepcopy(pack_doc))
    reshaped = json.loads(json.dumps(pack_doc, indent=7, sort_keys=False))
    mutated, issues = validate_pack(reshaped)
    assert_clean(issues)
    assert canonical_bytes(mutated) == canonical_bytes(reference)


def test_digest_still_binds_meaning(pack_doc: dict) -> None:
    """The other half of the contract: everything not on the list is binding."""
    reference, _ = validate_pack(copy.deepcopy(pack_doc))
    observation(pack_doc, "OBS_CUSTODY_002")["unit"] = "EUR"
    mutated, issues = validate_pack(pack_doc)
    assert_clean(issues)
    assert canonical_bytes(mutated) != canonical_bytes(reference)


# --------------------------------------------------------------------------
# review round 4: entry points never raise; instants are text; enum tables total
# --------------------------------------------------------------------------


def test_every_locator_type_has_a_required_field_entry() -> None:
    """L1 indexes this table by enum member; a missing row would be a KeyError, not an Issue."""
    assert set(LOCATOR_REQUIRED_FIELDS) == set(LocatorType)


def test_deeply_nested_json_is_an_issue_not_a_recursion_error() -> None:
    model, issues = validate_pack("[" * 1_000_000)
    assert model is None
    assert codes(issues) == ["invalid_json"]


def test_dict_input_with_an_oversized_int_is_an_issue_not_a_late_exception(pack_doc: dict) -> None:
    """The dict path used to skip json.loads' digit guard, then raise inside canonical_bytes."""
    observation(pack_doc, "OBS_CUSTODY_002")["value"] = 10**5000
    model, issues = validate_pack(pack_doc)
    assert model is None
    assert codes(issues) == ["invalid_json"]


def test_dict_input_with_a_set_is_an_issue_not_a_randomized_digest(pack_doc: dict) -> None:
    source(pack_doc, "src-ondo-docs")["stated_limitations"] = {"alpha", "beta"}
    model, issues = validate_pack(pack_doc)
    assert model is None
    assert codes(issues) == ["invalid_json"]


@pytest.mark.parametrize("value", [1700000000, 1700000000000, 1700000000.5, "1700000000"])
def test_numeric_timestamps_are_rejected(pack_doc: dict, value: object) -> None:
    """pydantic would read these as epoch seconds or milliseconds and assume UTC."""
    pack_doc["campaign"]["cutoff"] = value
    issues = pack_issues(pack_doc)
    assert_code(issues, "datetime_type")
    assert any(i.pointer == "/campaign/cutoff" for i in issues), rendered(issues)


def test_sub_microsecond_instants_are_rejected_not_truncated(pack_doc: dict) -> None:
    pack_doc["generated_at"] = "2026-09-02T10:00:00.1234567Z"
    issues = pack_issues(pack_doc)
    assert_code(issues, "datetime_precision")
    assert any(i.pointer == "/generated_at" for i in issues), rendered(issues)


def test_six_fractional_digits_still_round_trip(pack_doc: dict) -> None:
    pack_doc["generated_at"] = "2026-09-02T10:00:00.123456Z"
    pack, issues = validate_pack(pack_doc)
    assert_clean(issues)
    assert b'"generated_at": "2026-09-02T10:00:00.123456Z"' in canonical_bytes(pack)


def test_g1_message_is_rendered_not_a_format_template(assessment_doc: dict) -> None:
    only_check(assessment_doc)["gap"]["what_remains_unresolved"] = "unknown"
    text = rendered(assessment_issues(assessment_doc))
    assert "G1" in text
    assert "{" not in text
