# -*- coding: utf-8 -*-
# Core/Controller.py
import os
import sys
import re
import importlib
import FreeCAD
import FreeCADGui

def translate_text(text, lang):
    import Core.Dictionary as Dictionary
    # 日本語（デフォルト）または空文字の場合はそのまま返す
    if lang == "日本語" or not text:
        return text
    
    # 常に最新の辞書を参照する
    trans_dict = Dictionary.TRANSLATION_DICT

    if text in trans_dict:
        return trans_dict[text]
    
    match = re.match(r"^(<[^>]+>)*(.*?)(</[^>]+>|[:：\s])*$", text)
    if match:
        prefix = match.group(1) or ""
        core_text = match.group(2) or ""
        suffix = match.group(3) or ""
        if core_text in trans_dict:
            return prefix + trans_dict[core_text] + suffix
            
    new_text = text
    for jp in sorted(trans_dict.keys(), key=len, reverse=True):
        if jp in new_text:
            new_text = new_text.replace(jp, trans_dict[jp])
    return new_text


def auto_translate_widget(widget, lang):
    if lang == "日本語":
        return
    
    # ★直接インポートを削除し、QtCompatを使用
    from Core.QtCompat import QtWidgets
        
    if hasattr(widget, "windowTitle") and widget.windowTitle():
        widget.setWindowTitle(translate_text(widget.windowTitle(), lang))
    for form in widget.findChildren(QtWidgets.QFormLayout):
        for row in range(form.rowCount()):
            label_item = form.itemAt(row, QtWidgets.QFormLayout.LabelRole)
            if label_item and label_item.widget():
                lbl = label_item.widget()
                if hasattr(lbl, "text") and lbl.text():
                    lbl.setText(translate_text(lbl.text(), lang))
    for label in widget.findChildren(QtWidgets.QLabel):
        if label.text():
            label.setText(translate_text(label.text(), lang))
    for btn in widget.findChildren(QtWidgets.QAbstractButton):
        if btn.text():
            btn.setText(translate_text(btn.text(), lang))
    for group in widget.findChildren(QtWidgets.QGroupBox):
        if group.title():
            group.setTitle(translate_text(group.title(), lang))
    for combo in widget.findChildren(QtWidgets.QComboBox):
        for i in range(combo.count()):
            txt = combo.itemText(i)
            if txt:
                combo.setItemText(i, translate_text(txt, lang))


