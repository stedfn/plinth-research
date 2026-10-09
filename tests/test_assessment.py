"""Generated same-host C5 runs: no pilot archive; the shared `case` run is in conftest.py."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from plinth import archive as arc, assessment as asm, catalogue as cat, cli
from plinth.models import Assessment, EvidencePack, canonical_bytes, canonical_sha256
from plinth.validate import validate_assessment, validate_assessment_against_pack

def call(case, *words, source=None):
    args = [*words, case.run.manifest.campaign.run_id, "--runs-root", str(case.root)]
    if source is not None:
        args += ["--from", str(source)]
    return cli.main(args)


def assess(case):
    return asm.assess_assessment_for_run(case.proposal, run=case.run, pack=case.pack,
                                         catalogue=case.catalogue)


def snapshot(root):
    return {str(p): (p.read_bytes(), p.stat().st_ino) for p in root.rglob("*") if p.is_file()}


def test_packet(case):
    assert call(case, "packet", "assessment") == 0
    path = case.run.root / asm.PACKET_NAME
    packet = json.loads(path.read_bytes())
    assert packet["schema_version"] == "plinth.assessment-packet/1"
    assert packet["run_id"] == case.pack.campaign.run_id
    assert packet["campaign"] == case.pack.campaign.model_dump(mode="json")
    for pin in packet["inputs"].values():
        assert Path(pin["path"]).is_absolute()
        assert hashlib.sha256(Path(pin["path"]).read_bytes()).hexdigest() == pin["sha256"]
    assert packet["prompt"]["text"] == asm.PROMPT_PATH.read_text()
    assert packet["prompt"]["sha256"] == hashlib.sha256(asm.PROMPT_PATH.read_bytes()).hexdigest()
    assert packet["assessment_json_schema"] == Assessment.model_json_schema()
    assert packet["assessment_meta"] == {k: v for k, v in case.proposal["meta"].items()
                                           if k != "generated_at"}
    assert packet["generated_at_not_before"] == case.pack.model_dump(mode="json")["generated_at"]
    assert packet["missing_coverage_enabled"] is False
    assert packet["output_path"] == str(case.source.resolve())
    assert packet["check_order"] == [c["check_id"] for c in case.catalogue["checks"]]
    assert len(packet["checks"]) == 63
    assert all(set(c) == {"check_id", "pillar_id", "question", "fields"} for c in packet["checks"])
    assert "materiality" not in json.dumps(packet["checks"])
    assert "observations" not in packet
    before = snapshot(case.run.root)
    assert call(case, "packet", "assessment") == 0
    assert snapshot(case.run.root) == before


def test_changed_packet_is_replaced(case, monkeypatch, tmp_path):
    assert call(case, "packet", "assessment") == 0
    path = case.run.root / asm.PACKET_NAME
    inode = path.stat().st_ino
    prompt = tmp_path / "prompt.md"
    prompt.write_text(asm.PROMPT_PATH.read_text() + "\nTest revision.\n")
    monkeypatch.setattr(asm, "PROMPT_PATH", prompt)
    assert call(case, "packet", "assessment") == 0
    assert path.stat().st_ino != inode
    assert json.loads(path.read_bytes())["prompt"]["text"] == prompt.read_text()


@pytest.mark.parametrize("state", ["missing", "malformed", "drift"])
def test_packet_requires_valid_evidence(case, state):
    if state == "missing":
        case.run.accepted_pack_path.unlink()
    elif state == "malformed":
        case.run.accepted_pack_path.write_text("{}")
    else:
        blob = next(case.run.blobs_dir.iterdir())
        blob.chmod(0o644)
        blob.write_bytes(b"changed")
    assert call(case, "packet", "assessment") == 1
    assert not (case.run.root / asm.PACKET_NAME).exists()


def test_packet_reconstructs_catalogue(case, monkeypatch, tmp_path):
    # D13 still passes: only the source markdown, not the pinned catalogue, drifts.
    monkeypatch.setattr(cat, "INPUTS_DIR", tmp_path)
    for filename in cat.INPUT_FILES.values():
        (tmp_path / filename).write_bytes((cat.PROJECT_ROOT / "inputs" / filename).read_bytes())
    framework = tmp_path / cat.FRAMEWORK_MD
    framework.write_bytes(framework.read_bytes() + b"\nDrift\n")
    assert call(case, "packet", "assessment") == 1
    assert not (case.run.root / asm.PACKET_NAME).exists()


@pytest.mark.parametrize("mutation,code", [
    (lambda d: d["meta"].update(catalogue_sha256="0" * 64), "X7"),
    (lambda d: d["meta"].update(framework_version="v999"), "X8"),
    (lambda d: d["checks"].reverse(), "X9"),
    (lambda d: d["checks"][0]["gap"].update(question="Reworded question?"), "X10"),
    (lambda d: d["checks"][0].update(coverage="MISSING"), "X11"),
    (lambda d: d["checks"].append(copy.deepcopy(d["checks"][0])), "AS1"),
    (lambda d: d["meta"].update(evidence_pack_sha256="0" * 64), "X4"),
    (lambda d: d["meta"].update(campaign_run_id="other-run"), "X5"),
    (lambda d: d["meta"].update(generated_at="2000-01-01T00:00:00Z"), "X6"),
    (lambda d: d["checks"][0].update(applicability="UNRESOLVED"), "K2"),
    (lambda d: d["checks"][0].update(coverage_basis=None), "K5"),
    (lambda d: d["checks"][0].update(coverage="EVIDENCED"), "K6"),
    (lambda d: d["checks"][0].update(gap=None), "K8"),
    (lambda d: d["checks"][0]["gap"].update(what_remains_unresolved="Unknown"), "G1"),
    (lambda d: d["checks"][0].update(coverage="CONTRADICTORY", finding_observation_ids=["obs-1"]), "K7"),
    (lambda d: d["checks"][0].update(applicability_observation_ids=["invented"]), "X1"),
])
def test_acceptance_rules(case, mutation, code):
    assert assess(case)[1] == ()
    mutation(case.proposal)
    assert code in {p.code for p in assess(case)[1]}


def test_empty_checks_reports_every_missing_id(case):
    case.proposal["checks"] = []
    issues = assess(case)[1]
    missing = [p.message for p in issues if p.code == "X9" and p.message.startswith("missing")]
    assert missing == [f"missing catalogue check {c['check_id']}" for c in case.catalogue["checks"]]


def test_packet_and_validation_share_catalogue_order(case):
    case.catalogue["checks"].reverse()
    assert "X9" in {p.code for p in assess(case)[1]}
    case.proposal["checks"].reverse()
    assert assess(case)[1] == ()
    assert asm.canonical_check_order(case.catalogue) == [c["check_id"] for c in case.proposal["checks"]]


def test_forged_completed_route_cannot_enable_missing(case):
    raw = case.pack.model_dump(mode="json")
    raw["routes"] = [{"route_id": "forged", "description": "Claimed complete search",
                      "acquisition_mode": "HTTP_DOWNLOAD", "status": "COMPLETED",
                      "required_for_check_ids": [case.proposal["checks"][0]["check_id"]]}]
    case.pack = EvidencePack.model_validate(raw)
    case.proposal["meta"]["evidence_pack_sha256"] = canonical_sha256(case.pack)
    case.proposal["checks"][0]["coverage"] = "MISSING"
    model, problems = validate_assessment(case.proposal)
    assert not problems
    assert not validate_assessment_against_pack(model, case.pack)
    assert {p.code for p in assess(case)[1]} == {"X11"}


@pytest.mark.parametrize("valid", [True, False])
@pytest.mark.parametrize("external", [True, False])
def test_check_never_writes(case, valid, external, tmp_path, capsys):
    if not valid:
        case.proposal["checks"] = []
    source = tmp_path / "external.json" if external else case.source
    source.write_text(json.dumps(case.proposal))
    before = snapshot(tmp_path)
    assert call(case, "check", "assessment", source=source if external else None) == (0 if valid else 1)
    assert snapshot(tmp_path) == before
    output = capsys.readouterr()
    if valid:
        assert "valid but not accepted" in output.out
        assert canonical_sha256(Assessment.model_validate(case.proposal)) in output.out
    else:
        assert "X9" in output.err


def test_acceptance_is_canonical_and_immutable(case, capsys):
    assert call(case, "ingest", "assessment") == 0
    assert case.target.read_bytes() == canonical_bytes(Assessment.model_validate(case.proposal))
    before = snapshot(case.run.root)
    assert call(case, "ingest", "assessment") == 0
    assert snapshot(case.run.root) == before
    case.proposal["checks"][0]["finding"] = "A different valid finding."
    case.source.write_text(json.dumps(case.proposal))
    assert call(case, "ingest", "assessment") == 1
    assert "new run" in capsys.readouterr().err
    assert (case.target.read_bytes(), case.target.stat().st_ino) == before[str(case.target)]


@pytest.mark.parametrize("accepted", [True, False])
def test_rejection_diagnostics_preserve_canonical_files(case, accepted, tmp_path):
    if accepted:
        assert call(case, "ingest", "assessment") == 0
    before = snapshot(case.run.root)
    external = tmp_path / "bad.json"
    external.write_text('{"checks": []}')
    assert call(case, "ingest", "assessment", source=external) == 1
    issues = json.loads(external.with_suffix(".issues.json").read_bytes())
    assert issues["source"] == "bad.json" and issues["issues"]
    assert snapshot(case.run.root) == before


@pytest.mark.parametrize("drift", ["blob", "campaign", "lineage"])
def test_evidence_drift_blocks_ingestion(case, drift):
    assert call(case, "ingest", "assessment") == 0
    accepted = case.target.read_bytes()
    if drift == "blob":
        blob = next(case.run.blobs_dir.iterdir())
        blob.chmod(0o644)
        blob.write_bytes(b"tampered")
    else:
        raw = case.pack.model_dump(mode="json")
        if drift == "campaign":
            raw["campaign"]["subject"] = "Another subject"
        else:
            raw["observations"][0]["supports"][0]["locator_id"] = "invented"
        case.run.accepted_pack_path.write_text(json.dumps(raw))
    assert call(case, "ingest", "assessment") == 1
    assert case.target.read_bytes() == accepted
    assert call(case, "verify") == 1


def test_verify_stages(case, capsys):
    evidence = case.run.accepted_pack_path.read_bytes()
    case.run.accepted_pack_path.unlink()
    assert call(case, "verify") == 2
    assert "INCOMPLETE" in capsys.readouterr().err
    case.run.accepted_pack_path.write_bytes(evidence)
    assert call(case, "verify") == 0
    assert "EVIDENCE_ACCEPTED" in capsys.readouterr().out
    # Proposals and diagnostics do not change the accepted stage.
    case.source.write_text("bad JSON")
    (case.run.root / asm.ISSUES_NAME).write_text("bad JSON")
    assert call(case, "verify") == 0
    case.source.write_text(json.dumps(case.proposal))
    assert call(case, "ingest", "assessment") == 0
    assert call(case, "verify") == 0
    out = capsys.readouterr().out
    assert "ASSESSMENT_ACCEPTED" in out
    assert canonical_sha256(Assessment.model_validate(case.proposal)) in out
    case.run.accepted_pack_path.unlink()
    assert call(case, "verify") == 1


@pytest.mark.parametrize("tamper", ["malformed", "pin", "order", "formatting"])
def test_verify_rejects_tampered_assessment(case, tamper):
    assert call(case, "ingest", "assessment") == 0
    case.target.chmod(0o644)
    if tamper == "malformed":
        case.target.write_text("{}")
    elif tamper == "formatting":
        case.target.write_bytes(case.target.read_bytes() + b"\n")
    else:
        if tamper == "pin":
            case.proposal["meta"]["evidence_pack_sha256"] = "0" * 64
        else:
            case.proposal["checks"].reverse()
        case.target.write_bytes(canonical_bytes(Assessment.model_validate(case.proposal)))
    assert call(case, "verify") == 1


def test_unexpected_check_rejected(case):
    case.proposal["checks"][0]["check_id"] = "PF-BACKING-999"
    messages = [p.message for p in assess(case)[1] if p.code == "X9"]
    assert any("unexpected check PF-BACKING-999" in m for m in messages)
    assert any("missing catalogue check" in m for m in messages)


@pytest.mark.parametrize("command", ["check", "ingest"])
@pytest.mark.parametrize("state", ["missing", "invalid"])
def test_proposal_commands_require_accepted_evidence(case, command, state, tmp_path):
    if state == "missing":
        case.run.accepted_pack_path.unlink()
    else:
        case.run.accepted_pack_path.write_text("[]")
    before = snapshot(tmp_path)
    assert call(case, command, "assessment") == 1
    assert snapshot(tmp_path) == before


def test_default_rejection_diagnostic(case):
    case.source.write_text('{"checks": []}')
    assert call(case, "ingest", "assessment") == 1
    issues = json.loads((case.run.root / asm.ISSUES_NAME).read_bytes())
    assert issues["issues"] and not case.target.exists()


def test_trusted_operator_can_rewrite_valid_content(case):
    # Deliberate C3 threat model, selected by the operator: no acceptance
    # receipt/signature exists. Verification checks present content, not history.
    assert call(case, "ingest", "assessment") == 0
    case.proposal["checks"][0]["finding"] = "An operator-revised valid finding."
    arc.write_atomic(case.target, canonical_bytes(Assessment.model_validate(case.proposal)))
    assert call(case, "verify") == 0


def test_catalogue_drift_rejects_ingest_preserving_assessment(case, monkeypatch):
    assert call(case, "ingest", "assessment") == 0
    before = snapshot(case.run.root)
    original_read = Path.read_bytes

    def changed_catalogue(path):
        raw = original_read(path)
        return raw + b"\n" if path == cat.CATALOGUE_PATH else raw

    monkeypatch.setattr(Path, "read_bytes", changed_catalogue)
    assert call(case, "ingest", "assessment") == 1
    assert snapshot(case.run.root) == before


def test_pack_lineage_cycle_blocks_assessment(case, capsys):
    raw = case.pack.model_dump(mode="json")
    raw["observations"] += [{
        "observation_id": identifier, "subject": "Derived custody perimeter",
        "proposition": "A derived test proposition.", "parent_observation_ids": [parent],
        "derivation_rule_id": "rule", "derivation_rule_version": "1",
    } for identifier, parent in [("derived-a", "derived-b"), ("derived-b", "derived-a")]]
    case.run.accepted_pack_path.write_text(json.dumps(raw))
    assert call(case, "ingest", "assessment") == 1
    assert "P5" in capsys.readouterr().err
    assert not case.target.exists()


@pytest.mark.parametrize("mutation", [
    lambda c: c.clear(),
    lambda c: c.update(framework_version=None),
    lambda c: c.update(checks=None),
    lambda c: c.update(checks={}),
    lambda c: c.update(checks=[]),
    lambda c: c["checks"].__setitem__(0, None),
    lambda c: c["checks"][0].pop("question"),
    lambda c: c["checks"][0].update(check_id=[]),
    lambda c: c["checks"][0].update(question=""),
    lambda c: c["checks"].__setitem__(0, c["checks"][1]),
])
def test_malformed_catalogue_returns_issue(case, mutation):
    mutation(case.catalogue)
    assert "invalid_catalogue" in {p.code for p in assess(case)[1]}


@pytest.mark.parametrize("command", ["check", "ingest", "verify"])
def test_malformed_but_pinned_catalogue_fails_cleanly(case, monkeypatch, capsys, command):
    catalogue_bytes = b"{}"
    digest = hashlib.sha256(catalogue_bytes).hexdigest()
    manifest = case.run.manifest.model_copy(update={"catalogue_sha256": digest})
    arc.write_atomic(case.run.root / arc.RUN_MANIFEST_NAME, canonical_bytes(manifest))
    case.run = arc.load_run(case.run.root)
    case.proposal["meta"]["catalogue_sha256"] = digest
    case.source.write_text(json.dumps(case.proposal))
    arc.write_atomic(case.target, canonical_bytes(Assessment.model_validate(case.proposal)))
    original_read = Path.read_bytes
    original_text = Path.read_text
    monkeypatch.setattr(Path, "read_bytes", lambda p: catalogue_bytes
                        if p == cat.CATALOGUE_PATH else original_read(p))
    monkeypatch.setattr(Path, "read_text", lambda p, *a, **kw: "{}"
                        if p == cat.CATALOGUE_PATH else original_text(p, *a, **kw))
    # The pin genuinely matches; D13 cannot and should not reject these bytes.
    assert arc.assess_pack_for_run(canonical_bytes(case.pack), case.run)[1] == ()
    before = case.target.read_bytes()
    words = ("verify",) if command == "verify" else (command, "assessment")
    assert call(case, *words) == 1
    assert "invalid_catalogue" in capsys.readouterr().err
    assert case.target.read_bytes() == before
    if command == "ingest":
        diagnostics = json.loads((case.run.root / asm.ISSUES_NAME).read_bytes())
        assert "invalid_catalogue" in {p["code"] for p in diagnostics["issues"]}
