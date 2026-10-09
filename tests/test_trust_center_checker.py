"""The Trust Center skill scripts against runs the compiler actually accepted.

Every page here is built the way the skill tells an agent to build one: copy the
shell, run ``prefill_shell.py``, write the narrative placeholders, then check.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from plinth import archive as arc, assessment as asm, catalogue as cat, cli
from plinth.models import Campaign, EvidencePack, canonical_bytes, canonical_sha256
from plinth.vocab import AcquisitionMode

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "plinth-trust-center"
SHELL = SKILL / "assets" / "v0.3-two-mode-shell.html"
# Inner CSS of <style id="v03-skin">, byte-identical to the exemplar it was derived from.
V03_SKIN_SHA256 = "8792c57c991bd44c40154fa876ea148385d3b6c91a6f50d63983c3df6953d11a"
PRODUCT_RE = re.compile(r"(?i)(?<![a-z])(ousg|ondo|xauh|qmc|realfi|usdr)(?![a-z])")
FILL_REGIONS = {
    "framework-strip", "open-row", "evidence-requests", "source-count", "source-records",
    "methodology-distribution", "technical-index", "locator-records", "observation-records",
    "check-records", "footer-counts",
} | {f"pillar-{kind}:{pillar}" for kind in ("count", "table")
     for pillar in ("control", "backing", "economics", "governance_compliance", "continuity")}


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SKILL / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    # Registered before execution: dataclasses resolve string annotations through sys.modules.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


records_mod = _load("trust_center_records")
checker = _load("check_morphed_html")
prefill = _load("prefill_shell")


# ---------------------------------------------------------------------------
# runs
# ---------------------------------------------------------------------------
def _gap(check: dict, *, evidence_ids=(), unresolved="The complete proposition has not been assessed."):
    return {
        "question": check["question"], "what_is_known": "Only the generated statements were reviewed.",
        "what_remains_unresolved": unresolved,
        "what_this_means": "These records cannot establish the full check proposition.",
        "what_would_close_it": "Dated, scoped records that address the complete proposition.",
        "evidence": "The generated statements bound this review.",
        "evidence_observation_ids": list(evidence_ids),
    }


@pytest.fixture
def case_varied(tmp_path):
    """Every state the renderer must handle, accepted through the compiler's own rules.

    Two sources whose ids differ only by case, a blocked attempt beside a
    successful one, an excluded source with no acquisition, a ``javascript:``
    URL, a derived observation with an effective period, a quote containing
    ``</script>`` and ``{{x}}``, and one pillar that cites no observations.
    """
    now = datetime.now(UTC)
    campaign = Campaign.model_validate({
        "run_id": "c5-varied", "subject": "Generated product",
        "subject_description": "Test documentary perimeter",
        "cutoff": (now - timedelta(days=1)).isoformat(),
        "declared_acquisition_modes": ["HTTP_DOWNLOAD"],
        "declared_scope_note": "Two generated documents; one blocked attempt; no completed routes.",
        "bounded_public_evidence": True,
    })
    root = tmp_path / "runs"
    run = arc.create_run(campaign, runs_root=root)
    doc_a = tmp_path / "custody.txt"
    doc_a.write_text("Custody is held by Example Trust. Quoted markup: </script><b>bold</b> {{x}} end.")
    doc_b = tmp_path / "units.txt"
    doc_b.write_text("The product reports 100 units outstanding.")
    run, acq_a, art_a = arc.add_artifact(run, doc_a, source_id="SRC-A",
                                         acquisition_mode=AcquisitionMode.HTTP_DOWNLOAD,
                                         media_type="text/plain", retrieved_at=now)
    run, acq_b, art_b = arc.add_artifact(run, doc_b, source_id="src-a",
                                         acquisition_mode=AcquisitionMode.HTTP_DOWNLOAD,
                                         media_type="text/plain", retrieved_at=now)
    pack = EvidencePack.model_validate({
        "schema_version": "plinth.evidence/1", "campaign": campaign.model_dump(mode="json"),
        "sources": [
            {"source_id": "SRC-A", "title": "Custody statement", "source_type": "issuer_documentation",
             "url": "javascript:alert(1)", "research_posture": "self_attestation"},
            {"source_id": "src-a", "title": "Unit report", "source_type": "issuer_report",
             "url": "https://example.com/report", "research_posture": "independent_assurance"},
            {"source_id": "SRC-C", "title": "Marketing page", "source_type": "marketing",
             "disposition": "EXCLUDED", "excluded_reason": "Marketing copy is outside the perimeter."},
        ],
        "acquisitions": [
            {"acquisition_id": "SRC-A-blocked", "source_id": "SRC-A", "acquisition_mode": "HTTP_DOWNLOAD",
             "outcome": "ACCESS_BLOCKED", "attempted_at": (now - timedelta(hours=1)).isoformat(),
             "failure_reason": "HTTP 403 from the publisher"},
            acq_a.model_dump(mode="json"), acq_b.model_dump(mode="json"),
        ],
        "artifacts": [art_a.model_dump(mode="json"), art_b.model_dump(mode="json")],
        "locator_catalog": [
            {"locator_id": "loc-a", "artifact_sha256": art_a.sha256, "locator_type": "document_section",
             "section": "Custody", "quoted_text": doc_a.read_text()},
            {"locator_id": "LOC-B", "artifact_sha256": art_b.sha256, "locator_type": "document_section",
             "section": "Units", "quoted_text": doc_b.read_text()},
        ],
        "observations": [
            {"observation_id": "OBS-1", "proposition": "Custody is held by Example Trust.",
             "subject": "Custody", "evidence_as_of": (now - timedelta(days=2)).isoformat(),
             "supports": [{"acquisition_id": acq_a.acquisition_id, "locator_id": "loc-a"}]},
            {"observation_id": "obs-1", "proposition": "100 units are reported outstanding.",
             "subject": "Units", "value": 100, "unit": "units",
             "effective_period_start": (now - timedelta(days=30)).isoformat(),
             "effective_period_end": (now - timedelta(days=2)).isoformat(),
             "supports": [{"acquisition_id": acq_b.acquisition_id, "locator_id": "LOC-B"}]},
            {"observation_id": "OBS-DERIVED", "proposition": "Both statements concern the same reporting period.",
             "subject": "Reporting period", "parent_observation_ids": ["OBS-1", "obs-1"],
             "derivation_rule_id": "same-period", "derivation_rule_version": "1"},
        ],
        "routes": [
            {"route_id": "R1", "description": "Issuer documents", "acquisition_mode": "HTTP_DOWNLOAD",
             "status": "PARTIAL", "source_ids": ["SRC-A", "src-a"],
             "limitation": "One request was blocked by the publisher."},
        ],
        "generated_at": (now + timedelta(minutes=1)).isoformat(),
    })
    found = arc.assess_pack_for_run(canonical_bytes(pack), run)[1]
    assert found == (), found
    run.accepted_pack_path.write_bytes(canonical_bytes(pack))
    catalogue = json.loads(cat.CATALOGUE_PATH.read_bytes())

    def not_assessed(check):
        return {"check_id": check["check_id"], "applicability": "APPLIES",
                "applicability_basis": "The custody statement establishes the structure.",
                "applicability_observation_ids": ["OBS-1"], "coverage": "NOT_ASSESSED",
                "coverage_basis": "Route R1 is unfinished.",
                "finding": f"Only the custody statement was reviewed for {check['check_id']}.",
                "gap": _gap(check)}

    checks = []
    by_pillar: dict[str, list[dict]] = {}
    for check in catalogue["checks"]:
        by_pillar.setdefault(check["pillar_id"], []).append(check)
    for pillar, members in by_pillar.items():
        for position, check in enumerate(members):
            record = not_assessed(check)
            if pillar == "control" and position == 0:
                record = {"check_id": check["check_id"], "applicability": "APPLIES",
                          "applicability_basis": "The custody statement establishes the structure.",
                          "applicability_observation_ids": ["OBS-1"], "coverage": "EVIDENCED",
                          "coverage_basis": "The custody statement answers the bounded proposition.",
                          "finding_observation_ids": ["OBS-1"],
                          "finding": "Example Trust holds custody according to the issuer statement."}
            elif pillar == "backing" and position == 0:
                record = {"check_id": check["check_id"], "applicability": "APPLIES",
                          "applicability_basis": "Both statements address the reserve.",
                          "applicability_observation_ids": ["OBS-1"], "coverage": "CONTRADICTORY",
                          "coverage_basis": "The two statements conflict.",
                          "finding_observation_ids": ["OBS-1", "obs-1"],
                          "finding": "The custody and unit statements conflict on the reserve perimeter.",
                          "contradiction": {"conflicting_observation_ids": ["OBS-1", "obs-1"],
                                            "conflict_basis": "Different perimeters for one reserve.",
                                            "precedence_considered": ["No source states precedence."]},
                          "gap": _gap(check, evidence_ids=["OBS-1", "obs-1"],
                                      unresolved="Which perimeter governs the reserve.")}
            elif pillar == "backing" and position == 1:
                record = {"check_id": check["check_id"], "applicability": "APPLIES",
                          "applicability_basis": "The custody statement establishes the structure.",
                          "applicability_observation_ids": ["OBS-1"], "coverage": "PARTIAL",
                          "coverage_basis": "Only the reporting period is established.",
                          "finding_observation_ids": ["OBS-DERIVED"],
                          "finding": "The derived period is the only established part.",
                          "gap": _gap(check, evidence_ids=["OBS-DERIVED"],
                                      unresolved="The quantities for that period.")}
            elif pillar == "economics" and position == 0:
                record = {"check_id": check["check_id"], "applicability": "DOES_NOT_APPLY",
                          "applicability_basis": "The unit report shows no supported entry route.",
                          "applicability_observation_ids": ["obs-1"], "coverage": "NOT_APPLICABLE",
                          "finding": "No supported entry route exists in the accepted records."}
            elif pillar == "continuity":
                record = {"check_id": check["check_id"], "applicability": "UNRESOLVED",
                          "applicability_basis": "No accepted record addresses continuity.",
                          "finding": "Continuity arrangements are not addressed by any accepted record.",
                          "gap": _gap(check, unresolved="Whether the structural condition exists.")}
            checks.append(record)
    order = [check["check_id"] for check in catalogue["checks"]]
    checks.sort(key=lambda record: order.index(record["check_id"]))
    proposal = {"schema_version": "plinth.assessment/1", "checks": checks, "meta": {
        "campaign_run_id": campaign.run_id, "framework_version": catalogue["framework_version"],
        "catalogue_sha256": run.manifest.catalogue_sha256,
        "evidence_pack_sha256": canonical_sha256(pack),
        "generated_at": (now + timedelta(minutes=2)).isoformat(),
    }}
    source = run.root / asm.PROPOSED_ASSESSMENT_NAME
    source.write_text(json.dumps(proposal))
    return SimpleNamespace(run=run, root=root, target=run.root / asm.ACCEPTED_ASSESSMENT_NAME)


@pytest.fixture(params=["case", "case_varied"])
def accepted(request):
    """A run whose evidence and assessment the compiler accepted."""
    case = request.getfixturevalue(request.param)
    run_id = case.run.manifest.campaign.run_id
    assert cli.main(["ingest", "assessment", run_id, "--runs-root", str(case.root)]) == 0
    assert cli.main(["verify", run_id, "--runs-root", str(case.root)]) == 0
    files = SimpleNamespace(assessment=case.target, evidence=case.run.accepted_pack_path,
                            catalogue=cat.CATALOGUE_PATH)
    inputs = records_mod.load_inputs(files.assessment, files.evidence, files.catalogue)
    return SimpleNamespace(name=request.param, files=files, inputs=inputs,
                           records=records_mod.Records(inputs))


@pytest.fixture
def varied(case_varied):
    run_id = case_varied.run.manifest.campaign.run_id
    assert cli.main(["ingest", "assessment", run_id, "--runs-root", str(case_varied.root)]) == 0
    files = SimpleNamespace(assessment=case_varied.target, evidence=case_varied.run.accepted_pack_path,
                            catalogue=cat.CATALOGUE_PATH)
    inputs = records_mod.load_inputs(files.assessment, files.evidence, files.catalogue)
    return SimpleNamespace(files=files, inputs=inputs, records=records_mod.Records(inputs))


def file_args(files) -> list[str]:
    return ["--assessment", str(files.assessment), "--evidence", str(files.evidence),
            "--catalogue", str(files.catalogue)]


def prefilled(tmp_path: Path, files) -> str:
    out = tmp_path / "prefilled.html"
    assert prefill.main(["--product", "Generated product", *file_args(files), "--out", str(out)]) == 0
    return out.read_text(encoding="utf-8")


PAYLOAD_SPLIT = re.compile(r'(<script type="application/json" id="plinth-research-state">.*?</script>)', re.S)


def author(page: str, records) -> str:
    """Write every narrative placeholder the way the skill asks an author to.

    Pillar citations point at a source behind that pillar's own checks; a pillar
    that cites nothing loses its example citations. Everything else becomes
    neutral text. The payload is never touched.
    """
    for pillar, heading in records_mod.PILLAR_HEADING.items():
        start = page.index(f'<section aria-labelledby="{heading}"')
        end = page.index("</section>", start)
        segment = page[start:end]
        sources = sorted(records.pillar_sources(pillar))
        if sources:
            observations = [oid for oid in records.pillar_observation_ids(pillar)
                            if sources[0] in records.observation_sources(oid)]
            segment = (segment.replace("{{SOURCE_ID}}", sources[0])
                       .replace("{{OBSERVATION_IDS}}", observations[0])
                       .replace("{{SOURCE TITLE}}", records.sources[sources[0]]["title"]))
        else:
            segment = re.sub(r'<a class="claim-source[^"]*"[^>]*>.*?</a>', "", segment)
            segment = re.sub(r'<span class="source-prefix">.*?</span>', "", segment)
            segment = segment.replace("{{OBSERVATION_IDS}}", "")
        page = page[:start] + segment + page[end:]
    parts = PAYLOAD_SPLIT.split(page)
    for i, part in enumerate(parts):
        if part.startswith('<script type="application/json"'):
            continue
        part = (part.replace("{{SOURCE_ID}}", next(iter(records.sources)))
                .replace("{{OBSERVATION_IDS}}", next(iter(records.observations)))
                .replace("{{CHECK_IDS}}", records.check_order[0])
                .replace("{{CHECK_ID}}", records.check_order[0])
                .replace("{{EVIDENCE_CLASS}}", "mixed"))
        parts[i] = checker.PLACEHOLDER_RE.sub("Generated text", part)
    return "".join(parts)


def run_checker(tmp_path: Path, html: str, files) -> int:
    page = tmp_path / "page.html"
    page.write_text(html, encoding="utf-8")
    return checker.main([str(page), "--reference", str(SHELL), *file_args(files)])


# ---------------------------------------------------------------------------
# the shell
# ---------------------------------------------------------------------------
SHELL_TEXT = SHELL.read_text(encoding="utf-8")


def test_shell_contains_no_product_content():
    outside_fonts = re.sub(r"url\(data:font[^)]*\)", "", SHELL_TEXT)
    assert PRODUCT_RE.findall(outside_fonts) == []
    body = SHELL_TEXT[SHELL_TEXT.index("<body"):]  # the head's CSS selectors name these values legitimately
    assert "data-record-id" not in body, "canonical cards are rendered by prefill, never shipped"
    hrefs = set(re.findall(r'href="([^"]*)"', body))
    assert all(h.startswith("#") or h == "https://example.invalid/" for h in hrefs), hrefs
    for name in ("data-check-ids", "data-observation-ids", "data-evidence-class", "data-state"):
        values = set(re.findall(rf'{name}="([^"]*)"', body))
        assert all(v.startswith("{{") for v in values), (name, values)


def test_shell_keeps_the_exemplar_theme_and_fixes_fragment_decoding():
    skin = re.search(r'<style id="v03-skin">(.*?)</style>', SHELL_TEXT, re.S).group(1)
    assert hashlib.sha256(skin.encode("utf-8")).hexdigest() == V03_SKIN_SHA256
    assert "var id;try{id=decodeURIComponent(location.hash.slice(1))}catch(error){id=''}" in SHELL_TEXT
    assert "var id=decodeURIComponent(" not in SHELL_TEXT


def test_shell_keeps_record_titles_readable_on_narrow_screens():
    # Inherited defect: below 760px the badges take the full row and the summary
    # did not wrap, so every record title collapsed to zero width.
    fixes = re.search(r'<style data-purpose="shell-fixes">(.*?)</style>', SHELL_TEXT, re.S)
    assert fixes and "@media(max-width:760px){.record>summary{flex-wrap:wrap}}" in fixes.group(1)
    assert SHELL_TEXT.index('data-purpose="shell-fixes"') > SHELL_TEXT.index('<style id="v03-skin">')


def test_shell_has_every_structure_the_checker_and_router_need():
    index = checker.Index()
    index.feed(SHELL_TEXT)
    assert checker.REQUIRED_IDS <= set(index.ids)
    assert checker.REQUIRED_CLASSES - {"record"} <= index.classes
    panels = [element for element in checker.descendants_with_class(checker.element_by_id(index, "analyst-main"), "panel")
              if element.attrs.get("data-mode-panel") == "analyst"]
    assert [checker.panel_role(panel) for panel in panels] == checker.PANEL_ROLE_ORDER
    for selector_id in ("v3-executive", "v3-analyst", "executive"):
        assert index.ids[selector_id] == 1
    assert sorted(index.mode_values) == ["analyst", "executive"]
    assert set(re.findall(r'data-fill="([^"]+)"', SHELL_TEXT)) == FILL_REGIONS
    for key in ("control", "backing", "economics", "governance", "continuity"):
        assert index.ids[f"checks-{key}"] == 1


def test_bare_shell_is_not_an_output(tmp_path, varied):
    assert checker.find_placeholders(SHELL_TEXT)
    assert run_checker(tmp_path, SHELL_TEXT, varied.files) == 1


# ---------------------------------------------------------------------------
# the payload
# ---------------------------------------------------------------------------
def test_payload_is_the_accepted_records_with_every_angle_bracket_escaped(varied):
    text = records_mod.payload_text(varied.inputs)
    assert "<" not in text and "\\u003c/script>" in text
    assert json.loads(text) == {"assessment": varied.inputs.assessment, "evidence": varied.inputs.evidence}
    checker.check_payload(text, varied.inputs)


def _payload(value) -> str:
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


@pytest.mark.parametrize("mutate, message", [
    (lambda p: p["assessment"]["checks"].pop(), "embedded assessment differs"),
    (lambda p: p.__setitem__("extra", {}), "exactly the keys"),
    (lambda p: p["assessment"]["checks"][0].__setitem__("search_completed", False), "embedded assessment differs"),
    (lambda p: p["evidence"]["observations"][0].__setitem__("observation_id", "OBS-RENAMED"),
     "embedded evidence differs"),
])
def test_payload_must_equal_the_accepted_records(varied, mutate, message):
    payload = json.loads(json.dumps({"assessment": varied.inputs.assessment, "evidence": varied.inputs.evidence}))
    mutate(payload)
    with pytest.raises(AssertionError, match=message):
        checker.check_payload(_payload(payload), varied.inputs)


def test_payload_must_escape_angle_brackets(varied):
    raw = json.dumps({"assessment": varied.inputs.assessment, "evidence": varied.inputs.evidence},
                     ensure_ascii=False)
    assert "</script>" in raw
    with pytest.raises(AssertionError, match="unescaped"):
        checker.check_payload(raw, varied.inputs)


def test_inputs_must_belong_to_one_run(tmp_path, varied, case):
    assert cli.main(["ingest", "assessment", case.run.manifest.campaign.run_id, "--runs-root", str(case.root)]) == 0
    with pytest.raises(records_mod.RecordError, match="evidence_pack_sha256"):
        records_mod.load_inputs(varied.files.assessment, case.run.accepted_pack_path, cat.CATALOGUE_PATH)
    edited = tmp_path / "catalogue.json"
    edited.write_bytes(cat.CATALOGUE_PATH.read_bytes() + b"\n")
    with pytest.raises(records_mod.RecordError, match="catalogue_sha256"):
        records_mod.load_inputs(varied.files.assessment, varied.files.evidence, edited)


# ---------------------------------------------------------------------------
# end to end
# ---------------------------------------------------------------------------
def test_prefilled_and_authored_page_passes(tmp_path, accepted, capsys):
    page = author(prefilled(tmp_path, accepted.files), accepted.records)
    capsys.readouterr()  # discard prefill's report
    assert run_checker(tmp_path, page, accepted.files) == 0
    records = accepted.records
    assert capsys.readouterr().out == (
        "PASS: v0.3 two-mode interface; 6 Executive blocks; 14 Analyst panels; 63 checks; "
        f"{len(records.observations)} observations; {len(records.sources)} sources\n")


def test_prefill_renders_every_record_state(tmp_path, varied):
    page = prefilled(tmp_path, varied.files)
    assert 'id="source-SRC-A"' in page and 'id="source-src-a"' in page
    assert 'id="observation-OBS-1"' in page and 'id="observation-obs-1"' in page
    assert 'href="javascript:' not in page and "javascript:alert(1) (not linked" in page
    assert 'data-state="EXCLUDED"' in page and "NO ACQUISITION" in page
    assert "SRC-A-blocked: HTTP_DOWNLOAD, ACCESS_BLOCKED" in page and "failure: HTTP 403" in page
    assert 'href="#observation-OBS-1">OBS-1</a>, <a href="#observation-obs-1">obs-1</a>' in page
    assert "same-period version 1" in page and "effective " in page
    assert '<section aria-labelledby="pillar-continuity" data-pillar-sources="none">' in page
    assert page.count('aria-labelledby="pillar-control" data-pillar-sources') == 0
    assert "{{x}}" in page, "the quote survives inside the escaped payload"


def test_prefill_refuses_to_overwrite_and_rejects_mismatched_inputs(tmp_path, varied, case):
    out = tmp_path / "page.html"
    out.write_text("keep")
    assert prefill.main(["--product", "P", *file_args(varied.files), "--out", str(out)]) == 1
    assert out.read_text() == "keep"
    mixed = SimpleNamespace(assessment=varied.files.assessment, evidence=case.run.root / "missing.json",
                            catalogue=cat.CATALOGUE_PATH)
    assert prefill.main(["--product", "P", *file_args(mixed), "--out", str(tmp_path / "x.html")]) == 1


def _first_check_card(page: str, check_id: str) -> tuple[int, int]:
    start = page.index(f'<details class="record check-record" id="check-{check_id}"')
    return start, page.index("</details>", start)


def _edit_finding(page: str) -> str:
    start, end = _first_check_card(page, "PF-CONTROL-001")
    card = page[start:end].replace("Example Trust holds custody", "Somebody holds custody")
    return page[:start] + card + page[end:]


def _edit_open_row(page: str) -> str:
    return re.sub(r'(data-pillar="control" data-check-ids=")PF-CONTROL-001 ', r"\1", page, count=1)


def _retarget_pillar_links(page: str, heading: str, source_id: str) -> str:
    start = page.index(f'<section aria-labelledby="{heading}"')
    end = page.index("</section>", start)
    segment = re.sub(r'(class="claim-source[^"]*" href="#source-)[^"]+', rf"\g<1>{source_id}", page[start:end])
    return page[:start] + segment + page[end:]


MUTATIONS = [
    ("check coverage", lambda p: p.replace('data-record-id="PF-CONTROL-001" data-applicability="APPLIES" '
                                           'data-coverage="EVIDENCED"',
                                           'data-record-id="PF-CONTROL-001" data-applicability="APPLIES" '
                                           'data-coverage="PARTIAL"'), "check marker mismatch"),
    ("check applicability", lambda p: p.replace('data-record-id="PF-ECONOMICS-001" data-applicability="DOES_NOT_APPLY"',
                                                'data-record-id="PF-ECONOMICS-001" data-applicability="APPLIES"'),
     "check marker mismatch"),
    ("observation marker", lambda p: p.replace('data-record-type="observation" data-record-id="OBS-1"',
                                               'data-record-id="OBS-1"'), "missing canonical observation marker"),
    ("source marker", lambda p: p.replace('data-record-type="source" data-record-id="src-a"',
                                          'data-record-id="src-a"'), "missing canonical source marker"),
    ("stray marker", lambda p: p.replace('data-record-type="check" data-record-id="PF-GOV-001"',
                                         'data-record-type="check" data-record-id="PF-GOV-099"'),
     "records the run does not have"),
    ("visible finding", _edit_finding, "does not show its accepted finding"),
    ("visible source title", lambda p: p.replace("src-a — Unit report", "src-a — Unit memo"), "does not show its title"),
    ("visible metric", lambda p: p.replace('<div class="framework-n">63</div>', '<div class="framework-n">62</div>'),
     "framework figure shown"),
    ("metric value", lambda p: p.replace('data-metric="total" data-value="63"', 'data-metric="total" data-value="62"'),
     "framework strip differs"),
    ("partition", _edit_open_row, "open-evidence group differs"),
    ("placeholder", lambda p: p.replace('<div class="hero-name">', '<div class="hero-name">{{SUBJECT NAME}}', 1),
     "unfilled placeholders"),
    ("fill marker", lambda p: p.replace('<footer class="analyst-footer">', '<footer class="analyst-footer" data-fill="x">'),
     "unfilled prefill region"),
    ("javascript href", lambda p: p.replace('<footer class="analyst-footer">',
                                            '<footer class="analyst-footer"><a href="javascript:alert(1)">x</a>'),
     "links must be"),
    ("no related pillar source", lambda p: _retarget_pillar_links(p, "pillar-control", "src-a"),
     "links no source that supports its own checks"),
    ("false no-source marker", lambda p: p.replace('<section aria-labelledby="pillar-control">',
                                                   '<section aria-labelledby="pillar-control" data-pillar-sources="none">'),
     "must not be marked"),
    ("source on empty pillar", lambda p: p.replace(
        '<section aria-labelledby="pillar-continuity" data-pillar-sources="none">',
        '<section aria-labelledby="pillar-continuity" data-pillar-sources="none">'
        '<a class="claim-source" href="#source-SRC-A">Custody statement</a>'),
     "cites no observations but links sources"),
    ("unknown observation id", lambda p: p.replace('data-observation-ids="OBS-1"', 'data-observation-ids="OBS-404"', 1),
     "names unknown observation"),
    ("payload drift", lambda p: p.replace('"finding":"Example Trust holds custody', '"finding":"Example Trust held custody'),
     "embedded assessment differs"),
]


@pytest.mark.parametrize("label, mutate, message", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_checker_rejects(tmp_path, varied, capsys, label, mutate, message):
    page = author(prefilled(tmp_path, varied.files), varied.records)
    mutated = mutate(page)
    assert mutated != page, f"mutation {label!r} did not apply"
    assert run_checker(tmp_path, mutated, varied.files) == 1
    assert message in capsys.readouterr().err


def test_unrelated_pillar_source_is_a_warning_not_a_failure(tmp_path, varied, capsys):
    page = author(prefilled(tmp_path, varied.files), varied.records)
    once = page.replace('href="#source-SRC-A" data-evidence-class="mixed"',
                        'href="#source-src-a" data-evidence-class="mixed"', 1)
    assert once != page
    capsys.readouterr()
    assert run_checker(tmp_path, once, varied.files) == 0
    captured = capsys.readouterr()
    assert "WARN: control also links sources that support none of its checks: ['src-a']" in captured.err
    assert captured.out.startswith("PASS:")
