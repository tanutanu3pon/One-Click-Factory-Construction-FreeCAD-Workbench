# -*- coding: utf-8 -*-
import os
import math
import FreeCAD
import FreeCADGui
import Part
from Core.QtCompat import QtWidgets, QtGui, QtCore

try:
    from Core.Progress import ProgressManager
except ImportError:
    class ProgressManager:
        def __init__(self): pass
        def start(self, title, initial_text): pass
        def update(self, percent, text=None): pass
        def close(self): pass

def get_selected_spine_shape():
    selected = FreeCADGui.Selection.getSelection()
    if not selected: return None

    for obj in selected:
        if hasattr(obj, 'Shape') and obj.Shape and not obj.Shape.isNull():
            shape = obj.Shape
            if shape.Wires and len(shape.Wires) > 0:
                return shape.Wires[0]
            elif shape.Edges and len(shape.Edges) > 0:
                return Part.Wire(shape.Edges)
    return None

def smooth_step_val(t, t0, t1, v0, v1):
    if t <= t0: return v0
    if t >= t1: return v1
    x = (t - t0) / float(t1 - t0)
    s = x * x * (3.0 - 2.0 * x)
    return v0 + (v1 - v0) * s

def get_non_uniform_t_list(num_sections, mode_type):
    if mode_type == 0:
        return [i / float(num_sections - 1) for i in range(num_sections)]

    t_list = []
    for i in range(num_sections):
        u = i / float(num_sections - 1)
        if u < 0.2:
            t_val = smooth_step_val(u, 0.0, 0.2, 0.0, 0.12)
        elif u < 0.7:
            t_val = smooth_step_val(u, 0.2, 0.7, 0.12, 0.72)
        else:
            t_val = smooth_step_val(u, 0.7, 1.0, 0.72, 1.00)
        t_list.append(t_val)

    return t_list

def get_profile_radii(t, mode_type, spine_length, user_bulge):
    r_min = 0.01

    if mode_type == 0:
        half_w = user_bulge / 2.0
        r = r_min + (half_w - r_min) * math.sin(math.pi * t)
        return max(r, r_min), max(r, r_min), max(r, r_min)

    if mode_type == 1:
        max_h_top, max_h_bot, max_w = spine_length * 0.28, spine_length * 0.14, spine_length * 0.13
        t_pk_top, t_pk_bot, t_w = 0.32, 0.38, 0.75
        ht_mouth, ht_waist, ht_tail = 0.08, 0.18, 0.55
        hb_mouth, hb_waist, hb_tail = 0.06, 0.16, 0.50
        w_mouth, w_waist, w_tail = 0.05, 0.18, 0.04
    elif mode_type == 2:
        max_h_top, max_h_bot, max_w = spine_length * 0.13, spine_length * 0.11, spine_length * 0.13
        t_pk_top, t_pk_bot, t_w = 0.38, 0.36, 0.76
        ht_mouth, ht_waist, ht_tail = 0.08, 0.22, 0.50
        hb_mouth, hb_waist, hb_tail = 0.06, 0.20, 0.48
        w_mouth, w_waist, w_tail = 0.05, 0.22, 0.04
    elif mode_type == 3:
        max_h_top, max_h_bot, max_w = spine_length * 0.15, spine_length * 0.14, spine_length * 0.20
        t_pk_top, t_pk_bot, t_w = 0.33, 0.35, 0.78
        ht_mouth, ht_waist, ht_tail = 0.10, 0.18, 0.52
        hb_mouth, hb_waist, hb_tail = 0.08, 0.18, 0.50
        w_mouth, w_waist, w_tail = 0.08, 0.18, 0.04
    elif mode_type == 4:
        max_h_top, max_h_bot, max_w = spine_length * 0.14, spine_length * 0.12, spine_length * 0.15
        t_pk_top, t_pk_bot, t_w = 0.33, 0.35, 0.78
        ht_mouth, ht_waist, ht_tail = 0.08, 0.18, 0.50
        hb_mouth, hb_waist, hb_tail = 0.06, 0.18, 0.48
        w_mouth, w_waist, w_tail = 0.06, 0.18, 0.04
    elif mode_type == 5:
        max_h_top, max_h_bot, max_w = spine_length * 0.13, spine_length * 0.11, spine_length * 0.12
        t_pk_top, t_pk_bot, t_w = 0.40, 0.36, 0.76
        ht_mouth, ht_waist, ht_tail = 0.08, 0.22, 0.48
        hb_mouth, hb_waist, hb_tail = 0.06, 0.20, 0.45
        w_mouth, w_waist, w_tail = 0.05, 0.22, 0.04
    elif mode_type == 6:
        max_h_top, max_h_bot, max_w = spine_length * 0.06, spine_length * 0.06, spine_length * 0.08
        t_pk_top, t_pk_bot, t_w = 0.42, 0.42, 0.80
        ht_mouth, ht_waist, ht_tail = 0.10, 0.35, 0.50
        hb_mouth, hb_waist, hb_tail = 0.08, 0.35, 0.48
        w_mouth, w_waist, w_tail = 0.08, 0.35, 0.05
    else:
        max_h_top, max_h_bot, max_w = spine_length * 0.10, spine_length * 0.18, spine_length * 0.14
        t_pk_top, t_pk_bot, t_w = 0.32, 0.26, 0.74
        ht_mouth, ht_waist, ht_tail = 0.08, 0.20, 0.45
        hb_mouth, hb_waist, hb_tail = 0.10, 0.18, 0.42
        w_mouth, w_waist, w_tail = 0.08, 0.20, 0.04

    if t <= t_pk_top: fy_top = smooth_step_val(t, 0.0, t_pk_top, ht_mouth, 1.0)
    elif t <= t_w: fy_top = smooth_step_val(t, t_pk_top, t_w, 1.0, ht_waist)
    else: fy_top = smooth_step_val(t, t_w, 1.0, ht_waist, ht_tail)

    if t <= t_pk_bot: fy_bot = smooth_step_val(t, 0.0, t_pk_bot, hb_mouth, 1.0)
    elif t <= t_w: fy_bot = smooth_step_val(t, t_pk_bot, t_w, 1.0, hb_waist)
    else: fy_bot = smooth_step_val(t, t_w, 1.0, hb_waist, hb_tail)

    if t <= t_pk_top: fz = smooth_step_val(t, 0.0, t_pk_top, w_mouth, 1.0)
    elif t <= t_w: fz = smooth_step_val(t, t_pk_top, t_w, 1.0, w_waist)
    else: fz = smooth_step_val(t, t_w, 1.0, w_waist, w_tail)

    ry_top = max(r_min + (max_h_top - r_min) * fy_top, r_min)
    ry_bot = max(r_min + (max_h_bot - r_min) * fy_bot, r_min)
    rz     = max(r_min + (max_w/2.0 - r_min) * fz, r_min)

    return ry_top, ry_bot, rz

