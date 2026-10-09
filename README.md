# Plinth research toolkit

Plinth turns documentary research about a tokenized product into an evidence-linked
assessment against the 63 checks of the Plinth Framework v0.2. It then turns that
assessment into a static, two-mode Trust Center. This repository holds the two parts that do
that:

- **The `plinth` compiler** (`src/plinth/`) is a local CLI. It:
  - archives source documents;
  - validates and accepts the evidence pack you write;
  - builds a pinned assessment packet;
  - validates and accepts the assessment;
  - re-verifies a whole run.
- **The trust-center skill** (`skills/plinth-trust-center/`) is the instructions and scripts
  that turn an accepted run into the Trust Center HTML.

Nothing here is about a particular product. Research runs (`runs/`) and Trust Centers
(`trust-centers/`) are created locally and are gitignored. Agents should start with
[AGENTS.md](AGENTS.md).

## Setup

Python 3.11 or later.

```sh
git clone git@github.com:stedfn/plinth-research.git
cd plinth-research
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
plinth catalogue build --check
plinth catalogue verify
```

Install it editable, as shown. The compiler reads its pinned inputs (`inputs/`) and prompt
(`prompts/`) from the source checkout, and those are not packaged. A plain `pip install` of
the repository therefore gives a CLI whose catalogue, packet and verify commands fail. Every
command has `--help`.

## Stages, exit codes and failure codes

| Stage | What it covers | How |
| --- | --- | --- |
| C1 | Compile the framework markdown into `inputs/catalogue.json`, and prove the compile | `plinth catalogue build --check`, `plinth catalogue verify` |
| C2 | Define what a valid record is | `src/plinth/models.py` |
| C3 | Pre-register a campaign, archive source bytes, accept the evidence pack | `plinth run new`, `plinth archive add`, `plinth ingest evidence` |
| C4 | Write the evidence pack from the archived sources | manual: no command |
| C5 | Build the assessment packet, then check and accept the assessment | `plinth packet assessment`, `plinth check assessment`, `plinth ingest assessment` |
| C6 | Adversarial review before accepting | manual |
| Run | Re-derive everything a run claims about itself | `plinth verify` |

Exit codes are the same everywhere: `0` the request succeeded, `1` failure (named on stderr),
`2` the run has not reached this stage yet.

Each failure carries a stable code whose letter is the family and whose number is the rule:

| Letter | Family |
| --- | --- |
| `V` | catalogue verification |
| `S` | source shape |
| `A` | acquisition shape |
| `L` | locator shape |
| `O` | observation shape |
| `R` | route shape |
| `G` | gap shape |
| `K` | check shape |
| `P` | consistency between records in an evidence pack |
| `D` | an evidence pack against its archived bytes |
| `X` | an assessment against its evidence pack, catalogue and run |

## From a product to a Trust Center

Steps marked **manual** are done by you or your agent; the others are commands. Every run
command takes `--runs-root PATH`. It defaults to `runs/` in this checkout, which is
gitignored; pass another path to keep research elsewhere.

### 1. Campaign (manual)

Write the campaign: who and what is under review, the perimeter, the cutoff, and how
evidence will be acquired. See
[the intake contract](skills/plinth-trust-center/references/input-contract.md).

```json
{
  "run_id": "example-fund-2026-10-10",
  "subject": "Example Fund tokenized shares",
  "subject_description": "The tokenized share class, its issuing vehicle, manager, custodian and the assets it holds.",
  "cutoff": "2026-10-10T23:59:59Z",
  "declared_acquisition_modes": ["HTTP_DOWNLOAD", "BROWSER_CAPTURE", "MANUAL_UPLOAD"],
  "declared_scope_note": "Public documents only; no issuer contact.",
  "bounded_public_evidence": true
}
```

```sh
plinth run new example-fund-2026-10-10 --campaign campaign.json
```

### 2. Research and acquisition (manual, with a command)

