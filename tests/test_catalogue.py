"""Gates for the catalogue compiler.

The happy path is idempotence: a generated canonical artifact is correct when
regenerating it changes nothing. Everything else is a rejection path -- each test
mutates a copy of the real catalogue and asserts that a specific verifier check
fires.

Several mutations necessarily trip more than one check, because the verifier's
gates overlap by design: dropping a check also changes a pillar count and the
materiality distribution. Those tests assert the named gate fires. Where a
mutation is genuinely isolated -- the three V6 cases, V8, V9, V1 -- the test
asserts that gate fires *and no other*, which is the stronger claim.
"""

from __future__ import annotations

import codecs
import copy
import json
import shutil
from pathlib import Path

import pytest

from plinth import catalogue as cat

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUTS = PROJECT_ROOT / "inputs"


@pytest.fixture(scope="module")
def committed() -> dict:
    return json.loads((INPUTS / "catalogue.json").read_text(encoding="utf-8"))


@pytest.fixture
def mutable(committed: dict) -> dict:
    return copy.deepcopy(committed)


def tmp_inputs(tmp_path: Path) -> Path:
    """A writable copy of the pinned inputs, for tests that must perturb them."""
    inputs = tmp_path / "inputs"
    shutil.copytree(INPUTS, inputs)
    return inputs


def codes(failures) -> list[str]:
    return sorted({f.code for f in failures})


def messages(failures) -> str:
    return "\n".join(f.render() for f in failures)


# --------------------------------------------------------------------------
# happy path
# --------------------------------------------------------------------------


def test_build_is_idempotent(committed: dict) -> None:
    """Two builds from unchanged inputs are byte-identical, and equal the commit."""
    first = cat.canonical_json(cat.build_catalogue())
    second = cat.canonical_json(cat.build_catalogue())
    assert first == second
    assert first == (INPUTS / "catalogue.json").read_text(encoding="utf-8")
    assert json.loads(first) == committed


def test_committed_catalogue_verifies_clean(committed: dict) -> None:
    assert cat.verify(committed) == []


def test_shape_matches_the_framework(committed: dict) -> None:
    assert len(committed["checks"]) == 63
    assert [p["check_count"] for p in committed["pillars"]] == [8, 13, 14, 16, 12]
    assert committed["materiality_vocabulary"] == ["HIGH", "MEDIUM", "LOW"]
    assert committed["materiality_distribution"] == {"HIGH": 55, "MEDIUM": 8, "LOW": 0}
    assert len(committed["gap_rules"]) == 7
    assert set(committed["checks"][0]["fields"]) == set(cat.FIELD_KEYS)


# --------------------------------------------------------------------------
# rejection paths
# --------------------------------------------------------------------------


def test_dropped_check_fails_v2(mutable: dict) -> None:
    del mutable["checks"][0]
    failures = cat.verify(mutable)
    assert "V2" in codes(failures)
    assert "62 checks in the catalogue" in messages(failures)


def test_duplicated_id_fails_v2(mutable: dict) -> None:
    mutable["checks"][1]["check_id"] = mutable["checks"][0]["check_id"]
    failures = cat.verify(mutable)
    assert "V2" in codes(failures)
    assert "PF-CONTROL-001: duplicate check ID" in messages(failures)


def test_id_gap_fails_v3(mutable: dict) -> None:
    mutable["checks"][7]["check_id"] = "PF-CONTROL-009"  # 008 -> 009 leaves a hole
    failures = cat.verify(mutable)
    assert "V3" in codes(failures)
    assert "PF-CONTROL: numbering is not contiguous" in messages(failures)


def test_pillar_id_disagreeing_with_prefix_fails_only_v4(mutable: dict) -> None:
    mutable["checks"][0]["pillar_id"] = "backing"
    failures = cat.verify(mutable)
    assert codes(failures) == ["V4"], messages(failures)
    assert "PF-CONTROL-001: pillar_id is 'backing'" in messages(failures)


