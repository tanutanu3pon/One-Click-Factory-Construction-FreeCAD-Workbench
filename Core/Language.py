# -*- coding: utf-8 -*-
# Core/Language.py
import FreeCAD

_CURRENT_LANG = None

def init_language():
    global _CURRENT_LANG
    try:
        param_custom = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/ClickFactory")
        custom_lang = param_custom.GetString("Language", "")

        if custom_lang in ["English", "en"]:
            _CURRENT_LANG = "English"
            return
        elif custom_lang in ["Japanese", "ja", "日本語"]:
            _CURRENT_LANG = "日本語"
            return

        param_main = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/General")
        main_lang = param_main.GetString("Language", "Japanese")

        if main_lang.lower().startswith("en") or main_lang == "English":
            _CURRENT_LANG = "English"
        else:
            _CURRENT_LANG = "日本語"

    except Exception:
        _CURRENT_LANG = "日本語"

def get_language():
    # 【修正】古い記憶（キャッシュ）を使わず、毎回設定を確認しに行く
    init_language()
    return _CURRENT_LANG

def set_language(lang):
    global _CURRENT_LANG
    _CURRENT_LANG = "English" if lang in ["English", "en"] else "日本語"
    try:
        param = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/ClickFactory")
        param.SetString("Language", "English" if _CURRENT_LANG == "English" else "Japanese")

        import Core.Dictionary as Dictionary
        Dictionary.load_dictionary()
    except Exception:
        pass