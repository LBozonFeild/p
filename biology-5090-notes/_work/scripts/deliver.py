"""Regenerate the five deliverable files from the live state (decisions.json, items.json, notes/*.txt)."""
import sys, os, re, time, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state import *
NOW = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
FIG = {"viewed": "figure viewed", "text": "text sufficient / figure not rendered", "none": "no figure",
       "na": "n/a (out of scope)", "todo": "FIGURE NOT YET VIEWED"}
STAT = {"ver": "VERIFIED", "oos": "OUT-OF-SCOPE", "pend": "IN-SCOPE-PENDING"}
def rd(name):
    p = os.path.join(W, "text", name)
    return open(p, encoding="utf-8").read().rstrip("\n") if os.path.exists(p) else ""
def wr(name, txt):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f: f.write(txt.rstrip("\n") + "\n")
    print("wrote %-42s %8d bytes %6d lines" % (name, len(txt.encode("utf-8")), txt.count("\n") + 1))
def alt_count(ms):
    return sum(l.count("/") for l in ms.split("\n") if not l.startswith("<<MS"))
def main():
    items = load_items(); dec = load_dec(); pairs = load_pairs(); od = order()
    bypair = collections.defaultdict(list)
    for i in od: bypair[i.split(":")[0]].append(i)
    # ---------------------------------------------------------------- notes
    out = [open(os.path.join(W, "notes", "_header.txt"), encoding="utf-8").read().rstrip("\n"), ""]
    npts = {}; chap_seen = set()
    for s in SECS:
        c = s.split(".")[0]
        if c not in chap_seen:
            chap_seen.add(c); out += ["=" * 100, "%s. %s" % (c, CHAP[c]), "=" * 100, ""]
        t = notes(s).rstrip("\n"); npts[s] = len(re.findall(r"^- ", t, re.M))
        out += [t, ""]
    wr("biology_5090_papers_1_2_notes.txt", "\n".join(out))
    # ---------------------------------------------------------------- tracker
    T = ["FULL PAPER VERIFICATION TRACKER - Cambridge O Level Biology 5090, Papers 1 and 2",
         "Generated %s from the persistent verification state (biology-5090-notes/_work/state/decisions.json)." % NOW, "",
         "STATUS CODES (question level)",
         "VERIFIED          = question text and its official mark-scheme section (Paper 2) / answer key (Paper 1) were read by the verifier, the syllabus subsection was confirmed, and (Paper 1) the key was checked against the stem and options. Its in-scope marking points are in the notes subsection(s) shown.",
         "IN-SCOPE-PENDING  = classified into a requested subsection but NOT yet verified question-by-question.",
         "OUT-OF-SCOPE      = question read and classified by the verifier as belonging to a syllabus section that was not requested (code shows which); its marking points are deliberately NOT in the notes. Paper 1: stem, options and key were read (figures of out-of-scope questions were not rendered). Paper 2: stem and the start of the mark scheme were read at triage; afterwards the complete mark-scheme text of every out-of-scope part was first machine-scanned for the vocabulary of the requested sections and then read in full, and parts with creditable in-scope points were moved to a mixed code.",
         "Mixed code (e.g. o16+17.3) = the question belongs to an unrequested section, but its mark scheme (Paper 2) or its keyed answer (Paper 1) rests on a point that belongs to the requested subsection shown; only those points are in the notes. Remark \"moved in by full-MS audit\" marks Paper 2 parts re-classified when the complete mark-scheme text of every out-of-scope part was re-read; remark \"moved in on review ... learning objectives\" marks Paper 1 questions re-classified when the out-of-scope questions were re-checked against the 2026-2028 learning objectives. The rules used at the boundary are listed in excluded_files_and_issues.txt, section H.",
         "Out-of-scope codes: " + "; ".join("%s = %s" % kv for kv in OOS.items()),
         "Figure status: \"figure viewed\" = the diagram / graph / table was rendered from the PDF and inspected; \"FIGURE NOT YET VIEWED\" = answer depends on a figure that has not been inspected; \"text sufficient / figure not rendered\" = the extracted text (labels, tables, options, mark scheme) was sufficient to check the answer; \"no figure\" = the question has no figure.",
         "Marking points = number of separately credited points (\";\" separators) in the matched mark-scheme section(s); \"alt\" = number of \"/\" alternative separators in the same text; Paper 1 = 1 point per question. Mark schemes laid out as tables without \";\" show 0 pts - see the marks in square brackets.",
         "", "PART A - PAPER-LEVEL SUMMARY (%d eligible pairs)" % len(pairs), ""]
    tot = collections.Counter(); fully = 0; partA = []; perpair = {}
    for p in pairs:
        ids = bypair[p["id"]]; st = collections.Counter(dec[i]["status"] for i in ids)
        ver = [i for i in ids if dec[i]["status"] == "ver"]
        figv = sum(1 for i in ids if dec[i].get("fig") == "viewed")
        figo = sum(1 for i in ids if dec[i].get("fig") == "todo")
        if p["paper"] == 1:
            pts = len(ver); extra = ""
            msp = "pages %s" % p.get("ms_pages")
        else:
            pts = sum(items[i]["pts"] for i in ver)
            extra = " | accepted-alternative / guidance markers read: %d" % sum(alt_count(items[i]["ms_text"]) for i in ver)
            pg = sorted({x for i in ids for x in (items[i].get("ms_pages") or [])})
            msp = "pages %d-%d" % (pg[0], pg[-1]) if pg else "pages n/a"
        done = st["pend"] == 0 and figo == 0
        fully += done
        tot.update(st); tot["pts"] += pts; tot["marks"] += p["marks"]; tot["figv"] += figv; tot["figo"] += figo
        perpair[p["id"]] = (len(ids), st["ver"], st["oos"], st["pend"], pts, figv, figo, done)
        partA += ["%s | year %s | session %s | paper %d variant %s" % (p["id"], p["year"], p["session"], p["paper"], p["variant"]),
                  "   QP: %s | MS: %s (%s, %s)" % (p["qp"], p["ms"], p.get("ms_kind") or "mark scheme", msp),
                  "   questions: %d | sub-questions (mark-bearing parts): %d | marks available: %d" % (p["nq"], len(ids), p["marks"]),
                  "   checked: %d of %d (in scope and verified: %d; out of scope: %d; in scope still pending: %d)" % (st["ver"] + st["oos"], len(ids), st["ver"], st["oos"], st["pend"]),
                  "   marking points accounted for (verified in-scope items): %d of %d in-scope%s" % (pts, pts, extra),
                  "   figures inspected: %d item(s) | figure checks still outstanding: %d | notes update: %s" % (figv, figo, "done for all verified items" if st["pend"] == 0 else "PENDING for %d item(s)" % st["pend"]),
                  "   FINAL STATUS: %s" % ("FULLY VERIFIED" if done else "PARTIALLY VERIFIED")]
    T += partA + ["", "PART B - QUESTION-LEVEL EVIDENCE",
          "Paper 2 line: label [marks] | subsection(s) | mark-scheme section(s) matched (MS page) | points/alternatives | status | figure status | remarks",
          "Paper 1 line: question number, key | subsection(s) | status | figure status | same question also set in ... | remarks", ""]
    for p in pairs:
        T.append("--- %s  (%s / %s)" % (p["id"], p["qp"], p["ms"]))
        for i in bypair[p["id"]]:
            d = dec[i]; it = items[i]; rem = []
            if d.get("also"): rem.append("also: " + ", ".join(d["also"]))
            if d.get("flag"): rem.append("FLAG: " + d["flag"])
            r = d.get("remarks") or []
            rem += [str(x).replace("_", " ") for x in (r if isinstance(r, list) else [r])]
            tail = (" | " + " | ".join(rem)) if rem else ""
            if it["paper"] == 1:
                T.append("  Q%d key %s | %s | %s | %s%s" % (it["n"], d["key"], d["sec"], STAT[d["status"]], FIG[d.get("fig", "none")], tail))
            else:
                pg = ",".join(str(x) for x in (it.get("ms_pages") or [it.get("ms_page")]))
                T.append("  %s [%s] | %s | MS %s (p.%s) | %d pts / %d alt | %s | %s%s" % (it["label"], it["marks"], d["sec"],
                         ", ".join(it["ms_labels"]), pg, it["pts"], alt_count(it["ms_text"]), STAT[d["status"]], FIG[d.get("fig", "none")], tail))
        T.append("")
    wr("full_paper_verification_tracker.txt", "\n".join(T))
    # ---------------------------------------------------------------- counts used by the other files
    P1 = [i for i in od if items[i]["paper"] == 1]; P2 = [i for i in od if items[i]["paper"] == 2]
    def cnt(ids, s): return sum(1 for i in ids if dec[i]["status"] == s)
    secc = collections.OrderedDict((s, [0, 0, 0]) for s in SECS)
    for i in od:
        if dec[i]["status"] != "ver": continue
        for s in insecs(dec[i]):
            secc[s][0 if items[i]["paper"] == 1 else 1] += 1
    for s in SECS: secc[s][2] = npts[s]
    oosc = collections.Counter()
    for i in od:
        if dec[i]["status"] == "oos":
            oosc[(dec[i]["sec"], items[i]["paper"])] += 1
    moved = [i for i in P2 if dec[i]["status"] == "ver" and any("moved in by full-MS audit" in str(x) for x in (dec[i].get("remarks") or []))]
    flags = [(i, dec[i]["flag"]) for i in od if dec[i].get("flag")]
    npairs1 = sum(1 for p in pairs if p["paper"] == 1); npairs2 = len(pairs) - npairs1
    summary = ["Eligible question-paper / mark-scheme pairs: %d (Paper 1: %d; Paper 2: %d)" % (len(pairs), npairs1, npairs2),
               "Pairs FULLY VERIFIED: %d of %d" % (fully, len(pairs)),
               "Question-level items: %d (Paper 1 questions: %d; Paper 2 mark-bearing parts: %d)" % (len(od), len(P1), len(P2)),
               "   verified, in scope:      %5d (Paper 1: %d; Paper 2: %d)" % (cnt(od, "ver"), cnt(P1, "ver"), cnt(P2, "ver")),
               "   read, out of scope:      %5d (Paper 1: %d; Paper 2: %d)" % (cnt(od, "oos"), cnt(P1, "oos"), cnt(P2, "oos")),
               "   in scope, still pending: %5d" % cnt(od, "pend"),
               "Paper 2 items moved into scope by the full mark-scheme audit of out-of-scope items: %d" % len(moved),
               "Paper 1 questions moved into scope by the review against the learning objectives: %d" % sum(1 for i in dec if items[i]["paper"] == 1 and dec[i]["status"] == "ver" and any("moved in" in str(r) for r in (dec[i].get("remarks") or []))),
               "Marks available in the eligible papers: %d" % tot["marks"],
               "Marking points accounted for in verified items: %d (Paper 1 keys: %d; Paper 2 \";\" points: %d)" % (tot["pts"], cnt(P1, "ver"), tot["pts"] - cnt(P1, "ver")),
               "Items whose figure was rendered and inspected: %d (Paper 1: %d; Paper 2: %d) | figure checks outstanding: %d" % (tot["figv"], sum(1 for i in P1 if dec[i]["status"] == "ver" and dec[i]["fig"] == "viewed"), sum(1 for i in P2 if dec[i]["status"] == "ver" and dec[i]["fig"] == "viewed"), tot["figo"]),
               "Marking-point lines (dash bullets) in the notes: %d" % sum(npts.values()),
               "Flagged items (key / mark-scheme problems): %d" % len(flags)]
    sect = ["%-5s %-52s %7s %7s %7s" % ("sec", "title", "P1", "P2", "points")]
    for s in SECS:
        title = notes(s).split("\n")[0][len(s):].strip()
        sect.append("%-5s %-52s %7d %7d %7d" % (s, title[:52], secc[s][0], secc[s][1], secc[s][2]))
    oost = ["%-12s %6s %6s" % ("code", "P1", "P2")]
    for code in sorted({k[0] for k in oosc}, key=lambda c: (len(c.split("+")), c)):
        oost.append("%-12s %6d %6d" % (code, oosc[(code, 1)], oosc[(code, 2)]))
    # ---------------------------------------------------------------- checkpoint
    C = ["VERIFICATION CHECKPOINT - Cambridge O Level Biology 5090, Papers 1 and 2",
         "Written %s. This file is regenerated from the live state every time the deliverables are rebuilt." % NOW, "",
         "1. WHERE THE STATE LIVES (everything needed to resume is inside this folder)",
         "   biology-5090-notes/_work/state/decisions.json   one record per question-level item: subsection(s), status, key or matched mark-scheme labels, figure status, flags, remarks",
         "   biology-5090-notes/_work/state/pairs.json       the eligible question-paper / mark-scheme pairs",
         "   biology-5090-notes/_work/state/log.txt          time-stamped log of every decision and every note patch",
         "   biology-5090-notes/_work/data/items.json        extracted question text and full mark-scheme text for every item",
         "   biology-5090-notes/_work/notes/<subsection>.txt the live notes, one file per syllabus subsection",
         "   biology-5090-notes/_work/scripts/               extraction, viewing, marking, patching, audit and delivery scripts",
         "   To resume: python3 -m venv venv && venv/bin/pip install pymupdf pillow; then run scripts/show.py <item id> to view an item, scripts/mark.py to record a decision, scripts/deliver.py to rebuild these five files, scripts/audit.py to re-run the consistency checks.", "",
         "2. PROGRESS AT THIS CHECKPOINT"] + ["   " + x for x in summary] + ["",
         "3. VERIFIED ITEMS AND NOTE POINTS PER SUBSECTION (an item credited to two subsections is counted in both)"] + ["   " + x for x in sect] + ["",
         "4. OUT-OF-SCOPE ITEMS BY CODE"] + ["   " + x for x in oost] + ["",
         "5. PAIRS NOT YET FULLY VERIFIED"]
    nf = [k for k, v in perpair.items() if not v[7]]
    C += ["   none" if not nf else "   " + ", ".join(nf), ""]
    C += ["6. OPEN POINTS AT THIS CHECKPOINT", rd("checkpoint_open.txt") or "   (none recorded)", ""]
    wr("verification_checkpoint.txt", "\n".join(C))
    # ---------------------------------------------------------------- excluded files and issues
    files = sorted(os.listdir(SRC)); kinds = collections.Counter()
    used = {p["qp"] for p in pairs} | {p["ms"] for p in pairs}
    unused = collections.defaultdict(list)
    for f in files:
        m = re.match(r"5090_([swmy])(\d\d)_([a-z]+)_?(\d*)", f)
        if f in used: kinds["used"] += 1; continue
        if not m: unused["other / irregular file name"].append(f); continue
        typ, num = m.group(3), m.group(4)
        if "solved" in f: unused["unofficial 'solved' scans (image only, not official mark schemes)"].append(f)
        elif "erratum" in f or "_et_" in f: unused["errata sheets"].append(f)
        elif typ == "qp" and num[:1] in ("1", "2"): unused["Paper 1 / Paper 2 question papers WITHOUT a usable official mark scheme or key (excluded - see section A)"].append(f)
        elif typ == "ms" and num[:1] in ("1", "2"): unused["Paper 1 / Paper 2 mark schemes with no matching question paper"].append(f)
        elif typ in ("qp", "ms"): unused["question papers and mark schemes of other papers (Papers 3, 4, 6 - not requested)"].append(f)
        elif typ == "er": unused["examiner reports (used only where they publish the Paper 1 key table)"].append(f)
        elif typ in ("ir", "ci"): unused["practical instructions / confidential instructions"].append(f)
        elif typ == "gt": unused["grade thresholds"].append(f)
        elif typ == "sy": unused["syllabus documents"].append(f)
        else: unused["other file types (%s)" % typ].append(f)
    E = ["EXCLUDED FILES AND ISSUES - Cambridge O Level Biology 5090, Papers 1 and 2", "Written %s." % NOW, "",
         "Folder scanned: biology-5090/ (%d PDF files). Files used as an eligible question paper or as its mark scheme / key source: %d." % (len(files), len(used)), "",
         rd("issues_A_excluded.txt"), "", "B. FILES IN THE FOLDER THAT WERE NOT USED AS QUESTION PAPER OR MARK SCHEME"]
    for k in sorted(unused, key=lambda k: -len(unused[k])):
        v = unused[k]; E.append("   %-4d %s" % (len(v), k))
        if len(v) <= 12: E += ["          " + x for x in v]
    E += ["", "C. FLAGGED ITEMS (answer key or mark scheme appears wrong, ambiguous or in conflict)"]
    for i, f in flags: E += ["   %s  [%s, %s]" % (i, dec[i]["sec"], STAT[dec[i]["status"]]), "      " + f]
    E += ["", rd("issues_D_static.txt")]
    wr("excluded_files_and_issues.txt", "\n".join(E))
    # ---------------------------------------------------------------- final report
    R = ["FINAL VERIFICATION REPORT - Cambridge O Level Biology 5090, Papers 1 and 2", "Written %s." % NOW, "",
         "1. RESULT IN NUMBERS"] + ["   " + x for x in summary] + ["",
         "2. VERIFIED ITEMS AND NOTE POINTS PER SUBSECTION"] + ["   " + x for x in sect] + ["",
         "3. OUT-OF-SCOPE ITEMS BY CODE"] + ["   " + x for x in oost] + ["   Codes: " + "; ".join("%s = %s" % kv for kv in OOS.items()), "",
         rd("report_static.txt"), "",
         "AUTOMATIC CONSISTENCY AUDIT (scripts/audit.py)", rd("../state/audit_result.txt") or "   not yet run"]
    wr("final_verification_report.txt", "\n".join(R))
    print("\n".join(summary))
if __name__ == "__main__":
    main()
