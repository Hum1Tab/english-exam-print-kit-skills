#!/usr/bin/env python3
"""Combine answer/vocabulary PDFs and impose an eight-page A5 booklet for ONE A4 duplex print job."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
import fitz

A4 = fitz.paper_rect('a4')
A4L = fitz.paper_rect('a4-l')
A5 = fitz.paper_rect('a5')


def near(v, expected, tol=3):
    return abs(v - expected) <= tol


def validate_size(doc: fitz.Document, size: fitz.Rect, orientation: str, name: str):
    for i, p in enumerate(doc):
        if not (near(p.rect.width, size.width) and near(p.rect.height, size.height)):
            raise ValueError(f'{name} page {i+1}: requires {orientation} ({size.width:.0f} x {size.height:.0f}pt), got {p.rect.width:.1f} x {p.rect.height:.1f}')


def booklet(a5: fitz.Document) -> fitz.Document:
    # 8 A5 pages -> 2 A4 sheets, printed duplex, short-edge binding in landscape.
    if a5.page_count != 8:
        raise ValueError(f'A5 mini-book must have exactly 8 pages, got {a5.page_count}; do not truncate')
    validate_size(a5, A5, 'A5 portrait', 'mini')
    out = fitz.open()
    half = A4L.width / 2
    for a, b in [(8, 1), (2, 7), (6, 3), (4, 5)]:
        page = out.new_page(width=A4L.width, height=A4L.height)
        page.show_pdf_page(fitz.Rect(0, 0, half, A4L.height), a5, a - 1, keep_proportion=True)
        page.show_pdf_page(fitz.Rect(half, 0, A4L.width, A4L.height), a5, b - 1, keep_proportion=True)
    return out


def combine(answers: fitz.Document, vocab: fitz.Document, booklet_landscape: fitz.Document) -> fitz.Document:
    validate_size(answers, A4, 'A4 portrait', 'answers')
    validate_size(vocab, A4, 'A4 portrait', 'vocab')
    out = fitz.open()
    for src in (answers, vocab):
        out.insert_pdf(src)
    # Page parity: the mini-book section must start on the front of a fresh sheet.
    if out.page_count % 2:
        out.new_page(width=A4.width, height=A4.height)
    # A4 portrait, duplex LONG-edge throughout. Alternating rotations preserve back-side orientation.
    for i, _ in enumerate(booklet_landscape):
        page = out.new_page(width=A4.width, height=A4.height)
        page.show_pdf_page(page.rect, booklet_landscape, i, rotate=90 if i % 2 == 0 else 270, keep_proportion=True)
    assert out.page_count % 2 == 0
    return out


def main():
    ap = argparse.ArgumentParser(description='Build one-print A4 duplex package for Japanese English exam study.')
    ap.add_argument('--answers', type=Path, required=True)
    ap.add_argument('--vocab', type=Path, required=True)
    ap.add_argument('--mini', type=Path, required=True, help='A5 portrait PDF, exactly eight logical pages in reading order')
    ap.add_argument('--out-dir', type=Path, required=True)
    args = ap.parse_args()
    for f in (args.answers, args.vocab, args.mini):
        if not f.exists():
            ap.error(f'PDF not found: {f}')
    args.out_dir.mkdir(parents=True, exist_ok=True)
    with fitz.open(args.answers) as answers, fitz.open(args.vocab) as vocab, fitz.open(args.mini) as mini:
        mini_print = booklet(mini)
        merged = combine(answers, vocab, mini_print)
        pp = args.out_dir / '音読ミニブック_A4折り用.pdf'
        mp = args.out_dir / '一括印刷_A4両面長辺とじ.pdf'
        mini_print.save(pp, garbage=4, deflate=True)
        merged.set_metadata({'title': '英語過去問 学習セット — 一括印刷版', 'subject': 'A4 portrait / duplex long-edge; last 4 pages are foldable mini-book'})
        merged.save(mp, garbage=4, deflate=True)
        print(f'Booklet: {pp} ({mini_print.page_count} pages)')
        print(f'Bundle:  {mp} ({merged.page_count} pages, {merged.page_count//2} physical A4 sheets duplex)')
        print('PRINT SETTINGS: A4 portrait, duplex, LONG-edge binding, 100% (or printable-area fit if edges clipped).')
        print('The last two sheets fold together to form the mini-book; upside-down pages in the combined PDF are intentional.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, FileNotFoundError) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(2)
