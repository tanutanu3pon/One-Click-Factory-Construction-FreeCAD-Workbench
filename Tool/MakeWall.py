# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part

# 【修正】絶対インポートで安全にCoreモジュールを読み込む
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedDialog, translate_text
from Core.Language import get_language

# 【修正】TranslatedDialog を継承させて自動翻訳を有効化
class ModeSelectDialog(TranslatedDialog):
    def __init__(self, parent=None):
        super(ModeSelectDialog, self).__init__(parent)
        self.setWindowTitle("設計方針の選択")
        self.resize(360, 160)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("<h3>擁壁の設計方針を選択してください</h3>"))
        
        self.radio_uniform = QtWidgets.QRadioButton("① 表面の勾配をピシッと統一する\n   (高さに応じて底面幅を自動計算)")
        self.radio_twist = QtWidgets.QRadioButton("② ねじれ擁壁とする\n   (手前と奥の寸法をすべて自由に入力)")
        self.radio_uniform.setChecked(True)
        
        layout.addWidget(self.radio_uniform)
        layout.addSpacing(10)
        layout.addWidget(self.radio_twist)
        layout.addSpacing(15)
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
    def get_selected_mode(self):
        return 1 if self.radio_uniform.isChecked() else 2

# 【修正】TranslatedDialog を継承させて自動翻訳を有効化
class UniformWallDialog(TranslatedDialog):
    def __init__(self, parent=None):
        super(UniformWallDialog, self).__init__(parent)
        self.setWindowTitle("重力式擁壁・①勾配統一工場")
        self.resize(400, 480)
        
        layout = QtWidgets.QFormLayout(self)
        MAX_MM = 100000

        layout.addRow(QtWidgets.QLabel("<h3>【共通設定】</h3>"))
        
        self.spin_gradient = QtWidgets.QDoubleSpinBox()
        self.spin_gradient.setRange(0.00, 2.00)
        self.spin_gradient.setValue(0.50)
        self.spin_gradient.setSingleStep(0.05)
        self.spin_gradient.setSuffix(" (割/分)  ※垂直1 : 水平N")
        layout.addRow("<b>表面の固定勾配:</b>", self.spin_gradient)

        layout.addRow(QtWidgets.QLabel("<hr><h3>【手前側（始点 Y=0）の寸法】</h3>"))
        
        self.spin_height_start = QtWidgets.QSpinBox()
        self.spin_height_start.setRange(100, MAX_MM)
        self.spin_height_start.setValue(2000)
        self.spin_height_start.setSuffix(" mm")
        layout.addRow("高さ（手前）:", self.spin_height_start)
        
        self.spin_top_start = QtWidgets.QSpinBox()
        self.spin_top_start.setRange(50, MAX_MM)
        self.spin_top_start.setValue(500)
        self.spin_top_start.setSuffix(" mm")
        layout.addRow("天端幅（手前）:", self.spin_top_start)
        
        layout.addRow(QtWidgets.QLabel("<hr><h3>【奥側（終点 Y=L）の寸法】</h3>"))
        
        self.spin_height_end = QtWidgets.QSpinBox()
        self.spin_height_end.setRange(100, MAX_MM)
        self.spin_height_end.setValue(3000)
        self.spin_height_end.setSuffix(" mm")
        layout.addRow("高さ（奥方向）:", self.spin_height_end)
        
        self.spin_top_end = QtWidgets.QSpinBox()
        self.spin_top_end.setRange(50, MAX_MM)
        self.spin_top_end.setValue(500)
        self.spin_top_end.setSuffix(" mm")
        layout.addRow("天端幅（奥方向）:", self.spin_top_end)
        
        layout.addRow(QtWidgets.QLabel("<hr><h3>【配置・アライメントの設定】</h3>"))
        
        self.spin_length = QtWidgets.QSpinBox()
        self.spin_length.setRange(100, MAX_MM * 10)
        self.spin_length.setValue(5000)
        self.spin_length.setSuffix(" mm")
        layout.addRow("擁壁の延長（長さ L）:", self.spin_length)

        self.combo_align = QtWidgets.QComboBox()
        self.combo_align.addItems([
            "裏面（垂直・埋戻し側）をまっすぐ通す", 
            "表面（勾配・見えがかり側の下端）をまっすぐ通す"
        ])
        layout.addRow("基準線の通し方:", self.combo_align)

        layout.addRow(QtWidgets.QLabel("<hr><h3>【初期位置設定 (一番最初のみ適用)】</h3>"))
        self.check_origin = QtWidgets.QCheckBox("原点から開始する")
        self.check_origin.setChecked(True)
        layout.addRow(self.check_origin)

        self.spin_offset_x = QtWidgets.QSpinBox()
        self.spin_offset_x.setRange(0, MAX_MM)
        self.spin_offset_x.setValue(0)
        self.spin_offset_x.setSuffix(" mm")
        self.spin_offset_x.setEnabled(False)
        layout.addRow("X軸マイナス方向へのオフセット:", self.spin_offset_x)

        self.spin_offset_z = QtWidgets.QSpinBox()
        self.spin_offset_z.setRange(0, MAX_MM)
        self.spin_offset_z.setValue(0)
        self.spin_offset_z.setSuffix(" mm")
        self.spin_offset_z.setEnabled(False)
        layout.addRow("Z軸マイナス方向へのオフセット:", self.spin_offset_z)

        self.check_origin.toggled.connect(lambda checked: self.spin_offset_x.setEnabled(not checked))
        self.check_origin.toggled.connect(lambda checked: self.spin_offset_z.setEnabled(not checked))

        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        h_start = self.spin_height_start.value()
        h_end = self.spin_height_end.value()
        t_start = self.spin_top_start.value()
        t_end = self.spin_top_end.value()
        grad = self.spin_gradient.value()
        
        b_start = t_start + int(h_start * grad)
        b_end = t_end + int(h_end * grad)
        
        return {
            "h_start": h_start, "b_start": b_start, "t_start": t_start,
            "h_end": h_end,     "b_end": b_end,     "t_end": t_end,
            "length": self.spin_length.value(),
            "align_mode": self.combo_align.currentIndex(),
            "is_origin": self.check_origin.isChecked(),
            "offset_x": self.spin_offset_x.value(),
            "offset_z": self.spin_offset_z.value()
        }

