"""Aggregate full investigation tables without loading their rows into the browser."""
from collections import defaultdict
import csv


def summarize(path, toolsets, labels, document_column='', groups=(), query='', resource_type='', tool=''):
    memberships = defaultdict(list)
    for name, documents in toolsets.items():
        for document in documents:
            memberships[document].append(name)
    if tool and tool not in toolsets and tool != '__unassigned__':
        raise ValueError('Unknown exemplar tool')
    buckets = {}
    totals = {name: {'rows': 0, 'documents': set(), 'represented': set()} for name in toolsets}
    totals['__unassigned__'] = {'rows': 0, 'documents': set(), 'represented': set()}
    source_documents, matched_documents, unassigned_documents, overlap_documents, resource_types = set(), set(), set(), set(), set()
    source_rows = matched_rows = missing_document_rows = 0
    needle = query.strip().lower()
    with path.open(encoding='utf-8-sig', errors='replace', newline='') as handle:
        reader = csv.DictReader(handle, delimiter='\t' if path.suffix == '.tsv' else ',')
        headers = reader.fieldnames or []
        if not document_column:
            document_column = next((h for h in ('document', 'document_id', 'pdf', 'id') if h in headers), '')
        if not document_column or document_column not in headers:
            raise ValueError('Choose a column containing PDF document IDs to summarize across exemplars. Tables of totals without document IDs cannot be mapped to exemplars.')
        if document_column in ('prefix', 'resource_type', 'resource_name', 'number', 'object', 'reference', 'scope'):
            suggested = next((h for h in ('document', 'document_id', 'pdf', 'id') if h in headers), '')
            if suggested:
                raise ValueError(f'Choose {suggested} as the PDF ID column. {document_column} contains resource data, not PDF document IDs.')
        if len(groups) > 2 or any(g not in headers for g in groups) or len(set(groups)) != len(groups):
            raise ValueError('Choose up to two different result columns for the breakdown')
        if resource_type and 'resource_type' not in headers:
            raise ValueError('This table has no resource_type column')
        for raw in reader:
            row = {key: value or '' for key, value in raw.items() if key is not None}
            source_rows += 1
            if row.get('resource_type'):
                resource_types.add(row['resource_type'])
            document = row.get(document_column, '').strip().upper()
            names = memberships.get(document) or ['__unassigned__']
            if document:
                source_documents.add(document)
                for name in names:
                    totals[name]['represented'].add(document)
            if needle and needle not in ' '.join(row.values()).lower():
                continue
            if resource_type and row.get('resource_type') != resource_type:
                continue
            if tool and tool not in names:
                continue
            matched_rows += 1
            if document:
                matched_documents.add(document)
                if names == ['__unassigned__']:
                    unassigned_documents.add(document)
                if len(names) > 1:
                    overlap_documents.add(document)
            else:
                missing_document_rows += 1
            values = tuple(row.get(g, '') for g in groups)
            for name in names:
                if tool and name != tool:
                    continue
                totals[name]['rows'] += 1
                if document:
                    totals[name]['documents'].add(document)
                bucket = buckets.setdefault((name, values), {'rows': 0, 'documents': set()})
                bucket['rows'] += 1
                if document:
                    bucket['documents'].add(document)

    def metrics(name, item):
        exemplars = len(toolsets.get(name, ()))
        documents = len(item['documents'])
        return {'tool': 'Unassigned' if name == '__unassigned__' else name,
                'toolKey': name, 'producer': labels.get(name, 'No exemplar membership'),
                'rows': item['rows'], 'documents': documents, 'exemplars': exemplars,
                'represented': len(totals[name]['represented']),
                'coverage': round(documents / exemplars * 100, 2) if exemplars else None}

    selected = [name for name in sorted(toolsets) if not tool or tool == name]
    if (not tool and totals['__unassigned__']['rows']) or tool == '__unassigned__':
        selected.append('__unassigned__')
    overview = [metrics(name, totals[name]) for name in selected]
    if groups:
        rows = [{**metrics(name, item), 'values': list(values)} for (name, values), item in buckets.items()]
        rows.sort(key=lambda r: (r['toolKey'], -r['documents'], -r['rows'], r['values']))
    else:
        rows = [{**item, 'values': []} for item in overview]
    return {'headers': headers, 'documentColumn': document_column, 'groups': list(groups), 'resourceTypes': sorted(resource_types),
            'rows': rows, 'overview': overview,
            'counts': {'sourceRows': source_rows, 'sourceDocuments': len(source_documents),
                       'matchedRows': matched_rows, 'matchedDocuments': len(matched_documents),
                       'unassignedDocuments': len(unassigned_documents), 'missingDocumentRows': missing_document_rows,
                       'overlapDocuments': len(overlap_documents)},
            'scope': {'query': query, 'resourceType': resource_type, 'tool': tool}}
