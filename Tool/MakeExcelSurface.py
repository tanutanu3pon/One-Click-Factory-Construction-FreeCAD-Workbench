# -*- coding: utf-8 -*-
import os
import zipfile
import xml.etree.ElementTree as ET
import FreeCAD
import FreeCADGui
import Part
import Mesh

# 【修正】絶対インポートで安全にCoreモジュールを読み込む
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedInputDialog, translate_text
from Core.Language import get_language

class Tool_MakeExcelSurface:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "survey.png").replace('\\', '/')
        
        if not os.path.exists(icon_path):
            FreeCAD.Console.PrintWarning(f"[警告] アイコン画像が見つかりません: {icon_path}\n")

        return {
            'Pixmap': icon_path, 
            'MenuText': "エクセル座標読み込み", 
            'ToolTip': "エクセルのXYZ座標からサーフェス（メッシュ）を作成します"
        }

    def Activated(self):
        lang = get_language()

        try:
            from scipy.spatial import Delaunay
            import numpy as np
        except ImportError:
            err_title = "Missing Libraries" if lang == "English" else "ライブラリ不足"
            err_msg = (
                "The 'scipy' and 'numpy' libraries are required for surface (mesh) calculation.\n"
                "Please install scipy in your Python environment."
            ) if lang == "English" else (
                "サーフェス（メッシュ）の計算には 'scipy' および 'numpy' ライブラリが必要です。\n"
                "Python環境に scipy を導入してください。"
            )
            QtWidgets.QMessageBox.critical(None, err_title, err_msg)
            return

        guide_title = "Information" if lang == "English" else "ご案内"
        guide_msg = (
            "Select an Excel file (.xlsx) or CSV file.\n"
            "Column A = X, Column B = Y, Column C = Z."
        ) if lang == "English" else (
            "エクセルファイル（.xlsx）を選択します。A列はX軸座標、B列はY軸座標、C列はZ軸座標とします。"
        )
        QtWidgets.QMessageBox.information(None, guide_title, guide_msg)
        
        file_filters = "Excel / CSV Files (*.xlsx *.csv);;Excel Files (*.xlsx);;CSV Files (*.csv);;All Files (*)"
        dialog_title = "Select Excel Data" if lang == "English" else "エクセルデータを選択"
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None, dialog_title, "", file_filters
        )
        if not file_path:
            return

        scale_options = [
            "エクセルの「0.001」を「1mm」として読み込む (土木座標/メートル)", 
            "エクセルの「1」を「1mm」として読み込む (CAD座標/ミリメートル)"
        ]
        
        # 【修正】QtWidgets.QInputDialog から TranslatedInputDialog へ差し替え
        scale_choice, ok = TranslatedInputDialog.getItem(
            None, 
            "単位の確認", 
            "FreeCADの基準単位は「mm（ミリメートル）」です。\nエクセルに入力されている座標の単位を選んでください。", 
            scale_options, 
            0, False
        )
        if not ok or not scale_choice:
            return 
            
        trans_scale_options = [translate_text(opt, lang) for opt in scale_options]
        is_survey_scale = ("0.001" in scale_choice) or (scale_choice in trans_scale_options and trans_scale_options.index(scale_choice) == 0)
        scale_factor = 1000.0 if is_survey_scale else 1.0

        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("データ処理中", lang), initial_text=translate_text("データを読み込んでいます...", lang))

            try:
                points = []
                
                if file_path.endswith('.xlsx'):
                    with zipfile.ZipFile(file_path, 'r') as z:
                        strings = []
                        if 'xl/sharedStrings.xml' in z.namelist():
                            with z.open('xl/sharedStrings.xml') as f:
                                tree = ET.parse(f)
                                for si in tree.getroot().findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                                    t = si.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
                                    strings.append(t.text if t is not None and t.text is not None else "")
                        
                        if 'xl/worksheets/sheet1.xml' in z.namelist():
                            with z.open('xl/worksheets/sheet1.xml') as f:
                                tree = ET.parse(f)
                                for row in tree.getroot().iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'):
                                    vals = []
                                    for c in row.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
                                        v = c.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                                        val_str = ""
                                        if v is not None and v.text is not None:
                                            if c.get('t') == 's':
                                                idx = int(v.text)
                                                if idx < len(strings):
                                                    val_str = strings[idx]
                                            else:
                                                val_str = v.text
                                        vals.append(val_str)
                                    
                                    if len(vals) >= 3:
                                        try:
                                            x = float(vals[0]) * scale_factor
                                            y = float(vals[1]) * scale_factor
                                            z_val = float(vals[2]) * scale_factor
                                            points.append(FreeCAD.Vector(x, y, z_val))
                                        except ValueError:
                                            continue
                else:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            parts = line.strip().replace(',', ' ').split()
                            if len(parts) >= 3:
                                try:
                                    x = float(parts[0]) * scale_factor
                                    y = float(parts[1]) * scale_factor
                                    z_val = float(parts[2]) * scale_factor
                                    points.append(FreeCAD.Vector(x, y, z_val))
                                except ValueError:
                                    continue

                if len(points) < 3:
                    err_title = "Error" if lang == "English" else "エラー"
                    err_msg = (
                        "No valid coordinate data found.\n"
                        "Please check if numerical values exist in columns A, B, and C."
                    ) if lang == "English" else (
                        "有効な座標データが見つかりませんでした。\n"
                        "エクセルのA,B,C列に数値が入力されているか確認してください。"
                    )
                    QtWidgets.QMessageBox.warning(None, err_title, err_msg)
                    return

                bar.update(60, translate_text("サーフェス（メッシュ）を計算中...", lang))

                pts_2d = np.array([[p.x, p.y] for p in points])
                tri = Delaunay(pts_2d)
                
                faces = []
                for simplex in tri.simplices:
                    p1 = points[simplex[0]]
                    p2 = points[simplex[1]]
                    p3 = points[simplex[2]]
                    faces.append((p1, p2, p3))
                
                doc = FreeCAD.activeDocument() or FreeCAD.newDocument("Excel_Surface")
                mesh_obj = doc.addObject("Mesh::Feature", "Excel_Surface")
                mesh_obj.Mesh = Mesh.Mesh(faces)
                mesh_obj.ViewObject.ShapeColor = (0.6, 0.8, 0.4) 

                doc.recompute()
                bar.update(100, translate_text("完了！", lang))

                if lang == "English":
                    succ_title = "Completed"
                    succ_msg = f"Created surface mesh from {len(points)} points.\n(Applied scale: {scale_factor}x)"
                else:
                    succ_title = "完了"
                    succ_msg = f"{len(points)} 個の座標点からサーフェスを作成しました。\n（適用倍率: {scale_factor} 倍）"

                QtWidgets.QMessageBox.information(None, succ_title, succ_msg)

            except Exception as e:
                FreeCAD.Console.PrintError(f"Excel surface error: {str(e)}\n")
                err_title = "Error" if lang == "English" else "エラー"
                err_msg = f"An error occurred during processing:\n{str(e)}" if lang == "English" else f"処理中にエラーが発生しました:\n{str(e)}"
                QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Construction_MakeExcelSurface', Tool_MakeExcelSurface())