#!/usr/bin/env python3
"""Ch7+13 question bank that looks like cropped past-paper screenshots."""
import io, math, random, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

OUT = "/home/user/p/Ch7_Ch13_Question_Bank.pdf"
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
SERIFB = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANSB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

PAPER = (244, 241, 232)          # aged exam paper
INK = (28, 28, 30)
RULE = (55, 55, 58)
DOT = (90, 90, 95)
RED = (140, 35, 35)
HEADER_BLUE = (25, 45, 85)
DESK = (168, 174, 180)           # scanner/desk behind the crop
SHADOW = (70, 74, 78)

SCALE = 2  # render 2x then downscale = slightly soft "photo"


def font(path, size):
    return ImageFont.truetype(path, size)


def wrap(draw, text, fnt, width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def noise(img, amt=7):
    rnd = random.Random(7)
    px = img.load()
    w, h = img.size
    for _ in range(w * h // 18):
        x, y = rnd.randrange(w), rnd.randrange(h)
        d = rnd.randint(-amt, amt)
        r, g, b = px[x, y][:3]
        px[x, y] = (max(0, min(255, r + d)), max(0, min(255, g + d)), max(0, min(255, b + d)))
    return img


def scanlines(img):
    overlay = Image.new("RGB", img.size, PAPER)
    d = ImageDraw.Draw(overlay)
    for y in range(0, img.size[1], 3):
        d.line((0, y, img.size[0], y), fill=(236, 233, 224))
    return Image.blend(img, overlay, 0.07)


def paper_header(d, w, code, y=8):
    f = font(SANS, 11)
    fb = font(SANSB, 11)
    d.text((14, y), code, font=f, fill=(90, 90, 95))
    d.text((w - 14, y), "© UCLES", font=f, fill=(90, 90, 95), anchor="ra")
    d.line((14, y + 16, w - 14, y + 16), fill=RULE, width=1)


def dotted(d, x0, x1, y, n=1):
    f = font(SERIF, 13)
    gap = d.textlength(".", font=f) or 4
    count = max(8, int((x1 - x0) / gap))
    dots = "." * count
    for i in range(n):
        yy = y + i * 16
        d.text((x0, yy - 11), dots, font=f, fill=DOT)


def draw_path(d, x, y):
    labs = ["root hair", "cortex", "xylem", "mesophyll"]
    for i, lab in enumerate(labs):
        bx = x + i * 92
        d.rounded_rectangle((bx, y, bx + 78, y + 28), 3, outline=INK, width=1)
        d.text((bx + 39, y + 14), lab, font=font(SERIF, 12), fill=INK, anchor="mm")
        if i < 3:
            d.line((bx + 80, y + 14, bx + 90, y + 14), fill=INK, width=1)
            d.polygon([(bx + 90, y + 14), (bx + 84, y + 10), (bx + 84, y + 18)], fill=INK)
    return y + 40


def draw_leaf(d, x, y):
    # xylem | mesophyll | air space | stoma
    d.rectangle((x, y, x + 28, y + 70), outline=INK, fill=(176, 210, 230))
    d.rectangle((x + 28, y, x + 110, y + 70), outline=INK, fill=(198, 220, 190))
    d.rectangle((x + 118, y + 8, x + 175, y + 62), outline=INK, fill=(232, 240, 236))
    d.ellipse((x + 172, y + 8, x + 198, y + 32), outline=INK, fill=(240, 230, 160))
    d.ellipse((x + 172, y + 40, x + 198, y + 64), outline=INK, fill=(240, 230, 160))
    d.line((x + 198, y + 32, x + 198, y + 40), fill=INK, width=2)
    # arrows
    d.line((x + 50, y + 35, x + 100, y + 35), fill=RED, width=2)
    d.line((x + 110, y + 40, x + 130, y + 40), fill=RED, width=2)
    d.line((x + 198, y + 36, x + 230, y + 36), fill=RED, width=2)
    f = font(SERIFB, 12)
    d.text((x + 70, y + 22), "1", font=f, fill=RED)
    d.text((x + 118, y + 26), "2", font=f, fill=RED)
    d.text((x + 210, y + 22), "3", font=f, fill=RED)
    fs = font(SERIF, 11)
    d.text((x + 2, y + 76), "xylem", font=fs, fill=INK)
    d.text((x + 48, y + 76), "mesophyll", font=fs, fill=INK)
    d.text((x + 124, y + 76), "air space", font=fs, fill=INK)
    d.text((x + 200, y + 76), "stoma", font=fs, fill=INK)
    d.text((x + 240, y + 8), "Fig. 6.1", font=font(SERIFB, 11), fill=INK)
    return y + 96


def draw_ts(d, x, y):
    # stem
    cx, cy, r = x + 70, y + 62, 52
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=INK, width=2, fill=(250, 248, 242))
    d.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), outline=INK, fill=(230, 228, 220))
    for ang in (18, 90, 162, 234, 306):
        a = math.radians(ang)
        bx, by = cx + 34 * math.cos(a), cy + 34 * math.sin(a)
        d.ellipse((bx - 11, by - 7, bx + 11, by + 7), outline=INK, fill=(230, 170, 170))
        d.ellipse((bx - 5 + -4 * math.cos(a), by - 5 + -4 * math.sin(a),
                   bx + 5 + -4 * math.cos(a), by + 5 + -4 * math.sin(a)),
                  outline=INK, fill=(150, 190, 220))
    d.text((cx, y + 128), "Fig. 20.1  stem TS", font=font(SERIFB, 12), fill=INK, anchor="ma")
    # root
    cx2, cy2 = x + 230, y + 62
    d.ellipse((cx2 - r, cy2 - r, cx2 + r, cy2 + r), outline=INK, width=2, fill=(250, 248, 242))
    pts = []
    for i in range(8):
        a = math.radians(-90 + i * 45)
        rr = 28 if i % 2 == 0 else 11
        pts.append((cx2 + rr * math.cos(a), cy2 + rr * math.sin(a)))
    d.polygon(pts, outline=INK, fill=(150, 190, 220))
    for i in range(4):
        a = math.radians(-45 + i * 90)
        d.ellipse((cx2 + 18 * math.cos(a) - 6, cy2 + 18 * math.sin(a) - 6,
                   cx2 + 18 * math.cos(a) + 6, cy2 + 18 * math.sin(a) + 6),
                  outline=INK, fill=(230, 170, 170))
    d.text((cx2, y + 128), "Fig. 20.2  root TS", font=font(SERIFB, 12), fill=INK, anchor="ma")
    return y + 148


