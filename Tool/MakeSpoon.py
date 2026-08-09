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
class SpoonDialog(TranslatedDialog):
    def __init__(self, parent=None):
        super(SpoonDialog, self).__init__(parent)
        self.setWindowTitle("スプーン工場：【ステップ1】皿の形状")
        self.resize(380, 220)
        
        layout = QtWidgets.QFormLayout(self)
        
        self.spin_width = QtWidgets.QDoubleSpinBox()
        self.spin_width.setRange(5.0, 500.0)
        self.spin_width.setValue(40.0)
        self.spin_width.setSuffix(" mm")
        
        self.spin_length = QtWidgets.QDoubleSpinBox()
        self.spin_length.setRange(5.0, 500.0)
        self.spin_length.setValue(60.0)
        self.spin_length.setSuffix(" mm")

        self.spin_depth = QtWidgets.QDoubleSpinBox()
        self.spin_depth.setRange(2.0, 200.0)
        self.spin_depth.setValue(20.0)
        self.spin_depth.setSuffix(" mm")

        self.spin_wall = QtWidgets.QDoubleSpinBox()
        self.spin_wall.setRange(0.5, 10.0)
        self.spin_wall.setValue(1.5)
        self.spin_wall.setSuffix(" mm")

        layout.addRow("<b>皿の幅 (X方向):</b>", self.spin_width)
        layout.addRow("<b>皿の長さ (Y方向):</b>", self.spin_length)
        layout.addRow("<b>皿の深さ (Z方向):</b>", self.spin_depth)
        layout.addRow("<b>皿の肉厚 (厚み):</b>", self.spin_wall)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        return {
            "width": self.spin_width.value(),
            "length": self.spin_length.value(),
            "depth": self.spin_depth.value(),
            "wall": self.spin_wall.value()
        }

# 【修正】TranslatedDialog を継承させて自動翻訳を有効化
class HandleDialog(TranslatedDialog):
    def __init__(self, parent=None):
        super(HandleDialog, self).__init__(parent)
        self.setWindowTitle("スプーン工場：【ステップ2】柄と仕上げ")
        self.resize(380, 200)
        
        layout = QtWidgets.QFormLayout(self)
        
        self.spin_h_length = QtWidgets.QDoubleSpinBox()
        self.spin_h_length.setRange(10.0, 1000.0)
        self.spin_h_length.setValue(120.0)
        self.spin_h_length.setSuffix(" mm")
        
        self.spin_h_width = QtWidgets.QDoubleSpinBox()
        self.spin_h_width.setRange(2.0, 50.0)
        self.spin_h_width.setValue(8.0)
        self.spin_h_width.setSuffix(" mm")
        
        self.spin_h_thick = QtWidgets.QDoubleSpinBox()
        self.spin_h_thick.setRange(1.0, 30.0)
        self.spin_h_thick.setValue(3.0)
        self.spin_h_thick.setSuffix(" mm")
        
        self.spin_fillet = QtWidgets.QDoubleSpinBox()
        self.spin_fillet.setRange(0.0, 5.0)
        self.spin_fillet.setValue(0.5)
        self.spin_fillet.setSingleStep(0.1)
        self.spin_fillet.setSuffix(" mm")

        layout.addRow("<b>柄の長さ:</b>", self.spin_h_length)
        layout.addRow("柄の根本の幅（太さ）:", self.spin_h_width)
        layout.addRow("柄の厚み:", self.spin_h_thick)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        layout.addRow("<b>【仕上げ】口が触れるフチの角丸(R):</b>", self.spin_fillet)
        layout.addRow(QtWidgets.QLabel("<font color='gray'>※柄には角丸を適用しません</font>"))
        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        return {
            "h_length": self.spin_h_length.value(),
            "h_width": self.spin_h_width.value(),
            "h_thick": self.spin_h_thick.value(),
            "fillet": self.spin_fillet.value()
        }

