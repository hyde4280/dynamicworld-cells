# 作業ログ（セルデータ）

このリポジトリ（dynamicworld-cells）の変更履歴のうち、コミットメッセージだけでは分からない経緯を記録する場所。セルデータの追加・差し替え・形式まわりの記録はここに置き、ローダーやシーン（開発本体）の作業ログとは分けて管理する。

## 2026-10-31 cell001 テクスチャ追加

- `cells/cell001.png`（512×512 アトラス）を追加（commit 720c2b04）。生成は `tools/gen_cell001.py`（Python + Pillow）をローカルで実行。
- これで cell001 は OBJ＋PNG のペアが揃い、GitHub Pages 経由で両方とも取得できることを確認済み。
- カタログ（README / index.html）の状態表記を「配信中」に更新。

## 2026-10-28 リポジトリ開設と利用条件

- リポジトリを作成し、初期ファイルを投入（commit c0e3403b）: README（URL 規格とカタログ）、index.html、`.nojekyll`、`cells/cell001.obj`、`tools/gen_cell001.py`。
- GitHub Pages を有効化し、カタログページと cell001.obj が配信されることを確認。
- セルデータの利用条件として `LICENSE` を追加し、README に利用条件の節を設けた（commit f8d973bd）。暗号化は行わず、条件はライセンス表記で担保する方針。
