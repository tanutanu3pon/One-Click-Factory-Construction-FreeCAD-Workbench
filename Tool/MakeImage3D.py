# -*- coding: utf-8 -*-
# Tool/MakeImage3D.py
import os
import math
import FreeCAD
import FreeCADGui
import Part

from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedDialog, translate_text
from Core.Language import get_language

try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False


class Image3DDialog(TranslatedDialog):
    def __init__(self, parent=None):
        super(Image3DDialog, self).__init__(parent)
        self.setWindowTitle("カラー画像3Dセグメント成形")
        self.resize(400, 260)
        
        self.image_path = ""
        self.h_px = 0
        self.w_px = 0
        self.img_rgba = None

        layout = QtWidgets.QFormLayout(self)
        
        # 1. 画像選択
        self.btn_select = QtWidgets.QPushButton("1. 画像を選択 (JPG / PNG / JPEG)")
        self.btn_select.setStyleSheet("padding: 6px; font-weight: bold;")
        self.btn_select.clicked.connect(self.select_image)
        self.lbl_path = QtWidgets.QLabel("画像ファイルを選択してください。")
        self.lbl_path.setStyleSheet("color: gray; font-size: 11px;")
        
        layout.addRow(self.btn_select)
        layout.addRow(self.lbl_path)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        # 2. 横幅指定
        self.spin_width = QtWidgets.QDoubleSpinBox()
        self.spin_width.setRange(1.0, 1000.0)
        self.spin_width.setValue(100.0)
        self.spin_width.setSuffix(" mm")
        self.spin_width.valueChanged.connect(self.update_image_plane)
        layout.addRow("<b>2. 横幅 (左下原点):</b>", self.spin_width)
        
        # 3. 厚み指定
        self.spin_height = QtWidgets.QDoubleSpinBox()
        self.spin_height.setRange(0.5, 100.0)
        self.spin_height.setValue(3.0)
        self.spin_height.setSuffix(" mm")
        layout.addRow("<b>3. 基本厚み:</b>", self.spin_height)

        # 4. 色数指定
        self.spin_colors = QtWidgets.QSpinBox()
        self.spin_colors.setRange(2, 10)
        self.spin_colors.setValue(5)
        self.spin_colors.setSuffix(" 色")
        layout.addRow("<b>4. 分割色数:</b>", self.spin_colors)

        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        # 5. セグメント化実行ボタン
        self.btn_segment = QtWidgets.QPushButton("5. 3Dセグメント化 実行")
        self.btn_segment.setStyleSheet("padding: 8px; font-weight: bold; background-color: #007ACC; color: white;")
        self.btn_segment.clicked.connect(self.accept)
        layout.addRow(self.btn_segment)

    def select_image(self):
        lang = get_language()
        title_text = "Select Image" if lang == "English" else "画像を選択"
        file_filter = "Image Files (*.jpg *.jpeg *.png *.bmp)"
        
        download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(download_dir):
            download_dir = ""

        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, title_text, download_dir, file_filter)
        if path:
            self.image_path = path
            self.lbl_path.setText(os.path.basename(path))

            with open(path, "rb") as f:
                img_array = np.asarray(bytearray(f.read()), dtype=np.uint8)
            self.img_rgba = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)
            if self.img_rgba is not None:
                self.h_px, self.w_px = self.img_rgba.shape[0], self.img_rgba.shape[1]
                self.update_image_plane()

    def update_image_plane(self):
        """ 左下原点(0,0)にピッタリ合わせてImagePlaneを配置 """
        if not self.image_path or self.w_px == 0:
            return

        doc = FreeCAD.activeDocument() or FreeCAD.newDocument("Image3D_Model")
        
        width_mm = self.spin_width.value()
        scale = width_mm / float(self.w_px)
        height_mm = float(self.h_px) * scale

        texture_path = self.image_path.replace('\\', '/')

        img_plane = doc.getObject("Tracing_Image_Guide")
        if not img_plane:
            img_plane = doc.addObject("Image::ImagePlane", "Tracing_Image_Guide")

        img_plane.ImageFile = texture_path
        img_plane.XSize = width_mm
        img_plane.YSize = height_mm

        # 左下を(0,0,0)に一致させる配置
        img_plane.Placement.Base = FreeCAD.Vector(width_mm / 2.0, height_mm / 2.0, 0)

        doc.recompute()
        FreeCADGui.SendMsgToActiveView("ViewFit")

    def get_values(self):
        return {
            "path": self.image_path,
            "width": self.spin_width.value(),
            "height": self.spin_height.value(),
            "k_colors": self.spin_colors.value(),
            "img_rgba": self.img_rgba,
            "h_px": self.h_px,
            "w_px": self.w_px
        }


