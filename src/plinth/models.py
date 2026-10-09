"""Typed shapes for the two canonical artifacts, and the rules inside them.

``documentary-evidence.json`` becomes an :class:`EvidencePack`;
``assessment.json`` becomes an :class:`Assessment`. Every later stage is a model
emitting JSON that this module accepts or rejects.

What passing here proves, and what it does not:

    proves       the evidence graph is internally coherent
                 the assessment states are structurally legal
                 the assessment references the exact evidence pack

    claims not   that an extracted fact is true
                 that a source is authoritative for its proposition
                 that the evidence is sufficient
                 that a human verified an observation
                 that a technical collector ran

Rules that involve one record live here as model validators, coded with the
identifiers used in the commit plan (``A1``, ``O2``, ``K8`` ...). Rules that span
collections live in :mod:`plinth.validate`.

**One rule per record is reported.** Pydantic runs after-validators in sequence
and stops at the first that raises, so a record breaking ``A1`` and ``A3`` at
once reports only ``A1``. Errors *do* accumulate across sibling records and
across separate fields, which is what the re-prompt loop needs; the per-record
limit is why the entry points promise all *discoverable* issues rather than all
issues.

**pydantic is a compiler convenience, never a semantic authority.** A third
party must be able to re-verify ``assessment.json`` with the standard library
alone, so no pydantic-only construct -- computed field, discriminated-union tag,
validator side effect -- may ever be load-bearing for what an artifact means.
Everything below is either a shape a stdlib verifier can restate or a rule
written out in plain terms in its docstring.
"""

from __future__ import annotations

import hashlib
import re
import string
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StringConstraints,
    model_validator,
)
from pydantic_core import PydanticCustomError

from .catalogue import CHECK_ID_RE, GAP_RULES, canonical_json
from .vocab import (
    AcquisitionMode,
    AcquisitionOutcome,
    Applicability,
    Coverage,
    LocatorType,
    ResearchPosture,
    RouteStatus,
    SourceDisposition,
)

# --------------------------------------------------------------------------
# base configuration
# --------------------------------------------------------------------------


class PlinthModel(BaseModel):
    """Shared configuration for every model in the two artifacts.

    ``extra="forbid"`` is the point of the whole layer: an unknown key from an
    LLM yields ``extra_forbidden`` at the exact JSON path rather than being
    silently dropped, and a dropped key in an audit artifact is a fact that
    vanished between generation and storage.

    ``frozen=True`` is *shallow*. It blocks attribute assignment; it does not
    deep-freeze a nested container. Every collection field is therefore a
    ``tuple`` and :attr:`Observation.value` is a scalar, so that "frozen" is not
    a lie about a mutable payload sitting inside an immutable record.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        validate_default=True,
    )


# --------------------------------------------------------------------------
# field types
# --------------------------------------------------------------------------
#
# ``StrictBool``/``StrictInt`` are used rather than a global ``strict=True``.
# Lax mode turns "1" into 1 and "true" into True, which is exactly what LLM JSON
# does; global strict mode would additionally break ``str -> datetime`` and
# ``str -> enum``, both of which JSON input requires.

RECORD_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
"""The identifier shape, compiled once so non-pydantic code can reuse it.

:func:`plinth.archive.run_directory` joins a ``run_id`` onto a filesystem path
and must enforce this itself: a second copy of the pattern would be a second
thing to keep in step, and the copy that drifted would be the one guarding the
filesystem.
"""

RecordId = Annotated[
    str,
    StringConstraints(strict=True, pattern=RECORD_ID_RE.pattern),
]
"""An identifier a human writes and a machine joins on.

Deliberately permissive about case: ``src-ondo-docs``, ``OBS_CUSTODY_001`` and
``ousg-2026-09-06`` are all fine. An uppercase-only or slug-only rule would add
correction friction to every extraction without buying any integrity.

The leading-alphanumeric rule is what makes it path-safe: ``.``, ``..``, ``/``
and an absolute path are all unrepresentable.
"""

CheckId = Annotated[str, StringConstraints(strict=True, pattern=CHECK_ID_RE.pattern)]
"""C1's catalogue check identifier, matched against C1's own pattern.

This proves *shape*, not *existence*. That ``PF-BACKING-099`` is not in the
63-check catalogue is C5's ingestion check, not this one.
"""

Sha256 = Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]

NonEmpty = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)]

ExactText = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=False, min_length=1)
]
"""A string whose exact characters are the payload, surrounding whitespace included.

``PlinthModel`` sets ``str_strip_whitespace=True``, which is right for domain
prose and wrong wherever the characters themselves are load-bearing. Only two
fields qualify, and both break silently under stripping: an RFC 6901 pointer to
a key with trailing whitespace stops resolving, and a quoted span that C3 will
match against archived bytes stops matching.

``min_length=1`` is written out rather than inherited from :data:`NonEmpty`,
because the intent here is to *replace* the whitespace policy while keeping the
emptiness rule, and stating both leaves no doubt about which survives.
"""

PositiveCount = Annotated[StrictInt, Field(gt=0)]


def _to_utc(moment: datetime) -> datetime:
    """Normalize an aware datetime to UTC so comparisons and hashes agree.

    ``astimezone`` raises ``OverflowError`` at the very edges of the datetime
    range -- ``datetime.max`` at a negative UTC offset has no UTC
    representation. That is bad input, not a bug, so it becomes a field-located
    error rather than an exception escaping an entry point documented to return
    :class:`Issue`s.
    """
    try:
        return moment.astimezone(UTC)
    except OverflowError:
        raise PydanticCustomError(
            "datetime_range",
            "cannot be normalized to UTC without leaving the representable "
            "datetime range",
        ) from None


_ISO_DATE_PREFIX = re.compile(r"\d{4}-\d{2}-\d{2}")
_FRACTION_BEYOND_MICROSECONDS = re.compile(r"[.,]\d{7,}")


def _require_iso_text(value: object) -> object:
    """Accept an instant only as ISO-8601 text (or an in-process ``datetime``).

    pydantic's lax datetime parsing also accepts an epoch number -- seconds, or
    milliseconds past ``2e10`` -- a float, or a digit-only string, and assumes
    UTC for all of them. That is an unlabelled time handed a basis it never
    stated, and a float epoch reintroduces the collapse :func:`_require_scalar`
    refuses: two different submitted values, one digest.

    Fractional seconds beyond six digits are rejected rather than truncated for
    the same reason: ``.1234567`` and ``.1234568`` would otherwise hash alike.
    """
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not _ISO_DATE_PREFIX.match(value):
        raise PydanticCustomError(
            "datetime_type",
            "must be an ISO-8601 string beginning with a YYYY-MM-DD date and carrying "
            "an explicit offset; got {kind}",
            {"kind": type(value).__name__},
        )
    if _FRACTION_BEYOND_MICROSECONDS.search(value):
        raise PydanticCustomError(
            "datetime_precision",
            "carries more than six fractional-second digits, which cannot round-trip "
            "through the canonical form",
        )
    return value


UtcMoment = Annotated[
    AwareDatetime, BeforeValidator(_require_iso_text), AfterValidator(_to_utc)
]
"""A timezone-aware instant, normalized to UTC.

