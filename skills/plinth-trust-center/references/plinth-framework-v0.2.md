# Plinth Framework v0.2 — Working Draft

**Status:** Pre-consolidation testing draft  
**Purpose:** Plinth’s internal evidence-first methodology beneath Reviews and Trust Centers  
**Catalogue basis:** The 63 checks and their internal materiality assignments are retained unchanged from Plinth Framework v0.1

## Core commitments

### Coverage is not risk

Plinth records whether an allocator question is answered with sufficient evidence. It does not rate whether the answer is favorable, estimate loss, score the product, or recommend an investment. Opposite findings can have the same coverage status: a control threshold of 1-of-1 and a threshold of 7-of-9 can both be `EVIDENCED` when each is established by sufficient evidence.

### Commercial neutrality

**Commercial participation and payment cannot change applicability, materiality, admissibility, sufficiency, coverage, roll-ups, findings, or the visibility of gaps for otherwise identical eligible inputs.**

This commitment applies to public Reviews, participating-issuer Trust Centers and any other Plinth output. Better evidence access can produce different evidence results. Payment cannot change how the same eligible evidence is treated.

### Evidence before conclusion

Every check result traces to observations. Every observation traces to identifiable evidence or to reconstructible parent observations. Models may find, extract or propose observations; they cannot create authoritative facts on their own.

### Non-discovery is not absence

Plinth does not turn a failed search, missing access or an unidentified feature into a factual conclusion. `DOES_NOT_APPLY`, authoritative absence and `MISSING` each require their own positive evidentiary basis.

### External judgment remains external

An external rating, risk score, recommendation or research conclusion may be evidence that its author reached that exact conclusion about a stated subject, date, scale and methodology. It never determines Plinth applicability or coverage and never becomes a Plinth rating or recommendation. The underlying factual evidence is assessed separately where it is available.

### Historical outputs are immutable

Published framework versions and product snapshots retain the methodology and evidence basis under which they were produced. Corrections, new evidence and changed facts create linked successor versions rather than silently rewriting historical state.

## 1. Purpose and operating role

Plinth Framework v0.2 defines the diligence questions Plinth asks, when they apply, the observations needed to answer them, and the evidence principles used to determine coverage. It is the internal methodology used to produce consistent Reviews and Trust Centers across structurally different on-chain investment products.

The framework catalogue contains 63 asset-independent checks: 8 Control, 13 Assets & Backing, 14 Economics, 16 Governance & Compliance, and 12 Continuity. Each check has exactly one owning pillar, a fixed internal materiality within this version, a conceptual applicability condition, expected factual observations, likely acquisition modes and a proposition-specific evidence/sufficiency principle.

A Trust Center is a product-specific projection of the applicable checks, not a public rendering of all 63. Its organization may compose findings across pillars to answer an allocator’s practical question, but presentation cannot change check ownership, applicability, observations or coverage.

This document is a methodology, not a software specification, interface design, rule engine, risk rating, investment recommendation or asset-specific checklist. It does not consolidate the catalogue or decide the deferred candidates identified for later testing.

Companion documents in this working package are the [Trust Center Output Contract](trust-center-output-contract-v0.1.md) and the [External-Methodology Crosswalk](external-methodology-crosswalk.md).

## Authored change summary from v0.1

| Area | v0.1 baseline | v0.2 working change |
| --- | --- | --- |
| Operating role | Testing methodology for Reviews and Trust Centers | Explicitly defined as Plinth’s internal methodology beneath both output types |
| Core commitments | Present within shared semantics | Coverage-not-risk and payment neutrality moved to the opening page and made output obligations |
| Catalogue | 63 checks | Same 63 IDs, questions, substantive definitions and internal materiality assignments |
| `backing` label | Reserves | Provisional display label **Assets & Backing**; internal ID and ownership unchanged |
| Materiality | Internal `HIGH / MEDIUM / LOW` baseline | Assignments retained; public labels, ranking, sorting, scores and traffic lights expressly prohibited |
| Allocator composition | Findings primarily organized by methodology | Explicit claim path and party/service-provider architecture composed from existing observations |
| Evidence provenance | Source authority, independence and integrity separated | Author, publisher, commissioner/funder, subject relationship and research posture made explicit |
| Reserve verification | Proposition-specific evidence standard | Procedure, scope, period, cadence, relationship, assurance type and limitations expressly preserved; no brand proxy |
| External judgments | Kept separate from evidence coverage | Ratings and research conclusions explicitly typed as external evidence inputs that cannot determine Plinth outputs |
| Technical integrity | Technical evidence distributed across pillar questions | Named as a deferred test domain; no sixth pillar and no new check |
| Allocator-facing output | Not specified as a separate contract | Companion contract defines executive order, plain-language translation, gap explanations and factual coverage counts |
| Consolidation | Future testing could motivate changes | Candidate questions recorded, but no catalogue or pillar decision is made in this phase |

## 2. Shared methodology semantics

### 2.1 Applicability comes before coverage

Every check first receives one of three applicability outcomes:

- **APPLIES:** the structural condition for asking the question is adequately established.
- **DOES_NOT_APPLY:** adequate evidence establishes that the structural condition is absent.
- **UNRESOLVED:** the facts required to decide applicability have not been adequately established.

Only `DOES_NOT_APPLY` produces a coverage status of `NOT_APPLICABLE`. `UNRESOLVED` remains visible and has no coverage status. It must not be converted into `NOT_APPLICABLE` merely because the relevant feature was not found, or into `NOT_ASSESSED` merely because the assessment could not determine whether the check applies.

Applicability must depend on structural facts established independently of the check being gated. A check cannot depend for its applicability on an observation that can exist only after that same check is deemed applicable. More generally, the evaluation dependency graph must remain acyclic.

### 2.2 The review subject is the complete relevant product system

The review subject is the product as an operational, economic, legal and technical system—not merely a token contract, issuer or offering document. Its boundary includes every entity, deployment, representation, holder class, service relationship and off-ledger record needed to answer an applicable framework question.

Candidate members remain visible until supported, excluded on evidence or retained as unresolved. A candidate deployment does not become part of the established product merely because an address was found, and it does not disappear merely because issuer binding remains unresolved. Intentional exclusions state their evidentiary reason and expected effect on coverage.

### 2.3 Check materiality is different from scope inclusion

Two distinct judgments use similar language:

- **Check materiality** asks how important it is for an allocator to resolve a framework question.
- **Scope or population inclusion** asks whether a particular action, reserve item, route, obligation, entity, function, dependency, scenario, weakness or other candidate member is significant enough that the applicable check must account for it.

The first is a property of the check definition. The second determines the factual perimeter over which a check is answered. A low- or medium-materiality check may still require complete treatment of every member admitted to its scope, while a high-materiality check does not make every conceivable candidate member relevant.

“Material” cannot operate as an undocumented exclusion mechanism. Four principles apply:

1. **Inclusion:** Include a candidate member when omitting it could materially change applicability, the factual answer, evidence completeness or an allocator’s interpretation.
2. **Discovery:** Declare and execute asset-appropriate discovery across the known structural paths by which members could enter the population.
3. **Unresolved candidates:** Retain potentially includable but unresolved members. They prevent a complete-population claim where their inclusion could materially affect the answer.
4. **Exclusions:** Record intentional exclusions, their evidentiary basis and their effect on the result. A material exclusion prevents a full-perimeter claim.

A population is sufficiently complete only when declared discovery covers all known material entry paths, every discovered candidate is classified as included, evidenced-excluded or unresolved, and no unresolved candidate could materially alter the bounded answer. This is a conceptual standard rather than a universal discovery algorithm.

### 2.4 Coverage records evidence completion, not risk

For an applicable check, Plinth uses:

- **EVIDENCED:** admissible evidence supports all observations needed to answer the bounded question.
- **PARTIAL:** at least one necessary part is supported, but the answer is incomplete.
- **MISSING:** the declared assessment was completed and no admissible evidence sufficient to answer the question was identified.
- **CONTRADICTORY:** materially inconsistent admissible observations about the same proposition, subject, scope, unit and overlapping period remain unresolved.
- **NOT_ASSESSED:** the check applies, but the declared assessment was not completed.

`MISSING` is bounded to the declared assessment scope. It does not mean that evidence does not exist. A skipped or failed required acquisition path cannot silently produce `MISSING`.

`CONTRADICTORY` applies only where materially inconsistent, currently applicable and admissible observations cannot be resolved by explicit scope, precedence, supersession, versioning or freshness rules. Newer evidence does not win implicitly.

Coverage says nothing about whether a finding is good or bad. An authoritatively established absence of a recovery plan can be a complete adverse finding rather than an evidence gap.

### 2.5 The framework is broader than a campaign’s evidence access

The framework defines what should be known. An assessment campaign declares which evidence-access paths it will attempt. A public Review and a Trust Center use the same checks, applicability semantics, evidence standards and coverage meanings, but may have different access to private records, systems, personnel or workpapers.

