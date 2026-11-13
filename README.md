# dynamicworld-cells

VRChat ワールド向けセルローダー **Cell Loader (Dynamic World)** のセルデータ配信用リポジトリ。GitHub Pages で公開し、ワールド内のローダーが実行時に読み込む。

開発本体（仕組み・仕様）は別リポジトリ `hyde4280/dynamicworld`（private）側。セルデータは VRChat クライアントが認証なしで取得するため、こちらは public にしている。

セルデータ側の作業ログは [docs/work_log.md](docs/work_log.md) に置いています（開発本体の作業ログとは分けて管理）。

## 利用条件

セルデータは hyde4280 の著作物です。VRChat 内でローダーを通じて読み込み・閲覧するのは自由ですが、複製・再配布・改変公開・他作品への組み込み・商用利用には事前の許可が必要です。詳細は [LICENSE](LICENSE) を参照してください（暗号化は行っていません。公開は取得可能性のためであり、利用の自由を意味しません）。

## URL 規格

セル 1 件 = 2 ファイル（OBJ + アトラス PNG）。パスは連番で固定し、差し替えは同パスの上書きで行う。

| セル | メッシュ | テクスチャ |
|---|---|---|
| cell001 | `https://hyde4280.github.io/dynamicworld-cells/cells/cell001.obj` | `https://hyde4280.github.io/dynamicworld-cells/cells/cell001.png` |

- `*.github.io` は VRChat の String / Image Loading の許可リスト入りのため、「Allow Untrusted URLs」なしで読み込める。
- セル形式（10m 立方・床 y=0・入口は南面中央・マニフェストは OBJ ヘッダーコメント）の仕様は、本体リポジトリのプロトタイプ仕様 v0 に基づく。パッケージ公開時に本リポジトリにも仕様を同梱する予定。

## カタログ

| ID | 名前 | 状態 |
|---|---|---|
| cell001 | hajimari-no-hokora（はじまりの祠） | OBJ・PNG（512×512）とも投入済み。Pages で配信中（2026-10-31 確認）。252 tris |
| cell002 | niwa（夕の庭） | OBJ・PNG（1024×1024）とも配信中（2026-11-05、PNG は .b64 経由で復元）。5,334 tris |
| cell003 | iseki（昼の遺跡） | OBJ・PNG（1024×1024）とも配信中（2026-11-05、PNG は .b64 経由で復元）。20,090 tris |
| cell004 | suisho-doukutsu（水晶洞窟） | OBJ・PNG とも配信中（2026-11-05、OBJ は .part 分割投入→結合、PNG は .b64 経由で復元）。53,034 tris（上限探り用。コライダーは中心部と岩柱のみ） |
| cell005 | fujisan（富士山ジオラマ） | OBJ・PNG（512×512）とも配信中（PNG は .b64 経由で復元）。33,792 tris（地形 32,768＋スカート 1,024）。国土地理院DEMタイルから生成した眺める専用セル（コライダーなし）。2026-11-06 に実寸比（高さ 4.2m）＋裾スカート付きで再生成 |
| cell006 | jujiro-doukutsu（十字路の洞窟） | OBJ・PNG（512×512）とも配信中（PNG は .b64 経由で復元）。1,008 tris、コライダー 12。基本パターンセル：扉 N/E/S/W（`# door:` 行で宣言）。2026-11-13 坑道風に作り直し（CC0 写真岩＋岩半分レイアウト＋壁腕ランタン 2 基、`# cell.lights:` / `# cell.tiling:` 付き） |
| cell007 | teijiro-doukutsu（T字路の洞窟） | OBJ・PNG（512×512）とも配信中（PNG は .b64 経由で復元）。768 tris、コライダー 9。基本パターンセル：扉 N/E/S。2026-11-13 坑道風に作り直し（ランタン 2 基、lights/tiling 付き） |
| cell008 | ipponmichi-doukutsu（一本道の洞窟） | OBJ・PNG（512×512）とも配信中（PNG は .b64 経由で復元）。680 tris、コライダー 6。基本パターンセル：扉 N/S。2026-11-13 坑道風に作り直し（ランタン 2 基、lights/tiling 付き） |
| cell009 | magarimichi-doukutsu（曲がり道の洞窟） | OBJ・PNG（512×512）とも配信中（PNG は .b64 経由で復元）。700 tris、コライダー 9。基本パターンセル：扉 S/E。2026-11-13 坑道風に作り直し（ランタン 2 基、lights/tiling 付き） |
| cell010 | kaidan-no-doukutsu（階段の洞窟） | OBJ・PNG（512×512）とも配信中（PNG は .b64 経由で復元）。760 tris、コライダー 16。基本パターンセル：扉 S＋U（stair）。8 段の階段で y=3 の踊り場・中央台へ上がり、天井にハッチ |
| cell014 | kuichigai-jujiro-doukutsu（食い違い十字路の洞窟） | OBJ・PNG（512×512）とも配信中（PNG は .b64 経由で復元）。1,002 tris、コライダー 18。バリエーションパターンセル：扉 N/E/S/W（cell006 と同じ接続）だが内部の通路が食い違い、対面の扉同士が見えない |

## セルの追加方法

1. 形式に従って `cells/cellNNN.obj` と `cells/cellNNN.png` を用意する（NNN は連番）。
2. このリポジトリにコミットし、カタログ表に行を足す。
3. ワールド側のローダーに宣言済みの URL 枠がある番号までが読み込み対象になる。
