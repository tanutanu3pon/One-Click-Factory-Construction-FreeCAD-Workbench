# -*- coding: utf-8 -*-
import os
import sys
import math
import platform
import subprocess
import FreeCAD
import FreeCADGui
import Part
import Draft

# 【修正】絶対インポートで安全にCoreモジュールを読み込む
from Core.QtCompat import QtWidgets, QtGui, QtCore
import Core.Progress as Progress
from Core.Controller import TranslatedDialog, translate_text
from Core.Language import get_language

_FONT_SCAN_CACHE = None

def get_bundled_font_dir():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    font_dir = os.path.join(base_dir, "fonts").replace('\\', '/')
    if not os.path.exists(font_dir):
        try: os.makedirs(font_dir, exist_ok=True)
        except Exception: pass
    return font_dir

def parse_font_info_fast(file_name):
    raw_name = os.path.splitext(file_name)[0]
    style_keywords = [
        ("bolditalic", "Bold Italic"), ("bold_italic", "Bold Italic"), ("boldoblique", "Bold Italic"),
        ("extrabold", "Extra Bold"), ("semibold", "Semi Bold"), ("extralight", "Extra Light"),
        ("bold", "Bold"), ("italic", "Italic"), ("oblique", "Italic"), ("medium", "Medium"),
        ("light", "Light"), ("thin", "Thin"), ("black", "Black"), ("heavy", "Heavy"), ("regular", "Regular")
    ]
    parts = raw_name.replace('_', ' ').split('-')
    family_name = parts[0].strip()
    style_name = "Regular"
    if len(parts) > 1:
        possible_style = parts[1].lower().strip()
        for kw, label in style_keywords:
            if kw in possible_style:
                style_name = label
                break
    else:
        fn_lower = raw_name.lower()
        for kw, label in style_keywords:
            if kw in fn_lower:
                style_name = label
                break

    family_name = family_name.replace("VariableFont wght", "").replace("VariableFont", "").strip()
    if not family_name: family_name = raw_name
    return family_name, style_name

def scan_and_auto_classify_fonts(force_refresh=False):
    global _FONT_SCAN_CACHE
    if _FONT_SCAN_CACHE is not None and not force_refresh:
        return _FONT_SCAN_CACHE

    font_dir = get_bundled_font_dir()
    categorized = {
        0: {}, # 日本語
        1: {}, # 英語・汎用
        2: {}, # 奇抜・デザイン
        3: {}, # 特殊文字
        4: {}, # その他
        5: {}  # すべて
    }
    
    if os.path.exists(font_dir):
        for root, dirs, files in os.walk(font_dir):
            for file in files:
                if file.lower().endswith(('.ttf', '.otf')):
                    file_path = os.path.join(root, file).replace('\\', '/')
                    family_name, style_name = parse_font_info_fast(file)
                    text = (file_path + " " + family_name + " " + file).lower()

                    target_cats = []

                    jp_keywords = ["jp", "japanese", "gothic", "mincho", "meiryo", "msgothic", "msmincho", "yu", "hiragino", "noto sans jp", "noto serif jp", "mplus", "kosugi", "sawarabi", "shippori", "zen", "biz", "reggae", "potta", "dela", "rampart", "kaisei", "yuji", "klee", "mochiy", "yusei", "train", "stick", "dotgothic", "kiwi", "hachi", "rocknroll", "chokurui", "aoyagi", "kouzan"]
                    novelty_keywords = ["blood", "drip", "horror", "creep", "zombie", "monster", "vampire", "halloween", "scary", "rubik", "3d", "iso", "stencil", "black ops", "blackops", "train", "rampart", "reggae", "potta", "rocknroll", "chokurui", "comic", "cartoon", "pop", "fancy", "novelty", "decorative", "circus", "pixel", "arcade", "retro", "graffiti", "gothic_one", "cherry"]
                    symbol_keywords = ["symbol", "braille", "emoji", "icon", "dingbat", "math", "music", "sign", "wingdings", "webdings", "font awesome", "nerd", "dots", "material"]
                    other_lang_keywords = ["chinese", "zh-", "zh_", "sc", "tc", "hans", "hant", "noto sans sc", "noto sans tc", "hk", "kr", "korean", "hangul", "noto sans kr", "arabic", "ar", "noto sans arabic", "noto kufi", "noto naskh", "russian", "cyrillic", "ru", "noto sans cyrillic", "thai", "hebrew", "devanagari", "bengali", "tamil"]

                    is_jp = any(k in text for k in jp_keywords)
                    is_novelty = any(k in text for k in novelty_keywords)
                    is_symbol = any(k in text for k in symbol_keywords)
                    is_other_lang = any(k in text for k in other_lang_keywords)

                    if is_jp: target_cats.append(0)
                    if is_novelty: target_cats.append(2)
                    if is_symbol: target_cats.append(3)
                    elif is_other_lang: target_cats.append(4)
                    elif not is_jp and not is_novelty: target_cats.append(1)

                    target_cats.append(5)

                    for cat_idx in target_cats:
                        if family_name not in categorized[cat_idx]:
                            categorized[cat_idx][family_name] = {}
                        style_key = style_name
                        if style_key in categorized[cat_idx][family_name]:
                            style_key = f"{style_name} [{file}]"
                        categorized[cat_idx][family_name][style_key] = file_path

    _FONT_SCAN_CACHE = categorized
    return _FONT_SCAN_CACHE

