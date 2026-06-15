import json
import os
from pathlib import Path
from backend.config import settings

_translations: dict[str, dict] = {}
_i18n_dir = Path(__file__).parent


def load_translations():
    global _translations
    for lang in settings.supported_languages:
        filepath = _i18n_dir / f"{lang}.json"
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                _translations[lang] = json.load(f)


def t(key: str, lang: str = "en", **kwargs) -> str:
    if not _translations:
        load_translations()

    fallback_lang = settings.default_language
    data = _translations.get(lang, _translations.get(fallback_lang, {}))

    parts = key.split(".")
    value = data
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            value = None
            break

    if value is None:
        # Fallback to default language
        value = _translations.get(fallback_lang, {})
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return key

    if isinstance(value, str) and kwargs:
        for k, v in kwargs.items():
            value = value.replace(f"{{{k}}}", str(v))

    return value if isinstance(value, str) else key


def get_all_translations(lang: str = "en") -> dict:
    if not _translations:
        load_translations()
    return _translations.get(lang, _translations.get(settings.default_language, {}))


load_translations()