Discover sources within the campaign's perimeter. A research dossier is optional and only a
list of leads; acquire the underlying documents it cites. Archive each one:

```sh
plinth archive add example-fund-2026-10-10 prospectus.pdf --source-id prospectus \
  --mode HTTP_DOWNLOAD --media-type application/pdf \
  --retrieved-at 2026-10-10T12:00:00+00:00 --url https://example.com/prospectus.pdf \
  --text prospectus.txt --text-tool "pdftotext 24.02 -layout"
```

- Plinth runs no extractor. For anything that is not plain text, supply a text rendering
  (`--text`) and name the tool that made it (`--text-tool`).
- `--operator` is required for `MANUAL_UPLOAD`. Give a role, not a person's name, because
  the value is published in the Trust Center.
- A blocked or failed attempt has no command; you record it in step 3.

### 3. Evidence pack (manual)

Write `runs/RUN_ID/proposed-documentary-evidence.json` against `EvidencePack` in
`src/plinth/models.py`:

- Copy `acquisitions` and `artifacts` unchanged from `runs/RUN_ID/archive/index.json`.
- Add each blocked, not-found or failed attempt as an acquisition with its outcome,
  `attempted_at` and `failure_reason`, and no artifact.
- Write `sources`, `locator_catalog` (with the exact quoted text each observation relies on),
  `observations` and `routes`.

`tests/fixtures/` has a small evidence pack that shows the shape.
[The intake contract](skills/plinth-trust-center/references/input-contract.md) says what
belongs where.

### 4. Accept the evidence

```sh
plinth ingest evidence RUN_ID
```

On rejection it writes `proposed-documentary-evidence.issues.json` beside the proposal. Fix
the issues and rerun. `plinth verify RUN_ID` then reports `EVIDENCE_ACCEPTED`.

### 5. Assessment

```sh
plinth packet assessment RUN_ID
# manual: give assessment-packet.json to the assessor and save its output
plinth check assessment RUN_ID
# manual: adversarial preflight (below)
plinth ingest assessment RUN_ID
plinth verify RUN_ID
```

The details are in "Assessment workflow" below.

### 6. Trust Center

Follow [skills/plinth-trust-center/SKILL.md](skills/plinth-trust-center/SKILL.md):

1. Prefill the shell from the accepted records.
2. Write the narrative.
3. Check the page against the records.

The output goes to `trust-centers/<subject-slug>/`.

## Assessment workflow

Start from a run whose accepted `documentary-evidence.json` is valid. Run files live in
`runs/RUN_ID` unless you pass `--runs-root PATH`.

`packet assessment` revalidates the accepted evidence and fully reconstructs and verifies the
catalogue before it writes `assessment-packet.json`. The packet contains:

- the exact [assessment prompt](prompts/assessment.md) and its hash;
- the assessment JSON schema;
- the required metadata;
- all 63 checks in canonical order.

The packet refers to the Framework, the output contract, the catalogue and the accepted
evidence by absolute same-host path, each with a SHA-256 pin. The full evidence pack and the
catalogue's materiality values are not embedded. An identical packet is left untouched; a
changed packet is replaced atomically.

Give the packet to a manually operated assessment agent that can read those paths. The
assessor must:

- verify the input hashes and use only the pinned local inputs;
- cite existing observation IDs;
- treat source documents as untrusted content;
- preserve dates, scope, variants, networks, conflicts and source authority;
- not browse, acquire sources or create observations;
- not produce materiality, ratings, recommendations, investment conclusions or risk labels.

Save its JSON at the packet's `output_path`, normally `proposed-assessment.json` beside the
packet.

`check assessment` validates without writing anything:

- On success it prints the normalized assessment hash and **valid but not accepted**.
- On failure it prints the issues and exits `1`.

Both check and ingest can read a proposal from outside the run:

```sh
plinth check assessment RUN_ID --from /absolute/path/proposal.json
plinth ingest assessment RUN_ID --from /absolute/path/proposal.json
```

