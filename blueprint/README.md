# PHANTOMS // PROJECT BLUEPRINT

دليل الطالب لبناء مشروع تخرج قابل للتنفيذ والمناقشة — إصدار 2026.
المحتوى كامل في `content/` (Markdown)، والتصميم بيتبنى منه لناتجين:

| الناتج | المسار | الوصف |
|---|---|---|
| PDF جاهز للطباعة | `dist/PHANTOMS-Project-Blueprint.pdf` | A4، RTL، 52+ صفحة، خطوط مضمّنة |
| نسخة ويب (معاينة حية + طباعة) | `dist/web/index.html` | نفس الهوية، scroll + print CSS |

## البناء

```bash
cd blueprint
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python tools/build.py            # PDF + web
.venv/bin/python tools/build.py --pdf-only # PDF بس
```

معاينة حية محلية:

```bash
cd dist/web && python3 -m http.server 8080 --bind 0.0.0.0
```

## بنية المجلد

```
blueprint/
  content/        مصدر المحتوى الوحيد (Markdown مرقّم بالترتيب)
  design/tokens.json   الألوان والخطوط وهندسة الصفحة (مشتركة بين الناتجين)
  assets/fonts/   Alexandria + JetBrains Mono (OFL) — TTF مضمّنة في الـ PDF
  tools/
    mdast.py      parser: Markdown subset -> AST (جداول/قوائم/callouts/diagrams/emarks)
    render_pdf.py محرك الـ PDF: fpdf2 + HarfBuzz shaping + BiDi عربي/لاتيني
    render_web.py مولّد HTML/CSS للنسخة الويب
    build.py      أمر البناء الواحد
  dist/           نواتج البناء (الـ PDF مت-commit؛ web/ بيتبنى محلياً)
```

## قواعد المحتوى (مهم لمن يعدّل)

- **الترقيم ثابت:** الأقسام مرقّمة 01–73 عبر الـ PARTs — أي قسم جديد ياخد رقمه
  من تسلسله هو مش من مكانه (مثال: PART 00.5 واقف لوحده من غير ما يلمس ترقيم).
- الـ emojis اللي ليها معنى حالة (🟢🟡 ✅❌ ☐ 🆕 ✓) بتتحول تلقائياً لعناصر
  مرسومة vector في الـ PDF وCSS في الويب — سيبها زي ما هي في الـ Markdown.
- `[[box]] / [[ok]] / [[no]] / [[dot:green]] / [[new]] / [[tick]]` tokens مكافئة
  للـ emojis لو حبيت تكتبها يدوي.
- أي فقرة فيها أكتر من `[[box]]` بتترسم شبكة checklist بعمودين تلقائياً.
- الـ code fences بأنواعها: `flow` و`tree` و`erd` (بلوك mono)، `diagram`
  (سلاسل خطوات أو سلم رأسي)، `pillars` (مخطط الركائز الثلاثة)،
  و4+3 بيتعرف تلقائياً من كلمة LEARN/BUILD.
- أي callout فيه كلمة "PharmaTrack" بياخد بادج "RUNNING EXAMPLE" كهرماني تلقائياً.

## ملاحظات الإنتاج الأصلية (من مؤلف المحتوى — مش جزء من الـ PDF)

شايف `PRODUCTION-NOTES.md`.
