# -*- coding: utf-8 -*-
import os
import math
import FreeCAD
import FreeCADGui
import Part

from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedDialog, translate_text
from Core.Language import get_language

def make_ngon_solid(r_bottom, r_top, sides, height, z_offset=0.0):
    """多角形ソリッド（テーパー対応）を生成するヘルパー関数"""
    pts_bot = []
    pts_top = []
    angle_offset = math.pi / sides  # 向きを整える回転オフセット
    
    for i in range(sides):
        ang = (2.0 * math.pi / sides) * i + angle_offset
        pts_bot.append(FreeCAD.Vector(r_bottom * math.cos(ang), r_bottom * math.sin(ang), z_offset))
        pts_top.append(FreeCAD.Vector(r_top * math.cos(ang), r_top * math.sin(ang), z_offset + height))
        
    pts_bot.append(pts_bot[0])
    pts_top.append(pts_top[0])
    
    wire_bot = Part.makePolygon(pts_bot)
    wire_top = Part.makePolygon(pts_top)
    
    if abs(r_bottom - r_top) < 0.001:
        face = Part.Face(wire_bot)
        return face.extrude(FreeCAD.Vector(0, 0, height))
    else:
        return Part.makeLoft([wire_bot, wire_top], True)

class ReceiptSpikeDialog(TranslatedDialog):
    def __init__(self, parent=None):
        super(ReceiptSpikeDialog, self).__init__(parent)
        self.setWindowTitle("レシート刺し製造工場")
        self.resize(380, 280)
        
        layout = QtWidgets.QFormLayout(self)
        
        self.combo_type = QtWidgets.QComboBox()
        self.combo_type.addItems([
            "ハチの巣 (Honeycomb Hexagon)",
            "ジオメトリック (Faceted Hexagon)",
            "モダン・8角形 (Modern Octagon)"
        ])
        
        self.spin_base_r = QtWidgets.QDoubleSpinBox()
        self.spin_base_r.setRange(10.0, 200.0)
        self.spin_base_r.setValue(35.0)
        self.spin_base_r.setSuffix(" mm")
        
        self.spin_base_t = QtWidgets.QDoubleSpinBox()
        self.spin_base_t.setRange(2.0, 50.0)
        self.spin_base_t.setValue(12.0)
        self.spin_base_t.setSuffix(" mm")
        
        self.spin_spike_h = QtWidgets.QDoubleSpinBox()
        self.spin_spike_h.setRange(20.0, 500.0)
        self.spin_spike_h.setValue(120.0)
        self.spin_spike_h.setSuffix(" mm")
        
        self.spin_spike_r = QtWidgets.QDoubleSpinBox()
        self.spin_spike_r.setRange(0.5, 10.0)
        self.spin_spike_r.setValue(2.0)
        self.spin_spike_r.setSuffix(" mm")
        
        layout.addRow("<b>デザインスタイル:</b>", self.combo_type)
        layout.addRow("<b>土台のサイズ (半径):</b>", self.spin_base_r)
        layout.addRow("<b>土台の厚み:</b>", self.spin_base_t)
        layout.addRow("<b>軸の高さ:</b>", self.spin_spike_h)
        layout.addRow("<b>軸の太さ (半径):</b>", self.spin_spike_r)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        return {
            "style_idx": self.combo_type.currentIndex(),
            "base_r": self.spin_base_r.value(),
            "base_t": self.spin_base_t.value(),
            "spike_h": self.spin_spike_h.value(),
            "spike_r": self.spin_spike_r.value()
        }

class Tool_MakeReceiptSpike:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "receipt_spike.png").replace('\\', '/')
        return {
            'Pixmap': icon_path, 
            'MenuText': "レシート刺しの作成", 
            'ToolTip': "ハチの巣・多角形スタイルのモダンなレシート刺しを自動生成します"
        }

    def Activated(self):
        lang = get_language()
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument("ReceiptSpikeDesign")

        d = ReceiptSpikeDialog(FreeCADGui.getMainWindow())
        if d.exec_() != QtWidgets.QDialog.Accepted: 
            return
        vals = d.get_values()

        style_idx = vals["style_idx"]
        base_r = vals["base_r"]
        base_t = vals["base_t"]
        spike_h = vals["spike_h"]
        spike_r = vals["spike_r"]

        doc.openTransaction("CreateReceiptSpike")
        try:
            with Progress.ProgressManager() as bar:
                bar.start(title=translate_text("レシート刺し製造工場", lang), initial_text=translate_text("基本形状を計算中...", lang))
                
                sides = 6 if style_idx in (0, 1) else 8
                
                # --- 1. 土台の生成 ---
                bar.update(20, translate_text("多角形土台を作成中...", lang))
                base_solid = make_ngon_solid(base_r, base_r * 0.85, sides, base_t)
                
                # スタイル0: ハチの巣パターン（天面に6つの六角形ポケットを削り出す）
                if style_idx == 0:
                    bar.update(40, translate_text("ハチの巣彫り込みパターンを演算中...", lang))
                    pocket_r = base_r * 0.22
                    pocket_dist = base_r * 0.52
                    pocket_depth = base_t * 0.35
                    
                    pockets = []
                    for i in range(6):
                        ang = (2.0 * math.pi / 6.0) * i
                        px = pocket_dist * math.cos(ang)
                        py = pocket_dist * math.sin(ang)
                        
                        p_solid = make_ngon_solid(pocket_r, pocket_r, 6, pocket_depth + 1.0, z_offset=base_t - pocket_depth)
                        p_solid.translate(FreeCAD.Vector(px, py, 0))
                        pockets.append(p_solid)
                    
                    for p in pockets:
                        base_solid = base_solid.cut(p)

                # --- 2. スパイク（軸）の生成 ---
                bar.update(60, translate_text("幾何学スパイク（軸）を作成中...", lang))
                cyl_h = spike_h - (spike_r * 4.0)
                if cyl_h <= 0: cyl_h = spike_h * 0.7
                cone_h = spike_h - cyl_h
                
                spike_stem = make_ngon_solid(spike_r, spike_r * 0.8, sides, cyl_h, z_offset=base_t)
                spike_tip = make_ngon_solid(spike_r * 0.8, 0.2, sides, cone_h, z_offset=base_t + cyl_h)
                spike_solid = spike_stem.fuse(spike_tip)

                # --- 3. 一体化と仕上げ ---
                bar.update(85, translate_text("パーツを結合・最適化中...", lang))
                final_shape = base_solid.fuse(spike_solid)
                final_shape = final_shape.removeSplitter()

                bar.update(95, translate_text("FreeCADへ登録中...", lang))
                obj = doc.addObject("Part::Feature", "ReceiptSpike_Modern")
                obj.Shape = final_shape
                obj.ViewObject.ShapeColor = (0.80, 0.75, 0.65) if style_idx == 0 else (0.75, 0.78, 0.82)
                obj.ViewObject.DisplayMode = "Flat Lines"
                
                doc.commitTransaction()
                doc.recompute()
                
                bar.update(100, translate_text("完了しました！", lang))
                if FreeCADGui.activeView():
                    FreeCADGui.activeView().fitAll()

        except Exception as e:
            doc.abortTransaction()
            FreeCAD.Console.PrintError(f"Receipt Spike creation error: {str(e)}\n")
            err_title = "Error" if lang == "English" else "エラー"
            err_msg = f"An error occurred during creation:\n{str(e)}" if lang == "English" else f"生成中にエラーが発生しました:\n{str(e)}"
            QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Ring_MakeReceiptSpike', Tool_MakeReceiptSpike())