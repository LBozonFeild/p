#!/usr/bin/env python3
"""final_audit.py [spot [step [offset]]] — final audit; writes final_verification_report.txt.
It does not import check.py, lib.py or any parser of the pipeline. It reads the PDF files directly (PyMuPDF), the findings
files, the tracker text and the notes, and tests the pipeline's stored data against them:
 1 pair list rebuilt from the file names, compared with the tracker and with the exclusions file
 2 Paper 1 answer keys re-read from the mark-scheme PDFs by word geometry (number token + nearest letter token on the same
   line; the pipeline used a text-row regex) and compared with the answer letter of every findings line and, for repeated
   questions (tools/data/p1_dupmap.json), with the key and worked answer of the question repeated
 3 Paper 2: every '[n]' mark allocation printed in the raw text of every question paper is listed in page order and must
   fall exactly into the leaf sub-questions of tools/data/p2_manifest.json (the thing under test), each leaf adding up to
   its marks; the findings file must hold one line per leaf in the same order (extra lines only where a '!marks' line
   splits an EITHER/OR leaf without changing the paper total); the totals are compared with the tracker rows
 4 tracker summary rows re-read (status, notes column) and totals recomputed from the findings files
 5 notes audit (tools/audit_notes.py) run and its summary included
 6 spot-checks recorded in tools/data/spot_checks.txt included
'spot' prints a sample of Paper 2 notes lines with the findings line and the mark-scheme text they rest on, for reading
(it needs the digests in /home/user/work; run restore.sh first if they are missing)."""
import fitz, os, re, json, sys, collections, datetime, subprocess
SRC='/home/user/p/physics-5054'; REPO='/home/user/p/physics-5054-revision'; WORK='/home/user/work'
R=[];problems=[]
def P(s=''): R.append(s)
# ---------- 1 pairs from file names
rx=re.compile(r'^5054_([sw])(\d\d)_(qp|ms)(?:_(\d+))?\.pdf$')
files=sorted(f for f in os.listdir(SRC) if f.lower().endswith('.pdf'))
qp={};ms={};odd=[]
for f in files:
    m=rx.match(f)
    if not m:
        if re.match(r'^5054_[sw]\d\d_qp_[12]',f): odd.append(f)
        continue
    (qp if m.group(3)=='qp' else ms)[(m.group(1)+m.group(2),m.group(4))]=f
pairs={};nomatch=[]
for (sess,comp),f in sorted(qp.items()):
    if comp is None or comp[0] not in '12': continue
    if (sess,comp) in ms: pairs[f'{sess}_{comp}']=(f,ms[(sess,comp)])
    elif (sess,None) in ms: pairs[f'{sess}_{comp}']=(f,ms[(sess,None)])
    else: nomatch.append(f)
trk=open(REPO+'/full_paper_verification_tracker.txt',encoding='utf-8').read().split('\n')
tpairs={}
for ln in trk:
    m=re.match(r'^==== PAIR (\S+) \| Paper (\d) \| .*? \| QP (\S+) .*? \| MS (\S+)',ln)
    if m: tpairs[m.group(1)]=(m.group(3),m.group(4))
