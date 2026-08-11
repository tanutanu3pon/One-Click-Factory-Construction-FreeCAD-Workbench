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

class LureSpoonDialog(TranslatedDialog):
    """トラウト用スプーンルアーの設計ダイアログ"""
    def __init__(self, parent=None):
        super(LureSpoonDialog, self).__init__(parent)
        self.setWindowTitle("エリアトラウト・スプーンルアー工場")
        self.resize(380, 320)
        
        layout = QtWidgets.QFormLayout(self)
        
        self.combo_type = QtWidgets.QComboBox()
        self.combo_type.addItems([
            "1. ティアドロップ (Teardrop / 定番・ワイドウォブリング)",
            "2. リッジ溝入り (V-Ridge / 輝く反射・強アピール)",
            "3. ウィローリーフ (Willow Leaf / 細身・ハイピッチアクション)"
        ])
        
        self.spin_length = QtWidgets.QDoubleSpinBox()
        self.spin_length.setRange(10.0, 100.0)
        self.spin_length.setValue(25.0)
        self.spin_length.setSuffix(" mm")
        
        self.spin_width = QtWidgets.QDoubleSpinBox()
        self.spin_width.setRange(3.0, 50.0)
        self.spin_width.setValue(10.0)
        self.spin_width.setSuffix(" mm")

        self.spin_thick = QtWidgets.QDoubleSpinBox()
        self.spin_thick.setRange(0.5, 5.0)
        self.spin_thick.setValue(1.2)
        self.spin_thick.setSingleStep(0.1)
        self.spin_thick.setSuffix(" mm")

        self.spin_cup_depth = QtWidgets.QDoubleSpinBox()
        self.spin_cup_depth.setRange(0.5, 15.0)
        self.spin_cup_depth.setValue(2.8)
        self.spin_cup_depth.setSuffix(" mm")

        self.check_holes = QtWidgets.QCheckBox("前後にライン/フック穴（スプリットリング用）を空ける")
        self.check_holes.setChecked(True)

        self.spin_hole_r = QtWidgets.QDoubleSpinBox()
        self.spin_hole_r.setRange(0.3, 3.0)
        self.spin_hole_r.setValue(0.8)
        self.spin_hole_r.setSingleStep(0.1)
        self.spin_hole_r.setSuffix(" mm")

        self.check_holes.toggled.connect(self.spin_hole_r.setEnabled)

        layout.addRow("<b>スプーンのタイプ:</b>", self.combo_type)
        layout.addRow("<b>ルアー全体の長さ (Y方向):</b>", self.spin_length)
        layout.addRow("<b>最大幅 (X方向):</b>", self.spin_width)
        layout.addRow("<b>板厚 (板の厚み):</b>", self.spin_thick)
        layout.addRow("<b>カップの深さ (アクションの強さ):</b>", self.spin_cup_depth)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        layout.addRow(self.check_holes)
        layout.addRow("<b>リング穴の半径:</b>", self.spin_hole_r)
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
            "thick": self.spin_thick.value(),
            "cup_depth": self.spin_cup_depth.value(),
            "has_holes": self.check_holes.isChecked(),
            "hole_r": self.spin_hole_r.value()
        }

