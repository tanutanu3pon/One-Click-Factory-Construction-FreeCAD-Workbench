# -*- coding: utf-8 -*-
import os
import math
import FreeCAD
import FreeCADGui
import Part

# 絶対インポートで安全にCoreモジュールを読み込む
from Core.QtCompat import QtWidgets
import Core.Progress as Progress
from Core.Controller import TranslatedInputDialog, translate_text
from Core.Language import get_language

class Tool_MakeDonguri:
    def GetResources(self):
        current_dir = os.path.dirname(__file__)
        ring_dir = os.path.dirname(current_dir)
        icon_path = os.path.join(ring_dir, "icons", "donguri.png").replace('\\', '/')
        return {
            'Pixmap'  : icon_path,
            'MenuText': "どんぐりの作成",
            'ToolTip' : "細い・普通・太いの3種類の形状と、傘（帽子）の有無を選んでどんぐりの飾りを作成します（進捗窓付き）"
        }

    def Activated(self):
        lang = get_language()

        types = [
            "細いどんぐり (Slim)",
            "普通どんぐり (Standard)",
            "太いどんぐり (Plump)"
        ]
        selected_type, ok1 = TranslatedInputDialog.getItem(None, "形状の選択", "どんぐりの種類:", types, 1, False)
        if not ok1: return

        cap_options = [
            "傘をつける (With Cap)",
            "傘をつけない (Without Cap)"
        ]
        selected_cap, ok2 = TranslatedInputDialog.getItem(None, "傘の設定", "傘（帽子）の有無:", cap_options, 0, False)
        if not ok2: return

        height, ok3 = TranslatedInputDialog.getDouble(None, "寸法指定", "全体の高さ (mm):", 25.0, 10.0, 100.0, 1)
        if not ok3: return

        trans_types = [translate_text(t, lang) for t in types]
        if selected_type in (types[0], trans_types[0]):
            type_idx = 0
        elif selected_type in (types[1], trans_types[1]):
            type_idx = 1
        else:
            type_idx = 2

        trans_caps = [translate_text(t, lang) for t in cap_options]
        has_cap = True if selected_cap in (cap_options[0], trans_caps[0]) else False

        self.create_donguri(type_idx, has_cap, height, lang)

    def create_donguri(self, type_idx, has_cap, H, lang):
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
        
        try:
            doc.openTransaction("Create Donguri Model")
            with Progress.ProgressManager() as bar:
                bar.start(title=translate_text("3Dモデル生成", lang), initial_text=translate_text("基本形状を計算中...", lang))

                # 種類ごとのアスペクト比（最大半径の比率）
                r_ratio = [0.22, 0.32, 0.42][type_idx]
                r_max = H * r_ratio

                # ---------------------------------------------------------
                # 1. どんぐり本体の作成 (回転成形)
                # ---------------------------------------------------------
                bar.update(30, translate_text("どんぐり本体を成形中...", lang))
                
                tip_h = H * 0.03
                # 傘をつける場合も本体を深めに残す (0.75 -> 0.85)
                body_h = H if not has_cap else H * 0.85
                
                poles_body = [
                    FreeCAD.Vector(0, 0, 0),
                    FreeCAD.Vector(r_max * 0.1, 0, tip_h * 0.5),
                    FreeCAD.Vector(r_max * 0.4, 0, tip_h),
                    FreeCAD.Vector(r_max, 0, body_h * 0.45),
                    FreeCAD.Vector(r_max * 0.85, 0, body_h * 0.85),
                    FreeCAD.Vector(0, 0, body_h)
                ]
                
                c_body = Part.BSplineCurve()
                c_body.buildFromPoles(poles_body)
                
                line_axis = Part.makeLine(FreeCAD.Vector(0,0,body_h), FreeCAD.Vector(0,0,0))
                wire_body = Part.Wire([c_body.toShape(), line_axis])
                face_body = Part.Face(wire_body)
                body_shape = face_body.revolve(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), 360)

                # ---------------------------------------------------------
                # 2. 傘（帽子）と軸の作成 (サイズ感を浅く調整)
                # ---------------------------------------------------------
                if has_cap:
                    bar.update(60, translate_text("どんぐりの傘を成形中...", lang))
                    
                    # 傘の高さ方向の位置・深さを浅めに調整
                    cap_start_z = body_h * 0.78  # 覆う範囲を浅く (0.65 -> 0.78)
                    cap_top_z = H * 0.94
                    cap_r = r_max * 1.06
                    cap_thick = H * 0.045
                    
                    poles_cap_out = [
                        FreeCAD.Vector(r_max * 0.88, 0, cap_start_z),
                        FreeCAD.Vector(cap_r, 0, (cap_start_z + cap_top_z) * 0.5),
                        FreeCAD.Vector(cap_r * 0.45, 0, cap_top_z + cap_thick),
                        FreeCAD.Vector(0, 0, cap_top_z + cap_thick)
                    ]
                    
                    poles_cap_in = [
                        FreeCAD.Vector(0, 0, body_h),
                        FreeCAD.Vector(r_max * 0.92, 0, body_h * 0.98),
                        FreeCAD.Vector(r_max * 0.88, 0, cap_start_z)
                    ]

                    c_cap_out = Part.BSplineCurve()
                    c_cap_out.buildFromPoles(poles_cap_out)
                    
                    c_cap_in = Part.BSplineCurve()
                    c_cap_in.buildFromPoles(poles_cap_in)
                    
                    l_cap_axis = Part.makeLine(FreeCAD.Vector(0, 0, cap_top_z + cap_thick), FreeCAD.Vector(0, 0, body_h))
                    
                    wire_cap = Part.Wire([c_cap_out.toShape(), c_cap_in.toShape(), l_cap_axis])
                    face_cap = Part.Face(wire_cap)
                    cap_shape = face_cap.revolve(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), 360)

                    # ヘタ（枝の軸）
                    stem_r = H * 0.035
                    stem_h = H * 0.15
                    stem_shape = Part.makeCylinder(stem_r, stem_h, FreeCAD.Vector(0, 0, cap_top_z + cap_thick - 0.5))

                    bar.update(80, translate_text("パーツを結合中...", lang))
                    full_shape = body_shape.fuse(cap_shape).fuse(stem_shape)
                else:
                    stem_r = H * 0.035
                    stem_h = H * 0.12
                    stem_shape = Part.makeCylinder(stem_r, stem_h, FreeCAD.Vector(0, 0, body_h - 0.5))
                    full_shape = body_shape.fuse(stem_shape)

                # ---------------------------------------------------------
                # 3. 仕上げと配置
                # ---------------------------------------------------------
                bar.update(90, translate_text("不要なシーム線を消去して最適化中...", lang))
                full_shape = full_shape.removeSplitter()

                type_labels = ["Slim", "Standard", "Plump"]
                cap_label = "WithCap" if has_cap else "NoCap"
                obj = doc.addObject("Part::Feature", f"Donguri_{type_labels[type_idx]}_{cap_label}")
                obj.Shape = full_shape
                obj.ViewObject.DisplayMode = "Flat Lines"

                obj.ViewObject.ShapeColor = (0.58, 0.38, 0.22)
                if hasattr(obj.ViewObject, "Shininess"):
                    obj.ViewObject.Shininess = 0.7

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

FreeCADGui.addCommand('Ring_MakeDonguri', Tool_MakeDonguri())