exf=open(REPO+'/excluded_files_and_issues.txt',encoding='utf-8').read()
secA=exf.split('A. QUESTION PAPERS EXCLUDED')[1].split('\nB. ')[0]
exlisted=set(re.findall(r'^\s+(5054_\S+\.pdf):',secA,re.M))
P('1. PAIR LIST REBUILT FROM THE FILE NAMES')
P(f'   PDF files in physics-5054/: {len(files)}')
n1=sum(1 for k in pairs if k.split("_")[1][0]=="1"); n2=len(pairs)-n1
P(f'   Paper 1 and Paper 2 question papers with a mark scheme of the same session and component: {len(pairs)} (Paper 1: {n1}, Paper 2: {n2})')
P(f'   pairs recorded in the tracker: {len(tpairs)} | same pair ids and same file names: {"yes" if tpairs==pairs else "NO"}')
if tpairs!=pairs: problems.append('pair list differs from tracker')
exmine=set(nomatch)|set(odd)
P(f'   Paper 1/2 question papers without a mark scheme: {len(nomatch)} | non-standard duplicate copies: {len(odd)} | total excluded: {len(exmine)}')
P(f'   exclusions listed in excluded_files_and_issues.txt (section A): {len(exlisted)} | identical lists: {"yes" if exlisted==exmine else "NO"}')
used=set(q for q,m in pairs.values())|set(m for q,m in pairs.values())
other=[f for f in files if f not in used and f not in exmine]
secB=exf.split('B. FILES OUTSIDE THE REQUESTED SCOPE')[1].split('\nC. ')[0]
nB=sum(int(x) for x in re.findall(r'^\s+(\d+) file\(s\)',secB,re.M))
P(f'   every file accounted for: {len(used)} in pairs ({len(set(q for q,m in pairs.values()))} question papers + {len(set(m for q,m in pairs.values()))} mark-scheme files; the combined May/June 2004 scheme serves two pairs) + {len(exmine)} excluded + {len(other)} not Paper 1 or Paper 2 = {len(used)+len(exmine)+len(other)} of {len(files)}')
P(f'   files outside the requested scope listed in section B of the exclusions file: {nB} | same number: {"yes" if nB==len(other) else "NO"}')
if nB!=len(other) or len(used)+len(exmine)+len(other)!=len(files): problems.append('file accounting')
stray=[f for f in other if re.search(r'_(qp|ms)_[12]\d?[.-]',f) or re.fullmatch(r'5054_[sw]\d\d_(qp|ms)\.pdf',f)]
P(f'   Paper 1 or Paper 2 question papers or mark schemes left in neither list: {len(stray)}'+(f' {stray}' if stray else ''))
if exlisted!=exmine: problems.append('exclusion list differs')
# ---------- 2 Paper 1 keys by geometry
def keys_geom(path):
    doc=fitz.open(path); best={}
    for page in doc:
        words=page.get_text('words')
        nums=[w for w in words if re.fullmatch(r'\d{1,2}',w[4]) and 1<=int(w[4])<=40]
        lets=[w for w in words if w[4] in ('A','B','C','D')]
        found={}
        for n in nums:
            yc=(n[1]+n[3])/2
            cand=[l for l in lets if abs((l[1]+l[3])/2-yc)<5 and l[0]>=n[2]-1]
            if not cand: continue
            l=min(cand,key=lambda l:l[0]-n[2])
            between=[x for x in nums if x is not n and abs((x[1]+x[3])/2-yc)<5 and n[2]<=x[0]<l[0]]
            if between: continue
            d=l[0]-n[2]
            k=int(n[4])
            if k not in found or d<found[k][0]: found[k]=(d,l[4])
        if len(found)>=10:
            for k,(d,x) in found.items():
                if k not in best or d<best[k][0]: best[k]=(d,x)
    return ''.join(best[i][1] if i in best else '?' for i in range(1,41))
P('')
P('2. PAPER 1: ANSWER KEYS RE-READ FROM THE MARK-SCHEME PDFs (independent method) AND COMPARED WITH THE FINDINGS')
dm=json.load(open(REPO+'/tools/data/p1_dupmap.json'))
stored=json.load(open(REPO+'/tools/data/keys_p1.json'))
K={};bad_keys=[]
for pid,(q,m) in sorted(pairs.items()):
    if pid.split('_')[1][0]!='1': continue
    K[pid]=keys_geom(os.path.join(SRC,m))
    if '?' in K[pid]: bad_keys.append(pid)
P(f'   mark schemes read: {len(K)} | keys read: {sum(40-k.count("?") for k in K.values())} of {40*len(K)} | mark schemes with a key not found by this method: {len(bad_keys)} {bad_keys if bad_keys else ""}')
diff=[pid for pid in K if stored.get(pid,{}).get('key')!=K[pid]]
P(f'   agreement with the keys used during verification (tools/data/keys_p1.json): {len(K)-len(diff)} of {len(K)} papers identical'+(f' | differing: {diff}' if diff else ''))
if bad_keys or diff: problems.append('Paper 1 key re-read differs')
F1={};nline=0;mism=[];noline=[];both=[]
for pid in K:
    F1[pid]={}
    for ln in open(f'{REPO}/findings/p1/{pid}.txt',encoding='utf-8'):
        m=re.match(r'^(\d{1,2})\s+([ABCD?])\s+(\S+)',ln)
        if m: F1[pid][int(m.group(1))]=(m.group(2),m.group(3))
