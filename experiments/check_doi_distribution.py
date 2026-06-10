# -*- coding: utf-8 -*-
import json
from collections import Counter

data = json.load(open('C:/program 1 in 2025/test_data/crossref_10k.json', 'r', encoding='utf-8'))

doi_counts = Counter(d.get('doi') for d in data if d.get('doi'))
multi_author_dois = {doi: count for doi, count in doi_counts.items() if count > 1}

print(f'Total unique DOIs: {len(doi_counts)}')
print(f'DOIs with multiple authors: {len(multi_author_dois)}')
print(f'Total records in multi-author papers: {sum(multi_author_dois.values())}')

print(f'\nTop 5 papers by author count:')
for doi, count in sorted(multi_author_dois.items(), key=lambda x: -x[1])[:5]:
    print(f'  {doi}: {count} authors')