Naive input is rejected rather than assumed local: framework section 2.9 makes
the time basis part of the proposition, and an unlabelled wall-clock time has no
basis. See :func:`_require_iso_text` for why numbers are refused too.
"""


def _require_scalar(value: object) -> object:
    """Reject anything that is not a JSON scalar this compiler can round-trip.

    A field typed as a union of scalars would report an error per union member
    for one bad value, each at a synthetic path like
    ``/observations/0/value/int``. Those paths do not exist in the submitted
    document, and the pointer is the whole point of this layer, so the check is
    written out instead.

    **Floats are rejected outright, not repaired.** For an artifact whose entire
    value is that a digest binds it to exact content, a type that silently
    collapses two distinct submitted values into one is the wrong type:

    - ``42000000.250000000000001`` and ``42000000.25`` parse to the same float
      and therefore produce *identical* canonical bytes, so X4 cannot tell two
      different quantities apart;
    - ``1e-400`` underflows to ``0.0`` during parsing, turning a very small
      quantity into none at all;
    - ``1e400``, ``Infinity`` and ``NaN`` all serialize to ``null``, losing the
      value and colliding with each other.

    No precision limit can recover digits already lost in ``json.loads``, so the
    only honest answer is to refuse the type and ask for a string. Exact
    decimals travel verbatim as quoted strings alongside ``unit``, which needs
    no decimal parser, no format grammar and no custom serializer.

    ``bool`` is tested before ``int`` because ``isinstance(True, int)`` is true.
    """
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        # A lone surrogate survives json.loads (from a "\\ud800" escape) but
        # cannot be encoded, so it would pass validation and then make
        # canonical_bytes raise UnicodeEncodeError -- turning a bad document
        # into an exception on a path documented to return Issues instead.
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            raise PydanticCustomError(
                "scalar_value",
                "contains an unpaired surrogate, so it cannot be encoded as UTF-8",
            ) from None
        return value
    if isinstance(value, float):
        raise PydanticCustomError(
            "scalar_value",
            "is a float; a float cannot round-trip to an exact digest, so emit "
            'the decimal as a string, e.g. "42000000.25"',
        )
    if isinstance(value, int):
        return value
    raise PydanticCustomError(
        "scalar_value",
        "must be a string, integer, boolean or null; got {kind}",
        {"kind": type(value).__name__},
    )


ScalarValue = Annotated[Any, BeforeValidator(_require_scalar)]
"""An exactly-representable JSON scalar: ``str | int | bool | None``.

No floats. An exact decimal is a quoted string preserved verbatim
(``"42000000.00"``), interpreted at a calculation boundary where the unit is
known anyway -- see :func:`_require_scalar` for why repairing floats is not an
option.