def draw_urinary(d, x, y):
    d.rounded_rectangle((x + 70, y + 8, x + 118, y + 40), 10, outline=INK, fill=(190, 220, 235))
    d.rounded_rectangle((x + 170, y + 8, x + 218, y + 40), 10, outline=INK, fill=(190, 220, 235))
    d.rounded_rectangle((x + 118, y + 58, x + 170, y + 88), 4, outline=INK, fill=(235, 220, 140))
    d.line((x + 94, y + 40, x + 130, y + 58), fill=INK, width=2)
    d.line((x + 194, y + 40, x + 158, y + 58), fill=INK, width=2)
    d.line((x + 144, y + 88, x + 144, y + 112), fill=INK, width=2)
    f = font(SERIF, 12)
    d.text((x + 94, y), "A", font=font(SERIFB, 12), fill=INK, anchor="ma")
    d.text((x + 194, y), "kidney", font=f, fill=INK, anchor="ma")
    d.text((x + 40, y + 48), "B", font=font(SERIFB, 12), fill=INK)
    d.text((x + 178, y + 70), "C", font=font(SERIFB, 12), fill=INK)
    d.text((x + 152, y + 112), "D", font=font(SERIFB, 12), fill=INK)
    d.text((x + 240, y + 8), "Fig. 30.1", font=font(SERIFB, 11), fill=INK)
    return y + 128


def draw_nephron(d, x, y):
    d.ellipse((x + 20, y + 18, x + 88, y + 86), outline=INK, width=2)
    d.ellipse((x + 34, y + 32, x + 74, y + 72), outline=INK, fill=(220, 150, 150))
    d.rectangle((x + 70, y + 40, x + 92, y + 64), fill=PAPER)
    d.line((x + 80, y + 52, x + 108, y + 52), fill=INK, width=2)
    d.line((x + 108, y + 52, x + 108, y + 100), fill=INK, width=2)
    d.line((x + 108, y + 100, x + 150, y + 100), fill=INK, width=2)
    d.line((x + 150, y + 100, x + 150, y + 52), fill=INK, width=2)
    d.line((x + 150, y + 52, x + 186, y + 52), fill=INK, width=2)
    d.line((x + 186, y + 52, x + 186, y + 18), fill=INK, width=2)
    d.line((x + 8, y + 18, x + 40, y + 40), fill=RED, width=2)
    d.line((x + 70, y + 40, x + 100, y + 16), fill=RED, width=2)
    f, fb = font(SERIF, 11), font(SERIFB, 12)
    d.text((x + 8, y + 2), "blood in", font=f, fill=RED)
    d.text((x + 102, y + 2), "blood out", font=f, fill=RED)
    d.text((x, y + 88), "P", font=fb, fill=INK)
    d.text((x + 44, y + 90), "glomerulus", font=f, fill=INK, anchor="ma")
    d.text((x + 128, y + 108), "Q", font=fb, fill=INK)
    d.text((x + 198, y + 14), "R", font=fb, fill=INK)
    d.text((x + 250, y + 8), "Fig. 32.1", font=fb, fill=INK)
    return y + 128


