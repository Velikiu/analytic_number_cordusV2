"""
Конкурентный анализ для маркетплейса Ozon
Сравнение с конкурентами по ценам, рейтингам, позициям
"""
from datetime import datetime
import pandas as pd
from collections import defaultdict


class CompetitorAnalysis:
    """Класс для конкурентного анализа"""
    
    def __init__(self, orders=None, store_data=None):
        """
        Инициализация
        
        Args:
            orders: список заказов (для анализа собственных данных)
            store_data: данные магазина (для сравнения)
        """
        self.orders = orders or []
        self.store_data = store_data or {}
    
    def _is_delivered_status(self, status):
        """Проверяет, является ли статус доставленным"""
        if not status or pd.isna(status):
            return False
        status_str = str(status).lower().strip()
        return status_str in ['доставлен', 'delivered', 'доставка', 'delivery']
    
    def analyze_pricing_position(self, own_products, competitor_data):
        """
        Анализ ценовой позиции
        
        Args:
            own_products: dict с данными собственных товаров {sku: {price, ...}}
            competitor_data: dict с данными конкурентов {sku: [{competitor: name, price: value, ...}]}
        
        Returns:
            dict с анализом ценовой позиции
        """
        if not own_products or not competitor_data:
            return {}
        
        analysis = {}
        
        for sku, own_data in own_products.items():
            if sku not in competitor_data:
                continue
            
            own_price = own_data.get('price', 0)
            competitors = competitor_data[sku]
            
            if not competitors or own_price == 0:
                continue
            
            # Статистика по конкурентам
            competitor_prices = [c.get('price', 0) for c in competitors if c.get('price', 0) > 0]
            
            if not competitor_prices:
                continue
            
            min_price = min(competitor_prices)
            max_price = max(competitor_prices)
            avg_price = sum(competitor_prices) / len(competitor_prices)
            median_price = sorted(competitor_prices)[len(competitor_prices) // 2]
            
            # Позиция относительно конкурентов
            price_position = 'above_avg'
            if own_price < min_price:
                price_position = 'lowest'
            elif own_price < avg_price:
                price_position = 'below_avg'
            elif own_price == avg_price:
                price_position = 'at_avg'
            elif own_price < max_price:
                price_position = 'above_avg'
            else:
                price_position = 'highest'
            
            # Процент от средней цены
            price_vs_avg = ((own_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
            
            # Рекомендация по цене
            recommendation = self._get_price_recommendation(own_price, avg_price, min_price, max_price)
            
            analysis[sku] = {
                'own_price': float(own_price),
                'competitor_stats': {
                    'count': len(competitors),
                    'min_price': float(min_price),
                    'max_price': float(max_price),
                    'avg_price': float(avg_price),
                    'median_price': float(median_price)
                },
                'price_position': price_position,
                'price_vs_avg_percent': float(price_vs_avg),
                'recommendation': recommendation
            }
        
        return analysis
    
    def _get_price_recommendation(self, own_price, avg_price, min_price, max_price):
        """Получить рекомендацию по цене"""
        if own_price < min_price:
            return {
                'action': 'increase',
                'suggested_price': float(avg_price * 0.95),  # 5% ниже средней
                'reason': 'Цена слишком низкая, можно повысить до среднерыночной'
            }
        elif own_price > max_price:
            return {
                'action': 'decrease',
                'suggested_price': float(avg_price * 1.05),  # 5% выше средней
                'reason': 'Цена слишком высокая, рекомендуется снизить'
            }
        elif own_price > avg_price * 1.1:
            return {
                'action': 'consider_decrease',
                'suggested_price': float(avg_price),
                'reason': 'Цена выше среднерыночной на 10%+, рассмотрите снижение'
            }
        elif own_price < avg_price * 0.9:
            return {
                'action': 'consider_increase',
                'suggested_price': float(avg_price),
                'reason': 'Цена ниже среднерыночной на 10%+, можно повысить'
            }
        else:
            return {
                'action': 'maintain',
                'suggested_price': float(own_price),
                'reason': 'Цена в оптимальном диапазоне'
            }
    
    def analyze_rating_position(self, own_rating, competitor_ratings):
        """
        Анализ позиции по рейтингу
        
        Args:
            own_rating: собственный рейтинг
            competitor_ratings: список рейтингов конкурентов
        
        Returns:
            dict с анализом рейтинга
        """
        if not competitor_ratings:
            return {}
        
        competitor_ratings = [r for r in competitor_ratings if r and r > 0]
        
        if not competitor_ratings:
            return {}
        
        avg_rating = sum(competitor_ratings) / len(competitor_ratings)
        max_rating = max(competitor_ratings)
        min_rating = min(competitor_ratings)
        
        rating_position = 'above_avg'
        if own_rating < min_rating:
            rating_position = 'lowest'
        elif own_rating < avg_rating:
            rating_position = 'below_avg'
        elif own_rating == avg_rating:
            rating_position = 'at_avg'
        elif own_rating >= max_rating:
            rating_position = 'highest'
        
        rating_vs_avg = own_rating - avg_rating
        
        return {
            'own_rating': float(own_rating) if own_rating else None,
            'competitor_stats': {
                'count': len(competitor_ratings),
                'avg_rating': float(avg_rating),
                'max_rating': float(max_rating),
                'min_rating': float(min_rating)
            },
            'rating_position': rating_position,
            'rating_vs_avg': float(rating_vs_avg),
            'recommendation': self._get_rating_recommendation(own_rating, avg_rating, max_rating)
        }
    
    def _get_rating_recommendation(self, own_rating, avg_rating, max_rating):
        """Получить рекомендацию по рейтингу"""
        if not own_rating:
            return {
                'action': 'improve',
                'target': float(avg_rating),
                'reason': 'Нет данных о рейтинге, необходимо улучшить'
            }
        
        if own_rating < avg_rating:
            return {
                'action': 'improve_critical',
                'target': float(avg_rating),
                'reason': f'Рейтинг {own_rating:.2f} ниже среднерыночного {avg_rating:.2f}, требуется улучшение'
            }
        elif own_rating < max_rating - 0.1:
            return {
                'action': 'improve',
                'target': float(max_rating),
                'reason': f'Рейтинг можно улучшить до {max_rating:.2f}'
            }
        else:
            return {
                'action': 'maintain',
                'target': float(own_rating),
                'reason': 'Рейтинг на высоком уровне, поддерживайте качество'
            }
    
    def analyze_market_share(self, own_sales, competitor_sales):
        """
        Анализ доли рынка
        
        Args:
            own_sales: собственные продажи (dict {sku: revenue})
            competitor_sales: продажи конкурентов (dict {sku: {competitor: revenue}})
        
        Returns:
            dict с анализом доли рынка
        """
        if not own_sales or not competitor_sales:
            return {}
        
        market_share = {}
        
        for sku, own_revenue in own_sales.items():
            if sku not in competitor_sales:
                continue
            
            competitors = competitor_sales[sku]
            total_market = own_revenue + sum(competitors.values())
            
            if total_market == 0:
                continue
            
            own_share = (own_revenue / total_market * 100)
            
            # Позиция по доле рынка
            competitor_shares = [(rev / total_market * 100) for rev in competitors.values()]
            max_competitor_share = max(competitor_shares) if competitor_shares else 0
            
            position = 'leader'
            if own_share < max_competitor_share:
                position = 'follower'
            elif own_share < 10:
                position = 'small'
            
            market_share[sku] = {
                'own_revenue': float(own_revenue),
                'total_market': float(total_market),
                'market_share_percent': float(own_share),
                'position': position,
                'max_competitor_share': float(max_competitor_share),
                'competitors_count': len(competitors)
            }
        
        return market_share
    
    def get_competitive_summary(self, own_data, competitor_data):
        """
        Получить общую сводку по конкурентной позиции
        
        Args:
            own_data: собственные данные {products: {...}, rating: value, ...}
            competitor_data: данные конкурентов
        
        Returns:
            dict с общей сводкой
        """
        summary = {
            'pricing': {},
            'rating': {},
            'market_share': {},
            'overall_position': 'unknown'
        }
        
        # Анализ цен
        if 'products' in own_data and 'pricing' in competitor_data:
            summary['pricing'] = self.analyze_pricing_position(
                own_data['products'],
                competitor_data['pricing']
            )
        
        # Анализ рейтинга
        if 'rating' in own_data and 'ratings' in competitor_data:
            summary['rating'] = self.analyze_rating_position(
                own_data.get('rating'),
                competitor_data['ratings']
            )
        
        # Анализ доли рынка
        if 'sales' in own_data and 'sales' in competitor_data:
            summary['market_share'] = self.analyze_market_share(
                own_data['sales'],
                competitor_data['sales']
            )
        
        # Общая позиция
        summary['overall_position'] = self._calculate_overall_position(summary)
        
        return summary
    
    def _calculate_overall_position(self, summary):
        """Вычисляет общую конкурентную позицию"""
        scores = []
        
        # Оценка по ценам
        if summary.get('pricing'):
            pricing_scores = []
            for sku_data in summary['pricing'].values():
                position = sku_data.get('price_position', '')
                if position == 'lowest':
                    scores.append(1)  # Низкая оценка
                elif position == 'below_avg':
                    scores.append(2)
                elif position == 'at_avg':
                    scores.append(3)
                elif position == 'above_avg':
                    scores.append(4)
                elif position == 'highest':
                    scores.append(5)  # Высокая оценка
        
        # Оценка по рейтингу
        if summary.get('rating'):
            rating_pos = summary['rating'].get('rating_position', '')
            if rating_pos == 'lowest':
                scores.append(1)
            elif rating_pos == 'below_avg':
                scores.append(2)
            elif rating_pos == 'at_avg':
                scores.append(3)
            elif rating_pos == 'above_avg':
                scores.append(4)
            elif rating_pos == 'highest':
                scores.append(5)
        
        if not scores:
            return 'unknown'
        
        avg_score = sum(scores) / len(scores)
        
        if avg_score <= 2:
            return 'weak'
        elif avg_score <= 3:
            return 'average'
        elif avg_score <= 4:
            return 'strong'
        else:
            return 'leader'
    
    def get_recommendations(self, competitive_summary):
        """Получить рекомендации на основе конкурентного анализа"""
        recommendations = []
        
        # Рекомендации по ценам
        if competitive_summary.get('pricing'):
            for sku, pricing_data in competitive_summary['pricing'].items():
                rec = pricing_data.get('recommendation', {})
                if rec.get('action') != 'maintain':
                    recommendations.append({
                        'category': 'Ценообразование',
                        'priority': 'high' if rec.get('action') in ['increase', 'decrease'] else 'medium',
                        'title': f'Оптимизация цены для {sku}',
                        'description': rec.get('reason', ''),
                        'action': f"Текущая цена: {pricing_data['own_price']:.2f} руб. Рекомендуемая: {rec.get('suggested_price', 0):.2f} руб.",
                        'current_value': pricing_data['own_price'],
                        'suggested_value': rec.get('suggested_price')
                    })
        
        # Рекомендации по рейтингу
        if competitive_summary.get('rating'):
            rating_data = competitive_summary['rating']
            rec = rating_data.get('recommendation', {})
            if rec.get('action') != 'maintain':
                recommendations.append({
                    'category': 'Рейтинг',
                    'priority': 'high' if rec.get('action') == 'improve_critical' else 'medium',
                    'title': 'Улучшение рейтинга магазина',
                    'description': rec.get('reason', ''),
                    'action': f"Текущий рейтинг: {rating_data.get('own_rating', 'N/A')}. Целевой: {rec.get('target', 0):.2f}",
                    'current_value': rating_data.get('own_rating'),
                    'target_value': rec.get('target')
                })
        
        return recommendations
