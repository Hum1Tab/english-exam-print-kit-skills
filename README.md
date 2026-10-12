# english-exam-print-kit

大学入試の英語過去問から、**紙で読みやすい解答・構文解説／単語熟語一覧／音読ミニブック／一括印刷PDF**を作るためのカスタムAgent Skill。

このSKILLは**英文や正答を自動的に正しく解析するモデルではありません**。問題・正答PDFからAIが根拠を確認し、原稿を作成した後、付属ツールで印刷用PDFに組版・面付け・検査します。

## ファイル

```text
english-exam-print-kit/
├── SKILL.md                   ← AI向けの詳細作業手順
├── README.md                  ← このファイル
├── requirements.txt
├── references/
│   ├── reading-notes.md       ← 「ぐんぐん読める」的な解説方針
│   ├── print-rules.md         ← A4 / A5 / 両面印刷の仕様
│   └── data-contract.md       ← 原稿データの構造
├── examples/sample.json      ← 自作の架空英文での例
└── scripts/
    ├── build_from_json.py    ← 1つのJSONから教材一式を作る
    ├── impose_bundle.py      ← 既存3冊を一括印刷に面付け
    ├── pdf_qa.py             ← ページ・文字・画像検査
    └── self_test.py          ← 自動テスト
```

## SKILLとして使う

**Codex（Windows）**: ZIPを展開し、`english-exam-print-kit`フォルダ全体を `%USERPROFILE%\.codex\skills\` 配下に置く。`%USERPROFILE%\.codex\skills\english-exam-print-kit\SKILL.md` になる形。Codexを再起動して読み込む。

**Claude Code**: `~/.claude/skills/english-exam-print-kit/` または使用中のプロジェクトの `.claude/skills/english-exam-print-kit/` に置く。

**Claude.ai**: カスタムSkillsのアップロードを使える場合は、このZIPをアップロードする。

ChatGPT上でSkillsをアップロードできるかどうかは、利用中のワークスペース/プランの提供状況による。利用できない場合も、`SKILL.md` を作業ルールとしてAIに渡せる。

## 一言で依頼する例

> 英語過去問の問題PDFと正答PDFを添付しました。english-exam-print-kitに従って、A4印刷用の解答・解説、改訂版LEAP単語熟語、A5音読ミニブック、A4両面長辺とじの一括印刷PDFを作成してください。出典・飾りの説明は印刷紙面に不要です。内容の正確性・文字重なりを確認してください。

## 付属ツールを直接使う（CLI）

環境要件：Python 3.10+、`pymupdf`、`weasyprint`、`pillow`。WindowsでWeasyPrintの動作に必要なネイティブライブラリが不足する場合は、WeasyPrintの公式インストール手順に従うかWSL/Linuxで実行。

```bash
python -m pip install -r requirements.txt
python scripts/self_test.py

# 原稿データができた後
python scripts/build_from_json.py --input examples/sample.json --out-dir output/

# すでに3冊のPDFが存在する場合
python scripts/impose_bundle.py --answers answer.pdf --vocab vocab.pdf --mini mini_A5.pdf --out-dir output/

# 印刷前チェック（全ページのプレビュー画像も保存）
python scripts/pdf_qa.py --input output/一括印刷_A4両面長辺とじ.pdf --out-dir output/qa/ --enforce a4 --allow-blank
```

### 重要

- 原稿にない英語・選択肢は補わない。
- LEAP改訂版の番号は**実際に索引で照合済み**のものだけ記入する。未確認は `—`。
- ミニブックの全文英語ページ・全文訳ページがA5の1ページに収まらないとき、紙で読めない小ささにして無理やり通さない。
- 最終PDFは機械検査のあとに必ず全ページを実際に画像で確認する。
- ページの余白はプリンターごとに異なるため、最初の1冊は試し刷り推奨。

## 印刷

**一括PDF**：A4縦・両面・**長辺とじ**・原寸。ミニブック部分のみ、最後の2枚を取り出して折る。
