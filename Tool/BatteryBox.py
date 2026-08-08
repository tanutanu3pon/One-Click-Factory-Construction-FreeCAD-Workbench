# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part

# Qtの互換性確保（PySide2 / PySide6 両対応）
from Core.QtCompat import QtWidgets, QtGui, QtCore

import Core.Progress as Progress

# ==========================================
# ??? 電池の規格データ（直径, 長さ, 金具用余白, 側面遊び）
# ==========================================
BATTERY_SPECS = {
    "単1形 (D)": {"d": 34.2, "l": 61.5, "margin_l": 6.0, "margin_d": 0.6},
    "単3形 (AA)": {"d": 14.5, "l": 50.5, "margin_l": 4.5, "margin_d": 0.4},
    "単4形 (AAA)": {"d": 10.5, "l": 44.5, "margin_l": 4.5, "margin_d": 0.4},
}

# ==========================================
# ?? ダイヤログ画面
# ==========================================
class BatteryBoxDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(BatteryBoxDialog, self).__init__(parent)
        self.setWindowTitle("電池ボックスの設計")
        self.resize(320, 280)
        layout = QtWidgets.QFormLayout(self)
        
        self.combo_type = QtWidgets.QComboBox()
        self.combo_type.addItems(list(BATTERY_SPECS.keys()))
        
        self.spin_count = QtWidgets.QSpinBox()
        self.spin_count.setRange(1, 10)
        self.spin_count.setValue(2)
        self.spin_count.setSuffix(" 本")
        
        self.group_dir = QtWidgets.QButtonGroup(self)
        self.radio_horizontal = QtWidgets.QRadioButton("水平方向 (横に並べる)")
        self.radio_straight = QtWidgets.QRadioButton("直線方向 (縦につなげる)")
        self.radio_horizontal.setChecked(True)
        self.group_dir.addButton(self.radio_horizontal, 0)
        self.group_dir.addButton(self.radio_straight, 1)
        
        v_layout = QtWidgets.QVBoxLayout()
        v_layout.addWidget(self.radio_horizontal)
        v_layout.addWidget(self.radio_straight)
        
        self.spin_wall = QtWidgets.QDoubleSpinBox()
        self.spin_wall.setRange(1.5, 5.0)
        self.spin_wall.setValue(2.5)
        self.spin_wall.setSuffix(" mm")
        
        self.check_heat_hole = QtWidgets.QCheckBox("底面に軽量化・排熱用の穴をあける")
        self.check_heat_hole.setChecked(True)
        
        layout.addRow("電池の種類:", self.combo_type)
        layout.addRow("配置本数:", self.spin_count)
        layout.addRow("繋げる方向:", v_layout)
        layout.addRow("外壁の厚み:", self.spin_wall)
        layout.addRow("", self.check_heat_hole)
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        direction = "Horizontal" if self.radio_horizontal.isChecked() else "Straight"
        return (self.combo_type.currentText(), self.spin_count.value(), direction, self.spin_wall.value(), self.check_heat_hole.isChecked())


