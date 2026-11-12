"""Flowchart specs for the study guide. y increases downward."""


def N(id, type, label, x, y, w=None, h=None):
    d = dict(id=id, type=type, label=label, x=x, y=y)
    if w:
        d["w"] = w
    if h:
        d["h"] = h
    return d


def E(frm, to, label=None, path=None, exit=None, entry=None):
    d = dict(frm=frm, to=to)
    if label:
        d["label"] = label
    if path:
        d["path"] = path
    if exit:
        d["exit"] = exit
    if entry:
        d["entry"] = entry
    return d


CHARTS = {}

# 2.1 counting with a FOR loop
CHARTS["for-loop"] = dict(
    nodes=[
        N("s", "start", "Start", 170, 20),
        N("init", "process", "I \u2190 1", 170, 76),
        N("test", "decision", "I <= 5?", 170, 152, w=118, h=52),
        N("out", "io", "OUTPUT I", 170, 236, w=120),
        N("inc", "process", "I \u2190 I + 1", 170, 302, w=118),
        N("stop", "start", "Stop", 170, 372),
    ],
    edges=[
        E("s", "init"), E("init", "test"), E("test", "out", "Yes"),
        E("out", "inc"), E("inc", "test", path=[(72, 302), (72, 152)]),
        E("test", "stop", "No", path=[(300, 152), (300, 372)]),
    ])

# 2.2 WHILE (test at the top — may run zero times)
CHARTS["while-password"] = dict(
    nodes=[
        N("s", "start", "Start", 165, 20),
        N("init", "process", 'Password \u2190 ""', 165, 74),
        N("test", "decision", 'Password <> "Secret"?', 165, 152, w=196, h=54),
        N("inp", "io", "INPUT Password", 165, 240, w=140),
        N("out", "io", 'OUTPUT "Access granted"', 165, 330, w=190),
        N("stop", "start", "Stop", 165, 398),
    ],
    edges=[
        E("s", "init"), E("init", "test"), E("test", "inp", "Yes"),
        E("inp", "test", path=[(72, 240), (72, 152)]),
        E("test", "out", "No", path=[(300, 152), (300, 330)]),
        E("out", "stop"),
    ])

# 2.3 REPEAT...UNTIL (test at the bottom — always runs at least once)
CHARTS["repeat-password"] = dict(
    nodes=[
        N("s", "start", "Start", 165, 20),
        N("inp", "io", "INPUT Password", 165, 82, w=140),
        N("test", "decision", 'Password = "Secret"?', 165, 164, w=192, h=54),
        N("out", "io", 'OUTPUT "Access granted"', 165, 252, w=190),
        N("stop", "start", "Stop", 165, 320),
    ],
    edges=[
        E("s", "inp"), E("inp", "test"), E("test", "out", "Yes"),
        E("out", "stop"),
        E("test", "inp", "No", path=[(70, 164), (70, 82)]),
    ])

# 2.4 totalling, counting and selection inside a loop
CHARTS["total-count"] = dict(
    nodes=[
        N("s", "start", "Start", 140, 20),
        N("init", "process", "Total \u2190 0\nCount \u2190 0\nI \u2190 1", 140, 92, w=132, h=54),
        N("test", "decision", "I <= 5?", 140, 180, w=112, h=52),
        N("inp", "io", "INPUT Price", 140, 262, w=126),
        N("acc", "process", "Total \u2190 Total + Price", 140, 326, w=196),
        N("if2", "decision", "Price > 4?", 140, 408, w=118, h=52),
        N("cnt", "process", "Count \u2190 Count + 1", 330, 408, w=160),
        N("inc", "process", "I \u2190 I + 1", 140, 492, w=112),
        N("out", "io", "OUTPUT Total, Count", 355, 180, w=180),
        N("stop", "start", "Stop", 355, 252),
    ],
    edges=[
        E("s", "init"), E("init", "test"), E("test", "inp", "Yes"),
        E("inp", "acc"), E("acc", "if2"), E("if2", "cnt", "Yes"),
        E("cnt", "inc", path=[(330, 492)]), E("if2", "inc", "No"),
        E("inc", "test", path=[(52, 492), (52, 180)]),
        E("test", "out", "No"), E("out", "stop"),
    ])

