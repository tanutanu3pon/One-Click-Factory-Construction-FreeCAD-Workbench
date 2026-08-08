# -*- coding: utf-8 -*-
# Core/Controller.py
import os
import sys
import re
import FreeCAD
import FreeCADGui

try:
    from Core.Dictionary import TRANSLATION_DICT
except ImportError:
    TRANSLATION_DICT = {}

def translate_text(text, lang):
    if lang != "English" or not text:
        return text
    if text in TRANSLATION_DICT:
        return TRANSLATION_DICT[text]
    match = re.match(r"^(<[^>]+>)*(.*?)(</[^>]+>|[:：\s])*$", text)
    if match:
        prefix = match.group(1) or ""
        core_text = match.group(2) or ""
        suffix = match.group(3) or ""
        if core_text in TRANSLATION_DICT:
            return prefix + TRANSLATION_DICT[core_text] + suffix
    new_text = text
    for jp in sorted(TRANSLATION_DICT.keys(), key=len, reverse=True):
        if jp in new_text:
            new_text = new_text.replace(jp, TRANSLATION_DICT[jp])
    return new_text

def auto_translate_widget(widget, lang):
    if lang != "English":
        return
    try:
        from PySide2 import QtWidgets
    except ImportError:
        from PySide6 import QtWidgets
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
    import Core.Language as Language
    current_lang = Language.get_language()

    original_addCommand = FreeCADGui.addCommand

    def custom_addCommand(command_name, command_obj):
        if hasattr(command_obj, 'GetResources'):
            orig_get_resources = command_obj.GetResources
            def wrapped_get_resources(*args, **kwargs):
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
                try:
                    from PySide2 import QtWidgets
                except ImportError:
                    from PySide6 import QtWidgets
                
                orig_dialog_exec = getattr(QtWidgets.QDialog, 'exec_', None)
                orig_dialog_exec_new = getattr(QtWidgets.QDialog, 'exec', None)
                orig_dialog_show = QtWidgets.QDialog.show
                orig_msg_exec = getattr(QtWidgets.QMessageBox, 'exec_', None)
                orig_msg_exec_new = getattr(QtWidgets.QMessageBox, 'exec', None)
                orig_prog_show = QtWidgets.QProgressDialog.show
                orig_prog_setLabel = QtWidgets.QProgressDialog.setLabelText
                orig_prog_setWindow = QtWidgets.QProgressDialog.setWindowTitle
                orig_input_getItem = QtWidgets.QInputDialog.getItem
                orig_input_getDouble = QtWidgets.QInputDialog.getDouble
                orig_input_getInt = QtWidgets.QInputDialog.getInt
                orig_input_getText = QtWidgets.QInputDialog.getText
                orig_msg_warning = QtWidgets.QMessageBox.warning
                orig_msg_critical = QtWidgets.QMessageBox.critical
                orig_msg_information = QtWidgets.QMessageBox.information
                orig_msg_question = QtWidgets.QMessageBox.question

                def patched_dialog_exec(dialog_self):
                    auto_translate_widget(dialog_self, current_lang)
                    return orig_dialog_exec(dialog_self) if orig_dialog_exec else orig_dialog_exec_new(dialog_self)
                def patched_dialog_exec_new(dialog_self):
                    auto_translate_widget(dialog_self, current_lang)
                    return orig_dialog_exec_new(dialog_self)
                def patched_dialog_show(dialog_self):
                    auto_translate_widget(dialog_self, current_lang)
                    return orig_dialog_show(dialog_self)
                def patched_msg_exec(msg_self):
                    auto_translate_widget(msg_self, current_lang)
                    return orig_msg_exec(msg_self) if orig_msg_exec else orig_msg_exec_new(msg_self)
                def patched_msg_exec_new(msg_self):
                    auto_translate_widget(msg_self, current_lang)
                    return orig_msg_exec_new(msg_self)
                def patched_prog_show(prog_self):
                    auto_translate_widget(prog_self, current_lang)
                    return orig_prog_show(prog_self)
                def patched_prog_setLabel(prog_self, text):
                    return orig_prog_setLabel(prog_self, translate_text(text, current_lang))
                def patched_prog_setWindow(prog_self, text):
                    return orig_prog_setWindow(prog_self, translate_text(text, current_lang))

                def patched_input_getItem(parent, title, label, items, *args, **kwargs):
                    t_title = translate_text(title, current_lang)
                    t_label = translate_text(label, current_lang)
                    t_items = [translate_text(item, current_lang) for item in items]
                    res_text, ok = orig_input_getItem(parent, t_title, t_label, t_items, *args, **kwargs)
                    if ok and current_lang == "English":
                        reverse_dict = {translate_text(item, current_lang): item for item in items}
                        if res_text in reverse_dict:
                            res_text = reverse_dict[res_text]
                    return res_text, ok

                def patched_input_getDouble(parent, title, label, *args, **kwargs):
                    return orig_input_getDouble(parent, translate_text(title, current_lang), translate_text(label, current_lang), *args, **kwargs)
                def patched_input_getInt(parent, title, label, *args, **kwargs):
                    return orig_input_getInt(parent, translate_text(title, current_lang), translate_text(label, current_lang), *args, **kwargs)
                def patched_input_getText(parent, title, label, *args, **kwargs):
                    return orig_input_getText(parent, translate_text(title, current_lang), translate_text(label, current_lang), *args, **kwargs)
                def patched_msg_warning(parent, title, text, *args, **kwargs):
                    return orig_msg_warning(parent, translate_text(title, current_lang), translate_text(text, current_lang), *args, **kwargs)
                def patched_msg_critical(parent, title, text, *args, **kwargs):
                    return orig_msg_critical(parent, translate_text(title, current_lang), translate_text(text, current_lang), *args, **kwargs)
                def patched_msg_information(parent, title, text, *args, **kwargs):
                    return orig_msg_information(parent, translate_text(title, current_lang), translate_text(text, current_lang), *args, **kwargs)
                def patched_msg_question(parent, title, text, *args, **kwargs):
                    return orig_msg_question(parent, translate_text(title, current_lang), translate_text(text, current_lang), *args, **kwargs)

                if orig_dialog_exec: QtWidgets.QDialog.exec_ = patched_dialog_exec
                if orig_dialog_exec_new: QtWidgets.QDialog.exec = patched_dialog_exec_new
                QtWidgets.QDialog.show = patched_dialog_show
                if orig_msg_exec: QtWidgets.QMessageBox.exec_ = patched_msg_exec
                if orig_msg_exec_new: QtWidgets.QMessageBox.exec = patched_msg_exec_new
                QtWidgets.QProgressDialog.show = patched_prog_show
                QtWidgets.QProgressDialog.setLabelText = patched_prog_setLabel
                QtWidgets.QProgressDialog.setWindowTitle = patched_prog_setWindow
                QtWidgets.QInputDialog.getItem = patched_input_getItem
                QtWidgets.QInputDialog.getDouble = patched_input_getDouble
                QtWidgets.QInputDialog.getInt = patched_input_getInt
                QtWidgets.QInputDialog.getText = patched_input_getText
                QtWidgets.QMessageBox.warning = patched_msg_warning
                QtWidgets.QMessageBox.critical = patched_msg_critical
                QtWidgets.QMessageBox.information = patched_msg_information
                QtWidgets.QMessageBox.question = patched_msg_question
                
                # ★修正ポイント：大外でエラーを監視し、全自動でフリーズを解除する
                try:
                    orig_activated(*args, **kwargs)
                except Exception as e:
                    import traceback
                    FreeCAD.Console.PrintError(traceback.format_exc())
                    
                    # 1. 進行中のトランザクション（Undo用履歴）があれば強制破棄（ゴミを残さない）
                    doc = FreeCAD.activeDocument()
                    if doc and hasattr(doc, 'hasPendingTransaction') and doc.hasPendingTransaction():
                        doc.abortTransaction()
                    
                    # 2. 画面フリーズ（UpdateEnabled(False)のまま停止すること）の強制解除
                    main_win = FreeCADGui.getMainWindow()
                    if main_win:
                        main_win.setUpdatesEnabled(True)
                        
                    # 3. 画面に残りっぱなしのプログレスバーを強制的に閉じる
                    for widget in QtWidgets.QApplication.topLevelWidgets():
                        if isinstance(widget, QtWidgets.QProgressDialog):
                            widget.close()
                            
                    # 4. ユーザーにエラーを通知
                    QtWidgets.QMessageBox.critical(None, "ツール実行エラー", f"処理中に予期せぬエラーが発生しました。\n\n詳細:\n{str(e)}")
                    
                finally:
                    if orig_dialog_exec: QtWidgets.QDialog.exec_ = orig_dialog_exec
                    if orig_dialog_exec_new: QtWidgets.QDialog.exec = orig_dialog_exec_new
                    QtWidgets.QDialog.show = orig_dialog_show
                    if orig_msg_exec: QtWidgets.QMessageBox.exec_ = orig_msg_exec
                    if orig_msg_exec_new: QtWidgets.QMessageBox.exec = orig_msg_exec_new
                    QtWidgets.QProgressDialog.show = orig_prog_show
                    QtWidgets.QProgressDialog.setLabelText = orig_prog_setLabel
                    QtWidgets.QProgressDialog.setWindowTitle = orig_prog_setWindow
                    QtWidgets.QInputDialog.getItem = orig_input_getItem
                    QtWidgets.QInputDialog.getDouble = orig_input_getDouble
                    QtWidgets.QInputDialog.getInt = orig_input_getInt
                    QtWidgets.QInputDialog.getText = orig_input_getText
                    QtWidgets.QMessageBox.warning = orig_msg_warning
                    QtWidgets.QMessageBox.critical = orig_msg_critical
                    QtWidgets.QMessageBox.information = orig_msg_information
                    QtWidgets.QMessageBox.question = orig_msg_question
                        
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
            for tool in tools_config:
                module_name = f"Tool.{tool['module']}"
                try:
                    exec(f"import {module_name}")
                    command_list.append(tool['id'])
                except (ImportError, ModuleNotFoundError):
                    continue
                except Exception as e:
                    FreeCAD.Console.PrintWarning(f"ツール [{tool['module']}] スキップ: {str(e)}\n")
            
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
            for tool in tools_config:
                module_name = f"Tool.{tool['module']}"
                try:
                    exec(f"import {module_name}")
                    command_list.append(tool['id'])
                except (ImportError, ModuleNotFoundError):
                    continue
                except Exception as e:
                    FreeCAD.Console.PrintWarning(f"ツール [{tool['module']}] スキップ: {str(e)}\n")
            
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