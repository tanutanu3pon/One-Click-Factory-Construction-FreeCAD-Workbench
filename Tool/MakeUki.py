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

class UkiDialog(TranslatedDialog):
    """釣り用ウキ（浮き）の設計ダイアログ"""
    def __init__(self, parent=None):
        super(UkiDialog, self).__init__(parent)
        self.setWindowTitle("釣りウキ製造工場")
        self.resize(380, 360)
        
        layout = QtWidgets.QFormLayout(self)
        
        self.combo_type = QtWidgets.QComboBox()
        self.combo_type.addItems([
            "1. どんぐりウキ (Bullet / フカセ・遠投用)",
            "2. 棒ウキ (Slim Stick / 川・ヘラブナ高感度用)",
            "3. 玉ウキ (Ball / 堤防・小物用)",
            "4. 立ちウキ・足カン付き (Standing / 太根元・高耐久)"
        ])
        
        self.spin_length = QtWidgets.QDoubleSpinBox()
        self.spin_length.setRange(10.0, 300.0)
        self.spin_length.setValue(55.0)
        self.spin_length.setSuffix(" mm")
        
        self.spin_width = QtWidgets.QDoubleSpinBox()
        self.spin_width.setRange(5.0, 100.0)
        self.spin_width.setValue(22.0)
        self.spin_width.setSuffix(" mm")

        self.spin_hole_r = QtWidgets.QDoubleSpinBox()
        self.spin_hole_r.setRange(0.3, 5.0)
        self.spin_hole_r.setValue(1.0)
        self.spin_hole_r.setSingleStep(0.1)
        self.spin_hole_r.setSuffix(" mm")

        self.check_hollow = QtWidgets.QCheckBox("内部を中空（エア空間）にする")
        self.check_hollow.setChecked(True)

        self.spin_wall = QtWidgets.QDoubleSpinBox()
        self.spin_wall.setRange(0.8, 10.0)
        self.spin_wall.setValue(1.8)
        self.spin_wall.setSingleStep(0.2)
        self.spin_wall.setSuffix(" mm")

        self.check_hollow.toggled.connect(self.spin_wall.setEnabled)

        layout.addRow("<b>ウキのタイプ:</b>", self.combo_type)
        layout.addRow("<b>ウキ全体の長さ (Z方向):</b>", self.spin_length)
        layout.addRow("<b>最大幅/直径 (外径):</b>", self.spin_width)
        layout.addRow("<b>糸通し穴/足カン穴の半径:</b>", self.spin_hole_r)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        layout.addRow(self.check_hollow)
        layout.addRow("<b>壁の厚み (肉厚):</b>", self.spin_wall)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        return {
            "type_idx": self.combo_type.currentIndex(),
            "length": self.spin_length.value(),
            "width": self.spin_width.value(),
            "hole_r": self.spin_hole_r.value(),
            "is_hollow": self.check_hollow.isChecked(),
            "wall_t": self.spin_wall.value()
        }

