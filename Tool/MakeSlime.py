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

class SlimeDialog(TranslatedDialog):
    """3Dスライム製造工場の設計ダイアログ"""
    def __init__(self, parent=None):
        super(SlimeDialog, self).__init__(parent)
        self.setWindowTitle("3Dスライム製造工場")
        self.resize(360, 260)
        
        layout = QtWidgets.QFormLayout(self)
        
        self.spin_height = QtWidgets.QDoubleSpinBox()
        self.spin_height.setRange(10.0, 300.0)
        self.spin_height.setValue(35.0)
        self.spin_height.setSuffix(" mm")
        
        self.spin_width = QtWidgets.QDoubleSpinBox()
        self.spin_width.setRange(10.0, 300.0)
        self.spin_width.setValue(40.0)
        self.spin_width.setSuffix(" mm")

        self.check_face = QtWidgets.QCheckBox("目と口（顔パーツ）を配置する")
        self.check_face.setChecked(True)

        self.combo_color = QtWidgets.QComboBox()
        self.combo_color.addItems([
            "スライムブルー (Standard Blue)",
            "メタルシルバー (Metal)",
            "ライムグリーン (Lime Green)",
            "チェリーレッド (Cherry Red)",
            "キングイエロー (Gold Yellow)"
        ])

        layout.addRow("<b>全体の高さ (Z方向):</b>", self.spin_height)
        layout.addRow("<b>お腹の最大幅 (外径):</b>", self.spin_width)
        layout.addRow("", self.check_face)
        layout.addRow("<b>スライムのカラー:</b>", self.combo_color)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        return {
            "height": self.spin_height.value(),
            "width": self.spin_width.value(),
            "has_face": self.check_face.isChecked(),
            "color_idx": self.combo_color.currentIndex()
        }

