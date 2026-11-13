#!/usr/bin/env python3
"""bunpaired.py — the questions of the Paper 1 / Paper 2 question papers that have NO mark scheme in the repository
  -> ../data/bank_unpaired_questions.json   (durable; read by breports.py)

These papers are not in the bank (a question is never shown without its own official scheme and no scheme of another
paper is attached). So that the exclusions can be reconciled question by question, every question of these papers is
listed here with its source page(s) and its syllabus code(s):
  * a question whose text is identical to a question of a verified paper takes the code of that question
    (5054_s10_qp_13 and 5054_w10_qp_13 consist only of such questions; 5054_s10_qp_23 and 5054_w10_qp_23 repeat the
    variant-2 papers question for question — tested here, not assumed);
  * the other questions (Oct/Nov 2002, May/June 2003, Oct/Nov 2003) carry the code given to them by reading the
    question (../data/bank_unpaired_classification.json); where such a question is identical to a verified one the two
    codes are compared and a difference is reported."""
import sys, os, re, json, pickle, collections
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.dirname(HERE))
from lib import *
import parse_p1, parse_p2, notes_lib
ORDER={s:i for i,(s,_) in enumerate(notes_lib.SECS)}
DATA=os.path.join(os.path.dirname(HERE),'data')
def norm(t): return re.sub(r'\s+',' ',t).strip()
def first_in(sec):
    for s in sec.split('+'):
        if s in ORDER: return s
    return None
def main():
    S=pickle.load(open(WORK+'/state.pkl','rb')); res1,res2,pairs=S['res1'],S['res2'],S['pairs']
    C=json.load(open(DATA+'/bank_unpaired_classification.json'))
    files=[x['file'] for x in S['excl'] if 'no corresponding mark scheme' in x['reason']]
    # verified Paper 1 questions by text (the earliest paper wins, as in the verification)
    P1Q=json.load(open(WORK+'/p1_questions.json')); bytext={}
    for p in pairs:
        if p['paper']!=1: continue
        for q in P1Q[p['id']]: bytext.setdefault(norm(q['text']),(p['id'],q['n']))
    out=collections.OrderedDict(); problems=[]
    for fn in files:
        m=re.match(r'5054_([sw]\d\d)_qp_(\d+)\.pdf$',fn); sess=m.group(1); comp=m.group(2)
        paper=int(comp[0]); variant=int(comp[1]) if len(comp)==2 else 1
        path=os.path.join(SRC,fn); npages=len(fitz.open(path)); qs=[]
        if paper==1:
            for q in parse_p1.parse_qp1(path):
                idt=bytext.get(norm(q['text'])); hand=C['p1'].get(fn,{}).get(str(q['n']))
                inh=res1[idt[0]]['rows'][idt[1]]['sec'] if idt else None
                if hand is None and inh is None: problems.append((fn,q['n'],'no code')); continue
                raw=hand if hand is not None else inh
                if hand is not None and inh is not None and first_in(hand)!=first_in(inh): problems.append((fn,q['n'],f'hand code {hand} but identical verified question {idt} has {inh}'))
                f=first_in(raw)
                qs.append(dict(q=q['n'],pages=[q['page']],code=raw,secs=[f] if f else [],identical_to=list(idt) if idt else None,
                               basis='code read from the question text' if hand is not None else 'code of the identical verified question'))
            if len(qs)!=40: problems.append((fn,'questions parsed',len(qs)))
        else:
            mine=parse_p2.parse_qp2(path)[0]
            twin=C['identical_paper'].get(fn)
            if twin:
                tp=[p for p in pairs if p['id']==twin][0]; theirs=parse_p2.parse_qp2(os.path.join(SRC,tp['qp']))[0]
                same=len(mine)==len(theirs) and all(norm(a['text'])==norm(b['text']) and a['n']==b['n'] for a,b in zip(mine,theirs))
                if not same: problems.append((fn,'not identical to',twin))
            for q in mine:
                if twin:
                    secs=[]
                    for x in res2[twin]['rows']:
                        if int(re.match(r'^(\d+)',x['label']).group(1))==q['n']:
                            f=first_in(x['sec'])
                            if f and f not in secs: secs.append(f)
                    basis='codes of the identical question of the verified variant-2 paper'; idt=[twin,q['n']]
                else:
                    secs=C['p2'][fn][str(q['n'])]; basis='codes read from the question text'; idt=None
                secs=sorted(secs,key=lambda s:ORDER[s])
                qs.append(dict(q=q['n'],pages=sorted(set(q['pages'])),code='+'.join(secs) if secs else 'none of the selected subsections',secs=secs,identical_to=idt,basis=basis,marks=q.get('marks')))
            if len(qs)!=11: problems.append((fn,'questions parsed',len(qs)))
        out[fn]=dict(sess=sess,paper=paper,variant=variant,pages=npages,questions=qs)
    json.dump(dict(_note='Questions of the question papers without a mark scheme in the repository; written by bank/bunpaired.py. pages are 1-based source pages; secs = selected subsections of the question (empty = none).',files=out,problems=problems),
              open(DATA+'/bank_unpaired_questions.json','w'),indent=1)
    for fn,v in out.items():
        qs=v['questions']
        print(f"{fn:22s} questions {len(qs):3d} | on the selected sections {sum(1 for q in qs if q['secs']):3d} | question/subsection records {sum(len(q['secs']) for q in qs):3d} | identical to a verified question {sum(1 for q in qs if q['identical_to']):3d}")
    print('problems:',problems)
    return problems
if __name__=='__main__':
    sys.exit(1 if main() else 0)