def create_solid_from_shape(shape, height):
    if shape is None or shape.isNull(): return None
    try:
        ext = shape.extrude(FreeCAD.Vector(0, 0, height))
        if ext and ext.isValid() and ext.ShapeType == "Solid" and ext.isClosed():
            return ext
    except Exception: pass

    try:
        cleaned_faces = []
        if hasattr(shape, 'Faces') and shape.Faces:
            for f in shape.Faces:
                try: cleaned_faces.append(f.makeOffset2D(0.005, 0))
                except Exception: cleaned_faces.append(f)
        elif hasattr(shape, 'Wires') and shape.Wires:
            for w in shape.Wires:
                try: cleaned_faces.append(Part.Face(w).makeOffset2D(0.005, 0))
                except Exception: pass

        if cleaned_faces:
            comp_2d = cleaned_faces[0]
            for cf in cleaned_faces[1:]:
                try: comp_2d = comp_2d.fuse(cf)
                except Exception: pass
            ext = comp_2d.extrude(FreeCAD.Vector(0, 0, height))
            if ext and ext.isValid(): return ext
    except Exception: pass

    solids = []
    faces = shape.Faces if hasattr(shape, 'Faces') and shape.Faces else []
    if not faces and hasattr(shape, 'Wires') and shape.Wires:
        try: faces = [Part.Face(shape.Wires)]
        except Exception: pass

    for f in faces:
        try:
            ext = f.extrude(FreeCAD.Vector(0, 0, height))
            if ext.ShapeType != "Solid" or not ext.isClosed():
                solids.append(Part.makeSolid(Part.makeShell(ext.Faces)))
            else: solids.append(ext)
        except Exception:
            try: solids.append(f.extrude(FreeCAD.Vector(0, 0, height)))
            except Exception: pass

    if solids:
        compound = solids[0]
        for s in solids[1:]:
            try: compound = compound.fuse(s)
            except Exception: pass
        return compound

    try: return shape.extrude(FreeCAD.Vector(0, 0, height))
    except Exception: return None

def make_filled_face_from_shape(shape_2d):
    faces = []
    if hasattr(shape_2d, 'Faces') and shape_2d.Faces:
        for f in shape_2d.Faces:
            try: faces.append(Part.Face(f.OuterWire))
            except Exception: faces.append(f)
    elif hasattr(shape_2d, 'Wires') and shape_2d.Wires:
        for w in shape_2d.Wires:
            try: faces.append(Part.Face(w))
            except Exception: pass
    if not faces: return None
    comp = faces[0]
    for f in faces[1:]:
        try: comp = comp.fuse(f)
        except Exception: pass
    return comp

