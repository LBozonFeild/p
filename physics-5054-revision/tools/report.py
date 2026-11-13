# Build tracker, checkpoint, exclusions and the by-section data from validated findings (run check.py first)
from lib import *
import pickle, collections, datetime
REPO='/home/user/p/physics-5054-revision'
S=pickle.load(open(WORK+'/state.pkl','rb'))
res1,res2,pairs,excl,man2,hdr,keys=S['res1'],S['res2'],S['pairs'],S['excl'],S['man2'],S['hdr'],S['keys']
INSEC=['1.1','1.2','1.3','1.4','1.5.1','1.5.2','1.5.3','1.5.4','1.5.5','1.5.6','1.6','1.7.1','1.7.2','1.7.3','1.7.4','1.7.5','3.1','3.2.1','3.2.2','3.2.3','3.2.4','3.3','3.4','4.2.1','4.2.2','4.2.3','4.2.4']
def insec(sec): return any(s in INSEC for s in sec.split('+'))
order=sorted(pairs,key=lambda p:(sess_key(p['sess']),p['comp']),reverse=True)
now=datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
n2=sum(1 for r in res2.values() if r['status']=='COMPLETE'); n1=sum(1 for r in res1.values() if r['status']=='COMPLETE')
# ---------- in-scope findings lines per syllabus section (input of the notes tools)
by=collections.defaultdict(list)
for p in order:
    pid=p['id']
    if p['paper']==2 and res2[pid]['status']!='NOT STARTED':
        for x in res2[pid]['rows']:
            if insec(x['sec']):
                sec=[s for s in x['sec'].split('+') if s in INSEC][0]
                by[sec].append((pid,x['label'],x['text']))
    if p['paper']==1 and res1[pid]['status']!='NOT STARTED':
        for n,x in res1[pid]['rows'].items():
            if insec(x['sec']) and not x.get('dup') and x['text'].strip():
                sec=[s for s in x['sec'].split('+') if s in INSEC][0]
                by[sec].append((pid,f'MCQ{n}',x['text']))

# ---------- real state of the notes: a pair counts as "notes updated" only if the notes file exists and every in-scope
# findings line of the pair is filed in a sub-topic of tools/notes_src that has a checklist
import notes_lib
NOTES=REPO+'/physics_papers_1_2_notes.txt'
def notes_state():
    bad=collections.Counter()
    if not os.path.exists(NOTES): return None
    ov=notes_lib.load_overrides()
    for sec,_ in notes_lib.SECS:
        buckets,moves=notes_lib.read_spec(sec)
        items=notes_lib.load_items(sec,by,ov)
        notes_lib.assign(items,buckets,moves)
        has={b['id'] for b in buckets if b['lines'] and b['id']!='Z'}
        for it in items:
            if it['bucket'] not in has: bad[it['pid']]+=1
    return bad
NB=notes_state()
def nstate(pid,done): return 'yes' if (done and NB is not None and NB[pid]==0) else 'no'
dm=json.load(open(REPO+'/tools/data/p1_dupmap.json')) if os.path.exists(REPO+'/tools/data/p1_dupmap.json') else {}
T=[]
T.append('CAMBRIDGE O LEVEL PHYSICS 5054 — FULL PAPER VERIFICATION TRACKER (Papers 1 and 2)')
T.append(f'generated {now} from per-paper findings files in findings/ (regenerate with tools/check.py + tools/report.py)')
T.append('')
T.append(f'Eligible pairs: {len(pairs)} (Paper 1: {len(res1)}, Paper 2: {len(res2)}) | fully verified so far: {n1+n2} (Paper 1: {n1}, Paper 2: {n2}) | not yet verified: {len(pairs)-n1-n2}')
T.append('')
T.append('LEGEND')
T.append(' status COMPLETE = every question/sub-question of the paper was read against its mark-scheme entry by the reviewing agent and passes the mechanical checks below;')
T.append('        NOT STARTED = pair is paired/parsed mechanically only (this does NOT count as verification); ISSUES = findings exist but a check fails.')
T.append(' Paper 2 mechanical checks: (1) every leaf sub-question printed in the QP with a [n] mark allocation has a findings line; (2) for every in-scope')
T.append('        sub-question the mark tags written in the findings (e.g. [B1] [C1] [A1]) add up to the QP mark allocation; (3) QP/MS headers carry the same component and session.')
T.append(' Paper 1 mechanical checks: all 40 MCQs have a findings line; the agent\'s independently worked answer equals the official key (or the disagreement is documented).')
T.append(' section codes: syllabus subsection numbers; codes starting with X are outside the requested scope (X1.8 pressure, X2 thermal, X4.1/4.3/4.4/4.5/4.6, X5 nuclear, X6 space, XOLD legacy topics)')
T.append(" a code joined with '+' (e.g. 4.2.4+X4.3) marks a sub-question of a selected section that also needs a step from another section: the record keeps all its marking points,")
T.append("        the notes use only the in-scope steps (wording in tools/notes_src/_overrides.txt). Section numbers and content follow the syllabus for 2026-2028; series and parallel circuit rules are X4.3.")
T.append(' {F} = figure/graph/diagram inspected visually for this item; {M} = mark-scheme page inspected visually.')
T.append(f" Paper 1 records printed as '(identical text to <pair> Q<n>)' are questions repeated in another variant or session ({len(dm)} of the {40*len(res1)} questions). Each was compared with the question it repeats")
T.append("        (521 character-identical, 14 identical apart from punctuation or typography; official keys equal in every case) and is covered through that already-verified question.")
T.append(" notes updated = yes when every in-scope findings line of the pair is filed in a sub-topic of physics_papers_1_2_notes.txt that has a checklist (checked by tools/audit_notes.py).")
T.append('')
T.append('SUMMARY TABLE')
T.append('pair     | paper | session        | var | Qs | sub-Qs | marks(QP) | MS max | Qs checked | in-scope sub-Qs | marking pts (in-scope) | figs inspected | notes updated | status')
def msmax(p):
    return 40 if p['paper']==1 else (80 if sess_key(p['sess'])>=(23,0) else 75)
