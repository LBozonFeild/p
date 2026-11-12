"""Vector flowchart renderer for the study guide.

Draws proper flowchart shapes (stadium terminators, rectangles, diamonds,
parallelograms, double-barred subroutine boxes) as vector PDF graphics with
real, copy-pasteable text labels. Dark theme to match the guide.

A chart spec is:  dict(nodes=[...], edges=[...])
  node: dict(id, type, label, x, y[, w, h])   type: start/stop, process,
        io, decision, sub, label (plain text, no box)
  edge: dict(frm, to[, label, path, exit, entry])
        path = list of intermediate waypoints (x, y) in chart space,
        y increasing downward. exit/entry override anchor sides
        ('top', 'bottom', 'left', 'right').
"""
import math

from reportlab.lib import colors
from reportlab.platypus import Flowable

FONT = "DejaVu"
FSIZE = 7.2
LEADING = 9.6
TEXT = colors.HexColor("#e8e8e8")
STROKE = colors.HexColor("#c8c8c8")
EDGE = colors.HexColor("#a8a8a8")
FILL = colors.HexColor("#161616")

CHARW = 4.55   # rough width of one character at FSIZE (sizing estimate)
PAD = 10       # padding around the drawing


def _label_lines(label):
    return label.split("\n") if label else []


def _auto_size(node):
    t = node["type"]
    lines = _label_lines(node.get("label", ""))
    maxc = max((len(l) for l in lines), default=6)
    n = max(len(lines), 1)
    if t == "label":
        w, h = maxc * 4.2 + 8, 12
    elif t in ("start", "stop"):
        w, h = maxc * CHARW + 32, 25
    elif t == "decision":
        w, h = maxc * 5.1 + 42, 52 + 9 * (n - 1)
    elif t == "io":
        w, h = maxc * CHARW + 40, 16 + LEADING * n
    elif t == "sub":
        w, h = maxc * CHARW + 30, 15 + LEADING * n
    else:  # process
        w, h = maxc * CHARW + 24, 14 + LEADING * n
    return node.get("w", w), node.get("h", h)


def _anchor(node, side):
    x, y = node["_x"], node["_y"]
    w, h = node["_w"], node["_h"]
    if side == "top":
        return (x, y - h / 2)
    if side == "bottom":
        return (x, y + h / 2)
    if side == "left":
        return (x - w / 2, y)
    return (x + w / 2, y)   # right


_SIDES = ("top", "bottom", "left", "right")


def _nearest_side(node, point, sides=_SIDES):
    best, bestd = None, None
    for s in sides:
        ax, ay = _anchor(node, s)
        d = (ax - point[0]) ** 2 + (ay - point[1]) ** 2
        if bestd is None or d < bestd:
            best, bestd = s, d
    return best


