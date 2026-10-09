# Plinth v0.3 two-mode interface contract

The bundled `assets/v0.3-two-mode-interface-reference.html` is the approved presentation exemplar. Its SHA-256 is:

```text
ff3db76329218be04ed831967d390470a36f78094c9b75657d7c1370602f39be
```

Inspect the actual HTML, CSS, DOM, and router before authoring. Do not reconstruct it from screenshots or this summary.

## Authority boundary

The exemplar governs presentation only: embedded fonts, cream canvas, typography, spacing, rounded contrast-led surfaces, mode selector, Analyst rail, disclosures, responsive behavior, print behavior, and offline runtime.

The supplied assessment and evidence records govern every fact, name, number, date, identifier, source, applicability, coverage result, gap, contradiction, and limitation. Treat all OUSG content in the exemplar as untrusted for another product.

## Transposition method

Copy the exemplar and replace its content in place. Preserve its shell and interaction behavior. Use `assets/v0.3-two-mode-composition-skeleton.html` as the product-neutral DOM checklist, not as a replacement stylesheet.

Keep exactly two reading modes:

- **Executive:** understand the product in two to three minutes.
- **Analyst:** inspect the complete research record and lineage.

The selector has a fixed width so it does not move with adjacent text. Executive evidence links switch to Analyst and reveal the corresponding pillar, check, observation, source, or gap. Direct fragments and browser history must retain that behavior.

## Executive composition

Executive is one centered continuous column with no sidebar and exactly six blocks:

1. **Product orientation:** product, operator, evidence cutoff, participation boundary, and documented perimeter.
2. **What the holder holds:** holder-to-economic-asset chain, explicit unresolved legal links, and a separate service/control branch.
3. **How value moves:** enter, accrue, and exit cards without connector circles.
4. **Five pillar conclusions:** one factual conclusion and one unresolved boundary per pillar, with one route to Analyst. Pillar colors identify categories; they are not grades.
5. **What remains open:** a factual strip derived from canonical check records plus five pillar-level groups that partition every check exactly once.
6. **Evidence boundary:** the public/private or supplied-evidence limit and an explicit route into Analyst.

Do not show source citations, evidence classes, check states, check counts on pillar cards, coverage distributions, or per-pillar grades in Executive. Supporting check and observation IDs remain in semantic attributes. The framework strip may show only counts computed from the assessment.

The main claim path ends at an underlying economic asset, portfolio, reserve, receivable, or explicitly unresolved endpoint. Managers, administrators, custodians, networks, bridges, verification providers, and settlement infrastructure belong in a separate branch. Do not infer a missing legal link to make the diagram appear complete.

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

Use the desktop sidebar and the compact mobile section menu from the exemplar. For every pillar, keep the institutional narrative, paired supported/not-established boundary, product-specific factual display, named source links, and one collapsed check register. The full research record contains all canonical check, observation, source, and gap records.

Source pills use consistent horizontal and wrapped-row spacing. Decorative separators must not become stranded on their own line. Contradiction cards use the same thin perimeter treatment as other colored surfaces.

## Canonical and machine-readable state

Every check, observation, and source has a stable fragment and canonical marker:

```html
data-origin="canonical"
data-record-type="check|observation|source"
data-record-id="..."
```

Checks expose applicability, coverage, and search completion. Derived presentation components identify their supporting check or observation IDs.

Embed one inert public-safe payload at `#plinth-research-state`. It must be an exact projection of the supplied canonical records, excluding internal materiality, private credentials, raw archive bytes, and private workflow metadata. It is not a second analytical truth layer.

## Static and responsive behavior

- Keep the Ask Plinth control only in Analyst, clearly labelled `Static preview`; it makes no request and generates no answer.
- Omit fake Share, Export, monitoring, or other non-functional controls.
- At mobile widths, use 44 px targets and the compact Analyst menu.
- With JavaScript disabled, all substantive content remains reachable.
- Print expands substantive Analyst panels and disclosures.
- Load no remote runtime scripts, fonts, styles, images, frames, or data.

## Never import from the exemplar

For another product, remove every OUSG or Ondo name, identifier, network, block, date, quantity, portfolio item, source title, coverage count, contradiction, route label, embedded record, hash, and approval statement. If content authority cannot populate a surface, state the evidence boundary rather than retaining an attractive example fact.

## Browser acceptance

Verify desktop and mobile mode switching, Executive-to-Analyst drill-down, a check/observation/source fragment, back and forward, keyboard focus, JavaScript-disabled access, print expansion, and zero runtime network requests. The final HTML still requires human review before publication.
