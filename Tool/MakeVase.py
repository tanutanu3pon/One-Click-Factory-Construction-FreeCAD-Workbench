# -*- coding: utf-8 -*-
import os
import math
import FreeCAD
import FreeCADGui
import Part

# 【修正】絶対インポートで安全にCoreモジュールを読み込む
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedDialog, translate_text
from Core.Language import get_language

# 【修正】TranslatedDialog を継承させて自動翻訳を有効化
class VaseDialog(TranslatedDialog):
    def __init__(self, parent=None):
        super(VaseDialog, self).__init__(parent)
        self.setWindowTitle("スパイラル壺工場 (プリセット機能版)")
        self.resize(380, 360)
        
        layout = QtWidgets.QFormLayout(self)
        
        self.combo_preset = QtWidgets.QComboBox()
        self.combo_preset.addItems([
            "標準（デフォルト）",
            "縦長（スリム）",
            "幅広（ふっくら）",
            "小さめ（ミニ）"
        ])
        
        self.spin_height = QtWidgets.QDoubleSpinBox()
        self.spin_height.setRange(10.0, 2000.0)
        self.spin_height.setSuffix(" mm")
        
        self.spin_max_r = QtWidgets.QDoubleSpinBox()
        self.spin_max_r.setRange(5.0, 1000.0)
        self.spin_max_r.setSuffix(" mm")
        
        self.spin_top_r = QtWidgets.QDoubleSpinBox()
        self.spin_top_r.setRange(2.0, 500.0)
        self.spin_top_r.setSuffix(" mm")

        self.spin_bot_r = QtWidgets.QDoubleSpinBox()
        self.spin_bot_r.setRange(2.0, 500.0)
        self.spin_bot_r.setSuffix(" mm")
        
        self.spin_thick = QtWidgets.QDoubleSpinBox()
        self.spin_thick.setRange(0.5, 50.0)
        self.spin_thick.setSuffix(" mm")

        self.spin_rib_count = QtWidgets.QSpinBox()
        self.spin_rib_count.setRange(4, 200)
        self.spin_rib_count.setSuffix(" 本")

        self.spin_rib_depth = QtWidgets.QDoubleSpinBox()
        self.spin_rib_depth.setRange(0.1, 10.0)
        self.spin_rib_depth.setSuffix(" mm")

        layout.addRow("<b>壺の種類（プリセット）:</b>", self.combo_preset)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        layout.addRow("壺の高さ (Z軸):", self.spin_height)
        layout.addRow("最大半径（お腹）:", self.spin_max_r)
        layout.addRow("口元の半径（上部）:", self.spin_top_r)
        layout.addRow("底面の半径（下部）:", self.spin_bot_r)
        layout.addRow("肉厚（壁の厚み）:", self.spin_thick)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        layout.addRow("スパイラルの本数:", self.spin_rib_count)
        layout.addRow("模様の深さ（凸凹）:", self.spin_rib_depth)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)
        
        self.apply_preset(0)
        self.combo_preset.currentIndexChanged.connect(self.apply_preset)

    def apply_preset(self, index):
        if index == 0:
            self.spin_height.setValue(150.0)
            self.spin_max_r.setValue(60.0)
            self.spin_top_r.setValue(25.0)
            self.spin_bot_r.setValue(35.0)
            self.spin_thick.setValue(4.0)
            self.spin_rib_count.setValue(60)
            self.spin_rib_depth.setValue(1.5)
        elif index == 1:
            self.spin_height.setValue(240.0)
            self.spin_max_r.setValue(50.0)
            self.spin_top_r.setValue(20.0)
            self.spin_bot_r.setValue(30.0)
            self.spin_thick.setValue(4.0)
            self.spin_rib_count.setValue(48)
            self.spin_rib_depth.setValue(1.2)
        elif index == 2:
            self.spin_height.setValue(110.0)
            self.spin_max_r.setValue(85.0)
            self.spin_top_r.setValue(35.0)
            self.spin_bot_r.setValue(45.0)
            self.spin_thick.setValue(4.0)
            self.spin_rib_count.setValue(72)
            self.spin_rib_depth.setValue(2.0)
        elif index == 3:
            self.spin_height.setValue(80.0)
            self.spin_max_r.setValue(35.0)
            self.spin_top_r.setValue(15.0)
            self.spin_bot_r.setValue(20.0)
            self.spin_thick.setValue(2.5)
            self.spin_rib_count.setValue(36)
            self.spin_rib_depth.setValue(0.8)

    def get_values(self):
        return {
            "height": self.spin_height.value(),
            "max_r": self.spin_max_r.value(),
            "top_r": self.spin_top_r.value(),
            "bot_r": self.spin_bot_r.value(),
            "thick": self.spin_thick.value(),
            "rib_count": self.spin_rib_count.value(),
            "rib_depth": self.spin_rib_depth.value()
        }