class Tool_MakeLureSpoon:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "lure_spoon.png").replace('\\', '/')
        return {
            'Pixmap': icon_path if os.path.exists(icon_path) else "", 
            'MenuText': "ルアー（スプーン）の作成", 
            'ToolTip': "流体力学に基づいたウォブリングアクションを生み出すスプーンルアーを生成します"
        }

    def Activated(self):
        lang = get_language()
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument("LureSpoonDesign")

        d = LureSpoonDialog()
        if d.exec_() != QtWidgets.QDialog.Accepted: return
        vals = d.get_values()

        type_idx = vals["type_idx"]
        L = vals["length"]
        W = vals["width"]
        thick = vals["thick"]
        depth = vals["cup_depth"]
        has_holes = vals["has_holes"]
        hole_r = vals["hole_r"]

        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("スプーンルアー製造工場", lang), initial_text=translate_text("1. 流体力学シルエット（Top View）を計算中...", lang))
            
            doc.openTransaction("CreateLureSpoon")
            try:
                half_w = W / 2.0
                
                # ---------------------------------------------------------
                # 1. 2D平面流線型プロファイル（Top View）
                # ---------------------------------------------------------
                bar.update(25, translate_text("タイプ別の流線形輪郭を計算中...", lang))
                
                if type_idx == 0:  # ティアドロップ (ワイドアクション)
                    pts_r = [
                        FreeCAD.Vector(0, 0, 0),
                        FreeCAD.Vector(half_w * 0.40, L * 0.12, 0),
                        FreeCAD.Vector(half_w * 0.85, L * 0.45, 0),
                        FreeCAD.Vector(half_w, L * 0.70, 0),
                        FreeCAD.Vector(half_w * 0.50, L * 0.90, 0),
                        FreeCAD.Vector(0, L, 0)
                    ]
                elif type_idx == 1:  # リッジ溝入り (V-Ridge / 適切な幅の保持)
                    pts_r = [
                        FreeCAD.Vector(0, 0, 0),
                        FreeCAD.Vector(half_w * 0.50, L * 0.15, 0),
                        FreeCAD.Vector(half_w * 0.90, L * 0.40, 0),
                        FreeCAD.Vector(half_w, L * 0.65, 0),
                        FreeCAD.Vector(half_w * 0.55, L * 0.88, 0),
                        FreeCAD.Vector(0, L, 0)
                    ]
                else:  # ウィローリーフ (細身・ハイピッチ)
                    pts_r = [
                        FreeCAD.Vector(0, 0, 0),
                        FreeCAD.Vector(half_w * 0.60, L * 0.20, 0),
                        FreeCAD.Vector(half_w, L * 0.50, 0),
                        FreeCAD.Vector(half_w * 0.60, L * 0.80, 0),
                        FreeCAD.Vector(0, L, 0)
                    ]

                c_r = Part.BSplineCurve()
                c_r.buildFromPoles(pts_r)
                
                pts_l = [FreeCAD.Vector(-p.x, p.y, 0) for p in reversed(pts_r)]
                c_l = Part.BSplineCurve()
                c_l.buildFromPoles(pts_l)

                wire_outline = Part.Wire([c_r.toShape(), c_l.toShape()])
                face_outline = Part.Face(wire_outline)
                solid_top = face_outline.extrude(FreeCAD.Vector(0, 0, (depth + thick) * 4.0))
                solid_top.translate(FreeCAD.Vector(0, 0, -(depth + thick) * 2.0))

                # ---------------------------------------------------------
                # 2. 側面プロファイル（Side View S字ベント）
                # ---------------------------------------------------------
                bar.update(50, translate_text("2. ウォブリング（暴れ運動）を生み出すS字曲面を計算中...", lang))
                
                t_nose = FreeCAD.Vector(0, 0, thick)
                t_mid1 = FreeCAD.Vector(0, L * 0.30, -depth * 0.6 + thick)
                t_mid2 = FreeCAD.Vector(0, L * 0.65, depth * 0.8 + thick)
                t_tail = FreeCAD.Vector(0, L, depth * 0.4 + thick)
                
                c_side_top = Part.BSplineCurve()
                c_side_top.buildFromPoles([t_nose, t_mid1, t_mid2, t_tail])

                b_tail = FreeCAD.Vector(0, L, depth * 0.4)
                b_mid2 = FreeCAD.Vector(0, L * 0.65, depth * 0.8)
                b_mid1 = FreeCAD.Vector(0, L * 0.30, -depth * 0.6)
                b_nose = FreeCAD.Vector(0, 0, 0)
                
                c_side_bot = Part.BSplineCurve()
                c_side_bot.buildFromPoles([b_tail, b_mid2, b_mid1, b_nose])

                edge_nose = Part.makeLine(b_nose, t_nose)
                edge_tail = Part.makeLine(t_tail, b_tail)

                wire_side = Part.Wire([c_side_top.toShape(), edge_tail, c_side_bot.toShape(), edge_nose])
                face_side = Part.Face(wire_side)

                extrude_w = W * 10.0
                solid_side = face_side.extrude(FreeCAD.Vector(extrude_w, 0, 0))
                solid_side.translate(FreeCAD.Vector(-extrude_w / 2.0, 0, 0))

                # ---------------------------------------------------------
                # 3. 平面と立面の交差（Common）
                # ---------------------------------------------------------
                bar.update(65, translate_text("3. エアロボディを合成抽出中...", lang))
                spoon_body = solid_top.common(solid_side)

                # タイプ2 (リッジ溝) のみ、中央へ安全に浅いV字傾斜溝を入れる
                if type_idx == 1:
                    v_cut_depth = depth * 0.4
                    cut_w = W * 0.35
                    
                    # 削り過ぎない制御ボックス
                    v_box_r = Part.makeBox(cut_w, L * 1.2, (depth + thick) * 2.0)
                    v_box_r.translate(FreeCAD.Vector(cut_w * 0.2, -L * 0.1, -(depth + thick)))
                    v_box_r.Placement.Rotation = FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), 12.0)
                    
                    v_box_l = Part.makeBox(cut_w, L * 1.2, (depth + thick) * 2.0)
                    v_box_l.translate(FreeCAD.Vector(-cut_w * 1.2, -L * 0.1, -(depth + thick)))
                    v_box_l.Placement.Rotation = FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), -12.0)
                    
                    spoon_body = spoon_body.cut(v_box_r).cut(v_box_l)

                # ---------------------------------------------------------
                # 4. 前後のリング穴（十分な幅がある内側へ正確に配置）
                # ---------------------------------------------------------
                if has_holes:
                    bar.update(80, translate_text("4. ライン用・フック用の貫通リング穴を精密加工中...", lang))
                    
                    # 両端の肉厚・幅が十分な位置へ穴のY座標を自動配置（破綻防止）
                    hole_offset = max(hole_r * 2.5 + 1.2, L * 0.08)
                    hole_front_y = hole_offset
                    hole_back_y = L - hole_offset
                    
                    cyl_h = (depth + thick) * 20.0
                    cyl_front = Part.makeCylinder(hole_r, cyl_h, FreeCAD.Vector(0, hole_front_y, -cyl_h / 2.0))
                    cyl_back = Part.makeCylinder(hole_r, cyl_h, FreeCAD.Vector(0, hole_back_y, -cyl_h / 2.0))
                    
                    spoon_body = spoon_body.cut(cyl_front).cut(cyl_back)

                # ---------------------------------------------------------
                # 5. フチの滑らか加工（フィレット処理）
                # ---------------------------------------------------------
                bar.update(90, translate_text("5. 角丸（フィレット）加工を処理中...", lang))
                
                final_shape = spoon_body
                if hole_r > 0:
                    try:
                        fillet_r = min(thick * 0.30, 0.30)
                        valid_edges = [e for e in spoon_body.Edges if e.Length > hole_r * 4.0]
                        if valid_edges:
                            filleted = spoon_body.makeFillet(fillet_r, valid_edges)
                            if not filleted.isNull():
                                final_shape = filleted
                    except Exception:
                        pass

                final_shape = final_shape.removeSplitter()

                bar.update(95, translate_text("FreeCADへモデルを出力中...", lang))
                
                colors = [
                    (0.95, 0.80, 0.10),  # ゴールド (ティアドロップ)
                    (0.90, 0.90, 0.92),  # シルバー (V-リッジ)
                    (0.98, 0.40, 0.10)   # 蛍光オレンジ (ウィローリーフ)
                ]
                
                type_names = ["Teardrop", "VRidge", "WillowLeaf"]
                obj = doc.addObject("Part::Feature", f"LureSpoon_{type_names[type_idx]}")
                obj.Shape = final_shape
                obj.ViewObject.ShapeColor = colors[type_idx]
                obj.ViewObject.DisplayMode = "Shaded"
                if hasattr(obj.ViewObject, "Shininess"):
                    obj.ViewObject.Shininess = 0.95
                
                bar.update(100, translate_text("完了しました！", lang))
                
                doc.commitTransaction()
                doc.recompute()
                if FreeCADGui.activeView():
                    FreeCADGui.activeView().fitAll()
                    FreeCADGui.activeView().viewAxometric()

            except Exception as e:
                doc.abortTransaction()
                FreeCAD.Console.PrintError(f"Lure Spoon creation error: {str(e)}\n")
                err_title = "Error" if lang == "English" else "エラー"
                err_msg = f"An error occurred during creation:\n{str(e)}" if lang == "English" else f"生成中にエラーが発生しました:\n{str(e)}"
                QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Ring_MakeLureSpoon', Tool_MakeLureSpoon())