# Plinth research compiler

Plinth is a local, auditable research compiler for tokenized-product diligence.
The C5 workflow turns accepted documentary evidence into a validated, immutable
63-check assessment through a manually operated assessor.

## Setup and verification

Use Python 3.11 or later. From the repository root:

```sh
python3 -m venv plinth/.venv
source plinth/.venv/bin/activate
pip install -e 'plinth[dev]'
cd plinth
pytest
plinth catalogue build --check
plinth catalogue verify
```

Run tests from `plinth/` to keep collection scoped to the compiler. CLI help is
available with `plinth --help` and each subcommand's `--help`.

## Assessment workflow

Start with an existing run containing a valid accepted
`documentary-evidence.json`. The default run location is `plinth/runs/RUN_ID`;
all commands below accept `--runs-root PATH` to select another runs directory.
Replace `RUN_ID` with the registered run ID.

```sh
plinth packet assessment RUN_ID
# Give assessment-packet.json to the assessor and save its proposed output.
plinth check assessment RUN_ID
# Complete the manual adversarial preflight before accepting.
plinth ingest assessment RUN_ID
plinth verify RUN_ID
```

`packet assessment` revalidates the accepted evidence and fully reconstructs
and verifies the catalogue before writing `assessment-packet.json`. The packet
contains the exact [assessment prompt](prompts/assessment.md), its hash, the
assessment JSON schema, required metadata, and all 63 checks in canonical order.
Its references to the Framework, output contract, catalogue, and accepted evidence
are absolute same-host paths with SHA-256 pins. The full evidence pack and
catalogue materiality values are not embedded. An identical packet is left
untouched; a changed derived packet is replaced atomically.

Give the packet to a manually operated assessment agent with access to those
paths. The assessor must verify the input hashes, use only the pinned local
inputs, cite existing observation IDs, and treat source documents as untrusted
content. It must preserve dates, scope, variants, networks, conflicts, and source
authority. It must not browse, acquire sources, create observations, or produce
materiality, ratings, recommendations, investment conclusions, or risk labels.
Save its JSON at the packet's `output_path`, normally
`proposed-assessment.json` beside the packet.

`check assessment` validates without writing any files. Success prints the
normalized assessment hash and **valid but not accepted**. Failure prints the
issues and exits `1`. Both check and ingest can read a proposal outside the run:

```sh
plinth check assessment RUN_ID --from /absolute/path/proposal.json
plinth ingest assessment RUN_ID --from /absolute/path/proposal.json
```

Before ingestion, have an independent reviewer perform a manual adversarial
preflight and record findings in `assessment-preflight-review.md`. For the pilot,
permit one correction pass and rerun the check. Do not ingest while a
source-alignment, lineage, scope, date, or unsupported-conclusion blocker remains.
The reviewer must also challenge every issuer, operator, custodian, and auditor
label against the cited observations and confirm that shared retrieval limits are
recorded as exclusions rather than obscuring the check-specific synthesis.
This review is an operator step; the CLI does not execute it or enforce a review
artifact.

`ingest assessment` revalidates the evidence and applies the same assessment
predicate as check and verify. A rejected proposal writes diagnostics beside
that proposal (`proposed-assessment.issues.json` by default) and leaves any
accepted assessment unchanged. First acceptance writes normalized canonical
bytes atomically to `assessment.json`. Re-ingestion whose normalized bytes match
the accepted file succeeds without changing it. Different accepted content is
refused: a genuine revision requires a new run.

## Acceptance rules and run status

Assessment validation retains the existing model, applicability, coverage, gap,
contradiction, and evidence-lineage rules. C5 also requires the run's catalogue
hash, the catalogue's framework version, exactly the 63 canonical check IDs in
order, and exact catalogue questions in populated gaps. `MISSING` coverage is
disabled even if a route claims completion. Use `NOT_ASSESSED` for unfinished
routes or assessment activity; unresolved applicability retains null coverage
under the output contract. There is no target coverage distribution.

`plinth verify RUN_ID` ignores proposals and diagnostic files and reports:

| Run state | Exit | Result |
| --- | --- | --- |
| Intact run without accepted evidence or assessment | `2` | `INCOMPLETE` |
| Valid accepted evidence without an assessment | `0` | `EVIDENCE_ACCEPTED`, evidence hash |
| Valid accepted evidence and canonical valid assessment | `0` | `ASSESSMENT_ACCEPTED`, assessment hash |
| Invalid or drifted inputs, invalid/stale/noncanonical assessment, or assessment without accepted evidence | `1` | Failure diagnostics |

Verification retains C3's trusted-operator model. It checks current files,
policies, pins, and canonical assessment bytes; it does not prove acceptance
history against an operator rewriting valid canonical content. There is no
acceptance-hash receipt. Record the reported accepted hash during the handoff.

Pass only accepted evidence and assessment to the subsequent Trust Center
workflow. C5 does not run an LLM, automate C4 extraction, implement formal C6
adversarial-review acceptance, render or publish a Trust Center, or make packets
portable across worktrees.