# 【修正】TranslatedDialog を継承させて自動翻訳を有効化
class TwistWallDialog(TranslatedDialog):
    def __init__(self, parent=None):
        super(TwistWallDialog, self).__init__(parent)
        self.setWindowTitle("重力式擁壁・②自由変断面工場")
        self.resize(400, 500)
        
        layout = QtWidgets.QFormLayout(self)
        MAX_MM = 100000

        layout.addRow(QtWidgets.QLabel("<h3>【手前側（始点 Y=0）の寸法】</h3>"))
        
        self.spin_height_start = QtWidgets.QSpinBox()
        self.spin_height_start.setRange(100, MAX_MM)
        self.spin_height_start.setValue(2000)
        self.spin_height_start.setSuffix(" mm")
        layout.addRow("高さ（手前）:", self.spin_height_start)
        
        self.spin_base_start = QtWidgets.QSpinBox()
        self.spin_base_start.setRange(100, MAX_MM)
        self.spin_base_start.setValue(1500)
        self.spin_base_start.setSuffix(" mm")
        layout.addRow("底面幅（手前）:", self.spin_base_start)
        
        self.spin_top_start = QtWidgets.QSpinBox()
        self.spin_top_start.setRange(50, MAX_MM)
        self.spin_top_start.setValue(500)
        self.spin_top_start.setSuffix(" mm")
        layout.addRow("天端幅（手前）:", self.spin_top_start)
        
        layout.addRow(QtWidgets.QLabel("<hr><h3>【奥側（終点 Y=L）の寸法】</h3>"))
        
        self.spin_height_end = QtWidgets.QSpinBox()
        self.spin_height_end.setRange(100, MAX_MM)
        self.spin_height_end.setValue(3000)
        self.spin_height_end.setSuffix(" mm")
        layout.addRow("高さ（奥方向）:", self.spin_height_end)
        
        self.spin_base_end = QtWidgets.QSpinBox()
        self.spin_base_end.setRange(100, MAX_MM)
        self.spin_base_end.setValue(2000)
        self.spin_base_end.setSuffix(" mm")
        layout.addRow("底面幅（奥方向）:", self.spin_base_end)
        
        self.spin_top_end = QtWidgets.QSpinBox()
        self.spin_top_end.setRange(50, MAX_MM)
        self.spin_top_end.setValue(500)
        self.spin_top_end.setSuffix(" mm")
        layout.addRow("天端幅（奥方向）:", self.spin_top_end)
        
        layout.addRow(QtWidgets.QLabel("<hr><h3>【配置・アライメントの設定】</h3>"))
        
        self.spin_length = QtWidgets.QSpinBox()
        self.spin_length.setRange(100, MAX_MM * 10)
        self.spin_length.setValue(5000)
        self.spin_length.setSuffix(" mm")
        layout.addRow("擁壁の延長（長さ L）:", self.spin_length)

        self.combo_align = QtWidgets.QComboBox()
        self.combo_align.addItems([
            "裏面（垂直・埋戻し側）をまっすぐ通す", 
            "表面（勾配・見えがかり側の下端）をまっすぐ通す"
        ])
        layout.addRow("基準線の通し方:", self.combo_align)

        layout.addRow(QtWidgets.QLabel("<hr><h3>【初期位置設定 (一番最初のみ適用)】</h3>"))
        self.check_origin = QtWidgets.QCheckBox("原点から開始する")
        self.check_origin.setChecked(True)
        layout.addRow(self.check_origin)

        self.spin_offset_x = QtWidgets.QSpinBox()
        self.spin_offset_x.setRange(0, MAX_MM)
        self.spin_offset_x.setValue(0)
        self.spin_offset_x.setSuffix(" mm")
        self.spin_offset_x.setEnabled(False)
        layout.addRow("X軸マイナス方向へのオフセット:", self.spin_offset_x)

        self.spin_offset_z = QtWidgets.QSpinBox()
        self.spin_offset_z.setRange(0, MAX_MM)
        self.spin_offset_z.setValue(0)
        self.spin_offset_z.setSuffix(" mm")
        self.spin_offset_z.setEnabled(False)
        layout.addRow("Z軸マイナス方向へのオフセット:", self.spin_offset_z)

        self.check_origin.toggled.connect(lambda checked: self.spin_offset_x.setEnabled(not checked))
        self.check_origin.toggled.connect(lambda checked: self.spin_offset_z.setEnabled(not checked))

        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.validate_and_accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def validate_and_accept(self):
        lang = get_language()
        if self.spin_top_start.value() >= self.spin_base_start.value():
            err_title = "Input Error" if lang == "English" else "入力エラー"
            err_msg = "Top width (start) must be smaller than base width." if lang == "English" else "手前の「天端幅」は、「底面幅」よりも小さくしてください。"
            QtWidgets.QMessageBox.warning(self, err_title, err_msg)
            return
        if self.spin_top_end.value() >= self.spin_base_end.value():
            err_title = "Input Error" if lang == "English" else "入力エラー"
            err_msg = "Top width (end) must be smaller than base width." if lang == "English" else "奥方向の「天端幅」は、「底面幅」よりも小さくしてください。"
            QtWidgets.QMessageBox.warning(self, err_title, err_msg)
            return
        self.accept()

    def get_values(self):
        return {
            "h_start": self.spin_height_start.value(),
            "b_start": self.spin_base_start.value(),
            "t_start": self.spin_top_start.value(),
            "h_end": self.spin_height_end.value(),
            "b_end": self.spin_base_end.value(),
            "t_end": self.spin_top_end.value(),
            "length": self.spin_length.value(),
            "align_mode": self.combo_align.currentIndex(),
            "is_origin": self.check_origin.isChecked(),
            "offset_x": self.spin_offset_x.value(),
            "offset_z": self.spin_offset_z.value()
        }

