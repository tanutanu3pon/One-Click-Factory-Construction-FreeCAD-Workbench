exec(r'''
import os

wb_dir = r"C:\Users\horis\AppData\Roaming\FreeCAD\v1-1\Mod\Ring"
lang_py_path = os.path.join(wb_dir, "Core", "Language.py")

new_language_py = """# -*- coding: utf-8 -*-
# Core/Language.py
from Core.QtCompat import QtWidgets
import FreeCAD

_CURRENT_LANG = None

def get_language():
    global _CURRENT_LANG
    
    if _CURRENT_LANG is not None:
        return _CURRENT_LANG

    # 対応言語リスト
    languages = [
        "日本語", 
        "English", 
        "Deutsch (ドイツ語)", 
        "Francais (フランス語)", 
        "中文 (中国語)", 
        "??語 (韓国語)", 
        "Русский (ロシア語)"
    ]
    
    try:
        lang, ok = QtWidgets.QInputDialog.getItem(
            None, 
            "Language / 言語設定", 
            "Choose language / 言語を選択してください:", 
            languages, 
            0, False
        )
        if ok and lang:
            _CURRENT_LANG = lang
        else:
            _CURRENT_LANG = "日本語"
    except Exception:
        _CURRENT_LANG = "日本語"
        
    try:
        param = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/General")
        if "English" in _CURRENT_LANG:
            param.SetString("Language", "English")
        elif "Deutsch" in _CURRENT_LANG:
            param.SetString("Language", "German")
        elif "Francais" in _CURRENT_LANG:
            param.SetString("Language", "French")
        elif "中文" in _CURRENT_LANG:
            param.SetString("Language", "Chinese Simplified")
        elif "??" in _CURRENT_LANG:
            param.SetString("Language", "Korean")
        elif "Русский" in _CURRENT_LANG:
            param.SetString("Language", "Russian")
        else:
            param.SetString("Language", "Japanese")
    except Exception:
        pass
            
    return _CURRENT_LANG
"""

with open(lang_py_path, "w", encoding="utf-8") as f:
    f.write(new_language_py)

print("[設定完了] Core/Language.py を多言語（7言語）対応に更新しました！")
''')