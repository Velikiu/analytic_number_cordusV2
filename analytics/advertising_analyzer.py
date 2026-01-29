"""
Анализатор рекламных кампаний Ozon
Оценивает эффективность рекламы, ROI, оптимизацию ставок
"""
from typing import Dict, List, Optional
import pandas as pd


class AdvertisingAnalyzer:
    """Анализатор рекламных кампаний"""
    
    # Минимальные ставки для разных типов рекламы (2025)
    MIN_TRAFFARET_CPC = 7  # Минимальная ставка "Трафаретов"
    OPTIMAL_ROI_THRESHOLD = 3.0  # Оптимальный ROI (3x)
    MIN_ROI_THRESHOLD = 1.5  # Минимальный приемлемый ROI
    
    def __init__(self):
        self.campaigns_data = []
    
    def analyze_campaign(self, campaign_data: Dict) -> Dict:
        """
        Анализирует одну рекламную кампанию
        
        Args:
            campaign_data: данные кампании
        
        Returns:
            анализ эффективности кампании
        """
        campaign_type = campaign_data.get('type', 'unknown')
        spend = float(campaign_data.get('spend', 0) or 0)
        revenue = float(campaign_data.get('revenue', 0) or 0)
        clicks = int(campaign_data.get('clicks', 0) or 0)
        orders = int(campaign_data.get('orders', 0) or 0)
        impressions = int(campaign_data.get('impressions', 0) or 0)
        
        # Расчет метрик
        roi = (revenue / spend) if spend > 0 else 0
        cpc = (spend / clicks) if clicks > 0 else 0
        cpo = (spend / orders) if orders > 0 else 0
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        conversion_rate = (orders / clicks * 100) if clicks > 0 else 0
        
        # Оценка эффективности
        efficiency_score = self._calculate_efficiency_score(roi, ctr, conversion_rate, campaign_type)
        
        # Рекомендации
        recommendations = self._generate_campaign_recommendations(
            campaign_type, roi, cpc, cpo, ctr, conversion_rate, spend, revenue
        )
        
        return {
            'campaign_id': campaign_data.get('id') or campaign_data.get('campaign_id'),
            'campaign_type': campaign_type,
            'spend': spend,
            'revenue': revenue,
            'clicks': clicks,
            'orders': orders,
            'impressions': impressions,
            'roi': round(roi, 2),
            'cpc': round(cpc, 2),
            'cpo': round(cpo, 2),
            'ctr': round(ctr, 2),
            'conversion_rate': round(conversion_rate, 2),
            'efficiency_score': efficiency_score,
            'recommendations': recommendations
        }
    
    def _calculate_efficiency_score(
        self, 
        roi: float, 
        ctr: float, 
        conversion_rate: float,
        campaign_type: str
    ) -> float:
        """Рассчитывает общий score эффективности кампании"""
        score = 0
        
        # ROI (50 баллов)
        if roi >= self.OPTIMAL_ROI_THRESHOLD:
            score += 50
        elif roi >= self.MIN_ROI_THRESHOLD:
            score += 30
        elif roi >= 1.0:
            score += 15
        else:
            score += 5
        
        # CTR (25 баллов)
        if ctr >= 2.0:
            score += 25
        elif ctr >= 1.0:
            score += 15
        elif ctr >= 0.5:
            score += 10
        else:
            score += 5
        
        # Conversion Rate (25 баллов)
        if conversion_rate >= 5.0:
            score += 25
        elif conversion_rate >= 3.0:
            score += 15
        elif conversion_rate >= 1.0:
            score += 10
        else:
            score += 5
        
        return min(score, 100)
    
    def _generate_campaign_recommendations(
        self,
        campaign_type: str,
        roi: float,
        cpc: float,
        cpo: float,
        ctr: float,
        conversion_rate: float,
        spend: float,
        revenue: float
    ) -> List[Dict]:
        """Генерирует рекомендации для кампании"""
        recommendations = []
        
        # ROI рекомендации
        if roi < self.MIN_ROI_THRESHOLD:
            recommendations.append({
                'category': 'Эффективность',
                'priority': 'critical',
                'title': 'Низкий ROI рекламной кампании',
                'description': f'ROI: {roi:.2f}x. Минимальный приемлемый: {self.MIN_ROI_THRESHOLD}x',
                'action': 'Оптимизируйте ставки или остановите кампанию'
            })
        elif roi < self.OPTIMAL_ROI_THRESHOLD:
            recommendations.append({
                'category': 'Эффективность',
                'priority': 'medium',
                'title': 'ROI можно улучшить',
                'description': f'ROI: {roi:.2f}x. Оптимальный: {self.OPTIMAL_ROI_THRESHOLD}x+',
                'action': 'Попробуйте снизить ставки или улучшить конверсию'
            })
        
        # CPC для "Трафаретов"
        if campaign_type == 'traffaret' or campaign_type == 'cpc':
            if cpc < self.MIN_TRAFFARET_CPC:
                recommendations.append({
                    'category': 'Ставки',
                    'priority': 'low',
                    'title': 'Ставка ниже минимума',
                    'description': f'CPC: {cpc:.2f} руб. Минимум для "Трафаретов": {self.MIN_TRAFFARET_CPC} руб',
                    'action': 'Повысьте ставку до минимума для участия в аукционе'
                })
            elif cpc > self.MIN_TRAFFARET_CPC * 2:
                recommendations.append({
                    'category': 'Ставки',
                    'priority': 'medium',
                    'title': 'Высокая ставка CPC',
                    'description': f'CPC: {cpc:.2f} руб. Возможно, можно снизить без потери позиций',
                    'action': 'Попробуйте постепенно снижать ставку и отслеживать результаты'
                })
        
        # CTR рекомендации
        if ctr < 1.0:
            recommendations.append({
                'category': 'Контент',
                'priority': 'high',
                'title': 'Низкий CTR',
                'description': f'CTR: {ctr:.2f}%. Низкий кликабельность объявлений',
                'action': 'Улучшите заголовки и изображения в рекламе'
            })
        
        # Conversion Rate рекомендации
        if conversion_rate < 2.0:
            recommendations.append({
                'category': 'Конверсия',
                'priority': 'high',
                'title': 'Низкая конверсия из рекламы',
                'description': f'Конверсия: {conversion_rate:.2f}%. Пользователи кликают, но не покупают',
                'action': 'Улучшите карточки товаров и цены для рекламного трафика'
            })
        
        return recommendations
    
    def analyze_multiple_campaigns(self, campaigns_data: List[Dict]) -> Dict:
        """
        Анализирует несколько кампаний
        
        Args:
            campaigns_data: список кампаний
        
        Returns:
            агрегированная статистика
        """
        if not campaigns_data:
            return {
                'total_campaigns': 0,
                'total_spend': 0,
                'total_revenue': 0,
                'average_roi': 0,
                'recommendations': []
            }
        
        analyzed_campaigns = []
        for campaign in campaigns_data:
            analyzed = self.analyze_campaign(campaign)
            analyzed_campaigns.append(analyzed)
        
        df = pd.DataFrame(analyzed_campaigns)
        
        # Агрегация
        total_spend = df['spend'].sum()
        total_revenue = df['revenue'].sum()
        total_roi = (total_revenue / total_spend) if total_spend > 0 else 0
        avg_roi = df['roi'].mean()
        avg_cpc = df['cpc'].mean()
        avg_ctr = df['ctr'].mean()
        avg_conversion = df['conversion_rate'].mean()
        
        # Общие рекомендации
        all_recommendations = []
        for campaign in analyzed_campaigns:
            all_recommendations.extend(campaign['recommendations'])
        
        # Приоритизация рекомендаций
        critical_recs = [r for r in all_recommendations if r.get('priority') == 'critical']
        high_recs = [r for r in all_recommendations if r.get('priority') == 'high']
        
        return {
            'total_campaigns': len(analyzed_campaigns),
            'total_spend': round(total_spend, 2),
            'total_revenue': round(total_revenue, 2),
            'total_roi': round(total_roi, 2),
            'average_roi': round(avg_roi, 2),
            'average_cpc': round(avg_cpc, 2),
            'average_ctr': round(avg_ctr, 2),
            'average_conversion_rate': round(avg_conversion, 2),
            'campaigns_details': analyzed_campaigns,
            'recommendations': critical_recs + high_recs[:5]  # Критичные + топ-5 важных
        }
    
    def get_advertising_recommendations_based_on_metrics(
        self,
        sales_metrics: Dict,
        financial_metrics: Dict
    ) -> List[Dict]:
        """
        Генерирует рекомендации по рекламе на основе общих метрик
        
        Args:
            sales_metrics: метрики продаж
            financial_metrics: финансовые метрики
        
        Returns:
            список рекомендаций
        """
        recommendations = []
        
        conversion_rate = sales_metrics.get('conversion_rate', 0) or 0
        margin_percent = financial_metrics.get('margin_percent', 0) or 0
        
        # Рекомендации по использованию "Трафаретов"
        if conversion_rate < 70:
            recommendations.append({
                'category': 'Реклама',
                'priority': 'high',
                'title': 'Использование "Трафаретов" для увеличения трафика',
                'description': f'Конверсия: {conversion_rate:.1f}%. "Трафареты" могут увеличить охват в 8 раз, продажи в 3.3 раза.',
                'action': 'Начните с минимальной ставки 7 руб/клик и постепенно оптимизируйте',
                'action_plan': {
                    'immediate': [
                        'Создайте кампанию "Трафареты" с минимальной ставкой 7 руб/клик',
                        'Выберите топ-5 товаров для продвижения',
                        'Настройте бюджет на 5000-10000 руб для теста'
                    ],
                    'short_term': [
                        'Анализируйте ROI каждые 3 дня',
                        'Оптимизируйте ставки на основе данных',
                        'Расширяйте кампанию на другие товары при положительном ROI'
                    ],
                    'long_term': [
                        'Используйте объединенные CPC/CPO ставки для оптимизации',
                        'Создайте стратегию рекламы для разных товаров',
                        'Автоматизируйте управление ставками'
                    ],
                    'expected_result': 'Увеличение продаж на 30-50% при ROI 2-3x'
                }
            })
        
        # Рекомендации по "Вывод в топ"
        if margin_percent >= 20:
            recommendations.append({
                'category': 'Реклама',
                'priority': 'medium',
                'title': 'Использование "Вывод в топ" для топ-товаров',
                'description': f'Маржа: {margin_percent:.1f}%. Достаточная маржа для использования премиум-инструмента.',
                'action': 'Используйте "Вывод в топ" для топ-3 товаров',
                'action_plan': {
                    'immediate': [
                        'Выберите 1-2 топ-товара с лучшей маржой',
                        'Создайте кампанию "Вывод в топ"',
                        'Используйте возможность закрепления положительного отзыва'
                    ],
                    'short_term': [
                        'Мониторьте позиции в топ-12',
                        'Анализируйте конверсию из топ-позиций',
                        'Оптимизируйте ставки VCG-аукциона'
                    ],
                    'expected_result': 'Увеличение продаж топ-товаров на 50-100%'
                }
            })
        
        # Рекомендации по акционным механикам
        recommendations.append({
            'category': 'Реклама',
            'priority': 'medium',
            'title': 'Использование акционных механик',
            'description': 'Акции "Товар дня", "Уценённый товар" увеличивают видимость и продажи.',
            'action': 'Участвуйте в акционных механиках Ozon',
            'action_plan': {
                'immediate': [
                    'Подайте заявку на "Товар дня" для топ-товара',
                    'Используйте "Уценённый товар" для распродажи остатков',
                    'Участвуйте в "Выгодный день" для увеличения продаж'
                ],
                'short_term': [
                    'Планируйте участие в акциях заранее',
                    'Готовьте остатки для акций',
                    'Анализируйте эффективность акций'
                ],
                'expected_result': 'Увеличение продаж в дни акций на 100-200%'
            }
        })
        
        return recommendations
