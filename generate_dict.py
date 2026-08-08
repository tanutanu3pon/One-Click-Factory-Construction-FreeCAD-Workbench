# -*- coding: utf-8 -*-
# generate_dict.py
import os
import json
import ast
import re

# スクリプト自身の場所を基準にワークベンチのルートディレクトリを取得
wb_dir = os.path.dirname(os.path.abspath(__file__))
tool_dir = os.path.join(wb_dir, "Tool")
trans_dir = os.path.join(wb_dir, "translations")
json_path = os.path.join(trans_dir, "dictionary.json")

os.makedirs(trans_dir, exist_ok=True)

# 既存辞書の読み込み
existing_dict = {}
if os.path.exists(json_path):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            existing_dict = json.load(f)
    except Exception:
        pass

# 日本語文字（ひらがな・カタカナ・漢字）が含まれているか判定する正規表現
jp_char_regex = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]')

found_words = set()

# Tool フォルダ内の全 Python ファイルから日本語文字列を抽出
for root, _, files in os.walk(tool_dir):
    for file in files:
        if file.endswith(".py"):
            fp = os.path.join(root, file)
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    code = f.read()
                
                # ast (抽象構文木) を使ってPythonコードを解析
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    # 文字列リテラル（定数）のみを抽出
                    if isinstance(node, ast.Constant) and isinstance(node.value, str):
                        text = node.value.strip()
                        # 空文字ではなく、日本語文字が含まれている場合のみ追加
                        if text and jp_char_regex.search(text):
                            found_words.add(text)
                            
            except SyntaxError as e:
                print(f"構文エラーのためスキップしました ({file}): {e}")
            except Exception as e:
                print(f"読み込みエラー ({file}): {e}")

# 新規追加・更新された辞書データの作成
new_dict = {}
new_count = 0

for word in sorted(found_words):
    if word in existing_dict:
        new_dict[word] = existing_dict[word]  # 既存の英訳を保持
    else:
        new_dict[word] = word  # 未登録単語（初期値は日本語のまま）
        new_count += 1

# JSON ファイルへ保存
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(new_dict, f, ensure_ascii=False, indent=2)

print(f"辞書生成完了！\n・登録総数: {len(new_dict)} 件\n・新規検出: {new_count} 件")
print(f"保存先: {json_path}")