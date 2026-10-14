#!/usr/bin/env python3
"""Create a synthetic, compiler-accepted run and a fully authored presentation demo.

Every name and statement is fictional. This is an interface example, never research.
Run from an editable toolkit installation; output is private/generated, not committed.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from plinth import archive, catalogue, cli
from plinth.models import Campaign, EvidencePack, canonical_bytes, canonical_sha256
from plinth.vocab import AcquisitionMode

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/plinth-trust-center'
sys.path.insert(0, str(SKILL / 'scripts'))
import prefill_shell as prefill
from trust_center_records import Records, load_inputs, payload_text
from executive_questions import QUESTIONS, LABELS
from presentation import source_reference_entries, render_source_references_md

# One description per question, wholly synthetic. Context-only descriptions remain unresolved.
ANSWERS = (
    'Example Reserve describes a tokenized share in a fictional bond fund. Example Management is the stated issuer; the holder interest is described by the supplied share terms.',
    'The example terms identify a share interest but do not establish creditor ranking or the treatment of fund assets if an operating entity fails.',
    'The stated primary-market route is available to approved members who complete identity checks. Transfer eligibility follows the same membership rules.',
    'The issuer describes short-duration government bonds and cash balances supporting the share value. These are described assets, not verified holdings.',
    'Example Custody is named as the asset custodian. The description calls for separate fund accounts; account ownership and operative segregation have not been verified.',
    'A monthly statement is described, but no signed independent assurance report establishes its population, methodology or frequency.',
    'The described return comes from bond interest after costs. Share value can fall when bond prices change, and defaults or operating disruption could affect recovery.',
    'The stated annual management fee is 0.5%, deducted from fund value. The description also identifies settlement charges; a complete schedule and actual charges remain unverified.',
    'The issuer describes two director approvals for changes to issuance permissions. An identified administrator may pause the primary-market service; current deployed configuration is unresolved.',
    'The stated valuation uses closing bond prices and cash balances, updated each business day. Independent replay requires the input prices, positions and adjustment records.',
    'Approved members may request cash redemption through the primary-market service. The description permits temporary suspension during valuation or settlement disruption.',
    'The available description does not establish which record has legal precedence if the token ledger and the membership register disagree.',
)
UNRESOLVED = {2, 6, 12}
LIMITATIONS = (
    'Which signed instrument establishes the holder claim, and which entity is legally responsible for it?',
    'Provide the governing documents and insolvency analysis establishing holder ranking and asset recovery.',
    'Confirm the current eligibility rules for issuance, holding, transfer and redemption, including any channel differences.',
    'Provide dated positions and account evidence reconciling the asset population to the recognized shares.',
    'Provide the executed custody mandate and account records establishing ownership, segregation and any encumbrances.',
    'Provide a signed assurance report with its subject, date, population, procedures and limitations.',
    'Provide the complete return and loss allocation rules, including deductions and disruption treatment.',
    'Provide the current complete fee schedule, including settlement and exit charges, and explain how deductions are applied.',
    'Provide the current deployment identifiers, controller register and operative authorization rules.',
    'Provide valuation inputs, adjustment rules and controls sufficient to reproduce a dated valuation.',
    'Provide operative redemption terms, settlement evidence and the procedure for pending requests during suspension.',
    'Identify the authoritative ownership record and the procedure and authority for resolving a discrepancy.',
)


def build(out: Path) -> None:
    if out.exists():
        raise ValueError('Choose a new output directory; accepted demo records are never overwritten.')
    out.mkdir(parents=True)
    now = datetime.now(UTC)
    campaign = Campaign.model_validate({
        'run_id': 'synthetic-presentation', 'subject': 'Example Reserve',
        'subject_description': 'Fictional issuer, share interest, bond fund and custody arrangement for interface testing.',
        'cutoff': now.isoformat(), 'declared_acquisition_modes': ['MANUAL_UPLOAD'],
        'declared_scope_note': 'Synthetic supplied text only; no real issuer, deployment or research.',
        'bounded_public_evidence': False,
    })
    run = archive.create_run(campaign, runs_root=out / 'runs')
    text = out / 'synthetic-source.txt'
    text.write_text('\n\n'.join(f'Question {n}\n{answer}' for n, answer in enumerate(ANSWERS, 1)))
    run, acquisition, artifact = archive.add_artifact(
        run, text, source_id='SRC-DESIGN', acquisition_mode=AcquisitionMode.MANUAL_UPLOAD,
        media_type='text/plain', retrieved_at=now, operator='example author')
    observations, locators = [], []
    for n, answer in enumerate(ANSWERS, 1):
        locators.append({'locator_id': f'LOC-Q{n}', 'artifact_sha256': artifact.sha256,
                         'locator_type': 'document_section', 'section': f'Question {n}', 'quoted_text': answer})
        observations.append({'observation_id': f'OBS-Q{n}', 'subject': 'Example Reserve design',
                             'proposition': answer, 'supports': [{'acquisition_id': acquisition.acquisition_id,
                                                                'locator_id': f'LOC-Q{n}'}]})
    pack = EvidencePack.model_validate({
        'schema_version': 'plinth.evidence/1', 'campaign': campaign.model_dump(mode='json'),
        'sources': [{'source_id': 'SRC-DESIGN', 'title': 'Example Reserve supplied design description',
                     'publisher': 'Example Management', 'source_type': 'issuer_documentation',
                     'research_posture': 'self_attestation', 'stated_limitations': ['Fictional statements for presentation testing; no real product or verified operation.']}],
        'acquisitions': [acquisition.model_dump(mode='json')], 'artifacts': [artifact.model_dump(mode='json')],
        'locator_catalog': locators, 'observations': observations,
        'routes': [{'route_id': 'R-DESIGN', 'description': 'Synthetic documentary route', 'acquisition_mode': 'MANUAL_UPLOAD',
                    'status': 'PARTIAL', 'source_ids': ['SRC-DESIGN'], 'limitation': 'Full check propositions are deliberately unfinished.'}],
        'generated_at': (now + timedelta(minutes=1)).isoformat(),
    })
    (run.root / 'proposed-documentary-evidence.json').write_bytes(canonical_bytes(pack))
    if cli.main(['ingest', 'evidence', campaign.run_id, '--runs-root', str(out / 'runs')]) != 0:
        raise ValueError('Synthetic evidence did not pass the compiler.')
    cat = json.loads(catalogue.CATALOGUE_PATH.read_bytes())
    checks = []
    for c in cat['checks']:
        checks.append({'check_id': c['check_id'], 'applicability': 'APPLIES',
                       'applicability_basis': 'Synthetic operating perimeter for a presentation example.',
                       'applicability_observation_ids': ['OBS-Q1'], 'coverage': 'NOT_ASSESSED',
                       'coverage_basis': 'The complete proposition is unfinished in the synthetic route.',
                       'finding': 'Only the supplied synthetic design is described; the full check remains unfinished.',
                       'gap': {'question': c['question'], 'what_is_known': 'The supplied synthetic design is available.',
                               'what_remains_unresolved': 'The complete check proposition has not been assessed.',
                               'what_this_means': 'These statements do not establish complete evidence coverage.',
                               'what_would_close_it': 'Scoped operative records addressing the complete proposition.',
                               'evidence': 'Synthetic source description only.', 'evidence_observation_ids': ['OBS-Q1']}})
    assessment = {'schema_version': 'plinth.assessment/1', 'checks': checks,
                  'meta': {'campaign_run_id': campaign.run_id, 'framework_version': cat['framework_version'],
                           'catalogue_sha256': run.manifest.catalogue_sha256,
                           'evidence_pack_sha256': canonical_sha256(pack), 'generated_at': (now + timedelta(minutes=2)).isoformat()}}
    (run.root / 'proposed-assessment.json').write_text(json.dumps(assessment))
    for action in ('check', 'ingest'):
        if cli.main([action, 'assessment', campaign.run_id, '--runs-root', str(out / 'runs')]) != 0:
            raise ValueError('Synthetic assessment did not pass the compiler.')
    if cli.main(['verify', campaign.run_id, '--runs-root', str(out / 'runs')]) != 0:
        raise ValueError('Synthetic run failed verification.')
    inputs = load_inputs(run.root / 'assessment.json', run.accepted_pack_path, catalogue.CATALOGUE_PATH)
    records = Records(inputs)
    page, _ = prefill.fill(prefill.DEFAULT_SHELL.read_text(), records, payload_text(inputs), 'Example Reserve')
    for n, _, mapping in QUESTIONS:
        state = 'answer-unresolved' if n in UNRESOLVED else 'source-described'
        label, css = LABELS[state]
        replacements = {'STATE': state, 'LABEL': label, 'CLASS': css, 'OBSERVATION IDS': f'OBS-Q{n}',
                        'PILLARS': ' · '.join(dict.fromkeys(records.pillar_label[records.pillar_of[c]] for c in mapping)),
                        'ANSWER': '<p>' + html.escape(ANSWERS[n - 1]) + '</p>', 'LIMITATION': html.escape(LIMITATIONS[n - 1]),
                        'BASIS': f'<p>This supplied description is documentary evidence, not verified operation.</p><p><a href="#observation-OBS-Q{n}">Supporting observation ↗</a> · <a href="#source-SRC-DESIGN">Source description ↗</a></p>'}
        for name, value in replacements.items():
            page = page.replace(f'{{{{Q{n} {name}}}}}', value)
    page = page.replace('{{SUBJECT SUMMARY}}', 'A fictional tokenized bond fund used to demonstrate the twelve-question Trust Center interface. All descriptions and parties are synthetic.')
    page = page.replace('{{PARTICIPATION BOUNDARY}}', 'Synthetic demonstration · No commercial participation or publication approval.')
    page = page.replace('{{CLAIM PATH}}', 'Holder → described share interest → stated fund claim → Example Management / fund vehicle → account owner unresolved → Example Custody, issuer-named → described bonds and cash.')
    for name, value in {'ENTRY SUMMARY': 'Approved members subscribe through the stated primary-market service.',
                        'HOLDING SUMMARY': 'Share value follows described assets after fees; holdings remain unverified.',
                        'EXIT SUMMARY': 'Members request cash settlement; suspension terms and actual liquidity remain unverified.',
                        'EVIDENCE BOUNDARY TEXT': 'This example contains synthetic supplied issuer descriptions. It establishes no real reserves, legal rights, deployed permissions or operating state.'}.items():
        page = page.replace('{{' + name + '}}', value)
    parts = re.split(r'(<script type="application/json" id="plinth-research-state">.*?</script>)', page, flags=re.S)
    for i, part in enumerate(parts):
        if part.startswith('<script type="application/json"'):
            continue
        part = part.replace('{{SOURCE_ID}}', 'SRC-DESIGN').replace('{{SOURCE TITLE}}', 'Supplied design description')
        part = part.replace('{{OBSERVATION_IDS}}', 'OBS-Q1').replace('{{CHECK_IDS}}', records.check_order[0])
        part = part.replace('{{CHECK_ID}}', records.check_order[0]).replace('{{EVIDENCE_CLASS}}', 'issuer_declared')
        parts[i] = prefill.PLACEHOLDER_RE.sub('The supplied synthetic design does not establish operative records.', part)
    page = ''.join(parts)
    (out / 'index.html').write_text(page)
    (out / 'source-references.md').write_text(render_source_references_md(source_reference_entries(records)))
    print(f'Demo: {out / "index.html"}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        build(args.out)
    except (ValueError, OSError) as error:
        parser.exit(1, f'FAIL: {error}\n')
