"""
Анализатор карточек товаров магазина Ozon
Собирает и анализирует данные по каждой карточке товара
"""
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime
import json
import re

from .seo_analyzer import SEOAnalyzer
from .review_analyzer import ReviewAnalyzer
import config


class ProductCardAnalyzer:
    """Анализатор карточек товаров"""
    
    def __init__(self):
        self.seo_analyzer = SEOAnalyzer()
        self.review_analyzer = ReviewAnalyzer()
        self.products_data = []
        self.orders_data = []
        self.store_data = {}
        self.ozon_api_client = None  # Будет инициализирован при необходимости
    
    def load_data(self, store_data=None, orders=None, ozon_api_client=None):
        """Загружает данные для анализа"""
        self.store_data = store_data or {}
        self.orders_data = orders or []
        self.ozon_api_client = ozon_api_client  # Сохраняем клиент API если доступен
        
        # Загружаем данные о товарах из разных источников
        self._load_products_from_store_data()
        self._load_products_from_brand_docs()
        self._enrich_with_orders_data()
        # Изображения и отзывы собираются по требованию, чтобы не блокировать запуск
    
    def _load_products_from_store_data(self):
        """Загружает товары из данных магазина"""
        products_info = self.store_data.get('products_info', {})
        products_list = products_info.get('products_list', [])
        
        # Если products_list содержит только строки (ID товаров), 
        # они будут загружены из brand_documentation в _load_products_from_brand_docs
        # Здесь обрабатываем только если это словари
        for product in products_list:
            if isinstance(product, dict):
                self.products_data.append(product)
    
    def _load_products_from_brand_docs(self):
        """Загружает товары из документации бренда"""
        try:
            if config.BRAND_DOCUMENTATION_PATH.exists():
                with open(config.BRAND_DOCUMENTATION_PATH, 'r', encoding='utf-8') as f:
                    brand_data = json.load(f)
                
                products = brand_data.get('products', {})
                for product_id, product_info in products.items():
                    # Получаем SKU из product_info
                    sku = str(product_info.get('sku', product_id))
                    
                    # Проверяем, нет ли уже этого товара
                    existing = next((
                        p for p in self.products_data 
                        if str(p.get('sku', '')) == sku or 
                           str(p.get('id', '')) == product_id or
                           str(p.get('id', '')) == sku
                    ), None)
                    
                    if not existing:
                        # Используем цену из price_range если есть
                        price = product_info.get('price')
                        if not price and 'price_range' in product_info:
                            price = product_info['price_range'].get('avg')
                        
                        product_data = {
                            'id': product_id,
                            'sku': sku,
                            'product_name': product_info.get('full_name') or product_info.get('name') or product_info.get('title'),
                            'name': product_info.get('name'),
                            'full_name': product_info.get('full_name'),
                            'description': product_info.get('description'),
                            'price': price,
                            'price_range': product_info.get('price_range'),
                            'category': product_info.get('category'),
                            'type': product_info.get('type'),
                            'article': product_info.get('article'),
                            'features': product_info.get('features', []),
                            'weight_kg': product_info.get('weight_kg'),
                            'brand': brand_data.get('seller_name'),
                            'image_url': product_info.get('image_url') or product_info.get('image') or product_info.get('first_image'),
                            'source': 'brand_documentation'
                        }
                        self.products_data.append(product_data)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Ошибка загрузки товаров из документации бренда: {e}")
    
    def _enrich_single_product_image(self, product):
        """Быстрое получение изображения для одного товара"""
        import requests
        from bs4 import BeautifulSoup
        
        if product.get('image_url'):
            return
        
        sku = product.get('sku')
        if not sku:
            return
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Referer': 'https://www.ozon.ru/',
        }
        
        try:
            # Быстрая проверка через og:image
            product_url = f"https://www.ozon.ru/product/{sku}/"
            response = requests.get(product_url, headers=headers, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                meta_image = soup.find('meta', property='og:image')
                if meta_image and meta_image.get('content'):
                    img_url = meta_image['content']
                    if img_url and img_url.startswith('http'):
                        if '?' in img_url:
                            img_url = img_url.split('?')[0]
                        product['image_url'] = img_url
        except:
            pass
    
    def _enrich_with_product_images(self):
        """Дополняет данные товаров изображениями из Ozon"""
        import requests
        from bs4 import BeautifulSoup
        import time
        
        print(f"Начинаю сбор изображений для {len(self.products_data)} товаров...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.ozon.ru/',
            'Cache-Control': 'no-cache',
        }
        
        for idx, product in enumerate(self.products_data):
            # Если изображение уже есть, пропускаем
            if product.get('image_url'):
                continue
            
            sku = product.get('sku')
            if not sku:
                continue
            
            # Небольшая задержка между запросами
            if idx > 0:
                time.sleep(0.3)
            
            print(f"Сбор изображения для SKU {sku} ({idx+1}/{len(self.products_data)})...")
            
            try:
                # Способ 0: Используем Ozon API если доступен (самый надежный)
                if self.ozon_api_client:
                    try:
                        # Получаем информацию о товаре через API (используем правильный endpoint)
                        status, api_response = self.ozon_api_client.request('POST', '/v3/product/info/list', {
                            'product_id': [],
                            'offer_id': [],
                            'sku': [int(sku)]
                        })
                        if api_response and 'result' in api_response:
                            items = api_response.get('result', {}).get('items', [])
                            if items and len(items) > 0:
                                item = items[0]
                                # Получаем изображения из API
                                images = item.get('images', []) or item.get('primary_image', []) or item.get('images360', [])
                                if images:
                                    if isinstance(images, list) and len(images) > 0:
                                        first_img = images[0]
                                        if isinstance(first_img, str):
                                            product['image_url'] = first_img
                                        elif isinstance(first_img, dict):
                                            product['image_url'] = first_img.get('url') or first_img.get('file_name') or first_img.get('image')
                                    elif isinstance(images, str):
                                        product['image_url'] = images
                                    if product.get('image_url'):
                                        print(f"✓ Изображение получено через API для SKU {sku}")
                                        continue
                    except Exception as e:
                        print(f"Ошибка получения изображения через API для SKU {sku}: {e}")
                
                # Способ 1: Парсинг страницы товара (fallback)
                product_url = f"https://www.ozon.ru/product/{sku}/"
                response = requests.get(product_url, headers=headers, timeout=15, allow_redirects=True)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 1. В meta тегах (Open Graph) - самый надежный способ
                    meta_image = soup.find('meta', property='og:image')
                    if meta_image and meta_image.get('content'):
                        img_url = meta_image['content']
                        if img_url and img_url.startswith('http'):
                            # Убираем параметры размера для получения оригинала
                            if '?' in img_url:
                                img_url = img_url.split('?')[0]
                            product['image_url'] = img_url
                            continue
                    
                    # 2. В JSON данных страницы
                    json_data = self._extract_json_from_page(response.text)
                    if json_data:
                        # Пробуем разные ключи для изображений
                        images = None
                        # Ищем вложенные структуры
                        if 'widgetStates' in json_data:
                            for key, value in json_data['widgetStates'].items():
                                if isinstance(value, str):
                                    try:
                                        widget_data = json.loads(value)
                                        if 'image' in widget_data or 'images' in widget_data:
                                            images = widget_data.get('images') or widget_data.get('image')
                                    except:
                                        pass
                        
                        if not images:
                            images = (json_data.get('images') or 
                                     json_data.get('imageUrls') or 
                                     json_data.get('productImages') or
                                     json_data.get('mainImage') or
                                     json_data.get('image'))
                        
                        if isinstance(images, list) and len(images) > 0:
                            first_img = images[0]
                            if isinstance(first_img, str):
                                product['image_url'] = first_img.split('?')[0] if '?' in first_img else first_img
                            elif isinstance(first_img, dict):
                                product['image_url'] = (first_img.get('url') or first_img.get('src') or first_img.get('image') or '').split('?')[0]
                            if product.get('image_url'):
                                continue
                        elif isinstance(images, str):
                            product['image_url'] = images.split('?')[0] if '?' in images else images
                            continue
                        elif isinstance(images, dict):
                            img_url = images.get('url') or images.get('src') or ''
                            if img_url:
                                product['image_url'] = img_url.split('?')[0] if '?' in img_url else img_url
                                continue
                    
                    # 3. В img тегах - ищем главное изображение товара
                    # Ищем в галерее или основном блоке изображений
                    gallery = soup.find(['div', 'section'], class_=re.compile(r'gallery|image|photo|media', re.I))
                    if gallery:
                        img_tags = gallery.find_all('img')
                    else:
                        img_tags = soup.find_all('img')
                    
                    for img in img_tags:
                        img_url = (img.get('data-src') or 
                                  img.get('src') or 
                                  img.get('data-lazy-src') or 
                                  img.get('data-original') or '')
                        
                        if img_url and img_url.startswith('http'):
                            # Пропускаем иконки, логотипы и маленькие изображения
                            skip_patterns = ['icon', 'logo', 'avatar', 'thumb', 'sprite', 'badge', 'star', 'rating']
                            if any(skip in img_url.lower() for skip in skip_patterns):
                                continue
                            
                            # Ищем изображения товара (обычно содержат SKU или product)
                            if ('cdn.ozon' in img_url or 'ozon.ru' in img_url or 'ozon' in img_url) and \
                               ('product' in img_url.lower() or sku in img_url or 'multimedia' in img_url or 'catalog' in img_url.lower()):
                                # Убираем параметры размера
                                if '?' in img_url:
                                    img_url = img_url.split('?')[0]
                                product['image_url'] = img_url
                                print(f"✓ Изображение получено из img тега для SKU {sku}")
                                break
                    
                    if product.get('image_url'):
                        continue
                
                # Способ 2: Прямой URL изображения Ozon (fallback)
                # Пробуем разные форматы CDN
                for format_pattern in [
                    f"https://cdn.ozon.ru/s3/multimedia-{sku[:2]}/images/{sku}.jpg",
                    f"https://cdn.ozon.ru/s3/multimedia-{sku[:3]}/images/{sku}.jpg",
                    f"https://cdn.ozon.ru/s3/multimedia-{sku[:1]}/images/{sku}.jpg",
                    f"https://cdn.ozon.ru/s3/multimedia-{sku}/images/{sku}.jpg",
                    f"https://cdn.ozon.ru/s3/multimedia-{sku[:4]}/images/{sku}.jpg",
                ]:
                    try:
                        head_response = requests.head(format_pattern, headers=headers, timeout=5, allow_redirects=True)
                        if head_response.status_code == 200:
                            product['image_url'] = format_pattern
                            print(f"✓ Изображение получено через CDN для SKU {sku}")
                            break
                    except:
                        continue
                        
            except Exception as e:
                # Если не удалось получить изображение, продолжаем
                print(f"Ошибка получения изображения для SKU {sku}: {e}")
                pass
    
    def _enrich_with_product_reviews(self):
        """Дополняет данные товаров отзывами из Ozon"""
        import requests
        from bs4 import BeautifulSoup
        import time
        
        print(f"Начинаю сбор отзывов для {len(self.products_data)} товаров...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.ozon.ru/',
        }
        
        for idx, product in enumerate(self.products_data):
            # Если отзывы уже есть, пропускаем
            if product.get('reviews_data') and product.get('reviews_data', {}).get('has_data'):
                continue
            
            sku = product.get('sku')
            if not sku:
                continue
            
            # Небольшая задержка между запросами
            if idx > 0:
                time.sleep(0.5)
            
            print(f"Сбор отзывов для SKU {sku} ({idx+1}/{len(self.products_data)})...")
            
            try:
                # Способ 0: Используем Ozon API если доступен (самый надежный)
                if self.ozon_api_client:
                    try:
                        # Получаем информацию о товаре через API (используем правильный endpoint)
                        status, api_response = self.ozon_api_client.request('POST', '/v3/product/info/list', {
                            'product_id': [],
                            'offer_id': [],
                            'sku': [int(sku)]
                        })
                        if api_response and 'result' in api_response:
                            items = api_response.get('result', {}).get('items', [])
                            if items and len(items) > 0:
                                item = items[0]
                                # Получаем рейтинг из API
                                rating = item.get('rating') or item.get('rating_value') or item.get('ratingValue')
                                # Получаем количество отзывов
                                reviews_count = item.get('reviews_count') or item.get('reviewsCount') or item.get('reviews')
                                
                                if rating or reviews_count:
                                    product['reviews_data'] = {
                                        'reviews': [],
                                        'total_reviews': int(reviews_count) if reviews_count else 0,
                                        'average_rating': float(rating) if rating else None,
                                        'has_data': True
                                    }
                                    print(f"✓ Данные об отзывах получены через API для SKU {sku}: рейтинг={rating}, отзывов={reviews_count}")
                                    continue
                    except Exception as e:
                        print(f"Ошибка получения отзывов через API для SKU {sku}: {e}")
                
                # Способ 1: Парсинг страницы товара (fallback)
                product_url = f"https://www.ozon.ru/product/{sku}/"
                response = requests.get(product_url, headers=headers, timeout=15, allow_redirects=True)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 1. Получаем рейтинг из HTML (более надежный способ)
                    rating = self._extract_rating_from_html(soup)
                    
                    # 2. Ищем отзывы в JSON данных страницы
                    json_data = self._extract_json_from_page(response.text)
                    reviews_data = []
                    
                    if json_data:
                        # Пробуем разные ключи для отзывов
                        reviews_data = (json_data.get('reviews') or 
                                       json_data.get('reviewsList') or 
                                       json_data.get('productReviews') or
                                       json_data.get('items') or [])
                        
                        # Получаем рейтинг из JSON если не нашли в HTML
                        if not rating:
                            rating = (json_data.get('rating') or 
                                     json_data.get('averageRating') or 
                                     json_data.get('productRating') or
                                     json_data.get('ratingValue'))
                    
                    # 3. Парсим отзывы из HTML если не нашли в JSON
                    if not reviews_data:
                        reviews_data = self._extract_reviews_from_html(soup)
                    
                    # 4. Получаем рейтинг из текста страницы если не нашли ранее
                    if not rating:
                        rating = self._extract_rating_from_text(response.text)
                    
                    # Сохраняем данные об отзывах
                    if reviews_data or rating:
                        total_reviews_count = len(reviews_data) if isinstance(reviews_data, list) else 0
                        # Если нашли рейтинг, но нет отзывов, все равно помечаем как есть данные
                        if rating and total_reviews_count == 0:
                            total_reviews_count = 1  # Минимальное значение для отображения
                        
                        product['reviews_data'] = {
                            'reviews': reviews_data[:10] if isinstance(reviews_data, list) else [],
                            'total_reviews': total_reviews_count,
                            'average_rating': float(rating) if rating else None,
                            'has_data': True
                        }
                        print(f"✓ Собраны данные для SKU {sku}: рейтинг={rating}, отзывов={total_reviews_count}")
                    else:
                        product['reviews_data'] = {
                            'reviews': [],
                            'total_reviews': 0,
                            'average_rating': None,
                            'has_data': False
                        }
                        print(f"✗ Не удалось собрать данные для SKU {sku}")
                        
            except Exception as e:
                print(f"Ошибка получения отзывов для SKU {sku}: {e}")
                import traceback
                traceback.print_exc()
                product['reviews_data'] = {
                    'reviews': [],
                    'total_reviews': 0,
                    'average_rating': None,
                    'has_data': False
                }
    
    def _extract_reviews_from_html(self, soup):
        """Извлекает отзывы из HTML страницы"""
        reviews = []
        try:
            # 1. Ищем блоки с отзывами по различным селекторам
            review_selectors = [
                {'class': re.compile(r'review|comment|feedback', re.I)},
                {'data-review-id': True},
                {'itemprop': 'review'},
                {'id': re.compile(r'review', re.I)},
            ]
            
            review_blocks = []
            for selector in review_selectors:
                blocks = soup.find_all(['div', 'article', 'section', 'li'], selector)
                review_blocks.extend(blocks)
            
            # Убираем дубликаты
            seen = set()
            unique_blocks = []
            for block in review_blocks:
                block_id = id(block)
                if block_id not in seen:
                    seen.add(block_id)
                    unique_blocks.append(block)
            
            for block in unique_blocks[:20]:  # Берем первые 20 отзывов
                review_data = {}
                
                # Извлекаем рейтинг
                rating_elem = (block.find(['span', 'div', 'meta'], 
                                         class_=re.compile(r'rating|star|score', re.I)) or
                              block.find(['span', 'div'], itemprop=re.compile(r'rating', re.I)) or
                              block.find(['span', 'div'], {'data-rating': True}))
                
                if rating_elem:
                    # Пробуем data-rating атрибут
                    rating_val = rating_elem.get('data-rating') or rating_elem.get('content')
                    if rating_val:
                        try:
                            review_data['rating'] = int(float(rating_val))
                        except:
                            pass
                    
                    # Пробуем текст
                    if 'rating' not in review_data:
                        rating_text = rating_elem.get_text(strip=True)
                        rating_match = re.search(r'(\d+)', rating_text)
                        if rating_match:
                            rating_num = int(rating_match.group(1))
                            if 1 <= rating_num <= 5:
                                review_data['rating'] = rating_num
                
                # Извлекаем текст отзыва
                text_elem = (block.find(['p', 'div', 'span'], 
                                       class_=re.compile(r'text|content|body|comment|review-text', re.I)) or
                            block.find(['p', 'div', 'span'], itemprop='reviewBody') or
                            block.find('p'))
                
                if text_elem:
                    text = text_elem.get_text(strip=True)
                    if text and len(text) > 10:  # Минимальная длина отзыва
                        review_data['text'] = text
                
                # Извлекаем автора
                author_elem = (block.find(['span', 'div', 'a'], 
                                        class_=re.compile(r'author|user|name|reviewer', re.I)) or
                              block.find(['span', 'div', 'a'], itemprop='author'))
                if author_elem:
                    author = author_elem.get_text(strip=True)
                    if author:
                        review_data['author'] = author
                
                # Извлекаем дату
                date_elem = (block.find(['time', 'span', 'div'], 
                                      class_=re.compile(r'date|time', re.I)) or
                            block.find(['time', 'span', 'div'], itemprop='datePublished'))
                if date_elem:
                    date_val = date_elem.get('datetime') or date_elem.get_text(strip=True)
                    if date_val:
                        review_data['date'] = date_val
                
                # Проверяем наличие фото
                photo_elem = block.find('img', class_=re.compile(r'review|photo|image', re.I))
                review_data['has_photo'] = photo_elem is not None
                
                # Добавляем отзыв если есть хотя бы текст или рейтинг
                if review_data.get('text') or review_data.get('rating'):
                    reviews.append(review_data)
        except Exception as e:
            print(f"Ошибка извлечения отзывов из HTML: {e}")
            import traceback
            traceback.print_exc()
        
        return reviews
    
    def _extract_rating_from_html(self, soup):
        """Извлекает рейтинг товара из HTML"""
        try:
            # 1. Ищем в meta тегах
            meta_rating = soup.find('meta', {'itemprop': 'ratingValue'})
            if meta_rating and meta_rating.get('content'):
                try:
                    return float(meta_rating['content'])
                except:
                    pass
            
            # 2. Ищем в различных элементах с классом rating
            rating_selectors = [
                ('span', {'class': re.compile(r'rating|star', re.I)}),
                ('div', {'class': re.compile(r'rating|star', re.I)}),
                ('span', {'itemprop': 'ratingValue'}),
                ('div', {'data-rating': True}),
                ('span', {'data-rating': True}),
            ]
            
            for tag, attrs in rating_selectors:
                elems = soup.find_all(tag, attrs)
                for elem in elems:
                    # Пробуем атрибут data-rating
                    if 'data-rating' in attrs:
                        rating_val = elem.get('data-rating')
                        if rating_val:
                            try:
                                return float(rating_val)
                            except:
                                pass
                    
                    # Пробуем content атрибут
                    rating_val = elem.get('content')
                    if rating_val:
                        try:
                            return float(rating_val)
                        except:
                            pass
                    
                    # Пробуем текст
                    rating_text = elem.get_text(strip=True)
                    if rating_text:
                        # Ищем число с точкой или запятой
                        match = re.search(r'(\d+[.,]\d+)', rating_text)
                        if match:
                            try:
                                return float(match.group(1).replace(',', '.'))
                            except:
                                pass
                        # Ищем просто число (может быть рейтинг из 5)
                        match = re.search(r'(\d+)', rating_text)
                        if match:
                            rating_num = int(match.group(1))
                            if 1 <= rating_num <= 5:
                                return float(rating_num)
            
            # 3. Ищем в тексте страницы
            text = soup.get_text()
            patterns = [
                r'рейтинг[:\s]+(\d+[.,]\d+)',
                r'rating[:\s]+(\d+[.,]\d+)',
                r'(\d+[.,]\d+)\s*из\s*5',
                r'(\d+[.,]\d+)\s*звезд',
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        return float(match.group(1).replace(',', '.'))
                    except:
                        continue
        except Exception as e:
            print(f"Ошибка извлечения рейтинга из HTML: {e}")
        
        return None
    
    def _extract_rating_from_text(self, page_text):
        """Извлекает рейтинг из текста страницы (fallback)"""
        try:
            # Ищем паттерны рейтинга в тексте
            patterns = [
                r'"rating":\s*(\d+[.,]\d+)',
                r'"averageRating":\s*(\d+[.,]\d+)',
                r'"productRating":\s*(\d+[.,]\d+)',
                r'rating[:\s]*(\d+[.,]\d+)',
                r'рейтинг[:\s]*(\d+[.,]\d+)',
            ]
            for pattern in patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    try:
                        return float(match.group(1).replace(',', '.'))
                    except:
                        continue
        except:
            pass
        return None
    
    def _extract_json_from_page(self, page_text):
        """Извлекает JSON данные из страницы"""
        import json
        import re
        
        # Ищем JSON в script тегах
        json_patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
            r'window\.__APP_DATA__\s*=\s*({.+?});',
            r'window\.__PRELOADED_STATE__\s*=\s*({.+?});',
            r'"product":\s*({.+?})',
            r'{"sku":\s*"(\d+)"[^}]*}',
            r'"rating":\s*(\d+[.,]\d+)',
            r'"reviews":\s*(\[.+?\])',
            r'"averageRating":\s*(\d+[.,]\d+)',
        ]
        
        # Также ищем в script тегах
        script_patterns = [
            r'<script[^>]*>.*?({.*?"rating".*?}).*?</script>',
            r'<script[^>]*>.*?({.*?"reviews".*?}).*?</script>',
            r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',
        ]
        
        all_patterns = json_patterns + script_patterns
        
        for pattern in all_patterns:
            matches = re.findall(pattern, page_text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    match_str = match if isinstance(match, str) else str(match)
                    # Пытаемся найти полный JSON объект
                    if match_str.startswith('{'):
                        data = json.loads(match_str)
                        if isinstance(data, dict):
                            # Проверяем наличие полезных данных
                            if any(key in data for key in ['images', 'imageUrls', 'sku', 'rating', 'reviews', 'productRating', 'averageRating']):
                                return data
                    elif match_str.startswith('['):
                        data = json.loads(match_str)
                        if isinstance(data, list) and len(data) > 0:
                            return {'reviews': data}
                except (json.JSONDecodeError, ValueError):
                    continue
        return None
    
    def _enrich_with_orders_data(self):
        """Дополняет данные товаров информацией из заказов"""
        if not self.orders_data:
            return
        
        df = pd.DataFrame(self.orders_data)
        
        # Группируем по SKU/артикулу
        if 'sku' in df.columns:
            sku_column = 'sku'
        elif 'article' in df.columns:
            sku_column = 'article'
        else:
            return
        
        # Агрегируем данные по товарам
        product_stats = df.groupby(sku_column).agg({
            'paid_by_customer': ['sum', 'mean', 'count'],
            'quantity': 'sum',
            'product_name': 'first',
            'seller_price': 'mean',
            'discount_percent': 'mean'
        }).reset_index()
        
        product_stats.columns = [
            'sku', 'total_revenue', 'avg_price', 'orders_count',
            'total_quantity', 'product_name', 'avg_seller_price', 'avg_discount'
        ]
        
        # Объединяем с существующими данными
        for _, row in product_stats.iterrows():
            sku = str(row['sku'])
            existing = next((p for p in self.products_data if str(p.get('sku', '')) == sku), None)
            
            if existing:
                # Дополняем существующие данные
                existing['sales_data'] = {
                    'total_revenue': float(row['total_revenue']),
                    'avg_price': float(row['avg_price']),
                    'orders_count': int(row['orders_count']),
                    'total_quantity': int(row['total_quantity']),
                    'avg_seller_price': float(row['avg_seller_price']),
                    'avg_discount': float(row['avg_discount'])
                }
                if not existing.get('product_name'):
                    existing['product_name'] = row['product_name']
            else:
                # Создаем новую запись
                self.products_data.append({
                    'sku': sku,
                    'product_name': row['product_name'],
                    'sales_data': {
                        'total_revenue': float(row['total_revenue']),
                        'avg_price': float(row['avg_price']),
                        'orders_count': int(row['orders_count']),
                        'total_quantity': int(row['total_quantity']),
                        'avg_seller_price': float(row['avg_seller_price']),
                        'avg_discount': float(row['avg_discount'])
                    },
                    'source': 'orders'
                })
    
    def analyze_product_card(self, product_data: Dict) -> Dict:
        """
        Анализирует одну карточку товара
        
        Args:
            product_data: данные о товаре
        
        Returns:
            полная сводка по карточке
        """
        sku = product_data.get('sku') or product_data.get('id', '')
        product_name = product_data.get('product_name') or product_data.get('name', '')
        
        # Подготавливаем данные для SEO анализа
        seo_product_data = {
            'sku': sku,
            'product_name': product_name,
            'title': product_data.get('full_name') or product_name,
            'description': product_data.get('description', ''),
            'characteristics': {
                'category': product_data.get('category'),
                'type': product_data.get('type'),
                'article': product_data.get('article'),
                'features': product_data.get('features', []),
                'weight_kg': product_data.get('weight_kg')
            }
        }
        
        # SEO анализ
        seo_analysis = self.seo_analyzer.analyze_product_seo(seo_product_data)
        
        # Анализ продаж (если есть данные)
        sales_analysis = self._analyze_sales(product_data)
        
        # Анализ отзывов (если есть данные)
        reviews_analysis = self._analyze_reviews_for_product(product_data)
        
        # Общая оценка карточки
        overall_score = self._calculate_overall_score(seo_analysis, sales_analysis, reviews_analysis)
        
        # Рекомендации
        recommendations = self._generate_product_recommendations(
            seo_analysis, sales_analysis, reviews_analysis, product_data
        )
        
        # Статус карточки
        status = self._determine_card_status(overall_score, seo_analysis, sales_analysis)
        
        # Получаем изображение из product_data
        image_url = product_data.get('image_url')
        # Если изображения нет, пытаемся получить его сейчас
        if not image_url:
            # Быстрая попытка получить изображение для этого конкретного товара
            try:
                self._enrich_single_product_image(product_data)
                image_url = product_data.get('image_url')
            except:
                pass
        
        return {
            'sku': sku,
            'product_name': product_name,
            'image_url': image_url,  # Добавляем URL изображения
            'overall_score': overall_score,
            'status': status,
            'seo_analysis': {
                'score': seo_analysis.get('seo_score', 0),
                'level': seo_analysis.get('seo_level', 'unknown'),
                'title_score': seo_analysis.get('title_score', 0),
                'description_score': seo_analysis.get('description_score', 0),
                'characteristics_score': seo_analysis.get('characteristics_score', 0),
                'media_score': seo_analysis.get('media_score', 0),
                'issues': seo_analysis.get('issues', []),
                'recommendations': seo_analysis.get('recommendations', [])
            },
            'sales_analysis': sales_analysis,
            'reviews_analysis': reviews_analysis,
            'recommendations': recommendations,
            'last_updated': datetime.now().isoformat()
        }
    
    def _analyze_sales(self, product_data: Dict) -> Dict:
        """Анализирует продажи товара"""
        sales_data = product_data.get('sales_data', {})
        
        if not sales_data:
            return {
                'has_data': False,
                'note': 'Нет данных о продажах. Загрузите отчеты Ozon для анализа продаж.'
            }
        
        total_revenue = sales_data.get('total_revenue', 0)
        orders_count = sales_data.get('orders_count', 0)
        avg_price = sales_data.get('avg_price', 0)
        total_quantity = sales_data.get('total_quantity', 0)
        avg_discount = sales_data.get('avg_discount', 0)
        
        # Оценка продаж
        sales_score = 0
        if total_revenue > 100000:
            sales_score = 100
        elif total_revenue > 50000:
            sales_score = 75
        elif total_revenue > 10000:
            sales_score = 50
        elif total_revenue > 0:
            sales_score = 25
        
        # Определение статуса продаж
        if total_revenue > 100000:
            sales_status = 'excellent'
        elif total_revenue > 50000:
            sales_status = 'good'
        elif total_revenue > 10000:
            sales_status = 'fair'
        elif total_revenue > 0:
            sales_status = 'poor'
        else:
            sales_status = 'no_sales'
        
        return {
            'has_data': True,
            'total_revenue': total_revenue,
            'orders_count': orders_count,
            'avg_price': avg_price,
            'total_quantity': total_quantity,
            'avg_discount': avg_discount,
            'sales_score': sales_score,
            'sales_status': sales_status
        }
    
    def _analyze_reviews_for_product(self, product_data: Dict) -> Dict:
        """Анализирует отзывы для товара"""
        # Используем данные об отзывах, собранные для товара
        reviews_data = product_data.get('reviews_data', {})
        
        if reviews_data and reviews_data.get('has_data'):
            # Используем собранные данные
            reviews_list = reviews_data.get('reviews', [])
            average_rating = reviews_data.get('average_rating')
            total_reviews = reviews_data.get('total_reviews', 0)
        else:
            # Fallback: получаем данные об отзывах из store_data
            reviews_info = self.store_data.get('reviews_info', {})
            rating_info = self.store_data.get('rating_info', {})
            
            # Пытаемся найти отзывы конкретного товара
            product_reviews = reviews_info.get('product_reviews', {}).get(
                product_data.get('sku', ''), []
            )
            
            reviews_list = product_reviews if isinstance(product_reviews, list) else []
            average_rating = rating_info.get('overall_rating')
            total_reviews = len(reviews_list) if reviews_list else reviews_info.get('total_reviews', 0)
        
        # Анализируем отзывы если они есть
        if reviews_list and len(reviews_list) > 0:
            review_analysis = self.review_analyzer.analyze_reviews(reviews_list)
            return {
                'has_data': True,
                'total_reviews': review_analysis.get('total_reviews', len(reviews_list)),
                'average_rating': review_analysis.get('average_rating') or average_rating,
                'response_rate': review_analysis.get('response_rate', 0),
                'photo_reviews_ratio': review_analysis.get('photo_reviews_ratio', 0),
                'sentiment_distribution': review_analysis.get('sentiment_distribution', {}),
                'recommendations': review_analysis.get('recommendations', [])
            }
        
        # Если есть только рейтинг без отзывов
        if average_rating:
            return {
                'has_data': True,
                'total_reviews': total_reviews,
                'average_rating': float(average_rating),
                'note': 'Доступен только рейтинг. Для детального анализа нужны отзывы товара.',
                'recommendations': []
            }
        
        # Если нет конкретных отзывов, используем общий рейтинг магазина
        rating_info = self.store_data.get('rating_info', {})
        overall_rating = rating_info.get('overall_rating')
        if overall_rating:
            return {
                'has_data': True,
                'average_rating': overall_rating,
                'note': 'Используется общий рейтинг магазина. Для детального анализа нужны отзывы конкретного товара.',
                'recommendations': []
            }
        
        return {
            'has_data': False,
            'note': 'Нет данных об отзывах. Используйте кабинет Ozon или API для получения отзывов товара.'
        }
    
    def _calculate_overall_score(
        self,
        seo_analysis: Dict,
        sales_analysis: Dict,
        reviews_analysis: Dict
    ) -> float:
        """Рассчитывает общий score карточки"""
        # Веса для разных компонентов
        seo_weight = 0.4  # SEO критично для ранжирования
        sales_weight = 0.3  # Продажи важны
        reviews_weight = 0.3  # Отзывы критично для ранжирования
        
        seo_score = seo_analysis.get('seo_score', 0)
        
        sales_score = sales_analysis.get('sales_score', 0) if sales_analysis.get('has_data') else 50
        # Если нет продаж, снижаем оценку
        if not sales_analysis.get('has_data'):
            sales_score = 30
        
        # Оценка отзывов
        if reviews_analysis.get('has_data'):
            avg_rating = reviews_analysis.get('average_rating', 0) or 0
            if avg_rating > 0:
                reviews_score = (avg_rating / 5.0) * 100
            else:
                reviews_score = 50
        else:
            reviews_score = 40  # Нет данных об отзывах - снижаем оценку
        
        overall = (
            seo_score * seo_weight +
            sales_score * sales_weight +
            reviews_score * reviews_weight
        )
        
        return round(overall, 2)
    
    def _generate_product_recommendations(
        self,
        seo_analysis: Dict,
        sales_analysis: Dict,
        reviews_analysis: Dict,
        product_data: Dict
    ) -> List[Dict]:
        """Генерирует рекомендации для товара"""
        recommendations = []
        
        # SEO рекомендации
        seo_score = seo_analysis.get('seo_score', 0)
        if seo_score < 60:
            recommendations.append({
                'category': 'SEO',
                'priority': 'critical',
                'title': 'Критично: Низкий SEO Score',
                'description': f'SEO Score: {seo_score}/100. Карточка не оптимизирована для нового алгоритма Ozon 2025.',
                'actions': seo_analysis.get('recommendations', [])[:3]
            })
        
        # Рекомендации по продажам
        if sales_analysis.get('has_data'):
            total_revenue = sales_analysis.get('total_revenue', 0)
            if total_revenue == 0:
                recommendations.append({
                    'category': 'Продажи',
                    'priority': 'high',
                    'title': 'Нет продаж',
                    'description': 'Товар не продается. Требуется анализ причин.',
                    'actions': [
                        'Проверьте цену - возможно, она слишком высокая',
                        'Улучшите SEO карточки для попадания в поиск',
                        'Добавьте отзывы и рейтинг',
                        'Используйте рекламу для продвижения'
                    ]
                })
            elif total_revenue < 10000:
                recommendations.append({
                    'category': 'Продажи',
                    'priority': 'medium',
                    'title': 'Низкие продажи',
                    'description': f'Выручка: {total_revenue:,.0f} руб. Можно улучшить.',
                    'actions': [
                        'Улучшите SEO для увеличения видимости',
                        'Оптимизируйте цену',
                        'Добавьте больше отзывов',
                        'Используйте рекламу'
                    ]
                })
        
        # Рекомендации по отзывам
        if reviews_analysis.get('has_data'):
            avg_rating = reviews_analysis.get('average_rating', 0) or 0
            if avg_rating < 4.7:
                recommendations.append({
                    'category': 'Отзывы',
                    'priority': 'high',
                    'title': 'Низкий рейтинг',
                    'description': f'Рейтинг: {avg_rating:.2f}/5.0. Для попадания в топ нужен рейтинг 4.7+.',
                    'actions': [
                        'Проанализируйте негативные отзывы',
                        'Улучшите качество товара',
                        'Отвечайте на все отзывы',
                        'Просите довольных покупателей оставлять отзывы'
                    ]
                })
        else:
            recommendations.append({
                'category': 'Отзывы',
                'priority': 'medium',
                'title': 'Нет данных об отзывах',
                'description': 'Отзывы критически важны для ранжирования в новом алгоритме.',
                'actions': [
                    'Просите покупателей оставлять отзывы',
                    'Стимулируйте отзывы с фотографиями',
                    'Отвечайте на все отзывы быстро'
                ]
            })
        
        return recommendations
    
    def _determine_card_status(
        self,
        overall_score: float,
        seo_analysis: Dict,
        sales_analysis: Dict
    ) -> str:
        """Определяет статус карточки"""
        if overall_score >= 80:
            return 'excellent'
        elif overall_score >= 60:
            return 'good'
        elif overall_score >= 40:
            return 'needs_improvement'
        else:
            return 'critical'
    
    def analyze_all_products(self) -> Dict:
        """
        Анализирует все карточки товаров
        
        Returns:
            сводка по всем карточкам
        """
        # Собираем изображения и отзывы перед анализом (если еще не собраны)
        self._enrich_with_product_images()  # Получаем изображения товаров
        self._enrich_with_product_reviews()  # Получаем отзывы товаров
        if not self.products_data:
            return {
                'total_products': 0,
                'products': [],
                'summary': {},
                'note': 'Нет данных о товарах. Загрузите данные магазина или отчеты Ozon.'
            }
        
        analyzed_products = []
        total = len(self.products_data)
        for idx, product in enumerate(self.products_data, 1):
            print(f"Анализ карточки {idx}/{total}: SKU {product.get('sku', 'unknown')}")
            analysis = self.analyze_product_card(product)
            analyzed_products.append(analysis)
        
        # Сводная статистика
        total_products = len(analyzed_products)
        avg_score = sum(p['overall_score'] for p in analyzed_products) / total_products if total_products > 0 else 0
        
        # Распределение по статусам
        status_distribution = {}
        for product in analyzed_products:
            status = product['status']
            status_distribution[status] = status_distribution.get(status, 0) + 1
        
        # Распределение по SEO уровням
        seo_levels = {}
        for product in analyzed_products:
            seo_level = product['seo_analysis']['level']
            seo_levels[seo_level] = seo_levels.get(seo_level, 0) + 1
        
        # Топ проблем
        all_issues = []
        for product in analyzed_products:
            all_issues.extend(product['seo_analysis']['issues'])
        
        from collections import Counter
        top_issues = [issue for issue, count in Counter(all_issues).most_common(5)]
        
        return {
            'total_products': total_products,
            'average_score': round(avg_score, 2),
            'products': analyzed_products,
            'summary': {
                'status_distribution': status_distribution,
                'seo_levels_distribution': seo_levels,
                'top_issues': top_issues
            }
        }
    
    def get_product_summary(self, sku: str) -> Optional[Dict]:
        """
        Получает сводку по конкретному товару
        
        Args:
            sku: SKU или ID товара
        
        Returns:
            сводка по товару или None если не найден
        """
        product = next(
            (p for p in self.products_data if str(p.get('sku', '')) == str(sku) or str(p.get('id', '')) == str(sku)),
            None
        )
        
        if not product:
            return None
        
        return self.analyze_product_card(product)
