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
            msg += "・指輪（リング）と飾り（ダイヤモンド等）の2つを選択して実行してください。\n"
            msg += "（選択順序はどちらが先でも自動判定されます）"
            QtWidgets.QMessageBox.warning(None, "選択エラー", msg)
            return

        doc = FreeCAD.activeDocument()
        
        obj1 = sel[0]
        obj2 = sel[1]

        if not hasattr(obj1, "Shape") or not hasattr(obj2, "Shape") or obj1.Shape.isNull() or obj2.Shape.isNull():
            QtWidgets.QMessageBox.warning(None, "エラー", "立体モデルではないオブジェクトが選択されています。")
            return

        embed_depth, ok = QtWidgets.QInputDialog.getDouble(None, "配置設定", "輪への埋め込み量 (mm):", 1.5, 0.1, 20.0, 1)
        if not ok: return

        with Progress.ProgressManager() as bar:
            bar.start(title="ジュエリー結合処理", initial_text="オブジェクトの3Dサイズと位置を解析中...")

            # グローバル座標を正確に反映した形状を複製
            shape1 = obj1.Shape.copy()
            shape1.transformShape(obj1.getGlobalPlacement().toMatrix())
            
            shape2 = obj2.Shape.copy()
            shape2.transformShape(obj2.getGlobalPlacement().toMatrix())

            # サイズが大きい方を「指輪」、小さい方を「ダイヤ/飾り」として自動判定
            diag1 = shape1.BoundBox.DiagonalLength
            diag2 = shape2.BoundBox.DiagonalLength

            if diag1 >= diag2:
                obj_ring, shape_ring = obj1, shape1
                obj_daiya, shape_daiya = obj2, shape2
            else:
                obj_ring, shape_ring = obj2, shape2
                obj_daiya, shape_daiya = obj1, shape1

            bar.update(30, "ダイヤを指輪の外周向き（Y軸方向）へ回転・整列中...")

            # ダイヤの先端を指輪の内側へ、テーブル面（天面）を指輪の外側へ向けるため90度回転
            rot = FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), 90)
            shape_daiya.Placement = FreeCAD.Placement(FreeCAD.Vector(0,0,0), rot)

            # 回転後のバウンディングボックスを取得
            ring_bbox = shape_ring.BoundBox
            daiya_bbox = shape_daiya.BoundBox

            # 指輪のセンタリング座標 (X, Z) と 外周トップ (YMax)
            ring_center_x = (ring_bbox.XMin + ring_bbox.XMax) / 2.0
            ring_center_z = (ring_bbox.ZMin + ring_bbox.ZMax) / 2.0
            target_y = ring_bbox.YMax - embed_depth

            # 移動量の計算
            move_x = ring_center_x - ((daiya_bbox.XMin + daiya_bbox.XMax) / 2.0)
            move_z = ring_center_z - ((daiya_bbox.ZMin + daiya_bbox.ZMax) / 2.0)
            move_y = target_y - daiya_bbox.YMin

            shape_daiya.translate(FreeCAD.Vector(move_x, move_y, move_z))

            try:
                bar.update(60, "ステップ1: フラット底面用の石座カッターを準備中...")
                cutter_shape = shape_daiya.copy()
                # 確実に重ね合わせをつくるためマイナスY方向へ微小オフセット
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