class Tool_MakeImage3D:
    def GetResources(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        wb_dir = os.path.dirname(current_dir)
        icons_dir = os.path.join(wb_dir, "icons").replace('\\', '/')
        
        if os.path.exists(icons_dir):
            FreeCADGui.addIconPath(icons_dir)

        icon_path = os.path.join(icons_dir, "png3d.png").replace('\\', '/')
        if not os.path.exists(icon_path):
            icon_path = os.path.join(icons_dir, "main.png").replace('\\', '/')
        
        return {
            'Pixmap'  : icon_path,
            'MenuText': "画像カラー3Dセグメント成形",
            'ToolTip' : "左下原点で下絵と位置を完璧に一致させ、色ごとに独立した3Dパーツ群を生成します"
        }

    def Activated(self):
        lang = get_language()

        if not HAS_OPENCV:
            QtWidgets.QMessageBox.critical(
                None, 
                translate_text("ライブラリ不足", lang), 
                translate_text("画像処理には OpenCV および NumPy が必要です。\nFreeCADのPython環境に 'opencv-python' と 'numpy' をインストールしてください。", lang)
            )
            return

        dialog = Image3DDialog()
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
            
        vals = dialog.get_values()
        if not vals["path"] or vals["w_px"] == 0:
            QtWidgets.QMessageBox.warning(None, translate_text("エラー", lang), translate_text("画像が選択されていません。", lang))
            return

        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("3Dセグメント生成中", lang), initial_text=translate_text("キャラクター輪郭とカラーセグメントを抽出中...", lang))

            try:
                img_rgba = vals["img_rgba"]
                h_px, w_px = vals["h_px"], vals["w_px"]

                # 1. アルファチャンネルまたは白背景の解析
                if img_rgba.ndim == 3 and img_rgba.shape[2] == 4:
                    img_bgr = img_rgba[:, :, :3]
                    valid_mask = img_rgba[:, :, 3] > 50
                else:
                    img_bgr = img_rgba
                    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
                    valid_mask = gray < 235

                width_mm = vals["width"]
                scale = width_mm / float(w_px)

                # 2. エッジを保持したブラー処理
                img_blur = cv2.bilateralFilter(img_bgr, 7, 50, 50)

                # 3. K-Means 減色処理
                bar.update(25, translate_text("主要カラーを抽出中...", lang))
                valid_pixels = img_blur[valid_mask].reshape((-1, 3)).astype(np.float32)

                if len(valid_pixels) == 0:
                    raise ValueError("有効なキャラクター領域が検出できませんでした。")

                k = vals["k_colors"]
                criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 15, 0.5)
                _, labels_flat, centers = cv2.kmeans(valid_pixels, k, None, criteria, 10, cv2.KMEANS_PP_CENTERS)

                labels = np.full((h_px, w_px), -1, dtype=int)
                labels[valid_mask] = labels_flat.flatten()
                centers = np.uint8(centers)

                # 面積が大きい順（背景・ベース体積）に並べ替え
                counts = [np.sum(labels == i) for i in range(k)]
                sorted_color_indices = np.argsort(counts)[::-1]

                doc = FreeCAD.activeDocument() or FreeCAD.newDocument("Image3D_Model")
                group = doc.addObject("App::DocumentObjectGroup", "Image3D_ColorSegments")

                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                base_h = vals["height"]

                # 4. 色セグメントごとにソリッド化（小さいパーツほど前面に積層配置）
                for rank, color_idx in enumerate(sorted_color_indices):
                    pct = 30 + int(60 * (rank / float(k)))
                    bar.update(pct, f"色パーツ [{rank+1}/{k}] を立体化中...")

                    mask = (labels == color_idx).astype(np.uint8) * 255
                    if np.sum(mask) == 0:
                        continue

                    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

                    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    segment_faces = []
                    for cnt in contours:
                        if cv2.contourArea(cnt) < 15: # ノイズカット
                            continue

                        eps = 0.0012 * cv2.arcLength(cnt, True)
                        approx = cv2.approxPolyDP(cnt, eps, True)
                        if len(approx) < 3:
                            continue

                        # 【重要】左下原点 (0,0) に完全補正したY軸座標
                        pts = [FreeCAD.Vector(p[0][0] * scale, (h_px - p[0][1]) * scale, 0) for p in approx]
                        pts.append(pts[0])

                        try:
                            wire = Part.makePolygon(pts)
                            face = Part.Face(wire)
                            segment_faces.append(face)
                        except Exception:
                            pass

                    if not segment_faces:
                        continue

                    compound_face = Part.makeCompound(segment_faces)
                    
                    # 目・口など小さなパーツ（後方のランク）ほど高さをわずかに高く＆前面へ移動して埋没を防止
                    z_offset = rank * 0.12
                    part_h = base_h + (rank * 0.05)

                    solid_seg = compound_face.extrude(FreeCAD.Vector(0, 0, part_h))
                    solid_seg.translate(FreeCAD.Vector(0, 0, z_offset))

                    color = centers[color_idx]
                    rgb_color = (float(color[2]) / 255.0, float(color[1]) / 255.0, float(color[0]) / 255.0)

                    obj_name = f"Segment_Color_{rank+1}"
                    seg_obj = doc.addObject("Part::Feature", obj_name)
                    seg_obj.Shape = solid_seg
                    seg_obj.ViewObject.ShapeColor = rgb_color
                    seg_obj.ViewObject.DisplayMode = "Shaded"
                    group.addObject(seg_obj)

                # 5. 下絵（ImagePlane）の位置を最上面へ移動
                img_plane = doc.getObject("Tracing_Image_Guide")
                if img_plane:
                    height_mm = float(h_px) * scale
                    img_plane.Placement.Base = FreeCAD.Vector(width_mm / 2.0, height_mm / 2.0, base_h + (k * 0.12) + 0.1)

                doc.recompute()
                FreeCADGui.SendMsgToActiveView("ViewFit")

                bar.update(100, translate_text("完了しました！", lang))
                QtWidgets.QMessageBox.information(
                    None, 
                    "成功", 
                    "キャラクターの輪郭に応じた色別3Dセグメント群が生成されました！"
                )

            except Exception as e:
                FreeCAD.Console.PrintError(f"Image3D generation error: {str(e)}\n")
                QtWidgets.QMessageBox.critical(None, "エラー", f"処理中にエラーが発生しました:\n{str(e)}")


FreeCADGui.addCommand('Ring_MakeImage3D', Tool_MakeImage3D())