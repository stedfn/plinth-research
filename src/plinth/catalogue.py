"""Compile the pinned Framework v0.2 markdown into a canonical ``catalogue.json``.

The transformation is deterministic and requires exact byte fidelity, so it is a
parser rather than a model call. The source format is rigid: a check heading, six
fixed labels in fixed order, one-line values, five fixed pillar sections.

Three entry points:

``build``   parse the pinned markdown into canonical JSON
``verify``  independently reconstruct each check's markdown block from the
            committed JSON and assert that exact string is present in the source
``show``    human summary

``verify`` is anchored on raw file bytes rather than on the parser's own
assumptions, so it catches a *wrong* parser where ``build --check`` catches only
a *changed* one.
"""

from __future__ import annotations

import codecs
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .vocab import Applicability, Coverage, GapField, Materiality, PillarId

SCHEMA_VERSION = "plinth.catalogue/1"
FRAMEWORK_VERSION = "v0.2-working"
FRAMEWORK_STATUS = "Pre-consolidation testing draft"

# ``inputs/`` is a sibling of ``src/``, so it resolves the same way from an
# editable install as from the source tree.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUTS_DIR = PROJECT_ROOT / "inputs"
CATALOGUE_PATH = INPUTS_DIR / "catalogue.json"

FRAMEWORK_MD = "plinth-framework-v0.2-working.md"
OUTPUT_CONTRACT_MD = "trust-center-output-contract-v0.1.md"

# Recorded in the JSON regardless of which directory was read, so a catalogue
# built from a copy still names its canonical location.
INPUT_FILES = {
    "framework_md": FRAMEWORK_MD,
    "output_contract_md": OUTPUT_CONTRACT_MD,
}


@dataclass(frozen=True)
class Pillar:
    pillar_id: str
    display_label: str
    id_prefix: str
    check_count: int


# Written by hand, not inferred. No slug rule maps "Assets & Backing" to
# ``backing`` or "Governance & Compliance" to ``governance_compliance`` with the
# ID prefix ``PF-GOV``.
PILLAR_TABLE = (
    Pillar(PillarId.CONTROL, "Control", "PF-CONTROL", 8),
    Pillar(PillarId.BACKING, "Assets & Backing", "PF-BACKING", 13),
    Pillar(PillarId.ECONOMICS, "Economics", "PF-ECONOMICS", 14),
    Pillar(PillarId.GOVERNANCE_COMPLIANCE, "Governance & Compliance", "PF-GOV", 16),
    Pillar(PillarId.CONTINUITY, "Continuity", "PF-CONTINUITY", 12),
)

MATERIALITY_KEY = "materiality"

# Document order is normative: both the parser and the reconstructor read it,
# which is why ``fields`` is a JSON object rather than an ordered array.
# ``materiality`` is hoisted to the top level of each check; the reconstructor
# puts it back at document position 2.
FIELD_LABELS = (
    ("Allocator purpose", "allocator_purpose"),
    ("Materiality", MATERIALITY_KEY),
    ("Conceptual applicability", "conceptual_applicability"),
    ("Expected observations", "expected_observations"),
    ("Likely acquisition mode(s)", "likely_acquisition_modes"),
    ("Evidence/sufficiency principle", "evidence_sufficiency_principle"),
)
FIELD_KEYS = tuple(key for _, key in FIELD_LABELS if key != MATERIALITY_KEY)
CHECK_KEYS = ("check_id", "pillar_id", "question", "materiality", "fields")
# The scalar members of a check, in the order a failure report reads best.
SCALAR_KEYS = ("check_id", "pillar_id", "question", "materiality")

CHECK_ID_RE = re.compile(r"^PF-(CONTROL|BACKING|ECONOMICS|GOV|CONTINUITY)-(\d{3})$")

# The JSON projections of the two closed vocabularies this module emits.
MATERIALITY_VALUES = tuple(str(m) for m in Materiality)
GAP_FIELD_KEYS = tuple(str(f) for f in GapField)

