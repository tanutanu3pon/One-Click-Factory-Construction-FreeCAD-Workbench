# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part

from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedDialog, translate_text
from Core.Language import get_language

class BoxCulvertDialog(TranslatedDialog):
    """ボックスカルバートの設計・数量計算ダイアログ"""
    def __init__(self, parent=None):
        super(BoxCulvertDialog, self).__init__(parent)
        self.setWindowTitle("ボックスカルバート製造・数量計算工場")
        self.resize(420, 530)
        
        layout = QtWidgets.QFormLayout(self)
        MAX_MM = 100000.0

        layout.addRow(QtWidgets.QLabel("<h3>【断面基本寸法 (内空・壁厚)】</h3>"))
        
        self.spin_inner_w = QtWidgets.QDoubleSpinBox()
        self.spin_inner_w.setRange(10.0, MAX_MM)
        self.spin_inner_w.setValue(2000.0)
        self.spin_inner_w.setSuffix(" mm")
        layout.addRow("内空幅 (W):", self.spin_inner_w)
        
        self.spin_inner_h = QtWidgets.QDoubleSpinBox()
        self.spin_inner_h.setRange(10.0, MAX_MM)
        self.spin_inner_h.setValue(2000.0)
        self.spin_inner_h.setSuffix(" mm")
        layout.addRow("内空高 (H):", self.spin_inner_h)

        self.spin_t_top = QtWidgets.QDoubleSpinBox()
        self.spin_t_top.setRange(10.0, 2000.0)
        self.spin_t_top.setValue(250.0)
        self.spin_t_top.setSuffix(" mm")
        layout.addRow("頂版厚 (T1):", self.spin_t_top)

        self.spin_t_bot = QtWidgets.QDoubleSpinBox()
        self.spin_t_bot.setRange(10.0, 2000.0)
        self.spin_t_bot.setValue(250.0)
        self.spin_t_bot.setSuffix(" mm")
        layout.addRow("底版厚 (T2):", self.spin_t_bot)

        self.spin_t_side = QtWidgets.QDoubleSpinBox()
        self.spin_t_side.setRange(10.0, 2000.0)
        self.spin_t_side.setValue(250.0)
        self.spin_t_side.setSuffix(" mm")
        layout.addRow("側壁厚 (T3):", self.spin_t_side)

        layout.addRow(QtWidgets.QLabel("<hr><h3>【ハンチ・目地(継手)設定】</h3>"))

        self.spin_haunch = QtWidgets.QDoubleSpinBox()
        self.spin_haunch.setRange(0.0, 1000.0)
        self.spin_haunch.setValue(150.0)
        self.spin_haunch.setSuffix(" mm (0でハンチなし)")
        layout.addRow("ハンチサイズ (Hn):", self.spin_haunch)

        self.spin_span_l = QtWidgets.QDoubleSpinBox()
        self.spin_span_l.setRange(1.0, 10000.0)
        self.spin_span_l.setValue(2000.0)
        self.spin_span_l.setSuffix(" mm")
        layout.addRow("1製品標準長 (標準ピッチ):", self.spin_span_l)

        self.combo_joint = QtWidgets.QComboBox()
        self.combo_joint.setEditable(True)
        self.combo_joint.addItems(["10", "20"])
        self.combo_joint.setValidator(QtGui.QDoubleValidator(0.0, 100.0, 2, self))
        layout.addRow("目地幅 (Joint):", self.combo_joint)

        layout.addRow(QtWidgets.QLabel("<hr><h3>【全延長指定】</h3>"))

        self.spin_total_l = QtWidgets.QDoubleSpinBox()
        self.spin_total_l.setRange(1.0, MAX_MM * 10)
        self.spin_total_l.setValue(10500.0)
        self.spin_total_l.setSuffix(" mm")
        layout.addRow("全施工延長 (L):", self.spin_total_l)

        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        try:
            j_val = float(self.combo_joint.currentText().replace("mm", "").strip())
        except ValueError:
            j_val = 10.0

        return {
            "inner_w": self.spin_inner_w.value(),
            "inner_h": self.spin_inner_h.value(),
            "t_top": self.spin_t_top.value(),
            "t_bot": self.spin_t_bot.value(),
            "t_side": self.spin_t_side.value(),
            "haunch": self.spin_haunch.value(),
            "span_l": self.spin_span_l.value(),
            "joint_w": j_val,
            "total_l": self.spin_total_l.value()
        }

