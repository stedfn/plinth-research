---
name: plinth-trust-center
description: Turn one compiler-accepted Plinth run (its accepted documentary-evidence.json and assessment.json) into a static Plinth Framework v0.2 Trust Center in the v0.3 two-mode interface. Use after `plinth verify` reports ASSESSMENT_ACCEPTED, to author the allocator-facing synthesis and the HTML. Do not use it for source discovery, evidence intake, or assessment; the compiler pipeline in the repository README does those.
---

# Plinth Trust Center

Turn one accepted research run into a human-readable Trust Center in which every fact
resolves to the run's canonical records.

## Where this skill sits

This skill lives in `skills/plinth-trust-center/` of the plinth-research repository. Every
path below is relative to the repository root. That root is two directories above this
file's real location, so the paths still hold when the skill is reached through a symlink.

The compiler produces the canonical records, and this skill presents them:

1. The `plinth` CLI runs research intake, evidence ingestion and assessment, as described
   in `README.md` (stages C1–C5). Discovering and acquiring sources happens there, within
   the campaign's declared routes.
2. This skill starts only when `plinth verify RUN_ID --runs-root RUNS` reports
   `ASSESSMENT_ACCEPTED`. From then on, do not search for, acquire or add evidence,
   observations or assessment results. If the accepted records are thin, say so in the
   Trust Center, or return to intake with a new run.

## Inputs

- The run's accepted `documentary-evidence.json` and `assessment.json`: content authority.
- `inputs/catalogue.json`, `inputs/plinth-framework-v0.2-working.md` and
  `inputs/trust-center-output-contract-v0.1.md`: framework authority.
- `skills/plinth-trust-center/assets/v0.3-two-mode-shell.html`: UI authority.

Never modify these files.

## Required reading

Before authoring, read:

1. `inputs/plinth-framework-v0.2-working.md`, complete.
2. `inputs/trust-center-output-contract-v0.1.md`, complete.
3. [references/assessment-and-authoring.md](references/assessment-and-authoring.md).
4. [references/two-mode-interface-contract.md](references/two-mode-interface-contract.md).
5. The `<body>` of the shell. Do not read its `<head>`, which is 240 KB of CSS and embedded
   fonts that is copied, never edited.

[references/input-contract.md](references/input-contract.md) is the guidance for building the
evidence pack. Read it if you also run the research stage.

## Workflow

### 1. Record the inputs

Record:

- the run ID and runs root;
- the accepted evidence and assessment hashes that `plinth verify` prints;
- the catalogue hash;
- the evidence cutoff;
- whether the campaign is public-only (`bounded_public_evidence`).

Content authority is the accepted records plus the catalogue. UI authority is the shell.

### 2. Verify the run

```sh
plinth verify RUN_ID --runs-root RUNS
```

Stop unless it reports `ASSESSMENT_ACCEPTED`.

### 3. Prefill the mechanical parts

```sh
python3 skills/plinth-trust-center/scripts/prefill_shell.py --product "PRODUCT NAME" \
  --assessment RUNS/RUN_ID/assessment.json \
  --evidence RUNS/RUN_ID/documentary-evidence.json \
  --catalogue inputs/catalogue.json --out trust-centers/SLUG/index.html
```

This copies the shell and renders every region marked `data-fill`:

- the canonical check, observation, source and locator records;
- the pillar check registers, evidence requests and methodology counts;
- the Executive framework figures and open-evidence partition;
- the escaped payload and the product name.

It marks each pillar whose checks cite no observations with `data-pillar-sources="none"`,
and it lists the placeholders left for you.

### 4. Author the narrative

Replace every remaining `{{PLACEHOLDER}}` in `index.html` from the accepted records. Follow
[references/assessment-and-authoring.md](references/assessment-and-authoring.md) and
[references/two-mode-interface-contract.md](references/two-mode-interface-contract.md). This
covers:

- the six Executive blocks. Together they are a two-to-three-minute read covering:
  - what the product is and who is behind it;
  - what the holder is stated to hold, and what backs it;
  - how value enters, accrues and exits;
  - what Plinth can establish and what remains unresolved;
  - the evidence boundary;
- for each pillar: the narrative, the boundary between what is supported and what is not
  established, a product-specific factual display, and named source links;
- the claim-structure, legal, quantity, gap, technical-state and methodology panels.

Rules while authoring:

- Every factual statement resolves to observations and sources in the run.
- Repeat a component by copying the example the shell gives, and delete examples you do not
  need.
- In a pillar marked `data-pillar-sources="none"`, delete the example citations.
- Leave the canonical records, the payload and every region prefill rendered exactly as it
  wrote them.
- Do not expose internal materiality.
- Do not add risk labels, grades, rankings, recommendations, aggregate status, monitoring
  claims, or anything implying a live AI.
- "Ask Plinth" remains the static preview, in Analyst only.

### 5. Review and verify

Make a separate evidence-semantics pass over the prose. Challenge each statement's source
authority, subject, scope, time and proposition completeness, check that conflicts are
preserved, and remove language that sounds like a Plinth judgment. Then run:

```sh
plinth verify RUN_ID --runs-root RUNS
python3 skills/plinth-trust-center/scripts/check_morphed_html.py trust-centers/SLUG/index.html \
  --reference skills/plinth-trust-center/assets/v0.3-two-mode-shell.html \
  --assessment RUNS/RUN_ID/assessment.json \
  --evidence RUNS/RUN_ID/documentary-evidence.json \
  --catalogue inputs/catalogue.json
```

Fix every `FAIL`. Fix each `WARN`, or justify it in `review.md`.

Then check the page in a browser:

- desktop and mobile, in both modes;
- direct fragments, cross-panel links, back and forward, and a malformed fragment;
- keyboard focus, JavaScript disabled, and print;
- zero runtime network requests.

## Deliverables

```text
trust-centers/<subject-slug>/
├── index.html
├── report.md
└── review.md
```

`trust-centers/` is gitignored.

- `report.md` is the plain-text report, using the report structure in
  [references/assessment-and-authoring.md](references/assessment-and-authoring.md).
- `review.md` records:
  - the run ID;
  - the accepted evidence and assessment hashes, and the catalogue hash;
  - the checker output, including warnings;
  - any unresolved methodology divergences;
  - the pending human publication approval.

Never describe a draft as published or approved.
