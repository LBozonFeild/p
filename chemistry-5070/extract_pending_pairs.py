"""Extract eligible, uncertified question-paper/scheme pairs for subsequent human semantic review.

Text extraction is preparation only: it does not certify any question or pair.
"""
from pathlib import Path
import json
import pymupdf

ROOT = Path(__file__).resolve().parent
QUEUE = json.loads((ROOT / 'full_paper_work_queue.json').read_text())['pairs']
OUT = ROOT / 'pending_extractions'
OUT.mkdir(exist_ok=True)

for pair in QUEUE:
    if pair['status'] == 'certified':
        continue
    name = f"{pair['sequence']:03d}_{Path(pair['question_paper']).stem}"
    target = OUT / f'{name}.txt'
    with target.open('w', encoding='utf-8') as output:
        for label, filename in [('QUESTION PAPER', pair['question_paper']), ('MARK SCHEME', pair['mark_scheme'])]:
            with pymupdf.open(ROOT / filename) as doc:
                output.write(f'\n{label}: {filename} ({len(doc)} pages)\n')
                for page_number, page in enumerate(doc, 1):
                    output.write(f'\n=== {label} PAGE {page_number} ===\n')
                    output.write(page.get_text(sort=True).replace('\x00', ''))
                    output.write('\n')
    print(target.name)
print('Extraction only: certification status unchanged.')
