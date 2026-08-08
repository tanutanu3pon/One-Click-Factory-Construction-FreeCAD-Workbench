# -*- coding: utf-8 -*-
import os
import zipfile
import xml.etree.ElementTree as ET
import FreeCAD
import FreeCADGui
import Part
import Mesh

try:
    from PySide2 import QtWidgets, QtCore
except ImportError:
    from PySide6 import QtWidgets, QtCore

import Core.Progress as Progress

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
        # 必要なライブラリの事前確認
        try:
            from scipy.spatial import Delaunay
            import numpy as np
        except ImportError:
            QtWidgets.QMessageBox.critical(
                None, "ライブラリ不足", 
                "サーフェス（メッシュ）の計算には 'scipy' および 'numpy' ライブラリが必要です。\n"
                "Python環境に scipy を導入してください。"
            )
            return

        QtWidgets.QMessageBox.information(None, "ご案内", "エクセルファイル（.xlsx）を選択します。A列はX軸座標、B列はY軸座標、C列はZ軸座標とします。")
        
        file_filters = "Excel Files (*.xlsx);;CSV Files (*.csv);;All Files (*)"
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None, "エクセルデータを選択", "", file_filters
        )
        if not file_path:
            return

        # スケール（倍率）選択
        scale_options = [
            "エクセルの「0.001」を「1mm」として読み込む (土木座標/メートル)", 
            "エクセルの「1」を「1mm」として読み込む (CAD座標/ミリメートル)"
        ]
        scale_choice, ok = QtWidgets.QInputDialog.getItem(
            None, 
            "単位の確認", 
            "FreeCADの基準単位は「mm（ミリメートル）」です。\nエクセルに入力されている座標の単位を選んでください。", 
            scale_options, 
            0, False
        )
        if not ok or not scale_choice:
            return 
            
        scale_factor = 1000.0 if "0.001" in scale_choice else 1.0

        bar = Progress.ProgressManager()
        bar.start(title="データ処理中", initial_text="データを読み込んでいます...")

        try:
            points = []
            
            # --- .xlsxファイルの読み込み ---
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
            
            # --- CSVファイルだった場合の読み込み ---
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
                bar.close()
                QtWidgets.QMessageBox.warning(None, "エラー", "有効な座標データが見つかりませんでした。\nエクセルのA,B,C列に数値が入力されているか確認してください。")
                return

            bar.update(60, "サーフェス（メッシュ）を計算中...")

            # 三角分割によるサーフェス生成
            pts_2d = np.array([[p.x, p.y] for p in points])
            tri = Delaunay(pts_2d)
            
            faces = []
            for simplex in tri.simplices:
                p1 = points[simplex[0]]
                p2 = points[simplex[1]]
                p3 = points[simplex[2]]
                faces.append((p1, p2, p3))
            
            mesh_obj = FreeCAD.activeDocument().addObject("Mesh::Feature", "Excel_Surface")
            mesh_obj.Mesh = Mesh.Mesh(faces)
            mesh_obj.ViewObject.ShapeColor = (0.6, 0.8, 0.4) 

            FreeCAD.activeDocument().recompute()
            bar.update(100, "完了！")
            QtWidgets.QMessageBox.information(None, "完了", f"{len(points)} 個の座標点からサーフェスを作成しました。\n（適用倍率: {scale_factor} 倍）")

        except Exception as e:
            FreeCAD.Console.PrintError(f"エラー: {str(e)}\n")
            QtWidgets.QMessageBox.critical(None, "エラー", f"処理中にエラーが発生しました:\n{str(e)}")
        finally:
            bar.close()

FreeCADGui.addCommand('Construction_MakeExcelSurface', Tool_MakeExcelSurface())