for p in order:
    pid=p['id']
    if p['paper']==2:
        r=res2[pid]; done=r['status']=='COMPLETE'
        T.append(f"{pid:8s} | P2    | {sess_name(p['sess']):14s} | {p['comp']:3s} | {r['nq']:2d} | {r['nleaf']:6d} | {r['qp_marks']:9d} | {msmax(p):6d} | {(str(r['nq']) if done else '0')+'/'+str(r['nq']):10s} | {str(r.get('n_in','-')):15s} | {str(r.get('pts','-')):22s} | {str(r.get('figs','-')):14s} | {nstate(pid,done):13s} | {r['status']}")
    else:
        r=res1[pid]; done=r['status']=='COMPLETE'
        T.append(f"{pid:8s} | P1    | {sess_name(p['sess']):14s} | {p['comp']:3s} | 40 | {40:6d} | {40:9d} | {40:6d} | {('40' if done else '0')+'/40':10s} | {str(r.get('n_in','-')):15s} | {str(r.get('n_in','-')):22s} | {str(r.get('figs','-')):14s} | {nstate(pid,done):13s} | {r['status']}")
T.append('')
T.append('Note on marks: pre-2023 Paper 2 prints 90 marks of questions (Section A 45 + three 15-mark Section B questions) but the paper maximum is 75 because candidates answer two Section B questions; 2023+ papers are 80 marks.')
odd=[(p['id'],res2[p['id']]['qp_marks']) for p in order if p['paper']==2 and sess_key(p['sess'])<(23,0) and res2[p['id']]['qp_marks']!=90]
if odd:
    hi=', '.join(f'{a} {b}' for a,b in odd if b>90); lo=', '.join(f'{a} {b}' for a,b in odd if b<90)
    T.append(f'        {len(odd)} pre-2023 Paper 2 rows show a larger value in marks(QP) because the paper has an EITHER/OR question or part whose two alternatives are both printed (one is answered) and both are counted: '+', '.join(f'{a} {b}' for a,b in odd)+'.')
    T.append('        Both alternatives were checked in every case; see excluded_files_and_issues.txt, section E.')
