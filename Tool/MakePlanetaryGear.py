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

def create_gear_solid(m, z, height, internal=False, backlash=0.15, tip_relief=0.05, hole_radius=0.0):
    r = (m * z) / 2.0
    tan_alpha = math.tan(math.radians(20))

    if not internal:
        ra = r + m - tip_relief
        rf = max(r - 1.25 * m, 0.1)
        half_angle = (math.pi / z) / 2.0 - (backlash / (2.0 * r))
    else:
        ra_cutter = r + 1.25 * m
        rf_cutter = max(r - 1.0 * m, 0.1)
        half_angle = (math.pi / z) / 2.0 + (backlash / (2.0 * r))
        ra = ra_cutter
        rf = rf_cutter

    a_pitch = half_angle
    a_tip = half_angle - ((ra - r) * tan_alpha) / r
    a_root = half_angle - ((rf - r) * tan_alpha) / r

    if a_tip < 0: a_tip = 0.0
    if a_root > math.pi / z: a_root = math.pi / z

    pts = []
    angle_step = 2.0 * math.pi / z
    for i in range(z):
        phi = i * angle_step
        pts.append(FreeCAD.Vector(rf * math.cos(phi - a_root), rf * math.sin(phi - a_root), 0))
        pts.append(FreeCAD.Vector(r * math.cos(phi - a_pitch), r * math.sin(phi - a_pitch), 0))
        pts.append(FreeCAD.Vector(ra * math.cos(phi - a_tip), ra * math.sin(phi - a_tip), 0))
        
        pts.append(FreeCAD.Vector(ra * math.cos(phi + a_tip), ra * math.sin(phi + a_tip), 0))
        pts.append(FreeCAD.Vector(r * math.cos(phi + a_pitch), r * math.sin(phi + a_pitch), 0))
        pts.append(FreeCAD.Vector(rf * math.cos(phi + a_root), rf * math.sin(phi + a_root), 0))

    pts.append(pts[0])
    wire = Part.makePolygon(pts)
    face = Part.Face(wire)
    solid = face.extrude(FreeCAD.Vector(0, 0, height))

    if internal:
        rf_ring = r + 1.25 * m
        r_outer = rf_ring + 4.0 * m
        outer_cyl = Part.makeCylinder(r_outer, height)
        solid = outer_cyl.cut(solid)

    if hole_radius > 0.0:
        hole = Part.makeCylinder(hole_radius, height)
        solid = solid.cut(hole)

    return solid

