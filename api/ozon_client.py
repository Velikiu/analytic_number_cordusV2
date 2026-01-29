"""
Клиент OZON Seller API.
Только эндпоинты и форматы из официальной документации: https://docs.ozon.ru/api/seller/

Аутентификация: заголовки Client-Id, Api-Key (кабинет продавца → Настройки → API).
"""

import logging
from typing import Any, Optional, Tuple, List
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

import requests

import config

logger = logging.getLogger(__name__)

# Эндпоинты API по документации https://docs.ozon.ru/api/seller/en/
# Ozon использует прямые запросы к API вместо генерации отчётов

# Прямые эндпоинты для получения данных (актуальные)
OZON_RETURNS_FBO_PATH = "/v3/returns/company/fbo"
OZON_RETURNS_FBS_PATH = "/v3/returns/company/fbs"
OZON_POSTING_FBO_LIST_PATH = "/v2/posting/fbo/list"
OZON_POSTING_FBS_LIST_PATH = "/v3/posting/fbs/list"
OZON_STOCKS_PATH = "/v4/product/info/stocks"
OZON_PRODUCTS_LIST_PATH = "/v3/product/list"
OZON_PRODUCTS_INFO_PATH = "/v3/product/info/list"
OZON_FINANCE_TRANSACTION_PATH = "/v3/finance/transaction/list"
OZON_ANALYTICS_DATA_PATH = "/v1/analytics/data"

# Для асинхронной генерации отчётов (если поддерживается)
OZON_REPORT_CREATE_PATH = "/v1/report/info/create"
OZON_REPORT_INFO_PATH = "/v1/report/info"
OZON_REPORT_DOWNLOAD_PATH = "/v1/report/info"

# Типы данных для автоматической загрузки
OZON_AUTO_REPORT_TYPES = [
    "returns_fbo",              # Возвраты FBO
    "returns_fbs",              # Возвраты FBS  
    "postings_fbo",             # Заказы FBO
    "postings_fbs",             # Заказы FBS
    "stocks",                   # Остатки на складах
    "finance",                  # Финансовые транзакции
]


def get_last_n_months_ranges(n_months: int = 3) -> List[Tuple[str, str, str]]:
    """
    Возвращает список кортежей (month_label, date_from, date_to) за последние N месяцев.
    Например, для n_months=3 в январе 2026:
      - Декабрь 2025: ("2025-12", "2025-12-01", "2025-12-31")
      - Ноябрь 2025: ("2025-11", "2025-11-01", "2025-11-30")
      - Октябрь 2025: ("2025-10", "2025-10-01", "2025-10-31")
    """
    today = date.today()
    # Начинаем с первого дня текущего месяца
    first_of_current = today.replace(day=1)
    
    ranges = []
    for i in range(1, n_months + 1):
        # Первый день месяца, который на i месяцев раньше
        first_of_month = first_of_current - relativedelta(months=i)
        # Последний день этого месяца
        last_of_month = first_of_month + relativedelta(months=1) - relativedelta(days=1)
        
        month_label = first_of_month.strftime("%Y-%m")
        date_from = first_of_month.strftime("%Y-%m-%d")
        date_to = last_of_month.strftime("%Y-%m-%d")
        
        ranges.append((month_label, date_from, date_to))
    
    # Возвращаем от старых к новым
    return list(reversed(ranges))


class OzonAPIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, response: Any = None):
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class OzonAPIClient:
    """HTTP-клиент для OZON Seller API."""

    def __init__(
        self,
        client_id: str,
        api_key: str,
        base_url: Optional[str] = None,
    ):
        self.client_id = client_id
        self.api_key = api_key
        self.base_url = (base_url or config.OZON_API_BASE_URL).rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({
            "Client-Id": self.client_id,
            "Api-Key": self.api_key,
            "Content-Type": "application/json",
        })

    def request(
        self,
        method: str,
        path: str,
        json_body: Optional[dict] = None,
        params: Optional[dict] = None,
        timeout: int = 30,
    ) -> Tuple[int, dict]:
        """
        Выполняет запрос к API. Не логирует ключи.
        Возвращает (status_code, response_json).
        """
        url = f"{self.base_url}{path}"
        try:
            r = self._session.request(
                method,
                url,
                json=json_body,
                params=params,
                timeout=timeout,
            )
            try:
                data = r.json() if r.content else {}
            except Exception:
                data = {"raw": r.text[:500] if r.text else ""}
            if r.status_code >= 400:
                logger.warning("OZON API error: %s %s -> %s", method, path, r.status_code)
                raise OzonAPIError(
                    data.get("message") or data.get("error") or r.text or f"HTTP {r.status_code}",
                    status_code=r.status_code,
                    response=data,
                )
            return r.status_code, data
        except requests.exceptions.Timeout:
            logger.warning("OZON API timeout: %s %s", method, path)
            raise OzonAPIError("Таймаут запроса к OZON API", status_code=None)
        except requests.exceptions.RequestException as e:
            logger.warning("OZON API request error: %s %s -> %s", method, path, e)
            raise OzonAPIError(str(e), status_code=None)

    def report_create(self, report_type: str, date_from: str, date_to: str) -> dict:
        """
        Создание отчёта. Тело и путь — по документации.
        """
        payload = {
            "report_type": report_type,
            "date_from": date_from,
            "date_to": date_to,
        }
        status, data = self.request("POST", OZON_REPORT_CREATE_PATH, json_body=payload)
        return data

    def report_info(self, code: str) -> dict:
        """Получение статуса/информации об отчёте."""
        status, data = self.request("POST", OZON_REPORT_INFO_PATH, json_body={"code": code})
        return data

    def report_download(self, code: str) -> bytes:
        """
        Скачивание файла отчёта. OZON может возвращать URL в report/info;
        при наличии URL нужно запрашивать его отдельно. Здесь — запрос по коду.
        """
        url = f"{self.base_url}{OZON_REPORT_DOWNLOAD_PATH}"
        err_status = None
        try:
            r = self._session.get(url, params={"code": code}, timeout=60)
            err_status = r.status_code
            r.raise_for_status()
            return r.content
        except requests.exceptions.RequestException as e:
            logger.warning("OZON report download error: %s", e)
            raise OzonAPIError(str(e), status_code=err_status)

    def report_download_by_url(self, file_url: str) -> bytes:
        """
        Скачивание файла отчёта по прямому URL (из report_info).
        OZON часто возвращает URL в поле 'file' или 'file_url' после готовности отчёта.
        """
        err_status = None
        try:
            r = requests.get(file_url, timeout=120)
            err_status = r.status_code
            r.raise_for_status()
            return r.content
        except requests.exceptions.RequestException as e:
            logger.warning("OZON report download by URL error: %s", e)
            raise OzonAPIError(str(e), status_code=err_status)

    def get_available_report_types(self) -> List[str]:
        """Возвращает список типов отчётов для автозагрузки."""
        return OZON_AUTO_REPORT_TYPES.copy()

    def get_returns_fbo(self, date_from: str, date_to: str, limit: int = 1000, offset: int = 0) -> dict:
        """
        Получить возвраты FBO за период.
        https://docs.ozon.ru/api/seller/en/#tag/Returns/paths/~1v3~1returns~1company~1fbo/post
        """
        payload = {
            "filter": {
                "accepted_from_customer_moment": {
                    "time_from": f"{date_from}T00:00:00Z",
                    "time_to": f"{date_to}T23:59:59Z"
                }
            },
            "limit": limit,
            "offset": offset
        }
        status, data = self.request("POST", OZON_RETURNS_FBO_PATH, json_body=payload)
        return data

    def get_returns_fbs(self, date_from: str, date_to: str, limit: int = 1000, offset: int = 0) -> dict:
        """
        Получить возвраты FBS за период.
        https://docs.ozon.ru/api/seller/en/#tag/Returns/paths/~1v3~1returns~1company~1fbs/post
        """
        payload = {
            "filter": {
                "accepted_from_customer_moment": {
                    "time_from": f"{date_from}T00:00:00Z",
                    "time_to": f"{date_to}T23:59:59Z"
                }
            },
            "limit": limit,
            "offset": offset
        }
        status, data = self.request("POST", OZON_RETURNS_FBS_PATH, json_body=payload)
        return data

    def get_postings_fbo(self, date_from: str, date_to: str, limit: int = 1000, offset: int = 0) -> dict:
        """
        Получить отправления FBO за период.
        https://docs.ozon.ru/api/seller/en/#tag/FBO/paths/~1v2~1posting~1fbo~1list/post
        """
        payload = {
            "dir": "DESC",
            "filter": {
                "since": f"{date_from}T00:00:00Z",
                "to": f"{date_to}T23:59:59Z"
            },
            "limit": limit,
            "offset": offset,
            "with": {
                "analytics_data": True,
                "financial_data": True
            }
        }
        status, data = self.request("POST", OZON_POSTING_FBO_LIST_PATH, json_body=payload)
        return data

    def get_postings_fbs(self, date_from: str, date_to: str, limit: int = 1000, offset: int = 0) -> dict:
        """
        Получить отправления FBS за период.
        https://docs.ozon.ru/api/seller/en/#tag/FBS/paths/~1v3~1posting~1fbs~1list/post
        """
        payload = {
            "dir": "DESC",
            "filter": {
                "since": f"{date_from}T00:00:00Z",
                "to": f"{date_to}T23:59:59Z"
            },
            "limit": limit,
            "offset": offset,
            "with": {
                "analytics_data": True,
                "financial_data": True
            }
        }
        status, data = self.request("POST", OZON_POSTING_FBS_LIST_PATH, json_body=payload)
        return data

    def get_stocks(self, limit: int = 1000, cursor: str = "") -> dict:
        """
        Получить информацию об остатках.
        https://docs.ozon.ru/api/seller/en/#operation/ProductAPI_GetProductInfoStocks
        """
        payload = {
            "filter": {
                "visibility": "ALL"
            },
            "cursor": cursor,
            "limit": limit
        }
        status, data = self.request("POST", OZON_STOCKS_PATH, json_body=payload)
        return data

    def get_finance_transactions(self, date_from: str, date_to: str, page: int = 1, page_size: int = 1000) -> dict:
        """
        Получить финансовые транзакции за период.
        https://docs.ozon.ru/api/seller/en/#tag/Finance/paths/~1v3~1finance~1transaction~1list/post
        """
        payload = {
            "filter": {
                "date": {
                    "from": f"{date_from}T00:00:00Z",
                    "to": f"{date_to}T23:59:59Z"
                },
                "transaction_type": "all"
            },
            "page": page,
            "page_size": page_size
        }
        status, data = self.request("POST", OZON_FINANCE_TRANSACTION_PATH, json_body=payload)
        return data

    def get_products_list(self, limit: int = 1000, last_id: str = "") -> dict:
        """
        Получить список товаров.
        https://docs.ozon.ru/api/seller/en/#operation/ProductAPI_GetProductList
        """
        payload = {
            "filter": {
                "visibility": "ALL"
            },
            "last_id": last_id,
            "limit": limit
        }
        status, data = self.request("POST", OZON_PRODUCTS_LIST_PATH, json_body=payload)
        return data

    def fetch_data_for_period(self, data_type: str, date_from: str, date_to: str) -> dict:
        """
        Универсальный метод для получения данных по типу.
        Возвращает словарь с данными и метаинформацией.
        """
        try:
            if data_type == "returns_fbo":
                return self.get_returns_fbo(date_from, date_to)
            elif data_type == "returns_fbs":
                return self.get_returns_fbs(date_from, date_to)
            elif data_type == "postings_fbo":
                return self.get_postings_fbo(date_from, date_to)
            elif data_type == "postings_fbs":
                return self.get_postings_fbs(date_from, date_to)
            elif data_type == "stocks":
                return self.get_stocks()
            elif data_type == "finance":
                return self.get_finance_transactions(date_from, date_to)
            else:
                raise OzonAPIError(f"Неизвестный тип данных: {data_type}")
        except OzonAPIError:
            raise
        except Exception as e:
            raise OzonAPIError(f"Ошибка получения {data_type}: {e}")