class Tool_MakeVase:
    def GetResources(self):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "vase.png").replace('\\', '/')
        return {
            'Pixmap': icon_path, 
            'MenuText': "スパイラル壺の作成", 
            'ToolTip': "種類を選んでフリーズなしで様々なスパイラル壺を生成します"
        }

    def Activated(self):
        lang = get_language()
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument("SpiralVaseDesign")

        d = VaseDialog(FreeCADGui.getMainWindow())
        if d.exec_() != QtWidgets.QDialog.Accepted: 
            return
        vals = d.get_values()

        h = vals["height"]
        max_r = vals["max_r"]
        top_r = vals["top_r"]
        bot_r = vals["bot_r"]
        thick = vals["thick"]
        rib_count = vals["rib_count"]
        rib_depth = vals["rib_depth"]

        if thick >= min(top_r, bot_r, max_r):
            QtWidgets.QMessageBox.warning(None, translate_text("エラー", lang), translate_text("肉厚が半径に対して厚すぎます。", lang))
            return

        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("スパイラル壺工場", lang), initial_text=translate_text("ステップ1: 壺本体を生成中...", lang))
            
            doc.openTransaction("CreateSpiralVase")
            try:
                p_bot_out = FreeCAD.Vector(bot_r, 0, 0)
                p_mid_out = FreeCAD.Vector(max_r, 0, h * 0.4)
                p_top_out = FreeCAD.Vector(top_r, 0, h)
                
                curve_out = Part.BSplineCurve()
                curve_out.buildFromPoles([p_bot_out, p_mid_out, p_top_out])
                edge_out = curve_out.toShape()
                
                p_top_in = FreeCAD.Vector(top_r - thick, 0, h)
                p_mid_in = FreeCAD.Vector(max_r - thick, 0, h * 0.4)
                p_bot_in = FreeCAD.Vector(bot_r - thick, 0, thick)
                p_center_in = FreeCAD.Vector(0, 0, thick)
                p_center_bot = FreeCAD.Vector(0, 0, 0)
                
                curve_in = Part.BSplineCurve()
                curve_in.buildFromPoles([p_top_in, p_mid_in, p_bot_in])
                edge_in = curve_in.toShape()
                
                edge_top_lip   = Part.makeLine(p_top_out, p_top_in)
                edge_to_center = Part.makeLine(p_bot_in, p_center_in)
                edge_down_axis = Part.makeLine(p_center_in, p_center_bot)
                edge_bot_line  = Part.makeLine(p_center_bot, p_bot_out)
                
                wire_vase = Part.Wire([edge_out, edge_top_lip, edge_in, edge_to_center, edge_down_axis, edge_bot_line])
                face_vase = Part.Face(wire_vase)
                
                base_vase = face_vase.revolve(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), 360.0)

                bar.update(40, translate_text("ステップ2: 螺旋模様の刃を1本生成中...", lang))
                
                slices = 40
                turns = 0.25 
                rib_profiles = []
                
                for s in range(slices + 1):
                    t = float(s) / slices
                    z = t * h
                    r_base = (1-t)**2 * bot_r + 2*(1-t)*t * max_r + t**2 * top_r
                    a = t * (turns * 2 * math.pi)
                    w = (math.pi / rib_count) * 0.8
                    r_in = r_base - 0.5 
                    r_out = r_base + rib_depth
                    
                    p1 = FreeCAD.Vector(r_in * math.cos(a - w), r_in * math.sin(a - w), z)
                    p2 = FreeCAD.Vector(r_out * math.cos(a), r_out * math.sin(a), z)
                    p3 = FreeCAD.Vector(r_in * math.cos(a + w), r_in * math.sin(a + w), z)
                    
                    rib_profiles.append(Part.makePolygon([p1, p2, p3, p1]))
                
                single_rib = Part.makeLoft(rib_profiles, True, False)

                bar.update(70, translate_text("ステップ3: 模様を円周上に一斉配置中...", lang))
                
                all_parts = [base_vase]
                for i in range(rib_count):
                    angle = (360.0 / rib_count) * i
                    rot = FreeCAD.Rotation(FreeCAD.Vector(0,0,1), angle)
                    rib_copy = single_rib.copy()
                    rib_copy.Placement.Rotation = rot
                    all_parts.append(rib_copy)

                bar.update(90, translate_text("ステップ4: 複合化してデータを出力中...", lang))
                final_shape = Part.makeCompound(all_parts)
                
                bar.update(95, translate_text("完了処理中...", lang))
                
                obj = doc.addObject("Part::Feature", "SpiralVase")
                obj.Shape = final_shape
                obj.ViewObject.ShapeColor = (0.3, 0.8, 0.6)
                obj.ViewObject.DisplayMode = "Shaded"
                
                bar.update(100, translate_text("生成が完了しました！", lang))
                
                doc.commitTransaction()
                doc.recompute()
                if FreeCADGui.activeView():
                    FreeCADGui.activeView().fitAll()

            except Exception as e:
                doc.abortTransaction()
                FreeCAD.Console.PrintError(f"Spiral vase error: {str(e)}\n")
                err_title = "Error" if lang == "English" else "エラー"
                err_msg = f"An error occurred during creation:\n{str(e)}" if lang == "English" else f"生成中にエラーが発生しました:\n{str(e)}"
                QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Ring_Vase', Tool_MakeVase())