TOTAL_CHECKS = sum(p.check_count for p in PILLAR_TABLE)
EXPECTED_MATERIALITY_DISTRIBUTION = {"HIGH": 55, "MEDIUM": 8, "LOW": 0}

# Output Contract section 6. Keys are stable; the strings are the ``### <label>``
# headings and are verified against that document.
GAP_DISPLAY_LABELS = {
    GapField.QUESTION: "Question",
    GapField.WHAT_IS_KNOWN: "What is known",
    GapField.WHAT_REMAINS_UNRESOLVED: "What remains unresolved",
    GapField.WHAT_THIS_MEANS: "What this means",
    GapField.WHAT_WOULD_CLOSE_IT: "What would close it",
    GapField.EVIDENCE: "Evidence",
}

# Exhaustive over the legal (applicability, coverage) space, which makes it
# stronger than a gap-requirement table: any pair absent from it is illegal by
# construction. Framework section 2.1 -- only DOES_NOT_APPLY produces
# NOT_APPLICABLE, and UNRESOLVED has no coverage status at all.
GAP_RULES = (
    (Applicability.APPLIES, Coverage.EVIDENCED, False),
    (Applicability.APPLIES, Coverage.PARTIAL, True),
    (Applicability.APPLIES, Coverage.MISSING, True),
    (Applicability.APPLIES, Coverage.CONTRADICTORY, True),
    (Applicability.APPLIES, Coverage.NOT_ASSESSED, True),
    (Applicability.UNRESOLVED, None, True),
    (Applicability.DOES_NOT_APPLY, Coverage.NOT_APPLICABLE, False),
)


class BuildError(Exception):
    """The pinned markdown does not have the shape the parser requires."""


def pillar_record(pillar: Pillar) -> dict:
    """The JSON shape of one pillar. Build emits it; verify compares against it."""
    return {
        "pillar_id": str(pillar.pillar_id),
        "display_label": pillar.display_label,
        "id_prefix": pillar.id_prefix,
        "check_count": pillar.check_count,
    }


# --------------------------------------------------------------------------
# reading
# --------------------------------------------------------------------------


