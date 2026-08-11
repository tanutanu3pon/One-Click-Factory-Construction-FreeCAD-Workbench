# -*- coding: utf-8 -*-
import os
import datetime
import FreeCAD
import FreeCADGui

from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedInputDialog, translate_text
from Core.Language import get_language

class Tool_ExportIFC:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "ifc.png").replace('\\', '/')
        return {
            'Pixmap': icon_path if os.path.exists(icon_path) else "", 
            'MenuText': "IFCエクスポート", 
            'ToolTip': "選択した3D構造物（ボックスカルバート等）をBIM/CIM標準IFCフォーマットで出力します"
        }

    def Activated(self):
        lang = get_language()
        sel = FreeCADGui.Selection.getSelection()

        if not sel:
            QtWidgets.QMessageBox.warning(
                None, 
                translate_text("選択エラー", lang), 
                translate_text("出力対象となる3D構造物（ボックスカルバート等）をツリーまたは画面上から選択してください。", lang)
            )
            return

        # 1. 単位スケールの選択
        scale_options = [
            "1/1000 スケーリング (FreeCAD: mm → IFC: 米/メートル) [推奨]",
            "等倍スケーリング (FreeCAD: mm → IFC: mm)"
        ]
        
        scale_choice, ok = TranslatedInputDialog.getItem(
            None, 
            "出力単位の確認", 
            "IFCの標準単位系を選択してください。", 
            scale_options, 
            0, False
        )
        if not ok or not scale_choice:
            return

        trans_scale_options = [translate_text(opt, lang) for opt in scale_options]
        is_m_scale = ("1/1000" in scale_choice) or (scale_choice in trans_scale_options and trans_scale_options.index(scale_choice) == 0)
        scale_factor = 0.001 if is_m_scale else 1.0
        unit_str = ".METRE." if is_m_scale else ".MILLIMETRE."

        # 2. 出力先のファイルパス選択
        save_title = "IFCファイルの保存" if lang == "日本語" else "Save IFC File"
        file_filter = "IFC Files (*.ifc);;All Files (*)"
        default_name = f"{sel[0].Name}_BIM.ifc"
        
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            None, save_title, default_name, file_filter
        )
        if not file_path:
            return

        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("IFC出力処理中", lang), initial_text=translate_text("3DモデルからIFC要素を構築中...", lang))

            try:
                # 3. 形状データ（ポリゴンメッシュ）の抽出
                bar.update(30, translate_text("3Dポリゴンメッシュを抽出中...", lang))
                
                all_points = []
                all_faces = []
                pt_offset = 0

                for obj in sel:
                    raw_pts = []
                    raw_tris = []

                    if hasattr(obj, "Mesh") and obj.Mesh:
                        m = obj.Mesh
                        raw_pts = [(p.x * scale_factor, p.y * scale_factor, p.z * scale_factor) for p in m.Points]
                        for facet in m.Facets:
                            raw_tris.append((facet.PointIndices[0], facet.PointIndices[1], facet.PointIndices[2]))
                    elif hasattr(obj, "Shape") and obj.Shape:
                        tess = obj.Shape.tessellate(0.1)
                        raw_pts = [(p.x * scale_factor, p.y * scale_factor, p.z * scale_factor) for p in tess[0]]
                        raw_tris = tess[1]

                    for p in raw_pts:
                        all_points.append(p)

                    for tri in raw_tris:
                        all_faces.append((tri[0] + 1 + pt_offset, tri[1] + 1 + pt_offset, tri[2] + 1 + pt_offset))

                    pt_offset += len(raw_pts)

                if not all_points or not all_faces:
                    QtWidgets.QMessageBox.warning(None, translate_text("エラー", lang), translate_text("有効な3D形状データを抽出できませんでした。", lang))
                    return

                bar.update(60, translate_text("IFC4フォーマットを生成中...", lang))

                # 4. IFC4 STEPテキスト構造の書き出し (IfcOpenShell不使用)
                now_str = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                proj_name = sel[0].Label if sel else "BIM_Project"

                pts_str_list = [f"({p[0]:.4f},{p[1]:.4f},{p[2]:.4f})" for p in all_points]
                pts_text = ",".join(pts_str_list)

                faces_str_list = [f"({f[0]},{f[1]},{f[2]})" for f in all_faces]
                faces_text = ",".join(faces_str_list)

                ifc_lines = [
                    "ISO-10303-21;",
                    "HEADER;",
                    "FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');",
                    f"FILE_NAME('{os.path.basename(file_path)}','{now_str}',('FreeCAD User'),('Construction'),'FreeCAD Custom Exporter','FreeCAD','');",
                    "FILE_SCHEMA(('IFC4'));",
                    "ENDSEC;",
                    "DATA;",
                    "#1=IFCPERSON($,$,'User',$,$,$,$,$);",
                    "#2=IFCORGANIZATION($,'Construction',$,$,$);",
                    "#3=IFCPERSONANDORGANIZATION(#1,#2,$);",
                    "#4=IFCAPPLICATION(#2,'1.0','FreeCAD Custom Exporter','FreeCAD');",
                    "#5=IFCOWNERHISTORY(#3,#4,$,.ADDED.,$,#3,#4,1700000000);",
                    "#6=IFCDIMENSIONALEXPONENTS(0,0,0,0,0,0,0);",
                    f"#7=IFCSIUNIT(*,.LENGTHUNIT.,$,{unit_str});",
                    "#8=IFCUNITASSIGNMENT((#7));",
                    "#9=IFCCARTESIANPOINT((0.,0.,0.));",
                    "#10=IFCDIRECTION((0.,0.,1.));",
                    "#11=IFCDIRECTION((1.,0.,0.));",
                    "#12=IFCAXIS2PLACEMENT3D(#9,#10,#11);",
                    "#13=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.0E-05,#12,$);",
                    f"#14=IFCPROJECT('0$12345678901234567890',#5,'{proj_name}',$,$,$,$,(#13),#8);",
                    "#15=IFCSITE('1$12345678901234567890',#5,'Site',$,$,#12,$,$,.ELEMENT.,$,$,$,$,$);",
                    "#16=IFCBUILDING('2$12345678901234567890',#5,'Building',$,$,#12,$,$,.ELEMENT.,$,$,$);",
                    "#17=IFCRELAGGREGATES('3$12345678901234567890',#5,$,$,#14,(#15));",
                    "#18=IFCRELAGGREGATES('4$12345678901234567890',#5,$,$,#15,(#16));",
                    f"#19=IFCCARTESIANPOINTLIST3D(({pts_text}));",
                    f"#20=IFCTRIANGULATEDFACESET(#19,$,.F.,({faces_text}),$);",
                    "#21=IFCSHAPEREPRESENTATION(#13,'Body','SurfaceModel',(#20));",
                    "#22=IFCPRODUCTDEFINITIONSHAPE($,$,(#21));",
                    f"#23=IFCBUILDINGELEMENTPROXY('5$12345678901234567890',#5,'{proj_name}',$,$,#12,#22,$,$);",
                    "#24=IFCRELCONTAINEDINSPATIALSTRUCTURE('6$12345678901234567890',#5,$,$,(#23),#16);",
                    "ENDSEC;",
                    "END-ISO-10303-21;"
                ]

                bar.update(85, translate_text("ファイル書き出し中...", lang))

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(ifc_lines))

                bar.update(100, translate_text("完了！", lang))

                succ_title = "IFC出力完了" if lang == "日本語" else "IFC Export Completed"
                succ_msg = (
                    f"IFC(BIM/CIM標準)ファイルの出力が完了しました！\n\n"
                    f"・保存先: {file_path}\n"
                    f"・総頂点数: {len(all_points)} Pnts\n"
                    f"・総ポリゴン数: {len(all_faces)} Faces\n\n"
                    f"※Navisworks、Civil 3D、Solibri等のBIM/CIMツールで直接確認可能です。"
                ) if lang == "日本語" else (
                    f"Successfully exported IFC file!\n\n"
                    f"・File Path: {file_path}\n"
                    f"・Points: {len(all_points)}\n"
                    f"・Faces: {len(all_faces)}"
                )

                QtWidgets.QMessageBox.information(None, succ_title, succ_msg)

            except Exception as e:
                FreeCAD.Console.PrintError(f"IFC export error: {str(e)}\n")
                err_title = "Error" if lang == "English" else "エラー"
                err_msg = f"An error occurred during export:\n{str(e)}" if lang == "English" else f"出力中にエラーが発生しました:\n{str(e)}"
                QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Construction_ExportIFC', Tool_ExportIFC())