If evidence is available only through private access outside a public campaign’s declared scope, the applicable check may remain `NOT_ASSESSED`; lack of access is not evidence that the proposition is unsupported. If a required public acquisition path was in scope, completed and produced no qualifying evidence, `MISSING` may be appropriate. When private acquisition is included, its evidence is assessed through the same gates. The campaign discloses enough about access and exclusions for an allocator to understand the boundary.

### 2.6 Evidence passes three gates

Evidence is considered in this order:

1. **Provenance and integrity:** What exactly was obtained, from whom or where, when, and with what binding to the subject and proposition?
2. **Admissibility:** Is that evidence an acceptable basis for this particular question?
3. **Sufficiency:** Taken together, does the admissible evidence answer the complete bounded question?

Evidence class, acquisition mode, source authority, visibility, integrity, freshness, admissibility and sufficiency remain separate dimensions. On-chain data is not automatically authoritative for legal meaning or issuer identity. Issuer-authored evidence is not automatically inadequate. A third-party document is not automatically independent confirmation. Illustrative material never contributes to coverage.

**Authoritative for a proposition** means that the source has sufficient authority over the specific factual proposition asserted. Authority is proposition-specific; it does not make a source independent, infallible or superior for adjacent propositions. Validated blockchain state may be authoritative for bounded state at a validated deployment but not for issuer identity or legal ownership. A custodian record may be authoritative for a bounded holding but not for holder insolvency rights. An operative governing document may be authoritative for declared terms but not for whether those terms operated as declared.

An accountable first-party source can be sufficient for propositions it directly governs, such as declared terms. Self-attestation does not by itself establish actual operation, actual holdings, actor independence or completed independent oversight. Claims about real-world actor identity and common control, actual reserve existence and custody, operating effectiveness, and completed independent oversight require corroboration independent of unauthenticated labels and unsupported assertions by the reviewed party.

**Authoritative absence** requires evidence capable of addressing the complete bounded proposition: an explicit `none` from a source with proposition authority, or adequately exhaustive evidence across all material paths by which the thing could exist. The subject, scope, relevant period and limits of the negative conclusion must be stated. Silence, non-discovery and lack of access are never authoritative absence.

The likely acquisition modes listed for each check are non-binding testing hypotheses. They identify plausible evidence paths rather than universal requirements. A particular mode is required only where this methodology explicitly makes it necessary for the proposition.

### 2.7 Evidence commissioning and conflicts are provenance

Where applicable, evidence provenance records:

- author;
- publisher;
- commissioner or funder;
- relationship to the reviewed subject;
- whether the work is self-attestation, commissioned research, independent assurance, a rating or unaffiliated research;
- methodology scope and stated limitations.

Commissioned evidence is not automatically inadmissible. Unaffiliated research is not automatically independent confirmation. A prestigious author or verifier is not automatically sufficient. Qualification remains proposition-specific, and the relationship information is preserved so the reader can understand who produced the evidence and for what purpose.

### 2.8 Observations are factual building blocks

A check result is supported by observations rather than pointing directly to source material. An observation is a bounded factual proposition: for example, an authorizer set, a reserve quantity at a stated time, a redemption-pricing rule or an insolvency claim position.

Source-backed observations trace to identifiable evidence. Derived observations trace to their source observations and preserve subject identity, units, relevant periods, qualifications and authority limitations. Derivation cannot turn weak evidence into stronger evidence. Its provenance must be acyclic, its deterministic rule versioned, and its inputs compatible in unit and period.

An aggregate cannot be created until its components are compatible and its perimeter is adequately established. Cross-chain supply, for example, cannot be summed until product binding, canonical identity and native-versus-bridged status are evidenced.

Models may help find, extract or propose observations, but do not create authoritative facts without deterministic verification or an explicit human-controlled promotion decision.

### 2.9 Temporal semantics belong to the proposition

Time fields describe distinct events and cannot be substituted for one another:

- a source may have publication and retrieval dates;
- evidence may have an as-of date and an effective period;
- an observation may have an observation time and an effective period;
- an assessment snapshot has a source cutoff.

The relevant time basis is stated for each proposition. A recently retrieved old document is not fresh evidence about current state merely because retrieval is recent.

### 2.10 Materiality is internal and does not control visibility

Materiality is `HIGH`, `MEDIUM` or `LOW` and is fixed per check within this framework version. The 63 retained assignments are unchanged. It measures the internal diligence importance of resolving the question. It does not express asset risk, favorability, confidence, probability of loss or issuer quality.

Materiality is not published in Trust Centers and cannot determine whether an applicable gap is shown. Plinth does not publicly rank gaps, sort them by internal materiality, assign traffic lights, or turn materiality into a score or recommendation.

### 2.11 Operating history is fact, not manager judgment

Plinth may record dated, proposition-specific operating facts: how long a product, process or provider has operated; volumes or events observed; incidents; completed exercises; changes; and remediation history. It does not convert those facts into claims that a manager is capable, credible, experienced, high quality or suitable.

## 3. The five pillars

The internal pillar ID `backing` is retained. Its provisional v0.2 display label is **Assets & Backing**. Display labels do not change check IDs or ownership.

### 3.1 Control — who has power?

Control asks who can actually cause, prevent, authorize or execute a material action. It separates formal authorization from practical execution, identifier ownership from real-world actor control, and nominally distinct controllers from genuinely independent actors.

It does not decide which legal or policy rules govern an action, whether the economic terms are attractive, whether code is correct, or what recovery follows a failure.

### 3.2 Assets & Backing — what exists behind the product?

Assets & Backing establishes which assets, instruments, claims, balances and obligations exist; how much exists; who owns, holds or controls the holdings; and whether backing and obligations reconcile on a disclosed basis.

It distinguishes asset existence and claim identity from valuation, economic allocation, legal permission and insolvency consequences.

### 3.3 Economics — how does value enter, accrue, move, get allocated, get priced or leave?

Economics explains normal-course entry, pricing, fees, liquidity, redemption, settlement, yield, value allocation and loss incidence. It describes the participant’s economic bargain and the mechanics through which value moves.

Stressed redemption, suspension caused by disruption, dependency failure, insolvency recovery and wind-down belong to Continuity. The identity of actors who can change or stop economic mechanisms belongs to Control.

### 3.4 Governance & Compliance — under what rules does it operate?

Governance & Compliance establishes which legal, contractual, regulatory, policy and load-bearing operating rules govern the product and an actor’s conduct. It distinguishes legal identity from regulatory permission, written obligations from implemented controls, and implemented controls from demonstrated operating effectiveness.

Actual capacity to cause, prevent, authorize or execute an action belongs to Control even when law or policy constrains its permitted use.

### 3.5 Continuity — what happens under disruption, default, insolvency or failure?

Continuity examines stressed redemption, suspension, dependency failure, service degradation, response and recovery, communications, record access and reconstruction, insolvency, enforcement, wind-down, exercises and remediation.

It does not duplicate normal-course Economics or treat the mere existence of a plan as proof of resilience.

### 3.6 Pillar ownership and technical evidence

Each check has exactly one owner based on the primary allocator question it answers—not the mechanism that implements it, the evidence source used to answer it, or a downstream consequence. Related pillars may help a reader navigate connected observations but do not affect ownership, applicability, coverage or roll-ups.

Technical evidence answers questions within the five pillars. An upgrade key is evidence about Control; canonical cross-chain identity can be evidence about Assets & Backing; an executable redemption path can be evidence about Economics; a transfer restriction can evidence Governance & Compliance; and an oracle recovery path can evidence Continuity. Technical correctness, audit coverage, oracle/NAV integrity, bridge integrity and infrastructure dependency remain an explicit later test domain. No sixth pillar is introduced in this draft.

## 4. Claim and service-provider architecture

The allocator-facing output composes existing observations into the supported relationship path:

```text
Holder
→ token or recorded interest
→ legal claim
→ issuing vehicle
→ asset owner
→ custodian
→ underlying asset
```

The path represents questions, not an assumption that every product contains a separate party at each step. Each relationship is established, explicitly not applicable, or unresolved.

Where applicable, the composition also identifies the administrator, manager, transfer agent or registrar, auditor or assurance provider, redemption operator, oracle/NAV/data provider and technical controller. It records the function performed, the legal or operational relationship, the relevant scope and any evidenced common control or related-party relationship.

This architecture is not a new pillar or a new check. It is a reader-facing composition of retained Control, Assets & Backing and Governance & Compliance observations, with Economics and Continuity observations added where they explain value movement or failure consequences.

## 5. Reserve-verification quality

Evidence offered as reserve verification is evaluated according to the proposition and procedure actually covered. The record preserves:

- verifier identity and relationship to the reviewed subject;
- procedure performed;
- assurance or opinion type, if any;
- asset, account, entity and obligation scope;
- as-of date and covered period;
- cadence;
- exclusions and limitations;
- whether the work establishes existence, ownership, custody, segregation, allocation or reconciliation.

These propositions are not interchangeable. A point-in-time balance confirmation does not establish ownership, segregation, ongoing reconciliation or the absence of intervening shortfalls. An audit brand or professional designation does not supply a missing procedure, scope or conclusion. Plinth does not use rules such as “Big Four equals stronger evidence.”

