exec(r'''
import os

wb_dir = r"C:\Users\horis\AppData\Roaming\FreeCAD\v1-1\Mod\Ring"
dict_py_path = os.path.join(wb_dir, "Core", "Dictionary.py")

new_dictionary_py = """# -*- coding: utf-8 -*-
# Core/Dictionary.py
import os
import json
import Core.Language as Language

TRANSLATION_DICT = {}

def load_dictionary():
    global TRANSLATION_DICT
    TRANSLATION_DICT.clear()

    try:
        if '__file__' in globals():
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        else:
            import FreeCAD
            base_dir = os.path.join(FreeCAD.getUserAppDataDir(), "v1-1", "Mod", "Ring")

        current_lang = Language.get_language()

        # 言語名から対応する辞書ファイル名を決定
        lang_file_map = {
            "English": "dictionary_en.json",
            "Deutsch": "dictionary_de.json",
            "Francais": "dictionary_fr.json",
            "中文": "dictionary_zh.json",
            "??": "dictionary_ko.json",
            "Русский": "dictionary_ru.json",
        }

        dict_file = "dictionary_en.json"
        for key, fname in lang_file_map.items():
            if key in current_lang:
                dict_file = fname
                break

        json_path = os.path.join(base_dir, "translations", dict_file)

        # 該当言語のファイルがなければ英語辞書にフォールバック
        if not os.path.exists(json_path):
            json_path = os.path.join(base_dir, "translations", "dictionary_en.json")

        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                TRANSLATION_DICT = json.load(f)
    except Exception as e:
        print(f"翻訳辞書の読み込み失敗: {str(e)}")

load_dictionary()
"""

with open(dict_py_path, "w", encoding="utf-8") as f:
    f.write(new_dictionary_py)

print("[設定完了] Core/Dictionary.py を多言語動的ロード仕様に更新しました！")
''')