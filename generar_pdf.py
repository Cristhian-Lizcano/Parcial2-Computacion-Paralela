"""Convierte los Markdown de documentos/ a PDF (HTML intermedio + Chrome headless).

Soporta el subconjunto de Markdown usado en los informes: encabezados, parrafos,
listas, tablas, bloques de codigo, negrita, codigo en linea, imagenes y el
marcador <!-- PAGEBREAK -->. Sin dependencias externas salvo google-chrome o
chromium.
"""
import html
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / 'documentos'

CSS = """
@page { size: A4; margin: 18mm 17mm; }
body { font-family: 'DejaVu Serif', 'Liberation Serif', serif; font-size: 10.5pt;
       line-height: 1.38; color: #111; max-width: 100%; }
h1 { font-size: 17pt; margin: 0 0 6pt; }
h2 { font-size: 13.5pt; margin: 14pt 0 5pt; border-bottom: 1px solid #999; }
h3 { font-size: 11.5pt; margin: 11pt 0 3pt; }
p { margin: 0 0 6pt; text-align: justify; }
li { margin-bottom: 3pt; }
table { border-collapse: collapse; margin: 6pt auto 8pt; font-size: 9.5pt; }
th, td { border: 1px solid #777; padding: 2pt 7pt; text-align: center; }
th { background: #eee; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 9pt; }
pre { font-size: 8.3pt; line-height: 1.25; background: #f5f5f5; border: 1px solid #ccc;
      padding: 6pt; white-space: pre-wrap; word-wrap: break-word; margin: 4pt 0 8pt; }
img { display: block; margin: 6pt auto; max-width: 85%; }
.pagebreak { page-break-after: always; }
"""


def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', t)
    return t


def md_a_html(texto):
    out, i, lines = [], 0, texto.splitlines()
    while i < len(lines):
        l = lines[i]
        if l.startswith('```'):
            j = i + 1
            while j < len(lines) and not lines[j].startswith('```'):
                j += 1
            out.append('<pre><code>' + html.escape('\n'.join(lines[i + 1:j])) + '</code></pre>')
            i = j + 1
            continue
        if l.strip() == '<!-- PAGEBREAK -->':
            out.append('<div class="pagebreak"></div>'); i += 1; continue
        m = re.match(r'(#{1,3}) (.*)', l)
        if m:
            n = len(m.group(1)); out.append(f'<h{n}>{inline(m.group(2))}</h{n}>'); i += 1; continue
        if l.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')]); i += 1
            head, body = rows[0], [r for r in rows[2:]]
            out.append('<table><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in head) + '</tr>' +
                       ''.join('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>' for r in body) +
                       '</table>')
            continue
        m = re.match(r'(\d+)\. (.*)|- (.*)', l)
        if m:
            tag = 'ol' if m.group(1) else 'ul'
            items = []
            while i < len(lines) and re.match(r'(\d+\. |- )', lines[i]):
                items.append(re.sub(r'^(\d+\. |- )', '', lines[i])); i += 1
            out.append(f'<{tag}>' + ''.join(f'<li>{inline(x)}</li>' for x in items) + f'</{tag}>')
            continue
        if l.strip() == '':
            i += 1; continue
        par = []
        while i < len(lines) and lines[i].strip() and not re.match(r'(#{1,3} |\||```|- |\d+\. |<!--)', lines[i]):
            par.append(lines[i]); i += 1
        out.append('<p>' + inline(' '.join(par)) + '</p>')
    return '\n'.join(out)


def main():
    chrome = next((c for c in ['google-chrome', 'chromium', 'chromium-browser'] if shutil.which(c)), None)
    if not chrome:
        raise SystemExit('Se necesita google-chrome o chromium')
    for md in sorted(DOCS.glob('*.md')):
        htm = md.with_suffix('.html')
        htm.write_text('<!doctype html><html lang="es"><head><meta charset="utf-8">'
                       f'<title>{md.stem}</title><style>{CSS}</style></head><body>'
                       + md_a_html(md.read_text(encoding='utf-8')) + '</body></html>', encoding='utf-8')
        pdf = md.with_suffix('.pdf')
        subprocess.run([chrome, '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
                        f'--print-to-pdf={pdf}', htm.resolve().as_uri()],
                       check=True, capture_output=True)
        htm.unlink()
        print(pdf)


if __name__ == '__main__':
    main()
