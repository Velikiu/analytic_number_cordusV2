"""
Модуль для сбора данных с магазина Ozon
Собирает информацию о рейтинге, отзывах, товарах, конкурентах.
Fallback — brand_documentation; не используется неофициальный API.
"""
import json
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

import config


class OzonStoreCollector:
    """Сборщик данных с магазина Ozon"""
    
    def __init__(self, seller_id=None, seller_url=None):
        """
        Инициализация сборщика
        
        Args:
            seller_id: ID продавца (например, 2479303)
            seller_url: URL страницы продавца
        """
        self.seller_id = seller_id
        self.seller_url = seller_url
        
        # Извлекаем ID из URL если передан URL
        if seller_url and not seller_id:
            self.seller_id = self._extract_seller_id_from_url(seller_url)
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        self.collected_data = {}
    
    def _extract_seller_id_from_url(self, url):
        """Извлекает ID продавца из URL"""
        # Пример: https://www.ozon.ru/seller/cordus-sacrus-metodika-neyrofiziologa-koryukalova-2479303/
        match = re.search(r'-(\d+)/?$', url)
        if match:
            return match.group(1)
        return None
    
    def collect_all(self):
        """Собирает всю доступную информацию о магазине"""
        if not self.seller_id:
            raise ValueError("Не указан seller_id или seller_url")
        
        print(f"Начинаю сбор данных для продавца {self.seller_id}...")
        
        # Собираем данные с обработкой ошибок
        try:
            seller_info = self.collect_seller_info()
        except Exception as e:
            print(f"Ошибка сбора seller_info: {e}")
            seller_info = self._get_fallback_seller_info()
        
        try:
            products_info = self.collect_products_info()
        except Exception as e:
            print(f"Ошибка сбора products_info: {e}")
            products_info = self._get_products_from_brand_docs()
        
        try:
            reviews_info = self.collect_reviews_info()
        except Exception as e:
            print(f"Ошибка сбора reviews_info: {e}")
            reviews_info = {'total_reviews': None, 'note': 'Ошибка сбора данных'}
        
        try:
            rating_info = self.collect_rating_info()
        except Exception as e:
            print(f"Ошибка сбора rating_info: {e}")
            rating_info = {'overall_rating': None, 'note': 'Ошибка сбора данных'}
        
        try:
            competitors_info = self.collect_competitors_info()
        except Exception as e:
            print(f"Ошибка сбора competitors_info: {e}")
            competitors_info = {'note': 'Анализ конкурентов требует дополнительной реализации'}
        
        # Собираем данные
        self.collected_data = {
            'seller_id': self.seller_id,
            'seller_url': self.seller_url or f"https://www.ozon.ru/seller/{self.seller_id}/",
            'collected_at': datetime.now().isoformat(),
            'seller_info': seller_info,
            'products_info': products_info,
            'reviews_info': reviews_info,
            'rating_info': rating_info,
            'competitors_info': competitors_info,
            'collection_method': 'web_scraping_with_fallback',
            'note': 'Часть данных получена из документации бренда. Для полных данных используйте отчеты Ozon или API.'
        }
        
        return self.collected_data
    
    def _default_name(self):
        return config.get_brand_defaults().get('seller_name') or '—'

    def collect_seller_info(self):
        """Собирает базовую информацию о продавце (парсинг страницы или fallback из бренда)."""
        try:
            url = self.seller_url or f"https://www.ozon.ru/seller/{self.seller_id}/"
            response = requests.get(url, headers=self.headers, timeout=15, allow_redirects=True)
            response.raise_for_status()
            page_text = response.text
            json_data = self._extract_json_from_page(page_text)
            if json_data:
                return {
                    'name': json_data.get('sellerName') or json_data.get('name') or self._default_name(),
                    'rating': json_data.get('rating') or json_data.get('sellerRating'),
                    'reviews_count': json_data.get('reviewsCount') or json_data.get('reviews_count'),
                    'products_count': json_data.get('productsCount') or json_data.get('products_count'),
                    'since_date': json_data.get('sinceDate') or json_data.get('since_date'),
                    'description': json_data.get('description')
                }
            soup = BeautifulSoup(response.text, 'html.parser')
            return {
                'name': self._extract_seller_name(soup) or self._default_name(),
                'rating': self._extract_rating(soup),
                'reviews_count': self._extract_reviews_count(soup),
                'products_count': self._extract_products_count(soup),
                'since_date': self._extract_since_date(soup),
                'description': self._extract_description(soup)
            }
        except requests.exceptions.RequestException as e:
            print(f"Ошибка сети при сборе информации о продавце: {e}")
            return self._get_fallback_seller_info()
        except Exception as e:
            print(f"Ошибка при сборе информации о продавце: {e}")
            return self._get_fallback_seller_info()
    
    def _extract_json_from_page(self, page_text):
        """Извлекает JSON данные из страницы"""
        try:
            # Ищем JSON в script тегах
            import json as json_lib
            from bs4 import BeautifulSoup
            
            # 1. Ищем в script тегах с type="application/json"
            soup = BeautifulSoup(page_text, 'html.parser')
            json_scripts = soup.find_all('script', type='application/json')
            for script in json_scripts:
                try:
                    data = json_lib.loads(script.string)
                    if isinstance(data, dict) and any(key in data for key in ['reviews', 'rating', 'sellerInfo', 'reviewsCount', 'reviewsList']):
                        return data
                except:
                    continue
            
            # 2. Ищем в window переменных
            patterns = [
                r'window\.__APP_DATA__\s*=\s*({.+?});',
                r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
                r'window\.__PRELOADED_STATE__\s*=\s*({.+?});',
                r'"sellerInfo":\s*({.+?})',
                r'sellerData:\s*({.+?})',
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, page_text, re.DOTALL)
                for match in matches:
                    try:
                        data = json_lib.loads(match.group(1))
                        if isinstance(data, dict) and any(key in data for key in ['reviews', 'rating', 'sellerInfo', 'reviewsCount', 'reviewsList']):
                            return data
                    except (json_lib.JSONDecodeError, TypeError):
                        continue
            
            # 3. Ищем простые JSON объекты с ключевыми словами
            json_matches = re.findall(r'\{[^{}]*"(?:seller|rating|reviews)"[^{}]*\}', page_text)
            for match in json_matches:
                try:
                    data = json_lib.loads(match)
                    if isinstance(data, dict) and ('seller' in data or 'rating' in data or 'reviews' in data):
                        return data
                except (json_lib.JSONDecodeError, TypeError):
                    continue
            return None
        except Exception as e:
            print(f"Ошибка извлечения JSON: {e}")
            return None
    
    def _get_fallback_seller_info(self):
        """Возвращает базовую информацию из документации бренда"""
        brand = config.get_brand_defaults()
        try:
            if config.BRAND_DOCUMENTATION_PATH.exists():
                with open(config.BRAND_DOCUMENTATION_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                products = data.get('products') or {}
                return {
                    'name': data.get('seller_name') or brand.get('seller_name') or '—',
                    'rating': None,
                    'reviews_count': None,
                    'products_count': len(products),
                    'since_date': None,
                    'description': data.get('description', ''),
                    'note': 'Данные получены из документации бренда. Для актуальных данных нужен кабинет Ozon или Seller API.'
                }
        except (OSError, json.JSONDecodeError):
            pass
        return {
            'name': brand.get('seller_name') or '—',
            'rating': None,
            'reviews_count': None,
            'products_count': brand.get('products_count') or 0,
            'since_date': None,
            'description': '',
            'note': 'Используйте отчеты Ozon или Seller API для актуальной информации.'
        }
    
    def collect_products_info(self):
        """Собирает информацию о товарах"""
        try:
            # Используем данные из документации бренда
            return self._get_products_from_brand_docs()
        except Exception as e:
            print(f"Ошибка при сборе информации о товарах: {e}")
            return self._get_products_from_brand_docs()
    
    def _get_products_from_brand_docs(self):
        """Получает информацию о товарах из документации бренда"""
        brand = config.get_brand_defaults()
        try:
            if config.BRAND_DOCUMENTATION_PATH.exists():
                with open(config.BRAND_DOCUMENTATION_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                products = data.get('products') or {}
                sets = data.get('product_sets') or {}
                
                # Преобразуем в детальный список карточек
                products_cards = []
                for product_id, product_info in products.items():
                    card = {
                        'id': product_id,
                        'sku': str(product_info.get('sku', product_id)),
                        'product_name': product_info.get('full_name') or product_info.get('name', ''),
                        'name': product_info.get('name', ''),
                        'full_name': product_info.get('full_name', ''),
                        'description': product_info.get('description', ''),
                        'category': product_info.get('category', ''),
                        'type': product_info.get('type', ''),
                        'article': product_info.get('article', ''),
                        'price_range': product_info.get('price_range', {}),
                        'features': product_info.get('features', []),
                        'weight_kg': product_info.get('weight_kg'),
                        'source': 'brand_documentation'
                    }
                    products_cards.append(card)
                
                return {
                    'total_products': len(products),
                    'products_list': list(products.keys()),
                    'products_cards': products_cards,  # Детальные данные карточек
                    'product_sets': list(sets.keys()),
                    'note': 'Данные из документации бренда. Для актуальных данных используйте отчеты Ozon.'
                }
        except (OSError, json.JSONDecodeError) as e:
            print(f"Ошибка загрузки товаров из документации: {e}")
        
        return {
            'total_products': brand.get('products_count') or 0,
            'products_list': [],
            'products_cards': [],
            'product_sets': [],
            'note': 'Используйте отчеты Ozon для актуальной информации.'
        }
    
    def collect_reviews_info(self):
        """Собирает информацию об отзывах"""
        try:
            # Пытаемся получить через API или парсинг
            url = self.seller_url or f"https://www.ozon.ru/seller/{self.seller_id}/"
            response = requests.get(url, headers=self.headers, timeout=15, allow_redirects=True)
            
            page_text = response.text
            json_data = self._extract_json_from_page(page_text)
            
            if json_data:
                return {
                    'total_reviews': json_data.get('reviewsCount') or json_data.get('reviews_count'),
                    'rating_distribution': {},
                    'recent_reviews': [],
                    'note': 'Данные извлечены из страницы'
                }
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            recent_reviews = self._extract_recent_reviews(soup)
            
            info = {
                'total_reviews': self._extract_reviews_count(soup),
                'rating_distribution': self._extract_rating_distribution(soup),
                'recent_reviews': recent_reviews,
                'reviews_parsed': len(recent_reviews) > 0
            }
            
            return info
        except Exception as e:
            print(f"Ошибка при сборе информации об отзывах: {e}")
            return {
                'total_reviews': None,
                'rating_distribution': {},
                'recent_reviews': [],
                'note': 'Для получения данных об отзывах используйте отчеты Ozon или кабинет продавца'
            }
    
    def collect_rating_info(self):
        """Собирает информацию о рейтинге"""
        try:
            url = self.seller_url or f"https://www.ozon.ru/seller/{self.seller_id}/"
            response = requests.get(url, headers=self.headers, timeout=15, allow_redirects=True)
            
            page_text = response.text
            json_data = self._extract_json_from_page(page_text)
            
            if json_data:
                rating = json_data.get('rating') or json_data.get('sellerRating')
                return {
                    'overall_rating': float(rating) if rating else None,
                    'rating_breakdown': {},
                    'rating_trend': {},
                    'note': 'Данные извлечены из страницы'
                }
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            rating = self._extract_rating(soup)
            
            info = {
                'overall_rating': float(rating) if rating else None,
                'rating_breakdown': self._extract_rating_breakdown(soup),
                'rating_trend': self._extract_rating_trend(soup)
            }
            
            return info
        except Exception as e:
            print(f"Ошибка при сборе информации о рейтинге: {e}")
            return {
                'overall_rating': None,
                'rating_breakdown': {},
                'rating_trend': {},
                'note': 'Для получения рейтинга используйте кабинет продавца Ozon'
            }
    
    def collect_competitors_info(self):
        """Собирает информацию о конкурентах (базовая реализация)"""
        # Это можно расширить для анализа конкурентов
        return {
            'note': 'Анализ конкурентов требует дополнительной реализации',
            'suggested_actions': [
                'Используйте Ozon Seller API для получения данных о конкурентах',
                'Анализируйте топ-10 товаров в вашей категории',
                'Сравните цены и характеристики с конкурентами'
            ]
        }
    
    # Методы извлечения данных из HTML
    
    def _extract_seller_name(self, soup):
        """Извлекает название продавца"""
        try:
            # Ищем название в различных местах
            name_selectors = [
                'h1',
                '[data-widget="sellerName"]',
                '.seller-name',
                'title'
            ]
            
            for selector in name_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if text and len(text) > 3:
                        return text
            
            # Пытаемся извлечь из title
            title = soup.find('title')
            if title:
                return title.get_text(strip=True).split('—')[0].strip()
            
            return "Не удалось определить"
        except (AttributeError, TypeError, ValueError):
            return "Не удалось определить"

    def _extract_rating(self, soup):
        """Извлекает рейтинг продавца"""
        try:
            # Ищем рейтинг в различных форматах
            rating_selectors = [
                '[data-widget="sellerRating"]',
                '.seller-rating',
                '[itemprop="ratingValue"]',
                '.rating-value'
            ]
            
            for selector in rating_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    # Ищем число с точкой
                    match = re.search(r'(\d+[.,]\d+)', text)
                    if match:
                        return float(match.group(1).replace(',', '.'))
            
            # Ищем в тексте страницы
            text = soup.get_text()
            match = re.search(r'рейтинг[:\s]+(\d+[.,]\d+)', text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(',', '.'))
            
            return None
        except (AttributeError, TypeError, ValueError):
            return None

    def _extract_reviews_count(self, soup):
        """Извлекает количество отзывов"""
        try:
            text = soup.get_text()
            # Ищем паттерны типа "1234 отзывов"
            patterns = [
                r'(\d+)\s+отзыв',
                r'отзыв[ов]*[:\s]+(\d+)',
                r'(\d+)\s+review'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return int(match.group(1))
            
            return None
        except (AttributeError, TypeError, ValueError):
            return None

    def _extract_products_count(self, soup):
        """Извлекает количество товаров"""
        try:
            text = soup.get_text()
            patterns = [
                r'(\d+)\s+товар',
                r'товар[ов]*[:\s]+(\d+)',
                r'(\d+)\s+product'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return int(match.group(1))
            
            return None
        except (AttributeError, TypeError, ValueError):
            return None

    def _extract_since_date(self, soup):
        """Извлекает дату регистрации продавца"""
        try:
            text = soup.get_text()
            # Ищем паттерны типа "на Ozon с 2020"
            match = re.search(r'на\s+Ozon\s+с\s+(\d{4})', text, re.IGNORECASE)
            if match:
                return match.group(1)
            return None
        except (AttributeError, TypeError, ValueError):
            return None

    def _extract_description(self, soup):
        """Извлекает описание продавца"""
        try:
            desc_selectors = [
                '[data-widget="sellerDescription"]',
                '.seller-description',
                '[itemprop="description"]'
            ]
            
            for selector in desc_selectors:
                element = soup.select_one(selector)
                if element:
                    return element.get_text(strip=True)
            
            return None
        except (AttributeError, TypeError, ValueError):
            return None

    def _extract_top_products(self, soup):
        """Извлекает топ товары"""
        # Базовая реализация - можно расширить
        return []
    
    def _extract_categories(self, soup):
        """Извлекает категории товаров"""
        # Базовая реализация - можно расширить
        return []
    
    def _extract_rating_distribution(self, soup):
        """Извлекает распределение рейтингов"""
        # Базовая реализация
        return {}
    
    def _extract_recent_reviews(self, soup):
        """Извлекает последние отзывы"""
        reviews = []
        try:
            # 1. Пытаемся найти отзывы в JSON данных (более надежно)
            page_text = str(soup)
            json_data = self._extract_json_from_page(page_text)
            if json_data:
                reviews_data = (json_data.get('reviews') or 
                               json_data.get('reviewsList') or 
                               json_data.get('items') or [])
                if isinstance(reviews_data, list) and len(reviews_data) > 0:
                    for review in reviews_data[:10]:
                        if isinstance(review, dict):
                            reviews.append({
                                'rating': review.get('rating') or review.get('score') or review.get('stars'),
                                'text': review.get('text') or review.get('comment') or review.get('content') or review.get('message'),
                                'author': review.get('author') or review.get('userName') or review.get('name') or review.get('user'),
                                'date': review.get('date') or review.get('createdAt') or review.get('publishedAt') or review.get('time'),
                                'has_photo': bool(review.get('photos') or review.get('images') or review.get('hasPhoto'))
                            })
                    if reviews:
                        return reviews
            
            # 2. Ищем отзывы в HTML (fallback)
            review_selectors = [
                {'class': re.compile(r'review|comment|feedback', re.I)},
                {'data-review-id': True},
                {'itemprop': 'review'},
            ]
            
            review_blocks = []
            for selector in review_selectors:
                blocks = soup.find_all(['div', 'article', 'li'], selector)
                review_blocks.extend(blocks)
            
            # Убираем дубликаты
            seen = set()
            unique_blocks = []
            for block in review_blocks:
                block_id = id(block)
                if block_id not in seen:
                    seen.add(block_id)
                    unique_blocks.append(block)
            
            for block in unique_blocks[:10]:  # Берем первые 10 отзывов
                review_data = {}
                
                # Извлекаем рейтинг
                rating_elem = (block.find(['span', 'div'], class_=re.compile(r'rating|star|score', re.I)) or
                              block.find(['span', 'div'], {'data-rating': True}))
                if rating_elem:
                    rating_val = rating_elem.get('data-rating') or rating_elem.get('content')
                    if rating_val:
                        try:
                            review_data['rating'] = int(float(rating_val))
                        except:
                            pass
                    if 'rating' not in review_data:
                        rating_text = rating_elem.get_text(strip=True)
                        rating_match = re.search(r'(\d+)', rating_text)
                        if rating_match:
                            rating_num = int(rating_match.group(1))
                            if 1 <= rating_num <= 5:
                                review_data['rating'] = rating_num
                
                # Извлекаем текст отзыва
                text_elem = (block.find(['p', 'div', 'span'], 
                                       class_=re.compile(r'text|content|body|comment', re.I)) or
                            block.find('p'))
                if text_elem:
                    text = text_elem.get_text(strip=True)
                    if text and len(text) > 10:
                        review_data['text'] = text
                
                # Извлекаем автора
                author_elem = block.find(['span', 'div', 'a'], class_=re.compile(r'author|user|name', re.I))
                if author_elem:
                    author = author_elem.get_text(strip=True)
                    if author:
                        review_data['author'] = author
                
                # Извлекаем дату
                date_elem = block.find(['time', 'span', 'div'], class_=re.compile(r'date|time', re.I))
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
            print(f"Ошибка извлечения отзывов: {e}")
            import traceback
            traceback.print_exc()
        
        return reviews
    
    def _extract_rating_breakdown(self, soup):
        """Извлекает детализацию рейтинга"""
        # Базовая реализация
        return {}
    
    def _extract_rating_trend(self, soup):
        """Извлекает тренд рейтинга"""
        # Базовая реализация
        return {}
    
    def get_collected_data(self):
        """Возвращает собранные данные"""
        return self.collected_data
    
    def save_to_file(self, filepath=None):
        """Сохраняет собранные данные в файл"""
        path = filepath or str(config.STORE_DATA_FILE)
        config.ensure_dirs()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.collected_data, f, ensure_ascii=False, indent=2)
        print(f"Данные сохранены в {path}")