def test_wrong_pillar_count_fails_v4(mutable: dict) -> None:
    mutable["pillars"][0]["check_count"] = 9
    failures = cat.verify(mutable)
    assert "V4" in codes(failures)
    assert "the pillars block does not match" in messages(failures)


def test_low_materiality_fails_as_distribution_not_as_vocabulary(mutable: dict) -> None:
    """LOW is a legal value that this framework version happens not to use.

    It must be rejected because the distribution moved, never because the value
    is unknown -- otherwise a valid future framework edit would be unbuildable.
    """
    mutable["checks"][0]["materiality"] = "LOW"
    failures = cat.verify(mutable)
    text = messages(failures)
    assert "V5" in codes(failures)
    assert "materiality distribution mismatch" in text
    assert "not in the materiality vocabulary" not in text
    # Materiality is part of the reconstructed block, so the fidelity gate also
    # catches it. That overlap is the point of V6, not a defect in this case.
    assert "V6" in codes(failures)


def test_paraphrased_question_fails_only_v6(mutable: dict) -> None:
    mutable["checks"][0]["question"] = "Who is able to authorize the scoped material privileged action?"
    failures = cat.verify(mutable)
    assert codes(failures) == ["V6"], messages(failures)
    assert "PF-CONTROL-001: reconstructed block not found" in messages(failures)
    assert "0 leading lines matched; line 1 diverges" in messages(failures)


def test_paraphrased_field_value_fails_only_v6(mutable: dict) -> None:
    check = mutable["checks"][0]
    check["fields"]["expected_observations"] = check["fields"]["expected_observations"].replace(
        "Complete authorizer set", "Full authorizer set"
    )
    failures = cat.verify(mutable)
    assert codes(failures) == ["V6"], messages(failures)
    # Heading, blank line, and the three field lines above it still match, so the
    # diagnostic points at the sixth line of the block rather than at the block.
    assert "5 leading lines matched; line 6 diverges" in messages(failures)
    assert "json: - **Expected observations:** Full authorizer set;" in messages(failures)


def test_swapped_questions_fail_only_v6(mutable: dict) -> None:
    """The case a per-field verifier would pass: both strings still exist."""
    a, b = mutable["checks"][0], mutable["checks"][1]
    a["question"], b["question"] = b["question"], a["question"]
    failures = cat.verify(mutable)
    assert codes(failures) == ["V6"], messages(failures)
    assert len(failures) == 2
    assert {f.message.split(":")[0] for f in failures} == {"PF-CONTROL-001", "PF-CONTROL-002"}


def test_reworded_display_label_fails_only_v8(mutable: dict) -> None:
    mutable["gap_contract"]["display_labels"]["what_is_known"] = "What we know"
    failures = cat.verify(mutable)
    assert codes(failures) == ["V8"], messages(failures)
    assert "what_is_known: display label is 'What we know', expected 'What is known'" in messages(
        failures
    )


def test_gap_rules_missing_unresolved_row_fails_only_v9(mutable: dict) -> None:
    mutable["gap_rules"] = [
        r for r in mutable["gap_rules"] if r["applicability"] != "UNRESOLVED"
    ]
    failures = cat.verify(mutable)
    assert codes(failures) == ["V9"], messages(failures)
    assert "missing the legal pair: UNRESOLVED / None" in messages(failures)


def test_illegal_gap_rule_pair_fails_v9(mutable: dict) -> None:
    """UNRESOLVED with a coverage status contradicts framework section 2.1."""
    mutable["gap_rules"].append(
        {"applicability": "UNRESOLVED", "coverage": "NOT_ASSESSED", "gap_required": True}
    )
    failures = cat.verify(mutable)
    assert codes(failures) == ["V9"], messages(failures)
    assert "illegal pair: UNRESOLVED / NOT_ASSESSED" in messages(failures)


