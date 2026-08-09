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
class RoadDialog(TranslatedDialog):
    def __init__(self, parent=None):
        super(RoadDialog, self).__init__(parent)
        self.setWindowTitle("道路・連続成形工場")
        self.resize(400, 380)
        
        layout = QtWidgets.QFormLayout(self)
        MAX_MM = 1000000

        layout.addRow(QtWidgets.QLabel("<h3>【道路の幅と層構造】</h3>"))
        self.spin_width = QtWidgets.QSpinBox()
        self.spin_width.setRange(500, MAX_MM)
        self.spin_width.setValue(6000)
        self.spin_width.setSuffix(" mm")
        layout.addRow("道路幅:", self.spin_width)
        
        self.spin_pave = QtWidgets.QSpinBox()
        self.spin_pave.setRange(0, MAX_MM)
        self.spin_pave.setValue(100)
        self.spin_pave.setSuffix(" mm")
        layout.addRow("舗装厚（表層・基層）:", self.spin_pave)

        self.spin_upper = QtWidgets.QSpinBox()
        self.spin_upper.setRange(0, MAX_MM)
        self.spin_upper.setValue(150)
        self.spin_upper.setSuffix(" mm")
        layout.addRow("上層路盤厚:", self.spin_upper)

        self.spin_lower = QtWidgets.QSpinBox()
        self.spin_lower.setRange(0, MAX_MM)
        self.spin_lower.setValue(300)
        self.spin_lower.setSuffix(" mm")
        layout.addRow("下層路盤厚:", self.spin_lower)

        layout.addRow(QtWidgets.QLabel("<hr><h3>【配置・アライメントの設定】</h3>"))
        self.spin_length = QtWidgets.QSpinBox()
        self.spin_length.setRange(100, MAX_MM * 10)
        self.spin_length.setValue(100000)
        self.spin_length.setSuffix(" mm")
        layout.addRow("道路の延長（長さ L）:", self.spin_length)

        self.spin_z_offset = QtWidgets.QSpinBox()
        self.spin_z_offset.setRange(-MAX_MM, MAX_MM)
        self.spin_z_offset.setValue(0)
        self.spin_z_offset.setSuffix(" mm (坂道の高低差)")
        layout.addRow("縦断高低差 (Z軸):", self.spin_z_offset)

        self.combo_align = QtWidgets.QComboBox()
        self.combo_align.addItems([
            "道路中心（センターライン）を基準に通す", 
            "左側エッジを基準に通す",
            "右側エッジを基準に通す"
        ])
        layout.addRow("基準線の通し方:", self.combo_align)

        layout.addRow(QtWidgets.QLabel("<hr>"))
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        return {
            "width": self.spin_width.value(),
            "pave": self.spin_pave.value(),
            "upper": self.spin_upper.value(),
            "lower": self.spin_lower.value(),
            "length": self.spin_length.value(),
            "z_offset": self.spin_z_offset.value(),
            "align_mode": self.combo_align.currentIndex()
        }