# 【修正】TranslatedDialog を継承させて自動翻訳を機能させる
class Text3DDialog(TranslatedDialog):
    def __init__(self, parent=None):
        super(Text3DDialog, self).__init__(parent)
        self.setWindowTitle("3D文字・銘板の作成")
        self.resize(760, 530)
        self.categorized_fonts = {}
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        content_layout = QtWidgets.QHBoxLayout()
        content_layout.setSpacing(12)

        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        text_group = QtWidgets.QGroupBox("テキスト設定")
        text_layout = QtWidgets.QVBoxLayout(text_group)

        self.txt_input = QtWidgets.QPlainTextEdit()
        self.txt_input.setPlainText("FreeCAD 3D文字\nSample Line 2")
        self.txt_input.setMaximumHeight(65)
        text_layout.addWidget(self.txt_input)

        align_layout = QtWidgets.QHBoxLayout()
        align_layout.addWidget(QtWidgets.QLabel("配置揃え:"))
        self.combo_align = QtWidgets.QComboBox()
        self.combo_align.addItems(["中央揃え (Center)", "左揃え (Left)", "右揃え (Right)"])
        align_layout.addWidget(self.combo_align, 1)
        text_layout.addLayout(align_layout)
        left_layout.addWidget(text_group)

        font_group = QtWidgets.QGroupBox("フォント設定")
        font_layout = QtWidgets.QVBoxLayout(font_group)
        form_sub = QtWidgets.QFormLayout()

        self.combo_lang = QtWidgets.QComboBox()
        self.combo_lang.addItems(["日本語 (Japanese)", "英語・汎用 (English/Latin)", "奇抜・デザイン (Novelty/Fancy)", "特殊文字 (Symbols/Special)", "その他 (Other)", "すべて (All)"])
        
        self.combo_family = QtWidgets.QComboBox()
        self.combo_style = QtWidgets.QComboBox()

        self.lbl_font_path = QtWidgets.QLabel()
        self.lbl_font_path.setStyleSheet("color: #666; font-size: 8pt;")
        self.lbl_font_path.setWordWrap(True)

        btn_open_folder = QtWidgets.QPushButton("フォルダを開く")
        btn_refresh = QtWidgets.QPushButton("更新")
        btn_refresh.clicked.connect(lambda: self.refresh_font_data(force=True))
        btn_open_folder.clicked.connect(self.open_font_folder)

        font_btn_layout = QtWidgets.QHBoxLayout()
        font_btn_layout.addWidget(self.combo_family, 1)
        font_btn_layout.addWidget(btn_open_folder)
        font_btn_layout.addWidget(btn_refresh)

        form_sub.addRow("カテゴリ:", self.combo_lang)
        form_sub.addRow("フォント名:", font_btn_layout)
        form_sub.addRow("スタイル:", self.combo_style)
        form_sub.addRow("ファイル:", self.lbl_font_path)
        font_layout.addLayout(form_sub)

        font_layout.addWidget(QtWidgets.QLabel("<b>【プレビュー】</b>"))
        self.lbl_font_sample = QtWidgets.QLabel("FreeCAD 3D文字 Sample")
        self.lbl_font_sample.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_font_sample.setMinimumHeight(65)
        self.lbl_font_sample.setStyleSheet("QLabel { background-color: #ffffff; border: 1px solid #b0b0b0; border-radius: 4px; padding: 6px; color: #111111; }")
        font_layout.addWidget(self.lbl_font_sample)
        left_layout.addWidget(font_group)

        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        param_group = QtWidgets.QGroupBox("3D形状パラメータ")
        param_layout = QtWidgets.QFormLayout(param_group)

        self.spin_size = QtWidgets.QDoubleSpinBox()
        self.spin_size.setRange(1.0, 1000.0)
        self.spin_size.setValue(20.0)
        self.spin_size.setSuffix(" mm")

        self.spin_height = QtWidgets.QDoubleSpinBox()
        self.spin_height.setRange(0.1, 500.0)
        self.spin_height.setValue(5.0)
        self.spin_height.setSuffix(" mm")

        self.spin_tracking = QtWidgets.QDoubleSpinBox()
        self.spin_tracking.setRange(-10.0, 100.0)
        self.spin_tracking.setValue(0.0)
        self.spin_tracking.setSuffix(" mm")

        param_layout.addRow("文字の高さ (Size):", self.spin_size)
        param_layout.addRow("押し出し厚み (Depth):", self.spin_height)
        param_layout.addRow("文字間隔 (Tracking):", self.spin_tracking)
        right_layout.addWidget(param_group)

        base_group = QtWidgets.QGroupBox("土台 (プレート) 設定")
        base_layout = QtWidgets.QFormLayout(base_group)

        self.chk_add_base = QtWidgets.QCheckBox("台座プレートを作成する")
        self.chk_add_base.setChecked(True)

        self.combo_base_shape = QtWidgets.QComboBox()
        self.combo_base_shape.addItems(["長方形 (Rectangle)", "楕円 (Ellipse)", "円 (Circle)", "ダイカット / モコモコ (Die-cut)"])
        self.combo_base_shape.currentIndexChanged.connect(self.update_radius_state)

        self.spin_base_radius = QtWidgets.QDoubleSpinBox()
        self.spin_base_radius.setRange(0.0, 100.0)
        self.spin_base_radius.setValue(2.0)
        self.spin_base_radius.setSuffix(" mm")

        self.combo_base_mode = QtWidgets.QComboBox()
        self.combo_base_mode.addItems(["文字を上に載せる (凸 / 浮き彫り)", "文字をプレートに掘り込む (凹 / 彫り込み)"])

        self.spin_base_padding = QtWidgets.QDoubleSpinBox()
        self.spin_base_padding.setRange(0.0, 100.0)
        self.spin_base_padding.setValue(5.0)
        self.spin_base_padding.setSuffix(" mm")

        self.spin_base_thick = QtWidgets.QDoubleSpinBox()
        self.spin_base_thick.setRange(0.1, 100.0)
        self.spin_base_thick.setValue(2.0)
        self.spin_base_thick.setSuffix(" mm")

        self.combo_holes = QtWidgets.QComboBox()
        self.combo_holes.addItems(["なし (None)", "左側に1つ (キーホルダー用)", "左右に2つ (ネジ留め用)", "四隅に4つ (プレート固定用)"])
        self.combo_holes.currentIndexChanged.connect(self.update_hole_state)

        self.spin_hole_dia = QtWidgets.QDoubleSpinBox()
        self.spin_hole_dia.setRange(1.0, 30.0)
        self.spin_hole_dia.setValue(3.0)
        self.spin_hole_dia.setSuffix(" mm")
        self.spin_hole_dia.setEnabled(False)

        base_layout.addRow(self.chk_add_base)
        base_layout.addRow("プレート形状:", self.combo_base_shape)
        base_layout.addRow("角の丸み (Radius):", self.spin_base_radius)
        base_layout.addRow("文字加工タイプ:", self.combo_base_mode)
        base_layout.addRow("余白 (Padding):", self.spin_base_padding)
        base_layout.addRow("プレート厚み:", self.spin_base_thick)
        base_layout.addRow("取付穴:", self.combo_holes)
        base_layout.addRow("穴の直径:", self.spin_hole_dia)
        right_layout.addWidget(base_group)

        content_layout.addWidget(left_widget, 1)
        content_layout.addWidget(right_widget, 1)
        main_layout.addLayout(content_layout)

        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        main_layout.addWidget(btn_box)

        self.combo_lang.currentIndexChanged.connect(self.update_family_dropdown)
        self.combo_family.currentIndexChanged.connect(self.update_style_dropdown)
        self.combo_style.currentIndexChanged.connect(self.update_font_preview)
        self.txt_input.textChanged.connect(self.update_font_preview)

        self.refresh_font_data(force=False)

    def update_radius_state(self):
        self.spin_base_radius.setEnabled(self.combo_base_shape.currentIndex() == 0)

    def update_hole_state(self):
        self.spin_hole_dia.setEnabled(self.combo_holes.currentIndex() > 0)

    def refresh_font_data(self, force=False):
        self.categorized_fonts = scan_and_auto_classify_fonts(force_refresh=force)
        self.update_family_dropdown()

    def update_family_dropdown(self):
        self.combo_family.blockSignals(True)
        self.combo_family.clear()
        
        selected_cat_idx = self.combo_lang.currentIndex()
        families_dict = self.categorized_fonts.get(selected_cat_idx, {})
        family_names = sorted(list(families_dict.keys()))

        if not family_names:
            if selected_cat_idx != 5:
                all_fonts = self.categorized_fonts.get(5, {})
                if all_fonts:
                    self.combo_family.addItem("※ 該当カテゴリなし")
                    self.combo_family.setEnabled(False)
                    self.combo_family.blockSignals(False)
                    self.update_style_dropdown()
                    return

            self.combo_family.addItem("※ フォント(.ttf)が見つかりません")
            self.combo_family.setEnabled(False)
        else:
            self.combo_family.setEnabled(True)
            self.combo_family.addItems(family_names)

        self.combo_family.blockSignals(False)
        self.update_style_dropdown()

    def update_style_dropdown(self):
        self.combo_style.blockSignals(True)
        self.combo_style.clear()
        
        selected_cat_idx = self.combo_lang.currentIndex()
        selected_family = self.combo_family.currentText()
        
        styles_dict = self.categorized_fonts.get(selected_cat_idx, {}).get(selected_family, {})
        style_names = sorted(list(styles_dict.keys()))

        if not style_names or not self.combo_family.isEnabled():
            self.combo_style.addItem("※ 選択不可")
            self.combo_style.setEnabled(False)
        else:
            self.combo_style.setEnabled(True)
            self.combo_style.addItems(style_names)
            
            default_idx = 0
            for i, st in enumerate(style_names):
                if "regular" in st.lower():
                    default_idx = i
                    break
            self.combo_style.setCurrentIndex(default_idx)

        self.combo_style.blockSignals(False)
        self.update_font_preview()

    def update_font_preview(self):
        if not hasattr(self, 'lbl_font_path'): return
            
        if not self.combo_style.isEnabled():
            self.lbl_font_path.setText("フォント未検出")
            self.lbl_font_sample.setText("（サンプル不可）")
            self.lbl_font_sample.setFont(QtGui.QFont())
            return
        
        selected_cat_idx = self.combo_lang.currentIndex()
        selected_family = self.combo_family.currentText()
        selected_style = self.combo_style.currentText()
        
        font_path = self.categorized_fonts.get(selected_cat_idx, {}).get(selected_family, {}).get(selected_style, "")
        self.lbl_font_path.setText(font_path if font_path else "未選択")

        display_preview = self.txt_input.toPlainText() or "FreeCAD"

        if font_path and os.path.exists(font_path):
            font_id = QtGui.QFontDatabase.addApplicationFont(font_path)
            if font_id >= 0:
                families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    sample_font = QtGui.QFont(families[0], 18)
                    self.lbl_font_sample.setFont(sample_font)
                    self.lbl_font_sample.setText(display_preview)
                    return

        self.lbl_font_sample.setFont(QtGui.QFont())
        self.lbl_font_sample.setText("（エラー）")

    def open_font_folder(self):
        lang = get_language()
        font_dir = get_bundled_font_dir()
        system = platform.system()
        try:
            if system == "Windows": os.startfile(font_dir)
            elif system == "Darwin": subprocess.Popen(["open", font_dir])
            else: subprocess.Popen(["xdg-open", font_dir])
        except Exception as e:
            err_title = "Error" if lang == "English" else "エラー"
            err_msg = f"Could not open folder:\n{str(e)}" if lang == "English" else f"フォルダを開けませんでした:\n{str(e)}"
            QtWidgets.QMessageBox.warning(self, err_title, err_msg)

    def get_values(self):
        selected_cat_idx = self.combo_lang.currentIndex()
        selected_family = self.combo_family.currentText()
        selected_style = self.combo_style.currentText()
        
        font_path = self.categorized_fonts.get(selected_cat_idx, {}).get(selected_family, {}).get(selected_style, "")
        
        return {
            'text': self.txt_input.toPlainText(),
            'align_type': self.combo_align.currentIndex(),
            'font_path': font_path,
            'size': self.spin_size.value(),
            'height': self.spin_height.value(),
            'tracking': self.spin_tracking.value(),
            'add_base': self.chk_add_base.isChecked(),
            'base_shape_type': self.combo_base_shape.currentIndex(),
            'base_radius': self.spin_base_radius.value(),
            'base_mode': self.combo_base_mode.currentIndex(),
            'base_padding': self.spin_base_padding.value(),
            'base_thick': self.spin_base_thick.value(),
            'hole_type': self.combo_holes.currentIndex(),
            'hole_dia': self.spin_hole_dia.value(),
        }

