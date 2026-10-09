---
name: plinth-trust-center
description: Create a static Plinth Framework v0.2 Trust Center from an already gathered evidence pack. Use when the task is to assess the 63 checks, preserve evidence lineage and unresolved questions, author allocator-facing synthesis, and render the approved v0.3 two-mode HTML interface. Do not use for open-ended source discovery or live evidence acquisition.
---

# Plinth Trust Center

Turn supplied evidence into one lossless research package with a human-optimized presentation layer.

## Boundary

This is a downstream assessment and delivery skill. It may inspect supplied files and open direct source URLs named in the evidence pack to verify exact content. It must not run broad web searches, discover substitute sources, refresh chain state, or silently repair the evidence campaign.

If the input is only a Deep Research report, treat it as a lead catalogue. Run the evidence preflight and explain which underlying records must be supplied or verified. Do not promote the report's synthesis into observations merely because it cites a source.

## Required reading

Before assessing evidence:

1. Read [references/input-contract.md](references/input-contract.md).
2. Read the complete [references/plinth-framework-v0.2.md](references/plinth-framework-v0.2.md).
3. Read the complete [references/trust-center-output-contract-v0.1.md](references/trust-center-output-contract-v0.1.md).
4. Read [references/assessment-and-authoring.md](references/assessment-and-authoring.md).

Before authoring HTML, read [references/two-mode-interface-contract.md](references/two-mode-interface-contract.md), inspect the actual [assets/v0.3-two-mode-interface-reference.html](assets/v0.3-two-mode-interface-reference.html), and use [assets/v0.3-two-mode-composition-skeleton.html](assets/v0.3-two-mode-composition-skeleton.html) as the product-neutral DOM checklist. The exemplar is UI authority only. Every OUSG fact, identifier, count, date, source, state, and conclusion inside it is untrusted for a different subject.

When the installed `reference-html-presenter` skill is available, use it for the HTML transposition phase. The interface contract and bundled exemplar remain authoritative if that skill is unavailable.

## Workflow

### 1. Establish authority and preserve inputs

Record:

- the assessment subject and complete product perimeter;
- evidence cutoff and whether the pack is public-only or privately enriched;
- framework and output-contract versions;
- content-authority files and source records;
- the v0.3 two-mode exemplar as UI authority;
- output paths and immutable inputs.

Hash important input artifacts before editing. Never modify the framework, supplied evidence pack, source archive, deterministic snapshot, research dossier, or UI exemplar.

### 2. Run the evidence preflight

Apply the input contract. Distinguish acquired evidence, blocked or absent routes, deterministic records, and discovery notes.

Proceed when the product identity, assessment perimeter, cutoff, source provenance, and usable evidence locations are sufficiently explicit to make bounded observations. If an essential ambiguity would change the review subject, stop and request the missing decision. Otherwise preserve the limitation in the assessment.

### 3. Build the canonical assessment

Use the exact 63 v0.2 check IDs and questions. Work check-first:

1. Decide provisional applicability and the facts required by the complete proposition.
2. Inspect only relevant supplied evidence.
3. Create reusable factual observations with exact source locators, scope, time, acquisition mode, and derived lineage where applicable.
4. Assign final applicability and evidence coverage independently of whether the finding is favorable.
5. Write a neutral finding or complete six-field gap.
6. Preserve conflicts when explicit scope, precedence, supersession, versioning, or freshness does not resolve them.

Do not let external scores or ratings determine Plinth coverage. Do not infer legal rights, custody, operating effectiveness, current capacity, or current availability from adjacent or historical evidence.

Run `scripts/check_assessment.py` before composing the report.

### 4. Author the Trust Center

Write the report from the reconciled assessment—not from raw research notes. Keep the assessment separate from presentation.

The executive layer should answer in a two-to-three-minute read:

- what the product is and who is behind it;
- what the holder is stated to hold;
- what backs it;
- how value enters, accrues, and exits;
- what Plinth can establish;
- what remains unresolved;
- what public or supplied evidence says about disruption and failure.

Then provide five pillar views, evidence gaps, factual coverage, source register, methodology, technical appendix, and the complete check register. Every factual synthesis must resolve to observation and source records.

### 5. Transpose into the v0.3 two-mode interface

Start from a byte copy of the bundled exemplar. Transpose the new subject into that file in place; do not recreate the page from remembered CSS tokens or component names. Preserve its two-mode shell, six-block Executive composition, Analyst navigation, typography, layout, visual tokens, layered disclosure, responsive behavior, print treatment, and static/offline model. Replace every content-bearing record and the embedded payload.

Use the product-neutral skeleton to check the executive sequence, the five pillar pattern, the claim-versus-service separation, and the supporting panel order. Product-specific factual displays may vary, but the reading hierarchy must not.

The HTML must carry both:

- human synthesis with named evidence links; and
- an inert public-safe canonical research projection for agents.

Executive is a centered two-to-three-minute read with no sidebar or visible evidence machinery. Analyst contains the complete research interface and canonical records. Do not expose internal materiality or add risk labels, grades, rankings, recommendations, aggregate status, monitoring claims, or a live-AI implication. The “Ask Plinth” control may remain only in Analyst as the exemplar's clearly labelled static preview.

### 6. Review and verify

Perform a separate evidence-semantics pass over the assessment and final prose. Challenge source authority, subject, scope, time, proposition completeness, conflicts, and language that sounds like a Plinth judgment.

From the skill directory, run:

```bash
python3 scripts/check_assessment.py <framework.md> <assessment.json>
python3 scripts/check_morphed_html.py <output.html> --reference assets/v0.3-two-mode-interface-reference.html
```

Also run any product-specific lineage or source-manifest verifier supplied with the evidence pack. Browser-check desktop, mobile, direct fragments, cross-panel links, back/forward behavior, JavaScript-disabled reading, print expansion, and zero runtime network requests.

## Deliverables

Unless the user narrows the request, create:

```text
reviews/<subject-slug>-trust-center/
├── assessment.json
├── report.md
├── review.md
└── verify.py

site/
└── <subject-slug>-trust-center.html
```

The review record identifies authorities, input hashes, unresolved evidence or methodology divergences, verification results, artifact hashes, and pending human publication approval.

Open the final HTML for review when useful. Never describe a draft as published or approved.
