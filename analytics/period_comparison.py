"""
Сравнение периодов для аналитики Ozon
Сравнение текущего периода с предыдущим, MoM, YoY
"""
from datetime import datetime, timedelta
import pandas as pd


class PeriodComparison:
    """Класс для сравнения периодов"""
    
    def __init__(self, analytics_instance):
        """
        Инициализация с экземпляром OzonAnalytics
        
        Args:
            analytics_instance: экземпляр OzonAnalytics
        """
        self.analytics = analytics_instance
    
    def _calculate_previous_period(self, date_from, date_to):
        """Вычисляет предыдущий период"""
        if not date_from or not date_to:
            return None, None
        
        from_dt = pd.to_datetime(date_from)
        to_dt = pd.to_datetime(date_to)
        
        # Вычисляем длину периода
        period_length = (to_dt - from_dt).days + 1
        
        # Предыдущий период той же длины
        prev_to = from_dt - timedelta(days=1)
        prev_from = prev_to - timedelta(days=period_length - 1)
        
        return prev_from.strftime('%Y-%m-%d'), prev_to.strftime('%Y-%m-%d')
    
    def _calculate_mom_period(self, date_from, date_to):
        """Вычисляет период месяц назад (MoM)"""
        if not date_from or not date_to:
            return None, None
        
        from_dt = pd.to_datetime(date_from)
        to_dt = pd.to_datetime(date_to)
        
        # Месяц назад
        mom_from = from_dt - pd.DateOffset(months=1)
        mom_to = to_dt - pd.DateOffset(months=1)
        
        return mom_from.strftime('%Y-%m-%d'), mom_to.strftime('%Y-%m-%d')
    
    def _calculate_yoy_period(self, date_from, date_to):
        """Вычисляет период год назад (YoY)"""
        if not date_from or not date_to:
            return None, None
        
        from_dt = pd.to_datetime(date_from)
        to_dt = pd.to_datetime(date_to)
        
        # Год назад
        yoy_from = from_dt - pd.DateOffset(years=1)
        yoy_to = to_dt - pd.DateOffset(years=1)
        
        return yoy_from.strftime('%Y-%m-%d'), yoy_to.strftime('%Y-%m-%d')
    
    def _calculate_change(self, current, previous):
        """Вычисляет изменение в процентах"""
        if previous is None or previous == 0:
            return None
        return ((current - previous) / previous) * 100
    
    def compare_periods(self, date_from, date_to, comparison_type='previous'):
        """
        Сравнивает текущий период с другим периодом
        
        Args:
            date_from: начальная дата текущего периода
            date_to: конечная дата текущего периода
            comparison_type: тип сравнения ('previous', 'mom', 'yoy')
        
        Returns:
            dict с результатами сравнения
        """
        # Получаем аналитику текущего периода
        self.analytics.set_date_filter(date_from, date_to)
        current_analytics = self.analytics.get_full_analytics()
        
        # Определяем период для сравнения
        if comparison_type == 'previous':
            comp_from, comp_to = self._calculate_previous_period(date_from, date_to)
        elif comparison_type == 'mom':
            comp_from, comp_to = self._calculate_mom_period(date_from, date_to)
        elif comparison_type == 'yoy':
            comp_from, comp_to = self._calculate_yoy_period(date_from, date_to)
        else:
            comp_from, comp_to = self._calculate_previous_period(date_from, date_to)
        
        if not comp_from or not comp_to:
            return {
                'current_period': {
                    'date_from': date_from,
                    'date_to': date_to,
                    'analytics': current_analytics
                },
                'comparison_period': None,
                'changes': None,
                'error': 'Не удалось вычислить период для сравнения'
            }
        
        # Получаем аналитику периода сравнения
        self.analytics.set_date_filter(comp_from, comp_to)
        comparison_analytics = self.analytics.get_full_analytics()
        
        # Вычисляем изменения
        changes = self._calculate_changes(current_analytics, comparison_analytics)
        
        return {
            'current_period': {
                'date_from': date_from,
                'date_to': date_to,
                'analytics': current_analytics
            },
            'comparison_period': {
                'date_from': comp_from,
                'date_to': comp_to,
                'analytics': comparison_analytics
            },
            'changes': changes,
            'comparison_type': comparison_type
        }
    
    def _calculate_changes(self, current, previous):
        """Вычисляет изменения между периодами"""
        changes = {}
        
        # Метрики продаж
        if 'sales_metrics' in current and 'sales_metrics' in previous:
            current_sales = current['sales_metrics']
            previous_sales = previous['sales_metrics']
            
            changes['sales'] = {
                'total_revenue': {
                    'current': current_sales.get('total_revenue', 0),
                    'previous': previous_sales.get('total_revenue', 0),
                    'change': self._calculate_change(
                        current_sales.get('total_revenue', 0),
                        previous_sales.get('total_revenue', 0)
                    )
                },
                'total_orders': {
                    'current': current_sales.get('total_orders', 0),
                    'previous': previous_sales.get('total_orders', 0),
                    'change': self._calculate_change(
                        current_sales.get('total_orders', 0),
                        previous_sales.get('total_orders', 0)
                    )
                },
                'avg_order_value': {
                    'current': current_sales.get('avg_order_value', 0),
                    'previous': previous_sales.get('avg_order_value', 0),
                    'change': self._calculate_change(
                        current_sales.get('avg_order_value', 0),
                        previous_sales.get('avg_order_value', 0)
                    )
                },
                'conversion_rate': {
                    'current': current_sales.get('conversion_rate', 0),
                    'previous': previous_sales.get('conversion_rate', 0),
                    'change': self._calculate_change(
                        current_sales.get('conversion_rate', 0),
                        previous_sales.get('conversion_rate', 0)
                    )
                }
            }
        
        # Финансовые метрики
        if 'financial_metrics' in current and 'financial_metrics' in previous:
            current_fin = current['financial_metrics']
            previous_fin = previous['financial_metrics']
            
            changes['financial'] = {
                'margin_percent': {
                    'current': current_fin.get('margin_percent', 0),
                    'previous': previous_fin.get('margin_percent', 0),
                    'change': self._calculate_change(
                        current_fin.get('margin_percent', 0),
                        previous_fin.get('margin_percent', 0)
                    )
                },
                'total_discounts': {
                    'current': current_fin.get('total_discounts', 0),
                    'previous': previous_fin.get('total_discounts', 0),
                    'change': self._calculate_change(
                        current_fin.get('total_discounts', 0),
                        previous_fin.get('total_discounts', 0)
                    )
                }
            }
        
        # Метрики клиентов
        if 'customer_metrics' in current and 'customer_metrics' in previous:
            current_cust = current['customer_metrics']
            previous_cust = previous['customer_metrics']
            
            changes['customers'] = {
                'premium_ratio': {
                    'current': current_cust.get('premium_ratio', 0),
                    'previous': previous_cust.get('premium_ratio', 0),
                    'change': self._calculate_change(
                        current_cust.get('premium_ratio', 0),
                        previous_cust.get('premium_ratio', 0)
                    )
                }
            }
        
        # Метрики остатков
        if 'inventory_metrics' in current and 'inventory_metrics' in previous:
            current_inv = current['inventory_metrics']
            previous_inv = previous['inventory_metrics']
            
            changes['inventory'] = {
                'total_available': {
                    'current': current_inv.get('total_available', 0),
                    'previous': previous_inv.get('total_available', 0),
                    'change': self._calculate_change(
                        current_inv.get('total_available', 0),
                        previous_inv.get('total_available', 0)
                    )
                },
                'out_of_stock_count': {
                    'current': current_inv.get('out_of_stock_count', 0),
                    'previous': previous_inv.get('out_of_stock_count', 0),
                    'change': self._calculate_change(
                        current_inv.get('out_of_stock_count', 0),
                        previous_inv.get('out_of_stock_count', 0)
                    )
                }
            }
        
        # Метрики возвратов
        if 'returns_metrics' in current and 'returns_metrics' in previous:
            current_ret = current['returns_metrics']
            previous_ret = previous['returns_metrics']
            
            changes['returns'] = {
                'return_rate': {
                    'current': current_ret.get('return_rate', 0),
                    'previous': previous_ret.get('return_rate', 0),
                    'change': self._calculate_change(
                        current_ret.get('return_rate', 0),
                        previous_ret.get('return_rate', 0)
                    )
                }
            }
        
        # Расширенные метрики маркетплейса
        if 'marketplace_metrics' in current and 'marketplace_metrics' in previous:
            current_mp = current['marketplace_metrics']
            previous_mp = previous['marketplace_metrics']
            
            changes['marketplace'] = {}
            
            # GMV
            if 'sales_metrics' in current_mp and 'sales_metrics' in previous_mp:
                changes['marketplace']['gmv'] = {
                    'current': current_mp['sales_metrics'].get('gmv', 0),
                    'previous': previous_mp['sales_metrics'].get('gmv', 0),
                    'change': self._calculate_change(
                        current_mp['sales_metrics'].get('gmv', 0),
                        previous_mp['sales_metrics'].get('gmv', 0)
                    )
                }
            
            # LTV
            if 'customer_metrics' in current_mp and 'customer_metrics' in previous_mp:
                current_ltv = current_mp['customer_metrics'].get('ltv')
                previous_ltv = previous_mp['customer_metrics'].get('ltv')
                if current_ltv and previous_ltv:
                    changes['marketplace']['ltv'] = {
                        'current': current_ltv,
                        'previous': previous_ltv,
                        'change': self._calculate_change(current_ltv, previous_ltv)
                    }
        
        return changes
    
    def get_all_comparisons(self, date_from, date_to):
        """Получить все типы сравнений"""
        return {
            'previous': self.compare_periods(date_from, date_to, 'previous'),
            'mom': self.compare_periods(date_from, date_to, 'mom'),
            'yoy': self.compare_periods(date_from, date_to, 'yoy')
        }
