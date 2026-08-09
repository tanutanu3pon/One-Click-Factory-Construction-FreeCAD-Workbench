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
class JigOptionDialog(TranslatedDialog):
    def __init__(self, target_name, size_mm, volume_mm3, parent=None):
        super(JigOptionDialog, self).__init__(parent)
        self.setWindowTitle("梱包体積の計算結果")
        self.resize(400, 260)
        layout = QtWidgets.QFormLayout(self)
        
        lang = get_language()
        
        lbl_target = QtWidgets.QLabel(f"<b>{translate_text('対象モデル:', lang)}</b> {target_name}")
        
        info_text = (
            f"{translate_text('幅 (X):', lang)} {size_mm[0]:.2f} mm<br>"
            f"{translate_text('奥行 (Y):', lang)} {size_mm[1]:.2f} mm<br>"
            f"{translate_text('高さ (Z):', lang)} {size_mm[2]:.2f} mm"
        )
        lbl_size = QtWidgets.QLabel(info_text)
        
        vol_label_txt = translate_text("ジャスト体積:", lang)
        lbl_volume = QtWidgets.QLabel(f"<font color='#2e7d32' size='4'><b>{vol_label_txt} {volume_mm3:,.2f} mm3</b></font>")
        
        self.spin_margin = QtWidgets.QDoubleSpinBox()
        self.spin_margin.setRange(0.0, 100.0)
        self.spin_margin.setValue(0.0)
        self.spin_margin.setSingleStep(5.0)
        self.spin_margin.setSuffix(" mm")
        
        lbl_help = QtWidgets.QLabel(f"<font color='gray'>{translate_text('※モデルの周囲に持たせる「緩衝材や余白」の寸法を指定してください（片側分）。', lang)}</font>")
        lbl_help.setWordWrap(True)

        layout.addRow("", lbl_target)
        layout.addRow(f"<b>{translate_text('モデル単体サイズ:', lang)}</b>", lbl_size)
        layout.addRow(f"<b>{translate_text('モデル単体体積:', lang)}</b>", lbl_volume)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        layout.addRow(translate_text("段ボールへの余白 (全方向):", lang), self.spin_margin)
        layout.addRow("", lbl_help)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        return self.spin_margin.value()

class Tool_MakeJig:
    def GetResources(self):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "jig.png").replace('\\', '/')
        return {
            'Pixmap': icon_path, 
            'MenuText': "必要外包体積の計算", 
            'ToolTip': "モデルを包むために必要な段ボールのサイズと体積(mm3)を計算し、ガイドを配置します"
        }

    def Activated(self):
        lang = get_language()
        doc = FreeCAD.activeDocument()
        if not doc:
            QtWidgets.QMessageBox.warning(None, translate_text("エラー", lang), translate_text("開いているドキュメントがありません。", lang))
            return

        selection = FreeCADGui.Selection.getSelection()
        if not selection:
            QtWidgets.QMessageBox.warning(None, translate_text("エラー", lang), translate_text("モデルが選択されていません。画面上またはツリーから対象オブジェクトを選択してください。", lang))
            return
        
        target_obj = selection[0]
        if not hasattr(target_obj, "Shape") or target_obj.Shape.isNull():
            QtWidgets.QMessageBox.warning(None, translate_text("エラー", lang), translate_text("有効な形状を持たないオブジェクトです。", lang))
            return

        bbox = target_obj.Shape.BoundBox
        size_x = bbox.XMax - bbox.XMin
        size_y = bbox.YMax - bbox.YMin
        size_z = bbox.ZMax - bbox.ZMin
        
        volume_mm3 = size_x * size_y * size_z

        d = JigOptionDialog(target_obj.Label, (size_x, size_y, size_z), volume_mm3)
        if d.exec_() != QtWidgets.QDialog.Accepted: 
            return
            
        margin = d.get_values()
        
        with Progress.ProgressManager() as bar:
            bar.start(title=translate_text("段ボールサイズ箱生成", lang), initial_text=translate_text("位置とサイズを計算中...", lang))
            
            jig_w = size_x + (margin * 2.0)
            jig_l = size_y + (margin * 2.0)
            jig_h = size_z + (margin * 2.0)
            
            bar.update(50, translate_text("3D空間に外包ブロックを作成中...", lang))
            
            enclosing_box = Part.makeBox(jig_w, jig_l, jig_h)
            
            pos_x = bbox.XMin - margin
            pos_y = bbox.YMin - margin
            pos_z = bbox.ZMin - margin
            enclosing_box.translate(FreeCAD.Vector(pos_x, pos_y, pos_z))
            
            bar.update(80, translate_text("表示プロパティを調整中...", lang))
            
            obj_jig = doc.addObject("Part::Feature", f"CardboardBox_for_{target_obj.Name}")
            obj_jig.Shape = enclosing_box
            
            obj_jig.ViewObject.ShapeColor = (0.6, 0.8, 1.0)
            obj_jig.ViewObject.Transparency = 75 
            
            bar.update(100, translate_text("完了", lang))
            doc.recompute()
            FreeCADGui.activeView().fitAll()

        final_volume = jig_w * jig_l * jig_h
        
        if lang == "English":
            title_done = "Calculation Completed"
            msg_done = (
                f"Required cardboard box dimensions (inner size) determined!\n\n"
                f"* Width (X): {jig_w:.1f} mm\n"
                f"* Depth (Y): {jig_l:.1f} mm\n"
                f"* Height (Z): {jig_h:.1f} mm\n\n"
                f"Final Total Volume: {final_volume:,.1f} mm3"
            )
        else:
            title_done = "計算完了"
            msg_done = (
                f"必要となる段ボール（内寸）の大きさが確定しました！\n\n"
                f"■ 幅 (X): {jig_w:.1f} mm\n"
                f"■ 奥行 (Y): {jig_l:.1f} mm\n"
                f"■ 高さ (Z): {jig_h:.1f} mm\n\n"
                f"確定総体積: {final_volume:,.1f} mm3"
            )

        QtWidgets.QMessageBox.information(None, title_done, msg_done)

FreeCADGui.addCommand('Ring_MakeJig', Tool_MakeJig())