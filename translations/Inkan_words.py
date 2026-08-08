# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part
import Draft
from PySide import QtWidgets

# Core/Progress.py から最新の進捗マネージャーをインポート
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
        # 1. 形状の選択
        types = [
            "丸印 (シンプルな円柱)", 
            "角印 (シンプルな四角柱)",
            "丸スタンプ (持ち手付き)",
            "角スタンプ (持ち手付き)"
        ]
        selected_type_text, ok1 = QtWidgets.QInputDialog.getItem(None, "印鑑・スタンプ設計", "形状のタイプ:", types, 0, False)
        if not ok1: return
        # ★英語化対策：何番目が選ばれたかのインデックス（0～3）を取得
        type_idx = types.index(selected_type_text) if selected_type_text in types else 0
        
        # 2. 各形状に応じた寸法入力 (0, 2番目が「丸」系)
        if type_idx in [0, 2]:
            size, ok2 = QtWidgets.QInputDialog.getDouble(None, "寸法指定", "直径 (mm):", 15.0, 5.0, 50.0, 1)
            if not ok2: return
        else:
            size, ok2 = QtWidgets.QInputDialog.getDouble(None, "寸法指定", "一辺の幅 (mm):", 21.0, 5.0, 50.0, 1)
            if not ok2: return

        # 3. 高さ（長さ）の入力（0, 1番目が「シンプルな印鑑」系）
        if type_idx in [0, 1]:
            length, ok3 = QtWidgets.QInputDialog.getDouble(None, "寸法指定", "印鑑の長さ/高さ (mm):", 60.0, 10.0, 150.0, 1)
            if not ok3: return

            # 天面エッジの丸め処理を選択
            edge_items = ["丸めない (シャープ)", "丸める (なめらか)"]
            edge_sel_text, ok4 = QtWidgets.QInputDialog.getItem(None, "形状仕上げ", "天面（手で持つ側）の角処理:", edge_items, 0, False)
            if not ok4: return
            # ★英語化対策：インデックス判定
            edge_idx = edge_items.index(edge_sel_text) if edge_sel_text in edge_items else 0
            fillet_top = (edge_idx == 1)
        else:
            length = 55.0  # 持ち手付きスタンプの標準高さ
            fillet_top = False

        # 4. 彫り込む文字の入力
        text_str, ok5 = QtWidgets.QInputDialog.getText(None, "文字彫刻設定", "彫り込む文字を入力（例: 印, 田中）:")
        if not ok5 or not text_str: return

        # 5. 彫り込み深さ
        text_depth, ok6 = QtWidgets.QInputDialog.getDouble(None, "文字彫刻設定", "彫り込みの深さ (mm):", 1.0, 0.1, 5.0, 2)
        if not ok6: return

        # 生成・彫刻関数の呼び出し（安全のためにインデックスとテキストを両方渡す）
        self.create_and_carve_inkan(type_idx, selected_type_text, size, length, fillet_top, text_str, text_depth)

    def create_and_carve_inkan(self, type_idx, selected_type_text, size, length, fillet_top, text_str, text_depth):
        bar = Progress.ProgressManager()
        bar.start(title="印鑑・スタンプ生成", initial_text="OSのフォント環境をスキャン中...")

        doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
        
        # 確実に読み込めるフォントの探索
        font_candidates = [
            r"C:\Windows\Fonts\meiryo.ttc",
            r"C:\Windows\Fonts\msgothic.ttc",
            r"C:\Windows\Fonts\yugothr.ttf",
            r"C:\Windows\Fonts\arial.ttf"
        ]
        
        font_path = ""
        for path in font_candidates:
            if os.path.exists(path):
                font_path = path
                break

        # ==========================================
        # 1. 印鑑の土台（ソリッド）を作成
        # ==========================================
        bar.update(15, f"1/3: {selected_type_text} の土台ソリッドを構築中...")
        
        r_base = size / 2.0
        # 2, 3番目が「スタンプ」系
        h_base = 8.0 if type_idx in [2, 3] else length

        if type_idx == 0:  # 丸印 (シンプルな円柱)
            base_shape = Part.makeCylinder(r_base, length)
            label = f"Inkan_Maru_{text_str}"
        elif type_idx == 1:  # 角印 (シンプルな四角柱)
            half_s = size / 2.0
            p_start = FreeCAD.Vector(-half_s, -half_s, 0)
            base_shape = Part.makeBox(size, size, length, p_start)
            label = f"Inkan_Kaku_{text_str}"
        else:
            # --- 持ち手付きスタンプ（回転体）の作成 ---
            pts = [
                FreeCAD.Vector(0, 0, 0),                        # 中心底面
                FreeCAD.Vector(r_base, 0, 0),                   # 底面外角
                FreeCAD.Vector(r_base, 0, h_base),              # 土台の上の角
                FreeCAD.Vector(r_base * 0.8, 0, h_base + 3.0),   # くびれ始まり
                FreeCAD.Vector(r_base * 0.4, 0, length * 0.35), # 一番細いくびれ部分
                FreeCAD.Vector(r_base * 0.75, 0, length * 0.75),# 上部の膨らみ
                FreeCAD.Vector(r_base * 0.6, 0, length * 0.95), # 頭頂部手前
                FreeCAD.Vector(0, 0, length)                    # テッペン中心
            ]
            
            edges = []
            edges.append(Part.makeLine(pts[0], pts[1]))
            edges.append(Part.makeLine(pts[1], pts[2]))
            
            curve = Part.BSplineCurve()
            curve.buildFromPoles(pts[2:8])
            edges.append(curve.toShape())
            edges.append(Part.makeLine(pts[7], pts[0]))
            
            profile_face = Part.Face(Part.Wire(edges))
            handle_shape = profile_face.revolve(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), 360)

            if type_idx == 3:  # 角スタンプ (持ち手付き)
                half_s = size / 2.0
                box_base = Part.makeBox(size, size, h_base, FreeCAD.Vector(-half_s, -half_s, 0))
                cutter_cyl = Part.makeCylinder(r_base + 2.0, h_base)
                upper_handle = handle_shape.cut(cutter_cyl)
                base_shape = box_base.fuse(upper_handle)
                label = f"Stamp_Kaku_{text_str}"
            else:  # 丸スタンプ (持ち手付き)
                base_shape = handle_shape
                label = f"Stamp_Maru_{text_str}"

            # 前後がわかるアタリ（ポッチ）を合体
            try:
                marker = Part.makeSphere(size * 0.05)
                marker.translate(FreeCAD.Vector(0, -r_base * 0.7, h_base + 5.0))
                base_shape = base_shape.fuse(marker)
            except:
                pass

        # 天面のフィレット処理（シンプルな印鑑のみ：0, 1番目）
        if fillet_top and type_idx in [0, 1]:
            edges_to_fillet = []
            for e in base_shape.Edges:
                if hasattr(e, "CenterOfMass") and abs(e.CenterOfMass.z - length) < 0.001:
                    edges_to_fillet.append(e)
            if edges_to_fillet:
                try:
                    base_shape = base_shape.makeFillet(1.0, edges_to_fillet)
                except:
                    pass

        # 重複線をクリアして形状データをリフレッシュ
        base_shape = base_shape.removeSplitter()

        # ==========================================
        # 2. 自動サイズ調整付き：彫刻用の立体文字を作成
        # ==========================================
        bar.update(45, "2/3: 文字サイズを自動計測して3D最適化中...")
        try:
            # 限界収まるターゲットサイズを設定
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
            
            # 適切な文字サイズを逆算
            optimized_font_size = (max_allowed_zone / max_temp_dim) * temp_size
            
            # オブジェクトサイズを変更
            if hasattr(shapestring_obj, "Size"):
                shapestring_obj.Size = optimized_font_size
            elif hasattr(shapestring_obj, "size"):
                shapestring_obj.size = optimized_font_size
                
            doc.recompute()
            
            # 文字を下向き（Zマイナス方向）に押し出す
            bar.update(60, "立体文字（彫刻用カッター）をソリッド化中...")
            extra_depth = text_depth + 0.2
            text_solid = shapestring_obj.Shape.extrude(FreeCAD.Vector(0, 0, -extra_depth))
            
            if hasattr(text_solid, "ShapeType") and text_solid.ShapeType != "Solid":
                try: text_solid = Part.makeSolid(text_solid)
                except: pass
            
            # 文字の中心位置計算
            text_bbox = text_solid.BoundBox
            text_center_x = (text_bbox.XMax + text_bbox.XMin) / 2.0
            text_center_y = (text_bbox.YMax + text_bbox.YMin) / 2.0
            
            # 文字を中央へ移動
            text_solid.translate(FreeCAD.Vector(-text_center_x, -text_center_y, 0.1))
            
            # 一時オブジェクトの削除
            doc.removeObject(shapestring_obj.Name)

        except Exception as e:
            bar.close() 
            QtWidgets.QMessageBox.warning(None, "文字生成エラー", f"文字の立体化に失敗しました。\n詳細: {str(e)}")
            return

        # ==========================================
        # 3. ブーリアン演算（引き算）で印面を彫る
        # ==========================================
        bar.update(80, "3/3: 土台から文字をブーリアン減算(彫刻)中...")
        try:
            base_shape = Part.Solid(base_shape)
            
            # 土台から文字ソリッドを引き算（Cut）する
            final_inkan_shape = base_shape.cut(text_solid)
            final_inkan_shape = final_inkan_shape.removeSplitter()
            
        except Exception as e:
            bar.close()
            QtWidgets.QMessageBox.warning(None, "彫刻エラー", f"ブーリアン減算に失敗しました。\n詳細: {str(e)}")
            return

        # ==========================================
        # 4. FreeCADドキュメントへの登録
        # ==========================================
        bar.update(95, "印鑑オブジェクトの描画色を仕上げ中...")
        obj = doc.addObject("Part::Feature", label)
        obj.Shape = final_inkan_shape
        
        # 見やすく上品な明るいベージュ（アイボリー風）に設定
        obj.ViewObject.ShapeColor = (0.92, 0.88, 0.80)  
        obj.ViewObject.LineColor = (0.20, 0.20, 0.20)   
        obj.ViewObject.LineWidth = 1.5                  
        obj.ViewObject.DisplayMode = "Flat Lines"
        
        bar.update(100, "画面を更新しています...")
        bar.close()

        doc.recompute()
        FreeCADGui.activeView().viewAxometric()
        FreeCADGui.activeView().fitAll()

# 登録
FreeCADGui.addCommand('Ring_Inkan', Tool_Inkan())