# 【修正】TranslatedDialog を継承させて自動翻訳を有効化
class PlanetaryGearAnimator(TranslatedDialog):
    def __init__(self, doc_name, z_sun, z_planet, num_planets, m, parent=None):
        super(PlanetaryGearAnimator, self).__init__(parent)
        self.doc_name = doc_name
        self.z_sun = z_sun
        self.z_planet = z_planet
        self.n = num_planets
        self.m = m
        self.z_ring = z_sun + 2 * z_planet
        self.center_distance = m * (z_sun + z_planet) / 2.0
        
        self.current_angle = 0.0
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.update_animation)
        
        self.setWindowTitle("遊星ギア アニメーション制御")
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.resize(340, 260)
        
        self.setAutoFillBackground(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #f4f5f7;
                border: 1px solid #cccccc;
                border-radius: 6px;
            }
            QLabel {
                color: #222222;
                font-size: 11pt;
            }
            QComboBox, QSlider, QCheckBox {
                color: #222222;
                font-size: 10pt;
            }
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #ababab;
                border-radius: 4px;
                padding: 6px;
                font-weight: bold;
                font-size: 10pt;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #e6f0fa;
                border-color: #0066cc;
            }
            QPushButton:checked {
                background-color: #d0e4ff;
                border-color: #0055b8;
                color: #003366;
            }
        """)
        
        self.init_ui()
        self.move_to_optimal_position()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QtWidgets.QLabel("<b>【作動モード】</b>"))
        self.combo_mode = QtWidgets.QComboBox()
        self.combo_mode.addItems([
            "太陽入力 / 内歯固定 (標準減速)",
            "内歯入力 / 太陽固定",
            "キャリア固定 (逆転)"
        ])
        layout.addWidget(self.combo_mode)

        speed_layout = QtWidgets.QHBoxLayout()
        speed_layout.addWidget(QtWidgets.QLabel("回転速度:"))
        self.slider_speed = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_speed.setRange(1, 20)
        self.slider_speed.setValue(5)
        speed_layout.addWidget(self.slider_speed)
        layout.addLayout(speed_layout)

        self.chk_reverse = QtWidgets.QCheckBox("逆方向回転")
        layout.addWidget(self.chk_reverse)

        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_play = QtWidgets.QPushButton("再生")
        self.btn_play.setCheckable(True)
        self.btn_play.toggled.connect(self.toggle_play)
        
        btn_reset = QtWidgets.QPushButton("リセット")
        btn_reset.clicked.connect(self.reset_animation)

        btn_layout.addWidget(self.btn_play)
        btn_layout.addWidget(btn_reset)
        layout.addLayout(btn_layout)

    def move_to_optimal_position(self):
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.x() + parent_rect.width() - self.width() - 50
            y = parent_rect.y() + 140
            self.move(x, y)

    def toggle_play(self, checked):
        lang = get_language()
        if checked:
            txt = "Pause" if lang == "English" else "一時停止"
            self.btn_play.setText(txt)
            self.timer.start()
        else:
            txt = "Play" if lang == "English" else "再生"
            self.btn_play.setText(txt)
            self.timer.stop()

    def reset_animation(self):
        self.current_angle = 0.0
        self.update_positions(0.0)

    def update_animation(self):
        speed = self.slider_speed.value() * 0.5
        if self.chk_reverse.isChecked():
            speed = -speed
        
        self.current_angle += speed
        self.update_positions(self.current_angle)

    def update_positions(self, angle):
        doc = FreeCAD.getDocument(self.doc_name)
        if not doc:
            self.timer.stop()
            return

        mode = self.combo_mode.currentIndex()
        planet_align_offset = 180.0 - (self.z_planet // 2) * (360.0 / self.z_planet) - (180.0 / self.z_planet)
        ring_rot_init = (180.0 / self.z_ring) if (self.z_planet % 2 == 0) else 0.0

        if mode == 0:
            theta_sun = angle
            theta_ring = 0.0
            theta_carrier = theta_sun * (self.z_sun / (self.z_sun + self.z_ring))
        elif mode == 1:
            theta_ring = angle
            theta_sun = 0.0
            theta_carrier = theta_ring * (self.z_ring / (self.z_sun + self.z_ring))
        else:
            theta_carrier = 0.0
            theta_sun = angle
            theta_ring = -theta_sun * (self.z_sun / self.z_ring)

        sun_obj = doc.getObject("SunGear")
        if sun_obj:
            sun_obj.Placement.Rotation = FreeCAD.Rotation(FreeCAD.Vector(0,0,1), theta_sun)

        carrier_obj = doc.getObject("PlanetaryCarrier")
        if carrier_obj:
            carrier_obj.Placement.Rotation = FreeCAD.Rotation(FreeCAD.Vector(0,0,1), theta_carrier)

        ring_obj = doc.getObject("RingGear")
        if ring_obj:
            ring_obj.Placement.Rotation = FreeCAD.Rotation(FreeCAD.Vector(0,0,1), ring_rot_init + theta_ring)

        for i in range(self.n):
            p_obj = doc.getObject(f"PlanetGear_{i+1}")
            if p_obj:
                phi_base = i * 360.0 / self.n
                phi_curr = phi_base + theta_carrier
                
                x = self.center_distance * math.cos(math.radians(phi_curr))
                y = self.center_distance * math.sin(math.radians(phi_curr))

                rot_p = planet_align_offset + phi_curr * (1.0 + self.z_sun / self.z_planet) - theta_sun * (self.z_sun / self.z_planet)

                p_obj.Placement = FreeCAD.Placement(
                    FreeCAD.Vector(x, y, 0),
                    FreeCAD.Rotation(FreeCAD.Vector(0,0,1), rot_p)
                )

        FreeCADGui.updateGui()

    def closeEvent(self, event):
        self.timer.stop()
        event.accept()

# 【修正】TranslatedDialog を継承させて自動翻訳を有効化
class PlanetaryGearDialog(TranslatedDialog):
    def __init__(self, parent=None):
        super(PlanetaryGearDialog, self).__init__(parent)
        self.setWindowTitle("遊星ギアの作成 (位相・隙間 計算対応)")
        self.resize(560, 720)
        self.init_ui()

    def init_ui(self):
        lang = get_language()
        layout = QtWidgets.QVBoxLayout(self)
        tab_widget = QtWidgets.QTabWidget()

        tab1 = QtWidgets.QWidget()
        tab1_layout = QtWidgets.QVBoxLayout(tab1)
        
        if lang == "English":
            formula_text = (
                "<div style='font-size: 125%; line-height: 1.4;'>"
                "<b>[4 Key Design Requirements]</b><br>"
                "1. <b>Center Distance:</b> Z<sub>ring</sub> = Z<sub>sun</sub> + 2xZ<sub>planet</sub><br>"
                "2. <b>Equidistant Mesh:</b> (Z<sub>sun</sub> + Z<sub>ring</sub>) / N = Integer<br>"
                "3. <b>Adjacent Clearance:</b> (Z<sub>planet</sub> + 2) &lt; (Z<sub>sun</sub> + Z<sub>planet</sub>) x sin(&pi; / N)<br>"
                "4. <b>Internal Gear Clearance:</b> Z<sub>ring</sub> - Z<sub>planet</sub> &ge; 8<br><br>"
                "<b>[Gear Ratio by Operating Mode]</b><br>"
                "・Sun Input / Ring Fixed: <i>i = 1 + (Z<sub>ring</sub> / Z<sub>sun</sub>)</i><br>"
                "・Ring Input / Sun Fixed: <i>i = 1 + (Z<sub>sun</sub> / Z<sub>ring</sub>)</i><br>"
                "・Carrier Fixed (Reverse): <i>i = - (Z<sub>ring</sub> / Z<sub>sun</sub>)</i>"
                "</div><hr>"
            )
            tab1_title = "Planetary Gear Design"
            tab2_title = "Shaft & Base Design"
        else:
            formula_text = (
                "<div style='font-size: 135%; line-height: 1.4;'>"
                "<b>【機構成立の4大条件】</b><br>"
                "1. <b>中心距離:</b> Z<sub>ring</sub> ＝ Z<sub>sun</sub> ＋ 2×Z<sub>planet</sub><br>"
                "2. <b>等配条件:</b> (Z<sub>sun</sub> + Z<sub>ring</sub>) / N ＝ 整数<br>"
                "3. <b>隣接干渉:</b> (Z<sub>planet</sub> + 2) &lt; (Z<sub>sun</sub> + Z<sub>planet</sub>) × sin(π / N)<br>"
                "4. <b>内歯車干渉:</b> Z<sub>ring</sub> - Z<sub>planet</sub> ≧ 8<br><br>"
                "<b>【作動モード別 減速比】</b><br>"
                "・太陽入力/内歯固定: <i>i = 1 + (Z<sub>ring</sub> / Z<sub>sun</sub>)</i><br>"
                "・内歯入力/太陽固定: <i>i = 1 + (Z<sub>sun</sub> / Z<sub>ring</sub>)</i><br>"
                "・キャリア固定 (逆転): <i>i = - (Z<sub>ring</sub> / Z<sub>sun</sub>)</i>"
                "</div><hr>"
            )
            tab1_title = "遊星歯車の基本設計"
            tab2_title = "軸・台座の設計"

        info_label = QtWidgets.QLabel(formula_text)
        info_label.setWordWrap(True)
        tab1_layout.addWidget(info_label)

        form_layout1 = QtWidgets.QFormLayout()
        
        self.spin_module = QtWidgets.QDoubleSpinBox()
        self.spin_module.setRange(0.1, 50.0)
        self.spin_module.setValue(1.0)
        self.spin_module.setSingleStep(0.1)

        self.spin_z_sun = QtWidgets.QSpinBox()
        self.spin_z_sun.setRange(8, 200)
        self.spin_z_sun.setValue(12)

        self.spin_z_planet = QtWidgets.QSpinBox()
        self.spin_z_planet.setRange(8, 200)
        self.spin_z_planet.setValue(12)

        self.spin_num_planets = QtWidgets.QSpinBox()
        self.spin_num_planets.setRange(2, 12)
        self.spin_num_planets.setValue(3)

        self.spin_height = QtWidgets.QDoubleSpinBox()
        self.spin_height.setRange(1.0, 500.0)
        self.spin_height.setValue(10.0)

        self.spin_backlash = QtWidgets.QDoubleSpinBox()
        self.spin_backlash.setRange(0.0, 5.0)
        self.spin_backlash.setValue(0.15)
        self.spin_backlash.setSingleStep(0.05)
        
        self.spin_tip_relief = QtWidgets.QDoubleSpinBox()
        self.spin_tip_relief.setRange(0.0, 5.0)
        self.spin_tip_relief.setValue(0.05)
        self.spin_tip_relief.setSingleStep(0.01)

        form_layout1.addRow("モジュール (m):", self.spin_module)
        form_layout1.addRow("太陽歯車の歯数 (Z_sun):", self.spin_z_sun)
        form_layout1.addRow("遊星歯車の歯数 (Z_planet):", self.spin_z_planet)
        form_layout1.addRow("遊星歯車の個数 (N):", self.spin_num_planets)
        form_layout1.addRow("歯車の厚み (mm):", self.spin_height)
        form_layout1.addRow("バックラッシ (遊び) (mm):", self.spin_backlash)
        form_layout1.addRow("歯先カット量 (干渉回避) (mm):", self.spin_tip_relief)
        
        tab1_layout.addLayout(form_layout1)
        tab_widget.addTab(tab1, tab1_title)

        tab2 = QtWidgets.QWidget()
        tab2_layout = QtWidgets.QVBoxLayout(tab2)
        
        if lang == "English":
            basic_formula_text = (
                "<div style='font-size: 125%; line-height: 1.4;'>"
                "<b>[Standard Spur Gear Dimensions]</b> (Module: <i>m</i>, Teeth: <i>Z</i>)<br><br>"
                "・Pitch Diameter: <i>d = m x Z</i><br>"
                "・Tip Diameter: <i>d<sub>a</sub> = m x (Z + 2)</i><br>"
                "・Root Diameter: <i>d<sub>f</sub> = m x (Z - 2.5)</i><br>"
                "・Addendum: <i>h<sub>a</sub> = m</i><br>"
                "・Dedendum: <i>h<sub>f</sub> = 1.25 x m</i><br>"
                "・Whole Depth: <i>h = 2.25 x m</i><br>"
                "・Circular Pitch: <i>p = &pi; x m</i><br>"
                "・Center Distance: <i>a = m x (Z<sub>1</sub> + Z<sub>2</sub>) / 2</i>"
                "</div><hr>"
            )
        else:
            basic_formula_text = (
                "<div style='font-size: 135%; line-height: 1.4;'>"
                "<b>【標準平歯車の各部寸法計算】</b> (モジュール: <i>m</i>, 歯数: <i>Z</i>)<br><br>"
                "・基準ピッチ円直径: <i>d = m × Z</i><br>"
                "・歯先円直径: <i>d<sub>a</sub> = m × (Z + 2)</i><br>"
                "・歯底円直径: <i>d<sub>f</sub> = m × (Z - 2.5)</i><br>"
                "・歯末のたけ: <i>h<sub>a</sub> = m</i><br>"
                "・歯元のたけ: <i>h<sub>f</sub> = 1.25 × m</i><br>"
                "・全歯丈: <i>h = 2.25 × m</i><br>"
                "・円ピッチ: <i>p = π × m</i><br>"
                "・中心距離 (2歯車間): <i>a = m × (Z<sub>1</sub> + Z<sub>2</sub>) / 2</i><br><br>"
                "<span style='font-size: 90%; color: #555;'>※参考: もの作りのための機械設計工学</span>"
                "</div><hr>"
            )

        basic_info_label = QtWidgets.QLabel(basic_formula_text)
        basic_info_label.setWordWrap(True)
        tab2_layout.addWidget(basic_info_label)

        form_layout2 = QtWidgets.QFormLayout()
        
        self.spin_sun_shaft_dia = QtWidgets.QDoubleSpinBox()
        self.spin_sun_shaft_dia.setRange(1.0, 100.0)
        self.spin_sun_shaft_dia.setValue(8.0)

        self.spin_sun_shaft_len = QtWidgets.QDoubleSpinBox()
        self.spin_sun_shaft_len.setRange(0.0, 500.0)
        self.spin_sun_shaft_len.setValue(30.0)

        self.spin_carrier_shaft_dia = QtWidgets.QDoubleSpinBox()
        self.spin_carrier_shaft_dia.setRange(1.0, 100.0)
        self.spin_carrier_shaft_dia.setValue(8.0)

        self.spin_carrier_shaft_len = QtWidgets.QDoubleSpinBox()
        self.spin_carrier_shaft_len.setRange(0.0, 500.0)
        self.spin_carrier_shaft_len.setValue(30.0)

        self.spin_carrier_thick = QtWidgets.QDoubleSpinBox()
        self.spin_carrier_thick.setRange(1.0, 100.0)
        self.spin_carrier_thick.setValue(4.0)

        self.spin_planet_pin_extend = QtWidgets.QDoubleSpinBox()
        self.spin_planet_pin_extend.setRange(0.0, 100.0)
        self.spin_planet_pin_extend.setValue(2.0)
        self.spin_planet_pin_extend.setSingleStep(1.0)

        self.spin_base_thick = QtWidgets.QDoubleSpinBox()
        self.spin_base_thick.setRange(0.0, 100.0)
        self.spin_base_thick.setValue(5.0)

        form_layout2.addRow("入力軸(太陽) 径 (mm):", self.spin_sun_shaft_dia)
        form_layout2.addRow("入力軸(太陽) 長さ (mm):", self.spin_sun_shaft_len)
        form_layout2.addRow("出力軸(キャリア) 径 (mm):", self.spin_carrier_shaft_dia)
        form_layout2.addRow("出力軸(キャリア) 長さ (mm):", self.spin_carrier_shaft_len)
        form_layout2.addRow("キャリア台座の厚み (mm):", self.spin_carrier_thick)
        form_layout2.addRow("遊星ピンの突き出し量 (mm):", self.spin_planet_pin_extend)
        form_layout2.addRow("内歯車固定ベースの厚み (mm):", self.spin_base_thick)
        
        tab2_layout.addLayout(form_layout2)
        tab_widget.addTab(tab2, tab2_title)

        layout.addWidget(tab_widget)

        self.lbl_result = QtWidgets.QLabel()
        self.lbl_result.setStyleSheet("color: #0044cc; font-weight: bold; font-size: 110%;")
        layout.addWidget(self.lbl_result)

        self.spin_z_sun.valueChanged.connect(self.update_info)
        self.spin_z_planet.valueChanged.connect(self.update_info)
        self.spin_num_planets.valueChanged.connect(self.update_info)
        self.spin_module.valueChanged.connect(self.update_info)
        self.update_info()

        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        btn_box.accepted.connect(self.validate_and_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def update_info(self):
        lang = get_language()
        z_sun = self.spin_z_sun.value()
        z_planet = self.spin_z_planet.value()
        z_ring = z_sun + 2 * z_planet
        m = self.spin_module.value()
        
        center_dist = m * (z_sun + z_planet) / 2.0
        d_sun = m * z_sun
        d_planet = m * z_planet
        d_ring = m * z_ring
        d_outer = d_ring + 8.0 * m
        
        ratio_sun_in = 1.0 + (z_ring / z_sun)
        ratio_ring_in = 1.0 + (z_sun / z_ring)
        ratio_fixed_carrier = z_ring / z_sun

        if lang == "English":
            self.lbl_result.setText(
                f"[Real-time Calculation Specifications]\n"
                f"・Ring Gear Teeth (Z_ring): {z_ring}\n"
                f"・Pitch Dia. d: Sun={d_sun:.1f}mm / Planet={d_planet:.1f}mm / Ring={d_ring:.1f}mm\n"
                f"・Sun-Planet Center Dist. a: {center_dist:.2f} mm | Outer Dia. approx: {d_outer:.1f} mm\n"
                f"・Ratio [Sun Input / Ring Fixed]: 1 : {ratio_sun_in:.2f}\n"
                f"・Ratio [Ring Input / Sun Fixed]: 1 : {ratio_ring_in:.2f}\n"
                f"・Ratio [Carrier Fixed (Reverse)]: 1 : -{ratio_fixed_carrier:.2f}"
            )
        else:
            self.lbl_result.setText(
                f"【リアルタイム計算諸元】\n"
                f"・内歯車 歯数(Z_ring): {z_ring}\n"
                f"・ピッチ円径 d: 太陽={d_sun:.1f}mm / 遊星={d_planet:.1f}mm / 内歯={d_ring:.1f}mm\n"
                f"・太陽-遊星 軸間距離 a: {center_dist:.2f} mm | 全体外径概算: {d_outer:.1f} mm\n"
                f"・減速比 [太陽入力/内歯固定]: 1 : {ratio_sun_in:.2f}\n"
                f"・減速比 [内歯入力/太陽固定]: 1 : {ratio_ring_in:.2f}\n"
                f"・減速比 [キャリア固定(逆転)]: 1 : -{ratio_fixed_carrier:.2f}"
            )

    def validate_and_accept(self):
        lang = get_language()
        z_sun = self.spin_z_sun.value()
        z_planet = self.spin_z_planet.value()
        n = self.spin_num_planets.value()
        z_ring = z_sun + 2 * z_planet

        total_sum = z_sun + z_ring
        if total_sum % n != 0:
            valid_z_planets = []
            for zp in range(8, 100):
                if (z_sun + (z_sun + 2 * zp)) % n == 0:
                    valid_z_planets.append(zp)
                    if len(valid_z_planets) >= 5: break
            
            if lang == "English":
                title_err = "Error (Equidistant Mesh Failed)"
                msg_err = (
                    f"Planetary gears cannot be mesh-aligned with current teeth parameters!\n\n"
                    f"Valid candidates for Planet Teeth (Z_planet):\n => {', '.join(map(str, valid_z_planets))}"
                )
            else:
                title_err = "数値エラー（等配条件不可）"
                msg_err = (
                    f"現在の入力では遊星歯車を均等配置できません！\n\n"
                    f"設定可能な 遊星歯数(Z_planet) の候補:\n ⇒ {', '.join(map(str, valid_z_planets))} など"
                )
            QtWidgets.QMessageBox.warning(self, title_err, msg_err)
            return

        limit_val = (z_sun + z_planet) * math.sin(math.pi / n)
        if (z_planet + 2) >= limit_val:
            if lang == "English":
                title_err = "Error (Physical Collision)"
                msg_err = "Adjacent planet gears will collide physically!\nPlease increase teeth or reduce planet count."
            else:
                title_err = "数値エラー（物理干渉）"
                msg_err = "遊星歯車同士が物理的に衝突してしまいます！\n歯数を増やすか個数を減らしてください。"
            QtWidgets.QMessageBox.warning(self, title_err, msg_err)
            return

        if (z_ring - z_planet) < 8:
            if lang == "English":
                title_err = "Error (Internal Interference)"
                msg_err = "Difference between Ring and Planet teeth is less than 8, causing internal interference!"
            else:
                title_err = "数値エラー（内歯車干渉）"
                msg_err = "内歯車と遊星歯車の歯数差が8未満のため干渉します！"
            QtWidgets.QMessageBox.warning(self, title_err, msg_err)
            return

        self.accept()

    def get_values(self):
        return {
            'module': self.spin_module.value(),
            'z_sun': self.spin_z_sun.value(),
            'z_planet': self.spin_z_planet.value(),
            'num_planets': self.spin_num_planets.value(),
            'height': self.spin_height.value(),
            'backlash': self.spin_backlash.value(),
            'tip_relief': self.spin_tip_relief.value(),
            'sun_shaft_dia': self.spin_sun_shaft_dia.value(),
            'sun_shaft_len': self.spin_sun_shaft_len.value(),
            'carrier_shaft_dia': self.spin_carrier_shaft_dia.value(),
            'carrier_shaft_len': self.spin_carrier_shaft_len.value(),
            'carrier_thick': self.spin_carrier_thick.value(),
            'planet_pin_extend': self.spin_planet_pin_extend.value(),
            'base_thick': self.spin_base_thick.value()
        }

_animator_window = None

class Tool_MakePlanetaryGear:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "gear.png").replace('\\', '/')
        return {'Pixmap': icon_path, 'MenuText': "遊星ギアの作成", 'ToolTip': "パラメータを入力して遊星ギア（3Dモデル）を一括作成します"}

    def Activated(self):
        global _animator_window

        doc = FreeCAD.activeDocument()
        if doc is None:
            doc = FreeCAD.newDocument("PlanetaryGear")

        dlg = PlanetaryGearDialog(FreeCADGui.getMainWindow())
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        params = dlg.get_values()
        m = params['module']
        z_sun = params['z_sun']
        z_planet = params['z_planet']
        n = params['num_planets']
        height = params['height']
        bl = params['backlash']
        tr = params['tip_relief']
        z_ring = z_sun + 2 * z_planet

        sun_shaft_dia = params['sun_shaft_dia']
        sun_shaft_len = params['sun_shaft_len']
        carrier_shaft_dia = params['carrier_shaft_dia']
        carrier_shaft_len = params['carrier_shaft_len']
        carrier_thick = params['carrier_thick']
        planet_pin_extend = params['planet_pin_extend']
        base_thick = params['base_thick']

        center_distance = m * (z_sun + z_planet) / 2.0
        d_planet = m * z_planet

        sun_shape = create_gear_solid(m, z_sun, height, internal=False, backlash=bl, tip_relief=tr)
        if sun_shaft_len > 0:
            sun_shaft = Part.makeCylinder(sun_shaft_dia / 2.0, sun_shaft_len, FreeCAD.Vector(0, 0, -sun_shaft_len))
            sun_shape = sun_shape.fuse(sun_shaft)

        sun_obj = doc.addObject("Part::Feature", "SunGear")
        sun_obj.Shape = sun_shape
        sun_obj.ViewObject.ShapeColor = (0.8, 0.4, 0.4) 

        planet_align_offset = 180.0 - (z_planet // 2) * (360.0 / z_planet) - (180.0 / z_planet)

        planet_pin_dia = min(d_planet * 0.3, carrier_shaft_dia * 0.9)
        carrier_parts = []
        c_base_z = height + planet_pin_extend

        if carrier_thick > 0:
            c_base = Part.makeCylinder(center_distance + planet_pin_dia, carrier_thick, FreeCAD.Vector(0, 0, c_base_z))
            carrier_parts.append(c_base)
            
            if carrier_shaft_len > 0:
                c_shaft_z = c_base_z + carrier_thick
                c_shaft = Part.makeCylinder(carrier_shaft_dia / 2.0, carrier_shaft_len, FreeCAD.Vector(0, 0, c_shaft_z))
                carrier_parts.append(c_shaft)

        for i in range(n):
            phi = i * 360.0 / n
            x = center_distance * math.cos(math.radians(phi))
            y = center_distance * math.sin(math.radians(phi))

            pin_hole_radius = (planet_pin_dia / 2.0) + 0.2
            p_shape = create_gear_solid(m, z_planet, height, internal=False, backlash=bl, tip_relief=tr, hole_radius=pin_hole_radius)
            
            p_obj = doc.addObject("Part::Feature", f"PlanetGear_{i+1}")
            p_obj.Shape = p_shape
            
            rot_p = planet_align_offset + phi * (1.0 + z_sun / z_planet)
            p_obj.Placement = FreeCAD.Placement(
                FreeCAD.Vector(x, y, 0),
                FreeCAD.Rotation(FreeCAD.Vector(0,0,1), rot_p)
            )
            p_obj.ViewObject.ShapeColor = (0.4, 0.8, 0.4)

            if carrier_thick > 0:
                pin_length = height + planet_pin_extend + carrier_thick
                pin = Part.makeCylinder(planet_pin_dia / 2.0, pin_length, FreeCAD.Vector(x, y, 0))
                carrier_parts.append(pin)

        if carrier_parts:
            carrier_solid = carrier_parts[0]
            for p in carrier_parts[1:]:
                carrier_solid = carrier_solid.fuse(p)
            carrier_obj = doc.addObject("Part::Feature", "PlanetaryCarrier")
            carrier_obj.Shape = carrier_solid
            carrier_obj.ViewObject.ShapeColor = (0.8, 0.8, 0.4)

        ring_shape = create_gear_solid(m, z_ring, height, internal=True, backlash=bl, tip_relief=tr)
        ring_obj = doc.addObject("Part::Feature", "RingGear")
        ring_obj.Shape = ring_shape
        
        ring_rot = (180.0 / z_ring) if (z_planet % 2 == 0) else 0.0
        ring_obj.Placement.Rotation = FreeCAD.Rotation(FreeCAD.Vector(0,0,1), ring_rot)
        ring_obj.ViewObject.ShapeColor = (0.4, 0.6, 0.8)

        if base_thick > 0:
            rf_ring = (m * z_ring) / 2.0 + 1.25 * m
            r_outer = rf_ring + 4.0 * m
            base_z_start = -base_thick - 0.5 
            base_plate = Part.makeCylinder(r_outer, base_thick, FreeCAD.Vector(0, 0, base_z_start))
            
            if sun_shaft_len > 0:
                input_hole = Part.makeCylinder(sun_shaft_dia / 2.0 + 0.5, base_thick, FreeCAD.Vector(0, 0, base_z_start))
                base_plate = base_plate.cut(input_hole)
                
            base_obj = doc.addObject("Part::Feature", "BaseStand")
            base_obj.Shape = base_plate
            base_obj.ViewObject.ShapeColor = (0.6, 0.6, 0.6)

        doc.recompute()
        FreeCADGui.SendMsgToActiveView("ViewFit")

        _animator_window = PlanetaryGearAnimator(
            doc.Name, z_sun, z_planet, n, m, parent=FreeCADGui.getMainWindow()
        )
        _animator_window.show()

FreeCADGui.addCommand('Ring_MakePlanetaryGear', Tool_MakePlanetaryGear())