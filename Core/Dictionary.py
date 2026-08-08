# -*- coding: utf-8 -*-
# Core/Dictionary.py
import os
import json

TRANSLATION_DICT = {}

try:
    if '__file__' in globals():
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    else:
        import FreeCAD
        base_dir = os.path.join(FreeCAD.getUserAppDataDir(), "v1-1", "Mod", "Ring")

    json_path = os.path.join(base_dir, "translations", "dictionary.json")

    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            TRANSLATION_DICT = json.load(f)
except Exception as e:
    print(f"翻訳辞書の読み込み失敗: {str(e)}")