class Tool_MakeRoad:
    def GetResources(self):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "road.png").replace('\\', '/')
        return {
            'Pixmap': icon_path if os.path.exists(icon_path) else "", 
            'MenuText': "道路の作成", 
            'ToolTip': "道幅や各層の厚み、縦断勾配を指定して、本格的な舗装構成を持つ道路を連続生成します"
        }

    def Activated(self):
        lang = get_language()

        dialog = RoadDialog()
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
            
        vals = dialog.get_values()
        
        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("道路成形ライン", lang), initial_text=translate_text("既存の道路データをスキャン中...", lang))

            try:
                doc = FreeCAD.activeDocument()
                if not doc:
                    doc = FreeCAD.newDocument("Construction_Project")
                    
                max_end_y = 0.0        
                current_start_x = 0.0   
                current_start_z = 0.0   
                max_idx = 0            

                for obj in doc.Objects:
                    if obj.Name.startswith("Infra_Road_"):
                        try:
                            idx = int(obj.Name.split("_")[-1])
                            if idx > max_idx: max_idx = idx
                        except Exception: pass
                        if hasattr(obj, "EndOffsetY"):
                            if obj.EndOffsetY > max_end_y:
                                max_end_y = obj.EndOffsetY
                                current_start_x = getattr(obj, "EndOffsetX", 0.0)
                                current_start_z = getattr(obj, "EndOffsetZ", 0.0)

                next_idx = max_idx + 1  
                Y_start = max_end_y
                Y_end = max_end_y + vals["length"]

                w = vals["width"]
                if vals["align_mode"] == 0:
                    sx1, sx2 = current_start_x - w/2, current_start_x + w/2
                    cx_start = current_start_x
                elif vals["align_mode"] == 1:
                    sx1, sx2 = current_start_x, current_start_x + w
                    cx_start = current_start_x + w/2
                else:
                    sx1, sx2 = current_start_x - w, current_start_x
                    cx_start = current_start_x - w/2

                ex1, ex2 = sx1, sx2
                cx_end = cx_start
                next_end_x = current_start_x
                next_end_z = current_start_z + vals["z_offset"]

                Z0 = current_start_z
                Z1 = Z0 - vals["pave"]
                Z2 = Z1 - vals["upper"]
                Z3 = Z2 - vals["lower"]

                E0 = next_end_z
                E1 = E0 - vals["pave"]
                E2 = E1 - vals["upper"]
                E3 = E2 - vals["lower"]

                group_name = f"Infra_Road_{next_idx}"
                group = doc.addObject("App::DocumentObjectGroup", group_name)
                group.addProperty("App::PropertyFloat", "EndOffsetX", "Construction")
                group.addProperty("App::PropertyFloat", "EndOffsetY", "Construction")
                group.addProperty("App::PropertyFloat", "EndOffsetZ", "Construction")
                group.EndOffsetX = next_end_x
                group.EndOffsetY = Y_end
                group.EndOffsetZ = next_end_z

                def make_layer_solid(sz_top, sz_bot, ez_top, ez_bot, is_line=False):
                    if is_line:
                        lx1, lx2 = cx_start - 75, cx_start + 75
                    else:
                        lx1, lx2 = sx1, sx2

                    p1 = FreeCAD.Vector(lx1, Y_start, sz_top)
                    p2 = FreeCAD.Vector(lx2, Y_start, sz_top)
                    p3 = FreeCAD.Vector(lx2, Y_start, sz_bot)
                    p4 = FreeCAD.Vector(lx1, Y_start, sz_bot)
                    poly_start = Part.makePolygon([p1, p2, p3, p4, p1])

                    q1 = FreeCAD.Vector(lx1, Y_end, ez_top)
                    q2 = FreeCAD.Vector(lx2, Y_end, ez_top)
                    q3 = FreeCAD.Vector(lx2, Y_end, ez_bot)
                    q4 = FreeCAD.Vector(lx1, Y_end, ez_bot)
                    poly_end = Part.makePolygon([q1, q2, q3, q4, q1])

                    return Part.makeLoft([poly_start, poly_end], True)

                bar.update(30, translate_text("舗装層（アスファルト）を生成中...", lang))
                if vals["pave"] > 0:
                    obj = doc.addObject("Part::Feature", f"{group_name}_Pavement")
                    obj.Shape = make_layer_solid(Z0, Z1, E0, E1)
                    obj.ViewObject.ShapeColor = (0.2, 0.2, 0.2)
                    obj.ViewObject.DisplayMode = "Shaded"
                    group.addObject(obj)

                bar.update(50, translate_text("上層路盤を生成中...", lang))
                if vals["upper"] > 0:
                    obj = doc.addObject("Part::Feature", f"{group_name}_UpperBase")
                    obj.Shape = make_layer_solid(Z1, Z2, E1, E2)
                    obj.ViewObject.ShapeColor = (0.55, 0.55, 0.55)
                    obj.ViewObject.DisplayMode = "Shaded"
                    group.addObject(obj)

                bar.update(70, translate_text("下層路盤を生成中...", lang))
                if vals["lower"] > 0:
                    obj = doc.addObject("Part::Feature", f"{group_name}_LowerBase")
                    obj.Shape = make_layer_solid(Z2, Z3, E2, E3)
                    obj.ViewObject.ShapeColor = (0.45, 0.35, 0.25)
                    obj.ViewObject.DisplayMode = "Shaded"
                    group.addObject(obj)

                bar.update(85, translate_text("センターラインをペイント中...", lang))
                obj_line = doc.addObject("Part::Feature", f"{group_name}_CenterLine")
                obj_line.Shape = make_layer_solid(Z0 + 5, Z0, E0 + 5, E0, is_line=True)
                obj_line.ViewObject.ShapeColor = (1.0, 1.0, 1.0)
                obj_line.ViewObject.DisplayMode = "Shaded"
                group.addObject(obj_line)

                for old_name in ["GL_Ground_Plane", "Axis_X_Red", "Axis_Y_Green", "Axis_Z_Blue"]:
                    old_obj = doc.getObject(old_name)
                    if old_obj: doc.removeObject(old_obj.Name)

                bar.update(90, translate_text("GL環境を再スケーリング中...", lang))
                max_dim = max(w, Y_end, abs(next_end_z))
                guide_size = max_dim * 1.2
                
                ground_shape = Part.makeBox(guide_size * 2, guide_size * 2, 1)
                ground_obj = doc.addObject("Part::Feature", "GL_Ground_Plane")
                ground_obj.Shape = ground_shape
                ground_obj.Placement = FreeCAD.Placement(FreeCAD.Vector(-guide_size * 0.5, -guide_size * 0.1, Z3 - 1000), FreeCAD.Rotation())
                ground_obj.ViewObject.ShapeColor = (0.45, 0.42, 0.38)
                ground_obj.ViewObject.Transparency = 70
                
                for name, vec, color in [("Axis_X_Red", FreeCAD.Vector(guide_size, 0, 0), (1.0, 0.1, 0.1)),
                                         ("Axis_Y_Green", FreeCAD.Vector(0, guide_size, 0), (0.1, 0.8, 0.1)),
                                         ("Axis_Z_Blue", FreeCAD.Vector(0, 0, guide_size), (0.1, 0.1, 1.0))]:
                    ax = Part.LineSegment(FreeCAD.Vector(0, 0, 0), vec).toShape()
                    ax_obj = doc.addObject("Part::Feature", name)
                    ax_obj.Shape = ax
                    ax_obj.ViewObject.LineColor = color
                    ax_obj.ViewObject.LineWidth = 4
                
                doc.recompute()
                FreeCADGui.SendMsgToActiveView("ViewFit")
                
                bar.update(100, translate_text("完了しました！", lang))
                
                if lang == "English":
                    title_succ = "Success"
                    msg_succ = f"Road section #{next_idx} (multi-layer structure) deployed!"
                else:
                    title_succ = "成功"
                    msg_succ = f"第{next_idx}区間の道路（多層構造）を配備しました！"

                QtWidgets.QMessageBox.information(None, title_succ, msg_succ)

            except Exception as e:
                FreeCAD.Console.PrintError(f"Road creation error: {str(e)}\n")
                err_title = "Error" if lang == "English" else "エラー"
                err_msg = f"An error occurred during creation:\n{str(e)}" if lang == "English" else f"生成中にエラーが発生しました:\n{str(e)}"
                QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Construction_MakeRoad', Tool_MakeRoad())