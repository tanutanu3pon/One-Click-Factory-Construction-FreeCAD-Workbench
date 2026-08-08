# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part
import Mesh

try:
    from PySide2 import QtWidgets, QtCore
except ImportError:
    from PySide6 import QtWidgets, QtCore

import Core.Progress as Progress

class Tool_CalcEarthworkSolid:
    def GetResources(self):
        # ツールファイル (Tool/CalcEarthworkSolid.py) から親フォルダ (Ring) の icons/earthwork.png 絶対パスを取得
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "earthwork.png").replace('\\', '/')
        
        # アイコン画像が存在しない場合はコンソールに警告を出力
        if not os.path.exists(icon_path):
            FreeCAD.Console.PrintWarning(f"[警告] アイコン画像が見つかりません: {icon_path}\n")

        return {
            'Pixmap': icon_path, 
            'MenuText': "切盛土量計算 (Solid方式)", 
            'ToolTip': "基準GLを設定してサーフェスをソリッド化し、ブーリアン演算で正確な体積を計算します"
        }

    def create_solid_from_surface(self, obj_name, mesh_obj, base_z):
        """
        サーフェスメッシュから水密（Watertight）な立体メッシュを構築し、Part Solid を作成する
        """
        mesh = mesh_obj.Mesh
        all_facets = []
        
        # 1. 上面（元のサーフェスメッシュの三角形）
        for facet in mesh.Facets:
            pts = []
            for p in facet.Points:
                pts.append(p if hasattr(p, 'x') else FreeCAD.Vector(p[0], p[1], p[2]))
            all_facets.append((pts[0], pts[1], pts[2]))

        # 2. 外周エッジ（他の三角形と共有されていない境界辺）の検出
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

        # 3. 下面（base_z に投影した三角形。表裏を反転させて法線を下向きにする）
        for facet in mesh.Facets:
            pts = []
            for p in facet.Points:
                pts.append(FreeCAD.Vector(p[0], p[1], base_z))
            all_facets.append((pts[0], pts[2], pts[1]))

        # 4. 側面（外周エッジごとに2つの三角形を追加して塞ぐ）
        for p1, p2 in boundary_segments:
            b1 = FreeCAD.Vector(p1.x, p1.y, base_z)
            b2 = FreeCAD.Vector(p2.x, p2.y, base_z)
            # 側面三角形1
            all_facets.append((p1, p2, b2))
            # 側面三角形2
            all_facets.append((p1, b2, b1))

        # 5. 隙間のない完全な閉じたメッシュを構築し、Part Solid に変換
        closed_mesh = Mesh.Mesh(all_facets)
        shape = Part.Shape()
        shape.makeShapeFromMesh(closed_mesh.Topology, 0.1)
        solid = Part.Solid(Part.makeShell(shape.Faces))
        
        return solid

    def Activated(self):
        sel = FreeCADGui.Selection.getSelection()
        if len(sel) != 2:
            QtWidgets.QMessageBox.warning(None, "エラー", "比較する2つのサーフェスを選択してください。")
            return

        obj1, obj2 = sel[0], sel[1]
        if not hasattr(obj1, "Mesh") or not hasattr(obj2, "Mesh"):
            QtWidgets.QMessageBox.warning(None, "エラー", "選択されたオブジェクトはメッシュデータではありません。")
            return

        # 初期基準GL（最も低いZ座標より少し下）を自動計算
        min_z = min(obj1.Mesh.BoundBox.ZMin, obj2.Mesh.BoundBox.ZMin)
        default_gl = min_z - 1000.0 

        # ダイアログ設定
        dialog = QtWidgets.QDialog()
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

        bar = Progress.ProgressManager()
        bar.start(title="処理中", initial_text="ソリッドを生成しています...")

        try:
            doc = FreeCAD.activeDocument()
            
            # 1. 現況と計画のソリッド(Solid)を作成
            bar.update(20, "現況データのソリッド化...")
            solid_exist = self.create_solid_from_surface("Exist", obj_exist, base_z)
            
            bar.update(40, "計画データのソリッド化...")
            solid_plan = self.create_solid_from_surface("Plan", obj_plan, base_z)

            # 2. ブーリアン演算 (差分)
            bar.update(60, "土量の計算（ブーリアン減算）...")
            
            # --- 盛土 (Fill) ---
            fill_shape = solid_plan.cut(solid_exist)
            
            # --- 切土 (Cut) ---
            cut_shape = solid_exist.cut(solid_plan)

            # 3. 解析モデルとしてツリーに出力
            fill_obj = doc.addObject("Part::Feature", "Volume_Fill_Solid")
            fill_obj.Shape = fill_shape
            fill_obj.ViewObject.ShapeColor = (0.2, 0.6, 1.0) # 青(盛土)

            cut_obj = doc.addObject("Part::Feature", "Volume_Cut_Solid")
            cut_obj.Shape = cut_shape
            cut_obj.ViewObject.ShapeColor = (1.0, 0.4, 0.4) # 赤(切土)

            # 4. 体積を直接取得
            fill_vol = fill_shape.Volume
            cut_vol = cut_shape.Volume

            if is_mm_scale:
                fill_m3 = fill_vol / 1_000_000_000.0
                cut_m3 = cut_vol / 1_000_000_000.0
            else:
                fill_m3 = fill_vol
                cut_m3 = cut_vol
            
            # 元のメッシュは非表示にする
            obj_exist.ViewObject.Visibility = False
            obj_plan.ViewObject.Visibility = False
            
            doc.recompute()
            bar.update(100, "完了")

            msg = (f"【Solidブーリアン 土量計算結果】\n\n"
                   f"基準GL: Z = {base_z}\n"
                   f"--------------------------------------\n"
                   f"▼ 切土 (Cut) : {cut_m3:,.2f} m3\n"
                   f"▲ 盛土 (Fill): {fill_m3:,.2f} m3\n"
                   f"--------------------------------------\n"
                   f"差引合計 (盛-切): {fill_m3 - cut_m3:,.2f} m3\n\n"
                   f"※計算されたソリッドモデル（青/赤）をツリーに出力しました。\n"
                   f" 生成されたデータはエクスポートが可能です。")
            
            QtWidgets.QMessageBox.information(None, "計算完了", msg)

        except Exception as e:
            FreeCAD.Console.PrintError(f"エラー: {str(e)}\n")
            QtWidgets.QMessageBox.critical(None, "エラー", f"処理中にエラーが発生しました:\n{str(e)}")
        finally:
            bar.close()

FreeCADGui.addCommand('Construction_CalcEarthworkSolid', Tool_CalcEarthworkSolid())