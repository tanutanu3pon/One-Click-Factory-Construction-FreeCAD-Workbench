# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part
from PySide import QtWidgets
import math

# ?? Core/Progress.py から進捗マネージャーをインポート
import Core.Progress as Progress

class Tool_Heart:
    def GetResources(self):
        current_dir = os.path.dirname(__file__)
        ring_dir = os.path.dirname(current_dir)
        icon_path = os.path.join(ring_dir, "icons", "heart.png").replace('\\', '/')
        
        return {
            'Pixmap'  : icon_path,
            'MenuText': "ハート作成",
            'ToolTip' : "数式曲線から、紐通し穴付きのハート形状を作ります（進捗窓付き）"
        }

    def Activated(self):
        # 1. 横幅の入力
        w, ok1 = QtWidgets.QInputDialog.getDouble(None, "ハート設計", "横幅の目安 (mm):", 15.0, 5.0, 100.0, 1)
        if not ok1: return
        
        # 2. 厚みの入力
        t, ok2 = QtWidgets.QInputDialog.getDouble(None, "ハート設計", "厚み (mm):", 3.0, 0.5, 20.0, 1)
        if not ok2: return

        # 3. ふっくらさせるかどうかの選択
        items = ["フラット (単純押し出し)", "ふっくら (ぷっくりさせる)"]
        item, ok3 = QtWidgets.QInputDialog.getItem(None, "形状選択", "ハートのタイプ:", items, 1, False)
        if not ok3: return
        
        is_puffy = (item == "ふっくら (ぷっくりさせる)")

        # 4. 紐通し用の穴を設けるかどうかの選択窓
        hole_items = ["穴を設ける", "穴を設けない"]
        hole_choice, ok4 = QtWidgets.QInputDialog.getItem(None, "ハート設計", "紐通し穴の設定:", hole_items, 0, False)
        if not ok4: return
        
        has_hole = (hole_choice == "穴を設ける")
        r_hole = 0.8 # デフォルト値

        # 5. 穴を設ける場合のみ、穴の大きさを指定する窓を出す
        if has_hole:
            max_hole_r = max(0.5, w * 0.12)
            r_hole, ok5 = QtWidgets.QInputDialog.getDouble(None, "ハート設計", "穴の半径 (mm):", 0.8, 0.2, max_hole_r, 2)
            if not ok5: return

        # ==========================================
        # ? 【指示を出すだけ】Coreの窓コントロールを起動！
        # ==========================================
        bar = Progress.ProgressManager()
        bar.start(title="ハートモデル生成", initial_text="数式からハートの輪郭を計算中...")

        # ここで分岐先に「進捗マネージャー(bar)」をバトンタッチして渡す
        if is_puffy:
            self._create_puffy_heart(w, t, has_hole, r_hole, bar)
        else:
            self._create_flat_heart(w, t, has_hole, r_hole, bar)

    def _get_heart_points(self, scale, steps=60):
        """ハート方程式に基づいてXY平面上の点群を生成する共通関数"""
        pts = []
        for i in range(steps):
            angle = 2 * math.pi * i / steps
            x = 16 * math.pow(math.sin(angle), 3)
            y = 13 * math.cos(angle) - 5 * math.cos(2*angle) - 2 * math.cos(3*angle) - math.cos(4*angle)
            pts.append(FreeCAD.Vector(x * scale, y * scale, 0))
        pts.append(pts[0])
        return pts


    def _create_flat_heart(self, w, t, has_hole, r_hole, bar):
        """【独立プログラム1】普通の押し下げ（押し出し）ハートを作る"""
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
        scale = w / 32.0 
        pts = self._get_heart_points(scale)
        mid_wire = Part.makePolygon(pts)
        
        # --- 30% 完了 ---
        bar.update(30, "ハートの輪郭面を生成中...")
        face = Part.makeFace(mid_wire)
        
        # --- 55% 完了 ---
        bar.update(55, "ソリッドに押し出し（Extrude）中...")
        heart_shape = face.extrude(FreeCAD.Vector(0, 0, t))
        heart_shape = heart_shape.removeSplitter()
        
        # 穴あけ処理
        if has_hole:
            # --- 75% 完了 ---
            bar.update(75, "紐通し穴用の円柱を減算（Cut）中...")
            bbox = heart_shape.BoundBox
            hole_x = (bbox.XMin + bbox.Center.x) / 2.0
            hole_y = bbox.YMax - (bbox.YLength * 0.25)
            
            hole_cyl = Part.makeCylinder(r_hole, t + 4.0)
            hole_cyl.translate(FreeCAD.Vector(hole_x, hole_y, -2.0))
            heart_shape = heart_shape.cut(hole_cyl)

        # --- 90% 完了 ---
        bar.update(90, "FreeCADオブジェクトへハートデータを登録中...")
        obj = doc.addObject("Part::Feature", "Heart_Flat")
        obj.Shape = heart_shape
        obj.ViewObject.ShapeColor = (1.0, 0.4, 0.5)
        obj.ViewObject.DisplayMode = "Flat Lines"
        
        # ==========================================
        # ?? 【最重要】最後に100%にして、しっかり閉じる
        # ==========================================
        bar.update(100, "画面を更新しています...")
        bar.close()

        doc.recompute()
        FreeCADGui.activeView().fitAll()


    def _create_puffy_heart(self, w, t, has_hole, r_hole, bar):
        """【独立プログラム2】ふっくらしたハートを作る"""
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
        scale = w / 32.0 
        pts = self._get_heart_points(scale)
        mid_wire = Part.makePolygon(pts)
        
        # ロフトによるぷっくり形状生成
        bbox_wire = mid_wire.BoundBox
        center = bbox_wire.Center
        
        top_pt = FreeCAD.Vector(center.x, center.y, t / 2.0)
        bot_pt = FreeCAD.Vector(center.x, center.y, -t / 2.0)
        
        top_vertex = Part.Vertex(top_pt)
        bot_vertex = Part.Vertex(bot_pt)
        
        # --- 40% 完了（ロフト演算は非常に重いため、ここを丁寧に通知します）
        bar.update(40, "複雑な曲面を接合中（ロフト立体化）...")
        heart_shape = Part.makeLoft([bot_vertex, mid_wire, top_vertex], True)
        heart_shape.translate(FreeCAD.Vector(0, 0, t / 2.0))
        heart_shape = heart_shape.removeSplitter()
        
        # 穴あけ処理
        if has_hole:
            # --- 75% 完了 ---
            bar.update(75, "紐通し穴用の円柱を減算（Cut）中...")
            hole_x = -8.0 * scale
            hole_y = 4.0 * scale
            
            hole_cyl = Part.makeCylinder(r_hole, t + 4.0)
            hole_cyl.translate(FreeCAD.Vector(hole_x, hole_y, -2.0))
            heart_shape = heart_shape.cut(hole_cyl)

        # --- 90% 完了 ---
        bar.update(90, "FreeCADオブジェクトへハートデータを登録中...")
        obj = doc.addObject("Part::Feature", "Heart_Puffy")
        obj.Shape = heart_shape
        obj.ViewObject.ShapeColor = (1.0, 0.4, 0.5)
        obj.ViewObject.DisplayMode = "Flat Lines"
        
        # ==========================================
        # ?? 【最重要】最後に100%にして、しっかり閉じる
        # ==========================================
        bar.update(100, "画面を更新しています...")
        bar.close()

        doc.recompute()
        FreeCADGui.activeView().fitAll()

# ワークベンチへの登録
FreeCADGui.addCommand('Ring_Heart', Tool_Heart())