DIAG = {
    "path": draw_path,
    "leaf": draw_leaf,
    "ts": draw_ts,
    "urinary": draw_urinary,
    "nephron": draw_nephron,
}

# (paper_code, parts)  parts = list of (label, text, marks, diagram_or_None, dotted_lines)
# label '' means continuation
QUESTIONS = [
    ("5090/21/M/J/24", [
        ("1  (a)", "Give three structural features of a root hair cell and, for each, state how it helps water or ion uptake.", 6, None, 4),
        ("(b)", "Name the process by which water enters a root hair, and the process by which nitrate ions enter when their concentration is higher inside the cell than in the soil.", 2, None, 2),
    ]),
    ("5090/21/O/N/23", [
        ("2", "A chemical stops aerobic respiration in roots. Nitrate uptake slows; water uptake does not. Explain both observations.", 4, None, 4),
    ]),
    ("5090/22/M/J/24", [
        ("3  (a)", "Name, in the correct order, the four tissues / cells that water passes through from soil water to a leaf mesophyll cell.", 4, "path", 2),
        ("(b)", "Name the tissue that transports mineral ions from the root to the leaf.", 1, None, 1),
    ]),
    ("5090/21/M/J/17", [
        ("4  (a)", "A leafy shoot is cut under water and stood in eosin. A transverse section of the stem is cut after 1 hour. Which tissue is stained?", 1, None, 1),
        ("(b)", "Explain why the shoot is cut under water.", 1, None, 1),
        ("(c)", "Explain why the dye moves up the stem.", 1, None, 1),
    ]),
    ("5090/21/O/N/21", [
        ("5", "Define transpiration.", 2, None, 2),
    ]),
    ("5090/21/O/N/22", [
        ("6", "Fig. 6.1 shows water moving through part of a transpiring leaf. For each of arrows 1, 2 and 3, name the process taking place and define it.", 9, "leaf", 6),
    ]),
    ("5090/21/M/J/15", [
        ("7", "Explain how each of the following changes the rate of transpiration: (i) higher wind speed  (ii) higher temperature  (iii) higher humidity  (iv) higher light intensity.", 8, None, 6),
    ]),
    ("5090/21/O/N/22", [
        ("8", "Leaves from two species transpire at different rates in the same environmental conditions. Suggest three structural differences in the lower surface of these leaves which might produce the difference. Give a reason for each.", 6, None, 5),
    ]),
    ("5090/22/O/N/15", [
        ("9  (a)", "Explain how wilting occurs in a plant.", 4, None, 3),
        ("(b)", "A plant is pulled from the soil and replanted. It wilts for several days and then recovers. Explain both stages.", 4, None, 3),
    ]),
    ("5090/21/M/J/20", [
        ("10", "Bacteria reproduce inside a plant stem and block the xylem. The leaves wilt and become yellow. Explain both of these symptoms.", 5, None, 4),
    ]),
    ("5090/21/M/J/22", [
        ("11", "Softwood cuttings have their lower leaves removed and are covered with a transparent bag until roots develop. Explain how each of these two steps helps to prevent wilting.", 4, None, 4),
    ]),
    ("5090/22/O/N/25", [
        ("12", "Explain the mechanism by which water moves upwards in the xylem.", 5, None, 4),
    ]),
    ("5090/11/M/J/22", [
        ("13", "What is the main cause of water moving up to the leaves in xylem vessels? State the correct idea and identify three incorrect ideas that are often given as options.", 2, None, 3),
    ]),
    ("5090/11/M/J/24", [
        ("14  (a)", "A potted plant is watered and the pot is placed in a plastic bag. Mass at 09:00 = 1276 g. Mass at 15:00 = 1252 g. Calculate the mean rate of transpiration over the six hours. Show your working.", 2, None, 2),
        ("(b)", "Explain why the pot was placed in a plastic bag.", 1, None, 1),
    ]),
    ("5090/11/M/J/23", [
        ("15", "State the combination of humidity, temperature, wind and light intensity that gives the highest rate of transpiration.", 1, None, 1),
    ]),
    ("5090/22/M/J/25", [
        ("16", "Transpiration is both necessary for plants and a problem for plants. Discuss this statement.", 4, None, 4),
    ]),
    ("5090/22/M/J/23", [
        ("17  (a)", "Define translocation.", 3, None, 2),
        ("(b)", "Give one example of a source and one example of a sink.", 2, None, 2),
        ("(c)", "State one way in which the direction of translocation differs from transport in the xylem.", 1, None, 1),
    ]),
    ("5090/21/O/N/12", [
        ("18", "Aphids feed by piercing one plant tissue. Name this tissue and explain why it is more suitable for this purpose than xylem.", 3, None, 3),
    ]),
    ("5090/22/M/J/24", [
        ("19", "When flowers are cut for display, the leaves are removed and the stems are placed in a sucrose solution. Explain the benefit of providing sucrose to the cut flowers.", 3, None, 3),
    ]),
    ("5090/21/M/J/16", [
        ("20", "Fig. 20.1 shows a TS of a non-woody dicotyledonous stem. Fig. 20.2 shows a TS of a non-woody dicotyledonous root. For each figure, state the positions of the xylem, the phloem and the cortex.", 6, "ts", 4),
    ]),
    ("5090/21/M/J/22", [
        ("21  (a)", "State two functions of xylem vessels in a young stem.", 2, None, 2),
        ("(b)", "For each function, explain one way in which xylem structure is adapted for that function.", 4, None, 4),
    ]),
    ("5090/22/M/J/23", [
        ("22", "Relate each of the following features of xylem vessels to their function: (i) thick walls with lignin  (ii) no cell contents  (iii) cells joined end-to-end with no cross walls.", 6, None, 5),
    ]),
    ("5090/22/M/J/12", [
        ("23", "List three structural changes that occur in young plant cells as they develop into xylem tissue.", 3, None, 3),
    ]),
    ("5090/21/O/N/14", [
        ("24", "Describe two similarities and two differences in the structure or function of root hairs and villi.", 4, None, 4),
    ]),
    ("5090/21/O/N/15", [
        ("25", "Define excretion.", 3, None, 2),
    ]),
    ("5090/22/M/J/12", [
        ("26", "Explain why egestion is not excretion.", 2, None, 2),
    ]),
    ("5090/12/M/J/24", [
        ("27", "Which of the following is an example of excretion? Explain why the others are not.  • release of a hormone into the blood  • removal of carbon dioxide from the lungs  • removal of undigested food from the digestive system  • release of water from the sweat glands", 3, None, 4),
    ]),
    ("5090/21/O/N/19", [
        ("28", "Carbon dioxide is a waste product of metabolism. State where it is produced and how it is excreted.", 2, None, 2),
    ]),
    ("5090/22/M/J/24", [
        ("29  (a)", "Name the organ in which urea is produced.", 1, None, 1),
        ("(b)", "State what urea is produced from.", 1, None, 1),
        ("(c)", "Explain why urea must be excreted.", 1, None, 1),
    ]),
    ("5090/21/O/N/22", [
        ("30", "Fig. 30.1 shows the human urinary system. Identify structures A to D and state the function of each.", 8, "urinary", 5),
    ]),
    ("5090/22/M/J/22", [
        ("31", "Describe two similarities or differences between the ureter and the urethra.", 4, None, 3),
    ]),
    ("5090/22/M/J/24", [
        ("32", "Fig. 32.1 is a simplified diagram of a nephron. Identify the structures labelled P, Q and R.", 3, "nephron", 3),
    ]),
    ("5090/22/M/J/24", [
        ("33  (a)", "Outline the role of the glomerulus. Name four substances filtered from the blood.", 3, None, 2),
        ("(b)", "State what is reabsorbed by the nephron, and how much of each (all / some / most).", 3, None, 2),
        ("(c)", "Name three components of the urine that is formed.", 2, None, 2),
    ]),
    ("5090/22/M/J/24", [
        ("34", "Fluid leaving the collecting duct of a healthy person contains glucose at concentration 0.00 and protein at concentration 0.00. Use your knowledge of the function of a nephron to explain each of these zeros.", 5, None, 5),
    ]),
    ("5090/11/M/J/25", [
        ("35", "The table shows amounts entering the kidneys in the blood and leaving in the urine in one day.  water 150 dm³ → 1.5 dm³     glucose 150 g → 0 g     urea 50 g → 30 g.  Calculate the percentage of each substance that is reabsorbed.", 3, None, 3),
    ]),
    ("5090/11/M/J/23", [
        ("36", "Compare the blood in the renal artery with the blood in the renal vein with respect to urea, oxygen and carbon dioxide.", 3, None, 3),
    ]),
    ("5090/11/M/J/21", [
        ("37", "Which blood vessel has the highest concentration of urea, and which has the lowest: hepatic portal vein, hepatic vein, renal artery, renal vein? Explain your answers.", 3, None, 3),
    ]),
    ("5090/21/O/N/25", [
        ("38", "A person eats more protein than usual. Explain why the concentration of urea in the urine rises.", 3, None, 3),
    ]),
    ("5090/22/M/J/24", [
        ("39", "A person drinks a large volume of water. State and explain two changes in the urine.", 3, None, 3),
    ]),
    ("5090/12/M/J/25", [
        ("40", "Which of the following would not be present in the urine of a healthy person with a normal diet: glucose, salts, urea, water?", 1, None, 1),
    ]),
    ("5090/11/M/J/24", [
        ("41  (a)", "Name the process by which amino acids pass from the ileum into the blood.", 1, None, 1),
        ("(b)", "Name the process of converting amino acids to proteins in the liver.", 1, None, 1),
        ("(c)", "Name the blood vessel that carries amino acids from the small intestine to the liver.", 1, None, 1),
        ("(d)", "Name the process in the liver that produces urea from excess amino acids.", 1, None, 1),
    ]),
    ("5090/21/O/N/16", [
        ("42", "Define deamination.", 2, None, 2),
    ]),
    ("5090/12/M/J/24", [
        ("43", "The diagram of an amino acid molecule is not shown. Which part of the molecule is removed and used to make urea: the –NH₂ group, the R group, or the –COOH group?", 1, None, 1),
    ]),
    ("5090/21/O/N/19", [
        ("44", "Outline the path of the nitrogen from an absorbed amino acid until it leaves the body as urea.", 6, None, 5),
    ]),
]


