# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part
from Core.QtCompat import QtWidgets, QtGui, QtCore

# ?? Core/Progress.py から【決定版】の進捗マネージャーをインポート
import Core.Progress as Progress

class Tool_MakeMugSimple:
    def GetResources(self):
        current_dir = os.path.dirname(__file__)
        ring_dir = os.path.dirname(current_dir)
        icon_path = os.path.join(ring_dir, "icons", "mug.png").replace('\\', '/')
        return {
            'Pixmap'  : icon_path,
            'MenuText': "爆速マグカップ作成",
            'ToolTip' : "内外面の角を丸め、ゴミが溜まらない実用的なマグカップを生成します（進捗窓付き）"
        }

    def Activated(self):
        # 1. 外径と高さの指定
        h, ok1 = QtWidgets.QInputDialog.getDouble(None, "設計", "カップの高さ (mm):", 90.0, 10.0, 300.0, 1)
        if not ok1: return
        d, ok2 = QtWidgets.QInputDialog.getDouble(None, "設計", "カップの外径 (mm):", 80.0, 10.0, 200.0, 1)
        if not ok2: return

        # 2. 肉厚の指定
        w, ok3 = QtWidgets.QInputDialog.getDouble(None, "設計", "壁の肉厚 (mm):", 4.0, 1.0, 20.0, 1)
        if not ok3: return

        r_outer = d / 2.0
        r_inner = r_outer - w

        self.create_mug(h, d, w, r_outer, r_inner)

    def create_mug(self, h, d, w, r_outer, r_inner):
        # ==========================================
        # ? 【指示を出すだけ】最新のクラス方式で窓をスタート！
        # ==========================================
        bar = Progress.ProgressManager()
        bar.start(title="マグカップ生成", initial_text="コップの基本形状を計算中...")

        doc = FreeCAD.activeDocument() or FreeCAD.newDocument()

        # ==========================================
        # 【ステップ1】 2つの円柱の減算処理でコップを作る
        # ==========================================
        outer_cyl = Part.makeCylinder(r_outer, h)
        inner_cyl = Part.makeCylinder(r_inner, h, FreeCAD.Vector(0, 0, w))
        body_shape = outer_cyl.cut(inner_cyl)

        # ==========================================
        # 【ステップ2】 各種フィレット処理（取っ手結合前）
        # ==========================================
        bar.update(20, "コップのエッジ構造を解析中...")

        bottom_edges = []      
        rim_outer_edges = []   
        inner_floor_edges = [] 
        
        fillet_r_bottom = w * 0.8     
        fillet_r_rim = w * 0.3        
        fillet_r_inner = w * 0.5      

        all_edges = body_shape.Edges
        total_edges = len(all_edges)

        for idx, edge in enumerate(all_edges):
            try:
                curve = edge.Curve
                if isinstance(curve, Part.Circle):
                    center_z = curve.Center.z
                    radius = curve.Radius
                    
                    if abs(center_z) < 0.001 and abs(radius - r_outer) < 0.001:
                        bottom_edges.append(edge)
                        
                    if abs(center_z - h) < 0.001 and abs(radius - r_outer) < 0.001:
                        rim_outer_edges.append(edge)

                    if abs(center_z - w) < 0.001 and abs(radius - r_inner) < 0.001:
                        inner_floor_edges.append(edge)
            except:
                continue

            # ?? 4本に1回、進捗窓の％を滑らかに進める（20% ? 60% の間）
            if idx % 4 == 0 and total_edges > 0:
                loop_percent = int(20 + (40 * (idx / total_edges)))
                bar.update(loop_percent, "丸める角の位置を特定中...")

        # --- 65% 完了 ---
        bar.update(65, "特定した内外の角を丸め加工（フィレット）中...")

        if bottom_edges:
            try: body_shape = body_shape.makeFillet(fillet_r_bottom, bottom_edges)
            except: pass

        if rim_outer_edges:
            try: body_shape = body_shape.makeFillet(fillet_r_rim, rim_outer_edges)
            except: pass

        if inner_floor_edges:
            try: body_shape = body_shape.makeFillet(fillet_r_inner, inner_floor_edges)
            except: pass

        # ==========================================
        # 【ステップ3】 取っ手（C型）を作って結合する
        # ==========================================
        bar.update(80, "C型取っ手をスイープ生成中...")

        handle_h = h * 0.6
        handle_w = r_outer * 0.5
        handle_r = w * 0.8
        z_center = h / 2.0

        p1 = FreeCAD.Vector(r_outer - 0.5, 0, z_center + handle_h / 2.0)
        p2 = FreeCAD.Vector(r_outer + handle_w, 0, z_center)
        p3 = FreeCAD.Vector(r_outer - 0.5, 0, z_center - handle_h / 2.0)

        arc = Part.Arc(p1, p2, p3)
        wire_path = Part.Wire([arc.toShape()])
        circle_profile = Part.makeCircle(handle_r, p1, FreeCAD.Vector(1, 0, 0))
        wire_profile = Part.Wire([Part.Edge(circle_profile)])
        
        handle_shape = wire_path.makePipeShell([wire_profile], True, False)

        # --- 90% 完了 ---
        bar.update(90, "コップ本体と取っ手を一体化中...")
        mug_shape = body_shape.fuse(handle_shape)
        mug_shape = mug_shape.removeSplitter()

        # ==========================================
        # 登録と描画
        # ==========================================
        obj = doc.addObject("Part::Feature", "Simple_Mug")
        obj.Shape = mug_shape
        obj.ViewObject.ShapeColor = (0.9, 0.9, 0.95)
        obj.ViewObject.DisplayMode = "Flat Lines"

        # ==========================================
        # ?? 【最重要】最後に100%にして、しっかり閉じる
        # ==========================================
        bar.update(100, "画面を更新しています...")
        bar.close()
        
        doc.recompute()
        FreeCADGui.activeView().fitAll()

# 登録
FreeCADGui.addCommand('Ring_Mug', Tool_MakeMugSimple())