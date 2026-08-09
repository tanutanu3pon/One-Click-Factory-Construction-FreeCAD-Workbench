# -*- coding: utf-8 -*-
# InitGui.py
import os
import sys
import inspect
import FreeCAD
import FreeCADGui

# __file__ が存在しないFreeCAD起動環境でも確実にパスを取得
try:
    if '__file__' in globals() and __file__:
        base_path = os.path.dirname(os.path.abspath(__file__))
    else:
        current_file = inspect.getfile(inspect.currentframe())
        base_path = os.path.dirname(os.path.abspath(current_file))
except Exception:
    base_path = os.path.dirname(os.path.abspath(inspect.getfile(lambda: None)))

# 【修正】0番目(最優先)への強制追加を避け、末尾に追加(append)してFreeCAD全体の破壊を防ぎます
if base_path not in sys.path:
    sys.path.append(base_path)

icons_dir = os.path.join(base_path, "icons").replace('\\', '/')
if os.path.exists(icons_dir):
    FreeCADGui.addIconPath(icons_dir)

try:
    # エラーが出ない元のインポート方式（絶対インポート）に戻します
    import Core.Language as Language
    import Core.Dictionary as Dictionary
    import Core.Controller as Controller

    # 起動時のダイアログは出さず、設定から言語をサイレントに読み込む
    Language.init_language()
    Dictionary.load_dictionary()

    # ワークベンチを登録
    Controller.register_workbench(base_path)

except Exception as e:
    import traceback
    from FreeCAD import Console
    Console.PrintError(f"Coreシステムの読み込みに失敗しました: {str(e)}\n")
    Console.PrintError(traceback.format_exc())