# 2.5 nested IF (the taught pattern)
CHARTS["nested-if"] = dict(
    nodes=[
        N("s", "start", "Start", 200, 20),
        N("d1", "decision", "Score >= 80?", 200, 96, w=150, h=52),
        N("o1", "io", 'OUTPUT "Grade A"', 200, 182, w=140),
        N("d2", "decision", "Score >= 60?", 200, 264, w=150, h=52),
        N("o2", "io", 'OUTPUT "Grade B"', 200, 350, w=140),
        N("o3", "io", 'OUTPUT "Grade C"', 200, 432, w=140),
        N("stop", "start", "Stop", 200, 516),
    ],
    edges=[
        E("s", "d1"), E("d1", "o1", "Yes"), E("d1", "d2", "No"),
        E("d2", "o2", "Yes"), E("d2", "o3", "No"),
        E("o1", "stop", exit="right", entry="right", path=[(340, 182), (340, 516)]),
        E("o2", "stop", exit="right", entry="bottom", path=[(380, 350), (380, 545), (200, 545)]),
        E("o3", "stop"),
    ])

# 3.1 SUBSTRING / LENGTH / UCASE
CHARTS["substring-linear"] = dict(
    nodes=[
        N("s", "start", "Start", 210, 20),
        N("a1", "process", 'Text \u2190 "Computer"', 210, 82, w=155),
        N("a2", "process", "Part \u2190 SUBSTRING(Text, 3, 3)", 210, 146, w=250),
        N("a3", "process", "First \u2190 UCASE(SUBSTRING(Text, 1, 1))", 210, 210, w=295),
        N("o", "io", "OUTPUT Part, First", 210, 278, w=175),
        N("stop", "start", "Stop", 210, 348),
    ],
    edges=[E("s", "a1"), E("a1", "a2"), E("a2", "a3"), E("a3", "o"), E("o", "stop")])

# 3.2 counting with LENGTH + SUBSTRING
CHARTS["vowel-count"] = dict(
    nodes=[
        N("s", "start", "Start", 170, 20),
        N("inp", "io", "INPUT S", 170, 80, w=105),
        N("init", "process", "Count \u2190 0\nI \u2190 1", 170, 142, w=112, h=42),
        N("test", "decision", "I <= LENGTH(S)?", 170, 226, w=180, h=52),
        N("ch", "process", "Ch \u2190 UCASE(SUBSTRING(S, I, 1))", 170, 308, w=255),
        N("ifv", "decision", "Ch is a vowel?", 170, 392, w=165, h=52),
        N("cnt", "process", "Count \u2190 Count + 1", 368, 392, w=155),
        N("inc", "process", "I \u2190 I + 1", 170, 478, w=110),
        N("out", "io", "OUTPUT Count", 425, 226, w=135),
        N("stop", "start", "Stop", 425, 296),
    ],
    edges=[
        E("s", "inp"), E("inp", "init"), E("init", "test"), E("test", "ch", "Yes"),
        E("ch", "ifv"), E("ifv", "cnt", "Yes"), E("ifv", "inc", "No"),
        E("cnt", "inc", path=[(368, 478)]),
        E("inc", "test", path=[(60, 478), (60, 226)]),
        E("test", "out", "No"), E("out", "stop"),
    ])

# 4.1 filling and reading a 1D array
CHARTS["fill-array"] = dict(
    nodes=[
        N("s", "start", "Start", 170, 20),
        N("init", "process", "I \u2190 1", 170, 78),
        N("test", "decision", "I <= 4?", 170, 152, w=112, h=52),
        N("inp", "io", "INPUT Marks[I]", 170, 232, w=145),
        N("inc", "process", "I \u2190 I + 1", 170, 300, w=112),
        N("out", "io", "OUTPUT Marks[3]", 170, 382, w=150),
        N("stop", "start", "Stop", 170, 450),
    ],
    edges=[
        E("s", "init"), E("init", "test"), E("test", "inp", "Yes"), E("inp", "inc"),
        E("inc", "test", path=[(76, 300), (76, 152)]),
        E("test", "out", "No", path=[(310, 152), (310, 382)]),
        E("out", "stop"),
    ])

