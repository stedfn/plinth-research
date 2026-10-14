# Plinth v0.3 two-mode interface contract

The UI authority is `assets/v0.3-two-mode-shell.html`. It carries the approved v0.3
presentation and contains no product facts:

- embedded fonts and the cream canvas;
- typography, spacing, and rounded, contrast-led surfaces;
- the mode selector, the Analyst rail and the disclosures;
- responsive and print behaviour;
- the offline router.

Inspect the shell's `<body>` before authoring. Do not reconstruct the interface from
screenshots or from this summary, and do not edit the shell's `<head>`.

## Authority boundary

The shell governs presentation only. The run's accepted evidence and assessment govern every
fact, name, number, date, identifier, source, applicability, coverage result, gap,
contradiction and limitation.

## Transposition method

`scripts/prefill_shell.py` copies the shell and fills its mechanical regions, which are the
elements marked `data-fill`. You then replace the remaining `{{PLACEHOLDER}}`s. The shell
holds one example of each component; repeat it as needed and delete the ones you do not
use.

Keep exactly two reading modes:

- **Executive:** understand the product in two to three minutes.
- **Analyst:** inspect the complete research record and lineage.

The mode selector has a fixed width, so it does not move with adjacent text. Evidence links
in Executive switch to Analyst and reveal the corresponding pillar, check, observation,
source or gap. Direct fragments and browser history must keep that behaviour.

## Executive composition

The only Executive format is twelve questions in five groups. The shared shell holds one
`data-executive-slot`; prefill inserts `assets/executive-questions12.html` and writes
`data-executive-layout="questions12"` on `#v3-executive`. A custom `--shell` must have this
slot or a complete, marked twelve-question Executive. Old six-block shells are rejected.
There are no layout-selection options.

Use the bundled warm paper background, centred 960px column, lightweight title, rounded
chips, compact question index, soft white answer cards and inset limitations boxes. Preserve
the amber/rust documentary labels and the explicit Expand / Collapse cue with its chevron.
These colours identify answer categories; they are not a product rating or a severity scale.
Use the existing fonts, responsive layout and reduced-motion rules.

The questions and their default check mappings are defined in
`scripts/executive_questions.py`. Keep their headings and order. A known check outside a
question's mapping causes a warning to justify in `review.md`; an unknown ID fails.

| Group | Questions |
| --- | --- |
| A — Product & holder rights | 1–3 |
| B — Assets & backing | 4–6 |
| C — Returns & costs | 7–8 |
| D — Control & valuation | 9–10 |
| E — Exit & ownership records | 11–12 |

Every answer card contains the plain answer, a concrete unresolved-record question and a
native `details.evidence` disclosure called **Basis & limitations**. Its summary shows the
answer label, Expand / Collapse text and a chevron, with a 48px target. Supporting source
links and observation IDs may appear in that disclosure. Keep it collapsed in the delivered
draft unless documenting an expanded state for QA.

### Answer categories

The author chooses one category from the accepted observations, independently of coverage:

- **Source-described** (`source-described`, `p-part`): the answer restates at least one
  supporting observation about the question's core proposition. It requires supporting
  `data-observation-ids` on the question and links to them in its disclosure.
- **Answer unresolved** (`answer-unresolved`, `p-no`): no supporting observation answers
  the core proposition. Contextual observations may still be cited.

Keep each question's index label and disclosure label consistent. Source-described is not
independent verification, legal effect, deployment confirmation or complete check coverage.
The semantic review must check that the cited observation actually answers the proposition;
the verifier can prove only ID existence and linkage.

Executive may show source links and supporting IDs inside disclosures, plus aggregate
factual coverage counts. It must not show canonical record cards, evidence-class badges,
individual check-state badges, per-pillar grades or investment judgments.

### Conformance to the pinned output contract

| Contract requirement | Twelve-question element |
| --- | --- |
| §3.1 Orientation | Introduction, intended use, snapshot chip and evidence-context card |
| §3.2 Claim and parties; §11 identities | Q1 identifies issuer and holder claim; Q5 identifies custody and asset ownership; visible claim path beneath Q1 |
| §3.3 Value movement | Entry → Holding → Exit summary before Q7; Q7–Q12 explain mechanics |
| §3.4 Unresolved questions | Visible closing five-pillar summaries linking the complete gaps |
| §3.5 Coverage | Visible framework strip and factual aggregate coverage counts |
| §3.6 Technical basis | Closing technical/source/methodology routes, card disclosures and Analyst records |

The visible claim path covers holder → recorded interest → legal claim → issuer/vehicle →
asset owner → custodian → underlying asset. Use actual relationships; separate entities are
not mandatory. Mark every unsupported step unresolved or not applicable. Do not infer a
provider engagement from an issuer-named brand.

The framework strip, coverage counts and five open-question summaries stay visible, never
inside a closed disclosure. Keep all gaps in neutral pillar/check order. Coverage includes
applicable checks assessed, EVIDENCED, PARTIAL, MISSING, CONTRADICTORY and NOT_ASSESSED,
with unresolved applicability separate. MISSING remains zero and carries the compiler
limitation footnote; actual MISSING coverage is rejected.

