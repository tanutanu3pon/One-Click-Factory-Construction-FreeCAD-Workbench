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
    angle_offset = math.pi / sides
    
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

def apply_safe_fillet(solid, radius):
    """エラー回避のための安全なフィレット処理"""
    if radius <= 0.0:
        return solid
    try:
        # 半径に対して短すぎるエッジを除外してフィレットを適用（トポロジー破壊防止）
        edges = [e for e in solid.Edges if e.Length > radius * 2.05]
        if edges:
            filleted = solid.makeFillet(radius, edges)
            if not filleted.isNull():
                return filleted
    except Exception as e:
        FreeCAD.Console.PrintWarning(f"Fillet failed (skipped): {str(e)}\n")
    return solid

class CardHolderDialog(TranslatedDialog):
    def __init__(self, parent=None):
        super(CardHolderDialog, self).__init__(parent)
        self.setWindowTitle("カード刺し製造工場")
        self.resize(380, 320)
        
        layout = QtWidgets.QFormLayout(self)
        
        self.combo_type = QtWidgets.QComboBox()
        self.combo_type.addItems([
            "モダン・スリットブロック (Single Slotted Base)",
            "多段ステップスタンド (Multi-Card Tiered)",
            "ポール・ピンチ型 (Pole Pinch Stand)"
        ])
        
        self.spin_base_w = QtWidgets.QDoubleSpinBox()
        self.spin_base_w.setRange(10.0, 300.0)
        self.spin_base_w.setValue(50.0)
        self.spin_base_w.setSuffix(" mm")
        
        self.spin_base_h = QtWidgets.QDoubleSpinBox()
        self.spin_base_h.setRange(5.0, 200.0)
        self.spin_base_h.setValue(20.0)
        self.spin_base_h.setSuffix(" mm")
        
        self.spin_slot_w = QtWidgets.QDoubleSpinBox()
        self.spin_slot_w.setRange(0.5, 10.0)
        self.spin_slot_w.setValue(1.5)
        self.spin_slot_w.setSingleStep(0.1)
        self.spin_slot_w.setSuffix(" mm")
        
        self.spin_slot_angle = QtWidgets.QDoubleSpinBox()
        self.spin_slot_angle.setRange(0.0, 45.0)
        self.spin_slot_angle.setValue(15.0)
        self.spin_slot_angle.setSuffix(" 度")

        self.spin_fillet_r = QtWidgets.QDoubleSpinBox()
        self.spin_fillet_r.setRange(0.0, 10.0)
        self.spin_fillet_r.setValue(2.0)
        self.spin_fillet_r.setSingleStep(0.5)
        self.spin_fillet_r.setSuffix(" mm (0で丸めなし)")
        
        layout.addRow("<b>デザインタイプ:</b>", self.combo_type)
        layout.addRow("<b>土台の幅/外径 (mm):</b>", self.spin_base_w)
        layout.addRow("<b>土台の高さ (mm):</b>", self.spin_base_h)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        layout.addRow("<b>カード挿入溝の幅 (mm):</b>", self.spin_slot_w)
        layout.addRow("<b>カードの傾斜角度:</b>", self.spin_slot_angle)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        layout.addRow("<b>角の丸み (フィレット半径):</b>", self.spin_fillet_r)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        return {
            "style_idx": self.combo_type.currentIndex(),
            "base_w": self.spin_base_w.value(),
            "base_h": self.spin_base_h.value(),
            "slot_w": self.spin_slot_w.value(),
            "slot_angle": self.spin_slot_angle.value(),
            "fillet_r": self.spin_fillet_r.value()
        }

