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

class PizzaCutterDialog(TranslatedDialog):
    """3Dプリント組立対応ピザカッターの設計ダイアログ"""
    def __init__(self, parent=None):
        super(PizzaCutterDialog, self).__init__(parent)
        self.setWindowTitle("3Dプリント組立対応ピザカッター工場")
        self.resize(380, 300)
        
        layout = QtWidgets.QFormLayout(self)
        
        self.spin_wheel_d = QtWidgets.QDoubleSpinBox()
        self.spin_wheel_d.setRange(30.0, 150.0)
        self.spin_wheel_d.setValue(65.0)
        self.spin_wheel_d.setSuffix(" mm")

        self.spin_handle_l = QtWidgets.QDoubleSpinBox()
        self.spin_handle_l.setRange(50.0, 300.0)
        self.spin_handle_l.setValue(105.0)
        self.spin_handle_l.setSuffix(" mm")

        self.spin_blade_t = QtWidgets.QDoubleSpinBox()
        self.spin_blade_t.setRange(0.8, 4.0)
        self.spin_blade_t.setValue(1.5)
        self.spin_blade_t.setSingleStep(0.1)
        self.spin_blade_t.setSuffix(" mm")

        self.spin_clearance = QtWidgets.QDoubleSpinBox()
        self.spin_clearance.setRange(0.1, 1.0)
        self.spin_clearance.setValue(0.30)
        self.spin_clearance.setSingleStep(0.05)
        self.spin_clearance.setSuffix(" mm")

        self.check_animate = QtWidgets.QCheckBox("生成後にCAD上で回転動作を確認する")
        self.check_animate.setChecked(True)

        layout.addRow("<b>回転刃の直径 (カッター径):</b>", self.spin_wheel_d)
        layout.addRow("<b>持ち手（柄）の長さ:</b>", self.spin_handle_l)
        layout.addRow("<b>刃の厚み:</b>", self.spin_blade_t)
        layout.addRow("<b>ピンと穴の組み立てクリアランス:</b>", self.spin_clearance)
        layout.addRow("<b>ワッシャー厚み (固定):</b>", QtWidgets.QLabel("3.0 mm (固定)"))
        layout.addRow("", self.check_animate)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        return {
            "wheel_d": self.spin_wheel_d.value(),
            "handle_l": self.spin_handle_l.value(),
            "blade_t": self.spin_blade_t.value(),
            "clearance": self.spin_clearance.value(),
            "animate": self.check_animate.isChecked()
        }

