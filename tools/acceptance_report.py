"""Validate planning metadata, never execute or approve desktop acceptance."""
import argparse
import json
from pathlib import Path
import re

GATES = {'ci', 'kwin', 'visual', 'hardware', 'session'}
STATUSES = {'planned', 'partial', 'verified'}
STAGES = {'M0', 'M1', 'M2', 'M3', 'M4', 'extension'}


def validate(data):
    errors = []
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        return ['schema_version must be 1']
    reference = data.get('reference', {})
    if not isinstance(reference, dict) or not re.fullmatch('[0-9a-f]{40}', str(reference.get('commit', ''))):
        return ['reference must pin a full commit SHA']
    repository = reference.get('repository', '')
    if not isinstance(repository, str) or not repository.startswith('https://github.com/'):
        return ['reference repository must be a GitHub HTTPS URL']
    items = data.get('items')
    if not isinstance(items, list) or not items:
        return ['items must be a nonempty list']
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            errors.append('item must be an object')
            continue
        ident = item.get('id')
        if not isinstance(ident, str) or not re.fullmatch(r'[A-Z]+-\d{2}', ident):
            errors.append('invalid acceptance ID')
            continue
        if ident in seen:
            errors.append(f'{ident}: duplicate ID')
        seen.add(ident)
        if item.get('stage') not in STAGES or item.get('scope') not in {'required', 'extension'}:
            errors.append(f'{ident}: invalid stage or scope')
        if (item.get('stage') == 'extension') != (item.get('scope') == 'extension'):
            errors.append(f'{ident}: extension scope/stage must agree')
        if item.get('status') not in STATUSES:
            errors.append(f'{ident}: invalid status')
        for key in ('title',):
            if not isinstance(item.get(key), str) or not item[key].strip():
                errors.append(f'{ident}: {key} is required')
        for key in ('acceptance', 'sources', 'gates'):
            values = item.get(key)
            if not isinstance(values, list) or not values or any(not isinstance(x, str) or not x.strip() for x in values):
                errors.append(f'{ident}: {key} must contain nonempty strings')
        gates = item.get('gates', [])
        valid_gates = isinstance(gates, list) and all(isinstance(x, str) and x in GATES for x in gates)
        if not valid_gates or len(gates) != len(set(gates)):
            errors.append(f'{ident}: unknown or duplicate gate')
        sources = item.get('sources', [])
        prefix = f'{repository}/blob/{reference["commit"]}/'
        if isinstance(sources, list) and any(not isinstance(url, str) or not url.startswith(prefix) for url in sources):
            errors.append(f'{ident}: sources must use the pinned reference')
        evidence = item.get('evidence')
        if not isinstance(evidence, list):
            errors.append(f'{ident}: evidence must be a list')
            continue
        passed = set()
        reported = set()
        for record in evidence:
            if not isinstance(record, dict):
                errors.append(f'{ident}: evidence record must be an object')
                continue
            if (not isinstance(record.get('gate'), str) or record['gate'] not in GATES
                    or not isinstance(record.get('result'), str)
                    or record['result'] not in {'passed', 'failed', 'unrun'}):
                errors.append(f'{ident}: invalid evidence gate/result')
                continue
            if record['gate'] in reported:
                errors.append(f'{ident}: duplicate evidence gate; retain one current summary per gate')
            reported.add(record['gate'])
            # One report per gate may link a run containing multiple required scenarios.
            if record.get('result') == 'passed':
                if not re.fullmatch('[0-9a-f]{40}', str(record.get('matrix_commit', ''))):
                    errors.append(f'{ident}: passing evidence needs a Matrix SHA')
                elif not all(isinstance(record.get(key), str) and record[key].strip()
                             for key in ('report', 'reviewer')):
                    errors.append(f'{ident}: passing evidence needs report and reviewer')
                else:
                    passed.add(record['gate'])
        if item.get('status') == 'verified' and valid_gates and not set(gates).issubset(passed):
            errors.append(f'{ident}: verified requires reviewed passing evidence for every gate')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Validate metadata only')
    parser.add_argument('file', nargs='?', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'docs/acceptance.json')
    args = parser.parse_args()
    try:
        data = json.loads(args.file.read_text())
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    errors = validate(data)
    if errors:
        parser.exit(1, '\n'.join(errors) + '\n')
    if args.check:
        print('Acceptance metadata valid; desktop scenarios were not executed.')
        return
    required = [x for x in data['items'] if x['scope'] == 'required']
    verified = sum(x['status'] == 'verified' for x in required)
    print(f'Required acceptance: {verified}/{len(required)} verified (metadata only).')
    for item in data['items']:
        print(f'{item["id"]:12} {item["stage"]:10} {item["status"]:9} {item["title"]}')
    print('Release readiness requires actual evidence and review, not this report.')


if __name__ == '__main__':
    main()
