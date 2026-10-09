"""Fixtures shared across test modules: generated runs, never a pilot archive."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from plinth import archive as arc, assessment as asm, catalogue as cat
from plinth.models import Campaign, EvidencePack, canonical_bytes, canonical_sha256
from plinth.vocab import AcquisitionMode


@pytest.fixture
def case(tmp_path):
    now = datetime.now(UTC)
    campaign = Campaign.model_validate({
        "run_id": "c5-test", "subject": "Generated product",
        "subject_description": "Test documentary perimeter",
        "cutoff": (now - timedelta(days=1)).isoformat(),
        "declared_acquisition_modes": ["HTTP_DOWNLOAD"],
        "declared_scope_note": "One generated source; no completed research routes.",
        "bounded_public_evidence": True,
    })
    root = tmp_path / "runs"
    run = arc.create_run(campaign, runs_root=root)
    document = tmp_path / "source.txt"
    document.write_text("The product holds assets in custody.")
    run, acquisition, artifact = arc.add_artifact(
        run, document, source_id="src-1", acquisition_mode=AcquisitionMode.HTTP_DOWNLOAD,
        media_type="text/plain", retrieved_at=now,
    )
    pack = EvidencePack.model_validate({
        "schema_version": "plinth.evidence/1", "campaign": campaign.model_dump(mode="json"),
        "sources": [{"source_id": "src-1", "title": "Product description",
                     "source_type": "issuer_documentation", "disposition": "IN_SCOPE"}],
        "acquisitions": [acquisition.model_dump(mode="json")],
        "artifacts": [artifact.model_dump(mode="json")],
        "locator_catalog": [{"locator_id": "loc-1", "artifact_sha256": artifact.sha256,
                             "locator_type": "document_section", "section": "Description",
                             "quoted_text": document.read_text()}],
        "observations": [{"observation_id": "obs-1", "proposition": document.read_text(),
                          "subject": "Generated product", "supports": [{
                              "acquisition_id": acquisition.acquisition_id, "locator_id": "loc-1"}]}],
        "generated_at": (now + timedelta(minutes=1)).isoformat(),
    })
    assert arc.assess_pack_for_run(canonical_bytes(pack), run)[1] == ()
    run.accepted_pack_path.write_bytes(canonical_bytes(pack))
    catalogue = json.loads(cat.CATALOGUE_PATH.read_bytes())
    checks = [{
        "check_id": check["check_id"], "applicability": "APPLIES",
        "applicability_basis": "Generated custody fact for policy testing.",
        "applicability_observation_ids": ["obs-1"], "coverage": "NOT_ASSESSED",
        "coverage_basis": "The full proposition assessment activity is unfinished.",
        "finding": "Only the generated custody statement was reviewed.",
        "gap": {"question": check["question"], "what_is_known": "A custody statement exists.",
                "what_remains_unresolved": "The complete check proposition has not been assessed.",
                "what_this_means": "This record cannot establish the full check proposition.",
                "what_would_close_it": "Complete the declared proposition assessment.",
                "evidence": "The generated custody statement alone bounds this review."},
    } for check in catalogue["checks"]]
    proposal = {"schema_version": "plinth.assessment/1", "checks": checks, "meta": {
        "campaign_run_id": campaign.run_id, "framework_version": catalogue["framework_version"],
        "catalogue_sha256": run.manifest.catalogue_sha256,
        "evidence_pack_sha256": canonical_sha256(pack),
        "generated_at": (now + timedelta(minutes=2)).isoformat(),
    }}
    source = run.root / asm.PROPOSED_ASSESSMENT_NAME
    source.write_text(json.dumps(proposal))
    return SimpleNamespace(run=run, pack=pack, catalogue=catalogue, proposal=proposal,
                           source=source, root=root, target=run.root / asm.ACCEPTED_ASSESSMENT_NAME)
