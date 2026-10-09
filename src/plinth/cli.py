"""``plinth`` command line.

argparse rather than a CLI framework: the subcommands cost a few lines each here
and add no second import surface to keep current.

Exit codes are the same three everywhere, reusing the convention ``mock/check.py``
already established rather than inventing a finer taxonomy no consumer reads:

    0   what was asked for is true
    1   a failure, named on stderr
    2   INCOMPLETE -- the run exists but has not reached this stage yet
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from . import __version__, archive as arc, assessment as asm, catalogue as cat
from .models import Campaign, canonical_bytes, canonical_sha256
from .validate import construct
from .vocab import AcquisitionMode


def preflight() -> None:
    """Fail on a broken environment before doing any work.

    C1 needs nothing from pydantic, but C2 validates LLM output with it. Catching
    a half-installed environment here beats discovering it one commit later.
    """
    try:
        import pydantic
    except ImportError:  # pragma: no cover - environment failure
        sys.exit("plinth: pydantic is not installed. Run: pip install -e 'plinth[dev]'")
    if not pydantic.VERSION.startswith("2."):  # pragma: no cover - environment failure
        sys.exit(f"plinth: pydantic 2.x is required, found {pydantic.VERSION}")


def _abbrev(digest: str) -> str:
    return f"{digest[:8]}…{digest[-8:]}"


def _display_path(path: Path) -> str:
    """Repo-relative where that reads better, absolute otherwise.

    A redirected output path in a test lives outside PROJECT_ROOT, and printing
    it must not be the thing that raises.
    """
    try:
        return str(path.relative_to(cat.PROJECT_ROOT))
    except ValueError:
        return str(path)


def cmd_build(args: argparse.Namespace) -> int:
    try:
        built = cat.build_catalogue(cat.INPUTS_DIR)
    except cat.BuildError as exc:
        print(f"plinth: [build] {exc}", file=sys.stderr)
        return 1

    # The verifier is the single definition of a valid catalogue, so the builder
    # calls it rather than restating any part of it. An invalid build is never
    # compared against the commit and never written over it:
    #   if `catalogue build` exits 0, the result passes `catalogue verify`.
    failures = cat.verify(built, cat.INPUTS_DIR)
    if failures:
        for failure in failures:
            print(failure.render(), file=sys.stderr)
        print(
            f"plinth: [build] refusing an invalid catalogue — {len(failures)} failure(s); "
            f"{_display_path(cat.CATALOGUE_PATH)} is unchanged",
            file=sys.stderr,
        )
        return 1

    # Bytes, not text, on both sides: universal-newline translation on read would
    # hide CRLF drift in the committed file, which is exactly the drift worth
    # catching in a canonical artifact.
    payload = cat.canonical_json(built).encode("utf-8")

    if args.check:
        if not cat.CATALOGUE_PATH.exists():
            print(
                f"plinth: [build --check] {_display_path(cat.CATALOGUE_PATH)} does not exist",
                file=sys.stderr,
            )
            return 1
        try:
            committed = cat.CATALOGUE_PATH.read_bytes()
        except OSError as exc:
            print(f"plinth: cannot read {_display_path(cat.CATALOGUE_PATH)}: {exc}", file=sys.stderr)
            return 1
        if committed != payload:
            print(
                "plinth: [build --check] the committed catalogue differs from a fresh build\n"
                "        either the pinned inputs changed, the parser changed, or the JSON "
                "was hand-edited\n"
                "        run: plinth catalogue build",
                file=sys.stderr,
            )
            return 1
        print(f"plinth: catalogue is current ({len(built['checks'])} checks)")
        return 0

    try:
        cat.CATALOGUE_PATH.write_bytes(payload)
    except OSError as exc:
        print(f"plinth: cannot write {_display_path(cat.CATALOGUE_PATH)}: {exc}", file=sys.stderr)
        return 1
    print(
        f"plinth: wrote {_display_path(cat.CATALOGUE_PATH)} — "
        f"{len(built['checks'])} checks, {len(payload)} bytes"
    )
    return 0


def _load_catalogue() -> dict | None:
    if not cat.CATALOGUE_PATH.exists():
        print(
            f"plinth: {cat.CATALOGUE_PATH} does not exist. Run: plinth catalogue build",
            file=sys.stderr,
        )
        return None
    try:
        loaded = json.loads(cat.CATALOGUE_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"plinth: cannot read {cat.CATALOGUE_PATH}: {exc}", file=sys.stderr)
        return None
    if not isinstance(loaded, dict):
        print(
            f"plinth: {cat.CATALOGUE_PATH} is a JSON {type(loaded).__name__}, expected an object",
            file=sys.stderr,
        )
        return None
    return loaded


def cmd_verify(args: argparse.Namespace) -> int:
    catalogue = _load_catalogue()
    if catalogue is None:
        return 1
    failures = cat.verify(catalogue, cat.INPUTS_DIR)
    for failure in failures:
        print(failure.render(), file=sys.stderr)
    if failures:
        print(f"plinth: {len(failures)} failure(s)", file=sys.stderr)
        return 1
    print(
        f"plinth: catalogue verified — {len(catalogue['checks'])} checks, "
        f"reconstructed from and matched against inputs/{cat.FRAMEWORK_MD}"
    )
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    c = _load_catalogue()
    if c is None:
        return 1
    try:
        return _render(c)
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        # `show` summarizes a well-formed catalogue; diagnosing a broken one is
        # `verify`'s job, and it names every failure instead of the first.
        print(
            f"plinth: the catalogue is malformed ({exc!r}). Run: plinth catalogue verify",
            file=sys.stderr,
        )
        return 1


def _render(c: dict) -> int:
    print(f"Plinth catalogue — {c['schema_version']}")
    print(f"Framework {c['framework_version']} · {c['framework_status']}")

    print("\nInputs")
    width = max(len(v["path"]) for v in c["inputs"].values())
    for key in sorted(c["inputs"]):
        pin = c["inputs"][key]
        print(f"  {pin['path']:<{width}}  {pin['bytes']:>6} B  sha256 {_abbrev(pin['sha256'])}")

    total = len(c["checks"])
    print(f"\nPillars — {total} checks")
    id_width = max(len(p["pillar_id"]) for p in c["pillars"])
    label_width = max(len(p["display_label"]) for p in c["pillars"])
    for pillar in c["pillars"]:
        print(
            f"  {pillar['pillar_id']:<{id_width}}  {pillar['display_label']:<{label_width}}  "
            f"{pillar['id_prefix']:<14} {pillar['check_count']:>2}"
        )

    print("\nMateriality")
    print(f"  vocabulary    {' | '.join(c['materiality_vocabulary'])}")
    distribution = " · ".join(
        f"{m} {c['materiality_distribution'][m]}" for m in c["materiality_vocabulary"]
    )
    print(f"  distribution  {distribution}")

    fields = c["gap_contract"]["fields"]
    labels = c["gap_contract"]["display_labels"]
    print(f"\nGap contract — {len(fields)} fields (key → verified heading)")
    key_width = max(len(f) for f in fields)
    for key in fields:
        print(f"  {key:<{key_width}}  {labels[key]}")

    rules = c["gap_rules"]
    print(f"\nGap rules — {len(rules)} legal (applicability, coverage) pairs")
    for rule in rules:
        coverage = rule["coverage"] if rule["coverage"] is not None else "—"
        state = "gap required" if rule["gap_required"] else "no gap"
        print(f"  {rule['applicability']:<15} {coverage:<15} {state}")
    return 0


# --------------------------------------------------------------------------
# runs
# --------------------------------------------------------------------------


def _fail(message: str) -> int:
    print(f"plinth: {message}", file=sys.stderr)
    return 1


def _open_run(args: argparse.Namespace) -> arc.LoadedRun | None:
    """Load the named run, or report why it cannot be used."""
    try:
        return arc.load_run(arc.run_directory(args.run_id, args.runs_root))
    except arc.ArchiveError as exc:
        print(f"plinth: {exc}", file=sys.stderr)
        return None


def _report(problems, *, source: str) -> None:
    for problem in problems:
        print(problem.render(), file=sys.stderr)
    print(f"plinth: {len(problems)} issue(s) in {source}", file=sys.stderr)


def cmd_run_new(args: argparse.Namespace) -> int:
    """Pre-register a campaign, before any acquisition exists to be judged by it."""
    try:
        raw = args.campaign.read_bytes()
    except OSError as exc:
        return _fail(f"cannot read {args.campaign}: {exc}")

    campaign, problems = construct(Campaign, raw)
    if campaign is None:
        _report(problems, source=str(args.campaign))
        return 1
    if campaign.run_id != args.run_id:
        return _fail(
            f"{args.campaign} declares run_id {campaign.run_id!r}, but the command names "
            f"{args.run_id!r}"
        )

    try:
        run = arc.create_run(campaign, runs_root=args.runs_root)
    except arc.ArchiveError as exc:
        return _fail(str(exc))
    print(
        f"plinth: opened run {campaign.run_id} at {_display_path(run.root)} — "
        f"catalogue {_abbrev(run.manifest.catalogue_sha256)}"
    )
    return 0


def cmd_archive_add(args: argparse.Namespace) -> int:
    """Archive one file's bytes and record the acquisition that obtained them."""
    run = _open_run(args)
    if run is None:
        return 1
    try:
        _, acquisition, artifact = arc.add_artifact(
            run,
            args.file,
            source_id=args.source_id,
            acquisition_mode=args.mode,
            media_type=args.media_type,
            retrieved_at=args.retrieved_at,
            attempted_at=args.attempted_at,
            url=args.url,
            operator=args.operator,
            text_path=args.text,
            text_tool=args.text_tool,
            page_count=args.page_count,
            max_bytes=args.max_bytes,
        )
    except arc.ArchiveError as exc:
        return _fail(str(exc))
    print(
        f"plinth: archived {artifact.byte_length} bytes as {_abbrev(artifact.sha256)} — "
        f"acquisition {acquisition.acquisition_id}, source {acquisition.source_id}"
    )
    if artifact.text_sha256 is not None:
        print(f"        text {_abbrev(artifact.text_sha256)} — {artifact.text_extraction_tool}")
    return 0