# 4.2 2D array: nested loops
CHARTS["row-totals"] = dict(
    nodes=[
        N("s", "start", "Start", 140, 20),
        N("init", "process", "Row \u2190 1", 140, 78),
        N("t1", "decision", "Row <= 2?", 140, 152, w=130, h=52),
        N("init2", "process", "Sum \u2190 0\nCol \u2190 1", 140, 234, w=112, h=42),
        N("t2", "decision", "Col <= 3?", 140, 320, w=130, h=52),
        N("acc", "process", "Sum \u2190 Sum + Grid[Row, Col]", 140, 404, w=235),
        N("cinc", "process", "Col \u2190 Col + 1", 140, 472, w=125),
        N("rinc", "process", "Row \u2190 Row + 1", 140, 562, w=125),
        N("out", "io", "OUTPUT Row, Sum", 370, 320, w=155),
        N("stop", "start", "Stop", 500, 152),
    ],
    edges=[
        E("s", "init"), E("init", "t1"), E("t1", "init2", "Yes"), E("init2", "t2"),
        E("t2", "acc", "Yes"), E("acc", "cinc"),
        E("cinc", "t2", path=[(52, 472), (52, 320)]),
        E("t2", "out", "No"), E("out", "rinc", path=[(370, 562)]),
        E("rinc", "t1", path=[(24, 562), (24, 152)]), E("t1", "stop", "No"),
    ])

# 4.3 SQL-style filter (selection over parallel arrays)
CHARTS["sql-filter"] = dict(
    nodes=[
        N("s", "start", "Start", 170, 20),
        N("init", "process", "I \u2190 1", 170, 78),
        N("t", "decision", "I <= 5?", 170, 152, w=112, h=52),
        N("ifd", "decision", 'Class[I] = "9A"\nAND Mark[I] >= 80?', 170, 242, w=210, h=60),
        N("o", "io", "OUTPUT Name[I]", 170, 332, w=145),
        N("inc", "process", "I \u2190 I + 1", 170, 402, w=112),
        N("stop", "start", "Stop", 170, 478),
    ],
    edges=[
        E("s", "init"), E("init", "t"), E("t", "ifd", "Yes"), E("ifd", "o", "Yes"),
        E("ifd", "inc", "No"), E("o", "inc"),
        E("inc", "t", path=[(76, 402), (76, 152)]),
        E("t", "stop", "No", path=[(330, 152), (330, 478)]),
    ])

# 5.1 PROCEDURE with parameters
CHARTS["procedure-call"] = dict(
    nodes=[
        N("l1", "label", "Call site", 95, 12),
        N("s", "start", "Start", 95, 48),
        N("sub", "sub", "CALL PrintLine('*', 5)", 95, 112, w=195),
        N("stop", "start", "Stop", 95, 178),
        N("l2", "label", "PROCEDURE PrintLine", 390, 12),
        N("pinit", "process", 'LineText \u2190 ""\nI \u2190 1', 390, 60, w=125, h=42),
        N("ptest", "decision", "I <= Times?", 390, 148, w=155, h=52),
        N("pacc", "process", "LineText \u2190 LineText + Symbol", 390, 232, w=225),
        N("pinc", "process", "I \u2190 I + 1", 390, 300, w=112),
        N("pout", "io", "OUTPUT LineText", 390, 376, w=150),
        N("pstop", "start", "Stop", 390, 444),
    ],
    edges=[
        E("s", "sub"), E("sub", "stop"),
        E("pinit", "ptest"), E("ptest", "pacc", "Yes"), E("pacc", "pinc"),
        E("pinc", "ptest", path=[(285, 300), (285, 148)]),
        E("ptest", "pout", "No", path=[(545, 148), (545, 376)]),
        E("pout", "pstop"),
    ])