See :class:`PlinthModel` on shallow freezing: a ``dict`` here would remain
mutable inside a record the type system calls immutable.
"""


# --------------------------------------------------------------------------
# issues
# --------------------------------------------------------------------------


class Issue(PlinthModel):
    """One reason an artifact is not valid, addressed to the thing that emitted it.

    ``pointer`` is an RFC 6901 JSON pointer into the submitted document, e.g.
    ``/observations/2/supports/0/locator_id``. That pointer is what lets C4-C6
    re-prompt a model with the exact location of its mistake.

    There is no ``input_repr``: the pointer locates the problem, and echoing the
    offending value back into a diagnostic adds a second place for it to leak.

    ``pointer`` is :data:`ExactText`-typed rather than a plain ``str`` so the
    base config's whitespace stripping cannot touch it. A document key of
    ``"balance "`` produces the pointer ``/balance%20``-equivalent token
    ``/balance `` -- stripped, it names a key that does not exist, which defeats
    the only thing the pointer is for. The empty pointer means the whole
    document, so it is allowed here and excluded from the ``min_length`` rule by
    the union.
    """

    pointer: ExactText | Literal[""]
    code: str
    message: str

    def render(self) -> str:
        where = self.pointer or "<document>"
        return f"plinth: [{self.code}] {where}: {self.message}"


# --------------------------------------------------------------------------
# canonical serialization
# --------------------------------------------------------------------------


def canonical_bytes(model: BaseModel) -> bytes:
    """The canonical on-disk form of a model, as bytes.

    Bytes rather than ``str`` because ``hashlib`` consumes bytes; returning text
    invites an implicit default encoding somewhere downstream, and the digest of
    a mis-encoded artifact is a wrong answer that looks like a right one.

    **What the digest binds: the normalized model, not the submitted document.**
    Saying otherwise would be an overclaim, and the difference is the whole
    contract a third party re-verifies against. Two byte-different submissions
    hash identically whenever they differ only in something this list erases:

    1. leading and trailing whitespace on every declared ``str`` field except
       :data:`ExactText` ones (``str_strip_whitespace=True``); the ``Any``-typed
       :attr:`Observation.value` is not a declared ``str`` and is kept verbatim;
    2. timezone offset -- every instant is converted to UTC, so
       ``2026-08-31T20:00:00-04:00`` and ``2026-09-01T00:00:00Z`` are one value;
    3. datetime spelling -- rendered ISO-8601 in UTC with a trailing ``Z``
       (pydantic's form; stdlib ``isoformat()`` writes ``+00:00`` and a verifier
       must not copy that), fractional seconds omitted when zero and written as
       six digits otherwise;
    4. enum spelling -- rendered as the member's value;
    5. absent optional fields -- filled with their declared defaults, so a key
       omitted and the same key sent explicitly at its default are one document;
    6. key order, indentation and separators -- keys sorted, two-space indent,
       ``ensure_ascii=False``, one trailing newline;
    7. text encoding -- UTF-8.

    Everything not on that list is binding. ``X4`` hashes this form rather than
    the submitted bytes precisely so that reformatting does not break the pin
    while changing a proposition does.

    Two ways *information* used to be lost here are now rejected upstream rather
    than normalized away: floats (:func:`_require_scalar`) and duplicate JSON
    object keys (:func:`plinth.validate.parse_document`). Neither establishes
    literal input identity, and nothing here should -- the pin is over meaning.

    A later stdlib-only verifier must reproduce items 1-7 without pydantic: dump
    to plain JSON types, then :func:`plinth.catalogue.canonical_json`, then
    UTF-8.
    """
    return canonical_json(model.model_dump(mode="json")).encode("utf-8")


def canonical_sha256(model: BaseModel) -> str:
    """Hex SHA-256 of :func:`canonical_bytes`: the value ``X4`` pins an assessment to."""
    return hashlib.sha256(canonical_bytes(model)).hexdigest()


# --------------------------------------------------------------------------
# evidence models
# --------------------------------------------------------------------------


class Campaign(PlinthModel):
    """What this run set out to do, declared before it did it.

    Framework section 2.5: the framework defines what should be known; a
    campaign declares which evidence-access paths it will attempt. Section 2.2:
    the subject is the complete relevant product system, which is why the
    description is required rather than inferred from a token symbol.
    """

    run_id: RecordId
    subject: NonEmpty
    subject_description: NonEmpty
    cutoff: UtcMoment
    declared_acquisition_modes: Annotated[
        tuple[AcquisitionMode, ...], Field(min_length=1)
    ]
    declared_scope_note: NonEmpty
    bounded_public_evidence: StrictBool


class Source(PlinthModel):
    """A document or record the campaign considered, and who stands behind it.

    The provenance fields are framework section 2.7's list verbatim. They are
    optional because section 2.7 records them "where applicable": a regulatory
    filing has no research posture among the five members, and a commissioned
    report may have a genuinely unestablished funder. Forcing a value makes the
    extractor misclassify a record in order to satisfy a schema, which is worse
    than a null.
    """

    source_id: RecordId
    title: NonEmpty
    source_type: NonEmpty
    url: NonEmpty | None = None
    author: NonEmpty | None = None
    publisher: NonEmpty | None = None
    commissioner_or_funder: NonEmpty | None = None
    relationship_to_subject: NonEmpty | None = None
    research_posture: ResearchPosture | None = None
    publication_date: UtcMoment | None = None
    stated_methodology_scope: NonEmpty | None = None
    stated_limitations: tuple[NonEmpty, ...] = ()
    disposition: SourceDisposition = SourceDisposition.IN_SCOPE
    excluded_reason: NonEmpty | None = None
    superseded_by_source_id: RecordId | None = None
    notes: NonEmpty | None = None

    @model_validator(mode="after")
    def _s1_excluded_states_its_reason(self) -> Source:
        """S1 -- section 2.2: intentional exclusions state their evidentiary reason."""
        if self.disposition is SourceDisposition.EXCLUDED and self.excluded_reason is None:
            raise PydanticCustomError(
                "S1",
                "disposition is EXCLUDED, so excluded_reason must state the evidentiary "
                "reason for the exclusion",
            )
        return self

    @model_validator(mode="after")
    def _s2_superseded_names_its_successor(self) -> Source:
        """S2 -- a supersession with no named successor is an unfalsifiable claim."""
        if self.disposition is SourceDisposition.SUPERSEDED:
            if self.superseded_by_source_id is None:
                raise PydanticCustomError(
                    "S2",
                    "disposition is SUPERSEDED, so superseded_by_source_id must name "
                    "the superseding source",
                )
            if self.superseded_by_source_id == self.source_id:
                raise PydanticCustomError(
                    "S2", "a source cannot supersede itself"
                )
        return self


class Acquisition(PlinthModel):
    """One attempt to obtain one artifact from one source.

    The record is of the fetch and only the fetch. An acquisition that
    downloaded a document since superseded was ``ACQUIRED``; rewriting the
    outcome later would destroy the record of what actually happened, which is
    the thing framework section 2.6 gate 1 asks for.
    """

    acquisition_id: RecordId
    source_id: RecordId
    acquisition_mode: AcquisitionMode
    outcome: AcquisitionOutcome
    attempted_at: UtcMoment
    retrieved_at: UtcMoment | None = None
    artifact_sha256: Sha256 | None = None
    request_detail: NonEmpty | None = None
    operator: NonEmpty | None = None
    failure_reason: NonEmpty | None = None

    @model_validator(mode="after")
    def _a1_acquired_iff_artifact_and_time(self) -> Acquisition:
        """A1 -- ``ACQUIRED`` if and only if there are bytes and a retrieval time.

        Both directions matter. ``ACQUIRED`` with no digest is a success with
        nothing to show for it; a digest on a failed attempt is bytes with no
        account of where they came from.
        """
        acquired = self.outcome is AcquisitionOutcome.ACQUIRED
        complete = self.artifact_sha256 is not None and self.retrieved_at is not None
        if acquired and not complete:
            raise PydanticCustomError(
                "A1",
                "outcome is ACQUIRED, so artifact_sha256 and retrieved_at are both required",
            )
        if not acquired and (self.artifact_sha256 is not None or self.retrieved_at is not None):
            raise PydanticCustomError(
                "A1",
                "outcome is {outcome}, so artifact_sha256 and retrieved_at must both be null",
                {"outcome": str(self.outcome)},
            )
        return self

    @model_validator(mode="after")
    def _a2_retrieval_follows_attempt(self) -> Acquisition:
        """A2 -- section 2.9: retrieval cannot precede the attempt that caused it."""
        if self.retrieved_at is not None and self.retrieved_at < self.attempted_at:
            raise PydanticCustomError(
                "A2", "retrieved_at is earlier than attempted_at"
            )
        return self

    @model_validator(mode="after")
    def _a3_failure_states_why(self) -> Acquisition:
        """A3 -- section 2.5: a failed path cannot silently produce ``MISSING``.

        The reason is what an allocator reads to understand the boundary of the
        campaign, so an unexplained failure is not recordable.
        """
        if self.outcome is not AcquisitionOutcome.ACQUIRED and self.failure_reason is None:
            raise PydanticCustomError(
                "A3",
                "outcome is {outcome}, so failure_reason must say what prevented acquisition",
                {"outcome": str(self.outcome)},
            )
        return self

    @model_validator(mode="after")
    def _a4_manual_upload_names_its_operator(self) -> Acquisition:
        """A4 -- a hand-placed artifact has a human in its provenance chain."""
        if self.acquisition_mode is AcquisitionMode.MANUAL_UPLOAD and self.operator is None:
            raise PydanticCustomError(
                "A4",
                "acquisition_mode is MANUAL_UPLOAD, so operator must name who supplied "
                "the artifact",
            )
        return self


ARTIFACT_FILENAME_RE = re.compile(r"^[0-9a-f]{64}(\.[a-z0-9]{1,8})?$")
"""``<sha256>`` with an optional short lowercase extension, and nothing else.

