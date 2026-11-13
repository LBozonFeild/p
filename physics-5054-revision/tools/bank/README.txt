QUESTION BANK TOOLS (Physics 5054, Papers 1 and 2)
==================================================
Output:  ../../question_bank/
           physics_5054_past_paper_questions_with_ms.pdf      the bank
           physics_5054_question_bank_tracker.txt / .pdf      one line per record and per question left out
           physics_5054_question_bank_exclusions.txt / .pdf   what is not in the bank, and why
           physics_5054_question_bank_audit.txt / .pdf        counts, reconciliation, checks, visual review, limits
Scratch: /home/user/work/bank (volatile; everything in it is rebuilt by the programs below)

Scope and rules
  * papers: Paper 1 and Paper 2 question papers that have an official mark scheme in the repository (156 verified pairs);
  * topics: the selected sections of this project: 1.1-1.7 (not 1.8), 3.1-3.4, 4.2 (27 subsections); 4.3 is NOT included;
  * the syllabus subsection(s) of a question come from the verified findings (../../findings): a Paper 2 question is
    listed once under every selected subsection that at least one of its sub-questions was assigned to (first in-scope
    code of the tracker row); a Paper 1 question is listed under the first in-scope code of its row;
  * always the whole question and the whole scheme of that question; EITHER/OR alternatives are both kept (they are
    recognised from the text of the question paper; the marks of such a question are those of one alternative);
  * the header of a Paper 2 page names the mark-bearing units of the question that are on the subsection, each by all
    the sub-parts its mark covers ('(a)(i)-(ii)' where one '[2]' is printed for (a)(i) and (a)(ii));
  * a question is never shown without the official scheme of its own paper; nothing is taken from another paper;
  * order: subsection, year, session (May/June then Oct/Nov), variant, paper, question number.

Facts about the source PDFs (found while building; the programs depend on them)
  * every PDF in physics-5054/ is stored colour-inverted by a wrapper in the page content stream
    ('%ArenaInvertBase' ... '%ArenaInvertInvert', page key /ArenaInvert true). The wrapper also leaves the fill colour
    white for the original content, so content drawn in the default fill colour (whole blocks of text in the 2004-2009
    papers: 282 pages of 31 paired files) is INVISIBLE in the stored copy. bgeom.fix_arena() restores the original
    content stream (default colours reset, inverting rectangle dropped). Never render a source page without it and
    never "fix" by inverting pixels: the invisible text stays invisible.
  * the landscape mark schemes (2017+) carry /Rotate 90; text coordinates from PyMuPDF are unrotated. Doc() calls
    Page.remove_rotation(), which applies the rotation matrix to the content: everything is then in display coordinates.
  * the 2026 files carry a third-party watermark and footer (PapaCambridge); the Oct/Nov 2019 and 2020 mark schemes
    are landscape pages scaled down onto portrait pages (7.4 pt text; rendered at 252 dpi instead of 180 dpi).
  * rendering is made independent of earlier calls: Doc.gray() empties MuPDF's store first. Without that, a page
    whose text had been read with get_text('dict') rendered some hatchings and dot patterns differently (a bitmap
    decoded at another size was reused), and three pictures of the bank differed from a fresh rendering.

Run order (python = /home/user/.venv/bin/python; run from this directory; ../restore.sh first if /home/user/work is
missing: the bank needs WORK/p2_manifest.json, p1_questions.json, keys_p1.json, state.pkl)
  1  bgeom.py          crop geometry of every question, scheme and key row      -> WORK/bank/geom.json         3.5 min
  2  bcheck_geom.py    tests V1-V11 of the geometry against the source PDFs     -> WORK/bank/geom_check.json   8 min
  3  bbuild.py         renders the crops, assembles the bank PDF                -> ../../question_bank/*.pdf,
                       (picture cache WORK/bank/img; delete it or raise the        WORK/bank/manifest.json,
                       tag 'v4' in render() after any change to Doc/fix_arena)     WORK/bank/entries.json      7 min (2 with cache)
  4  bverify.py sheets reopens the PDF, renders every page, compares every      -> WORK/bank/verify.json,
                       picture with the source; contact sheets of all pages        WORK/bank/sheets/cs_NNN.png 9 min
  5  bunpaired.py      questions of the papers without a mark scheme            -> ../data/bank_unpaired_questions.json
  6  breports.py       tracker, exclusions, audit (.txt and .pdf); exit code 1 if anything failed or if the results
                       of steps 2 and 4 do not belong to the PDF and geometry on disk (hashes are compared)
  7  bfinal.py         reopens all deliverables from disk and checks them once more (page counts, bookmarks, text of
                       the reports against the bank)

Files
  bgeom.py        fix_arena(), Doc, page furniture, ink profile, question / scheme starts, bands, key rows
  bentries.py     the list of records in bank order, from the verified findings and the geometry; EITHER/OR questions
                  and the marks of a question
  bparts.py       sub-parts covered by each mark-bearing unit (repeats the label tracking of ../parse_p2.py; run alone
                  it checks that its units are identical to those of the parser for all 78 Paper 2 papers)
  bbuild.py       layout and PDF assembly
  bcheck_geom.py  V1 marks inside the crops, V2/V4 every row in exactly one crop, V3 starts, V5/V6 Paper 1 texts and key
                  rows, V7 ink on the cut lines, V8 mark codes of neighbouring schemes, V9 no crop without text,
                  V10 no ink left outside the crops, V11 no stroke crosses a cut line
  bverify.py      A structure (pages, records, order, bookmarks, size), B pictures (every page rendered; every picture
                  identical to a fresh rendering of its source region; page shows exactly these pixels; cut lines;
                  size), C texts of the grey bars; marks named in the header against the marks printed on the paper
  bunpaired.py    codes of the questions of the ten papers without a scheme (identical-text test + hand codes in
                  ../data/bank_unpaired_classification.json)
  breports.py     the three reports; reconciliation R1-R11
  bfinal.py       last check of the files on disk
  visual_review.txt   record of the inspection by eye (written by hand; printed in the audit, part 8)
  viewers         bpages.py (pages of the bank), bedge.py (a cut line in the bank next to the source page),
                  bview.py (source pages), bdebug.py / bdebug2.py (source pages with the bands drawn on them)

Versions used for the committed build: PyMuPDF 2.1 (MuPDF 1.28.6), numpy 2.4.6, Pillow 13.0.0.
Check B3b compares the stored pictures with a fresh rendering in the SAME environment; with another MuPDF version the
pictures of a new build can differ by anti-aliasing from the committed ones, so rebuild before verifying.
