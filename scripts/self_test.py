#!/usr/bin/env python3
"""End-to-end smoke test of the JSON compiler, booklet imposition, and A4 QA checks."""
from pathlib import Path
import subprocess
import sys
import tempfile
import json
import fitz

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
SAMPLE=ROOT/'examples/sample.json'


def run(args):
    print('>', ' '.join(map(str,args)),flush=True)
    subprocess.run(args,check=True)


def main():
    with tempfile.TemporaryDirectory(prefix='exam-print-skill-test-') as tmp:
        out=Path(tmp)/'output'
        run([sys.executable,HERE/'build_from_json.py','--input',SAMPLE,'--out-dir',out])
        with fitz.open(out/'音読ミニブック_A5順.pdf') as d:
            assert d.page_count==8
        with fitz.open(out/'一括印刷_A4両面長辺とじ.pdf') as d:
            assert d.page_count%2==0
            for pg in d:
                assert abs(pg.rect.width-fitz.paper_rect('a4').width)<3
                assert abs(pg.rect.height-fitz.paper_rect('a4').height)<3
        run([sys.executable,HERE/'pdf_qa.py','--input',out/'一括印刷_A4両面長辺とじ.pdf','--out-dir',out/'qa','--enforce','a4','--allow-blank','--dpi','90'])
        # A malformed markup MUST FAIL, never silently change source text.
        bad=json.loads(SAMPLE.read_text(encoding='utf8'))
        bad['reading']['sentences'][0]['markup'][0]['text']='WRONG TEXT'
        source=Path(tmp)/'invalid.json'
        source.write_text(json.dumps(bad,ensure_ascii=False),encoding='utf8')
        r=subprocess.run([sys.executable,HERE/'build_from_json.py','--input',source,'--out-dir',out/'invalid'],capture_output=True,text=True)
        assert r.returncode!=0 and 'markup' in r.stderr, 'markup mismatch should have failed'
        # Claiming an unverified LEAP ID MUST FAIL.
        bad=json.loads(SAMPLE.read_text(encoding='utf8'))
        bad['reading']['vocabulary'][0]['leap_revised_no']=1234
        source.write_text(json.dumps(bad,ensure_ascii=False),encoding='utf8')
        r=subprocess.run([sys.executable,HERE/'build_from_json.py','--input',source,'--out-dir',out/'invalid2'],capture_output=True,text=True)
        assert r.returncode!=0 and 'leap_verified' in r.stderr, 'unverified LEAP number should have failed'
    print('PASS: five outputs built, page sizes correct, QA passed, bad annotation and LEAP data rejected')


if __name__=='__main__':main()
