"""
Модуль аналитики для отчетов Ozon
Рассчитывает ключевые метрики и показатели
"""
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict
from .marketplace_metrics import MarketplaceMetrics
from .cohort_analysis import CohortAnalysis
from .period_comparison import PeriodComparison
from .forecasting import Forecasting
from .competitor_analysis import CompetitorAnalysis
from .seasonality_analysis import SeasonalityAnalysis
from .unit_economics import UnitEconomicsCalculator


class OzonAnalytics:
    """Класс для расчета аналитики по данным Ozon"""
    
    def __init__(self, unit_economics_manager=None):
        self.orders = []
        self.returns = []
        self.stocks = []
        self.accruals = []
        self.unit_economics = []
        self.sales_analytics_period = []
        self.sales_analytics_daily = []
        self.date_from = None
        self.date_to = None
        self.unit_economics_calculator = UnitEconomicsCalculator(unit_economics_manager)
    
    def load_data(self, parser_data):
        """Загружает данные из парсера"""
        self.orders = parser_data.get('orders', [])
        self.returns = parser_data.get('returns', [])
        self.stocks = parser_data.get('stocks', [])
        self.accruals = parser_data.get('accruals', [])
        self.unit_economics = parser_data.get('unit_economics', [])
        self.sales_analytics_period = parser_data.get('sales_analytics_period', [])
        self.sales_analytics_daily = parser_data.get('sales_analytics_daily', [])
    
    def set_date_filter(self, date_from=None, date_to=None):
        """Устанавливает фильтр по дате для аналитики"""
        self.date_from = date_from
        self.date_to = date_to
    
    def _filter_by_date(self, df, date_column='delivery_date'):
        """Фильтрует DataFrame по дате"""
        if df.empty:
            return df
        
        if date_column not in df.columns:
            return df
        
        if not self.date_from and not self.date_to:
            return df
        
        # Создаем копию для безопасной работы
        df_filtered = df.copy()
        
        # Конвертируем дату в datetime (поддерживаем строки, datetime объекты, Timestamp)
        if df_filtered[date_column].dtype == 'object':
            # Пробуем конвертировать строки в datetime
            df_filtered[date_column] = pd.to_datetime(df_filtered[date_column], errors='coerce', utc=True)
        elif not pd.api.types.is_datetime64_any_dtype(df_filtered[date_column]):
            # Если это не datetime тип, пробуем конвертировать
            df_filtered[date_column] = pd.to_datetime(df_filtered[date_column], errors='coerce', utc=True)
        
        # Нормализуем timezone для сравнения (убираем timezone, оставляем только дату)
        if pd.api.types.is_datetime64_any_dtype(df_filtered[date_column]):
            df_filtered[date_column] = df_filtered[date_column].dt.tz_localize(None)
        
        # Фильтруем по дате начала
        if self.date_from:
            date_from_dt = pd.to_datetime(self.date_from)
            # Фильтруем только записи с валидными датами
            mask = df_filtered[date_column].notna() & (df_filtered[date_column] >= date_from_dt)
            df_filtered = df_filtered[mask]
        
        # Фильтруем по дате окончания
        if self.date_to:
            date_to_dt = pd.to_datetime(self.date_to)
            # Добавляем один день, чтобы включить весь день окончания
            date_to_dt = date_to_dt + timedelta(days=1)
            # Фильтруем только записи с валидными датами
            mask = df_filtered[date_column].notna() & (df_filtered[date_column] < date_to_dt)
            df_filtered = df_filtered[mask]
        
        return df_filtered
    
    def get_full_analytics(self, store_data=None):
        """Полная аналитика по всем данным"""
        analytics = {
            'sales_metrics': self.get_sales_metrics(),
            'product_metrics': self.get_product_metrics(),
            'financial_metrics': self.get_financial_metrics(),
            'logistics_metrics': self.get_logistics_metrics(),
            'customer_metrics': self.get_customer_metrics(),
            'inventory_metrics': self.get_inventory_metrics(),
            'returns_metrics': self.get_returns_metrics(),
            'time_series': self.get_time_series(),
            'sales_analytics': self.get_sales_analytics()
        }
        
        # Добавляем расширенные метрики маркетплейса
        try:
            marketplace_metrics = self.get_marketplace_metrics(store_data)
            analytics['marketplace_metrics'] = marketplace_metrics
        except Exception as e:
            # Если ошибка, не прерываем выполнение
            print(f"Ошибка расчета расширенных метрик: {e}")
            analytics['marketplace_metrics'] = {}
        
        # Добавляем юнит-экономику
        try:
            unit_economics = self.get_unit_economics()
            analytics['unit_economics'] = unit_economics
        except Exception as e:
            print(f"Ошибка расчета юнит-экономики: {e}")
            analytics['unit_economics'] = {}
        
        return analytics
    
    def get_cohort_analysis(self, date_from=None, date_to=None):
        """Получить когортный анализ"""
        try:
            cohort_analyzer = CohortAnalysis(self.orders)
            return cohort_analyzer.calculate_cohorts(date_from, date_to)
        except Exception as e:
            print(f"Ошибка когортного анализа: {e}")
            return {}
    
    def get_period_comparison(self, date_from, date_to, comparison_type='previous'):
        """Получить сравнение периодов"""
        try:
            period_comparison = PeriodComparison(self)
            return period_comparison.compare_periods(date_from, date_to, comparison_type)
        except Exception as e:
            print(f"Ошибка сравнения периодов: {e}")
            return {}
    
    def get_forecast(self, forecast_type='sales', days_ahead=30, **kwargs):
        """Получить прогноз"""
        try:
            forecaster = Forecasting(self.orders, self.stocks)
            
            if forecast_type == 'sales':
                return forecaster.forecast_sales_simple(
                    days_ahead=days_ahead,
                    date_from=kwargs.get('date_from'),
                    date_to=kwargs.get('date_to')
                )
            elif forecast_type == 'inventory':
                return forecaster.forecast_inventory(
                    sku=kwargs.get('sku'),
                    days_ahead=days_ahead
                )
            elif forecast_type == 'anomalies':
                return forecaster.detect_anomalies(
                    date_from=kwargs.get('date_from'),
                    date_to=kwargs.get('date_to')
                )
            elif forecast_type == 'seasonality':
                return forecaster.forecast_seasonality(days_ahead=days_ahead)
            else:
                return {}
        except Exception as e:
            print(f"Ошибка прогнозирования: {e}")
            return {}
    
    def get_seasonality_analysis(self, date_from=None, date_to=None):
        """Получить анализ сезонности и спадов"""
        try:
            seasonality_analyzer = SeasonalityAnalysis(self.orders)
            return seasonality_analyzer.analyze_sales_drop(date_from, date_to)
        except Exception as e:
            print(f"Ошибка анализа сезонности: {e}")
            return {}
    
    def get_competitor_analysis(self, competitor_data=None, store_data=None):
        """Получить конкурентный анализ"""
        try:
            # Подготавливаем собственные данные
            own_data = self._prepare_own_data_for_competitor_analysis(store_data)
            
            # Создаем анализатор
            competitor_analyzer = CompetitorAnalysis(self.orders, store_data)
            
            # Получаем анализ
            if competitor_data:
                summary = competitor_analyzer.get_competitive_summary(own_data, competitor_data)
                recommendations = competitor_analyzer.get_recommendations(summary)
                return {
                    'summary': summary,
                    'recommendations': recommendations
                }
            else:
                return {
                    'summary': {},
                    'recommendations': [],
                    'note': 'Данные о конкурентах не предоставлены. Для полного анализа необходимо собрать данные о конкурентах.'
                }
        except Exception as e:
            print(f"Ошибка конкурентного анализа: {e}")
            return {}
    
    def _prepare_own_data_for_competitor_analysis(self, store_data):
        """Подготавливает собственные данные для конкурентного анализа"""
        own_data = {
            'products': {},
            'rating': None,
            'sales': {}
        }
        
        # Получаем данные о товарах из заказов
        if self.orders:
            df = pd.DataFrame(self.orders)
            delivered_mask = df['status'].apply(self._is_delivered_status)
            delivered = df[delivered_mask]
            
            if not delivered.empty:
                # Группируем по SKU
                product_stats = delivered.groupby('sku').agg({
                    'seller_price': 'mean',
                    'paid_by_customer': ['sum', 'mean']
                })
                
                for sku, stats in product_stats.iterrows():
                    own_data['products'][sku] = {
                        'price': float(stats[('seller_price', 'mean')]),
                        'revenue': float(stats[('paid_by_customer', 'sum')]),
                        'avg_price': float(stats[('paid_by_customer', 'mean')])
                    }
                    
                    own_data['sales'][sku] = float(stats[('paid_by_customer', 'sum')])
        
        # Получаем рейтинг из store_data
        if store_data:
            rating_info = store_data.get('rating_info', {})
            own_data['rating'] = rating_info.get('overall_rating')
        
        return own_data
    
    def get_marketplace_metrics(self, store_data=None):
        """Получить расширенные метрики маркетплейса"""
        if not self.orders:
            return {}
        
        df = pd.DataFrame(self.orders)
        
        # Фильтруем доставленные заказы
        delivered_mask = df['status'].apply(self._is_delivered_status)
        delivered = df[delivered_mask].copy()
        
        # Если выбран период, фильтруем по дате
        if self.date_from or self.date_to:
            delivered['_filter_date'] = delivered.apply(self._get_date_for_filtering, axis=1)
            if '_filter_date' in delivered.columns and not delivered.empty:
                delivered = self._filter_by_date(delivered, '_filter_date')
                delivered = delivered[delivered['_filter_date'].notna()]
            else:
                delivered = delivered.iloc[0:0].copy()
        
        if delivered.empty:
            return {}
        
        # Создаем экземпляр MarketplaceMetrics
        marketplace = MarketplaceMetrics(
            orders=self.orders,
            stocks=self.stocks,
            returns=self.returns,
            unit_economics=self.unit_economics
        )
        
        # Получаем все метрики
        return marketplace.get_all_metrics(delivered, df, store_data)
    
    def _is_delivered_status(self, status):
        """Проверяет, является ли статус доставленным (поддерживает русский и английский)"""
        if not status or pd.isna(status):
            return False
        status_str = str(status).lower().strip()
        # Расширенный список статусов, которые считаются доставленными
        delivered_statuses = [
            'доставлен', 'delivered', 'доставка', 'delivery',
            'client_received', 'получен клиентом', 'получен покупателем',
            'awaiting_delivery', 'ожидает доставки',  # В некоторых случаях это тоже считается
            'cancelled_by_customer', 'отменен покупателем'  # НЕ доставлен, но может быть оплачен
        ]
        # Исключаем явно не доставленные статусы
        not_delivered = [
            'cancelled', 'отменен', 'отменён', 'canceled',
            'returned', 'возврат', 'return',
            'awaiting_packaging', 'ожидает упаковки',
            'awaiting_fulfillment', 'ожидает выполнения'
        ]
        if status_str in not_delivered:
            return False
        return status_str in delivered_statuses
    
    def _get_date_for_filtering(self, row):
        """Получает дату для фильтрации: приоритет delivery_date, затем shipment_date, затем accepted_date"""
        if 'delivery_date' in row and pd.notna(row.get('delivery_date')):
            return row['delivery_date']
        if 'shipment_date' in row and pd.notna(row.get('shipment_date')):
            return row['shipment_date']
        if 'accepted_date' in row and pd.notna(row.get('accepted_date')):
            return row['accepted_date']
        return None
    
    def get_sales_metrics(self):
        """Метрики продаж"""
        if not self.orders:
            return {
                'total_revenue': 0,
                'total_orders': 0,
                'avg_order_value': 0,
                'conversion_rate': 0,
                'cancellation_rate': 0,
                'top_products': {}
            }
        
        df = pd.DataFrame(self.orders)
        
        # Определяем доставленные заказы (поддерживаем русский и английский статусы)
        delivered_mask = df['status'].apply(self._is_delivered_status)
        delivered = df[delivered_mask].copy()
        
        # Если выбран период, фильтруем доставленные заказы
        if self.date_from or self.date_to:
            # Создаем колонку с датой для фильтрации
            delivered['_filter_date'] = delivered.apply(self._get_date_for_filtering, axis=1)
            
            # Фильтруем по дате
            if '_filter_date' in delivered.columns and not delivered.empty:
                delivered = self._filter_by_date(delivered, '_filter_date')
                # Убираем заказы без даты, если период выбран
                delivered = delivered[delivered['_filter_date'].notna()]
            else:
                # Если нет дат вообще, очищаем delivered при выбранном периоде
                delivered = delivered.iloc[0:0].copy()
            
            # Для расчета конверсии используем все заказы, принятые в обработку в выбранном периоде
            # Фильтруем по accepted_date для расчета конверсии
            if 'accepted_date' in df.columns:
                df_filtered_for_conversion = self._filter_by_date(df.copy(), 'accepted_date')
            elif 'shipment_date' in df.columns:
                df_filtered_for_conversion = self._filter_by_date(df.copy(), 'shipment_date')
            else:
                df_filtered_for_conversion = df.copy()
        else:
            # Если период не выбран, используем все данные
            df_filtered_for_conversion = df.copy()
        
        total_revenue = delivered['paid_by_customer'].sum()
        # Считаем уникальные заказы по shipment_number или order_number
        if 'shipment_number' in delivered.columns and delivered['shipment_number'].notna().any():
            unique_orders = delivered['shipment_number'].nunique()
        elif 'order_number' in delivered.columns and delivered['order_number'].notna().any():
            unique_orders = delivered['order_number'].nunique()
        else:
            # Если нет номеров заказов, считаем по строкам (каждая строка = один товар в заказе)
            unique_orders = len(delivered)
        total_orders = unique_orders
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        # Конверсия (отношение доставленных к принятым в обработку)
        # Принятые в обработку = уникальные заказы с датой принятия в выбранном периоде
        accepted_with_date = df_filtered_for_conversion[df_filtered_for_conversion['accepted_date'].notna()]
        if 'shipment_number' in accepted_with_date.columns and accepted_with_date['shipment_number'].notna().any():
            total_accepted = accepted_with_date['shipment_number'].nunique()
        elif 'order_number' in accepted_with_date.columns and accepted_with_date['order_number'].notna().any():
            total_accepted = accepted_with_date['order_number'].nunique()
        else:
            total_accepted = len(accepted_with_date)
        # Конверсия = доставленные / принятые * 100
        conversion_rate = (total_orders / total_accepted * 100) if total_accepted > 0 else 0
        
        # Альтернативный расчет: доставленные / все заказы (включая отмененные)
        if 'shipment_number' in df_filtered_for_conversion.columns and df_filtered_for_conversion['shipment_number'].notna().any():
            total_all_orders = df_filtered_for_conversion['shipment_number'].nunique()
        elif 'order_number' in df_filtered_for_conversion.columns and df_filtered_for_conversion['order_number'].notna().any():
            total_all_orders = df_filtered_for_conversion['order_number'].nunique()
        else:
            total_all_orders = len(df_filtered_for_conversion)
        conversion_rate_all = (total_orders / total_all_orders * 100) if total_all_orders > 0 else 0
        
        # Отмененные заказы в выбранном периоде (поддерживаем русский и английский статусы)
        def _is_cancelled_status(status):
            if not status or pd.isna(status):
                return False
            status_str = str(status).lower().strip()
            return status_str in ['отменён', 'отменен', 'cancelled', 'canceled', 'отмена', 'cancellation']
        
        cancelled_mask = df_filtered_for_conversion['status'].apply(_is_cancelled_status)
        cancelled = df_filtered_for_conversion[cancelled_mask]
        # Считаем уникальные отмененные заказы
        if 'shipment_number' in cancelled.columns and cancelled['shipment_number'].notna().any():
            cancelled_count = cancelled['shipment_number'].nunique()
        elif 'order_number' in cancelled.columns and cancelled['order_number'].notna().any():
            cancelled_count = cancelled['order_number'].nunique()
        else:
            cancelled_count = len(cancelled)
        cancellation_rate = (cancelled_count / total_all_orders * 100) if total_all_orders > 0 else 0
        
        # Продажи по SKU
        sku_sales = delivered.groupby('sku').agg({
            'paid_by_customer': 'sum',
            'quantity': 'sum'
        }).sort_values('paid_by_customer', ascending=False)
        
        top_products = sku_sales.head(10).to_dict('index')
        
        # Получаем названия товаров для топ продуктов
        top_products_with_names = {}
        for sku, v in top_products.items():
            # Ищем название товара в заказах
            product_name = None
            product_row = delivered[delivered['sku'] == sku]
            if not product_row.empty and 'product_name' in product_row.columns:
                product_name = product_row.iloc[0].get('product_name')
                if pd.isna(product_name) or product_name == '':
                    product_name = None
            
            top_products_with_names[str(sku)] = {
                'revenue': float(v['paid_by_customer']), 
                'quantity': int(v['quantity']),
                'product_name': str(product_name) if product_name else None
            }
        
        return {
            'total_revenue': float(total_revenue),
            'total_orders': int(total_orders),
            'avg_order_value': float(avg_order_value),
            'conversion_rate': float(conversion_rate),
            'conversion_rate_all': float(conversion_rate_all),
            'cancellation_rate': float(cancellation_rate),
            'total_accepted': int(total_accepted),
            'total_all_orders': int(total_all_orders),
            'top_products': top_products_with_names
        }
    
    def get_product_metrics(self):
        """Метрики по товарам"""
        if not self.orders:
            return {}
        
        df = pd.DataFrame(self.orders)
        
        # Фильтруем доставленные заказы (поддерживаем русский и английский статусы)
        delivered_mask = df['status'].apply(self._is_delivered_status)
        delivered = df[delivered_mask].copy()
        
        # Если выбран период, фильтруем по дате
        if self.date_from or self.date_to:
            delivered['_filter_date'] = delivered.apply(self._get_date_for_filtering, axis=1)
            if '_filter_date' in delivered.columns and not delivered.empty:
                delivered = self._filter_by_date(delivered, '_filter_date')
                delivered = delivered[delivered['_filter_date'].notna()]
            else:
                delivered = delivered.iloc[0:0].copy()
        
        # Анализ по артикулам
        product_stats = delivered.groupby('article').agg({
            'paid_by_customer': ['sum', 'mean', 'count'],
            'quantity': 'sum',
            'discount_percent': 'mean'
        }).round(2)
        
        # Товары с наибольшей скидкой
        high_discount = delivered[delivered['discount_percent'] > 0].groupby('article').agg({
            'discount_percent': 'mean',
            'quantity': 'sum'
        }).sort_values('discount_percent', ascending=False).head(10)
        
        return {
            'total_products': int(delivered['article'].nunique()),
            'total_skus': int(delivered['sku'].nunique()),
            'avg_discount': float(delivered['discount_percent'].mean()),
            'high_discount_products': high_discount.to_dict('index') if len(high_discount) > 0 else {}
        }
    
    def get_financial_metrics(self):
        """Финансовые метрики"""
        if not self.orders:
            return {}
        
        df = pd.DataFrame(self.orders)
        
        # Фильтруем доставленные заказы (поддерживаем русский и английский статусы)
        delivered_mask = df['status'].apply(self._is_delivered_status)
        delivered = df[delivered_mask].copy()
        
        # Если выбран период, фильтруем по дате
        if self.date_from or self.date_to:
            delivered['_filter_date'] = delivered.apply(self._get_date_for_filtering, axis=1)
            if '_filter_date' in delivered.columns and not delivered.empty:
                delivered = self._filter_by_date(delivered, '_filter_date')
                delivered = delivered[delivered['_filter_date'].notna()]
            else:
                delivered = delivered.iloc[0:0].copy()
        
        # Фильтруем unit_economics по дате если есть
        unit_economics_filtered = self.unit_economics
        if self.unit_economics and (self.date_from or self.date_to):
            unit_df = pd.DataFrame(self.unit_economics)
            # Пробуем разные поля с датами
            date_columns = ['date', 'delivery_date', 'accepted_date', 'created_date']
            for col in date_columns:
                if col in unit_df.columns:
                    unit_df = self._filter_by_date(unit_df, col)
                    unit_economics_filtered = unit_df.to_dict('records')
                    break
        
        # Выручка (то, что заплатил покупатель)
        revenue = delivered['paid_by_customer'].sum()
        
        # Цена продавца (цена до скидок)
        seller_price_total = delivered['seller_price'].sum()
        
        # Общая сумма скидок
        total_discounts = delivered['discount_rub'].sum()
        
        # Проверяем наличие данных юнит-экономики для правильного расчета маржи
        margin_note = None
        if unit_economics_filtered and len(unit_economics_filtered) > 0:
            # Используем данные из юнит-экономики для расчета реальной маржи
            unit_df = pd.DataFrame(unit_economics_filtered)
            total_profit = unit_df['profit'].sum() if 'profit' in unit_df.columns else 0
            total_revenue_unit = unit_df['revenue'].sum() if 'revenue' in unit_df.columns else revenue
            
            # Маржа из юнит-экономики
            margin = float(total_profit)
            margin_percent = (margin / total_revenue_unit * 100) if total_revenue_unit > 0 else 0
        else:
            # Если нет данных юнит-экономики, используем приблизительный расчет
            # Разница между ценой продавца и оплаченной покупателем = скидки
            # Это НЕ маржа, но можно использовать как индикатор
            discount_amount = seller_price_total - revenue
            # Примечание: это не реальная маржа, а разница из-за скидок
            margin = float(discount_amount)
            margin_percent = (margin / seller_price_total * 100) if seller_price_total > 0 else 0
            # Добавляем пометку, что это не полная маржа
            margin_note = "Расчет без учета себестоимости. Используйте отчет юнит-экономики для точной маржи."
        
        # Анализ по способам оплаты
        payment_methods = delivered.groupby('payment_method')['paid_by_customer'].agg(['sum', 'count'])
        
        result = {
            'total_revenue': float(revenue),
            'seller_price_total': float(seller_price_total),
            'total_discounts': float(total_discounts),
            'margin': float(margin),
            'margin_percent': float(margin_percent),
            'payment_methods': payment_methods.to_dict('index') if len(payment_methods) > 0 else {}
        }
        
        if margin_note:
            result['margin_note'] = margin_note
        
        return result
    
    def get_logistics_metrics(self):
        """Метрики логистики"""
        if not self.orders:
            return {}
        
        df = pd.DataFrame(self.orders)
        
        # Фильтруем доставленные заказы (поддерживаем русский и английский статусы)
        delivered_mask = df['status'].apply(self._is_delivered_status)
        delivered = df[delivered_mask].copy()
        
        # Если выбран период, фильтруем по дате
        if self.date_from or self.date_to:
            delivered['_filter_date'] = delivered.apply(self._get_date_for_filtering, axis=1)
            if '_filter_date' in delivered.columns and not delivered.empty:
                delivered = self._filter_by_date(delivered, '_filter_date')
                delivered = delivered[delivered['_filter_date'].notna()]
            else:
                delivered = delivered.iloc[0:0].copy()
        
        # Время доставки
        # Фильтруем только записи с валидными датами
        valid_dates = delivered[
            delivered['delivery_date'].notna() & 
            delivered['shipment_date'].notna()
        ].copy()
        
        if len(valid_dates) > 0:
            try:
                valid_dates['delivery_days'] = (
                    pd.to_datetime(valid_dates['delivery_date']) - 
                    pd.to_datetime(valid_dates['shipment_date'])
                ).dt.days
                
                # Убираем отрицательные значения и выбросы (больше 90 дней)
                valid_delivery_days = valid_dates[
                    (valid_dates['delivery_days'] >= 0) & 
                    (valid_dates['delivery_days'] <= 90)
                ]['delivery_days']
                
                avg_delivery_time = valid_delivery_days.mean() if len(valid_delivery_days) > 0 else 0
            except Exception as e:
                print(f"Ошибка расчета времени доставки: {e}")
                avg_delivery_time = 0
        else:
            avg_delivery_time = 0
        
        # Распределение по способам доставки
        delivery_methods = delivered['delivery_method'].value_counts().to_dict()
        
        # Распределение по складам
        warehouses = delivered['warehouse'].value_counts().to_dict()
        
        # Распределение по регионам
        regions = delivered['region'].value_counts().head(10).to_dict()
        
        # Кластеры доставки
        delivery_clusters = delivered['delivery_time'].value_counts().to_dict()
        
        return {
            'avg_delivery_time_days': float(avg_delivery_time) if not pd.isna(avg_delivery_time) else 0,
            'delivery_methods': delivery_methods,
            'warehouses': warehouses,
            'top_regions': regions,
            'delivery_clusters': delivery_clusters
        }
    
    def get_customer_metrics(self):
        """Метрики по клиентам"""
        if not self.orders:
            return {}
        
        df = pd.DataFrame(self.orders)
        
        # Фильтруем доставленные заказы (поддерживаем русский и английский статусы)
        delivered_mask = df['status'].apply(self._is_delivered_status)
        delivered = df[delivered_mask].copy()
        
        # Если выбран период, фильтруем по дате
        if self.date_from or self.date_to:
            delivered['_filter_date'] = delivered.apply(self._get_date_for_filtering, axis=1)
            if '_filter_date' in delivered.columns and not delivered.empty:
                delivered = self._filter_by_date(delivered, '_filter_date')
                delivered = delivered[delivered['_filter_date'].notna()]
            else:
                delivered = delivered.iloc[0:0].copy()
        
        # Сегменты клиентов
        customer_segments = delivered['customer_segment'].value_counts().to_dict()
        
        # Премиум vs обычные
        premium_count = len(delivered[delivered['is_premium'] == True])
        regular_count = len(delivered[delivered['is_premium'] == False])
        
        # Средний чек по сегментам
        segment_avg = delivered.groupby('customer_segment')['paid_by_customer'].mean().to_dict()
        
        return {
            'customer_segments': customer_segments,
            'premium_customers': int(premium_count),
            'regular_customers': int(regular_count),
            'premium_ratio': float(premium_count / len(delivered) * 100) if len(delivered) > 0 else 0,
            'avg_order_by_segment': {k: float(v) for k, v in segment_avg.items()}
        }
    
    def get_inventory_metrics(self):
        """Метрики по остаткам"""
        if not self.stocks:
            return {}
        
        df = pd.DataFrame(self.stocks)
        
        total_available = df['available'].sum()
        total_reserved = df['reserved'].sum()
        total_in_transit = df['in_transit'].sum()
        
        # Товары с нулевыми остатками
        out_of_stock = len(df[df['available'] == 0])
        
        # Распределение по складам
        warehouse_stocks = df.groupby('warehouse').agg({
            'available': 'sum',
            'reserved': 'sum'
        }).to_dict('index')
        
        return {
            'total_available': int(total_available),
            'total_reserved': int(total_reserved),
            'total_in_transit': int(total_in_transit),
            'out_of_stock_count': int(out_of_stock),
            'warehouse_distribution': warehouse_stocks
        }
    
    def get_returns_metrics(self):
        """Метрики по возвратам"""
        if not self.returns:
            return {}
        
        df = pd.DataFrame(self.returns)
        
        # Фильтруем возвраты по дате (используем дату возврата если есть)
        if self.date_from or self.date_to:
            # Пробуем разные поля с датами
            date_columns = ['return_date', 'date', 'created_date', 'delivery_date']
            for col in date_columns:
                if col in df.columns:
                    df = self._filter_by_date(df, col)
                    break
        
        total_returns = len(df)
        
        # Причины возвратов
        return_reasons = df['return_reason'].value_counts().to_dict() if 'return_reason' in df.columns else {}
        
        # Статусы возвратов
        return_statuses = df['status'].value_counts().to_dict() if 'status' in df.columns else {}
        
        # Сравнение с продажами
        total_orders = len(self.orders) if self.orders else 1
        return_rate = (total_returns / total_orders * 100) if total_orders > 0 else 0
        
        return {
            'total_returns': int(total_returns),
            'return_rate': float(return_rate),
            'return_reasons': return_reasons,
            'return_statuses': return_statuses
        }
    
    def get_time_series(self):
        """Временные ряды для графиков
        
        ВАЖНО: Эта функция объединяет данные из двух источников:
        1. sales_analytics_daily - агрегированные данные по дням (если есть)
        2. orders - детальные данные по заказам (основной источник)
        
        Приоритет: данные из orders (они более полные и актуальные).
        sales_analytics_daily используется только для дополнения пробелов.
        """
        # Собираем данные из всех источников и объединяем их
        daily_revenue_dict = {}  # {date: revenue}
        daily_quantity_dict = {}  # {date: quantity}
        
        # 1. Обрабатываем данные из sales_analytics_daily (если есть)
        if self.sales_analytics_daily and len(self.sales_analytics_daily) > 0:
            for day in self.sales_analytics_daily:
                if day.get('date'):
                    try:
                        date_obj = pd.to_datetime(day['date'])
                        date_str = date_obj.strftime('%Y-%m-%d')
                        
                        # Применяем фильтр по дате если нужно
                        if self.date_from:
                            date_from_dt = pd.to_datetime(self.date_from).date()
                            if date_obj.date() < date_from_dt:
                                continue
                        if self.date_to:
                            date_to_dt = pd.to_datetime(self.date_to).date()
                            if date_obj.date() > date_to_dt:
                                continue
                        
                        revenue = float(day.get('revenue', day.get('paid_by_customer', 0)) or 0)
                        quantity = float(day.get('quantity', day.get('products_sold', 0)) or 0)
                        
                        # Объединяем с существующими данными (суммируем)
                        if date_str in daily_revenue_dict:
                            daily_revenue_dict[date_str] += revenue
                            daily_quantity_dict[date_str] += quantity
                        else:
                            daily_revenue_dict[date_str] = revenue
                            daily_quantity_dict[date_str] = quantity
                    except:
                        continue
        
        # 2. Обрабатываем данные из orders (всегда используем, чтобы дополнить пробелы)
        if self.orders:
            df = pd.DataFrame(self.orders)
            
            # ВАЖНО: Для графика используем ВСЕ заказы с оплатой, не только "доставленные"
            # Фильтруем только явно отмененные или возвращенные заказы
            def is_valid_order(row):
                status = str(row.get('status', '')).lower().strip() if pd.notna(row.get('status')) else ''
                excluded_statuses = ['cancelled', 'отменен', 'отменён', 'canceled', 'returned', 'возврат', 'return']
                if status in excluded_statuses:
                    return False
                paid = float(row.get('paid_by_customer', 0) or 0)
                return paid > 0 or status not in excluded_statuses
            
            valid_mask = df.apply(is_valid_order, axis=1)
            valid_orders = df[valid_mask].copy()
            
            if not valid_orders.empty:
                # Определяем дату для группировки
                valid_orders['date_for_chart'] = None
                
                # Пробуем delivery_date
                if 'delivery_date' in valid_orders.columns:
                    delivery_dates = pd.to_datetime(valid_orders['delivery_date'], errors='coerce')
                    mask = delivery_dates.notna()
                    valid_orders.loc[mask, 'date_for_chart'] = delivery_dates[mask].dt.date
                
                # Заполняем пропуски из shipment_date
                if 'shipment_date' in valid_orders.columns:
                    mask = valid_orders['date_for_chart'].isna()
                    if mask.any():
                        shipment_dates = pd.to_datetime(valid_orders.loc[mask, 'shipment_date'], errors='coerce')
                        valid_mask = shipment_dates.notna()
                        valid_orders.loc[mask & valid_mask, 'date_for_chart'] = shipment_dates[valid_mask].dt.date
                
                # Заполняем пропуски из accepted_date
                if 'accepted_date' in valid_orders.columns:
                    mask = valid_orders['date_for_chart'].isna()
                    if mask.any():
                        accepted_dates = pd.to_datetime(valid_orders.loc[mask, 'accepted_date'], errors='coerce')
                        valid_mask = accepted_dates.notna()
                        valid_orders.loc[mask & valid_mask, 'date_for_chart'] = accepted_dates[valid_mask].dt.date
                
                # Убираем записи без даты
                valid_orders = valid_orders[valid_orders['date_for_chart'].notna()].copy()
                
                if not valid_orders.empty:
                    # Применяем фильтр по дате если нужно
                    if self.date_from:
                        try:
                            date_from_dt = pd.to_datetime(self.date_from).date()
                            valid_orders = valid_orders[valid_orders['date_for_chart'] >= date_from_dt]
                        except:
                            pass
                    
                    if self.date_to:
                        try:
                            date_to_dt = pd.to_datetime(self.date_to).date()
                            valid_orders = valid_orders[valid_orders['date_for_chart'] <= date_to_dt]
                        except:
                            pass
                    
                    if not valid_orders.empty:
                        # Группируем по дате и суммируем
                        daily_sales = valid_orders.groupby('date_for_chart', as_index=False).agg({
                            'paid_by_customer': lambda x: x.fillna(0).sum() if x.notna().any() else 0,
                            'quantity': lambda x: x.fillna(0).sum() if x.notna().any() else 0
                        })
                        
                        # Добавляем данные из orders в общий словарь
                        # ПРИОРИТЕТ: данные из orders (они более полные и актуальные)
                        # sales_analytics_daily используется только для дополнения пробелов
                        for _, row in daily_sales.iterrows():
                            date_str = row['date_for_chart'].strftime('%Y-%m-%d') if hasattr(row['date_for_chart'], 'strftime') else str(row['date_for_chart'])
                            revenue = float(row['paid_by_customer'] or 0)
                            quantity = float(row['quantity'] or 0)
                            
                            # Если данных из sales_analytics_daily нет для этой даты, используем данные из orders
                            # Если данные из orders больше, используем их (приоритет orders)
                            if date_str not in daily_revenue_dict:
                                daily_revenue_dict[date_str] = revenue
                                daily_quantity_dict[date_str] = quantity
                            else:
                                # Используем максимальное значение (данные из orders обычно более полные)
                                if revenue > daily_revenue_dict[date_str]:
                                    daily_revenue_dict[date_str] = revenue
                                    daily_quantity_dict[date_str] = quantity
                                # Или суммируем, если оба источника имеют данные (на случай дублирования)
                                # Но обычно лучше использовать максимальное значение
        
        # 3. Формируем итоговый результат из объединенных данных
        if not daily_revenue_dict:
            return {}
        
        # Преобразуем словари в списки и сортируем по дате
        daily_revenue = [{'date': date, 'paid_by_customer': float(revenue)} 
                        for date, revenue in sorted(daily_revenue_dict.items())]
        daily_quantity = [{'date': date, 'quantity': float(quantity)} 
                         for date, quantity in sorted(daily_quantity_dict.items())]
        
        return {
            'daily_revenue': daily_revenue,
            'daily_quantity': daily_quantity
        }
    
    def get_unit_economics(self):
        """Рассчитывает юнит-экономику на основе себестоимости"""
        if not self.orders:
            return {}
        
        return self.unit_economics_calculator.calculate_unit_economics(
            self.orders,
            date_from=self.date_from,
            date_to=self.date_to
        )
    
    def get_sales_analytics(self):
        """Аналитика из отчетов аналитики продаж"""
        result = {
            'period_data': [],
            'daily_data': [],
            'has_data': False
        }
        
        # Данные за период
        if self.sales_analytics_period:
            result['period_data'] = self.sales_analytics_period
            result['has_data'] = True
        
        # Данные по дням
        if self.sales_analytics_daily:
            # Фильтруем по дате если нужно
            daily_data = self.sales_analytics_daily
            if self.date_from or self.date_to:
                filtered_daily = []
                for day in daily_data:
                    if day.get('date'):
                        day_date = pd.to_datetime(day['date'])
                        if self.date_from:
                            if day_date < pd.to_datetime(self.date_from):
                                continue
                        if self.date_to:
                            if day_date > pd.to_datetime(self.date_to):
                                continue
                    filtered_daily.append(day)
                daily_data = filtered_daily
            
            result['daily_data'] = daily_data
            result['has_data'] = True
            
            # Агрегированные метрики по дням
            if daily_data:
                df_daily = pd.DataFrame(daily_data)
                result['daily_summary'] = {
                    'total_revenue': float(df_daily['revenue'].sum()) if 'revenue' in df_daily.columns else 0,
                    'total_orders': int(df_daily['orders_count'].sum()) if 'orders_count' in df_daily.columns else 0,
                    'avg_daily_revenue': float(df_daily['revenue'].mean()) if 'revenue' in df_daily.columns else 0,
                    'avg_daily_orders': float(df_daily['orders_count'].mean()) if 'orders_count' in df_daily.columns else 0,
                    'days_count': len(daily_data)
                }
        
        return result
