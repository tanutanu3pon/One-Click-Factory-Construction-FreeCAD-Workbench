# -*- coding: utf-8 -*-
# Core/Language.py
try:
    from PySide2 import QtWidgets, QtCore
except ImportError:
    from PySide6 import QtWidgets, QtCore

import FreeCAD

_CURRENT_LANG = None

def get_language():
    """ 起動時にポップアップを出し、FreeCAD本体の言語設定も同時に書き換えます """
    global _CURRENT_LANG
    
    if _CURRENT_LANG is not None:
        return _CURRENT_LANG

    languages = ["日本語", "English"]
    
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
        if _CURRENT_LANG == "English":
            param.SetString("Language", "English")
        else:
            param.SetString("Language", "Japanese")
    except Exception:
        pass
            
    return _CURRENT_LANG