for pid in K:
    for n in range(1,41):
        k=K[pid][n-1]; d=dm.get(f'{pid}#{n}')
        if n in F1[pid]:
            nline+=1
            if d: both.append(f'{pid} Q{n}')
            if F1[pid][n][0]!=k: mism.append(f'{pid} Q{n}: worked {F1[pid][n][0]}, key {k}')
        elif d:
            tp,tn=d
            if tn not in F1.get(tp,{}): noline.append(f'{pid} Q{n} -> {tp} Q{tn} has no findings line')
            elif K[tp][tn-1]!=k or F1[tp][tn][0]!=k: mism.append(f'{pid} Q{n} (repeat of {tp} Q{tn}): key {k}, other key {K[tp][tn-1]}, worked {F1[tp][tn][0]}')
        else: noline.append(f'{pid} Q{n}: no findings line and not a recorded repeat')
P(f'   questions: {40*len(K)} | worked directly (findings line): {nline} | covered as a recorded repeat of a worked question: {len(dm)} | neither: {len(noline)} | both: {len(both)}')
P(f'   worked answer equal to the re-read official key: {nline-sum(1 for x in mism if "repeat" not in x)} of {nline} | repeats whose key equals the key and worked answer of the question repeated: {len(dm)-sum(1 for x in mism if "repeat" in x)} of {len(dm)}')
insc=sum(1 for pid in F1 for n,(a,s) in F1[pid].items() if any(not q.startswith('X') for q in s.split('+')))
P(f'   findings lines with an in-scope section code: {insc}')
for x in mism+noline+both: P('   PROBLEM '+x)
if mism or noline or both: problems.append('Paper 1 answer check')
# ---------- 3 Paper 2 re-count
P('')
P('3. PAPER 2: MARK ALLOCATIONS RE-COUNTED FROM THE QUESTION-PAPER TEXT AND COMPARED WITH THE FINDINGS AND THE TRACKER')
tsum={}
for ln in trk:
    f=[x.strip() for x in ln.split('|')]
    if len(f)==14 and f[1] in ('P1','P2') and f[0]!='pair': tsum[f[0]]=f
MAN=json.load(open(REPO+'/tools/data/p2_manifest.json'))
tot_alloc=tot_leaf=tot_in=tot_pts=tot_tags=tot_out=0;part_bad=[];lab_bad=[];dif_marks=[];multi=0;split=[];tag_ok=tag_n=0;tag_dif=[];eo=[]
for pid,(q,m) in sorted(pairs.items()):
    if pid.split('_')[1][0]!='2': continue
    doc=fitz.open(os.path.join(SRC,q)); txt='\n'.join(p.get_text() for p in doc)
    allocs=[int(x) for x in re.findall(r'\[\s*(\d{1,2})\s*\]',txt)]
    if re.search(r'\bEITHER\b',txt) and re.search(r'\bOR\b',txt): eo.append(pid)
    leaves=[];inl=0;pts=0;tags=0;over={};rows=[]
    for ln in open(f'{REPO}/findings/p2/{pid}.txt',encoding='utf-8'):
        ln=ln.rstrip('\n')
        if ln.startswith('!marks'):
            for a_,b_ in re.findall(r'(\S+)=(\d+)',ln): over[a_]=int(b_)
        if not ln.strip() or ln.startswith('#') or ln.startswith('!'): continue
        f=ln.split(' | ',2)
        if len(f)<3: continue
        lab=f[0].strip(); leaves.append(lab)
        ins=any(not s_.startswith('X') for s_ in f[1].strip().split('+'))
        tv=[int(x) for x in re.findall(r'\[[BCMA]?(\d)\]',f[2])]
        rows.append((lab,ins,sum(tv),'{~}' in f[2]))
        if ins: inl+=1; pts+=len([x for x in f[2].split(' ;; ') if x.strip()]); tags+=len(tv)
    t=tsum[pid]
    tot_alloc+=len(allocs); tot_leaf+=len(leaves); tot_in+=inl; tot_out+=len(leaves)-inl; tot_pts+=pts; tot_tags+=tags
    # every printed allocation must fall, in page order, into exactly one leaf of the manifest
    i=0;ok=True;mk={}
    for lab,k in MAN[pid]['leaves']:
        s_=0;n=0
        while i<len(allocs) and s_<k: s_+=allocs[i]; i+=1; n+=1
        if s_!=k: ok=False; break
        if n>1: multi+=1
        mk[lab]=k
    if not ok or i!=len(allocs): part_bad.append(pid)
    # findings lines = manifest leaves, in order; extra lines only through '!marks', which must keep the paper total
    man=[l for l,_ in MAN[pid]['leaves']]; extra=[l for l in leaves if l not in mk]
    mk2=dict(mk); mk2.update(over)
    if [l for l in leaves if l in mk]!=man or any(l not in over for l in extra) or sum(mk2.get(l,0) for l in leaves)!=sum(mk.values()): lab_bad.append(pid)
    elif extra: split.append(f'{pid} ({len(extra)} extra lines: {", ".join(extra)})')
    if sum(allocs)!=int(t[6]): dif_marks.append(f'{pid}: allocations in the QP text sum to {sum(allocs)}, tracker marks(QP) {t[6]}')
    if int(t[5])!=len(leaves) or int(t[9])!=inl or int(t[10])!=tags: problems.append(f'{pid}: tracker row differs from findings file (sub-Qs {t[5]}/{len(leaves)}, in-scope {t[9]}/{inl}, mark tags {t[10]}/{tags})')
    # in-scope lines: the values of the mark tags must add up to the marks printed for the leaf
    for lab,ins,tv,approx in rows:
        if not ins: continue
        tag_n+=1
        if tv==mk2.get(lab): tag_ok+=1
        else: tag_dif.append((pid,lab,tv,mk2.get(lab),approx))
