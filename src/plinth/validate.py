"""Entry points, and the rules no single record can enforce.

:mod:`plinth.models` decides whether a record is well-formed. This module
decides whether the records agree with one another: that every edge resolves,
that a support really traces through the acquisition that fetched the artifact
it points into, that lineage is acyclic, that every acquisition used an access
mode the campaign declared, and that an assessment refers to the exact evidence
pack it was produced from.

Three entry points:

``validate_pack``                     raw JSON -> :class:`~plinth.models.EvidencePack`
``validate_assessment``               raw JSON -> :class:`~plinth.models.Assessment`
``validate_assessment_against_pack``  the two together

Each returns **all discoverable issues**, not all issues. Malformed nested input
can stop a model from constructing, which stops every graph rule that depends on
it from running at all; and pydantic reports one cross-field rule per record.
Promising "every issue" would promise something the layering cannot deliver.

An artifact is valid only when the returned issue tuple is empty. The model is
returned whenever it *constructed*, so that a caller can inspect a
graph-invalid pack -- a non-``None`` model is not a verdict.
"""

from __future__ import annotations

import json
from collections import deque
from typing import Any, TypeVar
from urllib.parse import unquote, urlsplit

from pydantic import BaseModel, ValidationError

from .models import Assessment, EvidencePack, Issue, Route, canonical_sha256
from .vocab import AcquisitionOutcome, Coverage, RouteStatus, SourceDisposition

ModelT = TypeVar("ModelT", bound=BaseModel)


# --------------------------------------------------------------------------
# pointers
# --------------------------------------------------------------------------


def escape_token(token: str) -> str:
    """RFC 6901 section 3: ``~`` becomes ``~0`` and ``/`` becomes ``~1``.

    Order matters. Escaping ``/`` first would turn a literal ``~`` in the
    replacement back into an escape on the second pass.
    """
    return token.replace("~", "~0").replace("/", "~1")


def pointer(*tokens: str | int) -> str:
    """An RFC 6901 JSON pointer. No tokens is the whole document, spelled ``""``."""
    return "".join("/" + escape_token(str(token)) for token in tokens)


def issue(code: str, message: str, *tokens: str | int) -> Issue:
    return Issue(pointer=pointer(*tokens), code=code, message=message)


# --------------------------------------------------------------------------
# raw input
# --------------------------------------------------------------------------


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    """``object_pairs_hook`` that refuses a repeated key at any nesting depth.

    ``json.loads`` keeps the *last* value for a repeated key and says nothing
    about the ones it discarded. In a compiler whose whole contract is
    accept-or-reject, that is a silent drop of submitted content -- and it
    happens during parsing, before pydantic runs, so ``extra="forbid"`` never
    sees the shadowed value. A model emitting ``{"value": 1, "value": 2}`` would
    have one of its two answers deleted without a diagnostic.

    Raises ``ValueError`` so it arrives at :func:`parse_document` through the
    same path as any other malformed JSON.
    """
    seen: set[str] = set()
    for key, _ in pairs:
        if key in seen:
            raise ValueError(f"duplicate object key {key!r}")
        seen.add(key)
    return dict(pairs)


