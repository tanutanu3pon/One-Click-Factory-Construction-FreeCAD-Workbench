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
        lang = get_language()

        # 【修正】QtWidgets.QInputDialog から TranslatedInputDialog へ差し替え
        w, ok1 = TranslatedInputDialog.getDouble(None, "ハート設計", "横幅の目安 (mm):", 15.0, 5.0, 100.0, 1)
        if not ok1: return
        
        t, ok2 = TranslatedInputDialog.getDouble(None, "ハート設計", "厚み (mm):", 3.0, 0.5, 20.0, 1)
        if not ok2: return

        items = ["フラット (単純押し出し)", "ふっくら (ぷっくりさせる)"]
        item, ok3 = TranslatedInputDialog.getItem(None, "形状選択", "ハートのタイプ:", items, 1, False)
        if not ok3: return

        trans_items = [translate_text(it, lang) for it in items]

        if item in items:
            is_puffy = (items.index(item) == 1)
        elif item in trans_items:
            is_puffy = (trans_items.index(item) == 1)
        else:
            is_puffy = True

        hole_items = ["穴を設ける", "穴を設けない"]
        hole_choice, ok4 = TranslatedInputDialog.getItem(None, "ハート設計", "紐通し穴の設定:", hole_items, 0, False)
        if not ok4: return

        trans_hole_items = [translate_text(it, lang) for it in hole_items]
        if hole_choice in hole_items:
            has_hole = (hole_items.index(hole_choice) == 0)
        elif hole_choice in trans_hole_items:
            has_hole = (trans_hole_items.index(hole_choice) == 0)
        else:
            has_hole = True
        
        r_hole = 0.8

        if has_hole:
            max_hole_r = max(0.5, w * 0.12)
            r_hole, ok5 = TranslatedInputDialog.getDouble(None, "ハート設計", "穴の半径 (mm):", 0.8, 0.2, max_hole_r, 2)
            if not ok5: return

        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("ハートモデル生成", lang), initial_text=translate_text("数式からハートの輪郭を計算中...", lang))

            if is_puffy:
                self._create_puffy_heart(w, t, has_hole, r_hole, bar, lang)
            else:
                self._create_flat_heart(w, t, has_hole, r_hole, bar, lang)

    def _get_heart_points(self, scale, steps=60):
        pts = []
        for i in range(steps):
            angle = 2 * math.pi * i / steps
            x = 16 * math.pow(math.sin(angle), 3)
            y = 13 * math.cos(angle) - 5 * math.cos(2*angle) - 2 * math.cos(3*angle) - math.cos(4*angle)
            pts.append(FreeCAD.Vector(x * scale, y * scale, 0))
        pts.append(pts[0])
        return pts

    def _create_flat_heart(self, w, t, has_hole, r_hole, bar, lang):
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
        scale = w / 32.0 
        pts = self._get_heart_points(scale)
        mid_wire = Part.makePolygon(pts)
        
        bar.update(30, translate_text("ハートの輪郭面を生成中...", lang))
        face = Part.makeFace(mid_wire)
        
        bar.update(55, translate_text("ソリッドに押し出し（Extrude）中...", lang))
        heart_shape = face.extrude(FreeCAD.Vector(0, 0, t))
        heart_shape = heart_shape.removeSplitter()
        
        if has_hole:
            bar.update(75, translate_text("紐通し穴用の円柱を減算（Cut）中...", lang))
            bbox = heart_shape.BoundBox
            hole_x = (bbox.XMin + bbox.Center.x) / 2.0
            hole_y = bbox.YMax - (bbox.YLength * 0.25)
            
            hole_cyl = Part.makeCylinder(r_hole, t + 4.0)
            hole_cyl.translate(FreeCAD.Vector(hole_x, hole_y, -2.0))
            heart_shape = heart_shape.cut(hole_cyl)

        bar.update(90, translate_text("FreeCADオブジェクトへハートデータを登録中...", lang))
        obj = doc.addObject("Part::Feature", "Heart_Flat")
        obj.Shape = heart_shape
        obj.ViewObject.ShapeColor = (1.0, 0.4, 0.5)
        obj.ViewObject.DisplayMode = "Flat Lines"
        
        bar.update(100, translate_text("画面を更新しています...", lang))
        doc.recompute()
        FreeCADGui.activeView().fitAll()

    def _create_puffy_heart(self, w, t, has_hole, r_hole, bar, lang):
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
        scale = w / 32.0 
        pts = self._get_heart_points(scale)
        mid_wire = Part.makePolygon(pts)
        
        bbox_wire = mid_wire.BoundBox
        center = bbox_wire.Center
        
        top_pt = FreeCAD.Vector(center.x, center.y, t / 2.0)
        bot_pt = FreeCAD.Vector(center.x, center.y, -t / 2.0)
        
        top_vertex = Part.Vertex(top_pt)
        bot_vertex = Part.Vertex(bot_pt)
        
        bar.update(40, translate_text("複雑な曲面を接合中（ロフト立体化）...", lang))
        heart_shape = Part.makeLoft([bot_vertex, mid_wire, top_vertex], True)
        heart_shape.translate(FreeCAD.Vector(0, 0, t / 2.0))
        heart_shape = heart_shape.removeSplitter()
        
        if has_hole:
            bar.update(75, translate_text("紐通し穴用の円柱を減算（Cut）中...", lang))
            hole_x = -8.0 * scale
            hole_y = 4.0 * scale
            
            hole_cyl = Part.makeCylinder(r_hole, t + 4.0)
            hole_cyl.translate(FreeCAD.Vector(hole_x, hole_y, -2.0))
            heart_shape = heart_shape.cut(hole_cyl)

        bar.update(90, translate_text("FreeCADオブジェクトへハートデータを登録中...", lang))
        obj = doc.addObject("Part::Feature", "Heart_Puffy")
        obj.Shape = heart_shape
        obj.ViewObject.ShapeColor = (1.0, 0.4, 0.5)
        obj.ViewObject.DisplayMode = "Flat Lines"
        
        bar.update(100, translate_text("画面を更新しています...", lang))
        doc.recompute()
        FreeCADGui.activeView().fitAll()

FreeCADGui.addCommand('Ring_Heart', Tool_Heart())