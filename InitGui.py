# -*- coding: utf-8 -*-
# InitGui.py
import os
import sys
import FreeCAD
import FreeCADGui

if '__file__' in globals() and __file__:
    base_path = os.path.dirname(os.path.abspath(__file__))
else:
    user_mod_dir = os.path.join(FreeCAD.getUserAppDataDir(), "Mod")
    base_path = os.path.normpath(os.path.join(user_mod_dir, "Ring"))

if base_path not in sys.path:
    sys.path.append(base_path)

icons_dir = os.path.join(base_path, "icons").replace('\\', '/')
if os.path.exists(icons_dir):
    FreeCADGui.addIconPath(icons_dir)

try:
    import Core.Controller as Controller
    Controller.register_workbench(base_path)
except Exception as e:
    import traceback
    from FreeCAD import Console
    Console.PrintError(f"Coreシステムの読み込みに失敗しました: {str(e)}\n")
    Console.PrintError(traceback.format_exc())