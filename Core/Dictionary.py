# -*- coding: utf-8 -*-
# Core/Dictionary.py
import os
import xml.etree.ElementTree as ET
import importlib.util

CUSTOM_DICT = {}

TRANSLATION_DICT = CUSTOM_DICT.copy()

try:
    if '__file__' in globals():
        current_dir = os.path.dirname(os.path.abspath(__file__))
        translations_dir = os.path.join(os.path.dirname(current_dir), "translations")
    else:
        import FreeCAD
        user_mod_dir = FreeCAD.ConfigGet("UserModFolder")
        translations_dir = os.path.normpath(os.path.join(user_mod_dir, "Ring", "translations"))

    if os.path.exists(translations_dir):
        for filename in os.listdir(translations_dir):
            file_path = os.path.join(translations_dir, filename)
            
            if filename.endswith(".ts"):
                try:
                    tree = ET.parse(file_path)
                    root = tree.getroot()
                    for message in root.iter('message'):
                        source_elem = message.find('source')
                        trans_elem = message.find('translation')
                        if source_elem is not None and trans_elem is not None:
                            source_text = source_elem.text
                            trans_text = trans_elem.text
                            if trans_text and source_text:
                                clean_trans = trans_text.replace('\n', ' ').replace('\r', '').strip().replace('&', '')
                                clean_source = source_text.replace('\n', ' ').replace('\r', '').strip().replace('&', '')
                                if len(clean_trans) > 1 and len(clean_source) > 0:
                                    if clean_trans not in TRANSLATION_DICT:
                                        TRANSLATION_DICT[clean_trans] = clean_source
                except Exception as e:
                    print(f"TSエラー ({filename}): {str(e)}")
                    
            elif filename.endswith(".py") and filename != "__init__.py":
                try:
                    mod_name = os.path.splitext(filename)[0]
                    spec = importlib.util.spec_from_file_location(mod_name, file_path)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    
                    if hasattr(mod, 'WORDS') and isinstance(mod.WORDS, dict):
                        TRANSLATION_DICT.update(mod.WORDS)
                except Exception as e:
                    print(f"PY辞書読み込みエラー ({filename}): {str(e)}")

except Exception as main_err:
    print(f"辞書自動読み込みエラー: {str(main_err)}")