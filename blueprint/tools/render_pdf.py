"""PHANTOMS // PROJECT BLUEPRINT — PDF renderer (fpdf2 + HarfBuzz shaping, RTL)."""
import json, os, re, sys
from fpdf import FPDF, FontFace
from fpdf.enums import XPos, YPos

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mdast
from mdast import plain, has_mark, is_mark_only

T = json.load(open(os.path.join(ROOT, "design", "tokens.json")))
FONTDIR = os.path.join(ROOT, "assets", "fonts")

def hx(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i+2], 16) for i in (0, 2, 4))

BG, PANEL, PANEL2, HEAD = hx(T["bg"]), hx(T["bg_panel"]), hx(T["bg_panel2"]), hx(T["bg_head"])
LINE, LINES = hx(T["line"]), hx(T["line_soft"])
INK, BODY, DIM, FAINT = hx(T["ink"]), hx(T["ink_body"]), hx(T["ink_dim"]), hx(T["ink_faint"])
ACC, ACCS, ACCD = hx(T["accent"]), hx(T["accent_soft"]), hx(T["accent_dim"])
AMBER, GREEN, RED, VIOLET = hx(T["amber"]), hx(T["green"]), hx(T["red"]), hx(T["violet"])
DOTC = {"green": GREEN, "amber": AMBER, "red": RED}

ARABIC_RE = re.compile(r"[؀-ۿ]")
LAT_RUN = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._/+%°#=:'~-]*")

def iso(text):
    """Wrap latin runs in Unicode isolates so punctuation/digits keep their order."""
    def rep(m):
        return "\u2066" + m.group(0).rstrip(" .,;:") + "\u2069" + m.group(0)[len(m.group(0).rstrip(" .,;:")):]
    return LAT_RUN.sub(rep, text)
MX, TOP, BOT = T["page"]["mx"], T["page"]["top"], T["page"]["bottom"]
PAGE_H = T["page"]["h"]

STYLE_FONT = {"t": ("Alex", ""), "b": ("Alex", "B"), "i": ("Alex", "I"), "c": ("Mono", "")}
STYLE_SIZE = {"t": 0, "b": 0, "i": 0, "c": -0.8}
STYLE_COLOR = {"t": BODY, "b": INK, "i": (154, 173, 190), "c": ACCS}


