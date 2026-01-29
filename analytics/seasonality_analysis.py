"""
Анализ сезонности и спадов продаж для маркетплейса Ozon
Обнаружение аномалий, сезонных паттернов и причин спадов
"""
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from collections import defaultdict


class SeasonalityAnalysis:
    """Класс для анализа сезонности и спадов продаж"""
    
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
    
    def analyze_sales_drop(self, date_from=None, date_to=None):
        """
        Анализирует спад продаж и определяет причины
        
        Args:
            date_from: начальная дата для анализа
            date_to: конечная дата для анализа
        
        Returns:
            dict с анализом спада и рекомендациями
        """
        if not self.orders:
            return {}
        
        df = pd.DataFrame(self.orders)
        
        # Фильтруем доставленные заказы
        delivered_mask = df['status'].apply(self._is_delivered_status)
        delivered = df[delivered_mask].copy()
        
        if delivered.empty:
            return {}
        
        # Получаем даты заказов
        delivered['order_date'] = pd.to_datetime(
            delivered.get('delivery_date', delivered.get('shipment_date', delivered.get('accepted_date'))),
            errors='coerce'
        )
        delivered = delivered[delivered['order_date'].notna()]
        
        if delivered.empty:
            return {}
        
        # Группируем по дням
        daily_sales = delivered.groupby(delivered['order_date'].dt.date).agg({
            'paid_by_customer': 'sum',
            'quantity': 'sum'
        }).reset_index()
        daily_sales.columns = ['date', 'revenue', 'quantity']
        daily_sales = daily_sales.sort_values('date')
        
        if len(daily_sales) < 7:
            return {}
        
        # Вычисляем скользящее среднее за 7 дней
        daily_sales['revenue_ma7'] = daily_sales['revenue'].rolling(window=7, min_periods=1).mean()
        
        # Находим периоды спада
        drops = self._detect_drops(daily_sales)
        
        # Анализируем причины спада
        analysis = {
            'drops': drops,
            'seasonal_factors': self._analyze_seasonal_factors(daily_sales),
            'recommendations': []
        }
        
        # Генерируем рекомендации на основе найденных спадов
        if drops:
            latest_drop = drops[-1]  # Последний спад
            analysis['recommendations'] = self._generate_drop_recommendations(latest_drop, daily_sales)
        
        return analysis
    
    def _detect_drops(self, daily_sales):
        """Обнаруживает периоды спада продаж"""
        drops = []
        
        if len(daily_sales) < 14:
            return drops
        
        # Вычисляем процентное изменение от предыдущего дня
        daily_sales['pct_change'] = daily_sales['revenue'].pct_change() * 100
        
        # Вычисляем среднее за последние 7 дней для сравнения
        daily_sales['avg_last_7d'] = daily_sales['revenue'].rolling(window=7, min_periods=1).mean().shift(1)
        
        # Находим дни со значительным падением (>30%)
        significant_drops = daily_sales[
            (daily_sales['pct_change'] < -30) | 
            ((daily_sales['revenue'] < daily_sales['avg_last_7d'] * 0.7) & daily_sales['avg_last_7d'].notna())
        ].copy()
        
        if significant_drops.empty:
            return drops
        
        # Группируем последовательные дни спада
        significant_drops['date'] = pd.to_datetime(significant_drops['date'])
        significant_drops = significant_drops.sort_values('date')
        
        current_drop = None
        for idx, row in significant_drops.iterrows():
            if current_drop is None:
                current_drop = {
                    'start_date': row['date'].date(),
                    'end_date': row['date'].date(),
                    'days': 1,
                    'max_drop_pct': abs(row['pct_change']) if not pd.isna(row['pct_change']) else 0,
                    'avg_revenue_before': 0,
                    'avg_revenue_during': row['revenue'],
                    'total_loss': 0
                }
            else:
                # Проверяем, является ли это продолжением предыдущего спада
                days_diff = (row['date'].date() - current_drop['end_date']).days
                if days_diff <= 3:  # Спад продолжается, если перерыв не более 3 дней
                    current_drop['end_date'] = row['date'].date()
                    current_drop['days'] += days_diff + 1
                    current_drop['max_drop_pct'] = max(
                        current_drop['max_drop_pct'],
                        abs(row['pct_change']) if not pd.isna(row['pct_change']) else 0
                    )
                    current_drop['avg_revenue_during'] = (
                        (current_drop['avg_revenue_during'] * (current_drop['days'] - 1) + row['revenue']) / 
                        current_drop['days']
                    )
                else:
                    # Завершаем текущий спад и начинаем новый
                    drops.append(self._finalize_drop(current_drop, daily_sales))
                    current_drop = {
                        'start_date': row['date'].date(),
                        'end_date': row['date'].date(),
                        'days': 1,
                        'max_drop_pct': abs(row['pct_change']) if not pd.isna(row['pct_change']) else 0,
                        'avg_revenue_before': 0,
                        'avg_revenue_during': row['revenue'],
                        'total_loss': 0
                    }
        
        # Добавляем последний спад
        if current_drop:
            drops.append(self._finalize_drop(current_drop, daily_sales))
        
        return drops
    
    def _finalize_drop(self, drop, daily_sales):
        """Завершает анализ спада, вычисляя дополнительные метрики"""
        # Находим среднюю выручку за 7 дней до спада
        drop_start = pd.to_datetime(drop['start_date'])
        before_period = daily_sales[
            (pd.to_datetime(daily_sales['date']) >= drop_start - timedelta(days=14)) &
            (pd.to_datetime(daily_sales['date']) < drop_start)
        ]
        
        if not before_period.empty:
            drop['avg_revenue_before'] = float(before_period['revenue'].mean())
            drop['drop_pct'] = float(
                ((drop['avg_revenue_before'] - drop['avg_revenue_during']) / drop['avg_revenue_before'] * 100)
                if drop['avg_revenue_before'] > 0 else 0
            )
            drop['total_loss'] = float(
                (drop['avg_revenue_before'] - drop['avg_revenue_during']) * drop['days']
            )
        else:
            drop['drop_pct'] = drop['max_drop_pct']
            drop['total_loss'] = 0
        
        # Определяем тип спада
        drop['type'] = self._classify_drop_type(drop)
        
        # Проверяем сезонность
        drop['is_seasonal'] = self._check_seasonality(drop['start_date'])
        
        return drop
    
    def _classify_drop_type(self, drop):
        """Классифицирует тип спада"""
        drop_pct = drop.get('drop_pct', 0)
        days = drop.get('days', 0)
        
        if drop_pct > 70:
            return 'критический'
        elif drop_pct > 50:
            return 'сильный'
        elif drop_pct > 30:
            return 'умеренный'
        else:
            return 'слабый'
    
    def _check_seasonality(self, start_date):
        """Проверяет, является ли спад сезонным"""
        if not start_date:
            return False
        
        # Январь после новогодних праздников - типичный спад
        if start_date.month == 1 and start_date.day <= 15:
            return True
        
        # Летний период (июль-август) - возможный спад
        if start_date.month in [7, 8]:
            return True
        
        return False
    
    def _analyze_seasonal_factors(self, daily_sales):
        """Анализирует сезонные факторы"""
        if daily_sales.empty:
            return {}
        
        daily_sales['date'] = pd.to_datetime(daily_sales['date'])
        daily_sales['month'] = daily_sales['date'].dt.month
        daily_sales['day_of_week'] = daily_sales['date'].dt.dayofweek
        daily_sales['is_weekend'] = daily_sales['day_of_week'].isin([5, 6])
        
        # Средняя выручка по месяцам
        monthly_avg = daily_sales.groupby('month')['revenue'].mean().to_dict()
        
        # Средняя выручка по дням недели
        weekday_avg = daily_sales.groupby('day_of_week')['revenue'].mean().to_dict()
        
        # Выходные vs будни
        weekend_avg = daily_sales[daily_sales['is_weekend']]['revenue'].mean()
        weekday_avg_all = daily_sales[~daily_sales['is_weekend']]['revenue'].mean()
        
        return {
            'monthly_pattern': {int(k): float(v) for k, v in monthly_avg.items()},
            'weekday_pattern': {int(k): float(v) for k, v in weekday_avg.items()},
            'weekend_impact': {
                'weekend_avg': float(weekend_avg) if not pd.isna(weekend_avg) else 0,
                'weekday_avg': float(weekday_avg_all) if not pd.isna(weekday_avg_all) else 0,
                'difference_pct': float(
                    ((weekend_avg - weekday_avg_all) / weekday_avg_all * 100)
                    if weekday_avg_all > 0 and not pd.isna(weekend_avg) else 0
                )
            }
        }
    
    def _generate_drop_recommendations(self, drop, daily_sales):
        """Генерирует рекомендации на основе анализа спада"""
        recommendations = []
        
        drop_pct = drop.get('drop_pct', 0)
        days = drop.get('days', 0)
        is_seasonal = drop.get('is_seasonal', False)
        drop_type = drop.get('type', 'слабый')
        
        if is_seasonal:
            recommendations.append({
                'title': 'Сезонный спад продаж',
                'description': f'Обнаружен спад продаж на {days} дней ({drop_pct:.1f}% снижение). Это типично для периода после новогодних праздников.',
                'priority': 'medium',
                'actions': [
                    'Планируйте маркетинговые акции заранее (за 1-2 недели до спада)',
                    'Создайте специальные предложения для января: "Новогодние скидки", "Зимняя распродажа"',
                    'Увеличьте рекламный бюджет на январь для компенсации естественного спада',
                    'Сфокусируйтесь на товарах, которые популярны в январе (спорт, здоровье, обучение)',
                    'Используйте email-маркетинг для возврата клиентов',
                    'Запустите программу лояльности с бонусами за покупки в январе'
                ],
                'expected_impact': f'Снижение влияния сезонного спада на 20-30%, поддержание выручки на уровне 70-80% от декабрьского уровня'
            })
        else:
            recommendations.append({
                'title': f'Критический спад продаж ({drop_type})',
                'description': f'Обнаружен {drop_type} спад продаж на {days} дней ({drop_pct:.1f}% снижение). Требуется немедленное вмешательство.',
                'priority': 'high' if drop_type in ['критический', 'сильный'] else 'medium',
                'actions': [
                    'Проверьте остатки товаров - возможно, закончились популярные позиции',
                    'Проверьте рейтинг и отзывы - возможно, появились негативные отзывы',
                    'Проверьте цены конкурентов - возможно, они снизили цены',
                    'Увеличьте рекламный бюджет немедленно',
                    'Запустите промо-акцию: скидки 15-20% на топ-товары',
                    'Проверьте технические проблемы: доступность товаров, работа корзины',
                    'Анализируйте конкурентов - возможно, они запустили агрессивную рекламу',
                    'Свяжитесь с постоянными клиентами через email/SMS с персональными предложениями'
                ],
                'expected_impact': 'Восстановление продаж до нормального уровня за 5-10 дней'
            })
        
        # Дополнительные рекомендации на основе длительности спада
        if days > 7:
            recommendations.append({
                'title': 'Длительный спад продаж',
                'description': f'Спад продолжается уже {days} дней. Необходимы активные меры.',
                'priority': 'high',
                'actions': [
                    'Проведите глубокий анализ причин: опрос клиентов, анализ конкурентов',
                    'Рассмотрите возможность временного снижения цен на 20-30%',
                    'Увеличьте количество промо-акций и специальных предложений',
                    'Проверьте позиции товаров в поиске Ozon',
                    'Улучшите карточки товаров: добавьте фото, видео, отзывы',
                    'Запустите программу ретаргетинга для посетителей, которые не купили'
                ],
                'expected_impact': 'Постепенное восстановление продаж в течение 2-3 недель'
            })
        
        return recommendations
    
    def get_drop_analysis_summary(self, date_from=None, date_to=None):
        """Получить краткую сводку по спадам"""
        analysis = self.analyze_sales_drop(date_from, date_to)
        
        if not analysis or not analysis.get('drops'):
            return {
                'has_drops': False,
                'message': 'Значительных спадов не обнаружено'
            }
        
        drops = analysis['drops']
        latest_drop = drops[-1]
        
        return {
            'has_drops': True,
            'total_drops': len(drops),
            'latest_drop': {
                'start_date': str(latest_drop['start_date']),
                'end_date': str(latest_drop['end_date']),
                'days': latest_drop['days'],
                'drop_pct': latest_drop.get('drop_pct', 0),
                'type': latest_drop.get('type', 'неизвестно'),
                'is_seasonal': latest_drop.get('is_seasonal', False),
                'total_loss': latest_drop.get('total_loss', 0)
            },
            'recommendations_count': len(analysis.get('recommendations', []))
        }