def parse_document(raw: object) -> tuple[dict | None, tuple[Issue, ...]]:
    """Reduce whatever the caller has to a JSON object, or say why it is not one.

    Accepts bytes off disk, a decoded string, or an already-parsed object. Every
    failure below is a normal outcome of reading model output, so each becomes
    an :class:`~plinth.models.Issue` rather than an exception -- a caller
    handling three exception types alongside an issue tuple would inevitably
    handle one of them wrong.

    The ``except`` is ``ValueError`` rather than ``json.JSONDecodeError``.
    ``JSONDecodeError`` subclasses it, so this is a widening rather than a
    second branch, and it catches two things the narrower clause let escape: an
    integer literal past CPython's 4300-digit conversion limit, which raises a
    bare ``ValueError``, and :func:`reject_duplicate_keys`. ``RecursionError``
    is caught alongside it: ``json.loads`` raises it on deeply nested input
    (depth 10,000 on CPython 3.13, a ~20 KB document), and that is malformed
    input, not a bug.

    An already-parsed ``dict`` is re-entered through the text path rather than
    trusted. ``json.dumps`` refuses a ``set`` (``TypeError``) and an integer past
    the digit limit (``ValueError``); pydantic accepts both, and each would
    otherwise surface later as an exception out of :func:`canonical_bytes` --
    or, for the set, as a digest that changes with hash randomization.
    """
    if isinstance(raw, dict):
        try:
            raw = json.dumps(raw)
        except (TypeError, ValueError) as exc:
            return None, (issue("invalid_json", f"input is not JSON-serializable: {exc}"),)
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = bytes(raw).decode("utf-8")
        except UnicodeDecodeError as exc:
            return None, (issue("invalid_utf8", f"input is not valid UTF-8: {exc}"),)
    if isinstance(raw, str):
        try:
            raw = json.loads(raw, object_pairs_hook=reject_duplicate_keys)
        except (ValueError, RecursionError) as exc:
            return None, (issue("invalid_json", f"input is not valid JSON: {exc}"),)
    if not isinstance(raw, dict):
        return None, (
            issue(
                "not_an_object",
                f"input is a JSON {type(raw).__name__}, expected an object",
            ),
        )
    return raw, ()


def issues_from(error: ValidationError) -> tuple[Issue, ...]:
    """Turn a pydantic ``ValidationError`` into pointer-addressed issues.

    ``loc`` is already the path through the submitted document -- field names and
    list indices, in order -- because every model forbids extra keys and no
    field is aliased. That correspondence is what makes the pointer usable as
    re-prompt feedback, and it is why unions of scalars are avoided in the
    models: they would add union-member tags to ``loc`` that name nothing in the
    document.
    """
    return tuple(
        Issue(
            pointer=pointer(*error_detail["loc"]),
            code=str(error_detail["type"]),
            message=error_detail["msg"],
        )
        for error_detail in error.errors()
    )


def construct(model: type[ModelT], raw: object) -> tuple[ModelT | None, tuple[Issue, ...]]:
    """Parse and shape-validate, collecting issues instead of raising."""
    document, problems = parse_document(raw)
    if document is None:
        return None, problems
    try:
        return model.model_validate(document), ()
    except ValidationError as exc:
        return None, issues_from(exc)


# --------------------------------------------------------------------------
# pack graph rules
# --------------------------------------------------------------------------

# ``field on the pack``, ``the identifying attribute``. P1 walks this table.
PACK_COLLECTIONS: tuple[tuple[str, str], ...] = (
    ("sources", "source_id"),
    ("acquisitions", "acquisition_id"),
    ("artifacts", "sha256"),
    ("locator_catalog", "locator_id"),
    ("observations", "observation_id"),
    ("routes", "route_id"),
)


def check_p1_unique_ids(pack: EvidencePack) -> tuple[Issue, ...]:
    """P1 -- one identifier, one record.

    A duplicate is worse than a dangling reference: every join in this module
    silently picks one of the two, so the artifact would validate while meaning
    two different things depending on which record won. The message names both
    indices because "duplicate id" alone leaves the reader to find them.
    """
    found: list[Issue] = []
    for collection, key in PACK_COLLECTIONS:
        first_seen: dict[str, int] = {}
        for index, record in enumerate(getattr(pack, collection)):
            identifier = getattr(record, key)
            previous = first_seen.get(identifier)
            if previous is None:
                first_seen[identifier] = index
                continue
            found.append(
                issue(
                    "P1",
                    f"duplicate {key} {identifier!r}: also at "
                    f"{pointer(collection, previous, key)}",
                    collection,
                    index,
                    key,
                )
            )
    return tuple(found)


def index_of(pack: EvidencePack, collection: str, key: str) -> dict[str, Any]:
    """First record per identifier. P1 reports the duplicates that make this lossy."""
    index: dict[str, Any] = {}
    for record in getattr(pack, collection):
        index.setdefault(getattr(record, key), record)
    return index