def render_snippet(code, parts, seed):
    """Paint one exam-paper crop at 2x, return RGB image."""
    W = 720
    # measure height
    probe = Image.new("RGB", (W, 40), PAPER)
    pd = ImageDraw.Draw(probe)
    fb, fs = font(SERIFB, 15), font(SERIF, 15)
    fm = font(SERIF, 13)
    y = 36
    for label, text, marks, diag, ndot in parts:
        body = f"{label}  {text}"
        for ln in wrap(pd, body, fs if not label[:1].isdigit() else fb, W - 88):
            y += 20
        y += 6
        if diag:
            y += {"path": 48, "leaf": 104, "ts": 156, "urinary": 136, "nephron": 136}[diag]
        y += ndot * 16 + 10
    y += 28
    H = y + 8
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    # faint margin rule
    d.line((8, 0, 8, H), fill=(210, 205, 195), width=2)
    paper_header(d, W, code, y=6)
    yy = 36
    for label, text, marks, diag, ndot in parts:
        # hanging indent: number bold
        lab = label + "  "
        lw = d.textlength(lab, font=fb)
        body_lines = wrap(d, text, fs, W - 92 - (lw if True else 0))
        # first line sits after the bold label
        first_w = W - 36 - lw
        first = wrap(d, text, fs, first_w)
        d.text((16, yy), lab, font=fb, fill=INK)
        if first:
            d.text((16 + lw, yy), first[0], font=fs, fill=INK)
        yy += 20
        rest = " ".join(text.split()[len(first[0].split()):]) if first else text
        for ln in wrap(d, rest, fs, W - 36) if rest else []:
            d.text((16, yy), ln, font=fs, fill=INK)
            yy += 20
        # marks
        d.text((W - 16, yy - 18), f"[{marks}]", font=fm, fill=INK, anchor="ra")
        yy += 4
        if diag:
            yy = DIAG[diag](d, 28, yy)
        dotted(d, 16, W - 70, yy + 12, ndot)
        yy += ndot * 16 + 10
    # footer
    d.line((14, H - 22, W - 14, H - 22), fill=RULE, width=1)
    d.text((14, H - 18), code, font=font(SANS, 10), fill=(90, 90, 95))
    d.text((W - 14, H - 18), "[Turn over]", font=font(SANS, 10), fill=(90, 90, 95), anchor="ra")
    img = scanlines(img)
    img = noise(img, 6)
    # slight contrast like a phone photo of a paper
    img = ImageEnhance.Contrast(img).enhance(0.96)
    img = ImageEnhance.Color(img).enhance(0.92)
    img = ImageEnhance.Sharpness(img).enhance(0.85)
    # tiny rotation
    rnd = random.Random(seed)
    ang = rnd.uniform(-0.55, 0.55)
    img = img.rotate(ang, resample=Image.BICUBIC, expand=True, fillcolor=DESK)
    # jpeg artefacts
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=78, optimize=True)
    buf.seek(0)
    img = Image.open(buf).convert("RGB")
    return img