class Tool_MakeCardHolder:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "card_holder.png").replace('\\', '/')
        return {
            'Pixmap': icon_path, 
            'MenuText': "カード刺しの作成", 
            'ToolTip': "カード・名刺・写真をスマートに飾るカードスタンドを生成します"
        }

    def Activated(self):
        lang = get_language()
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument("CardHolderDesign")

        d = CardHolderDialog(FreeCADGui.getMainWindow())
        if d.exec_() != QtWidgets.QDialog.Accepted: 
            return
        vals = d.get_values()

        style_idx = vals["style_idx"]
        base_w = vals["base_w"]
        base_h = vals["base_h"]
        slot_w = vals["slot_w"]
        slot_angle = vals["slot_angle"]
        fillet_r = vals["fillet_r"]

        doc.openTransaction("CreateCardHolder")
        try:
            with Progress.ProgressManager() as bar:
                bar.start(title=translate_text("カード刺し製造工場", lang), initial_text=translate_text("形状を計算中...", lang))
                
                # --- カッター（カード挿入溝）生成関数 ---
                def create_slot_cutter(s_width, s_depth, s_length, angle_deg, pos_vector):
                    box = Part.makeBox(s_length, s_width, s_depth)
                    box.translate(FreeCAD.Vector(-s_length / 2.0, -s_width / 2.0, 0))
                    
                    if angle_deg != 0:
                        rot = FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), angle_deg)
                        box.Placement.Rotation = rot
                        
                    box.translate(pos_vector)
                    return box

                # --- 1. スタイル: モダン・スリットブロック ---
                if style_idx == 0:
                    bar.update(30, translate_text("重厚感のある土台を作成中...", lang))
                    r_base = base_w / 2.0
                    base_solid = make_ngon_solid(r_base, r_base * 0.9, 6, base_h)
                    
                    # カッター加工前にフィレット適用
                    bar.update(45, translate_text("角の丸め加工（フィレット）中...", lang))
                    base_solid = apply_safe_fillet(base_solid, fillet_r)
                    
                    bar.update(60, translate_text("カード挿入スリットを溝切り加工中...", lang))
                    slot_depth = base_h * 0.7
                    cutter = create_slot_cutter(
                        s_width=slot_w, 
                        s_depth=slot_depth + 5.0, 
                        s_length=base_w * 1.2, 
                        angle_deg=slot_angle, 
                        pos_vector=FreeCAD.Vector(0, 0, base_h - slot_depth)
                    )
                    final_shape = base_solid.cut(cutter)

                # --- 2. スタイル: 多段ステップスタンド ---
                elif style_idx == 1:
                    bar.update(30, translate_text("段差付きステップ土台を作成中...", lang))
                    steps = 3
                    step_h = base_h / steps
                    step_w = base_w
                    step_d = base_w * 0.8
                    
                    part_list = []
                    for i in range(steps):
                        h_curr = step_h * (i + 1)
                        y_curr = (step_d / steps) * i
                        b = Part.makeBox(step_w, step_d / steps, h_curr)
                        b.translate(FreeCAD.Vector(-step_w / 2.0, y_curr - step_d / 2.0, 0))
                        part_list.append(b)
                        
                    base_solid = part_list[0]
                    for p in part_list[1:]:
                        base_solid = base_solid.fuse(p)
                    
                    # 結合された全体にフィレット適用
                    bar.update(45, translate_text("角の丸め加工（フィレット）中...", lang))
                    base_solid = apply_safe_fillet(base_solid, fillet_r)
                        
                    bar.update(60, translate_text("複数カード用スリット群をブーリアン減算中...", lang))
                    cutters = []
                    for i in range(steps):
                        h_curr = step_h * (i + 1)
                        y_curr = (step_d / steps) * i
                        slot_depth = step_h * 0.8
                        
                        c = create_slot_cutter(
                            s_width=slot_w,
                            s_depth=slot_depth + 2.0,
                            s_length=step_w * 1.1,
                            angle_deg=slot_angle,
                            pos_vector=FreeCAD.Vector(0, y_curr - step_d / 2.0 + (step_d / (steps * 2)), h_curr - slot_depth)
                        )
                        cutters.append(c)
                        
                    for c in cutters:
                        base_solid = base_solid.cut(c)
                    final_shape = base_solid

                # --- 3. スタイル: ポール・ピンチ型 ---
                else:
                    bar.update(30, translate_text("スタンドベースと支柱（ポール）を作成中...", lang))
                    r_base = base_w / 2.0
                    base_plate = Part.makeCylinder(r_base, 8.0)
                    
                    pole_r = max(2.0, slot_w * 1.5)
                    pole_h = base_h
                    pole = Part.makeCylinder(pole_r, pole_h, FreeCAD.Vector(0, 0, 8.0))
                    
                    head_r = pole_r * 2.2
                    head_h = head_r * 2.0
                    head = Part.makeSphere(head_r, FreeCAD.Vector(0, 0, 8.0 + pole_h))
                    
                    combined = base_plate.fuse(pole).fuse(head)
                    
                    bar.update(45, translate_text("角の丸め加工（フィレット）中...", lang))
                    combined = apply_safe_fillet(combined, fillet_r)
                    
                    bar.update(70, translate_text("先端ピンチスリットを切削中...", lang))
                    slot_depth = head_r * 1.8
                    cutter = create_slot_cutter(
                        s_width=slot_w,
                        s_depth=slot_depth + 2.0,
                        s_length=head_r * 2.5,
                        angle_deg=slot_angle,
                        pos_vector=FreeCAD.Vector(0, 0, 8.0 + pole_h - (head_r * 0.5))
                    )
                    final_shape = combined.cut(cutter)

                bar.update(90, translate_text("不要なシーム線を最適化中...", lang))
                final_shape = final_shape.removeSplitter()

                bar.update(95, translate_text("FreeCADへ登録中...", lang))
                obj = doc.addObject("Part::Feature", "CardHolder_Stand")
                obj.Shape = final_shape
                obj.ViewObject.ShapeColor = (0.82, 0.70, 0.55) if style_idx == 1 else (0.70, 0.75, 0.80)
                obj.ViewObject.DisplayMode = "Flat Lines"
                
                doc.commitTransaction()
                doc.recompute()
                
                bar.update(100, translate_text("完了しました！", lang))
                if FreeCADGui.activeView():
                    FreeCADGui.activeView().fitAll()

        except Exception as e:
            doc.abortTransaction()
            FreeCAD.Console.PrintError(f"Card Holder creation error: {str(e)}\n")
            err_title = "Error" if lang == "English" else "エラー"
            err_msg = f"An error occurred during creation:\n{str(e)}" if lang == "English" else f"生成中にエラーが発生しました:\n{str(e)}"
            QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Ring_MakeCardHolder', Tool_MakeCardHolder())