# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part
import math
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress

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
        r_out, ok1 = QtWidgets.QInputDialog.getDouble(None, "三日月設計", "外側の半径 (mm):", 10.0, 2.0, 100.0, 1)
        if not ok1: return
        
        r_in, ok2 = QtWidgets.QInputDialog.getDouble(None, "三日月設計", "内側の半径 (mm):", 8.5, 1.0, r_out, 1)
        if not ok2: return

        offset, ok3 = QtWidgets.QInputDialog.getDouble(None, "三日月設計", "中心のズレ (mm):", 4.0, 0.1, r_out, 1)
        if not ok3: return

        t, ok4 = QtWidgets.QInputDialog.getDouble(None, "三日月設計", "厚み (mm):", 2.0, 0.5, 30.0, 1)
        if not ok4: return

        items = ["穴を設ける", "穴を設けない"]
        hole_choice, ok5 = QtWidgets.QInputDialog.getItem(None, "三日月設計", "紐通し穴の設定:", items, 0, False)
        if not ok5: return
        
        # 英語化モードでも破綻しないインデックス照合へ修正
        has_hole = (items.index(hole_choice) == 0)
        r_hole = 0.8

        if has_hole:
            max_hole_r = max(0.5, (r_out - r_in))
            r_hole, ok6 = QtWidgets.QInputDialog.getDouble(None, "三日月設計", "穴の半径 (mm):", 0.8, 0.2, max_hole_r, 2)
            if not ok6: return

        self.create_mikazuki(r_out, r_in, offset, t, has_hole, r_hole)

    def create_mikazuki(self, r_out, r_in, offset, t, has_hole, r_hole):
        with Progress.ProgressManager() as bar:
            bar.start(title="三日月モデル生成", initial_text="ベースとなる外円柱を生成中...")

            doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
            
            base_cyl = Part.makeCylinder(r_out, t)
            
            bar.update(25, "内側のくり抜き用カッターを配置中...")
            cutter_cyl = Part.makeCylinder(r_in, t)
            cutter_cyl.translate(FreeCAD.Vector(offset, 0, 0))
            
            bar.update(50, "ベース形状からカッターを減算（ブーリアンCut）中...")
            mikazuki_shape = base_cyl.cut(cutter_cyl)
            
            if has_hole:
                bar.update(70, "ペンダント紐通し穴の最適位置を自動計算中...")
                
                angle = math.radians(125.0)  
                out_x = r_out * math.cos(angle)
                out_y = r_out * math.sin(angle)
                
                in_x = offset + r_in * math.cos(angle)
                in_y = r_in * math.sin(angle)
                
                hole_x = (out_x + in_x) / 2.0
                hole_y = (out_y + in_y) / 2.0
                
                bar.update(85, "紐通し穴用の円柱を減算（くり抜き）中...")
                hole_cyl = Part.makeCylinder(r_hole, t)
                hole_cyl.translate(FreeCAD.Vector(hole_x, hole_y, 0))
                
                mikazuki_shape = mikazuki_shape.cut(hole_cyl)
            else:
                bar.update(85, "形状データをクリーニング中...")

            bar.update(95, "不要な結合シーム線をクリアに最適化中...")
            mikazuki_shape = mikazuki_shape.removeSplitter()

            obj = doc.addObject("Part::Feature", "Mikazuki")
            obj.Shape = mikazuki_shape
            
            obj.ViewObject.ShapeColor = (1.0, 1.0, 0.4)
            obj.ViewObject.DisplayMode = "Flat Lines"
            
            bar.update(100, "画面を更新しています...")
            
            doc.recompute()
            FreeCADGui.activeView().fitAll()

FreeCADGui.addCommand('Ring_Mikazuki', Tool_Mikazuki())