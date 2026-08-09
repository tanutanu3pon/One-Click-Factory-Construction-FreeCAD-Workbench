# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part
import math

# 【修正】エラーの原因だった相対インポート(..)をやめ、絶対インポート(Core.xxx)に戻しました！
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedInputDialog, translate_text
from Core.Language import get_language

class Tool_MakeButton:
    def GetResources(self):
        current_dir = os.path.dirname(__file__)
        ring_dir = os.path.dirname(current_dir)
        icon_path = os.path.join(ring_dir, "icons", "button.png").replace('\\', '/')
        
        return {
            'Pixmap'  : icon_path, 
            'MenuText': "服のボタン作成",
            'ToolTip' : "直径や厚み、お好みのデザインと穴数を選んでボタンを生成します（進捗窓付き）"
        }

    def Activated(self):
        # ボタンの種類（デザイン）を7種類
        design_items = [
            "単純なボタン (標準)", 
            "おしゃれなボタン (高級テーパー)", 
            "かわいいボタン (ぷっくり厚口)",
            "クラシックボタン (段付きダブルリム)",
            "ヴィンテージボタン (ドーム盛り上がり)",
            "モダンボタン (幅広リング溝)",
            "スポーツボタン (すり鉢状ディープ)"
        ]
        
        design_type, ok0 = TranslatedInputDialog.getItem(None, "デザイン選択", "ボタンのスタイル:", design_items, 0, False)
        if not ok0: return

        lang = get_language()
        trans_design_items = [translate_text(it, lang) for it in design_items]

        if design_type in design_items:
            design_idx = design_items.index(design_type)
        elif design_type in trans_design_items:
            design_idx = trans_design_items.index(design_type)
        else:
            design_idx = 0

        d, ok1 = TranslatedInputDialog.getDouble(None, "ボタン設計", "ボタンの直径 (mm):", 15.0, 5.0, 100.0, 1)
        if not ok1: return
        
        t, ok2 = TranslatedInputDialog.getDouble(None, "ボタン設計", "全体の厚み (mm):", 3.0, 1.0, 20.0, 1)
        if not ok2: return

        items = ["2つ穴 (標準)", "3つ穴 (トライアングル)", "4つ穴 (クロス)", "穴なし (パーツ用)"]
        
        item, ok3 = TranslatedInputDialog.getItem(None, "穴の設定", "糸通し穴のタイプ:", items, 0, False)
        if not ok3: return

        trans_items = [translate_text(it, lang) for it in items]
        if item in items:
            item_idx = items.index(item)
        elif item in trans_items:
            item_idx = trans_items.index(item)
        else:
            item_idx = 0

        hole_count_map = [2, 3, 4, 0]
        hole_count = hole_count_map[item_idx]

        self.create_clothing_button(d, t, hole_count, design_idx)

    def create_clothing_button(self, d, t, hole_count, design_idx):
        with Progress.ProgressManager() as bar:
            bar.start(title="ボタンモデル生成", initial_text="デザインに合わせた輪郭を計算中...")

            doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
            r = d / 2.0
            
            base_cyl = Part.makeCylinder(r, t)
            button_shape = base_cyl

            # --- デザイン別の減算・形状演算 ---
            if design_idx == 0:  # 単純なボタン
                bar.update(25, "単純なボタン：表面のフラットな窪みを削り出し中...")
                rim_w = d * 0.12        
                inner_r = r - rim_w     
                recess_d = t * 0.35     
                recess_cyl = Part.makeCylinder(inner_r, t, FreeCAD.Vector(0, 0, t - recess_d))
                button_shape = button_shape.cut(recess_cyl)
                
            elif design_idx == 1:  # おしゃれなボタン
                bar.update(25, "おしゃれなボタン：中央へ向かうテーパー面を減算加工中...")
                rim_w = d * 0.15        
                inner_r = r - rim_w
                recess_d = t * 0.45     
                cone_cutter = Part.makeCone(inner_r, inner_r * 0.4, recess_d, FreeCAD.Vector(0, 0, t - recess_d))
                button_shape = button_shape.cut(cone_cutter)
                
            elif design_idx == 2:  # かわいいボタン
                bar.update(25, "かわいいボタン：ふっくら丸い凹み形状を演算中...")
                rim_w = d * 0.18        
                inner_r = r - rim_w
                recess_d = t * 0.30     
                sphere_r = (inner_r * inner_r + recess_d * recess_d) / (2.0 * recess_d)
                sphere_cutter = Part.makeSphere(sphere_r)
                sphere_cutter.translate(FreeCAD.Vector(0, 0, t - recess_d + sphere_r))
                button_shape = button_shape.cut(sphere_cutter)

            elif design_idx == 3:  # クラシックボタン (段付きダブルリム)
                bar.update(25, "クラシックボタン：段付きダブルリム構造を演算中...")
                rim_w = d * 0.10
                inner_r1 = r - rim_w
                recess_d1 = t * 0.35
                recess_cyl1 = Part.makeCylinder(inner_r1, t, FreeCAD.Vector(0, 0, t - recess_d1))
                button_shape = button_shape.cut(recess_cyl1)

                inner_r2 = inner_r1 * 0.55
                recess_d2 = t * 0.15
                recess_cyl2 = Part.makeCylinder(inner_r2, t, FreeCAD.Vector(0, 0, t - recess_d1 - recess_d2))
                button_shape = button_shape.cut(recess_cyl2)

            elif design_idx == 4:  # ヴィンテージボタン (ドーム盛り上がり)
                bar.update(25, "ヴィンテージボタン：溝掘りと中央ドーム形状を演算中...")
                groove_outer_r = r * 0.82
                groove_inner_r = r * 0.55
                groove_d = t * 0.30
                
                outer_groove_cyl = Part.makeCylinder(groove_outer_r, t, FreeCAD.Vector(0, 0, t - groove_d))
                inner_groove_cyl = Part.makeCylinder(groove_inner_r, t, FreeCAD.Vector(0, 0, t - groove_d))
                donut_cutter = outer_groove_cyl.cut(inner_groove_cyl)
                button_shape = button_shape.cut(donut_cutter)

            elif design_idx == 5:  # モダンボタン (幅広リング溝)
                bar.update(25, "モダンボタン：幅広のリング溝を演算中...")
                groove_outer_r = r * 0.85
                groove_inner_r = r * 0.45
                groove_d = t * 0.25
                outer_groove_cyl = Part.makeCylinder(groove_outer_r, t, FreeCAD.Vector(0, 0, t - groove_d))
                inner_groove_cyl = Part.makeCylinder(groove_inner_r, t, FreeCAD.Vector(0, 0, t - groove_d))
                donut_cutter = outer_groove_cyl.cut(inner_groove_cyl)
                button_shape = button_shape.cut(donut_cutter)

            elif design_idx == 6:  # スポーツボタン (すり鉢状ディープ)
                bar.update(25, "スポーツボタン：すり鉢状の深い凹みを演算中...")
                rim_w = d * 0.20
                inner_r = r - rim_w
                recess_d = t * 0.60
                cone_cutter = Part.makeCone(inner_r, inner_r * 0.2, recess_d, FreeCAD.Vector(0, 0, t - recess_d))
                button_shape = button_shape.cut(cone_cutter)

            # --- 糸通し穴の配置と削り出し ---
            if hole_count > 0:
                bar.update(50, f"糸通し穴（{hole_count}個）の配置パターンを計算・くり抜き中...")
                hole_r = d * 0.055      
                pitch = d * 0.16        
                cutter_h = t + 2.0
                
                if hole_count == 2:
                    h1 = Part.makeCylinder(hole_r, cutter_h, FreeCAD.Vector(-pitch, 0, -1))
                    h2 = Part.makeCylinder(hole_r, cutter_h, FreeCAD.Vector(pitch, 0, -1))
                    button_shape = button_shape.cut(h1).cut(h2)
                    
                elif hole_count == 3:
                    h1_x = pitch * math.cos(math.radians(90))
                    h1_y = pitch * math.sin(math.radians(90))
                    h2_x = pitch * math.cos(math.radians(210))
                    h2_y = pitch * math.sin(math.radians(210))
                    h3_x = pitch * math.cos(math.radians(330))
                    h3_y = pitch * math.sin(math.radians(330))
                    
                    h1 = Part.makeCylinder(hole_r, cutter_h, FreeCAD.Vector(h1_x, h1_y, -1))
                    h2 = Part.makeCylinder(hole_r, cutter_h, FreeCAD.Vector(h2_x, h2_y, -1))
                    h3 = Part.makeCylinder(hole_r, cutter_h, FreeCAD.Vector(h3_x, h3_y, -1))
                    button_shape = button_shape.cut(h1).cut(h2).cut(h3)
                    
                elif hole_count == 4:
                    h1 = Part.makeCylinder(hole_r, cutter_h, FreeCAD.Vector(-pitch, 0, -1))
                    h2 = Part.makeCylinder(hole_r, cutter_h, FreeCAD.Vector(pitch, 0, -1))
                    h3 = Part.makeCylinder(hole_r, cutter_h, FreeCAD.Vector(0, -pitch, -1))
                    h4 = Part.makeCylinder(hole_r, cutter_h, FreeCAD.Vector(0, pitch, -1))
                    button_shape = button_shape.cut(h1).cut(h2).cut(h3).cut(h4)

            # --- エッジ加工 (フィレット) ---
            bar.update(75, "仕上げ加工：エッジの丸み（フィレット）を適用中...")
            edges_to_fillet = []
            for edge in button_shape.Edges:
                try:
                    curve = edge.Curve
                    if isinstance(curve, Part.Circle):
                        if abs(curve.Radius - r) < 0.001:
                            edges_to_fillet.append(edge)
                except Exception:
                    continue
                        
            if edges_to_fillet:
                try:
                    if design_idx == 2:
                        fillet_r = t * 0.30
                    elif design_idx in (3, 4, 5):
                        fillet_r = t * 0.20
                    elif design_idx == 6:
                        fillet_r = t * 0.25
                    else:
                        fillet_r = t * 0.15
                    button_shape = button_shape.makeFillet(fillet_r, edges_to_fillet)
                except Exception:
                    pass

            bar.update(90, "不要な結合線をクリーニング中...")
            button_shape = button_shape.removeSplitter()

            style_labels = ["Simple", "Stylish", "Cute", "Classic", "Vintage", "Modern", "Sports"]
            style_label = style_labels[design_idx] if design_idx < len(style_labels) else "Custom"
            label = f"{style_label}_Button_{hole_count}Holes" if hole_count > 0 else f"{style_label}_Button_NoHole"
            obj = doc.addObject("Part::Feature", label)
            obj.Shape = button_shape
            
            # デザイン別のカラーリング設定
            if design_idx == 0:
                obj.ViewObject.ShapeColor = (0.95, 0.95, 0.93)  # 生成りホワイト
            elif design_idx == 1:
                obj.ViewObject.ShapeColor = (0.25, 0.25, 0.28)  # チャコールグレー
            elif design_idx == 2:
                obj.ViewObject.ShapeColor = (1.00, 0.75, 0.80)  # パステルピンク
            elif design_idx == 3:
                obj.ViewObject.ShapeColor = (0.65, 0.45, 0.25)  # ベッコウ・ウッドブラウン
            elif design_idx == 4:
                obj.ViewObject.ShapeColor = (0.85, 0.70, 0.35)  # アンティークアンバー
            elif design_idx == 5:
                obj.ViewObject.ShapeColor = (0.20, 0.60, 0.85)  # オーシャンブルー
            elif design_idx == 6:
                obj.ViewObject.ShapeColor = (0.15, 0.15, 0.15)  # マットブラック

            obj.ViewObject.DisplayMode = "Flat Lines"

            bar.update(100, "画面を更新しています...")
            
            doc.recompute()
            FreeCADGui.activeView().fitAll()

FreeCADGui.addCommand('Ring_Button', Tool_MakeButton())