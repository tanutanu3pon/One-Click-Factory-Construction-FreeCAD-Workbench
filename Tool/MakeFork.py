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

class ForkHeadDialog(TranslatedDialog):
    """【ステップ1】フォーク先端（ヘッド・歯）の設計ダイアログ"""
    def __init__(self, parent=None):
        super(ForkHeadDialog, self).__init__(parent)
        self.setWindowTitle("フォーク工場：【ステップ1】先端（ヘッド）の形状")
        self.resize(380, 260)
        
        layout = QtWidgets.QFormLayout(self)
        
        self.spin_width = QtWidgets.QDoubleSpinBox()
        self.spin_width.setRange(10.0, 200.0)
        self.spin_width.setValue(26.0)
        self.spin_width.setSuffix(" mm")
        
        self.spin_length = QtWidgets.QDoubleSpinBox()
        self.spin_length.setRange(10.0, 300.0)
        self.spin_length.setValue(55.0)
        self.spin_length.setSuffix(" mm")

        self.spin_thick = QtWidgets.QDoubleSpinBox()
        self.spin_thick.setRange(0.8, 10.0)
        self.spin_thick.setValue(2.2)
        self.spin_thick.setSuffix(" mm")

        self.spin_tines = QtWidgets.QSpinBox()
        self.spin_tines.setRange(2, 6)
        self.spin_tines.setValue(4)
        self.spin_tines.setSuffix(" 本")

        self.spin_tine_depth = QtWidgets.QDoubleSpinBox()
        self.spin_tine_depth.setRange(5.0, 200.0)
        self.spin_tine_depth.setValue(35.0)
        self.spin_tine_depth.setSuffix(" mm")

        layout.addRow("<b>ヘッド最大幅 (X方向):</b>", self.spin_width)
        layout.addRow("<b>ヘッド全体の長さ (Y方向):</b>", self.spin_length)
        layout.addRow("<b>地金の厚み (Z方向):</b>", self.spin_thick)
        layout.addRow("<b>歯（フォークの刃）の本数:</b>", self.spin_tines)
        layout.addRow("<b>スリット（切り込み）の深さ:</b>", self.spin_tine_depth)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        return {
            "width": self.spin_width.value(),
            "length": self.spin_length.value(),
            "thick": self.spin_thick.value(),
            "tines": self.spin_tines.value(),
            "tine_depth": self.spin_tine_depth.value()
        }

class ForkHandleDialog(TranslatedDialog):
    """【ステップ2】柄（ハンドル）と仕上げ設計ダイアログ"""
    def __init__(self, parent=None):
        super(ForkHandleDialog, self).__init__(parent)
        self.setWindowTitle("フォーク工場：【ステップ2】柄と仕上げ")
        self.resize(380, 220)
        
        layout = QtWidgets.QFormLayout(self)
        
        self.spin_h_length = QtWidgets.QDoubleSpinBox()
        self.spin_h_length.setRange(20.0, 1000.0)
        self.spin_h_length.setValue(125.0)
        self.spin_h_length.setSuffix(" mm")
        
        self.spin_h_width = QtWidgets.QDoubleSpinBox()
        self.spin_h_width.setRange(2.0, 50.0)
        self.spin_h_width.setValue(10.0)
        self.spin_h_width.setSuffix(" mm")
        
        self.spin_h_thick = QtWidgets.QDoubleSpinBox()
        self.spin_h_thick.setRange(1.0, 30.0)
        self.spin_h_thick.setValue(3.2)
        self.spin_h_thick.setSuffix(" mm")
        
        self.spin_curve = QtWidgets.QDoubleSpinBox()
        self.spin_curve.setRange(0.0, 50.0)
        self.spin_curve.setValue(12.0)
        self.spin_curve.setSuffix(" mm")

        self.spin_fillet = QtWidgets.QDoubleSpinBox()
        self.spin_fillet.setRange(0.0, 3.0)
        self.spin_fillet.setValue(0.5)
        self.spin_fillet.setSingleStep(0.1)
        self.spin_fillet.setSuffix(" mm")

        layout.addRow("<b>柄の長さ:</b>", self.spin_h_length)
        layout.addRow("柄の最大幅（手元）:", self.spin_h_width)
        layout.addRow("柄の厚み:", self.spin_h_thick)
        layout.addRow("<b>すくい部（ヘッド）の湾曲高さ:</b>", self.spin_curve)
        layout.addRow("<b>【仕上げ】外周の丸み (フィレットR):</b>", self.spin_fillet)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        return {
            "h_length": self.spin_h_length.value(),
            "h_width": self.spin_h_width.value(),
            "h_thick": self.spin_h_thick.value(),
            "curve_h": self.spin_curve.value(),
            "fillet": self.spin_fillet.value()
        }