def test_altered_markdown_byte_fails_only_v1(mutable: dict, tmp_path: Path) -> None:
    """The pin is what protects against source drift, so it must be live."""
    inputs = tmp_inputs(tmp_path)
    target = inputs / cat.FRAMEWORK_MD
    # Appended outside every check block, so only the pin should notice.
    target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    failures = cat.verify(mutable, inputs)
    assert codes(failures) == ["V1"], messages(failures)
    assert "sha256 does not match the recorded pin" in messages(failures)
    assert "96618 bytes on disk, 96617 recorded" in messages(failures)


def test_build_from_copied_inputs_records_canonical_paths(tmp_path: Path) -> None:
    """A catalogue built from a copy still names inputs/ -- so the pin is portable."""
    inputs = tmp_inputs(tmp_path)
    built = cat.build_catalogue(inputs)
    assert built["inputs"]["framework_md"]["path"] == f"inputs/{cat.FRAMEWORK_MD}"
    assert cat.verify(built, inputs) == []


# --------------------------------------------------------------------------
# parser rejection paths -- the source, not the artifact
# --------------------------------------------------------------------------


def _framework_text() -> str:
    return (INPUTS / cat.FRAMEWORK_MD).read_text(encoding="utf-8")


def test_parser_rejects_a_reordered_field_block() -> None:
    text = _framework_text().replace(
        "- **Materiality:** HIGH.\n- **Conceptual applicability:** Applies separately to each material privileged action that",
        "- **Conceptual applicability:** Applies separately to each material privileged action that",
        1,
    )
    with pytest.raises(cat.BuildError, match="expected '- \\*\\*Materiality:\\*\\* '"):
        cat.parse_framework(text)


def test_parser_rejects_a_changed_pillar_count() -> None:
    text = _framework_text().replace("## Control — 8 checks", "## Control — 9 checks", 1)
    with pytest.raises(cat.BuildError, match="Control declares 9 checks, table says 8"):
        cat.parse_framework(text)


def test_parser_rejects_a_heading_that_is_not_a_question() -> None:
    text = _framework_text().replace(
        "### PF-CONTROL-001 — Who can authorize the scoped material privileged action?",
        "### PF-CONTROL-001 — Who can authorize the scoped material privileged action.",
        1,
    )
    with pytest.raises(cat.BuildError, match="question does not end with"):
        cat.parse_framework(text)


# --------------------------------------------------------------------------
# malformed artifacts -- a hand-edit must be named, never a traceback
# --------------------------------------------------------------------------


def test_checks_not_a_list_is_named(mutable: dict) -> None:
    mutable["checks"] = {"PF-CONTROL-001": {}}
    failures = cat.verify(mutable)
    assert "V2" in codes(failures)
    assert "checks is dict, expected a list" in messages(failures)


def test_check_missing_a_key_is_named_and_excluded(mutable: dict) -> None:
    del mutable["checks"][0]["question"]
    failures = cat.verify(mutable)
    text = messages(failures)
    assert "PF-CONTROL-001: missing question" in text
    # Excluded from the well-formed set, so the count disagrees too. Both are true.
    assert "62 checks in the catalogue" in text


def test_check_with_wrong_field_keys_is_named(mutable: dict) -> None:
    mutable["checks"][0]["fields"]["extra_field"] = "x"
    failures = cat.verify(mutable)
    assert "PF-CONTROL-001: fields is [" in messages(failures)


def test_gap_rules_not_a_list_is_named(mutable: dict) -> None:
    mutable["gap_rules"] = "APPLIES"
    failures = cat.verify(mutable)
    assert codes(failures) == ["V9"], messages(failures)
    assert "gap_rules is str, expected a list" in messages(failures)


def test_gap_contract_display_labels_not_an_object_is_named(mutable: dict) -> None:
    mutable["gap_contract"]["display_labels"] = ["Question"]
    failures = cat.verify(mutable)
    assert codes(failures) == ["V8"], messages(failures)
    assert "display_labels is list, expected an object" in messages(failures)


