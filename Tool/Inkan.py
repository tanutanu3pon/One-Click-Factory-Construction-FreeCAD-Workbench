# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part
import Draft
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress

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
        types = [
            "丸印 (シンプルな円柱)", 
            "角印 (シンプルな四角柱)",
            "丸スタンプ (持ち手付き)",
            "角スタンプ (持ち手付き)"
        ]
        selected_type, ok1 = QtWidgets.QInputDialog.getItem(None, "印鑑・スタンプ設計", "形状のタイプ:", types, 0, False)
        if not ok1: return
        type_idx = types.index(selected_type)

        is_maru = type_idx in (0, 2)
        is_simple = type_idx in (0, 1)

        if is_maru:
            size, ok2 = QtWidgets.QInputDialog.getDouble(None, "寸法指定", "直径 (mm):", 15.0, 5.0, 50.0, 1)
            if not ok2: return
        else:
            size, ok2 = QtWidgets.QInputDialog.getDouble(None, "寸法指定", "一辺の幅 (mm):", 21.0, 5.0, 50.0, 1)
            if not ok2: return

        if is_simple:
            length, ok3 = QtWidgets.QInputDialog.getDouble(None, "寸法指定", "印鑑の長さ/高さ (mm):", 60.0, 10.0, 150.0, 1)
            if not ok3: return

            edge_items = ["丸めない (シャープ)", "丸める (なめらか)"]
            edge_sel, ok4 = QtWidgets.QInputDialog.getItem(None, "形状仕上げ", "天面（手で持つ側）の角処理:", edge_items, 0, False)
            if not ok4: return
            fillet_top = (edge_items.index(edge_sel) == 1)
        else:
            length = 55.0
            fillet_top = False

        text_str, ok5 = QtWidgets.QInputDialog.getText(None, "文字彫刻設定", "彫り込む文字を入力（例: 印, 田中）:")
        if not ok5 or not text_str: return

        text_depth, ok6 = QtWidgets.QInputDialog.getDouble(None, "文字彫刻設定", "彫り込みの深さ (mm):", 1.0, 0.1, 5.0, 2)
        if not ok6: return

        self.create_and_carve_inkan(type_idx, size, length, fillet_top, text_str, text_depth)

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

    def create_and_carve_inkan(self, type_idx, size, length, fillet_top, text_str, text_depth):
        with Progress.ProgressManager() as bar:
            bar.start(title="印鑑・スタンプ生成", initial_text="OSのフォント環境をスキャン中...")

            doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
            font_path = self._get_system_font()

            if not font_path:
                QtWidgets.QMessageBox.critical(None, "エラー", "利用可能なフォントファイルが見つかりません。")
                return

            bar.update(15, "1/3: 土台ソリッドを構築中...")
            
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
            else:  # スタンプ
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

            if fillet_top and type_idx in (0, 1):
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

            bar.update(45, "2/3: 文字サイズを自動計測して3D最適化中...")
            try:
                max_allowed_zone = size * 0.75
                temp_size = 10.0
                try:
                    shapestring_obj = Draft.makeShapeString(Text=text_str, FontFile=font_path, Size=temp_size)
                except TypeError:
                    try:
                        shapestring_obj = Draft.makeShapeString(string=text_str, fontFile=font_path, size=temp_size)
                    except TypeError:
                        shapestring_obj = Draft.makeShapeString(String=text_str, FontFile=font_path, Size=temp_size)
                
                temp_bbox = shapestring_obj.Shape.BoundBox
                temp_width = temp_bbox.XMax - temp_bbox.XMin
                temp_height = temp_bbox.YMax - temp_bbox.YMin
                
                max_temp_dim = max(temp_width, temp_height)
                if max_temp_dim <= 0: max_temp_dim = 1.0
                
                optimized_font_size = (max_allowed_zone / max_temp_dim) * temp_size
                
                if hasattr(shapestring_obj, "Size"):
                    shapestring_obj.Size = optimized_font_size
                elif hasattr(shapestring_obj, "size"):
                    shapestring_obj.size = optimized_font_size
                    
                doc.recompute()
                
                bar.update(60, "立体文字（彫刻用カッター）をソリッド化中...")
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
                QtWidgets.QMessageBox.warning(None, "文字生成エラー", f"文字の立体化に失敗しました。\n詳細: {str(e)}")
                return

            bar.update(80, "3/3: 土台から文字をブーリアン減算(彫刻)中...")
            try:
                base_shape = Part.Solid(base_shape)
                final_inkan_shape = base_shape.cut(text_solid)
                final_inkan_shape = final_inkan_shape.removeSplitter()
            except Exception as e:
                QtWidgets.QMessageBox.warning(None, "彫刻エラー", f"ブーリアン減算に失敗しました。\n詳細: {str(e)}")
                return

            bar.update(95, "印鑑オブジェクトの描画色を仕上げ中...")
            obj = doc.addObject("Part::Feature", label)
            obj.Shape = final_inkan_shape
            
            obj.ViewObject.ShapeColor = (0.92, 0.88, 0.80)  
            obj.ViewObject.LineColor = (0.20, 0.20, 0.20)   
            obj.ViewObject.LineWidth = 1.5                  
            obj.ViewObject.DisplayMode = "Flat Lines"
            
            bar.update(100, "画面を更新しています...")

            doc.recompute()
            FreeCADGui.activeView().viewAxometric()
            FreeCADGui.activeView().fitAll()

FreeCADGui.addCommand('Ring_Inkan', Tool_Inkan())