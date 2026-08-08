# -*- coding: utf-8 -*-
# エクセル座標読み込みツール用 翻訳辞書

WORDS = {
    # ツール情報
    "エクセル座標読み込み": "Import Excel Coordinates",
    "エクセルのXYZ座標から点群またはサーフェスを作成します": "Create point cloud or surface from Excel XYZ coordinates",

    # ダイアログ・メッセージ
    "ご案内": "Notice",
    "エクセルファイル（.xlsx）またはCSVファイルを読み込んでください。": "Please select an Excel file (.xlsx) or CSV file.",
    "エクセルデータを選択": "Select Excel Data",
    "生成タイプの選択": "Select Generation Type",
    "読み込んだデータをどのように表示しますか？": "How would you like to display the imported data?",
    "点群データを読み込む": "Import as Point Cloud",
    "サーフェスにする": "Create Surface",
    "単位の確認": "Confirm Units",
    "FreeCADの基準単位は「mm（ミリメートル）」です。\nエクセルに入力されている座標の単位を選んでください。": "FreeCAD's standard unit is 'mm'.\nPlease select the coordinate unit used in your Excel file.",
    "エクセルの「0.001」を「1mm」として読み込む (土木座標/メートル)": "Import '0.001' as '1mm' (Civil Coordinates/Meter)",
    "エクセルの「1」を「1mm」として読み込む (CAD座標/ミリメートル)": "Import '1' as '1mm' (CAD Coordinates/Millimeter)",
    "ライブラリ不足": "Missing Library",
    "サーフェス（メッシュ）の計算には 'scipy' ライブラリが必要です。\n今回は「点群データ」として読み込むか、あらかじめ scipy を導入してください。": "The 'scipy' library is required for surface calculation.\nPlease import as 'Point Cloud' or install scipy.",

    # 進捗・通知メッセージ
    "データ処理中": "Processing Data",
    "データを読み込んでいます...": "Reading data...",
    "データを構築中...": "Building data...",
    "サーフェス（メッシュ）を計算中...": "Calculating surface (mesh)...",
    "有効な座標データが見つかりませんでした。\nエクセルのA,B,C列に数値が入力されているか確認してください。": "No valid coordinate data found.\nPlease verify that numbers are entered in columns A, B, and C.",
    "完了！": "Done!",
    "完了": "Complete",
    "処理中にエラーが発生しました:": "An error occurred during processing:"
}