class Tool_Make3DText:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "3dword.png").replace('\\', '/')
        return {
            'Pixmap': icon_path, 
            'MenuText': "3D文字の作成", 
            'ToolTip': "3D文字・キーホルダー・銘板を作成します"
        }

    def Activated(self):
        lang = get_language()
        doc = FreeCAD.activeDocument()
        if doc is None:
            doc = FreeCAD.newDocument("Text3D_Model")

        dlg = Text3DDialog(FreeCADGui.getMainWindow())
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        params = dlg.get_values()
        text = params['text']
        align_type = params['align_type']
        font_path = params['font_path']
        size = params['size']
        height = params['height']
        tracking = params['tracking']
        add_base = params['add_base']
        base_shape_type = params['base_shape_type']
        base_radius = params['base_radius']
        base_mode = params['base_mode']
        base_padding = params['base_padding']
        base_thick = params['base_thick']
        hole_type = params['hole_type']
        hole_dia = params['hole_dia']

        if not text.strip() or not font_path or not os.path.exists(font_path):
            QtWidgets.QMessageBox.warning(None, translate_text("警告", lang), translate_text("テキストまたはフォントが無効です。", lang))
            return

        if add_base and base_shape_type == 3:
            min_safe_tracking = max(2.0, size * 0.08)
            if tracking < min_safe_tracking:
                tracking = min_safe_tracking

        with Progress.ProgressManager() as pm:
            pm.start(translate_text("3D文字の生成中", lang), translate_text("文字データを解析中...", lang))

            doc.openTransaction("3D Text Creation")
            
            try:
                lines = text.split('\n')
                total_chars = sum([len(line.strip()) for line in lines if line.strip()])
                if total_chars == 0: total_chars = 1
                processed_chars = 0

                all_line_data = []

                for line in lines:
                    if not line: continue

                    line_solids = []
                    line_2d_faces = []
                    x_cursor = 0.0

                    for ch in line:
                        if ch in [' ', ' ', '\t']:
                            x_cursor += (size * 0.4) + tracking
                            continue

                        processed_chars += 1
                        pct = int(10 + (processed_chars / total_chars) * 40)
                        msg_char = f"Creating character: '{ch}'" if lang == "English" else f"文字を作成中: '{ch}'"
                        pm.update(pct, msg_char)

                        if hasattr(Draft, "make_shape_string"):
                            ss_c = Draft.make_shape_string(String=ch, FontFile=font_path, Size=size, Tracking=0)
                        else:
                            ss_c = Draft.makeShapeString(ch, font_path, size, 0)

                        if ss_c and ss_c.Shape and not ss_c.Shape.isNull():
                            c_shape = ss_c.Shape.copy()
                            cb = c_shape.BoundBox
                            c_w = cb.XMax - cb.XMin

                            trans_v = FreeCAD.Vector(x_cursor - cb.XMin, 0, 0)
                            c_shape.translate(trans_v)

                            c_solid = create_solid_from_shape(c_shape, height)
                            c_2d_filled = make_filled_face_from_shape(c_shape)

                            if c_solid: line_solids.append(c_solid)
                            if c_2d_filled: line_2d_faces.append(c_2d_filled)

                            x_cursor += c_w + (size * 0.1) + tracking

                        doc.removeObject(ss_c.Name)

                    if line_solids:
                        all_line_data.append({
                            'solids': line_solids,
                            'faces_2d': line_2d_faces,
                            'width': x_cursor
                        })

                if not all_line_data:
                    QtWidgets.QMessageBox.warning(None, translate_text("エラー", lang), translate_text("3D文字を生成できませんでした。", lang))
                    doc.abortTransaction()
                    return

                pm.update(55, translate_text("レイアウト位置を調整中...", lang))
                max_w = max([ld['width'] for ld in all_line_data])
                current_y = 0.0
                line_spacing = size * 1.3

                final_solids = []
                final_2d_faces = []

                for ld in all_line_data:
                    l_width = ld['width']
                    if align_type == 0: offset_x = -l_width / 2.0
                    elif align_type == 2: offset_x = (max_w / 2.0) - l_width
                    else: offset_x = -max_w / 2.0

                    shift_v = FreeCAD.Vector(offset_x, current_y, 0)

                    for s in ld['solids']:
                        s_cp = s.copy()
                        s_cp.translate(shift_v)
                        final_solids.append(s_cp)

                    for f2d in ld['faces_2d']:
                        f2d_cp = f2d.copy()
                        f2d_cp.translate(shift_v)
                        final_2d_faces.append(f2d_cp)

                    current_y -= line_spacing

                text_compound = final_solids[0]
                for s in final_solids[1:]:
                    try: text_compound = text_compound.fuse(s)
                    except Exception: pass

                final_shape = text_compound

                if add_base:
                    pm.update(70, translate_text("土台プレートを計算中...", lang))
                    bbox = text_compound.BoundBox
                    
                    p_min_x = bbox.XMin - base_padding
                    p_max_x = bbox.XMax + base_padding
                    p_min_y = bbox.YMin - base_padding
                    p_max_y = bbox.YMax + base_padding

                    c_x = (p_min_x + p_max_x) / 2.0
                    c_y = (p_min_y + p_max_y) / 2.0
                    half_w = (p_max_x - p_min_x) / 2.0
                    half_h = (p_max_y - p_min_y) / 2.0

                    if base_shape_type == 0:
                        width = half_w * 2.0
                        length = half_h * 2.0
                        base_box = Part.makeBox(width, length, base_thick)
                        base_box.translate(FreeCAD.Vector(p_min_x, p_min_y, -base_thick))

                        if base_radius > 0:
                            max_rad = min(width, length) / 2.0 - 0.01
                            r = min(base_radius, max_rad)
                            if r > 0:
                                edges_to_fillet = []
                                for e in base_box.Edges:
                                    v1, v2 = e.Vertexes[0].Point, e.Vertexes[-1].Point
                                    if abs(v1.x - v2.x) < 1e-4 and abs(v1.y - v2.y) < 1e-4:
                                        edges_to_fillet.append(e)
                                if edges_to_fillet:
                                    try: base_box = base_box.makeFillet(r, edges_to_fillet)
                                    except Exception: pass

                    elif base_shape_type == 1:
                        a = half_w * math.sqrt(2.0)
                        b = half_h * math.sqrt(2.0)
                        if a >= b:
                            ellipse_geom = Part.Ellipse(FreeCAD.Vector(c_x, c_y, -base_thick), a, b)
                            wire = Part.Wire([ellipse_geom.toShape()])
                        else:
                            ellipse_geom = Part.Ellipse(FreeCAD.Vector(0, 0, 0), b, a)
                            shape_e = ellipse_geom.toShape()
                            shape_e.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), 90)
                            shape_e.translate(FreeCAD.Vector(c_x, c_y, -base_thick))
                            wire = Part.Wire([shape_e])
                        face = Part.Face(wire)
                        base_box = face.extrude(FreeCAD.Vector(0, 0, base_thick))

                    elif base_shape_type == 2:
                        radius = math.sqrt(half_w**2 + half_h**2)
                        base_box = Part.makeCylinder(radius, base_thick, FreeCAD.Vector(c_x, c_y, -base_thick))

                    elif base_shape_type == 3:
                        pm.update(75, translate_text("モコモコ輪郭(2Dオフセット)を生成中...", lang))
                        effective_pad = max(base_padding, size * 0.25) + (size * 0.15)
                        
                        raw_offsets = []
                        for f2d in final_2d_faces:
                            try:
                                off_shape = f2d.makeOffset2D(effective_pad, 0)
                                raw_offsets.append(off_shape)
                            except Exception: pass

                        if raw_offsets:
                            pm.update(80, translate_text("モコモコ輪郭の隙間を滑らかに結合中...", lang))
                            merged_2d = raw_offsets[0]
                            for ro in raw_offsets[1:]:
                                try: merged_2d = merged_2d.fuse(ro)
                                except Exception: pass

                            try:
                                bridge_off = merged_2d.makeOffset2D(size * 0.2, 0)
                                merged_2d = bridge_off.makeOffset2D(-size * 0.2, 0)
                            except Exception: pass

                            clean_faces = []
                            if hasattr(merged_2d, 'Faces') and merged_2d.Faces:
                                for f in merged_2d.Faces:
                                    try: clean_faces.append(Part.Face(f.OuterWire))
                                    except Exception: clean_faces.append(f)
                            elif hasattr(merged_2d, 'Wires') and merged_2d.Wires:
                                for w in merged_2d.Wires:
                                    try: clean_faces.append(Part.Face(w))
                                    except Exception: pass

                            if clean_faces:
                                unified_2d = clean_faces[0]
                                for cf in clean_faces[1:]:
                                    try: unified_2d = unified_2d.fuse(cf)
                                    except Exception: pass
                                
                                unified_2d.translate(FreeCAD.Vector(0, 0, -base_thick))
                                base_box = unified_2d.extrude(FreeCAD.Vector(0, 0, base_thick))
                            else:
                                width = half_w * 2.0
                                length = half_h * 2.0
                                base_box = Part.makeBox(width, length, base_thick)
                                base_box.translate(FreeCAD.Vector(p_min_x, p_min_y, -base_thick))
                        else:
                            width = half_w * 2.0
                            length = half_h * 2.0
                            base_box = Part.makeBox(width, length, base_thick)
                            base_box.translate(FreeCAD.Vector(p_min_x, p_min_y, -base_thick))

                    pm.update(85, translate_text("文字とプレートを合成中...", lang))
                    if base_mode == 0:
                        try: final_shape = text_compound.fuse(base_box)
                        except Exception: final_shape = base_box.fuse(text_compound)
                    else:
                        text_cut = text_compound.copy()
                        text_cut.translate(FreeCAD.Vector(0, 0, -height + 0.01))
                        final_shape = base_box.cut(text_cut)

                    hole_shapes = []
                    edge_margin = (hole_dia / 2.0) + 3.0

                    if hole_type == 1:
                        if base_shape_type in [0, 3]: hx = p_min_x + edge_margin
                        elif base_shape_type == 1: hx = c_x - a + edge_margin
                        else: hx = c_x - radius + edge_margin
                            
                        cyl = Part.makeCylinder(hole_dia / 2.0, base_thick + height + 2.0, FreeCAD.Vector(hx, c_y, -base_thick - 1.0))
                        hole_shapes.append(cyl)

                    elif hole_type == 2:
                        if base_shape_type in [0, 3]:
                            hx_l = p_min_x + edge_margin
                            hx_r = p_max_x - edge_margin
                        elif base_shape_type == 1:
                            hx_l = c_x - a + edge_margin
                            hx_r = c_x + a - edge_margin
                        else:
                            hx_l = c_x - radius + edge_margin
                            hx_r = c_x + radius - edge_margin

                        cyl_l = Part.makeCylinder(hole_dia / 2.0, base_thick + height + 2.0, FreeCAD.Vector(hx_l, c_y, -base_thick - 1.0))
                        cyl_r = Part.makeCylinder(hole_dia / 2.0, base_thick + height + 2.0, FreeCAD.Vector(hx_r, c_y, -base_thick - 1.0))
                        hole_shapes.extend([cyl_l, cyl_r])

                    elif hole_type == 3:
                        if base_shape_type in [0, 3]:
                            x_l = p_min_x + edge_margin
                            x_r = p_max_x - edge_margin
                            y_b = p_min_y + edge_margin
                            y_t = p_max_y - edge_margin
                        else:
                            r_offset = (a if base_shape_type == 1 else radius) * 0.65
                            r_offset_y = (b if base_shape_type == 1 else radius) * 0.65
                            x_l, x_r = c_x - r_offset, c_x + r_offset
                            y_b, y_t = c_y - r_offset_y, c_y + r_offset_y

                        corners = [(x_l, y_b), (x_r, y_b), (x_l, y_t), (x_r, y_t)]
                        for cx, cy in corners:
                            cyl = Part.makeCylinder(hole_dia / 2.0, base_thick + height + 2.0, FreeCAD.Vector(cx, cy, -base_thick - 1.0))
                            hole_shapes.append(cyl)

                    if hole_shapes:
                        pm.update(92, translate_text("取付穴をあけています...", lang))
                        hole_compound = hole_shapes[0]
                        for hs in hole_shapes[1:]:
                            hole_compound = hole_compound.fuse(hs)
                        final_shape = final_shape.cut(hole_compound)

                pm.update(98, translate_text("3Dモデルを配置中...", lang))
                text_obj = doc.addObject("Part::Feature", "3D_Text")
                text_obj.Shape = final_shape
                text_obj.ViewObject.ShapeColor = (0.2, 0.6, 0.9) 

                doc.commitTransaction()
                doc.recompute()
                FreeCADGui.SendMsgToActiveView("ViewFit")
                pm.update(100, translate_text("完了", lang))

            except Exception as e:
                doc.abortTransaction()
                err_title = "Error" if lang == "English" else "エラー"
                err_msg = f"An error occurred while generating 3D text:\n{str(e)}" if lang == "English" else f"3D文字の生成中にエラーが発生しました:\n{str(e)}"
                QtWidgets.QMessageBox.critical(None, err_title, err_msg)

FreeCADGui.addCommand('Ring_Make3DText', Tool_Make3DText())