## 6. Complete check catalogue

The 63 check IDs, questions, substantive definitions and internal materiality assignments below are retained from v0.1. The only catalogue-heading change is the provisional display label **Assets & Backing** for the existing internal pillar `backing`.

## Control — 8 checks

### PF-CONTROL-001 — Who can authorize the scoped material privileged action?

- **Allocator purpose:** Identify who can approve each material action without conflating approval with execution.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies separately to each material privileged action that the product can perform. It does not apply only where adequate evidence establishes that the candidate action is absent from the product's material control surface; uncertainty about that surface leaves applicability unresolved.
- **Expected observations:** Complete authorizer set; direct, indirect, conditional, and delegated authorization paths.
- **Likely acquisition mode(s):** Deterministic inspection of technical state and documentary review of accountable off-system authority.
- **Evidence/sufficiency principle:** Evidence must bind every authorizer and path to the exact subject, deployment, capability, action, and current period. Completeness requires all material authorization paths, including off-system paths where relevant; identifying only one known authorizer is partial.

### PF-CONTROL-002 — Who can execute the scoped material privileged action?

- **Allocator purpose:** Show who can make a material action happen, separately from who approves it.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies separately to each established material privileged action. Adequately evidenced absence of the action makes the check inapplicable; an incomplete action perimeter leaves applicability unresolved.
- **Expected observations:** Complete executor set; direct, relayed, scheduled, automated, conditional, and delegated execution paths.
- **Likely acquisition mode(s):** Deterministic technical inspection and documentary review of off-system execution arrangements.
- **Evidence/sufficiency principle:** Every executor and every material route to execution must be resolved and bound to the precise action and scope. Evidence of an approval path does not prove execution power, and evidence of one execution route is partial if other routes remain unresolved.

### PF-CONTROL-003 — What approval rule governs the scoped material action?

- **Allocator purpose:** Make approval concentration and coalition requirements inspectable without judging whether the rule is favorable.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies for each material action with an authorization rule. If the action is adequately absent, it does not apply; if the action or applicable rule cannot be established, applicability is unresolved.
- **Expected observations:** Eligible controller set; number of eligible controllers; required approvals; other load-bearing authorization conditions.
- **Likely acquisition mode(s):** Deterministic configuration inspection and documentary confirmation of effective rules.
- **Evidence/sufficiency principle:** The full eligible set, required approval count, and all conditions that change whether approval is sufficient must be current and mutually compatible. A stated threshold without a complete eligible population is partial and cannot support a concentration conclusion.

### PF-CONTROL-004 — Which distinguishable actors control the identifiers in the scoped controller set?

- **Allocator purpose:** Translate technical or legal controller identifiers into evidence-bounded real-world actor exposure.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies whenever a material action is governed by a controller set containing identifiers whose controlling actors matter. It is inapplicable only where adequate evidence establishes that no such controller set exists; unidentified controllers make the answer incomplete, not inapplicable.
- **Expected observations:** Complete controller-identifier set; binding from each identifier to a distinguishable actor; unresolved identifiers.
- **Likely acquisition mode(s):** Deterministic identifier discovery combined with documentary, attestation, or other independent identity-binding work.
- **Evidence/sufficiency principle:** Every identifier must be attributed on evidence that binds the identifier, actor, scope, and relevant period. Merely naming or labeling an address is insufficient. Actor identity requires corroboration independent of unauthenticated labels and unsupported assertions by the reviewed party.

### PF-CONTROL-005 — Who can cause the scoped privileged credential to be used now?

- **Allocator purpose:** Reveal practical credential-level power that nominal roles or signer lists may conceal.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where a material action depends on a privileged credential, key, account, signing device, or equivalent capability. It does not apply only when the material control perimeter adequately excludes such a credential; incomplete credential discovery leaves applicability unresolved.
- **Expected observations:** Privileged credential set; persons or systems able to cause each credential's use; custody, sharing, reset, and recovery arrangements affecting current use.
- **Likely acquisition mode(s):** Deterministic credential discovery and hybrid review of custody and operational arrangements.
- **Evidence/sufficiency principle:** All scoped credentials and all current paths to their use must be covered. Nominal signer identity alone is insufficient where a custodian, shared secret, administrator, recovery process, or automation can cause use.

### PF-CONTROL-006 — Which nominal controllers in the scoped set are under common control?

- **Allocator purpose:** Prevent nominal controller counts from overstating independent control.
- **Materiality:** MEDIUM.
- **Conceptual applicability:** Applies when a material controller set contains multiple nominal identifiers or members whose independence affects interpretation of the approval rule. It does not apply only where adequate evidence establishes no relevant multi-member set; unresolved membership leaves applicability unresolved.
- **Expected observations:** Controller-identifier set; pairwise or grouped common-control relationships; unresolved independence relationships.
- **Likely acquisition mode(s):** Deterministic set construction and documentary or other independent ownership/control analysis.
- **Evidence/sufficiency principle:** Every material relationship must be resolved as common control or adequately independent. Shared service providers, custody arrangements, corporate control, or operational delegation must not be mistaken for independence. A claim of independence requires evidence beyond unsupported assertions by the actors whose independence is being assessed.

### PF-CONTROL-007 — Who or what can prevent the scoped authorized action from executing?

- **Allocator purpose:** Separate the power to block execution from authorization, execution, and cancellation power.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies to each material action for which execution can be attempted. Adequately established absence of the action makes it inapplicable; uncertainty about the action or blocking surface leaves applicability unresolved.
- **Expected observations:** Complete set of actors, systems, delays, conditions, or dependencies that can block execution; rule or mechanism by which each block operates.
- **Likely acquisition mode(s):** Deterministic inspection of technical paths and documentary review of off-system vetoes or dependencies.
- **Evidence/sufficiency principle:** Completeness requires both the blocker set and the operative blocking rules, including an adequately supported empty set where no blocker exists. A known timelock or veto is only partial if other blocking paths remain unresolved.

### PF-CONTROL-008 — Which actors can complete the scoped material action without another independently controlled actor?

- **Allocator purpose:** State the effective actor-level ability to complete a material action unilaterally.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies for each established material action after relevant authorization, execution, credential, and common-control relationships are considered. Adequately evidenced absence of the action makes it inapplicable; unresolved control relationships leave the answer incomplete.
- **Expected observations:** Mapping of each distinguishable actor to the action paths it can complete alone, including dependencies on actors that are or are not independently controlled.
- **Likely acquisition mode(s):** Deterministic analysis using technical state, supplemented by hybrid actor and control bindings.
- **Evidence/sufficiency principle:** A unilateral-capability conclusion must be reproducible from complete, time-compatible evidence about authorizers, executors, credentials, blockers, and common control. Apparent multisignature structure is not sufficient if one actor controls several nominal participants.

## Assets & Backing — 13 checks

### PF-BACKING-001 — Which assets, instruments, claims, or balances form the complete material reserve inventory, and what identity-defining terms apply to each item?

- **Allocator purpose:** Establish what actually sits within the reserve perimeter before considering quantities, composition, or ratios.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies to every review subject, including products for which the complete answer may be that no external reserve backing exists. An unestablished review subject makes applicability unresolved rather than inapplicable.
- **Expected observations:** Reserve perimeter; backing form; identity and instrument type of each material item; identity-defining terms; completeness and material exclusions.
- **Likely acquisition mode(s):** Deterministic, documentary, and hybrid inventory construction.
- **Evidence/sufficiency principle:** Every material reserve item must be identified on evidence appropriate to the existence proposition, with material terms and exclusions visible. A supported subset is partial where the perimeter is incomplete. An authoritative, appropriately bounded finding of no external reserve backing can be complete.

### PF-BACKING-002 — For each material reserve item, what quantity actually exists and exactly what does that quantity measure?

- **Allocator purpose:** Provide authority-qualified, time-specific quantities that cannot be treated as equivalent merely because displayed units match.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies when the product has an external backing arrangement containing material reserve items. It does not apply when adequate evidence establishes that no such arrangement exists; uncertainty about external backing leaves applicability unresolved.
- **Expected observations:** Quantity for each reserve item; actual unit; measurement kind and bounded scope; observation time; perimeter completeness and exclusions.
- **Likely acquisition mode(s):** Deterministic reads, accountable documents, and hybrid reconciliation of records.
- **Evidence/sufficiency principle:** Each material item needs a current, bounded quantity whose unit, subject, measurement meaning, and period are explicit. A declared quantity without authority for actual existence, or quantities covering only part of the perimeter, are partial.

### PF-BACKING-003 — What share of the complete material reserve perimeter does each item or defined category represent?

- **Allocator purpose:** Present reserve composition on one non-duplicated and intelligible denominator.
- **Materiality:** MEDIUM.
- **Conceptual applicability:** Applies where an external backing arrangement exists and a complete material reserve perimeter can be evaluated. It does not apply where external backing is adequately absent; uncertainty about backing or the denominator leaves applicability unresolved.
- **Expected observations:** Item or category shares; denominator and calculation basis; category definitions; perimeter completeness and exclusions.
- **Likely acquisition mode(s):** Deterministic calculation from reserve observations, supported by documentary definitions.
- **Evidence/sufficiency principle:** Shares must cover the complete material denominator on compatible units or an explicit conversion basis, use non-overlapping categories, and close within disclosed rounding tolerance. A supported share over an incomplete or ambiguous denominator is partial.

