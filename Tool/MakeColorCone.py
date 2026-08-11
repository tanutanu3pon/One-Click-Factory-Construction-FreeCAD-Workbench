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

class ColorConeDialog(TranslatedDialog):
    def __init__(self, parent=None):
        super(ColorConeDialog, self).__init__(parent)
        self.setWindowTitle("カラーコーン＆バー製造工場")
        self.resize(380, 320)
        
        layout = QtWidgets.QFormLayout(self)
        
        self.combo_mode = QtWidgets.QComboBox()
        self.combo_mode.addItems([
            "カラーコーン 2個 ＋ バー 1本 (設置セット)",
            "カラーコーンのみ (Color Cone Only)",
            "コーンバーのみ (Cone Bar Only)"
        ])
        
        self.spin_cone_h = QtWidgets.QDoubleSpinBox()
        self.spin_cone_h.setRange(200.0, 2000.0)
        self.spin_cone_h.setValue(700.0)
        self.spin_cone_h.setSuffix(" mm")
        
        self.spin_base_w = QtWidgets.QDoubleSpinBox()
        self.spin_base_w.setRange(100.0, 1000.0)
        self.spin_base_w.setValue(380.0)
        self.spin_base_w.setSuffix(" mm")

        self.spin_bar_len = QtWidgets.QDoubleSpinBox()
        self.spin_bar_len.setRange(500.0, 5000.0)
        self.spin_bar_len.setValue(2000.0)
        self.spin_bar_len.setSuffix(" mm")

        self.spin_bar_dia = QtWidgets.QDoubleSpinBox()
        self.spin_bar_dia.setRange(10.0, 100.0)
        self.spin_bar_dia.setValue(34.0)
        self.spin_bar_dia.setSuffix(" mm")

        self.check_tape = QtWidgets.QCheckBox("反射テープ（リフレクター段差）を成形する")
        self.check_tape.setChecked(True)
        
        layout.addRow("<b>生成モード:</b>", self.combo_mode)
        layout.addRow(QtWidgets.QLabel("<hr><h3>【カラーコーン設定】</h3>"))
        layout.addRow("<b>コーンの高さ:</b>", self.spin_cone_h)
        layout.addRow("<b>土台ベース幅:</b>", self.spin_base_w)
        layout.addRow(self.check_tape)
        layout.addRow(QtWidgets.QLabel("<hr><h3>【コーンバー設定】</h3>"))
        layout.addRow("<b>バーの長さ (スパン):</b>", self.spin_bar_len)
        layout.addRow("<b>バーの太さ (直径):</b>", self.spin_bar_dia)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        return {
            "mode": self.combo_mode.currentIndex(),
            "cone_h": self.spin_cone_h.value(),
            "base_w": self.spin_base_w.value(),
            "bar_len": self.spin_bar_len.value(),
            "bar_dia": self.spin_bar_dia.value(),
            "has_tape": self.check_tape.isChecked()
        }

