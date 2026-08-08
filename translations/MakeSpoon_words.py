# -*- coding: utf-8 -*-
# translations/spoon_words.py

WORDS = {
    # ========================================================
    # ▼ ダイアログUI・入力コントロール関係
    # ========================================================
    "スプーン工場：【ステップ1】皿の形状": "Spoon Factory: [Step 1] Bowl Shape",
    "<b>皿の幅 (X方向):</b>": "<b>Bowl Width (X Direction):</b>",
    "<b>皿の長さ (Y方向):</b>": "<b>Bowl Length (Y Direction):</b>",
    "<b>皿の深さ (Z方向):</b>": "<b>Bowl Depth (Z Direction):</b>",
    "<b>皿の肉厚 (厚み):</b>": "<b>Bowl Wall Thickness:</b>",
    "次へ（柄と仕上げ）": "Next (Handle & Finish)",
    
    "スプーン工場：【ステップ2】柄と仕上げ": "Spoon Factory: [Step 2] Handle & Finish",
    "<b>柄の長さ:</b>": "<b>Handle Length:</b>",
    "柄の根本の幅（太さ）:": "Handle Base Width (Thickness):",
    "柄の厚み:": "Handle Thickness:",
    "<b>【仕上げ】口が触れるフチの角丸(R):</b>": "<b>[Finish] Edge Rounding (R) for Lips:</b>",
    "<font color='gray'>※柄には角丸を適用しません</font>": "<font color='gray'>* Rounding will not be applied to the handle</font>",
    "スプーンを完全生成": "Fully Generate Spoon",

    # ========================================================
    # ▼ ワークベンチ登録・ツール情報
    # ========================================================
    "スプーンの作成": "Create Spoon",
    "写真を参考にした人間工学カーブと、パズル結合方式による安定生成を行います": "Generates a spoon using ergonomic curves based on reference photos and stable puzzle-joint methods.",

    # ========================================================
    # ▼ プログレスバー（進捗メッセージ）関係
    # ========================================================
    "スプーン製造ライン": "Spoon Production Line",
    "皿を計算中...": "Calculating bowl geometry...",
    "口が触れるフチのみを滑らかに加工中...": "Smoothing only the edges where lips touch...",
    "横からのS字シルエットを生成中...": "Generating S-curve silhouette from the side...",
    "上からのシルエットを生成中...": "Generating silhouette from the top...",
    "皿から柄のめり込みを減算（受け皿作成）中...": "Subtracting handle embedment from bowl (creating socket)...",
    "皿と柄をピッタリはめ込んでフュージョン中...": "Fitting bowl and handle perfectly and fusing via Boolean...",
    "FreeCADへ登録中...": "Registering to FreeCAD...",
    "すべての工程が完了しました！": "All processes completed successfully!",

    # ========================================================
    # ▼ 通知・エラーメッセージ関係
    # ========================================================
    "エラー": "Error",
    "肉厚が大きすぎるため、内側をくり抜くスペースがありません。": "The wall thickness is too large, so there is no space to hollow out the inside.",
    "フチの角丸処理をスキップしました: ": "Skipped edge rounding process: ",
}