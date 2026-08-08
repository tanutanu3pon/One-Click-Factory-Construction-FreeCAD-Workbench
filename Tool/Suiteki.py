# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part
import math
from Core.QtCompat import QtWidgets, QtGui, QtCore

# ?? Core/Progress.py を読み込めと指示
import Core.Progress as Progress

class Tool_Suiteki:
    def GetResources(self):
        current_dir = os.path.dirname(__file__)
        ring_dir = os.path.dirname(current_dir)
        icon_path = os.path.join(ring_dir, "icons", "suiteki.png").replace('\\', '/')
        return {
            'Pixmap'  : icon_path,
            'MenuText': "水滴ペンダント作成",
            'ToolTip' : "水滴形状のペンダントトップを生成します"
        }

    def Activated(self):
        r, ok1 = QtWidgets.QInputDialog.getDouble(None, "水滴設計", "基本半径 (mm):", 5.0, 1.0, 50.0, 1)
        if not ok1: return
        h, ok2 = QtWidgets.QInputDialog.getDouble(None, "水滴設計", "上部の長さ (mm):", 12.0, r, 100.0, 1)
        if not ok2: return
        hole_r, ok3 = QtWidgets.QInputDialog.getDouble(None, "水滴設計", "上部の穴の半径 (mm)\n※0で穴なし:", 1.0, 0.0, r, 1)
        if not ok3: return

        self.create_suiteki(r, h, hole_r)

    def create_suiteki(self, R, H, hole_r):
        # ==========================================
        # ? 【指示を出すだけ】
        # CoreのProgressManagerを呼び出して、窓をスタートさせます
        # ==========================================
        bar = Progress.ProgressManager()
        bar.start(title="水滴モデル生成", initial_text="下部（球体）を生成中...")

        doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
        
        # --- 1. 下部の生成 ---
        bottom_sphere = Part.makeSphere(R)

        # --- 2. 上部の生成 ---
        bar.update(10, "シュッと伸びる上部の断面曲線を計算中...")
        
        wires = []
        steps = 40
        for i in range(steps + 1):
            z = H * (i / steps)
            current_r = R * (1.0 - math.pow(z / H, 2))
            current_r = max(0.01, current_r)
            
            circle_edge = Part.makeCircle(current_r, FreeCAD.Vector(0, 0, z), FreeCAD.Vector(0, 0, 1))
            wires.append(Part.Wire([circle_edge]))
            
            # ?? 5回に1回、進捗窓の％を滑らかに進める（10% ? 50% の間）
            if i % 5 == 0:
                loop_percent = int(10 + (40 * (i / steps)))
                bar.update(loop_percent, "水滴の外郭スキンを計算中...")

        # --- 各種モデリング処理 ---
        bar.update(55, "断面を繋いでロフト化中...")
        top_loft = Part.makeLoft(wires, True)

        bar.update(70, "上部と下部を結合中...")
        suiteki_base = bottom_sphere.fuse(top_loft)

        if hole_r > 0:
            bar.update(85, "紐通し用バチカン穴をくり抜き中...")
            hole_z = max(R * 0.5, H - (hole_r * 2.5))
            hole_cyl = Part.makeCylinder(hole_r, R * 4, FreeCAD.Vector(-R * 2, 0, hole_z), FreeCAD.Vector(1, 0, 0))
            suiteki_final = suiteki_base.cut(hole_cyl)
        else:
            bar.update(85, "形状をクリーニング中...")
            suiteki_final = suiteki_base

        bar.update(95, "シーム（結合線）を消去して最適化中...")
        suiteki_final = suiteki_final.removeSplitter()

        # ドキュメントへの登録
        obj = doc.addObject("Part::Feature", "Suiteki")
        obj.Shape = suiteki_final
        obj.ViewObject.ShapeColor = (0.5, 0.8, 1.0) 
        obj.ViewObject.Transparency = 30  
        obj.ViewObject.DisplayMode = "Flat Lines"
        
        # ==========================================
        # ?? 【最重要】最後に必ず閉じて、画面のフリーズを解除
        # ==========================================
        bar.update(100, "画面を更新しています...")
        bar.close()

        doc.recompute()
        FreeCADGui.activeView().fitAll()

# コマンド登録
FreeCADGui.addCommand('Ring_Suiteki', Tool_Suiteki())