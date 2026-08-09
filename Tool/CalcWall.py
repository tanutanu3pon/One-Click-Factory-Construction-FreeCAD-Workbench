# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui
import Part

# 【修正】絶対インポートで安全にCoreモジュールを読み込む
from Core.QtCompat import QtWidgets, QtGui, QtCore
from Core.Controller import translate_text
from Core.Language import get_language

class Tool_CalcWall:
    def GetResources(self):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "calc.png").replace('\\', '/')
        return {
            'Pixmap': icon_path if os.path.exists(icon_path) else "", 
            'MenuText': "擁壁の数量計算", 
            'ToolTip': "選択した擁壁の体積(m3)と各面ごとの表面積(m2)を小数点以下1桁で計算します"
        }

    def Activated(self):
        lang = get_language()
        
        sel = FreeCADGui.Selection.getSelection()
        if not sel:
            QtWidgets.QMessageBox.warning(None, translate_text("選択エラー", lang), translate_text("数量計算を行いたい擁壁オブジェクトを画面またはツリーから選択してください。", lang))
            return
            
        obj = sel[0]
        if not hasattr(obj, "Shape") or obj.Shape.isNull() or not obj.Shape.Faces:
            QtWidgets.QMessageBox.warning(None, translate_text("エラー", lang), translate_text("有効な形状を持たないオブジェクトです。", lang))
            return
            
        shape = obj.Shape
        volume_m3 = shape.Volume / 1e9
        
        bbox = shape.BoundBox
        y_tol = (bbox.YMax - bbox.YMin) * 0.1 if (bbox.YMax - bbox.YMin) > 0 else 1.0
        z_tol = (bbox.ZMax - bbox.ZMin) * 0.1 if (bbox.ZMax - bbox.ZMin) > 0 else 1.0
        
        faces_info = {
            "底面 (GL接触部)": 0.0,
            "天端面 (上面)": 0.0,
            "裏面 (垂直・土砂埋戻し側)": 0.0,
            "表面 (勾配・見えがかり側)": 0.0,
            "手前面 (始点側 Y=0)": 0.0,
            "奥側面 (終点側 Y=L)": 0.0
        }
        
        total_area_m2 = 0.0
        
        for face in shape.Faces:
            c = face.CenterOfMass
            area_m2 = face.Area / 1e6
            total_area_m2 += area_m2
            
            if abs(c.y - bbox.YMin) < y_tol:
                faces_info["手前面 (始点側 Y=0)"] += area_m2
            elif abs(c.y - bbox.YMax) < y_tol:
                faces_info["奥側面 (終点側 Y=L)"] += area_m2
            elif abs(c.z - bbox.ZMin) < z_tol:
                faces_info["底面 (GL接触部)"] += area_m2
            elif abs(c.z - bbox.ZMax) < z_tol:
                faces_info["天端面 (上面)"] += area_m2
            else:
                if c.x < bbox.Center.x:
                    faces_info["裏面 (垂直・土砂埋戻し側)"] += area_m2
                else:
                    faces_info["表面 (勾配・見えがかり側)"] += area_m2
                    
        # 【修正】英語モードの場合はHTMLレポート自体を英語で構築する
        if lang == "English":
            msg = f"<h3>[Quantity Report: {obj.Label}]</h3><hr>"
            msg += f"<b>■ Volume (Concrete Volume):</b><br>"
            msg += f"&nbsp;&nbsp;&nbsp;&nbsp;<font color='#0055ff' size='5'><b>{volume_m3:.1f} m3</b></font><br><br>"
            
            msg += f"<b>■ Surface Area of Each Face (Formwork/Finishing Area):</b><br>"
            for name, area in faces_info.items():
                if area > 0:
                    trans_name = translate_text(name, lang)
                    msg += f"&nbsp;&nbsp;・{trans_name} : <b>{area:.1f} m2</b><br>"
                
            msg += f"<hr>"
            msg += f"&nbsp;&nbsp;<b>Total Surface Area :</b> <font color='#00aa00' size='5'><b>{total_area_m2:.1f} m2</b></font>"
            title_text = "Quantity Calculation Results"
            
        else:
            msg = f"<h3>【数量計算レポート : {obj.Label}】</h3><hr>"
            msg += f"<b>■ 体積 (コンクリート体積):</b><br>"
            msg += f"&nbsp;&nbsp;&nbsp;&nbsp;<font color='#0055ff' size='5'><b>{volume_m3:.1f} m3</b></font><br><br>"
            
            msg += f"<b>■ 各面の表面積 (型枠・仕上げ面積):</b><br>"
            for name, area in faces_info.items():
                if area > 0:
                    msg += f"&nbsp;&nbsp;・{name} : <b>{area:.1f} m2</b><br>"
                
            msg += f"<hr>"
            msg += f"&nbsp;&nbsp;<b>合計表面積 :</b> <font color='#00aa00' size='5'><b>{total_area_m2:.1f} m2</b></font>"
            title_text = "数量計算結果"
        
        QtWidgets.QMessageBox.information(None, title_text, msg)

FreeCADGui.addCommand('Construction_CalcWall', Tool_CalcWall())