def register_workbench(base_path):
    original_addCommand = FreeCADGui.addCommand

    def custom_addCommand(command_name, command_obj):
        if hasattr(command_obj, 'GetResources'):
            orig_get_resources = command_obj.GetResources
            def wrapped_get_resources(*args, **kwargs):
                import Core.Language as Language
                # UI登録時はその時点の言語を取得
                current_lang = Language.get_language()
                res = orig_get_resources(*args, **kwargs)
                if 'MenuText' in res:
                    res['MenuText'] = translate_text(res['MenuText'] if 'の作成' in res['MenuText'] else f"{res['MenuText']}の作成", current_lang)
                if 'ToolTip' in res:
                    res['ToolTip'] = translate_text(res['ToolTip'] if 'を作成します' in res['ToolTip'] else f"{res['ToolTip']}を作成します", current_lang)
                return res
            command_obj.GetResources = wrapped_get_resources

        if hasattr(command_obj, 'Activated'):
            orig_activated = command_obj.Activated
            def wrapped_activated(*args, **kwargs):
                # ★直接インポートを削除し、QtCompatを使用
                from Core.QtCompat import QtWidgets
                
                try:
                    orig_activated(*args, **kwargs)
                except Exception as e:
                    import traceback
                    FreeCAD.Console.PrintError(traceback.format_exc())
                    
                    doc = FreeCAD.activeDocument()
                    # エラー発生時はトランザクションを安全に破棄
                    if doc and hasattr(doc, 'hasPendingTransaction') and doc.hasPendingTransaction():
                        doc.abortTransaction()
                    
                    # 画面フリーズの解除
                    main_win = FreeCADGui.getMainWindow()
                    if main_win:
                        main_win.setUpdatesEnabled(True)
                        
                    # 残存しているプログレスバーがあれば閉じる
                    for widget in QtWidgets.QApplication.topLevelWidgets():
                        if isinstance(widget, QtWidgets.QProgressDialog):
                            widget.close()
                            
                    QtWidgets.QMessageBox.critical(None, "ツール実行エラー", f"処理中に予期せぬエラーが発生しました。\n\n詳細:\n{str(e)}")
                        
            command_obj.Activated = wrapped_activated

        original_addCommand(command_name, command_obj)


    gui_path = base_path.replace('\\', '/')
    icons_dir = os.path.join(gui_path, "icons").replace('\\', '/')
    FreeCADGui.addIconPath(icons_dir)
    
    ring_icon_path = os.path.join(icons_dir, "main.png").replace('\\', '/')
    const_icon_path = os.path.join(icons_dir, "main1.png").replace('\\', '/')

    class RingWorkbench(FreeCADGui.Workbench):
        MenuText = "Click Factory"
        ToolTip = "Click Factory Workbench"
        Icon = ring_icon_path

        def GetIcon(self):
            return ring_icon_path

        def Initialize(self):
            self.Icon = ring_icon_path

            tools_config = [
                {"module": "Launcher", "id": "Ring_Launcher"},
                {"module": "MakeRing", "id": "Ring_MakeRing"},
                {"module": "Tyoukoku", "id": "Ring_Tyoukoku"},
                {"module": "Daiya",    "id": "Ring_Daiya"},
                {"module": "Connect",  "id": "Ring_Connect"},
                {"module": "Weight",   "id": "Ring_Weight"},
                {"module": "MakeJig",   "id": "Ring_MakeJig"},
                {"module": "Magatama", "id": "Ring_Magatama"},
                {"module": "Suiteki",  "id": "Ring_Suiteki"},
                {"module": "Mikazuki", "id": "Ring_Mikazuki"},
                {"module": "Heart",    "id": "Ring_Heart"},
                {"module": "Hoshi",    "id": "Ring_Hoshi"},
                {"module": "Inkan",    "id": "Ring_Inkan"},    
                {"module": "Button",   "id": "Ring_Button"},
                {"module": "MakeMug",  "id": "Ring_Mug"},
                {"module": "MakeVase", "id": "Ring_Vase"},
                {"module": "Box",      "id": "Ring_Box"},
                {"module": "BatteryBox", "id": "Ring_BatteryBox"},
                {"module": "MakeSpoon", "id": "Ring_MakeSpoon"},
                {"module": "MakeSHook", "id": "Ring_MakeSHook"},
                {"module": "MakeCookie", "id": "Ring_MakeCookie"},
                {"module": "MakePlanetaryGear", "id": "Ring_MakePlanetaryGear"},
                {"module": "Make3DText", "id": "Ring_Make3DText"},    
                {"module": "ModelPresenter", "id": "Ring_ModelPresenter"},  
                {"module": "MakeFish", "id": "Ring_MakeFish"},
            ]

            FreeCADGui.addCommand = custom_addCommand
            command_list = []
            
            # ★ 修正: try...finally で囲んで確実に original_addCommand を復元する
            try:
                for tool in tools_config:
                    module_name = f"Tool.{tool['module']}"
                    try:
                        importlib.import_module(module_name)
                        command_list.append(tool['id'])
                    except (ImportError, ModuleNotFoundError):
                        continue
                    except Exception as e:
                        FreeCAD.Console.PrintWarning(f"ツール [{tool['module']}] スキップ: {str(e)}\n")
            finally:
                FreeCADGui.addCommand = original_addCommand
                
            if command_list:
                self.appendToolbar("Ring Tools", command_list)
                self.appendMenu(["&Ring"], command_list)

        def Activated(self): pass
        def Deactivated(self): pass
        def GetClassName(self): return "Gui::PythonWorkbench"

    class ConstructionWorkbench(FreeCADGui.Workbench):
        MenuText = "Construction"
        ToolTip = "Construction Workbench"
        Icon = const_icon_path

        def GetIcon(self):
            return const_icon_path

        def Initialize(self):
            self.Icon = const_icon_path

            tools_config = [
                {"module": "Launcher", "id": "Construction_Launcher"},
                {"module": "MakeWall", "id": "Construction_MakeWall"},
                {"module": "CalcWall", "id": "Construction_CalcWall"},
                {"module": "MakeRoad", "id": "Construction_MakeRoad"},
                {"module": "MakeTetrapod", "id": "Construction_MakeTetrapod"},
                {"module": "MakeExcelSurface", "id": "Construction_MakeExcelSurface"},
                {"module": "CalcEarthworkSolid", "id": "Construction_CalcEarthworkSolid"},
            ]

            FreeCADGui.addCommand = custom_addCommand
            command_list = []
            
            # ★ 修正: try...finally で囲んで確実に original_addCommand を復元する
            try:
                for tool in tools_config:
                    module_name = f"Tool.{tool['module']}"
                    try:
                        importlib.import_module(module_name)
                        command_list.append(tool['id'])
                    except (ImportError, ModuleNotFoundError):
                        continue
                    except Exception as e:
                        FreeCAD.Console.PrintWarning(f"ツール [{tool['module']}] スキップ: {str(e)}\n")
            finally:
                FreeCADGui.addCommand = original_addCommand
                
            if command_list:
                self.appendToolbar("Construction Tools", command_list)
                self.appendMenu(["&Construction"], command_list)

        def Activated(self): pass
        def Deactivated(self): pass
        def GetClassName(self): return "Gui::PythonWorkbench"

    try:
        FreeCADGui.addWorkbench(RingWorkbench())
    except KeyError:
        pass

    try:
        FreeCADGui.addWorkbench(ConstructionWorkbench())
    except KeyError:
        pass