def _issues_path(source: Path) -> Path:
    """``proposed-x.json`` -> ``proposed-x.issues.json``, beside the submission."""
    if source.suffix == ".json":
        return source.with_suffix(".issues.json")
    return source.with_name(source.name + ".issues.json")


def cmd_ingest_evidence(args: argparse.Namespace) -> int:
    """Accept a proposed evidence pack, or reject it and say exactly why.

    **On rejection plinth performs zero writes to any canonical path.** The
    proposed file keeps its name, is not moved, not rewritten and not deleted,
    and ``documentary-evidence.json`` is untouched -- so a rejected run is
    exactly the run that existed before, plus a diagnostic beside the
    submission.

    On acceptance the file holds the **normalized** form rather than the
    submitted bytes: ``X4`` pins the canonical form, so if what landed on disk
    were the submission, the pin would verify against something that is not the
    file.

    **An accepted pack is never replaced.** Re-ingesting byte-identical
    evidence succeeds and writes nothing; different evidence is refused. An
    overwrite would delete evidence a reader may already have cited and would
    silently stale every ``X4`` pin taken against the old digest, and the
    re-prompt loop does not need it -- rejected attempts happen *before*
    acceptance, never after. A genuine revision is a new run.
    """
    run = _open_run(args)
    if run is None:
        return 1
    source = args.from_path or run.proposed_pack_path
    try:
        raw = source.read_bytes()
    except OSError as exc:
        return _fail(f"cannot read {source}: {exc}")

    pack, problems = arc.assess_pack_for_run(raw, run)

    if problems:
        payload = cat.canonical_json(
            {
                "source": source.name,
                "issues": [problem.model_dump(mode="json") for problem in problems],
            }
        ).encode("utf-8")
        try:
            arc.write_atomic(_issues_path(source), payload)
        except arc.ArchiveError as exc:
            return _fail(str(exc))
        _report(problems, source=str(source))
        print(
            f"plinth: rejected — {_display_path(_issues_path(source))} written, "
            f"{arc.ACCEPTED_PACK_NAME} unchanged",
            file=sys.stderr,
        )
        return 1

    payload = canonical_bytes(pack)
    if run.accepted_pack_path.exists():
        try:
            accepted = run.accepted_pack_path.read_bytes()
        except OSError as exc:
            return _fail(f"cannot read {run.accepted_pack_path}: {exc}")
        if accepted == payload:
            print(
                f"plinth: already accepted — {_display_path(run.accepted_pack_path)} "
                "is unchanged"
            )
            print(canonical_sha256(pack))
            return 0
        return _fail(
            f"{arc.ACCEPTED_PACK_NAME} already holds different accepted evidence "
            f"({_abbrev(hashlib.sha256(accepted).hexdigest())} on disk, "
            f"{_abbrev(canonical_sha256(pack))} proposed); nothing was written. "
            "Revised evidence belongs to a new run."
        )

    try:
        arc.write_atomic(run.accepted_pack_path, payload)
    except arc.ArchiveError as exc:
        return _fail(str(exc))
    print(f"plinth: accepted {_display_path(run.accepted_pack_path)}")
    print(canonical_sha256(pack))
    return 0


