# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
from PySide import QtWidgets

# ?? Core/Progress.py から【決定版】の進捗マネージャーをインポート
import Core.Progress as Progress

class Tool_Weight:
    def GetResources(self):
        current_dir = os.path.dirname(__file__) 
        ring_dir = os.path.dirname(current_dir) 
        icon_path = os.path.join(ring_dir, "icons", "weight.png").replace('\\', '/')
        
        return {
            'Pixmap'  : icon_path, 
            'MenuText': "地金・樹脂重量計算",
            'ToolTip' : "選択したモデルの体積から、各貴金属および3Dプリント用フィラメントの重量(g)を計算します（進捗窓付き）"
        }

    def Activated(self):
        # 1. 選択されたオブジェクトを取得
        sel = FreeCADGui.Selection.getSelection()
        
        if not sel:
            QtWidgets.QMessageBox.warning(None, "エラー", "重さを量りたいモデルを選択してから実行してください。")
            return

        # ==========================================
        # ? 【指示を出すだけ】最新のクラス方式で窓をスタート！
        # ==========================================
        bar = Progress.ProgressManager()
        bar.start(title="重量計算システム", initial_text="選択されたオブジェクトを解析中...")

        total_volume_mm3 = 0.0
        total_objects = len(sel)
        
        # 2. 選択された全オブジェクトの体積(立方ミリメートル)を合計
        for idx, obj in enumerate(sel):
            # 複数選択されている場合を考慮して、スキャン進行度を表示（20%?50%の間）
            if total_objects > 0:
                loop_percent = int(20 + (30 * (idx / total_objects)))
                bar.update(loop_percent, f"モデルの3D体積（メッシュ構造）を計測中 ({idx+1}/{total_objects})...")

            if hasattr(obj, "Shape") and not obj.Shape.isNull():
                total_volume_mm3 += obj.Shape.Volume
        
        # 体積がない場合のエラー処理
        if total_volume_mm3 <= 0:
            bar.close() # エラーで抜ける前にも確実に進捗窓を閉じる
            QtWidgets.QMessageBox.warning(None, "エラー", "体積を持たないオブジェクトです。立体モデルを選択してください。")
            return

        # --- 65% 完了 ---
        bar.update(65, "体積単位を mm3 から cm3 へ変換中...")
        # 3. 立方ミリメートル (mm3) を 立方センチメートル (cm3) に変換
        volume_cm3 = total_volume_mm3 / 1000.0

        # --- 80% 完了 ---
        bar.update(80, "各貴金属および3Dプリンター用樹脂の比重から重量を試算中...")

        # 4. 各素材の一般的な比重（密度: g/cm3）
        metals = {
            "シルバー (SV925)": 10.4,
            "10金 (K10 ゴールド)": 11.6,
            "18金 (K18 ゴールド)": 15.5,
            "純金 (K24)": 19.3,
            "プラチナ (Pt950)": 20.5,
            "真鍮 (Brass)": 8.5
        }

        filaments = {
            "PLA フィラメント": 1.24,       
            "ABS フィラメント": 1.04,       
            "PETG フィラメント": 1.27,      
            "TPU (フレキシブル)": 1.21,     
            "UV造形レジン (光造形)": 1.15   
        }

        # 5. 画面に表示するテキストを作成
        result_text = f"合計体積 : {volume_cm3:.3f} cm3\n\n"
        
        # --- 上部：指輪・ジュエリー用貴金属 ---
        result_text += "【 ジュエリー用貴金属 重量 】\n"
        result_text += "-" * 35 + "\n"
        for metal, density in metals.items():
            weight = volume_cm3 * density
            result_text += f"  {metal:<16} : {weight:.2f} g\n"

        result_text += "\n"

        # --- 下部：家庭用3Dプリンター用フィラメント ---
        result_text += "【 3Dプリンター用樹脂 重量 】\n"
        result_text += "-" * 35 + "\n"
        for plastic, density in filaments.items():
            weight = volume_cm3 * density
            result_text += f"  {plastic:<16} : {weight:.2f} g\n"

        # --- 95% 完了 ---
        bar.update(95, "計算結果レポートを構築中...")

        # ==========================================
        # ?? 【最重要】ポップアップ窓を出す直前に、進捗バーを100%にして綺麗に閉じる
        # （閉じずにQMessageBoxを出すと、進捗窓が後ろに残って邪魔になるのを防ぎます）
        # ==========================================
        bar.update(100, "計算完了！")
        bar.close()

        # 6. メッセージボックス（ポップアップ）で結果を表示
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle("重量 (グラム) 計算結果")
        msg.setText("選択したモデルの推定重量です。")
        msg.setInformativeText(result_text)
        msg.setIcon(QtWidgets.QMessageBox.Information) 
        msg.exec_()

# コマンド登録
FreeCADGui.addCommand('Ring_Weight', Tool_Weight())