The archive names every blob for its own digest, so the filename carries no
operator-chosen component at all. Constraining it here is what lets
:mod:`plinth.archive` rebuild the path as ``sha256 + extension`` instead of
joining a submitted string: a ``filename`` of ``../../etc/passwd`` is rejected
by the shape, and even an accepted one is never used to address the filesystem.
Path traversal is impossible by construction rather than by sanitizing.
"""


class Artifact(PlinthModel):
    """Archived bytes, addressed by digest.

    There is no ``acquisition_ids`` backlink. :class:`Acquisition` already names
    its artifact; a reverse list would be a second edge that nothing forces to
    agree with the first, and two edges that can disagree are worse than one.

    **This layer never opens the file.** An artifact whose digest is plausible
    but whose bytes do not exist validates here; that is
    :func:`plinth.archive.validate_pack_against_run`'s ``D1``-``D4``, which need
    a run directory and so cannot be model validators -- a validator that opened
    files would make ``model_validate`` machine-dependent, and then
    :func:`canonical_bytes` would hash a model whose validity is not a property
    of the document.
    """

    sha256: Sha256
    media_type: NonEmpty
    byte_length: PositiveCount
    filename: NonEmpty
    original_filename: NonEmpty | None = None
    page_count: PositiveCount | None = None
    text_extraction_tool: NonEmpty | None = None
    text_sha256: Sha256 | None = None
    archived_at: UtcMoment

    @model_validator(mode="after")
    def _ar1_extracted_text_names_its_tool(self) -> Artifact:
        """AR1 -- extracted text without a named tool is unreproducible.

        Both directions: a digest with no tool cannot be recomputed, and a tool
        with no digest records a step that produced nothing checkable.
        """
        if (self.text_sha256 is None) != (self.text_extraction_tool is None):
            raise PydanticCustomError(
                "AR1",
                "text_sha256 and text_extraction_tool must both be present or both be null",
            )
        return self

    @model_validator(mode="after")
    def _ar2_filename_is_its_own_digest(self) -> Artifact:
        """AR2 -- the filename is the digest, so it can carry no other instruction.

        Checked here rather than in the archive layer because it is a property
        of one record and needs no filesystem: the pure layer can say that
        ``ousg.pdf`` and ``../../etc/passwd`` are both malformed without knowing
        whether any blob exists.
        """
        if not ARTIFACT_FILENAME_RE.match(self.filename):
            raise PydanticCustomError(
                "AR2",
                "filename must be the 64-character sha256 with an optional short "
                "lowercase extension, e.g. {expected}",
                {"expected": f"{self.sha256}.pdf"},
            )
        if self.filename[:64] != self.sha256:
            raise PydanticCustomError(
                "AR2",
                "filename names digest {named}, but sha256 is {actual}",
                {"named": self.filename[:64], "actual": self.sha256},
            )
        return self


# The field each locator type must carry. There is deliberately no forbidden
# field list: a PDF section legitimately spans pages, and an HTML heading
# legitimately also has a selector.
LOCATOR_REQUIRED_FIELDS: dict[LocatorType, tuple[str, ...]] = {
    LocatorType.PDF_PAGE: ("page",),
    LocatorType.DOCUMENT_SECTION: ("section",),
    LocatorType.DOCUMENT_FIELD: ("field_path",),
    LocatorType.HTML_HEADING: ("heading",),
    LocatorType.HTML_SELECTOR: ("selector",),
    LocatorType.TEXT_SPAN: ("char_start", "char_end"),
}


class Locator(PlinthModel):
    """Where inside an artifact a fact was read.

    **This layer never resolves the position.** A locator may name page 900 of
    a 42-page PDF, or quote text appearing nowhere in the file, and still
    validate here; resolution against archived bytes is
    :func:`plinth.archive.validate_pack_against_run`'s ``D8``-``D11``.

    What stays unresolved even there: ``page`` is checked against an
    operator-typed ``page_count`` and never against the PDF itself, and
    ``section``, ``field_path``, ``heading`` and ``selector`` have no positional
    check at all -- only :attr:`quoted_text` ties them to the document.
    """

    locator_id: RecordId
    artifact_sha256: Sha256
    locator_type: LocatorType
    page: StrictInt | None = None
    section: NonEmpty | None = None
    field_path: NonEmpty | None = None
    selector: NonEmpty | None = None
    heading: NonEmpty | None = None
    char_start: StrictInt | None = None
    char_end: StrictInt | None = None
    # ExactText, not NonEmpty: C3 resolves a locator by matching this against the
    # archived bytes, so a stripped copy of a span with surrounding whitespace
    # simply will not be found -- a schema decision surfacing as a mysterious
    # locator miss two commits later.
    quoted_text: ExactText | None = None

    @model_validator(mode="after")
    def _l1_declared_type_carries_its_address(self) -> Locator:
        """L1 -- a ``pdf_page`` locator with no page addresses nothing."""
        missing = [
            name
            for name in LOCATOR_REQUIRED_FIELDS[self.locator_type]
            if getattr(self, name) is None
        ]
        if missing:
            raise PydanticCustomError(
                "L1",
                "locator_type is {kind}, which requires {missing}",
                {"kind": str(self.locator_type), "missing": ", ".join(missing)},
            )
        return self

    @model_validator(mode="after")
    def _l2_positions_are_in_range(self) -> Locator:
        """L2 -- page numbering starts at 1, offsets at 0, and a span is non-empty."""
        if self.page is not None and self.page < 1:
            raise PydanticCustomError(
                "L2", "page is {page}; page numbering starts at 1", {"page": self.page}
            )
        if self.char_start is not None and self.char_start < 0:
            raise PydanticCustomError(
                "L2",
                "char_start is {start}; character offsets start at 0",
                {"start": self.char_start},
            )
        if self.char_start is not None and self.char_end is not None:
            if self.char_end <= self.char_start:
                raise PydanticCustomError(
                    "L2", "char_end must be greater than char_start; the span is empty"
                )
        return self


class ObservationSupport(PlinthModel):
    """One evidentiary leg of a source-backed observation.

    Naming the *acquisition* rather than the source is the load-bearing choice.
    A support keyed on ``source_id`` plus a locator left two edges nothing forced
    to agree: an artifact could list an acquisition that never acquired it, so a
    locator appeared to trace through the right source while the acquisition
    behind it fetched something else. The source is now derived through the
    acquisition -- one edge, one direction, checked by ``P3`` and ``P4``.
    """

    acquisition_id: RecordId
    locator_id: RecordId


class Observation(PlinthModel):
    """A bounded factual proposition (framework section 2.8).

    Not owned by a check. Section 2.8 makes observations reusable building
    blocks, and section 2.1 requires applicability to rest on facts established
    independently of the check being gated; in the OUSG corpus a single custody
    observation is cited by eleven checks. Which checks cite it lives on
    :class:`CheckAssessment`.

    Section 2.9's five temporal fields are not substitutable for one another,
    and three of them are here: ``evidence_as_of`` (when the evidence speaks
    about), ``observation_time`` (when the fact was true) and the effective
    period. The other two belong to the source and the acquisition.

    There is no ``confidential`` flag. Plinth has no access control and no
    redaction system, and a security-shaped field that does nothing is worse
    than an absent one, because it invites reliance on protection that is not
    there.
    """

    observation_id: RecordId
    proposition: NonEmpty
    subject: NonEmpty
    value: ScalarValue = None
    unit: NonEmpty | None = None
    observation_time: UtcMoment | None = None
    effective_period_start: UtcMoment | None = None
    effective_period_end: UtcMoment | None = None
    evidence_as_of: UtcMoment | None = None
    supports: tuple[ObservationSupport, ...] = ()
    parent_observation_ids: tuple[RecordId, ...] = ()
    derivation_rule_id: NonEmpty | None = None
    derivation_rule_version: NonEmpty | None = None
    authority_limitations: tuple[NonEmpty, ...] = ()
    qualifications: tuple[NonEmpty, ...] = ()

    @model_validator(mode="after")
    def _o1_every_observation_traces_somewhere(self) -> Observation:
        """O1 -- section 2.8: source-backed traces to evidence, derived traces to parents.

        An observation with neither is an assertion with no provenance at all,
        which is the one thing the framework's evidence-before-conclusion
        commitment forbids outright.
        """
        if not self.supports and not self.parent_observation_ids:
            raise PydanticCustomError(
                "O1",
                "an observation must be source-backed (supports) or derived "
                "(parent_observation_ids); this one is neither",
            )
        return self

    @model_validator(mode="after")
    def _o2_derivation_is_a_versioned_rule(self) -> Observation:
        """O2 -- section 2.8: a derivation's "deterministic rule" must be "versioned".

        Both directions: parents with no named rule is an unexplained
        derivation, and a named rule with no parents is a derivation with no
        inputs.
        """
        derived = bool(self.parent_observation_ids)
        ruled = self.derivation_rule_id is not None and self.derivation_rule_version is not None
        if derived and not ruled:
            raise PydanticCustomError(
                "O2",
                "parent_observation_ids is non-empty, so derivation_rule_id and "
                "derivation_rule_version are both required",
            )
        if not derived and (
            self.derivation_rule_id is not None or self.derivation_rule_version is not None
        ):
            raise PydanticCustomError(
                "O2",
                "derivation_rule_id/derivation_rule_version are set but "
                "parent_observation_ids is empty, so there is nothing being derived from",
            )
        return self

    @model_validator(mode="after")
    def _o3_no_self_derivation(self) -> Observation:
        """O3 -- section 2.8: derivation provenance "must be acyclic".

        The one-node case, caught here so ``P5`` only has to reason about cycles
        spanning more than one record.
        """
        if self.observation_id in self.parent_observation_ids:
            raise PydanticCustomError("O3", "an observation cannot derive from itself")
        return self

    @model_validator(mode="after")
    def _o4_effective_period_is_ordered(self) -> Observation:
        """O4 -- section 2.9: an effective period that ends before it starts has no basis."""
        if self.effective_period_start is not None and self.effective_period_end is not None:
            if self.effective_period_end < self.effective_period_start:
                raise PydanticCustomError(
                    "O4", "effective_period_end is earlier than effective_period_start"
                )
        return self

    @model_validator(mode="after")
    def _o5_unit_requires_a_value(self) -> Observation:
        """O5 -- section 2.8: derived observations "preserve ... units".

        A unit with nothing to measure cannot be checked for compatibility, so
        it is a unit claim that no later aggregation rule can act on.
        """
        if self.unit is not None and self.value is None:
            raise PydanticCustomError("O5", "unit is set but value is null")
        return self


class Route(PlinthModel):
    """A declared evidence-access path and whether it was carried out.

    Framework section 2.5: the campaign declares the paths it will attempt, and
    ``MISSING`` is bounded to that declaration. ``required_for_check_ids`` is
    therefore the search boundary against which a check's completeness is
    judged.

    **Ownership of that mapping is operational, not modelled here.** Routes come
    from run configuration, not model output: the extraction packet must not ask
    the model for ``required_for_check_ids``, and C4's ingest must reject a pack
    that supplies them. Without that, the extractor defines the boundary used to
    judge its own completeness.

    **Still prose, and C3 did not change that.** ``status`` remains
    model-authored and nothing links a ``COMPLETED`` route to an archived
    acquisition, so a route that was never attempted still licenses a
    ``MISSING`` claim -- see ``X2``, and the test named
    ``test_an_unattempted_route_marked_completed_still_unlocks_missing``, which
    asserts the gap rather than pretending it is closed.

    Closing it needs three pieces together, recorded here so they are not
    re-derived:

    1. run configuration pins ``route_id``, ``description``,
       ``acquisition_mode`` and ``required_for_check_ids``, so the model cannot
       choose which searches grade a check;
    2. attested non-``ACQUIRED`` outcomes exist in the archive index, so a
       genuine "searched, found nothing" route has something to point at;
    3. a ``COMPLETED`` route must name an index-backed acquisition on one of its
       sources, so the model cannot claim a search it never ran.

    Piece 2 is what makes piece 3 survivable, and piece 1 alone only narrows the
    hole, because ``status`` would still be the model's. Any pin also needs an
    operator-controlled amendment path with the accepted pack naming the
    manifest revision it was checked against: discovery legitimately changes
    what a search must cover -- a subsidiary, a replacement filing repository,
    an audit referenced inside another document -- so "a discovered route never
    requires a check" is false. The adversary this defends against is the
    extraction model, which does not exist until C4; that is where these land,
    with one real campaign's routes to calibrate against.
    """

    route_id: RecordId
    description: NonEmpty
    acquisition_mode: AcquisitionMode
    status: RouteStatus
    required_for_check_ids: tuple[CheckId, ...] = ()
    source_ids: tuple[RecordId, ...] = ()
    limitation: NonEmpty | None = None

    @model_validator(mode="after")
    def _r1_incomplete_route_states_its_limitation(self) -> Route:
        """R1 -- section 2.5: the campaign discloses enough for an allocator to see the boundary."""
        if self.status is not RouteStatus.COMPLETED and self.limitation is None:
            raise PydanticCustomError(
                "R1",
                "status is {status}, so limitation must say what was not covered",
                {"status": str(self.status)},
            )
        return self


class EvidencePack(PlinthModel):
    """Everything one campaign obtained, plus the facts read out of it.

    Unresolved routes are not stored separately: ``status != COMPLETED`` *is* the
    definition, and it is derivable from this JSON alone by a verifier that has
    never seen this module.
    """

    schema_version: Literal["plinth.evidence/1"]
    campaign: Campaign
    sources: tuple[Source, ...] = ()
    acquisitions: tuple[Acquisition, ...] = ()
    artifacts: tuple[Artifact, ...] = ()
    locator_catalog: tuple[Locator, ...] = ()
    observations: tuple[Observation, ...] = ()
    routes: tuple[Route, ...] = ()
    generated_at: UtcMoment


# --------------------------------------------------------------------------
# assessment models
# --------------------------------------------------------------------------

# The framework's own phrasing for what a gap must not say, reduced to the form
# G1 compares against. Output Contract section 6: "Do not say only 'insufficient
# evidence.'"
_GAP_PLACEHOLDERS = frozenset(
    {
        "insufficient evidence",
        "not enough evidence",
        "no evidence",
        "unknown",
        "unclear",
    }
)

# Mapped to spaces rather than removed: dropping a hyphen would turn
# "no-evidence" into "noevidence" and let the placeholder through.
_PUNCTUATION = str.maketrans(string.punctuation, " " * len(string.punctuation))


def _reduced(text: str) -> str:
    """Casefolded, punctuation-stripped, whitespace-collapsed."""
    return " ".join(text.translate(_PUNCTUATION).casefold().split())


class Contradiction(PlinthModel):
    """Why two admissible observations about the same proposition cannot both stand.

    Framework section 2.4: ``CONTRADICTORY`` applies only where the conflict
    "cannot be resolved by explicit scope, precedence, supersession, versioning
    or freshness rules", and "newer evidence does not win implicitly" --
    ``precedence_considered`` is the record that those rules were tried.

    Not required to address all four of scope, version, supersession and
    freshness: some conflicts have no version and no supersession relationship,
    and demanding all four produces boilerplate instead of evidence.

    No ``resolution`` field. ``coverage == CONTRADICTORY`` already says the
    conflict is unresolved; a resolution recorded next to it would contradict
    the status it sits under.
    """

    conflicting_observation_ids: Annotated[tuple[RecordId, ...], Field(min_length=2)]
    conflict_basis: NonEmpty
    precedence_considered: Annotated[tuple[NonEmpty, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def _cn1_conflict_needs_two_different_observations(self) -> Contradiction:
        """CN1 -- the two sides of a conflict must be two different observations.

        ``min_length=2`` counts entries, not distinct ones, so the same id twice
        satisfies it and every downstream rule: K9's subset test passes, and X1
        resolves both copies. The result is a ``CONTRADICTORY`` check whose
        conflict is one observation disagreeing with itself, which section 2.4
        cannot mean by "materially inconsistent ... observations".
        """
        if len(set(self.conflicting_observation_ids)) < 2:
            raise PydanticCustomError(
                "CN1",
                "conflicting_observation_ids names {count} entries but only {distinct} "
                "distinct observation(s); a conflict needs two different observations",
                {
                    "count": len(self.conflicting_observation_ids),
                    "distinct": len(set(self.conflicting_observation_ids)),
                },
            )
        return self


class Gap(PlinthModel):
    """The six Output Contract section 6 fields, in document order.

    Nested inside its check rather than held in a parallel array: a check has at
    most one gap, so a separate collection bought two identifier fields, a join
    and three container validators to assert what nesting makes structural.
    """

    question: NonEmpty
    what_is_known: NonEmpty
    what_remains_unresolved: NonEmpty
    what_this_means: NonEmpty
    what_would_close_it: NonEmpty
    evidence: NonEmpty
    evidence_observation_ids: tuple[RecordId, ...] = ()

    @model_validator(mode="after")
    def _g1_unresolved_is_specific(self) -> Gap:
        """G1 -- Output Contract section 6: "Do not say only 'insufficient evidence.'"

        The field must name the exact missing, incomplete, conflicting, stale or
        out-of-scope proposition. A bare placeholder tells an allocator nothing
        they did not already know from the coverage status.
        """
        if _reduced(self.what_remains_unresolved) in _GAP_PLACEHOLDERS:
            raise PydanticCustomError(
                "G1",
                "what_remains_unresolved is a bare placeholder; it must name the exact "
                "missing, incomplete, conflicting, stale or out-of-scope proposition",
            )
        return self


# ``(applicability, coverage) -> gap required``, built from C1's exhaustive
# table so that the two can never drift. Absence from this mapping means the
# pair is illegal, which K1-K3 have already rejected by the time K8 looks.
_GAP_REQUIRED: dict[tuple[Applicability, Coverage | None], bool] = {
    (applicability, coverage): required for applicability, coverage, required in GAP_RULES
}


class CheckAssessment(PlinthModel):
    """One catalogue check, answered.

    Carries no ``materiality`` and no ``pillar_id``: the C1 catalogue owns both,
    keyed by ``check_id``. Copying materiality here would create the exact leak
    surface section 2.10 forbids -- and then require a rule to police it. Not
    holding it deletes the surface instead.

    Carries no ``searched_route_ids`` (``Route.required_for_check_ids`` owns that
    mapping, and letting the check restate it invites disagreement), no
    ``assessed_at`` (``AssessmentMeta.generated_at`` covers the run), and no
    free-text scope bag: routes, ``exclusions`` and ``applicability_basis``
    already carry that content, and an unvalidated paragraph does not preserve
    section 2.3's population completeness, it only looks like it does.
    """

    check_id: CheckId
    applicability: Applicability
    applicability_basis: NonEmpty
    applicability_observation_ids: tuple[RecordId, ...] = ()
    coverage: Coverage | None = None
    coverage_basis: NonEmpty | None = None
    finding_observation_ids: tuple[RecordId, ...] = ()
    finding: NonEmpty
    exclusions: tuple[NonEmpty, ...] = ()
    contradiction: Contradiction | None = None
    gap: Gap | None = None

    def _labels(self) -> dict[str, str]:
        """Message context for the rules that name both fields; ``null`` for no coverage."""
        return {
            "applicability": str(self.applicability),
            "coverage": str(self.coverage) if self.coverage else "null",
        }

    # K2, K3 and K1 partition the same (applicability, coverage) space and are
    # written in the order they should fire, not in numeric order. Pydantic runs
    # after-validators in definition order and stops at the first that raises, so
    # the specific diagnosis has to come before the general one: K1 would answer
    # "APPLIES with NOT_APPLICABLE" only with "those two occur together", where K3
    # names which of the two fields is wrong.

    @model_validator(mode="after")
    def _k2_unresolved_has_no_coverage(self) -> CheckAssessment:
        """K2 -- section 2.1: "``UNRESOLVED`` remains visible and has no coverage status."

        It "must not be converted into ``NOT_APPLICABLE`` merely because the
        relevant feature was not found, or into ``NOT_ASSESSED`` merely because
        the assessment could not determine whether the check applies."
        """
        if self.applicability is Applicability.UNRESOLVED and self.coverage is not None:
            raise PydanticCustomError(
                "K2",
                "applicability is UNRESOLVED, which has no coverage status, but "
                "coverage is {coverage}",
                {"coverage": str(self.coverage)},
            )
        return self

    @model_validator(mode="after")
    def _k3_applies_has_a_real_coverage(self) -> CheckAssessment:
        """K3 -- section 2.4 lists five coverage statuses for an applicable check.

        ``NOT_APPLICABLE`` is not among them, and a null coverage on an
        applicable check is a check nobody answered.
        """
        if self.applicability is Applicability.APPLIES:
            if self.coverage is None:
                raise PydanticCustomError(
                    "K3", "applicability is APPLIES, so coverage is required"
                )
            if self.coverage is Coverage.NOT_APPLICABLE:
                raise PydanticCustomError(
                    "K3",
                    "applicability is APPLIES, so coverage cannot be NOT_APPLICABLE",
                )
        return self

    @model_validator(mode="after")
    def _k1_does_not_apply_iff_not_applicable(self) -> CheckAssessment:
        """K1 -- section 2.1: "Only ``DOES_NOT_APPLY`` produces a coverage status of
        ``NOT_APPLICABLE``."

        The reverse direction is the one that matters in practice: it stops a
        check that merely found nothing from being filed as inapplicable.
        """
        does_not_apply = self.applicability is Applicability.DOES_NOT_APPLY
        not_applicable = self.coverage is Coverage.NOT_APPLICABLE
        if does_not_apply != not_applicable:
            raise PydanticCustomError(
                "K1",
                "applicability is {applicability} and coverage is {coverage}; "
                "DOES_NOT_APPLY and NOT_APPLICABLE occur only together",
                self._labels(),
            )
        return self

    @model_validator(mode="after")
    def _k4_decided_applicability_rests_on_facts(self) -> CheckAssessment:
        """K4 -- section 2.1: applicability rests on "structural facts".

        Section 2.6's authoritative absence is why ``DOES_NOT_APPLY`` is included:
        establishing that a structural condition is *absent* needs positive
        evidence too. Only ``UNRESOLVED`` is exempt, because not having the facts
        is precisely what it records.
        """
        decided = self.applicability in (Applicability.APPLIES, Applicability.DOES_NOT_APPLY)
        if decided and not self.applicability_observation_ids:
            raise PydanticCustomError(
                "K4",
                "applicability is {applicability}, so applicability_observation_ids must "
                "cite the structural facts it rests on",
                {"applicability": str(self.applicability)},
            )
        return self

    @model_validator(mode="after")
    def _k5_not_assessed_names_the_unfinished_activity(self) -> CheckAssessment:
        """K5 -- Output Contract 6.1: ``NOT_ASSESSED`` must "identify the declared
        acquisition route or assessment activity that was not completed"."""
        if self.coverage is Coverage.NOT_ASSESSED and self.coverage_basis is None:
            raise PydanticCustomError(
                "K5",
                "coverage is NOT_ASSESSED, so coverage_basis must name the declared "
                "acquisition route or assessment activity that was not completed",
            )
        return self

    @model_validator(mode="after")
    def _k6_evidence_backed_coverage_cites_observations(self) -> CheckAssessment:
        """K6 -- section 2.8: a check result is supported by observations.

        ``EVIDENCED``, ``PARTIAL`` and ``CONTRADICTORY`` each assert that some
        admissible evidence exists, so each must say which.
        """
        needs_findings = self.coverage in (
            Coverage.EVIDENCED,
            Coverage.PARTIAL,
            Coverage.CONTRADICTORY,
        )
        if needs_findings and not self.finding_observation_ids:
            raise PydanticCustomError(
                "K6",
                "coverage is {coverage}, so finding_observation_ids must cite the "
                "observations that support the finding",
                {"coverage": str(self.coverage)},
            )
        return self

    @model_validator(mode="after")
    def _k7_contradictory_iff_contradiction(self) -> CheckAssessment:
        """K7 -- section 2.4: ``CONTRADICTORY`` names the inconsistent observations.

        Both directions: the status without the record is an unexplained
        conflict, and the record without the status is a conflict filed under a
        coverage that denies it.
        """
        contradictory = self.coverage is Coverage.CONTRADICTORY
        if contradictory and self.contradiction is None:
            raise PydanticCustomError(
                "K7", "coverage is CONTRADICTORY, so contradiction is required"
            )
        if not contradictory and self.contradiction is not None:
            raise PydanticCustomError(
                "K7",
                "contradiction is present but coverage is {coverage}, not CONTRADICTORY",
                self._labels(),
            )
        return self

    @model_validator(mode="after")
    def _k8_gap_presence_follows_the_catalogue(self) -> CheckAssessment:
        """K8 -- gap presence is decided by C1's ``GAP_RULES``, and by nothing else.

        Section 2.10: materiality "cannot determine whether an applicable gap is
        shown". Reading the requirement out of the catalogue table means this
        rule has no access to materiality even in principle.

        The pair is guaranteed to be in the table by K1-K3; if it is not, those
        rules already reported why and this one stays silent rather than adding
        a confusing second error.
        """
        required = _GAP_REQUIRED.get((self.applicability, self.coverage))
        if required is None:
            return self
        if required and self.gap is None:
            raise PydanticCustomError(
                "K8",
                "applicability {applicability} with coverage {coverage} requires a gap",
                self._labels(),
            )
        if not required and self.gap is not None:
            raise PydanticCustomError(
                "K8",
                "applicability {applicability} with coverage {coverage} takes no gap",
                self._labels(),
            )
        return self

    @model_validator(mode="after")
    def _k9_conflict_is_drawn_from_the_finding(self) -> CheckAssessment:
        """K9 -- the conflicting observations are a subset of the finding's own.

        Section 2.4 scopes ``CONTRADICTORY`` to "materially inconsistent
        admissible observations about the same proposition"; a conflict citing
        observations the finding never used describes a different finding.
        """
        if self.contradiction is None:
            return self
        cited = set(self.finding_observation_ids)
        stray = [
            observation_id
            for observation_id in self.contradiction.conflicting_observation_ids
            if observation_id not in cited
        ]
        if stray:
            raise PydanticCustomError(
                "K9",
                "contradiction cites {stray} which finding_observation_ids does not",
                {"stray": ", ".join(stray)},
            )
        return self

    @model_validator(mode="after")
    def _g2_partial_and_contradictory_gaps_cite_evidence(self) -> CheckAssessment:
        """G2 -- a gap cites evidence exactly when there is evidence to cite.

        ``PARTIAL`` and ``CONTRADICTORY`` both assert that admissible evidence
        exists, so the gap must show it. For ``MISSING``, ``NOT_ASSESSED`` and
        unresolved applicability the citation is optional: a completed campaign
        that found no qualifying evidence has nothing to cite, and requiring a
        citation would force a fabricated "nothing was found" observation --
        exactly the non-discovery-as-fact move the framework's core commitments
        forbid. The route records establish that boundary instead.
        """
        if self.gap is None:
            return self
        needs_evidence = self.coverage in (Coverage.PARTIAL, Coverage.CONTRADICTORY)
        if needs_evidence and not self.gap.evidence_observation_ids:
            raise PydanticCustomError(
                "G2",
                "coverage is {coverage}, so the gap must cite the evidence it has in "
                "gap.evidence_observation_ids",
                {"coverage": str(self.coverage)},
            )
        return self


