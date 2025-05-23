# translation_api.py
import requests
import json

def translate_en_to_fa_api(text, target_lang='fa'):
    if not text.strip():
        return ""
    base_url = 'https://translate.googleapis.com/translate_a/single'
    params = {
        'client': 'gtx',
        'sl': 'en',
        'tl': target_lang,
        'dt': 't',
        'q': text
    }
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        translation_data = response.json()
        if translation_data and len(translation_data) > 0 and len(translation_data[0]) > 0 and len(translation_data[0][0]) > 0:
            return translation_data[0][0][0]
        else:
            return text
    except requests.exceptions.RequestException as e:
        print(f"Translation API error for '{text}': {e}")
        return text