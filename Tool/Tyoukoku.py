# -*- coding: utf-8 -*-
import os
import math
import FreeCAD
import FreeCADGui
import Part
import Draft

# 【修正】絶対インポートで安全にCoreモジュールを読み込む
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedInputDialog, translate_text
from Core.Language import get_language

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
        lang = get_language()
        doc = FreeCAD.activeDocument()
        if not doc:
            QtWidgets.QMessageBox.information(None, translate_text("通知", lang), translate_text("アクティブなドキュメントがありません。", lang))
            return

        ring_obj = next((o for o in reversed(doc.Objects) if "Size" in o.Label or "Ring" in o.Name or "Ring" in o.Label), None)
        if not ring_obj:
            ring_obj = next((o for o in reversed(doc.Objects) if hasattr(o, "Shape") and o.Shape and not o.Shape.isNull()), None)

        if not ring_obj:
            QtWidgets.QMessageBox.warning(None, translate_text("エラー", lang), translate_text("刻印対象となるリングモデルが見つかりません。", lang))
            return

        try:
            inner_r = min(math.sqrt(v.Point.x**2 + v.Point.y**2) for v in ring_obj.Shape.Vertexes)
        except Exception:
            inner_r = 8.0
        
        # 【修正】TranslatedInputDialog へ差し替え
        default_txt = "Takuya to Yui" if lang == "English" else "拓也 to 結衣"
        text, ok1 = TranslatedInputDialog.getText(None, "刻印設定", "彫る文字 (日本語対応):", text=default_txt)
        if not ok1 or not text: return

        font_size, ok2 = TranslatedInputDialog.getDouble(None, "寸法指定", "文字の大きさ (mm):", 1.2, 0.1, 10.0, 2)
        if not ok2: return

        depth, ok3 = TranslatedInputDialog.getDouble(None, "寸法指定", "彫刻の深さ (mm):", 0.3, 0.01, 2.0, 2)
        if not ok3: return

        self.execute_engrave(doc, ring_obj, text, font_size, depth, inner_r, lang)

    def _get_system_font(self):
        """クロスプラットフォーム＆絶対参照排除の動的フォント検索"""
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

    def execute_engrave(self, doc, ring_obj, text_str, font_size, depth, radius, lang):
        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("内面刻印処理", lang), initial_text=translate_text("OSの日本語フォントを探しています...", lang))

            font_path = self._get_system_font()
            if not font_path:
                QtWidgets.QMessageBox.critical(None, translate_text("エラー", lang), translate_text("利用可能なフォントが見つかりません。", lang))
                return

            doc.openTransaction("EngraveTextOnRing")

            try:
                char_angles = []
                total_angle = 0.0
                letter_spacing = font_size * 0.12

                for char in text_str:
                    if char == " ":
                        w = font_size * 0.5
                    else:
                        if hasattr(Draft, "make_shape_string"):
                            ss_temp = Draft.make_shape_string(String=char, FontFile=font_path, Size=font_size, Tracking=0)
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
                        msg_progress = f"Engraving character ({i+1}/{total_chars})..." if lang == "English" else f"立体文字を生成・内壁に配置中 ({i+1}/{total_chars}文字)..."
                        bar.update(loop_percent, msg_progress)

                    if char == " ":
                        if i < total_chars - 1:
                            current_angle -= (char_angles[i]/2.0 + char_angles[i+1]/2.0)
                        continue
                    
                    if hasattr(Draft, "make_shape_string"):
                        ss = Draft.make_shape_string(String=char, FontFile=font_path, Size=font_size, Tracking=0)
                    else:
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

                bar.update(80, translate_text("全文字を結合（コンパウンド作成）中...", lang))

                if compound_list:
                    bar.update(85, translate_text("リング内壁から文字データを減算（ブーリアンCut）中...", lang))
                    engraver = Part.makeCompound(compound_list)
                    result_shape = ring_obj.Shape.cut(engraver)
                    ring_obj.Shape = result_shape

                bar.update(100, translate_text("画面を更新しています...", lang))
                doc.commitTransaction()
                doc.recompute()

            except Exception as e:
                doc.abortTransaction()
                FreeCAD.Console.PrintError(f"Engraving error: {str(e)}\n")
                err_title = "Error" if lang == "English" else "エラー"
                err_msg = f"An error occurred during engraving:\n{str(e)}" if lang == "English" else f"刻印処理中にエラーが発生しました:\n{str(e)}"
                QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Ring_Tyoukoku', Tool_Tyoukoku())