def check_p2_references_resolve(pack: EvidencePack) -> tuple[Issue, ...]:
    """P2 -- every identifier used as an edge names a record that exists.

    Enumerated explicitly rather than derived from type annotations: a
    ``RecordId`` field carries no information about which collection it points
    into, and inferring that from the field name would silently stop checking an
    edge the day someone renames one.
    """
    sources = index_of(pack, "sources", "source_id")
    acquisitions = index_of(pack, "acquisitions", "acquisition_id")
    artifacts = index_of(pack, "artifacts", "sha256")
    locators = index_of(pack, "locator_catalog", "locator_id")
    observations = index_of(pack, "observations", "observation_id")

    found: list[Issue] = []

    def require(target: dict[str, Any], value: str | None, kind: str, *tokens: str | int) -> None:
        if value is not None and value not in target:
            found.append(issue("P2", f"no {kind} with id {value!r}", *tokens))

    for index, acquisition in enumerate(pack.acquisitions):
        require(sources, acquisition.source_id, "source", "acquisitions", index, "source_id")
        require(
            artifacts,
            acquisition.artifact_sha256,
            "artifact",
            "acquisitions",
            index,
            "artifact_sha256",
        )

    for index, source in enumerate(pack.sources):
        require(
            sources,
            source.superseded_by_source_id,
            "source",
            "sources",
            index,
            "superseded_by_source_id",
        )

    for index, locator in enumerate(pack.locator_catalog):
        require(
            artifacts,
            locator.artifact_sha256,
            "artifact",
            "locator_catalog",
            index,
            "artifact_sha256",
        )

    for index, observation in enumerate(pack.observations):
        for support_index, support in enumerate(observation.supports):
            require(
                acquisitions,
                support.acquisition_id,
                "acquisition",
                "observations",
                index,
                "supports",
                support_index,
                "acquisition_id",
            )
            require(
                locators,
                support.locator_id,
                "locator",
                "observations",
                index,
                "supports",
                support_index,
                "locator_id",
            )
        for parent_index, parent_id in enumerate(observation.parent_observation_ids):
            require(
                observations,
                parent_id,
                "observation",
                "observations",
                index,
                "parent_observation_ids",
                parent_index,
            )

    for index, route in enumerate(pack.routes):
        for source_index, source_id in enumerate(route.source_ids):
            require(sources, source_id, "source", "routes", index, "source_ids", source_index)

    return tuple(found)


def check_p3_p4_supports_are_usable(pack: EvidencePack) -> tuple[Issue, ...]:
    """P3 and P4 -- a support has to actually trace to admitted evidence.

    They are computed together because both need the same three-record join, and
    doing it twice would be two chances to write it differently.

    **P3, coherence:** the acquisition and the locator must name the *same*
    artifact. Without this, a support could pair a real acquisition of document
    A with a real locator inside document B and read a fact from a file that
    acquisition never fetched.

    **P4, admission:** the acquisition must have succeeded, and the source
    behind it must not be excluded. The disposition half closes a hole that
    opens as soon as exclusion is a property of the source: the acquisition of
    a deliberately excluded source is still ``ACQUIRED``, so an outcome-only
    check would let an excluded source support a fact anyway.

    ``SUPERSEDED`` stays usable. A superseded document is authoritative for an
    explicitly dated historical observation, and section 2.4's own conflict
    rules name supersession as something that *resolves* a conflict, not
    something that voids evidence.

    Dangling references are skipped rather than re-reported: P2 owns them.
    """
    acquisitions = index_of(pack, "acquisitions", "acquisition_id")
    locators = index_of(pack, "locator_catalog", "locator_id")
    sources = index_of(pack, "sources", "source_id")

    found: list[Issue] = []
    for index, observation in enumerate(pack.observations):
        for support_index, support in enumerate(observation.supports):
            acquisition = acquisitions.get(support.acquisition_id)
            locator = locators.get(support.locator_id)
            where = ("observations", index, "supports", support_index)
            if acquisition is None or locator is None:
                continue

            if acquisition.outcome is not AcquisitionOutcome.ACQUIRED:
                found.append(
                    issue(
                        "P4",
                        f"acquisition {support.acquisition_id!r} has outcome "
                        f"{acquisition.outcome}, so it produced no evidence to cite",
                        *where,
                        "acquisition_id",
                    )
                )
            else:
                source = sources.get(acquisition.source_id)
                if source is not None and source.disposition is SourceDisposition.EXCLUDED:
                    found.append(
                        issue(
                            "P4",
                            f"acquisition {support.acquisition_id!r} belongs to source "
                            f"{source.source_id!r}, which is EXCLUDED from the campaign",
                            *where,
                            "acquisition_id",
                        )
                    )

            if acquisition.artifact_sha256 is None:
                # A1 already reported the acquisition; there is nothing to compare.
                continue
            if acquisition.artifact_sha256 != locator.artifact_sha256:
                found.append(
                    issue(
                        "P3",
                        f"locator {support.locator_id!r} points into artifact "
                        f"{locator.artifact_sha256} but acquisition "
                        f"{support.acquisition_id!r} fetched "
                        f"{acquisition.artifact_sha256}",
                        *where,
                        "locator_id",
                    )
                )
    return tuple(found)