class Tool_MakeSlime:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "slime.png").replace('\\', '/')
        return {
            'Pixmap': icon_path if os.path.exists(icon_path) else "", 
            'MenuText': "スライムの作成", 
            'ToolTip': "目と口が正しく分離した綺麗なスライムを生成します"
        }

    def Activated(self):
        lang = get_language()
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument("SlimeDesign")

        d = SlimeDialog()
        if d.exec_() != QtWidgets.QDialog.Accepted: return
        vals = d.get_values()

        H = vals["height"]
        W = vals["width"]
        has_face = vals["has_face"]
        color_idx = vals["color_idx"]

        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("3Dスライム製造工場", lang), initial_text=translate_text("1. スライムのシルエット曲線を計算中...", lang))
            
            doc.openTransaction("CreateSlime")
            try:
                r_max = W / 2.0
                
                # ---------------------------------------------------------
                # 1. スライムボディ断面プロフィール（BSpline）
                # ---------------------------------------------------------
                bar.update(25, translate_text("プルッとしたフォルムを計算中...", lang))
                
                pts = [
                    FreeCAD.Vector(0, 0, 0),
                    FreeCAD.Vector(r_max * 0.70, 0, H * 0.02),
                    FreeCAD.Vector(r_max, 0, H * 0.28),
                    FreeCAD.Vector(r_max * 0.85, 0, H * 0.55),
                    FreeCAD.Vector(r_max * 0.40, 0, H * 0.78),
                    FreeCAD.Vector(r_max * 0.22, 0, H * 0.90),
                    FreeCAD.Vector(0, 0, H)
                ]

                curve_body = Part.BSplineCurve()
                curve_body.buildFromPoles(pts)
                
                axis_line = Part.makeLine(FreeCAD.Vector(0, 0, H), FreeCAD.Vector(0, 0, 0))
                wire_profile = Part.Wire([curve_body.toShape(), axis_line])
                face_profile = Part.Face(wire_profile)

                bar.update(50, translate_text("回転体（Revolve）によりソリッドボディを生成中...", lang))
                slime_body = face_profile.revolve(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), 360.0)

                # ---------------------------------------------------------
                # 2. 顔パーツ（目と口の位置関係を最適調整）
                # ---------------------------------------------------------
                final_shape = slime_body

                if has_face:
                    bar.update(75, translate_text("2. 目と口パーツを独立させて配置中...", lang))
                    
                    # 目の位置（やや上方：Z = 0.42H）
                    eye_r = W * 0.075
                    eye_dist = W * 0.18
                    eye_z = H * 0.42
                    eye_y = -r_max * 0.82

                    eye_left = Part.makeSphere(eye_r, FreeCAD.Vector(-eye_dist, eye_y, eye_z))
                    eye_right = Part.makeSphere(eye_r, FreeCAD.Vector(eye_dist, eye_y, eye_z))

                    # 口の2Dアーチ描画（目からしっかり下方に離す：Z_base = 0.21H）
                    mouth_w = W * 0.20
                    mouth_h = H * 0.05
                    mouth_z_base = H * 0.21
                    line_t = W * 0.030

                    pts_mouth_out = [
                        FreeCAD.Vector(-mouth_w, 0, mouth_z_base + mouth_h),
                        FreeCAD.Vector(-mouth_w * 0.5, 0, mouth_z_base),
                        FreeCAD.Vector(0, 0, mouth_z_base - mouth_h * 0.3),
                        FreeCAD.Vector(mouth_w * 0.5, 0, mouth_z_base),
                        FreeCAD.Vector(mouth_w, 0, mouth_z_base + mouth_h)
                    ]
                    c_m_out = Part.BSplineCurve()
                    c_m_out.buildFromPoles(pts_mouth_out)

                    pts_mouth_in = [
                        FreeCAD.Vector(mouth_w, 0, mouth_z_base + mouth_h),
                        FreeCAD.Vector(mouth_w * 0.5, 0, mouth_z_base + line_t),
                        FreeCAD.Vector(0, 0, mouth_z_base - mouth_h * 0.3 + line_t),
                        FreeCAD.Vector(-mouth_w * 0.5, 0, mouth_z_base + line_t),
                        FreeCAD.Vector(-mouth_w, 0, mouth_z_base + mouth_h)
                    ]
                    c_m_in = Part.BSplineCurve()
                    c_m_in.buildFromPoles(pts_mouth_in)

                    wire_mouth = Part.Wire([c_m_out.toShape(), c_m_in.toShape()])
                    face_mouth = Part.Face(wire_mouth)

                    mouth_ext = face_mouth.extrude(FreeCAD.Vector(0, -r_max * 2.5, 0))
                    mouth_ext.translate(FreeCAD.Vector(0, r_max * 0.5, 0))

                    # 口の盛り上げ量
                    emboss_val = max(1.2, W * 0.035)
                    pts_emboss = []
                    for p in pts:
                        if p.x > 0.001:
                            pts_emboss.append(FreeCAD.Vector(p.x + emboss_val, 0, p.z))
                        else:
                            pts_emboss.append(p)
                            
                    curve_emboss = Part.BSplineCurve()
                    curve_emboss.buildFromPoles(pts_emboss)
                    wire_emboss = Part.Wire([curve_emboss.toShape(), axis_line])
                    slime_emboss_body = Part.Face(wire_emboss).revolve(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), 360.0)

                    mouth_embossed_solid = mouth_ext.common(slime_emboss_body)

                    # 一体化処理
                    final_shape = final_shape.fuse(eye_left).fuse(eye_right).fuse(mouth_embossed_solid)

                # ---------------------------------------------------------
                # 3. 仕上げとカラー設定
                # ---------------------------------------------------------
                bar.update(90, translate_text("3. 仕上げ処理中...", lang))
                final_shape = final_shape.removeSplitter()

                obj = doc.addObject("Part::Feature", "Slime_Model")
                obj.Shape = final_shape
                
                colors = [
                    (0.15, 0.55, 0.95),  # スライムブルー
                    (0.85, 0.88, 0.90),  # メタル
                    (0.40, 0.85, 0.25),  # ライムグリーン
                    (0.90, 0.15, 0.25),  # チェリーレッド
                    (0.95, 0.80, 0.10)   # キングイエロー
                ]
                
                obj.ViewObject.ShapeColor = colors[color_idx]
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
                FreeCAD.Console.PrintError(f"Slime creation error: {str(e)}\n")
                err_title = "Error" if lang == "English" else "エラー"
                err_msg = f"An error occurred during creation:\n{str(e)}" if lang == "English" else f"生成中にエラーが発生しました:\n{str(e)}"
                QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Ring_MakeSlime', Tool_MakeSlime())