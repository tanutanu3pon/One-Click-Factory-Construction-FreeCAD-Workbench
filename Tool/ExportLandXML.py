# -*- coding: utf-8 -*-
import os
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import FreeCAD
import FreeCADGui

from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedInputDialog, translate_text
from Core.Language import get_language

class Tool_ExportLandXML:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "surveyxml.png").replace('\\', '/')
        return {
            'Pixmap': icon_path if os.path.exists(icon_path) else "", 
            'MenuText': "LandXMLエクスポート", 
            'ToolTip': "世界標準(1.2)またはJ-LandXML(日本独自規格)形式でサーフェスを出力します"
        }

    def Activated(self):
        lang = get_language()
        sel = FreeCADGui.Selection.getSelection()

        if not sel:
            QtWidgets.QMessageBox.warning(
                None, 
                translate_text("選択エラー", lang), 
                translate_text("出力対象となるサーフェス（メッシュまたはモデル）を画面上から選択してください。", lang)
            )
            return

        target_obj = sel[0]
        
        # 1. 規格タイプの選択
        spec_options = [
            "日本独自規格: J-LandXML (国土交通省 i-Construction / 電子納品仕様)",
            "世界標準規格: LandXML v1.2 (汎用 / グローバル仕様)"
        ]
        
        spec_choice, ok = TranslatedInputDialog.getItem(
            None, 
            "規格タイプの選択", 
            "出力するLandXMLの規格を選択してください。", 
            spec_options, 
            0, False
        )
        if not ok or not spec_choice:
            return

        is_jlandxml = ("J-LandXML" in spec_choice)

        # 2. 平面直角座標系の選択 (都道府県・離島表示対応)
        crs_zone = 0
        if is_jlandxml:
            zones_info = [
                "第 1 系: 長崎県、対馬、壱岐",
                "第 2 系: 福岡・佐賀・熊本・大分・宮崎・鹿児島(本土)",
                "第 3 系: 山口・島根・広島",
                "第 4 系: 香川・愛媛・徳島・高知",
                "第 5 系: 兵庫・鳥取・岡山",
                "第 6 系: 京都・大阪・奈良・和歌山・滋賀・三重",
                "第 7 系: 石川・富山・岐阜・福井",
                "第 8 系: 新潟・長野・山梨・静岡",
                "第 9 系: 東京都(伊豆諸島)、愛知・岐阜・三重・静岡",
                "第 10 系: 東京都(本土)、埼玉・千葉・神奈川・茨城・栃木・群馬・山梨",
                "第 11 系: 福島・宮城・岩手",
                "第 12 系: 秋田・山形・青森",
                "第 13 系: 北海道(渡島・後志・胆振・日高・石狩・空知・留萌)",
                "第 14 系: 東京都(小笠原諸島)",
                "第 15 系: 沖縄県(沖縄本島・周辺離島)",
                "第 16 系: 沖縄県(宮古列島・八重山列島)",
                "第 17 系: 沖縄県(大東諸島)",
                "第 18 系: 北海道(上川・網走・十勝・釧路・根室)",
                "第 19 系: 北海道(宗谷)"
            ]
            zone_choice, ok = TranslatedInputDialog.getItem(
                None, 
                "平面直角座標系の選択", 
                "該当する地域・都道府県（第1系?第19系）を選択してください。", 
                zones_info, 
                9, False  # デフォルト: 第10系 (東京本土・関東)
            )
            if not ok or not zone_choice:
                return
            crs_zone = zones_info.index(zone_choice) + 1

        # 3. 単位スケールの選択
        scale_options = [
            "1/1000 スケーリング (FreeCAD: mm → XML: 米/メートル) [推奨]",
            "等倍スケーリング (FreeCAD: mm → XML: mm)"
        ]
        
        scale_choice, ok = TranslatedInputDialog.getItem(
            None, 
            "出力単位の確認", 
            "LandXMLの標準単位系を選択してください。", 
            scale_options, 
            0, False
        )
        if not ok or not scale_choice:
            return

        trans_scale_options = [translate_text(opt, lang) for opt in scale_options]
        is_m_scale = ("1/1000" in scale_choice) or (scale_choice in trans_scale_options and trans_scale_options.index(scale_choice) == 0)
        scale_factor = 0.001 if is_m_scale else 1.0
        unit_str = "meter" if is_m_scale else "millimeter"

        # 4. 出力先のファイルパス選択
        save_title = "LandXMLファイルの保存" if lang == "日本語" else "Save LandXML File"
        file_filter = "LandXML Files (*.xml);;All Files (*)"
        prefix = "J-LandXML" if is_jlandxml else "LandXML12"
        default_name = f"{target_obj.Name}_{prefix}.xml"
        
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            None, save_title, default_name, file_filter
        )
        if not file_path:
            return

        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("LandXML出力処理中", lang), initial_text=translate_text("サーフェス要素を抽出中...", lang))

            try:
                points = []
                faces = []

                if hasattr(target_obj, "Mesh") and target_obj.Mesh:
                    mesh = target_obj.Mesh
                    bar.update(20, translate_text("メッシュの節点・要素を解析中...", lang))
                    
                    point_map = {}
                    for idx, pt in enumerate(mesh.Points):
                        p_vec = (pt.x * scale_factor, pt.y * scale_factor, pt.z * scale_factor)
                        points.append(p_vec)
                        point_map[pt.Index] = idx + 1

                    for facet in mesh.Facets:
                        f_pts = facet.PointIndices
                        faces.append((f_pts[0] + 1, f_pts[1] + 1, f_pts[2] + 1))

                elif hasattr(target_obj, "Shape") and target_obj.Shape:
                    bar.update(20, translate_text("形状からメッシュ（TIN）を生成中...", lang))
                    raw_pts = target_obj.Shape.tessellate(0.1)[0]
                    raw_tri = target_obj.Shape.tessellate(0.1)[1]

                    for p in raw_pts:
                        points.append((p.x * scale_factor, p.y * scale_factor, p.z * scale_factor))
                    
                    for tri in raw_tri:
                        faces.append((tri[0] + 1, tri[1] + 1, tri[2] + 1))

                if not points or not faces:
                    QtWidgets.QMessageBox.warning(None, translate_text("エラー", lang), translate_text("有効なサーフェス面を抽出できませんでした。", lang))
                    return

                bar.update(60, translate_text("LandXMLツリー構造を生成中...", lang))

                root_attrs = {
                    'xmlns': 'http://www.landxml.org/schema/LandXML-1.2',
                    'version': '1.2',
                    'date': '2026-08-11',
                    'language': 'Japanese' if lang == "日本語" else 'English'
                }
                
                if is_jlandxml:
                    root_attrs['readOnly'] = 'false'

                root = ET.Element('LandXML', root_attrs)

                units = ET.SubElement(root, 'Units')
                metric = ET.SubElement(units, 'Metric', {
                    'linearUnit': unit_str,
                    'areaUnit': 'squareMeter',
                    'volumeUnit': 'cubicMeter',
                    'temperatureUnit': 'celsius'
                })

                if is_jlandxml and crs_zone > 0:
                    coord_sys = ET.SubElement(root, 'CoordinateSystem', {
                        'name': f'JGD2011 / 平面直角座標第{crs_zone}系',
                        'horizontalDatum': 'JGD2011',
                        'verticalDatum': 'T.P.'
                    })

                surfaces = ET.SubElement(root, 'Surfaces')
                surface = ET.SubElement(surfaces, 'Surface', {'name': target_obj.Label})
                definition = ET.SubElement(surface, 'Definition', {'surfType': 'TIN'})

                pnts = ET.SubElement(definition, 'Pnts')
                total_pts = len(points)
                for i, pt in enumerate(points):
                    p_elem = ET.SubElement(pnts, 'P', {'id': str(i + 1)})
                    p_elem.text = f"{pt[1]:.4f} {pt[0]:.4f} {pt[2]:.4f}"

                faces_elem = ET.SubElement(definition, 'Faces')
                total_faces = len(faces)
                for f in faces:
                    f_elem = ET.SubElement(faces_elem, 'F')
                    f_elem.text = f"{f[0]} {f[1]} {f[2]}"

                bar.update(85, translate_text("XMLファイルの書き出し中...", lang))

                xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(xml_str)

                bar.update(100, translate_text("完了！", lang))

                spec_name = f"J-LandXML (第{crs_zone}系)" if is_jlandxml else "LandXML v1.2 (世界標準)"
                if lang == "日本語":
                    succ_title = "LandXML出力完了"
                    succ_msg = (
                        f"LandXMLファイルの出力が完了しました！\n\n"
                        f"・適用規格: {spec_name}\n"
                        f"・保存先: {file_path}\n"
                        f"・総節点数: {total_pts} Pnts\n"
                        f"・総TIN面数: {total_faces} Faces"
                    )
                else:
                    succ_title = "LandXML Export Completed"
                    succ_msg = (
                        f"Successfully exported LandXML file!\n\n"
                        f"・Specification: {spec_name}\n"
                        f"・File Path: {file_path}\n"
                        f"・Total Points: {total_pts} Pnts\n"
                        f"・Total Faces: {total_faces} Faces"
                    )

                QtWidgets.QMessageBox.information(None, succ_title, succ_msg)

            except Exception as e:
                FreeCAD.Console.PrintError(f"LandXML export error: {str(e)}\n")
                err_title = "Error" if lang == "English" else "エラー"
                err_msg = f"An error occurred during export:\n{str(e)}" if lang == "English" else f"出力中にエラーが発生しました:\n{str(e)}"
                QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Construction_ExportLandXML', Tool_ExportLandXML())