def test_wrong_schema_version_fails_v1(mutable: dict) -> None:
    mutable["schema_version"] = "plinth.catalogue/2"
    failures = cat.verify(mutable)
    assert codes(failures) == ["V1"], messages(failures)


# --------------------------------------------------------------------------
# CLI -- read-only paths only; `build` writes the committed artifact
# --------------------------------------------------------------------------


def test_cli_check_verify_and_show_all_exit_zero(capsys) -> None:
    from plinth import cli

    assert cli.main(["catalogue", "build", "--check"]) == 0
    assert cli.main(["catalogue", "verify"]) == 0
    assert cli.main(["catalogue", "show"]) == 0

    out = capsys.readouterr().out
    for expected in (
        "63 checks",
        "backing",
        "Assets & Backing",
        "HIGH | MEDIUM | LOW",
        "HIGH 55 · MEDIUM 8 · LOW 0",
        "what_remains_unresolved  What remains unresolved",
        "7 legal (applicability, coverage) pairs",
        "2e507102",
        "fad5967d",
    ):
        assert expected in out, expected


def test_cli_show_on_a_malformed_catalogue_points_at_verify(monkeypatch, tmp_path, capsys) -> None:
    from plinth import cli

    broken = tmp_path / "catalogue.json"
    broken.write_text('{"schema_version": "plinth.catalogue/1"}\n', encoding="utf-8")
    monkeypatch.setattr(cat, "CATALOGUE_PATH", broken)

    assert cli.main(["catalogue", "show"]) == 1
    assert "Run: plinth catalogue verify" in capsys.readouterr().err


def test_build_does_not_alias_module_state() -> None:
    """Two builds must be independent objects, not views on module constants."""
    first, second = cat.build_catalogue(), cat.build_catalogue()
    first["materiality_vocabulary"].append("BOGUS")
    first["gap_contract"]["fields"].append("bogus")
    first["pillars"][0]["check_count"] = 99
    assert second["materiality_vocabulary"] == ["HIGH", "MEDIUM", "LOW"]
    assert second["gap_contract"]["fields"][-1] == "evidence"
    assert second["pillars"][0]["check_count"] == 8
    assert cat.verify(second) == []


def test_inputs_pin_stripped_to_a_string_is_named(mutable: dict) -> None:
    mutable["inputs"]["framework_md"] = "2e507102"
    failures = cat.verify(mutable)
    assert codes(failures) == ["V1"], messages(failures)
    assert "inputs.framework_md is str, expected an object" in messages(failures)
    assert "sha256 does not match the recorded pin" in messages(failures)


# --------------------------------------------------------------------------
# hardening regressions
# --------------------------------------------------------------------------


def test_truncated_final_field_fails_v6(mutable: dict) -> None:
    """The containment hole: a shortened last value is a prefix of the real line."""
    check = mutable["checks"][0]
    check["fields"]["evidence_sufficiency_principle"] = check["fields"][
        "evidence_sufficiency_principle"
    ][:40]
    source = (INPUTS / cat.FRAMEWORK_MD).read_text(encoding="utf-8")

    # Unanchored, the truncation still matches. The terminating newline is the
    # only thing that rejects it, which is why it is part of the comparison.
    assert cat.reconstruct_block(check) in source
    assert cat.anchored_block(check) not in source

    failures = cat.verify(mutable)
    assert "V6" in codes(failures)
    assert "PF-CONTROL-001: reconstructed block not found" in messages(failures)


def test_empty_final_field_is_rejected_before_reconstruction(mutable: dict) -> None:
    mutable["checks"][0]["fields"]["evidence_sufficiency_principle"] = ""
    failures = cat.verify(mutable)
    assert "V2" in codes(failures)
    assert "PF-CONTROL-001: fields.evidence_sufficiency_principle is empty" in messages(failures)


