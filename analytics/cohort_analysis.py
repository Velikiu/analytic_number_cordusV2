"""
Когортный анализ для маркетплейса Ozon
Анализ клиентов по когортам (месяц первой покупки)
"""
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from collections import defaultdict


class CohortAnalysis:
    """Класс для когортного анализа клиентов"""
    
    def __init__(self, orders):
        """
        Инициализация с данными заказов
        
        Args:
            orders: список заказов
        """
        self.orders = orders or []
    
    def _is_delivered_status(self, status):
        """Проверяет, является ли статус доставленным"""
        if not status or pd.isna(status):
            return False
        status_str = str(status).lower().strip()
        return status_str in ['доставлен', 'delivered', 'доставка', 'delivery']
    
    def _get_customer_id(self, row):
        """Получает ID клиента из строки заказа"""
        for col in ['customer_id', 'buyer_id', 'user_id', 'client_id']:
            if col in row and pd.notna(row.get(col)):
                return row[col]
        # Если нет customer_id, используем комбинацию полей как суррогат
        if 'shipment_number' in row and pd.notna(row.get('shipment_number')):
            return f"order_{row['shipment_number']}"
        elif 'order_number' in row and pd.notna(row.get('order_number')):
            return f"order_{row['order_number']}"
        return None
    
    def _get_order_date(self, row):
        """Получает дату заказа"""
        for col in ['delivery_date', 'shipment_date', 'accepted_date', 'created_date']:
            if col in row and pd.notna(row.get(col)):
                return pd.to_datetime(row[col], errors='coerce')
        return None
    
    def calculate_cohorts(self, date_from=None, date_to=None):
        """
        Расчет когорт клиентов
        
        Args:
            date_from: начальная дата фильтрации
            date_to: конечная дата фильтрации
        
        Returns:
            dict с данными когорт
        """
        if not self.orders:
            return {}
        
        df = pd.DataFrame(self.orders)
        
        # Фильтруем доставленные заказы
        delivered_mask = df['status'].apply(self._is_delivered_status)
        delivered = df[delivered_mask].copy()
        
        if delivered.empty:
            return {}
        
        # Фильтруем по дате если указано
        if date_from or date_to:
            delivered['_order_date'] = delivered.apply(self._get_order_date, axis=1)
            delivered = delivered[delivered['_order_date'].notna()]
            
            if date_from:
                date_from_dt = pd.to_datetime(date_from)
                delivered = delivered[delivered['_order_date'] >= date_from_dt]
            
            if date_to:
                date_to_dt = pd.to_datetime(date_to)
                delivered = delivered[delivered['_order_date'] <= date_to_dt]
        
        # Получаем ID клиентов и даты заказов
        delivered['customer_id'] = delivered.apply(self._get_customer_id, axis=1)
        delivered['order_date'] = delivered.apply(self._get_order_date, axis=1)
        
        # Убираем записи без customer_id или order_date
        delivered = delivered[
            delivered['customer_id'].notna() & 
            delivered['order_date'].notna()
        ]
        
        if delivered.empty:
            return {}
        
        # Определяем когорту (месяц первой покупки)
        first_purchase = delivered.groupby('customer_id')['order_date'].min().reset_index()
        first_purchase.columns = ['customer_id', 'first_purchase_date']
        first_purchase['cohort'] = first_purchase['first_purchase_date'].dt.to_period('M')
        
        # Объединяем с основными данными
        delivered = delivered.merge(first_purchase[['customer_id', 'cohort']], on='customer_id', how='left')
        
        # Определяем период заказа (месяц)
        delivered['order_period'] = delivered['order_date'].dt.to_period('M')
        
        # Считаем количество уникальных клиентов по когортам и периодам
        cohort_period = delivered.groupby(['cohort', 'order_period']).agg({
            'customer_id': 'nunique',
            'paid_by_customer': 'sum',
            'quantity': 'sum'
        }).reset_index()
        cohort_period.columns = ['cohort', 'period', 'customers', 'revenue', 'quantity']
        
        # Считаем общее количество клиентов в каждой когорте
        cohort_sizes = first_purchase.groupby('cohort')['customer_id'].count().to_dict()
        
        # Создаем таблицу retention
        retention_table = self._create_retention_table(cohort_period, cohort_sizes)
        
        # Создаем таблицу revenue по когортам
        revenue_table = self._create_revenue_table(cohort_period)
        
        # Считаем LTV по когортам
        ltv_by_cohort = self._calculate_ltv_by_cohort(delivered, first_purchase)
        
        # Статистика по когортам
        cohort_stats = self._calculate_cohort_stats(first_purchase, delivered, cohort_sizes)
        
        return {
            'retention_table': retention_table,
            'revenue_table': revenue_table,
            'ltv_by_cohort': ltv_by_cohort,
            'cohort_stats': cohort_stats,
            'cohort_sizes': {str(k): int(v) for k, v in cohort_sizes.items()}
        }
    
    def _create_retention_table(self, cohort_period, cohort_sizes):
        """Создает таблицу retention по когортам"""
        if cohort_period.empty:
            return {}
        
        # Создаем сводную таблицу
        pivot = cohort_period.pivot_table(
            index='cohort',
            columns='period',
            values='customers',
            fill_value=0
        )
        
        # Сортируем когорты и периоды
        pivot = pivot.sort_index()
        pivot = pivot.sort_index(axis=1)
        
        # Вычисляем retention rate (процент клиентов, вернувшихся в период)
        retention_pivot = pivot.copy()
        for cohort in pivot.index:
            cohort_size = cohort_sizes.get(cohort, 0)
            if cohort_size > 0:
                retention_pivot.loc[cohort] = (pivot.loc[cohort] / cohort_size * 100).round(2)
        
        # Конвертируем в словарь для JSON
        retention_dict = {}
        for cohort in retention_pivot.index:
            retention_dict[str(cohort)] = {
                'periods': {str(period): float(retention_pivot.loc[cohort, period]) 
                           for period in retention_pivot.columns},
                'cohort_size': int(cohort_sizes.get(cohort, 0))
            }
        
        return retention_dict
    
    def _create_revenue_table(self, cohort_period):
        """Создает таблицу revenue по когортам"""
        if cohort_period.empty:
            return {}
        
        # Создаем сводную таблицу по выручке
        revenue_pivot = cohort_period.pivot_table(
            index='cohort',
            columns='period',
            values='revenue',
            fill_value=0
        )
        
        # Сортируем
        revenue_pivot = revenue_pivot.sort_index()
        revenue_pivot = revenue_pivot.sort_index(axis=1)
        
        # Конвертируем в словарь
        revenue_dict = {}
        for cohort in revenue_pivot.index:
            revenue_dict[str(cohort)] = {
                'periods': {str(period): float(revenue_pivot.loc[cohort, period]) 
                           for period in revenue_pivot.columns},
                'total_revenue': float(revenue_pivot.loc[cohort].sum())
            }
        
        return revenue_dict
    
    def _calculate_ltv_by_cohort(self, delivered, first_purchase):
        """Рассчитывает LTV по когортам"""
        if delivered.empty or first_purchase.empty:
            return {}
        
        # Объединяем данные
        delivered = delivered.merge(
            first_purchase[['customer_id', 'cohort']], 
            on='customer_id', 
            how='left'
        )
        
        # Считаем LTV для каждого клиента
        customer_ltv = delivered.groupby(['customer_id', 'cohort'])['paid_by_customer'].sum().reset_index()
        customer_ltv.columns = ['customer_id', 'cohort', 'ltv']
        
        # Средний LTV по когортам
        cohort_ltv = customer_ltv.groupby('cohort')['ltv'].agg(['mean', 'median', 'sum', 'count']).reset_index()
        cohort_ltv.columns = ['cohort', 'avg_ltv', 'median_ltv', 'total_ltv', 'customers_count']
        
        # Конвертируем в словарь
        ltv_dict = {}
        for _, row in cohort_ltv.iterrows():
            ltv_dict[str(row['cohort'])] = {
                'avg_ltv': float(row['avg_ltv']),
                'median_ltv': float(row['median_ltv']),
                'total_ltv': float(row['total_ltv']),
                'customers_count': int(row['customers_count'])
            }
        
        return ltv_dict
    
    def _calculate_cohort_stats(self, first_purchase, delivered, cohort_sizes):
        """Рассчитывает статистику по когортам"""
        if first_purchase.empty or delivered.empty:
            return {}
        
        # Объединяем данные
        delivered = delivered.merge(
            first_purchase[['customer_id', 'cohort', 'first_purchase_date']], 
            on='customer_id', 
            how='left'
        )
        
        stats = {}
        for cohort in first_purchase['cohort'].unique():
            cohort_data = delivered[delivered['cohort'] == cohort]
            cohort_first = first_purchase[first_purchase['cohort'] == cohort]
            
            if cohort_data.empty:
                continue
            
            # Количество клиентов
            customers_count = len(cohort_first)
            
            # Количество повторных покупок
            repeat_customers = len(cohort_data[cohort_data['customer_id'].duplicated(keep=False)])
            repeat_rate = (repeat_customers / customers_count * 100) if customers_count > 0 else 0
            
            # Среднее количество заказов на клиента
            orders_per_customer = cohort_data.groupby('customer_id').size().mean()
            
            # Средний чек
            avg_order_value = cohort_data['paid_by_customer'].mean()
            
            # Общая выручка
            total_revenue = cohort_data['paid_by_customer'].sum()
            
            # Средний LTV
            customer_revenue = cohort_data.groupby('customer_id')['paid_by_customer'].sum()
            avg_ltv = customer_revenue.mean()
            
            # Период анализа (от первой покупки до последней)
            if 'order_date' in cohort_data.columns:
                first_date = cohort_data['order_date'].min()
                last_date = cohort_data['order_date'].max()
                analysis_period_days = (last_date - first_date).days + 1
            else:
                analysis_period_days = None
            
            stats[str(cohort)] = {
                'customers_count': int(customers_count),
                'repeat_rate': float(repeat_rate),
                'orders_per_customer': float(orders_per_customer),
                'avg_order_value': float(avg_order_value),
                'total_revenue': float(total_revenue),
                'avg_ltv': float(avg_ltv),
                'analysis_period_days': int(analysis_period_days) if analysis_period_days else None
            }
        
        return stats
    
    def get_cohort_summary(self, date_from=None, date_to=None):
        """Получить краткую сводку по когортам"""
        cohorts_data = self.calculate_cohorts(date_from, date_to)
        
        if not cohorts_data:
            return {}
        
        cohort_stats = cohorts_data.get('cohort_stats', {})
        cohort_sizes = cohorts_data.get('cohort_sizes', {})
        
        summary = {
            'total_cohorts': len(cohort_sizes),
            'total_customers': sum(cohort_sizes.values()),
            'avg_cohort_size': sum(cohort_sizes.values()) / len(cohort_sizes) if cohort_sizes else 0,
            'avg_repeat_rate': 0,
            'avg_ltv': 0
        }
        
        if cohort_stats:
            repeat_rates = [s['repeat_rate'] for s in cohort_stats.values()]
            ltvs = [s['avg_ltv'] for s in cohort_stats.values() if s.get('avg_ltv')]
            
            summary['avg_repeat_rate'] = sum(repeat_rates) / len(repeat_rates) if repeat_rates else 0
            summary['avg_ltv'] = sum(ltvs) / len(ltvs) if ltvs else 0
        
        return summary
