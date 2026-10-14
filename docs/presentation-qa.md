# Twelve-question presentation QA

The Executive now has one twelve-question format. Its visual target is the approved
private reference: warm paper, a 960px column, lightweight title, compact index, rounded
white answer cards, inset limitation boxes, warm documentary labels and clear disclosures.
Only generic visual patterns were reused. All committed example facts are synthetic.

## Automated verification

- PASS — full repository tests: 468 tests.
- PASS — catalogue build check and verification: unchanged 63 checks.
- PASS — existing sole HTML verifier checks the actual twelve-question synthetic page.
- PASS — exact accepted payload, canonical markers, findings, IDs and source links.
- PASS — layout, category linkage, conformance structure, visible accounting and mapping guards.
- PASS — shared HTML/Markdown references, cited acquisition dates, superseded sources and escaping.
- PASS — date boundaries, declared scopes, disabled MISSING coverage and deterministic prefill.
- PASS — original theme skin bytes and embedded fonts retained; no second font set.
- PASS — static checks find no external runtime assets in the generated page.
- PASS — new assets and example script contain no reference-product names or protected facts.
- PASS — request spacing and single-panel width rules preserve the shared interface fixes.

## Browser acceptance

**NOT RUN.** The session's browser policy denied local-file access. No alternate-browser
or local-server workaround was attempted. Automated source inspection is not a browser pass.

| Check | Result |
| --- | --- |
| Desktop Executive, collapsed and expanded disclosure | NOT RUN |
| Mobile Executive, layout and overflow | NOT RUN |
| Desktop and mobile Analyst, mode switching | NOT RUN |
| Question anchors and cross-panel source/observation links | NOT RUN |
| Back and forward; malformed fragment recovery | NOT RUN |
| Keyboard focus and disclosure controls | NOT RUN |
| JavaScript-disabled reading | NOT RUN |
| Print expansion and restoration | NOT RUN |
| Browser network log showing zero runtime requests | NOT RUN |

The requested screenshots remain pending: `executive-desktop.png`, `executive-mobile.png`,
`analyst-desktop.png` and `analyst-mobile.png`. A human browser pass, including comparison
against the approved private reference, is required **before merge**. Do not describe visual
acceptance or publication approval as completed.

## Reproduce

Use the synthetic demo and verifier commands in README. Choose a new output directory.
Inspect question 5 and its expanded Basis & limitations, a long answer, the question index,
visible unresolved/coverage sections and the single technical-state panel. Confirm three
index columns on desktop, two on mobile and one below 380px, without clipping.

Publication remains a separate human decision.
