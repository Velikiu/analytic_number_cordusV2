"""
Анализатор SEO-оптимизации карточек товаров Ozon
Оценивает качество контента, ключевые слова, полноту описаний
"""
import re
from typing import Dict, List, Optional
import pandas as pd


class SEOAnalyzer:
    """Анализатор SEO-оптимизации карточек товаров"""
    
    # Ключевые слова для медицинских товаров
    MEDICAL_KEYWORDS = [
        'медицинский', 'для лечения', 'сертифицирован', 'терапевтический',
        'физиотерапевтический', 'при остеохондрозе', 'при болях в спине',
        'для позвоночника', 'массажер', 'массаж', 'терапия', 'реабилитация'
    ]
    
    # Минимальные требования для хорошей карточки
    MIN_DESCRIPTION_LENGTH = 500  # символов
    MIN_PHOTOS_COUNT = 5
    MIN_CHARACTERISTICS_COUNT = 10
    
    def __init__(self):
        self.products_data = []
    
    def analyze_product_seo(self, product_data: Dict) -> Dict:
        """
        Анализирует SEO одного товара
        
        Args:
            product_data: словарь с данными товара (sku, product_name, description, etc.)
        
        Returns:
            словарь с оценкой SEO
        """
        score = 0
        max_score = 100
        issues = []
        recommendations = []
        
        # Проверка заголовка (30 баллов)
        title_score, title_issues, title_recs = self._analyze_title(
            product_data.get('product_name', '') or product_data.get('title', '')
        )
        score += title_score
        issues.extend(title_issues)
        recommendations.extend(title_recs)
        
        # Проверка описания (30 баллов)
        desc_score, desc_issues, desc_recs = self._analyze_description(
            product_data.get('description', '') or product_data.get('product_description', '')
        )
        score += desc_score
        issues.extend(desc_issues)
        recommendations.extend(desc_recs)
        
        # Проверка характеристик (20 баллов)
        char_score, char_issues, char_recs = self._analyze_characteristics(product_data)
        score += char_score
        issues.extend(char_issues)
        recommendations.extend(char_recs)
        
        # Проверка медиа-контента (20 баллов)
        media_score, media_issues, media_recs = self._analyze_media(product_data)
        score += media_score
        issues.extend(media_issues)
        recommendations.extend(media_recs)
        
        # Определение уровня
        if score >= 80:
            level = 'excellent'
        elif score >= 60:
            level = 'good'
        elif score >= 40:
            level = 'fair'
        else:
            level = 'poor'
        
        return {
            'sku': product_data.get('sku', ''),
            'product_name': product_data.get('product_name', ''),
            'seo_score': score,
            'seo_level': level,
            'title_score': title_score,
            'description_score': desc_score,
            'characteristics_score': char_score,
            'media_score': media_score,
            'issues': issues,
            'recommendations': recommendations
        }
    
    def _analyze_title(self, title: str) -> tuple:
        """Анализирует заголовок товара"""
        if not title:
            return 0, ['Заголовок отсутствует'], ['Добавьте заголовок товара']
        
        score = 0
        issues = []
        recommendations = []
        
        # Длина заголовка (10 баллов)
        if 30 <= len(title) <= 100:
            score += 10
        elif len(title) < 30:
            issues.append('Заголовок слишком короткий (менее 30 символов)')
            recommendations.append('Увеличьте заголовок до 30-100 символов')
            score += 5
        else:
            issues.append('Заголовок слишком длинный (более 100 символов)')
            recommendations.append('Сократите заголовок до 100 символов')
            score += 5
        
        # Наличие ключевых слов (10 баллов)
        title_lower = title.lower()
        found_keywords = [kw for kw in self.MEDICAL_KEYWORDS if kw in title_lower]
        if found_keywords:
            score += 10
            if len(found_keywords) >= 2:
                score += 5  # Бонус за несколько ключевых слов
        else:
            issues.append('В заголовке отсутствуют ключевые слова')
            recommendations.append('Добавьте ключевые слова: "медицинский", "для лечения", "сертифицирован"')
        
        # Наличие бренда/модели (5 баллов)
        if any(word in title_lower for word in ['cordus', 'sacrus', 'бренд', 'модель']):
            score += 5
        
        return min(score, 30), issues, recommendations
    
    def _analyze_description(self, description: str) -> tuple:
        """Анализирует описание товара"""
        if not description:
            return 0, ['Описание отсутствует'], ['Добавьте подробное описание товара']
        
        score = 0
        issues = []
        recommendations = []
        
        # Длина описания (15 баллов)
        desc_length = len(description)
        if desc_length >= self.MIN_DESCRIPTION_LENGTH:
            score += 15
        elif desc_length >= 300:
            score += 10
            issues.append(f'Описание короткое ({desc_length} символов)')
            recommendations.append(f'Увеличьте описание до {self.MIN_DESCRIPTION_LENGTH}+ символов')
        else:
            score += 5
            issues.append(f'Описание слишком короткое ({desc_length} символов)')
            recommendations.append(f'Добавьте подробное описание (минимум {self.MIN_DESCRIPTION_LENGTH} символов)')
        
        # Наличие ключевых слов (10 баллов)
        desc_lower = description.lower()
        found_keywords = [kw for kw in self.MEDICAL_KEYWORDS if kw in desc_lower]
        keyword_score = min(len(found_keywords) * 2, 10)
        score += keyword_score
        
        if len(found_keywords) < 3:
            issues.append('В описании мало ключевых слов')
            recommendations.append('Добавьте больше ключевых слов в описание')
        
        # Наличие структурированных элементов (5 баллов)
        has_bullets = bool(re.search(r'[•\-\*]', description))
        has_numbers = bool(re.search(r'\d+\.', description))
        has_paragraphs = description.count('\n') >= 2
        
        if has_bullets or has_numbers or has_paragraphs:
            score += 5
        else:
            issues.append('Описание не структурировано')
            recommendations.append('Используйте списки, нумерацию и абзацы для структурирования')
        
        return min(score, 30), issues, recommendations
    
    def _analyze_characteristics(self, product_data: Dict) -> tuple:
        """Анализирует характеристики товара"""
        score = 0
        issues = []
        recommendations = []
        
        # Подсчет характеристик
        characteristics_count = 0
        
        # Проверяем различные поля с характеристиками
        if 'characteristics' in product_data:
            if isinstance(product_data['characteristics'], dict):
                characteristics_count = len(product_data['characteristics'])
            elif isinstance(product_data['characteristics'], list):
                characteristics_count = len(product_data['characteristics'])
        
        # Проверяем наличие важных характеристик
        important_fields = [
            'material', 'size', 'weight', 'color', 'warranty',
            'certificate', 'indications', 'contraindications'
        ]
        
        found_important = sum(1 for field in important_fields 
                            if product_data.get(field) or product_data.get(field.replace('_', '_')) is not None)
        
        # Оценка (20 баллов)
        if characteristics_count >= self.MIN_CHARACTERISTICS_COUNT or found_important >= 5:
            score += 20
        elif characteristics_count >= 5 or found_important >= 3:
            score += 15
            issues.append('Характеристик недостаточно')
            recommendations.append('Добавьте больше характеристик товара')
        else:
            score += 10
            issues.append('Характеристики отсутствуют или их мало')
            recommendations.append('Добавьте характеристики: материал, размер, вес, гарантия, сертификаты')
        
        return score, issues, recommendations
    
    def _analyze_media(self, product_data: Dict) -> tuple:
        """Анализирует медиа-контент (фото, видео)"""
        score = 0
        issues = []
        recommendations = []
        
        # Подсчет фото
        photos_count = 0
        if 'photos' in product_data:
            if isinstance(product_data['photos'], list):
                photos_count = len(product_data['photos'])
            elif isinstance(product_data['photos'], str):
                photos_count = product_data['photos'].count(',') + 1
        
        if 'images' in product_data:
            if isinstance(product_data['images'], list):
                photos_count = max(photos_count, len(product_data['images']))
        
        # Подсчет видео
        has_video = False
        if 'video' in product_data and product_data['video']:
            has_video = True
        if 'videos' in product_data:
            if isinstance(product_data['videos'], list) and len(product_data['videos']) > 0:
                has_video = True
        
        # Оценка фото (15 баллов)
        if photos_count >= self.MIN_PHOTOS_COUNT:
            score += 15
        elif photos_count >= 3:
            score += 10
            issues.append(f'Мало фотографий ({photos_count})')
            recommendations.append(f'Добавьте минимум {self.MIN_PHOTOS_COUNT} фотографий')
        elif photos_count > 0:
            score += 5
            issues.append(f'Очень мало фотографий ({photos_count})')
            recommendations.append(f'Добавьте больше фотографий (минимум {self.MIN_PHOTOS_COUNT})')
        else:
            issues.append('Фотографии отсутствуют')
            recommendations.append('Добавьте фотографии товара с разных ракурсов')
        
        # Оценка видео (5 баллов)
        if has_video:
            score += 5
        else:
            issues.append('Видео отсутствует')
            recommendations.append('Добавьте видео-обзор или инструкцию по использованию')
        
        return score, issues, recommendations
    
    def analyze_multiple_products(self, products_data: List[Dict]) -> Dict:
        """
        Анализирует SEO нескольких товаров
        
        Args:
            products_data: список словарей с данными товаров
        
        Returns:
            агрегированная статистика по всем товарам
        """
        if not products_data:
            return {
                'total_products': 0,
                'average_seo_score': 0,
                'products_by_level': {},
                'common_issues': [],
                'top_recommendations': []
            }
        
        results = []
        for product in products_data:
            result = self.analyze_product_seo(product)
            results.append(result)
        
        # Агрегация
        total_score = sum(r['seo_score'] for r in results)
        avg_score = total_score / len(results) if results else 0
        
        # Распределение по уровням
        levels_count = {}
        for r in results:
            level = r['seo_level']
            levels_count[level] = levels_count.get(level, 0) + 1
        
        # Общие проблемы
        all_issues = []
        for r in results:
            all_issues.extend(r['issues'])
        
        # Подсчет частоты проблем
        from collections import Counter
        issues_counter = Counter(all_issues)
        common_issues = [issue for issue, count in issues_counter.most_common(5)]
        
        # Общие рекомендации
        all_recommendations = []
        for r in results:
            all_recommendations.extend(r['recommendations'])
        
        recommendations_counter = Counter(all_recommendations)
        top_recommendations = [rec for rec, count in recommendations_counter.most_common(5)]
        
        return {
            'total_products': len(results),
            'average_seo_score': round(avg_score, 2),
            'products_by_level': levels_count,
            'products_details': results,
            'common_issues': common_issues,
            'top_recommendations': top_recommendations
        }
    
    def get_seo_score_for_orders(self, orders: List[Dict]) -> Dict:
        """
        Получает SEO Score на основе данных заказов
        
        Args:
            orders: список заказов с информацией о товарах
        
        Returns:
            упрощенная оценка SEO на основе доступных данных
        """
        if not orders:
            return {'seo_score': 0, 'note': 'Нет данных о товарах'}
        
        df = pd.DataFrame(orders)
        
        # Анализируем доступные поля
        score = 0
        max_score = 100
        
        # Проверка наличия названий товаров (30 баллов)
        if 'product_name' in df.columns:
            has_names = df['product_name'].notna().sum()
            if has_names > 0:
                # Проверяем длину названий
                avg_name_length = df['product_name'].str.len().mean()
                if 30 <= avg_name_length <= 100:
                    score += 30
                elif avg_name_length > 0:
                    score += 20
        
        # Проверка наличия артикулов/SKU (10 баллов)
        if 'sku' in df.columns or 'article' in df.columns:
            score += 10
        
        # Проверка наличия описаний (если есть поле description)
        if 'description' in df.columns:
            has_desc = df['description'].notna().sum()
            if has_desc > 0:
                avg_desc_length = df['description'].str.len().mean()
                if avg_desc_length >= self.MIN_DESCRIPTION_LENGTH:
                    score += 30
                elif avg_desc_length >= 300:
                    score += 20
                else:
                    score += 10
        
        # Оценка на основе количества уникальных товаров (10 баллов)
        unique_products = df['sku'].nunique() if 'sku' in df.columns else 0
        if unique_products > 0:
            score += min(unique_products * 2, 10)
        
        # Остальные баллы (20) - требуют данных из кабинета или API
        # Можно добавить проверку через API или кабинет
        
        level = 'excellent' if score >= 80 else 'good' if score >= 60 else 'fair' if score >= 40 else 'poor'
        
        return {
            'seo_score': score,
            'seo_level': level,
            'note': 'Оценка на основе доступных данных. Для полной оценки нужны данные из кабинета Ozon или API.'
        }
