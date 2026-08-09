# -*- coding: utf-8 -*-
import os
import math
import FreeCAD
import FreeCADGui
import Part

# 【修正】絶対インポートで安全にCoreモジュールを読み込む
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedInputDialog, translate_text
from Core.Language import get_language

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
        lang = get_language()

        sizes = [str(i) for i in range(1, 31)]
        # 【修正】QtWidgets.QInputDialog から TranslatedInputDialog へ差し替え
        size_str, ok1 = TranslatedInputDialog.getItem(None, "サイズ選択", "リングサイズ (号):", sizes, 9, False)
        if not ok1: return
        size_num = int(size_str)

        types = ["フラット", "セミラウンド", "ラウンド"]
        ring_type, ok2 = TranslatedInputDialog.getItem(None, "形状選択", "断面形状:", types, 1, False)
        if not ok2: return

        trans_types = [translate_text(t, lang) for t in types]
        
        if ring_type in types:
            type_idx = types.index(ring_type)
        elif ring_type in trans_types:
            type_idx = trans_types.index(ring_type)
        else:
            type_idx = 1

        width, ok3 = TranslatedInputDialog.getDouble(None, "寸法指定", "リングの幅 (mm):", 2.5, 1.0, 10.0, 1)
        if not ok3: return
        thickness, ok4 = TranslatedInputDialog.getDouble(None, "寸法指定", "地金の厚み (mm):", 1.5, 0.5, 5.0, 1)
        if not ok4: return

        angle, ok5 = TranslatedInputDialog.getDouble(None, "角度指定", "回転角度 (度, 1~360):", 360.0, 1.0, 360.0, 1)
        if not ok5: return

        self.create_correct_ring(size_num, type_idx, width, thickness, angle, lang)

    def create_correct_ring(self, size_num, type_idx, width, thickness, angle, lang):
        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("リングモデル生成", lang), initial_text=translate_text("JIS規格の指輪サイズを計算中...", lang))

            doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
            
            inner_r = self.get_jis_size(size_num)
            h = width / 2.0
            
            bar.update(25, translate_text("断面のワイヤー（輪郭線）を生成中...", lang))

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

            bar.update(55, translate_text("断面からソリッド（面）を構成中...", lang))
            face = Part.Face(profile)
            
            msg_revolve = f"Revolving {angle} deg around Z axis..." if lang == "English" else f"Z軸を中心に {angle}度 回転（Revolve）させて立体化中..."
            bar.update(75, msg_revolve)
            ring_shape = face.revolve(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), angle)

            bar.update(90, translate_text("FreeCADオブジェクトへリングデータを登録中...", lang))
            type_labels = ["Flat", "SemiRound", "Round"]
            obj = doc.addObject("Part::Feature", f"Size{size_num}_{type_labels[type_idx]}_{angle}deg")
            obj.Shape = ring_shape
            
            bar.update(100, translate_text("画面を更新しています...", lang))

            doc.recompute()
            FreeCADGui.activeView().viewAxometric()
            FreeCADGui.activeView().fitAll()

FreeCADGui.addCommand('Ring_MakeRing', Tool_MakeRing())