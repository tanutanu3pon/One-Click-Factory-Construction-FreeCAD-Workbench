# -*- coding: utf-8 -*-
import os
import math
import FreeCAD
import FreeCADGui
import Part

from Core.QtCompat import QtWidgets
import Core.Progress as Progress
from Core.Controller import TranslatedInputDialog, translate_text
from Core.Language import get_language

class Tool_MakeHashioki:
    def GetResources(self):
        current_dir = os.path.dirname(__file__)
        ring_dir = os.path.dirname(current_dir)
        icon_path = os.path.join(ring_dir, "icons", "hashioki.png").replace('\\', '/')
        return {
            'Pixmap'  : icon_path,
            'MenuText': "箸置きの作成",
            'ToolTip' : "普通の形からおしゃれなデザインまで、4種類の箸置きを生成します（進捗窓付き）"
        }

    def Activated(self):
        lang = get_language()

        types = [
            "普通の箸置き (Standard)",
            "デザインチック (Geometric Twist)",
            "かわいいやつ (Cute Bean)",
            "おしゃれなやつ (Elegant Wave)"
        ]

        selected_type, ok0 = TranslatedInputDialog.getItem(None, "デザイン選択", "形状のタイプ:", types, 0, False)
        if not ok0: return

        trans_types = [translate_text(t, lang) for t in types]
        if selected_type in types:
            type_idx = types.index(selected_type)
        elif selected_type in trans_types:
            type_idx = trans_types.index(selected_type)
        else:
            type_idx = 0

        length, ok1 = TranslatedInputDialog.getDouble(None, "寸法指定", "全体の長さ (mm):", 50.0, 20.0, 150.0, 1)
        if not ok1: return

        self.create_hashioki(type_idx, length, lang)

    def create_hashioki(self, type_idx, L, lang):
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
        
        try:
            doc.openTransaction("Create Hashioki Model")
            with Progress.ProgressManager() as bar:
                bar.start(title=translate_text("3Dモデル生成", lang), initial_text=translate_text("基本形状を計算中...", lang))

                # --- 1. 普通の箸置き (Standard) ---
                if type_idx == 0:
                    bar.update(30, translate_text("基本形状を配置中...", lang))
                    W = L * 0.35
                    H = L * 0.25
                    box = Part.makeBox(L, W, H, FreeCAD.Vector(-L/2.0, -W/2.0, 0))
                    
                    cyl_r = L * 0.6
                    cut_z = H + cyl_r - (L * 0.08)
                    cyl = Part.makeCylinder(cyl_r, W + 10, FreeCAD.Vector(0, -W/2.0 - 5.0, cut_z), FreeCAD.Vector(0, 1, 0))
                    
                    bar.update(60, translate_text("中をくり抜き中...", lang))
                    shape = box.cut(cyl)
                    
                    bar.update(80, translate_text("先端とエッジの角丸（フィレット）加工中...", lang))
                    try: 
                        shape = shape.makeFillet(1.5, shape.Edges)
                    except Exception: 
                        pass
                    
                    label_name = "Hashioki_Standard"
                    color = (0.75, 0.60, 0.40)

                # --- 2. デザインチック (Geometric Twist) --- [修正]
                elif type_idx == 1:
                    bar.update(30, translate_text("断面を繋いでロフト化中...", lang))
                    W = L * 0.28
                    H = L * 0.22
                    num_sections = 11
                    wires = []
                    
                    sw = W / 2.0
                    sh = H / 2.0
                    
                    for i in range(num_sections):
                        t = i / (num_sections - 1.0)
                        x = -L/2.0 + L * t
                        angle = t * 90.0  # 自己交差を防ぐため90度回転へ最適化
                        rad = math.radians(angle)
                        
                        z_drop = (H * 0.25) * math.sin(math.pi * t)
                        
                        pts_local = [
                            FreeCAD.Vector(0, -sw, -sh),
                            FreeCAD.Vector(0, sw, -sh),
                            FreeCAD.Vector(0, sw, sh),
                            FreeCAD.Vector(0, -sw, sh),
                            FreeCAD.Vector(0, -sw, -sh)
                        ]
                        
                        # 手動座標変換で幾何エラーを回避
                        pts_world = []
                        cos_a = math.cos(rad)
                        sin_a = math.sin(rad)
                        for p in pts_local:
                            y_rot = p.y * cos_a - p.z * sin_a
                            z_rot = p.y * sin_a + p.z * cos_a
                            pts_world.append(FreeCAD.Vector(x, y_rot, z_rot + sh - z_drop))
                            
                        wire = Part.makePolygon(pts_world)
                        wires.append(wire)
                        
                    bar.update(70, translate_text("複雑な曲面を接合中（ロフト立体化）...", lang))
                    shape = Part.makeLoft(wires, True)
                    
                    try:
                        shape = shape.makeFillet(0.8, shape.Edges)
                    except Exception:
                        pass
                        
                    label_name = "Hashioki_Design"
                    color = (0.25, 0.25, 0.25)

                # --- 3. かわいいやつ (Cute Bean / そら豆) --- [修正]
                elif type_idx == 2:
                    bar.update(30, translate_text("基本形状を計算中...", lang))
                    W = L * 0.55
                    H = L * 0.28
                    
                    poles = [
                        FreeCAD.Vector(-L*0.45, 0, 0),
                        FreeCAD.Vector(-L*0.35, W*0.5, 0),
                        FreeCAD.Vector(L*0.1, W*0.5, 0),
                        FreeCAD.Vector(L*0.45, W*0.2, 0),
                        FreeCAD.Vector(L*0.45, -W*0.2, 0),
                        FreeCAD.Vector(0, W*0.12, 0),
                        FreeCAD.Vector(-L*0.35, -W*0.38, 0),
                        FreeCAD.Vector(-L*0.45, 0, 0)
                    ]
                    
                    c = Part.BSplineCurve()
                    c.buildFromPoles(poles)
                    wire_base = Part.Wire([c.toShape()])
                    face = Part.Face(wire_base)
                    
                    bar.update(50, translate_text("ソリッドに押し出し（Extrude）中...", lang))
                    shape = face.extrude(FreeCAD.Vector(0, 0, H))
                    
                    # 全体エッジへ大きな丸み加工を先行適用（ぷっくり化）
                    bar.update(70, translate_text("角を丸めてかわいらしいシルエットへ加工中...", lang))
                    fillet_r = min(H * 0.3, 2.5)
                    try:
                        shape = shape.makeFillet(fillet_r, shape.Edges)
                    except Exception:
                        valid_edges = [e for e in shape.Edges if e.Length > 1.0]
                        try:
                            shape = shape.makeFillet(1.2, valid_edges)
                        except Exception:
                            pass

                    # 箸置き用の滑らかな上面くぼみ加工
                    dimple_r = L * 0.45
                    dimple = Part.makeCylinder(dimple_r, W * 2.0, FreeCAD.Vector(0, -W, H + dimple_r - H*0.18), FreeCAD.Vector(0, 1, 0))
                    shape = shape.cut(dimple)
                    
                    try:
                        shape = shape.makeFillet(0.6, shape.Edges)
                    except Exception:
                        pass
                    
                    label_name = "Hashioki_Cute"
                    color = (0.60, 0.85, 0.60)

                # --- 4. おしゃれなやつ (Elegant Wave / 波型) ---
                else:
                    bar.update(30, translate_text("デザインに合わせた輪郭を計算中...", lang))
                    W = L * 0.25
                    H = L * 0.25
                    T = H * 0.35
                    
                    poles_top = [
                        FreeCAD.Vector(-L/2.0, 0, H*0.3),
                        FreeCAD.Vector(-L/4.0, 0, H),
                        FreeCAD.Vector(0, 0, H*0.3),
                        FreeCAD.Vector(L/4.0, 0, H),
                        FreeCAD.Vector(L/2.0, 0, H*0.3)
                    ]
                    c_top = Part.BSplineCurve()
                    c_top.buildFromPoles(poles_top)
                    
                    poles_bot = [
                        FreeCAD.Vector(L/2.0, 0, H*0.3 - T),
                        FreeCAD.Vector(L/4.0, 0, H - T),
                        FreeCAD.Vector(0, 0, H*0.3 - T),
                        FreeCAD.Vector(-L/4.0, 0, H - T),
                        FreeCAD.Vector(-L/2.0, 0, H*0.3 - T)
                    ]
                    c_bot = Part.BSplineCurve()
                    c_bot.buildFromPoles(poles_bot)
                    
                    edge_top = c_top.toShape()
                    edge_bot = c_bot.toShape()
                    edge_right = Part.makeLine(poles_top[-1], poles_bot[0])
                    edge_left = Part.makeLine(poles_bot[-1], poles_top[0])
                    
                    wire = Part.Wire([edge_top, edge_right, edge_bot, edge_left])
                    face = Part.Face(wire)
                    
                    bar.update(60, translate_text("ソリッドに押し出し（Extrude）中...", lang))
                    shape = face.extrude(FreeCAD.Vector(0, W, 0))
                    shape.translate(FreeCAD.Vector(0, -W/2.0, 0))
                    
                    bar.update(80, translate_text("先端とエッジの角丸（フィレット）加工中...", lang))
                    try: 
                        shape = shape.makeFillet(1.0, shape.Edges)
                    except Exception: 
                        pass
                    
                    label_name = "Hashioki_Elegant"
                    color = (0.95, 0.95, 0.98)

                bar.update(90, translate_text("不要なシーム線を消去して最適化中...", lang))
                shape = shape.removeSplitter()

                obj = doc.addObject("Part::Feature", label_name)
                obj.Shape = shape
                obj.ViewObject.ShapeColor = color
                obj.ViewObject.DisplayMode = "Flat Lines"
                if hasattr(obj.ViewObject, "Shininess"):
                    obj.ViewObject.Shininess = 0.8

                doc.commitTransaction()
                doc.recompute()

                bar.update(100, translate_text("画面を更新しています...", lang))
                if FreeCADGui.activeView():
                    FreeCADGui.activeView().viewAxometric()
                    FreeCADGui.activeView().fitAll()

        except Exception as e:
            doc.abortTransaction()
            err_title = "Error" if lang == "English" else "エラー"
            err_msg = f"An error occurred during processing:\n{str(e)}" if lang == "English" else f"処理中にエラーが発生しました:\n{str(e)}"
            QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Ring_MakeHashioki', Tool_MakeHashioki())