class Tool_MakeWall:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "wall.png").replace('\\', '/')
        return {
            'Pixmap': icon_path if os.path.exists(icon_path) else "", 
            'MenuText': "重力式擁壁の作成", 
            'ToolTip': "設計方針を選択してから、実寸の重力式擁壁を連続自動生成します"
        }

    def Activated(self):
        lang = get_language()

        mode_dialog = ModeSelectDialog()
        if mode_dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
            
        selected_mode = mode_dialog.get_selected_mode()
        
        if selected_mode == 1:
            dialog = UniformWallDialog()
            mode_title = translate_text("①勾配統一", lang)
        else:
            dialog = TwistWallDialog()
            mode_title = translate_text("②自由変断面", lang)
            
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
            
        vals = dialog.get_values()
        
        with Progress.ProgressManager() as bar:
            title_text = f"{translate_text('重力式擁壁', lang)}・{mode_title}"
            bar.start(title=title_text, initial_text=translate_text("既存の擁壁データをスキャン中...", lang))

            try:
                doc = FreeCAD.activeDocument() or FreeCAD.newDocument("Construction_Project")
                doc.openTransaction("CreateRetainingWall")

                max_end_y = 0.0        
                current_start_x = 0.0   
                current_start_z = 0.0  
                max_idx = 0            

                for obj in doc.Objects:
                    if obj.Name.startswith("Gravity_Retaining_Wall_"):
                        try:
                            idx = int(obj.Name.split("_")[-1])
                            if idx > max_idx: max_idx = idx
                        except Exception:
                            pass
                        if hasattr(obj, "EndOffsetY"):
                            if obj.EndOffsetY > max_end_y:
                                max_end_y = obj.EndOffsetY
                                if hasattr(obj, "EndOffsetX"):
                                    current_start_x = obj.EndOffsetX
                                if hasattr(obj, "EndOffsetZ"):
                                    current_start_z = obj.EndOffsetZ

                next_idx = max_idx + 1  
                total_length = max_end_y 

                if next_idx == 1:
                    if not vals["is_origin"]:
                        current_start_x = -float(vals["offset_x"])
                        current_start_z = -float(vals["offset_z"])

                msg_sect1 = f"Section #{next_idx}: Building front cross-section..." if lang == "English" else f"第{next_idx}区間：手前側断面を構築中..."
                bar.update(20, msg_sect1)

                p1 = FreeCAD.Vector(current_start_x, 0, current_start_z)
                p2 = FreeCAD.Vector(current_start_x + vals["b_start"], 0, current_start_z)
                p3 = FreeCAD.Vector(current_start_x + vals["t_start"], 0, current_start_z + vals["h_start"])
                p4 = FreeCAD.Vector(current_start_x, 0, current_start_z + vals["h_start"])
                poly_start = Part.makePolygon([p1, p2, p3, p4, p1])

                L = vals["length"]
                local_offset_x = 0
                if vals["align_mode"] == 1:
                    local_offset_x = vals["b_start"] - vals["b_end"]
                
                next_end_x = current_start_x + local_offset_x

                msg_sect2 = f"Section #{next_idx}: Adjusting back cross-section..." if lang == "English" else f"第{next_idx}区間：奥側断面を調整中..."
                bar.update(40, msg_sect2)

                q1 = FreeCAD.Vector(next_end_x, L, current_start_z)
                q2 = FreeCAD.Vector(next_end_x + vals["b_end"], L, current_start_z)
                q3 = FreeCAD.Vector(next_end_x + vals["t_end"], L, current_start_z + vals["h_end"])
                q4 = FreeCAD.Vector(next_end_x, L, current_start_z + vals["h_end"])
                poly_end = Part.makePolygon([q1, q2, q3, q4, q1])

                bar.update(60, translate_text("新スパンをロフト接続（ソリッド化）中...", lang))
                solid_wall = Part.makeLoft([poly_start, poly_end], True)
                
                for old_name in ["GL_Ground_Plane", "Axis_X_Red", "Axis_Y_Green", "Axis_Z_Blue"]:
                    old_obj = doc.getObject(old_name)
                    if old_obj: doc.removeObject(old_obj.Name)
                    
                wall_name = f"Gravity_Retaining_Wall_{next_idx}"
                obj = doc.addObject("Part::Feature", wall_name)
                obj.Shape = solid_wall
                
                obj.Placement.Base = FreeCAD.Vector(0, total_length, 0)
                
                obj.ViewObject.ShapeColor = (0.7, 0.7, 0.7)
                obj.ViewObject.DisplayMode = "Shaded"
                
                obj.addProperty("App::PropertyFloat", "EndOffsetX", "Construction")
                obj.addProperty("App::PropertyFloat", "EndOffsetY", "Construction")
                obj.addProperty("App::PropertyFloat", "EndOffsetZ", "Construction")
                
                obj.addProperty("App::PropertyLength", "WallLength", "Construction")
                obj.addProperty("App::PropertyLength", "HeightStart", "Construction")
                obj.addProperty("App::PropertyLength", "BaseWidthStart", "Construction")
                obj.addProperty("App::PropertyLength", "TopWidthStart", "Construction")
                obj.addProperty("App::PropertyLength", "HeightEnd", "Construction")
                obj.addProperty("App::PropertyLength", "BaseWidthEnd", "Construction")
                obj.addProperty("App::PropertyLength", "TopWidthEnd", "Construction")
                
                obj.EndOffsetX = next_end_x
                obj.EndOffsetY = total_length + L
                obj.EndOffsetZ = current_start_z
                obj.WallLength = L
                obj.HeightStart = vals["h_start"]
                obj.BaseWidthStart = vals["b_start"]
                obj.TopWidthStart = vals["t_start"]
                obj.HeightEnd = vals["h_end"]
                obj.BaseWidthEnd = vals["b_end"]
                obj.TopWidthEnd = vals["t_end"]
                
                bar.update(85, translate_text("総延長に合わせてGL環境を拡大再構築中...", lang))
                
                max_dim = max(vals["h_start"], vals["h_end"], vals["b_start"], vals["b_end"], total_length + L)
                guide_size = max_dim * 1.3
                
                ground_shape = Part.makeBox(guide_size * 2, guide_size * 2, 1)
                ground_obj = doc.addObject("Part::Feature", "GL_Ground_Plane")
                ground_obj.Shape = ground_shape
                ground_obj.Placement = FreeCAD.Placement(FreeCAD.Vector(-guide_size * 0.5, -guide_size * 0.2, current_start_z - 10), FreeCAD.Rotation())
                ground_obj.ViewObject.ShapeColor = (0.45, 0.42, 0.38)
                ground_obj.ViewObject.Transparency = 70
                ground_obj.ViewObject.DisplayMode = "Shaded"

                ax_x = Part.LineSegment(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(guide_size, 0, 0)).toShape()
                obj_x = doc.addObject("Part::Feature", "Axis_X_Red")
                obj_x.Shape = ax_x
                obj_x.ViewObject.LineColor = (1.0, 0.1, 0.1)
                obj_x.ViewObject.LineWidth = 4
                
                ax_y = Part.LineSegment(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, guide_size, 0)).toShape()
                obj_y = doc.addObject("Part::Feature", "Axis_Y_Green")
                obj_y.Shape = ax_y
                obj_y.ViewObject.LineColor = (0.1, 0.8, 0.1)
                obj_y.ViewObject.LineWidth = 4
                
                ax_z = Part.LineSegment(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, guide_size)).toShape()
                obj_z = doc.addObject("Part::Feature", "Axis_Z_Blue")
                obj_z.Shape = ax_z
                obj_z.ViewObject.LineColor = (0.1, 0.1, 1.0)
                obj_z.ViewObject.LineWidth = 4
                
                doc.commitTransaction()
                doc.recompute()
                if FreeCADGui.activeView():
                    FreeCADGui.SendMsgToActiveView("ViewFit")

                bar.update(100, translate_text("完了しました！", lang))

                if lang == "English":
                    title_succ = "Success"
                    msg_succ = f"Retaining wall section #{next_idx} completed and recorded to properties!"
                else:
                    title_succ = "成功"
                    msg_succ = f"第{next_idx}区間の擁壁が完成し、情報をプロパティに記録しました！"

                QtWidgets.QMessageBox.information(None, title_succ, msg_succ)

            except Exception as e:
                doc.abortTransaction()
                FreeCAD.Console.PrintError(f"Wall creation error: {str(e)}\n")
                err_title = "Error" if lang == "English" else "エラー"
                err_msg = f"An error occurred during creation:\n{str(e)}" if lang == "English" else f"生成中にエラーが発生しました:\n{str(e)}"
                QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Construction_MakeWall', Tool_MakeWall())