def _assessment_context(args: argparse.Namespace):
    """C5-only prerequisites; the stable C3 paths stay independent."""
    run = _open_run(args)
    if run is None:
        return None
    try:
        raw = run.accepted_pack_path.read_bytes()
    except OSError as exc:
        _fail(f"valid accepted evidence is required: {exc}")
        return None
    pack, problems = arc.assess_pack_for_run(raw, run)
    if problems:
        _report(problems, source=str(run.accepted_pack_path))
        return None
    catalogue = _load_catalogue()
    if catalogue is None:
        return None
    return run, pack, catalogue


def cmd_packet_assessment(args: argparse.Namespace) -> int:
    context = _assessment_context(args)
    if context is None:
        return 1
    run, pack, catalogue = context
    path = run.root / asm.PACKET_NAME
    try:
        packet = asm.build_assessment_packet(run=run, pack=pack, catalogue=catalogue)
        payload = cat.canonical_json(packet).encode("utf-8")
        if path.exists() and path.read_bytes() == payload:
            print(f"plinth: packet unchanged — {_display_path(path)}")
            return 0
        arc.write_atomic(path, payload)
    except (OSError, UnicodeDecodeError, arc.ArchiveError, cat.BuildError) as exc:
        return _fail(str(exc))
    print(f"plinth: wrote {_display_path(path)}")
    return 0


