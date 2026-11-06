# コマンド

カレントをスキルフォルダとした例。パスは対象に合わせる。`--help`で各引数を確認できる。

```powershell
python -X utf8 scripts/sysmac.py inspect 'C:/work/current.smc2' --report 'C:/work/inspection.json'
python -X utf8 scripts/sysmac.py inspect 'C:/work/current.smc2' --details --report 'C:/work/full.json'
python -X utf8 scripts/sysmac.py find-projects --query '対象名'
python -X utf8 scripts/sysmac.py compare 'C:/work/current.smc2' 'C:/OMRON/Data/Solution/対象GUID' --report 'C:/work/diff.json'
```

## 変更計画と候補

`source_sha256`はinspectで取得。sectionはinspectのkey/id/一意な節名。行番号は0始まり。操作は記載順なので、複数挿入は後方から行うか現在の行番号に合わせる。

```json
{
  "source_sha256": "inspectのSHA256",
  "operations": [
    {
      "op": "comment", "section": "BoxPacking_箱詰め", "row": 3,
      "expected": "変更前のコメント全文",
      "text": "【初回状態判定】\n\n【X1003】：コンテナ到着"
    },
    {
      "op": "map-indices", "section": "BoxPacking_箱詰め",
      "tag": "BoxPacking_M", "mapping": {"41": 42, "42": 43},
      "rows": [30, 31, 32], "include_st": false
    }
  ]
}
```

追加操作：
- `replace-row`：section,row,expected_sha256,value。行SHAは`jsha(行オブジェクト)`。必要ならreindex=true。
- `insert-row`：section,row,value。必要ならreindex=true。結線とメタデータは明示作成する。
- `replace-part`：part,expected_sha256,file。変数表/OEM等、既存エントリをファイルのバイトで置換。未知形式の全面書換えに使わない。同じエントリを他操作でも変更しない。

```powershell
python -X utf8 scripts/sysmac.py stage 'C:/work/current.smc2' --plan 'C:/work/plan.json' --output 'C:/work/candidate.smc2' --report 'C:/work/stage.json'
python -X utf8 scripts/sysmac.py native 'C:/work/candidate.smc2' --report 'C:/work/native.json'
python -X utf8 scripts/sysmac.py publish --stage-report 'C:/work/stage.json' --native-report 'C:/work/native.json' --destination 'C:/work/next.smc2' --report 'C:/work/published.json'
```

上書きは`--overwrite`、許可された制御/変数変更は`--allow-logic`、旧版を移動する指示なら`--archive-source`。これらは作業範囲の指定であり、ユーザーから許可されていることをモデル側で判断して使う。

nativeはPython経由でPowerShellをUTF-16LE EncodedCommandとして呼ぶ。PS5のUTF-8直読問題を回避するため、PSファイルを安易に直接`-File`で起動しない。

## コメント同期

```powershell
# 内部のコメントを既存SMC2の候補へ取り込む
python -X utf8 scripts/sysmac.py sync-comments --target 'C:/work/base.smc2' --reference 'C:/OMRON/Data/Solution/対象GUID' --output 'C:/work/synced.smc2' --report 'C:/work/stage.json'

# 内部Hへの乾式確認。expected-nameはOEM Solution名そのもの。
python -X utf8 scripts/sysmac.py direct-comments --source 'C:/work/updated.smc2' --project 'C:/OMRON/Data/Solution/対象GUID' --expected-name '対象プロジェクト名' --report 'C:/work/direct-plan.json'

# 今回閉じていることを確認済みの場合だけ実反映
python -X utf8 scripts/sysmac.py direct-comments --source 'C:/work/updated.smc2' --project 'C:/OMRON/Data/Solution/対象GUID' --expected-name '対象プロジェクト名' --report 'C:/work/direct-result.json' --apply --project-closed
```

direct-commentsは全体バックアップ後にCMTだけ更新する。変数宣言や制御が違えば停止し、途中失敗時は既に書いた対象を復元する。CLI自身は実画面の開閉を判定できない。--project-closedはその場の確認結果を記録するために使う。

`sync-comments`後の候補もnative→publishで公開できる。内部全体から新規SMC2をゼロから正式エクスポートする機能ではない。

## スキル自体の保守

この環境の保守元は`work-projects/.claude/skills/sysmac-studio`。編集後に`python tools/sync_skills.py`で`.agents/skills`へ同期する。Codex登録用の`~/.codex/skills/sysmac-studio`も同じ内容へ同期し、生成物（__pycache__等）を除外してハッシュを照合する。既存の別内容があれば、先に差分を確認して無関係な設定を消さない。
