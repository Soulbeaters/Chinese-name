# -*- coding: utf-8 -*-
import json

data = json.load(open('C:/program 1 in 2025/test_data/crossref_10k.json', 'r', encoding='utf-8'))

no_lastname = [i for i, d in enumerate(data) if 'lastname' not in d or not d.get('lastname')]
no_firstname = [i for i, d in enumerate(data) if 'firstname' not in d or not d.get('firstname')]
no_original_name = [i for i, d in enumerate(data) if 'original_name' not in d or not d.get('original_name')]

print(f'Total records: {len(data)}')
print(f'Records without lastname: {len(no_lastname)}')
print(f'Records without firstname: {len(no_firstname)}')
print(f'Records without original_name: {len(no_original_name)}')

missing_any = set(no_lastname) | set(no_firstname) | set(no_original_name)
print(f'\nRecords missing any field: {len(missing_any)}')

if missing_any:
    print('\nExamples:')
    for i in list(missing_any)[:5]:
        d = data[i]
        print(f'  [{i}] original_name: "{d.get("original_name", "")}"')
        print(f'       lastname: "{d.get("lastname", "")}"')
        print(f'       firstname: "{d.get("firstname", "")}"')