def test_malformed_scalars_are_named_not_raised(mutable: dict) -> None:
    """Each of these once reached a regex, a Counter or a set operation."""
    cases = [
        ("check_id", 12, "checks[0]: check_id is int, expected a string"),
        ("pillar_id", None, "PF-CONTROL-001: pillar_id is NoneType, expected a string"),
        ("question", "", "PF-CONTROL-001: question is empty"),
        ("materiality", ["HIGH"], "PF-CONTROL-001: materiality is list, expected a string"),
        (
            "question",
            "Who can authorize?\nAnd who cannot?",
            "PF-CONTROL-001: question contains a line break",
        ),
    ]
    for key, value, expected in cases:
        broken = copy.deepcopy(mutable)
        broken["checks"][0][key] = value
        failures = cat.verify(broken)  # must not raise
        assert expected in messages(failures), expected


def test_newline_injected_field_value_is_named(mutable: dict) -> None:
    """Two JSON lines must never pose as one source line."""
    mutable["checks"][0]["fields"]["allocator_purpose"] = (
        "Identify who can approve each material action without conflating "
        "approval with execution.\n- **Materiality:** LOW."
    )
    failures = cat.verify(mutable)
    assert "PF-CONTROL-001: fields.allocator_purpose contains a line break" in messages(failures)


def test_swapped_gap_display_labels_fail_v8(mutable: dict) -> None:
    """Both strings are still headings, so only exact-mapping equality catches it."""
    labels = mutable["gap_contract"]["display_labels"]
    labels["what_is_known"], labels["what_this_means"] = (
        labels["what_this_means"],
        labels["what_is_known"],
    )
    failures = cat.verify(mutable)
    assert codes(failures) == ["V8"], messages(failures)
    text = messages(failures)
    assert "what_is_known: display label is 'What this means', expected 'What is known'" in text
    assert "what_this_means: display label is 'What is known', expected 'What this means'" in text


def test_extra_gap_display_label_fails_v8(mutable: dict) -> None:
    mutable["gap_contract"]["display_labels"]["severity"] = "Severity"
    failures = cat.verify(mutable)
    assert codes(failures) == ["V8"], messages(failures)
    assert "unexpected entry 'severity'" in messages(failures)


def test_flipped_gap_required_fails_v9(mutable: dict) -> None:
    """Right shape, right counts, wrong requirement -- the quiet failure."""
    for rule in mutable["gap_rules"]:
        if rule["applicability"] == "APPLIES" and rule["coverage"] == "MISSING":
            rule["gap_required"] = False
    failures = cat.verify(mutable)
    assert codes(failures) == ["V9"], messages(failures)
    assert "APPLIES / MISSING: gap_required is False, expected True" in messages(failures)


def test_non_boolean_gap_required_fails_v9(mutable: dict) -> None:
    mutable["gap_rules"][0]["gap_required"] = 0
    failures = cat.verify(mutable)
    assert codes(failures) == ["V9"], messages(failures)
    assert "gap_required is 0, expected a boolean" in messages(failures)


def test_wrong_recorded_input_path_fails_v1(mutable: dict) -> None:
    mutable["inputs"]["framework_md"]["path"] = "framework/working/v0.2/" + cat.FRAMEWORK_MD
    failures = cat.verify(mutable)
    assert codes(failures) == ["V1"], messages(failures)
    assert f"expected 'inputs/{cat.FRAMEWORK_MD}'" in messages(failures)


def test_unreadable_and_bom_inputs_are_named_failures(mutable: dict, tmp_path: Path) -> None:
    absent = cat.verify(mutable, tmp_path / "nowhere")
    assert codes(absent) == ["V1"], messages(absent)
    assert "cannot be read" in messages(absent)

    inputs = tmp_inputs(tmp_path)
    target = inputs / cat.FRAMEWORK_MD
    target.write_bytes(codecs.BOM_UTF8 + target.read_bytes())
    failures = cat.verify(mutable, inputs)
    assert codes(failures) == ["V1"], messages(failures)
    assert "byte-order mark" in messages(failures)


# --------------------------------------------------------------------------
# an invalid build is refused before it can overwrite the committed artifact
# --------------------------------------------------------------------------


