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
        if '__file__' in globals() and __file__:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        else:
            current_file = inspect.getfile(inspect.currentframe())
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(current_file)))

        current_lang = Language.get_language()

        # 日本語表示の場合は辞書読み込みをスキップ（高速化）
        if current_lang == "日本語":
            return

        # 英語の場合は dictionary_en.json を読み込む
        json_path = os.path.join(base_dir, "translations", "dictionary_en.json")

        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                TRANSLATION_DICT = json.load(f)
    except Exception as e:
        print(f"翻訳辞書の読み込み失敗: {str(e)}")

load_dictionary()