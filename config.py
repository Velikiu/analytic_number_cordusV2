"""
Единая конфигурация приложения: пути, OZON API, дефолты из бренда.
Ключи API (Client-Id, Api-Key) не хранятся здесь — только ввод в UI / сессия.
"""
from pathlib import Path
import json
import os

# Корень проекта (каталог с app.py, config.py)
PROJECT_ROOT = Path(__file__).resolve().parent

# Пути (все относительно PROJECT_ROOT)
DATA_DIR = PROJECT_ROOT / "data"
UPLOAD_DIR = PROJECT_ROOT / "upload"
BRAND_DIR = PROJECT_ROOT / "brand"

PROCESSED_DATA_FILE = DATA_DIR / "processed_data.json"
STORE_DATA_FILE = DATA_DIR / "store_data.json"
BRAND_DOCUMENTATION_PATH = BRAND_DIR / "brand_documentation.json"
OZON_SELLER_TOOLS_PATH = BRAND_DIR / "ozon_seller_tools.json"

# OZON Seller API (официальная документация: https://docs.ozon.ru/api/seller/)
OZON_API_BASE_URL = os.environ.get("OZON_API_BASE_URL", "https://api-seller.ozon.ru")


def ensure_dirs():
    """Создаёт нужные каталоги при старте."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_brand_defaults():
    """
    Читает brand_documentation.json и возвращает seller_id, seller_name, seller_url.
    Используется как fallback для магазина и API; seller_url собирается из seller_id, если не задан.
    """
    out = {
        "seller_id": None,
        "seller_name": None,
        "seller_url": None,
        "products_count": 0,
    }
    try:
        if not BRAND_DOCUMENTATION_PATH.exists():
            return out
        with open(BRAND_DOCUMENTATION_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        out["seller_id"] = data.get("seller_id")
        out["seller_name"] = data.get("seller_name")
        out["products_count"] = len(data.get("products") or {})
        url = data.get("seller_url")
        if url:
            out["seller_url"] = url
        elif out["seller_id"]:
            out["seller_url"] = f"https://www.ozon.ru/seller/{out['seller_id']}/"
        return out
    except (json.JSONDecodeError, OSError) as e:
        import logging
        logging.getLogger(__name__).warning("get_brand_defaults: %s", e)
        return out
