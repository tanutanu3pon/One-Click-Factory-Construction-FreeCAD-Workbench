# -*- coding: utf-8 -*-
# generate_dict.py
import os
import sys
import json
import ast
import re

wb_dir = os.path.dirname(os.path.abspath(__file__))
trans_dir = os.path.join(wb_dir, "translations")
json_path = os.path.join(trans_dir, "dictionary_en.json")

os.makedirs(trans_dir, exist_ok=True)

existing_dict = {}
if os.path.exists(json_path):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            existing_dict = json.load(f)
    except json.JSONDecodeError as e:
        print(f"【エラー】既存の辞書ファイルが破損しています。上書き防止のため処理を中断します: {e}")
        sys.exit(1)
    except Exception:
        pass

# 句読点や全角英数、全角記号も含める正規表現
jp_char_regex = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\u3000-\u303F\uFF00-\uFFEF]')

found_words = set()

# スキャン対象ディレクトリ・ファイルの定義（Tool, Core, ルート直下）
scan_targets = [
    os.path.join(wb_dir, "Tool"),
    os.path.join(wb_dir, "Core"),
    wb_dir
]

scanned_files = set()

for target in scan_targets:
    if os.path.isdir(target):
        for root, dirs, files in os.walk(target):
            # 不要なフォルダを除外
            dirs[:] = [d for d in dirs if d not in ("translations", ".git", "__pycache__", "img", "icons")]
            for file in files:
                if file.endswith(".py"):
                    fp = os.path.join(root, file)
                    if fp not in scanned_files:
                        scanned_files.add(fp)
    elif os.path.isfile(target) and target.endswith(".py"):
        if target not in scanned_files:
            scanned_files.add(target)

# ソースコードから日本語文字列を抽出
for fp in sorted(scanned_files):
    try:
        with open(fp, "r", encoding="utf-8") as f:
            code = f.read()
        
        tree = ast.parse(code)
        for node in ast.walk(tree):
            text = None
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                text = node.value.strip()
            elif hasattr(ast, "Str") and isinstance(node, ast.Str): # 互換性維持
                text = node.s.strip()
                
            if text and jp_char_regex.search(text):
                found_words.add(text)
                    
    except SyntaxError as e:
        print(f"構文エラーのためスキップ ({os.path.basename(fp)}): {e}")
    except Exception as e:
        print(f"読み込みエラー ({os.path.basename(fp)}): {e}")

# 既存の翻訳辞書をベースに保持し、新規検出された単語のみを追加（既存データの消失防止）
new_dict = dict(existing_dict)
new_count = 0

for word in sorted(found_words):
    if word not in new_dict:
        new_dict[word] = word  # 新規キーの初期値は原文
        new_count += 1

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(new_dict, f, ensure_ascii=False, indent=2)

print(f"辞書更新完了！")
print(f"・解析ファイル数: {len(scanned_files)} 件")
print(f"・登録総数: {len(new_dict)} 件 (既存データを維持)")
print(f"・新規追加: {new_count} 件")
print(f"保存先: {json_path}")