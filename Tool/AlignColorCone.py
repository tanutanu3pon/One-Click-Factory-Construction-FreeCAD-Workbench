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

class AlignColorConeDialog(TranslatedDialog):
    def __init__(self, parent=None):
        super(AlignColorConeDialog, self).__init__(parent)
        self.setWindowTitle("カラーコーン自動整列")
        self.resize(380, 260)
        
        layout = QtWidgets.QFormLayout(self)
        
        self.spin_pitch = QtWidgets.QDoubleSpinBox()
        self.spin_pitch.setRange(500.0, 5000.0)
        self.spin_pitch.setValue(2000.0)
        self.spin_pitch.setSuffix(" mm (2.0m)")
        
        self.spin_min_pitch = QtWidgets.QDoubleSpinBox()
        self.spin_min_pitch.setRange(300.0, 2000.0)
        self.spin_min_pitch.setValue(1000.0)
        self.spin_min_pitch.setSuffix(" mm (1.0m)")

        self.spin_cone_h = QtWidgets.QDoubleSpinBox()
        self.spin_cone_h.setRange(200.0, 1500.0)
        self.spin_cone_h.setValue(700.0)
        self.spin_cone_h.setSuffix(" mm")

        self.spin_base_w = QtWidgets.QDoubleSpinBox()
        self.spin_base_w.setRange(100.0, 1000.0)
        self.spin_base_w.setValue(380.0)
        self.spin_base_w.setSuffix(" mm")

        self.check_bar = QtWidgets.QCheckBox("コーンバーも自動で架け渡す")
        self.check_bar.setChecked(True)
        
        layout.addRow("<b>基本配置間隔 (バー長さ):</b>", self.spin_pitch)
        layout.addRow("<b>最小許容間隔 (未満で調整):</b>", self.spin_min_pitch)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        layout.addRow("<b>コーンの高さ:</b>", self.spin_cone_h)
        layout.addRow("<b>コーンの土台幅:</b>", self.spin_base_w)
        layout.addRow(self.check_bar)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        return {
            "std_pitch": self.spin_pitch.value(),
            "min_pitch": self.spin_min_pitch.value(),
            "cone_h": self.spin_cone_h.value(),
            "base_w": self.spin_base_w.value(),
            "make_bar": self.check_bar.isChecked()
        }