def check_p5_lineage_is_acyclic(pack: EvidencePack) -> tuple[Issue, ...]:
    """P5 -- section 2.8: derivation provenance "must be acyclic".

    A cycle is a set of observations each justified by the others, which is a
    fact with no evidence underneath it however far you follow the chain.

    Kahn's algorithm peels observations with no remaining parents. Whatever
    survives is on a cycle or downstream of one, and every survivor has at least
    one surviving parent -- so walking parents from any survivor must revisit a
    node, and that revisit is a real cycle to name. Dangling parents are
    dropped first; P2 owns them, and counting them here would manufacture a
    false cycle out of a missing record.
    """
    known = {observation.observation_id for observation in pack.observations}
    parents = {
        observation.observation_id: [
            parent for parent in observation.parent_observation_ids if parent in known
        ]
        for observation in pack.observations
    }

    remaining = {node: len(node_parents) for node, node_parents in parents.items()}
    children: dict[str, list[str]] = {node: [] for node in parents}
    for node, node_parents in parents.items():
        for parent in node_parents:
            children[parent].append(node)

    ready = deque(node for node, count in remaining.items() if count == 0)
    settled = 0
    while ready:
        node = ready.popleft()
        settled += 1
        for child in children[node]:
            remaining[child] -= 1
            if remaining[child] == 0:
                ready.append(child)

    if settled == len(parents):
        return ()

    survivors = {node for node, count in remaining.items() if count > 0}
    path = walk_to_repeat(min(survivors), parents, survivors)
    index_by_id = {
        observation.observation_id: index for index, observation in enumerate(pack.observations)
    }
    return (
        issue(
            "P5",
            "derivation lineage contains a cycle: " + " -> ".join(path),
            "observations",
            index_by_id[path[0]],
            "parent_observation_ids",
        ),
    )


def walk_to_repeat(
    start: str, parents: dict[str, list[str]], survivors: set[str]
) -> list[str]:
    """Follow surviving parents until a node repeats, and return that cycle.

    The walk is guaranteed to terminate: every survivor has a surviving parent,
    and there are finitely many survivors. The returned list begins and ends on
    the same node so the message reads as a closed loop.
    """
    order: list[str] = []
    seen: dict[str, int] = {}
    node = start
    while node not in seen:
        seen[node] = len(order)
        order.append(node)
        node = next(parent for parent in parents[node] if parent in survivors)
    return [*order[seen[node] :], node]


