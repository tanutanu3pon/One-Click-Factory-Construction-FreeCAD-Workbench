# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part
from PySide import QtWidgets, QtCore

# Core/Progress.py から進捗マネージャーをインポート
import Core.Progress as Progress

# ==========================================
# ?? 第1ステップ：箱の基本寸法を決める窓
# ==========================================
class BoxDimensionDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(BoxDimensionDialog, self).__init__(parent)
        self.setWindowTitle("箱の設計 - ステップ 1/3")
        self.resize(300, 200)
        layout = QtWidgets.QFormLayout(self)
        
        self.input_w = self._create_spin(100.0)
        self.input_l = self._create_spin(150.0)
        self.input_h = self._create_spin(50.0)
        self.input_t = self._create_spin(3.0, 1.0, 20.0)
        self.input_tol = self._create_spin(0.25, 0.0, 5.0)
        
        layout.addRow("隙間の横幅 (X):", self.input_w)
        layout.addRow("隙間の奥行 (Y):", self.input_l)
        layout.addRow("隙間の高さ (Z):", self.input_h)
        layout.addRow("壁の厚み:", self.input_t)
        layout.addRow("クリアランス:", self.input_tol)
        
        self.btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.btn_box.accepted.connect(self.accept)
        self.btn_box.rejected.connect(self.reject)
        layout.addRow(self.btn_box)

    def _create_spin(self, val, min_v=5.0, max_v=1000.0):
        sb = QtWidgets.QDoubleSpinBox()
        sb.setRange(min_v, max_v)
        sb.setValue(val)
        sb.setSuffix(" mm")
        return sb

    def get_values(self):
        return (self.input_w.value(), self.input_l.value(), self.input_h.value(), self.input_t.value(), self.input_tol.value())

# ==========================================
# ?? 第2ステップ：エッジの加工を決める窓
# ==========================================
class BoxEdgeDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(BoxEdgeDialog, self).__init__(parent)
        self.setWindowTitle("角の処理 - ステップ 2/3")
        layout = QtWidgets.QVBoxLayout(self)
        
        self.radio_none = QtWidgets.QRadioButton("加工なし")
        self.radio_fillet = QtWidgets.QRadioButton("フィレット (丸める)")
        self.radio_chamfer = QtWidgets.QRadioButton("面取り (斜め)")
        self.radio_none.setChecked(True)
        
        layout.addWidget(self.radio_none)
        layout.addWidget(self.radio_fillet)
        layout.addWidget(self.radio_chamfer)
        
        self.input_size = QtWidgets.QDoubleSpinBox()
        self.input_size.setRange(0.1, 10.0)
        self.input_size.setValue(2.0)
        self.input_size.setEnabled(False)
        layout.addWidget(QtWidgets.QLabel("加工サイズ:"))
        layout.addWidget(self.input_size)
        
        self.radio_none.toggled.connect(lambda: self.input_size.setEnabled(False))
        self.radio_fillet.toggled.connect(lambda: self.input_size.setEnabled(True))
        self.radio_chamfer.toggled.connect(lambda: self.input_size.setEnabled(True))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_values(self):
        t = "Fillet" if self.radio_fillet.isChecked() else "Chamfer" if self.radio_chamfer.isChecked() else "None"
        return t, self.input_size.value()

# ==========================================
# ?? 第3ステップ：ふたの作成を決める窓
# ==========================================
class BoxLidDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(BoxLidDialog, self).__init__(parent)
        self.setWindowTitle("ふたの作成 - ステップ 3/3")
        layout = QtWidgets.QVBoxLayout(self)
        
        self.check_lid = QtWidgets.QCheckBox("落ちないふたを作成する")
        self.check_lid.setChecked(False)
        layout.addWidget(self.check_lid)
        
        self.group_lid = QtWidgets.QGroupBox("ふたの詳細設定")
        self.group_lid.setEnabled(False)
        group_layout = QtWidgets.QFormLayout(self.group_lid)
        
        self.input_lid_t = QtWidgets.QDoubleSpinBox()
        self.input_lid_t.setRange(1.0, 10.0)
        self.input_lid_t.setValue(2.0)
        self.input_lid_t.setSuffix(" mm")
        group_layout.addRow("ふたの板厚:", self.input_lid_t)
        layout.addWidget(self.group_lid)
        
        self.check_lid.toggled.connect(self.group_lid.setEnabled)
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_values(self):
        return self.check_lid.isChecked(), self.input_lid_t.value()

