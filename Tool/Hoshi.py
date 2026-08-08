# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part
from Core.QtCompat import QtWidgets, QtGui, QtCore
import math
import Core.Progress as Progress

class Tool_Hoshi:
    def GetResources(self):
        current_dir = os.path.dirname(__file__)
        ring_dir = os.path.dirname(current_dir)
        icon_path = os.path.join(ring_dir, "icons", "hoshi.png").replace('\\', '/')
        
        return {
            'Pixmap'  : icon_path,
            'MenuText': "立体星作成",
            'ToolTip' : "上部に紐通し穴を設けた、中心が盛り上がった立体的な星を作ります（進捗窓付き）"
        }

    def Activated(self):
        r, ok1 = QtWidgets.QInputDialog.getDouble(None, "星設計", "外側の半径 (mm):", 10.0, 5.0, 100.0, 1)
        if not ok1: return
        t, ok2 = QtWidgets.QInputDialog.getDouble(None, "星設計", "全体の厚み (mm):", 4.0, 1.0, 30.0, 1)
        if not ok2: return

        items = ["穴を設ける", "穴を設けない"]
        hole_choice, ok3 = QtWidgets.QInputDialog.getItem(None, "星設計", "紐通し穴の設定:", items, 0, False)
        if not ok3: return
        has_hole = (items.index(hole_choice) == 0)
        
        r_hole = 0.8

        if has_hole:
            max_hole_r = max(0.5, r * 0.15)
            r_hole, ok4 = QtWidgets.QInputDialog.getDouble(None, "星設計", "穴の半径 (mm):", 0.8, 0.2, max_hole_r, 2)
            if not ok4: return

        self.create_hoshi(r, t, has_hole, r_hole)

    def create_hoshi(self, r_out, t, has_hole, r_hole):
        with Progress.ProgressManager() as bar:
            bar.start(title="星モデル生成", initial_text="頂点座標を計算中...")

            doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
            
            n = 5
            r_in = r_out * 0.382
            half_t = t / 2.0
            
            pts = []
            for i in range(n * 2):
                radius = r_out if i % 2 == 0 else r_in
                angle = math.pi / 2 + i * math.pi / n
                pts.append(FreeCAD.Vector(radius * math.cos(angle), radius * math.sin(angle), 0))
                
            top_v = FreeCAD.Vector(0, 0, half_t)
            bot_v = FreeCAD.Vector(0, 0, -half_t)
            
            bar.update(30, "星の3Dサーフェス面を計算中...")

            faces = []
            total_steps = n * 2
            
            for i in range(total_steps):
                p1 = pts[i]
                p2 = pts[(i + 1) % (total_steps)]
                faces.append(Part.makeFace(Part.makePolygon([p1, p2, top_v, p1])))
                faces.append(Part.makeFace(Part.makePolygon([p2, p1, bot_v, p2])))
                
                loop_percent = int(30 + (35 * (i / total_steps)))
                bar.update(loop_percent, "ポリゴンフェイスを構築中...")
                
            bar.update(70, "面を縫い合わせてソリッド立体化中...")
            star_solid = Part.makeSolid(Part.makeShell(faces))

            if has_hole:
                bar.update(80, "上部エッジ付近の紐通し穴をくり抜き（Cut）中...")
                hole_y = r_out * 0.72
                hole_x = 0.0
                
                hole_cyl = Part.makeCylinder(r_hole, t + 4.0)
                hole_cyl.translate(FreeCAD.Vector(hole_x, hole_y, -half_t - 2.0))
                star_solid = star_solid.cut(hole_cyl)
            else:
                bar.update(80, "形状データをクリーニング中...")

            bar.update(90, "不要な境界線を消去して最適化中...")
            star_solid = star_solid.removeSplitter()

            bar.update(95, "FreeCADオブジェクトへ登録中...")
            obj = doc.addObject("Part::Feature", "Hoshi_Charm")
            obj.Shape = star_solid
            obj.ViewObject.ShapeColor = (1.0, 0.9, 0.2)
            obj.ViewObject.DisplayMode = "Flat Lines"
            
            bar.update(100, "画面を更新しています...")

            doc.recompute()
            FreeCADGui.activeView().fitAll()

FreeCADGui.addCommand('Ring_Hoshi', Tool_Hoshi())