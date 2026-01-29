"""
Модуль для управления себестоимостью товаров по SKU
Позволяет сохранять, загружать и обновлять себестоимость для расчета юнит-экономики
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


class UnitEconomicsManager:
    """Менеджер для управления себестоимостью товаров"""
    
    def __init__(self, data_file: Optional[Path] = None):
        """
        Инициализация менеджера
        
        Args:
            data_file: Путь к файлу для хранения данных. Если None, используется дефолтный путь.
        """
        if data_file is None:
            # Используем папку data для хранения себестоимости
            data_dir = Path(__file__).parent.parent / 'data'
            data_dir.mkdir(exist_ok=True)
            data_file = data_dir / 'unit_economics.json'
        
        self.data_file = Path(data_file)
        self._costs: Dict[str, float] = {}
        self._load_costs()
    
    def _load_costs(self):
        """Загружает себестоимость из файла"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Поддерживаем старый формат (просто словарь) и новый (с метаданными)
                    if isinstance(data, dict):
                        if 'costs' in data:
                            # Новый формат с метаданными
                            self._costs = data.get('costs', {})
                            self._metadata = data.get('metadata', {})
                        else:
                            # Старый формат - просто словарь себестоимости
                            self._costs = data
                            self._metadata = {}
                    else:
                        self._costs = {}
                        self._metadata = {}
            except (json.JSONDecodeError, IOError) as e:
                print(f"Ошибка загрузки себестоимости: {e}")
                self._costs = {}
                self._metadata = {}
        else:
            self._costs = {}
            self._metadata = {}
    
    def _save_costs(self):
        """Сохраняет себестоимость в файл"""
        try:
            # Обновляем метаданные
            self._metadata['last_updated'] = datetime.now().isoformat()
            self._metadata['total_skus'] = len(self._costs)
            
            data = {
                'costs': self._costs,
                'metadata': self._metadata
            }
            
            # Создаем директорию, если её нет
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except IOError as e:
            print(f"Ошибка сохранения себестоимости: {e}")
            return False
    
    def set_cost(self, sku: str, cost: float, product_name: Optional[str] = None):
        """
        Устанавливает себестоимость для SKU
        
        Args:
            sku: SKU товара
            cost: Себестоимость (в рублях)
            product_name: Название товара (опционально, для удобства)
        
        Returns:
            bool: True если успешно сохранено
        """
        if cost < 0:
            raise ValueError("Себестоимость не может быть отрицательной")
        
        sku_str = str(sku).strip()
        if not sku_str:
            raise ValueError("SKU не может быть пустым")
        
        self._costs[sku_str] = float(cost)
        
        # Сохраняем название товара в метаданных, если указано
        if product_name:
            if 'product_names' not in self._metadata:
                self._metadata['product_names'] = {}
            self._metadata['product_names'][sku_str] = str(product_name)
        
        return self._save_costs()
    
    def get_cost(self, sku: str) -> Optional[float]:
        """
        Получает себестоимость для SKU
        
        Args:
            sku: SKU товара
        
        Returns:
            float: Себестоимость или None, если не установлена
        """
        sku_str = str(sku).strip()
        return self._costs.get(sku_str)
    
    def get_all_costs(self) -> Dict[str, float]:
        """
        Получает все себестоимости
        
        Returns:
            dict: Словарь {sku: cost}
        """
        return self._costs.copy()
    
    def get_costs_with_names(self) -> Dict[str, Dict]:
        """
        Получает себестоимости с названиями товаров
        
        Returns:
            dict: Словарь {sku: {'cost': float, 'product_name': str}}
        """
        result = {}
        product_names = self._metadata.get('product_names', {})
        
        for sku, cost in self._costs.items():
            result[sku] = {
                'cost': cost,
                'product_name': product_names.get(sku)
            }
        
        return result
    
    def delete_cost(self, sku: str) -> bool:
        """
        Удаляет себестоимость для SKU
        
        Args:
            sku: SKU товара
        
        Returns:
            bool: True если успешно удалено
        """
        sku_str = str(sku).strip()
        if sku_str in self._costs:
            del self._costs[sku_str]
            
            # Удаляем название из метаданных
            if 'product_names' in self._metadata and sku_str in self._metadata['product_names']:
                del self._metadata['product_names'][sku_str]
            
            return self._save_costs()
        return False
    
    def bulk_set_costs(self, costs: Dict[str, float]) -> bool:
        """
        Массовое обновление себестоимости
        
        Args:
            costs: Словарь {sku: cost}
        
        Returns:
            bool: True если успешно сохранено
        """
        for sku, cost in costs.items():
            if cost < 0:
                raise ValueError(f"Себестоимость для SKU {sku} не может быть отрицательной")
            self._costs[str(sku).strip()] = float(cost)
        
        return self._save_costs()
    
    def get_statistics(self) -> Dict:
        """
        Получает статистику по себестоимости
        
        Returns:
            dict: Статистика
        """
        costs_list = list(self._costs.values())
        
        if not costs_list:
            return {
                'total_skus': 0,
                'avg_cost': 0,
                'min_cost': 0,
                'max_cost': 0
            }
        
        return {
            'total_skus': len(self._costs),
            'avg_cost': sum(costs_list) / len(costs_list),
            'min_cost': min(costs_list),
            'max_cost': max(costs_list),
            'last_updated': self._metadata.get('last_updated')
        }