class Tool_MakeBoxCulvert:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "box_culvert.png").replace('\\', '/')
        return {
            'Pixmap': icon_path if os.path.exists(icon_path) else "", 
            'MenuText': "ボックスカルバート作成", 
            'ToolTip': "目地選択・完全密着直線配置・数量計算対応ボックスカルバートを自動生成します"
        }

    def make_culvert_section_wire(self, iw, ih, tt, tb, ts, hn):
        """XZ平面（Y=0）上に垂直なハンチ付きカルバート断面（外郭・内郭）の2Dワイヤーを生成"""
        hw, hh = iw / 2.0, ih / 2.0
        ow, oh = hw + ts, hh + tt
        ob_h = hh + tb

        # 外郭ポリゴン (XZ平面)
        pts_out = [
            FreeCAD.Vector(-ow, 0, -ob_h),
            FreeCAD.Vector( ow, 0, -ob_h),
            FreeCAD.Vector( ow, 0,  oh),
            FreeCAD.Vector(-ow, 0,  oh),
            FreeCAD.Vector(-ow, 0, -ob_h)
        ]
        wire_out = Part.makePolygon(pts_out)

        # 内郭ポリゴン (XZ平面)
        if hn > 0.1:
            pts_in = [
                FreeCAD.Vector(-hw + hn, 0, -hh),
                FreeCAD.Vector( hw - hn, 0, -hh),
                FreeCAD.Vector( hw, 0, -hh + hn),
                FreeCAD.Vector( hw, 0,  hh - hn),
                FreeCAD.Vector( hw - hn, 0,  hh),
                FreeCAD.Vector(-hw + hn, 0,  hh),
                FreeCAD.Vector(-hw, 0,  hh - hn),
                FreeCAD.Vector(-hw, 0, -hh + hn),
                FreeCAD.Vector(-hw + hn, 0, -hh)
            ]
        else:
            pts_in = [
                FreeCAD.Vector(-hw, 0, -hh),
                FreeCAD.Vector( hw, 0, -hh),
                FreeCAD.Vector( hw, 0,  hh),
                FreeCAD.Vector(-hw, 0,  hh),
                FreeCAD.Vector(-hw, 0, -hh)
            ]
        wire_in = Part.makePolygon(pts_in)

        face_out = Part.Face(wire_out)
        face_in = Part.Face(wire_in)
        return face_out.cut(face_in)

    def Activated(self):
        lang = get_language()
        doc = FreeCAD.activeDocument() or FreeCAD.newDocument("BoxCulvertProject")

        d = BoxCulvertDialog(FreeCADGui.getMainWindow())
        if d.exec_() != QtWidgets.QDialog.Accepted: 
            return
        vals = d.get_values()

        iw, ih = vals["inner_w"], vals["inner_h"]
        tt, tb, ts = vals["t_top"], vals["t_bot"], vals["t_side"]
        hn = vals["haunch"]
        std_span_l = vals["span_l"]
        joint_w = vals["joint_w"]
        total_l = vals["total_l"]

        doc.openTransaction("CreateBoxCulvert")
        try:
            with Progress.ProgressManager() as bar:
                bar.start(title=translate_text("ボックスカルバート製造・数量計算工場", lang), initial_text=translate_text("カルバート断面を構築中...", lang))
                
                # 1. XZ平面上の2D断面Faceの作成
                sec_face = self.make_culvert_section_wire(iw, ih, tt, tb, ts, hn)

                # 2. 正確なブロック割付け計算
                block_lengths = []
                rem_len = total_l

                while rem_len > 0.001:
                    if rem_len >= (std_span_l + joint_w):
                        block_lengths.append(std_span_l)
                        rem_len -= (std_span_l + joint_w)
                    elif rem_len > std_span_l:
                        block_lengths.append(std_span_l)
                        rem_len -= std_span_l
                    else:
                        block_lengths.append(rem_len)
                        rem_len = 0.0

                num_blocks = len(block_lengths)
                grp = doc.addObject("App::DocumentObjectGroup", "BoxCulvert_Line")
                
                total_conc_vol_mm3 = 0.0
                total_form_area_mm2 = 0.0
                total_joint_area_mm2 = 0.0
                current_y = 0.0

                block_details_str = ""
                section_area_mm2 = sec_face.Area  # 断面1箇所の設置面積 (mm2)

                for i, curr_len in enumerate(block_lengths):
                    pct = int((i + 1) / float(num_blocks) * 85.0)
                    msg_txt = f"躯体・目地配置中 ({i+1}/{num_blocks})..." if lang == "日本語" else f"Building Block ({i+1}/{num_blocks})..."
                    bar.update(pct, msg_txt)

                    # --- A. 躯体コンクリート（回転なし、そのままY軸方向へ直進押出） ---
                    solid_block = sec_face.extrude(FreeCAD.Vector(0, curr_len, 0))
                    solid_block.translate(FreeCAD.Vector(0, current_y, 0))

                    total_conc_vol_mm3 += solid_block.Volume
                    total_form_area_mm2 += (solid_block.Area - (section_area_mm2 * 2.0))

                    obj_conc = doc.addObject("Part::Feature", f"BoxCulvert_Block_{i+1}")
                    obj_conc.Shape = solid_block.removeSplitter()
                    obj_conc.ViewObject.ShapeColor = (0.75, 0.75, 0.78)
                    obj_conc.ViewObject.DisplayMode = "Shaded"
                    grp.addObject(obj_conc)

                    current_y += curr_len

                    is_adjusted = " (端数調整)" if (curr_len < std_span_l - 0.001) else ""
                    block_details_str += f"&nbsp;&nbsp;・躯体 #{i+1} : <b>{curr_len:,.1f} mm</b>{is_adjusted}<br>"

                    # --- B. 目地材（躯体のすぐ後ろに完全密着で配置） ---
                    if joint_w > 0.01 and i < (num_blocks - 1):
                        solid_joint = sec_face.extrude(FreeCAD.Vector(0, joint_w, 0))
                        solid_joint.translate(FreeCAD.Vector(0, current_y, 0))

                        # 目地材は設置面積(m2)として加算
                        total_joint_area_mm2 += section_area_mm2

                        obj_joint = doc.addObject("Part::Feature", f"BoxCulvert_Joint_{i+1}")
                        obj_joint.Shape = solid_joint.removeSplitter()
                        obj_joint.ViewObject.ShapeColor = (0.15, 0.15, 0.15)  # 黒色
                        obj_joint.ViewObject.DisplayMode = "Shaded"
                        grp.addObject(obj_joint)

                        current_y += joint_w

                bar.update(95, translate_text("FreeCADへ登録中...", lang))
                doc.commitTransaction()
                doc.recompute()
                
                bar.update(100, translate_text("完了しました！", lang))
                if FreeCADGui.activeView():
                    FreeCADGui.activeView().fitAll()
                    FreeCADGui.activeView().viewAxometric()

            # --- 数量計算および個別長さ内訳レポートの出力 ---
            conc_m3 = total_conc_vol_mm3 / 1e9
            joint_m2 = total_joint_area_mm2 / 1e6  # 目地材面積(m2)
            form_m2 = total_form_area_mm2 / 1e6

            if lang == "日本語":
                res_title = "ボックスカルバート 数量・内訳レポート"
                res_msg = (
                    f"<h3>【ボックスカルバート 数量・割付けレポート】</h3><hr>"
                    f"<b>■ 全施工延長 (L):</b> {total_l:,.1f} mm ({num_blocks} 躯体 / 目地幅: {joint_w} mm)<br>"
                    f"<b>■ 躯体個別長さの内訳:</b><br>{block_details_str}<br>"
                    f"<b>■ コンクリート体積 (総体積):</b><br>"
                    f"&nbsp;&nbsp;&nbsp;&nbsp;<font color='#0055ff' size='5'><b>{conc_m3:,.2f} m3</b></font><br>"
                    f"<b>■ 黒色目地材 総設置面積:</b><br>"
                    f"&nbsp;&nbsp;&nbsp;&nbsp;<font color='#444444' size='4'><b>{joint_m2:,.2f} m2</b></font> ({num_blocks-1} 箇所)<br><br>"
                    f"<b>■ 必要型枠面積 (内空＋外壁面):</b><br>"
                    f"&nbsp;&nbsp;&nbsp;&nbsp;<font color='#00aa00' size='5'><b>{form_m2:,.2f} m2</b></font><br>"
                )
            else:
                res_title = "Box Culvert Quantity & Breakdown Report"
                res_msg = (
                    f"<h3>[Box Culvert Quantity & Breakdown Report]</h3><hr>"
                    f"<b>■ Total Length (L):</b> {total_l:,.1f} mm ({num_blocks} Blocks / Joint: {joint_w} mm)<br>"
                    f"<b>■ Individual Block Lengths:</b><br>{block_details_str}<br>"
                    f"<b>■ Concrete Volume:</b><br>"
                    f"&nbsp;&nbsp;&nbsp;&nbsp;<font color='#0055ff' size='5'><b>{conc_m3:,.2f} m3</b></font><br>"
                    f"<b>■ Joint Filler Area:</b><br>"
                    f"&nbsp;&nbsp;&nbsp;&nbsp;<font color='#444444' size='4'><b>{joint_m2:,.2f} m2</b></font> ({num_blocks-1} Places)<br><br>"
                    f"<b>■ Formwork Surface Area:</b><br>"
                    f"&nbsp;&nbsp;&nbsp;&nbsp;<font color='#00aa00' size='5'><b>{form_m2:,.2f} m2</b></font><br>"
                )

            QtWidgets.QMessageBox.information(None, res_title, res_msg)

        except Exception as e:
            doc.abortTransaction()
            FreeCAD.Console.PrintError(f"Box Culvert creation error: {str(e)}\n")
            err_title = "Error" if lang == "English" else "エラー"
            err_msg = f"An error occurred during creation:\n{str(e)}" if lang == "English" else f"生成中にエラーが発生しました:\n{str(e)}"
            QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Construction_MakeBoxCulvert', Tool_MakeBoxCulvert())