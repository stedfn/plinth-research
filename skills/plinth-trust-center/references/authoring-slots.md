# Populate the template from an accepted compiler run

The accepted evidence, assessment and catalogue determine facts. The shell determines
presentation. Start with prefill, not a previously authored product page or the preview.
Do not invent names, fees, provider engagements, quantities, rights, observations or states
to make a component look populated.

## Inputs and sequence

1. Read the accepted `assessment.json`, `documentary-evidence.json` and pinned catalogue.
   Run `plinth verify` and require ASSESSMENT_ACCEPTED.
2. Run `prefill_shell.py` with those files and the recorded product name. It inserts the
   twelve-question Executive and renders the canonical records, payload, counts and requests.
3. Populate remaining narrative slots from existing observations. Prefill lists their names.
   The Analyst sections carry `data-authoring-section` and a distinct uppercase prefix.
4. Fill or remove citation slots appropriately. An unsupported proposition stays unresolved.
   Never assign a first available observation or source to every statement.
5. Run the sole HTML verifier, check source meaning and scope, then inspect desktop/mobile.

Generated `data-fill` regions become normal HTML after prefill. Leave their records,
counts, questions and exact accepted-record payload unchanged. Never edit accepted files
or redact metadata inside the payload; changed facts require a successor compiler run.

## Executive slots

Each question has its own slots, `Q1` through `Q12`:

| Slot suffix | Fill with |
| --- | --- |
| ANSWER | Concise answer from observations; HTML paragraphs are allowed |
| LIMITATION | The exact unresolved proposition and records that would resolve it |
| STATE | `source-described` or `answer-unresolved`, independently of check coverage |
| LABEL / CLASS | `Source-described` / `p-part`, or `Answer unresolved` / `p-no` |
| OBSERVATION IDS | Space-separated accepted observation IDs supporting the answer; empty when none |
| PILLARS | The relevant framework pillar names |
| BASIS | Supporting explanation with links to every named observation and the actual sources |

The twelve headings, order, default check mappings and index/disclosure labels stay
consistent. Source-described requires an observation answering the core proposition;
context alone is insufficient. Do not infer that a source description verifies operation.

`SUBJECT SUMMARY`, `PARTICIPATION BOUNDARY`, `CLAIM PATH`, `ENTRY SUMMARY`, `HOLDING SUMMARY`,
`EXIT SUMMARY` and `EVIDENCE BOUNDARY TEXT` are separate narrative slots. Fill them from the
run. The claim path must identify unsupported relationships explicitly. The snapshot,
cutoff, declared scope and framework accounting are generated, not authored.

## Analyst slots

| Prefix | Section and intended content |
| --- | --- |
| CONTROL | Authorization, execution, and changes or restrictions |
| BACKING | Assets, custody/title, and verification |
| ECONOMICS | Entry, value/costs, and exit |
| GOVERNANCE | Issuer/claim, eligibility, and party roles |
| CONTINUITY | Normal exit, disruption, and reconciliation |
| CLAIM | Holder-to-asset relationships, recorded support, and unresolved links |
| LEGAL | Issuer/jurisdiction, governing instrument, ownership, and agreements |
| QUANTITY | Identifiers, quantities, dates and their separate populations/scopes |
| GAPS | Neutral gap themes pointing to complete canonical check records |
| REQUESTS | Introduction to compiler-rendered requests; do not rewrite generated gaps |
| SOURCES | Introduction to generated references and the full source registry |
| TECHNICAL | Product-bound deployments, state records, scope and limitations |
| METHODOLOGY | Campaign boundary; framework definitions and distribution remain fixed |
| APPENDIX | Technical anchors and introductory text; complete records are generated |

The five pillars use `PREFIX_INTRO`, `PREFIX_NARRATIVE`, `PREFIX_KNOWN`, `PREFIX_UNRESOLVED`,
`PREFIX_CHECK_IDS` and `PREFIX_OBSERVATION_IDS`. Their three fact cards have topic-specific
slots, such as `CONTROL_AUTHORIZATION` and `BACKING_CUSTODY`. Keep each statement's
citation beside it. Use explicit unresolved wording where the accepted records stop.

The CLAIM and LEGAL tables separate each layer's `*_KNOWN`, `*_UNRESOLVED` and `*_CITATIONS`.
They do not assume that an issuer, asset owner and custodian are distinct entities.
Repeat rows or fact cards only when the accepted inputs need them; lone cards fill width.

### Citation slots

Every `*_CITATIONS` slot accepts a complete citation component or an empty string.
Use existing observation and source IDs, preserving case. For example, the generic shape is:

```html
<span class="inline-citations" data-origin="derived-presentation"
      data-observation-ids="ACCEPTED_OBSERVATION_ID">
  <a class="claim-source inline-source" href="#source-ACCEPTED_SOURCE_ID"
     data-evidence-class="CLASS_FROM_SOURCE_POSTURE">RECORDED_SOURCE_TITLE</a>
</span>
```

The capitalized values above are instructions, not literal IDs or values to publish.
Use the source-posture mapping in `scripts/trust_center_records.py`; do not guess its class.
A pillar with `data-pillar-sources="none"` leaves citation slots empty. Missing evidence is
not replaced with invented source links, operators or acquisitions.

## Optional components and empty inputs

The default does not include a sample conflict alert or legal status badge. Add a factual
conflict description only when the accepted observations support it, with subject, scope,
dates and precedence qualifications. A different source version does not automatically
mean CONTRADICTORY coverage. Canonical contradiction records always remain in the register.

Remove unused optional rows/cards rather than fill them with repeated generic text. Retain
the supported/unresolved boundary, complete check register and all applicable gaps.
The layout handles one or several fact cards, wrapped labels and long identifiers.

`examples/build_presentation_demo.py` is an **empty-evidence preview**. It has zero sources
and observations, and unresolved applicability with null coverage for every check. Its
visible text is authoring guidance, never fictional product research. Do not copy that
guidance into an authored Trust Center; start from the accepted run and raw shell.
