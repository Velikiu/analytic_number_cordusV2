"""
Анализатор отзывов и рейтингов товаров Ozon
Оценивает качество отзывов, тональность, скорость ответов
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import re


class ReviewAnalyzer:
    """Анализатор отзывов и рейтингов"""
    
    # Положительные слова для анализа тональности
    POSITIVE_WORDS = [
        'отлично', 'хорошо', 'прекрасно', 'замечательно', 'рекомендую',
        'качественный', 'удобный', 'эффективный', 'помог', 'доволен',
        'работает', 'нравится', 'супер', 'класс', 'отличный'
    ]
    
    # Отрицательные слова
    NEGATIVE_WORDS = [
        'плохо', 'не работает', 'брак', 'некачественный', 'разочарован',
        'не рекомендую', 'неудобный', 'неэффективный', 'не помог',
        'недоволен', 'ужасно', 'кошмар', 'проблема', 'неисправность'
    ]
    
    TARGET_RATING = 4.7
    TARGET_RESPONSE_TIME_HOURS = 24
    TARGET_PHOTO_REVIEWS_RATIO = 0.3  # 30% отзывов с фото
    
    def __init__(self):
        self.reviews_data = []
    
    def analyze_review_sentiment(self, review_text: str) -> Dict:
        """
        Анализирует тональность отзыва
        
        Args:
            review_text: текст отзыва
        
        Returns:
            словарь с анализом тональности
        """
        if not review_text:
            return {
                'sentiment': 'neutral',
                'score': 0,
                'positive_words': [],
                'negative_words': []
            }
        
        text_lower = review_text.lower()
        
        # Поиск положительных слов
        positive_found = [word for word in self.POSITIVE_WORDS if word in text_lower]
        
        # Поиск отрицательных слов
        negative_found = [word for word in self.NEGATIVE_WORDS if word in text_lower]
        
        # Определение тональности
        positive_score = len(positive_found)
        negative_score = len(negative_found)
        
        if positive_score > negative_score:
            sentiment = 'positive'
            score = min(positive_score * 10, 100)
        elif negative_score > positive_score:
            sentiment = 'negative'
            score = max(100 - negative_score * 10, 0)
        else:
            sentiment = 'neutral'
            score = 50
        
        return {
            'sentiment': sentiment,
            'score': score,
            'positive_words': positive_found,
            'negative_words': negative_found,
            'positive_count': positive_score,
            'negative_count': negative_score
        }
    
    def analyze_single_review(self, review_data: Dict) -> Dict:
        """
        Анализирует один отзыв
        
        Args:
            review_data: словарь с данными отзыва
        
        Returns:
            анализ отзыва
        """
        review_text = review_data.get('text', '') or review_data.get('comment', '') or ''
        rating = review_data.get('rating', 0) or review_data.get('score', 0) or 0
        
        # Анализ тональности
        sentiment_analysis = self.analyze_review_sentiment(review_text)
        
        # Проверка наличия фото
        has_photo = bool(review_data.get('photos') or review_data.get('images'))
        
        # Проверка ответа продавца
        has_response = bool(review_data.get('seller_response') or review_data.get('response'))
        
        # Время ответа (если есть данные)
        response_time_hours = None
        if has_response:
            created_date = review_data.get('created_date') or review_data.get('date')
            response_date = review_data.get('response_date')
            if created_date and response_date:
                try:
                    created = pd.to_datetime(created_date)
                    responded = pd.to_datetime(response_date)
                    response_time_hours = (responded - created).total_seconds() / 3600
                except:
                    pass
        
        return {
            'review_id': review_data.get('id') or review_data.get('review_id'),
            'rating': float(rating) if rating else 0,
            'sentiment': sentiment_analysis['sentiment'],
            'sentiment_score': sentiment_analysis['score'],
            'has_photo': has_photo,
            'has_response': has_response,
            'response_time_hours': response_time_hours,
            'text_length': len(review_text),
            'is_helpful': review_data.get('helpful_count', 0) > 0
        }
    
    def analyze_reviews(self, reviews_data: List[Dict]) -> Dict:
        """
        Анализирует множество отзывов
        
        Args:
            reviews_data: список отзывов
        
        Returns:
            агрегированная статистика
        """
        if not reviews_data:
            return {
                'total_reviews': 0,
                'average_rating': 0,
                'rating_distribution': {},
                'sentiment_distribution': {},
                'response_rate': 0,
                'average_response_time_hours': None,
                'photo_reviews_ratio': 0,
                'recommendations': []
            }
        
        analyzed_reviews = []
        for review in reviews_data:
            analyzed = self.analyze_single_review(review)
            analyzed_reviews.append(analyzed)
        
        df = pd.DataFrame(analyzed_reviews)
        
        # Средний рейтинг
        avg_rating = df['rating'].mean() if 'rating' in df.columns else 0
        
        # Распределение рейтингов
        rating_dist = df['rating'].value_counts().to_dict() if 'rating' in df.columns else {}
        
        # Распределение тональности
        sentiment_dist = df['sentiment'].value_counts().to_dict() if 'sentiment' in df.columns else {}
        
        # Процент ответов
        response_rate = (df['has_response'].sum() / len(df) * 100) if 'has_response' in df.columns else 0
        
        # Среднее время ответа
        response_times = df[df['response_time_hours'].notna()]['response_time_hours']
        avg_response_time = response_times.mean() if len(response_times) > 0 else None
        
        # Процент отзывов с фото
        photo_reviews = df['has_photo'].sum() if 'has_photo' in df.columns else 0
        photo_ratio = (photo_reviews / len(df)) if len(df) > 0 else 0
        
        # Генерация рекомендаций
        recommendations = self._generate_recommendations(
            avg_rating, response_rate, avg_response_time, photo_ratio, sentiment_dist
        )
        
        return {
            'total_reviews': len(analyzed_reviews),
            'average_rating': round(avg_rating, 2),
            'rating_distribution': {str(k): int(v) for k, v in rating_dist.items()},
            'sentiment_distribution': sentiment_dist,
            'response_rate': round(response_rate, 2),
            'average_response_time_hours': round(avg_response_time, 2) if avg_response_time else None,
            'photo_reviews_ratio': round(photo_ratio * 100, 2),
            'positive_reviews_count': sentiment_dist.get('positive', 0),
            'negative_reviews_count': sentiment_dist.get('negative', 0),
            'neutral_reviews_count': sentiment_dist.get('neutral', 0),
            'recommendations': recommendations,
            'reviews_details': analyzed_reviews[:10]  # Первые 10 для деталей
        }
    
    def _generate_recommendations(
        self, 
        avg_rating: float, 
        response_rate: float, 
        avg_response_time: Optional[float],
        photo_ratio: float,
        sentiment_dist: Dict
    ) -> List[Dict]:
        """Генерирует рекомендации на основе анализа"""
        recommendations = []
        
        # Рейтинг
        if avg_rating < self.TARGET_RATING:
            recommendations.append({
                'category': 'Рейтинг',
                'priority': 'high',
                'title': 'Низкий рейтинг товаров',
                'description': f'Средний рейтинг: {avg_rating:.2f}. Целевой: {self.TARGET_RATING}+',
                'action': 'Улучшите качество товаров и работу с отзывами'
            })
        
        # Ответы на отзывы
        if response_rate < 80:
            recommendations.append({
                'category': 'Отзывы',
                'priority': 'high',
                'title': 'Низкий процент ответов на отзывы',
                'description': f'Отвечаете на {response_rate:.1f}% отзывов. Рекомендуется отвечать на все отзывы.',
                'action': 'Настройте автоматические ответы или отвечайте вручную на все отзывы'
            })
        
        # Время ответа
        if avg_response_time and avg_response_time > self.TARGET_RESPONSE_TIME_HOURS:
            recommendations.append({
                'category': 'Отзывы',
                'priority': 'medium',
                'title': 'Долгое время ответа на отзывы',
                'description': f'Среднее время ответа: {avg_response_time:.1f} часов. Целевое: {self.TARGET_RESPONSE_TIME_HOURS} часов.',
                'action': 'Отвечайте на отзывы быстрее, в течение 24 часов'
            })
        
        # Отзывы с фото
        if photo_ratio < self.TARGET_PHOTO_REVIEWS_RATIO:
            recommendations.append({
                'category': 'Отзывы',
                'priority': 'medium',
                'title': 'Мало отзывов с фотографиями',
                'description': f'Только {photo_ratio*100:.1f}% отзывов содержат фото. Целевое: {self.TARGET_PHOTO_REVIEWS_RATIO*100}%',
                'action': 'Стимулируйте покупателей оставлять отзывы с фотографиями'
            })
        
        # Негативные отзывы
        negative_count = sentiment_dist.get('negative', 0)
        total = sum(sentiment_dist.values())
        if total > 0 and negative_count / total > 0.1:  # Более 10% негативных
            recommendations.append({
                'category': 'Отзывы',
                'priority': 'critical',
                'title': 'Высокий процент негативных отзывов',
                'description': f'{negative_count} негативных отзывов из {total} ({negative_count/total*100:.1f}%)',
                'action': 'Проанализируйте причины негативных отзывов и устраните проблемы'
            })
        
        return recommendations
    
    def get_review_metrics_for_store(self, store_data: Dict) -> Dict:
        """
        Получает метрики отзывов из данных магазина
        
        Args:
            store_data: данные магазина
        
        Returns:
            метрики отзывов
        """
        reviews_info = store_data.get('reviews_info', {})
        rating_info = store_data.get('rating_info', {})
        
        total_reviews = reviews_info.get('total_reviews', 0) or 0
        overall_rating = rating_info.get('overall_rating', 0) or 0
        
        # Если есть детальные данные об отзывах
        reviews_list = reviews_info.get('reviews', []) or []
        
        if reviews_list:
            return self.analyze_reviews(reviews_list)
        
        # Упрощенная версия на основе агрегированных данных
        recommendations = []
        
        if overall_rating > 0 and overall_rating < self.TARGET_RATING:
            recommendations.append({
                'category': 'Рейтинг',
                'priority': 'high',
                'title': 'Низкий рейтинг магазина',
                'description': f'Рейтинг: {overall_rating:.2f}. Целевой: {self.TARGET_RATING}+',
                'action': 'Улучшите качество товаров и сервиса'
            })
        
        return {
            'total_reviews': total_reviews,
            'average_rating': overall_rating,
            'note': 'Данные ограничены. Для полного анализа нужны детальные данные об отзывах из кабинета Ozon или API.',
            'recommendations': recommendations
        }