def _drop_a_check(text: str) -> str:
    start = text.index("### PF-CONTROL-002 —")
    return text[:start] + text[text.index("### PF-CONTROL-003 —") :]


def _add_a_check(text: str) -> str:
    start = text.index("### PF-CONTROL-008 —")
    end = text.index("## Assets & Backing — 13 checks")
    block = text[start:end].replace("PF-CONTROL-008", "PF-CONTROL-009", 1)
    return text[:end] + block + text[end:]


@pytest.fixture
def redirected(monkeypatch, tmp_path: Path) -> Path:
    """Point the CLI at a scratch inputs directory and output path."""
    inputs = tmp_inputs(tmp_path)
    monkeypatch.setattr(cat, "INPUTS_DIR", inputs)
    monkeypatch.setattr(cat, "CATALOGUE_PATH", inputs / "catalogue.json")
    return inputs


@pytest.mark.parametrize(
    ("mutate", "expected_count"),
    [(_drop_a_check, 62), (_add_a_check, 64)],
)
def test_build_refuses_to_write_a_catalogue_of_the_wrong_size(
    redirected: Path, capsys, mutate, expected_count: int
) -> None:
    from plinth import cli

    source = redirected / cat.FRAMEWORK_MD
    source.write_text(mutate(source.read_text(encoding="utf-8")), encoding="utf-8")
    before = cat.CATALOGUE_PATH.read_bytes()

    assert cli.main(["catalogue", "build"]) == 1
    err = capsys.readouterr().err
    assert f"{expected_count} checks in the catalogue, expected 63" in err
    assert "refusing an invalid catalogue" in err
    assert cat.CATALOGUE_PATH.read_bytes() == before


def test_a_successful_build_always_passes_verify(redirected: Path) -> None:
    from plinth import cli

    assert cli.main(["catalogue", "build"]) == 0
    written = json.loads(cat.CATALOGUE_PATH.read_text(encoding="utf-8"))
    assert cat.verify(written, cat.INPUTS_DIR) == []


def test_build_check_detects_crlf_drift(redirected: Path, capsys) -> None:
    """A text-mode read would translate this away; the comparison is on bytes."""
    from plinth import cli

    assert cli.main(["catalogue", "build"]) == 0
    assert cli.main(["catalogue", "build", "--check"]) == 0
    capsys.readouterr()

    canonical = cat.CATALOGUE_PATH.read_bytes()
    cat.CATALOGUE_PATH.write_bytes(canonical.replace(b"\n", b"\r\n"))
    # Universal-newline translation makes the drifted file read back identical.
    # That is exactly why the comparison in `build --check` is on bytes.
    assert cat.CATALOGUE_PATH.read_text(encoding="utf-8") == canonical.decode("utf-8")
    assert cat.CATALOGUE_PATH.read_bytes() != canonical

    assert cli.main(["catalogue", "build", "--check"]) == 1
    assert "differs from a fresh build" in capsys.readouterr().err


def test_cli_failure_paths_exit_one(redirected: Path, monkeypatch, capsys) -> None:
    from plinth import cli

    cat.CATALOGUE_PATH.unlink(missing_ok=True)
    assert cli.main(["catalogue", "verify"]) == 1
    assert cli.main(["catalogue", "show"]) == 1
    assert cli.main(["catalogue", "build", "--check"]) == 1
    assert "does not exist" in capsys.readouterr().err

    # An unwritable destination must be reported, not raised.
    wedged = redirected / "wedged"
    wedged.mkdir()
    monkeypatch.setattr(cat, "CATALOGUE_PATH", wedged)
    assert cli.main(["catalogue", "build"]) == 1
    assert "cannot write" in capsys.readouterr().err


def test_display_path_tolerates_a_path_outside_the_project(tmp_path: Path) -> None:
    from plinth import cli

    assert cli._display_path(cat.PROJECT_ROOT / "inputs" / "x.json") == "inputs/x.json"
    assert cli._display_path(tmp_path / "x.json") == str(tmp_path / "x.json")
