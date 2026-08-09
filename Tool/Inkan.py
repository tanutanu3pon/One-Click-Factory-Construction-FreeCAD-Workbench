# -*- coding: utf-8 -*-
import os
import math
import FreeCAD
import FreeCADGui
import Part
import Draft

# 絶対インポートで安全にCoreモジュールを読み込む
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedInputDialog, translate_text
from Core.Language import get_language

class Tool_Inkan:
    def GetResources(self):
        current_dir = os.path.dirname(__file__)
        ring_dir = os.path.dirname(current_dir)
        icon_path = os.path.join(ring_dir, "icons", "p.png").replace('\\', '/')
        
        return {
            'Pixmap'  : icon_path,
            'MenuText': "印鑑・本格スタンプの作成",
            'ToolTip' : "文字や画像を自動スケールして彫り込み/凸成形します（進捗窓付き）"
        }

    def Activated(self):
        lang = get_language()

        types = [
            "丸印 (シンプルな円柱)", 
            "角印 (シンプルな四角柱)",
            "丸スタンプ (持ち手付き)",
            "角スタンプ (持ち手付き)",
            "小判印 (伝統的な楕円型)",
            "八角印 (開運の八角柱)",
            "六角印 (亀甲の六角柱)"
        ]
        
        selected_type, ok1 = TranslatedInputDialog.getItem(None, "印鑑・スタンプ設計", "形状のタイプ:", types, 0, False)
        if not ok1: return

        trans_types = [translate_text(t, lang) for t in types]

        if selected_type in types:
            type_idx = types.index(selected_type)
        elif selected_type in trans_types:
            type_idx = trans_types.index(selected_type)
        else:
            type_idx = 0

        is_maru = type_idx in (0, 2)
        is_simple = type_idx in (0, 1, 4, 5, 6)

        if is_maru:
            size, ok2 = TranslatedInputDialog.getDouble(None, "寸法指定", "直径 (mm):", 15.0, 5.0, 50.0, 1)
            if not ok2: return
        elif type_idx == 4: # 小判印
            size, ok2 = TranslatedInputDialog.getDouble(None, "寸法指定", "長径 / 縦幅 (mm):", 12.0, 5.0, 50.0, 1)
            if not ok2: return
        else:
            size, ok2 = TranslatedInputDialog.getDouble(None, "寸法指定", "一辺の幅 (mm):", 21.0, 5.0, 50.0, 1)
            if not ok2: return

        if is_simple:
            length, ok3 = TranslatedInputDialog.getDouble(None, "寸法指定", "印鑑の長さ/高さ (mm):", 60.0, 10.0, 150.0, 1)
            if not ok3: return

            edge_items = ["丸めない (シャープ)", "丸める (なめらか)"]
            edge_sel, ok4 = TranslatedInputDialog.getItem(None, "形状仕上げ", "天面（手で持つ側）の角処理:", edge_items, 0, False)
            if not ok4: return

            trans_edge_items = [translate_text(it, lang) for it in edge_items]
            if edge_sel in edge_items:
                fillet_top = (edge_items.index(edge_sel) == 1)
            elif edge_sel in trans_edge_items:
                fillet_top = (trans_edge_items.index(edge_sel) == 1)
            else:
                fillet_top = False
        else:
            length = 55.0
            fillet_top = False

        # 入力方法の選択（文字 or 画像）
        input_methods = ["文字を入力する", "画像ファイル (JPG/PNG) をトレース"]
        input_sel, ok_in = TranslatedInputDialog.getItem(None, "デザイン指定", "印面のデザインソース:", input_methods, 0, False)
        if not ok_in: return

        trans_input_methods = [translate_text(it, lang) for it in input_methods]
        if input_sel in input_methods:
            is_image_mode = (input_methods.index(input_sel) == 1)
        elif input_sel in trans_input_methods:
            is_image_mode = (trans_input_methods.index(input_sel) == 1)
        else:
            is_image_mode = False

        input_mode = "image" if is_image_mode else "text"
        input_data = ""

        if input_mode == "text":
            text_str, ok5 = TranslatedInputDialog.getText(None, "文字彫刻設定", "彫り込む文字を入力（例: 印, 田中）:")
            if not ok5 or not text_str: return
            input_data = text_str
        else:
            try:
                import cv2
                import numpy as np
            except ImportError:
                QtWidgets.QMessageBox.critical(None, translate_text("ライブラリ不足", lang), 
                    translate_text("画像トレースには OpenCV が必要です。\nFreeCADのPython環境に 'opencv-python' と 'numpy' をインストールしてください。", lang))
                return

            img_path, _ = QtWidgets.QFileDialog.getOpenFileName(None, translate_text("画像を選択", lang), "", "Images (*.png *.jpg *.jpeg *.bmp)")
            if not img_path: return
            input_data = img_path

        # 文字/画像の加工スタイル選択（凹 / 凸）
        carve_type_items = ["凹 (底に彫り込む)", "凸 (底から浮かせる)"]
        carve_type_sel, ok_type = TranslatedInputDialog.getItem(None, "文字/画像加工設定", "加工スタイル:", carve_type_items, 0, False)
        if not ok_type: return

        trans_carve_items = [translate_text(it, lang) for it in carve_type_items]
        if carve_type_sel in carve_type_items:
            is_emboss = (carve_type_items.index(carve_type_sel) == 1)
        elif carve_type_sel in trans_carve_items:
            is_emboss = (trans_carve_items.index(carve_type_sel) == 1)
        else:
            is_emboss = False

        depth_label = "凸の高さ (mm):" if is_emboss else "彫り込みの深さ (mm):"
        text_depth, ok6 = TranslatedInputDialog.getDouble(None, "深さ設定", depth_label, 1.0, 0.1, 5.0, 2)
        if not ok6: return

        self.create_and_carve_inkan(type_idx, size, length, fillet_top, input_mode, input_data, text_depth, is_emboss, lang)

    def _get_system_font(self):
        current_dir = os.path.dirname(__file__)
        wb_dir = os.path.dirname(current_dir)
        fonts_dir = os.path.join(wb_dir, "fonts")
        
        if os.path.exists(fonts_dir):
            for f in os.listdir(fonts_dir):
                if f.lower().endswith(('.ttf', '.otf', '.ttc')):
                    return os.path.join(fonts_dir, f)

        candidates = [
            r"C:\Windows\Fonts\meiryo.ttc",
            r"C:\Windows\Fonts\msgothic.ttc",
            r"C:\Windows\Fonts\arial.ttf",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return ""

    def _create_solid_from_image(self, img_path):
        """ OpenCVを用いて最外郭(アウトライン)のみを取得し、中身の詰まった塗りつぶしFaceを生成する """
        import cv2
        import numpy as np

        try:
            with open(img_path, "rb") as f:
                img_array = np.asarray(bytearray(f.read()), dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)
        except Exception as e:
            raise ValueError(f"画像の読み込みに失敗しました: {e}")

        if img is None:
            raise ValueError("画像のデコードに失敗しました。ファイル形式を確認してください。")

        # 二値化処理
        if img.ndim == 3 and img.shape[2] == 4 and np.min(img[:, :, 3]) < 255:
            thresh = (img[:, :, 3] > 10).astype(np.uint8) * 255
        else:
            if img.ndim == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
            thresh = (gray < 190).astype(np.uint8) * 255

        # ノイズ除去と輪郭線の結合補正
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # RETR_EXTERNAL で「最外郭輪郭（一番外側のアウトライン）」のみ抽出（中身の模様や穴は無視）
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        faces = []
        if contours:
            for contour in contours:
                # 小さいゴミノイズを除外
                if cv2.contourArea(contour) < 20:
                    continue

                # 輪郭の平滑化
                epsilon = 0.003 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                if len(approx) < 3: continue
                
                pts = [FreeCAD.Vector(float(p[0][0]), -float(p[0][1]), 0) for p in approx]
                pts.append(pts[0])
                
                try:
                    wire = Part.makePolygon(pts)
                    face = Part.Face(wire)  # 穴を作らず単一の面にする（中身を完全に塗りつぶす）
                    faces.append(face)
                except Exception:
                    pass

        if not faces:
            raise ValueError("画像から有効なシルエットを検出できませんでした。白地に黒描画の画像、または透過PNGをお試しください。")

        return Part.makeCompound(faces)

    def create_and_carve_inkan(self, type_idx, size, length, fillet_top, input_mode, input_data, text_depth, is_emboss, lang):
        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("印鑑・スタンプ生成", lang), initial_text=translate_text("処理を準備中...", lang))

            doc = FreeCAD.activeDocument() or FreeCAD.newDocument()

            if input_mode == "text":
                font_path = self._get_system_font()
                if not font_path:
                    QtWidgets.QMessageBox.critical(None, translate_text("エラー", lang), translate_text("利用可能なフォントファイルが見つかりません。", lang))
                    return
                label_suffix = input_data
            else:
                label_suffix = "Image"

            bar.update(15, translate_text("1/3: 土台ソリッドを構築中...", lang))
            
            r_base = size / 2.0
            is_stamp = type_idx in (2, 3)
            h_base = 8.0 if is_stamp else length

            if type_idx == 0:  # 丸印
                base_shape = Part.makeCylinder(r_base, length)
                label = f"Inkan_Maru_{label_suffix}"
            elif type_idx == 1:  # 角印
                half_s = size / 2.0
                p_start = FreeCAD.Vector(-half_s, -half_s, 0)
                base_shape = Part.makeBox(size, size, length, p_start)
                label = f"Inkan_Kaku_{label_suffix}"
            elif type_idx == 4:  # 小判印
                rx = size * 0.35
                ry = size * 0.50
                ellipse_geom = Part.Ellipse(FreeCAD.Vector(0, 0, 0), ry, rx)
                wire = Part.Wire([ellipse_geom.toShape()])
                face = Part.Face(wire)
                base_shape = face.extrude(FreeCAD.Vector(0, 0, length))
                label = f"Inkan_Koban_{label_suffix}"
            elif type_idx == 5:  # 八角印
                r_oct = size / 2.0
                pts_oct = []
                for k in range(8):
                    ang = math.pi / 8.0 + k * math.pi / 4.0
                    pts_oct.append(FreeCAD.Vector(r_oct * math.cos(ang), r_oct * math.sin(ang), 0))
                pts_oct.append(pts_oct[0])
                wire_oct = Part.makePolygon(pts_oct)
                face_oct = Part.Face(wire_oct)
                base_shape = face_oct.extrude(FreeCAD.Vector(0, 0, length))
                label = f"Inkan_Hakkaku_{label_suffix}"
            elif type_idx == 6:  # 六角印
                r_hex = size / 2.0
                pts_hex = []
                for k in range(6):
                    ang = math.pi / 6.0 + k * math.pi / 3.0
                    pts_hex.append(FreeCAD.Vector(r_hex * math.cos(ang), r_hex * math.sin(ang), 0))
                pts_hex.append(pts_hex[0])
                wire_hex = Part.makePolygon(pts_hex)
                face_hex = Part.Face(wire_hex)
                base_shape = face_hex.extrude(FreeCAD.Vector(0, 0, length))
                label = f"Inkan_Rokkaku_{label_suffix}"
            else:  # スタンプ各種
                pts = [
                    FreeCAD.Vector(0, 0, 0),
                    FreeCAD.Vector(r_base, 0, 0),
                    FreeCAD.Vector(r_base, 0, h_base),
                    FreeCAD.Vector(r_base * 0.8, 0, h_base + 3.0),
                    FreeCAD.Vector(r_base * 0.4, 0, length * 0.35),
                    FreeCAD.Vector(r_base * 0.75, 0, length * 0.75),
                    FreeCAD.Vector(r_base * 0.6, 0, length * 0.95),
                    FreeCAD.Vector(0, 0, length)
                ]
                
                edges = [
                    Part.makeLine(pts[0], pts[1]),
                    Part.makeLine(pts[1], pts[2])
                ]
                
                curve = Part.BSplineCurve()
                curve.buildFromPoles(pts[2:8])
                edges.append(curve.toShape())
                edges.append(Part.makeLine(pts[7], pts[0]))
                
                profile_face = Part.Face(Part.Wire(edges))
                handle_shape = profile_face.revolve(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), 360)

                if type_idx == 3:  # 角スタンプ
                    half_s = size / 2.0
                    box_base = Part.makeBox(size, size, h_base, FreeCAD.Vector(-half_s, -half_s, 0))
                    cutter_cyl = Part.makeCylinder(r_base + 2.0, h_base)
                    upper_handle = handle_shape.cut(cutter_cyl)
                    base_shape = box_base.fuse(upper_handle)
                    label = f"Stamp_Kaku_{label_suffix}"
                else:  # 丸スタンプ
                    base_shape = handle_shape
                    label = f"Stamp_Maru_{label_suffix}"

                try:
                    marker = Part.makeSphere(size * 0.05)
                    marker.translate(FreeCAD.Vector(0, -r_base * 0.7, h_base + 5.0))
                    base_shape = base_shape.fuse(marker)
                except Exception:
                    pass

            if fillet_top and type_idx in (0, 1, 4, 5, 6):
                edges_to_fillet = []
                for e in base_shape.Edges:
                    if hasattr(e, "CenterOfMass") and abs(e.CenterOfMass.z - length) < 0.001:
                        edges_to_fillet.append(e)
                if edges_to_fillet:
                    try:
                        base_shape = base_shape.makeFillet(1.0, edges_to_fillet)
                    except Exception:
                        pass

            base_shape = base_shape.removeSplitter()

            bar.update(45, translate_text("2/3: デザインのサイズを自動計測して3D最適化中...", lang))
            try:
                if input_mode == "text":
                    temp_size = 10.0
                    try:
                        shapestring_obj = Draft.makeShapeString(Text=input_data, FontFile=font_path, Size=temp_size)
                    except TypeError:
                        try:
                            shapestring_obj = Draft.makeShapeString(string=input_data, fontFile=font_path, size=temp_size)
                        except TypeError:
                            shapestring_obj = Draft.makeShapeString(String=input_data, FontFile=font_path, Size=temp_size)
                    
                    temp_bbox = shapestring_obj.Shape.BoundBox
                else:
                    comp_shape = self._create_solid_from_image(input_data)
                    temp_bbox = comp_shape.BoundBox

                temp_width = max(temp_bbox.XMax - temp_bbox.XMin, 0.1)
                temp_height = max(temp_bbox.YMax - temp_bbox.YMin, 0.1)
                
                # 自動スケール計算
                if type_idx in (0, 2):  # 丸印・丸スタンプ
                    diag = math.sqrt(temp_width**2 + temp_height**2)
                    scale = (size * 0.70) / diag
                elif type_idx == 4:  # 小判印
                    a_safe = (size * 0.35) * 0.75
                    b_safe = (size * 0.50) * 0.75
                    scale = 1.0 / math.sqrt(((temp_width / 2.0) / a_safe)**2 + ((temp_height / 2.0) / b_safe)**2)
                elif type_idx in (5, 6):  # 八角印・六角印
                    diag = math.sqrt(temp_width**2 + temp_height**2)
                    scale = (size * 0.65) / diag
                else:  # 角印・角スタンプ
                    scale = min((size * 0.70) / temp_width, (size * 0.70) / temp_height)

                bar.update(60, translate_text("デザインを立体ソリッド化中...", lang))
                extra_depth = text_depth + (0.1 if is_emboss else 0.2)
                
                if input_mode == "text":
                    optimized_font_size = temp_size * scale
                    if hasattr(shapestring_obj, "Size"): shapestring_obj.Size = optimized_font_size
                    elif hasattr(shapestring_obj, "size"): shapestring_obj.size = optimized_font_size
                    doc.recompute()
                    
                    design_solid = shapestring_obj.Shape.extrude(FreeCAD.Vector(0, 0, -extra_depth))
                    doc.removeObject(shapestring_obj.Name)
                else:
                    mat = FreeCAD.Matrix()
                    mat.scale(scale, scale, 1.0)
                    scaled_comp = comp_shape.transformGeometry(mat)
                    design_solid = scaled_comp.extrude(FreeCAD.Vector(0, 0, -extra_depth))
                
                if hasattr(design_solid, "ShapeType") and design_solid.ShapeType != "Solid":
                    try: design_solid = Part.makeSolid(design_solid)
                    except Exception: pass
                
                design_bbox = design_solid.BoundBox
                design_center_x = (design_bbox.XMax + design_bbox.XMin) / 2.0
                design_center_y = (design_bbox.YMax + design_bbox.YMin) / 2.0
                
                design_solid.translate(FreeCAD.Vector(-design_center_x, -design_center_y, 0.1))

            except Exception as e:
                err_title = "Design Generation Error" if lang == "English" else "デザイン生成エラー"
                err_msg = f"3D modeling failed.\nDetails: {str(e)}" if lang == "English" else f"デザインの立体化に失敗しました。\n詳細: {str(e)}"
                QtWidgets.QMessageBox.warning(None, err_title, err_msg)
                return

            if is_emboss:
                bar.update(80, translate_text("3/3: 土台にデザインをブーリアン結合(凸)中...", lang))
            else:
                bar.update(80, translate_text("3/3: 土台からデザインをブーリアン減算(凹)中...", lang))

            try:
                base_shape = Part.Solid(base_shape)
                if is_emboss:
                    final_inkan_shape = base_shape.fuse(design_solid)
                else:
                    final_inkan_shape = base_shape.cut(design_solid)

                final_inkan_shape = final_inkan_shape.removeSplitter()
            except Exception as e:
                err_title = "Processing Error" if lang == "English" else "加工エラー"
                err_msg = f"Boolean operation failed.\nDetails: {str(e)}" if lang == "English" else f"ブーリアン演算に失敗しました。\n詳細: {str(e)}"
                QtWidgets.QMessageBox.warning(None, err_title, err_msg)
                return

            bar.update(95, translate_text("印鑑オブジェクトの描画色を仕上げ中...", lang))
            obj = doc.addObject("Part::Feature", label)
            obj.Shape = final_inkan_shape
            
            obj.ViewObject.ShapeColor = (0.92, 0.88, 0.80)  
            obj.ViewObject.LineColor = (0.20, 0.20, 0.20)   
            obj.ViewObject.LineWidth = 1.5                  
            obj.ViewObject.DisplayMode = "Flat Lines"
            
            bar.update(100, translate_text("画面を更新しています...", lang))

            doc.recompute()
            FreeCADGui.activeView().viewAxometric()
            FreeCADGui.activeView().fitAll()

FreeCADGui.addCommand('Ring_Inkan', Tool_Inkan())