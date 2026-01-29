"""
Расширенные метрики маркетплейса для Ozon
Включает GMV, LTV, CAC, Retention и другие ключевые показатели
"""
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from collections import defaultdict
from .seo_analyzer import SEOAnalyzer
from .review_analyzer import ReviewAnalyzer
from .advertising_analyzer import AdvertisingAnalyzer


class MarketplaceMetrics:
    """Класс для расчета расширенных метрик маркетплейса"""
    
    def __init__(self, orders, stocks, returns, unit_economics=None):
        """
        Инициализация с данными
        
        Args:
            orders: список заказов
            stocks: список остатков
            returns: список возвратов
            unit_economics: данные юнит-экономики (опционально)
        """
        self.orders = orders or []
        self.stocks = stocks or []
        self.returns = returns or []
        self.unit_economics = unit_economics or []
        self.seo_analyzer = SEOAnalyzer()
        self.review_analyzer = ReviewAnalyzer()
        self.advertising_analyzer = AdvertisingAnalyzer()
    
    def calculate_sales_metrics(self, delivered_df):
        """Расчет метрик продаж"""
        if delivered_df.empty:
            return {}
        
        # GMV (Gross Merchandise Value) - общая стоимость товаров до скидок
        gmv = delivered_df['seller_price'].sum() if 'seller_price' in delivered_df.columns else 0
        
        # Net GMV - GMV после скидок (то, что заплатил покупатель)
        net_gmv = delivered_df['paid_by_customer'].sum() if 'paid_by_customer' in delivered_df.columns else 0
        
        # Basket Size - среднее количество товаров в заказе
        if 'shipment_number' in delivered_df.columns and delivered_df['shipment_number'].notna().any():
            orders_df = delivered_df.groupby('shipment_number').agg({
                'quantity': 'sum',
                'paid_by_customer': 'sum'
            })
            basket_size = orders_df['quantity'].mean() if len(orders_df) > 0 else 0
        elif 'order_number' in delivered_df.columns and delivered_df['order_number'].notna().any():
            orders_df = delivered_df.groupby('order_number').agg({
                'quantity': 'sum',
                'paid_by_customer': 'sum'
            })
            basket_size = orders_df['quantity'].mean() if len(orders_df) > 0 else 0
        else:
            basket_size = delivered_df['quantity'].mean() if 'quantity' in delivered_df.columns else 0
        
        # Product Mix - распределение по категориям (если есть поле category)
        product_mix = {}
        if 'category' in delivered_df.columns:
            product_mix = delivered_df.groupby('category')['paid_by_customer'].sum().to_dict()
        elif 'article' in delivered_df.columns:
            # Группируем по артикулам как суррогат категорий
            product_mix = delivered_df.groupby('article')['paid_by_customer'].sum().head(10).to_dict()
        
        return {
            'gmv': float(gmv),
            'net_gmv': float(net_gmv),
            'basket_size': float(basket_size),
            'product_mix': product_mix
        }
    
    def calculate_customer_metrics(self, delivered_df, all_orders_df):
        """Расчет метрик клиентов"""
        if delivered_df.empty:
            return {}
        
        # Определяем уникальных клиентов
        customer_id_col = None
        for col in ['customer_id', 'buyer_id', 'user_id', 'client_id']:
            if col in delivered_df.columns and delivered_df[col].notna().any():
                customer_id_col = col
                break
        
        if not customer_id_col:
            # Если нет customer_id, используем комбинацию полей или считаем по заказам
            return self._calculate_customer_metrics_fallback(delivered_df)
        
        customers_df = delivered_df[delivered_df[customer_id_col].notna()].copy()
        
        if customers_df.empty:
            return {}
        
        # Группируем по клиентам
        customer_stats = customers_df.groupby(customer_id_col).agg({
            'paid_by_customer': ['sum', 'count', 'mean'],
            'delivery_date': ['min', 'max']
        })
        
        customer_stats.columns = ['total_revenue', 'order_count', 'avg_order_value', 'first_order_date', 'last_order_date']
        
        # Repeat Purchase Rate - процент повторных покупок
        repeat_customers = len(customer_stats[customer_stats['order_count'] > 1])
        total_customers = len(customer_stats)
        repeat_purchase_rate = (repeat_customers / total_customers * 100) if total_customers > 0 else 0
        
        # New vs Returning Customers
        new_customers = len(customer_stats[customer_stats['order_count'] == 1])
        returning_customers = repeat_customers
        
        # LTV (Lifetime Value) - средняя пожизненная ценность клиента
        ltv = customer_stats['total_revenue'].mean() if len(customer_stats) > 0 else 0
        
        # Average Days Between Orders - среднее время между заказами
        avg_days_between = 0
        if len(customer_stats) > 0 and 'first_order_date' in customer_stats.columns:
            customer_stats['days_active'] = (
                pd.to_datetime(customer_stats['last_order_date']) - 
                pd.to_datetime(customer_stats['first_order_date'])
            ).dt.days
            # Для клиентов с несколькими заказами
            multi_order_customers = customer_stats[customer_stats['order_count'] > 1]
            if len(multi_order_customers) > 0:
                multi_order_customers['avg_days_between'] = (
                    multi_order_customers['days_active'] / (multi_order_customers['order_count'] - 1)
                )
                avg_days_between = multi_order_customers['avg_days_between'].mean()
        
        # Customer Retention Rate - процент удержания (клиенты, которые вернулись)
        # Для расчета нужны данные за несколько периодов, используем упрощенный расчет
        retention_rate = repeat_purchase_rate  # Упрощенная версия
        
        # Churn Rate - процент оттока (обратное retention)
        churn_rate = 100 - retention_rate
        
        # CAC (Customer Acquisition Cost) - стоимость привлечения клиента
        # Для расчета нужны данные о маркетинговых расходах, используем оценку
        # Если есть данные о комиссиях/расходах, можно использовать их
        cac = None
        if self.unit_economics:
            unit_df = pd.DataFrame(self.unit_economics)
            if 'marketing_cost' in unit_df.columns:
                total_marketing = unit_df['marketing_cost'].sum()
                cac = total_marketing / total_customers if total_customers > 0 else None
        
        # LTV/CAC Ratio
        ltv_cac_ratio = (ltv / cac) if cac and cac > 0 else None
        
        return {
            'repeat_purchase_rate': float(repeat_purchase_rate),
            'new_customers': int(new_customers),
            'returning_customers': int(returning_customers),
            'total_customers': int(total_customers),
            'ltv': float(ltv),
            'cac': float(cac) if cac else None,
            'ltv_cac_ratio': float(ltv_cac_ratio) if ltv_cac_ratio else None,
            'retention_rate': float(retention_rate),
            'churn_rate': float(churn_rate),
            'avg_days_between_orders': float(avg_days_between) if avg_days_between > 0 else None
        }
    
    def _calculate_customer_metrics_fallback(self, delivered_df):
        """Упрощенный расчет метрик клиентов без customer_id"""
        # Используем уникальные заказы как суррогат клиентов
        if 'shipment_number' in delivered_df.columns and delivered_df['shipment_number'].notna().any():
            orders_df = delivered_df.groupby('shipment_number').agg({
                'paid_by_customer': 'sum',
                'quantity': 'sum'
            })
        elif 'order_number' in delivered_df.columns and delivered_df['order_number'].notna().any():
            orders_df = delivered_df.groupby('order_number').agg({
                'paid_by_customer': 'sum',
                'quantity': 'sum'
            })
        else:
            return {}
        
        # LTV как средний чек
        ltv = orders_df['paid_by_customer'].mean() if len(orders_df) > 0 else 0
        
        return {
            'ltv': float(ltv),
            'total_customers': len(orders_df),
            'note': 'Расчет без customer_id, используется упрощенная модель'
        }
    
    def calculate_inventory_metrics(self, delivered_df):
        """Расчет метрик остатков"""
        if not self.stocks:
            return {}
        
        stocks_df = pd.DataFrame(self.stocks)
        if stocks_df.empty:
            return {}
        
        # Inventory Turnover - оборачиваемость запасов
        # Формула: COGS / Average Inventory
        # Используем упрощенную версию: Продажи / Средние остатки
        if not delivered_df.empty and 'quantity' in delivered_df.columns:
            total_sold = delivered_df['quantity'].sum()
            avg_inventory = stocks_df['available'].mean() if 'available' in stocks_df.columns else 0
            inventory_turnover = (total_sold / avg_inventory) if avg_inventory > 0 else 0
        else:
            inventory_turnover = 0
        
        # Days of Inventory (DOI) - дни запасов
        # Формула: (Average Inventory / Daily Sales) * Days in Period
        if not delivered_df.empty and 'quantity' in delivered_df.columns:
            avg_inventory = stocks_df['available'].mean() if 'available' in stocks_df.columns else 0
            # Подсчитываем дни в периоде
            if 'delivery_date' in delivered_df.columns:
                delivered_df['date'] = pd.to_datetime(delivered_df['delivery_date']).dt.date
                days_in_period = (delivered_df['date'].max() - delivered_df['date'].min()).days + 1 if len(delivered_df) > 1 else 1
                daily_sales = delivered_df['quantity'].sum() / days_in_period if days_in_period > 0 else 0
            else:
                daily_sales = delivered_df['quantity'].sum() / 30  # Предполагаем 30 дней
            doi = (avg_inventory / daily_sales) if daily_sales > 0 else 0
        else:
            doi = 0
        
        # Sell-through Rate - процент продажи от остатков
        total_available = stocks_df['available'].sum() if 'available' in stocks_df.columns else 0
        if not delivered_df.empty and 'quantity' in delivered_df.columns:
            total_sold = delivered_df['quantity'].sum()
            sell_through_rate = (total_sold / (total_available + total_sold) * 100) if (total_available + total_sold) > 0 else 0
        else:
            sell_through_rate = 0
        
        # Stockout Rate - процент товаров без остатков
        out_of_stock = len(stocks_df[stocks_df['available'] == 0]) if 'available' in stocks_df.columns else 0
        total_products = len(stocks_df)
        stockout_rate = (out_of_stock / total_products * 100) if total_products > 0 else 0
        
        # Overstock Rate - процент избыточных остатков
        # Определяем избыточные остатки как товары с остатками > 90 дней продаж
        overstock_count = 0
        if not delivered_df.empty and 'sku' in delivered_df.columns and 'sku' in stocks_df.columns:
            # Для каждого SKU считаем средние продажи в день
            sku_daily_sales = delivered_df.groupby('sku')['quantity'].sum()
            if 'delivery_date' in delivered_df.columns:
                delivered_df['date'] = pd.to_datetime(delivered_df['delivery_date']).dt.date
                days_in_period = (delivered_df['date'].max() - delivered_df['date'].min()).days + 1 if len(delivered_df) > 1 else 1
            else:
                days_in_period = 30
            
            for sku, stock_row in stocks_df.iterrows():
                if 'sku' in stocks_df.columns:
                    sku_value = stock_row['sku'] if isinstance(stock_row, pd.Series) else sku
                else:
                    sku_value = sku
                
                available = stock_row['available'] if 'available' in stock_row else 0
                daily_sales = sku_daily_sales.get(sku_value, 0) / days_in_period if days_in_period > 0 else 0
                
                if daily_sales > 0:
                    days_of_stock = available / daily_sales
                    if days_of_stock > 90:
                        overstock_count += 1
        
        overstock_rate = (overstock_count / total_products * 100) if total_products > 0 else 0
        
        # ABC Analysis - анализ товаров по важности
        abc_analysis = self._calculate_abc_analysis(delivered_df, stocks_df)
        
        return {
            'inventory_turnover': float(inventory_turnover),
            'days_of_inventory': float(doi),
            'sell_through_rate': float(sell_through_rate),
            'stockout_rate': float(stockout_rate),
            'overstock_rate': float(overstock_rate),
            'abc_analysis': abc_analysis
        }
    
    def _calculate_abc_analysis(self, delivered_df, stocks_df):
        """ABC анализ товаров"""
        if delivered_df.empty or 'sku' not in delivered_df.columns:
            return {}
        
        # Группируем по SKU и считаем выручку
        sku_revenue = delivered_df.groupby('sku')['paid_by_customer'].sum().sort_values(ascending=False)
        total_revenue = sku_revenue.sum()
        
        if total_revenue == 0:
            return {}
        
        # Категория A: 80% выручки
        # Категория B: следующие 15% выручки
        # Категория C: остальные 5%
        cumulative_revenue = 0
        abc_categories = {}
        
        for sku, revenue in sku_revenue.items():
            cumulative_revenue += revenue
            percentage = (cumulative_revenue / total_revenue) * 100
            
            if percentage <= 80:
                category = 'A'
            elif percentage <= 95:
                category = 'B'
            else:
                category = 'C'
            
            abc_categories[sku] = {
                'category': category,
                'revenue': float(revenue),
                'percentage': float((revenue / total_revenue) * 100),
                'cumulative_percentage': float(percentage)
            }
        
        # Статистика по категориям
        category_stats = {
            'A': {'count': 0, 'revenue': 0, 'percentage': 0},
            'B': {'count': 0, 'revenue': 0, 'percentage': 0},
            'C': {'count': 0, 'revenue': 0, 'percentage': 0}
        }
        
        for sku_data in abc_categories.values():
            cat = sku_data['category']
            category_stats[cat]['count'] += 1
            category_stats[cat]['revenue'] += sku_data['revenue']
            category_stats[cat]['percentage'] += sku_data['percentage']
        
        return {
            'products': abc_categories,
            'summary': {
                'A': {k: float(v) for k, v in category_stats['A'].items()},
                'B': {k: float(v) for k, v in category_stats['B'].items()},
                'C': {k: float(v) for k, v in category_stats['C'].items()}
            }
        }
    
    def calculate_logistics_metrics(self, delivered_df):
        """Расчет метрик логистики"""
        if delivered_df.empty:
            return {}
        
        # Fulfillment Rate - процент выполненных заказов
        # Используем отношение доставленных к принятым
        total_delivered = len(delivered_df)
        # Для расчета нужны все заказы, используем упрощенную версию
        fulfillment_rate = 100.0  # Предполагаем 100% если заказы доставлены
        
        # On-time Delivery Rate - процент доставок в срок
        # Нужны данные о promised_date, используем упрощенную версию
        on_time_rate = None
        if 'promised_date' in delivered_df.columns and 'delivery_date' in delivered_df.columns:
            delivered_df['promised_date_dt'] = pd.to_datetime(delivered_df['promised_date'], errors='coerce')
            delivered_df['delivery_date_dt'] = pd.to_datetime(delivered_df['delivery_date'], errors='coerce')
            on_time = delivered_df[
                delivered_df['promised_date_dt'].notna() & 
                delivered_df['delivery_date_dt'].notna() &
                (delivered_df['delivery_date_dt'] <= delivered_df['promised_date_dt'])
            ]
            on_time_rate = (len(on_time) / len(delivered_df) * 100) if len(delivered_df) > 0 else 0
        
        # Average Shipping Cost - средняя стоимость доставки
        avg_shipping_cost = None
        if 'shipping_cost' in delivered_df.columns:
            avg_shipping_cost = delivered_df['shipping_cost'].mean()
        elif 'delivery_cost' in delivered_df.columns:
            avg_shipping_cost = delivered_df['delivery_cost'].mean()
        
        # Warehouse Utilization - использование складов
        warehouse_utilization = {}
        if 'warehouse' in delivered_df.columns:
            warehouse_stats = delivered_df.groupby('warehouse').agg({
                'paid_by_customer': 'sum',
                'quantity': 'sum'
            })
            total_orders = len(delivered_df)
            for warehouse, stats in warehouse_stats.iterrows():
                warehouse_orders = len(delivered_df[delivered_df['warehouse'] == warehouse])
                warehouse_utilization[warehouse] = {
                    'orders_count': int(warehouse_orders),
                    'orders_percentage': float((warehouse_orders / total_orders * 100) if total_orders > 0 else 0),
                    'revenue': float(stats['paid_by_customer']),
                    'quantity': int(stats['quantity'])
                }
        
        return {
            'fulfillment_rate': float(fulfillment_rate),
            'on_time_delivery_rate': float(on_time_rate) if on_time_rate else None,
            'avg_shipping_cost': float(avg_shipping_cost) if avg_shipping_cost else None,
            'warehouse_utilization': warehouse_utilization
        }
    
    def calculate_reviews_metrics(self, store_data=None):
        """Расчет метрик отзывов и рейтингов"""
        # Используем ReviewAnalyzer для детального анализа
        if store_data:
            review_metrics = self.review_analyzer.get_review_metrics_for_store(store_data)
            return review_metrics
        
        # Если нет данных магазина, возвращаем пустую структуру
        return {
            'total_reviews': 0,
            'average_rating': 0,
            'note': 'Данные об отзывах недоступны. Используйте кабинет Ozon или API для получения данных.'
        }
    
    def calculate_seo_metrics(self, orders=None):
        """Расчет SEO метрик на основе данных заказов"""
        if not orders:
            orders = self.orders
        
        if not orders:
            return {
                'seo_score': 0,
                'seo_level': 'unknown',
                'note': 'Нет данных для анализа SEO'
            }
        
        # Используем SEOAnalyzer для расчета
        seo_result = self.seo_analyzer.get_seo_score_for_orders(orders)
        return seo_result
    
    def calculate_ranking_factors_score(self, delivered_df, store_data=None):
        """
        Рассчитывает общий Ranking Factors Score на основе факторов ранжирования Ozon 2025
        
        Args:
            delivered_df: DataFrame с доставленными заказами
            store_data: данные магазина
        
        Returns:
            словарь с оценкой факторов ранжирования
        """
        if delivered_df.empty:
            return {
                'overall_score': 0,
                'relevance_score': 0,
                'price_score': 0,
                'delivery_score': 0,
                'reviews_score': 0,
                'conversion_score': 0,
                'note': 'Недостаточно данных для расчета'
            }
        
        scores = {}
        
        # 1. Релевантность (SEO) - 25%
        seo_metrics = self.calculate_seo_metrics()
        relevance_score = seo_metrics.get('seo_score', 0)
        scores['relevance_score'] = relevance_score
        
        # 2. Цена и конкурентоспособность - 20%
        # Проверяем наличие цен и их конкурентоспособность
        if 'seller_price' in delivered_df.columns and 'paid_by_customer' in delivered_df.columns:
            avg_price = delivered_df['paid_by_customer'].mean()
            # Упрощенная оценка: если цена разумная (не слишком низкая и не слишком высокая)
            # В реальности нужен конкурентный анализ
            price_score = 70  # Базовая оценка
            # Можно улучшить, сравнивая с конкурентами
        else:
            price_score = 50
        scores['price_score'] = price_score
        
        # 3. Условия доставки - 20%
        delivery_score = 70  # Базовая оценка
        if 'delivery_time' in delivered_df.columns or 'avg_delivery_time_days' in delivered_df.columns:
            # Если есть данные о времени доставки
            logistics_metrics = self.calculate_logistics_metrics(delivered_df)
            avg_delivery = logistics_metrics.get('on_time_delivery_rate', None)
            if avg_delivery is not None:
                # Чем выше процент доставок в срок, тем выше оценка
                delivery_score = min(avg_delivery, 100)
        scores['delivery_score'] = delivery_score
        
        # 4. Отзывы покупателей - 25% (критически важно)
        reviews_metrics = self.calculate_reviews_metrics(store_data)
        avg_rating = reviews_metrics.get('average_rating', 0) or 0
        if avg_rating > 0:
            # Преобразуем рейтинг из 5-балльной шкалы в 100-балльную
            reviews_score = (avg_rating / 5.0) * 100
        else:
            reviews_score = 50  # Базовая оценка при отсутствии данных
        scores['reviews_score'] = reviews_score
        
        # 5. Рейтинг и конверсия - 10%
        # Конверсия уже рассчитывается в других метриках
        # Используем упрощенную оценку
        conversion_score = 70  # Базовая оценка
        scores['conversion_score'] = conversion_score
        
        # Общий score с весами
        overall_score = (
            relevance_score * 0.25 +
            price_score * 0.20 +
            delivery_score * 0.20 +
            reviews_score * 0.25 +
            conversion_score * 0.10
        )
        
        # Определение уровня
        if overall_score >= 80:
            level = 'excellent'
        elif overall_score >= 60:
            level = 'good'
        elif overall_score >= 40:
            level = 'fair'
        else:
            level = 'poor'
        
        return {
            'overall_score': round(overall_score, 2),
            'ranking_level': level,
            'relevance_score': round(relevance_score, 2),
            'price_score': round(price_score, 2),
            'delivery_score': round(delivery_score, 2),
            'reviews_score': round(reviews_score, 2),
            'conversion_score': round(conversion_score, 2),
            'weights': {
                'relevance': 0.25,
                'price': 0.20,
                'delivery': 0.20,
                'reviews': 0.25,
                'conversion': 0.10
            }
        }
    
    def get_all_metrics(self, delivered_df, all_orders_df, store_data=None):
        """Получить все расширенные метрики"""
        sales_metrics = self.calculate_sales_metrics(delivered_df)
        customer_metrics = self.calculate_customer_metrics(delivered_df, all_orders_df)
        inventory_metrics = self.calculate_inventory_metrics(delivered_df)
        logistics_metrics = self.calculate_logistics_metrics(delivered_df)
        reviews_metrics = self.calculate_reviews_metrics(store_data)
        seo_metrics = self.calculate_seo_metrics(self.orders)
        ranking_factors = self.calculate_ranking_factors_score(delivered_df, store_data)
        
        return {
            'sales_metrics': sales_metrics,
            'customer_metrics': customer_metrics,
            'inventory_metrics': inventory_metrics,
            'logistics_metrics': logistics_metrics,
            'reviews_metrics': reviews_metrics,
            'seo_metrics': seo_metrics,
            'ranking_factors': ranking_factors
        }