P(f'   Paper 2 question papers read: {n2} | "[n]" mark allocations printed in them: {tot_alloc} | findings lines (leaf sub-questions): {tot_leaf}')
P(f'   papers in which the printed allocations, taken in page order, fall exactly into the leaf sub-questions and add up to each leaf\'s marks: {n2-len(part_bad)} of {n2}'+(f' | not: {part_bad}' if part_bad else ''))
P(f'   (a leaf holds more than one printed allocation in {multi} cases: numbered sub-parts 1. and 2., two answer lines, or the merged parts of an EITHER/OR question)')
P(f'   papers in which the findings file has one line for every leaf, in the same order: {n2-len(lab_bad)} of {n2}'+(f' | not: {lab_bad}' if lab_bad else ''))
for x in split: P(f'      EITHER/OR leaf split into its own lines by a "!marks" line, paper total unchanged: {x}')
P(f'   papers where the sum of the printed allocations equals marks(QP) in the tracker: {n2-len(dif_marks)} of {n2}')
for x in dif_marks: P('   difference '+x+' — NOT EXPLAINED')
if dif_marks: problems.append(f'{len(dif_marks)} unexplained Paper 2 mark difference(s)')
if part_bad or lab_bad: problems.append('Paper 2 leaf re-count')
big=[p_ for p_ in eo if int(tsum[p_][6])>90]; same=[p_ for p_ in eo if int(tsum[p_][6])<=90]
P(f'   papers whose text prints an EITHER / OR choice: {len(eo)} | each alternative has its own allocations and both are counted in marks(QP): {len(big)} ('+', '.join(f'{p_} {tsum[p_][6]}' for p_ in big)+')'+(f' | the two alternatives share one allocation: {len(same)} ('+', '.join(f'{p_} {tsum[p_][6]}' for p_ in same)+')' if same else ''))
odd90=[p_ for p_ in tsum if tsum[p_][1]=='P2' and int(tsum[p_][6]) not in (80,90) and p_ not in eo]
P(f'   Paper 2 rows with marks(QP) other than 90 (to 2022) or 80 (from 2023) that are not EITHER/OR papers: {len(odd90)}'+(f' {odd90}' if odd90 else ''))
if odd90: problems.append('Paper 2 marks total unexplained')
P(f'   in-scope sub-questions: {tot_in} | outside the selected sections: {tot_out} | mark tags written for the in-scope ones: {tot_tags} | tracker rows agree with these counts for every paper: {"yes" if not any("tracker row differs" in x for x in problems) else "NO"}')
flagged=[x for x in tag_dif if x[4]]; unfl=[x for x in tag_dif if not x[4]]
P(f'   in-scope sub-questions whose mark tags add up to the marks printed for the leaf: {tag_ok} of {tag_n} | differing and marked "{{~}}" with the reason in the findings line: {len(flagged)} | differing without a reason: {len(unfl)}')
for pid,lab,tv,k,ap in tag_dif: P(f'      {pid} {lab}: tags {tv}, printed {k}'+(' (reason recorded)' if ap else ' — NO REASON RECORDED'))
if unfl: problems.append(f'{len(unfl)} in-scope leaf/leaves with mark tags not adding up')
# ---------- 4 tracker rows
P('')
P('4. TRACKER SUMMARY ROWS')
st=collections.Counter(f[13] for f in tsum.values()); nt=collections.Counter(f[12] for f in tsum.values())
P(f'   rows: {len(tsum)} | status: {dict(st)} | notes updated: {dict(nt)}')
if len(tsum)!=len(pairs) or set(st)!={'COMPLETE'} or set(nt)!={'yes'}: problems.append('tracker rows not all COMPLETE / notes yes')
p1in=sum(int(f[9]) for f in tsum.values() if f[1]=='P1')
P(f'   in-scope Paper 1 questions in the tracker rows (repeats counted in each paper): {p1in} | in-scope Paper 1 findings lines (each repeated question once): {insc}')
man=[l for l in open(REPO+'/findings/issues_manual.txt',encoding='utf-8') if l.strip()]
P(f'   manually recorded observations (excluded_files_and_issues.txt, section E): {len(man)}')
secD=exf.split('D. OPEN ISSUES FROM VERIFICATION')[1].split('\nE. ')[0].strip()
P(f'   open issues recorded by the checks (section D): {secD}')
# ---------- 5 notes audit
P('')
P('5. NOTES AUDIT (tools/audit_notes.py)')
a=subprocess.run([sys.executable,os.path.join(REPO,'tools','audit_notes.py')],capture_output=True,text=True,cwd=os.path.join(REPO,'tools'))
for ln in a.stdout.strip().split('\n'): P('   '+ln)
if a.returncode!=0 or 'A structure problems: 0' not in a.stdout or 'still to be read by hand: 0' not in a.stdout: problems.append('notes audit not clean')
notes=open(REPO+'/physics_papers_1_2_notes.txt',encoding='utf-8').read()
ntick=sum(1 for l in notes.split(chr(10)) if l.startswith('  - '))
P(f'   notes file: {notes.count(chr(10))} lines, {len(notes)} characters, {ntick} checklist lines (lines that start with "  - ")')
def _num(rx,default='?'):
    m_=re.search(rx,a.stdout); return m_.group(1) if m_ else default