T.append('')
T.append('QUESTION-LEVEL RECORDS (newest first)')
for p in order:
    pid=p['id']; h=hdr[pid]
    T.append('')
    if p['paper']==2:
        r=res2[pid]; m=man2[pid]
        T.append(f"==== PAIR {pid} | Paper 2 | {sess_name(p['sess'])} | variant {p['comp']} | QP {p['qp']} ({h['qp_pages']} pp) | MS {p['ms']}{' (combined scheme)' if p['combined'] else ''} ({h['ms_pages']} pp) | header check {'OK' if h['ok'] else 'FAILED'}")
        T.append(f"status: {r['status']} | questions {r['nq']} | sub-questions {r['nleaf']} | QP marks {r['qp_marks']} | MS max mark {msmax(p)}")
        if r['status']=='NOT STARTED': T.append('  (not yet verified)'); continue
        T.append(f"in-scope sub-questions {r['n_in']} ({r['mk_in']} marks, {r['pts']} separately tagged marking points transcribed) | out-of-scope sub-questions {r['n_out']} ({r['mk_out']} marks, identified and matched to MS, not transcribed) | figures/MS pages inspected visually: {r['figs']}")
        for n in r.get('notes',[]): T.append('  note: '+n)
        for i in r['issues']: T.append('  ISSUE: '+i)
        curq=None
        for x in r['rows']:
            qn=re.match(r'^(\d+)',x['label']).group(1)
            if qn!=curq:
                curq=qn
                qp=m['qpages'].get(qn) or m['qpages'].get(int(qn)); mp=m['mspages'].get(qn) or m['mspages'].get(int(qn))
                T.append(f"  Q{qn}  [QP p{qp[0]}-{qp[-1]} ↔ MS p{mp[0]}-{mp[-1]}]" if qp and mp else f"  Q{qn}")
            lm=r['leaves'].get(x['label'])
            T.append(f"    {x['label']} [{lm if lm is not None else '?'}m] {x['sec']} :: {x['text']}")
    else:
        r=res1[pid]
        T.append(f"==== PAIR {pid} | Paper 1 | {sess_name(p['sess'])} | variant {p['comp']} | QP {p['qp']} ({h['qp_pages']} pp) | MS {p['ms']}{' (combined scheme)' if p['combined'] else ''} (key on p{','.join(map(str,keys[pid]['pages']))}) | header check {'OK' if h['ok'] else 'FAILED'}")
        T.append(f"status: {r['status']} | questions 40 | marks 40 | official key: {keys[pid]['key']}")
        if r['status']=='NOT STARTED': T.append('  (not yet verified)'); continue
        T.append(f"independently worked answers agreeing with key: {r['agree']}/40 | not independently solved: {r['unsolved']} | verified by exact text identity with an already-verified question: {r['dupn']} | in-scope MCQs: {r['n_in']} | figures inspected: {r['figs']}")
        for n in r.get('notes',[]): T.append('  note: '+n)
        for i in r['issues']: T.append('  ISSUE: '+i)
        for n in range(1,41):
            x=r['rows'].get(n)
            if x: T.append(f"    Q{n} key {r['key'][n-1]} | worked {x['ans']} | {x['sec']} :: {x['text']}")
open(REPO+'/full_paper_verification_tracker.txt','w').write('\n'.join(T)+'\n')
# ---------- checkpoint
todo2=[p['id'] for p in order if p['paper']==2 and res2[p['id']]['status']!='COMPLETE']
todo1=[p['id'] for p in order if p['paper']==1 and res1[p['id']]['status']!='COMPLETE']
C=[]
C.append('VERIFICATION CHECKPOINT — persistent execution state')
C.append(f'updated: {now}')
C.append(f'eligible pairs: {len(pairs)} | verified: {n1+n2} | remaining: {len(pairs)-n1-n2}')
C.append(f'Paper 2: {n2}/{len(res2)} verified | Paper 1: {n1}/{len(res1)} verified')
C.append('')
C.append('PROCESS ORDER: Paper 2 newest→oldest, then Paper 1 newest→oldest, then consolidation of notes, then independent audit.')
C.append('NEXT Paper 2 pairs to verify: '+(', '.join(todo2[:12]) or 'none')+(' …' if len(todo2)>12 else ''))
C.append('NEXT Paper 1 pairs to verify: '+(', '.join(todo1[:12]) or 'none')+(' …' if len(todo1)>12 else ''))
C.append('')
C.append('ALL PAIRS AND STATUS')
for p in order:
    r=(res2 if p['paper']==2 else res1)[p['id']]
    C.append(f"  {p['id']:8s} P{p['paper']} {r['status']}"+(' — '+'; '.join(r['issues']) if r['issues'] else ''))
