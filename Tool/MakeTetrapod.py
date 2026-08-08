# -*- coding: utf-8 -*-
import os
import math
import FreeCAD
import FreeCADGui
import Part
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress

class TetrapodDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(TetrapodDialog, self).__init__(parent)
        self.setWindowTitle("テトラポッド（消波ブロック）製造工場")
        self.resize(380, 200)
        
        layout = QtWidgets.QFormLayout(self)
        
        self.spin_length = QtWidgets.QDoubleSpinBox()
        self.spin_length.setRange(5.0, 1000.0)
        self.spin_length.setValue(30.0)
        self.spin_length.setSuffix(" mm")
        
        self.spin_base_r = QtWidgets.QDoubleSpinBox()
        self.spin_base_r.setRange(1.0, 500.0)
        self.spin_base_r.setValue(10.0)
        self.spin_base_r.setSuffix(" mm")
        
        self.spin_tip_r = QtWidgets.QDoubleSpinBox()
        self.spin_tip_r.setRange(1.0, 500.0)
        self.spin_tip_r.setValue(6.0)
        self.spin_tip_r.setSuffix(" mm")

        layout.addRow("<b>足の長さ（中心から）:</b>", self.spin_length)
        layout.addRow("足の根本の太さ（半径）:", self.spin_base_r)
        layout.addRow("足の先端の太さ（半径）:", self.spin_tip_r)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.button(QtWidgets.QDialogButtonBox.Ok).setText("テトラポッドを生成")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        return {
            "length": self.spin_length.value(),
            "base_r": self.spin_base_r.value(),
            "tip_r": self.spin_tip_r.value()
        }

class Tool_MakeTetrapod:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "tetrapod.png").replace('\\', '/')
        return {
            'Pixmap': icon_path, 
            'MenuText': "テトラポッドの作成", 
            'ToolTip': "指定したサイズのテトラポッドをフリーズなしで高速生成します"
        }

    def Activated(self):
        doc = FreeCAD.activeDocument()
        if not doc:
            doc = FreeCAD.newDocument("TetrapodDesign")

        d = TetrapodDialog(FreeCADGui.getMainWindow())
        if d.exec_() != QtWidgets.QDialog.Accepted: 
            return
        vals = d.get_values()

        leg_length = vals["length"]
        base_r = vals["base_r"]
        tip_r = vals["tip_r"]

        if tip_r >= base_r:
            QtWidgets.QMessageBox.warning(None, "エラー", "先端の太さは、根本より細くしてください。")
            return

        with Progress.ProgressManager() as bar:
            bar.start(title="消波ブロック製造工場", initial_text="形状を計算中...")
            
            doc.openTransaction("CreateTetrapod")
            
            bar.update(40, "基本形状を配置中...")
            parts_list = []
            
            core_sphere = Part.makeSphere(base_r * 1.05)
            parts_list.append(core_sphere)
            
            leg1 = Part.makeCone(base_r, tip_r, leg_length)
            parts_list.append(leg1)
            
            tilt_rad = math.acos(-1.0 / 3.0)
            tilt_deg = math.degrees(tilt_rad)
            
            for yaw in [0, 120, 240]:
                cone = Part.makeCone(base_r, tip_r, leg_length)
                tilt_rot = FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), tilt_deg)
                yaw_rot = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), yaw)
                cone.Placement = FreeCAD.Placement(FreeCAD.Vector(0, 0, 0), yaw_rot.multiply(tilt_rot))
                parts_list.append(cone)

            bar.update(70, "パーツを複合化中...")
            final_shape = Part.makeCompound(parts_list)

            bar.update(95, "FreeCADへ形状を出力中...")
            
            obj = doc.addObject("Part::Feature", "Tetrapod")
            obj.Shape = final_shape
            obj.ViewObject.ShapeColor = (0.65, 0.65, 0.65)
            obj.ViewObject.DisplayMode = "Shaded"
            
            bar.update(100, "生成が完了しました！")
            
            doc.commitTransaction()
            doc.recompute()
            FreeCADGui.activeView().fitAll()

FreeCADGui.addCommand('Construction_MakeTetrapod', Tool_MakeTetrapod())