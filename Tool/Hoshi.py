# -*- coding: utf-8 -*-
import os
import math
import FreeCAD
import FreeCADGui
import Part

from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedInputDialog, translate_text
from Core.Language import get_language

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
        lang = get_language()

        r, ok1 = TranslatedInputDialog.getDouble(None, "星設計", "外側の半径 (mm):", 10.0, 5.0, 100.0, 1)
        if not ok1: return
        t, ok2 = TranslatedInputDialog.getDouble(None, "星設計", "全体の厚み (mm):", 4.0, 1.0, 30.0, 1)
        if not ok2: return

        # 1. 星のスタイル選択（シャープ / ふっくら）
        style_items = ["シャープ (標準)", "ふっくら (ぷっくり丸型)"]
        style_choice, ok_style = TranslatedInputDialog.getItem(None, "星設計", "星のスタイル:", style_items, 0, False)
        if not ok_style: return

        trans_style_items = [translate_text(it, lang) for it in style_items]
        if style_choice in style_items:
            is_puffy = (style_items.index(style_choice) == 1)
        elif style_choice in trans_style_items:
            is_puffy = (trans_style_items.index(style_choice) == 1)
        else:
            is_puffy = False

        has_hole = False
        r_hole = 0.8

        # 2. 穴の設定（「ふっくら」の場合はダイアログを出さず穴なし固定）
        if not is_puffy:
            hole_items = ["穴を設ける", "穴を設けない"]
            hole_choice, ok3 = TranslatedInputDialog.getItem(None, "星設計", "紐通し穴の設定:", hole_items, 0, False)
            if not ok3: return
            
            trans_hole_items = [translate_text(it, lang) for it in hole_items]
            if hole_choice in hole_items:
                has_hole = (hole_items.index(hole_choice) == 0)
            elif hole_choice in trans_hole_items:
                has_hole = (trans_hole_items.index(hole_choice) == 0)
            else:
                has_hole = True

            if has_hole:
                max_hole_r = max(0.5, r * 0.15)
                r_hole, ok4 = TranslatedInputDialog.getDouble(None, "星設計", "穴の半径 (mm):", 0.8, 0.2, max_hole_r, 2)
                if not ok4: return

        self.create_hoshi(r, t, is_puffy, has_hole, r_hole, lang)

    def create_hoshi(self, r_out, t, is_puffy, has_hole, r_hole, lang):
        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("星モデル生成", lang), initial_text=translate_text("頂点座標を計算中...", lang))

            doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
            
            n = 5
            # ふっくらの場合は内径を太くして谷を浅く設定
            r_in = r_out * 0.50 if is_puffy else r_out * 0.382
            half_t = t / 2.0
            
            pts = []
            for i in range(n * 2):
                radius = r_out if i % 2 == 0 else r_in
                angle = math.pi / 2 + i * math.pi / n
                pts.append(FreeCAD.Vector(radius * math.cos(angle), radius * math.sin(angle), 0))
                
            top_v = FreeCAD.Vector(0, 0, half_t)
            bot_v = FreeCAD.Vector(0, 0, -half_t)
            
            bar.update(30, translate_text("星の3Dサーフェス面を計算中...", lang))

            faces = []
            total_steps = n * 2
            
            for i in range(total_steps):
                p1 = pts[i]
                p2 = pts[(i + 1) % (total_steps)]
                faces.append(Part.makeFace(Part.makePolygon([p1, p2, top_v, p1])))
                faces.append(Part.makeFace(Part.makePolygon([p2, p1, bot_v, p2])))
                
                loop_percent = int(30 + (35 * (i / total_steps)))
                bar.update(loop_percent, translate_text("ポリゴンフェイスを構築中...", lang))
                
            bar.update(70, translate_text("面を縫い合わせてソリッド立体化中...", lang))
            star_solid = Part.makeSolid(Part.makeShell(faces))

            # ふっくらスタイルの場合、先端エッジにフィレットを適用して丸みを持たせる
            if is_puffy:
                bar.update(78, translate_text("先端とエッジの角丸（フィレット）加工中...", lang))
                fillet_edges = []
                for e in star_solid.Edges:
                    p1 = e.Vertexes[0].Point
                    p2 = e.Vertexes[1].Point
                    dist1 = math.hypot(p1.x, p1.y)
                    dist2 = math.hypot(p2.x, p2.y)
                    if abs(dist1 - r_out) < 0.01 or abs(dist2 - r_out) < 0.01:
                        fillet_edges.append(e)
                
                if fillet_edges:
                    try:
                        fillet_r = min(r_out * 0.18, half_t * 0.6)
                        star_solid = star_solid.makeFillet(fillet_r, fillet_edges)
                    except Exception:
                        try:
                            fillet_r = min(r_out * 0.10, half_t * 0.4)
                            star_solid = star_solid.makeFillet(fillet_r, fillet_edges)
                        except Exception:
                            pass

            if has_hole:
                bar.update(85, translate_text("上部エッジ付近の紐通し穴をくり抜き（Cut）中...", lang))
                hole_y = r_out * 0.72
                hole_x = 0.0
                
                hole_cyl = Part.makeCylinder(r_hole, t + 4.0)
                hole_cyl.translate(FreeCAD.Vector(hole_x, hole_y, -half_t - 2.0))
                star_solid = star_solid.cut(hole_cyl)
            else:
                bar.update(85, translate_text("形状データをクリーニング中...", lang))

            bar.update(92, translate_text("不要な境界線を消去して最適化中...", lang))
            star_solid = star_solid.removeSplitter()

            bar.update(95, translate_text("FreeCADオブジェクトへ登録中...", lang))
            label = "Hoshi_Puffy" if is_puffy else "Hoshi_Sharp"
            obj = doc.addObject("Part::Feature", label)
            obj.Shape = star_solid
            obj.ViewObject.ShapeColor = (1.0, 0.85, 0.25) if is_puffy else (1.0, 0.9, 0.2)
            obj.ViewObject.DisplayMode = "Flat Lines"
            
            bar.update(100, translate_text("画面を更新しています...", lang))

            doc.recompute()
            FreeCADGui.activeView().fitAll()

FreeCADGui.addCommand('Ring_Hoshi', Tool_Hoshi())