class Tool_MakeUki:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "uki.png").replace('\\', '/')
        return {
            'Pixmap': icon_path if os.path.exists(icon_path) else "", 
            'MenuText': "ウキ（浮き）の作成", 
            'ToolTip': "立ちウキ・どんぐりウキ・棒ウキ・玉ウキの4種類を自動生成します（中空エラー防止版）"
        }

    def Activated(self):
        lang = get_language()
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument("UkiDesign")

        d = UkiDialog()
        if d.exec_() != QtWidgets.QDialog.Accepted: 
            return
        vals = d.get_values()

        type_idx = vals["type_idx"]
        L = vals["length"]
        W = vals["width"]
        hole_r = vals["hole_r"]
        is_hollow = vals["is_hollow"]
        wall_t = vals["wall_t"]

        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("釣りウキ製造工場", lang), initial_text=translate_text("1. 断面プロファイルを計算中...", lang))
            
            doc.openTransaction("CreateUki")
            try:
                r_max = W / 2.0
                
                # ---------------------------------------------------------
                # 1. ウキタイプ別の回転体制御点群（Poles）の設定
                # ---------------------------------------------------------
                bar.update(30, translate_text("タイプ別の流線型浮力ボディを構築中...", lang))
                
                # [1] どんぐりウキ
                if type_idx == 0:
                    pts = [
                        FreeCAD.Vector(0, 0, 0),
                        FreeCAD.Vector(r_max * 0.4, 0, L * 0.15),
                        FreeCAD.Vector(r_max, 0, L * 0.65),
                        FreeCAD.Vector(r_max * 0.85, 0, L * 0.88),
                        FreeCAD.Vector(r_max * 0.3, 0, L * 0.98),
                        FreeCAD.Vector(0, 0, L)
                    ]
                # [2] 棒ウキ
                elif type_idx == 1:
                    r_stem = max(1.2, r_max * 0.22)
                    pts = [
                        FreeCAD.Vector(0, 0, 0),
                        FreeCAD.Vector(r_stem, 0, L * 0.02),
                        FreeCAD.Vector(r_stem, 0, L * 0.25),
                        FreeCAD.Vector(r_max, 0, L * 0.45),
                        FreeCAD.Vector(r_max * 0.8, 0, L * 0.60),
                        FreeCAD.Vector(r_stem, 0, L * 0.70),
                        FreeCAD.Vector(r_stem, 0, L * 0.98),
                        FreeCAD.Vector(0, 0, L)
                    ]
                # [3] 玉ウキ
                elif type_idx == 2:
                    pts = [
                        FreeCAD.Vector(0, 0, 0),
                        FreeCAD.Vector(r_max * 0.5, 0, L * 0.10),
                        FreeCAD.Vector(r_max, 0, L * 0.50),
                        FreeCAD.Vector(r_max * 0.5, 0, L * 0.90),
                        FreeCAD.Vector(0, 0, L)
                    ]
                # [4] 立ちウキ (根元を太く補強 + ドームトップ)
                else:
                    r_top = max(1.5, r_max * 0.28)
                    r_bottom_thick = max(r_max * 0.45, 3.5) # 折れ防止のため根元を太く設定
                    pts = [
                        FreeCAD.Vector(0, 0, 0),
                        FreeCAD.Vector(r_bottom_thick, 0, L * 0.08),
                        FreeCAD.Vector(r_max * 0.95, 0, L * 0.28),
                        FreeCAD.Vector(r_max, 0, L * 0.42),
                        FreeCAD.Vector(r_max * 0.70, 0, L * 0.58),
                        FreeCAD.Vector(r_top, 0, L * 0.68),
                        FreeCAD.Vector(r_top, 0, L * 0.96),
                        FreeCAD.Vector(0, 0, L)
                    ]

                curve_body = Part.BSplineCurve()
                curve_body.buildFromPoles(pts)
                
                axis_line = Part.makeLine(FreeCAD.Vector(0, 0, L), FreeCAD.Vector(0, 0, 0))
                wire_outer = Part.Wire([curve_body.toShape(), axis_line])
                face_outer = Part.Face(wire_outer)

                # ---------------------------------------------------------
                # 2. 安全な2Dオフセット方式による完全エラーフリー中空化
                # ---------------------------------------------------------
                if is_hollow and wall_t < r_max * 0.7:
                    bar.update(55, translate_text("2. 安全な平面オフセット減算により中空化中...", lang))
                    
                    try:
                        # 2D面自体を内側へ縮小オフセット処理
                        face_inner_offset = face_outer.makeOffset2D(-wall_t)
                        if not face_inner_offset.isNull() and face_inner_offset.Faces:
                            solid_outer = face_outer.revolve(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), 360.0)
                            solid_inner = face_inner_offset.revolve(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), 360.0)
                            uki_body = solid_outer.cut(solid_inner)
                        else:
                            uki_body = face_outer.revolve(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), 360.0)
                    except Exception:
                        # オフセットが万が一失敗した場合はソリッドとして生成
                        uki_body = face_outer.revolve(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), 360.0)
                else:
                    uki_body = face_outer.revolve(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), 360.0)

                # ---------------------------------------------------------
                # 3. 立ちウキ用の足カン部（太い根元への接合）と糸通し穴
                # ---------------------------------------------------------
                if type_idx == 3:
                    bar.update(75, translate_text("3. 補強された根元へ足カン（スイベル部）を結合中...", lang))
                    
                    tab_w = max(5.0, W * 0.40)
                    tab_h = max(6.0, L * 0.12)
                    tab_thick = max(3.0, wall_t * 1.5)
                    
                    # 根元にしっかりめり込ませて結合
                    tab_box = Part.makeBox(tab_w, tab_thick, tab_h + 2.0)
                    tab_box.translate(FreeCAD.Vector(-tab_w / 2.0, -tab_thick / 2.0, -tab_h))
                    
                    if hole_r > 0.1:
                        tab_hole = Part.makeCylinder(hole_r, tab_thick * 4.0, FreeCAD.Vector(0, -tab_thick * 2.0, -tab_h * 0.55), FreeCAD.Vector(0, 1, 0))
                        tab_box = tab_box.cut(tab_hole)
                        
                    uki_body = uki_body.fuse(tab_box)

                # タイプ0, 1, 2 用のセンター貫通糸通し穴
                elif hole_r > 0.1:
                    bar.update(75, translate_text("3. センター糸通し穴を貫通加工中...", lang))
                    hole_cyl = Part.makeCylinder(hole_r, L * 2.0, FreeCAD.Vector(0, 0, -L * 0.5))
                    uki_body = uki_body.cut(hole_cyl)

                # ---------------------------------------------------------
                # 4. 最適化と仕上げ
                # ---------------------------------------------------------
                bar.update(90, translate_text("4. 表面を綺麗に最適化中...", lang))
                final_shape = uki_body.removeSplitter()

                type_names = ["Bullet", "Stick", "Ball", "Standing"]
                obj = doc.addObject("Part::Feature", f"Uki_{type_names[type_idx]}")
                obj.Shape = final_shape
                
                if type_idx == 3:
                    obj.ViewObject.ShapeColor = (0.35, 0.38, 0.40)
                else:
                    obj.ViewObject.ShapeColor = (1.0, 0.25, 0.05)
                    
                obj.ViewObject.DisplayMode = "Shaded"
                if hasattr(obj.ViewObject, "Shininess"):
                    obj.ViewObject.Shininess = 0.90
                
                bar.update(100, translate_text("完了しました！", lang))
                
                doc.commitTransaction()
                doc.recompute()
                if FreeCADGui.activeView():
                    FreeCADGui.activeView().fitAll()
                    FreeCADGui.activeView().viewAxometric()

            except Exception as e:
                doc.abortTransaction()
                FreeCAD.Console.PrintError(f"Uki creation error: {str(e)}\n")
                err_title = "Error" if lang == "English" else "エラー"
                err_msg = f"An error occurred during creation:\n{str(e)}" if lang == "English" else f"生成中にエラーが発生しました:\n{str(e)}"
                QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Ring_MakeUki', Tool_MakeUki())