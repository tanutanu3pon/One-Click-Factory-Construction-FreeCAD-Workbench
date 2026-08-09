# -*- coding: utf-8 -*-
import os
import math
import FreeCAD
import FreeCADGui
import Part

# 【修正】絶対インポートで安全にCoreモジュールを読み込む
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedInputDialog, translate_text
from Core.Language import get_language

class Tool_Magatama:
    def GetResources(self):
        current_dir = os.path.dirname(__file__)
        ring_dir = os.path.dirname(current_dir)
        icon_path = os.path.join(ring_dir, "icons", "magatama.png").replace('\\', '/')
        
        return {
            'Pixmap'  : icon_path,
            'MenuText': "勾玉作成",
            'ToolTip' : "ロフト機能を利用して日本古来の勾玉を生成します（進捗窓付き）"
        }

    def Activated(self):
        lang = get_language()

        # 【追加】勾玉のスタイル選択（伝統型 / 出雲型 / スリム型）
        types = [
            "伝統型 (標準的な丸み)",
            "出雲型 (ぽっちゃり太尾)",
            "スリム型 (シャープな尾線)"
        ]
        
        selected_type, ok0 = TranslatedInputDialog.getItem(None, "勾玉設計", "勾玉のスタイル:", types, 0, False)
        if not ok0: return

        trans_types = [translate_text(t, lang) for t in types]
        if selected_type in types:
            type_idx = types.index(selected_type)
        elif selected_type in trans_types:
            type_idx = trans_types.index(selected_type)
        else:
            type_idx = 0

        r, ok1 = TranslatedInputDialog.getDouble(None, "勾玉設計", "頭部の半径 (mm):", 5.0, 1.0, 50.0, 1)
        if not ok1: return
        
        default_angle = 220.0 if type_idx == 0 else (200.0 if type_idx == 1 else 240.0)
        angle, ok2 = TranslatedInputDialog.getDouble(None, "勾玉設計", "巻きの角度 (度, 180~270がお勧め):", default_angle, 90.0, 360.0, 1)
        if not ok2: return

        hole_r, ok3 = TranslatedInputDialog.getDouble(None, "勾玉設計", "穴の半径 (mm):", 1.5, 0.0, r-0.5, 1)
        if not ok3: return

        self.create_magatama(r, angle, hole_r, type_idx, lang)

    def create_magatama(self, R, angle_deg, hole_r, type_idx, lang):
        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("勾玉モデル生成", lang), initial_text=translate_text("頭部（球体）を生成中...", lang))

            doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
            
            t_max = math.radians(angle_deg)
            
            # 【追加】タイプに応じたカーブの膨らみ（指数）と背面カーブ半径を設定
            if type_idx == 1:  # 出雲型（太くて力強い尾）
                decay_exp = 0.45
                spine_R = R * 1.15
                label_prefix = "Magatama_Izumo"
            elif type_idx == 2:  # スリム型（スマートな細尾）
                decay_exp = 1.10
                spine_R = R * 1.50
                label_prefix = "Magatama_Slim"
            else:  # 伝統型（標準）
                decay_exp = 0.70
                spine_R = R * 1.30
                label_prefix = "Magatama_Traditional"

            head = Part.makeSphere(R)

            bar.update(15, translate_text("尾部の断面曲線をスキャン計算中...", lang))
            
            wires = []
            steps = 40
            
            for i in range(steps + 1):
                t = t_max * (i / steps)
                
                cx = spine_R - spine_R * math.cos(t)
                cy = spine_R * math.sin(t)
                cz = 0.0
                center = FreeCAD.Vector(cx, cy, cz)
                
                nx = math.sin(t)
                ny = math.cos(t)
                nz = 0.0
                normal = FreeCAD.Vector(nx, ny, nz)
                
                ratio = t / t_max
                current_r = R * math.pow(1.0 - ratio, decay_exp)
                current_r = max(0.05, current_r)
                
                circle_edge = Part.makeCircle(current_r, center, normal)
                wire = Part.Wire([circle_edge])
                wires.append(wire)
                
                if i % 5 == 0:
                    loop_percent = int(15 + (40 * (i / steps)))
                    bar.update(loop_percent, translate_text("尾部の外郭スキンを構築中...", lang))

            bar.update(60, translate_text("断面を繋いで尾部をロフト立体化中...", lang))
            tail = Part.makeLoft(wires, True)

            bar.update(75, translate_text("頭部と尾部をブーリアン結合中...", lang))
            magatama_base = head.fuse(tail)

            if hole_r > 0:
                bar.update(85, translate_text("紐通し用の穴をくり抜き（Cut）中...", lang))
                get_vector_start = FreeCAD.Vector(0, 0, -R * 1.5)
                get_vector_dir = FreeCAD.Vector(0, 0, 1)
                hole_cyl = Part.makeCylinder(hole_r, R * 3, get_vector_start, get_vector_dir)
                magatama_final = magatama_base.cut(hole_cyl)
            else:
                bar.update(85, translate_text("形状データをクリーニング中...", lang))
                magatama_final = magatama_base

            bar.update(95, translate_text("シーム（結合線）を消去してツルツルに最適化中...", lang))
            magatama_final = magatama_final.removeSplitter()

            obj = doc.addObject("Part::Feature", label_prefix)
            obj.Shape = magatama_final
            
            # タイプ別の標準カラーリング
            if type_idx == 1:
                obj.ViewObject.ShapeColor = (0.15, 0.55, 0.35)  # 濃い翡翠色
            elif type_idx == 2:
                obj.ViewObject.ShapeColor = (0.35, 0.75, 0.65)  # アマゾナイトブルー
            else:
                obj.ViewObject.ShapeColor = (0.20, 0.70, 0.40)  # 明るい翡翠色

            obj.ViewObject.DisplayMode = "Flat Lines"
            
            bar.update(100, translate_text("画面を更新しています...", lang))
            
            doc.recompute()
            FreeCADGui.activeView().fitAll()

FreeCADGui.addCommand('Ring_Magatama', Tool_Magatama())