### PF-BACKING-004 — Who holds legal title to each material reserve asset or claim?

- **Allocator purpose:** Identify the legal holder of record without predicting insolvency treatment.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies to every material holding in an external backing arrangement. It does not apply where such backing is adequately absent; incomplete reserve or legal-entity scope leaves applicability unresolved.
- **Expected observations:** Legal title holder for each material reserve item, relevant legal capacity, and effective period; perimeter completeness and exclusions.
- **Likely acquisition mode(s):** Documentary legal review and manual verification.
- **Evidence/sufficiency principle:** Title must be supported for every material holding by evidence authoritative for legal ownership and effective for the relevant period. Custody, possession, or an issuer label alone does not prove title.

### PF-BACKING-005 — Who beneficially owns each material reserve asset or claim?

- **Allocator purpose:** Separate economic ownership from legal title and make unresolved beneficial ownership visible.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies to each material holding in an external backing arrangement. It does not apply where external backing is adequately absent; inability to determine whether title and beneficial ownership coincide is a coverage gap.
- **Expected observations:** Beneficial owner for each holding; status indicating identified, coextensive with title, or unresolved; perimeter completeness and exclusions.
- **Likely acquisition mode(s):** Documentary legal review and manual ownership analysis.
- **Evidence/sufficiency principle:** Every material holding must have a supported beneficial owner or an authoritative conclusion that beneficial ownership is coextensive with title. Unsupported assumptions that the titled entity owns economically are partial.

### PF-BACKING-006 — Where and with whom is each material reserve holding kept, and which bounded holding record confirms that relationship?

- **Allocator purpose:** Distinguish an attributed custodian from an accountable, bounded, directly confirmed holding relationship.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies to material holdings within an external backing arrangement, including self-custody or nontraditional holding arrangements. It does not apply where external backing is adequately absent; unresolved custody scope leaves applicability unresolved.
- **Expected observations:** Custody provider or equivalent venue; holding location; accountable record identifier and scope; confirmation status and as-of date; perimeter completeness and exclusions.
- **Likely acquisition mode(s):** Deterministic account or ledger evidence, documentary confirmations, and hybrid matching.
- **Evidence/sufficiency principle:** Every material holding must be tied to a bounded current record and accountable holder/custodian relationship. Indirect assertions, undated confirmations, or unbounded account evidence are partial; a provider name alone is insufficient.

### PF-BACKING-007 — To which obligations or reserve pool is each material holding allocated, and is that allocation exclusive?

- **Allocator purpose:** Show which obligations each holding supports and whether the same holding also supports another pool.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies to each material holding in an external backing arrangement. It does not apply where external backing is adequately absent; incomplete reserve or obligation perimeters leave applicability unresolved.
- **Expected observations:** Allocation target for each holding; whether allocation is exclusive or non-exclusive; relevant scope and period; perimeter completeness and exclusions.
- **Likely acquisition mode(s):** Documentary analysis and manual verification of legal and operational allocation.
- **Evidence/sufficiency principle:** Every material holding needs a supported allocation target and explicit exclusivity status. General statements that assets “back the product” are insufficient when pooling, cross-collateralization, or competing obligations remain possible.

### PF-BACKING-008 — Is each material reserve holding segregated from assets outside the relevant pool, and by what method?

- **Allocator purpose:** Show observed separation of backing while keeping operational and legal segregation distinct.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies to every material holding in an external backing arrangement. It does not apply where external backing is adequately absent; incomplete knowledge of holdings or segregation dimensions leaves applicability unresolved.
- **Expected observations:** Segregation status and method for each material legal and operational dimension; perimeter completeness and exclusions.
- **Likely acquisition mode(s):** Deterministic account inspection, documentary legal review, and hybrid confirmation.
- **Evidence/sufficiency principle:** Each material holding must be addressed for the relevant segregation dimensions, including an adequately supported `not segregated` finding where applicable. Separate accounts do not by themselves establish legal segregation, and legal language does not by itself establish operational separation.

### PF-BACKING-009 — What encumbrances affect each material reserve holding?

- **Allocator purpose:** Identify competing uses, claims, liens, pledges, restrictions, or other burdens without turning them into a score.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies to material holdings within an external backing arrangement. It does not apply where external backing is adequately absent; failure to discover an encumbrance is not the same as adequately establishing none.
- **Expected observations:** Encumbrance status and terms for each holding; scope of any search or confirmation; relevant period; perimeter completeness and exclusions.
- **Likely acquisition mode(s):** Documentary legal review and manual verification.
- **Evidence/sufficiency principle:** Every material holding needs either identified encumbrance terms or a bounded, authoritative conclusion that none were identified within a stated scope. Silence in product documentation is insufficient.

### PF-BACKING-010 — Which ledger and non-ledger obligation representations exist, and how is each classified and related to the others?

- **Allocator purpose:** Establish the complete obligation-representation topology needed to prevent omission and double counting.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies when the product has outstanding obligations, even if there is only one representation. It does not apply only where adequate evidence establishes that no outstanding obligation exists; uncertainty leaves applicability unresolved.
- **Expected observations:** Identity, classification, lifecycle status, and relationship mechanism of each ledger and non-ledger representation; complete obligation perimeter and exclusions.
- **Likely acquisition mode(s):** Deterministic ledger inspection, documentary records, and hybrid topology analysis.
- **Evidence/sufficiency principle:** Every material representation and relationship must be covered, including native, bridged, wrapped, book-entry, pending, or off-ledger forms where relevant. A list of contract addresses is incomplete without issuer binding and relationship classification.

### PF-BACKING-011 — What outstanding quantity exists in each obligation representation, and what deduplicated aggregate follows?

- **Allocator purpose:** Produce a correct outstanding-obligation quantity for both single- and multi-representation products.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies whenever outstanding obligations exist, including a single representation. It does not apply only where their absence is adequately established; unresolved representation identity or perimeter leaves applicability unresolved.
- **Expected observations:** Quantity, unit, measurement kind, and scope for each representation; representation relationships; deduplicated aggregate; completeness and exclusions.
- **Likely acquisition mode(s):** Deterministic reads, documentary records, and hybrid deduplication.
- **Evidence/sufficiency principle:** Per-representation quantities must be compatible in identity, unit, time, and meaning. A singleton aggregate equals its sole quantity; multiple representations require a reproducible method that avoids counting wrapped, bridged, pending, or mirrored obligations twice.

### PF-BACKING-012 — Do complete material reserve backing and outstanding obligations reconcile on one disclosed compatible basis?

- **Allocator purpose:** Show transparently how complete backing relates to complete obligations without expressing safety or favorability.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies when both external reserve backing and outstanding obligations are adequately established. If either is adequately absent, the check does not apply; if either perimeter or its identity is unresolved, applicability is unresolved.
- **Expected observations:** Complete reserve and obligation perimeters; reconciliation basis; accountable preparer and reviewer; reserve total and obligation total on that basis; difference and as-of date; exclusions and qualifications.
- **Likely acquisition mode(s):** Deterministic and documentary inputs combined through hybrid reconciliation.
- **Evidence/sufficiency principle:** Both perimeters must be complete and comparable in identity, definition, unit, and time. Any valuation or conversion must remain traceable to its economic assumptions. A disclosed subtotal or comparison across incompatible bases is partial, not a full reconciliation.

### PF-BACKING-013 — For each material pooled or layered reserve claim, which underlying assets, quantities, and identity-defining claim terms does it represent?

- **Allocator purpose:** Prevent pooled, fund, note, account, or layered reserve claims from hiding material unknown underlying assets or quantities.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where a material reserve item is itself a pooled, layered, intermediated, or look-through instrument. It does not apply when adequate evidence establishes no such item; uncertainty about reserve-item structure leaves applicability unresolved.
- **Expected observations:** Underlying asset identities and quantities; allocation basis; identity-defining claim terms; look-through scope and completeness; material gaps and exclusions.
- **Likely acquisition mode(s):** Deterministic and documentary evidence combined through hybrid look-through analysis.
- **Evidence/sufficiency principle:** Every material layered item must resolve its material underlyings, typed quantities, allocation basis, and claim terms on compatible evidence. A quantified “other” bucket or unknown percentage is useful disclosure but does not constitute a complete answer.

## Economics — 14 checks

### PF-ECONOMICS-001 — For each supported entry route, what value must a participant deliver and how is the acquired position amount determined?

