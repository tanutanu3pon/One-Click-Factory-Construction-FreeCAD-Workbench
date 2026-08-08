# -*- coding: utf-8 -*-
# InitGui.py
import os
import sys
import inspect
import FreeCAD
import FreeCADGui

# ハードコードを排除した安全なパス取得
if '__file__' in globals() and __file__:
    base_path = os.path.dirname(os.path.abspath(__file__))
else:
    current_file = inspect.getfile(inspect.currentframe())
    base_path = os.path.dirname(os.path.abspath(current_file))

if base_path not in sys.path:
    sys.path.append(base_path)

icons_dir = os.path.join(base_path, "icons").replace('\\', '/')
if os.path.exists(icons_dir):
    FreeCADGui.addIconPath(icons_dir)

try:
    import Core.Controller as Controller
    Controller.register_workbench(base_path)
    
    # ---------------------------------------------------------
    # 起動時の言語選択ダイアログ処理（フリーズ対策版）
    # ---------------------------------------------------------
    def show_language_dialog():
        import Core.Language as Language
        import Core.Dictionary as Dictionary
        Language.prompt_language()    # 言語ダイアログを表示
        Dictionary.load_dictionary()  # 選択された言語で辞書を再読み込み

    try:
        from PySide2 import QtCore
    except ImportError:
        from PySide6 import QtCore

    # FreeCADのメイン画面の描画が完了するのを待つため、1000ミリ秒(1秒)後に実行
    QtCore.QTimer.singleShot(1000, show_language_dialog)

except Exception as e:
    import traceback
    from FreeCAD import Console
    Console.PrintError(f"Coreシステムの読み込みに失敗しました: {str(e)}\n")
    Console.PrintError(traceback.format_exc())