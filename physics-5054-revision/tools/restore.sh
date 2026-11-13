#!/bin/bash
# Rebuilds the scratch data in /home/user/work (digests, crops, sheets, manifests, keys) and the Python environment.
# Nothing in /home/user/work is a deliverable: it is derived from the PDFs in physics-5054/ and can be rebuilt in about a minute.
# After it has run, tools/check.py and tools/report.py reproduce the tracker, checkpoint and exclusions file from findings/.
set -e
T=/home/user/p/physics-5054-revision/tools
[ -x /home/user/.venv/bin/python ] || python3 -m venv /home/user/.venv
# numpy is needed by the question-bank tools (tools/bank); the notes tools need only PyMuPDF and Pillow
/home/user/.venv/bin/python -c "import fitz, PIL, numpy" 2>/dev/null || /home/user/.venv/bin/pip install -q pymupdf pillow numpy
PY="/home/user/.venv/bin/python -W ignore"
mkdir -p /home/user/work/tools /home/user/work/txt /home/user/work/view /home/user/work/tmp
cd $T
$PY parse_ms1.py | tail -1        # Paper 1 keys from the mark-scheme PDFs  -> work/keys_p1.json
$PY parse_p1.py | tail -1         # Paper 1 questions from the QP PDFs       -> work/p1_questions.json
$PY header_check.py | tail -1     # QP/MS header agreement                   -> work/header_check.json
$PY build_p2.py | tail -2         # Paper 2 digests, crops and manifest      -> work/digest/p2, work/p2_manifest.json
$PY build_dupmap.py | head -1     # Paper 1 repeated questions (validated)   -> work/p1_dupmap.json
$PY build_p1.py | tail -2         # Paper 1 digests and figure sheets
$PY build_p1_rest.py > /dev/null  # remaining Paper 1 figure sheets
$PY check.py | tail -3            # validates findings/ against the manifests -> work/status.json, work/state.pkl
$PY report.py | tail -1           # tracker, checkpoint, exclusions, by_section.json
# The scratch data of the question bank (/home/user/work/bank) is rebuilt separately: see tools/bank/README.txt.
