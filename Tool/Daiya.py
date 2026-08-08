# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part
import math
from PySide import QtGui

# ?? Core/Progress.py から進捗マネージャーをインポート
import Core.Progress as Progress

class Tool_Daiya:
    def GetResources(self):
        current_dir = os.path.dirname(__file__)
        ring_dir = os.path.dirname(current_dir)
        icon_path = os.path.join(ring_dir, "icons", "daiya.png").replace('\\', '/')
        
        return {
            'Pixmap'  : icon_path,
            'MenuText': "多角形ダイヤ作成",
            'ToolTip' : "下部をカットするか選択してダイヤモンドを生成します（進捗窓付き）"
        }

    def Activated(self):
        # 1. 直径の入力
        d, ok1 = QtGui.QInputDialog.getDouble(None, "ダイヤ設計", "直径 (mm):", 5.0, 1.0, 50.0, 2)
        if not ok1: return
        
        # 2. 角数の入力
        n, ok2 = QtGui.QInputDialog.getInt(None, "ダイヤ設計", "角数 (8=標準的):", 8, 3, 64)
        if not ok2: return

        # 3. 下部をカットするかどうかの選択
        msg = QtGui.QMessageBox()
        msg.setWindowTitle("形状オプション")
        msg.setText("ダイヤモンドの下部をカットしますか？")
        msg.setInformativeText("「はい」：先端を半分でカットして平らにします\n「いいえ」：通常の尖った形状にします")
        msg.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        msg.setDefaultButton(QtGui.QMessageBox.No)
        res = msg.exec_()
        
        cut_ratio = 0.5 if res == QtGui.QMessageBox.Yes else 0.0

        self.create_polygon_diamond(d, n, cut_ratio)

    def create_polygon_diamond(self, d, n, cut_ratio):
        # ==========================================
        # ? 【指示を出すだけ】Coreの窓コントロールを起動！
        # ==========================================
        bar = Progress.ProgressManager()
        bar.start(title="ダイヤモンド生成", initial_text="プロポーション頂点を計算中...")

        doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
        r = d / 2.0
        
        # --- プロポーション計算 ---
        table_r = r * 0.53
        crown_h = r * 0.32
        pavilion_h_full = r * 0.80 
        girdle_h = r * 0.04

        pavilion_h_actual = pavilion_h_full * (1.0 - cut_ratio)
        bottom_r = r * cut_ratio 
        bottom_z = -pavilion_h_actual

        def get_poly_points(radius, z):
            pts = []
            for i in range(n):
                angle = 2 * math.pi * i / n
                pts.append(FreeCAD.Vector(radius * math.cos(angle), radius * math.sin(angle), z))
            return pts

        # 各高さの頂点リストを作成
        pts_p_bot   = get_poly_points(r, 0)
        pts_g_top   = get_poly_points(r, girdle_h)
        pts_table   = get_poly_points(table_r, girdle_h + crown_h)

        faces = []

        # --- 15% 完了 ---
        bar.update(15, "1/4: パビリオン面（下部ファセット）を生成中...")

        # 1. パビリオン（下部）の生成
        if cut_ratio == 0:
            culet = FreeCAD.Vector(0, 0, -pavilion_h_full)
            for i in range(n):
                p1 = culet
                p2 = pts_p_bot[i]
                p3 = pts_p_bot[(i+1)%n]
                faces.append(Part.makeFace(Part.makePolygon([p1, p2, p3, p1])))
                
                # 角数が多い場合を考慮して細かく進捗を更新
                if i % 4 == 0:
                    loop_percent = int(15 + (15 * (i / n)))
                    bar.update(loop_percent)
        else:
            pts_bottom = get_poly_points(bottom_r, bottom_z)
            for i in range(n):
                p1 = pts_bottom[i]
                p2 = pts_bottom[(i+1)%n]
                p3 = pts_p_bot[(i+1)%n]
                p4 = pts_p_bot[i]
                faces.append(Part.makeFace(Part.makePolygon([p1, p2, p3, p4, p1])))
                
                if i % 4 == 0:
                    loop_percent = int(15 + (15 * (i / n)))
                    bar.update(loop_percent)
                    
            bottom_wire = Part.makePolygon(pts_bottom + [pts_bottom[0]])
            faces.append(Part.makeFace(bottom_wire))

        # --- 35% 完了 ---
        bar.update(35, "2/4: ガードル面（側面ファセット）を生成中...")

        # 2. ガードル面 (側面)
        for i in range(n):
            p1 = pts_p_bot[i]
            p2 = pts_p_bot[(i+1)%n]
            p3 = pts_g_top[(i+1)%n]
            p4 = pts_g_top[i]
            faces.append(Part.makeFace(Part.makePolygon([p1, p2, p3, p4, p1])))
            
            if i % 4 == 0:
                loop_percent = int(35 + (15 * (i / n)))
                bar.update(loop_percent)

        # --- 55% 完了 ---
        bar.update(55, "3/4: クラウン面（上部ファセット）を生成中...")

        # 3. クラウン面 (上部サイド面)
        for i in range(n):
            p1 = pts_g_top[i]
            p2 = pts_g_top[(i+1)%n]
            p3 = pts_table[(i+1)%n]
            p4 = pts_table[i]
            faces.append(Part.makeFace(Part.makePolygon([p1, p2, p3, p4, p1])))
            
            if i % 4 == 0:
                loop_percent = int(55 + (15 * (i / n)))
                bar.update(loop_percent)

        # --- 75% 完了 ---
        bar.update(75, "4/4: テーブル面（天面）を生成中...")

        # 4. テーブル面 (天面)
        table_wire = Part.makePolygon(pts_table + [pts_table[0]])
        faces.append(Part.makeFace(table_wire))

        # --- 85% 完了 ---
        bar.update(85, "各ファセットを縫い合わせてソリッド立体化中...")
        shell = Part.makeShell(faces)
        diamond_solid = Part.makeSolid(shell)

        # --- 95% 完了 ---
        bar.update(95, "FreeCADオブジェクトへダイヤデータを登録中...")
        label = "Diamond_FlatBottom" if cut_ratio > 0 else "Diamond_Pointed"
        obj = doc.addObject("Part::Feature", label)
        obj.Shape = diamond_solid
        obj.ViewObject.ShapeColor = (0.9, 0.95, 1.0)
        obj.ViewObject.Transparency = 40
        obj.ViewObject.DisplayMode = "Flat Lines"
        
        # ==========================================
        # ?? 【最重要】最後に100%にして、しっかり閉じる
        # ==========================================
        bar.update(100, "画面を更新しています...")
        bar.close()

        doc.recompute()
        FreeCADGui.activeView().fitAll()

# 登録
FreeCADGui.addCommand('Ring_Daiya', Tool_Daiya())