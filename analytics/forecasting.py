"""
Прогнозирование продаж и остатков для маркетплейса Ozon
Использует простые методы прогнозирования временных рядов
"""
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from collections import defaultdict


class Forecasting:
    """Класс для прогнозирования продаж и остатков"""
    
    def __init__(self, orders, stocks):
        """
        Инициализация с данными
        
        Args:
            orders: список заказов
            stocks: список остатков
        """
        self.orders = orders or []
        self.stocks = stocks or []
    
    def _is_delivered_status(self, status):
        """Проверяет, является ли статус доставленным"""
        if not status or pd.isna(status):
            return False
        status_str = str(status).lower().strip()
        return status_str in ['доставлен', 'delivered', 'доставка', 'delivery']
    
    def _prepare_time_series(self, df, date_column='delivery_date', value_column='paid_by_customer'):
        """Подготавливает временной ряд для прогнозирования"""
        if df.empty or date_column not in df.columns:
            return None
        
        # Конвертируем дату
        df['date'] = pd.to_datetime(df[date_column], errors='coerce')
        df = df[df['date'].notna()]
        
        if df.empty:
            return None
        
        # Группируем по дням
        daily = df.groupby(df['date'].dt.date).agg({
            value_column: 'sum',
            'quantity': 'sum' if 'quantity' in df.columns else 'count'
        }).reset_index()
        
        daily.columns = ['date', 'value', 'quantity']
        daily['date'] = pd.to_datetime(daily['date'])
        daily = daily.sort_values('date')
        
        return daily
    
    def forecast_sales_simple(self, days_ahead=30, date_from=None, date_to=None):
        """
        Простое прогнозирование продаж на основе среднего
        
        Args:
            days_ahead: количество дней для прогноза
            date_from: начальная дата для обучения
            date_to: конечная дата для обучения
        
        Returns:
            dict с прогнозом
        """
        if not self.orders:
            return {}
        
        df = pd.DataFrame(self.orders)
        
        # Фильтруем доставленные заказы
        delivered_mask = df['status'].apply(self._is_delivered_status)
        delivered = df[delivered_mask].copy()
        
        # Фильтруем по дате если указано
        if date_from or date_to:
            delivered['_order_date'] = pd.to_datetime(
                delivered.get('delivery_date', delivered.get('shipment_date', delivered.get('accepted_date'))),
                errors='coerce'
            )
            delivered = delivered[delivered['_order_date'].notna()]
            
            if date_from:
                date_from_dt = pd.to_datetime(date_from)
                delivered = delivered[delivered['_order_date'] >= date_from_dt]
            
            if date_to:
                date_to_dt = pd.to_datetime(date_to)
                delivered = delivered[delivered['_order_date'] <= date_to_dt]
        
        if delivered.empty:
            return {}
        
        # Подготавливаем временной ряд
        ts = self._prepare_time_series(delivered, 'delivery_date', 'paid_by_customer')
        
        if ts is None or ts.empty:
            return {}
        
        # Простое прогнозирование: среднее значение за последние N дней
        lookback_days = min(30, len(ts))
        recent_data = ts.tail(lookback_days)
        
        avg_daily_revenue = recent_data['value'].mean()
        avg_daily_quantity = recent_data['quantity'].mean()
        
        # Тренд (линейная регрессия)
        if len(recent_data) > 1:
            x = np.arange(len(recent_data))
            y = recent_data['value'].values
            trend = np.polyfit(x, y, 1)[0]  # Наклон линии
        else:
            trend = 0
        
        # Генерируем прогноз
        last_date = ts['date'].max()
        forecast_dates = pd.date_range(start=last_date + timedelta(days=1), periods=days_ahead, freq='D')
        
        forecast = []
        for i, date in enumerate(forecast_dates):
            # Базовый прогноз + тренд
            forecast_value = avg_daily_revenue + (trend * (i + 1))
            forecast_quantity = avg_daily_quantity
            
            # Учитываем день недели (если есть достаточно данных)
            day_of_week = date.weekday()
            if len(ts) >= 14:  # Минимум 2 недели данных
                weekday_avg = ts[ts['date'].dt.weekday == day_of_week]['value'].mean()
                if not pd.isna(weekday_avg) and weekday_avg > 0:
                    # Корректируем прогноз на основе дня недели
                    overall_avg = ts['value'].mean()
                    adjustment = weekday_avg / overall_avg if overall_avg > 0 else 1
                    forecast_value = forecast_value * adjustment
            
            forecast.append({
                'date': date.strftime('%Y-%m-%d'),
                'revenue': max(0, float(forecast_value)),
                'quantity': max(0, float(forecast_quantity))
            })
        
        # Статистика
        total_forecast_revenue = sum(f['revenue'] for f in forecast)
        total_forecast_quantity = sum(f['quantity'] for f in forecast)
        
        # Доверительный интервал (упрощенный)
        std_dev = recent_data['value'].std()
        confidence_interval = {
            'lower': total_forecast_revenue - (1.96 * std_dev * np.sqrt(days_ahead)),
            'upper': total_forecast_revenue + (1.96 * std_dev * np.sqrt(days_ahead))
        }
        
        return {
            'forecast': forecast,
            'summary': {
                'total_revenue': float(total_forecast_revenue),
                'total_quantity': float(total_forecast_quantity),
                'avg_daily_revenue': float(total_forecast_revenue / days_ahead),
                'avg_daily_quantity': float(total_forecast_quantity / days_ahead),
                'trend': float(trend),
                'confidence_interval': {
                    'lower': float(max(0, confidence_interval['lower'])),
                    'upper': float(confidence_interval['upper'])
                }
            },
            'model_info': {
                'method': 'simple_average_with_trend',
                'lookback_days': lookback_days,
                'days_ahead': days_ahead
            }
        }
    
    def forecast_inventory(self, sku=None, days_ahead=30):
        """
        Прогнозирование остатков
        
        Args:
            sku: конкретный SKU (если None, то для всех)
            days_ahead: количество дней для прогноза
        
        Returns:
            dict с прогнозом остатков
        """
        if not self.stocks or not self.orders:
            return {}
        
        stocks_df = pd.DataFrame(self.stocks)
        orders_df = pd.DataFrame(self.orders)
        
        # Фильтруем доставленные заказы
        delivered_mask = orders_df['status'].apply(self._is_delivered_status)
        delivered = orders_df[delivered_mask].copy()
        
        if delivered.empty:
            return {}
        
        # Фильтруем по SKU если указан
        if sku:
            delivered = delivered[delivered['sku'] == sku]
            stocks_df = stocks_df[stocks_df['sku'] == sku]
        
        if delivered.empty or stocks_df.empty:
            return {}
        
        # Подготавливаем временной ряд продаж
        ts = self._prepare_time_series(delivered, 'delivery_date', 'quantity')
        
        if ts is None or ts.empty:
            return {}
        
        # Средние продажи в день
        avg_daily_sales = ts['value'].mean()
        
        # Текущие остатки
        current_stock = stocks_df['available'].sum() if 'available' in stocks_df.columns else 0
        
        # Прогноз: когда закончатся остатки
        if avg_daily_sales > 0:
            days_until_out_of_stock = current_stock / avg_daily_sales
        else:
            days_until_out_of_stock = float('inf')
        
        # Прогноз остатков на N дней вперед
        forecast = []
        for i in range(days_ahead):
            days_from_now = i + 1
            forecasted_stock = max(0, current_stock - (avg_daily_sales * days_from_now))
            
            forecast.append({
                'days_from_now': days_from_now,
                'forecasted_stock': float(forecasted_stock),
                'will_be_out_of_stock': forecasted_stock <= 0
            })
        
        return {
            'current_stock': float(current_stock),
            'avg_daily_sales': float(avg_daily_sales),
            'days_until_out_of_stock': float(days_until_out_of_stock) if days_until_out_of_stock != float('inf') else None,
            'forecast': forecast,
            'sku': sku if sku else 'all'
        }
    
    def detect_anomalies(self, date_from=None, date_to=None):
        """
        Обнаружение аномалий в продажах
        
        Args:
            date_from: начальная дата
            date_to: конечная дата
        
        Returns:
            dict с обнаруженными аномалиями
        """
        if not self.orders:
            return {}
        
        df = pd.DataFrame(self.orders)
        
        # Фильтруем доставленные заказы
        delivered_mask = df['status'].apply(self._is_delivered_status)
        delivered = df[delivered_mask].copy()
        
        # Фильтруем по дате
        if date_from or date_to:
            delivered['_order_date'] = pd.to_datetime(
                delivered.get('delivery_date', delivered.get('shipment_date')),
                errors='coerce'
            )
            delivered = delivered[delivered['_order_date'].notna()]
            
            if date_from:
                date_from_dt = pd.to_datetime(date_from)
                delivered = delivered[delivered['_order_date'] >= date_from_dt]
            
            if date_to:
                date_to_dt = pd.to_datetime(date_to)
                delivered = delivered[delivered['_order_date'] <= date_to_dt]
        
        if delivered.empty:
            return {}
        
        # Подготавливаем временной ряд
        ts = self._prepare_time_series(delivered, 'delivery_date', 'paid_by_customer')
        
        if ts is None or len(ts) < 7:
            return {}
        
        # Вычисляем статистики
        mean = ts['value'].mean()
        std = ts['value'].std()
        
        # Аномалии: значения за пределами 2 стандартных отклонений
        threshold_upper = mean + (2 * std)
        threshold_lower = mean - (2 * std)
        
        anomalies = ts[
            (ts['value'] > threshold_upper) | 
            (ts['value'] < threshold_lower)
        ].copy()
        
        anomaly_list = []
        for _, row in anomalies.iterrows():
            deviation = ((row['value'] - mean) / std) if std > 0 else 0
            anomaly_list.append({
                'date': row['date'].strftime('%Y-%m-%d'),
                'value': float(row['value']),
                'deviation': float(deviation),
                'type': 'high' if row['value'] > threshold_upper else 'low'
            })
        
        return {
            'anomalies': anomaly_list,
            'statistics': {
                'mean': float(mean),
                'std': float(std),
                'threshold_upper': float(threshold_upper),
                'threshold_lower': float(threshold_lower),
                'anomaly_count': len(anomaly_list)
            }
        }
    
    def forecast_seasonality(self, days_ahead=90):
        """
        Прогнозирование с учетом сезонности
        
        Args:
            days_ahead: количество дней для прогноза
        
        Returns:
            dict с прогнозом с учетом сезонности
        """
        if not self.orders:
            return {}
        
        df = pd.DataFrame(self.orders)
        
        # Фильтруем доставленные заказы
        delivered_mask = df['status'].apply(self._is_delivered_status)
        delivered = df[delivered_mask].copy()
        
        if delivered.empty:
            return {}
        
        # Подготавливаем временной ряд
        ts = self._prepare_time_series(delivered, 'delivery_date', 'paid_by_customer')
        
        if ts is None or ts.empty:
            return {}
        
        # Вычисляем сезонность по дням недели
        ts['day_of_week'] = ts['date'].dt.weekday
        ts['month'] = ts['date'].dt.month
        
        weekday_avg = ts.groupby('day_of_week')['value'].mean().to_dict()
        month_avg = ts.groupby('month')['value'].mean().to_dict()
        
        # Базовое среднее
        base_avg = ts['value'].mean()
        
        # Генерируем прогноз с учетом сезонности
        last_date = ts['date'].max()
        forecast_dates = pd.date_range(start=last_date + timedelta(days=1), periods=days_ahead, freq='D')
        
        forecast = []
        for date in forecast_dates:
            day_of_week = date.weekday()
            month = date.month
            
            # Базовый прогноз
            forecast_value = base_avg
            
            # Корректировка по дню недели
            if day_of_week in weekday_avg:
                weekday_factor = weekday_avg[day_of_week] / base_avg if base_avg > 0 else 1
                forecast_value = forecast_value * weekday_factor
            
            # Корректировка по месяцу
            if month in month_avg:
                month_factor = month_avg[month] / base_avg if base_avg > 0 else 1
                forecast_value = forecast_value * month_factor
            
            forecast.append({
                'date': date.strftime('%Y-%m-%d'),
                'revenue': float(max(0, forecast_value)),
                'day_of_week': day_of_week,
                'month': month
            })
        
        total_forecast = sum(f['revenue'] for f in forecast)
        
        return {
            'forecast': forecast,
            'summary': {
                'total_revenue': float(total_forecast),
                'avg_daily_revenue': float(total_forecast / days_ahead)
            },
            'seasonality_factors': {
                'weekday': {str(k): float(v) for k, v in weekday_avg.items()},
                'month': {str(k): float(v) for k, v in month_avg.items()}
            }
        }