# 5.2 FUNCTION with return value
CHARTS["function-call"] = dict(
    nodes=[
        N("l1", "label", "Call site", 110, 12),
        N("s", "start", "Start", 110, 42),
        N("sub", "sub", "W \u2190 MaxOf(72, 88)", 110, 104, w=175),
        N("o", "io", 'OUTPUT "The winner is ", W', 110, 168, w=215),
        N("stop", "start", "Stop", 110, 236),
        N("l2", "label", "FUNCTION MaxOf", 430, 12),
        N("fd", "decision", "Value1 > Value2?", 430, 70, w=185, h=54),
        N("fr1", "stop", "RETURN Value1", 430, 158, w=150, h=26),
        N("fr2", "stop", "RETURN Value2", 430, 232, w=150, h=26),
    ],
    edges=[
        E("s", "sub"), E("sub", "o"), E("o", "stop"),
        E("fd", "fr1", "Yes"), E("fd", "fr2", "No", path=[(565, 70), (565, 232)]),
    ])

# 5.3 local vs global variables
CHARTS["local-global"] = dict(
    nodes=[
        N("l1", "label", "Call site", 110, 12),
        N("s", "start", "Start", 110, 42),
        N("p", "process", "Total \u2190 5", 110, 102, w=110),
        N("sub", "sub", "CALL AddUp", 110, 162, w=130),
        N("o", "io", "OUTPUT Total", 110, 226, w=130),
        N("stop", "start", "Stop", 110, 292),
        N("l2", "label", "PROCEDURE AddUp", 360, 12),
        N("p2", "process", "local Total \u2190 10", 360, 82, w=160),
        N("r", "stop", "return", 360, 150, w=110, h=24),
    ],
    edges=[E("s", "p"), E("p", "sub"), E("sub", "o"), E("o", "stop"), E("p2", "r")])

# 6.1 file handling
CHARTS["file-average"] = dict(
    nodes=[
        N("s", "start", "Start", 165, 20),
        N("op", "process", 'OPENFILE "Scores.txt" FOR READ', 165, 80, w=255),
        N("init", "process", "Total \u2190 0\nI \u2190 1", 165, 146, w=112, h=42),
        N("t", "decision", "I <= 3?", 165, 228, w=112, h=52),
        N("rd", "io", 'READFILE "Scores.txt", Mark', 165, 312, w=235),
        N("acc", "process", "Total \u2190 Total + Mark", 165, 380, w=185),
        N("inc", "process", "I \u2190 I + 1", 165, 446, w=112),
        N("cl", "process", 'CLOSEFILE "Scores.txt"', 165, 522, w=195),
        N("o", "io", "OUTPUT Total / 3", 165, 590, w=155),
        N("stop", "start", "Stop", 165, 658),
    ],
    edges=[
        E("s", "op"), E("op", "init"), E("init", "t"), E("t", "rd", "Yes"),
        E("rd", "acc"), E("acc", "inc"),
        E("inc", "t", path=[(72, 446), (72, 228)]),
        E("t", "cl", "No", path=[(330, 228), (330, 522)]),
        E("cl", "o"), E("o", "stop"),
    ])

# 7.1 largest and smallest
CHARTS["max-min"] = dict(
    nodes=[
        N("s", "start", "Start", 150, 20),
        N("inp1", "io", "INPUT Value", 150, 80, w=130),
        N("init", "process", "Largest \u2190 Value\nSmallest \u2190 Value\nI \u2190 2", 150, 148, w=172, h=54),
        N("t", "decision", "I <= 3?", 150, 240, w=112, h=52),
        N("inp2", "io", "INPUT Value", 150, 322, w=130),
        N("d1", "decision", "Value > Largest?", 150, 404, w=185, h=52),
        N("p1", "process", "Largest \u2190 Value", 372, 404, w=150),
        N("d2", "decision", "Value < Smallest?", 150, 496, w=195, h=52),
        N("p2", "process", "Smallest \u2190 Value", 372, 496, w=160),
        N("inc", "process", "I \u2190 I + 1", 150, 588, w=112),
        N("out", "io", "OUTPUT Largest, Smallest", 150, 662, w=200),
        N("stop", "start", "Stop", 150, 732),
    ],
    edges=[
        E("s", "inp1"), E("inp1", "init"), E("init", "t"), E("t", "inp2", "Yes"),
        E("inp2", "d1"), E("d1", "p1", "Yes"), E("p1", "d2", path=[(372, 496)]),
        E("d1", "d2", "No"), E("d2", "p2", "Yes"), E("p2", "inc", path=[(372, 588)]),
        E("d2", "inc", "No"), E("inc", "t", path=[(52, 588), (52, 240)]),
        E("t", "out", "No", path=[(545, 240), (545, 662)]), E("out", "stop"),
    ])

