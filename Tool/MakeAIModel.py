# -*- coding: utf-8 -*-
# Tool/MakeAIModel.py
import os
import re
import json
import time
import math
import traceback
import threading
import urllib.request
import FreeCAD
import FreeCADGui
import Part

try:
    from PySide2 import QtWidgets, QtCore
except ImportError:
    from PySide6 import QtWidgets, QtCore

import Core.Progress as Progress

def load_all_learning_data(max_total_chars=3000):
    """
    「Tool」と「AI Study」フォルダ内をスキャンし、合計文字数が上限を超えない範囲で読み込む
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dirs = [
        os.path.join(base_dir, "Tool"),
        os.path.join(base_dir, "AI Study"),
        os.path.join(base_dir, "AIStudy")
    ]
    
    examples = []
    loaded_files_log = []
    total_chars = 0
    
    for t_dir in target_dirs:
        if os.path.exists(t_dir):
            for root, dirs, files in os.walk(t_dir):
                for filename in sorted(files):
                    if filename.endswith(".py") or filename.endswith(".FCMacro"):
                        if filename in ["MakeAIModel.py", "__init__.py"]:
                            continue
                        
                        filepath = os.path.join(root, filename)
                        rel_path = os.path.relpath(filepath, base_dir)
                        
                        try:
                            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                                code_text = f.read().strip()
                                if code_text:
                                    if len(code_text) > 500:
                                        code_text = code_text[:500] + "\n# ... (以下省略)"
                                        
                                    snippet = f"【お手本 ({rel_path})】\n```python\n{code_text}\n```"
                                    examples.append(snippet)
                                    loaded_files_log.append(rel_path)
                                    total_chars += len(snippet)
                                    
                                    if total_chars >= max_total_chars:
                                        break
                        except Exception:
                            pass
                if total_chars >= max_total_chars:
                    break
        if total_chars >= max_total_chars:
            break

    reference_knowledge = ""
    if examples:
        reference_knowledge = "\n\n以下は動作確認済みの正解コード群です。これを手本にしてください:\n\n" + "\n\n".join(examples)
            
    return reference_knowledge, loaded_files_log


def clean_python_code(response_text):
    """
    AIの返答から純粋なPythonコード部分だけを抽出・全角記号等をクリーニングする
    """
    code_match = re.search(r'```(?:python)?\s*(.*?)\s*```', response_text, re.DOTALL)
    cleaned_code = code_match.group(1).strip() if code_match else response_text.strip()

    cleaned_lines = []
    for line in cleaned_code.splitlines():
        if '#' in line:
            code_part, comment_part = line.split('#', 1)
            code_part = code_part.replace('。', '').replace('、', '').replace(' ', ' ')
            line = code_part + '#' + comment_part
        else:
            line = line.replace('。', '').replace('、', '').replace(' ', ' ')
        cleaned_lines.append(line)
    
    cleaned_code = "\n".join(cleaned_lines)
    cleaned_code = re.sub(r'\bfreecad\.newDocument\b', 'FreeCAD.newDocument', cleaned_code)
    cleaned_code = re.sub(r'\bfreecad\.activeDocument\b', 'FreeCAD.activeDocument', cleaned_code)

    return cleaned_code


class Tool_MakeAIModel:
    def GetResources(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icons_dir = os.path.join(base_dir, "icons")
        icon_path = os.path.join(icons_dir, "ai.png").replace('\\', '/')
        
        if not os.path.exists(icon_path) and os.path.exists(icons_dir):
            for filename in sorted(os.listdir(icons_dir)):
                if filename.lower().endswith(('.png', '.svg', '.xpm')):
                    icon_path = os.path.join(icons_dir, filename).replace('\\', '/')
                    break

        return {
            'Pixmap': icon_path, 
            'MenuText': "AIモデリング", 
            'ToolTip': "フォルダ内のコードを学習したAIがモデリングします"
        }

    def Activated(self):
        FreeCAD.Console.PrintMessage("\n" + "="*50 + "\n")
        FreeCAD.Console.PrintMessage(" [AIモデリング処理開始]\n")
        FreeCAD.Console.PrintMessage("="*50 + "\n")

        # ＝＝＝ 【ステップ1】 事前学習フェーズ ＝＝＝
        FreeCAD.Console.PrintMessage("\n[1/5] 学習データの読み込みを開始します...\n")
        reference_knowledge, loaded_files_log = load_all_learning_data()
        
        if loaded_files_log:
            log_msg = f"【AI学習完了】\n\n合計 {len(loaded_files_log)} 件のデータを手本としてAIに読み込ませました！"
            FreeCAD.Console.PrintMessage(f"[AI] 読み込み完了: 以下の {len(loaded_files_log)} 件を手本として参照します:\n")
            for rel_f in loaded_files_log:
                FreeCAD.Console.PrintMessage(f"  - {rel_f}\n")
            QtWidgets.QMessageBox.information(None, "AI学習フェーズ", log_msg)
        else:
            FreeCAD.Console.PrintWarning("[AI] 学習対象のファイルが見つかりませんでした。\n")
            QtWidgets.QMessageBox.warning(None, "AI学習フェーズ", "学習対象のファイルが見つかりませんでした。")

        # ＝＝＝ 【ステップ2】 指示フェーズ ＝＝＝
        prompt, ok = QtWidgets.QInputDialog.getText(
            None, 
            "AI への指示", 
            "学習したデータをもとに、何を作りますか？:\n（例: ヘリカルギアを生成 歯数20 モジュール2）"
        )
        if not ok or not prompt:
            FreeCAD.Console.PrintMessage("[AI] ユーザーによりキャンセルのため処理を終了します。\n")
            return

        FreeCAD.Console.PrintMessage(f"\n[2/5] AIへの指示:\n  > {prompt}\n")

        bar = Progress.ProgressManager()
        bar.start(title="AI思考中", initial_text="学習データをもとに思考中...")

        try:
            system_prompt = f"""
