# -*- coding: utf-8 -*-
# Core/Progress.py
import FreeCADGui
from Core.QtCompat import QtWidgets, QtCore

class ProgressManager:
    def __init__(self):
        self.pd = None
        self.doc = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def start(self, title, initial_text):
        main_win = FreeCADGui.getMainWindow()
        if main_win:
            main_win.setUpdatesEnabled(True)
        
        self.pd = QtWidgets.QProgressDialog(initial_text, None, 0, 100, None)
        self.pd.setWindowTitle(title)
        
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