def create_asymmetric_section_wire(ry_top, ry_bot, rz):
    e_top = Part.makeCircle(1.0, FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), 0, 180)
    mat_top = FreeCAD.Matrix()
    mat_top.scale(rz, ry_top, 1.0)
    e_top_scaled = e_top.transformGeometry(mat_top)

    e_bottom = Part.makeCircle(1.0, FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), 180, 360)
    mat_bottom = FreeCAD.Matrix()
    mat_bottom.scale(rz, ry_bot, 1.0)
    e_bottom_scaled = e_bottom.transformGeometry(mat_bottom)

    return Part.Wire([e_top_scaled, e_bottom_scaled])

def build_fish_from_spine(spine_wire, num_sections, mode_type, user_bulge):
    spine_length = spine_wire.Length
    t_list = get_non_uniform_t_list(num_sections, mode_type)
    
    sample_pts = spine_wire.discretize(Number=1000)
    n_samples = len(sample_pts)
    if n_samples < 2: return None

    wires = []

    for i, t in enumerate(t_list):
        idx = int(round(t * (n_samples - 1)))
        idx = max(0, min(n_samples - 1, idx))
        pt = sample_pts[idx]

        if idx == 0: tangent = sample_pts[1] - sample_pts[0]
        elif idx == n_samples - 1: tangent = sample_pts[n_samples - 1] - sample_pts[n_samples - 2]
        else: tangent = sample_pts[idx + 1] - sample_pts[idx - 1]

        if tangent.Length < 1e-6: continue
        vec_z = tangent.normalize()

        vec_up = FreeCAD.Vector(0, 0, 1)
        vec_side = vec_z.cross(vec_up)
        
        if vec_side.Length < 1e-6: vec_side = FreeCAD.Vector(1, 0, 0)
        else: vec_side.normalize()
            
        vec_up = vec_side.cross(vec_z).normalize()

        ry_top, ry_bot, rz = get_profile_radii(t, mode_type, spine_length, user_bulge)

        if mode_type == 0:
            base_circle = Part.makeCircle(ry_top, FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1))
            sec_wire = Part.Wire([base_circle])
        else:
            sec_wire = create_asymmetric_section_wire(ry_top, ry_bot, rz)

        mat = FreeCAD.Matrix(
            vec_side.x,  vec_up.x,  vec_z.x,  pt.x,
            vec_side.y,  vec_up.y,  vec_z.y,  pt.y,
            vec_side.z,  vec_up.z,  vec_z.z,  pt.z,
            0,           0,         0,        1
        )

        try:
            w_transformed = sec_wire.transformGeometry(mat)
            wires.append(w_transformed)
        except Exception: pass

    if len(wires) < 2: return None

    segment_solids = []
    for i in range(len(wires) - 1):
        try:
            seg = Part.makeLoft([wires[i], wires[i+1]], True)
            if seg and seg.isValid(): segment_solids.append(seg)
        except Exception: pass

    if not segment_solids: return None

    compound_shape = segment_solids[0]
    for seg in segment_solids[1:]:
        try: compound_shape = compound_shape.fuse(seg)
        except Exception: pass

    return compound_shape

class FishDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("背骨ライン → 3Dモデル生成")
        self.resize(350, 200)

        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()

        self.combo_type = QtWidgets.QComboBox()
        self.combo_type.addItems([
            "① 単純ロフト (丸チューブ)",
            "② たい (Red Seabream)",
            "③ ぶり (Japanese Amberjack)",
            "④ まぐろ (Tuna)",
            "⑤ かつお (Skipjack Tuna)",
            "⑥ さけ (Salmon)",
            "⑦ さんま (Pacific Saury)",
            "⑧ たら (Pacific Cod)"
        ])
        self.combo_type.currentIndexChanged.connect(self.update_ui_state)

        self.spin_steps = QtWidgets.QSpinBox()
        self.spin_steps.setRange(10, 500)
        self.spin_steps.setValue(80)

        self.spin_bulge = QtWidgets.QDoubleSpinBox()
        self.spin_bulge.setRange(0.1, 500.0)
        self.spin_bulge.setValue(20.0)
        self.spin_bulge.setSuffix(" mm")

        form.addRow("魚種・タイプ:", self.combo_type)
        form.addRow("背骨の分割数:", self.spin_steps)
        form.addRow("ふくらみ径 (①のみ):", self.spin_bulge)
        layout.addLayout(form)

        self.lbl_info = QtWidgets.QLabel("※背骨ラインのカーブを魚の水平方向の泳ぎとして反映します")
        self.lbl_info.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.lbl_info)

        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self.update_ui_state()

    def update_ui_state(self):
        is_simple = (self.combo_type.currentIndex() == 0)
        self.spin_bulge.setEnabled(is_simple)

    def get_values(self):
        return {
            'mode_type': self.combo_type.currentIndex(),
            'steps': self.spin_steps.value(),
            'bulge': self.spin_bulge.value()
        }

class Tool_MakeFish:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "fish.png").replace('\\', '/')
        return {
            'Pixmap': icon_path,
            'MenuText': "背骨から3Dモデルを作成",
            'ToolTip': "選択した背骨ラインからたい・まぐろ・さんま等の3Dモデルを生成します"
        }

    def Activated(self):
        doc = FreeCAD.activeDocument()
        if doc is None:
            QtWidgets.QMessageBox.information(None, "通知", "アクティブなドキュメントがありません。")
            return

        spine_shape = get_selected_spine_shape()

        if spine_shape is None:
            QtWidgets.QMessageBox.warning(
                None, 
                "選択エラー", 
                "画面上で『背骨ライン（スケッチまたは1本の線）』を選択してから実行してください。"
            )
            return

        dlg = FishDialog(FreeCADGui.getMainWindow())
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        params = dlg.get_values()
        pm = ProgressManager()
        pm.start("3Dモデル生成", "背骨を分割中！")

        doc.openTransaction("Create Fish Model From Spine")
        try:
            pm.update(30, "背骨を分割中！")
            
            fish_shape = build_fish_from_spine(
                spine_shape, 
                params['steps'], 
                params['mode_type'],
                params['bulge']
            )

            if fish_shape and not fish_shape.isNull():
                pm.update(85, "背骨を分割中！")
                type_names = [
                    "3D_Tube", "3D_Tai", "3D_Buri", 
                    "3D_Maguro", "3D_Katsuo", "3D_Sake", 
                    "3D_Sanma", "3D_Tara"
                ]
                fish_obj = doc.addObject("Part::Feature", type_names[params['mode_type']])
                fish_obj.Shape = fish_shape
                
                if hasattr(fish_obj, 'ViewObject') and fish_obj.ViewObject:
                    fish_obj.ViewObject.ShapeColor = (0.2, 0.7, 0.9)
                    if hasattr(fish_obj.ViewObject, "Shininess"):
                        fish_obj.ViewObject.Shininess = 0.9

                doc.commitTransaction()
                doc.recompute()
                FreeCADGui.SendMsgToActiveView("ViewFit")
                pm.update(100, "完了")
            else:
                doc.abortTransaction()
                QtWidgets.QMessageBox.warning(None, "エラー", "ロフト生成に失敗しました。背骨ラインの形状を確認してください。")

        except Exception as e:
            doc.abortTransaction()
            QtWidgets.QMessageBox.critical(None, "エラー", f"処理中にエラーが発生しました:\n{str(e)}")
        finally:
            pm.close()

FreeCADGui.addCommand('Ring_MakeFish', Tool_MakeFish())