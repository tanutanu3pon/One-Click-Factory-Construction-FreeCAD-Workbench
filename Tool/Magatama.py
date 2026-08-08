# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part
import math
from PySide import QtWidgets

# ?? Core/Progress.py から【決定版】の進捗マネージャーをインポート
import Core.Progress as Progress

class Tool_Magatama:
    def GetResources(self):
        current_dir = os.path.dirname(__file__)
        ring_dir = os.path.dirname(current_dir)
        icon_path = os.path.join(ring_dir, "icons", "magatama.png").replace('\\', '/')
        
        return {
            'Pixmap'  : icon_path,
            'MenuText': "勾玉作成",
            'ToolTip' : "ロフト機能を利用して日本古来の勾玉を生成します（進捗窓付き）"
        }

    def Activated(self):
        # 1. 頭部の入力（基準サイズ）
        r, ok1 = QtWidgets.QInputDialog.getDouble(None, "勾玉設計", "頭部の半径 (mm):", 5.0, 1.0, 50.0, 1)
        if not ok1: return
        
        # 2. 巻き角度の入力（尾の長さ）
        angle, ok2 = QtWidgets.QInputDialog.getDouble(None, "勾玉設計", "巻きの角度 (度, 180~270がお勧め):", 220.0, 90.0, 360.0, 1)
        if not ok2: return

        # 3. 穴のサイズの入力
        hole_r, ok3 = QtWidgets.QInputDialog.getDouble(None, "勾玉設計", "穴の半径 (mm):", 1.5, 0.0, r-0.5, 1)
        if not ok3: return

        self.create_magatama(r, angle, hole_r)

    def create_magatama(self, R, angle_deg, hole_r):
        # ==========================================
        # ? 【指示を出すだけ】最新のクラス方式で窓をスタート！
        # ==========================================
        bar = Progress.ProgressManager()
        bar.start(title="勾玉モデル生成", initial_text="頭部（球体）を生成中...")

        doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
        
        t_max = math.radians(angle_deg)
        spine_R = R * 1.3  # 勾玉の曲がり具合（背骨の半径）

        # --- 1. 頭部の生成（球体） ---
        head = Part.makeSphere(R)

        # --- 2. 尾部の生成（ロフト） ---
        bar.update(15, "尾部の断面曲線をスキャン計算中...")
        
        wires = []
        steps = 40 # 断面の解像度
        
        for i in range(steps + 1):
            t = t_max * (i / steps)
            
            # 軌道（背骨）の中心座標 (円弧を描く)
            cx = spine_R - spine_R * math.cos(t)
            cy = spine_R * math.sin(t)
            cz = 0.0
            center = FreeCAD.Vector(cx, cy, cz)
            
            # 軌道に対する法線ベクトル（接線方向）
            nx = math.sin(t)
            ny = math.cos(t)
            nz = 0.0
            normal = FreeCAD.Vector(nx, ny, nz)
            
            # 断面の半径（先端に行くほど細くする）
            ratio = t / t_max
            current_r = R * math.pow(1.0 - ratio, 0.7)
            current_r = max(0.05, current_r) # ロフト失敗を防ぐため最小値を設定
            
            # 円を作成してワイヤーに変換
            circle_edge = Part.makeCircle(current_r, center, normal)
            wire = Part.Wire([circle_edge])
            wires.append(wire)
            
            # ?? 5回に1回、進捗窓の％を滑らかに進める（15% ? 55% の間）
            if i % 5 == 0:
                loop_percent = int(15 + (40 * (i / steps)))
                bar.update(loop_percent, "尾部の外郭スキンを構築中...")

        # --- 60% 完了 ---
        bar.update(60, "断面を繋いで尾部をロフト立体化中...")
        tail = Part.makeLoft(wires, True)

        # --- 75% 完了 ---
        bar.update(75, "頭部と尾部をブーリアン結合中...")
        magatama_base = head.fuse(tail)

        # --- 85% 完了 ---
        if hole_r > 0:
            bar.update(85, "紐通し用の穴をくり抜き（Cut）中...")
            get_vector_start = FreeCAD.Vector(0, 0, -R * 1.5)
            get_vector_dir = FreeCAD.Vector(0, 0, 1)
            hole_cyl = Part.makeCylinder(hole_r, R * 3, get_vector_start, get_vector_dir)
            magatama_final = magatama_base.cut(hole_cyl)
        else:
            bar.update(85, "形状データをクリーニング中...")
            magatama_final = magatama_base

        # --- 95% 完了 ---
        bar.update(95, "シーム（結合線）を消去してツルツルに最適化中...")
        magatama_final = magatama_final.removeSplitter()

        # --- ドキュメントへの登録と見た目の調整 ---
        obj = doc.addObject("Part::Feature", "Magatama")
        obj.Shape = magatama_final
        
        # 翡翠（ヒスイ）をイメージした色を設定
        obj.ViewObject.ShapeColor = (0.2, 0.7, 0.4) 
        obj.ViewObject.DisplayMode = "Flat Lines"
        
        # ==========================================
        # ?? 【最重要】最後に100%にして、しっかり閉じる
        # ==========================================
        bar.update(100, "画面を更新しています...")
        bar.close()
        
        doc.recompute()
        FreeCADGui.activeView().fitAll()

# 登録名を「Magatama」に設定
FreeCADGui.addCommand('Ring_Magatama', Tool_Magatama())