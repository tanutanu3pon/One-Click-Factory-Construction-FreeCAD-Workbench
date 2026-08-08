# -*- coding: utf-8 -*-
# Windows環境での日本語エンコード対応
import os
import FreeCAD
import FreeCADGui
import Part
import math
from PySide import QtWidgets

# Core/Progress.py から新設した進捗マネージャーをインポート
import Core.Progress as Progress

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
        # 1. デザインタイプの選択
        design_items = ["単純なボタン (標準)", "おしゃれなボタン (高級テーパー)", "かわいいボタン (ぷっくり厚口)"]
        design_text, ok0 = QtWidgets.QInputDialog.getItem(None, "デザイン選択", "ボタンのスタイル:", design_items, 0, False)
        if not ok0: return
        # ★英語化対策：選ばれた文字列が何番目にあるかでインデックスを取得
        design_idx = design_items.index(design_text) if design_text in design_items else 0

        # 2. ボタンの外径（直径）の入力
        d, ok1 = QtWidgets.QInputDialog.getDouble(None, "ボタン設計", "ボタンの直径 (mm):", 15.0, 5.0, 100.0, 1)
        if not ok1: return
        
        # 3. 全体の厚みの入力
        t, ok2 = QtWidgets.QInputDialog.getDouble(None, "ボタン設計", "全体の厚み (mm):", 3.0, 1.0, 20.0, 1)
        if not ok2: return

        # 4. 糸を通す穴の数の選択
        items = ["2つ穴 (標準)", "3つ穴 (トライアングル)", "4つ穴 (クロス)", "穴なし (パーツ用)"]
        item_text, ok3 = QtWidgets.QInputDialog.getItem(None, "穴の設定", "糸通し穴のタイプ:", items, 0, False)
        if not ok3: return
        # ★英語化対策：選ばれた文字列が何番目にあるかでインデックスを取得
        hole_idx = items.index(item_text) if item_text in items else 3

        if hole_idx == 0:
            hole_count = 2
        elif hole_idx == 1:
            hole_count = 3
        elif hole_idx == 2:
            hole_count = 4
        else:
            hole_count = 0

        # ボタン生成関数を呼び出し
        self.create_clothing_button(d, t, hole_count, design_idx)

    def create_clothing_button(self, d, t, hole_count, design_idx):
        bar = Progress.ProgressManager()
        bar.start(title="ボタンモデル生成", initial_text="デザインに合わせた輪郭を計算中...")

        doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
        
        r = d / 2.0             # ボタンの半径
        
        # --- 基本ソリッドの構築 ---
        base_cyl = Part.makeCylinder(r, t)
        button_shape = base_cyl

        # ==========================================
        # 2. デザイン別の削り出し・モデリング処理（★インデックス判定に変更）
        # ==========================================
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
            
        else:  # かわいいボタン (design_idx == 2)
            bar.update(25, "かわいいボタン：ふっくら丸い凹み形状を演算中...")
            rim_w = d * 0.18        
            inner_r = r - rim_w
            recess_d = t * 0.30     
            
            sphere_r = (inner_r * inner_r + recess_d * recess_d) / (2.0 * recess_d)
            sphere_cutter = Part.makeSphere(sphere_r)
            sphere_cutter.translate(FreeCAD.Vector(0, 0, t - recess_d + sphere_r))
            button_shape = button_shape.cut(sphere_cutter)

        # ==========================================
        # 3. 糸を通す穴をあける
        # ==========================================
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

        # ==========================================
        # 4. 外側のエッジ（角）を滑らかに丸める
        # ==========================================
        bar.update(75, "仕上げ加工：エッジの丸み（フィレット）を適用中...")
        edges_to_fillet = []
        for edge in button_shape.Edges:
            try:
                curve = edge.Curve
                if isinstance(curve, Part.Circle):
                    if abs(curve.Radius - r) < 0.001:
                        edges_to_fillet.append(edge)
            except:
                continue
                    
        if edges_to_fillet:
            try:
                # ★インデックス判定に変更
                fillet_r = t * 0.30 if design_idx == 2 else t * 0.15
                button_shape = button_shape.makeFillet(fillet_r, edges_to_fillet)
            except:
                pass

        bar.update(90, "不要な結合線をクリーニング中...")
        button_shape = button_shape.removeSplitter()

        # ==========================================
        # 5. FreeCADへの登録
        # ==========================================
        # ★インデックス判定に変更
        style_label = "Simple" if design_idx == 0 else "Stylish" if design_idx == 1 else "Cute"
        label = f"{style_label}_Button_{hole_count}Holes" if hole_count > 0 else f"{style_label}_Button_NoHole"
        obj = doc.addObject("Part::Feature", label)
        obj.Shape = button_shape
        
        # ★インデックス判定に変更
        if design_idx == 0:
            obj.ViewObject.ShapeColor = (0.95, 0.95, 0.93) 
        elif design_idx == 1:
            obj.ViewObject.ShapeColor = (0.25, 0.25, 0.28) 
        else:
            obj.ViewObject.ShapeColor = (1.0, 0.75, 0.8)  
            
        obj.ViewObject.DisplayMode = "Flat Lines"

        bar.update(100, "画面を更新しています...")
        bar.close()
        
        doc.recompute()
        FreeCADGui.activeView().fitAll()

# 登録
FreeCADGui.addCommand('Ring_Button', Tool_MakeButton())