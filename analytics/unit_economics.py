"""
Модуль для расчета юнит-экономики на основе себестоимости товаров
"""
import pandas as pd
from typing import Dict, Optional, List
from utils.unit_economics_manager import UnitEconomicsManager


class UnitEconomicsCalculator:
    """Калькулятор юнит-экономики"""
    
    def __init__(self, unit_economics_manager: Optional[UnitEconomicsManager] = None):
        """
        Инициализация калькулятора
        
        Args:
            unit_economics_manager: Менеджер себестоимости. Если None, создается новый экземпляр.
        """
        self.cost_manager = unit_economics_manager or UnitEconomicsManager()
    
    def calculate_unit_economics(self, orders: List[Dict], date_from=None, date_to=None) -> Dict:
        """
        Рассчитывает юнит-экономику на основе заказов и себестоимости
        
        Args:
            orders: Список заказов
            date_from: Начальная дата фильтрации (опционально)
            date_to: Конечная дата фильтрации (опционально)
        
        Returns:
            dict: Метрики юнит-экономики
        """
        if not orders:
            return {
                'total_revenue': 0,
                'total_cost': 0,
                'total_profit': 0,
                'profit_margin': 0,
                'roi': 0,
                'by_sku': {}
            }
        
        df = pd.DataFrame(orders)
        
        # Фильтруем доставленные заказы
        delivered_mask = df['status'].apply(self._is_delivered_status)
        delivered = df[delivered_mask].copy()
        
        if delivered.empty:
            return {
                'total_revenue': 0,
                'total_cost': 0,
                'total_profit': 0,
                'profit_margin': 0,
                'roi': 0,
                'by_sku': {}
            }
        
        # Фильтруем по дате если нужно
        if date_from or date_to:
            delivered['_filter_date'] = delivered.apply(self._get_date_for_filtering, axis=1)
            if '_filter_date' in delivered.columns and not delivered.empty:
                delivered = self._filter_by_date(delivered, '_filter_date', date_from, date_to)
                delivered = delivered[delivered['_filter_date'].notna()]
        
        if delivered.empty:
            return {
                'total_revenue': 0,
                'total_cost': 0,
                'total_profit': 0,
                'profit_margin': 0,
                'roi': 0,
                'by_sku': {}
            }
        
        # Рассчитываем метрики по SKU
        total_revenue = 0
        total_cost = 0
        by_sku = {}
        
        for _, row in delivered.iterrows():
            sku = str(row.get('sku', ''))
            quantity = float(row.get('quantity', 1) or 1)
            revenue = float(row.get('paid_by_customer', 0) or 0)
            
            # Получаем себестоимость
            cost_per_unit = self.cost_manager.get_cost(sku)
            
            if cost_per_unit is None:
                # Если себестоимость не установлена, пропускаем расчет для этого товара
                continue
            
            cost_total = cost_per_unit * quantity
            profit = revenue - cost_total
            
            total_revenue += revenue
            total_cost += cost_total
            
            # Агрегируем по SKU
            if sku not in by_sku:
                by_sku[sku] = {
                    'revenue': 0,
                    'cost': 0,
                    'profit': 0,
                    'quantity': 0,
                    'profit_margin': 0,
                    'roi': 0
                }
            
            by_sku[sku]['revenue'] += revenue
            by_sku[sku]['cost'] += cost_total
            by_sku[sku]['profit'] += profit
            by_sku[sku]['quantity'] += quantity
        
        # Рассчитываем итоговые метрики
        total_profit = total_revenue - total_cost
        profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
        roi = (total_profit / total_cost * 100) if total_cost > 0 else 0
        
        # Рассчитываем метрики для каждого SKU
        for sku, metrics in by_sku.items():
            if metrics['revenue'] > 0:
                metrics['profit_margin'] = (metrics['profit'] / metrics['revenue'] * 100)
            if metrics['cost'] > 0:
                metrics['roi'] = (metrics['profit'] / metrics['cost'] * 100)
            
            # Конвертируем в float для JSON
            metrics['revenue'] = float(metrics['revenue'])
            metrics['cost'] = float(metrics['cost'])
            metrics['profit'] = float(metrics['profit'])
            metrics['quantity'] = int(metrics['quantity'])
            metrics['profit_margin'] = float(metrics['profit_margin'])
            metrics['roi'] = float(metrics['roi'])
        
        return {
            'total_revenue': float(total_revenue),
            'total_cost': float(total_cost),
            'total_profit': float(total_profit),
            'profit_margin': float(profit_margin),
            'roi': float(roi),
            'by_sku': by_sku,
            'skus_with_cost': len(by_sku),
            'skus_without_cost': len(delivered['sku'].unique()) - len(by_sku)
        }
    
    def _is_delivered_status(self, status):
        """Проверяет, является ли статус доставленным"""
        if not status or pd.isna(status):
            return False
        status_str = str(status).lower().strip()
        return status_str in ['доставлен', 'delivered', 'доставка', 'delivery']
    
    def _get_date_for_filtering(self, row):
        """Получает дату для фильтрации"""
        if 'delivery_date' in row and pd.notna(row.get('delivery_date')):
            return row['delivery_date']
        if 'shipment_date' in row and pd.notna(row.get('shipment_date')):
            return row['shipment_date']
        if 'accepted_date' in row and pd.notna(row.get('accepted_date')):
            return row['accepted_date']
        return None
    
    def _filter_by_date(self, df, date_column, date_from=None, date_to=None):
        """Фильтрует DataFrame по дате"""
        if df.empty:
            return df
        
        if date_column not in df.columns:
            return df
        
        if not date_from and not date_to:
            return df
        
        try:
            df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
            
            if date_from:
                date_from_dt = pd.to_datetime(date_from)
                df = df[df[date_column] >= date_from_dt]
            
            if date_to:
                date_to_dt = pd.to_datetime(date_to)
                df = df[df[date_column] <= date_to_dt]
        except:
            pass
        
        return df
