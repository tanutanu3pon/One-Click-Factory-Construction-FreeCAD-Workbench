# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui

# 【修正】絶対インポートで安全にCoreモジュールを読み込む
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import translate_text
from Core.Language import get_language

class Tool_Weight:
    def GetResources(self):
        current_dir = os.path.dirname(__file__) 
        ring_dir = os.path.dirname(current_dir) 
        icon_path = os.path.join(ring_dir, "icons", "weight.png").replace('\\', '/')
        
        return {
            'Pixmap'  : icon_path, 
            'MenuText': "地金・樹脂重量計算",
            'ToolTip' : "選択したモデルの体積から、各貴金属および3Dプリント用フィラメントの重量(g)を計算します（進捗窓付き）"
        }

    def Activated(self):
        lang = get_language()
        sel = FreeCADGui.Selection.getSelection()
        
        if not sel:
            QtWidgets.QMessageBox.warning(None, translate_text("エラー", lang), translate_text("重さを量りたいモデルを選択してから実行してください。", lang))
            return

        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("重量計算システム", lang), initial_text=translate_text("選択されたオブジェクトを解析中...", lang))

            total_volume_mm3 = 0.0
            total_objects = len(sel)
            
            for idx, obj in enumerate(sel):
                if total_objects > 0:
                    loop_percent = int(20 + (30 * (idx / total_objects)))
                    msg_prog = f"Measuring 3D volume ({idx+1}/{total_objects})..." if lang == "English" else f"モデルの3D体積（メッシュ構造）を計測中 ({idx+1}/{total_objects})..."
                    bar.update(loop_percent, msg_prog)

                if hasattr(obj, "Shape") and not obj.Shape.isNull():
                    total_volume_mm3 += obj.Shape.Volume
            
            if total_volume_mm3 <= 0:
                QtWidgets.QMessageBox.warning(None, translate_text("エラー", lang), translate_text("体積を持たないオブジェクトです。立体モデルを選択してください。", lang))
                return

            bar.update(65, translate_text("体積単位を mm3 から cm3 へ変換中...", lang))
            volume_cm3 = total_volume_mm3 / 1000.0

            bar.update(80, translate_text("各貴金属および3Dプリンター用樹脂の比重から重量を試算中...", lang))

            metals = {
                "シルバー (SV925)": 10.4,
                "10金 (K10 ゴールド)": 11.6,
                "18金 (K18 ゴールド)": 15.5,
                "純金 (K24)": 19.3,
                "プラチナ (Pt950)": 20.5,
                "真鍮 (Brass)": 8.5
            }

            filaments = {
                "PLA フィラメント": 1.24,       
                "ABS フィラメント": 1.04,       
                "PETG フィラメント": 1.27,      
                "TPU (フレキシブル)": 1.21,     
                "UV造形レジン (光造形)": 1.15   
            }

            if lang == "English":
                result_text = f"Total Volume : {volume_cm3:.3f} cm3\n\n"
                result_text += "[ Precious Metals Weight ]\n"
                result_text += "-" * 35 + "\n"
                for metal, density in metals.items():
                    trans_metal = translate_text(metal, lang)
                    weight = volume_cm3 * density
                    result_text += f"  {trans_metal:<20} : {weight:.2f} g\n"

                result_text += "\n"
                result_text += "[ 3D Printer Resins Weight ]\n"
                result_text += "-" * 35 + "\n"
                for plastic, density in filaments.items():
                    trans_plastic = translate_text(plastic, lang)
                    weight = volume_cm3 * density
                    result_text += f"  {trans_plastic:<20} : {weight:.2f} g\n"
            else:
                result_text = f"合計体積 : {volume_cm3:.3f} cm3\n\n"
                result_text += "【 ジュエリー用貴金属 重量 】\n"
                result_text += "-" * 35 + "\n"
                for metal, density in metals.items():
                    weight = volume_cm3 * density
                    result_text += f"  {metal:<16} : {weight:.2f} g\n"

                result_text += "\n"
                result_text += "【 3Dプリンター用樹脂 重量 】\n"
                result_text += "-" * 35 + "\n"
                for plastic, density in filaments.items():
                    weight = volume_cm3 * density
                    result_text += f"  {plastic:<16} : {weight:.2f} g\n"

            bar.update(95, translate_text("計算結果レポートを構築中...", lang))
            bar.update(100, translate_text("計算完了！", lang))

        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle(translate_text("重量 (グラム) 計算結果", lang))
        msg.setText(translate_text("選択したモデルの推定重量です。", lang))
        msg.setInformativeText(result_text)
        msg.setIcon(QtWidgets.QMessageBox.Information) 
        msg.exec_()

FreeCADGui.addCommand('Ring_Weight', Tool_Weight())