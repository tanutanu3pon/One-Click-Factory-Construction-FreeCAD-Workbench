# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part
import Mesh

# 【修正】絶対インポートで安全にCoreモジュールを読み込む
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedDialog, translate_text
from Core.Language import get_language

class Tool_CalcEarthworkSolid:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "earthwork.png").replace('\\', '/')
        
        if not os.path.exists(icon_path):
            FreeCAD.Console.PrintWarning(f"[警告] アイコン画像が見つかりません: {icon_path}\n")

        return {
            'Pixmap': icon_path, 
            'MenuText': "切盛土量計算 (Solid方式)", 
            'ToolTip': "基準GLを設定してサーフェスをソリッド化し、ブーリアン演算で正確な体積を計算します"
        }

    def create_solid_from_surface(self, obj_name, mesh_obj, base_z):
        mesh = mesh_obj.Mesh
        all_facets = []
        
        for facet in mesh.Facets:
            pts = []
            for p in facet.Points:
                pts.append(p if hasattr(p, 'x') else FreeCAD.Vector(p[0], p[1], p[2]))
            all_facets.append((pts[0], pts[1], pts[2]))

        edge_map = {}
        for facet in mesh.Facets:
            pts = []
            for p in facet.Points:
                pts.append(p if hasattr(p, 'x') else FreeCAD.Vector(p[0], p[1], p[2]))
            pairs = [(pts[0], pts[1]), (pts[1], pts[2]), (pts[2], pts[0])]
            for p1, p2 in pairs:
                key = tuple(sorted([(round(p1.x, 3), round(p1.y, 3), round(p1.z, 3)), 
                                    (round(p2.x, 3), round(p2.y, 3), round(p2.z, 3))]))
                if key not in edge_map:
                    edge_map[key] = (p1, p2, 1)
                else:
                    p1_orig, p2_orig, count = edge_map[key]
                    edge_map[key] = (p1_orig, p2_orig, count + 1)

        boundary_segments = [(val[0], val[1]) for val in edge_map.values() if val[2] == 1]

        for facet in mesh.Facets:
            pts = []
            for p in facet.Points:
                pts.append(FreeCAD.Vector(p[0], p[1], base_z))
            all_facets.append((pts[0], pts[2], pts[1]))

        for p1, p2 in boundary_segments:
            b1 = FreeCAD.Vector(p1.x, p1.y, base_z)
            b2 = FreeCAD.Vector(p2.x, p2.y, base_z)
            all_facets.append((p1, p2, b2))
            all_facets.append((p1, b2, b1))

        closed_mesh = Mesh.Mesh(all_facets)
        shape = Part.Shape()
        shape.makeShapeFromMesh(closed_mesh.Topology, 0.1)
        solid = Part.Solid(Part.makeShell(shape.Faces))
        
        return solid

    def Activated(self):
        lang = get_language()
        
        sel = FreeCADGui.Selection.getSelection()
        if len(sel) != 2:
            QtWidgets.QMessageBox.warning(None, translate_text("エラー", lang), translate_text("比較する2つのサーフェスを選択してください。", lang))
            return

        obj1, obj2 = sel[0], sel[1]
        if not hasattr(obj1, "Mesh") or not hasattr(obj2, "Mesh"):
            QtWidgets.QMessageBox.warning(None, translate_text("エラー", lang), translate_text("選択されたオブジェクトはメッシュデータではありません。", lang))
            return

        min_z = min(obj1.Mesh.BoundBox.ZMin, obj2.Mesh.BoundBox.ZMin)
        default_gl = min_z - 1000.0 

        # 【修正】QtWidgets.QDialog() から TranslatedDialog() に変更（これでUIが自動翻訳されます）
        dialog = TranslatedDialog()
        dialog.setWindowTitle("Solid方式 切盛土量計算")
        layout = QtWidgets.QFormLayout(dialog)

        combo_exist = QtWidgets.QComboBox()
        combo_exist.addItems([obj1.Label, obj2.Label])
        layout.addRow("【ベース】現況(施工前)データ:", combo_exist)

        spin_gl = QtWidgets.QDoubleSpinBox()
        spin_gl.setRange(-1000000.0, 1000000.0)
        spin_gl.setDecimals(3)
        spin_gl.setValue(default_gl)
        layout.addRow("基準GL (底面を作るZ座標):", spin_gl)

        combo_scale = QtWidgets.QComboBox()
        combo_scale.addItems([
            "モデルは mm 単位 (1m = 1000mm)",
            "モデルは m 単位 (1m = 1m)"
        ])
        layout.addRow("単位系:", combo_scale)

        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addRow(btn_box)

        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        is_obj1_exist = (combo_exist.currentIndex() == 0)
        obj_exist = obj1 if is_obj1_exist else obj2
        obj_plan  = obj2 if is_obj1_exist else obj1
        
        base_z = spin_gl.value()
        is_mm_scale = (combo_scale.currentIndex() == 0)

        with Progress.ProgressManager() as bar:
            # プログレスバーのテキストも明示的に翻訳
            bar.start(title=translate_text("処理中", lang), initial_text=translate_text("ソリッドを生成しています...", lang))

            try:
                doc = FreeCAD.activeDocument()
                
                bar.update(20, translate_text("現況データのソリッド化...", lang))
                solid_exist = self.create_solid_from_surface("Exist", obj_exist, base_z)
                
                bar.update(40, translate_text("計画データのソリッド化...", lang))
                solid_plan = self.create_solid_from_surface("Plan", obj_plan, base_z)

                bar.update(60, translate_text("土量の計算（ブーリアン減算）...", lang))
                fill_shape = solid_plan.cut(solid_exist)
                cut_shape = solid_exist.cut(solid_plan)

                fill_obj = doc.addObject("Part::Feature", "Volume_Fill_Solid")
                fill_obj.Shape = fill_shape
                fill_obj.ViewObject.ShapeColor = (0.2, 0.6, 1.0)

                cut_obj = doc.addObject("Part::Feature", "Volume_Cut_Solid")
                cut_obj.Shape = cut_shape
                cut_obj.ViewObject.ShapeColor = (1.0, 0.4, 0.4)

                fill_vol = fill_shape.Volume
                cut_vol = cut_shape.Volume

                if is_mm_scale:
                    fill_m3 = fill_vol / 1_000_000_000.0
                    cut_m3 = cut_vol / 1_000_000_000.0
                else:
                    fill_m3 = fill_vol
                    cut_m3 = cut_vol
                
                obj_exist.ViewObject.Visibility = False
                obj_plan.ViewObject.Visibility = False
                
                doc.recompute()
                bar.update(100, translate_text("完了", lang))

                # f文字列の中に変数がある場合、辞書の一致検索に失敗するため英語へ直接分岐
                if lang == "English":
                    msg = (f"[Solid Boolean Volume Calculation Result]\n\n"
                           f"Base GL: Z = {base_z}\n"
                           f"--------------------------------------\n"
                           f"▼ Cut Volume : {cut_m3:,.2f} m3\n"
                           f"▲ Fill Volume: {fill_m3:,.2f} m3\n"
                           f"--------------------------------------\n"
                           f"Net Total (Fill - Cut): {fill_m3 - cut_m3:,.2f} m3\n\n"
                           f"* Generated volume solid models (Blue/Red) in tree view.\n"
                           f" Generated data can be exported.")
                    title_done = "Calculation Completed"
                else:
                    msg = (f"【Solidブーリアン 土量計算結果】\n\n"
                           f"基準GL: Z = {base_z}\n"
                           f"--------------------------------------\n"
                           f"▼ 切土 (Cut) : {cut_m3:,.2f} m3\n"
                           f"▲ 盛土 (Fill): {fill_m3:,.2f} m3\n"
                           f"--------------------------------------\n"
                           f"差引合計 (盛-切): {fill_m3 - cut_m3:,.2f} m3\n\n"
                           f"※計算されたソリッドモデル（青/赤）をツリーに出力しました。\n"
                           f" 生成されたデータはエクスポートが可能です。")
                    title_done = "計算完了"
                
                QtWidgets.QMessageBox.information(None, title_done, msg)

            except Exception as e:
                err_title = "Error" if lang == "English" else "エラー"
                err_msg = f"An error occurred during processing:\n{str(e)}" if lang == "English" else f"処理中にエラーが発生しました:\n{str(e)}"
                
                FreeCAD.Console.PrintError(f"{err_title}: {str(e)}\n")
                QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Construction_CalcEarthworkSolid', Tool_CalcEarthworkSolid())