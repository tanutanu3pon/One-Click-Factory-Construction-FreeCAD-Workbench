# -*- coding: utf-8 -*-
# Core/Progress.py
import FreeCADGui
from Core.QtCompat import QtWidgets, QtCore

class ProgressManager:
    def __init__(self):
        self.pd = None
        self.doc = None

    # ★追加: with構文に入った時の処理
    def __enter__(self):
        return self

    # ★追加: with構文を抜けた時（正常終了時・エラー発生時問わず）に確実にcloseを呼ぶ
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def start(self, title, initial_text):
        main_win = FreeCADGui.getMainWindow()
        if main_win:
            main_win.setUpdatesEnabled(True)
        
        self.pd = QtWidgets.QProgressDialog(initial_text, None, 0, 100, None)
        self.pd.setWindowTitle(title)
        
        # ★改善: PySide6 (新しいQt) と PySide2 のフラグ指定の違いを安全に吸収
        if hasattr(QtCore.Qt, "WindowType"):
            flags = (QtCore.Qt.WindowType.Window | 
                     QtCore.Qt.WindowType.WindowTitleHint | 
                     QtCore.Qt.WindowType.CustomizeWindowHint)
        else:
            flags = (QtCore.Qt.Window | 
                     QtCore.Qt.WindowTitleHint | 
                     QtCore.Qt.CustomizeWindowHint)
                     
        self.pd.setWindowFlags(flags)
        self.pd.setWindowModality(QtCore.Qt.ApplicationModal)
        self.pd.setValue(0)
        self.pd.show()
        
        QtWidgets.QApplication.processEvents()
        if main_win:
            main_win.setUpdatesEnabled(False)

    def update(self, percent, text=None):
        if self.pd:
            if text:
                self.pd.setLabelText(f"{text} ({percent}%)")
            self.pd.setValue(percent)
            QtWidgets.QApplication.processEvents()

    def close(self):
        main_win = FreeCADGui.getMainWindow()
        if main_win:
            main_win.setUpdatesEnabled(True)
        if self.pd:
            self.pd.close()