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

class Tool_MakeHashi:
    def GetResources(self):
        current_dir = os.path.dirname(__file__)
        ring_dir = os.path.dirname(current_dir)
        icon_path = os.path.join(ring_dir, "icons", "hashi.png").replace('\\', '/')
        return {
            'Pixmap'  : icon_path,
            'MenuText': "お箸の作成",
            'ToolTip' : "角箸・丸箸・八角箸・モダン削り出しの4種類のお箸（一対）を生成します（進捗窓付き）"
        }

    def Activated(self):
        lang = get_language()

        types = [
            "角箸 (Square)",
            "丸箸 (Round)",
            "八角箸 (Octagonal)",
            "モダン削り出し (Modern Craft)"
        ]

        selected_type, ok0 = TranslatedInputDialog.getItem(None, "デザイン選択", "形状のタイプ:", types, 3, False)
        if not ok0: return

        trans_types = [translate_text(t, lang) for t in types]
        if selected_type in types:
            type_idx = types.index(selected_type)
        elif selected_type in trans_types:
            type_idx = trans_types.index(selected_type)
        else:
            type_idx = 3

        length, ok1 = TranslatedInputDialog.getDouble(None, "寸法指定", "箸の長さ (mm):", 225.0, 100.0, 350.0, 1)
        if not ok1: return

        head_w, ok2 = TranslatedInputDialog.getDouble(None, "寸法指定", "持ち手の太さ (mm):", 7.5, 3.0, 20.0, 1)
        if not ok2: return

        tip_w, ok3 = TranslatedInputDialog.getDouble(None, "寸法指定", "箸先の太さ (mm):", 2.0, 0.8, 10.0, 1)
        if not ok3: return

        if tip_w >= head_w:
            QtWidgets.QMessageBox.warning(None, translate_text("エラー", lang), translate_text("先端の太さは、根本より細くしてください。", lang))
            return

        self.create_hashi(type_idx, length, head_w, tip_w, lang)

    def make_section_wire(self, shape_type, width, z_pos):
        """全形状で同じ頂点数(16分割)を維持し、ロフト時の幾何破綻を防ぐ"""
        r = width / 2.0
        num_pts = 16
        pts = []

        for i in range(num_pts):
            ang = math.radians(360.0 / num_pts * i)
            cos_a = math.cos(ang)
            sin_a = math.sin(ang)

            # [1] 丸型 (円)
            if shape_type == 1:
                dist = r
            # [2] 八角形
            elif shape_type == 2:
                # 45度周期で八角形の外周点を計算
                ang_oct = (ang + math.pi / 8.0) % (math.pi / 4.0) - (math.pi / 8.0)
                dist = r / math.cos(ang_oct)
            # [0] 正方形
            else:
                max_c = max(abs(cos_a), abs(sin_a))
                dist = r / max_c if max_c > 1e-6 else r

            pts.append(FreeCAD.Vector(dist * cos_a, dist * sin_a, z_pos))

        pts.append(pts[0])
        return Part.makePolygon(pts)

    def create_single_chopstick(self, type_idx, L, head_w, tip_w):
        """1本のお箸ソリッドを構築"""
        # --- 1. 角箸 (Square) ---
        if type_idx == 0:
            w_tip = self.make_section_wire(0, tip_w, 0)
            w_head = self.make_section_wire(0, head_w, L)
            solid = Part.makeLoft([w_tip, w_head], True)
            try:
                solid = solid.makeFillet(0.6, solid.Edges)
            except Exception:
                pass

        # --- 2. 丸箸 (Round) ---
        elif type_idx == 1:
            w_tip = self.make_section_wire(1, tip_w, 0)
            w_head = self.make_section_wire(1, head_w, L)
            solid = Part.makeLoft([w_tip, w_head], True)

        # --- 3. 八角箸 (Octagonal) ---
        elif type_idx == 2:
            w_tip = self.make_section_wire(1, tip_w, 0)
            w_mid = self.make_section_wire(2, tip_w * 1.5, L * 0.12)
            w_head = self.make_section_wire(2, head_w, L)
            solid = Part.makeLoft([w_tip, w_mid, w_head], True)

        # --- 4. モダン削り出し (Modern Craft) ---
        else:
            # 16頂点の同位相ワイヤーで「丸 → 正方形 → 四角斜め変形 → 八角形」へ滑らかに遷移
            w_tip = self.make_section_wire(1, tip_w, 0)
            w_mid1 = self.make_section_wire(0, head_w * 0.55, L * 0.35)
            w_mid2 = self.make_section_wire(0, head_w * 0.85, L * 0.70)
            w_head = self.make_section_wire(2, head_w, L)
            solid = Part.makeLoft([w_tip, w_mid1, w_mid2, w_head], True)

        # 持ち手頭部（天面）のエッジフィレット処理（安全マージン適用）
        try:
            top_edges = [e for e in solid.Edges if abs(e.BoundBox.ZMax - L) < 0.05 and abs(e.BoundBox.ZMin - L) < 0.05]
            if top_edges:
                solid = solid.makeFillet(min(head_w * 0.08, 0.5), top_edges)
        except Exception:
            pass

        return solid

    def create_hashi(self, type_idx, L, head_w, tip_w, lang):
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
        
        try:
            doc.openTransaction("Create Hashi Model")
            with Progress.ProgressManager() as bar:
                bar.start(title=translate_text("3Dモデル生成", lang), initial_text=translate_text("基本形状を計算中...", lang))

                bar.update(30, translate_text("お箸（左）を成形中...", lang))
                single_hashi = self.create_single_chopstick(type_idx, L, head_w, tip_w)

                bar.update(65, translate_text("一対（2本組）に配置中...", lang))
                gap = head_w * 1.6
                
                hashi_left = single_hashi.copy()
                hashi_left.translate(FreeCAD.Vector(-gap / 2.0, 0, 0))

                hashi_right = single_hashi.copy()
                hashi_right.translate(FreeCAD.Vector(gap / 2.0, 0, 0))

                bar.update(85, translate_text("パーツを複合化中...", lang))
                pair_shape = Part.makeCompound([hashi_left, hashi_right])
                pair_shape = pair_shape.removeSplitter()

                label_names = ["Hashi_Square", "Hashi_Round", "Hashi_Octagonal", "Hashi_Modern"]
                obj = doc.addObject("Part::Feature", label_names[type_idx])
                obj.Shape = pair_shape
                obj.ViewObject.DisplayMode = "Flat Lines"

                if type_idx == 0:
                    obj.ViewObject.ShapeColor = (0.55, 0.35, 0.20)
                elif type_idx == 1:
                    obj.ViewObject.ShapeColor = (0.85, 0.75, 0.55)
                elif type_idx == 2:
                    obj.ViewObject.ShapeColor = (0.20, 0.15, 0.15)
                else:
                    obj.ViewObject.ShapeColor = (0.75, 0.20, 0.20)

                if hasattr(obj.ViewObject, "Shininess"):
                    obj.ViewObject.Shininess = 0.6

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

FreeCADGui.addCommand('Ring_MakeHashi', Tool_MakeHashi())