def check_p6_pack_times_are_ordered(pack: EvidencePack) -> tuple[Issue, ...]:
    """P6 -- section 2.9: the pack's own timeline has to make sense.

    The cutoff is the snapshot the campaign declared; generating the pack before
    it means the pack cannot contain what the cutoff promises.

    Every moment at which the pack acquired something must fall on or before the
    moment the pack closed. Checking only ``attempted_at`` is not enough: an
    acquisition attempted in time but *retrieved* afterwards, or an artifact
    archived afterwards, means the assessment rests on bytes that had not
    arrived when the record was written. A2 already orders retrieval after its
    own attempt, so without this the late retrieval is ordered but unbounded.
    """
    found: list[Issue] = []
    if pack.generated_at < pack.campaign.cutoff:
        found.append(
            issue(
                "P6",
                f"generated_at {pack.generated_at.isoformat()} precedes the campaign cutoff "
                f"{pack.campaign.cutoff.isoformat()}",
                "generated_at",
            )
        )

    def not_after_generation(moment, label: str, *tokens: str | int) -> None:
        if moment is not None and moment > pack.generated_at:
            found.append(
                issue(
                    "P6",
                    f"{label} {moment.isoformat()} is after the pack was generated at "
                    f"{pack.generated_at.isoformat()}",
                    *tokens,
                )
            )

    for index, acquisition in enumerate(pack.acquisitions):
        not_after_generation(
            acquisition.attempted_at, "attempted_at", "acquisitions", index, "attempted_at"
        )
        not_after_generation(
            acquisition.retrieved_at, "retrieved_at", "acquisitions", index, "retrieved_at"
        )
    for index, artifact in enumerate(pack.artifacts):
        not_after_generation(artifact.archived_at, "archived_at", "artifacts", index, "archived_at")
    return tuple(found)


def check_p7_acquisition_modes_are_declared(pack: EvidencePack) -> tuple[Issue, ...]:
    """P7 -- section 2.5: a campaign declares which access paths it will attempt.

    Without this, ``declared_acquisition_modes`` constrains nothing: a campaign
    could declare ``HTTP_DOWNLOAD`` only and then record a ``MANUAL_UPLOAD``,
    which is the difference between evidence a third party can re-fetch and
    evidence one operator hand-placed. It is also what gives ``run.json``'s
    pre-registration its force -- ``D5`` pins the declaration, and this is the
    rule that makes the declaration mean something.

    The campaign is a *declaration of intent*, so the check is one-directional:
    a declared mode that was never used is an unattempted path, which section
    2.5 records through :class:`~plinth.models.Route` status rather than by
    forbidding the declaration.
    """
    declared = set(pack.campaign.declared_acquisition_modes)
    found: list[Issue] = []
    for index, acquisition in enumerate(pack.acquisitions):
        if acquisition.acquisition_mode not in declared:
            found.append(
                issue(
                    "P7",
                    f"acquisition_mode {acquisition.acquisition_mode} is not among the "
                    "campaign's declared_acquisition_modes ("
                    + ", ".join(sorted(str(mode) for mode in declared))
                    + ")",
                    "acquisitions",
                    index,
                    "acquisition_mode",
                )
            )
    return tuple(found)


CREDENTIAL_QUERY_PARAMS = frozenset(
    {"api_key", "apikey", "access_token", "auth_token", "secret"}
)
"""Query parameter names that make a URL an authenticated request rather than an address.

Deliberately **narrower** than
:data:`plinth.archive.REDACTED_QUERY_PARAMS`, and the asymmetry is the point:
``archive`` *redacts* the values of its own broader list, where a false
positive costs one unreadable character run in a field plinth authored, while
``P8`` *rejects*, where a false positive stops the operator's work. So bare
``key`` and bare ``token`` are on the redaction list and not on this one --
both name public resources often enough (a sort key, a pagination token) that
refusing them would fail honest documentary URLs.

**Still a heuristic, and a name-based one.** A signed query parameter
(``?Signature=``, ``?X-Amz-Credential=``), a secret in a path segment and a
secret in a fragment all pass. This is a list of the names that actually recur,
not a proof of absence.

It is **not** the value-shape heuristic already refused here. That one matched
on the *value* -- "eight or more characters with a letter and a digit" -- and
got it backwards, killing ``ondo-20231231.htm`` and
``OUSG_Prospectus_2024.pdf`` while keeping the CIK ``000185039124000004``.
Nothing here ever looks at a value or at a path segment.
"""


