# -*- coding: utf-8 -*-
import os
import math
import FreeCAD
import FreeCADGui
import Part

# 【修正】絶対インポートで安全にCoreモジュールを読み込む
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedDialog, translate_text
from Core.Language import get_language

# 【修正】TranslatedDialog を継承させて自動翻訳を有効化
class SHookDialog(TranslatedDialog):
    def __init__(self, parent=None):
        super(SHookDialog, self).__init__(parent)
        self.setWindowTitle("S字フック製造工場")
        self.resize(380, 260)
        
        layout = QtWidgets.QFormLayout(self)
        
        # フック形状（丸型 / 角型）の選択ComboBox
        self.combo_type = QtWidgets.QComboBox()
        self.combo_type.addItems([
            "丸型 (なめらか曲線)",
            "角型 (かくかく直線)"
        ])
        
        self.spin_hook_d1 = QtWidgets.QDoubleSpinBox()
        self.spin_hook_d1.setRange(5.0, 1000.0)
        self.spin_hook_d1.setValue(40.0)
        self.spin_hook_d1.setSuffix(" mm")

        self.spin_hook_d2 = QtWidgets.QDoubleSpinBox()
        self.spin_hook_d2.setRange(5.0, 1000.0)
        self.spin_hook_d2.setValue(30.0)
        self.spin_hook_d2.setSuffix(" mm")
        
        self.spin_wire_d = QtWidgets.QDoubleSpinBox()
        self.spin_wire_d.setRange(0.5, 100.0)
        self.spin_wire_d.setValue(3.0)
        self.spin_wire_d.setSuffix(" mm")

        layout.addRow("<b>フックのタイプ:</b>", self.combo_type)
        layout.addRow("<b>上部フック幅(D1):</b>", self.spin_hook_d1)
        layout.addRow("<b>下部フック幅(D2):</b>", self.spin_hook_d2)
        layout.addRow("フック本体の太さ/線径(d):", self.spin_wire_d)
        layout.addRow(QtWidgets.QLabel("<p style='color:blue;'>※微小オーバーラップにより隙間なく滑らかに立体化します</p>"))
        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        return {
            "type_idx": self.combo_type.currentIndex(),
            "hook_r1": self.spin_hook_d1.value() / 2.0,
            "hook_r2": self.spin_hook_d2.value() / 2.0,
            "wire_r": self.spin_wire_d.value() / 2.0
        }

