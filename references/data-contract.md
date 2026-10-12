# JSON原稿の最小契約

入力はUTF-8 JSON。`examples/sample.json`参照。

```json
{
  "title": "大学名 年度 英語③",
  "exam_date": "2026-02-03",
  "reading": {
    "theme": "長文のテーマ",
    "sentences": [
      {
        "english": "The report you need to finish might take longer than you expect.",
        "translation": "...",
        "markup": [
          {"text":"The report", "role":"S"},
          {"text":" you need to finish", "role":"M→report"},
          {"text":" might take", "role":"V"},
          {"text":" longer than you expect.", "role":"M"}
        ],
        "explanation": "...",
        "trap": "...",
        "logic": "..."
      }
    ],
    "vocabulary": [{"word":"report","reading":"リポート","meaning":"報告書","leap_revised_no":null,"leap_verified":false}],
    "idioms": [{"phrase":"take longer than","meaning":"〜より時間がかかる","note":"比較表現","leap_revised_no":null,"leap_verified":false}],
    "cloze": [{"blank":"A", "correct":"⑤", "why":"...", "other_choices":"..."}]
  },
  "sections": [
    {"name":"Ⅲ 文法", "items":[{"label":"a", "english":"...", "answer":"②", "explanation":"...", "other_choices":"..."}]}
  ],
  "source_limitations": ["大問Iは問題原文が非掲載のため解説範囲に制限あり"]
}
```

- `sentences[].markup` が指定された場合、`text`を連結したものと`english`が**完全一致**しなければエラーにする。見出し間違い・空白欠落を見逃さないため。
- 空所補充は `english` に正解を入れた通読文を記載し、解説側の `cloze` で空所と選択肢の対応を明示。
- 改訂版LEAP番号が未検証なら `null`。実際に索引で番号を確認した場合に限り `leap_revised_no` に数字と `leap_verified:true` を設定。予測した番号は禁止。
- `sections` の項目は情報がない場合、空の見出しを表示しない。
- このJSONはAIが資料から根拠を確認して作成すること。`build_from_json.py` が英文の意味や正答を推測することはない。