class Tool_MakePizzaCutter:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "pizza_cutter.png").replace('\\', '/')
        return {
            'Pixmap': icon_path if os.path.exists(icon_path) else "", 
            'MenuText': "ピザカッターの作成", 
            'ToolTip': "治具と刃の間に厚み3mmのワッシャーを挟み込んだピザカッターを生成します"
        }

    def Activated(self):
        lang = get_language()
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument("PizzaCutterDesign")

        d = PizzaCutterDialog()
        if d.exec_() != QtWidgets.QDialog.Accepted: return
        vals = d.get_values()

        wheel_r = vals["wheel_d"] / 2.0
        handle_l = vals["handle_l"]
        blade_t = vals["blade_t"]
        clearance = vals["clearance"]
        do_animate = vals["animate"]
        
        # ご指示の固定値
        WASHER_THICKNESS = 3.0  # 厚み3mm（固定）

        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("3Dプリントピザカッター工場", lang), initial_text=translate_text("1. 貫通穴付き回転刃を成形中...", lang))
            
            doc.openTransaction("CreatePizzaCutter")
            try:
                pin_r = max(3.0, wheel_r * 0.08) # 軸ピンの半径
                washer_r = pin_r + 4.5           # ワッシャー外径
                
                # ---------------------------------------------------------
                # 1. 回転刃（中央貫通穴: pin_r + clearance）
                # ---------------------------------------------------------
                bar.update(25, translate_text("1. 回転刃と軸穴（ピン穴）を精密カット中...", lang))
                
                blade_disk = Part.makeCylinder(wheel_r, blade_t, FreeCAD.Vector(0, 0, -blade_t/2.0), FreeCAD.Vector(0, 0, 1))
                
                chamfer_depth = 3.0
                c_outer1 = Part.makeCone(wheel_r, wheel_r - chamfer_depth, chamfer_depth, FreeCAD.Vector(0, 0, blade_t/2.0 - chamfer_depth), FreeCAD.Vector(0, 0, 1))
                c_outer2 = Part.makeCone(wheel_r - chamfer_depth, wheel_r, chamfer_depth, FreeCAD.Vector(0, 0, -blade_t/2.0), FreeCAD.Vector(0, 0, 1))
                
                center_cylinder = Part.makeCylinder(wheel_r - chamfer_depth, blade_t, FreeCAD.Vector(0, 0, -blade_t/2.0), FreeCAD.Vector(0, 0, 1))
                blade_shape = center_cylinder.fuse(c_outer1).fuse(c_outer2)

                hole_r = pin_r + clearance
                blade_hole = Part.makeCylinder(hole_r, blade_t * 4.0, FreeCAD.Vector(0, 0, -blade_t * 2.0), FreeCAD.Vector(0, 0, 1))
                blade_shape = blade_shape.cut(blade_hole)

                slot_hole = Part.makeBox(wheel_r * 0.7, blade_t * 0.5, blade_t * 2.0)
                slot_hole.translate(FreeCAD.Vector(-wheel_r * 0.35, -blade_t * 0.25, -blade_t))
                blade_shape = blade_shape.cut(slot_hole)

                # ---------------------------------------------------------
                # 2. 独立したワッシャーパーツ（固定厚み 3.0mm）
                # ---------------------------------------------------------
                bar.update(45, translate_text("2. 治具と刃の間に配置する厚み3mmワッシャーを成形中...", lang))
                
                washer_z_start = blade_t/2.0 + clearance
                washer_solid = Part.makeCylinder(washer_r, WASHER_THICKNESS, FreeCAD.Vector(0, 0, washer_z_start), FreeCAD.Vector(0, 0, 1))
                washer_hole = Part.makeCylinder(hole_r, WASHER_THICKNESS * 4.0, FreeCAD.Vector(0, 0, washer_z_start - WASHER_THICKNESS), FreeCAD.Vector(0, 0, 1))
                washer_shape = washer_solid.cut(washer_hole)

                # ---------------------------------------------------------
                # 3. 本体フレーム（ワッシャー厚3mm分オフセットさせたアーム）
                # ---------------------------------------------------------
                bar.update(65, translate_text("3. ワッシャー分浮かせて固定した本体治具アームを成形中...", lang))
                
                stem_w = max(16.0, washer_r * 2.0)
                stem_t = 3.5
                
                handle_start_y = wheel_r + 8.0
                arm_z_pos = washer_z_start + WASHER_THICKNESS + clearance
                
                # 治具（アーム）
                stem_len = handle_start_y
                stem_box = Part.makeBox(stem_w, stem_len, stem_t)
                stem_box.translate(FreeCAD.Vector(-stem_w/2.0, 0, arm_z_pos))

                arm_cyl = Part.makeCylinder(stem_w/2.0, stem_t, FreeCAD.Vector(0, 0, arm_z_pos), FreeCAD.Vector(0, 0, 1))
                stem_arm = stem_box.fuse(arm_cyl)

                # ピン軸穴の貫通カット
                arm_hole = Part.makeCylinder(hole_r, stem_t * 4.0, FreeCAD.Vector(0, 0, arm_z_pos - stem_t), FreeCAD.Vector(0, 0, 1))
                stem_arm = stem_arm.cut(arm_hole)

                # フィンガーガード
                guard_w = 32.0
                guard_l = 16.0
                
                guard_arc = Part.makeCylinder(35.0, guard_w, FreeCAD.Vector(0, handle_start_y, -35.0 + stem_t/2.0 + arm_z_pos), FreeCAD.Vector(1, 0, 0))
                guard_arc.translate(FreeCAD.Vector(-guard_w/2.0, 0, 0))
                
                guard_inner = Part.makeCylinder(32.0, guard_w, FreeCAD.Vector(0, handle_start_y, -35.0 + stem_t/2.0 + arm_z_pos), FreeCAD.Vector(1, 0, 0))
                guard_inner.translate(FreeCAD.Vector(-guard_w/2.0, 0, 0))
                
                guard_plate = guard_arc.cut(guard_inner)
                
                guard_box = Part.makeBox(guard_w * 2.0, guard_l, 40.0)
                guard_box.translate(FreeCAD.Vector(-guard_w, handle_start_y - guard_l/2.0, -20.0))
                guard_final = guard_plate.common(guard_box)

                # 口金リング
                ferrule_r1 = 8.5
                ferrule_r2 = 10.0
                ferrule_h = 12.0
                ferrule = Part.makeCone(ferrule_r1, ferrule_r2, ferrule_h, FreeCAD.Vector(0, handle_start_y, arm_z_pos + stem_t/2.0), FreeCAD.Vector(0, 1, 0))

                # 木製ハンドル
                grip_start_y = handle_start_y + ferrule_h
                r_start = ferrule_r2
                r_mid = 12.5
                r_end = 9.5
                
                pts_handle = [
                    FreeCAD.Vector(r_start, grip_start_y, 0),
                    FreeCAD.Vector(r_mid, grip_start_y + handle_l * 0.45, 0),
                    FreeCAD.Vector(r_end * 1.1, grip_start_y + handle_l * 0.90, 0),
                    FreeCAD.Vector(0, grip_start_y + handle_l, 0)
                ]
                
                c_handle = Part.BSplineCurve()
                c_handle.buildFromPoles(pts_handle)
                
                edge_start = Part.makeLine(FreeCAD.Vector(0, grip_start_y, 0), FreeCAD.Vector(r_start, grip_start_y, 0))
                axis_line = Part.makeLine(FreeCAD.Vector(0, grip_start_y + handle_l, 0), FreeCAD.Vector(0, grip_start_y, 0))
                
                wire_handle = Part.Wire([edge_start, c_handle.toShape(), axis_line])
                face_handle = Part.Face(wire_handle)
                
                handle_solid = face_handle.revolve(FreeCAD.Vector(0, grip_start_y, 0), FreeCAD.Vector(0, 1, 0), 360.0)
                handle_solid.translate(FreeCAD.Vector(0, 0, arm_z_pos + stem_t/2.0))

                frame_body_solid = stem_arm.fuse(guard_final).fuse(ferrule).fuse(handle_solid)

                # ---------------------------------------------------------
                # 4. 貫通軸ピン（全貫通長さをワッシャー3mmに合わせ拡張）
                # ---------------------------------------------------------
                bar.update(80, translate_text("4. 貫通軸ピンを成形中...", lang))
                
                pin_z_min = -blade_t/2.0 - clearance * 2.0
                pin_z_max = arm_z_pos + stem_t + clearance * 1.0
                pin_shaft_len = pin_z_max - pin_z_min
                
                pin_shaft = Part.makeCylinder(pin_r, pin_shaft_len, FreeCAD.Vector(0, 0, pin_z_min), FreeCAD.Vector(0, 0, 1))
                
                cap_r = pin_r + 2.5
                cap_t = 1.8
                cap_back = Part.makeCylinder(cap_r, cap_t, FreeCAD.Vector(0, 0, pin_z_min - cap_t), FreeCAD.Vector(0, 0, 1))
                cap_front = Part.makeCylinder(cap_r, cap_t, FreeCAD.Vector(0, 0, pin_z_max), FreeCAD.Vector(0, 0, 1))

                pin_solid = pin_shaft.fuse(cap_back).fuse(cap_front)

                # ---------------------------------------------------------
                # 5. 出力
                # ---------------------------------------------------------
                bar.update(95, translate_text("FreeCADへ独立4パーツを出力中...", lang))
                
                # 1. 本体フレーム
                obj_frame = doc.addObject("Part::Feature", "PizzaCutter_BodyFrame")
                obj_frame.Shape = frame_body_solid.removeSplitter()
                obj_frame.ViewObject.ShapeColor = (0.80, 0.65, 0.45)
                obj_frame.ViewObject.DisplayMode = "Shaded"

                # 2. 回転刃
                obj_blade = doc.addObject("Part::Feature", "PizzaCutter_BladeWheel")
                obj_blade.Shape = blade_shape.removeSplitter()
                obj_blade.ViewObject.ShapeColor = (0.90, 0.90, 0.95)
                obj_blade.ViewObject.DisplayMode = "Shaded"
                if hasattr(obj_blade.ViewObject, "Shininess"):
                    obj_blade.ViewObject.Shininess = 0.95

                # 3. 独立ワッシャー (厚み3mm / 赤色カラー)
                obj_washer = doc.addObject("Part::Feature", "PizzaCutter_Washer_3mm")
                obj_washer.Shape = washer_shape.removeSplitter()
                obj_washer.ViewObject.ShapeColor = (0.95, 0.25, 0.15)
                obj_washer.ViewObject.DisplayMode = "Shaded"

                # 4. 保持ピン
                obj_pin = doc.addObject("Part::Feature", "PizzaCutter_RetainingPin")
                obj_pin.Shape = pin_solid.removeSplitter()
                obj_pin.ViewObject.ShapeColor = (0.30, 0.35, 0.40)
                obj_pin.ViewObject.DisplayMode = "Shaded"

                bar.update(100, translate_text("完了しました！", lang))
                
                doc.commitTransaction()
                doc.recompute()
                if FreeCADGui.activeView():
                    FreeCADGui.activeView().fitAll()
                    FreeCADGui.activeView().viewAxometric()

                if do_animate:
                    self.start_wheel_animation(obj_blade)

            except Exception as e:
                doc.abortTransaction()
                FreeCAD.Console.PrintError(f"Pizza Cutter creation error: {str(e)}\n")
                err_title = "Error" if lang == "English" else "エラー"
                err_msg = f"An error occurred during creation:\n{str(e)}" if lang == "English" else f"生成中にエラーが発生しました:\n{str(e)}"
                QtWidgets.QMessageBox.critical(None, err_title, err_msg)

    def start_wheel_animation(self, wheel_obj):
        """刃を回転アニメーション"""
        self.angle = 0
        self.timer = QtCore.QTimer()
        
        def update_spin():
            if not wheel_obj or not wheel_obj.Document:
                self.timer.stop()
                return
            self.angle = (self.angle + 8) % 360
            wheel_obj.Placement.Rotation = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), self.angle)
            FreeCADGui.updateGui()

        self.timer.timeout.connect(update_spin)
        self.timer.start(30)

FreeCADGui.addCommand('Ring_MakePizzaCutter', Tool_MakePizzaCutter())