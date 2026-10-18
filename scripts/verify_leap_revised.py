#!/usr/bin/env python3
"""Verify exam vocabulary against a legitimately obtained revised LEAP CSV.

Input lexicon: CSV with e.g. No,word columns. This utility deliberately does not
ship copyrighted LEAP datasets, definitions, or example sentences.
"""
import argparse, csv, re
from pathlib import Path

NO_KEYS = ("No", "no", "number", "番号", "見出番号", "見出し番号")
WORD_KEYS = ("word", "Word", "headword", "単語", "見出し語", "英単語")

def field(row, names):
    for name in names:
        v = row.get(name, "")
        if v and str(v).strip():
            return str(v).strip()
    return ""

def load_lexicon(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = csv.DictReader(f)
        if not rows.fieldnames or not any(k in rows.fieldnames for k in NO_KEYS) or not any(k in rows.fieldnames for k in WORD_KEYS):
            raise ValueError("CSV columns must include No/number/番号 and word/headword/単語")
        out = {}
        for row in rows:
            no, word = field(row, NO_KEYS), field(row, WORD_KEYS).lower()
            if not no.isdigit() or not word:
                continue
            if word in out and out[word] != no:
                raise ValueError("Conflicting numbers for: " + word)
            out[word] = no
        if not out:
            raise ValueError("No valid entries found")
        return out

def suggest_related(word, dictionary):
    candidates = set()
    for suffix, replacement in (("ies","y"),("ing",""),("ing","e"),("ed",""),("ed","e"),("es",""),("s",""),("ly","")):
        if word.endswith(suffix) and len(word) > len(suffix)+2:
            candidate = word[:-len(suffix)] + replacement
            if candidate in dictionary:
                candidates.add(candidate)
    return sorted(candidates)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lexicon", required=True, help="Locally licensed revised LEAP CSV")
    p.add_argument("--terms", required=True, help="UTF-8 newline-separated words or phrases")
    p.add_argument("--out", required=True, help="CSV output path")
    a = p.parse_args()
    lex = load_lexicon(a.lexicon)
    terms = [re.sub(r"\s+"," ",s.strip()).lower() for s in Path(a.terms).read_text(encoding="utf-8-sig").splitlines() if s.strip()]
    result=[]
    for term in dict.fromkeys(terms):
        if term in lex:
            result.append((term,term,lex[term],"exact-headword","verified"))
        else:
            related=suggest_related(term,lex) if " " not in term else []
            result.append((term,";".join(related),"","related-candidate" if related else "unverified","do not infer a number"))
    with open(a.out,"w",newline="",encoding="utf-8-sig") as f:
        w=csv.writer(f);w.writerow(("exam_term","matched_headword","leap_no","status","note"));w.writerows(result)
    print("Exact: %d; related candidates: %d; unverified: %d" % (sum(r[3]=="exact-headword" for r in result),sum(r[3]=="related-candidate" for r in result),sum(r[3]=="unverified" for r in result)))

if __name__ == "__main__": main()
