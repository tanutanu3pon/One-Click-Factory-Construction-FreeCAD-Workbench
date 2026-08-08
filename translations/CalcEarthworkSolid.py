# -*- coding: utf-8 -*-
# Solid方式 切盛土量計算ツール用 翻訳辞書

WORDS = {
    # ツール情報
    "切盛土量計算 (Solid方式)": "Cut/Fill Volume Calculation (Solid)",
    "基準GLを設定してサーフェスをソリッド化し、ブーリアン演算で正確な体積を計算します": "Solidify surfaces with base GL and calculate precise volume using boolean operations",

    # UIダイアログ
    "Solid方式 切盛土量計算": "Solid Cut/Fill Volume Calculation",
    "【ベース】現況(施工前)データ:": "[Base] Existing Ground Surface:",
    "基準GL (底面を作るZ座標):": "Base GL (Z coordinate for bottom):",
    "単位系:": "Unit System:",
    "モデルは mm 単位 (1m = 1000mm)": "Model is in mm (1m = 1000mm)",
    "モデルは m 単位 (1m = 1m)": "Model is in m (1m = 1m)",
    "比較する2つのサーフェスを選択してください。": "Please select two surfaces to compare.",
    "選択されたオブジェクトはメッシュデータではありません。": "Selected objects are not mesh data.",

    # 進捗メッセージ
    "ソリッドを生成しています...": "Generating solids...",
    "現況データのソリッド化...": "Solidifying existing ground surface...",
    "計画データのソリッド化...": "Solidifying planned surface...",
    "土量の計算（ブーリアン減算）...": "Calculating volumes (Boolean subtraction)...",

    # 結果メッセージ
    "【Solidブーリアン 土量計算結果】": "[Solid Boolean Volume Calculation Result]",
    "基準GL:": "Base GL:",
    "▼ 切土 (Cut) :": "▼ Cut Volume:",
    "▲ 盛土 (Fill):": "▲ Fill Volume:",
    "差引合計 (盛-切):": "Net Total (Fill - Cut):",
    "※計算されたソリッドモデル（青/赤）をツリーに出力しました。": "* Created volume solid models (Blue/Red) in tree view.",
    " 流体解析等にそのままエクスポート可能です。": " Can be directly exported for CFD analysis.",
    "底面の生成に失敗しました。メッシュの外周が複雑すぎる可能性があります。": "Failed to generate bottom face. Boundary mesh might be too complex."
}