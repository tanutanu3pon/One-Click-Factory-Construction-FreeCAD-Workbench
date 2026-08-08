# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part

# Qtの互換性確保（PySide2 / PySide6 両対応）
try:
    from PySide2 import QtWidgets, QtCore
except ImportError:
    from PySide6 import QtWidgets, QtCore

import Core.Progress as Progress

# ==========================================
# ?? 体積・サイズ確認＆余白（マージン）入力窓
# ==========================================
class JigOptionDialog(QtWidgets.QDialog):
    def __init__(self, target_name, size_mm, volume_mm3, parent=None):
        super(JigOptionDialog, self).__init__(parent)
        self.setWindowTitle("梱包体積の計算結果")
        self.resize(400, 260)
        layout = QtWidgets.QFormLayout(self)
        
        lbl_target = QtWidgets.QLabel(f"<b>対象モデル:</b> {target_name}")
        
        info_text = (
            f"幅 (X): {size_mm[0]:.2f} mm<br>"
            f"奥行 (Y): {size_mm[1]:.2f} mm<br>"
            f"高さ (Z): {size_mm[2]:.2f} mm"
        )
        lbl_size = QtWidgets.QLabel(info_text)
        lbl_volume = QtWidgets.QLabel(f"<font color='#2e7d32' size='4'><b>ジャスト体積: {volume_mm3:,.2f} mm3</b></font>")
        
        # 段ボールに必要な「余白」を入れる欄
        self.spin_margin = QtWidgets.QDoubleSpinBox()
        self.spin_margin.setRange(0.0, 100.0)
        self.spin_margin.setValue(0.0)
        self.spin_margin.setSingleStep(5.0)
        self.spin_margin.setSuffix(" mm")
        
        lbl_help = QtWidgets.QLabel("<font color='gray'>※モデルの周囲に持たせる「緩衝材や余白」の寸法を指定してください（片側分）。</font>")
        lbl_help.setWordWrap(True)

        layout.addRow("", lbl_target)
        layout.addRow("<b>モデル単体サイズ:</b>", lbl_size)
        layout.addRow("<b>モデル単体体積:</b>", lbl_volume)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        layout.addRow("段ボールへの余白 (全方向):", self.spin_margin)
        layout.addRow("", lbl_help)
        layout.addRow(QtWidgets.QLabel("<hr>"))
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.button(QtWidgets.QDialogButtonBox.Ok).setText("段ボール箱を生成")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_values(self):
        return self.spin_margin.value()


# ==========================================
# ?? ツール本体（外包体積計算＆包囲ブロック生成）
# ==========================================
class Tool_MakeJig:
    def GetResources(self):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "jig.png").replace('\\', '/')
        return {
            'Pixmap': icon_path, 
            'MenuText': "必要外包体積の計算", 
            'ToolTip': "モデルを包むために必要な段ボールのサイズと体積(mm3)を計算し、ガイドを配置します"
        }

    def Activated(self):
        doc = FreeCAD.activeDocument()
        if not doc:
            QtWidgets.QMessageBox.warning(None, "エラー", "開いているドキュメントがありません。")
            return

        # 1. 操作者がモデルをクリック（選択）したのを取得
        selection = FreeCADGui.Selection.getSelection()
        if not selection:
            QtWidgets.QMessageBox.warning(None, "エラー", "モデルが選択されていません。画面上またはツリーから対象オブジェクトを選択してください。")
            return
        
        target_obj = selection[0]
        if not hasattr(target_obj, "Shape") or target_obj.Shape.isNull():
            QtWidgets.QMessageBox.warning(None, "エラー", "有効な形状を持たないオブジェクトです。")
            return

        # 2. モデル全体のバウンディングボックス（境界箱）を取得
        bbox = target_obj.Shape.BoundBox
        size_x = bbox.XMax - bbox.XMin
        size_y = bbox.YMax - bbox.YMin
        size_z = bbox.ZMax - bbox.ZMin
        
        # 3. 体積の計算 (mm3 単位)
        volume_mm3 = size_x * size_y * size_z

        # 4. ダイアログを表示して計算結果を確認・余白を入力
        d = JigOptionDialog(target_obj.Label, (size_x, size_y, size_z), volume_mm3)
        if d.exec_() != QtWidgets.QDialog.Accepted: 
            return
            
        margin = d.get_values()
        
        # 5. 段ボール箱（包囲ブロック）の生成処理へ
        bar = Progress.ProgressManager()
        bar.start(title="段ボールサイズ箱生成", initial_text="位置とサイズを計算中...")
        
        # 元のサイズにマージン（両側分として2倍）を加算
        jig_w = size_x + (margin * 2.0)
        jig_l = size_y + (margin * 2.0)
        jig_h = size_z + (margin * 2.0)
        
        bar.update(50, "3D空間に外包ブロックを作成中...")
        
        # 包むための直方体を生成
        enclosing_box = Part.makeBox(jig_w, jig_l, jig_h)
        
        # 配置位置の計算（マージン分だけ最小座標から外側にずらす）
        pos_x = bbox.XMin - margin
        pos_y = bbox.YMin - margin
        pos_z = bbox.ZMin - margin
        enclosing_box.translate(FreeCAD.Vector(pos_x, pos_y, pos_z))
        
        bar.update(80, "表示プロパティを調整中...")
        
        # FreeCADへ出力
        obj_jig = doc.addObject("Part::Feature", f"CardboardBox_for_{target_obj.Name}")
        obj_jig.Shape = enclosing_box
        
        # 見栄えの調整：透明度75%の薄い水色に設定
        obj_jig.ViewObject.ShapeColor = (0.6, 0.8, 1.0)
        obj_jig.ViewObject.Transparency = 75 
        
        bar.update(100, "完了")
        bar.close()
        
        doc.recompute()
        FreeCADGui.activeView().fitAll()

        # 最終確定した段ボール内寸のレポート表示
        final_volume = jig_w * jig_l * jig_h
        QtWidgets.QMessageBox.information(
            None,
            "計算完了",
            f"必要となる段ボール（内寸）の大きさが確定しました！\n\n"
            f"■ 幅 (X): {jig_w:.1f} mm\n"
            f"■ 奥行 (Y): {jig_l:.1f} mm\n"
            f"■ 高さ (Z): {jig_h:.1f} mm\n\n"
            f"確定総体積: {final_volume:,.1f} mm3"
        )

# コマンドの登録（ツールバーアイコン用）
FreeCADGui.addCommand('Ring_MakeJig', Tool_MakeJig())