# 7.2 linear search
CHARTS["linear-search"] = dict(
    nodes=[
        N("s", "start", "Start", 150, 20),
        N("init", "process", "Found \u2190 FALSE\nPosition \u2190 0\nI \u2190 1", 150, 90, w=150, h=54),
        N("t", "decision", "Found = FALSE\nAND I <= 4?", 150, 182, w=205, h=58),
        N("d", "decision", "A[I] = SearchKey?", 150, 276, w=205, h=54),
        N("p", "process", "Found \u2190 TRUE\nPosition \u2190 I", 345, 276, w=155, h=42),
        N("inc", "process", "I \u2190 I + 1", 150, 362, w=112),
        N("d2", "decision", "Found = TRUE?", 150, 452, w=165, h=54),
        N("o1", "io", 'OUTPUT "Found at ", Position', 150, 536, w=215),
        N("o2", "io", 'OUTPUT "Not found"', 345, 536, w=155),
        N("stop", "start", "Stop", 150, 616),
    ],
    edges=[
        E("s", "init"), E("init", "t"), E("t", "d", "Yes"), E("d", "p", "Yes"),
        E("p", "inc", path=[(345, 362)]), E("d", "inc", "No"),
        E("inc", "t", path=[(52, 362), (52, 182)]),
        E("t", "d2", "No", path=[(525, 182), (525, 452)]),
        E("d2", "o1", "Yes"), E("d2", "o2", "No", path=[(250, 452), (250, 536)]),
        E("o1", "stop"), E("o2", "stop", path=[(345, 616)]),
    ])

# 7.3 bubble sort pass
CHARTS["bubble-pass"] = dict(
    nodes=[
        N("s", "start", "Start", 150, 20),
        N("init", "process", "Outer \u2190 1", 150, 80, w=115),
        N("t1", "decision", "Outer <= N - 1?", 150, 156, w=190, h=52),
        N("iinit", "process", "Inner \u2190 1", 150, 238, w=115),
        N("t2", "decision", "Inner <= N - Outer?", 150, 316, w=225, h=52),
        N("d", "decision", "A[Inner] > A[Inner + 1]?", 150, 402, w=250, h=52),
        N("sw", "process", "Temp \u2190 A[Inner]\nA[Inner] \u2190 A[Inner + 1]\nA[Inner + 1] \u2190 Temp", 150, 494, w=215, h=54),
        N("iinc", "process", "Inner \u2190 Inner + 1", 150, 586, w=145),
        N("oinc", "process", "Outer \u2190 Outer + 1", 150, 668, w=145),
        N("stop", "start", "Stop", 150, 742),
    ],
    edges=[
        E("s", "init"), E("init", "t1"), E("t1", "iinit", "Yes"), E("iinit", "t2"),
        E("t2", "d", "Yes"), E("d", "sw", "Yes"), E("sw", "iinc"),
        E("d", "iinc", "No", path=[(430, 402), (430, 586)]),
        E("t2", "oinc", "No", path=[(480, 316), (480, 668)]),
        E("iinc", "t2", path=[(56, 586), (56, 316)]),
        E("oinc", "t1", path=[(30, 668), (30, 156)]),
        E("t1", "stop", "No", path=[(245, 156), (545, 156), (545, 742)]),
    ])