class Tool_MakeFork:
    def GetResources(self):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "fork.png").replace('\\', '/')
        return {
            'Pixmap': icon_path if os.path.exists(icon_path) else "", 
            'MenuText': "フォークの作成", 
            'ToolTip': "歯の先端を徐々に補足し、首元を綺麗な曲線で繋いだ本格フォークを生成します"
        }

    def Activated(self):
        lang = get_language()
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument("ForkDesign")

        d_head = ForkHeadDialog()
        if d_head.exec_() != QtWidgets.QDialog.Accepted: return
        v_head = d_head.get_values()
        
        d_handle = ForkHandleDialog()
        if d_handle.exec_() != QtWidgets.QDialog.Accepted: return
        v_handle = d_handle.get_values()

        w_max = v_head["width"]
        l_head = v_head["length"]
        t_head = v_head["thick"]
        tines = v_head["tines"]
        l_tine = v_head["tine_depth"]
        
        l_handle = v_handle["h_length"]
        w_handle = v_handle["h_width"]
        t_handle = v_handle["h_thick"]
        c_h = v_handle["curve_h"]
        fillet_r = v_handle["fillet"]

        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("フォーク製造ライン", lang), initial_text=translate_text("1. 曲面輪郭（Top View）を計算中...", lang))
            
            doc.openTransaction("CreateFork")
            try:
                half_w_head = w_max / 2.0
                half_w_neck = (w_handle * 0.65) / 2.0
                half_w_tail = w_handle / 2.0
                
                # ---------------------------------------------------------
                # 1. 平面曲線プロファイル（BSplineによるなめらかなくびれ曲線）
                # ---------------------------------------------------------
                bar.update(25, translate_text("柄とヘッドを綺麗な滑らか曲線で接続中...", lang))
                
                # 右半分の滑らかな曲線（柄の手元 -> 首元 -> ヘッド最大幅 -> 先端）
                pts_r = [
                    FreeCAD.Vector(half_w_tail * 0.9, -l_handle, 0),
                    FreeCAD.Vector(half_w_tail, -l_handle * 0.8, 0),
                    FreeCAD.Vector(half_w_neck, -l_handle * 0.15, 0),
                    FreeCAD.Vector(half_w_neck, 0, 0), # ネック（首元）
                    FreeCAD.Vector(half_w_head * 0.85, l_head * 0.25, 0),
                    FreeCAD.Vector(half_w_head, l_head * 0.55, 0),
                    FreeCAD.Vector(half_w_head * 0.82, l_head, 0)
                ]
                c_right = Part.BSplineCurve()
                c_right.buildFromPoles(pts_r)

                # 先端の揃えライン（Y=l_head）
                edge_tip = Part.makeLine(FreeCAD.Vector(half_w_head * 0.82, l_head, 0), FreeCAD.Vector(-half_w_head * 0.82, l_head, 0))

                # 左半分の滑らかな曲線
                pts_l = [
                    FreeCAD.Vector(-half_w_head * 0.82, l_head, 0),
                    FreeCAD.Vector(-half_w_head, l_head * 0.55, 0),
                    FreeCAD.Vector(-half_w_head * 0.85, l_head * 0.25, 0),
                    FreeCAD.Vector(-half_w_neck, 0, 0),
                    FreeCAD.Vector(-half_w_neck, -l_handle * 0.15, 0),
                    FreeCAD.Vector(-half_w_tail, -l_handle * 0.8, 0),
                    FreeCAD.Vector(-half_w_tail * 0.9, -l_handle, 0)
                ]
                c_left = Part.BSplineCurve()
                c_left.buildFromPoles(pts_l)

                edge_tail = Part.makeLine(FreeCAD.Vector(-half_w_tail * 0.9, -l_handle, 0), FreeCAD.Vector(half_w_tail * 0.9, -l_handle, 0))

                wire_top = Part.Wire([c_right.toShape(), edge_tip, c_left.toShape(), edge_tail])
                face_top = Part.Face(wire_top)
                
                solid_top = face_top.extrude(FreeCAD.Vector(0, 0, (c_h + t_head + t_handle) * 2.0))
                solid_top.translate(FreeCAD.Vector(0, 0, -(c_h + t_head + t_handle)))

                # ---------------------------------------------------------
                # 2. 側面プロファイル（Side View - S字＋すくい部）
                # ---------------------------------------------------------
                bar.update(45, translate_text("2. 側面シルエット（Side View）を作成中...", lang))
                
                t_head_tip = FreeCAD.Vector(0, l_head, c_h + t_head)
                t_head_mid = FreeCAD.Vector(0, l_head * 0.3, c_h * 0.2 + t_head)
                t_neck = FreeCAD.Vector(0, 0, t_head)
                t_handle_mid = FreeCAD.Vector(0, -l_handle * 0.4, l_handle * 0.08)
                t_handle_tail = FreeCAD.Vector(0, -l_handle, -c_h * 0.15 + t_handle)
                
                c_side_top = Part.BSplineCurve()
                c_side_top.buildFromPoles([t_head_tip, t_head_mid, t_neck, t_handle_mid, t_handle_tail])

                b_handle_tail = FreeCAD.Vector(0, -l_handle, -c_h * 0.15)
                b_handle_mid = FreeCAD.Vector(0, -l_handle * 0.4, l_handle * 0.08 - t_handle)
                b_neck = FreeCAD.Vector(0, 0, 0)
                b_head_mid = FreeCAD.Vector(0, l_head * 0.3, c_h * 0.2)
                b_head_tip = FreeCAD.Vector(0, l_head, c_h)
                
                c_side_bot = Part.BSplineCurve()
                c_side_bot.buildFromPoles([b_handle_tail, b_handle_mid, b_neck, b_head_mid, b_head_tip])

                edge_side_head = Part.makeLine(b_head_tip, t_head_tip)
                edge_side_tail = Part.makeLine(t_handle_tail, b_handle_tail)

                wire_side = Part.Wire([c_side_top.toShape(), edge_side_tail, c_side_bot.toShape(), edge_side_head])
                face_side = Part.Face(wire_side)

                extrude_w = w_max * 10.0
                solid_side = face_side.extrude(FreeCAD.Vector(extrude_w, 0, 0))
                solid_side.translate(FreeCAD.Vector(-extrude_w / 2.0, 0, 0))

                # ---------------------------------------------------------
                # 3. 平面と立面の交差（Common）
                # ---------------------------------------------------------
                bar.update(65, translate_text("3. 流線型本体を抽出中...", lang))
                fork_base_solid = solid_top.common(solid_side)

                # ---------------------------------------------------------
                # 4. 歯（フォーク刃）の先細り（テーパー）スリットカット
                # ---------------------------------------------------------
                bar.update(80, translate_text("4. 歯の先端を徐々に細く（テーパー）スリット加工中...", lang))
                
                total_parts = tines * 1.2 + (tines - 1) * 0.8
                unit_w = w_max / total_parts
                slot_w_root = unit_w * 0.8         # 根元のスリット幅
                slot_w_tip = slot_w_root * 1.40    # 先端に向かって広げる（＝歯が細くなる）
                
                cutters = []
                for i in range(tines - 1):
                    curr_x_root = -half_w_head + (i + 1) * (unit_w * 1.2) + (i + 0.5) * slot_w_root
                    
                    # 先端側でスリット幅を広げるV字テーパーカッター
                    p_r_bot = FreeCAD.Vector(curr_x_root - slot_w_root/2.0, l_head - l_tine, 0)
                    p_r_top = FreeCAD.Vector(curr_x_root - slot_w_tip/2.0, l_head + 10.0, 0)
                    p_l_top = FreeCAD.Vector(curr_x_root + slot_w_tip/2.0, l_head + 10.0, 0)
                    p_l_bot = FreeCAD.Vector(curr_x_root + slot_w_root/2.0, l_head - l_tine, 0)
                    
                    wire_cutter = Part.makePolygon([p_r_bot, p_r_top, p_l_top, p_l_bot, p_r_bot])
                    face_cutter = Part.Face(wire_cutter)
                    c_box = face_cutter.extrude(FreeCAD.Vector(0, 0, (c_h + t_head) * 10.0))
                    c_box.translate(FreeCAD.Vector(0, 0, -(c_h + t_head) * 5.0))
                    
                    # スリット奥の丸み
                    c_cyl = Part.makeCylinder(slot_w_root / 2.0, (c_h + t_head) * 10.0, FreeCAD.Vector(curr_x_root, l_head - l_tine, -(c_h + t_head) * 5.0))
                    cutters.append(c_box.fuse(c_cyl))

                if cutters:
                    cutter_comp = Part.makeCompound(cutters)
                    fork_tined = fork_base_solid.cut(cutter_comp)
                else:
                    fork_tined = fork_base_solid

                # ---------------------------------------------------------
                # 5. エッジの角丸加工（フィレット処理）
                # ---------------------------------------------------------
                bar.update(90, translate_text("5. 全外周にフィレット（丸み）を適用中...", lang))
                
                final_shape = fork_tined
                if fillet_r > 0.05:
                    try:
                        valid_edges = [e for e in fork_tined.Edges if e.Length > fillet_r * 2.1]
                        if valid_edges:
                            filleted = fork_tined.makeFillet(fillet_r, valid_edges)
                            if not filleted.isNull():
                                final_shape = filleted
                    except Exception as e:
                        FreeCAD.Console.PrintWarning(f"Fillet skipped: {str(e)}\n")

                final_shape = final_shape.removeSplitter()

                bar.update(95, translate_text("FreeCADへモデルを出力中...", lang))
                
                obj = doc.addObject("Part::Feature", "Fork_Master_Model")
                obj.Shape = final_shape
                obj.ViewObject.ShapeColor = (0.85, 0.85, 0.88)
                obj.ViewObject.DisplayMode = "Shaded"
                if hasattr(obj.ViewObject, "Shininess"):
                    obj.ViewObject.Shininess = 0.85
                
                bar.update(100, translate_text("完了しました！", lang))
                
                doc.commitTransaction()
                doc.recompute()
                if FreeCADGui.activeView():
                    FreeCADGui.activeView().fitAll()
                    FreeCADGui.activeView().viewAxometric()

            except Exception as e:
                doc.abortTransaction()
                FreeCAD.Console.PrintError(f"Fork creation error: {str(e)}\n")
                err_title = "Error" if lang == "English" else "エラー"
                err_msg = f"An error occurred during creation:\n{str(e)}" if lang == "English" else f"生成中にエラーが発生しました:\n{str(e)}"
                QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Ring_MakeFork', Tool_MakeFork())