class Tool_MakeColorCone:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "color_cone.png").replace('\\', '/')
        return {
            'Pixmap': icon_path, 
            'MenuText': "カラーコーン＆バーの作成", 
            'ToolTip': "カラーコーンおよびコーンバー（または設置セット）を自動生成します"
        }

    def create_single_cone(self, cone_h, base_w, has_tape):
        base_h = cone_h * 0.045
        wall_t = 3.0
        
        base_box = Part.makeBox(base_w, base_w, base_h)
        base_box.translate(FreeCAD.Vector(-base_w / 2.0, -base_w / 2.0, 0))
        
        vertical_edges = []
        for e in base_box.Edges:
            if abs(e.BoundBox.XMin - e.BoundBox.XMax) < 0.01 and abs(e.BoundBox.YMin - e.BoundBox.YMax) < 0.01:
                vertical_edges.append(e)
        if vertical_edges:
            try:
                base_box = base_box.makeFillet(base_w * 0.08, vertical_edges)
            except Exception:
                pass

        r_bottom = base_w * 0.36
        r_top = r_bottom * 0.15
        cone_height = cone_h - base_h
        
        outer_cone = Part.makeCone(r_bottom, r_top, cone_height, FreeCAD.Vector(0, 0, base_h))
        inner_cone = Part.makeCone(r_bottom - wall_t, max(0.5, r_top - wall_t), cone_height + 2.0, FreeCAD.Vector(0, 0, base_h - 1.0))
        
        cone_body = outer_cone.cut(inner_cone)
        
        if has_tape:
            tape_h = cone_height * 0.22
            tape_z = base_h + cone_height * 0.45
            t_ratio = (tape_z - base_h) / cone_height
            r_tape_bot = r_bottom - (r_bottom - r_top) * t_ratio
            r_tape_top = r_bottom - (r_bottom - r_top) * (t_ratio + (tape_h / cone_height))
            
            tape_ring = Part.makeCone(r_tape_bot + 0.8, r_tape_top + 0.8, tape_h, FreeCAD.Vector(0, 0, tape_z))
            cone_body = cone_body.fuse(tape_ring)

        center_hole = Part.makeCylinder(r_bottom - wall_t, base_h + 2.0, FreeCAD.Vector(0, 0, -1.0))
        base_box = base_box.cut(center_hole)
        
        final_cone = base_box.fuse(cone_body)
        return final_cone.removeSplitter()

    def create_single_bar(self, bar_len, bar_dia):
        bar_r = bar_dia / 2.0
        ring_outer_r = bar_r * 2.5
        ring_inner_r = bar_r * 1.8
        ring_thick = bar_r * 0.8
        
        main_bar = Part.makeCylinder(bar_r, bar_len, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(1, 0, 0))
        
        def make_ring_hook(pos_x):
            outer_c = Part.makeCylinder(ring_outer_r, ring_thick, FreeCAD.Vector(pos_x, 0, -ring_thick/2.0), FreeCAD.Vector(0, 0, 1))
            inner_c = Part.makeCylinder(ring_inner_r, ring_thick + 2.0, FreeCAD.Vector(pos_x, 0, -ring_thick/2.0 - 1.0), FreeCAD.Vector(0, 0, 1))
            return outer_c.cut(inner_c)
            
        ring_left = make_ring_hook(0.0)
        ring_right = make_ring_hook(bar_len)
        
        final_bar = main_bar.fuse(ring_left).fuse(ring_right)
        return final_bar.removeSplitter()

    def Activated(self):
        lang = get_language()
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument("ColorConeDesign")

        d = ColorConeDialog(FreeCADGui.getMainWindow())
        if d.exec_() != QtWidgets.QDialog.Accepted: 
            return
        vals = d.get_values()

        mode = vals["mode"]
        cone_h = vals["cone_h"]
        base_w = vals["base_w"]
        bar_len = vals["bar_len"]
        bar_dia = vals["bar_dia"]
        has_tape = vals["has_tape"]

        doc.openTransaction("CreateColorCone")
        try:
            with Progress.ProgressManager() as bar:
                bar.start(title=translate_text("カラーコーン＆バー製造工場", lang), initial_text=translate_text("モデリング処理を開始中...", lang))
                
                if mode == 0:
                    bar.update(20, translate_text("カラーコーン本体(左/右)を成形中...", lang))
                    cone_shape = self.create_single_cone(cone_h, base_w, has_tape)
                    
                    obj_cone1 = doc.addObject("Part::Feature", "ColorCone_Left")
                    obj_cone1.Shape = cone_shape
                    obj_cone1.ViewObject.ShapeColor = (0.95, 0.25, 0.08)
                    
                    obj_cone2 = doc.addObject("Part::Feature", "ColorCone_Right")
                    obj_cone2.Shape = cone_shape.copy()
                    obj_cone2.Placement.Base = FreeCAD.Vector(bar_len, 0, 0)
                    obj_cone2.ViewObject.ShapeColor = (0.95, 0.25, 0.08)

                    bar.update(60, translate_text("コーンバーを生成し上部にセット中...", lang))
                    bar_shape = self.create_single_bar(bar_len, bar_dia)
                    
                    obj_bar = doc.addObject("Part::Feature", "ConeBar")
                    obj_bar.Shape = bar_shape
                    bar_z_pos = cone_h * 0.82
                    obj_bar.Placement.Base = FreeCAD.Vector(0, 0, bar_z_pos)
                    obj_bar.ViewObject.ShapeColor = (0.95, 0.80, 0.10)

                elif mode == 1:
                    bar.update(50, translate_text("カラーコーンを成形中...", lang))
                    cone_shape = self.create_single_cone(cone_h, base_w, has_tape)
                    
                    obj_cone = doc.addObject("Part::Feature", "ColorCone")
                    obj_cone.Shape = cone_shape
                    obj_cone.ViewObject.ShapeColor = (0.95, 0.25, 0.08)

                else:
                    bar.update(50, translate_text("コーンバーを成形中...", lang))
                    bar_shape = self.create_single_bar(bar_len, bar_dia)
                    
                    obj_bar = doc.addObject("Part::Feature", "ConeBar")
                    obj_bar.Shape = bar_shape
                    obj_bar.ViewObject.ShapeColor = (0.95, 0.80, 0.10)

                bar.update(95, translate_text("FreeCADへ登録中...", lang))
                doc.commitTransaction()
                doc.recompute()
                
                bar.update(100, translate_text("完了しました！", lang))
                if FreeCADGui.activeView():
                    FreeCADGui.activeView().fitAll()

        except Exception as e:
            doc.abortTransaction()
            FreeCAD.Console.PrintError(f"Color Cone creation error: {str(e)}\n")
            err_title = "Error" if lang == "English" else "エラー"
            err_msg = f"An error occurred during creation:\n{str(e)}" if lang == "English" else f"生成中にエラーが発生しました:\n{str(e)}"
            QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Construction_MakeColorCone', Tool_MakeColorCone())