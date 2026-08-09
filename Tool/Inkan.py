# -*- coding: utf-8 -*-
import os
import math
import FreeCAD
import FreeCADGui
import Part
import Draft

# 【修正】絶対インポートで安全にCoreモジュールを読み込む
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
            'ToolTip' : "土台のサイズに合わせて、文字が絶対にはみ出さないよう自動調整して彫り込みします（進捗窓付き）"
        }

    def Activated(self):
        lang = get_language()

        # 【追加】新種類「六角印 (亀甲の六角柱)」を追加した7種類の一覧
        types = [
            "丸印 (シンプルな円柱)", 
            "角印 (シンプルな四角柱)",
            "丸スタンプ (持ち手付き)",
            "角スタンプ (持ち手付き)",
            "小判印 (伝統的な楕円型)",
            "八角印 (開運の八角柱)",
            "六角印 (亀甲の六角柱)"
        ]
        
        # 【修正】QtWidgets.QInputDialog から TranslatedInputDialog へ差し替え
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

        text_str, ok5 = TranslatedInputDialog.getText(None, "文字彫刻設定", "彫り込む文字を入力（例: 印, 田中）:")
        if not ok5 or not text_str: return

        text_depth, ok6 = TranslatedInputDialog.getDouble(None, "文字彫刻設定", "彫り込みの深さ (mm):", 1.0, 0.1, 5.0, 2)
        if not ok6: return

        self.create_and_carve_inkan(type_idx, size, length, fillet_top, text_str, text_depth, lang)

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

    def create_and_carve_inkan(self, type_idx, size, length, fillet_top, text_str, text_depth, lang):
        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("印鑑・スタンプ生成", lang), initial_text=translate_text("OSのフォント環境をスキャン中...", lang))

            doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
            font_path = self._get_system_font()

            if not font_path:
                QtWidgets.QMessageBox.critical(None, translate_text("エラー", lang), translate_text("利用可能なフォントファイルが見つかりません。", lang))
                return

            bar.update(15, translate_text("1/3: 土台ソリッドを構築中...", lang))
            
            r_base = size / 2.0
            is_stamp = type_idx in (2, 3)
            h_base = 8.0 if is_stamp else length

            if type_idx == 0:  # 丸印
                base_shape = Part.makeCylinder(r_base, length)
                label = f"Inkan_Maru_{text_str}"
            elif type_idx == 1:  # 角印
                half_s = size / 2.0
                p_start = FreeCAD.Vector(-half_s, -half_s, 0)
                base_shape = Part.makeBox(size, size, length, p_start)
                label = f"Inkan_Kaku_{text_str}"
            elif type_idx == 4:  # 小判印 (楕円型: 縦横比 1 : 0.7)
                rx = size * 0.35
                ry = size * 0.50
                ellipse_geom = Part.Ellipse(FreeCAD.Vector(0, 0, 0), ry, rx)
                wire = Part.Wire([ellipse_geom.toShape()])
                face = Part.Face(wire)
                base_shape = face.extrude(FreeCAD.Vector(0, 0, length))
                label = f"Inkan_Koban_{text_str}"
            elif type_idx == 5:  # 八角印 (開運の八角柱)
                r_oct = size / 2.0
                pts_oct = []
                for k in range(8):
                    ang = math.pi / 8.0 + k * math.pi / 4.0
                    pts_oct.append(FreeCAD.Vector(r_oct * math.cos(ang), r_oct * math.sin(ang), 0))
                pts_oct.append(pts_oct[0])
                wire_oct = Part.makePolygon(pts_oct)
                face_oct = Part.Face(wire_oct)
                base_shape = face_oct.extrude(FreeCAD.Vector(0, 0, length))
                label = f"Inkan_Hakkaku_{text_str}"
            elif type_idx == 6:  # 【新規追加】六角印 (亀甲の六角柱)
                r_hex = size / 2.0
                pts_hex = []
                for k in range(6):
                    ang = math.pi / 6.0 + k * math.pi / 3.0
                    pts_hex.append(FreeCAD.Vector(r_hex * math.cos(ang), r_hex * math.sin(ang), 0))
                pts_hex.append(pts_hex[0])
                wire_hex = Part.makePolygon(pts_hex)
                face_hex = Part.Face(wire_hex)
                base_shape = face_hex.extrude(FreeCAD.Vector(0, 0, length))
                label = f"Inkan_Rokkaku_{text_str}"
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
                    label = f"Stamp_Kaku_{text_str}"
                else:  # 丸スタンプ
                    base_shape = handle_shape
                    label = f"Stamp_Maru_{text_str}"

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

            bar.update(45, translate_text("2/3: 文字サイズを自動計測して3D最適化中...", lang))
            try:
                temp_size = 10.0
                try:
                    shapestring_obj = Draft.makeShapeString(Text=text_str, FontFile=font_path, Size=temp_size)
                except TypeError:
                    try:
                        shapestring_obj = Draft.makeShapeString(string=text_str, fontFile=font_path, size=temp_size)
                    except TypeError:
                        shapestring_obj = Draft.makeShapeString(String=text_str, FontFile=font_path, Size=temp_size)
                
                temp_bbox = shapestring_obj.Shape.BoundBox
                temp_width = max(temp_bbox.XMax - temp_bbox.XMin, 0.1)
                temp_height = max(temp_bbox.YMax - temp_bbox.YMin, 0.1)
                
                # --- 幾何学的に絶対食み出さない自動スケール計算 ---
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

                optimized_font_size = temp_size * scale
                
                if hasattr(shapestring_obj, "Size"):
                    shapestring_obj.Size = optimized_font_size
                elif hasattr(shapestring_obj, "size"):
                    shapestring_obj.size = optimized_font_size
                    
                doc.recompute()
                
                bar.update(60, translate_text("立体文字（彫刻用カッター）をソリッド化中...", lang))
                extra_depth = text_depth + 0.2
                text_solid = shapestring_obj.Shape.extrude(FreeCAD.Vector(0, 0, -extra_depth))
                
                if hasattr(text_solid, "ShapeType") and text_solid.ShapeType != "Solid":
                    try: text_solid = Part.makeSolid(text_solid)
                    except Exception: pass
                
                text_bbox = text_solid.BoundBox
                text_center_x = (text_bbox.XMax + text_bbox.XMin) / 2.0
                text_center_y = (text_bbox.YMax + text_bbox.YMin) / 2.0
                
                text_solid.translate(FreeCAD.Vector(-text_center_x, -text_center_y, 0.1))
                doc.removeObject(shapestring_obj.Name)

            except Exception as e:
                err_title = "Text Generation Error" if lang == "English" else "文字生成エラー"
                err_msg = f"Text 3D modeling failed.\nDetails: {str(e)}" if lang == "English" else f"文字の立体化に失敗しました。\n詳細: {str(e)}"
                QtWidgets.QMessageBox.warning(None, err_title, err_msg)
                return

            bar.update(80, translate_text("3/3: 土台から文字をブーリアン減算(彫刻)中...", lang))
            try:
                base_shape = Part.Solid(base_shape)
                final_inkan_shape = base_shape.cut(text_solid)
                final_inkan_shape = final_inkan_shape.removeSplitter()
            except Exception as e:
                err_title = "Engraving Error" if lang == "English" else "彫刻エラー"
                err_msg = f"Boolean subtraction failed.\nDetails: {str(e)}" if lang == "English" else f"ブーリアン減算に失敗しました。\n詳細: {str(e)}"
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