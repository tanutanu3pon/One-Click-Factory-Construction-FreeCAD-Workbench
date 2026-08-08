# -*- coding: utf-8 -*-
# Tool/MakeSHook.py
import os
import math
import FreeCAD
import FreeCADGui
import Part

# Qtの互換性確保
from Core.QtCompat import QtWidgets, QtGui, QtCore

import Core.Progress as Progress

# ==========================================
# S字フック専用の設定ダイアログ窓
# ==========================================
class SHookDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(SHookDialog, self).__init__(parent)
        self.setWindowTitle("S字フック製造工場 (軽量オーバーラップ仕様)")
        self.resize(380, 220)
        
        layout = QtWidgets.QFormLayout(self)
        
        # 上部フックの曲がり直径 (D1)
        self.spin_hook_d1 = QtWidgets.QDoubleSpinBox()
        self.spin_hook_d1.setRange(5.0, 1000.0)
        self.spin_hook_d1.setValue(40.0)
        self.spin_hook_d1.setSuffix(" mm")

        # 下部フックの曲がり直径 (D2)
        self.spin_hook_d2 = QtWidgets.QDoubleSpinBox()
        self.spin_hook_d2.setRange(5.0, 1000.0)
        self.spin_hook_d2.setValue(30.0)
        self.spin_hook_d2.setSuffix(" mm")
        
        # 本体の太さ（線径の直径 d）
        self.spin_wire_d = QtWidgets.QDoubleSpinBox()
        self.spin_wire_d.setRange(0.5, 100.0)
        self.spin_wire_d.setValue(3.0)
        self.spin_wire_d.setSuffix(" mm")

        layout.addRow("<b>上部フック直径(D1):</b>", self.spin_hook_d1)
        layout.addRow("<b>下部フック直径(D2):</b>", self.spin_hook_d2)
        layout.addRow("フック本体の太さ/線径(d):", self.spin_wire_d)
        layout.addRow(QtWidgets.QLabel("<p style='color:blue;'>※微小オーバーラップにより、軽量なまま隙間を隠します</p>"))
        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.button(QtWidgets.QDialogButtonBox.Ok).setText("S字フックを生成")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        return {
            "hook_r1": self.spin_hook_d1.value() / 2.0,
            "hook_r2": self.spin_hook_d2.value() / 2.0,
            "wire_r": self.spin_wire_d.value() / 2.0
        }

# ==========================================
# ツール本体（超軽量・視覚補完モデル）
# ==========================================
class Tool_MakeSHook:
    def GetResources(self):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "s.png").replace('\\', '/')
        return {
            'Pixmap': icon_path, 
            'MenuText': "S字フックの作成", 
            'ToolTip': "データを極限まで軽く保ちつつ、隙間のない滑らかな外観を生成します"
        }

    def Activated(self):
        doc = FreeCAD.activeDocument()
        if not doc:
            doc = FreeCAD.newDocument("SHookDesign")

        d = SHookDialog()
        if d.exec_() != QtWidgets.QDialog.Accepted: 
            return
        vals = d.get_values()

        r_hook1 = vals["hook_r1"]
        r_hook2 = vals["hook_r2"]
        wire_r = vals["wire_r"]

        if wire_r >= r_hook1 or wire_r >= r_hook2:
            QtWidgets.QMessageBox.warning(None, "エラー", "本体の太さ(d)は、フックの直径よりも細くしてください。")
            return

        try:
            # with構文で囲むことで、例外発生時の abortTransaction やプログレスバーの close が全自動化されます
            with Progress.safe_transaction("S字フック製造工場", "手順1: 最適な分割密度を自動演算中...", doc=doc) as bar:
                
                # --------------------------------------------------
                # ① 適応型分割数の自動計算
                # --------------------------------------------------
                points = []
                deep_angle = 55.0 
                total_angle = 180.0 + deep_angle
                
                rad_total = math.radians(total_angle)
                segments1 = max(30, int((r_hook1 * rad_total) / 1.5))
                segments2 = max(30, int((r_hook2 * rad_total) / 1.5))
                
                # 上部フック
                start_ang1 = -90.0 - deep_angle
                end_ang1 = 90.0
                for i in range(segments1 + 1):
                    deg = start_ang1 + ((end_ang1 - start_ang1) * i / segments1)
                    rad = math.radians(deg)
                    x = r_hook1 * math.cos(rad)
                    y = r_hook1 + r_hook1 * math.sin(rad)
                    points.append(FreeCAD.Vector(x, y, 0))
                    
                # 下部フック
                start_ang2 = -90.0
                end_ang2 = 90.0 + deep_angle
                y_center2 = (2.0 * r_hook1) + r_hook2
                for i in range(1, segments2 + 1):
                    deg = start_ang2 + ((end_ang2 - start_ang2) * i / segments2)
                    rad = math.radians(deg)
                    x = -r_hook2 * math.cos(rad)
                    y = y_center2 + r_hook2 * math.sin(rad)
                    points.append(FreeCAD.Vector(x, y, 0))

                # --------------------------------------------------
                # ② 各分割線形での個別スイープ実行（食い込み処理を追加）
                # --------------------------------------------------
                parts_pool = []
                total_segments = len(points) - 1
                overlap_len = wire_r * 0.20 
                
                for i in range(total_segments):
                    p1 = points[i]
                    p2 = points[i+1]
                    vec = p2 - p1
                    length = vec.Length
                    
                    if length > 0.0001:
                        direction = vec.normalize()
                        
                        circle_edge = Part.makeCircle(wire_r, p1, direction)
                        profile_face = Part.Face(Part.Wire([circle_edge]))
                        
                        p2_extended = p1 + direction * (length + overlap_len)
                        
                        line_edge = Part.makeLine(p1, p2_extended)
                        line_path = Part.Wire([line_edge])
                        
                        segment_solid = line_path.makePipe(profile_face)
                        parts_pool.append(segment_solid)
                    
                    percent = int(20 + (50 * i / total_segments))
                    if i % 10 == 0:
                        bar.update(percent, f"手順3?4: 超軽量オーバーラップスイープ中... ({i}/{total_segments})")

                # --------------------------------------------------
                # ③ 両端の丸め処理
                # --------------------------------------------------
                bar.update(75, "手順4.5: 端部のフィレット球体を生成中...")
                sphere_start = Part.makeSphere(wire_r, points[0])
                sphere_end = Part.makeSphere(wire_r, points[-1])
                parts_pool.append(sphere_start)
                parts_pool.append(sphere_end)

                # --------------------------------------------------
                # ④ 複合体（Compound）化と画面更新
                # --------------------------------------------------
                bar.update(85, "手順5: 全パーツを複合体(Compound)に一括統合中...")
                final_shape = Part.makeCompound(parts_pool)

                bar.update(95, "最終処理: 画面の3D描画を更新中...")
                obj = doc.addObject("Part::Feature", "SHook")
                obj.Shape = final_shape
                obj.ViewObject.ShapeColor = (0.75, 0.75, 0.8)
                
                doc.recompute()
                obj.ViewObject.DisplayMode = "Shaded"
                
                bar.update(100, "超軽量・高外観なS字フックが完成しました！")
                
                if FreeCADGui.activeView():
                    FreeCADGui.activeView().fitAll()

        except Exception as e:
            FreeCAD.Console.PrintError(f"生成に失敗しました: {str(e)}\n")
            QtWidgets.QMessageBox.critical(None, "エラー", f"生成中にエラーが発生しました:\n{str(e)}")

# コマンド登録
FreeCADGui.addCommand('Ring_MakeSHook', Tool_MakeSHook())