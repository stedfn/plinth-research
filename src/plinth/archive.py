"""The run directory: archived bytes, and the checks that bind a pack to them.

:mod:`plinth.models` decides whether a record is well-formed.
:mod:`plinth.validate` decides whether the records agree with one another. This
module decides whether they agree with **the bytes on disk** -- and, before
that, it is what puts the bytes there.

The point of the commit this module implements is a shift in who authors what:

    before   the model proposes ``sha256``, ``byte_length``, ``retrieved_at``,
             ``filename`` and the whole campaign, and nothing checks any of it
    after    the operator authors them at archive time, they are written to
             ``archive/index.json`` and ``run.json``, and the model may only
             *reference* them -- ``D5``, ``D6`` and ``D7`` reject any deviation

What the model still authors -- locators and observations -- becomes checkable
against archived text by ``D8``-``D11``, and ``D14`` makes that checking
unavoidable: a locator an observation leans on must carry a quote to check.

What this layer proves, and what it does not::

    proves     every artifact the pack declares exists, and its bytes hash and
               measure as declared
               every quote an observation leans on really occurs in that
               artifact's archived text

    claims not that a quote sits on the page a locator names
               that operator-typed metadata (retrieved_at, page_count,
               media_type) is true
               that a failed or blocked acquisition ever happened
               that the bytes are what a server actually served

Layout of one run::

    runs/<run_id>/
    ├── run.json                                    pre-registered Campaign + catalogue pin
    ├── archive/
    │   ├── index.json                              append-only Acquisition + Artifact records
    │   └── blobs/
    │       ├── <sha256>.pdf                        raw bytes, mode 0444
    │       ├── <text_sha256>.txt                   text rendering, always .txt, 0444
    │       └── .tmp-XXXXXX                         in-flight only
    ├── proposed-documentary-evidence.json          model output; never overwritten here
    ├── proposed-documentary-evidence.issues.json   written on rejection
    └── documentary-evidence.json                   accepted; bytes == canonical_bytes(pack)

**Two content-addressed blobs per document, and plinth never runs an extraction
tool.** :attr:`~plinth.models.Locator.char_start` indexes *text*; an artifact is
*bytes*, usually a PDF. Rather than shell out to ``pdftotext`` -- a non-Python
runtime dependency absent from CI, whose output is version-sensitive, so that
verification would be machine-dependent, the exact failure
:func:`~plinth.models.canonical_bytes` exists to prevent -- the operator
supplies the text rendering and plinth archives it beside the raw bytes.

**The reproducibility anchor is the text blob, not the tool string.**
``text_extraction_tool`` is unverifiable provenance recorded verbatim; plinth
asserts nothing whatsoever about it. The digest is what binds the text.

One exception, because a decode is not an extraction: for the media types in
:data:`DECODABLE_MEDIA_TYPES` plinth writes the raw bytes as the text blob and
records a tool string saying exactly that, which a stdlib verifier can
reproduce. ``text/html`` is deliberately absent -- markup is not rendered text,
and a quote from the visible page would never match tags.

**``pdf_page`` and text offsets have no relation, and nothing here builds one.**
A page number indexes the raw PDF; a character offset indexes the text blob. A
``quoted_text`` on a ``pdf_page`` locator is matched against the *whole* text
blob, which proves the quote came from this document and not that it sits on
that page. Stated as a limit rather than papered over.
"""

from __future__ import annotations

import codecs
import hashlib
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypeVar
from urllib.parse import unquote, urlsplit, urlunsplit

from pydantic import ValidationError

from . import catalogue as cat
from .models import (
    ARTIFACT_FILENAME_RE,
    RECORD_ID_RE,
    Acquisition,
    Artifact,
    Campaign,
    EvidencePack,
    Issue,
    Locator,
    PlinthModel,
    Sha256,
    UtcMoment,
    canonical_bytes,
)
from .validate import construct, issue, issues_from, validate_pack
from .vocab import AcquisitionMode, AcquisitionOutcome

ModelT = TypeVar("ModelT", bound=PlinthModel)

RUNS_DIR = cat.PROJECT_ROOT / "runs"
"""Where runs live. Git-ignored: a run is local working state, not a committed artifact."""

MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
"""A module constant, not configuration.

The largest document in this class -- an SEC filing, a technical audit report --
is under 20 MB. An env var or a config key would turn a bound that exists to
stop plinth streaming an accidentally-selected disk image into a knob nobody
reviews, and the right response to a legitimately larger document is a reviewed
edit here.
"""

CHUNK_BYTES = 1024 * 1024

MEDIA_TYPE_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}$"
)
"""RFC 6838 ``type/subtype``, no parameters.

Syntax only. Nothing here sniffs the bytes or checks that a file claiming
``application/pdf`` is one: a guess recorded as a fact is worse than no fact,
and ``media_type`` is on :func:`verify`'s list of things the run *trusts* the
operator for.
"""

DECODABLE_MEDIA_TYPES = frozenset(
    {"text/plain", "text/csv", "text/markdown", "application/json"}
)
"""Media types whose raw bytes *are* their text rendering.

Decoding UTF-8 is not extraction: there is no tool, no version and no layout
heuristic, so a third party reproduces the text blob with the standard library
alone. ``text/html`` is excluded on purpose -- see the module docstring.
"""

RAW_DECODE_TOOL = "plinth: raw bytes decoded as UTF-8"

TEXT_BLOB_SUFFIX = ".txt"

BLOB_EXTENSION_RE = re.compile(r"^\.[a-z0-9]{1,8}$")

TMP_PREFIX = ".tmp-"

REDACTED_QUERY_PARAMS = frozenset({"apikey", "api_key", "key", "token", "access_token"})
"""Query parameter names whose *values* are redacted before a URL is recorded.

Broader than :data:`plinth.validate.CREDENTIAL_QUERY_PARAMS`, on purpose. This
list redacts a URL plinth authors from an operator's flag, where a false
positive costs one unreadable character run; that one *rejects* a URL the model
authored, where a false positive stops work. Bare ``key`` and ``token`` are
cheap to over-redact here and too common to refuse there.

There is deliberately **no shape-based path-segment redaction**. Tested against
real documentary URLs a "looks like a secret" heuristic is backwards: it hides
``ondo-20231231.htm`` and ``OUSG_Prospectus_2024.pdf`` -- exactly the provenance
the URL exists to record -- while keeping the all-digit CIK it was meant to
protect. This module has no HTTP client and no API acquisition modes, so a
``/v2/<KEY>``-style path secret cannot arise here; the heuristic returns, with
its own tests, when ``api``/``rpc`` modes do.

Recorded hole: :attr:`~plinth.models.Source.url` is authored in the pack by the
model and is not redacted by anything.
"""

RUN_MANIFEST_NAME = "run.json"
ARCHIVE_DIR_NAME = "archive"
INDEX_NAME = "index.json"
BLOBS_DIR_NAME = "blobs"
PROPOSED_PACK_NAME = "proposed-documentary-evidence.json"
ACCEPTED_PACK_NAME = "documentary-evidence.json"


class ArchiveError(Exception):
    """The operator's side of the run is wrong: a bad path, a collision, a broken run.

    Mirrors :class:`plinth.catalogue.BuildError`. Deliberately *not* an
    :class:`~plinth.models.Issue`: an issue addresses the untrusted party and
    carries a pointer into a document it emitted, whereas everything raised here
    is a mistake by the operator or the environment, with no document to point
    into.
    """


# --------------------------------------------------------------------------
# run-local models
# --------------------------------------------------------------------------
#
# These live here rather than in `models.py`, whose docstring scopes it to the
# two canonical artifacts. A run manifest and an archive index are local working
# state: nothing downstream re-verifies them, and no digest pins them.


