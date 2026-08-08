# -*- coding: utf-8 -*-
# Tool/Launcher.py
import os
import FreeCAD
import FreeCADGui

from Core.QtCompat import QtWidgets, QtGui, QtCore

# ---------------------------------------------------------
# [Ringワークベンチ用] 各ツールの初心者向け説明リスト (全23種)
# ---------------------------------------------------------
RING_TOOL_INFO_LIST = [
    {
        "id": "Ring_MakeRing",
        "name": "指輪の生成",
        "desc": "指輪のベースとなる3Dモデルを生成します。\n日本サイズ(号数)の指定や、甲丸・平打ちなどの断面形状をカスタマイズできます。"
    },
    {
        "id": "Ring_Tyoukoku",
        "name": "指輪への彫刻",
        "desc": "指輪の内側に文字を彫ることができます。日本語もOKです。"
    },
    {
        "id": "Ring_Daiya",
        "name": "ダイヤモンドの生成",
        "desc": "ラウンドブリリアントカット(簡易)したダイヤモンドを生成します。これを指輪に付けることができます。"
    },
    {
        "id": "Ring_Connect",
        "name": "パーツ結合",
        "desc": "指輪にダイヤモンドを載せるための専用ツールです。"
    },
    {
        "id": "Ring_Weight",
        "name": "重量の自動計算",
        "desc": "作成した3Dモデルの体積から、各種金属（K18、Pt900、SV925など）や樹脂で作った場合の推定重量を計算します。"
    },
    {
        "id": "Ring_MakeJig",
        "name": "梱包補助",
        "desc": "生成したモデルに隙間を指定して体積を求めます。梱包する際に便利です。"
    },
    {
        "id": "Ring_Magatama",
        "name": "勾玉(まがたま)の生成",
        "desc": "日本の伝統的な勾玉形状のアクセサリーチャームやペンダントトップを作成します。"
    },
    {
        "id": "Ring_Suiteki",
        "name": "水滴・しずくパーツの生成",
        "desc": "みずみずしい丸みを持った水滴（ドロップ）形状のチャームを作成します。"
    },
    {
        "id": "Ring_Mikazuki",
        "name": "三日月パーツの生成",
        "desc": "おしゃれな三日月（ムーン）モチーフの立体3Dモデルを作成します。"
    },
    {
        "id": "Ring_Heart",
        "name": "ハートパーツの生成",
        "desc": "ぷっくりとした可愛らしい立体ハートモチーフを作成します。"
    },
    {
        "id": "Ring_Hoshi",
        "name": "星パーツの生成",
        "desc": "エッジの効いた立体的な5角星モチーフのチャームを作成します。"
    },
    {
        "id": "Ring_Inkan",
        "name": "印鑑・ハンコの作成",
        "desc": "任意の文字を入力して、オリジナルのスタンプ・印鑑の3Dモデルを作成します。"
    },
    {
        "id": "Ring_Button",
        "name": "ボタンの作成",
        "desc": "服飾用のボタン（2つ穴・4つ穴など）の形状やサイズを指定して生成します。"
    },
    {
        "id": "Ring_Mug",
        "name": "マグカップの作成",
        "desc": "持ち手がついた実用的なマグカップの3Dモデルを作成します。"
    },
    {
        "id": "Ring_Vase",
        "name": "花瓶の作成",
        "desc": "滑らかな曲線美を持つ花瓶や壺の3Dモデルを作成します。"
    },
    {
        "id": "Ring_Box",
        "name": "収納ボックスの作成",
        "desc": "アクセサリーや小物パーツを収納するためのフタ付きケースを作成します。"
    },
    {
        "id": "Ring_BatteryBox",
        "name": "電池ボックスの作成",
        "desc": "単3や単4などの各種規格電池を収納・固定するための電池ホルダーを作成します。"
    },
    {
        "id": "Ring_MakeSpoon",
        "name": "スプーンの作成",
        "desc": "皿部分の深さや柄の長さを調整してスプーンを作成します。"
    },
    {
        "id": "Ring_MakeSHook",
        "name": "S字フックの作成",
        "desc": "吊り下げ収納に役立つS字フックの3Dモデルを任意の太さ・サイズで作成します。"
    },
    {
        "id": "Ring_MakeCookie",
        "name": "クッキー抜き型の作成",
        "desc": "3Dプリンターで印刷して使えるクッキー用抜き型（外枠＋押し型）を作成します。任意の絵を参照してふちをかたどります。"
    },
    {
        "id": "Ring_MakePlanetaryGear",
        "name": "遊星リングギアの作成",
        "desc": "実際に組み合わせて回転させることができるメカニカルな遊星歯車機構を作成します。画面上で動作確認ができます。"
    },
    {
        "id": "Ring_Make3DText",
        "name": "3D文字・銘板の作成",
        "desc": "フォントを指定して3D立体文字やネームプレート、キーホルダーを作成します。\n土台プレートの追加や角丸、取付穴の配置も自動で行えます。"
    }
]