def credential_query_parameters(url: str) -> tuple[str, ...]:
    """Names of credential-bearing query parameters in ``url``.

    The name is percent-decoded and case-folded before matching, so neither
    ``?API_KEY=`` nor ``?api%5Fkey=`` slips past the list.

    A parameter with a blank value, or no ``=`` at all, still counts. The rule
    is not "a live secret is present" -- it is that this URL is an
    authenticated request rather than a document's address, and an address only
    one party can dereference is not provenance a third party can follow.
    """
    try:
        query = urlsplit(url).query
    except ValueError:
        return ()
    found = []
    for pair in query.split("&"):
        name = unquote(pair.partition("=")[0]).strip().casefold()
        if name in CREDENTIAL_QUERY_PARAMS:
            found.append(name)
    return tuple(dict.fromkeys(found))


def check_p8_source_urls_carry_no_credentials(pack: EvidencePack) -> tuple[Issue, ...]:
    """P8 -- a ``Source.url`` may not carry credentials.

    :attr:`~plinth.models.Source.url` is authored by the model and copied
    verbatim into a canonical artifact, so it is the route by which a credential
    reaches a record that gets hashed, stored and published. Two forms are
    refused: a userinfo component, and a query parameter named in
    :data:`CREDENTIAL_QUERY_PARAMS`.

    The query half closes the gap the C3 plan recorded in as many words --
    *"query strings stay unchecked, and that is now the one remaining route for
    a secret into a canonical record"* -- and an asymmetry that went with it:
    ``archive add`` already redacted ``?api_key=`` out of the URL *plinth*
    records, while the URL the *model* records went through untouched into the
    same artifact.

    **Rejected, never rewritten.** ``plinth.archive`` may redact because it
    authors the field it is editing; rewriting a URL the model authored would
    make a canonical source record say something its author did not write. That
    is also what bounds the cost of a false positive: a refusal the operator
    reads, never a silent edit they do not.

    A ``url`` that is not a parseable URL at all is left alone. This rule is
    about credentials in a URL, not about URL syntax, and nothing fetches the
    field.
    """
    found: list[Issue] = []
    for index, source in enumerate(pack.sources):
        if source.url is None:
            continue
        try:
            netloc = urlsplit(source.url).netloc
        except ValueError:
            continue
        if "@" in netloc:
            found.append(
                issue(
                    "P8",
                    "url carries a userinfo component (credentials before the '@'); "
                    "remove it and resubmit -- plinth rejects rather than rewrites, "
                    "because editing a source record would make it say something its "
                    "author did not write",
                    "sources",
                    index,
                    "url",
                )
            )
        leaked = credential_query_parameters(source.url)
        if leaked:
            found.append(
                issue(
                    "P8",
                    "url carries credential query parameter(s) "
                    + ", ".join(repr(name) for name in leaked)
                    + "; cite the document's own address, not an authenticated request "
                    "to it -- an address only one party can dereference is not "
                    "provenance a third party can follow",
                    "sources",
                    index,
                    "url",
                )
            )
    return tuple(found)


PACK_GRAPH_RULES = (
    check_p1_unique_ids,
    check_p2_references_resolve,
    check_p3_p4_supports_are_usable,
    check_p5_lineage_is_acyclic,
    check_p6_pack_times_are_ordered,
    check_p7_acquisition_modes_are_declared,
    check_p8_source_urls_carry_no_credentials,
)


# --------------------------------------------------------------------------
# entry points
# --------------------------------------------------------------------------


