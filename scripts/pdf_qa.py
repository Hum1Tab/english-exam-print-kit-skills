#!/usr/bin/env python3
"""Print-production preflight: page size, text clipping, suspicious text overlap, and page thumbnails.

This tool is an early warning, NOT a substitute for visual page inspection.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import fitz
from PIL import Image, ImageDraw, ImageFont


def bounds_intersection(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def validate(doc: fitz.Document, min_edge_mm=4, allow_blank=False, enforce='any'):
    out=[]
    for ix, p in enumerate(doc):
        rect=p.rect
        raw=p.get_text('dict')
        words=p.get_text('words')
        spans=[]
        text_bbox=[]
        for b in raw.get('blocks', []):
            for line in b.get('lines', []):
                for s in line.get('spans', []):
                    if not s['text'].strip(): continue
                    spans.append((s['bbox'],s['text'], s['size']))
                    text_bbox.append(s['bbox'])
        errors=[]; warnings=[]
        if enforce!='any':
            expected=fitz.paper_rect(enforce)
            if abs(rect.width-expected.width)>3 or abs(rect.height-expected.height)>3:
                errors.append(f'Wrong paper size: {rect.width:.1f}x{rect.height:.1f}pt expected {enforce}')
        if not words and not allow_blank:
            warnings.append('No selectable text (blank or image-only page)')
        # flags near edges, allowing page numbers closer to trim.
        bmin=min_edge_mm/25.4*72
        for bbox, text, size in spans:
            x0,y0,x1,y1=bbox
            if x0 < -0.75 or y0 < -0.75 or x1 > rect.width+0.75 or y1 > rect.height+0.75:
                errors.append(f'Text outside physical page: {text[:36]!r} ({bbox})')
            elif x0<bmin or y0<bmin or x1>rect.width-bmin or y1>rect.height-bmin:
                warnings.append(f'Text near trim edge: {text[:25]!r}')
        # Check intersecting WORD rectangles; cut false positives from Japanese kerning.
        items=[(fitz.Rect(w[:4]),w[4],w[5],w[6]) for w in words if len(w[4].strip())>0]
        items.sort(key=lambda item:(item[0].y0,item[0].x0))
        bad=[]
        for k,(a,ta,ba,la) in enumerate(items):
            for b,tb,bb,lb in items[k+1:]:
                if b.y0 > a.y1+0.2: break
                if ta==tb and la==lb: continue
                area = bounds_intersection(a,b)
                if area>0 and area/min(a.get_area(), b.get_area())>0.14 and area>1.6:
                    bad.append((ta,tb,round(area,1)))
                    if len(bad)>8: break
            if len(bad)>8:break
        if bad: warnings.append(f'{len(bad)} possible text collisions, examples: {bad[:4]}')
        # Small fonts informative; don't ban footnotes/page numbers.
        count_small=sum(1 for b,t,size in spans if size<7.2 and t.strip())
        if count_small: warnings.append(f'{count_small} text spans smaller than 7.2pt')
        out.append({'page':ix+1,'size_pt':[round(rect.width,1),round(rect.height,1)],'words':len(words),'errors':sorted(set(errors)), 'warnings':sorted(set(warnings))})
    return out


def render(doc, outdir, dpi=160, contact_cols=3):
    outdir.mkdir(parents=True, exist_ok=True)
    imgs=[]
    for i,p in enumerate(doc):
        pix=p.get_pixmap(matrix=fitz.Matrix(dpi/72,dpi/72), alpha=False)
        fp=outdir/f'page-{i+1:02}.png'
        pix.save(fp)
        im=Image.open(fp).convert('RGB')
        im.thumbnail((310, 440))
        imgs.append(im.copy())
    cw, ch, gap = 320, 464, 16
    cols=min(contact_cols,len(imgs)) if imgs else 1
    rows=math.ceil(len(imgs)/cols)
    sheet=Image.new('RGB',(cols*cw+(cols+1)*gap,rows*ch+(rows+1)*gap),'#eaeaea')
    draw=ImageDraw.Draw(sheet)
    for i,im in enumerate(imgs):
        x=gap+(i%cols)*(cw+gap)+(cw-im.width)//2
        y=gap+(i//cols)*(ch+gap)
        sheet.paste(im,(x,y))
        draw.text((gap+(i%cols)*(cw+gap)+10,y+444),f'{i+1}',fill='#333')
    sheet.save(outdir/'contact_sheet.png')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--out-dir',type=Path,required=True)
    ap.add_argument('--dpi',type=int,default=160)
    ap.add_argument('--enforce',default='any',choices=['any','a4','a5','a4-l'])
    ap.add_argument('--allow-blank',action='store_true')
    args=ap.parse_args();args.out_dir.mkdir(parents=True,exist_ok=True)
    with fitz.open(args.input) as doc:
        rows=validate(doc,allow_blank=args.allow_blank,enforce=args.enforce)
        render(doc,args.out_dir,args.dpi)
        (args.out_dir/'report.json').write_text(json.dumps({'file':str(args.input),'pages':len(rows),'checks':rows},ensure_ascii=False,indent=2),encoding='utf8')
        err=sum(len(x['errors']) for x in rows)
        warn=sum(len(x['warnings']) for x in rows)
        print(f'Pages {len(rows)} | errors {err} | warnings {warn}')
        print(f'See {args.out_dir}/contact_sheet.png and report.json')
        for p in rows:
            if p['errors'] or p['warnings']:
                print(f'  Page {p["page"]}: {len(p["errors"])} errors / {len(p["warnings"])} warnings')
        if err: raise SystemExit(2)


if __name__=='__main__': main()
