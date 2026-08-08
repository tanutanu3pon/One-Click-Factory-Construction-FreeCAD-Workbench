# -*- coding: utf-8 -*-
# Core/Dictionary.py
import os
import json
import inspect
import Core.Language as Language

TRANSLATION_DICT = {}

def load_dictionary():
    global TRANSLATION_DICT
    TRANSLATION_DICT.clear()

    try:
        # スクリプト自身の場所（Core/）を基準に、1階層上のワークベンチのルートディレクトリを取得
        if '__file__' in globals() and __file__:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        else:
            # __file__ が取得できない場合の安全なフォールバック
            # inspect を使用して実行中の現在のファイルのパスを動的に取得する
            current_file = inspect.getfile(inspect.currentframe())
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(current_file)))

        current_lang = Language.get_language()

        # 言語名から対応する辞書ファイル名を決定（文字化けを修正）
        lang_file_map = {
            "English": "dictionary_en.json",
            "Deutsch": "dictionary_de.json",
            "Francais": "dictionary_fr.json",
            "中文": "dictionary_zh.json",
            "Korean": "dictionary_ko.json", 
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