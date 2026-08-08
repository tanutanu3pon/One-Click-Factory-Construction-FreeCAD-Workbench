# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress

class Tool_ConnectJewelry:
    def GetResources(self):
        current_dir = os.path.dirname(__file__) 
        ring_dir = os.path.dirname(current_dir) 
        icon_path = os.path.join(ring_dir, "icons", "connect.png").replace('\\', '/')
        
        return {
            'Pixmap'  : icon_path,
            'MenuText': "ジュエリーセット (減算結合)",
            'ToolTip' : "モデルを輪に埋め込んで減算し、そこに再度結合して完璧なデータにします（進捗窓付き）"
        }

    def Activated(self):
        sel = FreeCADGui.Selection.getSelection()
        
        if len(sel) != 2:
            msg = "エラー: 2つの立体モデルを選択してください。\n\n"
            msg += "1. 輪(リング)をクリック\n"
            msg += "2. CTRLキーを押しながら飾りをクリック\n"
            msg += "その後にこのアイコンを押してください。"
            QtWidgets.QMessageBox.warning(None, "選択エラー", msg)
            return

        doc = FreeCAD.activeDocument()
        obj_ring = sel[0]  
        obj_daiya = sel[1] 

        if not hasattr(obj_ring, "Shape") or not hasattr(obj_daiya, "Shape"):
            QtWidgets.QMessageBox.warning(None, "エラー", "立体モデルではないオブジェクトが選択されています。")
            return

        embed_depth, ok = QtWidgets.QInputDialog.getDouble(None, "配置設定", "輪への埋め込み量 (mm):", 1.5, 0.1, 20.0, 1)
        if not ok: return

        with Progress.ProgressManager() as bar:
            bar.start(title="ジュエリー結合処理", initial_text="オブジェクトの3D座標を解析中...")

            shape_ring = obj_ring.Shape.copy()
            shape_ring.Placement = obj_ring.Placement
            ring_bbox = shape_ring.BoundBox

            center_x = (ring_bbox.XMax + ring_bbox.XMin) / 2.0
            center_z = (ring_bbox.ZMax + ring_bbox.ZMin) / 2.0

            shape_daiya = obj_daiya.Shape.copy()
            
            bar.update(25, "ダイヤを垂直（側面埋め込み向き）に回転中...")
            
            rot = FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), 90)
            shape_daiya.Placement = FreeCAD.Placement(FreeCAD.Vector(0,0,0), rot)
            daiya_bbox = shape_daiya.BoundBox

            bar.update(45, "指輪の側面にダイヤの位置を正確にフィッティング中...")

            target_y = ring_bbox.YMax - embed_depth
            
            move_y = target_y - daiya_bbox.YMin
            move_x = center_x - ((daiya_bbox.XMax + daiya_bbox.XMin) / 2.0)
            move_z = center_z - ((daiya_bbox.ZMax + daiya_bbox.ZMin) / 2.0)

            shape_daiya.translate(FreeCAD.Vector(move_x, move_y, move_z))

            try:
                bar.update(60, "ステップ1: フラット底面用の穴あけカッターを最適化中...")
                cutter_shape = shape_daiya.copy()
                cutter_shape.translate(FreeCAD.Vector(0, -0.02, 0))
                
                bar.update(75, "ステップ2: 指輪にピッタリの石座（穴）を減算カット中...")
                shape_cut = shape_ring.cut(cutter_shape)
                
                bar.update(85, "ステップ3: 石座にダイヤを隙間なく一体溶接（Fuse）中...")
                fused_shape = shape_cut.fuse(shape_daiya)
                
                bar.update(95, "仕上げ: 重複する境界シーム線を綺麗にクリーニング中...")
                fused_shape = fused_shape.removeSplitter()
                
            except Exception as e:
                QtWidgets.QMessageBox.warning(None, "結合エラー", f"セットに失敗しました:\n{str(e)}")
                return

            new_label = f"Set_{obj_ring.Label}_{obj_daiya.Label}"
            jewelry_obj = doc.addObject("Part::Feature", new_label)
            jewelry_obj.Shape = fused_shape
            
            if hasattr(obj_ring, "ViewObject") and hasattr(obj_ring.ViewObject, "ShapeColor"):
                jewelry_obj.ViewObject.ShapeColor = obj_ring.ViewObject.ShapeColor
            
            obj_ring.ViewObject.Visibility = False
            obj_daiya.ViewObject.Visibility = False
            
            bar.update(100, "画面を更新しています...")

            doc.recompute()
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.Selection.addSelection(jewelry_obj)
            FreeCADGui.activeView().fitAll()

FreeCADGui.addCommand('Ring_Connect', Tool_ConnectJewelry())