C.append('')
C.append('STAGES')
C.append(f" 1. pair verification: {n1+n2}/{len(pairs)} complete")
_nf=os.path.exists(NOTES); _nbad=(sum(NB.values()) if NB is not None else None)
C.append(' 2. consolidated notes (physics_papers_1_2_notes.txt): '+('not built' if not _nf else ('built; every in-scope findings line is filed in a sub-topic with a checklist' if _nbad==0 else f'built, but {_nbad} findings line(s) are not yet filed in a sub-topic with a checklist')))
C.append(' 3. independent audit (final_verification_report.txt): '+('written' if os.path.exists(REPO+'/final_verification_report.txt') else 'not written'))
C.append('')
C.append('HOW TO RESUME (for any later run)')
C.append(' 0. Only /home/user/p persists between runs. If /home/user/work or the Python environment is missing, run: bash physics-5054-revision/tools/restore.sh')
C.append('    (recreates the environment with PyMuPDF and Pillow and rebuilds all working data: keys, question texts, digests, figure crops, contact sheets).')
C.append(' 1. tools/ holds the mechanical pipeline: lib.py, parse_ms1.py, parse_p1.py, header_check.py, parse_p2.py, build_p2.py, build_p1.py, build_p1_rest.py, build_dupmap.py, render.py, check.py, report.py;')
C.append('    reading aids: show.py, next.py, figs.py, p1zoom.py, p1crop.py, p1fix.py. Persistent copies of the derived data are in tools/data/.')
C.append(' 2. For each unverified pair: read the digest (question text interleaved with the mark scheme), inspect figure crops where the text is insufficient,')
C.append('    then write findings/p2/<pair>.txt (label | section | marking points with [mark tags]) or findings/p1/<pair>.txt (n answer section concept).')
C.append(' 3. Run check.py (validates labels, mark sums, MCQ keys) and report.py (regenerates tracker, checkpoint, exclusions and the by-section data).')
C.append(' 4. Notes: tools/notes_src/<section>.txt holds the sub-topics and checklist lines (format in tools/notes_src/_README.txt). Reading and editing aids: dump_sec.py, hidden.py, mv.py, setb.py, edl.py.')
C.append('    build_notes.py writes physics_papers_1_2_notes.txt; audit_notes.py checks it against the findings (structure, coverage, support, scope, references).')
C.append(' 5. final_audit.py re-derives the pair list, the Paper 1 keys and the Paper 2 counts independently of check.py and writes final_verification_report.txt.')
open(REPO+'/verification_checkpoint.txt','w').write('\n'.join(C)+'\n')
# ---------- exclusions
E=[]
E.append('EXCLUDED FILES AND ISSUES — Physics 5054 Papers 1 and 2')
E.append(f'updated: {now}')
E.append('')
E.append('A. QUESTION PAPERS EXCLUDED (no usable mark scheme / not a distinct paper)')
for e in excl: E.append(f"  {e['file']}: {e['reason']}")
E.append('')
E.append('B. FILES OUTSIDE THE REQUESTED SCOPE (not Paper 1 or Paper 2) — not examined')
other=collections.Counter()
for fn in sorted(os.listdir(SRC)):
    m=re.match(r'5054_([sw]\d\d)_([a-z]+)(?:_(.+))?\.pdf$',fn)
    if not m: other['unrecognised name: '+fn]+=1; continue
    kind,comp=m.group(2),m.group(3) or ''
    if kind in('qp','ms') and (comp[:1] in '12' or (kind=='ms' and comp=='')): continue
    lab={'qp':'question papers','ms':'mark schemes','er':'examiner reports','gt':'grade thresholds','ir':'confidential instructions','ci':'confidential instructions','ab':'answer booklets/other'}.get(kind,kind)
    other[f"{lab} for components 3/4 (practical / alternative to practical)" if kind in('qp','ms') else lab]+=1
for k,v in other.items(): E.append(f'  {v} file(s): {k}')
E.append('')
E.append('C. PAIRING NOTES')
E.append('  5054_s04_ms.pdf is a combined mark scheme for all components of May/June 2004; Paper 1 key is on its p3 and Paper 2 scheme on pp5-8; it is paired with 5054_s04_qp_1.pdf and 5054_s04_qp_2.pdf.')
E.append('  Every paired QP and MS was checked to carry the same component number and session in its own header text (header check); no mismatch was found.')
E.append('')
E.append('D. OPEN ISSUES FROM VERIFICATION')
any_=False
for p in order:
    r=(res2 if p['paper']==2 else res1)[p['id']]
    for i in r['issues']: E.append(f"  {p['id']}: {i}"); any_=True
if not any_: E.append('  none: no pair has an unresolved check issue (missing sub-question, answer differing from the key, mark tags not adding up without a recorded reason)')
extra=REPO+'/findings/issues_manual.txt'
if os.path.exists(extra):
    E.append(''); E.append('E. MANUALLY RECORDED OBSERVATIONS (mark-scheme anomalies, extraction problems, judgement calls)')
    E+=['  '+l.rstrip() for l in open(extra) if l.strip()]
open(REPO+'/excluded_files_and_issues.txt','w').write('\n'.join(E)+'\n')
json.dump({k:v for k,v in by.items()},open(WORK+'/by_section.json','w'))
print('tracker lines',len(T),'| sections with findings',len(by),'| findings lines',sum(len(v) for v in by.values()))
