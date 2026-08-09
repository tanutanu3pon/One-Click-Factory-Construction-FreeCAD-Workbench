# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part
import math

# 【修正】絶対インポートで安全にCoreモジュールを読み込む
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedDialog, translate_text
from Core.Language import get_language

# 【修正】TranslatedDialog を継承させることでUIを自動翻訳
class DangomushiDialog(TranslatedDialog):
    """ダンゴムシのパラメータ指定ダイアログ"""
    def __init__(self, parent=None):
        super(DangomushiDialog, self).__init__(parent)
        self.setWindowTitle("ダンゴムシの設計")
        self.resize(340, 320)
        
        layout = QtWidgets.QFormLayout(self)
        
        self.spin_length = self._create_double_spin(30.0, 10.0, 100.0, " mm")
        self.spin_width = self._create_double_spin(15.0, 5.0, 50.0, " mm")
        self.spin_height = self._create_double_spin(9.0, 3.0, 30.0, " mm")
        
        # 構造を固定化（頭部1+胸部7+腹部5+尾部1）するため、スピンボックスではなく情報表示にする
        self.label_structure = QtWidgets.QLabel("頭部1節 ＋ 胸部7節 ＋ 腹部5節 ＋ 尾部1節 (計14節)")
        
        self.slider_curl = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_curl.setRange(0, 100)
        self.slider_curl.setValue(20) 
        
        self.combo_color = QtWidgets.QComboBox()
        self.combo_color.addItems([
            "黒色 (Natural Black)", 
            "灰色 (Slate Gray)", 
            "白色 (Albino White)"
        ])
        
        self.check_antennae = QtWidgets.QCheckBox("触角と目をつける")
        self.check_antennae.setChecked(True)
        
        self.check_legs = QtWidgets.QCheckBox("手足（14本）を付ける")
        self.check_legs.setChecked(True)
        
        layout.addRow("全体の長さ:", self.spin_length)
        layout.addRow("体の幅:", self.spin_width)
        layout.addRow("体の高さ:", self.spin_height)
        layout.addRow("体の構造:", self.label_structure)
        layout.addRow("丸まり具合:", self.slider_curl)
        layout.addRow("殻の色:", self.combo_color)
        layout.addRow("", self.check_antennae)
        layout.addRow("", self.check_legs)

        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def _create_double_spin(self, val, min_v, max_v, suffix):
        sb = QtWidgets.QDoubleSpinBox()
        sb.setRange(min_v, max_v)
        sb.setValue(val)
        sb.setSuffix(suffix)
        return sb

    def get_values(self):
        return (
            self.spin_length.value(),
            self.spin_width.value(),
            self.spin_height.value(),
            self.slider_curl.value(),
            self.combo_color.currentIndex(),
            self.check_antennae.isChecked(),
            self.check_legs.isChecked()
        )

