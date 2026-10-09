# Assessment and authoring procedure

This reference preserves the non-obvious decisions learned from the OUSG calibration while remaining product-neutral.

## Canonical records

Keep assessment and presentation separate. The assessment contains two canonical collections:

```text
observations[]
checks[]
```

An observation records:

- stable ID;
- factual statement;
- subject and scope;
- relevant time, effective period, or deterministic anchor;
- documentary, deterministic, or derived acquisition mode;
- source IDs and exact locators;
- optional parent observations and a derivation explanation.

Each check records:

- exact Framework ID, pillar, and question;
- applicability;
- coverage;
- supporting observation IDs;
- searched routes and whether the required search was completed;
- neutral factual finding;
- complete gap where required.

Names and file shapes may follow an established project convention, but the semantics above must remain explicit.

## Applicability and coverage

Applicability:

- `APPLIES`: evidence establishes the structural condition for asking the question.
- `DOES_NOT_APPLY`: positive evidence establishes that the structural condition is absent.
- `UNRESOLVED`: evidence does not establish whether the structural condition is present.

Coverage:

- `EVIDENCED`: the complete bounded proposition is supported by qualifying evidence.
- `PARTIAL`: qualifying evidence supports only part of the proposition.
- `MISSING`: no qualifying evidence was found after every required in-scope route was completed.
- `NOT_ASSESSED`: a required route was access-controlled, excluded, unavailable, or otherwise incomplete.
- `CONTRADICTORY`: qualifying evidence conflicts and no explicit precedence rule resolves it.
- `NOT_APPLICABLE`: used only with positively supported `DOES_NOT_APPLY`.

`UNRESOLVED` applicability always has null coverage. Coverage measures evidence completion, not product quality, risk, importance, or finding favorability.

## Evidence gates

Qualify evidence proposition by proposition:

1. **Identity:** is it the correct subject, entity, contract, account, asset, route, or representation?
2. **Authority and scope:** can this source establish this kind of fact, across the required population and period?
3. **Time:** is the statement current, historical, prospective, point-in-time, or operating-period evidence?

Preserve these recurring boundaries:

- issuer statement versus independent confirmation;
- provider capability versus actual engagement;
- registrant submission versus regulator verification;
- wrapper facts versus underlying-product facts;
- stated limit versus executable remaining capacity;
- current mechanics versus dated announcement;
- chain configuration versus real-world credential ownership or operating procedure;
- one filing or test versus complete obligation or operating-effectiveness evidence;
- separately anchored quantities versus a deduplicated product-wide total.

Do not use “newest wins” unless an explicit source rule establishes supersession or precedence.

## Complete gap contract

Every applicable check that is not fully evidenced, and every unresolved-applicability check, receives:

```text
Question
What is known
What remains unresolved
What this means
What would close it
Evidence
```

“What this means” states only the conclusion the current evidence cannot support. It must not state severity, probability, importance, recommendation, or a Plinth opinion.

“What would close it” requests proposition-appropriate evidence. Avoid prestige heuristics. For assurance and reserve verification, identify procedure, scope, period, cadence, exclusions, relationship, and the exact proposition established.

## Claim and party structure

Attempt to express, without forcing unsupported links:

```text
Holder
→ token or recorded interest
→ legal claim
→ issuing vehicle
→ asset owner
→ custodian
→ underlying asset
```

Identify manager, administrator, transfer agent, auditor, redemption operator, oracle or data provider, and technical controller where applicable. Mark links unresolved when the evidence does not establish them. A service-provider list is not a relationship graph.

## Plain-language synthesis

Each executive statement follows:

```text
Institutional question
→ plain factual answer
→ evidentiary limitation
→ optional technical basis
```

Simplification must preserve subject, scope, time, source authority, and uncertainty. Distinguish factual operating history from judgments about manager quality or credibility.

Use named source links in the human layer. Keep observation IDs accessible in drill-down and machine-readable state rather than dumping them into prose.

## Report structure

Use:

1. Product orientation
2. Claim and party structure
3. How value moves
4. Five trust pillars
5. Evidence gaps
6. Evidence coverage
7. Source register
8. Methodology and independence
9. Technical appendix
10. Complete check register

Every pillar contains:

1. concise institutional read;
2. supported evidence boundary;
3. unresolved evidence boundary;
4. product-specific factual display;
5. named sources;
6. collapsed complete checks.

Do not rank or hide applicable gaps. Editorial order may foreground the claim, parties, backing, value movement, and disruption behavior without becoming a materiality judgment.

## External judgments

When including a rating or research conclusion, state its exact subject, scale, date, methodology, posture, and commissioning relationship. Expose underlying evidence separately when available. Never translate an external grade into Plinth coverage or imply endorsement or contradiction.

## Review pass

After authoring, challenge every substantive synthesis for:

- correct observation and source lineage;
- source-to-proposition alignment;
- complete population and temporal scope;
- retained contradictions;
- absence of implied legal conclusions;
- absence of product-quality or investment judgments;
- faithful translation of technical facts;
- explicit evidence cutoff and public/private boundary.

Record unresolved methodology disagreements rather than deciding them silently.
