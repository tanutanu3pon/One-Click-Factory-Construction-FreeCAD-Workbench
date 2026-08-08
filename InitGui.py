# -*- coding: utf-8 -*-
# InitGui.py
import os
import sys
import inspect
import FreeCAD
import FreeCADGui

# __file__ が存在しないFreeCAD起動環境でも確実にパスを取得する修正
try:
    if '__file__' in globals() and __file__:
        base_path = os.path.dirname(os.path.abspath(__file__))
    else:
        current_file = inspect.getfile(inspect.currentframe())
        base_path = os.path.dirname(os.path.abspath(current_file))
except Exception:
    base_path = os.path.dirname(os.path.abspath(inspect.getfile(lambda: None)))

if base_path not in sys.path:
    sys.path.append(base_path)

icons_dir = os.path.join(base_path, "icons").replace('\\', '/')
if os.path.exists(icons_dir):
    FreeCADGui.addIconPath(icons_dir)

try:
    import Core.Language as Language
    import Core.Dictionary as Dictionary
    import Core.Controller as Controller

    # ワークベンチ登録前に言語選択ダイアログを表示・辞書ロードを完了させる
    Language.prompt_language()
    Dictionary.load_dictionary()

    # 言語が確定した状態の辞書でワークベンチを登録
    Controller.register_workbench(base_path)

except Exception as e:
    import traceback
    from FreeCAD import Console
    Console.PrintError(f"Coreシステムの読み込みに失敗しました: {str(e)}\n")
    Console.PrintError(traceback.format_exc())