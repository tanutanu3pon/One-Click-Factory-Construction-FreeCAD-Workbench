# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part
import Draft
import math
from Core.QtCompat import QtWidgets, QtGui, QtCore

# ?? Core/Progress.py から進捗マネージャーをインポート
import Core.Progress as Progress

class Tool_Tyoukoku:
    def GetResources(self):
        current_dir = os.path.dirname(__file__) 
        ring_dir = os.path.dirname(current_dir) 
        icon_path = os.path.join(ring_dir, "icons", "tyoukoku.png").replace('\\', '/')
        
        return {
            'Pixmap'  : icon_path, 
            'MenuText': "内面刻印（左から右）",
            'ToolTip' : "ひらがな・カタカナ・漢字・英数字をリングの内壁に彫刻します（進捗窓付き）"
        }

    def Activated(self):
        doc = FreeCAD.activeDocument()
        if not doc: return

        ring_obj = next((o for o in reversed(doc.Objects) if "Size" in o.Label), None)
        if not ring_obj:
            QtGui.QMessageBox.warning(None, "エラー", "リングが見つかりません。")
            return

        try:
            inner_r = min(math.sqrt(v.Point.x**2 + v.Point.y**2) for v in ring_obj.Shape.Vertexes)
        except:
            inner_r = 8.0
        
        text, ok1 = QtGui.QInputDialog.getText(None, "刻印設定", "彫る文字 (日本語対応):", text="拓也 to 結衣")
        if not ok1 or not text: return

        font_size, ok2 = QtGui.QInputDialog.getDouble(None, "寸法指定", "文字の大きさ (mm):", 1.2, 0.1, 10.0, 2)
        if not ok2: return

        depth, ok3 = QtGui.QInputDialog.getDouble(None, "寸法指定", "彫刻の深さ (mm):", 0.3, 0.01, 2.0, 2)
        if not ok3: return

        self.execute_engrave(doc, ring_obj, text, font_size, depth, inner_r)

    def execute_engrave(self, doc, ring_obj, text_str, font_size, depth, radius):
        bar = Progress.ProgressManager()
        bar.start(title="内面刻印処理", initial_text="OSの日本語フォントを探しています...")

        # ==========================================
        # ① 日本語対応フォントの自動選定
        # ==========================================
        font_candidates = [
            "C:/Windows/Fonts/meiryo.ttc",    # メイリオ（CAD向き）
            "C:/Windows/Fonts/msgothic.ttc",  # MS ゴシック
            "C:/Windows/Fonts/yugothr.ttf",   # 游ゴシック
            "C:/Windows/Fonts/arialbd.ttf"    # 予備
        ]
        
        font_path = "C:/Windows/Fonts/arialbd.ttf"
        for path in font_candidates:
            if os.path.exists(path):
                font_path = path
                break

        # ==========================================
        # ② 【最重要】各文字の実際の幅を事前スキャン（可変ピッチ計算）
        # ==========================================
        char_angles = []
        total_angle = 0.0
        letter_spacing = font_size * 0.12  # 文字同士の美しい隙間（カーニング幅）

        for char in text_str:
            if char == " ":
                # 半角スペースはフォントサイズの半分の幅を擬似的に持たせる
                w = font_size * 0.5
            else:
                # 一瞬だけ文字を作って、3D上の正確な横幅（BoundBox）を計測する
                ss_temp = Draft.makeShapeString(char, font_path, font_size)
                doc.recompute()
                bbox = ss_temp.Shape.BoundBox
                w = bbox.XMax - bbox.XMin
                # 極端に細い文字のめり込み防止セーフティ
                if w < font_size * 0.15:
                    w = font_size * 0.4
                doc.removeObject(ss_temp.Name)
            
            # この文字の配置に必要な角度を計算してストック
            ang = math.degrees((w + letter_spacing) / radius)
            char_angles.append(ang)
            total_angle += ang

        # 全体がリングの真ん中（センター）にくるように開始角度を逆算
        current_angle = (total_angle / 2.0) - (char_angles[0] / 2.0)

        compound_list = []
        total_chars = len(text_str)

        # ==========================================
        # ③ 各文字を固有の計算角度で内壁に配置
        # ==========================================
        for i, char in enumerate(text_str):
            if total_chars > 0:
                loop_percent = int(10 + (65 * (i / total_chars)))
                bar.update(loop_percent, f"立体文字を生成・内壁に配置中 ({i+1}/{total_chars}文字)...")

            if char == " ":
                # スペースの分だけ角度を進めてスキップ
                if i < total_chars - 1:
                    current_angle -= (char_angles[i]/2.0 + char_angles[i+1]/2.0)
                continue
            
            ss = Draft.makeShapeString(char, font_path, font_size)
            doc.recompute()
            
            # 文字自体のローカルBoundBoxを測定
            bbox = ss.Shape.BoundBox
            center_x = (bbox.XMax + bbox.XMin) / 2.0
            center_y = (bbox.YMax + bbox.YMin) / 2.0  # 上下のズレもこれで完全補正
            
            extrude_len = depth + 0.5
            char_shape = ss.Shape.extrude(FreeCAD.Vector(0, 0, extrude_len))
            
            # ? 1. 文字の「真の中心」をローカル原点(0,0)に強制移動（重心のズレを完全リセット）
            char_shape.translate(FreeCAD.Vector(-center_x, -center_y, 0))
            
            # 2. リングの内壁の向きに合わせる回転
            char_shape.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(1,0,0), 90)
            char_shape.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), -90)
            
            # 3. リングの内壁（半径方向）へパッと押し出す
            char_shape.translate(FreeCAD.Vector(radius - 0.1, 0, 0))
            
            # 4. 個別に計算された累積角度で正確に配置
            char_shape.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), current_angle)
            
            compound_list.append(char_shape)
            doc.removeObject(ss.Name)
            
            # ?? 【カーニング移動】次の文字のために、お互いの文字幅の半分ずつ角度を進める
            if i < total_chars - 1:
                current_angle -= (char_angles[i]/2.0 + char_angles[i+1]/2.0)

        # ==========================================
        # ④ 一括ブーリアン減算
        # ==========================================
        bar.update(80, "全文字を結合（コンパウンド作成）中...")

        if compound_list:
            try:
                bar.update(85, "リング内壁から文字データを減算（ブーリアンCut）中...")
                engraver = Part.makeCompound(compound_list)
                result_shape = ring_obj.Shape.cut(engraver)
                ring_obj.Shape = result_shape
            except Exception as e:
                bar.close() 
                FreeCAD.Console.PrintError(f"カット失敗: {str(e)}\n")
                return

        bar.update(100, "画面を更新しています...")
        bar.close()
        doc.recompute()

# 登録
FreeCADGui.addCommand('Ring_Tyoukoku', Tool_Tyoukoku())