def cmd_check_assessment(args: argparse.Namespace) -> int:
    context = _assessment_context(args)
    if context is None:
        return 1
    run, pack, catalogue = context
    source = args.from_path or run.root / asm.PROPOSED_ASSESSMENT_NAME
    try:
        raw = source.read_bytes()
    except OSError as exc:
        return _fail(f"cannot read {source}: {exc}")
    assessment, problems = asm.assess_assessment_for_run(
        raw, run=run, pack=pack, catalogue=catalogue,
    )
    if problems:
        _report(problems, source=str(source))
        return 1
    print("plinth: assessment valid but not accepted")
    print(canonical_sha256(assessment))
    return 0


def cmd_ingest_assessment(args: argparse.Namespace) -> int:
    context = _assessment_context(args)
    if context is None:
        return 1
    run, pack, catalogue = context
    source = args.from_path or run.root / asm.PROPOSED_ASSESSMENT_NAME
    target = run.root / asm.ACCEPTED_ASSESSMENT_NAME
    try:
        raw = source.read_bytes()
    except OSError as exc:
        return _fail(f"cannot read {source}: {exc}")
    assessment, problems = asm.assess_assessment_for_run(
        raw, run=run, pack=pack, catalogue=catalogue,
    )
    if problems:
        payload = cat.canonical_json({
            "source": source.name,
            "issues": [problem.model_dump(mode="json") for problem in problems],
        }).encode("utf-8")
        try:
            arc.write_atomic(_issues_path(source), payload)
        except arc.ArchiveError as exc:
            return _fail(str(exc))
        _report(problems, source=str(source))
        return _fail(f"rejected — {_display_path(_issues_path(source))} written, "
                     f"{asm.ACCEPTED_ASSESSMENT_NAME} unchanged")

    payload = canonical_bytes(assessment)
    try:
        if target.exists():
            if target.read_bytes() == payload:
                print("plinth: assessment already accepted — unchanged")
                print(canonical_sha256(assessment))
                return 0
            return _fail("assessment.json already holds different accepted content; "
                         "nothing was written. Revised assessments belong to a new run.")
        arc.write_atomic(target, payload)
    except (OSError, arc.ArchiveError) as exc:
        return _fail(str(exc))
    print(f"plinth: accepted {_display_path(target)}")
    print(canonical_sha256(assessment))
    return 0