- **Allocator purpose:** Explain what a participant exchanges to enter through every supported route.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where the product has at least one supported entry route, whether direct, intermediated, on-chain, off-chain, primary, or secondary. It does not apply only where an adequately established route perimeter is empty; incomplete route discovery leaves applicability unresolved.
- **Expected observations:** Consideration delivered for each entry route; denomination and delivery basis; formula or fixed basis determining the acquired position; valuation time, rounding, discretion, and material route variants.
- **Likely acquisition mode(s):** Deterministic transaction or contract inspection, documentary terms, hybrid comparison, and manual testing or inquiry.
- **Evidence/sufficiency principle:** Every supported route and every load-bearing pricing element must be covered. A headline subscription price is partial if denomination, timing, rounding, discretion, participant class, or channel changes the actual acquired amount.

### PF-ECONOMICS-002 — For each supported exit route, what value does a participant receive and how is that delivered amount determined?

- **Allocator purpose:** Explain what a participant receives on exit through every supported route.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where at least one supported exit route exists. It does not apply only where an adequately established exit-route perimeter is empty; uncertainty about possible direct, intermediary, market, redemption, or conversion exits leaves applicability unresolved.
- **Expected observations:** Delivered value form and denomination; amount formula or fixed basis; valuation time; selection rules; rounding; discretion; material participant and channel variants.
- **Likely acquisition mode(s):** Deterministic inspection, documentary terms, hybrid comparison, and manual testing or inquiry.
- **Evidence/sufficiency principle:** Every supported exit route must be resolved on its actual delivery and pricing basis. A stated redemption value is partial if payment form, timing basis, deductions, discretion, or material variants remain unknown.

### PF-ECONOMICS-003 — What direct economic charges apply to each supported entry, exit, or transfer route?

- **Allocator purpose:** Make direct route friction and fee recipients comparable without assuming issuance or redemption.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies whenever an entry, exit, or transfer route exists. It does not apply only when all three route populations are adequately established as empty; unresolved potentially material routes leave applicability unresolved.
- **Expected observations:** Charge schedule by route, including payer, recipient, basis, amount or formula, denomination, tiers, minima, maxima, caps, and exemptions; explicit no-charge findings where applicable.
- **Likely acquisition mode(s):** Deterministic state or transaction inspection, documentary fee terms, and hybrid reconciliation.
- **Evidence/sufficiency principle:** Every supported route must have either all direct charges identified or an authoritative bounded no-charge finding. A published base fee is partial if channel fees, spreads charged as fees, recipient deductions, tiers, or exemptions remain unresolved.

### PF-ECONOMICS-004 — When does each supported entry, exit, or transfer route become economically settled or final?

- **Allocator purpose:** Make completion timing and reversibility visible across route types.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies whenever at least one entry, exit, or transfer route exists. It does not apply only where all route populations are adequately complete and empty; an incomplete route perimeter leaves applicability unresolved.
- **Expected observations:** Settlement or finality event for each route; time window; revocation, cancellation, failure, or reversal treatment; scope and limitations.
- **Likely acquisition mode(s):** Deterministic protocol or transaction evidence, documentary operating and contractual terms, and hybrid comparison.
- **Evidence/sufficiency principle:** Each supported route needs a bounded definition of completion and the conditions that can delay or reverse it. Marketing timelines or blockchain confirmation counts alone are insufficient if legal, banking, transfer-agent, or delivery finality differs.

### PF-ECONOMICS-005 — What conditions and quantitative constraints govern each supported entry, exit, or transfer route?

- **Allocator purpose:** Show whether a desired transaction is available to the relevant participant at the required scale.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies whenever an entry, exit, or transfer route exists. It does not apply only where all route populations are adequately complete and empty; unresolved route or participant scope leaves applicability unresolved.
- **Expected observations:** Access conditions; eligibility dependencies; minimums and maximums; caps, gates, quotas, frequency limits, windows, and authoritative no-limit findings.
- **Likely acquisition mode(s):** Deterministic configuration inspection, documentary terms, hybrid comparison, and manual inquiry or testing.
- **Evidence/sufficiency principle:** Conditions and limits must be resolved for every supported route and material participant or channel variant. A contractual right is not sufficient where operative capacity, window, eligibility, or quantitative restrictions materially constrain use.

### PF-ECONOMICS-006 — What dated capacity is available to complete exit through each supported route?

- **Allocator purpose:** Separate contractual permission to exit from the dated ability to complete exit.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies to each supported exit route. It does not apply where the complete exit-route perimeter is adequately empty; uncertainty about routes or the relevant capacity proposition leaves applicability unresolved.
- **Expected observations:** Declared or observed exit capacity by route, as-of date, denomination, included and excluded resources, deductions, access constraints, and replenishment or depletion conditions.
- **Likely acquisition mode(s):** Deterministic balance or facility inspection, documentary capacity statements, hybrid calculations, and manual confirmation.
- **Evidence/sufficiency principle:** Evidence must state whether it describes contractual ceiling, declared available capacity, or observed executable capacity. A maximum facility size or reserve balance alone is partial unless the accessible amount and relevant deductions and constraints are established.

### PF-ECONOMICS-007 — What reference value applies, and how is it determined at each relevant decision time?

- **Allocator purpose:** Explain the meaning, inputs, and timing of reference value without assuming a periodic NAV model.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where the product uses at least one reference valuation method, whether periodic, continuous, event-driven, or per transaction. It does not apply only where an adequately established method perimeter is empty; uncertainty about material valuation uses leaves applicability unresolved.
- **Expected observations:** Unit meaning and denomination; input definitions and sources; transformations, exclusions, and fallbacks; calculation or update trigger; cutoff, price time, time zone, publication lag, and qualifications.
- **Likely acquisition mode(s):** Deterministic oracle or calculation inspection, documentary methodology, hybrid reproduction, and manual verification.
- **Evidence/sufficiency principle:** Every material reference-value method must be intelligible and reproducible at its decision time. A displayed value is partial without its unit definition, source inputs, transformation rules, timing, and fallback behavior.

### PF-ECONOMICS-008 — How do executable transaction and conversion values relate to other economically relevant value measures?

- **Allocator purpose:** Prevent reference, market, transaction, and conversion values from being silently treated as equivalent.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where a transaction or conversion route exists, or where the product exposes multiple economically relevant value measures. It does not apply only when all such routes and multiple measures are adequately absent; unresolved measures or routes leave applicability unresolved.
- **Expected observations:** Purpose, unit, time basis, relationship or non-equivalence among value measures; transaction spreads; conversion-rate source and direction; rounding, charges, and settlement basis where relevant.
- **Likely acquisition mode(s):** Deterministic price or transaction evidence, documentary definitions, hybrid comparison, and manual execution testing.
- **Evidence/sufficiency principle:** Every material measure and route must be mapped explicitly. Similar labels or denominations do not establish equivalence, and a reference price does not prove an executable amount.

### PF-ECONOMICS-009 — What generates economic value, and how does any holder share accrue to the holder position?

- **Allocator purpose:** Explain the origin of economic value and whether and how it reaches the holder.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where the product or its backing has a material value-generating mechanism. It does not apply where adequate evidence establishes no such mechanism; uncertainty about yield, revenue, rewards, interest, appreciation, or other value sources leaves applicability unresolved.
- **Expected observations:** Material value sources and dependencies; design versus realized scope; holder-accrual rule, including eligibility, basis, timing, compounding, rounding, forfeiture, and whether value changes quantity, claim, entitlement, or position value.
- **Likely acquisition mode(s):** Deterministic distribution or balance evidence, documentary economics, hybrid analysis, and manual inquiry.
- **Evidence/sufficiency principle:** All material value sources and the complete path to the holder position must be identified. An authoritative no-holder-accrual finding can be complete even where the issuer or reserve earns value.

### PF-ECONOMICS-010 — How is generated economic value allocated among recipients and when is it distributed or reflected?

- **Allocator purpose:** Show who captures generated value, in what order, and when.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where material economic value is generated and allocated among one or more recipients. It does not apply where adequate evidence establishes no allocation event or retained/generated value; uncertainty about recipients or allocation mechanisms leaves applicability unresolved.
- **Expected observations:** Recipient classes; allocation basis and priority; retained amounts and deductions; discretion; calculation windows; record dates; distribution or reflection triggers and timing; delay rules.
- **Likely acquisition mode(s):** Deterministic distribution evidence, documentary allocation terms, hybrid reconciliation, and manual inquiry.
- **Evidence/sufficiency principle:** Every material recipient, priority, deduction, and timing rule must be covered. Describing the holder yield alone is partial if issuer, manager, service-provider, reserve-owner, or other retained allocations remain unresolved.

### PF-ECONOMICS-011 — What is the all-in cost for a defined entry, holding, and exit scenario, including every recurring or embedded layer?

- **Allocator purpose:** Provide a comparable total cost without hiding indirect layers or double counting.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where the product has an entry, holding, and exit path for which an all-in cost can be meaningfully assessed. A testing campaign declares at least one scenario before evidence collection; failure to select or complete a scenario is `NOT_ASSESSED`, not product inapplicability.
- **Expected observations:** Scenario parameters; all direct, recurring, embedded, and indirect charge components; payer and recipient; basis and frequency; caps; componentized and total cost.
- **Likely acquisition mode(s):** Deterministic and documentary charge inputs combined with hybrid or manual scenario analysis.
- **Evidence/sufficiency principle:** The scenario and every material cost layer must be explicit, with a reproducible total that avoids double counting. An authoritative zero-cost scenario can be complete. This check does not by itself prove that declared charges match every executed transaction.

