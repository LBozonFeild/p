NOTES SOURCES (input of tools/build_notes.py)
One file per syllabus section, <section>.txt. Format (see tools/notes_lib.py):
  ORDER A B C …                                 first line: order in which the sub-topics are printed
  == ID | sub-topic title | regex | priority    sub-topic heading; findings lines matching the regex are filed under it
                                                (the rule with the lowest priority number is tried first)
  ALSO ID | regex | priority                    extra filing rule for a sub-topic
  - text    checklist point credited in Paper 2 mark schemes (official marking point, generalised, marks in brackets)
  * text    checklist point needed for Paper 1 multiple-choice questions (own explanation that leads to the official key)
  MOVE pair|label|ID                            manual filing of one findings line
  == Z | Other points                           catch-all; must stay empty (build_notes.py refuses to build otherwise)
Field separator in the == and ALSO lines is exactly " | "; a regex must not end with "|".

_overrides.txt  pair|label|text: wording used in the notes for mixed sub-questions (steps that need rules from outside the
                selected sections are removed; the findings file and the tracker keep the full line)
_audit_ok.txt   exceptions of tools/audit_notes.py that were read and accepted, one per line: key <TAB> reason
                (keys: B|section|pair|label|point index, C|section|sub-topic|first 60 characters of the line, N|…)

Tools (run from tools/ with the Python of restore.sh):
  dump_sec.py <sec> [ids|all] [full|brief] [page]   read every findings line of a section, grouped by sub-topic
  hidden.py <sec> [ID,ID]                           findings lines merged into a longer one in the dump
  mv.py <sec> ID:idx,idx …                          re-file findings lines (writes MOVE lines)
  setb.py <sec> < text                              replace the checklists of the sub-topics named by @ID lines
  edl.py <sec> <match> <new line|DELETE> …          edit one checklist line; +ID as match appends a line to sub-topic ID
  build_notes.py                                    writes physics_papers_1_2_notes.txt (never edit that file by hand)
  audit_notes.py                                    checks the notes against the findings; lists in /home/user/work/notes_audit.txt
Order after any change of findings or sources:
  check.py -> report.py -> cp /home/user/work/{by_section.json,status.json} data/ -> build_notes.py -> audit_notes.py -> final_audit.py
Do not rewrite a section file from scratch: its ORDER, MOVE and checklist lines would be lost. Edit in place.

Scope rules used for the checklists (syllabus for 2026-2028):
  - only the content of sections 1.1-1.7, 3.1-3.4 and 4.2 (4.2.1-4.2.4);
  - series and parallel circuit rules and the potential divider (4.3), P = IV and cost of electricity (4.4), fusion in the
    Sun (5, 6) and pressure (1.8) are left out, also when they are a step inside a question of a selected section;
  - 4.2.4 keeps R = V/I for one component or for the whole circuit (total resistance treated as known);
  - the kilowatt-hour stays in 1.7.5 only as a unit of energy used with E = Pt;
  - content of earlier syllabuses under a selected heading is kept and named in the header of the notes.