class Tool_AlignColorCone:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "align_cone.png").replace('\\', '/')
        return {
            'Pixmap': icon_path, 
            'MenuText': "沿線カラーコーン整列配置", 
            'ToolTip': "選択した線分（DWG/DXF/スケッチ/曲線対応）に沿ってカラーコーンとコーンバーを自動整列配置します"
        }

    def extract_discrete_points(self, sel_objs, step_dist=50.0):
        all_shapes = []
        for sel in sel_objs:
            if sel.HasSubObjects:
                for sub in sel.SubObjects:
                    all_shapes.append(sub)
            elif hasattr(sel, "Object") and hasattr(sel.Object, "Shape"):
                all_shapes.append(sel.Object.Shape)
            elif hasattr(sel, "Shape"):
                all_shapes.append(sel.Shape)

        if not all_shapes:
            return []

        edges = []
        for sh in all_shapes:
            if isinstance(sh, Part.Edge):
                edges.append(sh)
            elif isinstance(sh, Part.Wire):
                edges.extend(sh.Edges)
            elif hasattr(sh, "Edges") and sh.Edges:
                edges.extend(sh.Edges)

        if not edges:
            return []

        try:
            try:
                sorted_edges = Part.__sortEdges__(edges)
                wire = Part.Wire(sorted_edges)
            except Exception:
                wire = Part.Wire(edges)
            
            pts = list(wire.discretize(Distance=step_dist))
            if pts and len(pts) >= 2:
                return pts
        except Exception:
            pass

        discrete_pts = []
        for e in edges:
            try:
                e_pts = list(e.discretize(Distance=step_dist))
            except Exception:
                e_pts = [e.Vertex1.Point, e.Vertex2.Point]

            if not e_pts:
                continue

            if not discrete_pts:
                discrete_pts.extend(e_pts)
            else:
                d_start = (e_pts[0] - discrete_pts[-1]).Length
                d_end = (e_pts[-1] - discrete_pts[-1]).Length
                
                if d_start <= d_end:
                    if d_start < 10.0:
                        discrete_pts.extend(e_pts[1:])
                    else:
                        discrete_pts.extend(e_pts)
                else:
                    rev_pts = list(reversed(e_pts))
                    if d_end < 10.0:
                        discrete_pts.extend(rev_pts[1:])
                    else:
                        discrete_pts.extend(rev_pts)

        return discrete_pts

    def find_chord_intersection(self, discrete_pts, start_idx, curr_p, target_r):
        for i in range(start_idx, len(discrete_pts) - 1):
            p1 = discrete_pts[i]
            p2 = discrete_pts[i+1]
            
            d1 = (p1 - curr_p).Length
            d2 = (p2 - curr_p).Length
            
            if (d1 <= target_r <= d2) or (d2 <= target_r <= d1):
                v = p2 - p1
                w = p1 - curr_p
                a = v.dot(v)
                b = 2.0 * w.dot(v)
                c = w.dot(w) - target_r**2
                disc = b**2 - 4.0*a*c
                if disc >= 0 and a > 1e-6:
                    t = (-b + math.sqrt(disc)) / (2.0*a)
                    if 0.0 <= t <= 1.0:
                        return i, p1 + v * t
        return len(discrete_pts) - 1, discrete_pts[-1]

    def calc_step_points(self, discrete_pts, std_pitch, min_pitch):
        if not discrete_pts or len(discrete_pts) < 2:
            return []

        points = [discrete_pts[0]]
        curr_idx = 0
        end_pt = discrete_pts[-1]

        while True:
            curr_p = points[-1]
            rem_to_end = (end_pt - curr_p).Length
            
            if rem_to_end <= std_pitch:
                if rem_to_end < min_pitch and len(points) >= 2:
                    last_p = points.pop()
                    prev_p = points[-1]
                    mid_idx, mid_p = self.find_chord_intersection(discrete_pts, 0, prev_p, (end_pt - prev_p).Length / 2.0)
                    points.append(mid_p)
                    points.append(end_pt)
                else:
                    points.append(end_pt)
                break
                
            next_idx, next_p = self.find_chord_intersection(discrete_pts, curr_idx, curr_p, std_pitch)
            
            if (next_p - curr_p).Length < 10.0 or next_idx >= len(discrete_pts) - 1:
                if (end_pt - points[-1]).Length > 10.0:
                    points.append(end_pt)
                break
                
            points.append(next_p)
            curr_idx = next_idx

        return points

    def create_single_cone(self, cone_h, base_w):
        base_h = cone_h * 0.045
        wall_t = 3.0
        
        base_box = Part.makeBox(base_w, base_w, base_h)
        base_box.translate(FreeCAD.Vector(-base_w / 2.0, -base_w / 2.0, 0))
        
        r_bottom = base_w * 0.36
        r_top = r_bottom * 0.15
        cone_height = cone_h - base_h
        
        outer_cone = Part.makeCone(r_bottom, r_top, cone_height, FreeCAD.Vector(0, 0, base_h))
        inner_cone = Part.makeCone(r_bottom - wall_t, max(0.5, r_top - wall_t), cone_height + 2.0, FreeCAD.Vector(0, 0, base_h - 1.0))
        cone_body = outer_cone.cut(inner_cone)
        
        tape_h = cone_height * 0.22
        tape_z = base_h + cone_height * 0.45
        t_ratio = (tape_z - base_h) / cone_height
        r_tape_bot = r_bottom - (r_bottom - r_top) * t_ratio
        r_tape_top = r_bottom - (r_bottom - r_top) * (t_ratio + (tape_h / cone_height))
        tape_ring = Part.makeCone(r_tape_bot + 0.8, r_tape_top + 0.8, tape_h, FreeCAD.Vector(0, 0, tape_z))
        
        cone_body = cone_body.fuse(tape_ring)
        center_hole = Part.makeCylinder(r_bottom - wall_t, base_h + 2.0, FreeCAD.Vector(0, 0, -1.0))
        base_box = base_box.cut(center_hole)
        
        return base_box.fuse(cone_body).removeSplitter()

    def create_fast_bar(self, bar_len, bar_dia=34.0):
        bar_r = bar_dia / 2.0
        ring_outer_r = bar_r * 2.5
        ring_inner_r = bar_r * 1.8
        ring_thick = bar_r * 0.8
        
        main_bar = Part.makeCylinder(bar_r, bar_len, FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(1, 0, 0))
        
        def make_ring_hook(pos_x):
            outer_c = Part.makeCylinder(ring_outer_r, ring_thick, FreeCAD.Vector(pos_x, 0, -ring_thick/2.0), FreeCAD.Vector(0, 0, 1))
            inner_c = Part.makeCylinder(ring_inner_r, ring_thick + 2.0, FreeCAD.Vector(pos_x, 0, -ring_thick/2.0 - 1.0), FreeCAD.Vector(0, 0, 1))
            return outer_c.cut(inner_c)
            
        ring_l = make_ring_hook(0.0)
        ring_r = make_ring_hook(bar_len)
        return Part.makeCompound([main_bar, ring_l, ring_r])

    def Activated(self):
        lang = get_language()
        doc = FreeCAD.activeDocument()
        
        sel_objs = FreeCADGui.Selection.getSelectionEx()
        discrete_pts = self.extract_discrete_points(sel_objs, step_dist=50.0)

        if len(discrete_pts) < 2:
            msg = "画面上で配置の基準となる『線（DWG/DXF/スケッチ/曲線など）』を選択してから実行してください。" if lang == "日本語" else "Please select a line or curve first."
            QtWidgets.QMessageBox.warning(None, translate_text("選択エラー", lang), translate_text(msg, lang))
            return

        d = AlignColorConeDialog(FreeCADGui.getMainWindow())
        if d.exec_() != QtWidgets.QDialog.Accepted:
            return
        vals = d.get_values()

        std_pitch = vals["std_pitch"]
        min_pitch = vals["min_pitch"]
        cone_h = vals["cone_h"]
        base_w = vals["base_w"]
        make_bar = vals["make_bar"]

        doc.openTransaction("AlignColorCones")
        try:
            with Progress.ProgressManager() as bar:
                bar.start(title=translate_text("沿線カラーコーン整列配置", lang), initial_text=translate_text("配置ポイントを非同期計算中...", lang))
                
                final_points = self.calc_step_points(discrete_pts, std_pitch, min_pitch)
                total_items = len(final_points)

                if total_items < 2:
                    return

                grp = doc.addObject("App::DocumentObjectGroup", "Cone_Array_Group")
                cone_base_shape = self.create_single_cone(cone_h, base_w)

                bar_z_pos = cone_h * 0.82
                bar_count = 0
                total_dist_mm = 0.0
                
                for i in range(total_items):
                    pct = int((i + 1) / total_items * 90.0)
                    msg_text = f"カラーコーン・バーを配置中 ({i+1}/{total_items})..." if lang == "日本語" else f"Placing Cone/Bar ({i+1}/{total_items})..."
                    bar.update(pct, msg_text)

                    # コーンの配置
                    pt = final_points[i]
                    c_obj = doc.addObject("Part::Feature", f"Aligned_Cone_{i+1}")
                    c_obj.Shape = cone_base_shape.copy()
                    c_obj.Placement.Base = pt
                    c_obj.ViewObject.ShapeColor = (0.95, 0.25, 0.08)
                    grp.addObject(c_obj)

                    # バーの配置および総延長の加算
                    if i > 0:
                        p_start = final_points[i-1] + FreeCAD.Vector(0, 0, bar_z_pos)
                        p_end = final_points[i] + FreeCAD.Vector(0, 0, bar_z_pos)
                        vec = p_end - p_start
                        span_len = vec.Length
                        total_dist_mm += span_len
                        
                        if make_bar and span_len > 1.0:
                            bar_shape = self.create_fast_bar(span_len)
                            bar_obj = doc.addObject("Part::Feature", f"Aligned_Bar_{i}")
                            bar_obj.Shape = bar_shape
                            
                            rot = FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), vec)
                            bar_obj.Placement = FreeCAD.Placement(p_start, rot)
                            bar_obj.ViewObject.ShapeColor = (0.95, 0.80, 0.10)
                            grp.addObject(bar_obj)
                            bar_count += 1

                bar.update(98, translate_text("画面表示を更新中...", lang))
                doc.commitTransaction()
                doc.recompute()
                
                bar.update(100, translate_text("完了しました！", lang))
                if FreeCADGui.activeView():
                    FreeCADGui.activeView().fitAll()

            # --- 配置集計レポートダイアログの表示 ---
            total_dist_m = total_dist_mm / 1000.0
            cone_count = total_items
            
            if lang == "日本語":
                res_title = "配置完了レポート"
                res_msg = (
                    f"カラーコーンの整列配置が完了しました！\n\n"
                    f"・総延長: {total_dist_m:.2f} m ({total_dist_mm:,.1f} mm)\n"
                    f"・カラーコーン: {cone_count} 個\n"
                    f"・コーンバー: {bar_count} 本"
                )
            else:
                res_title = "Placement Report"
                res_msg = (
                    f"Color cone alignment completed!\n\n"
                    f"・Total Extension: {total_dist_m:.2f} m ({total_dist_mm:,.1f} mm)\n"
                    f"・Color Cones: {cone_count} pcs\n"
                    f"・Cone Bars: {bar_count} pcs"
                )

            QtWidgets.QMessageBox.information(None, res_title, res_msg)

        except Exception as e:
            doc.abortTransaction()
            FreeCAD.Console.PrintError(f"Cone alignment error: {str(e)}\n")
            err_title = "Error" if lang == "English" else "エラー"
            err_msg = f"An error occurred during creation:\n{str(e)}" if lang == "English" else f"生成中にエラーが発生しました:\n{str(e)}"
            QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Construction_AlignColorCone', Tool_AlignColorCone())