### PF-ECONOMICS-012 — For each material economic loss exposure, who bears the loss and in what allocation order?

- **Allocator purpose:** Establish economic loss incidence across ordinary and failure-triggered events.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where the product exposes any participant or stakeholder to a material economic loss mechanism, including ordinary shortfall, impairment, default, settlement failure, pricing error, or operational error. It does not apply only where a complete exposure review adequately establishes no such exposure; uncertainty leaves applicability unresolved.
- **Expected observations:** Loss trigger and recognition basis; first incidence; ordered allocation or sharing; buffers and limits; residual incidence; affected classes.
- **Likely acquisition mode(s):** Deterministic state or transaction evidence, documentary loss terms, hybrid analysis, and manual legal/economic review.
- **Evidence/sufficiency principle:** Every material exposure must resolve the complete loss waterfall. An authoritative absence of an allocation rule can be a complete adverse finding; a recovery procedure or reserve statement alone does not answer who bears the loss.

### PF-ECONOMICS-013 — What notice and effective-time rules apply when economic terms change?

- **Allocator purpose:** Show when changed economics bind and whether existing positions can respond.
- **Materiality:** MEDIUM.
- **Conceptual applicability:** Applies where any material economic term can change. It does not apply where adequate evidence establishes the relevant terms are immutable; uncertainty about changeability leaves applicability unresolved.
- **Expected observations:** Changeable term classes; notice method and period; effective-time rule; treatment of existing and prospective positions; grandfathering; cancellation or exit rights; exceptions.
- **Likely acquisition mode(s):** Documentary terms, deterministic configuration or event evidence, hybrid comparison, and manual review.
- **Evidence/sufficiency principle:** Every changeable material term class must be covered. Identifying who can change a term does not establish when the change binds or what affected holders can do.

### PF-ECONOMICS-014 — What economic equivalence, conversion, or non-equivalence applies across each supported pair of deployments or representations?

- **Allocator purpose:** Show whether value is preserved, transformed, delayed, or charged across representations.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where there is at least one supported route between deployments or representations. It does not apply where adequate evidence establishes no such route; unresolved source/destination identity or canonical status leaves applicability unresolved.
- **Expected observations:** Source and destination identity; equivalence, conversion, or explicit non-equivalence rule; effective period; qualifications; relationship to general route charges, limits, and settlement.
- **Likely acquisition mode(s):** Deterministic cross-deployment or bridge evidence, documentary issuer definitions, hybrid identity and value analysis, and manual testing.
- **Evidence/sufficiency principle:** Every supported pair must be resolved without assuming that equal ticker symbols, decimals, or nominal quantities imply economic equivalence. Canonical identity and native-versus-bridged status must be established before cross-deployment conclusions are made.

## Governance & Compliance — 16 checks

### PF-GOV-001 — Which legal subject, jurisdiction, and capacity govern operation of the product?

- **Allocator purpose:** Identify the legal person or persons operating the product, where they operate, and in what capacity.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies to every established review subject. If the review subject itself cannot be adequately identified, applicability is unresolved rather than inapplicable.
- **Expected observations:** Material operating legal subjects; organizational capacity; jurisdiction; scope; effective period; bounded absences and qualifications.
- **Likely acquisition mode(s):** Documentary legal and corporate records with manual verification.
- **Evidence/sufficiency principle:** Every material operating role must be bound to an identifiable legal subject, jurisdiction, capacity, and effective period. A brand, website, token label, or affiliate-group name does not establish the accountable legal operator.

### PF-GOV-002 — What regulatory permission, exemption, restriction, or prohibition status governs the product?

- **Allocator purpose:** Establish the product's regulatory operating basis separately from the identity of its legal operator.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies to every established review subject; the complete answer may be an evidenced absence of a required permission, an exemption, a restriction, or unresolved classification. Missing subject identity leaves applicability unresolved.
- **Expected observations:** Permission, license, registration, exemption, restriction, or prohibition; responsible authority; jurisdiction; product and activity scope; effective period; qualifications.
- **Likely acquisition mode(s):** Documentary regulatory sources and manual legal verification.
- **Evidence/sufficiency principle:** Every material activity and jurisdiction must be covered by evidence authoritative for the claimed regulatory status. Entity registration or a legal opinion alone does not necessarily prove product-specific permission.

### PF-GOV-003 — What legal relationship does the product create with holders?

- **Allocator purpose:** Clarify what the holder legally owns, holds, or is owed instead of inferring rights from product labels or economic resemblance.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies to every established review subject and each material holder class. Missing or unclear legal characterization is a finding or coverage gap, not a reason to suppress the question.
- **Expected observations:** Relevant parties; legal nature of the holder relationship; governing instrument; affected holder classes; effective period; qualifications and uncertainty.
- **Likely acquisition mode(s):** Documentary legal review and manual analysis.
- **Evidence/sufficiency principle:** The relationship must be grounded in operative instruments and tied to the relevant parties and holder classes. Marketing descriptions such as “ownership,” “backed,” or “share” are insufficient without their legal meaning.

### PF-GOV-004 — What ordinary legal rights and remedies govern the holder relationship?

- **Allocator purpose:** Make enforceable rights, conditions, and ordinary remedies visible if normal operation or counterparty performance fails.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies to every established review subject and material holder class. An authoritative absence or limitation of a right can be a complete finding; uncertainty about holder classes or operative instruments leaves the answer incomplete.
- **Expected observations:** Ordinary holder rights and remedies; conditions and exclusions; governing law; dispute forum; holder class; operative instrument and effective period.
- **Likely acquisition mode(s):** Documentary legal sources and manual legal analysis.
- **Evidence/sufficiency principle:** Every material holder class and operative instrument must be covered. Economic expectations, customary practice, or issuer discretion do not substitute for an enforceable right.

### PF-GOV-005 — What rules govern offer, distribution, access, and holder eligibility?

- **Allocator purpose:** Reveal who may acquire, hold, transfer, or lose access and how those limits affect the accessible market and holder base.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies to every established review subject, including products whose adequately supported answer is that no material restriction applies. Missing subject or distribution perimeter leaves applicability unresolved.
- **Expected observations:** Offer and distribution rules; access and eligibility rules; territories, channels, participant classes, lifecycle stages, exceptions, and accountable parties.
- **Likely acquisition mode(s):** Documentary offering, contractual, regulatory, and operating materials with manual verification.
- **Evidence/sufficiency principle:** All material channels, territories, participant classes, and lifecycle stages must be covered. A broad “eligible investors only” or “permissionless” statement is partial without the operative criteria and exceptions.

### PF-GOV-006 — Which material legal, regulatory, contractual, compliance, or load-bearing operating obligations govern the product?

- **Allocator purpose:** Define the obligation universe against which control design, implementation, and effectiveness can be assessed.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies to every established review subject, including internally operated or non-distributed products. The answer may include a bounded absence of a proposed obligation, but lack of discovery does not make the check inapplicable.
- **Expected observations:** Material governed obligations; legal or policy basis; subject and activity scope; accountable party; exceptions; version and effective period.
- **Likely acquisition mode(s):** Documentary legal, contractual, regulatory, and policy review with manual analysis.
- **Evidence/sufficiency principle:** The obligation perimeter must cover material subjects, activities, participants, territories, and lifecycle stages. Controls cannot be credited against obligations that have not first been adequately identified.

### PF-GOV-007 — What controls are designed to implement each material governed obligation?

- **Allocator purpose:** Determine whether the compliance-control design covers the identified obligation universe before implementation or outcomes are credited.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where at least one material governed obligation exists. It does not apply only where a complete obligation assessment adequately establishes an empty obligation set; incomplete obligation discovery leaves applicability unresolved.
- **Expected observations:** Control objective, trigger, scope, method, frequency, owner, escalation, exception handling, version, and effective period for each obligation.
- **Likely acquisition mode(s):** Documentary policy and control-design review with manual analysis.
- **Evidence/sufficiency principle:** Every material obligation must map to an approved control design or an authoritative absence. Generic policy statements are partial where they do not state how, when, by whom, and across what scope the obligation is addressed.

### PF-GOV-008 — Which designed controls for material governed obligations are implemented across the required scope?

- **Allocator purpose:** Distinguish written control intent from actual deployment and expose operator or delegation concentration.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where material governed obligations and associated designed controls exist. It does not apply only where the complete obligation population is adequately empty; unresolved design or required scope leaves applicability unresolved.
- **Expected observations:** Implementation status; deployed scope; operator; material delegation; version; activation period; known deviations for each designed control.
- **Likely acquisition mode(s):** Documentary implementation records, hybrid system/configuration evidence, and manual verification.
- **Evidence/sufficiency principle:** Every designed control must be traced to its actual implemented state across the required scope. Policy approval, vendor engagement, or a system screenshot alone does not establish complete implementation.

### PF-GOV-009 — Are implemented controls for material governed obligations evidenced as operating effectively during the review period?