class Tool_MakeDangomushi:
    def GetResources(self):
        current_dir = os.path.dirname(__file__)
        wb_dir = os.path.dirname(current_dir)
        icon_path = os.path.join(wb_dir, "icons", "dangomushi.png").replace('\\', '/')
        
        return {
            'Pixmap'  : icon_path, 
            'MenuText': "ダンゴムシ作成", 
            'ToolTip' : "構造（頭1+胸7+腹5+尾1）に忠実な3Dプリント用モデルを生成します"
        }

    def Activated(self):
        d = DangomushiDialog()
        if d.exec_() != QtWidgets.QDialog.Accepted: 
            return
            
        length, width, height, curl_percent, color_idx, has_antennae, has_legs = d.get_values()
        # 胸の節は7で固定（本物の構造）
        self.create_dangomushi(length, width, height, 7, curl_percent, color_idx, has_antennae, has_legs)

    def _make_limb_compound(self, pts, radii):
        """関節パーツ群をCompoundでまとめる（エラー回避・3Dプリント対応）"""
        parts = []
        for j in range(len(pts)-1):
            p_start = pts[j]
            p_end = pts[j+1]
            v = p_end - p_start
            length = v.Length
            if length < 0.001: continue
            
            cone = Part.makeCone(radii[j], radii[j+1], length)
            z_dir = FreeCAD.Vector(0,0,1)
            axis = z_dir.cross(v)
            angle = math.degrees(z_dir.getAngle(v))
            
            if axis.Length < 0.001:
                rot = FreeCAD.Rotation() if z_dir.dot(v) > 0 else FreeCAD.Rotation(FreeCAD.Vector(1,0,0), 180)
            else:
                rot = FreeCAD.Rotation(axis, angle)
                
            cone.Placement = FreeCAD.Placement(p_start, rot)
            parts.append(cone)
            # 関節の球体
            parts.append(Part.makeSphere(radii[j], p_start))
            
        parts.append(Part.makeSphere(radii[-1], pts[-1]))
        return Part.makeCompound(parts)

    def _create_shell_profile(self, w, h, y):
        """Bスプライン曲線を用いた甲殻断面"""
        w = max(w, 0.1)
        h = max(h, 0.1)
        
        p0 = FreeCAD.Vector(0, y, h)
        p1 = FreeCAD.Vector(w * 0.35, y, h * 0.95)
        p2 = FreeCAD.Vector(w * 0.48, y, h * 0.3)
        p3 = FreeCAD.Vector(w * 0.55, y, 0)
        
        c_R = Part.BSplineCurve()
        c_R.buildFromPoles([p0, p1, p2, p3])
        
        p1_L = FreeCAD.Vector(-w * 0.35, y, h * 0.95)
        p2_L = FreeCAD.Vector(-w * 0.48, y, h * 0.3)
        p3_L = FreeCAD.Vector(-w * 0.55, y, 0)
        
        c_L = Part.BSplineCurve()
        c_L.buildFromPoles([p3_L, p2_L, p1_L, p0])
        
        belly = Part.makeLine(p3, p3_L)
        
        wire = Part.Wire([c_L.toShape(), c_R.toShape(), belly])
        return Part.Face(wire)

    def create_dangomushi(self, total_length, width, height, num_segments, curl_percent, color_idx, has_antennae, has_legs):
        lang = get_language()
        
        if color_idx == 0: shape_color = (0.16, 0.17, 0.20)
        elif color_idx == 1: shape_color = (0.45, 0.46, 0.48)
        else: shape_color = (0.85, 0.85, 0.82)

        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("ダンゴムシ生成", lang), initial_text=translate_text("解剖学的ボディラインを計算中...", lang))
            
            doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
            
            total_bend_angle = math.pi * (curl_percent / 100.0)
            bend_radius = total_length / total_bend_angle if total_bend_angle > 0.001 else 0.0
            
            def get_envelope(y_pos):
                cy = total_length * 0.35
                front_extent = cy * 1.2
                back_extent = (total_length - cy) * 1.05
                
                if y_pos < cy:
                    t = (cy - y_pos) / front_extent
                else:
                    t = (y_pos - cy) / back_extent
                    
                t = min(max(t, 0.0), 1.0)
                factor = math.sqrt(1.0 - t**2)
                
                return width * factor, height * factor

            # 【重要】実際の構造に基づく14枚のプレートの関節位置を計算
            Y_hinges = [0]
            Y_hinges.append(total_length * 0.10) # 頭部 (1節)
            for i in range(7): # 胸部 (7節)
                Y_hinges.append(total_length * 0.10 + (i+1)*(total_length * 0.60 / 7))
            for i in range(5): # 腹部 (5節)
                Y_hinges.append(total_length * 0.70 + (i+1)*(total_length * 0.20 / 5))
            Y_hinges.append(total_length) # 尾部 (1節)
            
            body_parts = []
            
            for k in range(14):
                bar.update(10 + int(80 * (k / 14.0)))
                
                y_start = Y_hinges[k]
                y_end = Y_hinges[k+1]
                L_k = y_end - y_start
                overlap = L_k * 0.4 if k < 13 else 0.0
                
                w_front, h_front = get_envelope(y_start)
                w_back, h_back = get_envelope(y_start + L_k + overlap)
                
                if k == 13: # 尾部 (Telson)
                    face_front = self._create_shell_profile(w_front, h_front, 0)
                    vertex_back = Part.Vertex(0, L_k, 0)
                    seg_solid = Part.makeLoft([face_front, vertex_back], True, True)
                else: # 頭部・胸部・腹部
                    face_front = self._create_shell_profile(w_front, h_front, 0)
                    face_back = self._create_shell_profile(w_back, h_back, L_k + overlap)
                    seg_solid = Part.makeLoft([face_front, face_back], True, True)
                
                components = [seg_solid]
                
                # --- 目と触角の生成（頭部 k=0） ---
                if k == 0 and has_antennae:
                    eye_radius = w_front * 0.08
                    eye_l = Part.makeSphere(eye_radius, FreeCAD.Vector(-w_front*0.45, L_k*0.5, h_front*0.4))
                    eye_r = Part.makeSphere(eye_radius, FreeCAD.Vector(w_front*0.45, L_k*0.5, h_front*0.4))
                    components.extend([eye_l, eye_r])

                    # 触角の根元を頭部の「内部」に食い込ませる（3Dプリント時の離脱防止）
                    splay_angle = math.radians(25)
                    # y=0が顔の先端、y=L_kが首。L_k*0.4 の位置なら確実に頭の中に入る。
                    ant_base_y = L_k * 0.4 
                    ant_base_z = h_front * 0.15
                    
                    p0 = FreeCAD.Vector(-w_front*0.25, ant_base_y, ant_base_z) 
                    p1 = p0 + FreeCAD.Vector(-total_length*0.12 * math.sin(splay_angle), -total_length*0.15 * math.cos(splay_angle), -height*0.05)
                    p2 = p1 + FreeCAD.Vector(-total_length*0.1 * math.sin(splay_angle*1.2), -total_length*0.1 * math.cos(splay_angle*1.2), -height*0.05)
                    
                    p0_R = FreeCAD.Vector(w_front*0.25, ant_base_y, ant_base_z)
                    p1_R = p0_R + FreeCAD.Vector(total_length*0.12 * math.sin(splay_angle), -total_length*0.15 * math.cos(splay_angle), -height*0.05)
                    p2_R = p1_R + FreeCAD.Vector(total_length*0.1 * math.sin(splay_angle*1.2), -total_length*0.1 * math.cos(splay_angle*1.2), -height*0.05)
                    
                    ant_radii = [0.35, 0.25, 0.05]
                    components.append(self._make_limb_compound([p0, p1, p2], ant_radii))
                    components.append(self._make_limb_compound([p0_R, p1_R, p2_R], ant_radii))

                # --- 14本の脚の生成（胸部 k=1～7 のみに配置） ---
                if 1 <= k <= 7 and has_legs:
                    leg_splay = math.radians(35 - 70 * (k / 7.0)) 
                    scale_leg = 1.0 - 0.2 * (k / 7.0) 
                    
                    # 根元を甲殻の内部（中心寄り）に深く食い込ませる
                    base_x = -w_front * 0.25 
                    base_y = L_k * 0.5
                    
                    p0 = FreeCAD.Vector(base_x, base_y, h_front * 0.1) # Z軸方向も少し上に配置して内部へ
                    p1 = p0 + FreeCAD.Vector(-w_front*0.35*scale_leg * math.cos(leg_splay), w_front*0.35*scale_leg * math.sin(leg_splay), -height*0.2*scale_leg)
                    p2 = p1 + FreeCAD.Vector(-w_front*0.15*scale_leg, 0, -height*0.3*scale_leg)
                    p3 = p2 + FreeCAD.Vector(-w_front*0.05*scale_leg, 0, -height*0.2*scale_leg)
                    
                    p0_R = FreeCAD.Vector(-base_x, base_y, h_front * 0.1)
                    p1_R = p0_R + FreeCAD.Vector(w_front*0.35*scale_leg * math.cos(leg_splay), w_front*0.35*scale_leg * math.sin(leg_splay), -height*0.2*scale_leg)
                    p2_R = p1_R + FreeCAD.Vector(w_front*0.15*scale_leg, 0, -height*0.3*scale_leg)
                    p3_R = p2_R + FreeCAD.Vector(w_front*0.05*scale_leg, 0, -height*0.2*scale_leg)
                    
                    leg_radii = [0.4*scale_leg, 0.3*scale_leg, 0.15*scale_leg, 0.05*scale_leg]
                    components.append(self._make_limb_compound([p0, p1, p2, p3], leg_radii))
                    components.append(self._make_limb_compound([p0_R, p1_R, p2_R, p3_R], leg_radii))

                seg_comp = Part.makeCompound(components)
                
                plc = FreeCAD.Placement()
                if bend_radius > 0:
                    alpha = (y_start / total_length) * total_bend_angle
                    pos_y = bend_radius * math.sin(alpha)
                    pos_z = -bend_radius * (1.0 - math.cos(alpha))
                    
                    plc.Base = FreeCAD.Vector(0, pos_y, pos_z)
                    plc.Rotation = FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), -math.degrees(alpha))
                else:
                    plc.Base = FreeCAD.Vector(0, y_start, 0)
                    
                seg_comp.Placement = plc
                body_parts.append(seg_comp)

            bar.update(95, translate_text("FreeCADへモデルを出力中...", lang))
            
            # 最終的な全体複合体を作成（スライサーソフトで1つのオブジェクトとして認識されます）
            dangomushi_shape = Part.makeCompound(body_parts)
            
            obj = doc.addObject("Part::Feature", "Dangomushi_Printable")
            obj.Shape = dangomushi_shape
            
            obj.ViewObject.ShapeColor = shape_color
            obj.ViewObject.DisplayMode = "Flat Lines"
            try:
                obj.ViewObject.ShapeMaterial.Shininess = 0.85
                obj.ViewObject.ShapeMaterial.SpecularColor = (0.7, 0.7, 0.7)
            except Exception:
                pass
            
            bar.update(100, translate_text("完了", lang))
            doc.recompute()
            FreeCADGui.activeView().fitAll()

FreeCADGui.addCommand('Ring_Dangomushi', Tool_MakeDangomushi())