# ==========================================
# ?? ツール本体
# ==========================================
class Tool_MakeBox:
    def GetResources(self):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "box.png").replace('\\', '/')
        return {'Pixmap': icon_path, 'MenuText': "隙間にはまる箱作成", 'ToolTip': "落ちないストッパー付きの箱とふたを生成します"}

    def Activated(self):
        d1 = BoxDimensionDialog()
        if d1.exec_() != QtWidgets.QDialog.Accepted: return
        gap_w, gap_l, gap_h, wall_t, tolerance = d1.get_values()

        d2 = BoxEdgeDialog()
        if d2.exec_() != QtWidgets.QDialog.Accepted: return
        edge_type, edge_size = d2.get_values()

        d3 = BoxLidDialog()
        if d3.exec_() != QtWidgets.QDialog.Accepted: return
        lid_needed, lid_t = d3.get_values()

        self.create_perfect_fit_box(gap_w, gap_l, gap_h, wall_t, tolerance, edge_type, edge_size, lid_needed, lid_t)

    def create_perfect_fit_box(self, gap_w, gap_l, gap_h, wall_t, tolerance, edge_type, edge_size, lid_needed, lid_t):
        bar = Progress.ProgressManager()
        bar.start(title="箱モデル生成", initial_text="基本形状の作成中...")
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument()
        
        # 1. 箱の外寸・内寸の計算
        outer_w = gap_w - (tolerance * 2.0)
        outer_l = gap_l - (tolerance * 2.0)
        outer_h = gap_h - tolerance
        
        inner_w = outer_w - (wall_t * 2.0)
        inner_l = outer_l - (wall_t * 2.0)
        inner_h = outer_h - wall_t

        # 2. 箱本体のソリッド作成
        outer_box = Part.makeBox(outer_w, outer_l, outer_h)
        bar.update(40, "中をくり抜き中...")
        inner_box = Part.makeBox(inner_w, inner_l, inner_h)
        inner_box.translate(FreeCAD.Vector(wall_t, wall_t, wall_t))
        box_shape = outer_box.cut(inner_box)

        # エッジ加工（面取り/フィレット）
        if edge_type != "None":
            bar.update(60, f"{edge_type} 加工中...")
            edges = [e for e in box_shape.Edges if abs(e.BoundBox.ZMin) < 0.001 and abs(e.BoundBox.ZMax) < 0.001]
            if edges:
                try:
                    box_shape = box_shape.makeFillet(edge_size, edges) if edge_type == "Fillet" else box_shape.makeChamfer(edge_size, edges)
                except: pass

        obj_box = doc.addObject("Part::Feature", "PerfectBox")
        obj_box.Shape = box_shape.removeSplitter()
        obj_box.ViewObject.ShapeColor = (0.8, 0.8, 0.8)

        # 3. 【改善】「落ちないふた」の生成ロジック
        if lid_needed:
            bar.update(85, "ストッパー付きのふたを計算・生成中...")
            
            # ① ふたのメイン天板 (箱の外寸と同じサイズ)
            lid_top = Part.makeBox(outer_w, outer_l, lid_t)
            
            # ② 内側に入り込むストッパー（凸）のサイズ計算
            # スムーズ脱着のため、箱の内寸(inner_w, inner_l)よりさらに片側 0.15mm（両側で0.3mm）小さくします
            lid_clearance = 0.15 
            plug_w = inner_w - (lid_clearance * 2.0)
            plug_l = inner_l - (lid_clearance * 2.0)
            plug_h = wall_t  # ストッパーの突起の高さは、箱の肉厚と同じにする
            
            lid_plug = Part.makeBox(plug_w, plug_l, plug_h)
            
            # ストッパーを天板の「真裏の中央」に配置するための移動量を計算
            # 天板のフチから、(壁の厚み + ふたのクリアランス) 分だけ内側にずらす
            shift_x = wall_t + lid_clearance
            shift_y = wall_t + lid_clearance
            shift_z = -plug_h # 天板の裏側（下方向）に突き出させる
            
            lid_plug.translate(FreeCAD.Vector(shift_x, shift_y, shift_z))
            
            # 天板とストッパーをブーリアン演算でガッチリ一体化（結合）する
            full_lid_shape = lid_top.fuse(lid_plug)
            
            # 分かりやすいように、完成したフタを箱の上空 15.0mm に浮かせて配置します
            full_lid_shape.translate(FreeCAD.Vector(0, 0, outer_h + 15.0))
            
            obj_lid = doc.addObject("Part::Feature", "PerfectBox_Lid")
            obj_lid.Shape = full_lid_shape.removeSplitter()
            obj_lid.ViewObject.ShapeColor = (0.2, 0.6, 0.8)  # おしゃれなブルー

        bar.update(100, "完了")
        bar.close()
        doc.recompute()
        FreeCADGui.activeView().fitAll()

FreeCADGui.addCommand('Ring_Box', Tool_MakeBox())