- **Allocator purpose:** Separate control presence from demonstrated operation and expose exceptions, testing limitations, and unresolved remediation.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where at least one governed control is implemented. It does not apply only where a complete implementation assessment establishes an empty implemented-control set; unresolved implementation leaves applicability unresolved.
- **Expected observations:** Test population and completeness basis; sample where used; test procedure and criteria; result; exceptions; remediation; reviewer; period; limitations and provenance.
- **Likely acquisition mode(s):** Deterministic event or transaction evidence, documentary test work, and manual operating-effectiveness review.
- **Evidence/sufficiency principle:** Every implemented material control must have review-period evidence showing what was tested and with what result. Design evidence or isolated examples cannot establish operating effectiveness; failed operation may nevertheless be fully evidenced.

### PF-GOV-010 — What accountability, approval, and change rules govern the compliance policy framework?

- **Allocator purpose:** Show who owns and approves the policy framework and how controlled changes become effective.
- **Materiality:** MEDIUM.
- **Conceptual applicability:** Applies to every established review subject. An authoritative absence of a formal policy framework may be a complete adverse finding rather than making the question inapplicable.
- **Expected observations:** Policy ownership and accountable roles; approval; versioning; change initiation and approval; notice and effective-time rules; bounded absence where applicable.
- **Likely acquisition mode(s):** Documentary policy-governance records and manual review.
- **Evidence/sufficiency principle:** Accountability and the complete change lifecycle must be resolved for the material policy framework. A named compliance officer or current policy document alone does not establish controlled approval and change.

### PF-GOV-011 — What exception and waiver rules govern the compliance policy framework?

- **Allocator purpose:** Show whether exceptions and waivers are possible, who can grant them, and what limits govern their use.
- **Materiality:** MEDIUM.
- **Conceptual applicability:** Applies to every established review subject. An authoritative finding that no exceptions or waivers are permitted can be complete; silence or non-discovery is not adequate absence.
- **Expected observations:** Exception and waiver authority; criteria; scope; duration; documentation; oversight; revocation; bounded absence.
- **Likely acquisition mode(s):** Documentary policy and exception records with manual review.
- **Evidence/sufficiency principle:** Material exception paths must be covered end to end. A policy's mandatory wording is insufficient if another actor or process can waive it outside the visible policy.

### PF-GOV-012 — What external or independent oversight arrangement applies to the compliance program?

- **Allocator purpose:** Establish whether an accountable challenge or review arrangement exists and what it is intended to cover.
- **Materiality:** MEDIUM.
- **Conceptual applicability:** Applies to every established review subject. An authoritative bounded absence of independent oversight can be a complete finding; it does not make the question inapplicable.
- **Expected observations:** Oversight provider or reviewer; independence basis; mandate; scope; effective period; limitations; bounded absence.
- **Likely acquisition mode(s):** Documentary engagement, mandate, governance, or assurance records with manual verification.
- **Evidence/sufficiency principle:** The arrangement must be current, accountable, scoped, and meaningfully independent for the claimed purpose. Naming an auditor, regulator, board, or service provider does not establish the mandate or independence of oversight.

### PF-GOV-013 — What completed external or independent oversight work covers the compliance program?

- **Allocator purpose:** Determine whether external oversight was actually performed and what findings or limitations remain.
- **Materiality:** MEDIUM.
- **Conceptual applicability:** Applies to every established review subject. The answer may be an authoritatively established absence of completed work; the existence of an oversight arrangement does not itself answer this check.
- **Expected observations:** Completed work product; reviewer and independence basis; scope and period; procedures; result; limitations; findings and follow-up; bounded absence.
- **Likely acquisition mode(s):** Documentary assurance or review work products and manual verification.
- **Evidence/sufficiency principle:** Completed work must be distinguished from appointment, engagement, or planned review. A report title or attestation summary is partial if scope, period, procedures, result, or material limitations remain unknown.

### PF-GOV-014 — What continuing regulatory reporting obligations apply?

- **Allocator purpose:** Identify recurring regulatory duties whose breach could affect permission or operations.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies to every established review subject because determining whether obligations exist is itself part of the question. An authoritative bounded absence may be complete; non-discovery is not proof of absence.
- **Expected observations:** Reporting authority and recipient; subject; report type; trigger or cadence; due-date rule; territory; accountable party; exceptions; version and effective period.
- **Likely acquisition mode(s):** Documentary regulatory sources, internal obligation records, and manual legal analysis.
- **Evidence/sufficiency principle:** Every material continuing obligation must be identified across relevant entities, activities, and jurisdictions. A license or registration record alone does not establish its ongoing reporting duties.

### PF-GOV-015 — Were applicable regulatory reporting obligations met during the review period?

- **Allocator purpose:** Show whether recurring regulatory duties were actually met and whether late, incomplete, or remediated filings occurred.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where at least one continuing regulatory reporting obligation is adequately established. It does not apply only where authoritative bounded evidence establishes that none exists; non-discovery leaves applicability unresolved.
- **Expected observations:** Each due filing; report period; due date; submission event; receipt or acknowledgement; timeliness and completeness; exception and remediation; source and retrieval time.
- **Likely acquisition mode(s):** Documentary filing records and manual verification.
- **Evidence/sufficiency principle:** Every filing due during the review period must be accounted for. A general statement of compliance or one example filing is partial where the due-filing population is incomplete.

### PF-GOV-016 — How can material non-economic holder-facing terms change, and when do changes bind?

- **Allocator purpose:** Explain how rights or operating terms other than economic terms can change for existing and future holders.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where at least one material non-economic holder-facing term can change. It does not apply only where the complete term perimeter is adequately established as immutable or empty; uncertainty about material terms or changeability leaves applicability unresolved.
- **Expected observations:** Changeable term classes; change authority or immutability; consent; notice; effective time; grandfathering or exit treatment; exception handling; bounded absence.
- **Likely acquisition mode(s):** Documentary legal and operating terms, supplemented by hybrid technical change evidence.
- **Evidence/sufficiency principle:** Every material term class must be covered through its full change and binding lifecycle. Technical change authority alone does not establish legal effectiveness, holder consent, notice, or grandfathering.

## Continuity — 12 checks

### PF-CONTINUITY-001 — Which material failure scenarios are addressed by the continuity arrangements?

- **Allocator purpose:** Expose which material disruptions the arrangements contemplate and which remain explicitly uncovered.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies to every established review subject. An evidenced absence of continuity arrangements or coverage for a material scenario is a complete adverse finding, not a reason to make the check inapplicable.
- **Expected observations:** Material failure-scenario set; mapping from each scenario to contemplated consequences and intended end states; dependencies, exclusions, and limitations.
- **Likely acquisition mode(s):** Documentary continuity materials and manual scenario analysis.
- **Evidence/sufficiency principle:** Every material scenario must be matched to an explicit coverage or non-coverage finding. A plan can be fully evidenced as incomplete; omission of a potentially material scenario from the assessed scenario set prevents a complete answer.

### PF-CONTINUITY-002 — What controlled lifecycle governs a material disruption response?

- **Allocator purpose:** Show whether a disruption enters and exits a controlled response process instead of relying on ambiguous handoffs or open-ended escalation.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies to every established review subject. An authoritative absence of a controlled lifecycle can be a complete adverse finding; missing subject identity leaves applicability unresolved.
- **Expected observations:** Response states; entry triggers; accountable coordinator; permitted handoffs; escalation transitions; resumption or termination criteria; closure evidence; dependencies and limitations.
- **Likely acquisition mode(s):** Documentary response procedures and manual process analysis.
- **Evidence/sufficiency principle:** Every materially distinct response state and transition must be covered. A contact list, escalation chart, or generic incident policy is partial without triggers, authority, exit criteria, and closure evidence.

### PF-CONTINUITY-003 — What service trajectory is defined for each critical function during disruption?

- **Allocator purpose:** Make the holder-relevant degraded state and recovery expectation concrete for every critical function.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where the product has one or more material critical functions. It does not apply only where an adequately established critical-function assessment is empty; failure to establish the function set leaves applicability unresolved.
- **Expected observations:** For each critical function: disruption service state, preservation or backlog treatment, recovery priority, bounded recovery objective or authoritative absence, intended restored state, and material limitations.
- **Likely acquisition mode(s):** Documentary service-continuity sources and manual operational analysis.
- **Evidence/sufficiency principle:** Every critical function must have an explicit trajectory. Product-wide recovery slogans or infrastructure uptime targets are partial when they do not explain holder-facing service states, backlog treatment, capacity constraints, and restoration objectives.

### PF-CONTINUITY-004 — How will holders receive usable information during a material disruption?

- **Allocator purpose:** Show whether holders can learn what happened, what remains possible, and when further information is due.
- **Materiality:** MEDIUM.
- **Conceptual applicability:** Applies to every established review subject. An authoritative absence of a disruption-communication plan can be a complete adverse finding; missing subject identity leaves applicability unresolved.
- **Expected observations:** Notification triggers; affected recipients; primary and fallback channels; initial and recurring update targets; accountable function; minimum content; accessibility and coverage limitations.
- **Likely acquisition mode(s):** Documentary communication and incident-response materials with manual review.
- **Evidence/sufficiency principle:** Material scenario classes with different holder information needs must be covered. A general promise to communicate is partial without triggers, audiences, fallback channels, timing, accountable ownership, and minimum usable content.

