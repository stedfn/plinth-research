# Trust Center Output Contract v0.1

**Status:** Working authoring contract for Plinth Framework v0.2 testing  
**Scope:** The allocator-facing projection of a product assessment  
**Not in scope:** Page design, interface implementation, scoring, recommendations, or a fixed Trust Center template

## 1. Purpose

A Trust Center is the product-specific expression of the Plinth methodology. It presents the checks that apply to a reviewed subject, the factual findings supported by the evidence, and the questions that remain unresolved. It is not a public rendering of the entire framework catalogue.

The output must help an allocator answer three questions without requiring fluency in smart-contract or blockchain terminology:

1. What is this product, who is behind it, and what does the holder own?
2. How does the product operate in normal conditions and under disruption?
3. What is established by evidence, and what cannot yet be concluded?

Plinth does not rank products, score their quality, recommend an allocation, or predict loss. A reader may form a favorable or unfavorable view from the same neutral evidence structure.

## 2. Output principles

### 2.1 Methodology before presentation

The Trust Center is generated from check-level applicability, observations, evidence and coverage. Presentation cannot change those results. Hiding a gap, changing its prominence, or rephrasing uncertainty as a conclusion is a methodology change, not copy editing.

### 2.2 Applicable projection, not catalogue dump

The Trust Center contains the subset of framework questions that apply to the reviewed subject, together with any questions whose applicability remains unresolved. Checks that demonstrably do not apply need not become public sections, although the underlying assessment retains their applicability decisions and support.

### 2.3 Plain institutional language

The executive layer states the institutional meaning first. Technical terms may appear where they are the clearest accurate language, but they must be explained or placed in the supporting layer.

For example:

- Prefer “One party can change the token contract without another party’s approval” to “The proxy administrator is an EOA.”
- Prefer “Transfers can be stopped by the issuer’s designated controller” to “The token exposes a single-key pause interface.”
- Prefer “Tokens issued on different networks rely on different mechanisms to remain part of one recognized supply” to a list of chain- and bridge-specific terms without explanation.

This translation must not erase who can act, what can be affected, which deployment or legal entity is in scope, when the evidence was observed, how authoritative the source is, or what remains uncertain.

### 2.4 Neutrality

The public output must not contain:

- materiality labels;
- gap rankings or sorting by internal importance;
- scores, grades, traffic lights or risk bands;
- “strong,” “weak,” “safe,” “unsafe,” “credible” or equivalent product judgments;
- recommendations or suggested allocation decisions.

All applicable gaps remain visible regardless of the check’s internal materiality. Commercial participation and payment cannot change which findings or gaps are shown for otherwise identical eligible inputs.

### 2.5 Traceability

Every factual statement and every gap must trace to the observations used to produce it. Those observations must trace to evidence or to reconstructible parent observations. Technical detail may be hidden by default, but it cannot be absent from the underlying record.

## 3. Required executive structure

Every Trust Center uses the following order. Sections may be short or omitted only as specified below; they are not pillar headings and need not mirror the internal check catalogue.

### 3.1 Product orientation

Give a concise factual description of:

- the product and reviewed subject;
- the form in which the investor holds an interest;
- the intended normal-course use of the product;
- the principal entry, holding and exit mechanics;
- the snapshot date and material scope limitations.

Where a useful traditional reference can be justified, provide a sourced operational comparison. Compare only factual differences in legal form, access, custody, settlement, transfer, fees, liquidity, redemption and value distribution. Do not claim that either form is better, safer, more efficient or more suitable.

The comparison must name the reference and explain why it is the appropriate comparator. If no defensible reference exists, omit the comparison.

### 3.2 Claim and party structure

Show, in plain language, the supported path from holder to underlying value:

```text
Holder
→ token or recorded interest
→ legal claim
→ issuing vehicle
→ asset owner
→ custodian
→ underlying asset
```

The structure must not imply that every product has a separate entity at every step. It must show the actual relationships or mark them as unresolved or not applicable.

At minimum, the executive layer must make the following easy to find:

- issuer or equivalent responsible entity;
- the legal nature of the holder’s claim;
- custodian, if custody is relevant;
- issuing vehicle and asset owner, where distinct;
- any unresolved break in the claim path.

The supporting party map identifies, where applicable:

- administrator;
- investment or asset manager;
- transfer agent or registrar;
- auditor or assurance provider;
- redemption operator;
- oracle, NAV or data provider;
- technical controller;
- material related-party relationships.

Absence of an identified party is a gap when the applicable check requires that identity. The output must not fill the blank by assuming that a prominent brand performs a particular role.

### 3.3 How value moves

Explain normal-course value mechanics in a coherent sequence:

- how the holder enters;
- what value is received or created;
- how underlying value or yield is generated;
- how price or NAV is established;
- which fees, spreads or deductions apply;
- how liquidity is provided;
- how the holder exits or redeems;
- how value is settled and distributed.