def add_shadow(crop):
    """Drop shadow so it reads as a floating screenshot."""
    pad = 18
    blob = Image.new("L", (crop.size[0] + pad * 2, crop.size[1] + pad * 2), 0)
    bd = ImageDraw.Draw(blob)
    bd.rectangle((pad + 6, pad + 8, pad + crop.size[0] + 6, pad + crop.size[1] + 8), fill=160)
    blob = blob.filter(ImageFilter.GaussianBlur(7))
    desk = Image.new("RGB", blob.size, DESK)
    sh = Image.composite(Image.new("RGB", blob.size, SHADOW), desk, blob)
    sh.paste(crop, (pad, pad))
    # 1 px screenshot border
    d = ImageDraw.Draw(sh)
    d.rectangle((pad - 1, pad - 1, pad + crop.size[0], pad + crop.size[1]), outline=(60, 60, 62), width=1)
    return sh


MS = [
    ("1", "(a) long/projection/finger-like → large SA ; large SA → absorb water and ions ; thin wall → short distance ; (partially permeable) membrane → osmosis of water / AT of ions ; mitochondria/living → ATP for ions ; vacuole → store / turgor ; [max 6]\n(b) water: osmosis (A diffusion) ; ions: active transport ; [2]\nR water by AT ; R ions by osmosis ; R partially permeable cell wall"),
    ("2", "ions need AT / against gradient ; AT needs energy from respiration ; chemical stops respiration → slower ion uptake ; water by osmosis / does not need energy ; [4]"),
    ("3", "(a) root hair (cell) ; (root) cortex (cell) ; xylem (vessel) ; palisade/spongy mesophyll (cell) ; this order [4]\n(b) xylem ; [1]  R phloem"),
    ("4", "(a) xylem ; (b) prevent air lock / air bubbles in xylem ; (c) transpiration pull / evaporation from leaves draws water + dye up ; [3]"),
    ("5", "loss of water ; as vapour / evaporation ; from leaves ; through stomata ; [max 2]\nR evaporation from the epidermis as the main cause of the pull"),
    ("6", "1 osmosis ; water higher → lower water potential across a partially permeable membrane ;\n2 evaporation ; liquid → water vapour (from mesophyll wall/film) ;\n3 diffusion ; vapour high → lower concentration / out through stomata ; [9]"),
    ("7", "wind ↑: vapour blown away ; humidity around leaf falls ; steeper diffusion gradient ;\ntemp ↑: more KE ; faster evaporation ;\nhumidity ↑ rate ↓: smaller vapour-concentration difference ; shallower gradient ;  R stomata as the humidity explanation ;\nlight ↑: stomata open/wider ; [8]"),
    ("8", "leaf SA ; stomata number/density/size ; stomata upper vs lower ; cuticle thickness ; sunken stomata/hairs/rolled leaves trap humid air ; [max 6 — feature + reason]"),
    ("9", "(a) water lost (transpiration) faster than gained ; cells lose turgor / become flaccid ; no longer support plant ; [4]  Prefer flaccid (plasmolysed R on an older wilting MS).\n(b) wilt: root hairs damaged ; less water absorbed ; recover: hairs regrow ; cells turgid again ; [4]"),
    ("10", "water lost cannot be replaced / cannot pass up stem ; lose turgor → wilt ; Mg cannot reach leaves ; less chlorophyll → yellow ; less photosynthesis ; [5]"),
    ("11", "remove leaves: less SA/fewer stomata → less transpiration ; bag: higher humidity ; smaller diffusion gradient ; less water loss ; [4]"),
    ("12", "evaporates/transpires from leaves ; lowers leaf water potential ; water up xylem ; transpiration pull ; forces of attraction between water molecules / column held together ; [max 5]\nR root pressure/capillarity as the main mechanism ; R active transport"),
    ("13", "correct: evaporation from the walls of the mesophyll cells ;\nwrong: active transport ; evaporation from the epidermis ; use of water in photosynthesis ; [2]"),
    ("14", "(a) 1276 − 1252 = 24 g in 6 h → 4 g/h ; [2]  (b) so mass loss is leaf transpiration, not soil evaporation ; [1]"),
    ("15", "low humidity + high temperature + wind + high light/day ; [1]"),
    ("16", "necessary: water for photosynthesis ; ions to leaves ; turgor ; cools leaf ;\nproblem: too much loss → wilt/death ; close stomata → less CO2 → slower photosynthesis ; [4]"),
    ("17", "(a) sucrose and amino acids ; in phloem ; source (produce/release) → sink (use/store) ; in solution ; [max 3]  R glucose/food\n(b) source = leaf (or storage releasing) ; sink = root/meristem/fruit ; [2]\n(c) phloem bidirectional ; xylem up only ; [1]"),
    ("18", "phloem ; sucrose + amino acids ; in solution ; not lignified/softer ; [max 3]"),
    ("19", "cut flowers cannot photosynthesise ; sucrose in phloem ; respiration/energy ; last longer ; [max 3]"),
    ("20", "STEM: bundles in a ring towards outside ; xylem inner ; phloem outer ; cortex between epidermis and ring ;\nROOT: xylem in centre (star) ; phloem between arms ; wide cortex ; [6]"),
    ("21", "(a) transport water and mineral ions ; support ; [2]  R sugars\n(b) transport ↔ hollow / no cytoplasm / no end walls / continuous tube ; support ↔ lignified/thick walls ; pair them ; [4]"),
    ("22", "(i) lignin → support / stop collapse ;\n(ii) no contents → hollow / free flow ;\n(iii) no cross walls → continuous tube / uninterrupted column ; [6]"),
    ("23", "elongation ; loss of contents / death / hollow ; loss of end walls ; add lignin ; [max 3]"),
    ("24", "same: elongated/large SA ; absorption ; AT/diffusion ; water/ions ;\ndiff: hair = one cell + wall, from soil ; villus = multicellular + vessels, from gut ; [4]"),
    ("25", "removal from the organism ; of toxic/poisonous materials ; and waste products of metabolism ; [3]\nR harmful ; R salts as the definition"),
    ("26", "egestion = undigested food / fibre/cellulose ; not from metabolism ; [2]"),
    ("27", "excretion = CO2 from lungs ; hormone = secretion ; faeces = egestion ; sweat = cooling/homeostasis ; [3]"),
    ("28", "waste of (aerobic) respiration ; excreted through lungs / exhaled / blood → alveoli ; [2]"),
    ("29", "(a) liver ; (b) breakdown of excess amino acids ; (c) urea is toxic ; [3]  R kidney produces urea"),
    ("30", "A kidney: removes urea + excess salts + water from blood as urine ;\nB ureter: urine kidney → bladder ;\nC bladder: stores urine ;\nD urethra: urine bladder → out ; R ‘just urea’ ; male urethra also sperm ; [8]"),
    ("31", "both carry urine ; ureter kidney → bladder ; urethra bladder → out ; male urethra also sperm ; [4]"),
    ("32", "P Bowman's capsule ; Q loop of Henle ; R collecting duct ; [3]"),
    ("33", "(a) filtration ; water, glucose, urea, ions ; into Bowman's ; [3]\n(b) all glucose ; some ions ; most water ; back into blood ; [3]\n(c) urea ; excess water ; excess ions ; [2]"),
    ("34", "glucose: filtered into Bowman's ; then all reabsorbed ;\nprotein: too large ; not filtered ; [5]"),
    ("35", "water 99% ; glucose 100% ; urea 40% ; [3]  R quoting amount (148.5) as a %"),
    ("36", "renal vein: less urea ; less oxygen ; more carbon dioxide ; [3]"),
    ("37", "highest = hepatic vein (liver just made it) ; lowest = renal vein (kidney just removed it) ; [3]"),
    ("38", "more amino acids deaminated (liver) ; more urea formed ; more urea filtered into urine ; [3]"),
    ("39", "higher urine volume ; lower ion concentration / more dilute ; homeostasis of water in blood ; [3]"),
    ("40", "glucose ; [1]"),
    ("41", "(a) absorption ; (b) assimilation ; (c) hepatic portal vein ; (d) deamination ; [4]"),
    ("42", "removal of the nitrogen-containing part (–NH2) of amino acids ; formation of urea ; [2]"),
    ("43", "the nitrogen-containing / –NH2 group ; [1]"),
    ("44", "absorbed in villi ; hepatic portal vein ; liver ; deamination ; urea in renal artery ; kidney filters ; urine ; ureter → bladder → urethra ; [max 6]"),
]


