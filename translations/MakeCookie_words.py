# -*- coding: utf-8 -*-
# translations/cookie_words.py

WORDS = {
    # ========================================================
    # ▼ ダイアログ・UIコントロール関係
    # ========================================================
    "クッキー型枠・製造工場": "Cookie Cutter Factory",
    "画像を選択 (JPG / PNG)": "Select Image (JPG / PNG)",
    "背景が白または透明の写真を選択してください。": "Please select a photo with a white or transparent background.",
    "<b>型の厚み (線の幅):</b>": "<b>Cutter Thickness (Line Width):</b>",
    "<b>型の高さ (押し出し量):</b>": "<b>Cutter Height (Extrusion):</b>",
    "型の最大横幅:": "Max Width of Cutter:",
    "クッキー型を生成": "Generate Cookie Cutter",
    "キャンセル": "Cancel",
    "画像を選択": "Select Image",
    "クッキー型の作成": "Create Cookie Cutter",
    "画像から外枠を自動トレースして立体のクッキー型枠を作成します": "Automatically trace the outline from an image to create a 3D cookie cutter frame.",

    # ========================================================
    # ▼ プログレスバー（進捗メッセージ）関係
    # ========================================================
    "クッキー型枠・立体成形": "Cookie Cutter 3D Modeling",
    "画像をSVG風に高精度トレース中...": "Tracing image into SVG-style contours...",
    "AI画像処理で厚みを計算中...": "Calculating cutter thickness via AI image processing...",
    "曲線の最適化中...": "Optimizing vector curves...",
    "立体化のための面を構築中...": "Building 3D faces for extrusion...",
    "mm 押し出して成形中...": "mm Extruding and shaping...",  # 動的メッセージの部分一致用
    "中身をくり抜いて空洞にしています...": "Hollowing out the inside to create the cutter frame...",
    "完了しました！": "Completed!",

    # ========================================================
    # ▼ ダイアログ通知・エラーメッセージ関係
    # ========================================================
    "成功": "Success",
    "中身を完璧にくり抜いた、本物のクッキー型枠が完成しました！": "Success! A real cookie cutter frame with a perfectly hollowed-out inside has been created.",
    "エラー": "Error",
    "画像が選択されていません。": "No image selected. Please choose an image file first.",
    "画像の読み込みに失敗しました。": "Failed to load the image file.",
    "輪郭を検出できませんでした。": "Could not detect any valid contours from the image.",
    "クッキー型立体化エラー: ": "Cookie Cutter 3D Modeling Error: ",
    "立体化中にエラーが発生しました:\n": "An error occurred during the 3D modeling process:\n",
}