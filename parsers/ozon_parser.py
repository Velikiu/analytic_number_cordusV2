"""
Парсер для различных типов отчетов Ozon
"""
import pandas as pd
import os
import json
from datetime import datetime
import re


class OzonReportParser:
    """Парсер отчетов Ozon"""
    
    def __init__(self):
        self.parsed_data = {
            'orders': [],
            'returns': [],
            'stocks': [],
            'accruals': [],
            'unit_economics': [],
            'sales_analytics_period': [],
            'sales_analytics_daily': [],
            'finance': [],
            'postings_fbo': [],
            'postings_fbs': []
        }
    
    def detect_report_type(self, filepath):
        """Определяет тип отчета по имени файла и содержимому"""
        filename = os.path.basename(filepath).lower()
        
        # JSON файлы от API
        if filename.endswith('.json'):
            return self._detect_json_type(filepath)
        
        # API-данные в имени файла
        if 'ozon_api_' in filename:
            if 'returns_fbo' in filename:
                return 'returns_fbo_api'
            elif 'returns_fbs' in filename:
                return 'returns_fbs_api'
            elif 'postings_fbo' in filename:
                return 'postings_fbo_api'
            elif 'postings_fbs' in filename:
                return 'postings_fbs_api'
            elif 'stocks' in filename:
                return 'stocks_api'
            elif 'finance' in filename:
                return 'finance_api'
        
        if 'orders' in filename or filename.endswith('.csv'):
            return 'orders'
        elif 'returns' in filename or 'возврат' in filename:
            return 'returns'
        elif 'stocks' in filename or 'остатк' in filename:
            return 'stocks'
        elif 'начисл' in filename or 'accrual' in filename:
            return 'accruals'
        elif 'юнит' in filename or 'unit' in filename or 'экономик' in filename:
            return 'unit_economics'
        elif 'analytics_report' in filename or 'аналитик' in filename:
            # Определяем тип аналитики: по дням или за период
            if 'per day' in filename or 'по дням' in filename or 'daily' in filename:
                return 'sales_analytics_daily'
            else:
                return 'sales_analytics_period'
        else:
            # Пытаемся определить по содержимому
            return self._detect_by_content(filepath)
    
    def _detect_json_type(self, filepath):
        """Определяет тип JSON-файла с данными API"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data_type = data.get('data_type', '')
            if data_type:
                return f"{data_type}_api"
            
            # Пробуем определить по структуре данных
            if 'items' in data or 'result' in data:
                items = data.get('items', data.get('result', []))
                if items and isinstance(items, list) and len(items) > 0:
                    sample = items[0]
                    if isinstance(sample, dict):
                        if 'posting_number' in sample:
                            return 'postings_api'
                        elif 'return_id' in sample:
                            return 'returns_api'
                        elif 'warehouse_name' in sample or 'fbo_sku' in sample:
                            return 'stocks_api'
                        elif 'operation_type' in sample or 'operation_id' in sample:
                            return 'finance_api'
            
            return 'unknown_api'
        except (json.JSONDecodeError, OSError, KeyError):
            return 'unknown'
    
    def _detect_by_content(self, filepath):
        """Определение типа отчета по содержимому"""
        try:
            if filepath.endswith('.csv'):
                df = pd.read_csv(filepath, sep=';', encoding='utf-8', nrows=5)
                if 'Номер заказа' in df.columns or 'номер заказа' in str(df.columns).lower():
                    return 'orders'
            elif filepath.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(filepath, nrows=5)
                columns_str = ' '.join([str(col) for col in df.columns]).lower()
                if 'возврат' in columns_str or 'return' in columns_str:
                    return 'returns'
                elif 'остат' in columns_str or 'stock' in columns_str:
                    return 'stocks'
        except (ValueError, TypeError, OSError):
            pass
        return 'unknown'
    
    def parse_orders(self, filepath):
        """Парсинг отчета по заказам"""
        try:
            # Пробуем разные кодировки
            encodings = ['utf-8', 'utf-8-sig', 'cp1251', 'windows-1251']
            df = None
            for enc in encodings:
                try:
                    df = pd.read_csv(filepath, sep=';', encoding=enc)
                    break
                except (UnicodeDecodeError, ValueError, OSError):
                    continue
            
            if df is None:
                raise Exception("Не удалось прочитать файл с любой кодировкой")
            
            # Нормализация названий колонок
            df.columns = df.columns.str.strip().str.replace('"', '')
            
            # Преобразование данных
            orders = []
            for _, row in df.iterrows():
                try:
                    # Вычисляем значения перед созданием словаря
                    quantity_val = self._parse_int(row.get('Количество', 1))
                    paid_by_customer_val = self._parse_float(row.get('Оплачено покупателем', 0))
                    seller_price_unit = self._parse_float(row.get('Ваша цена', 0))
                    # Если "Ваша цена" больше "Оплачено покупателем" и оба > 0, значит это цена за единицу
                    if seller_price_unit > 0 and paid_by_customer_val > 0 and seller_price_unit > paid_by_customer_val:
                        seller_price_total = seller_price_unit * quantity_val
                    else:
                        seller_price_total = seller_price_unit  # Уже общая сумма
                    
                    order = {
                        'order_number': str(row.get('Номер заказа', '')).strip('"'),
                        'shipment_number': str(row.get('Номер отправления', '')).strip('"'),
                        'accepted_date': self._parse_date(row.get('Принят в обработку', '')),
                        'shipment_date': self._parse_date(row.get('Дата отгрузки', '')),
                        'status': str(row.get('Статус', '')).strip('"'),
                        'delivery_date': self._parse_date(row.get('Дата доставки', '')),
                        'total_amount': self._parse_float(row.get('Сумма отправления', 0)),
                        'currency': str(row.get('Код валюты отправления', 'RUB')).strip('"'),
                        'product_name': str(row.get('Название товара', '')).strip('"'),
                        'sku': str(row.get('SKU', '')).strip('"'),
                        'article': str(row.get('Артикул', '')).strip('"'),
                        'quantity': quantity_val,
                        'paid_by_customer': paid_by_customer_val,  # В CSV обычно уже общая сумма
                        'seller_price': seller_price_total,  # Может быть за единицу или общая
                        'discount_percent': self._parse_float(str(row.get('Скидка %', '0')).replace('%', '')),
                        'discount_rub': self._parse_float(row.get('Скидка руб', 0)),
                        'promotions': str(row.get('Акции', '')).strip('"'),
                        'delivery_method': str(row.get('Способ доставки', '')).strip('"'),
                        'customer_segment': str(row.get('Сегмент клиента', '')).strip('"'),
                        'payment_method': str(row.get('Способ оплаты', '')).strip('"'),
                        'region': str(row.get('Регион доставки', '')).strip('"'),
                        'city': str(row.get('Город доставки', '')).strip('"'),
                        'warehouse': str(row.get('Склад отгрузки', '')).strip('"'),
                        'delivery_time': self._parse_int(row.get('Норм. время доставки до покупателя', 0)),
                        'is_premium': str(row.get('Сегмент клиента', '')).strip('"') == 'Премиум',
                        'is_buyout': str(row.get('Выкуп товара', '')).strip('"') == 'Подлежит выкупу'
                    }
                    orders.append(order)
                except Exception as e:
                    print(f"Ошибка парсинга строки заказа: {e}")
                    continue
            
            self.parsed_data['orders'].extend(orders)
            return {'type': 'orders', 'count': len(orders), 'data': orders}
        except Exception as e:
            raise Exception(f"Ошибка парсинга заказов: {str(e)}")
    
    def parse_returns(self, filepath):
        """Парсинг отчета по возвратам"""
        try:
            # Excel файлы с возвратами имеют сложную структуру
            df = pd.read_excel(filepath, header=None)
            
            # Ищем строку с заголовками (обычно строка 4-5)
            header_row = None
            for i in range(min(10, len(df))):
                row_str = ' '.join([str(x) for x in df.iloc[i].values]).lower()
                if 'номер отправления' in row_str or 'ozon sku' in row_str:
                    header_row = i
                    break
            
            if header_row is not None:
                df = pd.read_excel(filepath, header=header_row)
            
            returns = []
            # Базовый парсинг - можно расширить
            for _, row in df.iterrows():
                try:
                    return_data = {
                        'shipment_number': str(row.get('Номер отправления', '') or row.get('Unnamed: 2', '')),
                        'sku': str(row.get('OZON SKU ID', '') or row.get('Unnamed: 4', '')),
                        'return_date': self._parse_date(row.get('Дата возврата', '') or row.get('Unnamed: 5', '')),
                        'return_reason': str(row.get('Причина возврата', '') or row.get('Unnamed: 6', '')),
                        'status': str(row.get('Статус', '') or row.get('Unnamed: 7', ''))
                    }
                    if return_data['shipment_number'] and return_data['shipment_number'] != 'nan':
                        returns.append(return_data)
                except (ValueError, TypeError, KeyError):
                    continue

            self.parsed_data['returns'].extend(returns)
            return {'type': 'returns', 'count': len(returns), 'data': returns}
        except Exception as e:
            raise Exception(f"Ошибка парсинга возвратов: {str(e)}")
    
    def parse_stocks(self, filepath):
        """Парсинг отчета по остаткам"""
        try:
            df = pd.read_excel(filepath, header=2)  # Обычно заголовки на строке 2
            
            stocks = []
            for _, row in df.iterrows():
                try:
                    stock = {
                        'product_name': str(row.get('Название товара', '') or row.get('Название', '')),
                        'sku': str(row.get('SKU', '')),
                        'warehouse': str(row.get('Склад', '') or row.get('Склад отгрузки', '')),
                        'available': self._parse_int(row.get('Доступно', 0) or row.get('Доступно к продаже', 0)),
                        'reserved': self._parse_int(row.get('Зарезервировано', 0)),
                        'in_transit': self._parse_int(row.get('В пути', 0))
                    }
                    if stock['sku'] and stock['sku'] != 'nan':
                        stocks.append(stock)
                except (ValueError, TypeError, KeyError):
                    continue

            self.parsed_data['stocks'].extend(stocks)
            return {'type': 'stocks', 'count': len(stocks), 'data': stocks}
        except Exception as e:
            raise Exception(f"Ошибка парсинга остатков: {str(e)}")
    
    def parse_accruals(self, filepath):
        """Парсинг отчета по начислениям"""
        try:
            # Может быть несколько листов
            excel_file = pd.ExcelFile(filepath)
            accruals = []
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(filepath, sheet_name=sheet_name)
                # Парсинг зависит от структуры - базовая реализация
                for _, row in df.iterrows():
                    try:
                        accrual = {
                            'date': self._parse_date(row.get('Дата', '')),
                            'type': str(row.get('Тип операции', '') or sheet_name),
                            'amount': self._parse_float(row.get('Сумма', 0) or row.get('Начислено', 0)),
                            'description': str(row.get('Описание', ''))
                        }
                        if accrual['amount'] != 0:
                            accruals.append(accrual)
                    except (ValueError, TypeError, KeyError):
                        continue

            self.parsed_data['accruals'].extend(accruals)
            return {'type': 'accruals', 'count': len(accruals), 'data': accruals}
        except Exception as e:
            raise Exception(f"Ошибка парсинга начислений: {str(e)}")
    
    def parse_unit_economics(self, filepath):
        """Парсинг отчета по юнит-экономике"""
        try:
            excel_file = pd.ExcelFile(filepath)
            unit_data = []
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(filepath, sheet_name=sheet_name)
                for _, row in df.iterrows():
                    try:
                        unit = {
                            'sku': str(row.get('SKU', '')),
                            'product_name': str(row.get('Товар', '') or row.get('Название', '')),
                            'revenue': self._parse_float(row.get('Выручка', 0)),
                            'cost': self._parse_float(row.get('Себестоимость', 0)),
                            'commission': self._parse_float(row.get('Комиссия', 0)),
                            'logistics': self._parse_float(row.get('Логистика', 0)),
                            'profit': self._parse_float(row.get('Прибыль', 0)),
                            'margin': self._parse_float(row.get('Маржа', 0))
                        }
                        if unit['sku'] and unit['sku'] != 'nan':
                            unit_data.append(unit)
                    except (ValueError, TypeError, KeyError):
                        continue

            self.parsed_data['unit_economics'].extend(unit_data)
            return {'type': 'unit_economics', 'count': len(unit_data), 'data': unit_data}
        except Exception as e:
            raise Exception(f"Ошибка парсинга юнит-экономики: {str(e)}")
    
    def parse_sales_analytics_period(self, filepath):
        """Парсинг отчета аналитики продаж за период (месяц)"""
        try:
            # Пробуем разные способы чтения файла
            df = None
            engines = ['openpyxl', 'xlrd']
            
            for engine in engines:
                try:
                    # Пробуем читать с разными параметрами
                    excel_file = pd.ExcelFile(filepath, engine=engine)
                    if len(excel_file.sheet_names) > 0:
                        # Пробуем первый лист
                        df = pd.read_excel(filepath, sheet_name=0, engine=engine, header=None)
                        # Ищем строку с заголовками
                        header_row = None
                        for i in range(min(10, len(df))):
                            row_str = ' '.join([str(x) for x in df.iloc[i].values if pd.notna(x)]).lower()
                            if any(keyword in row_str for keyword in ['дата', 'date', 'выручка', 'revenue', 'заказы', 'orders']):
                                header_row = i
                                break
                        
                        if header_row is not None:
                            df = pd.read_excel(filepath, sheet_name=0, engine=engine, header=header_row)
                        break
                except Exception as e:
                    continue
            
            # Если стандартные методы не работают, пробуем читать как CSV или использовать другие подходы
            if df is None:
                # Пробуем прочитать как бинарный файл и восстановить
                try:
                    import zipfile
                    with zipfile.ZipFile(filepath, 'r') as zip_ref:
                        pass
                except (OSError, zipfile.BadZipFile):
                    pass
            
            if df is None:
                # Если не удалось прочитать, создаем запись о файле
                return {
                    'type': 'sales_analytics_period',
                    'count': 0,
                    'data': [],
                    'note': 'Файл не удалось прочитать. Возможно, файл поврежден или имеет нестандартный формат.',
                    'filename': os.path.basename(filepath)
                }
            
            # Нормализация названий колонок
            df.columns = df.columns.str.strip().str.replace('"', '')
            
            # Парсим данные аналитики
            analytics_data = []
            for _, row in df.iterrows():
                try:
                    # Пытаемся найти стандартные поля аналитики
                    period_data = {
                        'period_start': self._parse_date(row.get('Период начала', '') or row.get('Дата начала', '') or row.get('Начало периода', '')),
                        'period_end': self._parse_date(row.get('Период окончания', '') or row.get('Дата окончания', '') or row.get('Конец периода', '')),
                        'revenue': self._parse_float(row.get('Выручка', 0) or row.get('Revenue', 0) or row.get('Сумма', 0)),
                        'orders_count': self._parse_int(row.get('Заказы', 0) or row.get('Orders', 0) or row.get('Количество заказов', 0)),
                        'avg_order_value': self._parse_float(row.get('Средний чек', 0) or row.get('Avg Order Value', 0) or row.get('AOV', 0)),
                        'products_sold': self._parse_int(row.get('Товаров продано', 0) or row.get('Products Sold', 0) or row.get('Количество товаров', 0)),
                        'conversion_rate': self._parse_float(row.get('Конверсия', 0) or row.get('Conversion Rate', 0)),
                        'cancellation_rate': self._parse_float(row.get('Отмены', 0) or row.get('Cancellation Rate', 0))
                    }
                    
                    # Если есть хотя бы одно значимое значение, добавляем запись
                    if (period_data['revenue'] > 0 or period_data['orders_count'] > 0 or 
                        period_data['period_start'] is not None):
                        analytics_data.append(period_data)
                except Exception as e:
                    continue
            
            self.parsed_data['sales_analytics_period'].extend(analytics_data)
            return {
                'type': 'sales_analytics_period',
                'count': len(analytics_data),
                'data': analytics_data
            }
        except Exception as e:
            # В случае ошибки возвращаем информацию о файле
            return {
                'type': 'sales_analytics_period',
                'count': 0,
                'data': [],
                'error': str(e),
                'filename': os.path.basename(filepath)
            }
    
    def parse_sales_analytics_daily(self, filepath):
        """Парсинг отчета аналитики продаж по дням"""
        try:
            # Пробуем разные способы чтения файла
            df = None
            engines = ['openpyxl', 'xlrd']
            
            for engine in engines:
                try:
                    excel_file = pd.ExcelFile(filepath, engine=engine)
                    if len(excel_file.sheet_names) > 0:
                        # Пробуем первый лист
                        df = pd.read_excel(filepath, sheet_name=0, engine=engine, header=None)
                        # Ищем строку с заголовками
                        header_row = None
                        for i in range(min(10, len(df))):
                            row_str = ' '.join([str(x) for x in df.iloc[i].values if pd.notna(x)]).lower()
                            if any(keyword in row_str for keyword in ['дата', 'date', 'выручка', 'revenue', 'заказы', 'orders', 'день', 'day']):
                                header_row = i
                                break
                        
                        if header_row is not None:
                            df = pd.read_excel(filepath, sheet_name=0, engine=engine, header=header_row)
                        break
                except Exception as e:
                    continue
            
            if df is None:
                # Если не удалось прочитать, создаем запись о файле
                return {
                    'type': 'sales_analytics_daily',
                    'count': 0,
                    'data': [],
                    'note': 'Файл не удалось прочитать. Возможно, файл поврежден или имеет нестандартный формат.',
                    'filename': os.path.basename(filepath)
                }
            
            # Нормализация названий колонок
            df.columns = df.columns.str.strip().str.replace('"', '')
            
            # Парсим данные аналитики по дням
            daily_data = []
            for _, row in df.iterrows():
                try:
                    # Пытаемся найти стандартные поля аналитики
                    day_data = {
                        'date': self._parse_date(row.get('Дата', '') or row.get('Date', '') or row.get('День', '')),
                        'revenue': self._parse_float(row.get('Выручка', 0) or row.get('Revenue', 0) or row.get('Сумма', 0)),
                        'orders_count': self._parse_int(row.get('Заказы', 0) or row.get('Orders', 0) or row.get('Количество заказов', 0)),
                        'avg_order_value': self._parse_float(row.get('Средний чек', 0) or row.get('Avg Order Value', 0) or row.get('AOV', 0)),
                        'products_sold': self._parse_int(row.get('Товаров продано', 0) or row.get('Products Sold', 0) or row.get('Количество товаров', 0)),
                        'conversion_rate': self._parse_float(row.get('Конверсия', 0) or row.get('Conversion Rate', 0)),
                        'cancellation_rate': self._parse_float(row.get('Отмены', 0) or row.get('Cancellation Rate', 0))
                    }
                    
                    # Если есть дата или значимые данные, добавляем запись
                    if day_data['date'] is not None or day_data['revenue'] > 0 or day_data['orders_count'] > 0:
                        daily_data.append(day_data)
                except Exception as e:
                    continue
            
            self.parsed_data['sales_analytics_daily'].extend(daily_data)
            return {
                'type': 'sales_analytics_daily',
                'count': len(daily_data),
                'data': daily_data
            }
        except Exception as e:
            # В случае ошибки возвращаем информацию о файле
            return {
                'type': 'sales_analytics_daily',
                'count': 0,
                'data': [],
                'error': str(e),
                'filename': os.path.basename(filepath)
            }
    
    def parse_file(self, filepath):
        """Главный метод парсинга - определяет тип и парсит"""
        report_type = self.detect_report_type(filepath)
        
        if report_type == 'orders':
            return self.parse_orders(filepath)
        elif report_type == 'returns':
            return self.parse_returns(filepath)
        elif report_type == 'stocks':
            return self.parse_stocks(filepath)
        elif report_type == 'accruals':
            return self.parse_accruals(filepath)
        elif report_type == 'unit_economics':
            return self.parse_unit_economics(filepath)
        elif report_type == 'sales_analytics_period':
            return self.parse_sales_analytics_period(filepath)
        elif report_type == 'sales_analytics_daily':
            return self.parse_sales_analytics_daily(filepath)
        # API JSON типы
        elif report_type in ('returns_fbo_api', 'returns_fbs_api', 'returns_api'):
            return self.parse_api_returns(filepath)
        elif report_type in ('postings_fbo_api', 'postings_fbs_api', 'postings_api'):
            return self.parse_api_postings(filepath)
        elif report_type == 'stocks_api':
            return self.parse_api_stocks(filepath)
        elif report_type == 'finance_api':
            return self.parse_api_finance(filepath)
        elif report_type.endswith('_api') or report_type == 'unknown_api':
            # Попытка парсить как универсальный JSON
            return self.parse_api_generic(filepath)
        else:
            raise Exception(f"Неизвестный тип отчета: {report_type}")
    
    def parse_api_returns(self, filepath):
        """Парсинг JSON возвратов из API"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            items = data.get('items', data.get('raw_response', {}).get('result', {}).get('returns', []))
            if not items:
                items = data.get('raw_response', {}).get('returns', [])
            
            returns = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                try:
                    return_data = {
                        'return_id': str(item.get('return_id', '') or item.get('id', '')),
                        'shipment_number': str(item.get('posting_number', '') or item.get('shipment_number', '')),
                        'sku': str(item.get('sku', '') or item.get('product', {}).get('sku', '')),
                        'product_name': str(item.get('product_name', '') or item.get('product', {}).get('name', '')),
                        'return_date': self._parse_api_date(item.get('accepted_from_customer_moment') or item.get('return_date') or item.get('created_at')),
                        'return_reason': str(item.get('return_reason_name', '') or item.get('return_reason', '')),
                        'status': str(item.get('status', '') or item.get('state', '')),
                        'quantity': self._parse_int(item.get('quantity', 1)),
                        'price': self._parse_float(item.get('price', 0) or (item.get('product', {}) or {}).get('price', 0))
                    }
                    if return_data['return_id'] or return_data['shipment_number']:
                        returns.append(return_data)
                except (ValueError, TypeError, KeyError):
                    continue
            
            self.parsed_data['returns'].extend(returns)
            return {'type': 'returns', 'count': len(returns), 'data': returns, 'source': 'api'}
        except Exception as e:
            raise Exception(f"Ошибка парсинга API возвратов: {str(e)}")
    
    def parse_api_postings(self, filepath):
        """Парсинг JSON отправлений/заказов из API"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # items уже содержит массив отправлений
            items = data.get('items', [])
            if not items and 'raw_response' in data:
                raw = data['raw_response']
                if isinstance(raw, dict):
                    items = raw.get('result', {}).get('postings', raw.get('postings', []))
            
            data_type = data.get('data_type', 'postings')
            target_key = 'postings_fbo' if 'fbo' in data_type else 'postings_fbs'
            
            orders = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                try:
                    # Финансовые данные из отправления
                    financial = item.get('financial_data', {}) or {}
                    financial_products = financial.get('products', []) or []
                    
                    # Товары из самого отправления
                    posting_products = item.get('products', []) or []
                    
                    # Если есть товары в отправлении, создаём запись для каждого
                    if posting_products:
                        for i, prod in enumerate(posting_products):
                            # Пытаемся найти соответствующие финансовые данные
                            fin_prod = {}
                            if financial_products and i < len(financial_products):
                                fin_prod = financial_products[i]
                            elif financial_products:
                                # Ищем по SKU
                                prod_sku = str(prod.get('sku', ''))
                                for fp in financial_products:
                                    if str(fp.get('product_id', '')) == prod_sku or str(fp.get('sku', '')) == prod_sku:
                                        fin_prod = fp
                                        break
                            
                            # Объединяем данные продукта и финансовые данные
                            merged_product = {**prod, **fin_prod}
                            order = self._parse_posting_item(item, merged_product, financial)
                            if order:
                                orders.append(order)
                    else:
                        # Если товаров нет, создаём одну запись
                        order = self._parse_posting_item(item, {}, financial)
                        if order:
                            orders.append(order)
                except (ValueError, TypeError, KeyError) as e:
                    continue
            
            # Добавляем в orders для единообразия аналитики
            self.parsed_data['orders'].extend(orders)
            if target_key in self.parsed_data:
                self.parsed_data[target_key].extend(orders)
            
            return {'type': 'orders', 'count': len(orders), 'data': orders, 'source': 'api'}
        except Exception as e:
            raise Exception(f"Ошибка парсинга API отправлений: {str(e)}")
    
    def _parse_posting_item(self, posting, product, financial):
        """Парсинг одного товара из отправления"""
        try:
            # Безопасное получение вложенных значений
            delivery_method = posting.get('delivery_method')
            if isinstance(delivery_method, dict):
                delivery_method_name = str(delivery_method.get('name', '') or '')
            else:
                delivery_method_name = str(delivery_method or '')
            
            analytics_data = posting.get('analytics_data')
            if not isinstance(analytics_data, dict):
                analytics_data = {}
            
            order = {
                'order_number': str(posting.get('order_id', '') or ''),
                'shipment_number': str(posting.get('posting_number', '') or ''),
                'accepted_date': self._parse_api_date(posting.get('in_process_at') or posting.get('created_at')),
                'shipment_date': self._parse_api_date(posting.get('shipment_date')),
                'status': str(posting.get('status', '') or ''),
                'delivery_date': self._parse_api_date(posting.get('delivering_date')),
                'total_amount': self._parse_float(product.get('price', 0)) * self._parse_int(product.get('quantity', 1)),  # Цена * количество
                'currency': str(product.get('currency_code') or posting.get('currency_code') or 'RUB'),
                'product_name': str(product.get('name', '') or posting.get('product_name', '') or ''),
                'sku': str(product.get('sku', '') or posting.get('sku', '') or ''),
                'article': str(product.get('offer_id', '') or posting.get('offer_id', '') or ''),
                'seller_price': (self._parse_float(product.get('old_price') if product.get('old_price') is not None else product.get('price', 0))) * self._parse_int(product.get('quantity', 1)),  # Цена до скидок * количество
                'paid_by_customer': self._parse_float(product.get('price', 0)) * self._parse_int(product.get('quantity', 1)),  # Цена * количество
                'quantity': self._parse_int(product.get('quantity', 1)),
                'discount_percent': self._parse_float(product.get('total_discount_percent') if product.get('total_discount_percent') is not None else product.get('discount_percent', 0)),
                'discount_rub': self._parse_float(product.get('total_discount_value') if product.get('total_discount_value') is not None else (product.get('discount_value', 0) * self._parse_int(product.get('quantity', 1)))),
                'promotions': ', '.join(product.get('actions', [])) if isinstance(product.get('actions'), list) and product.get('actions') else '',
                'delivery_method': delivery_method_name,
                'customer_segment': 'Премиум' if analytics_data.get('is_premium') else '',
                'payment_method': str(analytics_data.get('payment_type_group_name', '')),
                'region': str(analytics_data.get('region', '') or ''),
                'city': str(analytics_data.get('city', '') or ''),
                'warehouse': str(analytics_data.get('warehouse_name', '') or ''),
                'delivery_time': 0,
                'is_premium': bool(analytics_data.get('is_premium', False)),
                'is_buyout': True,
                'commission': self._parse_float(product.get('commission_amount') if product.get('commission_amount') is not None else 0),  # Из financial_data (уже общая сумма)
                'payout': self._parse_float(product.get('payout') if product.get('payout') is not None else 0),  # Из financial_data (уже общая сумма)
                'source': 'api'
            }
            
            if order['shipment_number'] or order['order_number']:
                return order
            return None
        except (ValueError, TypeError, KeyError) as e:
            return None
    
    def parse_api_stocks(self, filepath):
        """Парсинг JSON остатков из API"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            items = data.get('items', data.get('raw_response', {}).get('result', {}).get('items', []))
            if not items:
                items = data.get('raw_response', {}).get('items', [])
            
            stocks = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                try:
                    # Остатки могут быть по складам
                    stock_list = item.get('stocks', [])
                    if stock_list:
                        for stock_entry in stock_list:
                            stock = {
                                'product_name': str(item.get('product_name', '') or item.get('name', '')),
                                'sku': str(item.get('sku', '') or item.get('product_id', '')),
                                'offer_id': str(item.get('offer_id', '')),
                                'warehouse': str(stock_entry.get('warehouse_name', '') or stock_entry.get('type', '')),
                                'available': self._parse_int(stock_entry.get('present', 0) or stock_entry.get('free_to_sell_amount', 0)),
                                'reserved': self._parse_int(stock_entry.get('reserved', 0)),
                                'in_transit': self._parse_int(stock_entry.get('incoming', 0))
                            }
                            if stock['sku']:
                                stocks.append(stock)
                    else:
                        # Одна запись без разбивки по складам
                        stock = {
                            'product_name': str(item.get('product_name', '') or item.get('name', '')),
                            'sku': str(item.get('sku', '') or item.get('product_id', '')),
                            'offer_id': str(item.get('offer_id', '')),
                            'warehouse': '',
                            'available': self._parse_int(item.get('present', 0) or item.get('free_to_sell_amount', 0)),
                            'reserved': self._parse_int(item.get('reserved', 0)),
                            'in_transit': self._parse_int(item.get('incoming', 0))
                        }
                        if stock['sku']:
                            stocks.append(stock)
                except (ValueError, TypeError, KeyError):
                    continue
            
            self.parsed_data['stocks'].extend(stocks)
            return {'type': 'stocks', 'count': len(stocks), 'data': stocks, 'source': 'api'}
        except Exception as e:
            raise Exception(f"Ошибка парсинга API остатков: {str(e)}")
    
    def parse_api_finance(self, filepath):
        """Парсинг JSON финансовых транзакций из API"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Структура: items -> [{ operations: [...] }]
            items = data.get('items', [])
            operations = []
            
            # Извлекаем операции из вложенной структуры
            for item in items:
                if isinstance(item, dict) and 'operations' in item:
                    operations.extend(item.get('operations', []))
                elif isinstance(item, dict) and 'operation_id' in item:
                    # Если сам item это операция
                    operations.append(item)
            
            # Если операции не найдены, проверяем raw_response
            if not operations and 'raw_response' in data:
                raw = data['raw_response']
                if isinstance(raw, dict):
                    result = raw.get('result', raw)
                    if isinstance(result, dict) and 'operations' in result:
                        operations = result.get('operations', [])
                    elif isinstance(result, list):
                        for r in result:
                            if isinstance(r, dict) and 'operations' in r:
                                operations.extend(r.get('operations', []))
            
            finance = []
            for item in operations:
                if not isinstance(item, dict):
                    continue
                try:
                    posting = item.get('posting', {})
                    if not isinstance(posting, dict):
                        posting = {}
                    
                    transaction = {
                        'operation_id': str(item.get('operation_id', '') or item.get('id', '')),
                        'operation_type': str(item.get('operation_type_name', '') or item.get('operation_type', '')),
                        'operation_date': self._parse_api_date(item.get('operation_date') or item.get('created_at')),
                        'amount': self._parse_float(item.get('amount', 0)),
                        'accrual': self._parse_float(item.get('accruals_for_sale', 0)),
                        'sale_commission': self._parse_float(item.get('sale_commission', 0)),
                        'delivery_charge': self._parse_float(item.get('delivery_charge', 0)),
                        'return_delivery_charge': self._parse_float(item.get('return_delivery_charge', 0)),
                        'posting_number': str(posting.get('posting_number', '')),
                        'sku': '',
                        'description': str(item.get('operation_type_name', ''))
                    }
                    
                    # Извлекаем SKU из items внутри операции
                    op_items = item.get('items', [])
                    if op_items and isinstance(op_items, list):
                        skus = [str(i.get('sku', '')) for i in op_items if isinstance(i, dict)]
                        transaction['sku'] = ', '.join(filter(None, skus))
                    
                    if transaction['operation_id'] or transaction['amount'] != 0:
                        finance.append(transaction)
                except (ValueError, TypeError, KeyError):
                    continue
            
            self.parsed_data['finance'].extend(finance)
            # Также добавляем в accruals для совместимости
            self.parsed_data['accruals'].extend([{
                'date': t['operation_date'],
                'type': t['operation_type'],
                'amount': t['amount'],
                'description': t['description']
            } for t in finance])
            
            return {'type': 'finance', 'count': len(finance), 'data': finance, 'source': 'api'}
        except Exception as e:
            raise Exception(f"Ошибка парсинга API финансов: {str(e)}")
    
    def parse_api_generic(self, filepath):
        """Универсальный парсинг JSON из API когда тип не определён"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data_type = data.get('data_type', 'unknown')
            items = data.get('items', [])
            
            if not items and 'raw_response' in data:
                raw = data['raw_response']
                if isinstance(raw, dict):
                    # Ищем данные в стандартных местах
                    for key in ['result', 'items', 'postings', 'returns', 'operations']:
                        if key in raw:
                            items = raw[key]
                            if isinstance(items, dict):
                                items = items.get('items', items.get('postings', items.get('returns', [items])))
                            break
            
            count = len(items) if isinstance(items, list) else (1 if items else 0)
            
            return {
                'type': data_type,
                'count': count,
                'data': items if isinstance(items, list) else [items] if items else [],
                'source': 'api',
                'note': 'Generic API data parsing'
            }
        except Exception as e:
            raise Exception(f"Ошибка парсинга API данных: {str(e)}")
    
    def _parse_api_date(self, value):
        """Парсинг даты из API (ISO 8601 формат)"""
        if not value or pd.isna(value) or str(value).strip() == '':
            return None
        try:
            if isinstance(value, str):
                # ISO 8601 форматы
                for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                    try:
                        return pd.to_datetime(value.replace('Z', '+00:00').split('+')[0], format=fmt.replace('Z', '').replace('%z', ''))
                    except (ValueError, TypeError):
                        continue
            return pd.to_datetime(value)
        except (ValueError, TypeError):
            return None
    
    def _parse_date(self, value):
        """Парсинг даты с поддержкой различных форматов"""
        if pd.isna(value) or value == '' or str(value).strip() == '':
            return None
        try:
            # Если это уже datetime объект
            if isinstance(value, pd.Timestamp) or isinstance(value, datetime):
                return pd.to_datetime(value)
            
            if isinstance(value, str):
                value = value.strip()
                # Различные форматы дат (в порядке приоритета)
                formats = [
                    '%Y-%m-%d %H:%M:%S',  # 2025-01-15 12:30:45
                    '%Y-%m-%d',           # 2025-01-15
                    '%d.%m.%Y %H:%M:%S',  # 15.01.2025 12:30:45
                    '%d.%m.%Y',           # 15.01.2025
                    '%d/%m/%Y %H:%M:%S',  # 15/01/2025 12:30:45
                    '%d/%m/%Y',           # 15/01/2025
                    '%Y.%m.%d',           # 2025.01.15
                    '%d-%m-%Y',           # 15-01-2025
                    '%Y/%m/%d',           # 2025/01/15
                ]
                
                for fmt in formats:
                    try:
                        parsed = pd.to_datetime(value, format=fmt)
                        # Проверяем, что дата разумная (не слишком старая и не в будущем)
                        if parsed.year >= 2020 and parsed.year <= 2030:
                            return parsed
                    except (ValueError, TypeError):
                        continue
                
                # Если не удалось распарсить с форматом, пробуем автоматический парсинг
                try:
                    parsed = pd.to_datetime(value, infer_datetime_format=True)
                    if parsed.year >= 2020 and parsed.year <= 2030:
                        return parsed
                except:
                    pass
            
            # Для не-строковых значений (числа, datetime объекты)
            parsed = pd.to_datetime(value)
            if parsed.year >= 2020 and parsed.year <= 2030:
                return parsed
            return None
        except (ValueError, TypeError, AttributeError):
            return None
    
    def _parse_float(self, value):
        """Парсинг числа с плавающей точкой"""
        if pd.isna(value) or value == '' or value is None:
            return 0.0
        try:
            if isinstance(value, str):
                value = value.replace(',', '.').replace(' ', '').strip('"')
            result = float(value)
            # Проверяем на NaN и Infinity
            if pd.isna(result) or result != result:  # NaN check
                return 0.0
            return result
        except (ValueError, TypeError):
            return 0.0
    
    def _parse_int(self, value):
        """Парсинг целого числа"""
        if pd.isna(value) or value == '':
            return 0
        try:
            if isinstance(value, str):
                value = value.replace(',', '').replace(' ', '').strip('"')
            return int(float(value))
        except (ValueError, TypeError):
            return 0
    
    def get_parsed_data(self):
        """Получить все распарсенные данные"""
        return self.parsed_data
