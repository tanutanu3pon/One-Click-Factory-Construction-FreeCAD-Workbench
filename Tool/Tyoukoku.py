# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part
import Draft
import math
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress

class Tool_Tyoukoku:
    def GetResources(self):
        current_dir = os.path.dirname(__file__) 
        ring_dir = os.path.dirname(current_dir) 
        icon_path = os.path.join(ring_dir, "icons", "tyoukoku.png").replace('\\', '/')
        
        return {
            'Pixmap'  : icon_path, 
            'MenuText': "内面刻印（左から右）",
            'ToolTip' : "ひらがな・カタカナ・漢字・英数字をリングの内壁に彫刻します（進捗窓付き）"
        }

    def Activated(self):
        doc = FreeCAD.activeDocument()
        if not doc: return

        ring_obj = next((o for o in reversed(doc.Objects) if "Size" in o.Label), None)
        if not ring_obj:
            # ★ 修正: PySide6 互換の QtWidgets へ書き換え
            QtWidgets.QMessageBox.warning(None, "エラー", "リングが見つかりません。")
            return

        try:
            inner_r = min(math.sqrt(v.Point.x**2 + v.Point.y**2) for v in ring_obj.Shape.Vertexes)
        except Exception:
            inner_r = 8.0
        
        # ★ 修正: PySide6 互換の QtWidgets へ書き換え
        text, ok1 = QtWidgets.QInputDialog.getText(None, "刻印設定", "彫る文字 (日本語対応):", text="拓也 to 結衣")
        if not ok1 or not text: return

        font_size, ok2 = QtWidgets.QInputDialog.getDouble(None, "寸法指定", "文字の大きさ (mm):", 1.2, 0.1, 10.0, 2)
        if not ok2: return

        depth, ok3 = QtWidgets.QInputDialog.getDouble(None, "寸法指定", "彫刻の深さ (mm):", 0.3, 0.01, 2.0, 2)
        if not ok3: return

        self.execute_engrave(doc, ring_obj, text, font_size, depth, inner_r)

    def _get_system_font(self):
        """★ 修正: クロスプラットフォーム＆絶対参照排除の動的フォント検索"""
        current_dir = os.path.dirname(__file__)
        wb_dir = os.path.dirname(current_dir)
        fonts_dir = os.path.join(wb_dir, "fonts")
        
        if os.path.exists(fonts_dir):
            for f in os.listdir(fonts_dir):
                if f.lower().endswith(('.ttf', '.otf', '.ttc')):
                    return os.path.join(fonts_dir, f)

        candidates = [
            r"C:\Windows\Fonts\meiryo.ttc",
            r"C:\Windows\Fonts\msgothic.ttc",
            r"C:\Windows\Fonts\arialbd.ttf",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return ""

    def execute_engrave(self, doc, ring_obj, text_str, font_size, depth, radius):
        with Progress.ProgressManager() as bar:
            bar.start(title="内面刻印処理", initial_text="OSの日本語フォントを探しています...")

            font_path = self._get_system_font()
            if not font_path:
                QtWidgets.QMessageBox.critical(None, "エラー", "利用可能なフォントが見つかりません。")
                return

            char_angles = []
            total_angle = 0.0
            letter_spacing = font_size * 0.12

            for char in text_str:
                if char == " ":
                    w = font_size * 0.5
                else:
                    ss_temp = Draft.makeShapeString(char, font_path, font_size)
                    doc.recompute()
                    bbox = ss_temp.Shape.BoundBox
                    w = bbox.XMax - bbox.XMin
                    if w < font_size * 0.15:
                        w = font_size * 0.4
                    doc.removeObject(ss_temp.Name)
                
                ang = math.degrees((w + letter_spacing) / radius)
                char_angles.append(ang)
                total_angle += ang

            current_angle = (total_angle / 2.0) - (char_angles[0] / 2.0)

            compound_list = []
            total_chars = len(text_str)

            for i, char in enumerate(text_str):
                if total_chars > 0:
                    loop_percent = int(10 + (65 * (i / total_chars)))
                    bar.update(loop_percent, f"立体文字を生成・内壁に配置中 ({i+1}/{total_chars}文字)...")

                if char == " ":
                    if i < total_chars - 1:
                        current_angle -= (char_angles[i]/2.0 + char_angles[i+1]/2.0)
                    continue
                
                ss = Draft.makeShapeString(char, font_path, font_size)
                doc.recompute()
                
                bbox = ss.Shape.BoundBox
                center_x = (bbox.XMax + bbox.XMin) / 2.0
                center_y = (bbox.YMax + bbox.YMin) / 2.0
                
                extrude_len = depth + 0.5
                char_shape = ss.Shape.extrude(FreeCAD.Vector(0, 0, extrude_len))
                
                char_shape.translate(FreeCAD.Vector(-center_x, -center_y, 0))
                
                char_shape.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(1,0,0), 90)
                char_shape.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), -90)
                
                char_shape.translate(FreeCAD.Vector(radius - 0.1, 0, 0))
                
                char_shape.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), current_angle)
                
                compound_list.append(char_shape)
                doc.removeObject(ss.Name)
                
                if i < total_chars - 1:
                    current_angle -= (char_angles[i]/2.0 + char_angles[i+1]/2.0)

            bar.update(80, "全文字を結合（コンパウンド作成）中...")

            if compound_list:
                try:
                    bar.update(85, "リング内壁から文字データを減算（ブーリアンCut）中...")
                    engraver = Part.makeCompound(compound_list)
                    result_shape = ring_obj.Shape.cut(engraver)
                    ring_obj.Shape = result_shape
                except Exception as e:
                    FreeCAD.Console.PrintError(f"カット失敗: {str(e)}\n")
                    return

            bar.update(100, "画面を更新しています...")
            doc.recompute()

FreeCADGui.addCommand('Ring_Tyoukoku', Tool_Tyoukoku())