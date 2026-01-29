"""
Анализатор настроек кабинета Ozon Seller
Проверяет соответствие настроек рекомендациям и возможностям кабинета
"""
import json

import config
from .seo_analyzer import SEOAnalyzer
from .review_analyzer import ReviewAnalyzer


class CabinetAnalyzer:
    """Анализатор настроек кабинета продавца"""

    def __init__(self):
        self.brand_info = None
        self.seller_tools = None
        self.current_settings = {}
        self.seo_analyzer = SEOAnalyzer()
        self.review_analyzer = ReviewAnalyzer()
        self.load_brand_info()
        self.load_seller_tools()

    def load_brand_info(self):
        """Загружает информацию о бренде"""
        try:
            if config.BRAND_DOCUMENTATION_PATH.exists():
                with open(config.BRAND_DOCUMENTATION_PATH, 'r', encoding='utf-8') as f:
                    self.brand_info = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Ошибка загрузки информации о бренде: {e}")

    def load_seller_tools(self):
        """Загружает информацию об инструментах Ozon"""
        try:
            if config.OZON_SELLER_TOOLS_PATH.exists():
                with open(config.OZON_SELLER_TOOLS_PATH, 'r', encoding='utf-8') as f:
                    self.seller_tools = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Ошибка загрузки инструментов Ozon: {e}")
    
    def analyze_cabinet_settings(self, analytics_data=None, store_data=None):
        """Анализирует настройки кабинета на основе данных"""
        if not self.brand_info:
            self.load_brand_info()
        if not self.seller_tools:
            self.load_seller_tools()
        
        recommendations = []
        
        # Анализ настроек товаров
        recommendations.extend(self._analyze_product_settings(analytics_data))
        
        # Анализ настроек ценообразования
        recommendations.extend(self._analyze_pricing_settings(analytics_data))
        
        # Анализ настроек продвижения
        recommendations.extend(self._analyze_promotion_settings(analytics_data))
        
        # Анализ настроек логистики
        recommendations.extend(self._analyze_logistics_settings(analytics_data))
        
        # Анализ настроек отзывов
        recommendations.extend(self._analyze_reviews_settings(store_data))
        
        # Анализ настроек профиля
        recommendations.extend(self._analyze_profile_settings(store_data))
        
        # Анализ комплектов товаров
        recommendations.extend(self._analyze_product_sets(analytics_data))
        
        # Анализ SEO-оптимизации карточек
        recommendations.extend(self._analyze_seo_optimization(analytics_data))
        
        # Анализ работы с отзывами
        recommendations.extend(self._analyze_reviews_management(store_data))
        
        # Анализ рекламных кампаний
        recommendations.extend(self._analyze_advertising_campaigns(analytics_data))
        
        # Анализ Rich-контента
        recommendations.extend(self._analyze_rich_content(analytics_data))
        
        return recommendations
    
    def _analyze_product_settings(self, analytics_data):
        """Анализирует настройки товаров"""
        recs = []
        
        if not analytics_data or not self.brand_info:
            return recs
        
        product_metrics = analytics_data.get('product_metrics', {})
        total_products = product_metrics.get('total_products', 0) or 0
        
        # Проверка количества товаров
        if total_products is not None and total_products < 10:
            recs.append({
                'category': 'Настройки кабинета',
                'priority': 'medium',
                'title': 'Расширение ассортимента',
                'description': f'В продаже {total_products} товаров. Рекомендуется расширить ассортимент для увеличения продаж.',
                'action': 'Добавьте больше товаров в кабинет',
                'action_plan': {
                    'immediate': [
                        'Проверьте, все ли товары из бренда добавлены в кабинет',
                        'Используйте шаблоны товаров для быстрого добавления',
                        'Добавьте недостающие товары из линейки'
                    ],
                    'short_term': [
                        'Создайте варианты товаров (разные размеры, цвета)',
                        'Добавьте сопутствующие товары',
                        'Используйте массовое редактирование для обновления'
                    ],
                    'long_term': [
                        'Разработайте стратегию расширения ассортимента',
                        'Добавьте новые товары на основе спроса',
                        'Создайте линейку товаров разной ценовой категории'
                    ],
                    'expected_result': 'Увеличение ассортимента до 15-20 товаров, рост продаж на 20-30%'
                }
            })
        
        # Проверка комплектов
        existing_sets = self.brand_info.get('current_implementations', {}).get('product_sets', {}).get('existing_sets', [])
        potential_sets = self.brand_info.get('current_implementations', {}).get('product_sets', {}).get('potential_sets', [])
        
        if len(potential_sets) > len(existing_sets):
            recs.append({
                'category': 'Настройки кабинета',
                'priority': 'high',
                'title': 'Создание дополнительных комплектов',
                'description': f'Создано {len(existing_sets)} комплектов, можно создать еще {len(potential_sets) - len(existing_sets)}.',
                'action': 'Создайте дополнительные комплекты товаров',
                'action_plan': {
                    'immediate': [
                        'Создайте комплект "Cordus Easy + Sacrus Easy" (базовый)',
                        'Создайте комплект "Cordus Plus + Sacrus Easy + Кейс" (полный)',
                        'Используйте инструмент "Создание товара" → "Комплект"'
                    ],
                    'short_term': [
                        'Создайте комплект "Cordus Vibro + Sacrus Vibro" (премиум)',
                        'Создайте комплект "Массажер + Хондропротектор"',
                        'Настройте цены комплектов с выгодой 15-20%'
                    ],
                    'long_term': [
                        'Разработайте стратегию комплектов',
                        'Создайте сезонные комплекты',
                        'Используйте комплекты для увеличения среднего чека'
                    ],
                    'expected_result': 'Увеличение среднего чека на 30-40%, рост продаж комплектов'
                }
            })
        
        return recs
    
    def _analyze_pricing_settings(self, analytics_data):
        """Анализирует настройки ценообразования"""
        recs = []
        
        if not analytics_data:
            return recs
        
        financial_metrics = analytics_data.get('financial_metrics', {})
        product_metrics = analytics_data.get('product_metrics', {})
        
        avg_discount = product_metrics.get('avg_discount', 0)
        
        # Проверка автоматического ценообразования
        if avg_discount > 50:
            recs.append({
                'category': 'Настройки кабинета',
                'priority': 'high',
                'title': 'Настройка автоматического ценообразования',
                'description': f'Средняя скидка {avg_discount:.0f}% слишком высока. Используйте автоматическое ценообразование для контроля.',
                'action': 'Настройте автоматическое ценообразование в кабинете',
                'action_plan': {
                    'immediate': [
                        'Перейдите в "Цены" → "Автоматическое ценообразование"',
                        'Установите минимальные цены для защиты маржи',
                        'Настройте правила отслеживания конкурентов'
                    ],
                    'short_term': [
                        'Настройте автоматическую корректировку цен',
                        'Установите максимальные скидки (не более 30%)',
                        'Мониторьте изменения цен конкурентов'
                    ],
                    'long_term': [
                        'Оптимизируйте правила ценообразования',
                        'Используйте динамическое ценообразование',
                        'Анализируйте эффективность автоматического ценообразования'
                    ],
                    'expected_result': 'Контроль цен, защита маржи, поддержание конкурентоспособности'
                }
            })
        
        # Проверка рассрочки
        sales_metrics = analytics_data.get('sales_metrics', {})
        avg_order = sales_metrics.get('avg_order_value', 0)
        
        if avg_order > 5000:
            recs.append({
                'category': 'Настройки кабинета',
                'priority': 'medium',
                'title': 'Подключение рассрочки',
                'description': f'Средний чек {avg_order:.0f} руб. Рассрочка может увеличить конверсию.',
                'action': 'Подключите рассрочку для товаров от 5000 руб',
                'action_plan': {
                    'immediate': [
                        'Перейдите в "Рассрочка" → "Подключить"',
                        'Настройте условия рассрочки (0-0-6, 0-0-12)',
                        'Подключите товары от 5000 руб'
                    ],
                    'short_term': [
                        'Мониторьте конверсию товаров с рассрочкой',
                        'Оптимизируйте условия рассрочки',
                        'Используйте рассрочку в описаниях товаров'
                    ],
                    'long_term': [
                        'Анализируйте эффективность рассрочки',
                        'Расширяйте условия рассрочки',
                        'Используйте рассрочку для увеличения среднего чека'
                    ],
                    'expected_result': 'Увеличение конверсии на 10-15% для товаров с рассрочкой'
                }
            })
        
        return recs
    
    def _analyze_promotion_settings(self, analytics_data):
        """Анализирует настройки продвижения"""
        recs = []
        
        if not analytics_data:
            return recs
        
        sales_metrics = analytics_data.get('sales_metrics', {})
        conversion = sales_metrics.get('conversion_rate', 0) or 0
        
        # Проверка рекламы
        if conversion is not None and conversion < 75:
            recs.append({
                'category': 'Настройки кабинета',
                'priority': 'high',
                'title': 'Настройка Ozon Advertising',
                'description': f'Конверсия {conversion:.1f}% ниже целевой. Реклама может увеличить видимость и конверсию.',
                'action': 'Настройте рекламу в кабинете продавца',
                'action_plan': {
                    'immediate': [
                        'Перейдите в "Реклама" → "Создать кампанию"',
                        'Настройте рекламу для топ-3 товаров',
                        'Установите начальный бюджет 5000-10000 руб/месяц'
                    ],
                    'short_term': [
                        'Настройте ретаргетинг для увеличения конверсии',
                        'Оптимизируйте ставки на основе данных',
                        'Расширьте рекламу на другие товары'
                    ],
                    'long_term': [
                        'Разработайте стратегию рекламы',
                        'Используйте разные типы рекламы',
                        'Анализируйте ROI рекламы'
                    ],
                    'expected_result': 'Увеличение конверсии до 75-80%, рост продаж на 20-30%'
                }
            })
        
        return recs
    
    def _analyze_logistics_settings(self, analytics_data):
        """Анализирует настройки логистики"""
        recs = []
        
        if not analytics_data:
            return recs
        
        logistics_metrics = analytics_data.get('logistics_metrics', {})
        warehouses = logistics_metrics.get('warehouses', {})
        
        # Проверка FBO
        if warehouses:
            total_orders = sum(warehouses.values())
            fbo_warehouses = [w for w in warehouses.keys() if 'РФЦ' in w]
            fbo_ratio = len(fbo_warehouses) / len(warehouses) * 100 if warehouses else 0
            
            if fbo_ratio is not None and fbo_ratio < 50:
                recs.append({
                    'category': 'Настройки кабинета',
                    'priority': 'medium',
                    'title': 'Использование FBO для топ-товаров',
                    'description': f'Только {fbo_ratio:.0f}% заказов через FBO. FBO ускоряет доставку и увеличивает конверсию.',
                    'action': 'Передайте топ-товары на склады Ozon (FBO)',
                    'action_plan': {
                        'immediate': [
                            'Перейдите в "Логистика" → "FBO"',
                            'Выберите топ-3 товара',
                            'Создайте заявку на передачу товаров на склады Ozon'
                        ],
                        'short_term': [
                            'Разместите товары на складах в топ-5 регионов',
                            'Поддерживайте остатки на складах Ozon',
                            'Мониторьте скорость доставки'
                        ],
                        'long_term': [
                            'Расширьте использование FBO',
                            'Оптимизируйте распределение по складам',
                            'Используйте прогнозирование для планирования остатков'
                        ],
                        'expected_result': 'Снижение времени доставки до 2-3 дней, увеличение конверсии на 10-15%'
                    }
                })
        
        return recs
    
    def _analyze_reviews_settings(self, store_data):
        """Анализирует настройки работы с отзывами"""
        recs = []
        
        if not store_data:
            return recs
        
        reviews_info = store_data.get('reviews_info', {})
        total_reviews = reviews_info.get('total_reviews', 0) or 0
        
        if total_reviews is not None and total_reviews < 100:
            recs.append({
                'category': 'Настройки кабинета',
                'priority': 'high',
                'title': 'Настройка автоматических напоминаний об отзывах',
                'description': f'Всего {total_reviews} отзывов. Автоматические напоминания могут увеличить количество отзывов.',
                'action': 'Настройте автоматические напоминания в кабинете',
                'action_plan': {
                    'immediate': [
                        'Перейдите в "Настройки" → "Уведомления"',
                        'Включите уведомления об отзывах',
                        'Настройте автоматические напоминания покупателям'
                    ],
                    'short_term': [
                        'Создайте программу поощрения за отзывы',
                        'Используйте шаблоны для просьбы об отзыве',
                        'Добавьте просьбу об отзыве в упаковку'
                    ],
                    'long_term': [
                        'Разработайте стратегию сбора отзывов',
                        'Создайте программу лояльности для рецензентов',
                        'Используйте отзывы в маркетинге'
                    ],
                    'expected_result': 'Увеличение количества отзывов в 2-3 раза за квартал'
                }
            })
        
        return recs
    
    def _analyze_profile_settings(self, store_data):
        """Анализирует настройки профиля"""
        recs = []
        
        if not store_data:
            return recs
        
        seller_info = store_data.get('seller_info', {})
        description = seller_info.get('description')
        
        if not description:
            recs.append({
                'category': 'Настройки кабинета',
                'priority': 'high',
                'title': 'Заполнение описания магазина',
                'description': 'Описание магазина не заполнено. Это снижает доверие покупателей.',
                'action': 'Заполните описание магазина в настройках',
                'action_plan': {
                    'immediate': [
                        'Перейдите в "Настройки" → "Магазин"',
                        'Добавьте название магазина',
                        'Создайте детальное описание магазина'
                    ],
                    'short_term': [
                        'Добавьте информацию о бренде',
                        'Укажите историю компании',
                        'Добавьте контактную информацию'
                    ],
                    'long_term': [
                        'Создайте брендированную страницу магазина',
                        'Добавьте логотип и изображения',
                        'Разработайте корпоративный стиль'
                    ],
                    'expected_result': 'Увеличение доверия покупателей, рост конверсии на 5-10%'
                }
            })
        
        return recs
    
    def _analyze_product_sets(self, analytics_data):
        """Анализирует комплекты товаров"""
        recs = []
        
        if not self.brand_info or not analytics_data:
            return recs
        
        product_sets = self.brand_info.get('product_sets', {})
        current_sets = self.brand_info.get('current_implementations', {}).get('product_sets', {}).get('existing_sets', [])
        
        # Анализ потенциальных комплектов
        potential_sets = [
            {
                'name': 'Cordus Easy + Sacrus Easy',
                'products': ['cordus_easy', 'sacrus_easy'],
                'description': 'Базовый комплект для лечения спины, шеи и поясницы'
            },
            {
                'name': 'Cordus Plus + Sacrus Easy + Кейс',
                'products': ['cordus_plus', 'sacrus_easy', 'case'],
                'description': 'Полный комплект с кейсом'
            },
            {
                'name': 'Массажер + Хондропротектор',
                'products': ['cordus_plus', 'chondroprotector'],
                'description': 'Комплект для комплексного лечения'
            }
        ]
        
        if len(potential_sets) > len(current_sets):
            recs.append({
                'category': 'Настройки кабинета',
                'priority': 'high',
                'title': 'Создание новых комплектов товаров',
                'description': f'Можно создать {len(potential_sets) - len(current_sets)} дополнительных комплектов для увеличения среднего чека.',
                'action': 'Создайте новые комплекты в кабинете',
                'action_plan': {
                    'immediate': [
                        'Перейдите в "Товары" → "Создать товар" → "Комплект"',
                        'Создайте комплект "Cordus Easy + Sacrus Easy"',
                        'Настройте цену с выгодой 15-20% от суммы отдельных товаров'
                    ],
                    'short_term': [
                        'Создайте комплект "Cordus Plus + Sacrus Easy + Кейс"',
                        'Создайте комплект "Массажер + Хондропротектор"',
                        'Добавьте описания комплектов с преимуществами'
                    ],
                    'long_term': [
                        'Разработайте стратегию комплектов',
                        'Создайте сезонные комплекты',
                        'Используйте комплекты для увеличения среднего чека'
                    ],
                    'expected_result': 'Увеличение среднего чека на 30-40%, рост продаж комплектов'
                }
            })
        
        return recs
    
    def _analyze_seo_optimization(self, analytics_data):
        """Анализирует SEO-оптимизацию карточек товаров"""
        recs = []
        
        if not analytics_data:
            return recs
        
        # Получаем данные о товарах из заказов
        orders = []
        if hasattr(self, 'analytics') and self.analytics:
            orders = self.analytics.orders if hasattr(self.analytics, 'orders') else []
        elif 'orders' in analytics_data:
            orders = analytics_data['orders']
        
        if orders:
            # Анализируем SEO
            seo_result = self.seo_analyzer.get_seo_score_for_orders(orders)
            seo_score = seo_result.get('seo_score', 0)
            seo_level = seo_result.get('seo_level', 'unknown')
            
            if seo_score < 60:
                recs.append({
                    'category': 'Настройки кабинета',
                    'priority': 'critical',
                    'title': 'КРИТИЧНО: Низкая SEO-оптимизация карточек',
                    'description': f'SEO Score: {seo_score}/100 ({seo_level}). Карточки не оптимизированы для нового алгоритма Ozon 2025.',
                    'action': 'Срочно оптимизируйте карточки товаров в кабинете',
                    'action_plan': {
                        'immediate': [
                            'Проверьте заголовки всех товаров - должны быть 30-100 символов с ключевыми словами',
                            'Увеличьте описания до 500+ символов',
                            'Добавьте минимум 5 фотографий для каждого товара',
                            'Заполните все характеристики товаров'
                        ],
                        'short_term': [
                            'Добавьте ключевые слова в заголовки и описания',
                            'Структурируйте описания (списки, абзацы)',
                            'Добавьте видео в карточки товаров',
                            'Используйте инструменты SEO в кабинете Ozon'
                        ],
                        'long_term': [
                            'Создайте контент-стратегию для каждого товара',
                            'Регулярно обновляйте контент карточек',
                            'Мониторьте позиции в поиске',
                            'Адаптируйте контент под изменения алгоритма'
                        ],
                        'expected_result': 'Увеличение SEO Score до 70-80+, улучшение позиций в поиске'
                    }
                })
        
        return recs
    
    def _analyze_reviews_management(self, store_data):
        """Анализирует работу с отзывами"""
        recs = []
        
        if not store_data:
            return recs
        
        # Анализируем отзывы
        review_metrics = self.review_analyzer.get_review_metrics_for_store(store_data)
        avg_rating = review_metrics.get('average_rating', 0) or 0
        response_rate = review_metrics.get('response_rate', 0) or 0
        
        if avg_rating > 0 and avg_rating < 4.7:
            recs.append({
                'category': 'Настройки кабинета',
                'priority': 'high',
                'title': 'Низкий рейтинг - требуется улучшение',
                'description': f'Рейтинг: {avg_rating:.2f}/5.0. Для попадания в топ нужен рейтинг 4.7+.',
                'action': 'Улучшите качество товаров и работу с отзывами в кабинете',
                'action_plan': {
                    'immediate': [
                        'Проверьте раздел "Отзывы" в кабинете Ozon',
                        'Ответьте на все неотвеченные отзывы',
                        'Проанализируйте негативные отзывы и устраните проблемы'
                    ],
                    'short_term': [
                        'Настройте уведомления о новых отзывах',
                        'Создайте шаблоны ответов на частые вопросы',
                        'Просите довольных покупателей оставлять отзывы'
                    ],
                    'expected_result': 'Увеличение рейтинга до 4.7+, улучшение репутации'
                }
            })
        
        if response_rate < 80:
            recs.append({
                'category': 'Настройки кабинета',
                'priority': 'high',
                'title': 'Низкий процент ответов на отзывы',
                'description': f'Отвечаете на {response_rate:.1f}% отзывов. Рекомендуется отвечать на все отзывы.',
                'action': 'Используйте раздел "Отзывы" в кабинете для ответов',
                'action_plan': {
                    'immediate': [
                        'Откройте раздел "Отзывы" в кабинете Ozon',
                        'Ответьте на все неотвеченные отзывы',
                        'Настройте ежедневную проверку новых отзывов'
                    ],
                    'short_term': [
                        'Используйте мобильное приложение для быстрых ответов',
                        'Создайте процесс работы с отзывами',
                        'Мониторьте время ответа (целевое: 24 часа)'
                    ],
                    'expected_result': 'Увеличение процента ответов до 90%+, улучшение репутации'
                }
            })
        
        return recs
    
    def _analyze_advertising_campaigns(self, analytics_data):
        """Анализирует настройки рекламных кампаний"""
        recs = []
        
        # Рекомендации по использованию новых инструментов рекламы
        recs.append({
            'category': 'Настройки кабинета',
            'priority': 'medium',
            'title': 'Использование новых рекламных инструментов Ozon 2025',
            'description': 'Ozon обновил рекламные инструменты: "Трафареты" (минимум 7 руб), объединенные CPC/CPO ставки.',
            'action': 'Изучите новые возможности рекламы в кабинете',
            'action_plan': {
                'immediate': [
                    'Откройте раздел "Реклама" в кабинете Ozon',
                    'Изучите новые инструменты: "Трафареты", "Вывод в топ"',
                    'Проверьте возможность использования объединенных CPC/CPO ставок'
                ],
                'short_term': [
                    'Создайте тестовую кампанию "Трафареты" с минимальной ставкой',
                    'Протестируйте "Вывод в топ" для топ-товара',
                    'Анализируйте эффективность новых инструментов'
                ],
                'expected_result': 'Оптимизация рекламных расходов, увеличение продаж'
            }
        })
        
        return recs
    
    def _analyze_rich_content(self, analytics_data):
        """Анализирует использование Rich-контента"""
        recs = []
        
        product_metrics = analytics_data.get('product_metrics', {}) if analytics_data else {}
        total_products = product_metrics.get('total_products', 0) or 0
        
        if total_products > 0:
            recs.append({
                'category': 'Настройки кабинета',
                'priority': 'high',
                'title': 'Добавление Rich-контента в карточки товаров',
                'description': f'У вас {total_products} товаров. Rich-контент увеличивает конверсию на 15-25% и улучшает позиции в поиске.',
                'action': 'Используйте инструмент "Rich-контент" в кабинете Ozon',
                'action_plan': {
                    'immediate': [
                        'Откройте раздел "Товары" → выберите товар → "Rich-контент"',
                        'Создайте мини-лендинг для топ-3 товаров',
                        'Добавьте блоки: преимущества, применение, отзывы, сравнение'
                    ],
                    'short_term': [
                        'Создайте Rich-контент для всех товаров',
                        'Используйте визуальные элементы: иконки, схемы, таблицы',
                        'Добавьте интерактивные элементы',
                        'Тестируйте разные варианты контента'
                    ],
                    'long_term': [
                        'Разработайте единый стиль Rich-контента',
                        'Обновляйте контент регулярно',
                        'Анализируйте влияние на конверсию',
                        'Оптимизируйте на основе данных'
                    ],
                    'expected_result': 'Увеличение конверсии на 15-25%, улучшение позиций в поиске'
                }
            })
        
        return recs


def get_brand_info():
    """Загружает информацию о бренде"""
    try:
        if config.BRAND_DOCUMENTATION_PATH.exists():
            with open(config.BRAND_DOCUMENTATION_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (OSError, json.JSONDecodeError):
        pass
    return None


def get_seller_tools():
    """Загружает информацию об инструментах Ozon"""
    try:
        if config.OZON_SELLER_TOOLS_PATH.exists():
            with open(config.OZON_SELLER_TOOLS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (OSError, json.JSONDecodeError):
        pass
    return None