### PF-CONTINUITY-005 — What recovery path applies when a material continuity dependency fails or becomes impaired?

- **Allocator purpose:** Provide a comparable answer for substitution, access, stabilization, enforcement, or restoration after each dependency failure.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where at least one material continuity dependency exists. It does not apply only where an adequately established dependency assessment is empty; incomplete dependency discovery leaves applicability unresolved.
- **Expected observations:** Dependency and failure trigger; affected function; containment or fallback; substitution, transfer, enforcement, or restoration path; prerequisites, handoffs, completion criteria, expected interruption, and limitations.
- **Likely acquisition mode(s):** Deterministic dependency evidence, documentary arrangements, hybrid verification, and manual operational analysis.
- **Evidence/sufficiency principle:** Every material dependency must be matched to a recovery path or an authoritative absence. Vendor names, redundancy claims, or termination rights alone are partial without access, capacity, cooperation, reconciliation, and completion conditions.

### PF-CONTINUITY-006 — How is authorized access to authoritative records maintained during disruption?

- **Allocator purpose:** Show whether authoritative holder and operational state remains reachable when the normal access path fails.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where the product depends on authoritative records, regardless of whether they are on-chain, off-chain, or hybrid. It does not apply only where an adequately established record assessment is empty; incomplete record discovery leaves applicability unresolved.
- **Expected observations:** Authoritative record set; primary and fallback access paths; activation and authentication prerequisites; readable scope and latency; dependency and integrity limitations; states in which access remains unavailable.
- **Likely acquisition mode(s):** Deterministic system evidence, documentary access procedures, and hybrid testing.
- **Evidence/sufficiency principle:** Every authoritative record source must have a bounded access answer. Backup existence is insufficient if authorized users cannot activate it, authenticate, obtain a complete readable scope, or understand its latency and integrity limitations.

### PF-CONTINUITY-007 — How is authoritative record state recovered after material error, corruption, or loss?

- **Allocator purpose:** Show whether authoritative state can return to a validated, traceable condition after erroneous, corrupt, or unavailable records.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where the product depends on authoritative records. It does not apply only where an adequately established record assessment is empty; unresolved record systems leave applicability unresolved.
- **Expected observations:** Correction path for erroneous available state; reconstruction path for corrupt or lost state; authorization; immutable lineage; recovery source; maximum data-loss boundary; integrity validation; holder-impact reconciliation; completion criteria and limitations.
- **Likely acquisition mode(s):** Deterministic system evidence, documentary recovery procedures, and hybrid recovery or reconciliation testing.
- **Evidence/sufficiency principle:** Every authoritative record source must address both correction and reconstruction, or authoritatively establish a branch as unavailable. Generic backup statements are partial without traceability, validation, data-loss bounds, and holder-impact reconciliation.

### PF-CONTINUITY-008 — What is the holder's legal position if a material entity in the value or service chain becomes insolvent?

- **Allocator purpose:** Make holder position, estate treatment, priority, and recourse visible for every material entity.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where at least one material legal entity participates in the value or service chain. It does not apply only where an adequately established legal-entity assessment is empty; a holder claim need not already be proven for the question to apply.
- **Expected observations:** For each material entity: direct, indirect, proprietary, beneficial, secured, unsecured, or no evidenced position; estate inclusion or exclusion; priority; recourse; law and forum; assumptions, disputes, and qualifications.
- **Likely acquisition mode(s):** Documentary legal sources and manual insolvency analysis.
- **Evidence/sufficiency principle:** Every material entity and holder class must be addressed. Asset segregation, contractual ownership language, or reserve title alone does not establish insolvency treatment or priority.

### PF-CONTINUITY-009 — What path can holders use to participate or enforce during insolvency or comparable distress?

- **Allocator purpose:** Separate substantive legal position from the usable procedure for asserting it under distress.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where material entities and actual or potential holder positions exist. It does not apply only where an adequately established entity/position assessment is empty; uncertainty about whether a claim succeeds does not suppress the procedural question.
- **Expected observations:** Forum; notice and filing sequence; deadlines and prerequisites; remedy or authoritative absence; representation or collective constraints; cost, stay, recognition, timing, and enforceability limitations.
- **Likely acquisition mode(s):** Documentary procedural and contractual sources with manual legal analysis.
- **Evidence/sufficiency principle:** Every material entity and holder position must have a usable procedural answer. Stating that holders “retain all rights” or may sue is partial without forum, sequence, deadlines, prerequisites, remedies, and material constraints.

### PF-CONTINUITY-010 — What terminal disposition governs an orderly wind-down?

- **Allocator purpose:** Expose whether permanent discontinuation reaches a bounded, auditable end state for holders and unfinished obligations.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies to every established review subject. An authoritative absence of a wind-down plan can be a complete adverse finding rather than making the check inapplicable.
- **Expected observations:** Wind-down initiation and ordered stages; material obligations; disposition and holder milestones; record retention and access; successor or termination state; completion evidence; legal, resource, timing, and scope limitations.
- **Likely acquisition mode(s):** Documentary wind-down, legal, and operating plans with manual review.
- **Evidence/sufficiency principle:** Every material unfinished obligation must map to a disposition and end state. A termination clause or discretionary shutdown right is partial without holder treatment, records, sequencing, accountability, and evidence of completion.

### PF-CONTINUITY-011 — What is the evidenced exercise history of the continuity arrangements?

- **Allocator purpose:** Distinguish documented intent from dated, never-exercised, or unknown exercise history without converting that finding into a rating.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies to every established review subject. `Never exercised` and an authoritatively bounded `unknown` can be complete findings; they do not make the check inapplicable.
- **Expected observations:** Exercise-history status; most recent completed exercise or authoritative never-exercised state; stated, regulatory, or contractual cadence where applicable; scope; result; limitations; as-of date.
- **Likely acquisition mode(s):** Documentary exercise evidence, hybrid corroboration, and manual review.
- **Evidence/sufficiency principle:** History, date, applicable cadence, scope, result, and limitations must all be supported. v0.1 has no universal freshness threshold. Where an applicable stated, regulatory, or contractual cadence exists, timeliness may be reported against it; otherwise Plinth reports the dated evidence without generating a `stale` classification. Freshness never changes evidence coverage.

### PF-CONTINUITY-012 — What is the remediation status of material continuity weaknesses?

- **Allocator purpose:** Show whether each material exercise or incident weakness is open, closed, validated, accepted, failed, or unresolved.
- **Materiality:** HIGH.
- **Conceptual applicability:** Applies where at least one material continuity weakness has been identified independently from exercises, incidents, or other evidence. It does not apply only where an adequately established weakness assessment is empty; incomplete weakness discovery leaves applicability unresolved.
- **Expected observations:** Weakness; accountable remediation owner; current status; claimed completion evidence; validation or retest; residual qualification; accepted or unresolved state; limitations.
- **Likely acquisition mode(s):** Documentary remediation records, hybrid validation evidence, and manual review.
- **Evidence/sufficiency principle:** Every material weakness must have a bounded current remediation status. Open, failed, absent, or risk-accepted remediation can be fully evidenced; a management statement that an issue is closed is partial without completion evidence and appropriate validation.


## 7. Deferred candidate questions for testing

The following are recorded as explicit test questions. They do not add checks, change the five pillars or alter the retained catalogue:

- Does the catalogue give code correctness and audit coverage a sufficiently direct allocator answer?
- Does it distinguish the integrity and manipulation resistance of oracle/NAV data from who controls the oracle and what happens when it fails?
- Does it establish bridge and cross-chain integrity, including native/bridged identity and product-wide canonical supply, without awkward inference?
- Are material infrastructure dependencies and actual transaction conformance explicit enough?
- Does it capture factual operator and product operating history without judging manager quality or product credibility?
- Are manager conflicts and related-party service providers visible enough?
- Does reserve evidence expose attestation cadence, relationship, procedure, scope and independence clearly enough?
- Are secondary-market and holder concentration facts captured where they answer an allocator question?
- Is the line between normal-course and stressed redemption capacity consistently applied?

These questions may later support `MERGE`, `SPLIT`, `REMOVE`, `ADD`, `REWORD`, `CHANGE APPLICABILITY`, `CHANGE OBSERVATION BOUNDARY`, `CHANGE MATERIALITY` or `NO CHANGE`. No such consolidation decision is made in this phase.

## 8. Pre-consolidation testing boundaries

This working draft is ready to test as methodology, but it is not a finalized release. Testing should ask whether the applicable subset produces an allocator-useful Trust Center without forced exceptions and whether the output contract faithfully translates technical depth into plain institutional language.

This phase does not perform product mappings, consolidate the catalogue, add schemas or validation machinery, implement a Trust Center interface, or publish a release. v0.1 and every output produced under it remain unchanged.
