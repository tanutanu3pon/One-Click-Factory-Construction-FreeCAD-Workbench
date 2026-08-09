# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part
import math

# 【修正】絶対インポートで安全にCoreモジュールを読み込む
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedInputDialog, translate_text
from Core.Language import get_language

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
        lang = get_language()

        # 【修正】QtWidgets.QInputDialog から TranslatedInputDialog へ差し替え
        d, ok1 = TranslatedInputDialog.getDouble(None, "ダイヤ設計", "直径 (mm):", 5.0, 1.0, 50.0, 2)
        if not ok1: return
        
        n, ok2 = TranslatedInputDialog.getInt(None, "ダイヤ設計", "角数 (8=標準的):", 8, 3, 64)
        if not ok2: return

        # 【修正】QMessageBoxの各テキストを translate_text で翻訳
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle(translate_text("形状オプション", lang))
        msg.setText(translate_text("ダイヤモンドの下部をカットしますか？", lang))
        msg.setInformativeText(translate_text("「はい」：先端を半分でカットして平らにします\n「いいえ」：通常の尖った形状にします", lang))
        msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        msg.setDefaultButton(QtWidgets.QMessageBox.No)
        res = msg.exec_()
        
        cut_ratio = 0.5 if res == QtWidgets.QMessageBox.Yes else 0.0

        # lang 引数を追加して渡す
        self.create_polygon_diamond(d, n, cut_ratio, lang)

    def create_polygon_diamond(self, d, n, cut_ratio, lang):
        with Progress.ProgressManager() as bar:
            # 【修正】プログレスバーのテキストを翻訳
            bar.start(title=translate_text("ダイヤモンド生成", lang), initial_text=translate_text("プロポーション頂点を計算中...", lang))

            doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
            r = d / 2.0
            
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

            pts_p_bot   = get_poly_points(r, 0)
            pts_g_top   = get_poly_points(r, girdle_h)
            pts_table   = get_poly_points(table_r, girdle_h + crown_h)

            faces = []

            bar.update(15, translate_text("1/4: パビリオン面（下部ファセット）を生成中...", lang))

            if cut_ratio == 0:
                culet = FreeCAD.Vector(0, 0, -pavilion_h_full)
                for i in range(n):
                    p1 = culet
                    p2 = pts_p_bot[i]
                    p3 = pts_p_bot[(i+1)%n]
                    faces.append(Part.makeFace(Part.makePolygon([p1, p2, p3, p1])))
                    
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

            bar.update(35, translate_text("2/4: ガードル面（側面ファセット）を生成中...", lang))

            for i in range(n):
                p1 = pts_p_bot[i]
                p2 = pts_p_bot[(i+1)%n]
                p3 = pts_g_top[(i+1)%n]
                p4 = pts_g_top[i]
                faces.append(Part.makeFace(Part.makePolygon([p1, p2, p3, p4, p1])))
                
                if i % 4 == 0:
                    loop_percent = int(35 + (15 * (i / n)))
                    bar.update(loop_percent)

            bar.update(55, translate_text("3/4: クラウン面（上部ファセット）を生成中...", lang))

            for i in range(n):
                p1 = pts_g_top[i]
                p2 = pts_g_top[(i+1)%n]
                p3 = pts_table[(i+1)%n]
                p4 = pts_table[i]
                faces.append(Part.makeFace(Part.makePolygon([p1, p2, p3, p4, p1])))
                
                if i % 4 == 0:
                    loop_percent = int(55 + (15 * (i / n)))
                    bar.update(loop_percent)

            bar.update(75, translate_text("4/4: テーブル面（天面）を生成中...", lang))

            table_wire = Part.makePolygon(pts_table + [pts_table[0]])
            faces.append(Part.makeFace(table_wire))

            bar.update(85, translate_text("各ファセットを縫い合わせてソリッド立体化中...", lang))
            shell = Part.makeShell(faces)
            diamond_solid = Part.makeSolid(shell)

            bar.update(95, translate_text("FreeCADオブジェクトへダイヤデータを登録中...", lang))
            label = "Diamond_FlatBottom" if cut_ratio > 0 else "Diamond_Pointed"
            obj = doc.addObject("Part::Feature", label)
            obj.Shape = diamond_solid
            obj.ViewObject.ShapeColor = (0.9, 0.95, 1.0)
            obj.ViewObject.Transparency = 40
            obj.ViewObject.DisplayMode = "Flat Lines"
            
            bar.update(100, translate_text("画面を更新しています...", lang))

            doc.recompute()
            FreeCADGui.activeView().fitAll()

FreeCADGui.addCommand('Ring_Daiya', Tool_Daiya())