class Tool_MakeSpoon:
    def GetResources(self):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "spoon.png").replace('\\', '/')
        return {
            'Pixmap': icon_path, 
            'MenuText': "スプーンの作成", 
            'ToolTip': "写真を参考にした人間工学カーブと、パズル結合方式による安定生成を行います"
        }

    def Activated(self):
        lang = get_language()
        doc = FreeCAD.activeDocument()
        if not doc:
            doc = FreeCAD.newDocument("SpoonDesign")

        d_bowl = SpoonDialog()
        if d_bowl.exec_() != QtWidgets.QDialog.Accepted: 
            return
        vals_bowl = d_bowl.get_values()
        
        d_handle = HandleDialog()
        if d_handle.exec_() != QtWidgets.QDialog.Accepted:
            return
        vals_handle = d_handle.get_values()

        width = vals_bowl["width"]
        length = vals_bowl["length"]
        depth = vals_bowl["depth"]
        wall = vals_bowl["wall"]
        
        h_length = vals_handle["h_length"]
        h_width = vals_handle["h_width"]
        h_thick = vals_handle["h_thick"]
        fillet_r = vals_handle["fillet"]

        if width <= wall * 2.0 or length <= wall * 2.0:
            QtWidgets.QMessageBox.warning(None, translate_text("エラー", lang), translate_text("肉厚が大きすぎるため、内側をくり抜くスペースがありません。", lang))
            return

        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("スプーン製造ライン", lang), initial_text=translate_text("皿を計算中...", lang))
            
            doc.openTransaction("CreateCompleteSpoon")
            try:
                base_sphere = Part.makeSphere(1.0)
                
                mat_base = FreeCAD.Matrix()
                mat_base.scale(width / 2.0, length / 2.0, depth / 2.0)
                outer_ellipse = base_sphere.transformGeometry(mat_base)
                
                mat_inner = FreeCAD.Matrix()
                mat_inner.scale((width - wall*2)/2.0, (length - wall*2)/2.0, depth/2.0)
                inner_ellipse = base_sphere.transformGeometry(mat_inner)
                inner_ellipse.translate(FreeCAD.Vector(0, 0, wall))
                
                hollow_bowl = outer_ellipse.cut(inner_ellipse)
                
                box_size = max(width, length) + 20.0
                cutter_box = Part.makeBox(box_size, box_size, box_size)
                cutter_box.translate(FreeCAD.Vector(-box_size / 2.0, -box_size / 2.0, 0))
                final_spoon_bowl = hollow_bowl.cut(cutter_box)

                if fillet_r > 0.0:
                    bar.update(30, translate_text("口が触れるフチのみを滑らかに加工中...", lang))
                    top_edges = []
                    for e in final_spoon_bowl.Edges:
                        if abs(e.BoundBox.ZMax) < 0.01 and abs(e.BoundBox.ZMin) < 0.01:
                            top_edges.append(e)
                    
                    if top_edges:
                        try:
                            safe_r = min(fillet_r, wall / 2.0 - 0.05)
                            f_bowl = final_spoon_bowl.makeFillet(safe_r, top_edges)
                            if not f_bowl.isNull():
                                final_spoon_bowl = f_bowl
                        except Exception as e:
                            from FreeCAD import Console
                            Console.PrintWarning(f"Skip rim fillet: {str(e)}\n")
                
                bar.update(45, translate_text("横からのS字シルエットを生成中...", lang))
                
                y_neck = -length / 2.0 + (wall * 0.8)
                table_z = -depth / 2.0
                
                t0 = FreeCAD.Vector(0, y_neck, 0)
                t1 = FreeCAD.Vector(0, y_neck - h_length * 0.25, h_length * 0.15)
                t2 = FreeCAD.Vector(0, y_neck - h_length * 0.7, table_z + h_thick)
                t3 = FreeCAD.Vector(0, y_neck - h_length, table_z + h_thick)
                
                curve_top = Part.BezierCurve()
                curve_top.setPoles([t0, t1, t2, t3])
                edge_top = curve_top.toShape()
                
                b3 = FreeCAD.Vector(0, y_neck - h_length, table_z)
                b2 = FreeCAD.Vector(0, y_neck - h_length * 0.7, table_z)
                b1 = FreeCAD.Vector(0, y_neck - h_length * 0.25, h_length * 0.15 - h_thick)
                b0 = FreeCAD.Vector(0, y_neck, -h_thick)
                
                curve_bottom = Part.BezierCurve()
                curve_bottom.setPoles([b3, b2, b1, b0])
                edge_bottom = curve_bottom.toShape()
                
                edge_neck = Part.makeLine(b0, t0)
                edge_tail = Part.makeLine(t3, b3)
                
                side_wire = Part.Wire([edge_top, edge_tail, edge_bottom, edge_neck])
                side_face = Part.Face(side_wire)
                
                max_w = h_width * 3.0
                side_solid = side_face.extrude(FreeCAD.Vector(max_w, 0, 0))
                side_solid.translate(FreeCAD.Vector(-max_w / 2.0, 0, 0))

                bar.update(60, translate_text("上からのシルエットを生成中...", lang))
                
                w_n = h_width / 2.0
                w_t = (h_width * 1.5) / 2.0
                
                pt0 = FreeCAD.Vector(-w_n, y_neck, 0)
                pt1 = FreeCAD.Vector(w_n, y_neck, 0)
                pt2 = FreeCAD.Vector(w_t, y_neck - h_length, 0)
                pt3 = FreeCAD.Vector(-w_t, y_neck - h_length, 0)
                
                top_poly = Part.makePolygon([pt0, pt1, pt2, pt3, pt0])
                top_face = Part.Face(Part.Wire(top_poly))
                
                z_min = table_z - 10.0
                z_height = h_length * 0.5 + 20.0
                top_solid = top_face.extrude(FreeCAD.Vector(0, 0, z_height))
                top_solid.translate(FreeCAD.Vector(0, 0, z_min))

                handle_solid = side_solid.common(top_solid)

                bar.update(75, translate_text("皿から柄のめり込みを減算（受け皿作成）中...", lang))
                socket_bowl = final_spoon_bowl.cut(handle_solid)

                bar.update(85, translate_text("皿と柄をピッタリはめ込んでフュージョン中...", lang))
                final_shape = socket_bowl.fuse(handle_solid)

                bar.update(95, translate_text("FreeCADへ登録中...", lang))
                
                obj = doc.addObject("Part::Feature", "CompleteSpoon")
                obj.Shape = final_shape
                obj.ViewObject.ShapeColor = (0.5, 0.45, 0.4)
                obj.ViewObject.DisplayMode = "Shaded"
                
                bar.update(100, translate_text("完了しました！", lang))
                
                doc.commitTransaction()
                doc.recompute()
                if FreeCADGui.activeView():
                    FreeCADGui.activeView().fitAll()
                    FreeCADGui.activeView().viewRight()

            except Exception as e:
                doc.abortTransaction()
                FreeCAD.Console.PrintError(f"Spoon creation error: {str(e)}\n")
                err_title = "Error" if lang == "English" else "エラー"
                err_msg = f"An error occurred during creation:\n{str(e)}" if lang == "English" else f"生成中にエラーが発生しました:\n{str(e)}"
                QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Ring_MakeSpoon', Tool_MakeSpoon())