Draft and pending publication-approval status remain visible. Preparation, extraction and
agent-review history belongs in the private review record. Accepted metadata is never
redacted from the payload: unwanted records require a successor run.

## Analyst composition

Analyst keeps one panel visible at a time, in this order:

1. Control
2. Assets & Backing
3. Economics
4. Governance & Compliance
5. Continuity
6. Claim and party structure
7. Legal and operating structure
8. Quantity boundaries
9. Evidence gaps
10. Evidence requests
11. Evidence registry
12. Observed technical state
13. Methodology and independence
14. Full research record

Keep the shell's desktop sidebar and compact mobile section menu.

Every pillar keeps five elements:

- the institutional narrative;
- the paired supported/not-established boundary;
- a product-specific factual display;
- named source links;
- one collapsed check register.

The full research record contains every canonical check, observation, source and locator
record.

Source pills use consistent horizontal and wrapped-row spacing. Decorative separators must
not be stranded on their own line. Contradiction cards use the same thin perimeter treatment
as other colored surfaces.

## Canonical and machine-readable state

Prefill renders every canonical check, observation and source record with these attributes:

```html
data-origin="canonical"
data-record-type="check|observation|source"
data-record-id="<canonical id>"
```

Check records also carry `data-applicability` and `data-coverage`. `data-coverage` is empty
when applicability is unresolved.

Fragment ids keep the canonical case, because accepted ids may differ only by case. Never
lowercase them:

- `check-PF-CONTROL-001`
- `observation-<observation_id>`
- `source-<source_id>`
- `locator-<locator_id>`
- `request-<check_id>`

Derived presentation components carry their supporting ids in `data-check-ids` and
`data-observation-ids`, space-separated. Every id named there must exist in the run.

The payload at `#plinth-research-state` is exactly
`{"assessment": <accepted assessment.json>, "evidence": <accepted documentary-evidence.json>}`:

- Every `<` is written as the JSON escape `<`, so a quoted `</script>` cannot end the
  element.
- It is not a projection, and it has no aliases.
- It embeds the records verbatim. That includes source URLs, original filenames,
  text-extraction tool names and, for manual uploads, the operator recorded at archive time.

Anything that must not be published therefore needs a new run with different records. Give
`plinth archive add --operator` a role rather than a person's name.

### Fixed hooks

| Hook | Values |
| --- | --- |
| Pillar keys (`data-pillar`, `checks-<key>`, `pillar-<key>` classes) | `control`, `backing`, `economics`, `governance` (catalogue `governance_compliance`), `continuity` |
| Pillar heading ids | `pillar-control`, `pillar-reserves` (Assets & Backing), `pillar-economics`, `pillar-governance-compliance`, `pillar-continuity` |
| Framework strip cells | `<div class="framework-cell" data-metric="M" data-value="N">` with the attributes in that order. Metrics: `total`, `applies`, `applicability-unresolved`, `applicable-not-fully-answered`. Prefill writes them. |
| Pillar with no evidence | `data-pillar-sources="none"` on the pillar `<section>`. Prefill sets it when the pillar's checks cite no observations, and such a pillar links no sources. Any other pillar links at least one source behind its own checks; links to other sources produce a checker warning. |
| `data-evidence-class` on citations | Taken from the source's `research_posture`. `self_attestation` maps to `issuer_declared`. Commissioned research, independent assurance, rating and unaffiliated research map to `third_party_authored`. Use `mixed` for a citation spanning both, and `analyst_derived` for a derived observation. |
| `data-state` on source records | Written by prefill: the source's disposition when it is not `IN_SCOPE`; otherwise the last acquisition outcome when nothing was acquired. |
| Links | Only `#fragment`, `http://` or `https://`. Prefill renders any other source URL as plain text. |

## Static and responsive behavior

- Keep the Ask Plinth control only in Analyst, clearly labelled `Static preview`; it makes no request and generates no answer.
- Omit fake Share, Export, monitoring, or other non-functional controls.
- At mobile widths, use 44 px targets and the compact Analyst menu.
- With JavaScript disabled, all substantive content remains reachable.
- Print expands substantive Analyst panels and disclosures.
- Load no remote runtime scripts, fonts, styles, images, frames, or data.

## Never import product content

The shell contains placeholders, not facts. Never carry anything from another Trust Center
into a new one, including:

- names, identifiers and networks;
- dates and quantities;
- source titles, counts and routes;
- records.

If the accepted records cannot populate a surface, state the evidence boundary rather than
leaving an attractive example.

## Browser acceptance

Verify each of these:

- mode switching on desktop and mobile;
- drill-down from Executive to Analyst;
- a check, an observation and a source fragment;
- back and forward;
- a malformed fragment such as `#%E0%A4%A`, after which the page must stay usable;
- keyboard focus;
- access with JavaScript disabled;
- print expansion;
- zero runtime network requests.

The final HTML still requires human review before publication.
