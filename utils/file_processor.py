"""
Утилита для обработки файлов из папки upload
"""
import json
import os
import math
from datetime import datetime

from parsers.ozon_parser import OzonReportParser
from analytics.ozon_analytics import OzonAnalytics
from recommendations.ozon_recommendations import OzonRecommendations

import config


def _sanitize_value(obj):
    """Рекурсивно очищает объект от NaN/Infinity для валидного JSON."""
    if isinstance(obj, dict):
        return {k: _sanitize_value(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_value(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    return obj


class FileProcessor:
    """Обработчик файлов отчетов"""
    
    def __init__(self):
        self.parser = OzonReportParser()
        self.analytics = OzonAnalytics()
        self.recommendations = OzonRecommendations()
        self.processed_files = []
        self.data_file = str(config.PROCESSED_DATA_FILE)
        
        config.ensure_dirs()
        self._load_data()
    
    def process_file(self, filepath):
        """Обрабатывает один файл"""
        try:
            result = self.parser.parse_file(filepath)
            self.analytics.load_data(self.parser.get_parsed_data())
            self.recommendations.set_analytics(self.analytics)
            self._save_data()
            file_info = {
                'filename': os.path.basename(filepath),
                'type': result['type'],
                'count': result['count'],
                'processed_at': datetime.now().isoformat()
            }
            self.processed_files.append(file_info)
            return {'file': file_info, 'parsed': result}
        except Exception as e:
            raise Exception(f"Ошибка обработки файла {filepath}: {str(e)}")
    
    def _clear_before_process_folder(self):
        """Очищает parsed_data и processed_files перед обработкой папки (избегаем дублей)."""
        # Убедимся что все необходимые ключи существуют
        required_keys = ['orders', 'returns', 'stocks', 'accruals', 'unit_economics', 
                        'sales_analytics_period', 'sales_analytics_daily', 
                        'finance', 'postings_fbo', 'postings_fbs']
        for key in required_keys:
            self.parser.parsed_data[key] = []
        self.processed_files = []

    def process_folder(self, folder_path):
        """Обрабатывает все файлы из папки"""
        results = []
        
        folder = str(folder_path)
        if not os.path.exists(folder):
            return results
        
        self._clear_before_process_folder()
        
        files = [f for f in os.listdir(folder) 
                if f.endswith(('.csv', '.xlsx', '.xls', '.json'))]
        
        for filename in files:
            filepath = os.path.join(folder, filename)
            try:
                result = self.process_file(filepath)
                results.append(result)
            except Exception as e:
                print(f"Ошибка обработки {filename}: {e}")
                results.append({
                    'file': filename,
                    'error': str(e)
                })
        
        return results
    
    def get_processed_reports(self):
        """Возвращает список обработанных отчетов"""
        return self.processed_files
    
    def _save_data(self):
        """Сохраняет обработанные данные"""
        try:
            data = {
                'parsed_data': self.parser.get_parsed_data(),
                'processed_files': self.processed_files,
                'last_update': datetime.now().isoformat()
            }
            
            # Очищаем от NaN/Infinity и конвертируем даты
            data = _sanitize_value(data)
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения данных: {e}")
    
    def _load_data(self):
        """Загружает ранее обработанные данные"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Восстанавливаем данные парсера
                    if 'parsed_data' in data:
                        loaded_data = data['parsed_data']
                        # Добавляем отсутствующие ключи из текущей структуры
                        for key in self.parser.parsed_data:
                            if key not in loaded_data:
                                loaded_data[key] = []
                        self.parser.parsed_data = loaded_data
                    
                    # Восстанавливаем список файлов
                    if 'processed_files' in data:
                        self.processed_files = data['processed_files']
                    
                    # Загружаем данные в аналитику
                    self.analytics.load_data(self.parser.get_parsed_data())
                    self.recommendations.set_analytics(self.analytics)
        except Exception as e:
            print(f"Ошибка загрузки данных: {e}")