class Flowchart(Flowable):
    def __init__(self, spec, max_width=503, max_height=680, label="flowchart"):
        super().__init__()
        self.spec = spec
        self.label = label
        self._prepare(max_width, max_height)

    # ------------------------------------------------------------ layout
    def _prepare(self, max_width, max_height):
        nodes = {}
        for n in self.spec["nodes"]:
            n = dict(n)
            n["_w"], n["_h"] = _auto_size(n)
            n["_x"], n["_y"] = n["x"], n["y"]
            nodes[n["id"]] = n
        self.nodes = nodes

        edges = []
        pts_all = []
        for e in self.spec["edges"]:
            frm, to = nodes[e["frm"]], nodes[e["to"]]
            path = e.get("path") or []
            if "exit" in e:
                exit_side = e["exit"]
            else:
                target = path[0] if path else (to["_x"], to["_y"])
                exit_side = _nearest_side(frm, target)
            if "entry" in e:
                entry_side = e["entry"]
            else:
                source = path[-1] if path else (frm["_x"], frm["_y"])
                entry_side = _nearest_side(to, source)
            pts = [_anchor(frm, exit_side)] + [tuple(p) for p in path]
            last = _anchor(to, entry_side)
            if pts[-1] != last:
                pts.append(last)
            edges.append((e, pts))
            pts_all.extend(pts)
        self.edges = edges

        xs = [n["_x"] - n["_w"] / 2 for n in nodes.values()] + \
             [n["_x"] + n["_w"] / 2 for n in nodes.values()] + \
             [p[0] for p in pts_all]
        ys = [n["_y"] - n["_h"] / 2 for n in nodes.values()] + \
             [n["_y"] + n["_h"] / 2 for n in nodes.values()] + \
             [p[1] for p in pts_all]
        self.minx, self.maxy = min(xs), max(ys)
        self.miny = min(ys)
        bw = max(xs) - min(xs) + 2 * PAD
        bh = self.maxy - self.miny + 2 * PAD
        self.scale = min(max_width / bw, max_height / bh, 1.15)
        self.width = bw * self.scale
        self.height = bh * self.scale

    # -------------------------------------------------------- primitives
    def _tx(self, x):
        return (x - self.minx + PAD) * self.scale

    def _ty(self, y):
        return (self.maxy - y + PAD) * self.scale

    def _draw_text(self, x, y, text, color=TEXT, anchor="middle"):
        c = self.canv
        c.setFillColor(color)
        c.setFont(FONT, FSIZE)
        if anchor == "middle":
            c.drawCentredString(x, y, text)
        else:
            c.drawString(x, y, text)

    def _node_text(self, node):
        c = self.canv
        lines = _label_lines(node.get("label", ""))
        if not lines:
            return
        cx = self._tx(node["_x"])
        cy = self._ty(node["_y"])
        total = (len(lines) - 1) * LEADING
        c.setFillColor(TEXT)
        c.setFont(FONT, FSIZE)
        for i, ln in enumerate(lines):
            c.drawCentredString(cx, cy + total / 2 - i * LEADING - 2.6, ln)

    def _draw_node(self, node):
        c = self.canv
        t = node["type"]
        w, h = node["_w"] * self.scale, node["_h"] * self.scale
        x0 = self._tx(node["_x"]) - w / 2
        y0 = self._ty(node["_y"]) - h / 2
        c.saveState()
        c.setLineWidth(0.9)
        c.setStrokeColor(STROKE)
        c.setFillColor(FILL)
        if t == "label":
            self._node_text(node)
        elif t in ("start", "stop"):
            c.roundRect(x0, y0, w, h, h / 2, stroke=1, fill=1)
            self._node_text(node)
        elif t == "process":
            c.rect(x0, y0, w, h, stroke=1, fill=1)
            self._node_text(node)
        elif t == "sub":
            c.rect(x0, y0, w, h, stroke=1, fill=1)
            bar = 6 * self.scale
            c.line(x0 + bar, y0, x0 + bar, y0 + h)
            c.line(x0 + w - bar, y0, x0 + w - bar, y0 + h)
            self._node_text(node)
        elif t == "io":
            s = 9 * self.scale
            p = c.beginPath()
            p.moveTo(x0 + s, y0)
            p.lineTo(x0 + w, y0)
            p.lineTo(x0 + w - s, y0 + h)
            p.lineTo(x0, y0 + h)
            p.close()
            c.drawPath(p, stroke=1, fill=1)
            self._node_text(node)
        elif t == "decision":
            p = c.beginPath()
            p.moveTo(x0 + w / 2, y0)
            p.lineTo(x0 + w, y0 + h / 2)
            p.lineTo(x0 + w / 2, y0 + h)
            p.lineTo(x0, y0 + h / 2)
            p.close()
            c.drawPath(p, stroke=1, fill=1)
            self._node_text(node)
        c.restoreState()

    def _arrow_head(self, tip, prev):
        c = self.canv
        dx, dy = tip[0] - prev[0], tip[1] - prev[1]
        d = math.hypot(dx, dy) or 1.0
        ux, uy = dx / d, dy / d
        px, py = -uy, ux
        L, Wd = 6.6 * self.scale, 2.3 * self.scale
        base = (tip[0] - ux * L, tip[1] - uy * L)
        p = c.beginPath()
        p.moveTo(*tip)
        p.lineTo(base[0] + px * Wd, base[1] + py * Wd)
        p.lineTo(base[0] - px * Wd, base[1] - py * Wd)
        p.close()
        c.setFillColor(EDGE)
        c.drawPath(p, stroke=0, fill=1)

    def _draw_edge(self, e, pts):
        c = self.canv
        c.saveState()
        c.setStrokeColor(EDGE)
        c.setLineWidth(0.9)
        tpts = [(self._tx(x), self._ty(y)) for x, y in pts]
        # trim the tail so it stops at the arrow base area
        for i in range(len(tpts) - 1):
            c.line(tpts[i][0], tpts[i][1], tpts[i + 1][0], tpts[i + 1][1])
        # drop duplicated points
        uniq = [tpts[0]]
        for p in tpts[1:]:
            if p != uniq[-1]:
                uniq.append(p)
        if len(uniq) >= 2:
            self._arrow_head(uniq[-1], uniq[-2])
        if e.get("label"):
            (x1, y1), (x2, y2) = uniq[0], uniq[1]
            dx, dy = x2 - x1, y2 - y1
            d = math.hypot(dx, dy) or 1.0
            ux, uy = dx / d, dy / d
            px, py = -uy, ux   # left of travel
            lx = x1 + ux * min(17, d * 0.5) + px * 8
            ly = y1 + uy * min(17, d * 0.5) + py * 8
            self._draw_text(lx, ly - 2.4, e["label"])
        c.restoreState()

    # ----------------------------------------------------------- render
    def draw(self):
        c = self.canv
        c.saveState()
        for e, pts in self.edges:
            self._draw_edge(e, pts)
        for node in self.nodes.values():
            self._draw_node(node)
        c.restoreState()

    def wrap(self, availWidth, availHeight):
        return self.width, self.height