def read_input(inputs_dir: Path, name: str) -> tuple[bytes, str]:
    """Read one pinned input, or raise ``BuildError``.

    Absent file, unreadable file, invalid UTF-8, a byte-order mark and a CRLF
    line ending all become named ``BuildError``s, so ``verify`` reports them as
    failure lines rather than letting an exception escape.
    """
    path = inputs_dir / name
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise BuildError(f"{name}: cannot be read: {exc}") from exc
    if raw.startswith(codecs.BOM_UTF8):
        raise BuildError(
            f"{name}: starts with a UTF-8 byte-order mark; the pinned inputs are "
            "BOM-free and a BOM would shift every offset by three bytes"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BuildError(f"{name}: is not valid UTF-8: {exc}") from exc
    if "\r" in text:
        raise BuildError(
            f"{name}: contains a carriage return; the pinned inputs are LF-only "
            "and every offset in this compiler assumes it"
        )
    return raw, text


def scalar_problem(value: object) -> str | None:
    """Why ``value`` cannot be a catalogue scalar, or ``None`` if it can.

    Catalogue scalars are exactly the strings reconstructed back into a Markdown
    block. A line break inside one would let a two-line JSON value pose as a
    single source line, and an empty one would let a truncated block match a
    prefix of the authoritative text.
    """
    if not isinstance(value, str):
        return f"is {type(value).__name__}, expected a string"
    if value == "":
        return "is empty"
    if "\n" in value or "\r" in value:
        return "contains a line break"
    return None


def canonical_json(obj: object) -> str:
    """UTF-8, sorted keys, two-space indent, trailing newline.

    ``ensure_ascii=False`` so the source's curly quotes and em dashes survive
    verbatim -- the verifier compares them against the markdown byte for byte.
    """
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------


def parse_framework(text: str) -> list[dict]:
    """Single forward pass. No regex, no state machine.

    Only two line forms are ever inspected: the five pillar H2s and lines
    beginning ``### PF-``. Neither occurs inside the document's code fence or
    its change-summary table, so no fence or table handling is needed.
    """
    lines = text.split("\n")
    pillar_by_label = {p.display_label: p for p in PILLAR_TABLE}
    current: Pillar | None = None
    checks: list[dict] = []

    for i, line in enumerate(lines):
        lineno = i + 1

        if line.startswith("## ") and line.endswith(" checks") and " — " in line:
            label, _, tail = line[3:].partition(" — ")
            pillar = pillar_by_label.get(label)
            if pillar is None:
                raise BuildError(f"line {lineno}: unknown pillar heading: {line!r}")
            declared = tail.removesuffix(" checks")
            if declared != str(pillar.check_count):
                raise BuildError(
                    f"line {lineno}: {label} declares {declared} checks, "
                    f"table says {pillar.check_count}"
                )
            current = pillar
            continue

        if not line.startswith("### PF-"):
            continue

        if current is None:
            raise BuildError(f"line {lineno}: check heading before any pillar heading")

        check_id, sep, question = line[len("### ") :].partition(" — ")
        if not sep:
            raise BuildError(f"line {lineno}: check heading has no ' — ': {line!r}")
        if not check_id.startswith(current.id_prefix + "-"):
            raise BuildError(
                f"line {lineno}: {check_id} is not in the current pillar "
                f"{current.pillar_id} ({current.id_prefix}-*)"
            )
        problem = scalar_problem(question)
        if problem is not None:
            raise BuildError(f"line {lineno}: {check_id} question {problem}")
        if not question.endswith("?"):
            raise BuildError(f"line {lineno}: {check_id} question does not end with '?'")
        if i + 1 >= len(lines) or lines[i + 1] != "":
            raise BuildError(f"line {lineno + 1}: {check_id} heading is not followed by a blank line")

        values: dict[str, str] = {}
        for offset, (label, key) in enumerate(FIELD_LABELS):
            at = i + 2 + offset
            prefix = f"- **{label}:** "
            field_line = lines[at] if at < len(lines) else ""
            if not field_line.startswith(prefix):
                raise BuildError(
                    f"line {at + 1}: {check_id} expected {prefix!r}, got {field_line[:80]!r}"
                )
            value = field_line[len(prefix) :]
            problem = scalar_problem(value)
            if problem is not None:
                raise BuildError(f"line {at + 1}: {check_id} {label} value {problem}")
            values[key] = value

        # Guards against a seventh label being silently dropped.
        after = i + 2 + len(FIELD_LABELS)
        if after < len(lines) and lines[after] != "":
            raise BuildError(
                f"line {after + 1}: {check_id} block is not terminated by a blank line: "
                f"{lines[after][:80]!r}"
            )

        materiality = values.pop(MATERIALITY_KEY)
        if not materiality.endswith("."):
            raise BuildError(f"{check_id}: materiality {materiality!r} has no trailing period")
        materiality = materiality[:-1]
        if materiality not in MATERIALITY_VALUES:
            raise BuildError(f"{check_id}: materiality {materiality!r} is not a known value")

        checks.append(
            {
                "check_id": check_id,
                "pillar_id": str(current.pillar_id),
                "question": question,
                "materiality": materiality,
                "fields": values,
            }
        )

    return checks


def build_catalogue(inputs_dir: Path = INPUTS_DIR) -> dict:
    pins = {}
    texts = {}
    for key, name in INPUT_FILES.items():
        raw, texts[key] = read_input(inputs_dir, name)
        pins[key] = {
            "path": f"inputs/{name}",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        }

    checks = parse_framework(texts["framework_md"])
    distribution = Counter(c["materiality"] for c in checks)

    return {
        "schema_version": SCHEMA_VERSION,
        "framework_version": FRAMEWORK_VERSION,
        "framework_status": FRAMEWORK_STATUS,
        "inputs": pins,
        "materiality_vocabulary": list(MATERIALITY_VALUES),
        "materiality_distribution": {m: distribution.get(m, 0) for m in MATERIALITY_VALUES},
        "pillars": [pillar_record(p) for p in PILLAR_TABLE],
        "checks": checks,
        "gap_contract": {
            "fields": list(GAP_FIELD_KEYS),
            "display_labels": {str(k): v for k, v in GAP_DISPLAY_LABELS.items()},
        },
        "gap_rules": [
            {
                "applicability": str(applicability),
                "coverage": None if coverage is None else str(coverage),
                "gap_required": gap_required,
            }
            for applicability, coverage, gap_required in GAP_RULES
        ],
    }


# --------------------------------------------------------------------------
# verify
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Failure:
    code: str
    message: str
    detail: tuple[str, ...] = field(default=())

    def render(self) -> str:
        head = f"plinth: [{self.code}] {self.message}"
        return "\n".join([head, *(" " * 8 + d for d in self.detail)])


def reconstruct_block(check: dict) -> str:
    """Rebuild a check's markdown block exactly as it appears in the source.

    ``materiality`` is the one transform build and verify must agree on: build
    strips the trailing period, this puts it back. If the source ever drops the
    period, containment fails loudly, which is the wanted behaviour.
    """
    out = [f"### {check['check_id']} — {check['question']}", ""]
    for label, key in FIELD_LABELS:
        value = f"{check['materiality']}." if key == MATERIALITY_KEY else check["fields"][key]
        out.append(f"- **{label}:** {value}")
    return "\n".join(out)


def anchored_block(check: dict) -> str:
    """The reconstructed block plus the newlines that bound it in the source.

    Without the terminating newline, a shortened or emptied final field value
    matches a *prefix* of the authoritative line and V6 passes on truncated
    content. The leading newline closes the same hole at the other end, so the
    match has to begin and end on real line boundaries.
    """
    return f"\n{reconstruct_block(check)}\n"


def _check_label(check: dict, index: int) -> str:
    """Name a check by its ID when that ID is usable, by position otherwise."""
    check_id = check.get("check_id")
    return check_id if isinstance(check_id, str) and check_id else f"checks[{index}]"


def _diagnose_block(block: str, lines: list[str], check_id: str) -> tuple[str, ...]:
    """Name the first line on which the JSON and the source diverge."""
    anchor = f"### {check_id} "
    idx = next((i for i, line in enumerate(lines) if line.startswith(anchor)), None)
    if idx is None:
        return (f"no `{anchor.strip()} …` heading exists in the source",)
    for k, expected in enumerate(block.split("\n")):
        actual = lines[idx + k] if idx + k < len(lines) else "<end of file>"
        if actual != expected:
            return (
                f"{k} leading lines matched; line {k + 1} diverges",
                f"json: {expected}",
                f"file: {actual}",
            )
    return ("every line matches, but the block is not bounded by real line breaks",)


def verify(catalogue: dict, inputs_dir: Path = INPUTS_DIR) -> list[Failure]:
    """Every failure is accumulated and reported together."""
    failures: list[Failure] = []

    def fail(code: str, message: str, detail: tuple[str, ...] = ()) -> None:
        failures.append(Failure(code, message, detail))

    # V1 -- the artifact names the version it was compiled from, and both pinned
    # markdown files hash to the recorded sha256.
    for key, expected in (
        ("schema_version", SCHEMA_VERSION),
        ("framework_version", FRAMEWORK_VERSION),
        ("framework_status", FRAMEWORK_STATUS),
    ):
        if catalogue.get(key) != expected:
            fail("V1", f"{key} is {catalogue.get(key)!r}, expected {expected!r}")

    recorded = catalogue.get("inputs")
    if not isinstance(recorded, dict):
        fail("V1", f"inputs is {type(recorded).__name__}, expected an object")
        recorded = {}

    texts: dict[str, str] = {}
    for key, name in INPUT_FILES.items():
        pin = recorded.get(key)
        if not isinstance(pin, dict):
            fail("V1", f"inputs.{key} is {type(pin).__name__}, expected an object")
            pin = {}
        try:
            raw, text = read_input(inputs_dir, name)
        except (OSError, BuildError) as exc:
            fail("V1", f"{name}: cannot be read: {exc}")
            continue
        texts[key] = text
        expected_path = f"inputs/{name}"
        if pin.get("path") != expected_path:
            fail("V1", f"inputs.{key}.path is {pin.get('path')!r}, expected {expected_path!r}")
        digest = hashlib.sha256(raw).hexdigest()
        if digest != pin.get("sha256"):
            fail(
                "V1",
                f"{name}: sha256 does not match the recorded pin",
                (f"json: {pin.get('sha256')}", f"file: {digest}"),
            )
        if len(raw) != pin.get("bytes"):
            fail("V1", f"{name}: {len(raw)} bytes on disk, {pin.get('bytes')} recorded")

    # Structural floor. Every gate below indexes into these records, so a
    # hand-edit that deletes a key has to produce a named failure rather than a
    # traceback. Malformed records are reported and then excluded, which also
    # makes the count below disagree -- both facts are worth saying.
    raw_checks = catalogue.get("checks")
    if not isinstance(raw_checks, list):
        fail("V2", f"checks is {type(raw_checks).__name__}, expected a list")
        raw_checks = []
    checks: list[dict] = []
    for index, check in enumerate(raw_checks):
        if not isinstance(check, dict):
            fail("V2", f"checks[{index}] is {type(check).__name__}, expected an object")
            continue
        label = _check_label(check, index)
        missing = [k for k in CHECK_KEYS if k not in check]
        if missing:
            fail("V2", f"{label}: missing {', '.join(missing)}")
            continue

        # Scalars are typed here, before any regex, Counter, set membership or
        # reconstruction below touches them.
        problems = [
            f"{key} {problem}"
            for key in SCALAR_KEYS
            if (problem := scalar_problem(check[key])) is not None
        ]
        values = check["fields"]
        if not isinstance(values, dict) or set(values) != set(FIELD_KEYS):
            found = sorted(values) if isinstance(values, dict) else type(values).__name__
            problems.append(f"fields is {found}, expected {sorted(FIELD_KEYS)}")
        else:
            problems.extend(
                f"fields.{key} {problem}"
                for key in FIELD_KEYS
                if (problem := scalar_problem(values[key])) is not None
            )
        if problems:
            for problem in problems:
                fail("V2", f"{label}: {problem}")
            continue
        checks.append(check)

    # V2 -- exactly 63 checks, no duplicate IDs.
    if len(checks) != TOTAL_CHECKS:
        fail("V2", f"{len(checks)} checks in the catalogue, expected {TOTAL_CHECKS}")
    duplicates = sorted(cid for cid, n in Counter(c["check_id"] for c in checks).items() if n > 1)
    for check_id in duplicates:
        fail("V2", f"{check_id}: duplicate check ID")

    # V3 -- ID shape, and contiguous 001..N within each pillar.
    by_prefix: dict[str, list[int]] = {}
    for check in checks:
        check_id = check["check_id"]
        match = CHECK_ID_RE.match(check_id)
        if match is None:
            fail("V3", f"{check_id}: does not match {CHECK_ID_RE.pattern}")
            continue
        by_prefix.setdefault(f"PF-{match.group(1)}", []).append(int(match.group(2)))
    for pillar in PILLAR_TABLE:
        numbers = sorted(by_prefix.get(pillar.id_prefix, []))
        expected = list(range(1, len(numbers) + 1))
        if numbers != expected:
            fail(
                "V3",
                f"{pillar.id_prefix}: numbering is not contiguous 001..{len(numbers):03d}",
                (f"found: {', '.join(f'{n:03d}' for n in numbers)}",),
            )

    # V4 -- per-pillar counts, and each check's pillar_id agrees with its prefix.
    prefix_to_pillar = {p.id_prefix: str(p.pillar_id) for p in PILLAR_TABLE}
    for check in checks:
        match = CHECK_ID_RE.match(check["check_id"])
        if match is None:
            continue
        expected_pillar = prefix_to_pillar[f"PF-{match.group(1)}"]
        if check.get("pillar_id") != expected_pillar:
            fail(
                "V4",
                f"{check['check_id']}: pillar_id is {check.get('pillar_id')!r}, "
                f"its ID prefix says {expected_pillar!r}",
            )
    counted = Counter(c.get("pillar_id") for c in checks)
    for pillar in PILLAR_TABLE:
        actual = counted.get(str(pillar.pillar_id), 0)
        if actual != pillar.check_count:
            fail(
                "V4",
                f"{pillar.pillar_id}: {actual} checks, expected {pillar.check_count}",
            )
    if catalogue.get("pillars") != [pillar_record(p) for p in PILLAR_TABLE]:
        fail("V4", "the pillars block does not match the compiler's pillar table")

    # V5 -- vocabulary membership and the current distribution, reported apart.
    # The absence of LOW in v0.2 is a property of this catalogue, not of the
    # vocabulary: encoding it as an invalid enum value would reject a valid
    # future framework edit.
    vocabulary = list(MATERIALITY_VALUES)
    if catalogue.get("materiality_vocabulary") != vocabulary:
        fail(
            "V5",
            f"materiality_vocabulary is {catalogue.get('materiality_vocabulary')!r}, "
            f"expected {vocabulary!r}",
        )
    for check in checks:
        if check.get("materiality") not in vocabulary:
            fail(
                "V5",
                f"{check['check_id']}: materiality {check.get('materiality')!r} "
                f"is not in the materiality vocabulary",
            )
    observed = {m: 0 for m in vocabulary}
    for check in checks:
        materiality = check.get("materiality")
        if materiality in observed:
            observed[materiality] += 1
    if observed != EXPECTED_MATERIALITY_DISTRIBUTION:
        fail(
            "V5",
            "materiality distribution mismatch",
            (f"checks:   {observed}", f"expected: {EXPECTED_MATERIALITY_DISTRIBUTION}"),
        )
    if catalogue.get("materiality_distribution") != observed:
        fail(
            "V5",
            "the recorded materiality_distribution disagrees with the checks",
            (
                f"json:   {catalogue.get('materiality_distribution')}",
                f"checks: {observed}",
            ),
        )

    framework_text = texts.get("framework_md")
    framework_lines = framework_text.split("\n") if framework_text is not None else []

    # V6 -- the gate that makes V2..V5 more than shape checks. One containment
    # check per check binds the ID to its question, each label to its value, and
    # the six fields to their order, all at once. A per-field check would pass on
    # two questions swapped between checks, because both strings still exist
    # somewhere in the document.
    if framework_text is not None:
        for check in checks:
            block = reconstruct_block(check)
            if anchored_block(check) not in framework_text:
                fail(
                    "V6",
                    f"{check['check_id']}: reconstructed block not found in inputs/{FRAMEWORK_MD}",
                    _diagnose_block(block, framework_lines, check["check_id"]),
                )

    # V7 -- pin the display labels and declared counts to the document itself.
    if framework_text is not None:
        pillars = catalogue.get("pillars")
        for pillar in pillars if isinstance(pillars, list) else []:
            if not isinstance(pillar, dict):
                fail("V7", f"a pillars entry is {type(pillar).__name__}, expected an object")
                continue
            heading = f"## {pillar.get('display_label')} — {pillar.get('check_count')} checks"
            if heading not in framework_lines:
                fail("V7", f"pillar heading not found in inputs/{FRAMEWORK_MD}: {heading!r}")

    # V8 -- every display label is a real heading in the Output Contract.
    contract_text = texts.get("output_contract_md")
    if contract_text is not None:
        contract_lines = contract_text.split("\n")
        expected_keys = list(GAP_FIELD_KEYS)
        gap_contract = catalogue.get("gap_contract")
        if not isinstance(gap_contract, dict):
            fail("V8", f"gap_contract is {type(gap_contract).__name__}, expected an object")
            gap_contract = {}
        labels = gap_contract.get("display_labels")
        if not isinstance(labels, dict):
            fail("V8", f"gap_contract.display_labels is {type(labels).__name__}, expected an object")
            labels = {}
        if gap_contract.get("fields") != expected_keys:
            fail("V8", f"gap_contract.fields is not {expected_keys!r}")

        # The recorded mapping must equal the canonical one entry for entry, so
        # a missing, changed, swapped or extra label is caught. Swapping two
        # labels is the case a per-entry "is this string a heading somewhere"
        # test passes, because both strings are still headings.
        canonical_labels = {str(k): v for k, v in GAP_DISPLAY_LABELS.items()}
        for key in sorted(set(canonical_labels) | set(labels)):
            expected_label = canonical_labels.get(key)
            actual_label = labels.get(key)
            if actual_label == expected_label:
                continue
            if expected_label is None:
                fail(
                    "V8",
                    f"gap_contract.display_labels has an unexpected entry "
                    f"{key!r}: {actual_label!r}",
                )
            elif key not in labels:
                fail("V8", f"gap_contract.display_labels has no entry for {key!r}")
            else:
                fail(
                    "V8",
                    f"{key}: display label is {actual_label!r}, expected {expected_label!r}",
                )

        # And the canonical labels must still be headings in the source, which is
        # what would catch the Output Contract being reworded underneath us.
        for key, label in canonical_labels.items():
            if f"### {label}" not in contract_lines:
                fail(
                    "V8",
                    f"{key}: display label {label!r} is not a heading in "
                    f"inputs/{OUTPUT_CONTRACT_MD}",
                )

    # V9 -- exhaustive over the legal (applicability, coverage) space, each pair
    # exactly once. Any pair absent from the catalogue's rules is illegal by
    # construction, so C4 reads coverage legality and gap requirement from one
    # source instead of two overlapping predicate sets.
    expected_rules = {
        (str(applicability), None if coverage is None else str(coverage)): gap_required
        for applicability, coverage, gap_required in GAP_RULES
    }
    legal = set(expected_rules)
    seen: Counter[tuple[str, str | None]] = Counter()
    raw_rules = catalogue.get("gap_rules")
    if not isinstance(raw_rules, list):
        fail("V9", f"gap_rules is {type(raw_rules).__name__}, expected a list")
        raw_rules = []
    for index, rule in enumerate(raw_rules):
        if not isinstance(rule, dict):
            fail("V9", f"gap_rules[{index}] is {type(rule).__name__}, expected an object")
            continue
        applicability = rule.get("applicability")
        coverage = rule.get("coverage")
        gap_required = rule.get("gap_required")
        if not isinstance(applicability, str):
            fail(
                "V9",
                f"gap_rules[{index}].applicability is {type(applicability).__name__}, "
                "expected a string",
            )
            continue
        if coverage is not None and not isinstance(coverage, str):
            fail(
                "V9",
                f"gap_rules[{index}].coverage is {type(coverage).__name__}, "
                "expected a string or null",
            )
            continue
        pair = (applicability, coverage)
        seen[pair] += 1
        if pair not in legal:
            fail("V9", f"gap_rules contains an illegal pair: {applicability} / {coverage}")
            continue
        # A legal pair with the wrong requirement is the quiet failure: the shape
        # is right and every count matches, but C4 would demand or omit a gap
        # the framework does not.
        if not isinstance(gap_required, bool):
            fail(
                "V9",
                f"gap_rules {applicability} / {coverage}: gap_required is "
                f"{gap_required!r}, expected a boolean",
            )
        elif gap_required != expected_rules[pair]:
            fail(
                "V9",
                f"gap_rules {applicability} / {coverage}: gap_required is "
                f"{gap_required}, expected {expected_rules[pair]}",
            )
    for pair in sorted(legal, key=lambda p: (p[0], p[1] or "")):
        if seen[pair] == 0:
            fail("V9", f"gap_rules is missing the legal pair: {pair[0]} / {pair[1]}")
        elif seen[pair] > 1:
            fail("V9", f"gap_rules repeats the pair {pair[0]} / {pair[1]} {seen[pair]} times")

    return failures