Where legal terms, on-chain execution and operational practice differ, state each layer separately. A stated redemption right is not evidence that the mechanism works as described or that liquidity is available under stress.

### 3.4 What remains unresolved

Present all applicable evidence gaps and all unresolved applicability questions. Use the gap contract in section 6. Do not label this section “material gaps,” “key risks” or “red flags.” Do not rank or sort gaps by severity or internal materiality.

A stable presentation order may follow pillar and check ID, the product’s operating sequence, or another deterministic neutral convention. It cannot be altered to make a participating issuer appear more complete.

### 3.5 Evidence coverage

Report factual counts, not qualitative bands. The minimum disclosure is:

- applicable checks assessed;
- `EVIDENCED`;
- `PARTIAL`;
- `MISSING`;
- `CONTRADICTORY`;
- `NOT_ASSESSED`;
- checks with `UNRESOLVED` applicability, reported separately because they have no coverage status.

`NOT_APPLICABLE` may be reported for completeness but must not be treated as successful coverage. A count is descriptive, not a score, and must not be combined into a percentage that implies product quality.

Coverage counts must include the assessment snapshot and scope. Two counts from different campaigns are not directly comparable unless their subjects, source cutoffs and declared acquisition scopes are compatible.

### 3.6 Technical evidence and methodology

Provide the technical basis necessary to audit the executive statements. Depending on the product, this may include:

- reviewed deployments and how they were bound to the issuer or product;
- smart-contract architecture and privileged functions;
- audit scope, dates, versions and limitations;
- oracle, NAV and data dependencies;
- bridge, cross-chain or canonical-supply assumptions;
- observed transaction or state evidence;
- infrastructure dependencies and recovery mechanisms.

This section is not a technology score. Technical evidence answers allocator questions in the five pillars unless a later methodology version establishes another category.

## 4. Executive statement contract

Every substantive executive statement follows this structure:

```text
Institutional question
→ plain factual answer
→ evidentiary limitation
→ optional technical basis
```

Example:

> **Who can stop transfers?** The issuer’s designated controller can pause transfers for the reviewed deployment. The available evidence identifies the controlling address but does not establish the identities or approval process of all people able to use it. Technical basis: the issuer-linked contract exposes a pause function controlled by the recorded administrator address as observed at the stated block.

The plain answer may be “not established.” It must not convert an unresolved identity, deployment, legal scope or date into a definitive conclusion.

### 4.1 Minimum semantic preservation

Simplification must preserve:

- **subject:** the entity, product, account, contract or deployment addressed;
- **scope:** which assets, jurisdictions, networks, accounts or processes are covered;
- **time:** the applicable, observed or evidence-as-of period;
- **authority:** who made or verified the source statement;
- **uncertainty:** what is not known, not covered or not independently supported.

### 4.2 Finding language

State findings as observations and supported relationships. Avoid adjectives that turn facts into ratings.

Acceptable:

- “The reviewed upgrade authority requires one approval.”
- “The attestation covers the named custody accounts as of 30 June; it does not cover the intervening period.”
- “The redemption terms allow suspension under the listed conditions.”

Not acceptable:

- “Upgrade governance is weak.”
- “Reserves are strong.”
- “Redemption risk is high.”

## 5. Claim and service-provider presentation

### 5.1 Relationship, not logo list

A party list is insufficient. The output must state what each party does, the source for that role, and whether the relationship is contractual, operational, technical, custodial, advisory or merely asserted.

### 5.2 Identity confidence

Differentiate:

- named legal entity;
- brand or trade name without established legal entity;
- technical address or key without established human/legal controller;
- candidate identity not adequately bound to the reviewed subject;
- unresolved identity.

Do not collapse these into one “provider” field.

### 5.3 Related parties

Disclose evidenced affiliations and common control among issuer, manager, custodian, administrator, auditor, technical controller and other material providers. Factual affiliation is not a Plinth judgment about the arrangement.

## 6. Gap contract

Every public gap contains the following fields.

### Question

The allocator question that cannot yet be answered completely.

### What is known

The facts supported by admissible evidence. If nothing relevant is established, say so plainly.

### What remains unresolved

The exact missing, incomplete, conflicting, stale or out-of-scope proposition. Do not say only “insufficient evidence.”

### What this means

Identify only the conclusion that cannot currently be supported. This field must not express importance, severity, probability, recommendation, product quality or a Plinth view.

Acceptable:

> Plinth cannot establish from the reviewed evidence that the named custodian holds all assets represented by the outstanding tokens as of the snapshot date.

Not acceptable:

> This is a critical custody risk.

### What would close it

Describe the proposition and type of evidence required, without prescribing a particular commercial vendor or making a guarantee that any single document will be sufficient. Examples include:

- an issuer-bound identification of the controlling legal entity;
- a current custody record covering the defined asset and account perimeter;
- independent confirmation of the relevant balance as of the assessment date;
- documented redemption terms plus evidence of the actual operating mechanism;
- a complete chain/deployment identity record for the claimed product-wide supply.

### Evidence

Link or identify the evidence that supports the known facts and the reason it does not close the question. Confidential sources require enough non-confidential metadata to make the support and limitation intelligible; otherwise the result must be narrowed or kept private.

### 6.1 Coverage-specific wording

- `PARTIAL`: identify which required propositions are supported and which are not.
- `MISSING`: state that sufficient evidence was not identified within the declared campaign scope; do not claim the evidence does not exist.
- `CONTRADICTORY`: identify the materially inconsistent applicable observations and why scope, precedence, supersession, versioning or freshness did not resolve them.
- `NOT_ASSESSED`: identify the declared acquisition route or assessment activity that was not completed.
- `UNRESOLVED` applicability: identify the structural fact required before Plinth can determine whether the question applies; coverage remains null.

## 7. Evidence-card contract

An evidence card makes the support for a finding inspectable. It should disclose, as applicable:

- source title and source type;
- author and publisher;
- commissioner or funder;
- relationship to the reviewed subject;
- whether the work is self-attestation, commissioned research, independent assurance, a rating, or unaffiliated research;
- publication, retrieval, effective and evidence-as-of dates according to the record type;
- exact subject and scope;
- relevant excerpt, extracted fact or deterministic observation;
- methodology or procedure performed;
- stated exclusions and limitations;
- visibility and access restrictions;
- provenance/integrity, admissibility and proposition-specific sufficiency.

Source prestige is not a substitute for proposition-specific sufficiency. Commissioned evidence is not automatically inadmissible. An issuer declaration remains an issuer declaration even when professionally presented.

## 8. External ratings and research

An external rating, score, recommendation or research conclusion may be presented as evidence about what its author concluded. It does not determine Plinth applicability, coverage or findings.

Whenever one appears, the Trust Center must identify:

- the exact rated or researched subject;
- the scale or conclusion used;
- the effective or publication date;
- the methodology and version, where available;
- whether the source is judgment-issuing, advisory, commissioned, or primarily evidence-surfacing;
- relevant relationships, funding or conflicts disclosed by the source;
- the underlying factual evidence separately, where available.

The output must not:

- translate a grade into a Plinth coverage state;
- treat a rating of a fund, issuer, reserve asset or stablecoin as a rating of a different token or deployment;
- imply that Plinth endorses or contradicts the external judgment;
- quote a conclusion without its subject, date and material scope limitations.

## 9. Product-orientation comparison

A traditional-reference comparison is included only when it improves understanding of what tokenization or the on-chain wrapper changes operationally.

The comparison must:

1. identify the reference product or structure;
2. cite the source for both sides;
3. compare like with like at a stated date and scope;
4. use factual dimensions only;
5. distinguish legal product differences from distribution-channel or technology differences.

Permitted dimensions are:

- legal form and claim;
- eligibility and access process;
- custody and recordkeeping;
- subscription and settlement;
- transferability and distribution;
- disclosed fees and spreads;
- normal-course liquidity and redemption;
- value or income distribution.

Market adoption, convenience, speed or cost may be reported only when supported by appropriate product-specific evidence. Marketing claims cannot be restated as facts.

## 10. Freshness, monitoring and successor outputs

Every Trust Center is an immutable historical snapshot with a source cutoff. Freshness is attached to the relevant evidence and findings, not converted into a hidden product grade.

A material change may reopen a finding when it affects:

- the reviewed subject or deployment;
- an applicability-driving structural observation;
- a party, role or legal claim;
- a privileged authority or approval process;
- asset, custody or reserve scope;
- pricing, fees, redemption or settlement;
- a material dependency, audit, incident or recovery mechanism;
- the effective period or sufficiency of supporting evidence.

New evidence or changed facts create a linked successor snapshot. They do not rewrite the earlier Trust Center.

## 11. Conformance requirements

A Trust Center conforms to this contract only if:

- it is a projection of applicable and unresolved checks, not a catalogue dump;
- issuer identity, legal claim and custodian are visible or explicitly unresolved/not applicable;
- every executive statement preserves subject, scope, time, authority and uncertainty;
- every gap follows the six-field gap contract;
- all applicable gaps remain visible without public materiality or ranking;
- coverage is presented as factual counts without aggregate quality bands;
- technical evidence remains traceable beneath the plain-language layer;
- external ratings cannot bypass Plinth evidence semantics;
- product comparison is sourced, factual and omitted when no defensible reference exists;
- historical outputs remain immutable and successor versions are linked.

This contract defines what the methodology must be capable of producing. It does not prescribe a user interface or authorize implementation work.
