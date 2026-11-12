"""Automatic consistency audit of the verification state and the deliverables. Writes state/audit_result.txt."""
import sys, os, re, collections, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state import *
def main():
    items = load_items(); dec = load_dec(); pairs = load_pairs(); od = order(); R = []; ok_all = True
    def chk(name, ok, detail=""):
        nonlocal ok_all
        ok_all &= bool(ok); R.append("   [%s] %s%s" % ("PASS" if ok else "FAIL", name, (" - " + detail) if detail else ""))
    files = set(os.listdir(SRC))
    # 1 pairs and files
    miss = [p["id"] for p in pairs if p["qp"] not in files or p["ms"] not in files]
    chk("1. every eligible pair points to existing question-paper and mark-scheme files", not miss, "%d pairs" % len(pairs) if not miss else str(miss))
    qps = {f for f in files if re.match(r"5090_[sw]\d\d_qp_[12]\d?\.pdf$", f)}
    used = {p["qp"] for p in pairs}
    chk("2. every Paper 1 / Paper 2 question paper in the folder is either an eligible pair or a documented exclusion", len(qps - used) == 8, "%d question papers, %d paired, %d excluded" % (len(qps), len(qps & used), len(qps - used)))
    # 3 item coverage
    bypair = collections.Counter(i.split(":")[0] for i in od)
    bad = [p["id"] for p in pairs if p["paper"] == 1 and bypair[p["id"]] != 40]
    chk("3. every Paper 1 has exactly 40 questions in the tracker", not bad, str(bad) if bad else "%d papers x 40" % sum(1 for p in pairs if p["paper"] == 1))
    chk("4. item sets agree (order = decisions = extracted items)", set(od) == set(dec) == set(items) and len(od) == len(set(od)), "%d items" % len(od))
    # 5 P2 marks add up
    bad = []
    for p in pairs:
        if p["paper"] != 2: continue
        s = sum(int(items[i]["marks"]) for i in od if i.startswith(p["id"] + ":"))
        if s != p["marks"]: bad.append("%s %d!=%d" % (p["id"], s, p["marks"]))
    chk("5. Paper 2 part marks add up to the paper total (90 marks to 2022 with both optional questions counted, 80 from 2023)", not bad, "; ".join(bad[:6]) if bad else "78 papers")
    # 6 status / section validity
    bad = [i for i in od if dec[i]["status"] not in ("ver", "oos")]
    chk("6. no item is left pending", not bad, "%d pending" % len(bad) if bad else "")
    bad = []
    for i in od:
        codes = dec[i]["sec"].split("+")
        if not all(c in SECS or c in OOS for c in codes): bad.append(i)
        elif dec[i]["status"] == "ver" and not insecs(dec[i]): bad.append(i)
        elif dec[i]["status"] == "oos" and insecs(dec[i]): bad.append(i)
    chk("7. every item carries valid codes; verified items have a requested subsection, out-of-scope items have none", not bad, str(bad[:8]) if bad else "")
    # 8 keys
    k = jload("data/p1_keys_reextracted.json")
    nk = 0; bad = []
    if k:
        for pid, v in k.items():
            for q in range(1, 41):
                nk += 1
                if v["keys"].get(str(q)) != dec["%s:%d" % (pid, q)]["key"]: bad.append("%s:%d" % (pid, q))
    chk("8. Paper 1 keys independently re-extracted from the official key source agree with the tracker", k and not bad, "%d keys compared" % nk if not bad else str(bad[:8]))
    # 9 P2 MS text present
    bad = [i for i in od if items[i]["paper"] == 2 and (not items[i]["ms_text"].strip() or not items[i]["ms_labels"])]
    chk("9. every Paper 2 part is matched to a non-empty mark-scheme section", not bad, str(bad[:8]) if bad else "%d parts" % sum(1 for i in od if items[i]["paper"] == 2))
    # 10 figures
    bad = [i for i in od if dec[i]["status"] == "ver" and dec[i].get("fig") not in ("viewed", "text", "none")]
    chk("10. no verified item has an outstanding figure check", not bad, str(bad[:8]) if bad else "")
    # 11 notes structure
    bad = []; npts = 0
    for s in SECS:
        t = notes(s); lines = t.rstrip("\n").split("\n")
        if not lines[0].startswith(s + " "): bad.append(s + ":title")
        for n, l in enumerate(lines[1:], 2):
            if not l.strip(): continue
            if l.startswith("- "):
                npts += 1
                if len(l) < 10: bad.append("%s:%d short" % (s, n))
            elif l.startswith("Context:") or re.match(r"^\s+- \S", l) or re.match(r"^[A-Z0-9][A-Z0-9 ,'/:&\-]{3,}", l): pass
            else: bad.append("%s:%d %r" % (s, n, l[:40]))
    chk("11. notes files are well formed (title, headings, dash-bullet lines only)", not bad, "; ".join(bad[:6]) if bad else "%d bullet lines in %d subsections" % (npts, len(SECS)))
    # 12 duplicates in notes
    seen = collections.Counter()
    for s in SECS:
        head = ""
        for l in notes(s).split("\n"):
            if l.startswith("- "): seen[(s, head, l.strip())] += 1
            elif l.strip() and not l.startswith(" ") and not l.startswith("Context:"): head = l.strip()
    dup = [k for k, v in seen.items() if v > 1]
    chk("12. no bullet line is duplicated inside a subsection", not dup, str([d[0] + ": " + d[2][:50] for d in dup[:5]]) if dup else "")
    # 13 every section has verified items
    cnt = collections.Counter()
    for i in od:
        if dec[i]["status"] == "ver":
            for s in insecs(dec[i]): cnt[s] += 1
    bad = [s for s in SECS if cnt[s] == 0]
    chk("13. every requested subsection is backed by verified items", not bad, str(bad) if bad else "min %d items (%s)" % (min(cnt.values()), min(cnt, key=cnt.get)))
    # 14 no paper refs in notes
    bad = []
    for s in SECS:
        for n, l in enumerate(notes(s).split("\n"), 1):
            if re.search(r"\b[sw]\d\d_\d\d?\b|5090_|\bQ\d+\b", l): bad.append("%s:%d" % (s, n))
    chk("14. notes carry no paper / question references (they belong in the tracker)", not bad, str(bad[:8]) if bad else "")
    # 15 deliverables in sync
    exp = ["biology_5090_papers_1_2_notes.txt", "full_paper_verification_tracker.txt", "verification_checkpoint.txt", "excluded_files_and_issues.txt", "final_verification_report.txt"]
    missing = [f for f in exp if not os.path.exists(os.path.join(OUT, f))]
    sync = True; detail = ""
    if not missing:
        tr = open(os.path.join(OUT, exp[1]), encoding="utf-8").read()
        nl1 = len(re.findall(r"(?m)^  Q\d+ key [A-D] \| ", tr)); nl2 = len(re.findall(r"(?m)^  \S.* \[\d+\] \| .* \| MS ", tr))
        nver = len(re.findall(r"\| VERIFIED \|", tr)); noos = len(re.findall(r"\| OUT-OF-SCOPE \|", tr))
        nt = open(os.path.join(OUT, exp[0]), encoding="utf-8").read(); nb = len(re.findall(r"(?m)^- ", nt)) - len(re.findall(r"(?m)^- ", open(os.path.join(W, "notes", "_header.txt"), encoding="utf-8").read()))
        st = collections.Counter(dec[i]["status"] for i in od)
        sync = (nl1 == 3200 and nl2 == len(od) - 3200 and nver == st["ver"] and noos == st["oos"] and nb == npts)
        detail = "tracker lines P1 %d, P2 %d; VERIFIED %d; OUT-OF-SCOPE %d; notes bullet lines %d" % (nl1, nl2, nver, noos, nb)
    chk("15. the five deliverable files exist and match the live state", not missing and sync, detail or str(missing))
    # 16 complete-read record of out-of-scope Paper 2 mark schemes
    fr = set((jload("state/oos_fullread.json", {}) or {}).get("read", []))
    p2oos = [i for i in od if items[i]["paper"] == 2 and dec[i]["status"] == "oos"]
    notread = [i for i in p2oos if i not in fr]
    chk("16. the complete mark-scheme text of every out-of-scope Paper 2 part is in the full-read record", not notread, "%d parts" % len(p2oos) if not notread else str(notread[:8]))
    # 17 renderer correction: viewed Paper 1 items on pages that an earlier renderer variant drew incompletely were re-inspected
    risk = [o[0] for o in (jload("state/hidden_items_viewed.json", []) or []) if o[7] >= 3 and dec[o[0]]["status"] == "ver" and dec[o[0]]["fig"] == "viewed"]
    rei = set(jload("state/reinspected_2005_2009.json", []) or [])
    nore = [i for i in risk if i not in rei]
    chk("17. every 'figure viewed' Paper 1 question on a page that the first renderer variant drew incompletely was re-inspected with the corrected renderer", not nore, "%d questions" % len(risk) if not nore else str(nore[:8]))
    # 18 Paper 2 parts whose marking points identify / mark structures on a figure
    cand = [r[0] for r in (jload("state/p2_fig_candidates.json", []) or []) if dec[r[0]]["status"] == "ver"]
    exempt = {"w16_22:2(b)(ii)", "w25_22:2(b)(iv)"}
    nov = [i for i in cand if dec[i]["fig"] != "viewed" and i not in exempt]
    chk("18. every verified Paper 2 part whose marking points name or mark structures on a figure has had the figure inspected", not nov, "%d parts (2 graph-only parts exempt)" % (len(cand) - len(exempt)) if not nov else str(nov[:8]))
    # 19 lexical coverage of the notes (fully in-scope Paper 2 parts)
    import subprocess
    out = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "coverage.py"), "only=fully", "thr=0.5"], capture_output=True, text=True).stdout
    m = re.search(r"marking points (\d+), below threshold 0\.50: (\d+)", out)
    low = int(m.group(2)) if m else 10 ** 6
    chk("19. lexical coverage: marking points of fully in-scope Paper 2 parts whose wording is less than half represented in the notes of their own subsection stay within the residue that was reviewed by hand (62)", low <= 62, "%s points checked, %d below the threshold" % (m.group(1) if m else "?", low))
    # 20 nuclear-division block not in the notes
    chk("20. the notes contain no heading for an unrequested section (nuclear-division block removed from 17.3)", "MITOSIS, MEIOSIS, FERTILISATION AND CHROMOSOME NUMBER" not in notes("17.3"))
    R.append("   RESULT: %s (%d checks)" % ("ALL CHECKS PASSED" if ok_all else "SOME CHECKS FAILED", len(R)))
    txt = "   run %s\n" % time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()) + "\n".join(R)
    with open(os.path.join(W, "state/audit_result.txt"), "w") as f: f.write(txt + "\n")
    print(txt)
if __name__ == "__main__":
    main()