def render_ms_pages():
    """Official-looking MS pages as screenshot images."""
    pages = []
    W, H = 720, 1020
    y0 = 0

    def newpage():
        im = Image.new("RGB", (W, H), (248, 248, 250))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, W, 42), fill=(40, 55, 80))
        d.text((14, 14), "Cambridge O Level  –  Mark Scheme  PUBLISHED", font=font(SANSB, 13), fill=(255, 255, 255))
        d.text((W - 14, 16), "5090", font=font(SANS, 11), fill=(200, 210, 220), anchor="ra")
        d.line((14, 52, W - 14, 52), fill=(40, 55, 80), width=1)
        d.text((14, 58), "Question", font=font(SANSB, 10), fill=(40, 55, 80))
        d.text((90, 58), "Answer", font=font(SANSB, 10), fill=(40, 55, 80))
        d.text((W - 14, 58), "Marks / guidance", font=font(SANSB, 10), fill=(40, 55, 80), anchor="ra")
        d.line((14, 74, W - 14, 74), fill=(180, 185, 190), width=1)
        return im, d, 82

    im, d, y = newpage()
    fb, fs = font(SANSB, 11), font(SANS, 11)
    for qid, ans in MS:
        # estimate height
        lines = []
        for para in ans.split("\n"):
            lines.extend(wrap(d, para, fs, W - 110) or [""])
        need = 8 + 14 * len(lines) + 8
        if y + need > H - 28:
            pages.append(im)
            im, d, y = newpage()
        d.text((20, y), qid, font=fb, fill=(40, 55, 80))
        yy = y
        for para in ans.split("\n"):
            fnt = font(SANS, 11)
            fill = (140, 40, 40) if para.startswith("R ") else (30, 30, 32)
            for ln in wrap(d, para, fnt, W - 110):
                d.text((90, yy), ln, font=fnt, fill=fill)
                yy += 14
        y = yy + 8
        d.line((14, y - 4, W - 14, y - 4), fill=(220, 222, 225), width=1)
    pages.append(im)
    return pages