def cmd_run_verify(args: argparse.Namespace) -> int:
    """Re-derive every claim the run makes about itself, from the files it holds.

    Composes the merged entry points and reimplements none of them.

    What this **trusts**, and cannot check: that the blobs are bytes a server
    actually served -- there is no signature, no timestamp authority and no WARC;
    ``text_extraction_tool``; the operator's clock; and ``media_type``,
    ``original_filename`` and ``page_count``, which means ``D8`` is a consistency
    check against a number nothing counted.
    """
    run = _open_run(args)
    if run is None:
        return 1

    if not run.accepted_pack_path.exists():
        if (run.root / asm.ACCEPTED_ASSESSMENT_NAME).exists():
            return _fail("assessment present without accepted evidence")
        found = arc.check_run_integrity(run)
        if found:
            _report(found, source=_display_path(run.root))
            return 1
        print(
            f"plinth: run {args.run_id} is INCOMPLETE — no {arc.ACCEPTED_PACK_NAME} yet",
            file=sys.stderr,
        )
        return 2

    try:
        raw = run.accepted_pack_path.read_bytes()
    except OSError as exc:
        return _fail(f"cannot read {run.accepted_pack_path}: {exc}")

    # The same predicate `ingest evidence` accepted against, re-run from the
    # files as they stand now. Anything it reports is drift since acceptance.
    pack, found = arc.assess_pack_for_run(raw, run)
    found = list(found)

    if found:
        _report(found, source=_display_path(run.root))
        if pack is not None:
            print("plinth: evidence trace", file=sys.stderr)
            for line in _evidence_trace(pack):
                print(line, file=sys.stderr)
        return 1

    assessment_path = run.root / asm.ACCEPTED_ASSESSMENT_NAME
    if assessment_path.exists():
        catalogue = _load_catalogue()
        if catalogue is None:
            return 1
        try:
            assessment_raw = assessment_path.read_bytes()
        except OSError as exc:
            return _fail(f"cannot read {assessment_path}: {exc}")
        assessment, problems = asm.assess_assessment_for_run(
            assessment_raw, run=run, pack=pack, catalogue=catalogue,
        )
        if problems:
            _report(problems, source=str(assessment_path))
            return 1
        # Accepted output has one canonical representation. Formatting edits
        # are not a new acceptance and must not silently pass verification.
        if assessment_raw != canonical_bytes(assessment):
            return _fail("accepted assessment bytes are not canonical")
        print(f"plinth: run {args.run_id} verified — ASSESSMENT_ACCEPTED")
        print(canonical_sha256(assessment))
        return 0

    print(
        f"plinth: run {args.run_id} verified — EVIDENCE_ACCEPTED — {len(pack.artifacts)} artifact(s), "
        f"{len(pack.observations)} observation(s)"
    )
    print(canonical_sha256(pack))
    return 0


def _evidence_trace(pack) -> list[str]:
    """``artifact <- acquisition <- source`` for every archived fetch in the pack.

    Printed whole rather than filtered to the failing records: deciding which
    artifact an issue implicates would mean parsing its JSON pointer back into a
    record, and a parser that is wrong about that would name the wrong document
    in a diagnostic about tampering.
    """
    titles = {source.source_id: source.title for source in pack.sources}
    lines = []
    for acquisition in pack.acquisitions:
        if acquisition.artifact_sha256 is None:
            continue
        title = titles.get(acquisition.source_id, "<unknown source>")
        lines.append(
            f"  artifact {_abbrev(acquisition.artifact_sha256)}  ← acquisition "
            f"{acquisition.acquisition_id}  ← source {acquisition.source_id} ({title})"
        )
    return lines


