# -*- coding: utf-8 -*-
import os
import math
import FreeCAD
import FreeCADGui
import Part
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress

import cv2
import numpy as np

class CookieDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(CookieDialog, self).__init__(parent)
        self.setWindowTitle("クッキー型枠・製造工場")
        self.resize(380, 240)
        
        layout = QtWidgets.QFormLayout(self)
        
        self.btn_select = QtWidgets.QPushButton("画像を選択 (JPG / PNG)")
        self.btn_select.setStyleSheet("padding: 6px; font-weight: bold;")
        self.btn_select.clicked.connect(self.select_image)
        self.lbl_path = QtWidgets.QLabel("背景が白または透明の写真を選択してください。")
        self.lbl_path.setStyleSheet("color: gray; font-size: 11px;")
        
        layout.addRow(self.btn_select)
        layout.addRow(self.lbl_path)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        self.spin_thickness = QtWidgets.QSpinBox()
        self.spin_thickness.setRange(1, 15)
        self.spin_thickness.setValue(2)
        self.spin_thickness.setSuffix(" mm")
        layout.addRow("<b>型の厚み (線の幅):</b>", self.spin_thickness)
        
        self.spin_height = QtWidgets.QSpinBox()
        self.spin_height.setRange(1, 50)
        self.spin_height.setValue(15)
        self.spin_height.setSuffix(" mm")
        layout.addRow("<b>型の高さ (押し出し量):</b>", self.spin_height)
        
        self.spin_scale = QtWidgets.QSpinBox()
        self.spin_scale.setRange(10, 300)
        self.spin_scale.setValue(70)
        self.spin_scale.setSuffix(" mm")
        layout.addRow("型の最大横幅:", self.spin_scale)

        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.button(QtWidgets.QDialogButtonBox.Ok).setText("クッキー型を生成")
        btn_box.button(QtWidgets.QDialogButtonBox.Cancel).setText("キャンセル")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

        self.image_path = ""

    def select_image(self):
        file_filter = "Image Files (*.jpg *.jpeg *.png *.bmp)"
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "画像を選択", "", file_filter)
        if path:
            self.image_path = path
            self.lbl_path.setText(os.path.basename(path))

    def get_values(self):
        return {
            "path": self.image_path,
            "thickness": self.spin_thickness.value(),
            "height": self.spin_height.value(),
            "target_width": self.spin_scale.value()
        }

class Tool_MakeCookie:
    def GetResources(self):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "cookie.png").replace('\\', '/')
        return {
            'Pixmap': icon_path, 
            'MenuText': "クッキー型の作成", 
            'ToolTip': "画像から外枠を自動トレースして立体のクッキー型枠を作成します"
        }

    def Activated(self):
        dialog = CookieDialog()
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
            
        vals = dialog.get_values()
        if not vals["path"]:
            QtWidgets.QMessageBox.warning(None, "エラー", "画像が選択されていません。")
            return

        with Progress.ProgressManager() as bar:
            bar.start(title="クッキー型枠・立体成形", initial_text="画像をSVG風に高精度トレース中...")

            try:
                with open(vals["path"], "rb") as f:
                    img_array = np.asarray(bytearray(f.read()), dtype=np.uint8)
                img_bgr = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)

                if img_bgr is None:
                    raise ValueError("画像の読み込みに失敗しました。")

                if img_bgr.shape[2] == 4 and np.min(img_bgr[:, :, 3]) < 255:
                    thresh_inner = (img_bgr[:, :, 3] > 10).astype(np.uint8) * 255
                else:
                    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
                    thresh_inner = (img_gray < 190).astype(np.uint8) * 255

                kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                thresh_inner = cv2.morphologyEx(thresh_inner, cv2.MORPH_CLOSE, kernel_close)

                contours_in, _ = cv2.findContours(thresh_inner, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if not contours_in:
                    raise ValueError("輪郭を検出できませんでした。")
                
                main_contour_in = max(contours_in, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(main_contour_in)
                scale = vals["target_width"] / w if w > 0 else 1.0

                bar.update(30, "AI画像処理で厚みを計算中...")
                thickness_px = int(vals["thickness"] / scale)
                if thickness_px < 1: thickness_px = 1
                
                kernel_size = thickness_px * 2 + 1
                dilate_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
                thresh_outer = cv2.dilate(thresh_inner, dilate_kernel, iterations=1)

                contours_out, _ = cv2.findContours(thresh_outer, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                main_contour_out = max(contours_out, key=cv2.contourArea)

                bar.update(50, "曲線の最適化中...")
                eps_in = 0.003 * cv2.arcLength(main_contour_in, True)
                approx_in = cv2.approxPolyDP(main_contour_in, eps_in, True)
                
                eps_out = 0.003 * cv2.arcLength(main_contour_out, True)
                approx_out = cv2.approxPolyDP(main_contour_out, eps_out, True)

                freecad_points_in = []
                for pt in approx_in:
                    freecad_points_in.append(FreeCAD.Vector((pt[0][0] - x) * scale, -(pt[0][1] - y) * scale, 0))
                freecad_points_in.append(freecad_points_in[0])

                freecad_points_out = []
                for pt in approx_out:
                    freecad_points_out.append(FreeCAD.Vector((pt[0][0] - x) * scale, -(pt[0][1] - y) * scale, 0))
                freecad_points_out.append(freecad_points_out[0])

                bar.update(70, "立体化のための面を構築中...")
                inner_wire = Part.makePolygon(freecad_points_in)
                outer_wire = Part.makePolygon(freecad_points_out)

                face_inner = Part.Face(inner_wire)
                face_outer = Part.Face(outer_wire)

                bar.update(80, f"{vals['height']}mm 押し出して成形中...")
                solid_inner = face_inner.extrude(FreeCAD.Vector(0, 0, vals["height"]))
                solid_outer = face_outer.extrude(FreeCAD.Vector(0, 0, vals["height"]))

                bar.update(90, "中身をくり抜いて空洞にしています...")
                solid_cookie = solid_outer.cut(solid_inner)

                doc = FreeCAD.activeDocument()
                if not doc:
                    doc = FreeCAD.newDocument("CookieCutter")
                
                for name in ["Cookie_Outline_Wire", "Cookie_Cutter_Solid"]:
                    old_obj = doc.getObject(name)
                    if old_obj: doc.removeObject(old_obj.Name)
                    
                obj = doc.addObject("Part::Feature", "Cookie_Cutter_Solid")
                obj.Shape = solid_cookie
                obj.ViewObject.ShapeColor = (1.0, 0.6, 0.2)
                obj.ViewObject.DisplayMode = "Shaded"
                
                doc.recompute()
                FreeCADGui.SendMsgToActiveView("ViewFit")

                bar.update(100, "完了しました！")
                QtWidgets.QMessageBox.information(None, "成功", "中身を完璧にくり抜いた、本物のクッキー型枠が完成しました！")

            except Exception as e:
                FreeCAD.Console.PrintError(f"クッキー型立体化エラー: {str(e)}\n")
                QtWidgets.QMessageBox.critical(None, "エラー", f"立体化中にエラーが発生しました:\n{str(e)}")

FreeCADGui.addCommand('Ring_MakeCookie', Tool_MakeCookie())