class RunManifest(PlinthModel):
    """``run.json`` -- what the run declared before it did anything.

    Holding the **entire** :class:`~plinth.models.Campaign` is the load-bearing
    choice. Framework section 2.5 says a campaign declares its evidence-access
    paths before attempting them; storing the declaration here makes that
    structural rather than aspirational, and it stops the extraction model
    inventing ``cutoff``, ``declared_scope_note`` or ``bounded_public_evidence``
    after the fact -- ``D5`` rejects any campaign that is not this one.

    ``catalogue_sha256`` pins which 63-check catalogue the run was opened
    against, so a framework edit mid-run is visible rather than silent.
    """

    schema_version: Literal["plinth.run/1"]
    campaign: Campaign
    catalogue_sha256: Sha256
    created_at: UtcMoment


class ArchiveIndex(PlinthModel):
    """``archive/index.json`` -- the operator-authored record of what was fetched.

    **Threat model, stated so nobody later mistakes this for a tamper-evident
    log.** ``D6`` and ``D7`` make this file authoritative over the pack, and
    nothing makes the file itself tamper-evident: a hand edit propagates
    straight into an accepted pack. That is deliberate. The untrusted party in
    this system is the language model; the operator already controls the blobs,
    the run directory and the repository, so hash-chaining the index would
    defend against the one party there is no reason to defend against.

    Append-only by convention, not by enforcement -- there is no ``archive
    amend`` and no locking, so two concurrent ``archive add`` processes lose an
    entry. This is a single-operator local tool.
    """

    schema_version: Literal["plinth.archive/1"]
    acquisitions: tuple[Acquisition, ...] = ()
    artifacts: tuple[Artifact, ...] = ()


@dataclass(frozen=True)
class LoadedRun:
    """A run directory that parsed: its manifest, its index, and where it lives."""

    root: Path
    manifest: RunManifest
    index: ArchiveIndex

    @property
    def blobs_dir(self) -> Path:
        return self.root / ARCHIVE_DIR_NAME / BLOBS_DIR_NAME

    @property
    def index_path(self) -> Path:
        return self.root / ARCHIVE_DIR_NAME / INDEX_NAME

    @property
    def proposed_pack_path(self) -> Path:
        return self.root / PROPOSED_PACK_NAME

    @property
    def accepted_pack_path(self) -> Path:
        return self.root / ACCEPTED_PACK_NAME


# --------------------------------------------------------------------------
# writing
# --------------------------------------------------------------------------