def validate_pack(raw: object) -> tuple[EvidencePack | None, tuple[Issue, ...]]:
    """Shape-validate an evidence pack, then check the graph it describes."""
    pack, problems = construct(EvidencePack, raw)
    if pack is None:
        return None, problems
    found: list[Issue] = []
    for rule in PACK_GRAPH_RULES:
        found.extend(rule(pack))
    return pack, tuple(found)


def validate_assessment(raw: object) -> tuple[Assessment | None, tuple[Issue, ...]]:
    """Shape-validate an assessment on its own.

    Every rule an assessment can be judged by in isolation is a model validator,
    so there is no graph pass here. Everything else needs the pack.
    """
    return construct(Assessment, raw)


def routes_by_required_check(pack: EvidencePack) -> dict[str, list[Route]]:
    """``check_id -> the declared searches whose completion decides MISSING vs NOT_ASSESSED``.

    Built once per pack: ``required_for_check_ids`` is unbounded and may repeat,
    so scanning every route per ``MISSING`` check is quadratic in the wrong place.
    """
    by_check: dict[str, list[Route]] = {}
    for route in pack.routes:
        for check_id in dict.fromkeys(route.required_for_check_ids):
            by_check.setdefault(check_id, []).append(route)
    return by_check


def validate_assessment_against_pack(
    assessment: Assessment, pack: EvidencePack
) -> tuple[Issue, ...]:
    """Check that the assessment is an assessment *of this pack*.

    Assumes both arguments already validated on their own. Pointers are into the
    assessment, because that is the document a re-prompt would ask a model to
    correct.
    """
    found: list[Issue] = []
    found.extend(check_x1_citations_exist(assessment, pack))
    found.extend(check_x2_coverage_matches_routes(assessment, pack))
    found.extend(check_x4_x5_x6_pack_is_pinned(assessment, pack))
    return tuple(found)


def check_x1_citations_exist(assessment: Assessment, pack: EvidencePack) -> tuple[Issue, ...]:
    """X1 -- every observation an assessment cites is in the pack.

    Without this, a check could cite an observation the extraction stage never
    produced, and the finding would rest on an identifier rather than a fact.
    """
    known = {observation.observation_id for observation in pack.observations}
    found: list[Issue] = []
    for index, check in enumerate(assessment.checks):
        cited: list[tuple[tuple[str | int, ...], tuple[str, ...]]] = [
            (("checks", index, "applicability_observation_ids"),
             check.applicability_observation_ids),
            (("checks", index, "finding_observation_ids"), check.finding_observation_ids),
        ]
        if check.gap is not None:
            cited.append(
                (("checks", index, "gap", "evidence_observation_ids"),
                 check.gap.evidence_observation_ids)
            )
        for where, identifiers in cited:
            for position, observation_id in enumerate(identifiers):
                if observation_id not in known:
                    found.append(
                        issue(
                            "X1",
                            f"no observation with id {observation_id!r} in the evidence pack",
                            *where,
                            position,
                        )
                    )
    return tuple(found)


