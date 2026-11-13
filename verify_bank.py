#!/usr/bin/env python3
"""Verify the rebuilt dark-mode bank: render every page, check darkness,
coverage, MCQ answer text, ordering and bookmarks; emit contact sheets."""
import fitz, json, os, re, sys
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(ROOT, '.rebuilt.pdf')
MAN = os.path.join(ROOT, '.manifest.json')
STATS = os.path.join(ROOT, '.stats.json')
SHEETS = os.path.join(ROOT, 'review_sheets')
os.makedirs(SHEETS, exist_ok=True)
LOG = open(os.path.join(ROOT, '.review.log'), 'w', buffering=1)

def log(*a):
    print(*a, file=LOG)

doc = fitz.open(PDF)
man = json.load(open(MAN))
stats = json.load(open(STATS))
dark, blank, errors, answers = [], [], [], {}
label_re = re.compile(r'^(May/June|October/November|February/March) (\d{4}) \u2022 Paper (\d) \u2022 Variant (\d) \u2022 Question (\d+)')
ans_re = re.compile(r'Correct answer: ([A-D])')

ORDER = {'October/November': 2, 'May/June': 1, 'February/March': 0}

def sort_key_from_label(lab):
    m = label_re.match(lab)
    return (-int(m.group(2)), -ORDER[m.group(1)], int(m.group(3)), int(m.group(4)), int(m.group(5)))

# 1. render every page
print('rendering', doc.page_count, 'pages')
for i, page in enumerate(doc):
    try:
        pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
    except Exception as e:
        errors.append((i, str(e)))
        continue
    v = pix.samples
    n = max(1, len(v) // 3)
    mean = sum(v) / len(v)
    bright = sum(1 for j in range(0, len(v), 3) if v[j] > 60) / n
    if mean > 90:
        dark.append((i, round(mean, 1)))
    if bright < 0.002:
        blank.append((i, round(bright, 5)))
    if (i + 1) % 500 == 0:
        print('  ...', i + 1)

# 2. text checks
full_text = ''
for i, page in enumerate(doc):
    t = page.get_text()
    for m in ans_re.finditer(t):
        answers[len(answers) + 1] = m.group(1)

mcq_expected = stats['mcq']
n_ans = len(answers)

# 3. ordering + labels vs tracker
labels = [e['label'] for e in man]
order_ok = all(sort_key_from_label(labels[i]) <= sort_key_from_label(labels[i + 1])
               for i in range(len(labels) - 1))

toc = doc.get_toc()
toc_labels = [t[1] for t in toc if t[0] == 2]
toc_ok = len(toc_labels) == len(man)

# bookmarks must start at their entry pages, and the label must really be there
bm_bad = []
for t, e in zip([t for t in toc if t[0] == 2], man):
    if not e['pages'] or t[2] != e['pages'][0]:
        bm_bad.append((e['label'], t[2], e['pages'][:1]))
    else:
        ptxt = doc[e['pages'][0] - 1].get_text().replace('\u00b7', '\u2022')
        if e['label'] not in ptxt:
            bm_bad.append((e['label'], 'label not on start page', e['pages'][:1]))

# 4. MCQ answer letters must match the tracker keys
tracker_keys = {}
for ln in open(os.path.join(ROOT, 'biology-5090', 'biology_5090_question_bank_tracker.txt'), encoding='utf-8'):
    f = ln.rstrip('\n').split('\t')
    if len(f) >= 13 and f[12] == 'INCLUDED' and f[4] == '1':
        m = re.match(r'^Question (\d+) / key ([A-D])$', f[9])
        if m:
            key = (int(f[1]), f[2], f[3], f[4], int(f[5]))
            tracker_keys[key] = m.group(2) if key not in tracker_keys else tracker_keys[key]
# rebuild per-label answers from the pdf text near each bookmark
per_entry = []
ans_mismatch = 0
for e in man:
    lab = e['label']
    m = label_re.match(lab)
    key = (-int(m.group(2)), -ORDER[m.group(1)], int(m.group(3)), int(m.group(4)), int(m.group(5)))
    if m.group(3) == '1':
        p0, p1 = e['pages'][0], e['pages'][1]
        t = ''.join(doc[p - 1].get_text() for p in range(p0, min(p1, p0 + 2) + 1) if 1 <= p <= doc.page_count)
        t = t.replace('\u00b7', '\u2022')
        am = re.search(re.escape(lab) + r'\nCorrect answer: ([A-D])', t)
        got = am.group(1) if am else None
        want = tracker_keys.get((int(m.group(2)), m.group(1), m.group(4), '1', int(m.group(5))))
        if got != want:
            ans_mismatch += 1
            log('ANSWER MISMATCH', lab, 'got', got, 'want', want)

log('pages', doc.page_count)
log('dark pages (light leaks)', dark[:20], len(dark))
log('blank pages', blank[:20], len(blank))
log('render errors', errors)
log('answers found', n_ans, 'expected mcq', mcq_expected)
log('order ok', order_ok)
log('toc entries', len(toc_labels), 'manifest', len(man), 'match', toc_ok)
log('bookmark page mismatches', bm_bad[:10], len(bm_bad))
log('answer mismatches', ans_mismatch)

# 6. span sanity: every entry has content items with sane source pages
srcs = {}
span_bad = []
for e in man:
    if not e.get('items'):
        span_bad.append((e['label'], 'no items'))
        continue
    for it in e['items']:
        fn = it['source']
        if fn not in srcs:
            srcs[fn] = fitz.open(os.path.join(ROOT, 'biology-5090', fn)).page_count
        sp = it['source_pages']
        if not sp or sp[0] < 1 or sp[-1] > srcs[fn] or sp[0] > sp[-1]:
            span_bad.append((e['label'], fn, sp))
log('span problems', span_bad[:10], len(span_bad))

# 5. contact sheets: 20 sample pages per sheet, 5x4 grid
print('contact sheets')
idxs = list(range(0, doc.page_count, max(1, doc.page_count // 600)))
for si in range(0, min(len(idxs), 600), 20):
    chunk = idxs[si:si + 20]
    thumbs = []
    for i in chunk:
        pix = doc[i].get_pixmap(matrix=fitz.Matrix(0.34, 0.34))
        thumbs.append((i, Image.frombytes('RGB', (pix.width, pix.height), pix.samples)))
    if not thumbs:
        break
    w, h = thumbs[0][1].size
    sheet = Image.new('RGB', (w * 5 + 24, h * 4 + 24), (28, 28, 28))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    for k, (pi, im) in enumerate(thumbs):
        x = (k % 5) * (w + 4) + 4
        y = (k // 5) * (h + 4) + 4
        sheet.paste(im, (x, y))
        d.text((x + 3, y + 3), str(pi + 1), fill=(255, 60, 60))
    sheet.save(os.path.join(SHEETS, f'sheet{si // 20:03d}.png'))
print('DONE')
print(open(os.path.join(ROOT, '.review.log')).read()[:4000])
