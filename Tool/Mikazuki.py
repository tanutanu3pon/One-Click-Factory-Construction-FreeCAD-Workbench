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

class Tool_Mikazuki:
    def GetResources(self):
        current_dir = os.path.dirname(__file__)
        ring_dir = os.path.dirname(current_dir)
        icon_path = os.path.join(ring_dir, "icons", "mikazuki.png").replace('\\', '/')
        
        return {
            'Pixmap'  : icon_path, 
            'MenuText': "三日月チャーム作成",
            'ToolTip' : "2つの円柱の差分から、紐通し穴付きの美しい三日月形状を生成します（進捗窓付き）"
        }

    def Activated(self):
        lang = get_language()

        # 【修正】QtWidgets.QInputDialog から TranslatedInputDialog へ差し替え
        r_out, ok1 = TranslatedInputDialog.getDouble(None, "三日月設計", "外側の半径 (mm):", 10.0, 2.0, 100.0, 1)
        if not ok1: return
        
        r_in, ok2 = TranslatedInputDialog.getDouble(None, "三日月設計", "内側の半径 (mm):", 8.5, 1.0, r_out, 1)
        if not ok2: return

        offset, ok3 = TranslatedInputDialog.getDouble(None, "三日月設計", "中心のズレ (mm):", 4.0, 0.1, r_out, 1)
        if not ok3: return

        t, ok4 = TranslatedInputDialog.getDouble(None, "三日月設計", "厚み (mm):", 2.0, 0.5, 30.0, 1)
        if not ok4: return

        styles = ["標準 (シャープ)", "かわいい (角丸ぷっくり)"]
        style_choice, ok_style = TranslatedInputDialog.getItem(None, "デザイン選択", "三日月のスタイル:", styles, 0, False)
        if not ok_style: return

        trans_styles = [translate_text(s, lang) for s in styles]

        if style_choice in styles:
            style_idx = styles.index(style_choice)
        elif style_choice in trans_styles:
            style_idx = trans_styles.index(style_choice)
        else:
            style_idx = 0

        items = ["穴を設ける", "穴を設けない"]
        hole_choice, ok5 = TranslatedInputDialog.getItem(None, "三日月設計", "紐通し穴の設定:", items, 0, False)
        if not ok5: return
        
        trans_items = [translate_text(it, lang) for it in items]
        
        if hole_choice in items:
            has_hole = (items.index(hole_choice) == 0)
        elif hole_choice in trans_items:
            has_hole = (trans_items.index(hole_choice) == 0)
        else:
            has_hole = True

        r_hole = 0.8

        if has_hole:
            max_hole_r = max(0.5, (r_out - r_in))
            r_hole, ok6 = TranslatedInputDialog.getDouble(None, "三日月設計", "穴の半径 (mm):", 0.8, 0.2, max_hole_r, 2)
            if not ok6: return

        self.create_mikazuki(r_out, r_in, offset, t, style_idx, has_hole, r_hole, lang)

    def create_mikazuki(self, r_out, r_in, offset, t, style_idx, has_hole, r_hole, lang):
        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("三日月モデル生成", lang), initial_text=translate_text("ベースとなる外円柱を生成中...", lang))

            doc = FreeCAD.activeDocument() or FreeCAD.newDocument("MikazukiDesign")
            doc.openTransaction("CreateMikazuki")
            
            try:
                base_cyl = Part.makeCylinder(r_out, t)
                
                bar.update(25, translate_text("内側のくり抜き用カッターを配置中...", lang))
                cutter_cyl = Part.makeCylinder(r_in, t)
                cutter_cyl.translate(FreeCAD.Vector(offset, 0, 0))
                
                bar.update(45, translate_text("ベース形状からカッターを減算（ブーリアンCut）中...", lang))
                mikazuki_shape = base_cyl.cut(cutter_cyl)
                
                if style_idx == 1:
                    bar.update(60, translate_text("角を丸めてかわいらしいシルエットへ加工中...", lang))
                    fillet_r = min(0.8, t * 0.35)
                    edges_to_fillet = []
                    for e in mikazuki_shape.Edges:
                        if abs(e.BoundBox.ZMin - 0.0) < 0.01 or abs(e.BoundBox.ZMax - t) < 0.01:
                            edges_to_fillet.append(e)
                    if edges_to_fillet:
                        try:
                            mikazuki_shape = mikazuki_shape.makeFillet(fillet_r, edges_to_fillet)
                        except Exception:
                            pass

                if has_hole:
                    bar.update(75, translate_text("ペンダント紐通し穴の最適位置を自動計算中...", lang))
                    
                    angle = math.radians(125.0)  
                    out_x = r_out * math.cos(angle)
                    out_y = r_out * math.sin(angle)
                    
                    in_x = offset + r_in * math.cos(angle)
                    in_y = r_in * math.sin(angle)
                    
                    hole_x = (out_x + in_x) / 2.0
                    hole_y = (out_y + in_y) / 2.0
                    
                    bar.update(85, translate_text("紐通し穴用の円柱を減算（くり抜き）中...", lang))
                    hole_cyl = Part.makeCylinder(r_hole, t + 2.0)
                    hole_cyl.translate(FreeCAD.Vector(hole_x, hole_y, -1.0))
                    
                    mikazuki_shape = mikazuki_shape.cut(hole_cyl)
                else:
                    bar.update(85, translate_text("形状データをクリーニング中...", lang))

                bar.update(95, translate_text("不要な結合シーム線をクリアに最適化中...", lang))
                mikazuki_shape = mikazuki_shape.removeSplitter()

                label = "Mikazuki_Cute" if style_idx == 1 else "Mikazuki"
                obj = doc.addObject("Part::Feature", label)
                obj.Shape = mikazuki_shape
                
                if style_idx == 1:
                    obj.ViewObject.ShapeColor = (1.0, 0.9, 0.5)
                else:
                    obj.ViewObject.ShapeColor = (1.0, 1.0, 0.4)
                obj.ViewObject.DisplayMode = "Flat Lines"
                
                bar.update(100, translate_text("画面を更新しています...", lang))
                
                doc.commitTransaction()
                doc.recompute()
                if FreeCADGui.activeView():
                    FreeCADGui.activeView().fitAll()

            except Exception as e:
                doc.abortTransaction()
                FreeCAD.Console.PrintError(f"Mikazuki creation error: {str(e)}\n")
                err_title = "Error" if lang == "English" else "エラー"
                err_msg = f"An error occurred during creation:\n{str(e)}" if lang == "English" else f"生成中にエラーが発生しました:\n{str(e)}"
                QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Ring_Mikazuki', Tool_Mikazuki())