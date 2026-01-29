"""
Расширенная система рекомендаций для улучшения показателей на Ozon
Основана на анализе реальных данных и лучших практиках для медицинских товаров
"""
from datetime import datetime, timedelta
import pandas as pd
from .niche_analysis import NicheAnalysis, SUCCESS_CASES
from analytics.seo_analyzer import SEOAnalyzer
from analytics.review_analyzer import ReviewAnalyzer
from analytics.advertising_analyzer import AdvertisingAnalyzer


class OzonRecommendations:
    """Генератор рекомендаций с конкретными планами действий"""
    
    def __init__(self):
        self.analytics = None
        self.store_analytics = None
        self.niche_analysis = NicheAnalysis()
        self.seo_analyzer = SEOAnalyzer()
        self.review_analyzer = ReviewAnalyzer()
        self.advertising_analyzer = AdvertisingAnalyzer()
    
    def set_store_analytics(self, store_analytics):
        """Устанавливает объект аналитики магазина"""
        self.store_analytics = store_analytics
    
    def set_analytics(self, analytics):
        """Устанавливает объект аналитики"""
        self.analytics = analytics
    
    def generate_recommendations(self):
        """Генерирует список рекомендаций с планами действий"""
        if not self.analytics:
            return []
        
        recommendations = []
        
        # Загружаем метрики
        sales_metrics = self.analytics.get_sales_metrics()
        financial_metrics = self.analytics.get_financial_metrics()
        logistics_metrics = self.analytics.get_logistics_metrics()
        inventory_metrics = self.analytics.get_inventory_metrics()
        returns_metrics = self.analytics.get_returns_metrics()
        customer_metrics = self.analytics.get_customer_metrics()
        product_metrics = self.analytics.get_product_metrics() or {}
        
        # Рекомендации по продажам
        recommendations.extend(self._sales_recommendations(sales_metrics, product_metrics))
        
        # Рекомендации по финансам
        recommendations.extend(self._financial_recommendations(financial_metrics, sales_metrics, product_metrics))
        
        # Рекомендации по логистике
        recommendations.extend(self._logistics_recommendations(logistics_metrics))
        
        # Рекомендации по остаткам
        recommendations.extend(self._inventory_recommendations(inventory_metrics, sales_metrics))
        
        # Рекомендации по возвратам
        recommendations.extend(self._returns_recommendations(returns_metrics))
        
        # Рекомендации по клиентам
        recommendations.extend(self._customer_recommendations(customer_metrics))
        
        # Рекомендации по товарам (медицинские товары)
        recommendations.extend(self._medical_products_recommendations(product_metrics, sales_metrics))
        
        # Рекомендации по контенту карточек
        recommendations.extend(self._content_recommendations(product_metrics))
        
        # Рекомендации по ценообразованию
        recommendations.extend(self._pricing_recommendations(financial_metrics, product_metrics))
        
        # Рекомендации на основе успешных кейсов
        recommendations.extend(self._success_cases_recommendations(sales_metrics, financial_metrics))
        
        # Новые рекомендации на основе алгоритма Ozon 2025
        recommendations.extend(self._seo_recommendations(sales_metrics, product_metrics))
        recommendations.extend(self._review_management_recommendations())
        recommendations.extend(self._advertising_recommendations(sales_metrics, financial_metrics))
        recommendations.extend(self._ranking_factors_recommendations(sales_metrics, financial_metrics))
        
        # Рекомендации на основе данных магазина
        if self.store_analytics:
            store_recommendations = self.store_analytics.get_store_recommendations()
            recommendations.extend(store_recommendations)
        
        # Приоритизация и расчет ROI
        recommendations = self._prioritize_recommendations(recommendations, sales_metrics, financial_metrics)
        
        return recommendations
    
    def _prioritize_recommendations(self, recommendations, sales_metrics, financial_metrics):
        """Приоритизирует рекомендации на основе ROI и потенциального эффекта"""
        if not recommendations:
            return []
        
        # Рассчитываем ROI для каждой рекомендации
        for rec in recommendations:
            roi_score = self._calculate_roi_score(rec, sales_metrics, financial_metrics)
            rec['roi_score'] = roi_score
            rec['priority_score'] = self._calculate_priority_score(rec, roi_score)
        
        # Сортируем по priority_score (высший приоритет = выше)
        recommendations.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
        
        # Добавляем ранги
        for i, rec in enumerate(recommendations, 1):
            rec['rank'] = i
        
        return recommendations
    
    def _calculate_roi_score(self, recommendation, sales_metrics, financial_metrics):
        """Рассчитывает ROI score для рекомендации"""
        priority = recommendation.get('priority', 'medium')
        category = recommendation.get('category', '')
        
        # Базовый ROI на основе приоритета
        priority_scores = {
            'critical': 100,
            'high': 75,
            'medium': 50,
            'low': 25
        }
        base_roi = priority_scores.get(priority, 50)
        
        # Множители на основе категории и потенциального эффекта
        category_multipliers = {
            'Финансы': 1.5,  # Финансовые рекомендации имеют высокий ROI
            'Продажи': 1.3,
            'Возвраты': 1.2,
            'Остатки': 1.1,
            'Логистика': 1.0,
            'Клиенты': 0.9,
            'Контент': 0.8
        }
        multiplier = category_multipliers.get(category, 1.0)
        
        # Оценка потенциального эффекта на основе текущих метрик
        potential_impact = self._estimate_potential_impact(recommendation, sales_metrics, financial_metrics)
        
        # Оценка сложности реализации
        complexity = self._estimate_complexity(recommendation)
        complexity_factor = 1.0 / complexity if complexity > 0 else 1.0
        
        # Итоговый ROI score
        roi_score = base_roi * multiplier * potential_impact * complexity_factor
        
        return roi_score
    
    def _estimate_potential_impact(self, recommendation, sales_metrics, financial_metrics):
        """Оценивает потенциальный эффект от рекомендации"""
        category = recommendation.get('category', '')
        priority = recommendation.get('priority', 'medium')
        
        # Базовый эффект на основе приоритета
        impact_scores = {
            'critical': 1.5,
            'high': 1.3,
            'medium': 1.0,
            'low': 0.7
        }
        base_impact = impact_scores.get(priority, 1.0)
        
        # Дополнительный эффект на основе категории и текущих метрик
        if category == 'Финансы':
            margin = financial_metrics.get('margin_percent', 0) or 0
            if margin < 0:
                return base_impact * 2.0  # Критично низкая маржа
            elif margin < 10:
                return base_impact * 1.5
        elif category == 'Продажи':
            conversion = sales_metrics.get('conversion_rate', 0) or 0
            if conversion < 70:
                return base_impact * 1.5  # Низкая конверсия
        elif category == 'Возвраты':
            return_rate = 0  # Нужно получить из returns_metrics
            if return_rate > 5:
                return base_impact * 1.3  # Высокий процент возвратов
        
        return base_impact
    
    def _estimate_complexity(self, recommendation):
        """Оценивает сложность реализации рекомендации"""
        action_plan = recommendation.get('action_plan', {})
        priority = recommendation.get('priority', 'medium')
        
        # Базовая сложность на основе приоритета
        complexity_scores = {
            'critical': 1.0,  # Проще реализовать критичные
            'high': 1.2,
            'medium': 1.5,
            'low': 2.0
        }
        base_complexity = complexity_scores.get(priority, 1.5)
        
        # Увеличиваем сложность если много шагов
        immediate_steps = len(action_plan.get('immediate', []))
        short_term_steps = len(action_plan.get('short_term', []))
        long_term_steps = len(action_plan.get('long_term', []))
        
        total_steps = immediate_steps + short_term_steps + long_term_steps
        if total_steps > 10:
            base_complexity *= 1.5
        elif total_steps > 5:
            base_complexity *= 1.2
        
        return base_complexity
    
    def _calculate_priority_score(self, recommendation, roi_score):
        """Рассчитывает итоговый priority score"""
        priority = recommendation.get('priority', 'medium')
        
        # Базовый score на основе приоритета
        priority_base_scores = {
            'critical': 1000,
            'high': 500,
            'medium': 200,
            'low': 50
        }
        base_score = priority_base_scores.get(priority, 200)
        
        # Добавляем ROI score
        final_score = base_score + roi_score
        
        return final_score
    
    def _sales_recommendations(self, metrics, product_metrics):
        """Рекомендации по продажам с планами действий"""
        recs = []
        
        cancellation_rate = metrics.get('cancellation_rate', 0) or 0
        if cancellation_rate is not None and cancellation_rate > 5:
            recs.append({
                'category': 'Продажи',
                'priority': 'high',
                'title': 'Критично: Высокий процент отмен заказов',
                'description': f'Текущий процент отмен: {cancellation_rate:.1f}%. Это критично влияет на рейтинг продавца и видимость товаров.',
                'action': 'Проверьте описания товаров, добавьте детальные фото и характеристики',
                'action_plan': {
                    'immediate': [
                        'Проанализируйте причины отмен через личный кабинет Ozon',
                        'Проверьте наличие всех обязательных характеристик в карточках',
                        'Добавьте минимум 10 качественных фотографий для каждого товара'
                    ],
                    'short_term': [
                        'Создайте видео-обзоры товаров (особенно для медицинских массажеров)',
                        'Добавьте инструкцию по применению прямо в описание',
                        'Улучшите заголовки товаров - добавьте ключевые слова: "медицинский", "для лечения", "сертифицирован"'
                    ],
                    'long_term': [
                        'Настройте автоматические напоминания покупателям о заказах',
                        'Улучшите упаковку - добавьте инструкцию и гарантийный талон',
                        'Создайте FAQ раздел в описании товара'
                    ],
                    'expected_result': 'Снижение отмен на 30-50% в течение месяца'
                }
            })
        
        conversion_rate = metrics.get('conversion_rate', 0) or 0
        if conversion_rate is not None and conversion_rate < 70:
            recs.append({
                'category': 'Продажи',
                'priority': 'high',
                'title': 'Низкая конверсия заказов',
                'description': f'Конверсия: {conversion_rate:.1f}%. Для медицинских товаров норма 75-85%.',
                'action': 'Оптимизируйте карточки товаров и ценообразование',
                'action_plan': {
                    'immediate': [
                        'Проведите конкурентный анализ - сравните цены топ-5 конкурентов',
                        'Проверьте рейтинг товаров (должен быть выше 4.5)',
                        'Убедитесь, что все товары имеют сертификаты и документы'
                    ],
                    'short_term': [
                        'Добавьте отзывы покупателей с фотографиями (особенно важно для медицинских товаров)',
                        'Создайте сравнение с конкурентами в описании',
                        'Добавьте гарантии и сервисные обязательства'
                    ],
                    'long_term': [
                        'Настройте ретаргетинг через Ozon Advertising',
                        'Создайте брендированные карточки с единым стилем',
                        'Запустите программу лояльности для повторных покупок'
                    ],
                    'expected_result': 'Увеличение конверсии до 75-80% за 2-3 месяца'
                }
            })
        
        avg_order = metrics.get('avg_order_value', 0) or 0
        if avg_order is not None and avg_order < 8000:
            recs.append({
                'category': 'Продажи',
                'priority': 'medium',
                'title': 'Повышение среднего чека',
                'description': f'Средний чек: {avg_order:.0f} руб. Для медицинских товаров можно увеличить до 12-15 тыс. руб.',
                'action': 'Создайте комплекты и предложения сопутствующих товаров',
                'action_plan': {
                    'immediate': [
                        'Создайте комплекты: "Cordus + Sacrus + Кейс" с выгодой 15-20%',
                        'Добавьте сопутствующие товары: кремы, инструкции, дополнительные насадки',
                        'Настройте автоматические рекомендации в карточке товара'
                    ],
                    'short_term': [
                        'Создайте программу "Купи 2 - получи скидку 10%"',
                        'Добавьте товары для ухода за массажерами',
                        'Создайте подарочные наборы для разных случаев'
                    ],
                    'long_term': [
                        'Разработайте линейку товаров разной ценовой категории',
                        'Создайте подписку на расходные материалы',
                        'Запустите программу trade-in старых товаров'
                    ],
                    'expected_result': 'Увеличение среднего чека на 30-40% за квартал'
                }
            })
        
        return recs
    
    def _financial_recommendations(self, metrics, sales_metrics, product_metrics):
        """Рекомендации по финансам с планами действий"""
        recs = []
        
        margin_percent = metrics.get('margin_percent', 0) or 0
        margin_note = metrics.get('margin_note', '')
        
        # Проверяем, есть ли данные юнит-экономики
        has_unit_economics = not margin_note or 'юнит-экономики' not in margin_note.lower()
        
        if margin_percent is not None and margin_percent < 0:
            title = 'КРИТИЧНО: Отрицательная маржа - работа в убыток'
            description = f'Маржа: {margin_percent:.1f}%. Вы теряете деньги на каждой продаже!'
            
            if not has_unit_economics:
                title += ' (требуется отчет юнит-экономики)'
                description += ' Для точного расчета маржи загрузите отчет "Юнит-экономика".'
            
            recs.append({
                'category': 'Финансы',
                'priority': 'critical',
                'title': title,
                'description': description,
                'action': 'СРОЧНО пересмотрите ценообразование и себестоимость',
                'action_plan': {
                    'immediate': [
                        'Проведите аудит себестоимости каждого товара',
                        'Рассчитайте минимальную цену: Себестоимость + Комиссия Ozon (8-15%) + Логистика + Налоги + Маржа (минимум 20%)',
                        'Повысьте цены на товары с отрицательной маржой минимум на 30%'
                    ],
                    'short_term': [
                        'Пересмотрите договоры с поставщиками - договоритесь о скидках при больших объемах',
                        'Оптимизируйте логистику - используйте более дешевые склады',
                        'Снизьте комиссии Ozon через программу лояльности продавцов'
                    ],
                    'long_term': [
                        'Разработайте собственную линейку товаров с лучшей маржой',
                        'Оптимизируйте налоговую схему',
                        'Создайте прямые каналы продаж для снижения комиссий'
                    ],
                    'expected_result': 'Достижение маржи минимум 15-20% в течение месяца'
                }
            })
        elif margin_percent is not None and margin_percent < 10:
            recs.append({
                'category': 'Финансы',
                'priority': 'high',
                'title': 'Низкая маржинальность',
                'description': f'Маржа: {margin_percent:.1f}%. Для медицинских товаров норма 20-30%.',
                'action': 'Оптимизируйте закупочные цены и увеличивайте средний чек',
                'action_plan': {
                    'immediate': [
                        'Проведите переговоры с поставщиками о снижении цен на 10-15%',
                        'Увеличьте цены на товары с низкой маржой на 10-15%',
                        'Сфокусируйтесь на продаже товаров с лучшей маржой'
                    ],
                    'short_term': [
                        'Создайте комплекты с маржой 25-30%',
                        'Оптимизируйте ассортимент - уберите товары с маржой менее 10%',
                        'Используйте динамическое ценообразование'
                    ],
                    'long_term': [
                        'Разработайте премиум-линейку с маржой 40%+',
                        'Создайте прямые контракты с производителями',
                        'Оптимизируйте складские расходы'
                    ],
                    'expected_result': 'Увеличение маржи до 20-25% за 2-3 месяца'
                }
            })
        
        total_discounts = metrics.get('total_discounts', 0)
        revenue = metrics.get('total_revenue', 1)
        discount_ratio = (total_discounts / revenue * 100) if revenue > 0 else 0
        
        avg_discount = product_metrics.get('avg_discount', 0) if product_metrics else 0
        if discount_ratio > 30 or avg_discount > 50:
            recs.append({
                'category': 'Финансы',
                'priority': 'high',
                'title': 'Критично: Слишком высокие скидки разрушают маржу',
                'description': f'Средняя скидка: {avg_discount:.0f}%, доля скидок в выручке: {discount_ratio:.1f}%. Для медицинских товаров большие скидки снижают доверие.',
                'action': 'Пересмотрите стратегию скидок - используйте точечные акции',
                'action_plan': {
                    'immediate': [
                        'Снизьте постоянные скидки до 10-15% максимум',
                        'Уберите скидки выше 30% - они создают впечатление низкого качества',
                        'Вместо постоянных скидок используйте акции на 1-2 недели'
                    ],
                    'short_term': [
                        'Создайте акцию "Первая покупка - скидка 10%" только для новых клиентов',
                        'Используйте скидки на комплекты, а не на отдельные товары',
                        'Запустите программу "День рождения - скидка 15%"'
                    ],
                    'long_term': [
                        'Создайте программу лояльности вместо постоянных скидок',
                        'Используйте скидки только для распродажи остатков',
                        'Фокусируйтесь на ценности, а не на цене'
                    ],
                    'expected_result': 'Снижение доли скидок до 15-20%, увеличение маржи на 5-10%'
                }
            })
        
        return recs
    
    def _logistics_recommendations(self, metrics):
        """Рекомендации по логистике"""
        recs = []
        
        avg_delivery = metrics.get('avg_delivery_time_days', 0) or 0
        if avg_delivery is not None and avg_delivery > 5:
            recs.append({
                'category': 'Логистика',
                'priority': 'high',
                'title': 'Долгая доставка снижает конверсию',
                'description': f'Среднее время доставки: {avg_delivery:.1f} дней. Для медицинских товаров важна быстрая доставка.',
                'action': 'Оптимизируйте распределение по складам',
                'action_plan': {
                    'immediate': [
                        'Разместите товары на складах в топ-5 регионов продаж',
                        'Используйте FBO (Fulfillment by Ozon) для быстрой доставки',
                        'Настройте автоматическое распределение остатков'
                    ],
                    'short_term': [
                        'Проанализируйте карту продаж и разместите товары ближе к покупателям',
                        'Используйте экспресс-доставку для премиум-клиентов',
                        'Оптимизируйте упаковку для снижения веса и объема'
                    ],
                    'long_term': [
                        'Создайте региональные склады в топ-3 городах',
                        'Настройте систему прогнозирования спроса',
                        'Автоматизируйте пополнение остатков'
                    ],
                    'expected_result': 'Снижение времени доставки до 2-3 дней, увеличение конверсии на 10-15%'
                }
            })
        
        warehouses = metrics.get('warehouses', {})
        if warehouses:
            total_orders = sum(warehouses.values())
            if total_orders > 0:
                max_warehouse_share = max(warehouses.values()) / total_orders * 100
                if max_warehouse_share > 60:
                    recs.append({
                        'category': 'Логистика',
                        'priority': 'medium',
                        'title': 'Неравномерное распределение по складам',
                        'description': f'Один склад обрабатывает {max_warehouse_share:.0f}% заказов.',
                        'action': 'Распределите товары по нескольким складам',
                        'action_plan': {
                            'immediate': [
                                'Разместите 30-40% остатков на складах в регионах',
                                'Используйте склад в Москве для центрального региона',
                                'Добавьте склад в Санкт-Петербурге для СЗО'
                            ],
                            'short_term': [
                                'Проанализируйте регионы продаж и разместите товары соответственно',
                                'Настройте автоматическое перераспределение остатков',
                                'Используйте прогнозирование спроса по регионам'
                            ],
                            'long_term': [
                                'Создайте стратегию размещения товаров на основе данных',
                                'Оптимизируйте складские расходы',
                                'Автоматизируйте процесс пополнения'
                            ],
                            'expected_result': 'Снижение времени доставки на 30-40%, увеличение удовлетворенности клиентов'
                        }
                    })
        
        return recs
    
    def _inventory_recommendations(self, metrics, sales_metrics):
        """Рекомендации по остаткам"""
        recs = []
        
        out_of_stock = metrics.get('out_of_stock_count', 0) or 0
        if out_of_stock is not None and out_of_stock > 0:
            recs.append({
                'category': 'Остатки',
                'priority': 'high',
                'title': 'Товары с нулевыми остатками теряют позиции',
                'description': f'Найдено {out_of_stock} товаров без остатков. Ozon снижает позиции товаров без остатков.',
                'action': 'Срочно пополните остатки',
                'action_plan': {
                    'immediate': [
                        'Пополните остатки товаров, которые закончились',
                        'Установите минимальный остаток = 30 дней продаж',
                        'Настройте уведомления о низких остатках'
                    ],
                    'short_term': [
                        'Создайте систему автоматического заказа при достижении минимума',
                        'Проанализируйте скорость продаж каждого товара',
                        'Оптимизируйте остатки на основе сезонности'
                    ],
                    'long_term': [
                        'Внедрите систему прогнозирования спроса',
                        'Создайте резервные остатки на случай пиков',
                        'Автоматизируйте процесс закупок'
                    ],
                    'expected_result': 'Снижение потерь продаж на 20-30%, поддержание позиций в поиске'
                }
            })
        
        # Анализ остатков для топ-товаров
        top_products = sales_metrics.get('top_products', {})
        if top_products:
            recs.append({
                'category': 'Остатки',
                'priority': 'medium',
                'title': 'Оптимизация остатков топ-товаров',
                'description': f'У вас {len(top_products)} топ-товаров. Важно поддерживать их остатки.',
                'action': 'Увеличьте остатки топ-товаров',
                'action_plan': {
                    'immediate': [
                        'Увеличьте остатки топ-3 товаров до 60 дней продаж',
                        'Разместите топ-товары на всех складах',
                        'Создайте резервный запас на случай пиков'
                    ],
                    'short_term': [
                        'Настройте автоматическое пополнение для топ-товаров',
                        'Мониторьте остатки топ-товаров ежедневно',
                        'Создайте систему раннего предупреждения'
                    ],
                    'long_term': [
                        'Разработайте стратегию остатков для каждого товара',
                        'Используйте прогнозирование для топ-товаров',
                        'Оптимизируйте складские расходы'
                    ],
                    'expected_result': 'Снижение потерь продаж топ-товаров на 50%'
                }
            })
        
        return recs
    
    def _returns_recommendations(self, metrics):
        """Рекомендации по возвратам"""
        recs = []
        
        return_rate = metrics.get('return_rate', 0) or 0
        if return_rate is not None and return_rate > 5:
            recs.append({
                'category': 'Возвраты',
                'priority': 'high',
                'title': 'Высокий процент возвратов',
                'description': f'Процент возвратов: {return_rate:.1f}%. Для медицинских товаров норма 1-3%.',
                'action': 'Улучшите карточки товаров и качество',
                'action_plan': {
                    'immediate': [
                        'Проанализируйте причины возвратов в личном кабинете',
                        'Добавьте детальные фотографии со всех сторон',
                        'Улучшите описание - добавьте размеры, вес, материалы'
                    ],
                    'short_term': [
                        'Создайте видео-инструкцию по использованию',
                        'Добавьте сравнение размеров с известными предметами',
                        'Улучшите упаковку - добавьте инструкцию и гарантию'
                    ],
                    'long_term': [
                        'Создайте программу предпродажной консультации',
                        'Добавьте возможность виртуальной примерки (для некоторых товаров)',
                        'Улучшите качество товаров на основе отзывов'
                    ],
                    'expected_result': 'Снижение возвратов до 2-3% в течение 2-3 месяцев'
                }
            })
        elif return_rate is not None and return_rate > 2:
            recs.append({
                'category': 'Возвраты',
                'priority': 'medium',
                'title': 'Умеренный процент возвратов',
                'description': f'Процент возвратов: {return_rate:.1f}%. Есть потенциал для улучшения.',
                'action': 'Проанализируйте причины и устраните основные проблемы',
                'action_plan': {
                    'immediate': [
                        'Изучите отзывы покупателей о причинах возвратов',
                        'Улучшите описания товаров на основе частых вопросов',
                        'Добавьте больше фотографий и видео'
                    ],
                    'short_term': [
                        'Создайте FAQ на основе частых причин возвратов',
                        'Улучшите упаковку и инструкции',
                        'Добавьте контактную информацию для консультаций'
                    ],
                    'long_term': [
                        'Создайте программу улучшения качества на основе возвратов',
                        'Разработайте систему предпродажной консультации',
                        'Оптимизируйте ассортимент - уберите товары с высоким процентом возвратов'
                    ],
                    'expected_result': 'Снижение возвратов до 1-2%'
                }
            })
        
        return_reasons = metrics.get('return_reasons', {})
        if return_reasons:
            top_reason = max(return_reasons.items(), key=lambda x: x[1]) if return_reasons else None
            if top_reason:
                action_plan = self._get_return_reason_plan(top_reason[0])
                action_plan['expected_result'] = 'Снижение возвратов по этой причине на 50-70%'
                recs.append({
                    'category': 'Возвраты',
                    'priority': 'high',
                    'title': f'Основная причина возвратов: {top_reason[0]}',
                    'description': f'Наиболее частая причина: {top_reason[0]} ({top_reason[1]} случаев).',
                    'action': f'Сфокусируйтесь на устранении: {top_reason[0]}',
                    'action_plan': action_plan,
                })
        
        return recs
    
    def _get_return_reason_plan(self, reason):
        """План действий для конкретной причины возврата"""
        reason_lower = reason.lower()
        
        if 'не подошел' in reason_lower or 'размер' in reason_lower:
            return {
                'immediate': [
                    'Добавьте детальную таблицу размеров с примерами',
                    'Создайте визуальное сравнение размеров',
                    'Добавьте рекомендации по выбору размера'
                ],
                'short_term': [
                    'Создайте калькулятор размера на основе параметров покупателя',
                    'Добавьте возможность консультации перед покупкой',
                    'Улучшите описание размеров с примерами'
                ],
                'long_term': [
                    'Разработайте систему виртуальной примерки',
                    'Создайте программу обмена размера вместо возврата',
                    'Оптимизируйте ассортимент размеров'
                ]
            }
        elif 'качество' in reason_lower or 'брак' in reason_lower:
            return {
                'immediate': [
                    'Проведите аудит качества товаров',
                    'Улучшите контроль качества перед отправкой',
                    'Добавьте фотографии реального товара, а не стоковые'
                ],
                'short_term': [
                    'Смените поставщиков товаров с высоким процентом брака',
                    'Улучшите упаковку для защиты товара',
                    'Добавьте гарантию качества в описание'
                ],
                'long_term': [
                    'Создайте программу контроля качества',
                    'Разработайте стандарты качества',
                    'Оптимизируйте цепочку поставок'
                ]
            }
        elif 'описание' in reason_lower or 'не соответствует' in reason_lower:
            return {
                'immediate': [
                    'Пересмотрите все описания товаров',
                    'Добавьте детальные характеристики',
                    'Убедитесь, что описание соответствует товару'
                ],
                'short_term': [
                    'Добавьте реальные фотографии товара',
                    'Создайте видео-обзоры',
                    'Улучшите описания на основе отзывов'
                ],
                'long_term': [
                    'Создайте стандарты описаний',
                    'Проводите регулярный аудит описаний',
                    'Автоматизируйте проверку соответствия'
                ]
            }
        else:
            return {
                'immediate': [
                    'Проанализируйте конкретные случаи возвратов',
                    'Свяжитесь с покупателями для выяснения причин',
                    'Улучшите описание товара'
                ],
                'short_term': [
                    'Создайте программу предотвращения возвратов',
                    'Улучшите качество товаров и описаний',
                    'Добавьте консультации перед покупкой'
                ],
                'long_term': [
                    'Разработайте стратегию снижения возвратов',
                    'Создайте систему обратной связи',
                    'Оптимизируйте ассортимент'
                ]
            }
    
    def _customer_recommendations(self, metrics):
        """Рекомендации по клиентам"""
        recs = []
        
        premium_ratio = metrics.get('premium_ratio', 0) or 0
        if premium_ratio is not None and premium_ratio < 20:
            recs.append({
                'category': 'Клиенты',
                'priority': 'medium',
                'title': 'Низкая доля премиум-клиентов',
                'description': f'Доля премиум-клиентов: {premium_ratio:.1f}%. Премиум-клиенты покупают больше и чаще.',
                'action': 'Улучшите качество сервиса для привлечения премиум-клиентов',
                'action_plan': {
                    'immediate': [
                        'Предлагайте экспресс-доставку для всех товаров',
                        'Улучшите упаковку - используйте премиум-материалы',
                        'Добавьте гарантию и сервисное обслуживание'
                    ],
                    'short_term': [
                        'Создайте программу лояльности для премиум-клиентов',
                        'Предлагайте эксклюзивные товары и комплекты',
                        'Улучшите качество товаров и упаковки'
                    ],
                    'long_term': [
                        'Разработайте премиум-линейку товаров',
                        'Создайте программу VIP-обслуживания',
                        'Запустите программу персональных предложений'
                    ],
                    'expected_result': 'Увеличение доли премиум-клиентов до 25-30%, увеличение среднего чека на 20-30%'
                }
            })
        
        return recs
    
    def _medical_products_recommendations(self, product_metrics, sales_metrics):
        """Специфические рекомендации для медицинских товаров"""
        recs = []
        
        recs.append({
            'category': 'Медицинские товары',
            'priority': 'high',
            'title': 'Оптимизация карточек медицинских товаров',
            'description': 'Для медицинских товаров критически важны сертификаты, инструкции и детальные описания.',
            'action': 'Улучшите карточки товаров для медицинской ниши',
            'action_plan': {
                'immediate': [
                    'Добавьте сертификаты и документы в карточки товаров',
                    'Укажите медицинские показания и противопоказания',
                    'Добавьте инструкцию по применению прямо в описание',
                    'Укажите материалы и их безопасность (гипоаллергенность, экологичность)'
                ],
                'short_term': [
                    'Создайте видео-инструкции по использованию',
                    'Добавьте отзывы врачей и специалистов',
                    'Создайте раздел "Часто задаваемые вопросы"',
                    'Добавьте информацию о клинических исследованиях (если есть)'
                ],
                'long_term': [
                    'Разработайте образовательный контент о применении',
                    'Создайте программу консультаций с врачами',
                    'Разработайте брендированные материалы',
                    'Создайте сообщество пользователей'
                ],
                'expected_result': 'Увеличение конверсии на 15-25%, снижение возвратов на 30-40%'
            }
        })
        
        recs.append({
            'category': 'Медицинские товары',
            'priority': 'medium',
            'title': 'Работа с отзывами и рейтингом',
            'description': 'Для медицинских товаров отзывы критически важны - покупатели доверяют опыту других.',
            'action': 'Активно работайте с отзывами и рейтингом',
            'action_plan': {
                'immediate': [
                    'Настройте автоматические напоминания покупателям оставить отзыв',
                    'Отвечайте на все отзывы (особенно негативные)',
                    'Просите покупателей оставлять отзывы с фотографиями',
                    'Создайте программу поощрения за отзывы'
                ],
                'short_term': [
                    'Проанализируйте все негативные отзывы и устраните проблемы',
                    'Создайте шаблоны ответов на частые вопросы',
                    'Добавьте отзывы в карточки товаров',
                    'Создайте раздел "Истории успеха" покупателей'
                ],
                'long_term': [
                    'Разработайте стратегию работы с отзывами',
                    'Создайте программу лояльности для активных рецензентов',
                    'Используйте отзывы для улучшения товаров',
                    'Создайте репутационную программу'
                ],
                'expected_result': 'Увеличение рейтинга до 4.7-4.8, увеличение конверсии на 10-15%'
            }
        })
        
        return recs
    
    def _content_recommendations(self, product_metrics):
        """Рекомендации по контенту карточек"""
        recs = []
        
        recs.append({
            'category': 'Контент',
            'priority': 'high',
            'title': 'Оптимизация SEO для медицинских товаров',
            'description': 'Правильные ключевые слова увеличивают видимость в поиске Ozon.',
            'action': 'Оптимизируйте заголовки и описания для поиска',
            'action_plan': {
                'immediate': [
                    'Добавьте ключевые слова в заголовки: "медицинский", "для лечения", "сертифицирован"',
                    'Используйте длинные хвостовые запросы: "массажер для спины при остеохондрозе"',
                    'Добавьте синонимы и альтернативные названия',
                    'Укажите бренд и модель в заголовке'
                ],
                'short_term': [
                    'Проведите анализ поисковых запросов по вашей нише',
                    'Используйте инструменты Ozon для анализа ключевых слов',
                    'Оптимизируйте описания под топ-10 запросов',
                    'Добавьте теги и категории'
                ],
                'long_term': [
                    'Создайте контент-стратегию для каждого товара',
                    'Используйте A/B тестирование заголовков',
                    'Мониторьте позиции в поиске',
                    'Адаптируйте контент под сезонность'
                ],
                'expected_result': 'Увеличение органического трафика на 30-50%, улучшение позиций в поиске'
            }
        })
        
        return recs
    
    def _pricing_recommendations(self, financial_metrics, product_metrics):
        """Рекомендации по ценообразованию"""
        recs = []
        
        avg_discount = (product_metrics.get('avg_discount', 0) if product_metrics else 0) or 0
        if avg_discount is not None and avg_discount > 50:
            recs.append({
                'category': 'Ценообразование',
                'priority': 'high',
                'title': 'Пересмотр стратегии ценообразования',
                'description': f'Средняя скидка: {avg_discount:.0f}%. Для медицинских товаров большие скидки снижают доверие.',
                'action': 'Используйте психологию ценообразования',
                'action_plan': {
                    'immediate': [
                        'Используйте цены, заканчивающиеся на 9 (999, 1999) - это увеличивает конверсию',
                        'Показывайте цену "было-стало" только при реальных акциях',
                        'Используйте якорные цены - показывайте более дорогой вариант рядом',
                        'Создайте ценовую лестницу: базовый-стандарт-премиум'
                    ],
                    'short_term': [
                        'Проведите конкурентный анализ цен',
                        'Используйте динамическое ценообразование',
                        'Создайте ценовую стратегию для каждого товара',
                        'Используйте психологические триггеры: "Осталось 3 штуки"'
                    ],
                    'long_term': [
                        'Разработайте ценовую стратегию бренда',
                        'Создайте программу лояльности вместо скидок',
                        'Используйте ценовую дифференциацию по сегментам',
                        'Оптимизируйте цены на основе данных'
                    ],
                    'expected_result': 'Увеличение конверсии на 10-15%, улучшение восприятия ценности'
                }
            })
        
        return recs
    
    def _success_cases_recommendations(self, sales_metrics, financial_metrics):
        """Рекомендации на основе успешных кейсов в нише"""
        recs = []
        
        # Сравниваем с успешными кейсами
        margin = financial_metrics.get('margin_percent', 0) or 0
        conversion = sales_metrics.get('conversion_rate', 0) or 0
        
        if margin is not None and margin < 25:
            recs.append({
                'category': 'Успешные кейсы',
                'priority': 'medium',
                'title': 'Применение стратегии премиум-позиционирования',
                'description': 'Успешные продавцы медицинских товаров получают маржу 28-35% через премиум-позиционирование.',
                'action': 'Изучите кейс премиум-позиционирования и примените лучшие практики',
                'action_plan': {
                    'immediate': [
                        'Добавьте детальные описания с медицинскими терминами',
                        'Создайте видео-инструкции (можно привлечь врача)',
                        'Улучшите упаковку до премиум-уровня'
                    ],
                    'short_term': [
                        'Предложите гарантию 2 года (вместо стандартной)',
                        'Создайте программу лояльности',
                        'Добавьте отзывы врачей и специалистов'
                    ],
                    'long_term': [
                        'Разработайте брендированную линейку',
                        'Создайте образовательный контент',
                        'Постройте репутацию эксперта в нише'
                    ],
                    'expected_result': 'Увеличение маржи до 25-30%, улучшение восприятия бренда'
                }
            })
        
        if conversion is not None and conversion < 75:
            recs.append({
                'category': 'Успешные кейсы',
                'priority': 'high',
                'title': 'Стратегия комплексных решений',
                'description': 'Успешные продавцы увеличивают конверсию до 78-82% через комплексные решения.',
                'action': 'Создайте комплекты и образовательный контент',
                'action_plan': {
                    'immediate': [
                        'Создайте комплекты: основной товар + сопутствующие + инструкция',
                        'Добавьте образовательный контент в карточки',
                        'Начните активно работать с отзывами (отвечайте на все)'
                    ],
                    'short_term': [
                        'Обеспечьте быструю доставку (1-2 дня)',
                        'Создайте программу консультаций перед покупкой',
                        'Разработайте FAQ на основе частых вопросов'
                    ],
                    'long_term': [
                        'Создайте блог с полезными статьями',
                        'Разработайте программу обучения клиентов',
                        'Постройте сообщество пользователей'
                    ],
                    'expected_result': 'Увеличение конверсии до 75-80%, снижение возвратов на 30-40%'
                }
            })
        
        return recs
    
    def _product_recommendations(self):
        """Рекомендации по товарам (legacy метод для совместимости)"""
        return []
    
    def _seo_recommendations(self, sales_metrics, product_metrics):
        """Рекомендации по SEO оптимизации (критично для нового алгоритма 2025)"""
        recs = []
        
        # Анализируем SEO на основе доступных данных
        if self.analytics and self.analytics.orders:
            seo_result = self.seo_analyzer.get_seo_score_for_orders(self.analytics.orders)
            seo_score = seo_result.get('seo_score', 0)
            seo_level = seo_result.get('seo_level', 'unknown')
            
            if seo_score < 60:
                recs.append({
                    'category': 'SEO и контент',
                    'priority': 'critical',
                    'title': 'КРИТИЧНО: Низкий SEO Score - товары не попадут в топ без рекламы',
                    'description': f'SEO Score: {seo_score}/100 ({seo_level}). Новый алгоритм Ozon 2025 требует качественный контент для органического продвижения.',
                    'action': 'Срочно оптимизируйте карточки товаров для нового алгоритма',
                    'action_plan': {
                        'immediate': [
                            'Оптимизируйте заголовки: добавьте ключевые слова "медицинский", "для лечения", "сертифицирован"',
                            'Увеличьте описания до 500+ символов с ключевыми словами',
                            'Добавьте минимум 5 качественных фотографий с разных ракурсов',
                            'Структурируйте описания: используйте списки, абзацы, нумерацию'
                        ],
                        'short_term': [
                            'Добавьте Rich-контент (мини-лендинги) в карточки товаров',
                            'Создайте видео-обзоры или инструкции по использованию',
                            'Проведите анализ поисковых запросов по вашей нише',
                            'Оптимизируйте описания под топ-10 поисковых запросов'
                        ],
                        'long_term': [
                            'Создайте контент-стратегию для каждого товара',
                            'Используйте A/B тестирование заголовков',
                            'Мониторьте позиции в поиске Ozon',
                            'Адаптируйте контент под сезонность и тренды'
                        ],
                        'expected_result': 'Увеличение SEO Score до 70-80+, улучшение позиций в поиске на 30-50%'
                    }
                })
            elif seo_score < 80:
                recs.append({
                    'category': 'SEO и контент',
                    'priority': 'high',
                    'title': 'SEO можно улучшить для лучших позиций',
                    'description': f'SEO Score: {seo_score}/100 ({seo_level}). Есть потенциал для улучшения органического продвижения.',
                    'action': 'Дополните карточки товаров Rich-контентом и видео',
                    'action_plan': {
                        'immediate': [
                            'Добавьте Rich-контент в топ-5 товаров',
                            'Создайте видео-инструкции для медицинских товаров',
                            'Добавьте больше ключевых слов в описания'
                        ],
                        'short_term': [
                            'Проведите конкурентный анализ SEO',
                            'Улучшите структуру описаний',
                            'Добавьте FAQ разделы в карточки'
                        ],
                        'expected_result': 'Увеличение SEO Score до 80+, рост органического трафика на 20-30%'
                    }
                })
        
        # Рекомендации по Rich-контенту
        recs.append({
            'category': 'SEO и контент',
            'priority': 'high',
            'title': 'Добавление Rich-контента (мини-лендингов)',
            'description': 'Rich-контент увеличивает конверсию на 15-25% и улучшает позиции в новом алгоритме.',
            'action': 'Создайте мини-лендинги для топ-товаров',
            'action_plan': {
                'immediate': [
                    'Используйте инструмент "Rich-контент" в кабинете Ozon',
                    'Создайте мини-лендинги для топ-3 товаров',
                    'Добавьте блоки: преимущества, применение, отзывы, сравнение'
                ],
                'short_term': [
                    'Создайте Rich-контент для всех товаров',
                    'Используйте визуальные элементы: иконки, схемы, таблицы',
                    'Добавьте интерактивные элементы'
                ],
                'expected_result': 'Увеличение конверсии на 15-25%, улучшение позиций в поиске'
            }
        })
        
        return recs
    
    def _review_management_recommendations(self):
        """Рекомендации по работе с отзывами (критично для нового алгоритма)"""
        recs = []
        
        # Получаем данные об отзывах из аналитики
        store_data = {}
        if self.store_analytics:
            store_metrics = self.store_analytics.get_store_metrics()
            store_data = {'reviews_info': store_metrics.get('reviews_info', {}), 
                         'rating_info': store_metrics.get('rating_info', {})}
        
        review_metrics = self.review_analyzer.get_review_metrics_for_store(store_data)
        avg_rating = review_metrics.get('average_rating', 0) or 0
        total_reviews = review_metrics.get('total_reviews', 0) or 0
        
        # Критичные рекомендации по отзывам
        if avg_rating > 0 and avg_rating < 4.7:
            recs.append({
                'category': 'Работа с отзывами',
                'priority': 'critical',
                'title': 'КРИТИЧНО: Низкий рейтинг снижает позиции в новом алгоритме',
                'description': f'Рейтинг: {avg_rating:.2f}/5.0. Отзывы - критический фактор ранжирования в алгоритме 2025.',
                'action': 'Срочно улучшите качество товаров и работу с отзывами',
                'action_plan': {
                    'immediate': [
                        'Проанализируйте все негативные отзывы и устраните проблемы',
                        'Отвечайте на ВСЕ отзывы в течение 24 часов',
                        'Просите довольных покупателей оставлять отзывы',
                        'Улучшите качество товаров на основе отзывов'
                    ],
                    'short_term': [
                        'Настройте автоматические напоминания покупателям об отзывах',
                        'Создайте программу поощрения за отзывы с фотографиями',
                        'Используйте шаблоны ответов на частые вопросы',
                        'Добавьте отзывы в карточки товаров'
                    ],
                    'long_term': [
                        'Разработайте стратегию работы с отзывами',
                        'Создайте программу лояльности для активных рецензентов',
                        'Используйте отзывы для улучшения товаров',
                        'Постройте репутационную программу'
                    ],
                    'expected_result': 'Увеличение рейтинга до 4.7-4.8, улучшение позиций в поиске на 20-30%'
                }
            })
        
        # Рекомендации по ответам на отзывы
        response_rate = review_metrics.get('response_rate', 0) or 0
        if response_rate < 80:
            recs.append({
                'category': 'Работа с отзывами',
                'priority': 'high',
                'title': 'Низкий процент ответов на отзывы',
                'description': f'Отвечаете на {response_rate:.1f}% отзывов. Ozon учитывает активность продавца в новом алгоритме.',
                'action': 'Отвечайте на все отзывы, особенно негативные',
                'action_plan': {
                    'immediate': [
                        'Проверьте все неотвеченные отзывы',
                        'Ответьте на все отзывы за последние 7 дней',
                        'Используйте вежливый и профессиональный тон'
                    ],
                    'short_term': [
                        'Настройте ежедневную проверку новых отзывов',
                        'Создайте шаблоны ответов на частые вопросы',
                        'Используйте персонализированные ответы'
                    ],
                    'expected_result': 'Увеличение процента ответов до 90%+, улучшение репутации'
                }
            })
        
        # Рекомендации по отзывам с фото
        photo_ratio = review_metrics.get('photo_reviews_ratio', 0) or 0
        if photo_ratio < 30:
            recs.append({
                'category': 'Работа с отзывами',
                'priority': 'medium',
                'title': 'Мало отзывов с фотографиями',
                'description': f'Только {photo_ratio:.1f}% отзывов содержат фото. Отзывы с фото увеличивают доверие и конверсию.',
                'action': 'Стимулируйте покупателей оставлять отзывы с фотографиями',
                'action_plan': {
                    'immediate': [
                        'Добавьте в упаковку просьбу оставить отзыв с фото',
                        'Создайте программу поощрения за отзывы с фото',
                        'Напишите покупателям после доставки с просьбой об отзыве'
                    ],
                    'short_term': [
                        'Используйте автоматические напоминания',
                        'Предлагайте небольшие бонусы за отзывы с фото',
                        'Показывайте примеры хороших отзывов'
                    ],
                    'expected_result': 'Увеличение отзывов с фото до 30%+, рост конверсии на 10-15%'
                }
            })
        
        return recs
    
    def _advertising_recommendations(self, sales_metrics, financial_metrics):
        """Рекомендации по рекламной стратегии"""
        recs = []
        
        # Используем AdvertisingAnalyzer для генерации рекомендаций
        advertising_recs = self.advertising_analyzer.get_advertising_recommendations_based_on_metrics(
            sales_metrics, financial_metrics
        )
        recs.extend(advertising_recs)
        
        # Дополнительные рекомендации по новым инструментам Ozon 2025
        conversion_rate = sales_metrics.get('conversion_rate', 0) or 0
        
        recs.append({
            'category': 'Реклама',
            'priority': 'high',
            'title': 'Использование объединенных CPC/CPO ставок',
            'description': 'Ozon объединил CPC и CPO ставки для оптимизации расходов на рекламу.',
            'action': 'Используйте объединенные ставки для снижения расходов',
            'action_plan': {
                'immediate': [
                    'Переключитесь на объединенные CPC/CPO ставки в кампаниях',
                    'Протестируйте на 1-2 товарах',
                    'Сравните эффективность с предыдущими кампаниями'
                ],
                'short_term': [
                    'Оптимизируйте ставки на основе данных',
                    'Используйте автоматическую оптимизацию',
                    'Расширьте на все товары при положительных результатах'
                ],
                'expected_result': 'Снижение рекламных расходов на 15-25% при сохранении продаж'
            }
        })
        
        return recs
    
    def _ranking_factors_recommendations(self, sales_metrics, financial_metrics):
        """Рекомендации по улучшению факторов ранжирования"""
        recs = []
        
        # Получаем Ranking Factors Score из аналитики
        if self.analytics:
            try:
                marketplace_metrics = self.analytics.get_marketplace_metrics({})
                ranking_factors = marketplace_metrics.get('ranking_factors', {})
                overall_score = ranking_factors.get('overall_score', 0) or 0
                
                if overall_score < 60:
                    recs.append({
                        'category': 'Факторы ранжирования',
                        'priority': 'critical',
                        'title': 'КРИТИЧНО: Низкий Ranking Factors Score',
                        'description': f'Общий score факторов ранжирования: {overall_score}/100. Товары не попадут в топ без улучшения.',
                        'action': 'Улучшите все факторы ранжирования комплексно',
                        'action_plan': {
                            'immediate': [
                                'Улучшите SEO (релевантность) - оптимизируйте карточки',
                                'Работайте с отзывами - отвечайте на все, улучшайте рейтинг',
                                'Оптимизируйте цены - сделайте их конкурентоспособными',
                                'Улучшите доставку - сократите сроки, используйте FBO'
                            ],
                            'short_term': [
                                'Добавьте Rich-контент в карточки',
                                'Улучшите рейтинг до 4.7+',
                                'Проанализируйте конкурентов по ценам',
                                'Распределите товары по складам для быстрой доставки'
                            ],
                            'long_term': [
                                'Разработайте комплексную стратегию ранжирования',
                                'Мониторьте позиции в поиске',
                                'Адаптируйте стратегию под изменения алгоритма',
                                'Автоматизируйте процессы улучшения'
                            ],
                            'expected_result': 'Увеличение Ranking Factors Score до 70-80+, попадание в топ без рекламы'
                        }
                    })
            except Exception as e:
                # Если ошибка, добавляем общую рекомендацию
                pass
        
        # Рекомендации по органическому продвижению
        recs.append({
            'category': 'Факторы ранжирования',
            'priority': 'high',
            'title': 'Стратегия органического продвижения без рекламы',
            'description': 'Новый алгоритм позволяет попасть в топ без рекламы при высоких органических показателях.',
            'action': 'Фокусируйтесь на улучшении органических факторов',
            'action_plan': {
                'immediate': [
                    'Улучшите SEO всех карточек товаров',
                    'Доведите рейтинг до 4.7+',
                    'Оптимизируйте цены под конкурентов',
                    'Улучшите скорость доставки'
                ],
                'short_term': [
                    'Создайте Rich-контент для всех товаров',
                    'Активно работайте с отзывами',
                    'Мониторьте позиции в поиске',
                    'Анализируйте конкурентов'
                ],
                'long_term': [
                    'Постройте долгосрочную стратегию органического продвижения',
                    'Создайте брендированный контент',
                    'Постройте репутацию эксперта в нише',
                    'Используйте данные для постоянной оптимизации'
                ],
                'expected_result': 'Попадание в топ-12 поиска без рекламы, снижение рекламных расходов на 50-70%'
            }
        })
        
        return recs