A_else=_num(r'sister sections\): (\d+)'); A_spread=_num(r'several lines of the section: (\d+)'); A_okB=_num(r'listed in _audit_ok.txt\): (\d+)')
A_okC=_num(r'section: accepted after reading (\d+)'); A_okN=_num(r'section findings: accepted after reading (\d+)')
A_p2=_num(r'checklist lines: Paper 2 (\d+)'); A_p1=_num(r'Paper 2 \d+, Paper 1 (\d+)'); A_pts=_num(r'MCQ lines checked: (\d+)'); A_fl=_num(r'findings lines: (\d+)')
# ---------- 6 spot checks
P('')
P('6. SPOT-CHECKS OF NOTES STATEMENTS AGAINST THE MARK-SCHEME TEXT')
sp=REPO+'/tools/data/spot_checks.txt'
if os.path.exists(sp):
    for ln in open(sp,encoding='utf-8'): P('   '+ln.rstrip())
else: P('   not recorded'); problems.append('spot-checks not recorded')
def ms_excerpt(pid,lab):
    import glob
    m=re.match(r'^(\d+)(E|O)?([a-h])?([ivx]+)?(\d)?$',lab)
    out=[]
    for fn in sorted(glob.glob(f'{WORK}/digest/p2/{pid}.*.txt')):
        L=open(fn,encoding='utf-8').read().split('\n')
        qn=m.group(1) if m else re.match(r'\d+',lab).group(0)
        st=[i for i,l in enumerate(L) if l.startswith(f'── MS Q{qn} ')]
        if not st: continue
        e=st[0]+1
        while e<len(L) and not L[e].startswith('━━') and not L[e].startswith('── MS Q'): e+=1
        blk=L[st[0]+1:e]
        if m and m.group(3):
            want=qn+f'({m.group(3)})'+(f'({m.group(4)})' if m.group(4) else '')
            idx=[i for i,l in enumerate(blk) if l.replace(' ','').startswith(want)]
            if idx:
                j=idx[0]+1
                while j<len(blk) and not re.match(r'^\d+\s?\(',blk[j]): j+=1
                return ' / '.join(x.strip() for x in blk[idx[0]:j])
        return ' / '.join(x.strip() for x in blk)[:1500]
    return '(digest not found)'
