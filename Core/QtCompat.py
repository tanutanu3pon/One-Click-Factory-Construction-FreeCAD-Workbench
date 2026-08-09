# -*- coding: utf-8 -*-
# Core/QtCompat.py

# PySide2 と PySide6 の純粋な互換インポートのみに絞り、
# フリーズや型判定エラーの原因となっていたクラスの再定義・ラップを廃止しました。
try:
    from PySide2 import QtWidgets, QtGui, QtCore
except ImportError:
    from PySide6 import QtWidgets, QtGui, QtCore