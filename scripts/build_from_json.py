#!/usr/bin/env python3
"""Deterministic A4 answer / vocabulary and A5 read-aloud booklet compiler.

Content validation must be done BY THE AI before compiling. This builder never guesses answers,
Japanese translations, source wording, or revised LEAP IDs.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from html import escape
import json
from pathlib import Path
import subprocess
import sys
import math
import fitz
from weasyprint import HTML

ROOT=Path(__file__).resolve().parent

def h(value):return escape(str(value or ''),quote=True)
def text(value):return h(value).replace('\n','<br>')
def tag(s):return f'<span class="lab">{h(s)}</span>'

CSS_BASE='''
@page {size: A4; margin: 12mm 13mm 14mm 13mm;
 @bottom-center{content:counter(page);font-family:"Noto Sans CJK JP";color:#777;font-size:7.5pt;}}
*{box-sizing:border-box} body{font-family:"Noto Sans CJK JP","Noto Sans",sans-serif;color:#222;font-size:9pt;line-height:1.58}
h1{font-size:14pt;margin:0 0 3mm;font-weight:700}h2{font-size:11pt;border-bottom:.6px solid #888;padding-bottom:1mm;margin:4mm 0 2mm;break-after:avoid}
h3{font-size:9.4pt;margin:3mm 0 1mm;break-after:avoid}
p{margin:.7mm 0 1.3mm;orphans:2;widows:2}.muted{color:#666;font-size:7.5pt}
.key{font-size:8pt;padding:1.2mm 0 2mm;border-bottom:.6px solid #bbb;margin-bottom:2.5mm}
.rsentence{break-inside:avoid;padding:1.7mm 0 2mm;border-bottom:.55px solid #ddd}
.en{font-family:"Noto Sans","Noto Sans CJK JP",sans-serif;font-size:9.2pt;line-height:1.7;overflow-wrap:normal;word-break:normal}
.tok{border-bottom:.5px solid #aaa}.role{font-size:6.7pt;color:#555;letter-spacing:0;vertical-align:baseline;margin-right:1pt;font-weight:750}
.tip{font-size:8.4pt;line-height:1.58;margin:1.1mm 0}.label{color:#555;font-weight:700;font-size:7.5pt;margin-right:1.8mm}
.jp{font-size:8.65pt;line-height:1.58;margin:1mm 0}.trap{font-size:8.15pt;color:#333}.logic{font-size:8.15pt;color:#4c4c4c}
.phead{font-size:9.2pt;font-weight:700;border-bottom:.5px solid #ccc;margin:3.3mm 0 1.4mm;padding-bottom:.6mm;break-after:avoid}
.item{padding:1.4mm 0 2mm;border-bottom:.5px solid #ddd;break-inside:avoid}
.table-grid{display:flex;gap:5mm}.table-grid table{width:50%;table-layout:fixed}.lex{border-collapse:collapse;font-size:7.9pt;line-height:1.5}
.lex td,.lex th{padding:1.35mm 1.1mm;border-bottom:.55px solid #ddd;vertical-align:top;overflow-wrap:break-word}
.lex th{background:#eee;text-align:left;font-weight:700}.lex td.enword{font-family:"Noto Sans",sans-serif;font-weight:650;word-break:normal;overflow-wrap:normal}
.lex td.no{width:10mm;white-space:nowrap;text-align:right}.lex td.reading{white-space:normal}.unit-page{break-before:page}
.reading-label{font-size:8pt;color:#666}.lex-heading{font-size:11pt;margin:0 0 2mm}
'''

CSS_MINI='''
@page {size:A5; margin:9mm 9mm 9.5mm 9mm}
*{box-sizing:border-box}
body{font-family:"Noto Sans CJK JP","Noto Sans",sans-serif;font-size:8.8pt;line-height:1.52;color:#161616}
h1{font-size:16pt;margin:0 0 5mm}h2{font-size:10.8pt;border-bottom:.5px solid #aaa;padding-bottom:1.2mm;margin:0 0 3.6mm}
p{margin:0 0 2.6mm;orphans:2;widows:2}.mini-reading{font-family:"Noto Sans","Noto Sans CJK JP",sans-serif;word-break:normal;overflow-wrap:normal;line-height:1.48}
.mini-jp{line-height:1.58}.hint{font-size:7.7pt;color:#777}.entry{break-inside:avoid;margin-bottom:2.2mm;line-height:1.36;font-size:7.5pt}
.term{font-family:"Noto Sans",sans-serif;font-weight:700}.meaning{font-size:7.4pt}.mini-cols{column-count:2;column-gap:5mm}
.underline{border-bottom:1px solid #999;height:8mm;margin:2mm 0}.small{font-size:7.8pt;color:#666}
'''

def html_page(body, extra='', css=CSS_BASE):
    return '<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><style>'+css+extra+'</style></head><body>'+body+'</body></html>'


def render_pdf(body, out, css=CSS_BASE, extra=''):
    src=html_page(body,extra,css)
    HTML(string=src, base_url=str(out.parent)).write_pdf(out)
    return fitz.open(out)


def validate(data):
    if not isinstance(data.get('reading',{}).get('sentences'),list) or not data['reading']['sentences']:
        raise ValueError('reading.sentences must be a nonempty array')
    for i,s in enumerate(data['reading']['sentences']):
        if not s.get('english') or not s.get('translation'):
            raise ValueError(f'sentence {i+1}: missing english or translation')
        if s.get('markup') and ''.join(chunk.get('text','') for chunk in s['markup']) != s['english']:
            raise ValueError(f'sentence {i+1}: markup text does not exactly match english; do not silently fix source text')
    for row in data['reading'].get('vocabulary',[])+data['reading'].get('idioms',[]):
        v=row.get('leap_revised_no')
        if v is not None and (not isinstance(v,int) or isinstance(v,bool) or v<=0):
            raise ValueError(f'Invalid LEAP index: {v!r}. Use an independently verified integer or null')
        if v is not None and row.get('leap_verified') is not True:
            raise ValueError(f'LEAP index {v} for {row.get("word",row.get("phrase"))!r} has no leap_verified=true flag. Check the revised edition index first.')
    return data


def annotation(sentence):
    if not sentence.get('markup'):
        return h(sentence['english'])
    out=[]
    for m in sentence['markup']:
        label=m.get('role')
        piece=h(m.get('text',''))
        if label: out.append(f'<span class="tok"><span class="role">{h(label)}</span>{piece}</span>')
        else:out.append(piece)
    return ''.join(out)


def grouped_paragraphs(sentences,key):
    groups=[]
    for i,s in enumerate(sentences):
        p=s.get('paragraph',1)
        if not groups or groups[-1][0]!=p:groups.append([p,[]])
        groups[-1][1].append(s[key].strip())
    return [' '.join(g[1]) if key=='english' else ''.join(g[1]) for g in groups]


def answer_pdf(data,out):
    reading=data['reading']; body=[f'<h1>{h(data.get("title","英語過去問"))}　解答・解説</h1>']
    if data.get('source_limitations'):
        body.append('<p class="muted">'+h('／'.join(data['source_limitations']))+'</p>')
    body.append('<h2>長文｜構文・和訳</h2>')
    last=None
    for i,s in enumerate(reading['sentences'],1):
        if s.get('paragraph')!=last:
            last=s.get('paragraph')
            if s.get('paragraph_note'):body.append(f'<div class="phead">{h(s["paragraph_note"])}</div>')
        body.append('<article class="rsentence">')
        body.append(f'<div class="en">{annotation(s)}</div>')
        if s.get('explanation'):body.append(f'<p class="tip"><span class="label">構文</span>{text(s["explanation"])}</p>')
        if s.get('logic'):body.append(f'<p class="logic"><span class="label">読解</span>{text(s["logic"])}</p>')
        if s.get('trap'):body.append(f'<p class="trap"><span class="label">注意</span>{text(s["trap"])}</p>')
        body.append(f'<p class="jp"><span class="label">訳</span>{text(s["translation"])}</p>')
        body.append('</article>')
    if reading.get('cloze'):
        body.append('<h2>空所補充｜正答の根拠</h2>')
        for x in reading['cloze']:
            body.append('<article class="item">')
            body.append(f'<b>{h(x.get("blank",""))}　{h(x.get("correct",""))}</b>')
            body.append(f'<p>{text(x.get("why",""))}</p>')
            if x.get('other_choices'):body.append(f'<p class="muted">他の選択肢：{text(x["other_choices"])}</p>')
            body.append('</article>')
    for sec in data.get('sections',[]):
        if not sec.get('items'): continue
        body.append(f'<h2>{h(sec.get("name","問題"))}</h2>')
        for x in sec['items']:
            body.append('<article class="item">')
            body.append(f'<b>{h(x.get("label",""))}　正答 {h(x.get("answer",""))}</b>')
            if x.get('english'):body.append(f'<div class="en">{h(x["english"])}</div>')
            if x.get('explanation'):body.append(f'<p>{text(x["explanation"])}</p>')
            if x.get('other_choices'):body.append(f'<p class="muted">誤答：{text(x["other_choices"])}</p>')
            body.append('</article>')
    doc=render_pdf('\n'.join(body),out)
    if doc.page_count<1:raise ValueError('Failed to produce answer PDF')
    return doc.page_count


def vocab_table(items, is_idiom=False):
    c=[f'<table class="lex"><thead><tr><th style="width:{"54" if is_idiom else "35"}%">{"表現" if is_idiom else "単語"}</th>']
    if not is_idiom:c.append('<th style="width:22%">読み</th>')
    c.append('<th>意味</th><th style="width:14%">LEAP</th></tr></thead><tbody>')
    for row in items:
        term=row.get('phrase') if is_idiom else row.get('word')
        c.append('<tr><td class="enword">'+h(term)+'</td>')
        if not is_idiom:c.append('<td class="reading">'+h(row.get('reading',''))+'</td>')
        meaning=row.get('meaning','')
        if is_idiom and row.get('note'):meaning += '／'+row['note']
        c.append('<td>'+h(meaning)+'</td>')
        no=row.get('leap_revised_no')
        c.append('<td class="no">'+str(no) if no is not None else '<td class="no">—')
        c.append('</td></tr>')
    return ''.join(c)+'</tbody></table>'


def vocab_pdf(data,out):
    voc=data['reading'].get('vocabulary',[])
    idi=data['reading'].get('idioms',[])
    pages=[]; files=[]
    # Fill pages dynamically; the exact number of rows depends on phrase length and Japanese wrapping.
    for items,is_idiom,title,max_rows in [
        (voc,False,'長文の単語｜改訂版LEAP',30),
        (idi,True,'長文の熟語・重要表現',22)
    ]:
        remaining=list(items)
        while remaining:
            success=False
            for rows_per_col in range(min(max_rows,math.ceil(len(remaining)/2)),0,-1):
                chunk=remaining[:rows_per_col*2]
                halfway=math.ceil(len(chunk)/2)
                body=f'<h1>{h(title)}</h1><div class="table-grid">{vocab_table(chunk[:halfway],is_idiom)}{vocab_table(chunk[halfway:],is_idiom)}</div>'
                tmp=out.parent/f'__vocabpage_{len(pages)+1}.pdf'
                d=render_pdf(body,tmp)
                if d.page_count == 1:
                    pages.append(d);files.append(tmp)
                    remaining=remaining[len(chunk):]
                    success=True
                    break
                d.close()
            if not success:
                raise ValueError('Even six entries per column overflow A4. A phrase may be excessively long: revise layout; do not shrink fonts beyond legibility.')
    if not pages:
        tmp=out.parent/'__vocabpage_1.pdf'
        pages.append(render_pdf('<h1>長文の単語・熟語</h1><p>登録された語句はありません。</p>',tmp))
        files.append(tmp)
    merged=fitz.open()
    for d in pages:merged.insert_pdf(d);d.close()
    merged.save(out,garbage=4,deflate=True)
    for p in files:p.unlink(missing_ok=True)
    return merged.page_count


def mini_pdf(data,out):
    title=data.get('title','英語過去問');reading=data['reading']
    sens=reading['sentences']; voc=reading.get('vocabulary',[]);idi=reading.get('idioms',[])
    contents=[None]*8
    contents[0]=f'<h1>{h(title)}</h1><p>{h(reading.get("theme","長文音読"))}</p><p class="small">音読練習用</p>'
    paragraphs_en=grouped_paragraphs(sens,'english')
    paragraphs_jp=grouped_paragraphs(sens,'translation')
    contents[1]='<h2>英文</h2><div class="mini-reading">'+''.join('<p>'+h(x)+'</p>' for x in paragraphs_en)+'</div>'
    contents[2]='<h2>和訳</h2><div class="mini-jp">'+''.join('<p>'+h(x)+'</p>' for x in paragraphs_jp)+'</div>'
    # Balanced pages: vocabulary -> 4,5, idioms -> 6,7.
    for k in (0,1):
        lo=math.ceil(len(voc)/2)*k;hi=math.ceil(len(voc)/2)*(k+1)
        vals=voc[lo:hi]
        cells=[]
        for v in vals:
            n=v.get('leap_revised_no')
            cells.append('<div class="entry"><span class="term">'+h(v.get('word',''))+'</span> '+h(v.get('reading',''))+
                ' <span class="small">'+str(n if n is not None else '—')+'</span><br><span class="meaning">'+h(v.get('meaning',''))+'</span></div>')
        contents[3+k]='<h2>長文単語'+('（続き）' if k else '')+'</h2><div class="mini-cols">'+''.join(cells)+'</div>'
    for k in (0,1):
        lo=math.ceil(len(idi)/2)*k;hi=math.ceil(len(idi)/2)*(k+1)
        vals=idi[lo:hi]
        cells=[]
        for v in vals:
            cells.append('<div class="entry"><span class="term">'+h(v.get('phrase',''))+'</span><br><span class="meaning">'+h(v.get('meaning',''))+'</span></div>')
        contents[5+k]='<h2>熟語・重要表現'+('（続き）' if k else '')+'</h2><div class="mini-cols">'+''.join(cells)+'</div>'
    contents[7]='<h2>音読・復習</h2><p>今日の音読回数： ______ 回</p><p>分からなかった表現</p>'+''.join('<div class="underline"></div>' for _ in range(7))
    docs=[];temp=[]
    for i,body in enumerate(contents):
        success=False
        # Keep font >= 8pt for the actual long-form reading. Never silently squeeze below that threshold.
        variants = []
        if i in (1,2):
            for pt in [8.9,8.5,8.2,8.0]:
                variants.append(f'.mini-reading, .mini-jp{{font-size:{pt}pt;}}')
            # The 2-column fallback offers another readable layout before rejecting an unusually long passage.
            for pt in [8.7,8.4,8.0]:
                variants.append(f'.mini-reading, .mini-jp{{font-size:{pt}pt;column-count:2;column-gap:4.5mm;line-height:1.48}} .mini-reading p, .mini-jp p{{break-inside:avoid;}}')
        else:
            variants=['']
        for extra in variants:
            tmp=out.parent/f'__minipage_{i+1}.pdf'
            d=render_pdf(body,tmp,CSS_MINI,extra)
            if d.page_count == 1:
                docs.append(d);temp.append(tmp);success=True;break
            d.close()
        if not success:
            raise ValueError(f'Mini-book page {i+1} overflows A5. One-page English/Japanese requirement conflicts with readable type size; revise content/layout rather than squeezing below 8pt.')
    merged=fitz.open()
    for d in docs:merged.insert_pdf(d);d.close()
    merged.save(out,garbage=4,deflate=True)
    for p in temp:p.unlink(missing_ok=True)
    return merged.page_count


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',required=True,type=Path)
    ap.add_argument('--out-dir',required=True,type=Path)
    args=ap.parse_args()
    data=validate(json.loads(args.input.read_text(encoding='utf-8')))
    args.out_dir.mkdir(parents=True,exist_ok=True)
    ans=args.out_dir/'解答・構文解説_A4.pdf'
    voc=args.out_dir/'長文単語・熟語_A4.pdf'
    mini=args.out_dir/'音読ミニブック_A5順.pdf'
    print('Created answer pages:',answer_pdf(data,ans))
    print('Created vocab pages:',vocab_pdf(data,voc))
    print('Created mini-book pages:',mini_pdf(data,mini))
    cmd=[sys.executable,str(ROOT/'impose_bundle.py'),'--answers',str(ans),'--vocab',str(voc),'--mini',str(mini),'--out-dir',str(args.out_dir)]
    subprocess.run(cmd,check=True)
    print('Done: all PDFs in',args.out_dir)

if __name__=='__main__':
    try: main()
    except (ValueError,RuntimeError,KeyError) as e:
        print(f'ERROR: {e}',file=sys.stderr)
        sys.exit(2)
