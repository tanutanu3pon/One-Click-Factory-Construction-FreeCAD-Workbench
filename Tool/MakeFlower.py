# -*- coding: utf-8 -*-
import os
import math
import FreeCAD
import FreeCADGui
import Part

from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedDialog, translate_text
from Core.Language import get_language

class FlowerDialog(TranslatedDialog):
    def __init__(self, parent=None):
        super(FlowerDialog, self).__init__(parent)
        self.setWindowTitle("3D花びら・花製造工場")
        self.resize(380, 280)
        
        layout = QtWidgets.QFormLayout(self)
        
        self.combo_mode = QtWidgets.QComboBox()
        self.combo_mode.addItems([
            "花全体 (Full Flower)",
            "花びら1枚のみ (Single Petal)"
        ])
        
        self.combo_type = QtWidgets.QComboBox()
        self.combo_type.addItems([
            "サクラ (Cherry Blossom)",
            "バラ (Rose)",
            "チューリップ (Tulip)",
            "ユリ (Lily)",
            "ヒマワリ (Sunflower)"
        ])
        
        self.spin_size = QtWidgets.QDoubleSpinBox()
        self.spin_size.setRange(5.0, 500.0)
        self.spin_size.setValue(30.0)
        self.spin_size.setSuffix(" mm")
        
        self.spin_thick = QtWidgets.QDoubleSpinBox()
        self.spin_thick.setRange(0.2, 10.0)
        self.spin_thick.setValue(1.0)
        self.spin_thick.setSingleStep(0.1)
        self.spin_thick.setSuffix(" mm")
        
        layout.addRow("<b>出力モード:</b>", self.combo_mode)
        layout.addRow("<b>花の種類:</b>", self.combo_type)
        layout.addRow("<b>サイズ (花びらの長さ/花径):</b>", self.spin_size)
        layout.addRow("<b>花びらの肉厚:</b>", self.spin_thick)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        return {
            "is_full": self.combo_mode.currentIndex() == 0,
            "flower_idx": self.combo_type.currentIndex(),
            "size": self.spin_size.value(),
            "thick": self.spin_thick.value()
        }

