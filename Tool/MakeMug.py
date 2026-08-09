# -*- coding: utf-8 -*-
import os
import math
import FreeCAD
import FreeCADGui
import Part

# 【修正】絶対インポートで安全にCoreモジュールを読み込む
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedInputDialog, translate_text
from Core.Language import get_language

class Tool_MakeMugSimple:
    def GetResources(self):
        current_dir = os.path.dirname(__file__)
        ring_dir = os.path.dirname(current_dir)
        icon_path = os.path.join(ring_dir, "icons", "mug.png").replace('\\', '/')
        return {
            'Pixmap'  : icon_path,
            'MenuText': "カップ・グラス類の作成",
            'ToolTip' : "マグカップ、波型湯呑み、おちょこ、ショットグラス、ワイングラスを生成します（進捗窓付き）"
        }

    def Activated(self):
        lang = get_language()

        types = [
            "マグカップ (標準取っ手付き)",
            "湯呑み (手になじむ波型グリップ)",
            "おちょこ (日本酒用)",
            "ショットグラス (厚底)",
            "ワイングラス (脚付き)"
        ]

        selected_type, ok0 = TranslatedInputDialog.getItem(None, "グラス・カップ設計", "器のタイプ:", types, 0, False)
        if not ok0: return

        trans_types = [translate_text(t, lang) for t in types]
        if selected_type in types:
            type_idx = types.index(selected_type)
        elif selected_type in trans_types:
            type_idx = trans_types.index(selected_type)
        else:
            type_idx = 0

        default_h = [90.0, 80.0, 45.0, 60.0, 140.0][type_idx]
        default_d = [80.0, 65.0, 50.0, 45.0, 65.0][type_idx]
        default_w = [4.0, 4.0, 3.0, 3.5, 2.0][type_idx]

        h, ok1 = TranslatedInputDialog.getDouble(None, "設計", "全体の高さ (mm):", default_h, 10.0, 300.0, 1)
        if not ok1: return

        d, ok2 = TranslatedInputDialog.getDouble(None, "設計", "最大外径 (mm):", default_d, 10.0, 200.0, 1)
        if not ok2: return

        w, ok3 = TranslatedInputDialog.getDouble(None, "設計", "壁の肉厚 (mm):", default_w, 1.0, 20.0, 1)
        if not ok3: return

        self.create_cup(type_idx, h, d, w, lang)

    def _apply_lip_fillet(self, shape, target_z, fillet_r):
        """口元（飲み口）のエッジを検出してなめらかにフィレット"""
        rim_edges = []
        for e in shape.Edges:
            bb = e.BoundBox
            if abs(bb.ZMax - target_z) < 0.8 and abs(bb.ZMin - target_z) < 0.8:
                rim_edges.append(e)
        if rim_edges:
            try:
                return shape.makeFillet(fillet_r, rim_edges)
            except Exception:
                pass
        return shape

    def create_cup(self, type_idx, h, d, w, lang):
        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("カップ・グラス生成", lang), initial_text=translate_text("基本形状を計算中...", lang))

            doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
            r_outer = d / 2.0
            r_inner = max(r_outer - w, 0.5)

            # --- 1. マグカップ (取っ手付き) ---
            if type_idx == 0:
                bar.update(20, translate_text("マグカップ本体を成形中...", lang))
                outer_cyl = Part.makeCylinder(r_outer, h)
                inner_cyl = Part.makeCylinder(r_inner, h, FreeCAD.Vector(0, 0, w))
                body_shape = outer_cyl.cut(inner_cyl)

                bar.update(60, translate_text("C型取っ手をスイープ生成中...", lang))
                handle_h = h * 0.6
                handle_w = r_outer * 0.5
                handle_r = w * 0.8
                z_center = h / 2.0

                p1 = FreeCAD.Vector(r_outer - 0.5, 0, z_center + handle_h / 2.0)
                p2 = FreeCAD.Vector(r_outer + handle_w, 0, z_center)
                p3 = FreeCAD.Vector(r_outer - 0.5, 0, z_center - handle_h / 2.0)

                arc = Part.Arc(p1, p2, p3)
                wire_path = Part.Wire([arc.toShape()])
                circle_profile = Part.makeCircle(handle_r, p1, FreeCAD.Vector(1, 0, 0))
                wire_profile = Part.Wire([Part.Edge(circle_profile)])
                
                handle_shape = wire_path.makePipeShell([wire_profile], True, False)

                bar.update(85, translate_text("本体と取っ手を一体化中...", lang))
                cup_shape = body_shape.fuse(handle_shape)
                label_name = "Mug_Cup"
                color = (0.90, 0.90, 0.95)

            # --- 2. 湯呑み (口元フィレット一体成形型) ---
            elif type_idx == 1:
                bar.update(30, translate_text("手にフィットする波型胴体を計算中...", lang))
                num_pts = 60
                profile_pts = []
                wave_amp = 1.2
                wave_freq = 4.0
                
                # 外側の波型プロフィール
                for i in range(num_pts + 1):
                    z_curr = (h * i) / num_pts
                    r_curr = r_outer + wave_amp * math.sin(wave_freq * math.pi * (z_curr / h))
                    profile_pts.append(FreeCAD.Vector(r_curr, 0, z_curr))
                
                p_out_top = profile_pts[-1]
                p_in_top = FreeCAD.Vector(r_inner, 0, h)
                
                # 【修正】口元に丸みをもたせるアーチ状の2D曲線を作成
                p_lip_mid = FreeCAD.Vector((p_out_top.x + r_inner) / 2.0, 0, h + w * 0.35)
                arc_lip = Part.Arc(p_out_top, p_lip_mid, p_in_top).toShape()

                edge_outer = Part.makePolygon(profile_pts)
                
                bottom_thick = w * 1.5
                edge_inner = Part.makePolygon([
                    p_in_top,
                    FreeCAD.Vector(r_inner, 0, bottom_thick),
                    FreeCAD.Vector(0, 0, bottom_thick),
                    FreeCAD.Vector(0, 0, 0),
                    profile_pts[0]
                ])

                wire = Part.Wire([edge_outer, arc_lip, edge_inner])
                face = Part.Face(wire)
                cup_shape = face.revolve(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), 360)

                label_name = "Yunomi_Wavy"
                color = (0.35, 0.45, 0.35)

            # --- 3. おちょこ (日本酒用テーパー型) ---
            elif type_idx == 2:
                bar.update(30, translate_text("おちょこの広がり輪郭を計算中...", lang))
                r_bottom_out = r_outer * 0.70
                r_bottom_in = max(r_bottom_out - w, 0.3)

                outer_cone = Part.makeCone(r_bottom_out, r_outer, h)
                inner_cone = Part.makeCone(r_bottom_in, r_inner, h, FreeCAD.Vector(0, 0, w))
                cup_shape = outer_cone.cut(inner_cone)

                label_name = "Ochoko_SakeCup"
                color = (0.95, 0.95, 0.90)

            # --- 4. ショットグラス (重厚厚底) ---
            elif type_idx == 3:
                bar.update(30, translate_text("ショットグラスの厚底構造を成形中...", lang))
                bottom_thick = max(w * 3.5, h * 0.30)

                outer_cyl = Part.makeCylinder(r_outer, h)
                inner_cyl = Part.makeCylinder(r_inner, h, FreeCAD.Vector(0, 0, bottom_thick))
                cup_shape = outer_cyl.cut(inner_cyl)

                label_name = "Shot_Glass"
                color = (0.80, 0.90, 0.95)

            # --- 5. ワイングラス (回転成形方式) ---
            else:
                bar.update(20, translate_text("ワイングラスの優美な断面プロファイルを計算中...", lang))
                
                base_h = 3.5
                stem_h = h * 0.42
                bowl_h = h - base_h - stem_h
                r_max = d / 2.0
                r_rim = r_max * 0.82
                r_stem = max(2.5, w * 1.1)
                r_base = max(r_max * 0.85, r_stem * 3.0)

                p0 = FreeCAD.Vector(0, 0, 0)
                p1 = FreeCAD.Vector(r_base, 0, 0)
                p2 = FreeCAD.Vector(r_base, 0, 1.0)
                p3 = FreeCAD.Vector(r_stem, 0, base_h)
                p4 = FreeCAD.Vector(r_stem, 0, base_h + stem_h)

                p5 = FreeCAD.Vector(r_max, 0, base_h + stem_h + bowl_h * 0.38)
                p6 = FreeCAD.Vector(r_rim, 0, h)

                p_rim_mid = FreeCAD.Vector(r_rim - w / 2.0, 0, h + w / 3.0)
                p7 = FreeCAD.Vector(r_rim - w, 0, h)

                p8 = FreeCAD.Vector(r_max - w, 0, base_h + stem_h + bowl_h * 0.40)
                p9 = FreeCAD.Vector(0, 0, base_h + stem_h + w * 1.8)

                l_bot = Part.makeLine(p0, p1)
                l_base_side = Part.makeLine(p1, p2)
                
                c_base = Part.BSplineCurve()
                c_base.buildFromPoles([p2, FreeCAD.Vector(r_stem * 1.8, 0, base_h * 0.5), p3])
                
                l_stem = Part.makeLine(p3, p4)

                c_bowl_out = Part.BSplineCurve()
                c_bowl_out.buildFromPoles([p4, p5, p6])

                arc_rim = Part.Arc(p6, p_rim_mid, p7).toShape()

                c_bowl_in = Part.BSplineCurve()
                c_bowl_in.buildFromPoles([p7, p8, p9])

                l_axis = Part.makeLine(p9, p0)

                wire = Part.Wire([
                    l_bot, l_base_side, c_base.toShape(), l_stem,
                    c_bowl_out.toShape(), arc_rim, c_bowl_in.toShape(), l_axis
                ])
                
                face = Part.Face(wire)
                
                bar.update(70, translate_text("360度回転成形（Revolve）中...", lang))
                cup_shape = face.revolve(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), 360)
                label_name = "Wine_Glass"
                color = (0.85, 0.92, 0.98)

            # マグ、おちょこ、ショットグラスに飲み口フィレットを適用
            if type_idx in (0, 2, 3):
                bar.update(90, translate_text("口元（飲み口）の角を丸め加工（フィレット）中...", lang))
                lip_fillet_r = min(w * 0.4, 1.5)
                cup_shape = self._apply_lip_fillet(cup_shape, h, lip_fillet_r)

            bar.update(95, translate_text("不要なシーム線を消去して最適化中...", lang))
            cup_shape = cup_shape.removeSplitter()

            obj = doc.addObject("Part::Feature", label_name)
            obj.Shape = cup_shape
            obj.ViewObject.ShapeColor = color
            if type_idx in (3, 4):
                obj.ViewObject.Transparency = 50
            obj.ViewObject.DisplayMode = "Flat Lines"

            bar.update(100, translate_text("画面を更新しています...", lang))

            doc.recompute()
            FreeCADGui.activeView().fitAll()

FreeCADGui.addCommand('Ring_Mug', Tool_MakeMugSimple())