if __name__=='__main__' and len(sys.argv)>1 and sys.argv[1]=='spot':
    sys.path.insert(0,os.path.join(REPO,'tools'))
    from notes_lib import toks
    import build_notes
    step=int(sys.argv[2]) if len(sys.argv)>2 else 42; off=int(sys.argv[3]) if len(sys.argv)>3 else 20
    k=0
    for sec,title,rows in build_notes.sections():
        for b,p2,p1,items in rows:
            for l in p2:
                k+=1
                if k%step!=off%step: continue
                T=toks(l); best=None;bs=-1
                for it in items:
                    if it['p1']: continue
                    I=toks(it['text']); sc=len(T&I)/(len(T)**0.5*len(I)**0.5+1e-9)
                    if sc>bs: bs=sc;best=it
                print(f'#{k} [{sec} {b["id"]}] NOTE: {l[:420]}')
                if best: print(f'    FINDING {best["key"]}: {best["text"][:300]}'); print(f'    MS: {ms_excerpt(best["pid"],best["lab"])[:700]}')
                print()
if __name__=='__main__' and len(sys.argv)==1:
    now=datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    H=['FINAL VERIFICATION REPORT — Cambridge O Level Physics 5054, Papers 1 and 2',f'generated {now} by tools/final_audit.py (does not use tools/check.py or the pipeline parsers)','',
       'RESULT',
       f'   eligible question paper / mark scheme pairs: {len(pairs)} | verified: {st.get("COMPLETE",0)} | unverified: {len(pairs)-st.get("COMPLETE",0)}',
       f'   excluded files: {len(exmine)} | manually recorded observations: {len(man)} | problems found by this audit: {len(problems)}']
    H+=['   '+('no problem found' if not problems else 'PROBLEMS: '+'; '.join(problems)),'']
    rew=[]
    for pid in sorted(F1):
        for ln in open(f'{REPO}/findings/p1/{pid}.txt',encoding='utf-8'):
            m_=re.match(r'^(\d{1,2})\s+[ABCD]\s.*\[reworked',ln)
            if m_: rew.append(f'{pid} Q{m_.group(1)}')
    H+=['FILES',
        '   physics_papers_1_2_notes.txt          consolidated checklist notes (sections 1.1–1.7, 3.1–3.4, 4.2)',
        '   full_paper_verification_tracker.txt   one summary row and the question-level records for each of the pairs',
        '   verification_checkpoint.txt           state of the work and how to resume it',
        '   excluded_files_and_issues.txt         excluded files, pairing notes, open issues, manually recorded observations',
        '   final_verification_report.txt         this report',
        '   findings/                             the per-paper verification records (evidence); tools/ the scripts and their data','',
        'NOTES FOR THE READER',
        f'   Paper 1 answers reworked after a first-pass disagreement with the key (the key was right in every case; marked "[reworked" in the findings): {len(rew)} — '+', '.join(rew),
        '   No Paper 1 question was found to be discounted or to have a disputed key.',
        f'   The {len(man)} manual observations (on {len(set(l.split()[0] for l in man))} papers, all Paper 2) concern: EITHER/OR questions (10 papers); label slips and misprints in the published mark schemes; the 2026 scheme that prints "1" in its Marks column for every part; mark allocations printed for groups of sub-parts in the two 2004 papers; two question-specific allowances;',
        '   and three 2-mark sub-questions for which the published scheme prints a single marking point: s16_22 5(a)(ii) and 5(b)(i) (in the selected sections; the printed point is recorded as it stands, the second point is not published) and s16_21 7(a) (outside the selected sections).',
        '   None of them leaves a pair unverified.','']
    H+=['LIMITS AND JUDGEMENT CALLS (read these before relying on the figures)',
        '   1. "Verified" means: every question and sub-question of the paper was read against its mark-scheme entry by the reviewing agent (an AI model), with the figures viewed where the text was not enough,',
        '      and the mechanical checks of sections 1-4 pass. It is not a check by a teacher or an examiner.',
        '   2. Paper 1: a multiple-choice mark scheme gives only the answer letter. The Paper 1 points in the notes are explanations written for the notes, not official marking points;',
        '      what was checked is that every worked answer equals the official key (section 2).',
        f'   3. Notes audit (section 5): the notes are compared with the findings by word matching. Of the {A_pts} findings points, {int(A_else)+int(A_spread) if A_else.isdigit() and A_spread.isdigit() else "?"} ({A_else} + {A_spread}) fell below the threshold in their own sub-topic and were accepted',
        f'      because their words are found elsewhere in the same section family; these were not read one by one. {A_okB} points, {A_okC} checklist lines and {A_okN} number were read and accepted (tools/notes_src/_audit_ok.txt).',
        f'   4. Spot-checks against the mark-scheme text (section 6) cover 36 of the {A_p2} Paper 2 checklist lines.',
        '   5. Scope of the notes. The section numbers and their content are those of the syllabus for 2026-2028 (the syllabus text was read from published copies; it is not in the repository).',
        '      a. Series and parallel circuits (4.3.2) and the potential divider (4.3.3) are outside the selected sections. On 2026-11-12 the questions on resistance were re-classified:',
        '         steps that need those rules are left out of the notes, 4.2.4 keeps R = V/I for one component or for the whole circuit. 82 findings lines were re-coded for this and for b and c below',
        '         (list in tools/data/scope_recode_2026-11-12.py; notes wording of the mixed questions in tools/notes_src/_overrides.txt).',
        '      b. Nuclear fusion in the Sun is not in 1.7.3 of this syllabus (it is in chapters 5 and 6): seven Paper 1 questions were re-coded as nuclear physics and their two lines removed from the notes.',
        '      c. Diode: 4.2.4 names the current-voltage graph of a diode. No verified paper asks for a sketch of that graph. Three Paper 2 marking points on the action of a diode',
        '         (s16_22 8(d), s20_22 10(d)(i), s21_21 7(b)(iv)) are filed under 4.2.4; Paper 1 questions on diode symbols and diodes in circuits stay under 4.3.',
        '      d. The kilowatt-hour belongs to 4.4.1. It is kept under 1.7.5 only as a unit of energy used with E = Pt; the cost of electricity and P = IV are left out.',
        '      e. LDR, thermistor, lamp, heater and motor appear only as the component in a V = IR, Q = It or energy question; "potential divider" appears once, as an accepted way to vary the p.d. in the',
        '         resistance experiment; generator and transformer appear in the descriptions of power stations (1.7.3).',
        '      f. Content of earlier syllabuses that sits under a selected heading was kept; the main items are named in the header of the notes: vernier calipers, vector diagrams for vectors not at right angles (1.1),',
        '         ticker-tape timers (1.2), camera, projector and enlarger (3.2.3), induced charges, earthing, charging by induction and static electricity in practice (4.2.1). The notes were not compared line by line',
        '         with the syllabus list, so other points of older papers that the present syllabus no longer names may remain under the selected headings.',
        '   6. Marks: for papers before 2023 marks(QP) is 90 or more against a paper maximum of 75 because Section B offers a choice; EITHER/OR alternatives are both counted (see section 3).','']
    open(REPO+'/final_verification_report.txt','w',encoding='utf-8').write('\n'.join(H+R)+'\n')
    print('\n'.join(H+R))
