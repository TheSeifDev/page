"""PHANTOMS Blueprint — markdown subset parser -> AST (shared by PDF & web renderers)."""
import re, json, glob, os

EMOJI = {
    "✅": "[[ok]]", "❌": "[[no]]", "🟢": "[[dot:green]]", "🟡": "[[dot:amber]]",
    "🔴": "[[dot:red]]", "☐": "[[box]]", "🆕": "[[new]]", "✓": "[[tick]]",
    "🧠": "[[emo:brain]]", "🔨": "[[emo:hammer]]",
}

def norm(text: str) -> str:
    for k, v in EMOJI.items():
        text = text.replace(k, v)
    return text

INLINE_RE = re.compile(r"(\*\*.+?\*\*|\*[^*\n]+?\*|`[^`\n]+?`|\[\[[a-z:]+\]\])")

MARK_RE = re.compile(r"\[\[[a-z:]+\]\]")
ARAB = re.compile(r"[\u0600-\u06ff]")

def _chunk(val):
    """split a styled segment into arabic / latin word-chunks"""
    words = val.split(" ")
    chunks, cur, cur_cls = [], [], None
    for i, w in enumerate(words):
        cls = "A" if ARAB.search(w) else "L"
        if cur_cls is None:
            cur_cls = cls
        if cls != cur_cls:
            chunks.append((cur_cls, " ".join(cur)))
            cur, cur_cls = [], cls
        cur.append(w)
    if cur:
        chunks.append((cur_cls, " ".join(cur)))
    out = []
    for i, (cls, txt) in enumerate(chunks):
        out.append(txt + (" " if i < len(chunks) - 1 else ""))
    return out

def inline(text: str):
    """-> list of segments {'s': 't'|'b'|'i'|'c'|'m', 'v': str, 'k': mark-kind}"""
    out = []

    def push(style, val):
        pos = 0
        def emit(text):
            if style in ("t", "b", "i") and text.strip():
                lead = text[:len(text) - len(text.lstrip(" "))]
                tail = text[len(text.rstrip(" ")):]
                if lead:
                    out.append({"s": style, "v": lead})
                for ch in _chunk(text.strip()):
                    out.append({"s": style, "v": ch})
                if tail:
                    out.append({"s": style, "v": tail})
            elif text:
                out.append({"s": style, "v": text})
        for m in MARK_RE.finditer(val):
            if m.start() > pos:
                emit(val[pos:m.start()])
            out.append({"s": "m", "v": "", "k": m.group(0)[2:-2]})
            pos = m.end()
        if pos < len(val):
            emit(val[pos:])

    for piece in INLINE_RE.split(norm(text)):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**") and len(piece) > 4:
            push("b", piece[2:-2])
        elif piece.startswith("*") and piece.endswith("*") and len(piece) > 2:
            push("i", piece[1:-1])
        elif piece.startswith("`") and piece.endswith("`") and len(piece) > 2:
            push("c", piece[1:-1])
        elif piece.startswith("[[") and piece.endswith("]]"):
            out.append({"s": "m", "v": "", "k": piece[2:-2]})
        else:
            push("t", piece)
    return out

def is_mark_only(runs):
    return len(runs) == 1 and runs[0]["s"] == "m"

def plain(runs):
    return "".join(r["v"] for r in runs if r["s"] != "m")

def has_mark(runs, kind):
    return any(r["s"] == "m" and r["k"] == kind for r in runs)

def split_table_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]

SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}.*\|")

def parse_file(path):
    raw = open(path, encoding="utf-8").read().replace("\r\n", "\n")
    blocks = []
    meta = {}
    lines = raw.split("\n")
    i = 0
    if lines and lines[0].strip() == "---":
        j = lines.index("---", 1)
        for l in lines[1:j]:
            if ":" in l:
                k, v = l.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
        i = j + 1

    def flush_para(buf):
        if buf:
            blocks.append({"t": "p", "runs": inline(" ".join(buf))})
            buf.clear()

    para_buf = []
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            flush_para(para_buf)
            i += 1
            continue
        if s == "---":
            flush_para(para_buf)
            blocks.append({"t": "hr"})
            i += 1
            continue
        if s.startswith("```"):
            flush_para(para_buf)
            kind = s[3:].strip() or "code"
            buf = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            blocks.append({"t": "code", "kind": kind, "text": "\n".join(buf)})
            continue
        if s.startswith(">"):
            flush_para(para_buf)
            q = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                q.append(lines[i].strip().lstrip(">").strip())
                i += 1
            items = []
            for l in q:
                if not l:
                    continue
                if l.startswith("- "):
                    items.append({"t": "li", "runs": inline(l[2:])})
                else:
                    items.append({"t": "ln", "runs": inline(l)})
            blocks.append({"t": "callout", "items": items})
            continue
        if s.startswith("#"):
            flush_para(para_buf)
            lvl = len(s) - len(s.lstrip("#"))
            txt = s.lstrip("#").strip()
            blocks.append({"t": f"h{min(lvl,4)}", "runs": inline(txt)})
            i += 1
            continue
        if s.startswith("|"):
            flush_para(para_buf)
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            head = split_table_row(rows[0])
            body = [split_table_row(r) for r in rows[2:] if not SEP_RE.match(r)]
            if len(rows) > 1 and SEP_RE.match(rows[1]):
                blocks.append({"t": "table", "head": [inline(c) for c in head],
                               "rows": [[inline(c) for c in r] for r in body]})
            else:
                blocks.append({"t": "table", "head": None,
                               "rows": [[inline(c) for c in r] for r in [head] + body]})
            continue
        m = re.match(r"^(\d+)\.\s+(.*)$", s)
        if m:
            flush_para(para_buf)
            items = []
            while i < len(lines):
                mm = re.match(r"^(\d+)\.\s+(.*)$", lines[i].strip())
                if not mm:
                    break
                items.append(inline(mm.group(2)))
                i += 1
            blocks.append({"t": "olist", "items": items})
            continue
        if s.startswith("- "):
            flush_para(para_buf)
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(inline(lines[i].strip()[2:]))
                i += 1
            if all(has_mark(it, "box") and plain(it).strip() for it in items):
                blocks.append({"t": "check", "items": items})
            else:
                blocks.append({"t": "ulist", "items": items})
            continue
        para_buf.append(s)
        i += 1
    flush_para(para_buf)
    return {"meta": meta, "blocks": blocks, "file": os.path.basename(path)}

def load_all(content_dir):
    docs = []
    for p in sorted(glob.glob(os.path.join(content_dir, "*.md"))):
        docs.append(parse_file(p))
    return docs

if __name__ == "__main__":
    import sys
    docs = load_all(sys.argv[1] if len(sys.argv) > 1 else "content")
    print(json.dumps(docs, ensure_ascii=False)[:600])
    print("files:", len(docs), "blocks:", sum(len(d["blocks"]) for d in docs))
