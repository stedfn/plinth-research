"""Closed vocabularies shared by every Plinth stage.

These are the framework's own terms, not implementation conveniences. Each
value below is quoted verbatim from Plinth Framework v0.2 sections 2.1, 2.4
and 2.10; adding a member is a framework change, not a refactor.
"""

from __future__ import annotations

from enum import StrEnum


class PillarId(StrEnum):
    """The five owning pillars.

    ``Assets & Backing -> backing`` and ``Governance & Compliance ->
    governance_compliance`` (ID prefix ``PF-GOV``) follow no slug rule, which is
    why the mapping is written by hand in ``catalogue.PILLAR_TABLE`` and pinned
    to the framework's own section headings by V7.
    """

    CONTROL = "control"
    BACKING = "backing"
    ECONOMICS = "economics"
    GOVERNANCE_COMPLIANCE = "governance_compliance"
    CONTINUITY = "continuity"


class Materiality(StrEnum):
    """Framework section 2.10. Internal diligence importance, never published.

    All three members are legal in any framework version. That v0.2 assigns no
    check ``LOW`` is a property of the current catalogue, asserted separately as
    a distribution, not a constraint on the vocabulary.
    """

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Applicability(StrEnum):
    """Framework section 2.1. Decided before coverage."""

    APPLIES = "APPLIES"
    DOES_NOT_APPLY = "DOES_NOT_APPLY"
    UNRESOLVED = "UNRESOLVED"


class Coverage(StrEnum):
    """Framework section 2.4. Records evidence completion, not risk."""

    EVIDENCED = "EVIDENCED"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    CONTRADICTORY = "CONTRADICTORY"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_ASSESSED = "NOT_ASSESSED"


class GapField(StrEnum):
    """Output Contract section 6. Stable JSON keys for the six-field gap.

    The human-readable headings live in ``catalogue.GAP_DISPLAY_LABELS`` and are
    verified against the Output Contract markdown. Visible labels are not stable
    keys: rewording a heading must not break every consumer.
    """

    QUESTION = "question"
    WHAT_IS_KNOWN = "what_is_known"
    WHAT_REMAINS_UNRESOLVED = "what_remains_unresolved"
    WHAT_THIS_MEANS = "what_this_means"
    WHAT_WOULD_CLOSE_IT = "what_would_close_it"
    EVIDENCE = "evidence"


class AcquisitionMode(StrEnum):
    """How an artifact was, or would be, obtained.

    Framework section 2.6 -- acquisition mode is a dimension of evidence
    separate from authority, admissibility and sufficiency, and the modes listed
    per check are "non-binding testing hypotheses". The three members below are
    the ones a documentary-only campaign can actually perform; ``api`` and
    ``rpc`` arrive when a stage emits them.

    Extraction and calculation are deliberately absent: neither obtains an
    artifact from a source, so neither is an acquisition. A derived observation
    records its lineage instead (section 2.8).
    """

    HTTP_DOWNLOAD = "HTTP_DOWNLOAD"
    BROWSER_CAPTURE = "BROWSER_CAPTURE"
    MANUAL_UPLOAD = "MANUAL_UPLOAD"


class AcquisitionOutcome(StrEnum):
    """What one attempt to obtain an artifact actually did.

    Framework section 2.5 -- "a skipped or failed required acquisition path
    cannot silently produce ``MISSING``", which is only enforceable if the
    failure modes are distinguishable from success.

    This vocabulary describes the fetch and nothing else. An acquisition that
    downloaded a document later superseded remains ``ACQUIRED``; supersession is
    a property of the source, recorded in ``SourceDisposition``.
    """

    ACQUIRED = "ACQUIRED"
    ACCESS_BLOCKED = "ACCESS_BLOCKED"
    NOT_FOUND = "NOT_FOUND"
    FAILED = "FAILED"


class SourceDisposition(StrEnum):
    """Whether a source counts toward the campaign's evidence.

    Framework section 2.2 -- "intentional exclusions state their evidentiary
    reason and expected effect on coverage". ``SUPERSEDED`` remains usable
    evidence: a superseded document is authoritative for an explicitly dated
    historical proposition even though it is not current.
    """

    IN_SCOPE = "IN_SCOPE"
    EXCLUDED = "EXCLUDED"
    SUPERSEDED = "SUPERSEDED"


class RouteStatus(StrEnum):
    """Whether a declared evidence-access path was carried out.

    Framework section 2.5 -- the campaign "declares which evidence-access paths
    it will attempt", and the distinction between a completed search that found
    nothing (``MISSING``) and a search that did not finish (``NOT_ASSESSED``)
    rests entirely on this field.
    """

    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"


class LocatorType(StrEnum):
    """How a position inside an archived artifact is addressed.

    Framework section 2.6 gate 1 -- "what exactly was obtained". A locator is
    the part of provenance that says *where in the artifact*, so that a third
    party can return to the same position.
    """

    PDF_PAGE = "pdf_page"
    DOCUMENT_SECTION = "document_section"
    DOCUMENT_FIELD = "document_field"
    HTML_HEADING = "html_heading"
    HTML_SELECTOR = "html_selector"
    TEXT_SPAN = "text_span"


class ResearchPosture(StrEnum):
    """Framework section 2.7. Who produced a source and on whose behalf.

    The five members are the framework's own list, verbatim: "whether the work
    is self-attestation, commissioned research, independent assurance, a rating
    or unaffiliated research". Section 2.7 records provenance "where
    applicable", and a regulatory filing fits none of the five, so the field
    carrying this enum is optional rather than defaulted.
    """

    SELF_ATTESTATION = "self_attestation"
    COMMISSIONED_RESEARCH = "commissioned_research"
    INDEPENDENT_ASSURANCE = "independent_assurance"
    RATING = "rating"
    UNAFFILIATED_RESEARCH = "unaffiliated_research"