def main(argv: list[str] | None = None) -> int:
    preflight()
    parser = argparse.ArgumentParser(prog="plinth", description=__doc__)
    parser.add_argument("--version", action="version", version=f"plinth {__version__}")
    top = parser.add_subparsers(dest="group", required=True)

    catalogue_parser = top.add_parser("catalogue", help="the 63-check framework catalogue")
    sub = catalogue_parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="compile the pinned markdown into inputs/catalogue.json")
    build.add_argument(
        "--check",
        action="store_true",
        help="regenerate in memory and exit 1 if the committed JSON differs",
    )
    build.set_defaults(func=cmd_build)

    sub.add_parser("verify", help="reverse-check the committed JSON against the source").set_defaults(
        func=cmd_verify
    )
    sub.add_parser("show", help="human summary").set_defaults(func=cmd_show)

    # One parent for every command that addresses a run, so `--runs-root` is
    # declared once. It exists so that a test can build a whole run in tmp_path:
    # the alternative, a module-level path the tests monkeypatch, makes the
    # production default something no test ever exercises.
    run_scoped = argparse.ArgumentParser(add_help=False)
    run_scoped.add_argument("run_id", metavar="RUN_ID", help="the campaign's run_id")
    run_scoped.add_argument(
        "--runs-root",
        type=Path,
        default=arc.RUNS_DIR,
        help=f"directory holding runs (default: {_display_path(arc.RUNS_DIR)})",
    )

    run_parser = top.add_parser("run", help="open and inspect a campaign run")
    run_sub = run_parser.add_subparsers(dest="command", required=True)
    run_new = run_sub.add_parser(
        "new", parents=[run_scoped], help="pre-register a campaign and open an empty archive"
    )
    run_new.add_argument(
        "--campaign",
        type=Path,
        required=True,
        help="JSON file holding the Campaign to pre-register",
    )
    run_new.set_defaults(func=cmd_run_new)

    archive_parser = top.add_parser("archive", help="archived bytes and the fetches that got them")
    archive_sub = archive_parser.add_subparsers(dest="command", required=True)
    archive_add = archive_sub.add_parser(
        "add", parents=[run_scoped], help="archive one file and record its acquisition"
    )
    archive_add.add_argument("file", metavar="FILE", type=Path, help="the file to archive")
    archive_add.add_argument(
        "--source-id",
        required=True,
        help="join key only; this command authors no Source, because title, author and "
        "research posture are research judgment",
    )
    archive_add.add_argument(
        "--mode",
        required=True,
        type=AcquisitionMode,
        choices=list(AcquisitionMode),
        help="how the artifact was obtained",
    )
    archive_add.add_argument(
        "--media-type",
        required=True,
        help="recorded verbatim and never sniffed; a guess stored as a fact is worse "
        "than no fact",
    )
    archive_add.add_argument("--retrieved-at", required=True, help="ISO-8601 with an offset")
    archive_add.add_argument(
        "--attempted-at", default=None, help="ISO-8601 with an offset (default: --retrieved-at)"
    )
    archive_add.add_argument("--url", default=None, help="recorded with secrets redacted")
    archive_add.add_argument("--operator", default=None, help="required for MANUAL_UPLOAD (A4)")
    archive_add.add_argument(
        "--text", type=Path, default=None, help="UTF-8 text rendering of the document"
    )
    archive_add.add_argument(
        "--text-tool", default=None, help="what produced --text; recorded, never verified"
    )
    archive_add.add_argument("--page-count", type=int, default=None, help="pages, if known")
    archive_add.add_argument(
        "--max-bytes",
        type=int,
        default=arc.MAX_ARTIFACT_BYTES,
        help=f"refuse a file larger than this (default: {arc.MAX_ARTIFACT_BYTES})",
    )
    archive_add.set_defaults(func=cmd_archive_add)

    ingest_parser = top.add_parser("ingest", help="accept or reject a stage's proposed output")
    ingest_sub = ingest_parser.add_subparsers(dest="command", required=True)
    ingest_evidence = ingest_sub.add_parser(
        "evidence", parents=[run_scoped], help="validate and accept a documentary evidence pack"
    )
    ingest_evidence.add_argument(
        "--from",
        dest="from_path",
        type=Path,
        default=None,
        help=f"the proposed pack (default: <run>/{arc.PROPOSED_PACK_NAME})",
    )
    ingest_evidence.set_defaults(func=cmd_ingest_evidence)

    packet_parser = top.add_parser("packet", help="generate a pinned stage handoff")
    packet_sub = packet_parser.add_subparsers(dest="command", required=True)
    packet_sub.add_parser("assessment", parents=[run_scoped]).set_defaults(
        func=cmd_packet_assessment
    )
    check_parser = top.add_parser("check", help="validate without accepting or writing")
    check_sub = check_parser.add_subparsers(dest="command", required=True)
    for subcommands, handler in (
        (check_sub, cmd_check_assessment), (ingest_sub, cmd_ingest_assessment),
    ):
        command = subcommands.add_parser("assessment", parents=[run_scoped])
        command.add_argument("--from", dest="from_path", type=Path, default=None,
                             help=f"proposal (default: <run>/{asm.PROPOSED_ASSESSMENT_NAME})")
        command.set_defaults(func=handler)

    top.add_parser(
        "verify", parents=[run_scoped], help="re-derive every claim a run makes about itself"
    ).set_defaults(func=cmd_run_verify)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
