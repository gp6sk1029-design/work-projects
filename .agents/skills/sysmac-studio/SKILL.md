---
name: sysmac-studio
description: "Omron Sysmac Studioの.smc2・登録済みプロジェクトを分析・編集する。ラダーの問題と対策を画像で提示し、I版を基準に行間・変数コメントを整え、工程番号・STの修正、検査、履歴保存を行う。"
---

# Sysmac Studio編集

生産技術のPLC編集担当として、日本語で依頼された範囲を実装する。提案依頼では実ファイルを変更しない。画面操作なしの処理を基本とし、必要なら利用可能なWindows操作スキルを使う。

## 方法の選択

| 依頼 | 方法 |
|---|---|
| 分析・矛盾・参照先の確認 | `inspect` / `compare`。要求元から受け側まで追う |
| `.smc2`生成・編集・上書き | `stage` → `native` → `publish` |
| 閉じた登録済みプロジェクトのコメント修正 | `find-projects` → `direct-comments`。確認済みの範囲 |
| 内部コメントをファイルへ反映 | 既存ベース`.smc2`へ`sync-comments` |
| 内部の新規登録・構造/変数変更 | 直接更新は未検証。まず`.smc2`を編集・検査。追加検証は隔離コピーで行う |

`.smc2`をフォルダへ置くこと、一覧内本体を更新すること、アプリで保存することは別。実施した範囲を区別して報告する。

## 進め方

1. 最新の対象を`inspect`し、SHA256・節・変数表を取得。同名でも前回のGUID・行番号を使い回さない。
2. 関係する資料だけ読む。
   - ファイル編集：[references/file-editing.md](references/file-editing.md)
   - 内部反映：[references/internal-projects.md](references/internal-projects.md)
   - デバッグ：[references/ladder-review.md](references/ladder-review.md)
   - ラダーの画像提示：[references/ladder-diagrams.md](references/ladder-diagrams.md)
   - 行間/変数コメント：[references/comment-style.md](references/comment-style.md)
   - CLI/変更計画：[references/commands.md](references/commands.md)
3. 候補へ変更し差分を確認。コメント依頼なら非CMT差分0、構造変更なら関連工程・要求/受け側・変数定義も照合。
4. 同梱処理で読込み検査。必要な条件モデル・全体ビルドを追加。部分検査を実機/全体ビルド成功と呼ばない。
5. 元SHAを再確認し、バックアップ後に公開。ユーザーの上書き指示は`--overwrite`へ反映し、再承認を求めない。
6. 出力先・変更点・検証・未確認事項を簡潔に報告。ルートMEMORY.mdと振り返りを更新。

## 標準の提示機能（ユーザー指定）

- **ラダーの分析・対策案・修正結果を説明する回答では、毎回ラダー画像を本文へ表示する。** 白背景・黒い結線/接点/コイル・変更箇所を青とする。ASCII図だけで済ませない。図のルールと描画機能は[ladder-diagrams.md](references/ladder-diagrams.md)。ユーザーが図不要と指定した場合は従う。
- **コメントは20261105IのBoxPacking/Destackerで確定した形式を標準にする。** 大工程は`#【番号 名称】`、中工程は`【名称】`、小工程は短い動作文。改行・空行、I/O番号と意味、RCON軸名、分岐/合流元と行先を明示する。[comment-style.md](references/comment-style.md)の例を使う。
- 見本は表示形式の基準。過去I版の工程番号・接点・物理動作を他版へコピーしない。図やコメントの依頼で制御を変更しない。

## 共通スクリプト

`scripts/sysmac.py --help`を使う。`scripts/`はこのスキル内。Python標準ライブラリで動く。

このPCでは次のPythonも使える：
`C:\Users\SEIGI-N13\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`

```text
inspect          .smc2 / 内部プロジェクトの構造を読む
find-projects    登録済みプロジェクトを名前で探す
compare          コメント差分と制御/その他差分を区別
stage            JSON変更計画から候補.smc2を生成
native           同梱読込み・コイル接続検査
publish          バックアップ付き新規保存/上書き
sync-comments    参照元のコメントをベース.smc2へ反映
direct-comments  閉じた既存本体へコメントだけ直接反映
```

画像は`scripts/render_ladder.py --input 図のJSON --output 図.png`で描く（Pillow使用）。`assets/ladder-example.json`が配置・自己保持・変更色・凡例の再利用見本。プログラムの書込み機能とは独立している。

## 編集時の判断

- 番号詰めと工程追加を区別。接点・自己保持・コイル・STの参照を追い、動作が変わる不明点だけ質問する。
- 既存方式を維持。独自ST化、受付方式、時間、運転許可、個数処理を依頼と無関係に作り替えない。方式変更の明示指示があれば優先。
- I/Oは`【Y1204】：コンテナ排出戻`、`【X1003】：コンテナ到着`。センサーの検出範囲を名前から推測しない。
- 変数追加は型・スコープ・保持・初期値・ATを確認。新規SLWDに`Const=0`/`RO=0`、非保持なら`R=0`を明示。既存属性を理由なく変更しない。
- RCONのReadyと機械の運転許可は別。未確認の通信/配置/軸許可をTRUE固定しない。
- PLC接続・転送・運転を、ファイル編集の依頼に含めない。明示された場合はその条件を確認する。

## 実績と境界

Sysmac Studio 1.67環境で、SMC2のラダー/ST/変数編集・同梱読込みと、閉じた内部HのCMT18行更新を実施。内部コメントはユーザーが再読込み表示を確認済み。

内部への構造/変数変更、新規一覧登録、全体コンパイル、実機動作まで自動化済みとは扱わない。共有コードの回帰確認は`scripts/self_test.py`で実プロジェクトを変更せず行う。

## 自己改善ループ（AGENTS.mdに準拠）

このエージェントはAGENTS.mdの方針に従い、タスク完了のたびに振り返りレポートを出力し、SKILL.mdとMEMORY.mdを更新し続ける。ROI評価を毎回行い、費用対効果を最大化する。

新しい成功範囲は保存/再読込みの実績で更新する。失敗の修正は原因に絞り、1件の例を全作業の制約に拡大しない。
