# -*- coding: utf-8 -*-
# Core/Controller.py
import os
import re
import importlib
import FreeCAD
import FreeCADGui

# 【修正】絶対インポートに統一
from Core.QtCompat import QtWidgets

def translate_text(text, lang):
    import Core.Dictionary as Dictionary
    if not text:
        return text
    
    trans_dict = Dictionary.TRANSLATION_DICT
    rev_dict = Dictionary.REVERSE_DICT
    clean_dict = Dictionary.CLEAN_TRANSLATION_DICT

    # 【英語モード】日本語 -> 英語
    if lang == "English":
        if text in trans_dict:
            return trans_dict[text]

        clean_text = re.sub(r'(の作成|の生成|の計算|を作成します|を生成します|を作成|を生成|作成|生成)$', '', text).strip()
        if clean_text in clean_dict:
            return clean_dict[clean_text]

        match = re.match(r"^(<[^>]+>)*(.*?)(</[^>]+>|[:：\s])*$", text)
        if match:
            prefix, core_text, suffix = match.group(1) or "", match.group(2) or "", match.group(3) or ""
            if core_text in trans_dict:
                return prefix + trans_dict[core_text] + suffix

    # 【日本語モード】英語 -> 日本語（逆引き）
    elif lang == "日本語":
        if text in rev_dict:
            return rev_dict[text]
            
        match = re.match(r"^(<[^>]+>)*(.*?)(</[^>]+>|[:：\s])*$", text)
        if match:
            prefix, core_text, suffix = match.group(1) or "", match.group(2) or "", match.group(3) or ""
            if core_text in rev_dict:
                return prefix + rev_dict[core_text] + suffix

    return text

def auto_translate_widget(widget, lang):
    """ダイアログやウィンドウ内の全テキストを現在の言語へ変換"""
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

def update_all_open_ui(lang):
    """現在画面上に開いているすべてのウィンドウ・ダイアログの表記を即座に書き換える"""
    for widget in QtWidgets.QApplication.topLevelWidgets():
        try:
            auto_translate_widget(widget, lang)
        except Exception:
            pass

# --- 1. QDialogのカスタムクラス ---
class TranslatedDialog(QtWidgets.QDialog):
    def showEvent(self, event):
        import Core.Language as Language
        try:
            current_lang = Language.get_language()
            auto_translate_widget(self, current_lang)
        except Exception as e:
            # 【修正】エラーを握りつぶさずコンソールに出力する
            FreeCAD.Console.PrintError(f"Translation Error (Dialog): {e}\n")
        super(TranslatedDialog, self).showEvent(event)

# --- 2. QInputDialogの安全なラッパークラス ---
class TranslatedInputDialog:
    @staticmethod
    def getDouble(parent, title, label, *args, **kwargs):
        import Core.Language as Language
        lang = Language.get_language()
        trans_title = translate_text(title, lang)
        trans_label = translate_text(label, lang)
        return QtWidgets.QInputDialog.getDouble(parent, trans_title, trans_label, *args, **kwargs)

    @staticmethod
    def getText(parent, title, label, *args, **kwargs):
        import Core.Language as Language
        lang = Language.get_language()
        trans_title = translate_text(title, lang)
        trans_label = translate_text(label, lang)
        return QtWidgets.QInputDialog.getText(parent, trans_title, trans_label, *args, **kwargs)

    @staticmethod
    def getInt(parent, title, label, *args, **kwargs):
        import Core.Language as Language
        lang = Language.get_language()
        trans_title = translate_text(title, lang)
        trans_label = translate_text(label, lang)
        return QtWidgets.QInputDialog.getInt(parent, trans_title, trans_label, *args, **kwargs)

    @staticmethod
    def getItem(parent, title, label, items, *args, **kwargs):
        import Core.Language as Language
        lang = Language.get_language()
        trans_title = translate_text(title, lang)
        trans_label = translate_text(label, lang)
        trans_items = [translate_text(str(it), lang) for it in items]
        return QtWidgets.QInputDialog.getItem(parent, trans_title, trans_label, trans_items, *args, **kwargs)

