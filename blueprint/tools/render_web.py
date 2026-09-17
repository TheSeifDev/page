"""PHANTOMS // PROJECT BLUEPRINT — web renderer (live preview + print-ready HTML)."""
import html, os, re, sys, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mdast
from mdast import plain

WEB = os.path.join(ROOT, "dist", "web")


def esc(t):
    return html.escape(t, quote=False)


def inline_html(runs):
    out = []
    for r in runs:
        if r["s"] == "m":
            k = r["k"]
            if k == "box":
                out.append('<span class="mk box"></span>')
            elif k.startswith("dot:"):
                out.append(f'<span class="mk dot {k.split(":")[1]}"></span>')
            elif k in ("ok", "tick"):
                out.append('<span class="mk ok">✓</span>')
            elif k == "no":
                out.append('<span class="mk no">✕</span>')
            elif k == "new":
                out.append('<span class="badge new">NEW</span>')
            continue
        t = esc(r["v"])
        if r["s"] == "b":
            out.append(f"<strong>{t}</strong>")
        elif r["s"] == "i":
            out.append(f"<em>{t}</em>")
        elif r["s"] == "c":
            out.append(f"<code>{t}</code>")
        else:
            out.append(t)
    return "".join(out)


def table_html(b):
    rows = []
    if b["head"]:
        rows.append("<thead><tr>" + "".join(
            f"<th>{inline_html(c)}</th>" for c in b["head"]) + "</tr></thead>")
    body = []
    for r in b["rows"]:
        cells = []
        for c in r:
            if mdast.is_mark_only(c):
                k = c[0]["k"]
                if k == "box":
                    cells.append('<td class="cx"><span class="mk box"></span></td>')
                elif k.startswith("dot:"):
                    cells.append(f'<td><span class="mk dot {k.split(":")[1]}"></span> </td>')
                elif k == "ok":
                    cells.append('<td class="cx"><span class="mk ok">✓</span></td>')
                elif k == "no":
                    cells.append('<td class="cx"><span class="mk no">✕</span></td>')
                else:
                    cells.append("<td></td>")
            else:
                cells.append(f"<td>{inline_html(c)}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    rows.append("<tbody>" + "".join(body) + "</tbody>")
    return '<div class="tbl"><table>' + "".join(rows) + "</table></div>"


def code_html(b):
    kind, text = b["kind"], b["text"]
    if kind == "diagram" and "LEARN" in text and "BUILD" in text:
        return ('<div class="t43"><div class="ph learn"><b>LEARN</b>'
                '<span>4 شهور — تعلم موجه + قطع حقيقية</span></div>'
                '<div class="ph build"><b>BUILD</b>'
                '<span>3 شهور — تنفيذ فعلي مكثف</span></div></div>'
                '<div class="t43cap">↑ القطع الصغيرة بتتلم من جوّه مرحلة التعلم</div>')
    if kind == "pillars":
        groups = re.findall(r"\[([^\]]+)\]", text)
        en = re.findall(r"(Localization|Cost Optimization|Smart Integration)", text)
        kids = "".join(
            f'<div class="pkid"><b>{esc(g)}</b><span>{esc(en[i]) if i < len(en) else ""}</span></div>'
            for i, g in enumerate(groups[1:4]))
        return (f'<div class="pillars"><div class="proot">{esc(groups[0])}</div>'
                f'<div class="pcon"></div><div class="pkids">{kids}</div></div>')
    if kind == "diagram":
        steps = []
        for ln in text.split("\n"):
            ln = ln.strip()
            if ln:
                steps += [p.strip() for p in re.split(r"\s*(?:→|↓|←)\s*", ln) if p.strip()]
        vertical = "↓" in text
        cls = "chain v" if vertical else "chain"
        inner = "".join(
            f'<span class="cstep">{esc(s)}</span>' +
            ('<span class="carr">↓</span>' if vertical and i < len(steps) - 1 else
             '<span class="carr">←</span>' if not vertical and i < len(steps) - 1 else "")
            for i, s in enumerate(steps))
        return f'<div class="{cls}">{inner}</div>'
    return f'<pre class="code {kind}">{esc(text)}</pre>'


def block_html(b):
    t = b["t"]
    if t == "h2":
        return f'<h2 class="sec">{inline_html(b["runs"])}</h2>'
    if t == "h3":
        return f'<h3 class="sub">{inline_html(b["runs"])}</h3>'
    if t == "p":
        if sum(1 for r in b["runs"] if r["s"] == "m" and r["k"] == "box") >= 2:
            items, cur = [], []
            for r in b["runs"]:
                if r["s"] == "m" and r["k"] == "box":
                    if cur:
                        items.append(cur)
                    cur = []
                else:
                    cur.append(r)
            if cur:
                items.append(cur)
            return '<div class="cgrid">' + "".join(
                f'<div class="citem"><span class="mk box"></span><span>{inline_html(it)}</span></div>'
                for it in items) + "</div>"
        return f'<p>{inline_html(b["runs"])}</p>'
    if t == "table":
        return table_html(b)
    if t == "check":
        return '<ul class="check">' + "".join(
            f'<li><span class="mk box"></span><span>{inline_html([r for r in it if not (r["s"]=="m" and r["k"]=="box")])}</span></li>'
            for it in b["items"]) + "</ul>"
    if t == "ulist":
        return '<ul class="bul">' + "".join(
            f"<li>{inline_html(it)}</li>" for it in b["items"]) + "</ul>"
    if t == "olist":
        return '<ol class="num">' + "".join(
            f"<li><span>{inline_html(it)}</span></li>" for it in b["items"]) + "</ol>"
    if t == "callout":
        pt = any("PharmaTrack" in plain(it["runs"]) for it in b["items"])
        inner = []
        for it in b["items"]:
            if it["t"] == "li":
                inner.append(f'<div class="cli">{inline_html(it["runs"])}</div>')
            else:
                inner.append(f'<div class="cln">{inline_html(it["runs"])}</div>')
        cls = "callout pt" if pt else "callout"
        chip = '<span class="ptchip">PharmaTrack — RUNNING EXAMPLE</span>' if pt else ""
        return f'<div class="{cls}">{chip}' + "".join(inner) + "</div>"
    if t == "code":
        return code_html(b)
    if t == "hr":
        return '<div class="hr"></div>'
    return ""


CSS = """
:root{
  --bg:#0B0F14; --panel:#0E1621; --panel2:#101A26; --head:#12202E;
  --line:#1C2836; --lines:#16202C;
  --ink:#E6EEF5; --body:#C7D3DF; --dim:#8CA0B3; --faint:#5C7186;
  --acc:#22D3EE; --accs:#67E8F9; --accd:#0E7490;
  --amber:#F5B04C; --green:#34D399; --red:#F87171; --violet:#A78BFA;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--body);
  font-family:Alexandria,system-ui,sans-serif;font-size:15px;line-height:1.95;direction:rtl}
@font-face{font-family:Alexandria;src:url('fonts/Alexandria-400Regular.ttf');font-weight:400}
@font-face{font-family:Alexandria;src:url('fonts/Alexandria-500Medium.ttf');font-weight:500}
@font-face{font-family:Alexandria;src:url('fonts/Alexandria-600SemiBold.ttf');font-weight:600}
@font-face{font-family:Alexandria;src:url('fonts/Alexandria-700Bold.ttf');font-weight:700}
@font-face{font-family:Alexandria;src:url('fonts/Alexandria-800ExtraBold.ttf');font-weight:800}
@font-face{font-family:JetBrainsMono;src:url('fonts/JetBrainsMono-400Regular.ttf')}
@font-face{font-family:JetBrainsMono;src:url('fonts/JetBrainsMono-700Bold.ttf');font-weight:700}
.mono{font-family:JetBrainsMono,monospace}
/* topbar */
#bar{position:fixed;inset-inline:0;top:0;z-index:9;display:flex;gap:14px;align-items:center;
  padding:10px 22px;background:rgba(11,15,20,.92);backdrop-filter:blur(8px);
  border-bottom:1px solid var(--line)}
#bar .brand{font-family:JetBrainsMono;font-weight:700;color:var(--acc);letter-spacing:.18em;font-size:12px}
#bar .sub{color:var(--faint);font-size:12px;font-family:JetBrainsMono;letter-spacing:.08em}
#bar .sp{flex:1}
#bar a,#bar button{font-family:JetBrainsMono;font-size:11px;letter-spacing:.1em;color:var(--accs);
  border:1px solid var(--accd);background:#0C1A22;border-radius:999px;padding:6px 14px;
  text-decoration:none;cursor:pointer}
#bar a:hover,#bar button:hover{background:#12303c}
main{max-width:980px;margin:0 auto;padding:86px 26px 90px}
/* cover */
.cover{padding:70px 0 40px;text-align:right}
.cover .kick{font-family:JetBrainsMono;color:var(--acc);letter-spacing:.35em;font-size:13px}
.cover .kick2{font-family:JetBrainsMono;color:var(--dim);letter-spacing:.22em;font-size:11px;margin-top:6px}
.cover .grad{height:4px;margin:34px 0;border-radius:2px;
  background:linear-gradient(90deg,var(--violet),var(--acc))}
.cover h1{font-size:clamp(34px,7vw,64px);font-weight:800;color:var(--ink);margin:0;letter-spacing:.01em;
  font-family:JetBrainsMono,Alexandria}
.cover h2{font-size:clamp(18px,3vw,26px);color:var(--accs);font-weight:700;margin:14px 0 6px}
.cover .pipe{font-family:JetBrainsMono;color:var(--dim);font-size:12px;letter-spacing:.06em}
.quote{background:var(--panel2);border:1px solid var(--line);border-inline-end:4px solid var(--acc);
  border-radius:10px;padding:18px 22px;margin:30px 0;font-weight:700;color:var(--ink);font-size:17px}
.gates{display:flex;gap:8px;margin:26px 0 8px;flex-wrap:wrap}
.gates span{font-family:JetBrainsMono;font-weight:700;font-size:13px;color:var(--acc);
  border:1px solid var(--accd);background:var(--panel);border-radius:8px;padding:8px 0;flex:1;text-align:center;min-width:52px}
.gates span:last-child{color:var(--green);border-color:#1d5c46;background:#12241c}
/* toc */
.toc{margin:40px 0}
.toc h2{font-size:30px;color:var(--ink);font-weight:800;border:none;margin:0 0 18px}
.toc h2:after{content:"";display:block;width:64px;height:3px;background:var(--acc);margin-top:8px}
.toc a{display:flex;gap:10px;align-items:baseline;color:var(--body);text-decoration:none;
  padding:7px 4px;border-bottom:1px dashed #223140;font-size:14.5px}
.toc a:hover{color:var(--accs);background:#0d1520}
.toc a .pg{font-family:JetBrainsMono;color:var(--acc);font-size:12px;font-weight:700}
.toc a .dots{flex:1;border-bottom:1px dotted #2a3a4a;transform:translateY(-4px)}
/* part opener */
.part{margin:70px 0 0;padding-top:26px;border-top:1px solid var(--lines);position:relative}
.part .ghost{position:absolute;top:34px;inset-inline-end:auto;inset-inline-start:0;
  font-family:JetBrainsMono;font-weight:700;font-size:86px;color:#141d28;line-height:1;pointer-events:none}
.part .pk{font-family:JetBrainsMono;color:var(--acc);letter-spacing:.3em;font-size:12px;font-weight:700}
.part h1{font-size:clamp(26px,4.4vw,40px);font-weight:800;color:var(--ink);margin:6px 0 4px}
.part .pgrad{height:3px;width:220px;border-radius:2px;margin:10px 0 6px;
  background:linear-gradient(270deg,var(--acc),transparent)}
.part .kick{color:var(--accs);font-weight:700;margin:4px 0}
.part .note{color:var(--dim);font-style:italic;font-size:13.5px}
/* sections */
h2.sec{color:var(--ink);font-size:20px;font-weight:700;margin:38px 0 10px;padding-bottom:10px;
  border-bottom:1px solid var(--line);position:relative}
h2.sec:before{content:"";position:absolute;bottom:-1px;inset-inline-start:0;width:0}
h2.sec:after{content:"";position:absolute;bottom:-1.5px;inset-inline-end:0;width:56px;height:3px;background:var(--acc)}
h3.sub{color:var(--accs);font-size:16.5px;font-weight:700;margin:26px 0 8px;padding-inline-start:12px;
  border-inline-start:3px solid var(--acc)}
p{margin:10px 0}
strong{color:var(--ink)}
em{color:#9AADC0}
code{font-family:JetBrainsMono;font-size:.86em;color:var(--accs);background:#101a26;
  border-radius:5px;padding:1px 6px}
/* marks */
.mk{display:inline-block;vertical-align:-2px}
.mk.box{width:13px;height:13px;border:1.5px solid #46586A;border-radius:4px;margin-inline-end:2px}
.mk.dot{width:10px;height:10px;border-radius:50%;margin-inline-end:2px}
.mk.dot.green{background:var(--green);box-shadow:0 0 0 3px rgba(52,211,153,.18)}
.mk.dot.amber{background:var(--amber);box-shadow:0 0 0 3px rgba(245,176,76,.18)}
.mk.dot.red{background:var(--red);box-shadow:0 0 0 3px rgba(248,113,113,.18)}
.mk.ok{color:var(--green);font-weight:700}
.mk.no{color:var(--red);font-weight:700}
.badge.new{font-family:JetBrainsMono;font-size:10px;font-weight:700;letter-spacing:.14em;color:var(--amber);
  background:#3A2A12;border:1px solid var(--amber);border-radius:999px;padding:2px 9px;
  vertical-align:2px;margin-inline-start:8px}
/* tables */
.tbl{overflow-x:auto;margin:16px 0;border:1px solid var(--line);border-radius:10px}
table{width:100%;border-collapse:collapse;font-size:13.8px}
th{background:var(--head);color:var(--accs);font-weight:700;text-align:right;padding:10px 12px;
  border-bottom:2px solid var(--acc)}
td{padding:9px 12px;border-bottom:1px solid var(--lines);vertical-align:top}
tbody tr:nth-child(even){background:var(--panel)}
tbody tr:last-child td{border-bottom:none}
td.cx{text-align:center}
/* lists */
ul.bul{margin:10px 0;padding:0;list-style:none}
ul.bul li{padding-inline-start:20px;position:relative;margin:7px 0}
ul.bul li:before{content:"";position:absolute;inset-inline-start:2px;top:12px;width:7px;height:7px;background:var(--acc)}
ul.check{margin:10px 0;padding:0;list-style:none}
ul.check li{margin:8px 0;display:flex;gap:10px;align-items:flex-start}
ul.check li .mk.box{margin-top:7px}
ol.num{margin:10px 0;padding:0;list-style:none;counter-reset:n}
ol.num li{counter-increment:n;margin:9px 0;display:flex;gap:10px}
ol.num li:before{content:counter(n,decimal-leading-zero);font-family:JetBrainsMono;font-size:11px;font-weight:700;
  color:var(--acc);background:#0C1A22;border:1px solid var(--accd);border-radius:7px;
  padding:3px 7px;height:fit-content;margin-top:4px}
.cgrid{display:grid;grid-template-columns:1fr 1fr;gap:8px 26px;margin:12px 0}
.citem{display:flex;gap:9px;align-items:flex-start;font-size:14px}
.citem .mk.box{margin-top:7px}
/* callouts */
.callout{background:var(--panel2);border:1px solid var(--line);border-inline-end:4px solid var(--acc);
  border-radius:10px;padding:14px 20px;margin:16px 0;position:relative}
.callout.pt{border-inline-end-color:var(--amber)}
.callout .cln{margin:4px 0}
.callout .cli{margin:4px 0;padding-inline-start:16px;position:relative}
.callout .cli:before{content:"";position:absolute;inset-inline-start:2px;top:12px;width:6px;height:6px;background:var(--accs)}
.ptchip{position:absolute;top:-11px;inset-inline-start:16px;font-family:JetBrainsMono;font-size:10px;
  font-weight:700;letter-spacing:.1em;color:var(--amber);background:#3A2A12;border:1px solid var(--amber);
  border-radius:999px;padding:2px 10px}
.callout.pt{margin-top:22px}
/* diagrams */
pre.code{background:#0D141D;border:1px solid var(--line);border-inline-start:3px solid var(--accd);
  border-radius:10px;padding:14px 18px;overflow-x:auto;direction:ltr;text-align:left;
  font-family:JetBrainsMono,monospace;font-size:12.4px;line-height:1.85;color:#9FB6CC}
.chain{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:14px 0}
.chain .cstep{background:var(--panel2);border:1px solid var(--accd);border-radius:9px;
  padding:7px 14px;font-weight:700;color:var(--ink);font-size:13.5px}
.chain .carr{color:var(--acc);font-weight:700}
.chain.v{flex-direction:column;align-items:stretch}
.chain.v .cstep{text-align:center}
.chain.v .carr{text-align:center;line-height:1}
.t43{display:flex;gap:10px;margin:18px 0 6px}
.t43 .ph{border-radius:10px;padding:12px 16px;text-align:center}
.t43 .ph b{font-family:JetBrainsMono;letter-spacing:.25em;font-size:15px;display:block}
.t43 .ph span{font-size:12.5px;font-weight:600}
.t43 .learn{flex:4;background:#0E2A34;border:1.5px solid var(--acc);color:var(--accs)}
.t43 .learn b{color:var(--acc)}
.t43 .build{flex:3;background:#2E203C;border:1.5px solid var(--violet);color:#C8B4F0}
.t43 .build b{color:var(--violet)}
.t43cap{color:var(--dim);font-size:12.5px;margin:2px 0 10px}
.pillars{margin:18px 0}
.proot{width:fit-content;margin:0 auto;background:#0E2A34;border:1.5px solid var(--acc);color:var(--accs);
  font-weight:700;border-radius:10px;padding:8px 22px}
.pcon{width:2px;height:16px;background:var(--acc);margin:0 auto}
.pkids{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px;position:relative}
.pkids:before{content:"";position:absolute;top:-14px;inset-inline:16%;height:2px;background:var(--acc)}
.pkid{background:var(--panel2);border:1px solid var(--accd);border-radius:10px;padding:10px;text-align:center}
.pkid b{display:block;color:var(--ink)}
.pkid span{font-family:JetBrainsMono;font-size:11px;color:var(--dim)}
.hr{height:1px;background:var(--lines);margin:26px 0}
/* back */
.back{margin-top:80px;text-align:right}
.back h1{font-size:34px;color:var(--ink);font-weight:800}
.back .q{color:var(--accs);font-size:20px;font-weight:700;margin:6px 0}
.back .brand{font-family:JetBrainsMono;letter-spacing:.2em;color:var(--ink);font-weight:700;margin-top:26px}
.back .tag{font-family:JetBrainsMono;letter-spacing:.16em;color:var(--dim);font-size:12px}
footer{border-top:1px solid var(--line);margin-top:60px;padding:22px;text-align:center;
  color:var(--faint);font-family:JetBrainsMono;font-size:11px;letter-spacing:.12em}
@media print{
  #bar{display:none}
  body{background:#0B0F14;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  main{max-width:none;padding:0}
  .part{page-break-before:always}
  .tbl,.callout{page-break-inside:avoid}
  @page{size:A4;margin:12mm}
}
"""


def render(docs, out_dir):
    os.makedirs(os.path.join(out_dir, "fonts"), exist_ok=True)
    for f in os.listdir(os.path.join(ROOT, "assets", "fonts")):
        if f.endswith(".ttf"):
            shutil.copy(os.path.join(ROOT, "assets", "fonts", f),
                        os.path.join(out_dir, "fonts", f))
    P = []
    P.append('<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8">')
    P.append('<meta name="viewport" content="width=device-width,initial-scale=1">')
    P.append("<title>PHANTOMS // PROJECT BLUEPRINT</title>")
    P.append(f"<style>{CSS}</style></head><body>")
    P.append('<div id="bar"><span class="brand">PHANTOMS</span>'
             '<span class="sub">// PROJECT BLUEPRINT — 2026</span><span class="sp"></span>'
             '<a href="PHANTOMS-Project-Blueprint.pdf" download>⤓ PDF</a>'
             '<button onclick="window.print()">⎙ PRINT</button>'
             '<a href="#toc">CONTENTS</a></div><main>')
    # cover
    P.append('<section class="cover"><div class="kick">PHANTOMS</div>'
             '<div class="kick2">TECH BEYOND THE ORDINARY</div><div class="grad"></div>'
             "<h1>PROJECT BLUEPRINT</h1>"
             "<h2>دليل الطالب لبناء مشروع تخرج قابل للتنفيذ والمناقشة</h2>"
             '<div class="pipe">Idea &gt; Scope &gt; Architecture &gt; Prototype &gt; Testing &gt; '
             'Documentation &gt; Presentation &gt; Defense &gt; Approval</div>'
             '<div class="quote">الفكرة الصح مش أكبر فكرة.<br>الفكرة الصح هي اللي تقدروا تثبتوها.</div>'
             '<div class="gates">' + "".join(f"<span>{g}</span>" for g in
             ["G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7"]) + "</div>"
             '<p style="color:var(--dim);font-size:13px">من الاعتماد الأول لحد توقيع الدكتور — '
             "كل بوابة ليها شرط عبور مكتوب.</p></section>")
    # front blocks
    front = next(d for d in docs if d["meta"].get("kind") == "front")
    P.append('<section class="front">')
    for b in front["blocks"]:
        if b["t"] in ("h1",):
            continue
        if b["t"] == "h2" and plain(b["runs"]).startswith("دليل الطالب"):
            continue
        P.append(block_html(b))
    P.append("</section>")
    # toc
    P.append('<section class="toc" id="toc"><h2>المحتويات</h2>')
    for d in docs:
        m = d["meta"]
        if m.get("part"):
            lbl = m.get("toc") or m.get("title", "")
            anchor = "part-" + m["part"].replace(" ", "-").replace(".", "-")
            P.append(f'<a href="#{anchor}"><span class="pg">{m["part"]}</span>'
                     f"<span>{esc(lbl)}</span><span class=\"dots\"></span></a>")
    P.append("</section>")
    # parts
    for d in docs:
        m = d["meta"]
        if m.get("kind") in ("front", "back"):
            continue
        anchor = "part-" + m["part"].replace(" ", "-").replace(".", "-")
        P.append(f'<section class="part" id="{anchor}">')
        num = m.get("part", "").replace("PART", "").strip() or "APP"
        P.append(f'<div class="ghost">{esc(num)}</div>')
        P.append(f'<div class="pk">{esc(m.get("part",""))}</div>')
        title = esc(m.get("title", ""))
        new = '<span class="badge new">NEW</span>' if m.get("new") else ""
        P.append(f"<h1>{title}{new}</h1><div class=\"pgrad\"></div>")
        if m.get("kicker"):
            P.append(f'<div class="kick">{esc(m["kicker"])}</div>')
        if m.get("note"):
            P.append(f'<div class="note">({esc(m["note"])})</div>')
        for b in d["blocks"]:
            P.append(block_html(b))
        P.append("</section>")
    # back
    back = next(d for d in docs if d["meta"].get("kind") == "back")
    P.append('<section class="back"><h1>الخاتمة</h1>')
    for b in back["blocks"]:
        if b["t"] == "callout":
            for it in b["items"]:
                P.append(f'<div class="q">{inline_html(it["runs"])}</div>')
        elif b["t"] == "p":
            txt = plain(b["runs"])
            if txt.startswith("PHANTOMS //"):
                P.append('<div class="brand">PHANTOMS // TECH BEYOND THE ORDINARY</div>'
                         '<div class="tag">BUILD. LEARN. SHARE. GROW.</div>')
            else:
                P.append(f"<p>{inline_html(b['runs'])}</p>")
        elif b["t"] == "h1":
            pass
    P.append("</section>")
    P.append("<footer>PHANTOMS // PROJECT BLUEPRINT — EDITION 2026 — BUILD. LEARN. SHARE. GROW.</footer>")
    P.append("</main></body></html>")
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8").write("\n".join(P))
    return os.path.join(out_dir, "index.html")


if __name__ == "__main__":
    docs = mdast.load_all(os.path.join(ROOT, "content"))
    print("written", render(docs, WEB))