def layout_pages(crops):
    """Pack screenshot cards onto A4 desk pages."""
    # A4 at 140 dpi
    PW, PH = 827, 1169
    margin = 22
    gap = 14
    pages = []
    x = margin
    y = margin + 28
    page = Image.new("RGB", (PW, PH), DESK)
    pd = ImageDraw.Draw(page)
    pd.text((margin, 8), "screenshots  ·  do the questions first  ·  MS after the crops",
            font=font(SANS, 14), fill=(70, 74, 78))

    def flush():
        nonlocal page, pd, x, y
        pages.append(page)
        page = Image.new("RGB", (PW, PH), DESK)
        pd = ImageDraw.Draw(page)
        pd.text((margin, 8), "screenshots  ·  do the questions first  ·  MS after the crops",
                font=font(SANS, 14), fill=(70, 74, 78))
        x, y = margin, margin + 28

    max_w = PW - 2 * margin
    for crop in crops:
        # fit width
        if crop.size[0] > max_w:
            nh = int(crop.size[1] * max_w / crop.size[0])
            crop = crop.resize((max_w, nh), Image.LANCZOS)
        card = add_shadow(crop)
        if y + card.size[1] > PH - 18:
            flush()
        page.paste(card, (margin + (max_w - card.size[0]) // 2, y))
        y += card.size[1] + gap
    pages.append(page)
    return pages


def to_pdf(q_pages, ms_pages):
    c = pdfcanvas.Canvas(OUT, pagesize=A4)
    aw, ah = A4
    def blit(im, jpeg_q=72):
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "JPEG", quality=jpeg_q, optimize=True)
        buf.seek(0)
        c.drawImage(ImageReader(buf), 0, 0, width=aw, height=ah)
        c.showPage()
    for im in q_pages:
        blit(im, 74)
    for im in ms_pages:
        # MS also as a slightly rotated screenshot on desk
        rnd_im = im
        rnd_im = ImageOps.expand(rnd_im, border=10, fill=(248, 248, 250))
        rnd_im = scanlines(rnd_im)
        rnd_im = noise(rnd_im, 4)
        card = add_shadow(rnd_im)
        # fit on desk page
        desk = Image.new("RGB", (827, 1169), DESK)
        # scale card to page
        max_w, max_h = 827 - 36, 1169 - 36
        sc = min(max_w / card.size[0], max_h / card.size[1])
        nw, nh = int(card.size[0] * sc), int(card.size[1] * sc)
        card = card.resize((nw, nh), Image.LANCZOS)
        desk.paste(card, ((827 - nw) // 2, (1169 - nh) // 2))
        blit(desk, 76)
    c.save()


def main():
    random.seed(5090)
    crops = []
    for i, (code, parts) in enumerate(QUESTIONS):
        crops.append(render_snippet(code, parts, seed=100 + i))
        print("crop", i + 1, crops[-1].size)
    q_pages = layout_pages(crops)
    ms_pages = render_ms_pages()
    to_pdf(q_pages, ms_pages)
    print("wrote", OUT, "qpages", len(q_pages), "mspages", len(ms_pages),
          "bytes", os.path.getsize(OUT))


if __name__ == "__main__":
    main()