class Tool_MakeSHook:
    def GetResources(self):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "s.png").replace('\\', '/')
        return {
            'Pixmap': icon_path, 
            'MenuText': "S字フックの作成", 
            'ToolTip': "丸型・角型（かくかく）のS字フックを軽量かつ隙間なく自動生成します"
        }

    def Activated(self):
        lang = get_language()
        doc = FreeCAD.activeDocument()
        if not doc:
            doc = FreeCAD.newDocument("SHookDesign")

        d = SHookDialog()
        if d.exec_() != QtWidgets.QDialog.Accepted: 
            return
        vals = d.get_values()

        type_idx = vals["type_idx"]
        r_hook1 = vals["hook_r1"]
        r_hook2 = vals["hook_r2"]
        wire_r = vals["wire_r"]

        if wire_r >= r_hook1 or wire_r >= r_hook2:
            QtWidgets.QMessageBox.warning(None, translate_text("エラー", lang), translate_text("本体の太さ(d)は、フックの直径よりも細くしてください。", lang))
            return

        doc.openTransaction("CreateSHook")
        try:
            with Progress.ProgressManager() as bar:
                bar.start(title=translate_text("S字フック製造工場", lang), initial_text=translate_text("手順1: 骨格ラインの計算中...", lang))
                
                points = []
                
                # --- 1. 丸型 (なめらか曲線) の点群計算 ---
                if type_idx == 0:
                    deep_angle = 55.0 
                    total_angle = 180.0 + deep_angle
                    
                    rad_total = math.radians(total_angle)
                    segments1 = max(30, int((r_hook1 * rad_total) / 1.5))
                    segments2 = max(30, int((r_hook2 * rad_total) / 1.5))
                    
                    start_ang1 = -90.0 - deep_angle
                    end_ang1 = 90.0
                    for i in range(segments1 + 1):
                        deg = start_ang1 + ((end_ang1 - start_ang1) * i / segments1)
                        rad = math.radians(deg)
                        x = r_hook1 * math.cos(rad)
                        y = r_hook1 + r_hook1 * math.sin(rad)
                        points.append(FreeCAD.Vector(x, y, 0))
                        
                    start_ang2 = -90.0
                    end_ang2 = 90.0 + deep_angle
                    y_center2 = (2.0 * r_hook1) + r_hook2
                    for i in range(1, segments2 + 1):
                        deg = start_ang2 + ((end_ang2 - start_ang2) * i / segments2)
                        rad = math.radians(deg)
                        x = -r_hook2 * math.cos(rad)
                        y = y_center2 + r_hook2 * math.sin(rad)
                        points.append(FreeCAD.Vector(x, y, 0))

                # --- 2. 角型 (かくかく直角S字) の頂点計算 ---
                else:
                    w1 = r_hook1 * 2.0  # 上部フック幅
                    w2 = r_hook2 * 2.0  # 下部フック幅
                    h1 = r_hook1 * 1.2  # 上部先端のかえり高さ
                    h2 = r_hook2 * 1.2  # 下部先端のかえり高さ
                    stem_len = (r_hook1 + r_hook2) * 1.8  # 中央縦幹線の長さ

                    # P0: 上フック先端
                    # P1: 上フック左上角
                    # P2: 中央縦線の上端
                    # P3: 中央縦線の下端
                    # P4: 下フック右下角
                    # P5: 下フック先端
                    p0 = FreeCAD.Vector(-w1, stem_len - h1, 0)
                    p1 = FreeCAD.Vector(-w1, stem_len, 0)
                    p2 = FreeCAD.Vector(0, stem_len, 0)
                    p3 = FreeCAD.Vector(0, 0, 0)
                    p4 = FreeCAD.Vector(w2, 0, 0)
                    p5 = FreeCAD.Vector(w2, h2, 0)

                    key_pts = [p0, p1, p2, p3, p4, p5]
                    
                    for k in range(len(key_pts) - 1):
                        pt_a = key_pts[k]
                        pt_b = key_pts[k+1]
                        dist = (pt_b - pt_a).Length
                        sub_segs = max(2, int(dist / 2.0))
                        for s in range(sub_segs):
                            t = float(s) / sub_segs
                            points.append(pt_a + (pt_b - pt_a) * t)
                    points.append(key_pts[-1])

                parts_pool = []
                total_segments = len(points) - 1
                overlap_len = wire_r * 0.20 
                
                bar.update(30, translate_text("手順2: 各セグメントをスイープ接続中...", lang))

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
                    
                    percent = int(30 + (45 * i / total_segments))
                    if i % 10 == 0:
                        bar.update(percent, translate_text("オーバーラップパイプを生成中...", lang))

                bar.update(80, translate_text("手順3: 端部・関節部のフィレット処理中...", lang))
                for pt in points:
                    parts_pool.append(Part.makeSphere(wire_r, pt))

                bar.update(90, translate_text("手順4: 全パーツを統合中...", lang))
                final_shape = Part.makeCompound(parts_pool)

                bar.update(95, translate_text("最終処理: FreeCADオブジェクトへ登録中...", lang))
                label_str = "SHook_Angular" if type_idx == 1 else "SHook_Smooth"
                obj = doc.addObject("Part::Feature", label_str)
                obj.Shape = final_shape
                obj.ViewObject.ShapeColor = (0.75, 0.75, 0.8)
                
                doc.commitTransaction()
                doc.recompute()
                obj.ViewObject.DisplayMode = "Shaded"
                
                bar.update(100, translate_text("完了しました！", lang))
                
                if FreeCADGui.activeView():
                    FreeCADGui.activeView().fitAll()

        except Exception as e:
            doc.abortTransaction()
            FreeCAD.Console.PrintError(f"Hook creation error: {str(e)}\n")
            err_title = "Error" if lang == "English" else "エラー"
            err_msg = f"An error occurred during creation:\n{str(e)}" if lang == "English" else f"生成中にエラーが発生しました:\n{str(e)}"
            QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Ring_MakeSHook', Tool_MakeSHook())