# ---------------------------------------------------------
# [Constructionワークベンチ用] 各ツールの初心者向け説明リスト (全7種)
# ---------------------------------------------------------
CONST_TOOL_INFO_LIST = [
    {
        "id": "Construction_MakeWall",
        "name": "擁壁(ようへき)の作成",
        "desc": "重力式擁壁などの構造物3Dモデルを生成します。\n高さや底盤長などのパラメータを任意に調整できます。"
    },
    {
        "id": "Construction_CalcWall",
        "name": "体積計算",
        "desc": "作成した擁壁の体積、表面積を算出します。"
    },
    {
        "id": "Construction_MakeRoad",
        "name": "道路モデルの作成",
        "desc": "線形データや幅員・勾配パラメータに基づいて3D道路形状を生成します。"
    },
    {
        "id": "Construction_MakeTetrapod",
        "name": "消波ブロック(テトラポッド)",
        "desc": "海岸や河川工事で使用される標準的な消波ブロック（テトラポッド）の3Dモデルを作成します。"
    },
    {
        "id": "Construction_MakeExcelSurface",
        "name": "Excelデータからの3D地形作成",
        "desc": "ExcelのXYZ座標データを読み込み、点群から3D地形サーフェス（TIN/メッシュ）を自動構築します。"
    },
    {
        "id": "Construction_CalcEarthworkSolid",
        "name": "切盛り土量の算出",
        "desc": "現況地形と計画形状の3Dソリッドモデルから、切土量・盛土量の体積（土量）を差分計算します。"
    }
]


class ToolLauncherDialog(QtWidgets.QDialog):
    """ 説明を見ながらツールを選んで実行できるランチャーダイアログ """
    def __init__(self, tool_list, title, parent=None):
        super().__init__(parent)
        self.tool_list = tool_list
        self.setWindowTitle(title)
        self.resize(520, 360)
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(12)

        select_group = QtWidgets.QGroupBox("1. やりたいこと・機能を選択")
        select_layout = QtWidgets.QVBoxLayout(select_group)

        self.combo_tools = QtWidgets.QComboBox()
        self.combo_tools.setStyleSheet("font-size: 11pt; padding: 4px;")
        
        for tool in self.tool_list:
            self.combo_tools.addItem(tool["name"], tool)

        select_layout.addWidget(self.combo_tools)
        main_layout.addWidget(select_group)

        desc_group = QtWidgets.QGroupBox("2. 機能の説明・使い方")
        desc_layout = QtWidgets.QVBoxLayout(desc_group)

        self.lbl_desc = QtWidgets.QLabel()
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.lbl_desc.setStyleSheet("""
            QLabel {
                font-size: 10pt;
                line-height: 1.5;
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 10px;
                color: #222222;
            }
        """)
        desc_layout.addWidget(self.lbl_desc)
        main_layout.addWidget(desc_group, 1)

        btn_layout = QtWidgets.QHBoxLayout()
        
        self.btn_cancel = QtWidgets.QPushButton("閉じる")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_run = QtWidgets.QPushButton("?? このプログラムを起動する")
        self.btn_run.setFixedHeight(42)
        self.btn_run.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                font-size: 11pt;
                background-color: #0078d4;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        self.btn_run.clicked.connect(self.run_selected_tool)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_run, 2)
        main_layout.addLayout(btn_layout)

        self.combo_tools.currentIndexChanged.connect(self.update_description)
        self.update_description()

    def update_description(self):
        tool_data = self.combo_tools.currentData()
        if tool_data and "desc" in tool_data:
            self.lbl_desc.setText(tool_data["desc"])
        else:
            self.lbl_desc.setText("説明が登録されていません。")

    def run_selected_tool(self):
        tool_data = self.combo_tools.currentData()
        if tool_data and "id" in tool_data:
            cmd_id = tool_data["id"]
            self.accept()
            QtCore.QTimer.singleShot(100, lambda: FreeCADGui.runCommand(cmd_id))


# =========================================================
# コマンド登録 (Ring用とConstruction用の2つを生成)
# =========================================================

class Tool_LauncherRing:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "hatena.png").replace('\\', '/')
        return {
            'Pixmap': icon_path, 
            'MenuText': "機能案内ガイド (Ring用)", 
            'ToolTip': "説明を見ながら目的のツールを選んで起動できます"
        }

    def Activated(self):
        dlg = ToolLauncherDialog(RING_TOOL_INFO_LIST, "Click Factory - 機能案内ガイド", FreeCADGui.getMainWindow())
        dlg.exec_()


class Tool_LauncherConstruction:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icons", "hatena.png").replace('\\', '/')
        return {
            'Pixmap': icon_path, 
            'MenuText': "機能案内ガイド (土木用)", 
            'ToolTip': "説明を見ながら目的のツールを選んで起動できます"
        }

    def Activated(self):
        dlg = ToolLauncherDialog(CONST_TOOL_INFO_LIST, "Construction - 機能案内ガイド", FreeCADGui.getMainWindow())
        dlg.exec_()


# 2種類のランチャーコマンドをFreeCADに登録
FreeCADGui.addCommand('Ring_Launcher', Tool_LauncherRing())
FreeCADGui.addCommand('Construction_Launcher', Tool_LauncherConstruction())