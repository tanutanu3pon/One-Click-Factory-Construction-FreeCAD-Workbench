# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part
import math
from PySide import QtGui, QtCore

# ?? Core/Progress.py から【決定版】の進捗マネージャーをインポート
import Core.Progress as Progress

class Tool_MakeRing:
    def GetResources(self):
        # 【完全解決】__file__（このファイル自体の場所）を基準に逆算します。
        # これにより、PCのユーザー名が変わっても100%確実にアイコンを読み込めます。
        current_dir = os.path.dirname(__file__) # Tool フォルダの場所を取得
        ring_dir = os.path.dirname(current_dir) # 一階層上の Ring フォルダの場所を取得
        icon_path = os.path.join(ring_dir, "icons", "ring.png").replace('\\', '/')
        
        return {
            'Pixmap'  : icon_path,
            'MenuText': "指輪を精密設計",
            'ToolTip' : "断面を垂直に回転させてリングを作成します（進捗窓付き）"
        }

    def get_jis_size(self, size_num):
        """画像サイズ表に基づく内半径の計算"""
        inner_diameter = 13.0 + (size_num - 1) / 3.0
        return inner_diameter / 2.0

    def Activated(self):
        sizes = [str(i) for i in range(1, 31)]
        size_str, ok1 = QtGui.QInputDialog.getItem(None, "サイズ選択", "リングサイズ (号):", sizes, 9, False)
        if not ok1: return
        size_num = int(size_str)

        types = ["フラット", "セミラウンド", "ラウンド"]
        ring_type, ok2 = QtGui.QInputDialog.getItem(None, "形状選択", "断面形状:", types, 1, False)
        if not ok2: return

        width, ok3 = QtGui.QInputDialog.getDouble(None, "寸法指定", "リングの幅 (mm):", 2.5, 1.0, 10.0, 1)
        if not ok3: return
        thickness, ok4 = QtGui.QInputDialog.getDouble(None, "寸法指定", "地金の厚み (mm):", 1.5, 0.5, 5.0, 1)
        if not ok4: return

        # 回転角度（スイープの程度）の入力
        angle, ok5 = QtGui.QInputDialog.getDouble(None, "角度指定", "回転角度 (度, 1~360):", 360.0, 1.0, 360.0, 1)
        if not ok5: return

        self.create_correct_ring(size_num, ring_type, width, thickness, angle)

    def create_correct_ring(self, size_num, ring_type, width, thickness, angle):
        # ==========================================
        # ? 【指示を出すだけ】最新のクラス方式で窓をスタート！
        # ==========================================
        bar = Progress.ProgressManager()
        bar.start(title="リングモデル生成", initial_text="JIS規格の指輪サイズを計算中...")

        doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
        
        inner_r = self.get_jis_size(size_num)
        h = width / 2.0  # 幅を上下に振り分ける
        
        # --- 25% 完了 ---
        bar.update(25, f"{ring_type} 断面のワイヤー（輪郭線）を生成中...")

        # --- 断面（XZ平面）の定義 ---
        p1 = FreeCAD.Vector(inner_r, 0, -h)             # 内側・下
        p2 = FreeCAD.Vector(inner_r + thickness, 0, -h)  # 外側・下
        p3 = FreeCAD.Vector(inner_r + thickness, 0,  h)  # 外側・上
        p4 = FreeCAD.Vector(inner_r, 0,  h)              # 内側・上

        if "フラット" in ring_type:
            mid_inner = FreeCAD.Vector(inner_r - 0.15, 0, 0)
            arc_inner = Part.Arc(p4, mid_inner, p1).toShape()
            line_bottom = Part.makeLine(p1, p2)
            line_outer = Part.makeLine(p2, p3)
            line_top = Part.makeLine(p3, p4)
            profile = Part.Wire([line_bottom, line_outer, line_top, arc_inner])
        
        elif "セミラウンド" in ring_type:
            mid_outer = FreeCAD.Vector(inner_r + thickness + 0.25, 0, 0)
            arc_outer = Part.Arc(p2, mid_outer, p3).toShape()
            mid_inner = FreeCAD.Vector(inner_r - 0.2, 0, 0)
            arc_inner = Part.Arc(p4, mid_inner, p1).toShape()
            line_bottom = Part.makeLine(p1, p2)
            line_top = Part.makeLine(p3, p4)
            profile = Part.Wire([line_bottom, arc_outer, line_top, arc_inner])

        else: # ラウンド
            mid_outer = FreeCAD.Vector(inner_r + thickness + 0.5, 0, 0)
            arc_outer = Part.Arc(p2, mid_outer, p3).toShape()
            mid_inner = FreeCAD.Vector(inner_r - 0.5, 0, 0)
            arc_inner = Part.Arc(p4, mid_inner, p1).toShape()
            line_bottom = Part.makeLine(p1, p2)
            line_top = Part.makeLine(p3, p4)
            profile = Part.Wire([line_bottom, arc_outer, line_top, arc_inner])

        # --- 55% 完了 ---
        bar.update(55, "断面からソリッド（面）を構成中...")
        face = Part.Face(profile)
        
        # --- 75% 完了 ---
        bar.update(75, f"Z軸を中心に {angle}度 回転（Revolve）させて立体化中...")
        ring_shape = face.revolve(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), angle)

        # --- 90% 完了 ---
        bar.update(90, "FreeCADオブジェクトへリングデータを登録中...")
        obj = doc.addObject("Part::Feature", f"Size{size_num}_{ring_type}_{angle}deg")
        obj.Shape = ring_shape
        
        # ==========================================
        # ?? 【最重要】最後に100%にして、しっかり閉じる
        # ==========================================
        bar.update(100, "画面を更新しています...")
        bar.close()

        doc.recompute()
        FreeCADGui.activeView().viewAxometric()
        FreeCADGui.activeView().fitAll()

FreeCADGui.addCommand('Ring_MakeRing', Tool_MakeRing())