def check_x2_coverage_matches_routes(
    assessment: Assessment, pack: EvidencePack
) -> tuple[Issue, ...]:
    """X2 -- section 2.5: "a skipped or failed required acquisition path cannot
    silently produce ``MISSING``".

    ``MISSING`` is the strong claim: the declared assessment was completed and
    found nothing. The route records are the only place that completion is
    written down, so the claim is checked against them.

    **The direction is easy to read backwards, so state it.** The test below is
    ``status is not COMPLETED``, and any such route is an error. So
    ``COMPLETED`` *unlocks* the ``MISSING`` claim and ``BLOCKED`` *prevents* it
    -- not the other way round. Which means the attack here is a route marked
    ``COMPLETED`` that was never run, and the stronger version of it is
    *omission*: because the condition is universal over required routes,
    dropping an inconvenient ``BLOCKED`` route from the pack is more effective
    than adding a fake ``COMPLETED`` one.

    Nothing yet ties a ``COMPLETED`` route to an archived acquisition on any of
    its sources; see :class:`~plinth.models.Route` for the three pieces that
    close it and why they land together in C4/C5 rather than separately.

    **X2 has two halves and needs both.** "Every required route is completed"
    passes *vacuously* when zero routes require the check -- which would let any
    check claim ``MISSING`` having declared no search at all. Requiring at least
    one route closes that.

    **There is deliberately no mirror rule for ``NOT_ASSESSED``.** The obvious
    one -- "at least one required route must be unfinished" -- is wrong, and
    wrong in the direction that matters. Framework check PF-ECONOMICS-011 says
    outright that "failure to select or complete a scenario is ``NOT_ASSESSED``",
    and a cost scenario is an assessment activity, not an acquisition route: a
    campaign can retrieve every fee document (all routes ``COMPLETED``) and still
    never compute the scenario. Output Contract 6.1 names both kinds of
    unfinished work -- "the declared acquisition route **or assessment
    activity**" -- and C2 models only the first.

    Enforcing the mirror anyway would push an honest campaign toward the
    stronger ``MISSING`` claim or toward mislabelling a completed route as
    ``BLOCKED``, which is worse than not checking. ``K5`` still requires
    ``coverage_basis`` to name the unfinished activity. Closing this properly
    needs declared assessment activities in the model, which is C4/C5 scope; it
    is tracked in the deferred list.
    """
    found: list[Issue] = []
    by_check = routes_by_required_check(pack)
    for index, check in enumerate(assessment.checks):
        if check.coverage is not Coverage.MISSING:
            continue
        required = by_check.get(check.check_id, [])
        where = ("checks", index, "coverage")

        if not required:
            found.append(
                issue(
                    "X2",
                    f"coverage is MISSING but no route declares {check.check_id} in "
                    "required_for_check_ids, so no search was declared for it",
                    *where,
                )
            )
            continue
        unfinished = [route for route in required if route.status is not RouteStatus.COMPLETED]
        if unfinished:
            found.append(
                issue(
                    "X2",
                    "coverage is MISSING but required route(s) "
                    + ", ".join(f"{route.route_id} ({route.status})" for route in unfinished)
                    + " did not complete; an unfinished search is NOT_ASSESSED",
                    *where,
                )
            )
    return tuple(found)


def check_x4_x5_x6_pack_is_pinned(
    assessment: Assessment, pack: EvidencePack
) -> tuple[Issue, ...]:
    """X4, X5, X6 -- the assessment names this pack, and no other.

    X4 hashes the pack's *canonical* form, so reformatting the JSON or writing
    ``Z`` for ``+00:00`` leaves the pin intact while changing one proposition
    breaks it. X5 catches the case X4 cannot explain: two packs from different
    runs. X6 is the ordering that makes the pin meaningful -- an assessment
    generated before its evidence assessed something else.
    """
    found: list[Issue] = []
    digest = canonical_sha256(pack)
    if assessment.meta.evidence_pack_sha256 != digest:
        found.append(
            issue(
                "X4",
                f"meta.evidence_pack_sha256 is {assessment.meta.evidence_pack_sha256}, but "
                f"the canonical form of this pack hashes to {digest}",
                "meta",
                "evidence_pack_sha256",
            )
        )
    if assessment.meta.campaign_run_id != pack.campaign.run_id:
        found.append(
            issue(
                "X5",
                f"meta.campaign_run_id is {assessment.meta.campaign_run_id!r}, but the pack's "
                f"campaign is {pack.campaign.run_id!r}",
                "meta",
                "campaign_run_id",
            )
        )
    if assessment.meta.generated_at < pack.generated_at:
        found.append(
            issue(
                "X6",
                f"meta.generated_at {assessment.meta.generated_at.isoformat()} precedes the "
                f"pack's generated_at {pack.generated_at.isoformat()}",
                "meta",
                "generated_at",
            )
        )
    return tuple(found)


__all__ = [
    "Assessment",
    "EvidencePack",
    "Issue",
    "canonical_sha256",
    "escape_token",
    "pointer",
    "validate_assessment",
    "validate_assessment_against_pack",
    "validate_pack",
]
