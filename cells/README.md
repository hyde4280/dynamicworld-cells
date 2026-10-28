# cells/

セルデータ本体の置き場。1 セル = `cellNNN.obj` + `cellNNN.png` のペア。

- OBJ: 三角形化済み。マニフェスト（名前・環境色・キーライト・コライダー一覧）はヘッダーコメントに埋め込む。
- PNG: アトラステクスチャ（最大 2048×2048）。
- cell001.png は `../tools/gen_cell001.py`（Python + Pillow）で生成できる。