# ==========================================
# ? ツール本体
# ==========================================
class Tool_MakeBatteryBox:
    def GetResources(self):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "battery.png").replace('\\', '/')
        return {
            'Pixmap': icon_path, 
            'MenuText': "電池ボックス作成", 
            'ToolTip': "条件を指定して最適な電池ボックスを生成します"
        }

    def Activated(self):
        d = BatteryBoxDialog()
        if d.exec_() != QtWidgets.QDialog.Accepted: 
            return
            
        b_type, b_count, b_dir, wall_t, need_hole = d.get_values()
        self.create_battery_box(b_type, b_count, b_dir, wall_t, need_hole)

    def create_battery_box(self, b_type, b_count, b_dir, wall_t, need_hole):
        bar = Progress.ProgressManager()
        bar.start(title="電池BOX生成", initial_text="仕切り壁の計算中...")
        
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
        
        spec = BATTERY_SPECS[b_type]
        slot_w = spec["d"] + spec["margin_d"]
        slot_l = spec["l"] + spec["margin_l"]
        radius = slot_w / 2.0
        
        divider_t = 1.8 if "単1形" in b_type else 1.5
        
        if b_dir == "Horizontal":
            total_w = (slot_w * b_count) + (divider_t * (b_count - 1)) + (wall_t * 2.0)
            total_l = slot_l + (wall_t * 2.0)
        else:
            total_w = slot_w + (wall_t * 2.0)
            total_l = (slot_l * b_count) + (divider_t * (b_count - 1)) + (wall_t * 2.0)
            
        total_h = radius + (spec["d"] * 0.35) + wall_t

        bar.update(20, "外殻（ベース）を作成中...")
        # 最終的な成果物となる形状のベース
        box_shape = Part.makeBox(total_w, total_l, total_h)
        
        bar.update(50, "電池スロットおよび穴の形状を計算・減算中...")
        
        # 直方体（排熱穴用）の基本サイズを定義
        hole_w = slot_w * 0.5
        hole_l = slot_l - 10.0 
        hole_h = wall_t + 5.0  # 底面を絶対に突き抜けるように高さを拡大（余裕を持たせる）

        # ?? 各スロットの計算と、ベース形状からの直接減算ループ
        for i in range(b_count):
            if b_dir == "Horizontal":
                slot_center_x = wall_t + i * (slot_w + divider_t) + radius
                slot_start_y = wall_t
            else:
                slot_center_x = wall_t + radius
                slot_start_y = wall_t + i * (slot_l + divider_t)

            # ① 円柱スロット（電池の入る空間）の作成
            cylinder_slot = Part.makeCylinder(radius, slot_l)
            cylinder_slot.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(1,0,0), -90)
            
            top_box = Part.makeBox(slot_w, slot_l, total_h + 2.0)
            top_box.translate(FreeCAD.Vector(-radius, 0, 0))
            slot_shape = cylinder_slot.fuse(top_box)
            slot_shape.translate(FreeCAD.Vector(slot_center_x, slot_start_y, wall_t + radius))
            
            # 本体から電池スロットを直接カット
            box_shape = box_shape.cut(slot_shape)

            # ② 水平方向かつ2本目以降の場合、仕切り壁を低くするカット処理
            if b_dir == "Horizontal" and i > 0:
                div_x = wall_t + i * (slot_w + divider_t) - divider_t
                remaining_h = total_h * (2.0 / 3.0)
                cut_h = total_h - remaining_h + 2.0
                
                div_cutter = Part.makeBox(divider_t, slot_l, cut_h)
                div_cutter.translate(FreeCAD.Vector(div_x, wall_t, remaining_h))
                
                # 本体から仕切りカッターを直接カット
                box_shape = box_shape.cut(div_cutter)

            # ③ ??【仕様変更】底面の排熱穴（直方体）をその場で直接カットする
            if need_hole:
                heat_hole = Part.makeBox(hole_w, hole_l, hole_h)
                # Z位置を -2.0mm からスタートさせて、下側へ確実に「はみ出す」ように配置（完全貫通のハック）
                heat_hole.translate(FreeCAD.Vector(slot_center_x - (hole_w / 2.0), slot_start_y + 5.0, -2.0))
                
                # 本体から直方体を直接引き算
                box_shape = box_shape.cut(heat_hole)
        
        # ?? 配線用の貫通穴（丸穴）をあける
        bar.update(80, "端子穴をセンターに配置中...")
        wire_hole_radius = 1.25 if "単1形" in b_type else 1.0
        wire_hole_len = wall_t + 5.0  # 確実に貫通するように長さを延長
        
        all_holes = []
        for i in range(b_count):
            if b_dir == "Horizontal":
                slot_center_x = wall_t + i * (slot_w + divider_t) + radius
                hole_front_y = wall_t + 2.0  # 完全にまたぐように調整
                hole_back_y = total_l + 2.0
            else:
                slot_center_x = wall_t + radius
                if i == 0:
                    hole_front_y = wall_t + 2.0
                    hole_back_y = -10.0 
                elif i == b_count - 1:
                    hole_front_y = -10.0 
                    hole_back_y = total_l + 2.0
                else:
                    continue 

            hole_z = wall_t + radius
            
            if hole_front_y > 0:
                hole_front = Part.makeCylinder(wire_hole_radius, wire_hole_len)
                hole_front.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(1,0,0), 90)
                # Y座標の配置を少し手前に引いて、確実に壁を跨がせる
                hole_front.translate(FreeCAD.Vector(slot_center_x, hole_front_y, hole_z))
                all_holes = hole_front if not all_holes else all_holes.fuse(hole_front)
            
            if hole_back_y > 0:
                hole_back = Part.makeCylinder(wire_hole_radius, wire_hole_len)
                hole_back.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(1,0,0), 90)
                # Y座標の配置を少し奥にずらして、確実に壁を跨がせる
                hole_back.translate(FreeCAD.Vector(slot_center_x, hole_back_y, hole_z))
                all_holes = hole_back if not all_holes else all_holes.fuse(hole_back)
                
        if all_holes:
            box_shape = box_shape.cut(all_holes)

        # FreeCADへモデルを出力
        bar.update(90, "FreeCADへモデルを出力中...")
        obj_box = doc.addObject("Part::Feature", "BatteryHolder")
        obj_box.Shape = box_shape.removeSplitter()
        obj_box.ViewObject.ShapeColor = (0.75, 0.75, 0.75) 
        
        bar.update(100, "完了")
        bar.close()
        
        doc.recompute()
        FreeCADGui.activeView().fitAll()

FreeCADGui.addCommand('Ring_BatteryBox', Tool_MakeBatteryBox())