class BP(FPDF):
    def __init__(self):
        super().__init__(format="A4", unit="mm")
        self.set_title("PHANTOMS // PROJECT BLUEPRINT")
        self.set_author("PHANTOMS")
        self.set_text_shaping(True)
        self.add_font("Alex", "", os.path.join(FONTDIR, "Alexandria-400Regular.ttf"))
        self.add_font("Alex", "B", os.path.join(FONTDIR, "Alexandria-700Bold.ttf"))
        self.add_font("Alex", "I", os.path.join(FONTDIR, "Alexandria-500Medium.ttf"))
        self.add_font("Mono", "", os.path.join(FONTDIR, "JetBrainsMono-400Regular.ttf"))
        self.add_font("Mono", "B", os.path.join(FONTDIR, "JetBrainsMono-700Bold.ttf"))
        self.set_fallback_fonts(["Alex"])
        self.set_margins(MX, TOP, MX)
        self.set_auto_page_break(False)
        self.part_pages = {}
        self.current_part = None
        self.chrome = True
        self.bottom = PAGE_H - BOT

    # ---------- primitives ----------
    def bg(self):
        self.set_fill_color(*BG)
        self.rect(0, 0, 210, PAGE_H, "F")
        self.set_draw_color(*LINES)
        self.set_line_width(0.3)
        self.ellipse(-30, PAGE_H - 60, 120, 120, style="D")
        self.set_draw_color(*LINE)
        self.ellipse(150, -70, 130, 130, style="D")

    def set_ls(self, v):
        self.set_char_spacing(v)

    def meas(self, text, family="Alex", style="", size=10):
        self.set_font(family, style, size)
        return self.get_string_width(text)

    def mark_w(self, k):
        if k == "new":
            return self.meas("NEW", "Mono", "B", 6.4) + 3.4
        return {"box": 3.8, "dot:green": 3.2, "dot:amber": 3.2, "dot:red": 3.2,
                "ok": 3.6, "no": 3.6, "tick": 3.2}.get(k, 3.4)

    def draw_mark(self, k, x_right, y, lh):
        """draw mark so its right edge = x_right; returns width"""
        w = self.mark_w(k)
        cy = y + lh / 2
        if k == "box":
            self.set_draw_color(70, 88, 106)
            self.set_line_width(0.35)
            self.rect(x_right - w + 0.3, y + (lh - 3.2) / 2, 3.2, 3.2, style="D",
                      round_corners=True, corner_radius=0.7)
        elif k.startswith("dot:"):
            c = DOTC[k.split(":")[1]]
            self.set_fill_color(*c)
            self.circle(x_right - w / 2, cy, 1.15, style="F")
            self.set_draw_color(*c)
            self.set_line_width(0.3)
            self.circle(x_right - w / 2, cy, 1.9, style="D")
        elif k in ("ok", "tick"):
            c = GREEN if k == "ok" else ACC
            self.set_draw_color(*c)
            self.set_line_width(0.6)
            x0 = x_right - w + 0.4
            self.line(x0, cy - 0.1, x0 + 1.1, cy + 1.1)
            self.line(x0 + 1.1, cy + 1.1, x0 + 3.0, cy - 1.3)
        elif k == "no":
            self.set_draw_color(*RED)
            self.set_line_width(0.6)
            x0 = x_right - w + 0.6
            self.line(x0, cy - 1.2, x0 + 2.4, cy + 1.2)
            self.line(x0 + 2.4, cy - 1.2, x0, cy + 1.2)
        elif k == "new":
            tw = w - 3.4
            self.set_fill_color(58, 42, 18)
            self.set_draw_color(*AMBER)
            self.set_line_width(0.3)
            self.rect(x_right - w, cy - 2.0, w, 4.0, style="DF", round_corners=True, corner_radius=1.8)
            self.set_font("Mono", "B", 6.4)
            self.set_text_color(*AMBER)
            self.set_ls(0.6)
            self.set_xy(x_right - w + 1.7, cy - 1.6)
            self.cell(tw, 3.2, "NEW", align="C")
            self.set_ls(0)
        return w

    def _units(self, toks, ltr=False):
        """Group consecutive same-run word tokens; latin groups keep LTR order."""
        units = []
        cur = None
        for tk in toks:
            if "sp" in tk:
                if cur is None:
                    units.append({"k": "sp", "w": tk["sp"]})
                else:
                    cur["toks"].append(tk)
                    cur["w"] += tk["sp"]
                continue
            if "m" in tk:
                if cur:
                    units.append(cur); cur = None
                units.append({"k": "m", "m": tk["m"], "w": tk["w"]})
                continue
            if cur is None or tk["ri"] != cur["ri"]:
                if cur:
                    units.append(cur)
                cur = {"k": None, "ri": tk["ri"], "toks": [], "w": 0.0}
            cur["toks"].append(tk)
            cur["w"] += tk.get("w", tk.get("sp", 0))
        if cur:
            units.append(cur)
        out = []
        for u in units:
            if u["k"] is None:
                joined = "".join(t.get("txt", " ") for t in u["toks"])
                has_ar = bool(ARABIC_RE.search(joined))
                if ltr:
                    u["k"] = "grp_rtl" if has_ar else "seq"
                else:
                    u["k"] = "grp_ltr" if not has_ar else "seq"
            out.append(u)
        return out

    # ---------- rich text ----------
    def _tokens(self, runs, size):
        toks = []
        for r in runs:
            if r["s"] == "m":
                toks.append({"m": r["k"], "w": self.mark_w(r["k"])})
                continue
            fam, st = STYLE_FONT[r["s"]]
            sz = size + STYLE_SIZE[r["s"]]
            words = r["v"].split(" ")
            for i, wd in enumerate(words):
                if wd == "":
                    if i != len(words) - 1:
                        toks.append({"sp": self.meas(" ", fam, st, sz)})
                    continue
                toks.append({"txt": wd, "ri": id(r), "fam": fam, "st": st, "sz": sz,
                             "rs": r["s"], "w": self.meas(wd, fam, st, sz)})
                if i != len(words) - 1:
                    toks.append({"sp": self.meas(" ", fam, st, sz)})
        return toks

    def wrap(self, runs, width, size):
        toks = self._tokens(runs, size)
        lines, cur, curw = [], [], 0.0
        for tk in toks:
            w = tk.get("w", tk.get("sp", 0))
            is_space = "sp" in tk
            if is_space and not cur:
                continue
            if curw + w > width + 0.01 and cur:
                lines.append((cur, curw))
                cur, curw = [], 0.0
                if is_space:
                    continue
            cur.append(tk)
            curw += w
        if cur:
            lines.append((cur, curw))
        return lines

    def draw_line(self, toks, w, x_right, y, lh, align="R", base_color=BODY, size=10.2):
        x = x_right
        if align == "C":
            x = x_right - (self.epw - w) / 2
        elif align == "L":
            x = x_right - self.epw
        simple = all(("sp" in tk) or (tk.get("rs") in ("t", "b", "i")) for tk in toks)
        if simple:
            segs, cur_ri, cur_txt, cur_rs = [], None, [], None
            for tk in toks:
                if "sp" in tk:
                    cur_txt.append(" ")
                    continue
                if cur_ri is not None and tk["ri"] != cur_ri:
                    segs.append((cur_rs, "".join(cur_txt)))
                    cur_txt = []
                cur_ri = tk["ri"]
                cur_rs = tk["rs"]
                cur_txt.append(tk["txt"])
            if cur_txt:
                segs.append((cur_rs, "".join(cur_txt)))
            groups = []
            for rs, txt in segs:
                if groups and groups[-1][0] == rs and rs in ("t", "b", "i"):
                    groups[-1][1] += txt
                else:
                    groups.append([rs, txt])
            md = ""
            for rs, txt in groups:
                txt = iso(txt)
                md += {"t": txt, "b": "**" + txt + "**", "i": "*" + txt + "*"}.get(rs, txt)
            self.set_font("Alex", "", size)
            self.set_text_color(*base_color)
            self.set_xy(x - w, y)
            self.cell(w, lh, md, markdown=True)
            return
        for unit in self._units(toks):
            if unit["k"] == "sp":
                x -= unit["w"]
                continue
            if unit["k"] == "m":
                self.draw_mark(unit["m"], x, y, lh)
                x -= unit["w"]
                continue
            if unit["k"] == "grp_ltr":
                trail = 0.0
                for tk in reversed(unit["toks"]):
                    if "sp" in tk:
                        trail += tk["sp"]
                    else:
                        break
                gx = x - unit["w"] + trail
                for tk in unit["toks"]:
                    if "sp" in tk:
                        gx += tk["sp"]
                        continue
                    self.set_font(tk["fam"], tk["st"], tk["sz"])
                    col = STYLE_COLOR.get(tk["rs"], base_color)
                    if tk["rs"] == "c":
                        self.set_fill_color(16, 26, 38)
                        self.rect(gx - 0.6, y + (lh - tk["sz"] * 0.42) / 2 - 0.4,
                                  tk["w"] + 1.2, tk["sz"] * 0.42 + 1.2, style="F",
                                  round_corners=True, corner_radius=0.8)
                        col = ACCS
                    self.set_text_color(*col)
                    self.set_xy(gx, y)
                    self.cell(tk["w"], lh, tk["txt"])
                    gx += tk["w"]
                x -= unit["w"]
                continue
            for tk in unit["toks"]:
                if "sp" in tk:
                    x -= tk["sp"]
                    continue
                self.set_font(tk["fam"], tk["st"], tk["sz"])
                col = STYLE_COLOR.get(tk["rs"], base_color)  # seq rtl
                if tk["rs"] == "c":
                    self.set_fill_color(16, 26, 38)
                    self.rect(x - tk["w"] - 0.6, y + (lh - tk["sz"] * 0.42) / 2 - 0.4,
                              tk["w"] + 1.2, tk["sz"] * 0.42 + 1.2, style="F",
                              round_corners=True, corner_radius=0.8)
                    col = ACCS
                self.set_text_color(*col)
                self.set_xy(x - tk["w"], y)
                self.cell(tk["w"], lh, tk["txt"])
                x -= tk["w"]

    def rich(self, runs, width=None, size=10.2, lh=None, align="R", color=BODY,
             x_right=None, gap_after=2.0, dry=False):
        width = width or self.epw
        lh = lh or size * 0.56
        lines = self.wrap(runs, width, size)
        if dry:
            return len(lines) * lh
        xr = x_right if x_right is not None else self.l_margin + self.epw
        y = self.get_y()
        for toks, w in lines:
            self.draw_line(toks, w, xr, y, lh, align=align, base_color=color, size=size)
            y += lh
        self.set_y(y + gap_after)
        return y

    def ensure(self, h):
        if self.get_y() + h > self.bottom:
            self.add_page()

    # ---------- blocks ----------
    def h2(self, runs):
        self.ensure(36)
        y = self.get_y() + 4.5
        new = has_mark(runs, "new")
        title_runs = [r for r in runs if not (r["s"] == "m")]
        txt = plain(title_runs)
        m = re.match(r"^(\d+|APPENDIX [A-F]|Q\d+)\s*—\s*(.*)$", txt)
        xr = self.l_margin + self.epw
        bw = 0
        if m:
            num, rest = m.groups()
            self.set_font("Mono", "B", 8)
            self.set_text_color(*ACC)
            self.set_draw_color(*ACCD)
            self.set_fill_color(12, 26, 34)
            bw = self.meas(num, "Mono", "B", 8) + 3.6
            self.rect(xr - bw, y - 0.4, bw, 6.2, style="DF", round_corners=True, corner_radius=1.4)
            self.set_xy(xr - bw, y + 0.5)
            self.cell(bw, 4.4, num, align="C")
            tw = self.meas(rest, "Alex", "B", 13)
            self.set_font("Alex", "B", 13)
            self.set_text_color(*INK)
            self.set_xy(xr - bw - 2.6 - tw, y - 0.2)
            self.cell(tw, 6.6, rest)
            total = bw + 2.6 + tw
        else:
            tw = self.meas(txt, "Alex", "B", 13)
            self.set_font("Alex", "B", 13)
            self.set_text_color(*INK)
            self.set_xy(xr - tw, y - 0.2)
            self.cell(tw, 6.6, txt)
            total = tw
        if new:
            self.draw_mark("new", xr - total - 3.0, y + 0.6, 4.4)
        self.set_draw_color(*ACC)
        self.set_line_width(0.9)
        self.line(xr - 14, y + 7.4, xr, y + 7.4)
        self.set_draw_color(*LINE)
        self.set_line_width(0.3)
        self.line(xr - 14, y + 7.4, self.l_margin, y + 7.4)
        self.set_y(y + 12.5)

    def h3(self, runs):
        self.ensure(22)
        y = self.get_y() + 3.5
        xr = self.l_margin + self.epw
        self.set_fill_color(*ACC)
        self.rect(xr - 1.2, y + 0.6, 1.2, 4.2, "F")
        new = has_mark(runs, "new")
        txt = plain([r for r in runs if r["s"] != "m"])
        tw = self.meas(txt, "Alex", "B", 11)
        self.set_font("Alex", "B", 11)
        self.set_text_color(*ACCS)
        self.set_xy(xr - 3.4 - tw, y)
        self.cell(tw, 5.4, txt)
        if new:
            self.draw_mark("new", xr - 5.0 - tw, y + 0.6, 4.2)
        self.set_y(y + 8.6)

    def para(self, runs, size=10.2):
        if sum(1 for r in runs if r["s"] == "m" and r["k"] == "box") >= 2:
            return self.checkgrid(runs)
        if sum(1 for r in runs if r["s"] == "m" and r["k"] == "tick") >= 2:
            return self.chipflow(runs)
        h = self.rich(runs, size=size, dry=True) + 1.6
        self.ensure(h)
        self.rich(runs, size=size)

    def checkgrid(self, runs):
        items, cur = [], []
        for r in runs:
            if r["s"] == "m" and r["k"] == "box":
                if cur:
                    items.append(cur)
                cur = []
            else:
                cur.append(r)
        if cur:
            items.append(cur)
        colw = (self.epw - 6) / 2
        lh = 5.0
        heights = [self.rich(it, width=colw, size=9.4, lh=lh, dry=True) for it in items]
        rows = [heights[i:i+2] for i in range(0, len(items), 2)]
        total = sum(max(r + [0]) for r in rows) + 2
        self.ensure(min(total, self.bottom - TOP))
        y = self.get_y() + 1
        for ri, row in enumerate(rows):
            rh = max(row)
            if y + rh > self.bottom:
                self.add_page()
                y = self.get_y() + 1
            y0 = y
            for ci, it in enumerate(items[ri*2:ri*2+2]):
                xr = self.l_margin + self.epw - ci * (colw + 6)
                self.set_y(y0)
                self.draw_mark("box", xr, y0 + 0.4, lh)
                self.rich(it, width=colw, size=9.4, lh=lh, x_right=xr - 5.0,
                          gap_after=0)
            y = y0 + rh + 1.2
        self.set_y(y + 1.5)

    def chipflow(self, runs):
        items, cur = [], []
        for r in runs:
            if r["s"] == "m" and r["k"] == "tick":
                if cur:
                    items.append(cur)
                cur = []
            else:
                if r["s"] == "t" and r["v"].strip().startswith("—"):
                    r = dict(r, v=r["v"].lstrip("— ").strip() and r["v"] or r["v"])
                cur.append(r)
        if cur:
            items.append(cur)
        lh = 5.0
        y = self.get_y() + 1
        x = self.l_margin + self.epw
        for it in items:
            txt = plain(it).strip(" —-")
            if not txt:
                continue
            w = self.meas(txt, "Alex", "", 8.8) + 7.5
            if x - w < self.l_margin:
                x = self.l_margin + self.epw
                y += 8.6
            if y + 8 > self.bottom:
                self.add_page()
                y = self.get_y() + 1
                x = self.l_margin + self.epw
            self.set_fill_color(*PANEL2)
            self.set_draw_color(*LINE)
            self.set_line_width(0.3)
            self.rect(x - w, y, w, 7.4, style="DF", round_corners=True, corner_radius=2)
            self.draw_mark("tick", x - 2.2, y + 1.4, 4.6)
            self.set_font("Alex", "", 8.8)
            self.set_text_color(*BODY)
            self.set_xy(x - w + 1.6, y + 1.6)
            self.cell(w - 6.4, 4.4, iso(txt))
            x -= w + 2.4
        self.set_y(y + 11)

    def checklist(self, items):
        lh = 5.2
        for it in items:
            rs = [r for r in it if not (r["s"] == "m" and r["k"] == "box")]
            h = self.rich(rs, width=self.epw - 6, size=10, lh=lh, dry=True) + 1.4
            self.ensure(h)
            y = self.get_y()
            xr = self.l_margin + self.epw
            self.draw_mark("box", xr, y + 0.3, lh)
            self.rich(rs, width=self.epw - 6, size=10, lh=lh, x_right=xr - 5.4)

    def ulist(self, items):
        for it in items:
            h = self.rich(it, width=self.epw - 6, size=10.2, dry=True) + 1.5
            self.ensure(h)
            y = self.get_y()
            xr = self.l_margin + self.epw
            self.set_fill_color(*ACC)
            self.rect(xr - 2.6, y + 2.0, 1.6, 1.6, "F")
            self.rich(it, width=self.epw - 6, size=10.2, x_right=xr - 5.4)

    def olist(self, items):
        for n, it in enumerate(items, 1):
            h = self.rich(it, width=self.epw - 8, size=10.2, dry=True) + 1.5
            self.ensure(h)
            y = self.get_y()
            xr = self.l_margin + self.epw
            num = f"{n:02d}"
            nw = self.meas(num, "Mono", "B", 8) + 3
            self.set_fill_color(12, 26, 34)
            self.set_draw_color(*ACCD)
            self.set_line_width(0.3)
            self.rect(xr - nw, y + 0.2, nw, 5.0, style="DF", round_corners=True, corner_radius=1.2)
            self.set_font("Mono", "B", 8)
            self.set_text_color(*ACC)
            self.set_xy(xr - nw, y + 1.1)
            self.cell(nw, 3.4, num, align="C")
            self.rich(it, width=self.epw - nw - 4, size=10.2, x_right=xr - nw - 4)

    def callout(self, items):
        pt = any("PharmaTrack" in plain(it["runs"]) for it in items)
        sizes = []
        for it in items:
            w = self.epw - 12
            sizes.append(self.rich(it["runs"], width=w, size=10, lh=5.2, dry=True) +
                         (1.5 if it["t"] == "li" else 1.0))
        h = sum(sizes) + 8
        if h > self.bottom - TOP:
            h = self.bottom - TOP
        self.ensure(min(h, self.bottom - TOP))
        y = self.get_y() + 1
        boxh = sum(sizes) + 7 + (3 if pt else 0)
        self.set_fill_color(*PANEL2)
        self.set_draw_color(*LINE)
        self.set_line_width(0.35)
        self.rect(self.l_margin, y, self.epw, boxh, style="DF", round_corners=True, corner_radius=2)
        self.set_fill_color(*(AMBER if pt else ACC))
        self.rect(self.l_margin + self.epw - 1.5, y + 2, 1.5, boxh - 4, "F")
        if pt:
            lbl = "PharmaTrack — RUNNING EXAMPLE"
            cw = self.meas(lbl, "Mono", "B", 6.2) + 4
            self.set_fill_color(*BG)
            self.rect(self.l_margin + 4, y - 2.6, cw + 2, 5.2, "F")
            self.set_fill_color(58, 42, 18)
            self.set_draw_color(*AMBER)
            self.set_line_width(0.3)
            self.rect(self.l_margin + 5, y - 2.1, cw, 4.2, style="DF", round_corners=True, corner_radius=1.8)
            self.set_font("Mono", "B", 6.2)
            self.set_text_color(*AMBER)
            self.set_ls(0.4)
            self.set_xy(self.l_margin + 5, y - 1.5)
            self.cell(cw, 3.0, lbl, align="C")
            self.set_ls(0)
        yy = y + 4.3 + (2.5 if pt else 0)
        for it, sh in zip(items, sizes):
            xr = self.l_margin + self.epw - 6
            if it["t"] == "li":
                self.set_fill_color(*ACCS)
                self.rect(xr - 2.2, yy + 2.1, 1.3, 1.3, "F")
                self.rich(it["runs"], width=self.epw - 12, size=10, lh=5.2,
                          x_right=xr - 4.4, gap_after=1.5)
            else:
                self.rich(it["runs"], width=self.epw - 12, size=10, lh=5.2,
                          x_right=xr, gap_after=1.0)
            yy += sh
        self.set_y(y + boxh + 4)

    # ---------- tables ----------
    def col_ltr(self, cells):
        txt = " ".join(plain(c) for c in cells).strip()
        return bool(txt) and not ARABIC_RE.search(txt)

    def cell_ltr(self, cell):
        txt = plain(cell).strip()
        return bool(txt) and not ARABIC_RE.search(txt)

    def table(self, head, rows):
        ncols = len(head) if head else len(rows[0])
        cols = list(range(ncols))
        ltr = []
        for c in cols:
            cells = [r[c] for r in rows if c < len(r)]
            ltr.append(self.col_ltr(cells))
            if head and not ltr[c]:
                ltr[c] = self.cell_ltr(head[c])
        maxw = []
        for c in cols:
            w = max([self.meas(plain(x), "Alex", "B", 9.2) for x in (head[c:c+1] if head else [])] +
                    [self.meas(plain(r[c]) if c < len(r) else "", "Alex", "", 9.2)
                     for r in rows] + [8])
            maxw.append(min(max(w + 6, 14), 74))
        s = sum(maxw)
        widths = [m * self.epw / s for m in maxw]
        pad = 2.2
        lh = 4.8

        def row_h(cells):
            h = lh
            for c, cell in enumerate(cells):
                w = widths[c] - 2 * pad
                n = self.wrap(cell, w, 9.2)
                h = max(h, len(n) * lh)
            return h + 2 * pad

        def draw_row(cells, y, is_head=False):
            h = row_h(cells)
            if is_head:
                self.set_fill_color(*HEAD)
                self.rect(self.l_margin, y, self.epw, h, "F")
            elif not is_head and (draw_row.i % 2 == 1):
                self.set_fill_color(*PANEL)
                self.rect(self.l_margin, y, self.epw, h, "F")
            x = self.l_margin + self.epw
            for c in cols:
                w = widths[c]
                x -= w
                cell = cells[c] if c < len(cells) else []
                if is_mark_only(cell):
                    self.draw_mark(cell[0]["k"], x + w / 2 + 1.8, y + h / 2 - 2.4, 4.8)
                    continue
                cell_ltr = ltr[c] or (not is_head and self.cell_ltr(cell))
                yy = y + pad
                for toks, tw in self.wrap(cell, w - 2 * pad, 9.2):
                    if cell_ltr and ltr[c]:
                        self.draw_line_ltr(toks, tw, x + pad, yy, lh, head=is_head)
                    elif cell_ltr:
                        self.draw_line_ltr(toks, tw, x + w - pad - tw, yy, lh,
                                           head=is_head)
                    else:
                        self.draw_line(toks, tw, x + w - pad, yy, lh,
                                       base_color=ACCS if is_head else BODY, size=9.2)
                    yy += lh
            self.set_draw_color(*LINES)
            self.set_line_width(0.25)
            self.line(self.l_margin, y + h, self.l_margin + self.epw, y + h)
            draw_row.i += 1
            return h
        draw_row.i = 0

        def draw_line_ltr(toks, w, x_left, y, lh, head=False):
            simple = all(("sp" in tk) or (tk.get("rs") in ("t", "b", "i")) for tk in toks)
            if simple:
                segs, cur_ri, cur_txt, cur_rs = [], None, [], None
                for tk in toks:
                    if "sp" in tk:
                        cur_txt.append(" ")
                        continue
                    if cur_ri is not None and tk["ri"] != cur_ri:
                        segs.append((cur_rs, "".join(cur_txt)))
                        cur_txt = []
                    cur_ri = tk["ri"]
                    cur_rs = tk["rs"]
                    cur_txt.append(tk["txt"])
                if cur_txt:
                    segs.append((cur_rs, "".join(cur_txt)))
                groups = []
                for rs, txt in segs:
                    if groups and groups[-1][0] == rs and rs in ("t", "b", "i"):
                        groups[-1][1] += txt
                    else:
                        groups.append([rs, txt])
                md = ""
                for rs, txt in groups:
                    md += {"t": txt, "b": "**" + txt + "**", "i": "*" + txt + "*"}.get(rs, txt)
                self.set_font("Alex", "", 9.2)
                self.set_text_color(*(ACCS if head else BODY))
                self.set_xy(x_left, y)
                self.cell(w, lh, md, markdown=True)
                return
            x = x_left
            for unit in self._units(toks, ltr=True):
                if unit["k"] == "sp":
                    x += unit["w"]
                    continue
                if unit["k"] == "m":
                    self.draw_mark(unit["m"], x + unit["w"], y, lh)
                    x += unit["w"]
                    continue
                if unit["k"] == "grp_rtl":
                    trail = 0.0
                    for tk in reversed(unit["toks"]):
                        if "sp" in tk:
                            trail += tk["sp"]
                        else:
                            break
                    gx = x + unit["w"] - trail
                    for tk in unit["toks"]:
                        if "sp" in tk:
                            gx -= tk["sp"]
                            continue
                        self.set_font(tk["fam"], tk["st"], tk["sz"])
                        col = (ACCS if head else STYLE_COLOR.get(tk["rs"], BODY))
                        self.set_text_color(*col)
                        self.set_xy(gx - tk["w"], y)
                        self.cell(tk["w"], lh, tk["txt"])
                        gx -= tk["w"]
                    x += unit["w"]
                    continue
                for tk in unit["toks"]:
                    if "sp" in tk:
                        x += tk["sp"]
                        continue
                    self.set_font(tk["fam"], tk["st"], tk["sz"])
                    col = (ACCS if head else STYLE_COLOR.get(tk["rs"], BODY))
                    if tk["rs"] == "c":
                        col = ACCS
                    self.set_text_color(*col)
                    self.set_xy(x, y)
                    self.cell(tk["w"], lh, tk["txt"])
                    x += tk["w"]
        self.draw_line_ltr = draw_line_ltr

        y = self.get_y() + 1.5
        seg_start = y
        if head:
            hh = row_h(head)
            if y + hh > self.bottom:
                self.add_page(); y = self.get_y() + 1.5; seg_start = y
            draw_row(head, y, True)
            self.set_draw_color(*ACC)
            self.set_line_width(0.5)
            self.line(self.l_margin, y + hh, self.l_margin + self.epw, y + hh)
            y += hh
        for r in rows:
            h = row_h(r)
            if y + h > self.bottom:
                self.set_draw_color(*LINE)
                self.set_line_width(0.35)
                self.rect(self.l_margin, seg_start, self.epw, y - seg_start, style="D")
                self.add_page(); y = self.get_y() + 1.5; seg_start = y
                if head:
                    hh = row_h(head)
                    draw_row(head, y, True); y += hh
            draw_row(r, y)
            y += h
        self.set_draw_color(*LINE)
        self.set_line_width(0.35)
        self.rect(self.l_margin, seg_start, self.epw, y - seg_start, style="D")
        self.set_y(y + 4)

    # ---------- code / diagrams ----------
    def codeblock(self, kind, text):
        lines = text.split("\n")
        if kind == "pillars":
            return self.pillars(text)
        if kind == "diagram" and "LEARN" in text and "BUILD" in text:
            return self.timeline43(text)
        if kind == "diagram":
            return self.chain(text)
        lh = 4.5
        h = len(lines) * lh + 8
        self.ensure(min(h, self.bottom - TOP))
        y = self.get_y() + 1
        self.set_fill_color(13, 20, 29)
        self.set_draw_color(*LINE)
        self.set_line_width(0.35)
        self.rect(self.l_margin, y, self.epw, h, style="DF", round_corners=True, corner_radius=2)
        self.set_fill_color(*ACCD)
        self.rect(self.l_margin, y + 2, 0.9, h - 4, "F")
        yy = y + 4
        for ln in lines:
            self.set_font("Mono", "", 8.2)
            self.set_text_color(159, 182, 204)
            self.set_xy(self.l_margin + 4, yy)
            self.cell(self.epw - 8, lh, ln)
            yy += lh
        self.set_y(y + h + 4)

    def chain(self, text):
        text = text.replace("🧠", "").replace("🔨", "")
        steps = []
        for ln in text.split("\n"):
            ln = ln.strip()
            if not ln:
                continue
            parts = re.split(r"\s*(?:→|↓|←)\s*", ln)
            vertical = "↓" in ln
            for i, p in enumerate(parts):
                steps.append((p.strip(), vertical))
        steps = [(s, v) for s, v in steps if s]
        if any(v for _, v in steps):
            lh = 5.0
            h = len(steps) * (8.5 + 4) + 6
            self.ensure(min(h, self.bottom - TOP))
            y = self.get_y() + 1
            for i, (s, _) in enumerate(steps):
                w = min(self.meas(s, "Alex", "B", 9.4) + 8, self.epw)
                x = self.l_margin + (self.epw - w) / 2
                self.set_fill_color(*PANEL2)
                self.set_draw_color(*ACCD)
                self.set_line_width(0.35)
                self.rect(x, y, w, 8.0, style="DF", round_corners=True, corner_radius=2)
                self.set_font("Alex", "B", 9.4)
                self.set_text_color(*INK)
                self.set_xy(x, y + 1.8)
                self.cell(w, 4.6, s, align="C")
                y += 8.0
                if i < len(steps) - 1:
                    self.set_draw_color(*ACC)
                    self.set_line_width(0.5)
                    cx = self.l_margin + self.epw / 2
                    self.line(cx, y + 0.6, cx, y + 3.2)
                    self.line(cx - 1.0, y + 2.2, cx, y + 3.4)
                    self.line(cx + 1.0, y + 2.2, cx, y + 3.4)
                    y += 4.0
            self.set_y(y + 3)
            return
        # horizontal chips with wrap
        y = self.get_y() + 1
        x = self.l_margin + self.epw
        rowh = 8.0
        for i, (s, _) in enumerate(steps):
            w = self.meas(s, "Alex", "B", 9.2) + 7
            arrow = 6 if i < len(steps) - 1 else 0
            if x - w - arrow < self.l_margin:
                x = self.l_margin + self.epw
                y += rowh + 4
            self.set_fill_color(*PANEL2)
            self.set_draw_color(*ACCD)
            self.set_line_width(0.35)
            self.rect(x - w, y, w, rowh, style="DF", round_corners=True, corner_radius=2)
            self.set_font("Alex", "B", 9.2)
            self.set_text_color(*INK)
            self.set_xy(x - w, y + 1.7)
            self.cell(w, 4.6, s, align="C")
            x -= w
            if arrow:
                self.set_draw_color(*ACC)
                self.set_line_width(0.5)
                self.line(x - 1.0, y + rowh / 2, x - 4.4, y + rowh / 2)
                self.line(x - 3.4, y + rowh / 2 - 1.0, x - 4.6, y + rowh / 2)
                self.line(x - 3.4, y + rowh / 2 + 1.0, x - 4.6, y + rowh / 2)
                x -= 6
        self.set_y(y + rowh + 4)

    def timeline43(self, text):
        self.ensure(46)
        y = self.get_y() + 2
        total = self.epw
        lw = total * 4 / 7
        bw = total - lw
        lx = self.l_margin + self.epw - lw          # LEARN block (right, first)
        bx = self.l_margin                           # BUILD block (left, second)
        self.set_fill_color(14, 42, 52)
        self.rect(lx, y, lw - 1.2, 14, "F", round_corners=True, corner_radius=2)
        self.set_fill_color(46, 32, 60)
        self.rect(bx, y, bw - 1.2, 14, "F", round_corners=True, corner_radius=2)
        self.set_draw_color(*ACC)
        self.set_line_width(0.6)
        self.rect(lx, y, lw - 1.2, 14, "D", round_corners=True, corner_radius=2)
        self.set_draw_color(*VIOLET)
        self.rect(bx, y, bw - 1.2, 14, "D", round_corners=True, corner_radius=2)
        self.set_font("Mono", "B", 10)
        self.set_text_color(*ACC)
        self.set_ls(0.8)
        self.set_xy(lx, y + 2.6)
        self.cell(lw - 1.2, 5, "LEARN", align="C")
        self.set_text_color(*VIOLET)
        self.set_xy(bx, y + 2.6)
        self.cell(bw - 1.2, 5, "BUILD", align="C")
        self.set_ls(0)
        self.set_font("Alex", "B", 8.6)
        self.set_text_color(*ACCS)
        self.set_xy(lx, y + 8.2)
        self.cell(lw - 1.2, 4.4, "4 شهور — تعلم موجه + قطع حقيقية", align="C")
        self.set_text_color(200, 180, 240)
        self.set_xy(bx, y + 8.2)
        self.cell(bw - 1.2, 4.4, "3 شهور — تنفيذ فعلي مكثف", align="C")
        y += 18
        self.set_draw_color(*FAINT)
        self.set_line_width(0.3)
        self.line(self.l_margin, y + 2, self.l_margin + self.epw, y + 2)
        cap = "↑ القطع الصغيرة بتتلم من جوّه مرحلة التعلم"
        cw = self.meas(cap, "Alex", "", 8.4)
        self.set_font("Alex", "", 8.4)
        self.set_text_color(*DIM)
        self.set_xy(self.l_margin + self.epw - cw, y + 4)
        self.cell(cw, 4.2, cap)
        self.set_y(y + 11)

    def pillars(self, text):
        self.ensure(52)
        y = self.get_y() + 2
        groups = re.findall(r"\[([^\]]+)\]", text)
        root = groups[0] if groups else "القيمة المضافة الحقيقية"
        kids = groups[1:4] if len(groups) > 3 else groups[1:]
        en = re.findall(r"(Localization|Cost Optimization|Smart Integration)", text)
        rw = self.meas(root, "Alex", "B", 10) + 10
        cx = self.l_margin + self.epw / 2
        self.set_fill_color(14, 42, 52)
        self.set_draw_color(*ACC)
        self.set_line_width(0.5)
        self.rect(cx - rw / 2, y, rw, 9, style="DF", round_corners=True, corner_radius=2)
        self.set_font("Alex", "B", 10)
        self.set_text_color(*ACCS)
        self.set_xy(cx - rw / 2, y + 2.2)
        self.cell(rw, 4.6, root, align="C")
        y += 9
        self.set_draw_color(*ACC)
        self.set_line_width(0.4)
        self.line(cx, y, cx, y + 4)
        cw = (self.epw - 8) / 3
        self.line(self.l_margin + cw / 2, y + 4, self.l_margin + self.epw - cw / 2, y + 4)
        for i in range(3):
            kx = self.l_margin + cw / 2 + i * (cw + 4)
            self.line(kx, y + 4, kx, y + 8)
            self.line(kx - 1, y + 7, kx, y + 8.4)
            self.line(kx + 1, y + 7, kx, y + 8.4)
        y += 9
        for i, k in enumerate(kids):
            kx = self.l_margin + cw / 2 + i * (cw + 4)
            w = cw
            self.set_fill_color(*PANEL2)
            self.set_draw_color(*ACCD)
            self.set_line_width(0.35)
            self.rect(kx - w / 2, y, w, 12, style="DF", round_corners=True, corner_radius=2)
            self.set_font("Alex", "B", 9)
            self.set_text_color(*INK)
            self.set_xy(kx - w / 2, y + 2.2)
            self.cell(w, 4.2, k, align="C")
            if i < len(en):
                self.set_font("Mono", "", 7)
                self.set_text_color(*DIM)
                self.set_xy(kx - w / 2, y + 7)
                self.cell(w, 3.4, en[i], align="C")
        self.set_y(y + 16)

    # ---------- chrome ----------
    def chrome_on(self, part_label):
        self.current_part = part_label

    def draw_chrome(self):
        if not self.chrome or self.page_no() < 2:
            return
        y0 = self.get_y()
        x0 = self.get_x()
        self.set_draw_color(*LINE)
        self.set_line_width(0.3)
        self.line(MX, 16.5, 210 - MX, 16.5)
        self.set_font("Mono", "B", 6.6)
        self.set_text_color(*ACCD)
        self.set_ls(0.8)
        self.set_xy(MX, 11.5)
        self.cell(90, 3.4, "PHANTOMS // PROJECT BLUEPRINT")
        self.set_ls(0)
        if self.current_part:
            lbl = self.current_part
            w = self.meas(lbl, "Mono", "", 6.6)
            self.set_font("Mono", "", 6.6)
            self.set_text_color(*FAINT)
            self.set_ls(0.5)
            self.set_xy(210 - MX - w, 11.5)
            self.cell(w, 3.4, lbl)
            self.set_ls(0)
        self.set_draw_color(*LINE)
        self.line(MX, PAGE_H - 12, 210 - MX, PAGE_H - 12)
        self.set_font("Mono", "B", 7.4)
        self.set_text_color(*ACC)
        self.set_xy(MX, PAGE_H - 10)
        self.cell(20, 4, f"{self.page_no():02d}")
        tag = "BUILD. LEARN. SHARE. GROW."
        w = self.meas(tag, "Mono", "", 6.2)
        self.set_font("Mono", "", 6.2)
        self.set_text_color(*FAINT)
        self.set_ls(0.6)
        self.set_xy(210 - MX - w, PAGE_H - 9.6)
        self.cell(w, 3.4, tag)
        self.set_ls(0)
        self.set_xy(x0, y0)

    def header(self):
        self.bg()
        self.draw_chrome()
        self.set_y(self.t_margin)

    # ---------- structural ----------
    def cover(self):
        self.current_part = ""
        self.add_page()
        # gradient strip
        n = 90
        for i in range(n):
            t = i / (n - 1)
            c = tuple(int(ACC[j] + (VIOLET[j] - ACC[j]) * t) for j in range(3))
            self.set_fill_color(*c)
            self.rect(MX + i * self.epw / n, 60, self.epw / n + 0.2, 1.6, "F")
        self.set_font("Mono", "B", 9)
        self.set_text_color(*ACC)
        self.set_ls(2.2)
        self.set_xy(MX, 34)
        self.cell(self.epw, 5, "PHANTOMS", align="R")
        self.set_ls(0)
        self.set_font("Mono", "", 7.4)
        self.set_text_color(*DIM)
        self.set_ls(1.4)
        self.set_xy(MX, 41)
        self.cell(self.epw, 4, "TECH BEYOND THE ORDINARY", align="R")
        self.set_ls(0)
        self.set_font("Alex", "B", 34)
        self.set_text_color(*INK)
        self.set_xy(MX, 74)
        self.cell(self.epw, 17, "PROJECT BLUEPRINT", align="R")
        self.set_font("Alex", "B", 15)
        self.set_text_color(*ACCS)
        self.set_xy(MX, 94)
        self.cell(self.epw, 8, "دليل الطالب لبناء مشروع تخرج قابل للتنفيذ والمناقشة", align="R")
        self.set_font("Mono", "", 7.6)
        self.set_text_color(*DIM)
        self.set_ls(0.4)
        self.set_xy(MX, 105)
        self.cell(self.epw, 4, "Idea > Scope > Architecture > Prototype > Testing > Docs > Defense > Approval", align="R")
        self.set_ls(0)
        # quote panel
        y = 128
        self.set_fill_color(*PANEL2)
        self.set_draw_color(*LINE)
        self.set_line_width(0.35)
        self.rect(MX, y, self.epw, 30, style="DF", round_corners=True, corner_radius=2.5)
        self.set_fill_color(*ACC)
        self.rect(MX + self.epw - 1.5, y + 3, 1.5, 24, "F")
        self.set_font("Alex", "B", 13)
        self.set_text_color(*INK)
        self.set_xy(MX + 6, y + 6)
        self.cell(self.epw - 12, 7, "الفكرة الصح مش أكبر فكرة.", align="R")
        self.set_xy(MX + 6, y + 15)
        self.cell(self.epw - 12, 7, "الفكرة الصح هي اللي تقدروا تثبتوها.", align="R")
        # gates strip
        y = 176
        self.set_font("Mono", "", 6.6)
        self.set_text_color(*FAINT)
        self.set_ls(0.8)
        self.set_xy(MX, y - 6)
        self.cell(self.epw, 3.4, "THE SEVEN GATES", align="R")
        self.set_ls(0)
        gates = ["G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7"]
        gw = (self.epw - 7 * 3) / 8
        for i, g in enumerate(gates):
            x = MX + self.epw - (i + 1) * gw - i * 3
            self.set_fill_color(PANEL if i < 7 else (20, 44, 40))
            self.set_draw_color(*(ACCD if i < 7 else GREEN))
            self.set_line_width(0.35)
            self.rect(x, y, gw, 10, style="DF", round_corners=True, corner_radius=2)
            self.set_font("Mono", "B", 8)
            self.set_text_color(*(ACC if i < 7 else GREEN))
            self.set_xy(x, y + 2.6)
            self.cell(gw, 4.4, g, align="C")
        self.set_font("Alex", "", 8.4)
        self.set_text_color(*DIM)
        self.set_xy(MX, y + 14)
        self.cell(self.epw, 4.2, "من الاعتماد الأول لحد توقيع الدكتور — كل بوابة ليها شرط عبور مكتوب.", align="R")
        self.set_font("Alex", "", 8)
        self.set_text_color(*FAINT)
        self.set_xy(MX, PAGE_H - 30)
        self.cell(self.epw, 4, "وثيقة إرشادية وتطبيقية موجهة لفرق مشاريع التخرج والمواد الممتدة — إصدار 2026", align="R")
        self.set_font("Mono", "", 6.6)
        self.set_ls(0.6)
        self.set_xy(MX, PAGE_H - 24)
        self.cell(self.epw, 3.4, "PHANTOMS // TECH BEYOND THE ORDINARY — BUILD. LEARN. SHARE. GROW.", align="R")
        self.set_ls(0)

    def toc_page(self, entries):
        self.current_part = "CONTENTS"
        self.add_page()
        xr = self.l_margin + self.epw
        y = 30
        self.set_font("Alex", "B", 20)
        self.set_text_color(*INK)
        self.set_xy(MX, y)
        self.cell(self.epw, 10, "المحتويات", align="R")
        self.set_draw_color(*ACC)
        self.set_line_width(0.9)
        self.line(xr - 22, y + 12, xr, y + 12)
        y += 20
        lh = 7.2
        for label, pg in entries:
            self.set_font("Alex", "", 9.4)
            self.set_text_color(*BODY)
            lw = self.meas(label, "Alex", "", 9.4)
            self.set_xy(xr - lw, y)
            self.cell(lw, 5, label)
            self.set_font("Mono", "B", 8)
            self.set_text_color(*ACC)
            pw = self.meas(f"{pg:02d}", "Mono", "B", 8)
            self.set_xy(MX, y)
            self.cell(pw, 5, f"{pg:02d}")
            dots_x0 = MX + pw + 3
            dots_x1 = xr - lw - 3
            self.set_draw_color(40, 54, 68)
            self.set_line_width(0.35)
            xx = dots_x1
            while xx > dots_x0:
                self.line(xx, y + 3.6, xx - 0.6, y + 3.6)
                xx -= 2.4
            y += lh
            if y > self.bottom - 6:
                self.add_page()
                y = self.get_y() + 4
        self.set_y(y)

    def part_opener(self, meta):
        part = meta.get("part", "")
        title = meta.get("title", "")
        self.current_part = f"{part} — {title}" if part else title
        self.add_page()
        self.part_pages[part or title] = self.page_no()
        xr = self.l_margin + self.epw
        y = 40
        num = part.replace("PART", "").strip()
        self.set_font("Mono", "B", 60)
        self.set_text_color(21, 31, 42)
        self.set_ls(-1)
        nw = self.meas(num or "APP", "Mono", "B", 60)
        self.set_xy(MX, y - 14)
        self.cell(nw, 30, num or "APP")
        self.set_ls(0)
        self.set_font("Mono", "B", 8.4)
        self.set_text_color(*ACC)
        self.set_ls(1.6)
        pw = self.meas(part, "Mono", "B", 8.4)
        self.set_xy(xr - pw, y - 4)
        self.cell(pw, 4.4, part)
        self.set_ls(0)
        self.set_font("Alex", "B", 22)
        self.set_text_color(*INK)
        tw = self.meas(title, "Alex", "B", 22)
        self.set_xy(xr - tw, y + 4)
        self.cell(tw, 11, title)
        if meta.get("new"):
            self.draw_mark("new", xr - tw - 4, y + 7, 5)
        y += 20
        n = 70
        for i in range(n):
            t = i / (n - 1)
            c = tuple(int(ACC[j] + (BG[j] - ACC[j]) * t) for j in range(3))
            self.set_fill_color(*c)
            self.rect(xr - 60 + i * 60 / n, y, 60 / n + 0.2, 1.2, "F")
        y += 6
        if meta.get("kicker") and meta.get("_skip_kicker"):
            pass
        elif meta.get("kicker"):
            self.set_font("Alex", "B", 10.5)
            self.set_text_color(*ACCS)
            kw = self.meas(meta["kicker"], "Alex", "B", 10.5)
            self.set_xy(xr - kw, y)
            self.cell(kw, 5.4, meta["kicker"])
            y += 8
        if meta.get("note"):
            self.set_font("Alex", "I", 9)
            self.set_text_color(*DIM)
            kw = self.meas(meta["note"], "Alex", "I", 9)
            self.set_xy(xr - kw, y)
            self.cell(kw, 4.6, meta["note"])
            y += 8
        self.set_y(y + 8)

    def back_page(self, blocks):
        self.current_part = "OUTRO"
        self.add_page()
        xr = self.l_margin + self.epw
        y = 60
        self.set_font("Alex", "B", 24)
        self.set_text_color(*INK)
        self.set_xy(MX, y)
        self.cell(self.epw, 12, "الخاتمة", align="R")
        y += 22
        for b in blocks:
            if b["t"] == "callout":
                for it in b["items"]:
                    txt = plain(it["runs"])
                    self.set_font("Alex", "B", 14)
                    self.set_text_color(*ACCS)
                    w = self.meas(txt, "Alex", "B", 14)
                    self.set_xy(xr - w, y)
                    self.cell(w, 8, txt)
                    y += 10
            elif b["t"] == "p":
                txt = plain(b["runs"])
                if txt.startswith("PHANTOMS //"):
                    self.set_font("Mono", "B", 9)
                    self.set_text_color(*INK)
                    self.set_ls(1.2)
                    w = self.meas("PHANTOMS // TECH BEYOND THE ORDINARY", "Mono", "B", 9)
                    self.set_xy(xr - w, y)
                    self.cell(w, 5, "PHANTOMS // TECH BEYOND THE ORDINARY")
                    self.set_ls(0)
                    y += 9
                    tag = "Build. Learn. Share. Grow."
                    self.set_font("Mono", "", 8)
                    self.set_text_color(*DIM)
                    self.set_ls(1.0)
                    w = self.meas(tag, "Mono", "", 8)
                    self.set_xy(xr - w, y)
                    self.cell(w, 4.4, tag)
                    self.set_ls(0)
                    y += 9
                    continue
                bold = any(r["s"] == "b" for r in b["runs"])
                lines = self.wrap(b["runs"], self.epw - 10, 11 if bold else 10.5)
                for toks, w in lines:
                    self.draw_line(toks, w, xr, y, 6.6, size=11 if bold else 10.5,
                                   base_color=INK if bold else DIM)
                    y += 6.8
                y += 3
        n = 90
        for i in range(n):
            t = i / (n - 1)
            c = tuple(int(ACC[j] + (VIOLET[j] - ACC[j]) * t) for j in range(3))
            self.set_fill_color(*c)
            self.rect(MX + i * self.epw / n, PAGE_H - 46, self.epw / n + 0.2, 1.4, "F")
        self.set_font("Mono", "B", 9)
        self.set_text_color(*INK)
        self.set_ls(1.6)
        self.set_xy(MX, PAGE_H - 38)
        self.cell(self.epw, 5, "PHANTOMS // TECH BEYOND THE ORDINARY", align="R")
        self.set_ls(0)
        self.set_font("Mono", "", 7.4)
        self.set_text_color(*DIM)
        self.set_ls(1.2)
        self.set_xy(MX, PAGE_H - 31)
        self.cell(self.epw, 4, "BUILD. LEARN. SHARE. GROW.", align="R")
        self.set_ls(0)


