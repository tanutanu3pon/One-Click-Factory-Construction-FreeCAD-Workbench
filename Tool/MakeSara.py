# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part

# 絶対インポートでCoreモジュールを読み込む
from Core.QtCompat import QtWidgets
import Core.Progress as Progress
from Core.Controller import TranslatedInputDialog, translate_text
from Core.Language import get_language

class Tool_MakeSara:
    def GetResources(self):
        current_dir = os.path.dirname(__file__)
        ring_dir = os.path.dirname(current_dir)
        # 指定された sara.png をアイコンとして設定
        icon_path = os.path.join(ring_dir, "icons", "sara.png").replace('\\', '/')
        return {
            'Pixmap'  : icon_path,
            'MenuText': "お皿の作成",
            'ToolTip' : "ご飯の茶碗、みそ汁の茶碗、小皿、深い皿を生成します（進捗窓付き）"
        }

    def Activated(self):
        lang = get_language()

        types = [
            "ご飯の茶碗 (Rice Bowl)",
            "みそ汁の茶碗 (Soup Bowl)",
            "小皿 (Small Plate)",
            "深い皿 (Deep Plate)"
        ]

        # 種類の選択ダイアログ
        selected_type, ok0 = TranslatedInputDialog.getItem(None, "お皿設計", "器のタイプ:", types, 0, False)
        if not ok0: return

        trans_types = [translate_text(t, lang) for t in types]
        if selected_type in types:
            type_idx = types.index(selected_type)
        elif selected_type in trans_types:
            type_idx = trans_types.index(selected_type)
        else:
            type_idx = 0

        # 種類ごとのデフォルトサイズ (高さ, 直径, 肉厚)
        default_h = [60.0, 70.0, 20.0, 45.0][type_idx]
        default_d = [115.0, 110.0, 120.0, 200.0][type_idx]
        default_w = [3.0, 3.5, 3.0, 4.0][type_idx]

        h, ok1 = TranslatedInputDialog.getDouble(None, "寸法指定", "全体の高さ (mm):", default_h, 5.0, 300.0, 1)
        if not ok1: return

        d, ok2 = TranslatedInputDialog.getDouble(None, "寸法指定", "最大外径 (mm):", default_d, 20.0, 400.0, 1)
        if not ok2: return

        w, ok3 = TranslatedInputDialog.getDouble(None, "寸法指定", "壁の肉厚 (mm):", default_w, 1.0, 20.0, 1)
        if not ok3: return

        self.create_sara(type_idx, h, d, w, lang)

    def make_sara_profile(self, r_max, h, w, base_h, base_r_out, poles_out, poles_in):
        """指定された制御点からお皿の断面（ワイヤー）を構築する"""
        base_r_in = max(base_r_out - w, 1.0)
        
        # 原点中心から高台部分の構成点
        p0 = FreeCAD.Vector(0, 0, base_h)
        p1 = FreeCAD.Vector(base_r_in, 0, base_h)
        p2 = FreeCAD.Vector(base_r_in, 0, 0)
        p3 = FreeCAD.Vector(base_r_out, 0, 0)
        p4 = FreeCAD.Vector(base_r_out, 0, base_h)
        
        # 外側カーブ (BSpline)
        c_out = Part.BSplineCurve()
        c_out.buildFromPoles([p4] + poles_out)
        
        # 口元の丸み処理 (Arc)
        p_lip_out = poles_out[-1]
        p_lip_in = poles_in[0]
        # 口元が尖らないよう、Z軸方向に肉厚分膨らませた中間点を計算
        p_lip_mid = FreeCAD.Vector((p_lip_out.x + p_lip_in.x) / 2.0, 0, max(p_lip_out.z, p_lip_in.z) + w * 0.4)
        arc_lip = Part.Arc(p_lip_out, p_lip_mid, p_lip_in).toShape()
        
        # 内側カーブ (BSpline)
        p_last = FreeCAD.Vector(0, 0, base_h + w)
        c_in = Part.BSplineCurve()
        c_in.buildFromPoles(poles_in + [p_last])
        
        # 各セグメントの直線
        l_axis = Part.makeLine(p_last, p0)
        l_base_in_top = Part.makeLine(p0, p1)
        l_base_in_side = Part.makeLine(p1, p2)
        l_base_bot = Part.makeLine(p2, p3)
        l_base_out = Part.makeLine(p3, p4)
        
        # 全てを繋いでひとつの閉じたワイヤーにする
        wire = Part.Wire([
            l_base_in_top, l_base_in_side, l_base_bot, l_base_out,
            c_out.toShape(), arc_lip, c_in.toShape(), l_axis
        ])
        return wire

    def create_sara(self, type_idx, h, d, w, lang):
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
        
        try:
            doc.openTransaction("Create Sara Model")
            with Progress.ProgressManager() as bar:
                bar.start(title=translate_text("お皿生成", lang), initial_text=translate_text("基本形状を計算中...", lang))

                r_max = d / 2.0

                # 1. ご飯の茶碗 (Rice Bowl)
                if type_idx == 0:
                    base_h = h * 0.15
                    base_r_out = r_max * 0.35
                    poles_out = [
                        FreeCAD.Vector(base_r_out + (r_max - base_r_out)*0.4, 0, base_h + (h - base_h)*0.3),
                        FreeCAD.Vector(r_max * 0.98, 0, h * 0.7),
                        FreeCAD.Vector(r_max, 0, h)
                    ]
                    poles_in = [
                        FreeCAD.Vector(r_max - w, 0, h),
                        FreeCAD.Vector(r_max * 0.98 - w, 0, h * 0.7),
                        FreeCAD.Vector(base_r_out + (r_max - base_r_out)*0.4 - w*0.8, 0, base_h + (h - base_h)*0.3 + w*0.8)
                    ]
                    label_name = "Rice_Bowl"
                    color = (0.95, 0.95, 0.90) # 白米が映えるオフホワイト

                # 2. みそ汁の茶碗 (Soup Bowl)
                elif type_idx == 1:
                    base_h = h * 0.15
                    base_r_out = r_max * 0.4
                    poles_out = [
                        FreeCAD.Vector(r_max * 0.9, 0, base_h + (h - base_h)*0.4),
                        FreeCAD.Vector(r_max, 0, h * 0.8),
                        FreeCAD.Vector(r_max * 0.96, 0, h)
                    ]
                    poles_in = [
                        FreeCAD.Vector(r_max * 0.96 - w, 0, h),
                        FreeCAD.Vector(r_max - w, 0, h * 0.8),
                        FreeCAD.Vector(r_max * 0.9 - w*0.8, 0, base_h + (h - base_h)*0.4 + w*0.8)
                    ]
                    label_name = "Soup_Bowl"
                    color = (0.40, 0.20, 0.10) # 漆器風の濃い茶色

                # 3. 小皿 (Small Plate)
                elif type_idx == 2:
                    base_h = h * 0.15
                    base_r_out = r_max * 0.45
                    poles_out = [
                        FreeCAD.Vector(base_r_out + (r_max - base_r_out)*0.5, 0, base_h + (h - base_h)*0.2),
                        FreeCAD.Vector(r_max, 0, h)
                    ]
                    poles_in = [
                        FreeCAD.Vector(r_max - w*0.5, 0, h),
                        FreeCAD.Vector(base_r_out + (r_max - base_r_out)*0.5 - w*0.8, 0, base_h + (h - base_h)*0.2 + w)
                    ]
                    label_name = "Small_Plate"
                    color = (0.92, 0.95, 0.98) # 清潔感のある薄いブルー

                # 4. 深い皿 (Deep Plate)
                else:
                    base_h = h * 0.1
                    base_r_out = r_max * 0.5
                    poles_out = [
                        FreeCAD.Vector(base_r_out + (r_max - base_r_out)*0.2, 0, base_h + (h - base_h)*0.1),
                        FreeCAD.Vector(r_max * 0.8, 0, base_h + (h - base_h)*0.4),
                        FreeCAD.Vector(r_max, 0, h)
                    ]
                    poles_in = [
                        FreeCAD.Vector(r_max - w*0.6, 0, h),
                        FreeCAD.Vector(r_max * 0.8 - w*0.8, 0, base_h + (h - base_h)*0.4 + w*0.8),
                        FreeCAD.Vector(base_r_out + (r_max - base_r_out)*0.2 - w, 0, base_h + (h - base_h)*0.1 + w)
                    ]
                    label_name = "Deep_Plate"
                    color = (0.98, 0.98, 0.98) # 真っ白

                bar.update(40, translate_text("断面プロファイルを構築中...", lang))
                wire = self.make_sara_profile(r_max, h, w, base_h, base_r_out, poles_out, poles_in)
                face = Part.Face(wire)
                
                bar.update(60, translate_text("360度回転成形（Revolve）中...", lang))
                # Z軸を中心に360度回転させて立体化
                sara_shape = face.revolve(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), 360)
                
                bar.update(85, translate_text("不要なシーム線を消去して最適化中...", lang))
                sara_shape = sara_shape.removeSplitter()

                obj = doc.addObject("Part::Feature", label_name)
                obj.Shape = sara_shape
                obj.ViewObject.ShapeColor = color
                obj.ViewObject.DisplayMode = "Flat Lines"
                if hasattr(obj.ViewObject, "Shininess"):
                    obj.ViewObject.Shininess = 0.8 # 陶器らしいツヤを付与

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

# ワークベンチへのコマンド登録
FreeCADGui.addCommand('Ring_MakeSara', Tool_MakeSara())