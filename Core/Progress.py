# -*- coding: utf-8 -*-
# Core/Progress.py
import FreeCADGui

try:
    from PySide2 import QtWidgets, QtCore
except ImportError:
    from PySide6 import QtWidgets, QtCore

class ProgressManager:
    """
    FreeCADの起動システムを絶対に壊さず、
    確実に進捗窓を画面に出現させて一括コントロールするクラス
    """
    def __init__(self):
        self.pd = None
        self.doc = None  # 追加: トランザクション管理用のドキュメント保持

    def start(self, title, initial_text):
        """ 進捗窓を画面に出現させて、本体の描画を一時凍結する """
        FreeCADGui.getMainWindow().setUpdatesEnabled(True)
        
        self.pd = QtWidgets.QProgressDialog(initial_text, None, 0, 100, None)
        self.pd.setWindowTitle(title)
        self.pd.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowTitleHint | QtCore.Qt.CustomizeWindowHint)
        self.pd.setWindowModality(QtCore.Qt.ApplicationModal)
        self.pd.setValue(0)
        self.pd.show()
        
        QtWidgets.QApplication.processEvents()
        FreeCADGui.getMainWindow().setUpdatesEnabled(False)

    def update(self, percent, text=None):
        """ 進捗％と文字をリアルタイムに更新する """
        if self.pd:
            if text:
                self.pd.setLabelText(f"{text} ({percent}%)")
            self.pd.setValue(percent)
            QtWidgets.QApplication.processEvents()

    def close(self):
        """ 進捗窓を閉じ、画面のフリーズを解除する """
        FreeCADGui.getMainWindow().setUpdatesEnabled(True)
        if self.pd:
            self.pd.close()

    # ==========================================
    # ▼ 追加: with構文（コンテキストマネージャ）対応
    # ==========================================
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ withブロックを抜ける際に絶対に呼ばれる終了処理 """
        self.close()  # エラーが起きても絶対にプログレスバーを閉じてフリーズ解除
        
        if self.doc:
            if exc_type is not None:
                # エラー発生時は自動でロールバック（ゴミデータを残さない）
                self.doc.abortTransaction()
            else:
                # 正常終了時は自動でコミット
                self.doc.commitTransaction()


def safe_transaction(title, initial_text, doc=None):
    """
    【新規追加】
    with構文で呼び出すだけで、プログレスバーの開始・終了と
    トランザクション（Undo/Redo履歴）の記録・破棄を自動で行う関数
    """
    pm = ProgressManager()
    pm.doc = doc
    if doc:
        doc.openTransaction(title)
    pm.start(title, initial_text)
    return pm