class AssessmentMeta(PlinthModel):
    """What this assessment was produced from.

    ``evidence_pack_sha256`` is the pin that makes the assessment
    non-transferable between evidence packs; ``X4`` recomputes it.
    """

    campaign_run_id: RecordId
    framework_version: NonEmpty
    catalogue_sha256: Sha256
    evidence_pack_sha256: Sha256
    generated_at: UtcMoment


class Assessment(PlinthModel):
    """Every check this campaign answered.

    That all 63 catalogue checks are present is campaign policy enforced at C5
    ingestion, not a model invariant: a one-check assessment is a legal
    document, it is just not a complete review.
    """

    schema_version: Literal["plinth.assessment/1"]
    meta: AssessmentMeta
    checks: tuple[CheckAssessment, ...] = ()

    @model_validator(mode="after")
    def _as1_one_answer_per_check(self) -> Assessment:
        """AS1 -- two answers for one check is two claims with no rule to pick between them."""
        seen: dict[str, int] = {}
        for index, check in enumerate(self.checks):
            first = seen.get(check.check_id)
            if first is not None:
                raise PydanticCustomError(
                    "AS1",
                    "check_id {check_id} appears at checks[{first}] and checks[{second}]",
                    {"check_id": check.check_id, "first": first, "second": index},
                )
            seen[check.check_id] = index
        return self
