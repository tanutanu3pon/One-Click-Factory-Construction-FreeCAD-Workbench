# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part
import math
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress

class Tool_MakeRing:
    def GetResources(self):
        current_dir = os.path.dirname(__file__)
        ring_dir = os.path.dirname(current_dir)
        icon_path = os.path.join(ring_dir, "icons", "ring.png").replace('\\', '/')
        
        return {
            'Pixmap'  : icon_path,
            'MenuText': "指輪を精密設計",
            'ToolTip' : "断面を垂直に回転させてリングを作成します（進捗窓付き）"
        }

    def get_jis_size(self, size_num):
        inner_diameter = 13.0 + (size_num - 1) / 3.0
        return inner_diameter / 2.0

    def Activated(self):
        sizes = [str(i) for i in range(1, 31)]
        # QtGui -> QtWidgets に修正 (PySide6 互換)
        size_str, ok1 = QtWidgets.QInputDialog.getItem(None, "サイズ選択", "リングサイズ (号):", sizes, 9, False)
        if not ok1: return
        size_num = int(size_str)

        types = ["フラット", "セミラウンド", "ラウンド"]
        ring_type, ok2 = QtWidgets.QInputDialog.getItem(None, "形状選択", "断面形状:", types, 1, False)
        if not ok2: return
        type_idx = types.index(ring_type) # インデックス数値判定に修正

        width, ok3 = QtWidgets.QInputDialog.getDouble(None, "寸法指定", "リングの幅 (mm):", 2.5, 1.0, 10.0, 1)
        if not ok3: return
        thickness, ok4 = QtWidgets.QInputDialog.getDouble(None, "寸法指定", "地金の厚み (mm):", 1.5, 0.5, 5.0, 1)
        if not ok4: return

        angle, ok5 = QtWidgets.QInputDialog.getDouble(None, "角度指定", "回転角度 (度, 1~360):", 360.0, 1.0, 360.0, 1)
        if not ok5: return

        self.create_correct_ring(size_num, type_idx, width, thickness, angle)

    def create_correct_ring(self, size_num, type_idx, width, thickness, angle):
        with Progress.ProgressManager() as bar:
            bar.start(title="リングモデル生成", initial_text="JIS規格の指輪サイズを計算中...")

            doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
            
            inner_r = self.get_jis_size(size_num)
            h = width / 2.0
            
            bar.update(25, "断面のワイヤー（輪郭線）を生成中...")

            p1 = FreeCAD.Vector(inner_r, 0, -h)
            p2 = FreeCAD.Vector(inner_r + thickness, 0, -h)
            p3 = FreeCAD.Vector(inner_r + thickness, 0,  h)
            p4 = FreeCAD.Vector(inner_r, 0,  h)

            if type_idx == 0:  # フラット
                mid_inner = FreeCAD.Vector(inner_r - 0.15, 0, 0)
                arc_inner = Part.Arc(p4, mid_inner, p1).toShape()
                line_bottom = Part.makeLine(p1, p2)
                line_outer = Part.makeLine(p2, p3)
                line_top = Part.makeLine(p3, p4)
                profile = Part.Wire([line_bottom, line_outer, line_top, arc_inner])
            
            elif type_idx == 1:  # セミラウンド
                mid_outer = FreeCAD.Vector(inner_r + thickness + 0.25, 0, 0)
                arc_outer = Part.Arc(p2, mid_outer, p3).toShape()
                mid_inner = FreeCAD.Vector(inner_r - 0.2, 0, 0)
                arc_inner = Part.Arc(p4, mid_inner, p1).toShape()
                line_bottom = Part.makeLine(p1, p2)
                line_top = Part.makeLine(p3, p4)
                profile = Part.Wire([line_bottom, arc_outer, line_top, arc_inner])

            else:  # ラウンド
                mid_outer = FreeCAD.Vector(inner_r + thickness + 0.5, 0, 0)
                arc_outer = Part.Arc(p2, mid_outer, p3).toShape()
                mid_inner = FreeCAD.Vector(inner_r - 0.5, 0, 0)
                arc_inner = Part.Arc(p4, mid_inner, p1).toShape()
                line_bottom = Part.makeLine(p1, p2)
                line_top = Part.makeLine(p3, p4)
                profile = Part.Wire([line_bottom, arc_outer, line_top, arc_inner])

            bar.update(55, "断面からソリッド（面）を構成中...")
            face = Part.Face(profile)
            
            bar.update(75, f"Z軸を中心に {angle}度 回転（Revolve）させて立体化中...")
            ring_shape = face.revolve(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), angle)

            bar.update(90, "FreeCADオブジェクトへリングデータを登録中...")
            type_labels = ["Flat", "SemiRound", "Round"]
            obj = doc.addObject("Part::Feature", f"Size{size_num}_{type_labels[type_idx]}_{angle}deg")
            obj.Shape = ring_shape
            
            bar.update(100, "画面を更新しています...")

            doc.recompute()
            FreeCADGui.activeView().viewAxometric()
            FreeCADGui.activeView().fitAll()

FreeCADGui.addCommand('Ring_MakeRing', Tool_MakeRing())