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
        lang = get_language()

        # 【修正】QtWidgets.QInputDialog から TranslatedInputDialog へ差し替え
        r, ok1 = TranslatedInputDialog.getDouble(None, "水滴設計", "基本半径 (mm):", 5.0, 1.0, 50.0, 1)
        if not ok1: return
        h, ok2 = TranslatedInputDialog.getDouble(None, "水滴設計", "上部の長さ (mm):", 12.0, r, 100.0, 1)
        if not ok2: return
        hole_r, ok3 = TranslatedInputDialog.getDouble(None, "水滴設計", "上部の穴の半径 (mm)\n※0で穴なし:", 1.0, 0.0, r, 1)
        if not ok3: return

        self.create_suiteki(r, h, hole_r, lang)

    def create_suiteki(self, R, H, hole_r, lang):
        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("水滴モデル生成", lang), initial_text=translate_text("下部（球体）を生成中...", lang))

            doc = FreeCAD.activeDocument() or FreeCAD.newDocument("SuitekiDesign")
            doc.openTransaction("CreateSuiteki")

            try:
                bottom_sphere = Part.makeSphere(R)

                bar.update(10, translate_text("シュッと伸びる上部の断面曲線を計算中...", lang))
                
                wires = []
                steps = 40
                for i in range(steps + 1):
                    z = H * (i / steps)
                    current_r = R * (1.0 - math.pow(z / H, 2))
                    current_r = max(0.01, current_r)
                    
                    circle_edge = Part.makeCircle(current_r, FreeCAD.Vector(0, 0, z), FreeCAD.Vector(0, 0, 1))
                    wires.append(Part.Wire([circle_edge]))
                    
                    if i % 5 == 0:
                        loop_percent = int(10 + (40 * (i / steps)))
                        bar.update(loop_percent, translate_text("水滴の外郭スキンを計算中...", lang))

                bar.update(55, translate_text("断面を繋いでロフト化中...", lang))
                top_loft = Part.makeLoft(wires, True)

                bar.update(70, translate_text("上部と下部を結合中...", lang))
                suiteki_base = bottom_sphere.fuse(top_loft)

                if hole_r > 0:
                    bar.update(85, translate_text("紐通し用バチカン穴をくり抜き中...", lang))
                    hole_z = max(R * 0.5, H - (hole_r * 2.5))
                    hole_cyl = Part.makeCylinder(hole_r, R * 4, FreeCAD.Vector(-R * 2, 0, hole_z), FreeCAD.Vector(1, 0, 0))
                    suiteki_final = suiteki_base.cut(hole_cyl)
                else:
                    bar.update(85, translate_text("形状をクリーニング中...", lang))
                    suiteki_final = suiteki_base

                bar.update(95, translate_text("シーム（結合線）を消去して最適化中...", lang))
                suiteki_final = suiteki_final.removeSplitter()

                obj = doc.addObject("Part::Feature", "Suiteki")
                obj.Shape = suiteki_final
                obj.ViewObject.ShapeColor = (0.5, 0.8, 1.0) 
                obj.ViewObject.Transparency = 30  
                obj.ViewObject.DisplayMode = "Flat Lines"
                
                bar.update(100, translate_text("画面を更新しています...", lang))

                doc.commitTransaction()
                doc.recompute()
                if FreeCADGui.activeView():
                    FreeCADGui.activeView().fitAll()

            except Exception as e:
                doc.abortTransaction()
                FreeCAD.Console.PrintError(f"Suiteki creation error: {str(e)}\n")
                err_title = "Error" if lang == "English" else "エラー"
                err_msg = f"An error occurred during creation:\n{str(e)}" if lang == "English" else f"生成中にエラーが発生しました:\n{str(e)}"
                QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Ring_Suiteki', Tool_Suiteki())