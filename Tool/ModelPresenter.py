# -*- coding: utf-8 -*-
# Tool/ModelPresenter.py
import os
import math
import random
import FreeCAD
import FreeCADGui

from Core.QtCompat import QtWidgets, QtGui, QtCore

# Coin3D (ライティング・カメラ制御用)
try:
    from pivy import coin
except ImportError:
    coin = None

# おしゃれなカラーパレット定義
COLOR_PALETTES = {
    "1. 高級ゴールド & マットブラック": [(0.90, 0.75, 0.30), (0.12, 0.12, 0.14), (0.85, 0.85, 0.88)],
    "2. 情熱ルビー & ローズゴールド": [(0.85, 0.10, 0.25), (0.92, 0.68, 0.65), (0.20, 0.15, 0.18)],
    "3. 深海サファイア & プラチナ": [(0.10, 0.30, 0.85), (0.80, 0.85, 0.90), (0.05, 0.15, 0.35)],
    "4. 秘境エメラルド & ダークメタル": [(0.05, 0.70, 0.40), (0.25, 0.28, 0.30), (0.70, 0.90, 0.75)],
    "5. サイバーパンク (ネオン)": [(0.00, 0.90, 1.00), (1.00, 0.00, 0.50), (0.10, 0.10, 0.20)],
    "6. 桜和モダン (サクラピンク)": [(0.98, 0.75, 0.82), (0.95, 0.92, 0.88), (0.40, 0.25, 0.28)],
    "7. サンセットグラデーション": [(1.00, 0.40, 0.10), (0.90, 0.20, 0.40), (0.30, 0.10, 0.30)],
    "8. 北欧ナチュラル (パステル)": [(0.91, 0.58, 0.49), (0.55, 0.68, 0.60), (0.95, 0.92, 0.85)],
    "9. チタン & メカニカル": [(0.20, 0.50, 0.80), (0.70, 0.72, 0.75), (0.95, 0.40, 0.10)],
    "10. ミニマルモノトーン": [(0.90, 0.90, 0.92), (0.40, 0.42, 0.45), (0.15, 0.15, 0.16)],
}

def check_has_valid_models():
    doc = FreeCAD.activeDocument()
    if not doc: return False
    for o in doc.Objects:
        if hasattr(o, "Shape") and hasattr(o, "ViewObject"):
            if o.Shape and not o.Shape.isNull():
                return True
    return False

class PresenterDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("モデル・プレゼンター")
        self.resize(380, 580)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)

        self.setStyleSheet("""
            QDialog { background-color: #f4f5f7; }
            QGroupBox { font-weight: bold; }
            QPushButton { background-color: #ffffff; border: 1px solid #ababab; border-radius: 4px; padding: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #e6f0fa; border-color: #0066cc; }
            QPushButton:checked { background-color: #d0e4ff; border-color: #0055b8; color: #003366; }
        """)

        # アニメーション用タイマー
        self.anim_timer = QtCore.QTimer(self)
        self.anim_timer.setInterval(30)
        self.anim_timer.timeout.connect(self.update_animation)
        
        self.is_animating = False
        
        # 初期位置の記録用
        self.initial_cam_pos = None
        self.initial_cam_rot = None
        
        # ズーム制作用
        self.anim_time = 0.0

        self.light_node = None

        self.init_light_node()
        self.init_ui()

    def get_active_view(self):
        if FreeCADGui.ActiveDocument:
            return FreeCADGui.ActiveDocument.ActiveView
        return None

    def init_light_node(self):
        if not coin: return
        view = self.get_active_view()
        if not view: return
        sg = view.getSceneGraph()
        if not sg: return

        search = coin.SoSearchAction()
        search.setType(coin.SoDirectionalLight.getClassTypeId())
        search.setInterest(coin.SoSearchAction.FIRST)
        search.apply(sg)
        path = search.getPath()

        if path:
            self.light_node = path.getTail()
        else:
            self.light_node = coin.SoDirectionalLight()
            sg.insertChild(self.light_node, 0)

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12) 

        # --- 1. カラーパレット ---
        color_group = QtWidgets.QGroupBox("カラー・配色設定")
        color_layout = QtWidgets.QVBoxLayout(color_group)

        self.combo_palette = QtWidgets.QComboBox()
        self.combo_palette.addItems(list(COLOR_PALETTES.keys()))
        color_layout.addWidget(self.combo_palette)

        btn_apply_color = QtWidgets.QPushButton("選択スタイルを適用")
        btn_apply_color.clicked.connect(self.apply_preset_color)
        color_layout.addWidget(btn_apply_color)

        btn_random_color = QtWidgets.QPushButton("おまかせランダム着色")
        btn_random_color.clicked.connect(self.apply_random_color)
        color_layout.addWidget(btn_random_color)
        layout.addWidget(color_group)

        # --- 2. ライティング調整 ---
        light_group = QtWidgets.QGroupBox("光源・ライティング調整")
        light_layout = QtWidgets.QFormLayout(light_group)

        self.slider_azimuth = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_azimuth.setRange(0, 360)
        self.slider_azimuth.setValue(45)
        self.slider_azimuth.valueChanged.connect(self.update_lighting)

        self.slider_elevation = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_elevation.setRange(-90, 90)
        self.slider_elevation.setValue(45)
        self.slider_elevation.valueChanged.connect(self.update_lighting)

        self.slider_intensity = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_intensity.setRange(10, 200)
        self.slider_intensity.setValue(100)
        self.slider_intensity.valueChanged.connect(self.update_lighting)

        light_layout.addRow("光の向き:", self.slider_azimuth)
        light_layout.addRow("光の高さ:", self.slider_elevation)
        light_layout.addRow("明るさ:", self.slider_intensity)
        layout.addWidget(light_group)

        # --- 3. 画面(カメラ)回転演出 ---
        anim_group = QtWidgets.QGroupBox("カメラ旋回演出")
        anim_layout = QtWidgets.QVBoxLayout(anim_group)
        
        lbl_info = QtWidgets.QLabel("※見つめている場所（マウス操作の中心）を軸に回ります")
        lbl_info.setStyleSheet("color: #555555; font-size: 11px;")
        anim_layout.addWidget(lbl_info)

        btn_fit = QtWidgets.QPushButton("画面中央に整える")
        btn_fit.clicked.connect(self.fit_model_center)
        anim_layout.addWidget(btn_fit)

        self.chk_zoom = QtWidgets.QCheckBox("ランダム拡大縮小効果をオンにする")
        anim_layout.addWidget(self.chk_zoom)

        speed_layout = QtWidgets.QHBoxLayout()
        speed_layout.addWidget(QtWidgets.QLabel("回転スピード:"))
        self.slider_speed = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_speed.setRange(1, 20)
        self.slider_speed.setValue(5)
        speed_layout.addWidget(self.slider_speed)
        anim_layout.addLayout(speed_layout)

        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_play = QtWidgets.QPushButton("再生")
        self.btn_play.setCheckable(True)
        self.btn_play.toggled.connect(self.toggle_play)
        
        btn_reset_pos = QtWidgets.QPushButton("カメラリセット")
        btn_reset_pos.clicked.connect(self.reset_camera_position)
        
        btn_layout.addWidget(self.btn_play)
        btn_layout.addWidget(btn_reset_pos)
        anim_layout.addLayout(btn_layout)

        layout.addWidget(anim_group)

        # --- 4. 閉じる ---
        btn_close = QtWidgets.QPushButton("閉じる")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

        self.update_lighting()

    def fit_model_center(self):
        view = self.get_active_view()
        if view: view.fitAll()

    # ==========================================
    # カメラ旋回＆ズーム アニメーション
    # ==========================================
    def toggle_play(self, checked):
        if checked:
            if not check_has_valid_models():
                self.btn_play.setChecked(False)
                QtWidgets.QMessageBox.information(self, "通知", "モデルが存在しません。")
                return

            view = self.get_active_view()
            if not view or not coin:
                return

            cam = view.getCameraNode()
            if not cam:
                return

            self.initial_cam_pos = cam.position.getValue()
            self.initial_cam_rot = cam.orientation.getValue()
            
            if hasattr(cam, 'height'):
                self.initial_height = cam.height.getValue()
            if hasattr(cam, 'heightAngle'):
                self.initial_heightAngle = cam.heightAngle.getValue()
                
            self.anim_time = 0.0

            self.btn_play.setText("一時停止")
            self.is_animating = True
            self.anim_timer.start()
        else:
            self.btn_play.setText("再生")
            self.anim_timer.stop()
            self.is_animating = False

    def update_animation(self):
        if not self.is_animating:
            return

        try:
            view = self.get_active_view()
            if not view or not coin: return
            
            cam = view.getCameraNode()
            if not cam: return

            speed = float(self.slider_speed.value()) * 0.5
            rad = math.radians(speed)
            cos_val = math.cos(rad)
            sin_val = math.sin(rad)

            pos = cam.position.getValue()
            ori = cam.orientation.getValue()
            q_val = ori.getValue() 
            qx, qy, qz, qw = q_val[0], q_val[1], q_val[2], q_val[3]
            
            foc_dist = cam.focalDistance.getValue()

            fx = 2.0 * (qx * qz + qw * qy)
            fy = 2.0 * (qy * qz - qw * qx)
            fz = 1.0 - 2.0 * (qx * qx + qy * qy)
            dir_x, dir_y, dir_z = -fx, -fy, -fz

            focal_x = pos[0] + dir_x * foc_dist
            focal_y = pos[1] + dir_y * foc_dist
            focal_z = pos[2] + dir_z * foc_dist

            dx = pos[0] - focal_x
            dy = pos[1] - focal_y
            dz = pos[2] - focal_z

            new_dx = dx * cos_val - dy * sin_val
            new_dy = dx * sin_val + dy * cos_val

            cam.position.setValue(focal_x + new_dx, focal_y + new_dy, focal_z + dz)

            half_rad = rad * 0.5
            sz = math.sin(half_rad)
            cw = math.cos(half_rad)

            new_qx = cw * qx - sz * qy
            new_qy = cw * qy + sz * qx
            new_qz = cw * qz + sz * qw
            new_qw = cw * qw - sz * qz

            cam.orientation.setValue(new_qx, new_qy, new_qz, new_qw)

            if getattr(self, 'chk_zoom', None) and self.chk_zoom.isChecked():
                self.anim_time += speed * 0.02
                zoom_scale = 1.0 + 0.15 * math.sin(self.anim_time) + 0.08 * math.sin(self.anim_time * 1.618)
                
                if hasattr(cam, 'height') and getattr(self, 'initial_height', None):
                    cam.height.setValue(self.initial_height * zoom_scale)
                if hasattr(cam, 'heightAngle') and getattr(self, 'initial_heightAngle', None):
                    cam.heightAngle.setValue(self.initial_heightAngle * zoom_scale)
            else:
                if hasattr(cam, 'height') and getattr(self, 'initial_height', None):
                    cam.height.setValue(self.initial_height)
                if hasattr(cam, 'heightAngle') and getattr(self, 'initial_heightAngle', None):
                    cam.heightAngle.setValue(self.initial_heightAngle)

            view.redraw()
            FreeCADGui.updateGui()
            
        except Exception as e:
            self.anim_timer.stop()
            self.is_animating = False
            self.btn_play.setChecked(False)
            self.btn_play.setText("再生")
            FreeCAD.Console.PrintError(f"Animation Error: {str(e)}\n")

    def reset_camera_position(self):
        if self.btn_play.isChecked():
            self.btn_play.setChecked(False)
            
        view = self.get_active_view()
        if view and coin and self.initial_cam_pos and self.initial_cam_rot:
            cam = view.getCameraNode()
            if cam:
                cam.position.setValue(self.initial_cam_pos)
                cam.orientation.setValue(self.initial_cam_rot)
                
                if hasattr(self, 'initial_height') and self.initial_height and hasattr(cam, 'height'):
                    cam.height.setValue(self.initial_height)
                if hasattr(self, 'initial_heightAngle') and self.initial_heightAngle and hasattr(cam, 'heightAngle'):
                    cam.heightAngle.setValue(self.initial_heightAngle)
                    
                view.redraw()

    # ==========================================
    # その他ツール機能
    # ==========================================
    def update_lighting(self):
        if not coin or not self.light_node: return
        x = math.cos(math.radians(self.slider_elevation.value())) * math.sin(math.radians(self.slider_azimuth.value()))
        y = math.cos(math.radians(self.slider_elevation.value())) * math.cos(math.radians(self.slider_azimuth.value()))
        z = math.sin(math.radians(self.slider_elevation.value()))
        self.light_node.direction.setValue(-x, -y, -z)
        self.light_node.intensity.setValue(self.slider_intensity.value() / 100.0)
        view = self.get_active_view()
        if view: view.redraw()

    def apply_preset_color(self):
        objs = self.get_target_objects()
        if not objs: return
        colors = COLOR_PALETTES.get(self.combo_palette.currentText(), [(0.8, 0.8, 0.8)])
        for idx, obj in enumerate(objs):
            obj.ViewObject.ShapeColor = colors[idx % len(colors)]
            if hasattr(obj.ViewObject, "Shininess"): obj.ViewObject.Shininess = 0.85
        FreeCADGui.updateGui()

    def get_target_objects(self):
        doc = FreeCAD.activeDocument()
        if not doc: return []
        selected = FreeCADGui.Selection.getSelection()
        if selected:
            return selected
        objs = []
        for obj in doc.Objects:
            if hasattr(obj, 'Visibility') and obj.Visibility:
                if hasattr(obj, 'Shape') and obj.Shape and not obj.Shape.isNull():
                    objs.append(obj)
        return objs

    def apply_random_color(self):
        objs = self.get_target_objects()
        if not objs: return
        for obj in objs:
            c = QtGui.QColor.fromHsvF(random.random(), random.uniform(0.55, 0.90), random.uniform(0.70, 0.95))
            obj.ViewObject.ShapeColor = (c.redF(), c.greenF(), c.blueF())
            if hasattr(obj.ViewObject, "Shininess"): obj.ViewObject.Shininess = 0.90
        FreeCADGui.updateGui()

    def closeEvent(self, event):
        self.anim_timer.stop()
        self.reset_camera_position()
        super().closeEvent(event)


class Tool_ModelPresenter:
    def GetResources(self):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons", "renda.png").replace('\\', '/')
        return {'Pixmap': icon_path, 'MenuText': "モデルお披露目・着色", 'ToolTip': "モデルをおしゃれに着色し、回転演出します"}

    def Activated(self):
        if not check_has_valid_models():
            QtWidgets.QMessageBox.information(FreeCADGui.getMainWindow(), "通知", "モデルを生成してください。")
            return
        dlg = PresenterDialog(FreeCADGui.getMainWindow())
        dlg.show()

FreeCADGui.addCommand('Ring_ModelPresenter', Tool_ModelPresenter())