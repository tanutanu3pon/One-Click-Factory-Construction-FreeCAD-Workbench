# -*- coding: utf-8 -*-
# Core/Language.py
from Core.QtCompat import QtWidgets
import FreeCAD

_CURRENT_LANG = None
_ALREADY_PROMPTED = False

def get_language():
    """起動時はダイアログを出さず、設定から言語を静かに読み込む"""
    global _CURRENT_LANG
    
    if _CURRENT_LANG is not None:
        return _CURRENT_LANG

    try:
        param = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/General")
        lang_code = param.GetString("Language", "Japanese")
        _CURRENT_LANG = "English" if lang_code == "English" else "日本語"
    except Exception:
        _CURRENT_LANG = "日本語"
        
    return _CURRENT_LANG


def prompt_language(force=False):
    """ワークベンチ起動時に呼ばれる言語選択ダイアログ"""
    global _CURRENT_LANG, _ALREADY_PROMPTED
    
    # GUI非依存環境（CUIモード）でのクラッシュ防止
    if not FreeCAD.GuiUp:
        return get_language()
    
    if _ALREADY_PROMPTED and not force:
        return get_language()
        
    _ALREADY_PROMPTED = True
    
    languages = ["日本語", "English"]
    current = get_language()
    default_index = languages.index(current) if current in languages else 0
    
    try:
        lang, ok = QtWidgets.QInputDialog.getItem(
            None, 
            "Language / 言語設定", 
            "言語を選択してください\n(Choose language):", 
            languages, 
            default_index, False
        )
        if ok and lang:
            if lang == current:
                return _CURRENT_LANG
            _CURRENT_LANG = lang
        else:
            return _CURRENT_LANG
    except Exception:
        pass
        
    try:
        param = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/General")
        target_fc_lang = "English" if _CURRENT_LANG == "English" else "Japanese"
            
        if param.GetString("Language", "") != target_fc_lang:
            param.SetString("Language", target_fc_lang)
            
    except Exception:
        pass
            
    return _CURRENT_LANG