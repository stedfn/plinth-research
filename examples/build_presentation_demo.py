#!/usr/bin/env python3
"""Build an empty-evidence template preview, never fictional product research.

The accepted run has no sources, artifacts or observations. All 63 checks have
UNRESOLVED applicability and null coverage. Visible guidance explains authoring
slots; it makes no claims about an issuer, assets, fees, controls or operation.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from plinth import archive, catalogue, cli
from plinth.models import Campaign, EvidencePack, canonical_bytes, canonical_sha256

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/plinth-trust-center'
sys.path.insert(0, str(SKILL / 'scripts'))
import prefill_shell as prefill
from trust_center_records import Records, load_inputs, payload_text
from executive_questions import QUESTIONS
from presentation import source_reference_entries, render_source_references_md

QUESTION_GUIDANCE = (
    'Describe the product, issuer and legal nature of the holder interest from accepted observations.',
    'Explain the documented insolvency position. Mark the claim path and recovery terms unresolved where evidence stops.',
    'Describe eligibility separately for issuance, holding, transfer and redemption. Preserve channel distinctions.',
    'Identify the documented assets or obligations and their scope. Separate a stated backing model from recorded holdings.',
    'Identify the asset owner and custody arrangements. Distinguish named providers from executed mandates and verified segregation.',
    'Describe the verification record, author, date, population and limitations. Do not assume a report covers reserves.',
    'Explain the documented sources of return and how loss reaches the holder. Keep third-party activity separate.',
    'Describe the supported fees, deductions and settlement costs. Do not infer a complete schedule from one fee.',
    'Describe who can act, the authorization rules and the reviewed scope. Separate documented design from deployed state.',
    'Explain the supported valuation inputs, update process and what allows independent reproduction.',
    'Describe normal exit, settlement and disruption procedures. Keep pending-request and completed-settlement rules distinct.',
    'Identify the ownership record and discrepancy procedure if supported. Otherwise state which precedence question remains unresolved.',
)

PANEL_INTROS = {
    'CONTROL': 'Describe supported action authorities, actors and approval rules here.',
    'BACKING': 'Describe the documented asset population, title, custody and assurance scope here.',
    'ECONOMICS': 'Describe entry, value movement, deductions and exit here.',
    'GOVERNANCE': 'Describe issuer identity, holder rights, eligibility and party relationships here.',
    'CONTINUITY': 'Describe supported normal operation, disruption and recovery arrangements here.',
    'CLAIM': 'Map the holder-to-asset path from records. Mark each unsupported link unresolved.',
    'LEGAL': 'Record the governing entities, instruments and agreements without inferring legal effect.',
    'QUANTITY': 'Keep quantities attached to their own identifiers, dates, populations and scopes.',
    'GAPS': 'Group unresolved propositions in neutral framework order and link to complete check records.',
    'REQUESTS': 'These questions come from the accepted check-level gap records.',
    'SOURCES': 'Only actual source and acquisition records belong here. This preview supplies none.',
    'TECHNICAL': 'Bind technical records to official identifiers and scope before describing observed state.',
    'APPENDIX': 'The compiler records below remain unchanged. This preview has no source artifacts or observations.',
}


def preview_slot(name: str) -> str:
    """Explicit preview guidance, not invented claims or a universal filler sentence."""
    if name.endswith(('CITATIONS', 'OBSERVATION_IDS')):
        return ''
    if name.endswith('CHECK_IDS'):
        return ''
    prefix = name.split('_', 1)[0]
    field = name.removeprefix(prefix + '_')
    if field in ('INTRO', 'SECTION_LEDE'):
        return PANEL_INTROS.get(prefix, 'Populate this section from accepted records.')
    if name == 'TECHNICAL_STATE':
        return 'No state records supplied'
    if name == 'TECHNICAL_SCOPE':
        return 'Template preview only'
    if name in ('QUANTITY_GROUP', 'QUANTITY_IDENTIFIER', 'QUANTITY_VALUE', 'QUANTITY_SCOPE'):
        return 'Not supplied'
    if name.startswith('TECHNICAL_RECORD_'):
        return {'TITLE': 'Deployment / state record', 'SCOPE': 'No record supplied',
                'UNRESOLVED': 'Product binding and recorded state are unresolved.'}.get(field.removeprefix('RECORD_'), '')
    if name == 'GAPS_THEME_TITLE':
        return 'Product applicability remains unresolved'
    if name == 'GAPS_THEME_TEXT':
        return 'No product evidence was supplied. The full framework questions remain in the check register.'
    if field.endswith('KNOWN'):
        return 'No product observation supplied.'
    if field.endswith('UNRESOLVED'):
        return 'Awaiting product-specific records.'
    if 'LIMITATION' in field:
        return 'No product evidence is supplied in this preview. This does not establish absence of the product or its arrangements.'
    if field.endswith('TITLE'):
        return 'Record scope'
    if field in ('TABLE_CELL', 'IDENTIFIER', 'CELL_NOTE', 'FACT', 'CAVEAT'):
        return 'Not supplied'
    return 'Describe ' + field.replace('_', ' ').lower() + ' from accepted observations.'


def author_preview(inputs) -> str:
    if inputs.evidence.get('sources') or inputs.evidence.get('observations') or any(
        check['applicability'] != 'UNRESOLVED' or check.get('coverage') is not None
        for check in inputs.assessment['checks']
    ):
        raise ValueError('Preview guidance requires empty evidence and unresolved applicability; author real runs from the slot guide.')
    records = Records(inputs)
    page, _ = prefill.fill(prefill.DEFAULT_SHELL.read_text(), records, payload_text(inputs), 'Trust Center template')
    for n, _, mapping in QUESTIONS:
        replacements = {'STATE': 'answer-unresolved', 'LABEL': 'Answer unresolved', 'CLASS': 'p-no',
                        'OBSERVATION IDS': '',
                        'PILLARS': ' · '.join(dict.fromkeys(records.pillar_label[records.pillar_of[c]] for c in mapping)),
                        'ANSWER': '<p>' + html.escape(QUESTION_GUIDANCE[n - 1]) + '</p>',
                        'LIMITATION': 'No product evidence supplied. Populate the answer and boundary from the accepted run.',
                        'BASIS': '<p>No supporting observation is supplied in this preview. Add the accepted observation IDs and source links when authoring.</p>'}
        for key, value in replacements.items():
            page = page.replace(f'{{{{Q{n} {key}}}}}', value)
    values = {'SUBJECT SUMMARY': 'Template preview · No product evidence supplied. The text describes authoring slots, not a product or its operation.',
              'PARTICIPATION BOUNDARY': 'Authoring guidance only. No issuer, provider, fee, asset holding or deployed capability is assumed.',
              'CLAIM PATH': 'Populate each link from observations; mark unsupported relationships unresolved or not applicable.',
              'ENTRY SUMMARY': 'Describe the supported entry route and its scope.',
              'HOLDING SUMMARY': 'Describe what the holder holds and how value moves.',
              'EXIT SUMMARY': 'Describe the supported exit route and disruption limits.',
              'EVIDENCE BOUNDARY TEXT': 'This preview has zero sources and zero observations. All framework applicability remains unresolved; no product finding is asserted.',
              'PILLAR OPEN QUESTION': 'Which product records establish this pillar’s structural conditions?',
              'OBSERVATION_IDS': '', 'CHECK_IDS': '', 'EVIDENCE BOUNDARY': 'Template preview — no product evidence'}
    parts = re.split(r'(<script type="application/json" id="plinth-research-state">.*?</script>)', page, flags=re.S)
    for i, part in enumerate(parts):
        if part.startswith('<script type="application/json"'):
            continue
        for key, value in values.items():
            part = part.replace('{{' + key + '}}', html.escape(value))
        parts[i] = prefill.PLACEHOLDER_RE.sub(lambda match: html.escape(preview_slot(match[0][2:-2])), part)
    return ''.join(parts)


def build(out: Path) -> None:
    if out.exists():
        raise ValueError('Choose a new output directory; accepted preview records are never overwritten.')
    out.mkdir(parents=True)
    now = datetime.now(UTC)
    campaign = Campaign.model_validate({
        'run_id': 'template-preview', 'subject': 'Unpopulated Trust Center template',
        'subject_description': 'Presentation preview without a product evidence perimeter.',
        'cutoff': now.isoformat(), 'declared_acquisition_modes': ['MANUAL_UPLOAD'],
        'declared_scope_note': 'No product sources or observations supplied; authoring guidance only.',
        'bounded_public_evidence': False,
    })
    run = archive.create_run(campaign, runs_root=out / 'runs')
    pack = EvidencePack.model_validate({'schema_version': 'plinth.evidence/1',
                                      'campaign': campaign.model_dump(mode='json'),
                                      'generated_at': datetime.now(UTC).isoformat()})
    (run.root / 'proposed-documentary-evidence.json').write_bytes(canonical_bytes(pack))
    if cli.main(['ingest', 'evidence', campaign.run_id, '--runs-root', str(out / 'runs')]) != 0:
        raise ValueError('Empty preview evidence did not pass the compiler.')
    cat = json.loads(catalogue.CATALOGUE_PATH.read_bytes())
    checks = [{'check_id': c['check_id'], 'applicability': 'UNRESOLVED',
               'applicability_basis': 'No product observation establishes the structural condition for this preview.',
               'finding': 'No product evidence was supplied; applicability remains unresolved.',
               'gap': {'question': c['question'], 'what_is_known': 'The framework question is available, but no product observations are supplied.',
                       'what_remains_unresolved': 'Whether the structural condition described in this question exists for the reviewed product.',
                       'what_this_means': 'Applicability remains unresolved and has no coverage value.',
                       'what_would_close_it': 'Product-specific records establishing whether the question’s structural condition is present.',
                       'evidence': 'No product observations supplied.'}}
              for c in cat['checks']]
    assessment = {'schema_version': 'plinth.assessment/1', 'checks': checks,
                  'meta': {'campaign_run_id': campaign.run_id, 'framework_version': cat['framework_version'],
                           'catalogue_sha256': run.manifest.catalogue_sha256, 'evidence_pack_sha256': canonical_sha256(pack),
                           'generated_at': datetime.now(UTC).isoformat()}}
    (run.root / 'proposed-assessment.json').write_text(json.dumps(assessment))
    for action in ('check', 'ingest'):
        if cli.main([action, 'assessment', campaign.run_id, '--runs-root', str(out / 'runs')]) != 0:
            raise ValueError('Empty preview assessment did not pass the compiler.')
    if cli.main(['verify', campaign.run_id, '--runs-root', str(out / 'runs')]) != 0:
        raise ValueError('Empty preview run failed verification.')
    inputs = load_inputs(run.root / 'assessment.json', run.accepted_pack_path, catalogue.CATALOGUE_PATH)
    (out / 'index.html').write_text(author_preview(inputs))
    (out / 'source-references.md').write_text(render_source_references_md(source_reference_entries(Records(inputs))))
    print(f'Preview: {out / "index.html"}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        build(args.out)
    except (ValueError, OSError) as error:
        parser.exit(1, f'FAIL: {error}\n')