# 8.1 validation (range check)
CHARTS["validation-age"] = dict(
    nodes=[
        N("s", "start", "Start", 170, 20),
        N("inp", "io", "INPUT Age", 170, 84, w=115),
        N("d", "decision", "13 <= Age <= 19?", 170, 164, w=190, h=52),
        N("ok", "io", 'OUTPUT "Welcome"', 170, 252, w=140),
        N("bad", "io", 'OUTPUT "Invalid age"', 372, 164, w=160),
        N("stop", "start", "Stop", 170, 322),
    ],
    edges=[
        E("s", "inp"), E("inp", "d"), E("d", "ok", "Yes"), E("ok", "stop"),
        E("d", "bad", "No"),
        E("bad", "inp", path=[(372, 84)]),
    ])

# 8.2 verification (double entry)
CHARTS["double-entry"] = dict(
    nodes=[
        N("s", "start", "Start", 170, 20),
        N("i1", "io", "INPUT First", 170, 80, w=130),
        N("i2", "io", "INPUT Second", 170, 144, w=148),
        N("d", "decision", "First = Second?", 170, 222, w=180, h=52),
        N("ok", "io", 'OUTPUT "Verified"', 170, 308, w=135),
        N("bad", "io", 'OUTPUT "Mismatch"', 378, 222, w=150),
        N("stop", "start", "Stop", 170, 378),
    ],
    edges=[
        E("s", "i1"), E("i1", "i2"), E("i2", "d"), E("d", "ok", "Yes"),
        E("d", "bad", "No"), E("ok", "stop"),
        E("bad", "stop", path=[(378, 378)]),
    ])

# 10.1 logic gate evaluation as an algorithm
CHARTS["gates-eval"] = dict(
    nodes=[
        N("s", "start", "Start", 170, 20),
        N("inp", "io", "INPUT A, B, C", 170, 82, w=135),
        N("d1", "decision", "A = 1 AND B = 1?", 170, 164, w=195, h=52),
        N("px", "process", "X \u2190 1", 368, 207, w=95),
        N("d2", "decision", "C = 1?", 170, 252, w=115, h=52),
        N("p3", "process", "X \u2190 0", 170, 338, w=95),
        N("out", "io", "OUTPUT X", 170, 412, w=115),
        N("stop", "start", "Stop", 170, 482),
    ],
    edges=[
        E("s", "inp"), E("inp", "d1"),
        E("d1", "px", "Yes", exit="right", entry="top", path=[(368, 164)]),
        E("d2", "px", "Yes", exit="right", entry="bottom", path=[(368, 252)]),
        E("px", "out", exit="right", entry="right", path=[(455, 207), (455, 412)]),
        E("d1", "d2", "No"), E("d2", "p3", "No"), E("p3", "out"), E("out", "stop"),
    ])

# 11 scenario: nested loops + selection + validation + parallel arrays
CHARTS["scenario-loop"] = dict(
    nodes=[
        N("s", "start", "Start", 150, 20),
        N("init", "process", "Day \u2190 1", 150, 78, w=110),
        N("t", "decision", "Day <= 10?", 150, 152, w=145, h=52),
        N("inp", "io", "INPUT Value", 150, 236, w=130),
        N("d", "decision", "Value >= 0?", 150, 318, w=155, h=52),
        N("bad", "io", 'OUTPUT "Invalid"', 368, 318, w=135),
        N("put", "process", "Meals[Day] \u2190 Value", 150, 406, w=170),
        N("inc", "process", "Day \u2190 Day + 1", 150, 474, w=140),
        N("proc", "process", "Calculate Total, Average,\nHighest, DaysAbove", 150, 558, w=235, h=42),
        N("out", "io", "OUTPUT results", 150, 638, w=150),
        N("stop", "start", "Stop", 150, 708),
    ],
    edges=[
        E("s", "init"), E("init", "t"), E("t", "inp", "Yes"), E("inp", "d"),
        E("d", "put", "Yes"), E("d", "bad", "No"),
        E("bad", "inp", exit="right", entry="right", path=[(435, 318), (430, 318), (430, 236)]),
        E("put", "inc"), E("inc", "t", path=[(58, 474), (58, 152)]),
        E("t", "proc", "No", exit="right", entry="right", path=[(525, 152), (525, 558)]),
        E("proc", "out"), E("out", "stop"),
    ])