def write_atomic(path: Path, payload: bytes, *, mode: int = 0o444) -> None:
    """Write ``payload`` to ``path`` so that no reader ever sees a partial file.

    ``mkstemp`` in the *target directory* so that :func:`os.replace` is a rename
    within one filesystem and therefore atomic; a temporary file in ``/tmp``
    would make the final step a copy, which is exactly the non-atomic write this
    exists to avoid.

    ``fsync`` on the file before the rename, so a crash cannot leave the
    directory entry pointing at unflushed content, and ``fsync`` on the parent
    directory after it, so the rename itself survives. Without the second one
    the file's *contents* are durable while the name pointing at them is not,
    which on a crash leaves the old name or no name at all -- durability of the
    bytes alone is not durability of the write.

    ``0444`` on every file this writes, canonical artifacts and diagnostics
    alike. Read-only is not a security boundary -- the operator owns the
    directory -- it is a speed bump against hand-editing an archived blob or an
    accepted pack. Replacing and deleting still work, because both need write
    permission on the *directory*, not on the file.
    """
    directory = path.parent
    try:
        handle_fd, tmp_name = tempfile.mkstemp(dir=directory, prefix=TMP_PREFIX)
    except OSError as exc:
        raise ArchiveError(f"cannot write {path}: {exc}") from exc
    tmp = Path(tmp_name)
    try:
        with os.fdopen(handle_fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
        _fsync_directory(directory)
    except OSError as exc:
        raise ArchiveError(f"cannot write {path}: {exc}") from exc
    finally:
        tmp.unlink(missing_ok=True)


def _fsync_directory(directory: Path) -> None:
    """Flush a directory entry, so a completed rename survives a crash."""
    handle_fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(handle_fd)
    finally:
        os.close(handle_fd)


def _load_model(path: Path, model: type[ModelT], label: str) -> ModelT:
    """Read one run-local JSON file into its model, or raise :class:`ArchiveError`.

    The run directory is operator-controlled, so a malformed file here is a
    broken environment rather than an untrusted party's mistake -- an exception
    with every reason listed, not an issue tuple a caller might forward to a
    re-prompt.
    """
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ArchiveError(f"cannot read {label} at {path}: {exc}") from exc

    loaded, problems = construct(model, raw)
    if loaded is None:
        detail = "\n".join(f"  {problem.render()}" for problem in problems)
        raise ArchiveError(f"{label} at {path} is not valid:\n{detail}")
    return loaded


# --------------------------------------------------------------------------
# URL redaction
# --------------------------------------------------------------------------


def redact_url(url: str) -> str:
    """Drop userinfo and the fragment; redact the values of known secret parameters.

    Everything else survives byte for byte. Non-secret query pairs are copied
    verbatim rather than re-encoded, because re-encoding would silently rewrite
    a URL that had no secret in it at all, and the URL is provenance.

    The parameter name is unquoted before comparison, so ``%6Bey=`` cannot slip
    a secret past the list.
    """
    try:
        parts = urlsplit(url)
    except ValueError as exc:
        raise ArchiveError(f"--url is not a parseable URL: {exc}") from exc
    # Userinfo is everything before the last "@"; rpartition leaves the whole
    # netloc untouched when there is none.
    netloc = parts.netloc.rpartition("@")[2]
    return urlunsplit((parts.scheme, netloc, parts.path, _redact_query(parts.query), ""))


def _redact_query(query: str) -> str:
    if not query:
        return ""
    redacted = []
    for pair in query.split("&"):
        name, separator, _ = pair.partition("=")
        if separator and unquote(name).strip().lower() in REDACTED_QUERY_PARAMS:
            redacted.append(f"{name}=REDACTED")
        else:
            redacted.append(pair)
    return "&".join(redacted)


# --------------------------------------------------------------------------
# run creation
# --------------------------------------------------------------------------


def run_directory(run_id: str, runs_root: Path = RUNS_DIR) -> Path:
    """``runs_root/<run_id>``, with the id checked rather than assumed.

    The shape is :data:`~plinth.models.RecordId`'s: an alphanumeric first
    character and no separator, which makes ``..``, ``/etc`` and
    ``../../escaped`` all unrepresentable. This used to be documented as a
    precondition on the caller, which is the same as not enforcing it -- the CLI
    hands over whatever the operator typed. Misrouting a path is an
    operator-facing failure rather than a model exploit, since no model supplies
    a run id, but a precondition nothing checks is not a guarantee.
    """
    if not RECORD_ID_RE.match(run_id):
        raise ArchiveError(
            f"run id {run_id!r} is not a valid identifier: it must start with a letter "
            "or digit and contain only letters, digits, '.', '-' and '_'"
        )
    return runs_root / run_id


def create_run(
    campaign: Campaign,
    *,
    runs_root: Path = RUNS_DIR,
    catalogue_path: Path = cat.CATALOGUE_PATH,
    created_at: datetime | None = None,
) -> LoadedRun:
    """Pre-register a campaign and open an empty archive for it.

    Refuses an existing run rather than merging into it: a second ``run new``
    would otherwise silently replace the declaration that ``D5`` checks every
    later pack against, which is the one file in the run that is supposed to
    predate everything.

    **Not a transaction.** Each write is individually atomic and durable; the
    pair is not. The index is published before the manifest deliberately, so
    that the file whose presence *means* "this run exists" is the last one to
    appear: a crash in between leaves a directory with no ``run.json``, which
    :func:`load_run` reports as no run at all rather than as a run with a
    missing archive.
    """
    root = run_directory(campaign.run_id, runs_root)
    manifest_path = root / RUN_MANIFEST_NAME
    if manifest_path.exists():
        raise ArchiveError(
            f"run {campaign.run_id!r} already exists at {root}; "
            f"{RUN_MANIFEST_NAME} is unchanged"
        )

    try:
        catalogue_bytes = catalogue_path.read_bytes()
    except OSError as exc:
        raise ArchiveError(
            f"cannot read the catalogue at {catalogue_path}: {exc}. "
            "Run: plinth catalogue build"
        ) from exc

    manifest = RunManifest(
        schema_version="plinth.run/1",
        campaign=campaign,
        catalogue_sha256=hashlib.sha256(catalogue_bytes).hexdigest(),
        created_at=created_at or datetime.now(UTC),
    )
    index = ArchiveIndex(schema_version="plinth.archive/1")

    try:
        (root / ARCHIVE_DIR_NAME / BLOBS_DIR_NAME).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ArchiveError(f"cannot create {root}: {exc}") from exc

    write_atomic(root / ARCHIVE_DIR_NAME / INDEX_NAME, canonical_bytes(index))
    write_atomic(manifest_path, canonical_bytes(manifest))
    return LoadedRun(root=root, manifest=manifest, index=index)


def load_run(root: Path) -> LoadedRun:
    """Read ``run.json`` and ``archive/index.json``, or say why the run is unusable."""
    manifest_path = root / RUN_MANIFEST_NAME
    if not manifest_path.exists():
        raise ArchiveError(f"no run at {root}: {RUN_MANIFEST_NAME} does not exist")
    manifest = _load_model(manifest_path, RunManifest, "run manifest")
    index = _load_model(root / ARCHIVE_DIR_NAME / INDEX_NAME, ArchiveIndex, "archive index")
    return LoadedRun(root=root, manifest=manifest, index=index)


# --------------------------------------------------------------------------
# archiving bytes
# --------------------------------------------------------------------------


def _regular_file(source: Path, *, max_bytes: int, label: str) -> tuple[Path, int]:
    """The ordered safety checks, before anything opens the file.

    Order is the point. ``resolve(strict=True)`` first, so a broken symlink is a
    named error rather than a confusing read failure. Then ``S_ISREG``: the FIFO
    is the dangerous case, because opening one blocks forever and no size check
    would ever run. Then emptiness -- ``byte_length`` is a
    :data:`~plinth.models.PositiveCount`, so a zero-byte file could not be
    recorded even if it were archived. Then the size bound, **before opening**,
    so an oversized file is never streamed at all.

    A symlink *to a regular file* is accepted, and what gets archived is the
    target's bytes. The operator chose the path; following it is the behaviour
    every other tool has.
    """
    try:
        resolved = source.resolve(strict=True)
    except OSError as exc:
        raise ArchiveError(f"{label} {source}: {exc}") from exc
    try:
        info = resolved.stat()
    except OSError as exc:
        raise ArchiveError(f"{label} {source}: {exc}") from exc
    if stat.S_ISDIR(info.st_mode):
        raise ArchiveError(f"{label} {source} is a directory")
    if not stat.S_ISREG(info.st_mode):
        raise ArchiveError(
            f"{label} {source} is not a regular file; plinth archives files, and "
            "reading a device or a FIFO would block or never terminate"
        )
    if info.st_size == 0:
        raise ArchiveError(f"{label} {source} is empty; there is nothing to archive")
    if info.st_size > max_bytes:
        raise ArchiveError(
            f"{label} {source} is {info.st_size} bytes, over the {max_bytes}-byte limit"
        )
    return resolved, info.st_size


def _archive_blob(
    source: Path,
    blobs_dir: Path,
    *,
    extension: str,
    max_bytes: int,
    require_utf8: bool,
    label: str,
) -> tuple[str, int]:
    """Stream one file into a content-addressed blob. Returns ``(sha256, byte_length)``.

    The bytes are never imported, never executed and never sniffed: they are
    hashed and copied, and a UTF-8 decode is attempted only when the caller says
    this file is a text rendering.

    **If the destination already exists it is re-hashed.** Equal means this is
    the same document arriving a second time: succeed idempotently and reuse the
    blob, which is what makes two acquisitions of identical bytes share one
    artifact. Unequal means an archived blob has been corrupted or replaced, and
    that is a hard failure that writes nothing -- overwriting it would destroy
    the evidence that something went wrong.

    The temporary file is removed in ``finally``, so an interrupted write leaves
    neither a blob nor a ``.tmp-`` behind.
    """
    resolved, expected_size = _regular_file(source, max_bytes=max_bytes, label=label)
    decoder = codecs.getincrementaldecoder("utf-8")() if require_utf8 else None
    try:
        with open(resolved, "rb") as reader:
            handle_fd, tmp_name = tempfile.mkstemp(dir=blobs_dir, prefix=TMP_PREFIX)
            tmp = Path(tmp_name)
            try:
                digest = hashlib.sha256()
                written = 0
                with os.fdopen(handle_fd, "wb") as writer:
                    while chunk := reader.read(CHUNK_BYTES):
                        written += len(chunk)
                        if written > max_bytes:
                            raise ArchiveError(
                                f"{label} {source} grew past the {max_bytes}-byte limit "
                                "while it was being archived"
                            )
                        digest.update(chunk)
                        if decoder is not None:
                            _decode(decoder, chunk, source, label)
                        writer.write(chunk)
                    if decoder is not None:
                        _decode(decoder, b"", source, label, final=True)
                    writer.flush()
                    os.fsync(writer.fileno())

                if written != expected_size:
                    raise ArchiveError(
                        f"{label} {source} changed size while it was being archived "
                        f"({expected_size} bytes when checked, {written} when read)"
                    )

                sha256 = digest.hexdigest()
                destination = blobs_dir / f"{sha256}{extension}"
                if destination.exists():
                    existing, _ = _digest_file(destination)
                    if existing != sha256:
                        raise ArchiveError(
                            f"{destination} already exists and hashes to {existing}, "
                            f"not {sha256}; refusing to overwrite an archived blob"
                        )
                    return sha256, written
                os.chmod(tmp, 0o444)
                os.replace(tmp, destination)
                return sha256, written
            finally:
                tmp.unlink(missing_ok=True)
    except OSError as exc:
        raise ArchiveError(f"cannot archive {label} {source}: {exc}") from exc


def _decode(decoder, chunk: bytes, source: Path, label: str, *, final: bool = False) -> None:
    try:
        decoder.decode(chunk, final)
    except UnicodeDecodeError as exc:
        raise ArchiveError(
            f"{label} {source} is not valid UTF-8 ({exc}); a text rendering must "
            "decode, because locator offsets index characters"
        ) from None


def _digest_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    length = 0
    with open(path, "rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            digest.update(chunk)
            length += len(chunk)
    return digest.hexdigest(), length


def blob_extension(name: str) -> str:
    """The archived extension for an original filename, or ``""``.

    Rebuilt from the original name and constrained to
    ``AR2``'s alphabet, so an operator-supplied ``.tar.gz`` or ``.PDF`` becomes
    ``.gz`` / ``.pdf`` and anything else becomes no extension at all. The
    extension is a convenience for a human opening the directory; nothing reads
    it back as a fact.
    """
    suffix = Path(name).suffix.lower()
    return suffix if BLOB_EXTENSION_RE.match(suffix) else ""


def next_acquisition_id(index: ArchiveIndex, source_id: str) -> str:
    """``acq-<source_id>-NNN``, first number not already used.

    Generated rather than taken from the operator: the id is a join key with no
    meaning of its own, and one typo in a hand-typed id is a silently
    disconnected acquisition.
    """
    used = {acquisition.acquisition_id for acquisition in index.acquisitions}
    number = 1
    while (candidate := f"acq-{source_id}-{number:03d}") in used:
        number += 1
    return candidate


ARCHIVING_LOCAL_ARTIFACT_FIELDS = frozenset({"archived_at", "original_filename", "filename"})
"""Artifact fields that describe *this* archiving, not the document.

The same bytes legitimately arrive twice from two paths at two times, so these
three differ without disagreeing about anything. The first archiving's values
stand: its blob is the one on disk under that filename, and its timestamp is
when the bytes actually entered the archive.
"""


def reconcile_artifact(stored: Artifact, incoming: Artifact) -> Artifact:
    """Merge a re-archived record into the one already in the index, or refuse.

    Content addressing means a second ``archive add`` of identical bytes finds
    an existing artifact record. Keeping the stored record unconditionally --
    which is what this used to do -- silently discards whatever the new call
    knew: archiving a document, then re-archiving it **with** ``--text``, exited
    0 and left ``text_sha256`` null, with no recovery path and no diagnostic.
    ``D11``'s own error message tells the operator to archive a text rendering,
    which did nothing.

    Three cases, and no new flag:

    ======================  =========================  ==========================
    stored                  this call                  result
    ======================  =========================  ==========================
    field is ``None``       supplies a value           **upgraded** -- strictly
                                                       more is known, nothing is
                                                       lost
    any value               says nothing (``None``)    kept -- omitting a flag
                                                       asserts nothing
    a value                 a *different* value        **refused**, naming both
    ======================  =========================  ==========================

    Refusing the third case rather than keeping the first is the point: the same
    bytes cannot be both ``application/pdf`` and ``text/plain``, and two
    different text renderings of one document are two different claims about
    what it says. One of them is wrong and plinth cannot tell which, so it
    records neither silently.
    """
    updates: dict[str, object] = {}
    conflicts: list[str] = []
    for field in type(stored).model_fields:
        if field in ARCHIVING_LOCAL_ARTIFACT_FIELDS:
            continue
        archived, offered = getattr(stored, field), getattr(incoming, field)
        if archived == offered or offered is None:
            continue
        if archived is None:
            updates[field] = offered
        else:
            conflicts.append(f"{field}: archived as {archived}, this call says {offered}")

    if conflicts:
        raise ArchiveError(
            f"artifact {stored.sha256} is already archived with different metadata, and "
            "plinth cannot tell which is right:\n"
            + "\n".join(f"  {line}" for line in conflicts)
        )
    if not updates:
        return stored

    # Rebuilt through the model rather than `model_copy`, so AR1 and AR2 run on
    # the merged record: an upgrade that produced a text digest with no tool
    # would otherwise be written straight into the index unvalidated.
    data = stored.model_dump()
    data.update(updates)
    try:
        return Artifact(**data)
    except ValidationError as exc:
        detail = "\n".join(f"  {problem.render()}" for problem in issues_from(exc))
        raise ArchiveError(
            f"artifact {stored.sha256} could not be updated:\n{detail}"
        ) from None


PREFLIGHT_DIGEST = "0" * 64
"""A stand-in digest, so every predictable rule can run before the blob is written.

Not a magic value anything stores: the records built with it are thrown away.
Its only job is to satisfy :data:`~plinth.models.Sha256` and ``AR2`` while the
fields that are *not* yet known -- the real digest and the real length -- are
the only ones a preflight cannot check.
"""


def _compose_records(
    *,
    acquisition_id: str,
    source_id: str,
    acquisition_mode: AcquisitionMode,
    retrieved_at: str | datetime,
    attempted_at: str | datetime | None,
    request_detail: str | None,
    operator: str | None,
    media_type: str,
    original_filename: str,
    page_count: int | None,
    extraction_tool: str | None,
    sha256: str,
    byte_length: int,
    extension: str,
    text_sha256: str | None,
    archived_at: datetime,
) -> tuple[Acquisition, Artifact]:
    """Build both records, or raise :class:`ArchiveError` naming every rule they break.

    Called **twice** by :func:`add_artifact`: once with
    :data:`PREFLIGHT_DIGEST` before anything touches the archive, and once with
    the real digest afterwards. That is deliberately not a second copy of the
    validation rules -- a preflight that restated ``A2``, ``A4``, ``AR1`` and
    the field types would be a second definition of "valid" free to drift from
    the models, which are the only authority on it. Running the real
    constructors against a stand-in digest reuses that authority exactly.
    """
    try:
        return (
            Acquisition(
                acquisition_id=acquisition_id,
                source_id=source_id,
                acquisition_mode=acquisition_mode,
                outcome=AcquisitionOutcome.ACQUIRED,
                attempted_at=attempted_at if attempted_at is not None else retrieved_at,
                retrieved_at=retrieved_at,
                artifact_sha256=sha256,
                request_detail=request_detail,
                operator=operator,
            ),
            Artifact(
                sha256=sha256,
                media_type=media_type,
                byte_length=byte_length,
                filename=f"{sha256}{extension}",
                original_filename=original_filename,
                page_count=page_count,
                text_extraction_tool=extraction_tool,
                text_sha256=text_sha256,
                archived_at=archived_at,
            ),
        )
    except ValidationError as exc:
        detail = "\n".join(f"  {problem.render()}" for problem in issues_from(exc))
        raise ArchiveError(f"the acquisition could not be recorded:\n{detail}") from None


def add_artifact(
    run: LoadedRun,
    source_path: Path,
    *,
    source_id: str,
    acquisition_mode: AcquisitionMode,
    media_type: str,
    retrieved_at: str | datetime,
    attempted_at: str | datetime | None = None,
    url: str | None = None,
    operator: str | None = None,
    text_path: Path | None = None,
    text_tool: str | None = None,
    page_count: int | None = None,
    max_bytes: int = MAX_ARTIFACT_BYTES,
) -> tuple[LoadedRun, Acquisition, Artifact]:
    """Archive one file and record the :class:`Acquisition` and :class:`Artifact` for it.

    Emits both records and **no** :class:`~plinth.models.Source`. Title, author,
    research posture and stated limitations are research judgment about a
    document, not facts about a fetch, and inventing them here would put the
    trusted party's name on a guess.

    The outcome is always ``ACQUIRED``: this command has bytes in hand. Blocked
    and failed attempts have no command yet, which is a recorded hole -- a
    fabricated *failed* acquisition is undetectable, though ``P4`` stops one
    supporting any evidence, so the worst case is a fabricated limitation.

    **The index is re-read from disk here, not taken from the caller's
    ``LoadedRun``.** Atomic file replacement makes each write all-or-nothing; it
    does not make read-modify-write atomic. A caller holding one ``LoadedRun``
    across two calls used to build the second index from the first snapshot and
    silently drop an entry -- no concurrency required, four adds landing three.
    Returns the run rebuilt around the new index so the caller's copy is current
    either way.

    **This does not make the index race-safe.** Two concurrent processes still
    interleave read and write and still lose an entry; locking stays deferred,
    and this is a single-operator local tool. What is fixed is the
    single-process loss, which was never safe and read as though it were.

    **Everything predictable is checked before anything touches the archive.**
    The mode, the media type, the flag pairings, the URL, the timestamp grammar
    and both records' own rules all run first, against
    :data:`PREFLIGHT_DIGEST`, because a model-construction failure after the
    write left an orphan blob for a mistake as ordinary as a mistyped
    ``--retrieved-at``.

    What cannot be checked first is the digest and the length, which is why the
    blob is still written before the index entry. A text rendering rejected
    after the raw bytes have landed therefore still leaves an orphan blob --
    harmless, because it is content-addressed: ``D12`` reads it as correctly
    named, nothing references it, and re-running the command reuses it rather
    than writing a second copy.
    """
    # ---- everything predictable, before anything touches the archive --------
    try:
        acquisition_mode = AcquisitionMode(acquisition_mode)
    except ValueError:
        raise ArchiveError(
            f"--mode {acquisition_mode!r} is not an acquisition mode; legal values are "
            + ", ".join(str(mode) for mode in AcquisitionMode)
        ) from None
    if not MEDIA_TYPE_RE.match(media_type):
        raise ArchiveError(
            f"--media-type {media_type!r} is not a type/subtype pair, e.g. application/pdf"
        )
    if (text_path is None) != (text_tool is None):
        raise ArchiveError(
            "--text and --text-tool must be given together: a text blob with no named "
            "tool cannot be reproduced, and a named tool with no blob records nothing "
            "checkable (AR1)"
        )
    if acquisition_mode is AcquisitionMode.MANUAL_UPLOAD and operator is None:
        raise ArchiveError(
            "--operator is required for MANUAL_UPLOAD: a hand-placed artifact needs a "
            "human in its provenance chain (A4)"
        )

    blobs_dir = run.blobs_dir
    if not blobs_dir.is_dir():
        raise ArchiveError(f"no archive at {blobs_dir}; the run directory is incomplete")
    if run.accepted_pack_path.exists():
        raise ArchiveError(
            f"{ACCEPTED_PACK_NAME} has already been accepted for this run, and adding "
            "an acquisition would make it fail D7; evidence acquired after acceptance "
            "belongs to a new run"
        )

    extension = blob_extension(source_path.name)
    # Redaction ahead of the write too: `redact_url` refuses an unparseable URL,
    # and it did so after the bytes had landed.
    request_detail = redact_url(url) if url is not None else None
    # A throwaway pair, built only so that every rule the models know -- the
    # timestamp grammar, `A2`, `A4`, `AR1`, `page_count > 0`, the id shapes --
    # fails here rather than after an orphan blob is already on disk.
    _compose_records(
        acquisition_id="acq-preflight",
        source_id=source_id,
        acquisition_mode=acquisition_mode,
        retrieved_at=retrieved_at,
        attempted_at=attempted_at,
        request_detail=request_detail,
        operator=operator,
        media_type=media_type,
        original_filename=source_path.name,
        page_count=page_count,
        # AR1 wants the pair, and whether a text blob results is already settled
        # by the flag check above; its digest is the only part still unknown.
        extraction_tool=text_tool or (
            RAW_DECODE_TOOL if media_type in DECODABLE_MEDIA_TYPES else None
        ),
        text_sha256=(
            PREFLIGHT_DIGEST
            if text_path is not None or media_type in DECODABLE_MEDIA_TYPES
            else None
        ),
        sha256=PREFLIGHT_DIGEST,
        byte_length=1,
        extension=extension,
        archived_at=datetime.now(UTC),
    )

    sha256, byte_length = _archive_blob(
        source_path,
        blobs_dir,
        extension=extension,
        max_bytes=max_bytes,
        require_utf8=False,
        label="artifact",
    )

    text_sha256: str | None = None
    extraction_tool: str | None = None
    if text_path is not None:
        text_sha256, _ = _archive_blob(
            text_path,
            blobs_dir,
            extension=TEXT_BLOB_SUFFIX,
            max_bytes=max_bytes,
            require_utf8=True,
            label="text rendering",
        )
        extraction_tool = text_tool
    elif media_type in DECODABLE_MEDIA_TYPES:
        # Archived from the **blob**, never a second read of `source_path`. The
        # tool string claims this text is a decode of the archived bytes, and
        # re-reading the source would make that claim false the moment the file
        # changed between the two reads -- the digest would bind one document
        # while every locator resolved against another.
        #
        # When the artifact's own extension is already `.txt` the destination is
        # the source, and the re-hash branch in `_archive_blob` makes that a
        # no-op rather than a clash.
        text_sha256, _ = _archive_blob(
            blobs_dir / f"{sha256}{extension}",
            blobs_dir,
            extension=TEXT_BLOB_SUFFIX,
            max_bytes=max_bytes,
            require_utf8=True,
            label="text rendering",
        )
        extraction_tool = RAW_DECODE_TOOL

    current = load_run(run.root)
    acquisition, artifact = _compose_records(
        acquisition_id=next_acquisition_id(current.index, source_id),
        source_id=source_id,
        acquisition_mode=acquisition_mode,
        retrieved_at=retrieved_at,
        attempted_at=attempted_at,
        request_detail=request_detail,
        operator=operator,
        media_type=media_type,
        original_filename=source_path.name,
        page_count=page_count,
        extraction_tool=extraction_tool,
        sha256=sha256,
        byte_length=byte_length,
        extension=extension,
        text_sha256=text_sha256,
        archived_at=datetime.now(UTC),
    )

    # Identical bytes from two sources are one artifact and two acquisitions.
    stored = next(
        (record for record in current.index.artifacts if record.sha256 == sha256), None
    )
    if stored is None:
        recorded = artifact
        artifacts = (*current.index.artifacts, artifact)
    else:
        recorded = reconcile_artifact(stored, artifact)
        artifacts = tuple(
            recorded if record.sha256 == sha256 else record
            for record in current.index.artifacts
        )

    index = ArchiveIndex(
        schema_version="plinth.archive/1",
        acquisitions=(*current.index.acquisitions, acquisition),
        artifacts=artifacts,
    )
    write_atomic(current.index_path, canonical_bytes(index))
    reloaded = LoadedRun(root=current.root, manifest=current.manifest, index=index)
    return reloaded, acquisition, recorded


# --------------------------------------------------------------------------
# text matching
# --------------------------------------------------------------------------


def collapse_whitespace(text: str) -> str:
    """``" ".join(text.split())`` -- the one normalization applied before matching.

    Line wrapping is an artifact of extraction rather than of the document, and
    ``str.split()`` also folds the no-break spaces a PDF emits constantly.

    **Nothing else is erased.** No case folding, no smart-quote unification, no
    ligature expansion, no hyphen repair. Each would let a materially different
    quote pass as a match, and each is a policy a third-party verifier would
    have to reproduce exactly to get the same answer.
    """
    return " ".join(text.split())


# --------------------------------------------------------------------------
# reading blobs
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Blob:
    """One archived file, read exactly once.

    ``error`` means the bytes could not be obtained at all -- absent, not a
    regular file, unreadable. ``decode_error`` means they were obtained and are
    not UTF-8 text, which is the *normal* state of a PDF and only a failure for
    a blob something claims is a text rendering. Keeping the two apart is what
    lets ``D2`` pass on a PDF while ``D4`` rejects a text blob that stopped
    decoding.
    """

    name: str
    sha256: str | None = None
    byte_length: int | None = None
    text: str | None = None
    error: str | None = None
    decode_error: str | None = None


class BlobStore:
    """Cached reads of one run's ``blobs/`` directory.

    Cached for two reasons, and the second is a correctness requirement rather
    than a speed one:

    * the D rules walk the same blob from several directions -- ``D1``-``D3``
      per artifact, then ``D9``-``D10`` once per locator into it -- and
      re-hashing a 20 MB PDF per locator would make verification quadratic in
      the size of the evidence;
    * **one read per blob, hashed and decoded from the same bytes.** Two reads
      of one path can straddle a change and report the old digest beside the new
      text, which would let a tampered document pass ``D2`` while a locator
      resolved against content that never hashed to anything.
    """

    def __init__(self, blobs_dir: Path) -> None:
        self.blobs_dir = blobs_dir
        self._blobs: dict[str, Blob] = {}

    def read(self, name: str) -> Blob:
        if name not in self._blobs:
            self._blobs[name] = self._read_once(name)
        return self._blobs[name]

    def _read_once(self, name: str) -> Blob:
        """Hash, measure and (for a text blob) decode, from one pass over the file.

        ``lstat`` and ``S_ISREG`` **before** opening, mirroring the writer's own
        ordered check and for the same reason: reading a FIFO blocks forever, so
        a verification run would hang rather than fail. A symlink is refused
        outright rather than followed -- plinth writes every blob itself and
        never writes a link, so one appearing here is either a mistake or an
        attempt to make the archive resolve outside itself.

        The decoded text is kept only for ``.txt`` names. Every text rendering
        is archived under that suffix by construction, and keeping a decoded
        copy of every artifact would hold the whole archive in memory to answer
        a question no rule asks.
        """
        path = self.blobs_dir / name
        try:
            info = os.lstat(path)
        except FileNotFoundError:
            return Blob(name=name, error="does not exist")
        except OSError as exc:
            return Blob(name=name, error=f"cannot be read: {exc}")
        if stat.S_ISLNK(info.st_mode):
            return Blob(
                name=name,
                error="is a symlink; the archive holds bytes, and following a link "
                "would resolve outside it",
            )
        if not stat.S_ISREG(info.st_mode):
            return Blob(name=name, error="is not a regular file")

        wants_text = name.endswith(TEXT_BLOB_SUFFIX)
        digest = hashlib.sha256()
        length = 0
        decoder = codecs.getincrementaldecoder("utf-8")() if wants_text else None
        pieces: list[str] = []
        decode_error: str | None = None
        try:
            with open(path, "rb") as handle:
                while chunk := handle.read(CHUNK_BYTES):
                    digest.update(chunk)
                    length += len(chunk)
                    if decoder is not None and decode_error is None:
                        try:
                            pieces.append(decoder.decode(chunk))
                        except UnicodeDecodeError as exc:
                            decode_error = f"is not valid UTF-8: {exc}"
                if decoder is not None and decode_error is None:
                    try:
                        pieces.append(decoder.decode(b"", True))
                    except UnicodeDecodeError as exc:
                        decode_error = f"is not valid UTF-8: {exc}"
        except OSError as exc:
            return Blob(name=name, error=f"cannot be read: {exc}")

        return Blob(
            name=name,
            sha256=digest.hexdigest(),
            byte_length=length,
            text=None if decode_error is not None or not wants_text else "".join(pieces),
            decode_error=decode_error,
        )

    def names(self) -> tuple[str, ...]:
        """Every entry directly in ``blobs/``, sorted, unfiltered.

        Unfiltered on purpose: a subdirectory or a symlink in here is itself
        something ``D12`` should report, and filtering by ``is_file()`` would
        both hide them and follow links to decide.

        Raises :class:`ArchiveError` rather than reading an unlistable archive as
        an empty one -- "no blobs" and "the archive cannot be opened" are
        opposite facts, and the quiet answer is the one that says a tampered run
        is clean.
        """
        try:
            return tuple(sorted(entry.name for entry in self.blobs_dir.iterdir()))
        except OSError as exc:
            raise ArchiveError(f"cannot list {self.blobs_dir}: {exc}") from exc


def blob_name(artifact: Artifact) -> str:
    """``<sha256><extension>``, rebuilt rather than read from ``filename``.

    ``AR2`` guarantees ``filename`` is exactly this string, so rebuilding it
    changes nothing when the record is honest -- and when it is not, the
    filesystem is addressed by a 64-character hex digest and a validated
    extension, never by a submitted path. Traversal is impossible by
    construction, not by escaping.
    """
    return f"{artifact.sha256}{artifact.filename[64:]}"


# --------------------------------------------------------------------------
# the D rules: pack against the run directory it belongs to
# --------------------------------------------------------------------------
#
# `S/A/AR/L/O/R/K/G/CN/AS` are rules about one record; `P` is the pack graph,
# pure; `X` is artifact against artifact. `D` is pack against the run directory.
#
#   D1-D4    an artifact's bytes exist, hash, measure and (for text) decode
#   D5-D7    the pack copies `run.json` and `archive/index.json` rather than
#            authoring them
#   D8-D11   a locator resolves as far as the archived bytes honestly allow
#   D12-D13  run-level integrity, checkable with no pack at all
#   D14      a locator an observation leans on carries a quote to check
#
# They are not model validators and they are not part of `validate_pack`.
# `validate_pack`'s documented contract is that the records agree with one
# another, and all three of its entry points take raw JSON with no path; a
# `root: Path | None` parameter would force every caller to decide, and a `None`
# default would silently downgrade the strongest check in the system to
# optional.


def check_d5_campaign_is_preregistered(pack: EvidencePack, run: LoadedRun) -> tuple[Issue, ...]:
    """D5 -- the pack's campaign is the one the run declared before it started.

    The alternative -- *injecting* the manifest's campaign over whatever the
    model sent -- is rejected. Overwriting erases a model's error instead of
    reporting it, and accept-or-reject is the product.
    """
    declared = run.manifest.campaign
    if canonical_bytes(pack.campaign) == canonical_bytes(declared):
        return ()
    differing = _differing_fields(pack.campaign, declared)
    return (
        issue(
            "D5",
            "campaign differs from the campaign pre-registered in "
            f"{RUN_MANIFEST_NAME}; field(s): {', '.join(differing)}",
            "campaign",
        ),
    )


def _differing_fields(left: PlinthModel, right: PlinthModel) -> tuple[str, ...]:
    """Which top-level fields two records of the same type disagree on.

    Compared on the JSON dump rather than on attributes so that the answer is in
    the vocabulary of the submitted document -- an enum reads as its value and an
    instant as its canonical spelling, which is what a re-prompt needs to see.
    """
    left_fields = left.model_dump(mode="json")
    right_fields = right.model_dump(mode="json")
    return tuple(
        sorted(
            key
            for key in left_fields.keys() | right_fields.keys()
            if left_fields.get(key) != right_fields.get(key)
        )
    )


def check_d6_records_match_the_archive(pack: EvidencePack, run: LoadedRun) -> tuple[Issue, ...]:
    """D6 -- every artifact, and every acquisition the archive knows, is copied exactly.

    With ``D7`` this is the commit's integrity core: it converts "the model
    proposes artifact metadata and we hope" into "the model may only reference".

    Three cases, and the middle one matters most:

    * an acquisition whose id is in the index must be **canonically identical**
      to it whatever its outcome -- checking only ``ACQUIRED`` records would let
      a model relabel an archived acquisition ``FAILED``, invent a
      ``failure_reason`` and drop the evidence it actually had;
    * an ``ACQUIRED`` acquisition absent from the index is a fetch that never
      happened;
    * every artifact must be in the index and identical to it, because
      ``sha256``, ``byte_length``, ``filename`` and ``archived_at`` are all facts
      about an archiving step the model did not perform.
    """
    indexed_acquisitions = {
        record.acquisition_id: record for record in run.index.acquisitions
    }
    indexed_artifacts = {record.sha256: record for record in run.index.artifacts}

    found: list[Issue] = []
    for index, acquisition in enumerate(pack.acquisitions):
        archived = indexed_acquisitions.get(acquisition.acquisition_id)
        if archived is None:
            if acquisition.outcome is AcquisitionOutcome.ACQUIRED:
                found.append(
                    issue(
                        "D6",
                        f"acquisition {acquisition.acquisition_id!r} is ACQUIRED but has no "
                        f"record in {ARCHIVE_DIR_NAME}/{INDEX_NAME}; nothing was archived "
                        "under that id",
                        "acquisitions",
                        index,
                        "acquisition_id",
                    )
                )
            continue
        if canonical_bytes(acquisition) != canonical_bytes(archived):
            found.append(
                issue(
                    "D6",
                    f"acquisition {acquisition.acquisition_id!r} differs from its "
                    f"{ARCHIVE_DIR_NAME}/{INDEX_NAME} record; field(s): "
                    + ", ".join(_differing_fields(acquisition, archived)),
                    "acquisitions",
                    index,
                )
            )

    for index, artifact in enumerate(pack.artifacts):
        archived_artifact = indexed_artifacts.get(artifact.sha256)
        if archived_artifact is None:
            found.append(
                issue(
                    "D6",
                    f"artifact {artifact.sha256} has no record in "
                    f"{ARCHIVE_DIR_NAME}/{INDEX_NAME}; it was never archived",
                    "artifacts",
                    index,
                    "sha256",
                )
            )
            continue
        if canonical_bytes(artifact) != canonical_bytes(archived_artifact):
            found.append(
                issue(
                    "D6",
                    f"artifact {artifact.sha256} differs from its "
                    f"{ARCHIVE_DIR_NAME}/{INDEX_NAME} record; field(s): "
                    + ", ".join(_differing_fields(artifact, archived_artifact)),
                    "artifacts",
                    index,
                )
            )
    return tuple(found)


def check_d7_archive_is_fully_represented(
    pack: EvidencePack, run: LoadedRun
) -> tuple[Issue, ...]:
    """D7 -- nothing archived may be silently dropped from the pack.

    Framework section 2.2 wants intentional exclusions *stated* -- a
    :class:`~plinth.models.Source` with ``disposition = EXCLUDED`` and ``S1``'s
    required reason -- not omitted. Without this rule a model that read an
    inconvenient document could simply not mention it, and the pack would be
    internally perfect while misrepresenting what the campaign had in hand.
    """
    pack_acquisitions = {acquisition.acquisition_id for acquisition in pack.acquisitions}
    pack_artifacts = {artifact.sha256 for artifact in pack.artifacts}

    found: list[Issue] = []
    for record in run.index.acquisitions:
        if record.acquisition_id not in pack_acquisitions:
            found.append(
                issue(
                    "D7",
                    f"{ARCHIVE_DIR_NAME}/{INDEX_NAME} records acquisition "
                    f"{record.acquisition_id!r} of source {record.source_id!r}, which the "
                    "pack does not contain; an excluded source is stated, not omitted",
                    "acquisitions",
                )
            )
    for record in run.index.artifacts:
        if record.sha256 not in pack_artifacts:
            found.append(
                issue(
                    "D7",
                    f"{ARCHIVE_DIR_NAME}/{INDEX_NAME} records artifact {record.sha256} "
                    f"({record.original_filename or record.filename}), which the pack "
                    "does not contain",
                    "artifacts",
                )
            )
    return tuple(found)


def check_d1_d2_d3_artifact_bytes(pack: EvidencePack, blobs: BlobStore) -> tuple[Issue, ...]:
    """D1, D2, D3 -- the blob exists, hashes to its digest, and is the stated length.

    ``D2`` is the rule the whole commit exists for. Before it, an artifact with
    a plausible ``sha256`` and ``byte_length`` validated cleanly while no such
    file existed anywhere, and every guarantee downstream of it rested on
    nothing.

    ``D3`` is not redundant with ``D2``. The digest binds the bytes, but
    ``byte_length`` is a separately-authored number a reader uses to decide
    whether a document is plausible at all, and a record that disagrees with
    itself should not validate.
    """
    found: list[Issue] = []
    for index, artifact in enumerate(pack.artifacts):
        name = blob_name(artifact)
        measured = blobs.read(name)
        if measured.error is not None:
            found.append(
                issue(
                    "D1",
                    f"{BLOBS_DIR_NAME}/{name} {measured.error}; the artifact claims bytes "
                    "the archive does not hold",
                    "artifacts",
                    index,
                    "sha256",
                )
            )
            continue
        if measured.sha256 != artifact.sha256:
            found.append(
                issue(
                    "D2",
                    f"{BLOBS_DIR_NAME}/{name} hashes to {measured.sha256}, not "
                    f"{artifact.sha256}; the archived bytes are not the bytes this "
                    "artifact names",
                    "artifacts",
                    index,
                    "sha256",
                )
            )
        if measured.byte_length != artifact.byte_length:
            found.append(
                issue(
                    "D3",
                    f"{BLOBS_DIR_NAME}/{name} is {measured.byte_length} bytes, not "
                    f"{artifact.byte_length}",
                    "artifacts",
                    index,
                    "byte_length",
                )
            )
    return tuple(found)


def check_d4_text_bytes(pack: EvidencePack, blobs: BlobStore) -> tuple[Issue, ...]:
    """D4 -- a declared text rendering exists, hashes to its digest, and decodes.

    The decode is checked rather than assumed because ``char_start`` and
    ``char_end`` index *characters*: text that does not decode has no character
    positions for a locator to address.
    """
    found: list[Issue] = []
    for index, artifact in enumerate(pack.artifacts):
        if artifact.text_sha256 is None:
            continue
        name = f"{artifact.text_sha256}{TEXT_BLOB_SUFFIX}"
        decoded = blobs.read(name)
        if decoded.error is not None or decoded.decode_error is not None:
            found.append(
                issue(
                    "D4",
                    f"{BLOBS_DIR_NAME}/{name} {decoded.error or decoded.decode_error}",
                    "artifacts",
                    index,
                    "text_sha256",
                )
            )
            continue
        if decoded.sha256 != artifact.text_sha256:
            found.append(
                issue(
                    "D4",
                    f"{BLOBS_DIR_NAME}/{name} hashes to {decoded.sha256}, not "
                    f"{artifact.text_sha256}",
                    "artifacts",
                    index,
                    "text_sha256",
                )
            )
    return tuple(found)


def check_d8_to_d14_locators(pack: EvidencePack, blobs: BlobStore) -> tuple[Issue, ...]:
    """D8-D11 and D14 -- resolve every locator as far as the archived bytes allow.

    What each locator type honestly gets, and what it does not:

    ``pdf_page``          position: ``D8``, against an operator-typed
                          ``page_count`` that nothing counted. Quote: ``D10``,
                          document-wide -- **not** proof the quote is on that
                          page.
    ``text_span``         position: ``D9``, exact offsets. Quote: ``D9`` and
                          ``D10``.
    ``document_section``  position: none. ``D10`` only; that a section by that
                          name exists is unchecked.
    ``document_field``    position: none. ``D10`` only; ``field_path`` has no
                          declared syntax and no JSON artifact exists yet.
    ``html_heading``      position: none. ``D10`` only; resolving it needs an
                          HTML parser.
    ``html_selector``     position: none. ``D10`` only; resolving it needs a CSS
                          engine.

    ``D9`` and ``D10`` deliberately overlap. If the offsets are wrong but the
    quote is real, ``D9`` fires and ``D10`` passes, and *"your quote exists, your
    offsets do not"* is exactly the diagnosis a re-prompt needs.

    ``D11`` is a hard error rather than a silent skip. If an artifact could opt
    out of having text, the strongest check in the commit would become optional
    and an operator could dodge it by omitting one flag.

    ``D14`` is the rule that makes the rest of them load-bearing. Every check
    above is gated on the locator *having* something to resolve, so before
    ``D14`` a locator cited by an observation could carry no ``quoted_text`` at
    all and pass every one of them: a ``text_span`` with offsets and no quote
    skipped ``D9``'s comparison and ``D10`` entirely, and a
    ``document_section`` with neither quote nor offsets skipped even ``D11``.
    Both were source-backed observations asserting facts that nothing checked,
    which is the exact hole this whole layer exists to close.

    **An observation cannot be supported by a scanned page with no text layer.**
    That is the deliberate consequence, stated plainly: either the operator
    supplies OCR through ``--text`` and the quote is checked against it, or the
    fact has to come from a document plinth can read. Plinth cannot verify a
    quote against an image and must not accept one it cannot verify.

    A locator nobody cites stays free to be unquoted -- the catalogue is allowed
    to hold addresses that no observation leans on yet. Derived observations are
    unaffected: they reach evidence through ``parent_observation_ids``, not
    ``supports``.

    Dangling ``artifact_sha256`` is skipped rather than re-reported: ``P2`` owns
    it. So are artifacts whose text blob ``D4`` has already rejected.
    """
    artifacts: dict[str, Artifact] = {}
    for artifact in pack.artifacts:
        artifacts.setdefault(artifact.sha256, artifact)

    supported_ids = {
        support.locator_id
        for observation in pack.observations
        for support in observation.supports
    }

    found: list[Issue] = []
    for index, locator in enumerate(pack.locator_catalog):
        artifact = artifacts.get(locator.artifact_sha256)
        if artifact is None:
            continue
        where = ("locator_catalog", index)

        if locator.page is not None and artifact.page_count is not None:
            if locator.page > artifact.page_count:
                found.append(
                    issue(
                        "D8",
                        f"page {locator.page} is past the end of artifact "
                        f"{artifact.sha256}, which has {artifact.page_count} pages",
                        *where,
                        "page",
                    )
                )

        is_supported = locator.locator_id in supported_ids
        if is_supported and not collapse_whitespace(locator.quoted_text or ""):
            found.append(
                issue(
                    "D14",
                    f"locator {locator.locator_id!r} is cited by an observation but "
                    "carries no quoted_text, so nothing ties the proposition to the "
                    "archived document; quote the exact span the fact was read from",
                    *where,
                    "quoted_text",
                )
            )

        # `is_supported` belongs in this disjunction, not just in D14: without it
        # a cited locator with neither quote nor offsets would skip D11 too, and
        # the pack would never be told its artifact has no readable text.
        addresses_text = (
            locator.quoted_text is not None
            or locator.char_start is not None
            or locator.char_end is not None
            or is_supported
        )
        if not addresses_text:
            continue
        if artifact.text_sha256 is None:
            found.append(
                issue(
                    "D11",
                    f"artifact {artifact.sha256} has no text_sha256, so nothing can "
                    "resolve this locator's quoted_text or character offsets; archive a "
                    "text rendering of the document",
                    *where,
                    "char_start"
                    if locator.quoted_text is None and locator.char_start is not None
                    else "quoted_text",
                )
            )
            continue
        decoded = blobs.read(f"{artifact.text_sha256}{TEXT_BLOB_SUFFIX}")
        if decoded.text is None:
            # D4 has already reported why.
            continue
        found.extend(_resolve_locator(locator, decoded.text, where))
    return tuple(found)


def _resolve_locator(
    locator: Locator, text: str, where: tuple[str | int, ...]
) -> list[Issue]:
    """``D9`` then ``D10`` against one artifact's archived text.

    ``L2`` has already ordered the two offsets and kept them non-negative, so
    the only thing left to establish is that they address characters this text
    actually has.
    """
    found: list[Issue] = []
    start, end = locator.char_start, locator.char_end
    in_range = True

    if start is not None and start >= len(text):
        in_range = False
        found.append(
            issue(
                "D9",
                f"char_start {start} is at or past the end of the text, which is "
                f"{len(text)} characters",
                *where,
                "char_start",
            )
        )
    if end is not None and end > len(text):
        in_range = False
        found.append(
            issue(
                "D9",
                f"char_end {end} is past the end of the text, which is {len(text)} "
                "characters",
                *where,
                "char_end",
            )
        )

    quote = locator.quoted_text
    if quote is not None and start is not None and end is not None and in_range:
        sliced = collapse_whitespace(text[start:end])
        if sliced != collapse_whitespace(quote):
            found.append(
                issue(
                    "D9",
                    f"characters {start}-{end} of the text are {sliced!r}, which is not "
                    "quoted_text",
                    *where,
                    "quoted_text",
                )
            )

    if quote is not None:
        collapsed = collapse_whitespace(quote)
        if not collapsed:
            found.append(
                issue(
                    "D10",
                    "quoted_text has no non-whitespace characters, so it matches every "
                    "document and proves nothing",
                    *where,
                    "quoted_text",
                )
            )
        elif collapsed not in collapse_whitespace(text):
            found.append(
                issue(
                    "D10",
                    "quoted_text does not occur in the archived text of artifact "
                    f"{locator.artifact_sha256}, after collapsing whitespace",
                    *where,
                    "quoted_text",
                )
            )
    return found


PACK_RUN_RULES = (
    check_d5_campaign_is_preregistered,
    check_d6_records_match_the_archive,
    check_d7_archive_is_fully_represented,
)


def validate_pack_against_run(pack: EvidencePack, run: LoadedRun) -> tuple[Issue, ...]:
    """Check that an evidence pack describes **this run's** archived bytes.

    Symmetric with
    :func:`~plinth.validate.validate_assessment_against_pack`: it assumes the
    pack already validated on its own, and its pointers address the pack,
    because that is the document a re-prompt would ask a model to correct.
    """
    found: list[Issue] = []
    for rule in PACK_RUN_RULES:
        found.extend(rule(pack, run))
    blobs = BlobStore(run.blobs_dir)
    found.extend(check_d1_d2_d3_artifact_bytes(pack, blobs))
    found.extend(check_d4_text_bytes(pack, blobs))
    found.extend(check_d8_to_d14_locators(pack, blobs))
    return tuple(found)


# --------------------------------------------------------------------------
# run-level integrity: no pack required
# --------------------------------------------------------------------------


def check_d12_blobs_are_self_named(run: LoadedRun) -> tuple[Issue, ...]:
    """D12 -- every file in ``blobs/`` is named for its own digest.

    Runs without a pack, and that is the point: it catches a flipped byte in a
    blob the pack never references, and a ``.tmp-`` left behind by an
    interrupted ``archive add``, neither of which any pack-anchored rule would
    ever look at.
    """
    blobs = BlobStore(run.blobs_dir)
    found: list[Issue] = []
    try:
        names = blobs.names()
    except ArchiveError as exc:
        # An unlistable archive used to read as an empty one, which is the
        # quiet answer that calls a tampered run clean.
        return (issue("D12", str(exc)),)
    for name in names:
        if not ARTIFACT_FILENAME_RE.match(name):
            found.append(
                issue(
                    "D12",
                    f"{BLOBS_DIR_NAME}/{name} is not named for a digest; an interrupted "
                    "archive add or a hand-placed file",
                )
            )
            continue
        measured = blobs.read(name)
        if measured.error is not None:
            found.append(issue("D12", f"{BLOBS_DIR_NAME}/{name} {measured.error}"))
        elif measured.sha256 != name[:64]:
            found.append(
                issue(
                    "D12",
                    f"{BLOBS_DIR_NAME}/{name} hashes to {measured.sha256}; the archived "
                    "bytes have changed since they were written",
                )
            )
    return tuple(found)


def check_d13_catalogue_is_unchanged(
    run: LoadedRun, catalogue_path: Path = cat.CATALOGUE_PATH
) -> tuple[Issue, ...]:
    """D13 -- the catalogue is the one the run was opened against.

    A framework edit mid-run is legitimate; doing it silently is not, because
    the assessment stage answers a fixed set of 63 questions and ``run.json``
    is where the run says which set.
    """
    try:
        digest = hashlib.sha256(catalogue_path.read_bytes()).hexdigest()
    except OSError as exc:
        return (issue("D13", f"cannot read the catalogue at {catalogue_path}: {exc}"),)
    if digest != run.manifest.catalogue_sha256:
        return (
            issue(
                "D13",
                f"{catalogue_path} now hashes to {digest}, but this run was opened "
                f"against {run.manifest.catalogue_sha256}",
            ),
        )
    return ()


def check_run_integrity(
    run: LoadedRun, catalogue_path: Path = cat.CATALOGUE_PATH
) -> tuple[Issue, ...]:
    """``D12`` and ``D13`` -- what a run must satisfy with no pack involved."""
    return (
        *check_d13_catalogue_is_unchanged(run, catalogue_path),
        *check_d12_blobs_are_self_named(run),
    )


def assess_pack_for_run(
    raw: object, run: LoadedRun, catalogue_path: Path = cat.CATALOGUE_PATH
) -> tuple[EvidencePack | None, tuple[Issue, ...]]:
    """The single definition of an acceptable pack for a run.

    Both ``ingest evidence`` and ``verify`` call this, because they were
    answering the same question with different rules: ingest skipped ``D12`` and
    ``D13``, so an unchanged proposal could be accepted against a drifted
    catalogue or a corrupted blob and then fail verification immediately
    afterwards. Accepting a pack against a drifted catalogue is precisely what
    ``D13`` exists to stop, so the stricter side wins and there is now one
    predicate rather than two that can diverge again.

    The pack is returned whenever it *constructed*, matching
    :func:`~plinth.validate.validate_pack`: a non-``None`` model is not a
    verdict.
    """
    pack, problems = validate_pack(raw)
    found: list[Issue] = [*check_run_integrity(run, catalogue_path), *problems]
    if pack is not None:
        found.extend(validate_pack_against_run(pack, run))
    return pack, tuple(found)


__all__ = [
    "ArchiveError",
    "ArchiveIndex",
    "BlobStore",
    "LoadedRun",
    "MAX_ARTIFACT_BYTES",
    "RUNS_DIR",
    "RunManifest",
    "add_artifact",
    "assess_pack_for_run",
    "blob_name",
    "check_run_integrity",
    "collapse_whitespace",
    "create_run",
    "load_run",
    "reconcile_artifact",
    "redact_url",
    "run_directory",
    "validate_pack_against_run",
    "write_atomic",
]
