# ClickFactory Workbench for FreeCAD

?? *[???? 日本語の説明はこちら (Click here for Japanese Description)](#-日本語説明)*

A multi-functional 3D modeling extension workbench for FreeCAD. It contains two workbenches: **"Click Factory"** for jewelry and daily goods, and **"Construction"** for civil engineering structures and terrain analysis.

Designed for both beginners and professionals, it allows you to generate high-quality 3D models in seconds through intuitive parametric inputs.

![ClickFactory Overview](img/title1.png)

---

## ??? Features & Capabilities

### ?? 1. Click Factory (Jewelry & Daily Goods)
![Click Factory Features](img/title2.png)
- **Jewelry & Ring Design**: Precision ring generation based on JIS sizes, custom profiles, diamond creation, side-fit alignment, and boolean subtraction.
- **3D Text & Engraving**: Nameplate creation with font selection, variable pitch text engraving on inner ring walls (Japanese, English, Numbers).
- **Daily Essentials & Parts**: Customizable mugs, vases, spoons, S-hooks, buttons, storage boxes with drop-proof lids, and battery holders.
- **Charms & Accessories**: Magatama beads, drops, crescents, 3D hearts, and star parts.
- **Image & Animation Tools**: Auto-tracing image into cookie cutters, planetary gear generation with dynamic animation control.
- **Special Features**: AI-assisted modeling (Local LLM integration), turntable rotation presentation with auto-coloring, and material weight estimation (Precious metals & 3D printing resins).

### ??? 2. Construction (Civil Engineering & Terrain Analysis)
![Construction Features](img/title3.png)
- **Retaining Walls & Quantities**: Continuous generation of uniform or twisted gravity retaining walls, automatic calculation of concrete volume and formwork surface area.
- **Infrastructure Structures**: Multi-layer road modeling (asphalt, base, lane lines) with longitudinal slopes, and wave-dissipating blocks (Tetrapods).
- **Terrain & Earthwork**: 3D terrain mesh generation from Excel/CSV XYZ point clouds, GL-solid cut/fill volume calculation via boolean operations.

---

## ? Highlights
- **Multi-language Support**: Full support for English and Japanese.
- **Robust UI & Error Handling**: Automatic progress bar and error recovery preventing freeze/crashing during heavy loft and boolean operations.
- **Interactive Launcher**: Built-in launcher to select and execute tools with visual descriptions.

---

## ?? Installation

1. Download this repository as a ZIP file (click the `Code` button -> `Download ZIP`) or clone it via `git clone`.
2. Extract the file and place the folder (named `ClickFactory` or `Ring`) into your FreeCAD `Mod` directory:
   - **Windows**: `%APPDATA%\FreeCAD\Mod\` (or `C:\Users\<Username>\AppData\Roaming\FreeCAD\Mod\`)
   - **macOS**: `~/Library/Application Support/FreeCAD/Mod/`
   - **Linux**: `~/.local/share/FreeCAD/Mod/` or `~/.FreeCAD/Mod/`
3. Restart FreeCAD. **"Click Factory"** and **"Construction"** will appear in the workbench selector dropdown menu.

---

## ???? 日本語説明

FreeCAD向けの多機能3Dモデリング拡張ワークベンチです。アクセサリーや生活雑貨を作成する **「Click Factory」** と、土木構造物や地形解析を行う **「Construction」** の2つのワークベンチが含まれています。

初心者から実務者まで、ダイアログからのパラメータ入力だけで高度な3Dモデルを短時間で正確に生成できます。

### 主な機能

#### ?? 1. Click Factory (ジュエリー・生活雑貨)
- **指輪・ジュエリー設計**: JIS規格(号数)・断面指定のリング生成、ダイヤモンド作成、リング側面への自動フィット・減算結合
- **文字刻印・3Dテキスト**: フォント指定可能なネームプレート作成、リング内面への可変ピッチ文字刻印（日本語・英数字）
- **生活雑貨・機構パーツ**: マグカップ、花瓶、スプーン、S字フック、服飾ボタン、隙間収納ケース、電池ホルダー
- **アクセサリーチャーム**: 勾玉、水滴、三日月、立体ハート、星パーツ
- **画像・アニメーション**: 画像からのクッキー型枠自動トレース、遊星ギアの生成と動的アニメーション制御
- **その他便利機能**: AIモデリング（ローカルLLM連携）、ターンテーブル回転演出＆自動着色、モデル重量計算（貴金属・3Dプリント樹脂対応）

#### ??? 2. Construction (土木構造物・地形解析)
- **擁壁設計・数量計算**: 重力式擁壁・ねじれ変断面擁壁の連続生成、コンクリート体積および部位別表面積（型枠面積）の自動算出
- **インフラ構造**: 多層構造（アスファルト・路盤・白線）および縦断勾配対応の連続道路生成、消波ブロック（テトラポッド）生成
- **地形・土量計算**: Excel/CSVのXYZ座標からの3D地形（メッシュ）構築、基準GL底面ソリッド化とブーリアン演算による正確な切盛土量算出

### 特徴
- **完全多言語対応**: 日本語と英語に完全対応（設定から切り替え可能）。
- **高耐久な処理**: 重いブーリアン演算やロフト処理中も画面フリーズや強制終了を防ぐ自動プログレスバー管理。
- **ガイド機能**: 各ツールの機能や使い方を説明文を見ながら選んで起動できるランチャーを搭載。

### インストール方法
1. 本リポジトリの `Code` ボタンから **Download ZIP** を選択するか、`git clone` でダウンロードします。
2. 解凍したフォルダ（フォルダ名: `ClickFactory` または `Ring`）を FreeCAD の `Mod` ディレクトリへ配置します。
   - **Windows**: `%APPDATA%\FreeCAD\Mod\`
   - **macOS**: `~/Library/Application Support/FreeCAD/Mod/`
   - **Linux**: `~/.local/share/FreeCAD/Mod/` または `~/.FreeCAD/Mod/`
3. FreeCADを起動すると、ワークベンチ選択メニューに **「Click Factory」** と **「Construction」** が追加されます。

---

## ?? License
LGPL-2.1-or-later