あなたはFreeCADのPythonスクリプト専門家です。
以下の【正解コード群】の書き方を手本にして、ユーザーの指示通りのコードを作成してください。
【重要注意事項】:
1. 作成した形状（Shape）は、コードの最後で必ず `Part.show(shape)` または `doc.addObject('Part::Feature', '...').Shape = shape` を使って画面に登録・表示させてください。
2. 説明文は不要です。```python と ``` で囲んだ実行可能なコードのみ出力してください。

{reference_knowledge}
"""

            data = {
                "model": "codegemma",
                "prompt": system_prompt + "\n\nユーザー指示: " + prompt,
                "stream": True,
                "options": {
                    "temperature": 0.1,
                    "num_ctx": 4096
                }
            }
            
            req = urllib.request.Request(
                'http://localhost:11434/api/generate',
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )

            res_chunks = []
            err_box = {}
            done_flag = [False]

            def fetch():
                try:
                    with urllib.request.urlopen(req, timeout=120) as response:
                        for line in response:
                            if line:
                                chunk = json.loads(line.decode('utf-8'))
                                res_chunks.append(chunk.get('response', ''))
                except Exception as e:
                    err_box['error'] = e
                finally:
                    done_flag[0] = True

            FreeCAD.Console.PrintMessage("\n[3/5] --- AIのリアルタイム応答出力開始 ---\n")

            t = threading.Thread(target=fetch)
            t.start()

            printed_idx = 0
            count = 0
            while not done_flag[0]:
                while printed_idx < len(res_chunks):
                    FreeCAD.Console.PrintMessage(res_chunks[printed_idx])
                    printed_idx += 1
                
                count += 1
                pct = 30 + (count % 50)
                bar.update(pct, "AIが思考・コード生成中...")
                QtWidgets.QApplication.processEvents()
                time.sleep(0.05)

            while printed_idx < len(res_chunks):
                FreeCAD.Console.PrintMessage(res_chunks[printed_idx])
                printed_idx += 1

            FreeCAD.Console.PrintMessage("\n--- AIのリアルタイム応答出力終了 ---\n")

            if 'error' in err_box:
                raise err_box['error']

            ai_response = "".join(res_chunks)

            FreeCAD.Console.PrintMessage("\n[4/5] コードのクリーニング・検証を行っています...\n")
            cleaned_code = clean_python_code(ai_response)

            if not cleaned_code:
                raise ValueError("有効なコードが生成されませんでした。")

            FreeCAD.Console.PrintMessage("\n--- [確定コード] ---\n" + cleaned_code + "\n---------------------\n")

            bar.close()

            doc = FreeCAD.activeDocument()
            if not doc:
                doc = FreeCAD.newDocument("AI_Model")

            try:
                import freecad
                for attr in dir(FreeCAD):
                    if not hasattr(freecad, attr):
                        try:
                            setattr(freecad, attr, getattr(FreeCAD, attr))
                        except Exception:
                            pass
            except Exception:
                pass

            exec_globals = {
                'FreeCAD': FreeCAD, 
                'freecad': FreeCAD, 
                'App': FreeCAD, 
                'FreeCADGui': FreeCADGui,
                'Gui': FreeCADGui,
                'Part': Part, 
                'Vector': FreeCAD.Vector, 
                'doc': doc,
                'math': math
            }
            
            FreeCAD.Console.PrintMessage("[5/5] FreeCADドキュメントにコードを適用中...\n")
            try:
                # 実行前のドキュメント内オブジェクト数を記録
                initial_obj_count = len(doc.Objects)

                exec(cleaned_code, exec_globals)
                doc.recompute()

                # ★【自動救済ロジック】AIが Part.show() を忘れてオブジェクト数が変化しなかった場合
                if len(doc.Objects) == initial_obj_count:
                    recovered = False
                    for var_name, var_val in exec_globals.items():
                        if isinstance(var_val, Part.Shape) and not var_val.isNull():
                            Part.show(var_val)
                            recovered = True
                            FreeCAD.Console.PrintWarning(f"[自動救済] メモリ上の形状変数 '{var_name}' を Part.show() で画面に表示しました。\n")
                    
                    doc.recompute()
                    
                    if not recovered and len(doc.Objects) == initial_obj_count:
                        FreeCAD.Console.PrintWarning("[警告] 3Dオブジェクトがドキュメントに追加されませんでした。AIコンソールログを確認してください。\n")
                        QtWidgets.QMessageBox.warning(None, "表示警告", "コード実行は完了しましたが、3D形状オブジェクトが生成されませんでした。\nPythonコンソールのコードを確認してください。")
                    else:
                        FreeCADGui.SendMsgToActiveView("ViewFit")
                        FreeCAD.Console.PrintMessage("\n[AIモデリング完了] 自動救済により形状を表示しました！\n")
                        FreeCAD.Console.PrintMessage("="*50 + "\n")
                        QtWidgets.QMessageBox.information(None, "成功", "モデリングが完了しました！")
                else:
                    FreeCADGui.SendMsgToActiveView("ViewFit")
                    FreeCAD.Console.PrintMessage("\n[AIモデリング完了] モデリングが成功しました！\n")
                    FreeCAD.Console.PrintMessage("="*50 + "\n")
                    QtWidgets.QMessageBox.information(None, "成功", "モデリングが完了しました！")

            except Exception as exec_err:
                error_detail = traceback.format_exc()
                FreeCAD.Console.PrintError(f"\n[AIコード実行エラー詳細]\n{error_detail}\n")
                FreeCAD.Console.PrintMessage("="*50 + "\n")
                QtWidgets.QMessageBox.critical(
                    None, 
                    "実行エラー", 
                    f"AIが生成したコードの実行中にエラーが発生しました:\n\n{str(exec_err)}\n\n※詳細はPythonコンソールを確認してください。"
                )

        except Exception as e:
            FreeCAD.Console.PrintError(f"\n[エラー処理発生]\n{str(e)}\n")
            FreeCAD.Console.PrintMessage("="*50 + "\n")
            QtWidgets.QMessageBox.critical(None, "エラー", f"処理中にエラーが発生しました:\n\n{str(e)}")
        finally:
            bar.close()

FreeCADGui.addCommand('Ring_MakeAIModel', Tool_MakeAIModel())