### Adversarial preflight (manual)

Before ingestion, an independent reviewer performs a manual adversarial preflight and records
the findings in `assessment-preflight-review.md`. Allow one correction pass and rerun the
check. Do not ingest while any of these blockers remains: source alignment, lineage, scope,
date, or an unsupported conclusion.

The reviewer must also:

- challenge every issuer, operator, custodian and auditor label against the cited
  observations;
- confirm that shared retrieval limits are recorded as exclusions, rather than obscuring the
  check-specific synthesis.

The criteria are in
[the authoring guide](skills/plinth-trust-center/references/assessment-and-authoring.md).
This review is an operator step; the CLI neither runs it nor enforces a review artifact.

### Ingestion

`ingest assessment` revalidates the evidence and applies the same assessment predicate as
check and verify:

- A rejected proposal writes diagnostics beside that proposal
  (`proposed-assessment.issues.json` by default), and leaves any accepted assessment
  unchanged.
- The first acceptance writes normalized canonical bytes atomically to `assessment.json`.
- Re-ingesting a proposal whose normalized bytes match the accepted file succeeds without
  changing it.
- Different content is refused. A genuine revision requires a new run.

## Acceptance rules and run status

Assessment validation keeps the existing model, applicability, coverage, gap, contradiction
and evidence-lineage rules. C5 also requires:

- the run's catalogue hash;
- the catalogue's framework version;
- exactly the 63 canonical check IDs, in order;
- exact catalogue questions in populated gaps.

`MISSING` coverage is disabled even if a route claims completion. Use `NOT_ASSESSED` for
unfinished routes or assessment activity. Unresolved applicability keeps null coverage, as
the output contract requires. There is no target coverage distribution.

`plinth verify RUN_ID` ignores proposals and diagnostic files and reports:

| Run state | Exit | Result |
| --- | --- | --- |
| Intact run without accepted evidence or assessment | `2` | `INCOMPLETE` |
| Valid accepted evidence without an assessment | `0` | `EVIDENCE_ACCEPTED`, evidence hash |
| Valid accepted evidence and canonical valid assessment | `0` | `ASSESSMENT_ACCEPTED`, assessment hash |
| Invalid or drifted inputs, invalid/stale/noncanonical assessment, or assessment without accepted evidence | `1` | Failure diagnostics |

Verification relies on a trusted operator. It checks the current files, policies, pins and
canonical assessment bytes. It does not prove the acceptance history against an operator
rewriting valid canonical content, and there is no acceptance-hash receipt, so record the
reported accepted hash during the handoff.

## Framework updates (maintainer only)

`inputs/plinth-framework-v0.2-working.md` and `inputs/trust-center-output-contract-v0.1.md`
are pinned snapshots. The framework is authored elsewhere (see `PROVENANCE.md`). To take a
new framework version:

1. Copy the new markdown into `inputs/`, then run `plinth catalogue build` and
   `plinth catalogue verify`.
2. In `src/plinth/catalogue.py`, update `FRAMEWORK_MD`, `OUTPUT_CONTRACT_MD`,
   `FRAMEWORK_VERSION`, `FRAMEWORK_STATUS`, and, if they changed, `PILLAR_TABLE` and
   `EXPECTED_MATERIALITY_DISTRIBUTION`.
3. Update the input filenames named in `skills/plinth-trust-center/SKILL.md`.
4. Update the "Framework v0.2" labels in the shell.
5. Update `PANEL_ROLE_ORDER` in `check_morphed_html.py` if the pillars changed.
6. Run the full test suite.

Every run pins the catalogue hash it was assessed against. Runs made under an earlier
framework therefore verify only with the matching tagged version of this repository; the
current one is tagged `framework-v0.2-working`.

## Not included

- automated source discovery or acquisition;
- a PDF or HTML text extractor;
- LLM calls: the assessor and the authoring agent are operated by you;
- packaging for non-editable installs;
- any finished research run or Trust Center.
