# -*- coding: utf-8 -*-
import os
import math
import FreeCAD
import FreeCADGui
import Part

# 絶対インポートで安全にCoreモジュールを読み込む
from Core.QtCompat import QtWidgets
import Core.Progress as Progress
from Core.Controller import TranslatedInputDialog, translate_text
from Core.Language import get_language

class Tool_MakeCoaster:
    def GetResources(self):
        current_dir = os.path.dirname(__file__)
        ring_dir = os.path.dirname(current_dir)
        # 指定された coaster.png をアイコンとして設定
        icon_path = os.path.join(ring_dir, "icons", "coaster.png").replace('\\', '/')
        return {
            'Pixmap'  : icon_path,
            'MenuText': "コースターの作成",
            'ToolTip' : "丸・四角の形状と、ハニカム・水玉・格子状の模様を選んでコースターを作成します（進捗窓付き）"
        }

    def Activated(self):
        lang = get_language()

        shapes = [
            "丸 (Round)",
            "四角 (Square)"
        ]
        selected_shape, ok1 = TranslatedInputDialog.getItem(None, "外枠の形状", "コースターの形状:", shapes, 0, False)
        if not ok1: return
        
        patterns = [
            "ハチの巣状 (Honeycomb)",
            "水玉 (Polka Dot)",
            "格子状 (Grid)"
        ]
        selected_pattern, ok2 = TranslatedInputDialog.getItem(None, "模様の選択", "中の模様:", patterns, 0, False)
        if not ok2: return

        # コースターのサイズ (一般的な直径/一辺は 80mm ~ 100mm 程度)
        size, ok3 = TranslatedInputDialog.getDouble(None, "寸法指定", "サイズ(直径/一辺) (mm):", 90.0, 50.0, 200.0, 1)
        if not ok3: return

        # インデックスの判定
        trans_shapes = [translate_text(t, lang) for t in shapes]
        shape_idx = 0 if selected_shape in (shapes[0], trans_shapes[0]) else 1
        
        trans_patterns = [translate_text(t, lang) for t in patterns]
        if selected_pattern in (patterns[0], trans_patterns[0]):
            pattern_idx = 0
        elif selected_pattern in (patterns[1], trans_patterns[1]):
            pattern_idx = 1
        else:
            pattern_idx = 2

        self.create_coaster(shape_idx, pattern_idx, size, lang)

    def create_coaster(self, shape_idx, pattern_idx, size, lang):
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
        
        try:
            doc.openTransaction("Create Coaster Model")
            with Progress.ProgressManager() as bar:
                bar.start(title=translate_text("コースター生成", lang), initial_text=translate_text("ベース形状を構築中...", lang))

                H = 4.5           # 全体の厚み
                base_h = 1.5      # 貫通させないための底面厚み（水滴こぼれ防止）
                rim_w = 4.0       # 外縁（リム）の幅
                corner_r = 8.0    # 四角コースターの角丸半径
                r_outer = size / 2.0
                r_inner = r_outer - rim_w

                # ---------------------------------------------------------
                # 1. ベース形状の作成 (フィレットで上下のフチを丸める)
                # ---------------------------------------------------------
                def apply_outer_fillet(solid, f_r):
                    edges_to_fillet = []
                    for edge in solid.Edges:
                        bb = edge.BoundBox
                        # Z=0(底面) または Z=H(上面) の水平なエッジを抽出
                        if abs(bb.ZMax - bb.ZMin) < 0.01:
                            if abs(bb.ZMax) < 0.01 or abs(bb.ZMax - H) < 0.01:
                                edges_to_fillet.append(edge)
                    if edges_to_fillet:
                        try: return solid.makeFillet(f_r, edges_to_fillet)
                        except Exception: pass
                    return solid

                if shape_idx == 0:
                    base_solid = Part.makeCylinder(r_outer, H, FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1))
                    base_solid = apply_outer_fillet(base_solid, 1.2)
                else:
                    box = Part.makeBox(size, size, H, FreeCAD.Vector(-r_outer, -r_outer, 0))
                    # 垂直エッジにコーナーRを適用
                    vertical_edges = [e for e in box.Edges if abs((e.BoundBox.ZMax - e.BoundBox.ZMin) - H) < 0.01]
                    if vertical_edges:
                        try: box = box.makeFillet(corner_r, vertical_edges)
                        except Exception: pass
                    base_solid = apply_outer_fillet(box, 1.2)


                # ---------------------------------------------------------
                # 2. 中の模様（カッター）の計算
                # ---------------------------------------------------------
                bar.update(40, translate_text("模様のくり抜きカッターを計算中...", lang))
                
                cutters = []
                z_cut = base_h
                h_cut = H - base_h + 1.0 # 確実に上面を貫通させるためのマージン

                # 内側（模様を彫る領域）の判定関数
                def is_inside(x, y, r_hole):
                    if shape_idx == 0:
                        return math.sqrt(x*x + y*y) + r_hole < r_inner
                    else:
                        inner_corner_r = max(corner_r - rim_w, 0.0)
                        if abs(x) + r_hole > r_inner or abs(y) + r_hole > r_inner:
                            return False
                        corner_cx = r_inner - inner_corner_r
                        corner_cy = r_inner - inner_corner_r
                        if abs(x) > corner_cx and abs(y) > corner_cy:
                            dist = math.sqrt((abs(x) - corner_cx)**2 + (abs(y) - corner_cy)**2)
                            if dist + r_hole > inner_corner_r:
                                return False
                        return True

                # [A] ハチの巣状 (Honeycomb / 六角柱)
                if pattern_idx == 0:
                    R_hex = 4.0
                    wall = 1.5
                    D = math.sqrt(3) * R_hex + wall # セル間距離
                    dx = D * math.sqrt(3) / 2.0
                    dy = D
                    
                    N_col = int(r_outer / dx) + 2
                    N_row = int(r_outer / dy) + 2
                    for col in range(-N_col, N_col+1):
                        for row in range(-N_row, N_row+1):
                            x = col * dx
                            y = row * dy
                            if col % 2 != 0:
                                y += dy / 2.0
                            
                            if is_inside(x, y, R_hex):
                                pts = []
                                for i in range(7):
                                    ang = math.radians(60 * i) # 頂点が左右を向く六角形
                                    pts.append(FreeCAD.Vector(x + R_hex * math.cos(ang), y + R_hex * math.sin(ang), z_cut))
                                wire = Part.makePolygon(pts)
                                hex_solid = Part.Face(wire).extrude(FreeCAD.Vector(0,0,h_cut))
                                cutters.append(hex_solid)

                # [B] 水玉 (Polka Dot / 円柱)
                elif pattern_idx == 1:
                    R_dot = 3.5
                    wall = 2.5
                    D = 2 * R_dot + wall
                    dx = D
                    dy = D * math.sqrt(3) / 2.0 # 千鳥配置
                    
                    N_col = int(r_outer / dx) + 2
                    N_row = int(r_outer / dy) + 2
                    for row in range(-N_row, N_row+1):
                        for col in range(-N_col, N_col+1):
                            x = col * dx
                            if row % 2 != 0:
                                x += dx / 2.0
                            y = row * dy
                            
                            if is_inside(x, y, R_dot):
                                cyl = Part.makeCylinder(R_dot, h_cut, FreeCAD.Vector(x, y, z_cut), FreeCAD.Vector(0,0,1))
                                cutters.append(cyl)

                # [C] 格子状 (Grid / 四角柱)
                elif pattern_idx == 2:
                    S_sq = 6.0
                    wall = 2.0
                    D = S_sq + wall
                    r_sq = S_sq * math.sqrt(2) / 2.0 # 外接円半径による厳密な領域判定
                    
                    N = int(r_outer / D) + 2
                    for row in range(-N, N+1):
                        for col in range(-N, N+1):
                            x = col * D
                            y = row * D
                            
                            if is_inside(x, y, r_sq):
                                box = Part.makeBox(S_sq, S_sq, h_cut, FreeCAD.Vector(x - S_sq/2.0, y - S_sq/2.0, z_cut))
                                cutters.append(box)


                # ---------------------------------------------------------
                # 3. 結合とブーリアン演算 (Cut)
                # ---------------------------------------------------------
                if cutters:
                    bar.update(65, translate_text("カッター群を複合化中...", lang))
                    cutter_compound = Part.makeCompound(cutters)
                    
                    bar.update(80, translate_text("模様をくり抜き中（ブーリアンCut）...", lang))
                    final_shape = base_solid.cut(cutter_compound)
                else:
                    final_shape = base_solid

                bar.update(90, translate_text("不要なシーム線を消去して最適化中...", lang))
                final_shape = final_shape.removeSplitter()

                label_name = "Coaster_" + ("Round" if shape_idx == 0 else "Square")
                obj = doc.addObject("Part::Feature", label_name)
                obj.Shape = final_shape
                obj.ViewObject.DisplayMode = "Flat Lines"

                # 模様に合わせたカラー設定
                if pattern_idx == 0:
                    obj.ViewObject.ShapeColor = (0.90, 0.75, 0.20) # ハニカム（ミツバチイエロー系）
                elif pattern_idx == 1:
                    obj.ViewObject.ShapeColor = (0.45, 0.75, 0.90) # 水玉（爽やかな水色）
                else:
                    obj.ViewObject.ShapeColor = (0.75, 0.55, 0.40) # 格子（木材/コルク系）
                    
                if hasattr(obj.ViewObject, "Shininess"):
                    obj.ViewObject.Shininess = 0.5

                doc.commitTransaction()
                doc.recompute()

                bar.update(100, translate_text("画面を更新しています...", lang))
                if FreeCADGui.activeView():
                    FreeCADGui.activeView().viewAxometric()
                    FreeCADGui.activeView().fitAll()

        except Exception as e:
            doc.abortTransaction()
            err_title = "Error" if lang == "English" else "エラー"
            err_msg = f"An error occurred during processing:\n{str(e)}" if lang == "English" else f"処理中にエラーが発生しました:\n{str(e)}"
            QtWidgets.QMessageBox.critical(None, err_title, err_msg)

# ワークベンチへのコマンド登録
FreeCADGui.addCommand('Ring_MakeCoaster', Tool_MakeCoaster())