class Tool_MakeFlower:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "flower.png").replace('\\', '/')
        return {
            'Pixmap': icon_path, 
            'MenuText': "花びら・花の作成", 
            'ToolTip': "サクラ・バラ・チューリップ等の花びら単体または花全体を生成します"
        }

    def make_section_wire(self, w, c, z, thick, y):
        """B-スプライン補間により断面プロファイルを作成"""
        w = max(w, 0.5)
        thick = max(thick, 0.2)
        
        p0 = FreeCAD.Vector(-w/2.0, y, z)
        p1 = FreeCAD.Vector(0, y, z + c)
        p2 = FreeCAD.Vector(w/2.0, y, z)
        
        p2_b = FreeCAD.Vector(w/2.0, y, z - thick)
        p1_b = FreeCAD.Vector(0, y, z + c - thick)
        p0_b = FreeCAD.Vector(-w/2.0, y, z - thick)
        
        bs_top = Part.BSplineCurve()
        bs_top.interpolate([p0, p1, p2])
        edge_top = bs_top.toShape()
        
        edge_r = Part.makeLine(p2, p2_b)
        
        bs_bot = Part.BSplineCurve()
        bs_bot.interpolate([p2_b, p1_b, p0_b])
        edge_bot = bs_bot.toShape()
        
        edge_l = Part.makeLine(p0_b, p0)
        
        return Part.Wire([edge_top, edge_r, edge_bot, edge_l])

    def create_single_petal(self, flower_idx, L, thick):
        """花びら1枚のソリッド形状を安定ロフト生成"""
        profiles = []
        
        # 1. サクラ
        if flower_idx == 0:
            params = [
                (0.02, L*0.08, L*0.02, 0.00),
                (0.40, L*0.75, L*0.10, L*0.05),
                (0.80, L*0.85, L*0.06, L*0.10),
                (1.00, L*0.70, L*0.02, L*0.12)
            ]
        # 2. バラ
        elif flower_idx == 1:
            params = [
                (0.02, L*0.10, L*0.05, 0.00),
                (0.40, L*0.85, L*0.25, L*0.15),
                (0.80, L*0.95, L*0.15, L*0.25),
                (1.00, L*0.65, -L*0.05, L*0.20)
            ]
        # 3. チューリップ
        elif flower_idx == 2:
            params = [
                (0.02, L*0.15, L*0.05, 0.00),
                (0.40, L*0.80, L*0.40, L*0.10),
                (0.75, L*0.85, L*0.35, L*0.30),
                (1.00, L*0.30, L*0.10, L*0.50)
            ]
        # 4. ユリ
        elif flower_idx == 3:
            params = [
                (0.02, L*0.06, L*0.02, 0.00),
                (0.40, L*0.38, L*0.08, L*0.06),
                (0.75, L*0.32, L*0.04, L*0.02),
                (1.00, L*0.05, -L*0.04, -L*0.20)
            ]
        # 5. ヒマワリ
        else:
            params = [
                (0.02, L*0.08, L*0.02, 0.00),
                (0.50, L*0.30, L*0.05, L*0.03),
                (0.85, L*0.22, L*0.03, L*0.05),
                (1.00, L*0.04, L*0.01, L*0.04)
            ]

        for t, w, c, z in params:
            y = L * t
            wire = self.make_section_wire(w, c, z, thick, y)
            profiles.append(wire)

        petal_solid = Part.makeLoft(profiles, True)

        # サクラのV字カット
        if flower_idx == 0:
            try:
                notch_w = L * 0.20
                notch_h = L * 0.15
                p1 = FreeCAD.Vector(0, L - notch_h, -L * 2.0)
                p2 = FreeCAD.Vector(-notch_w, L + L*0.5, -L * 2.0)
                p3 = FreeCAD.Vector(notch_w, L + L*0.5, -L * 2.0)
                
                cutter_wire = Part.makePolygon([p1, p2, p3, p1])
                cutter_face = Part.Face(cutter_wire)
                cutter_solid = cutter_face.extrude(FreeCAD.Vector(0, 0, L * 4.0))
                petal_solid = petal_solid.cut(cutter_solid)
            except Exception:
                pass

        return petal_solid

    def create_full_flower(self, flower_idx, L, thick):
        """花びらパーツを配列生成しCompoundで結合"""
        base_petal = self.create_single_petal(flower_idx, L, thick)
        parts = []

        # 1. サクラ
        if flower_idx == 0:
            for i in range(5):
                p = base_petal.copy()
                rot_z = FreeCAD.Rotation(FreeCAD.Vector(0,0,1), i * 72.0)
                rot_x = FreeCAD.Rotation(FreeCAD.Vector(1,0,0), 10.0)
                p.Placement.Rotation = rot_z.multiply(rot_x)
                parts.append(p)
            center = Part.makeSphere(L * 0.12)
            parts.append(center)

        # 2. バラ
        elif flower_idx == 1:
            layers = [(3, 0.60, 10.0, 0), (5, 0.82, 25.0, 24), (7, 1.00, 42.0, 12)]
            for count, scale, tilt, offset_ang in layers:
                for i in range(count):
                    p = base_petal.copy()
                    p.scale(scale)
                    rot_z = FreeCAD.Rotation(FreeCAD.Vector(0,0,1), offset_ang + i * (360.0 / count))
                    rot_x = FreeCAD.Rotation(FreeCAD.Vector(1,0,0), tilt)
                    p.Placement.Rotation = rot_z.multiply(rot_x)
                    parts.append(p)

        # 3. チューリップ
        elif flower_idx == 2:
            for i in range(3):
                p_in = base_petal.copy()
                p_in.scale(0.95)
                p_in.translate(FreeCAD.Vector(0, -L*0.05, 0))
                rot_z = FreeCAD.Rotation(FreeCAD.Vector(0,0,1), i * 120.0)
                rot_x = FreeCAD.Rotation(FreeCAD.Vector(1,0,0), -12.0)
                p_in.Placement.Rotation = rot_z.multiply(rot_x)
                parts.append(p_in)
                
            for i in range(3):
                p_out = base_petal.copy()
                p_out.translate(FreeCAD.Vector(0, L*0.02, 0))
                rot_z = FreeCAD.Rotation(FreeCAD.Vector(0,0,1), i * 120.0 + 60.0)
                rot_x = FreeCAD.Rotation(FreeCAD.Vector(1,0,0), -5.0)
                p_out.Placement.Rotation = rot_z.multiply(rot_x)
                parts.append(p_out)

        # 4. ユリ
        elif flower_idx == 3:
            for i in range(3):
                p_in = base_petal.copy()
                r_z = FreeCAD.Rotation(FreeCAD.Vector(0,0,1), i * 120.0)
                r_x = FreeCAD.Rotation(FreeCAD.Vector(1,0,0), 28.0)
                p_in.Placement.Rotation = r_z.multiply(r_x)
                parts.append(p_in)
                
                p_out = base_petal.copy()
                p_out.scale(1.08)
                r_z2 = FreeCAD.Rotation(FreeCAD.Vector(0,0,1), i * 120.0 + 60.0)
                r_x2 = FreeCAD.Rotation(FreeCAD.Vector(1,0,0), 40.0)
                p_out.Placement.Rotation = r_z2.multiply(r_x2)
                parts.append(p_out)

        # 5. ヒマワリ (背面円柱を削除・2重花びら配置)
        else:
            num_petals = 16
            for i in range(num_petals):
                p = base_petal.copy()
                rot_z = FreeCAD.Rotation(FreeCAD.Vector(0,0,1), i * (360.0 / num_petals))
                rot_x = FreeCAD.Rotation(FreeCAD.Vector(1,0,0), 6.0)
                p.Placement.Rotation = rot_z.multiply(rot_x)
                parts.append(p)
                
            for i in range(num_petals):
                p_in = base_petal.copy()
                p_in.scale(0.85)
                rot_z = FreeCAD.Rotation(FreeCAD.Vector(0,0,1), i * (360.0 / num_petals) + (180.0 / num_petals))
                rot_x = FreeCAD.Rotation(FreeCAD.Vector(1,0,0), 12.0)
                p_in.Placement.Rotation = rot_z.multiply(rot_x)
                parts.append(p_in)

        return Part.makeCompound(parts)

    def Activated(self):
        lang = get_language()
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument("FlowerDesign")

        d = FlowerDialog(FreeCADGui.getMainWindow())
        if d.exec_() != QtWidgets.QDialog.Accepted: 
            return
        vals = d.get_values()

        is_full = vals["is_full"]
        flower_idx = vals["flower_idx"]
        size = vals["size"]
        thick = vals["thick"]

        doc.openTransaction("CreateFlower")
        try:
            with Progress.ProgressManager() as bar:
                bar.start(title=translate_text("3D花びら・花製造工場", lang), initial_text=translate_text("花びらの曲面を生成中...", lang))
                
                flower_names = ["Sakura", "Rose", "Tulip", "Lily", "Sunflower"]
                base_name = flower_names[flower_idx]
                
                if is_full:
                    bar.update(50, translate_text("花びらを1枚ずつ組み立て複合化中...", lang))
                    shape = self.create_full_flower(flower_idx, size, thick)
                    obj_name = f"{base_name}_Full"
                else:
                    bar.update(50, translate_text("花びら単体を生成中...", lang))
                    shape = self.create_single_petal(flower_idx, size, thick)
                    obj_name = f"{base_name}_Petal"

                bar.update(85, translate_text("FreeCADへ登録中...", lang))
                obj = doc.addObject("Part::Feature", obj_name)
                obj.Shape = shape
                
                colors = [
                    (1.00, 0.82, 0.88),  # サクラピンク
                    (0.90, 0.15, 0.25),  # ローズレッド
                    (0.95, 0.35, 0.20),  # チューリップオレンジ
                    (0.95, 0.95, 0.90),  # ユリホワイト
                    (0.98, 0.80, 0.10)   # ヒマワルイエロー
                ]
                obj.ViewObject.ShapeColor = colors[flower_idx]
                obj.ViewObject.DisplayMode = "Flat Lines"
                
                doc.commitTransaction()
                doc.recompute()
                
                bar.update(100, translate_text("完了しました！", lang))
                if FreeCADGui.activeView():
                    FreeCADGui.activeView().fitAll()

        except Exception as e:
            doc.abortTransaction()
            FreeCAD.Console.PrintError(f"Flower creation error: {str(e)}\n")
            err_title = "Error" if lang == "English" else "エラー"
            err_msg = f"An error occurred during creation:\n{str(e)}" if lang == "English" else f"生成中にエラーが発生しました:\n{str(e)}"
            QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Ring_MakeFlower', Tool_MakeFlower())