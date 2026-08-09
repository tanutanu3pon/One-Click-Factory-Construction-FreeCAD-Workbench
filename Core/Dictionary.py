# -*- coding: utf-8 -*-
# Core/Dictionary.py
import os
import json
import inspect
import re
import FreeCAD

TRANSLATION_DICT = {}
REVERSE_DICT = {}
CLEAN_TRANSLATION_DICT = {}

def load_dictionary():
    global TRANSLATION_DICT, REVERSE_DICT, CLEAN_TRANSLATION_DICT
    TRANSLATION_DICT.clear()
    REVERSE_DICT.clear()
    CLEAN_TRANSLATION_DICT.clear()

    try:
        if '__file__' in globals() and __file__:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        else:
            current_file = inspect.getfile(inspect.currentframe())
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(current_file)))

        json_path = os.path.join(base_dir, "translations", "dictionary_en.json")

        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                TRANSLATION_DICT = json.load(f)
            
            # 英語 -> 日本語 への逆引き用マップを作成
            REVERSE_DICT = {v: k for k, v in TRANSLATION_DICT.items() if v}
            
            # 【追加】UI読み込み時のフリーズを防ぐため、接尾辞をカットした高速検索用辞書を作成
            suffix_regex = re.compile(r'(の作成|の生成|の計算|を作成します|を生成します|を作成|を生成|作成|生成)$')
            for k, v in TRANSLATION_DICT.items():
                clean_k = suffix_regex.sub('', k).strip()
                if clean_k:
                    CLEAN_TRANSLATION_DICT[clean_k] = v
                    
            FreeCAD.Console.PrintMessage(f"[ClickFactory] 翻訳辞書ロード完了 ({len(TRANSLATION_DICT)} 件)\n")
    except Exception as e:
        FreeCAD.Console.PrintError(f"[ClickFactory] 辞書読み込み失敗: {str(e)}\n")