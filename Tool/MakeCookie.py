# -*- coding: utf-8 -*-
# Tool/MakeCookie.py
import os
import math
import FreeCAD
import FreeCADGui
import Part

try:
    from PySide2 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui

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
        
        # QSpinBoxに変更し、小数点以下を廃止（整数のみ）
        self.spin_thickness = QtWidgets.QSpinBox()
        self.spin_thickness.setRange(1, 15)
        self.spin_thickness.setValue(2) # デフォルト2mm
        self.spin_thickness.setSuffix(" mm")
        layout.addRow("<b>型の厚み (線の幅):</b>", self.spin_thickness)
        
        self.spin_height = QtWidgets.QSpinBox()
        self.spin_height.setRange(1, 50)
        self.spin_height.setValue(15) # デフォルト15mm
        self.spin_height.setSuffix(" mm")
        layout.addRow("<b>型の高さ (押し出し量):</b>", self.spin_height)
        
        self.spin_scale = QtWidgets.QSpinBox()
        self.spin_scale.setRange(10, 300)
        self.spin_scale.setValue(70) # デフォルト70mm
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

        bar = Progress.ProgressManager()
        bar.start(title="クッキー型枠・立体成形", initial_text="画像をSVG風に高精度トレース中...")

        try:
            with open(vals["path"], "rb") as f:
                img_array = np.asarray(bytearray(f.read()), dtype=np.uint8)
            img_bgr = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)

            if img_bgr is None:
                raise ValueError("画像の読み込みに失敗しました。")

            # 1. 内周のシルエット画像を生成（全自動判定版）
            # アルファチャンネル（透過）が存在し、かつ実際に透明な部分があるかチェック
            if img_bgr.shape[2] == 4 and np.min(img_bgr[:, :, 3]) < 255:
                # 【パターンA】本物の透過PNGの場合（背景色に依存せず透明部分で切り抜き）
                thresh_inner = (img_bgr[:, :, 3] > 10).astype(np.uint8) * 255
            else:
                # 【パターンB】背景が白、または市松模様（ダミー透過）の場合
                img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
                # 薄いグレー（市松模様）や純白の背景を自動で無視し、オブジェクトだけを抽出
                thresh_inner = (img_gray < 190).astype(np.uint8) * 255

            kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            thresh_inner = cv2.morphologyEx(thresh_inner, cv2.MORPH_CLOSE, kernel_close)

            # 内周の輪郭とスケールを取得
            contours_in, _ = cv2.findContours(thresh_inner, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours_in:
                raise ValueError("輪郭を検出できませんでした。")
            
            main_contour_in = max(contours_in, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(main_contour_in)
            scale = vals["target_width"] / w if w > 0 else 1.0

            # 2. 画像処理で外周（厚み）を生成
            bar.update(30, "AI画像処理で厚みを計算中...")
            thickness_px = int(vals["thickness"] / scale)
            if thickness_px < 1: thickness_px = 1
            
            kernel_size = thickness_px * 2 + 1
            dilate_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            thresh_outer = cv2.dilate(thresh_inner, dilate_kernel, iterations=1)

            contours_out, _ = cv2.findContours(thresh_outer, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            main_contour_out = max(contours_out, key=cv2.contourArea)

            # 3. 輪郭の最適化
            bar.update(50, "曲線の最適化中...")
            eps_in = 0.003 * cv2.arcLength(main_contour_in, True)
            approx_in = cv2.approxPolyDP(main_contour_in, eps_in, True)
            
            eps_out = 0.003 * cv2.arcLength(main_contour_out, True)
            approx_out = cv2.approxPolyDP(main_contour_out, eps_out, True)

            # 4. 実寸座標への変換
            freecad_points_in = []
            for pt in approx_in:
                freecad_points_in.append(FreeCAD.Vector((pt[0][0] - x) * scale, -(pt[0][1] - y) * scale, 0))
            freecad_points_in.append(freecad_points_in[0])

            freecad_points_out = []
            for pt in approx_out:
                freecad_points_out.append(FreeCAD.Vector((pt[0][0] - x) * scale, -(pt[0][1] - y) * scale, 0))
            freecad_points_out.append(freecad_points_out[0])

            # 5. 内側と外側、それぞれの「中身の詰まった面」を作る
            bar.update(70, "立体化のための面を構築中...")
            inner_wire = Part.makePolygon(freecad_points_in)
            outer_wire = Part.makePolygon(freecad_points_out)

            face_inner = Part.Face(inner_wire)
            face_outer = Part.Face(outer_wire)

            # 6. それぞれを押し出して「ブロック」にする
            bar.update(80, f"{vals['height']}mm 押し出して成形中...")
            solid_inner = face_inner.extrude(FreeCAD.Vector(0, 0, vals["height"]))
            solid_outer = face_outer.extrude(FreeCAD.Vector(0, 0, vals["height"]))

            # 7. 外側のブロックから、内側のブロックを引き算（Cut）して「完璧な中空の枠」を作る
            bar.update(90, "中身をくり抜いて空洞にしています...")
            solid_cookie = solid_outer.cut(solid_inner)

            # 8. 画面へ出力
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
        finally:
            bar.close()

# コマンドの登録
FreeCADGui.addCommand('Ring_MakeCookie', Tool_MakeCookie())