def register_workbench(base_path):
    original_addCommand = FreeCADGui.addCommand

    def custom_addCommand(command_name, command_obj):
        if hasattr(command_obj, 'GetResources'):
            orig_get_resources = command_obj.GetResources
            def wrapped_get_resources(*args, **kwargs):
                import Core.Language as Language
                current_lang = Language.get_language()
                res = orig_get_resources(*args, **kwargs)
                if 'MenuText' in res and res['MenuText']:
                    res['MenuText'] = translate_text(res['MenuText'], current_lang)
                if 'ToolTip' in res and res['ToolTip']:
                    res['ToolTip'] = translate_text(res['ToolTip'], current_lang)
                return res
            command_obj.GetResources = wrapped_get_resources

        if hasattr(command_obj, 'Activated'):
            orig_activated = command_obj.Activated
            def wrapped_activated(*args, **kwargs):
                try:
                    orig_activated(*args, **kwargs)
                except Exception as e:
                    import traceback
                    FreeCAD.Console.PrintError(traceback.format_exc())
                    
                    doc = FreeCAD.activeDocument()
                    if doc:
                        try:
                            doc.abortTransaction()
                        except Exception:
                            pass
                    
                    main_win = FreeCADGui.getMainWindow()
                    if main_win:
                        main_win.setUpdatesEnabled(True)
                        
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
        def GetIcon(self): return ring_icon_path
        def Initialize(self):
            tools_config = [
                {"module": "MakeRing", "id": "Ring_MakeRing"},
                {"module": "Tyoukoku", "id": "Ring_Tyoukoku"},
                {"module": "Daiya",    "id": "Ring_Daiya"},
                {"module": "Connect",  "id": "Ring_Connect"},
                {"module": "Weight",   "id": "Ring_Weight"},
                {"module": "MakeJig",  "id": "Ring_MakeJig"},
                {"module": "Magatama", "id": "Ring_Magatama"},
                {"module": "Suiteki",  "id": "Ring_Suiteki"},
                {"module": "Mikazuki", "id": "Ring_Mikazuki"},
                {"module": "Heart",    "id": "Ring_Heart"},
                {"module": "Hoshi",    "id": "Ring_Hoshi"},
                {"module": "MakeDonguri", "id": "Ring_MakeDonguri"},
                {"module": "Inkan",    "id": "Ring_Inkan"},    
                {"module": "Button",   "id": "Ring_Button"},
                {"module": "MakeMug",  "id": "Ring_Mug"},
                {"module": "MakeSara", "id": "Ring_MakeSara"},
                {"module": "MakeHashioki", "id": "Ring_MakeHashioki"},
                {"module": "MakeCoaster", "id": "Ring_MakeCoaster"},
                {"module": "MakeVase", "id": "Ring_Vase"},
                {"module": "Box",      "id": "Ring_Box"},
                {"module": "BatteryBox", "id": "Ring_BatteryBox"},
                {"module": "MakeSpoon", "id": "Ring_MakeSpoon"},
                {"module": "MakeHashi", "id": "Ring_MakeHashi"},
                {"module": "MakeSHook", "id": "Ring_MakeSHook"},
                {"module": "MakeCookie", "id": "Ring_MakeCookie"},
                {"module": "MakePlanetaryGear", "id": "Ring_MakePlanetaryGear"},
                {"module": "Make3DText", "id": "Ring_Make3DText"},    
                {"module": "ModelPresenter", "id": "Ring_ModelPresenter"},  
                {"module": "MakeFish", "id": "Ring_MakeFish"},
                {"module": "Dangomushi", "id": "Ring_Dangomushi"},
            ]
            FreeCADGui.addCommand = custom_addCommand
            command_list = []
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
        def GetClassName(self): return "Gui::PythonWorkbench"

    class ConstructionWorkbench(FreeCADGui.Workbench):
        MenuText = "Construction"
        ToolTip = "Construction Workbench"
        Icon = const_icon_path
        def GetIcon(self): return const_icon_path
        def Initialize(self):
            tools_config = [
                {"module": "MakeWall", "id": "Construction_MakeWall"},
                {"module": "CalcWall", "id": "Construction_CalcWall"},
                {"module": "MakeRoad", "id": "Construction_MakeRoad"},
                {"module": "MakeTetrapod", "id": "Construction_MakeTetrapod"},
                {"module": "MakeExcelSurface", "id": "Construction_MakeExcelSurface"},
                {"module": "CalcEarthworkSolid", "id": "Construction_CalcEarthworkSolid"},
            ]
            FreeCADGui.addCommand = custom_addCommand
            command_list = []
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
        def GetClassName(self): return "Gui::PythonWorkbench"

    try:
        FreeCADGui.addWorkbench(RingWorkbench())
    except KeyError:
        pass
    try:
        FreeCADGui.addWorkbench(ConstructionWorkbench())
    except KeyError:
        pass