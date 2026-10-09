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

Some fixed labels assume a public-only campaign (`bounded_public_evidence: true`). Rewrite
them for a privately enriched campaign. They are:

- "Public evidence supports" and "Public evidence does not establish";
- "Where public evidence stops";
- "Bounded public-evidence assessment";
- "Fixed public snapshot".

## Executive composition

Executive is one centered continuous column with no sidebar and exactly six blocks:

1. **Product orientation:** product, operator, evidence cutoff, participation boundary, and documented perimeter.
2. **What the holder holds:** holder-to-economic-asset chain, explicit unresolved legal links, and a separate service/control branch.
3. **How value moves:** enter, accrue, and exit cards without connector circles.
4. **Five pillar conclusions:** one factual conclusion and one unresolved boundary per pillar, with one route to Analyst. Pillar colors identify categories; they are not grades.
5. **What remains open:** a factual strip derived from canonical check records plus five pillar-level groups that partition every check exactly once. Prefill writes both; you write each group's question.
6. **Evidence boundary:** the public/private or supplied-evidence limit and an explicit route into Analyst.

Executive must not show any of the following:

- source citations, evidence classes or check states;
- check counts on pillar cards;
- coverage distributions;
- per-pillar grades.

Supporting check and observation IDs stay in semantic attributes. The framework strip shows
only counts computed from the assessment.

The main claim path ends at an underlying economic asset, portfolio, reserve, receivable, or
explicitly unresolved endpoint. The following belong in a separate branch:

- managers and administrators;
- custodians;
- networks and bridges;
- verification providers;
- settlement infrastructure.

Do not infer a missing legal link to make the diagram appear complete.

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
