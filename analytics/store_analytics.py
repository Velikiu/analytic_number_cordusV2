"""
Аналитика на основе данных магазина Ozon
Интегрирует данные с сайта в общую аналитику
"""
from datetime import datetime

import config


class StoreAnalytics:
    """Аналитика магазина на основе собранных данных"""
    
    def __init__(self):
        self.store_data = {}
    
    def load_store_data(self, store_data):
        """Загружает данные магазина"""
        self.store_data = store_data or {}
        
        # Дополняем данными из отчетов если есть
        self._enrich_with_reports_data()
    
    def _enrich_with_reports_data(self):
        """Дополняет данные магазина информацией из отчетов"""
        try:
            import json
            if not config.PROCESSED_DATA_FILE.exists():
                return
            with open(config.PROCESSED_DATA_FILE, 'r', encoding='utf-8') as f:
                reports_data = json.load(f)
            parsed_data = reports_data.get('parsed_data', {})
            orders = parsed_data.get('orders', [])
            if not orders or not self.store_data:
                return
            if 'products_info' not in self.store_data or not self.store_data['products_info'].get('total_products'):
                unique_products = len(set(o.get('article') for o in orders if o.get('article')))
                if 'products_info' not in self.store_data:
                    self.store_data['products_info'] = {}
                self.store_data['products_info']['total_products'] = unique_products
                self.store_data['products_info']['from_reports'] = True
        except (OSError, json.JSONDecodeError) as e:
            print(f"Ошибка дополнения данных из отчетов: {e}")
    
    def get_store_metrics(self):
        """Возвращает метрики магазина"""
        if not self.store_data:
            # Возвращаем данные из документации бренда
            return self._get_metrics_from_brand_docs()
        
        seller_info = self.store_data.get('seller_info', {})
        rating_info = self.store_data.get('rating_info', {})
        reviews_info = self.store_data.get('reviews_info', {})
        products_info = self.store_data.get('products_info', {})
        
        # Если данные не получены, используем fallback
        if seller_info.get('error') or not seller_info.get('name'):
            return self._get_metrics_from_brand_docs()
        
        brand = config.get_brand_defaults()
        def _name():
            return seller_info.get('name') or brand.get('seller_name') or '—'
        def _n():
            return products_info.get('total_products') or seller_info.get('products_count') or brand.get('products_count') or 0
        return {
            'seller_name': _name(),
            'seller_id': self.store_data.get('seller_id') or brand.get('seller_id') or '—',
            'rating': {
                'overall': rating_info.get('overall_rating') or seller_info.get('rating'),
                'target': 4.7,
                'status': self._get_rating_status(rating_info.get('overall_rating') or seller_info.get('rating'))
            },
            'reviews': {
                'total': reviews_info.get('total_reviews') or seller_info.get('reviews_count'),
                'target_ratio': 0.3,
                'status': self._get_reviews_status(reviews_info.get('total_reviews') or seller_info.get('reviews_count'))
            },
            'products': {
                'total': _n(),
                'status': self._get_products_status(_n())
            },
            'trust_indicators': {
                'has_description': bool(seller_info.get('description')),
                'since_date': seller_info.get('since_date'),
                'years_on_ozon': self._calculate_years_on_ozon(seller_info.get('since_date'))
            },
            'data_source': self.store_data.get('collection_method', 'unknown'),
            'note': self.store_data.get('note', '')
        }
    
    def _get_metrics_from_brand_docs(self):
        """Получает метрики из документации бренда"""
        try:
            import json
            if not config.BRAND_DOCUMENTATION_PATH.exists():
                return self._fallback_metrics()
            with open(config.BRAND_DOCUMENTATION_PATH, 'r', encoding='utf-8') as f:
                brand_data = json.load(f)
            products = brand_data.get('products') or {}
            return {
                'seller_name': brand_data.get('seller_name') or '—',
                'seller_id': brand_data.get('seller_id') or '—',
                'rating': {
                    'overall': None,
                    'target': 4.7,
                    'status': 'unknown',
                    'note': 'Используйте кабинет продавца Ozon для получения рейтинга'
                },
                'reviews': {
                    'total': None,
                    'target_ratio': 0.3,
                    'status': 'unknown',
                    'note': 'Используйте отчеты Ozon для получения данных об отзывах'
                },
                'products': {
                    'total': len(products),
                    'status': self._get_products_status(len(products)),
                    'products_list': list(products.keys())
                },
                'trust_indicators': {
                    'has_description': bool(brand_data.get('description')),
                    'since_date': None,
                    'years_on_ozon': None
                },
                'data_source': 'brand_documentation',
                'note': 'Данные из документации бренда. Для актуальных данных используйте отчеты Ozon или кабинет продавца.'
            }
        except (OSError, json.JSONDecodeError):
            return self._fallback_metrics()

    def _fallback_metrics(self):
        """Метрики при отсутствии бренд-документации"""
        brand = config.get_brand_defaults()
        n = brand.get('products_count') or 0
        return {
            'seller_name': brand.get('seller_name') or '—',
            'seller_id': brand.get('seller_id') or '—',
            'rating': {'overall': None, 'target': 4.7, 'status': 'unknown'},
            'reviews': {'total': None, 'target_ratio': 0.3, 'status': 'unknown'},
            'products': {'total': n, 'status': self._get_products_status(n)},
            'trust_indicators': {'has_description': False},
            'data_source': 'fallback',
            'note': 'Используйте отчеты Ozon для получения актуальных данных'
        }

    def get_store_recommendations(self):
        """Генерирует рекомендации на основе данных магазина"""
        recommendations = []
        metrics = self.get_store_metrics()
        
        # Рекомендации по рейтингу
        rating = metrics['rating']['overall']
        if rating is not None and rating < 4.5:
            recommendations.append({
                'category': 'Рейтинг магазина',
                'priority': 'critical',
                'title': 'Критично низкий рейтинг',
                'description': f'Текущий рейтинг: {rating:.2f if rating else "неизвестен"}. Для медицинских товаров критически важен высокий рейтинг (целевой 4.7+).',
                'action': 'Срочно улучшите качество товаров и сервиса',
                'action_plan': {
                    'immediate': [
                        'Проанализируйте все негативные отзывы за последний месяц',
                        'Свяжитесь с покупателями, оставившими низкие оценки',
                        'Исправьте все выявленные проблемы'
                    ],
                    'short_term': [
                        'Настройте автоматические напоминания оставить отзыв',
                        'Отвечайте на все отзывы в течение 24 часов',
                        'Создайте программу поощрения за отзывы с фотографиями'
                    ],
                    'long_term': [
                        'Разработайте стратегию работы с отзывами',
                        'Создайте программу улучшения качества на основе отзывов',
                        'Постройте систему обратной связи с клиентами'
                    ],
                    'expected_result': 'Увеличение рейтинга до 4.6-4.7 в течение 2-3 месяцев'
                }
            })
        elif rating is not None and rating < 4.7:
            recommendations.append({
                'category': 'Рейтинг магазина',
                'priority': 'medium',
                'title': 'Рейтинг ниже целевого',
                'description': f'Текущий рейтинг: {rating:.2f if rating else "неизвестен"}. Целевой для медицинских товаров: 4.7+.',
                'action': 'Продолжайте улучшать качество и работу с отзывами',
                'action_plan': {
                    'immediate': [
                        'Проанализируйте отзывы с оценкой 3-4 звезды',
                        'Улучшите товары и сервис на основе замечаний',
                        'Активно просите довольных покупателей оставлять отзывы'
                    ],
                    'short_term': [
                        'Создайте программу улучшения качества',
                        'Улучшите упаковку и инструкции',
                        'Добавьте гарантии и сервисное обслуживание'
                    ],
                    'long_term': [
                        'Постройте репутацию эксперта в нише',
                        'Создайте программу лояльности',
                        'Разработайте стандарты качества'
                    ],
                    'expected_result': 'Достижение рейтинга 4.7-4.8'
                }
            })
        
        # Рекомендации по отзывам
        reviews_count = metrics['reviews']['total']
        if reviews_count is not None and reviews_count < 100:
            recommendations.append({
                'category': 'Отзывы',
                'priority': 'high',
                'title': 'Недостаточно отзывов',
                'description': f'Всего отзывов: {reviews_count or 0}. Для медицинских товаров важно иметь много отзывов для доверия.',
                'action': 'Активно собирайте отзывы от покупателей',
                'action_plan': {
                    'immediate': [
                        'Настройте автоматические напоминания оставить отзыв',
                        'Создайте программу поощрения за отзывы',
                        'Добавьте просьбу об отзыве в упаковку'
                    ],
                    'short_term': [
                        'Свяжитесь с покупателями, которые еще не оставили отзыв',
                        'Предложите скидку на следующий заказ за отзыв с фото',
                        'Создайте шаблоны для просьбы об отзыве'
                    ],
                    'long_term': [
                        'Разработайте стратегию сбора отзывов',
                        'Создайте программу лояльности для активных рецензентов',
                        'Используйте отзывы в маркетинге'
                    ],
                    'expected_result': 'Увеличение количества отзывов в 2-3 раза за квартал'
                }
            })
        
        # Рекомендации по описанию магазина
        if not metrics['trust_indicators']['has_description']:
            recommendations.append({
                'category': 'Контент магазина',
                'priority': 'medium',
                'title': 'Отсутствует описание магазина',
                'description': 'Описание магазина повышает доверие покупателей, особенно для медицинских товаров.',
                'action': 'Добавьте детальное описание магазина',
                'action_plan': {
                    'immediate': [
                        'Создайте описание магазина с историей бренда',
                        'Добавьте информацию о сертификатах и качестве',
                        'Укажите гарантии и сервисное обслуживание'
                    ],
                    'short_term': [
                        'Добавьте информацию о производителе',
                        'Создайте раздел "О нас"',
                        'Добавьте контактную информацию'
                    ],
                    'long_term': [
                        'Создайте брендированную страницу магазина',
                        'Добавьте образовательный контент',
                        'Разработайте корпоративный стиль'
                    ],
                    'expected_result': 'Увеличение доверия покупателей, рост конверсии на 5-10%'
                }
            })
        
        return recommendations
    
    def _get_rating_status(self, rating):
        """Определяет статус рейтинга"""
        if rating is None:
            return 'unknown'
        try:
            rating = float(rating)
            if rating >= 4.7:
                return 'excellent'
            elif rating >= 4.5:
                return 'good'
            elif rating >= 4.0:
                return 'needs_improvement'
            else:
                return 'critical'
        except (TypeError, ValueError):
            return 'unknown'
    
    def _get_reviews_status(self, count):
        """Определяет статус количества отзывов"""
        if count is None:
            return 'unknown'
        try:
            count = int(count)
            if count >= 500:
                return 'excellent'
            elif count >= 100:
                return 'good'
            elif count >= 50:
                return 'needs_improvement'
            else:
                return 'critical'
        except (TypeError, ValueError):
            return 'unknown'
    
    def _get_products_status(self, count):
        """Определяет статус количества товаров"""
        if count is None:
            return 'unknown'
        try:
            count = int(count)
            if count >= 50:
                return 'good'
            elif count >= 20:
                return 'needs_improvement'
            else:
                return 'low'
        except (TypeError, ValueError):
            return 'unknown'
    
    def _calculate_years_on_ozon(self, since_date):
        """Вычисляет количество лет на Ozon"""
        if not since_date:
            return None
        try:
            year = int(since_date)
            current_year = datetime.now().year
            return current_year - year
        except:
            return None
