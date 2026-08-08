# -*- coding: utf-8 -*-
# Core/Language.py
from Core.QtCompat import QtWidgets
import FreeCAD

_CURRENT_LANG = None
_ALREADY_PROMPTED = False  # ★追加: 重複表示を防止するフラグ

def get_language():
    """起動時はダイアログを出さず、設定から言語を静かに読み込む"""
    global _CURRENT_LANG
    
    if _CURRENT_LANG is not None:
        return _CURRENT_LANG

    # FreeCADのユーザーパラメータから前回の言語設定を読み込む
    try:
        param = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/General")
        lang_code = param.GetString("Language", "Japanese")
        
        # FreeCADの内部言語コードとのマッピング（文字化けを修正）
        lang_map = {
            "Japanese": "日本語",
            "English": "English",
            "German": "Deutsch (ドイツ語)",
            "French": "Francais (フランス語)",
            "Chinese Simplified": "中文 (中国語)",
            "Korean": "Korean (韓国語)", 
            "Russian": "Русский (ロシア語)"
        }
        _CURRENT_LANG = lang_map.get(lang_code, "日本語")
    except Exception:
        _CURRENT_LANG = "日本語"
        
    return _CURRENT_LANG


def prompt_language(force=False):
    """ワークベンチ起動時（アイコンクリック時）に呼ばれる、言語選択ダイアログ"""
    global _CURRENT_LANG, _ALREADY_PROMPTED
    
    # ★改善ポイント: すでにダイアログを出した履歴があれば、2回目は強制キャンセル
    if _ALREADY_PROMPTED and not force:
        return get_language()
        
    _ALREADY_PROMPTED = True  # 表示したことを記録
    
    # リスト内の文字化けも修正
    languages = [
        "日本語", 
        "English", 
        "Deutsch (ドイツ語)", 
        "Francais (フランス語)", 
        "中文 (中国語)", 
        "Korean (韓国語)", 
        "Русский (ロシア語)"
    ]
    
    current = get_language()
    default_index = languages.index(current) if current in languages else 0
    
    try:
        lang, ok = QtWidgets.QInputDialog.getItem(
            None, 
            "Language / 言語設定", 
            "開発モード: 言語を選択してください\n(Choose language):", 
            languages, 
            default_index, False
        )
        if ok and lang:
            # 前回と同じ言語なら重い保存処理をスキップして即終了
            if lang == current:
                return _CURRENT_LANG
            _CURRENT_LANG = lang
        else:
            return _CURRENT_LANG # キャンセル時はそのまま
    except Exception:
        pass
        
    # --- ここから下はFreeCAD全体を更新するため「重い処理」 ---
    try:
        param = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/General")
        target_fc_lang = "Japanese"
        
        if "English" in _CURRENT_LANG:
            target_fc_lang = "English"
        elif "Deutsch" in _CURRENT_LANG:
            target_fc_lang = "German"
        elif "Francais" in _CURRENT_LANG:
            target_fc_lang = "French"
        elif "中文" in _CURRENT_LANG:
            target_fc_lang = "Chinese Simplified"
        elif "Korean" in _CURRENT_LANG: # 照合ロジックの文字化けを修正
            target_fc_lang = "Korean"
        elif "Русский" in _CURRENT_LANG:
            target_fc_lang = "Russian"
            
        # FreeCAD本体の設定と違う場合のみ書き換える
        if param.GetString("Language", "") != target_fc_lang:
            param.SetString("Language", target_fc_lang)
            
    except Exception:
        pass
            
    return _CURRENT_LANG