def render(docs, out, toc_entries=None):
    pdf = BP()
    entries = toc_entries
    collected = {}
    for pass_no in (1, 2):
        pdf = BP()
        pdf.cover()
        # front / how-to page
        front = next(d for d in docs if d["meta"].get("kind") == "front")
        pdf.current_part = "HOW TO USE"
        pdf.add_page()
        xr = pdf.l_margin + pdf.epw
        for b in front["blocks"]:
            if b["t"] == "h1":
                y = 34
                pdf.set_font("Mono", "B", 15)
                pdf.set_text_color(*ACC)
                pdf.set_ls(1.2)
                t = plain(b["runs"])
                w = pdf.meas(t, "Mono", "B", 15)
                pdf.set_xy(xr - w, y)
                pdf.cell(w, 8, t)
                pdf.set_ls(0)
                pdf.set_y(y + 12)
            elif b["t"] == "h2" and plain(b["runs"]).startswith("دليل الطالب"):
                pdf.rich(b["runs"], size=13, lh=8, color=INK)
            elif b["t"] == "p" and plain(b["runs"]).startswith("From Idea"):
                pdf.set_font("Mono", "", 7.2)
                pdf.set_text_color(*DIM)
                t = plain(b["runs"]).replace("→", ">")
                w = pdf.meas(t, "Mono", "", 7.2)
                pdf.set_xy(xr - w, pdf.get_y())
                pdf.cell(w, 4, t)
                pdf.set_y(pdf.get_y() + 6)
            elif b["t"] == "p" and plain(b["runs"]).startswith("(وثيقة"):
                pdf.rich(b["runs"], size=8.6, color=DIM)
                pdf.set_y(pdf.get_y() + 2)
            elif b["t"] == "callout":
                pdf.callout(b["items"])
                pdf.set_y(pdf.get_y() + 4)
            elif b["t"] == "hr":
                pdf.set_draw_color(*LINE)
                pdf.set_line_width(0.4)
                yy = pdf.get_y() + 2
                pdf.line(MX, yy, 210 - MX, yy)
                pdf.set_y(yy + 6)
            elif b["t"] == "h2":
                pdf.h2(b["runs"])
            elif b["t"] == "table":
                pdf.table(b["head"], b["rows"])
            elif b["t"] == "p":
                pdf.para(b["runs"], size=9.8)
        # TOC
        if entries is None:
            entries = []
            for d in docs:
                m = d["meta"]
                if m.get("part"):
                    lbl = m.get("toc") or m.get("title", "")
                    entries.append((f"{m['part']} — {lbl}", 0))
        pdf.toc_page(entries if pass_no == 2 else
                     [(l, 0) for l, _ in entries])
        # body
        for d in docs:
            m = d["meta"]
            if m.get("kind") in ("front", "back"):
                continue
            m = dict(m)
            fh2 = next((plain(b["runs"]) for b in d["blocks"] if b["t"] == "h2"), None)
            if fh2 and fh2.strip() == (m.get("kicker") or "").strip():
                m["_skip_kicker"] = True
            pdf.part_opener(m)
            for b in d["blocks"]:
                t = b["t"]
                if t == "h2":
                    pdf.h2(b["runs"])
                elif t == "h3":
                    pdf.h3(b["runs"])
                elif t == "p":
                    pdf.para(b["runs"])
                elif t == "table":
                    pdf.table(b["head"], b["rows"])
                elif t == "check":
                    pdf.checklist(b["items"])
                elif t == "ulist":
                    pdf.ulist(b["items"])
                elif t == "olist":
                    pdf.olist(b["items"])
                elif t == "callout":
                    pdf.callout(b["items"])
                elif t == "code":
                    pdf.codeblock(b["kind"], b["text"])
                elif t == "hr":
                    pdf.set_y(pdf.get_y() + 1.5)
        back = next(d for d in docs if d["meta"].get("kind") == "back")
        pdf.back_page(back["blocks"])
        collected = dict(pdf.part_pages)
        if pass_no == 1:
            keys = [d["meta"].get("part") or d["meta"].get("title")
                    for d in docs if d["meta"].get("part")]
            entries = [(l, collected.get(k, 0)) for (l, _), k in zip(entries, keys)]
    pdf.output(out)
    return collected


if __name__ == "__main__":
    content = os.path.join(ROOT, "content")
    docs = mdast.load_all(content)
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "dist", "PHANTOMS-Project-Blueprint.pdf")
    pages = render(docs, out)
    print("written", out, "part pages:", json.dumps(pages, ensure_ascii=False))
