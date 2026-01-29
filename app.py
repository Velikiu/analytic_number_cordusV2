"""
Главное приложение Flask для системы аналитики Ozon
"""
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
import os
import time
import math
from datetime import datetime
import json
import logging
import traceback

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sanitize_for_json(obj):
    """
    Рекурсивно очищает объект от NaN/Infinity для валидного JSON.
    """
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif hasattr(obj, 'isoformat'):  # datetime
        return obj.isoformat()
    return obj

import config
from parsers.ozon_parser import OzonReportParser
from analytics.ozon_analytics import OzonAnalytics
from analytics.store_analytics import StoreAnalytics
from analytics.cabinet_analyzer import CabinetAnalyzer
from analytics.product_card_analyzer import ProductCardAnalyzer
from recommendations.ozon_recommendations import OzonRecommendations
from utils.file_processor import FileProcessor
from utils.export_reports import ReportExporter
from utils.unit_economics_manager import UnitEconomicsManager
from collectors.ozon_store_collector import OzonStoreCollector
from api.ozon_client import OzonAPIClient, OzonAPIError, get_last_n_months_ranges, OZON_AUTO_REPORT_TYPES

app = Flask(__name__, static_folder='static', static_url_path='')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-in-production')
CORS(app, supports_credentials=True)

config.ensure_dirs()

parser = OzonReportParser()
unit_economics_manager = UnitEconomicsManager()
analytics = OzonAnalytics(unit_economics_manager=unit_economics_manager)
store_analytics = StoreAnalytics()
cabinet_analyzer = CabinetAnalyzer()
product_card_analyzer = ProductCardAnalyzer()
recommendations = OzonRecommendations()
file_processor = FileProcessor()

UPLOAD_FOLDER = str(config.UPLOAD_DIR)


def sync_data():
    """Синхронизирует данные между парсером, аналитикой и рекомендациями"""
    parsed_data = parser.get_parsed_data()
    orders_count = len(parsed_data.get('orders', []))
    logger.info(f"Синхронизация данных: заказов={orders_count}, возвратов={len(parsed_data.get('returns', []))}, остатков={len(parsed_data.get('stocks', []))}")
    analytics.load_data(parsed_data)
    recommendations.set_analytics(analytics)
    recommendations.set_store_analytics(store_analytics)
    
    # Синхронизируем данные для анализа карточек
    store_data = {}
    if config.STORE_DATA_FILE.exists():
        try:
            with open(config.STORE_DATA_FILE, 'r', encoding='utf-8') as f:
                store_data = json.load(f)
        except Exception as e:
            logger.warning(f"Ошибка загрузки данных магазина для анализа карточек: {e}")
    
    # Получаем Ozon API клиент если доступен
    ozon_api_client = None
    try:
        client_id = session.get('ozon_client_id')
        api_key = session.get('ozon_api_key')
        if client_id and api_key:
            ozon_api_client = OzonAPIClient(client_id, api_key)
    except Exception as e:
        logger.debug(f"Ozon API не доступен: {e}")
    
    # Загружаем данные для анализа карточек
    try:
        product_card_analyzer.load_data(
            store_data=store_data,
            orders=parsed_data.get('orders', []),
            ozon_api_client=ozon_api_client
        )
    except Exception as e:
        logger.warning(f"Ошибка загрузки данных для анализа карточек: {e}")

# Синхронизируем данные из file_processor в глобальный parser при старте
parser.parsed_data = file_processor.parser.get_parsed_data()
sync_data()


@app.route('/')
def index():
    """Главная страница"""
    return send_from_directory('static', 'index.html')


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Загрузка файла через UI"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не найден'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Имя файла пустое'}), 400
    
    try:
        # Сохраняем файл
        filename = file.filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Обрабатываем файл
        result = file_processor.process_file(filepath)
        
        # Синхронизируем данные
        parser.parsed_data = file_processor.parser.get_parsed_data()
        sync_data()
        
        return jsonify({
            'success': True,
            'message': 'Файл успешно загружен и обработан',
            'data': sanitize_for_json(result)
        })
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        return jsonify({'error': f'Файл не найден: {str(e)}'}), 404
    except ValueError as e:
        logger.error(f"Ошибка валидации данных: {e}")
        return jsonify({'error': f'Неверный формат данных: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'Ошибка обработки файла: {str(e)}'}), 500


@app.route('/api/process-folder', methods=['POST'])
def process_folder():
    """Автоматическая обработка всех файлов из папки upload"""
    try:
        results = file_processor.process_folder(UPLOAD_FOLDER)
        
        # Синхронизируем данные
        parser.parsed_data = file_processor.parser.get_parsed_data()
        sync_data()
        
        return jsonify({
            'success': True,
            'message': f'Обработано файлов: {len(results)}',
            'data': sanitize_for_json(results)
        })
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        return jsonify({'error': f'Файл не найден: {str(e)}'}), 404
    except ValueError as e:
        logger.error(f"Ошибка валидации данных: {e}")
        return jsonify({'error': f'Неверный формат данных: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'Ошибка обработки файла: {str(e)}'}), 500


@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Получить аналитику по всем загруженным данным"""
    try:
        sync_data()
        
        # Получаем параметры периода из запроса
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Устанавливаем период фильтрации в аналитике
        analytics.set_date_filter(date_from, date_to)
        
        # Получаем данные магазина для расширенных метрик
        store_data = {}
        if config.STORE_DATA_FILE.exists():
            try:
                with open(config.STORE_DATA_FILE, 'r', encoding='utf-8') as f:
                    store_data = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Ошибка загрузки данных магазина: {e}")
            except Exception as e:
                logger.error(f"Неожиданная ошибка загрузки данных магазина: {e}\n{traceback.format_exc()}")
        
        analytics_data = analytics.get_full_analytics(store_data=store_data)
        
        # Добавляем метрики магазина если есть
        store_metrics = store_analytics.get_store_metrics()
        if store_metrics.get('seller_id'):
            analytics_data['store_metrics'] = store_metrics
        
        # Очищаем от NaN/Infinity для валидного JSON
        analytics_data = sanitize_for_json(analytics_data)
        
        return jsonify({
            'success': True,
            'data': analytics_data,
            'period': {
                'date_from': date_from,
                'date_to': date_to
            }
        })
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        return jsonify({'error': f'Файл не найден: {str(e)}'}), 404
    except ValueError as e:
        logger.error(f"Ошибка валидации данных: {e}")
        return jsonify({'error': f'Неверный формат данных: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'Ошибка обработки файла: {str(e)}'}), 500


@app.route('/api/export/analytics', methods=['GET'])
def export_analytics():
    """Экспортировать аналитику в Excel"""
    try:
        sync_data()
        
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        analytics.set_date_filter(date_from, date_to)
        
        # Получаем данные магазина
        store_data = {}
        if config.STORE_DATA_FILE.exists():
            try:
                with open(config.STORE_DATA_FILE, 'r', encoding='utf-8') as f:
                    store_data = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Ошибка загрузки данных магазина: {e}")
            except Exception as e:
                logger.error(f"Неожиданная ошибка загрузки данных магазина: {e}\n{traceback.format_exc()}")
        
        analytics_data = analytics.get_full_analytics(store_data=store_data)
        
        # Экспортируем
        exporter = ReportExporter()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"analytics_export_{timestamp}.xlsx"
        filepath = os.path.join(str(config.UPLOAD_DIR), filename)
        
        exporter.export_analytics_to_excel(analytics_data, filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'path': filepath,
            'message': f'Отчет сохранен: {filename}'
        })
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        return jsonify({'error': f'Файл не найден: {str(e)}'}), 404
    except ValueError as e:
        logger.error(f"Ошибка валидации данных: {e}")
        return jsonify({'error': f'Неверный формат данных: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'Ошибка обработки файла: {str(e)}'}), 500


@app.route('/api/export/recommendations', methods=['GET'])
def export_recommendations():
    """Экспортировать рекомендации в Excel"""
    try:
        sync_data()
        
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        analytics.set_date_filter(date_from, date_to)
        
        recs = recommendations.generate_recommendations()
        
        # Экспортируем
        exporter = ReportExporter()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"recommendations_export_{timestamp}.xlsx"
        filepath = os.path.join(str(config.UPLOAD_DIR), filename)
        
        exporter.export_recommendations_to_excel(recs, filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'path': filepath,
            'message': f'Рекомендации сохранены: {filename}'
        })
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        return jsonify({'error': f'Файл не найден: {str(e)}'}), 404
    except ValueError as e:
        logger.error(f"Ошибка валидации данных: {e}")
        return jsonify({'error': f'Неверный формат данных: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'Ошибка обработки файла: {str(e)}'}), 500


@app.route('/api/seasonality', methods=['GET'])
def get_seasonality_analysis():
    """Получить анализ сезонности и спадов продаж"""
    try:
        sync_data()
        
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        analysis_data = analytics.get_seasonality_analysis(date_from, date_to)
        
        # Очищаем от NaN/Infinity для валидного JSON
        analysis_data = sanitize_for_json(analysis_data)
        
        return jsonify({
            'success': True,
            'data': analysis_data
        })
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        return jsonify({'error': f'Файл не найден: {str(e)}'}), 404
    except ValueError as e:
        logger.error(f"Ошибка валидации данных: {e}")
        return jsonify({'error': f'Неверный формат данных: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'Ошибка обработки файла: {str(e)}'}), 500


@app.route('/api/competitors', methods=['POST', 'GET'])
def get_competitor_analysis():
    """Получить конкурентный анализ"""
    try:
        sync_data()
        
        # Получаем данные о конкурентах из body (POST) или query (GET)
        competitor_data = None
        if request.method == 'POST':
            competitor_data = request.get_json()
        elif request.method == 'GET':
            # Можно передать через query параметры или использовать кэш
            pass
        
        # Получаем данные магазина
        store_data = {}
        if config.STORE_DATA_FILE.exists():
            try:
                with open(config.STORE_DATA_FILE, 'r', encoding='utf-8') as f:
                    store_data = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Ошибка загрузки данных магазина: {e}")
            except Exception as e:
                logger.error(f"Неожиданная ошибка загрузки данных магазина: {e}\n{traceback.format_exc()}")
        
        analysis_data = analytics.get_competitor_analysis(competitor_data, store_data)
        
        # Очищаем от NaN/Infinity для валидного JSON
        analysis_data = sanitize_for_json(analysis_data)
        
        return jsonify({
            'success': True,
            'data': analysis_data
        })
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        return jsonify({'error': f'Файл не найден: {str(e)}'}), 404
    except ValueError as e:
        logger.error(f"Ошибка валидации данных: {e}")
        return jsonify({'error': f'Неверный формат данных: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'Ошибка обработки файла: {str(e)}'}), 500


@app.route('/api/forecast', methods=['GET'])
def get_forecast():
    """Получить прогноз продаж или остатков"""
    try:
        sync_data()
        
        forecast_type = request.args.get('type', 'sales')  # sales, inventory, anomalies, seasonality
        days_ahead = int(request.args.get('days_ahead', 30))
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        sku = request.args.get('sku')
        
        forecast_data = analytics.get_forecast(
            forecast_type=forecast_type,
            days_ahead=days_ahead,
            date_from=date_from,
            date_to=date_to,
            sku=sku
        )
        
        # Очищаем от NaN/Infinity для валидного JSON
        forecast_data = sanitize_for_json(forecast_data)
        
        return jsonify({
            'success': True,
            'data': forecast_data,
            'type': forecast_type
        })
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        return jsonify({'error': f'Файл не найден: {str(e)}'}), 404
    except ValueError as e:
        logger.error(f"Ошибка валидации данных: {e}")
        return jsonify({'error': f'Неверный формат данных: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'Ошибка обработки файла: {str(e)}'}), 500


@app.route('/api/period-comparison', methods=['GET'])
def get_period_comparison():
    """Получить сравнение периодов"""
    try:
        sync_data()
        
        # Получаем параметры периода из запроса
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        comparison_type = request.args.get('comparison_type', 'previous')  # previous, mom, yoy
        
        if not date_from or not date_to:
            return jsonify({'error': 'Укажите date_from и date_to'}), 400
        
        comparison_data = analytics.get_period_comparison(date_from, date_to, comparison_type)
        
        # Очищаем от NaN/Infinity для валидного JSON
        comparison_data = sanitize_for_json(comparison_data)
        
        return jsonify({
            'success': True,
            'data': comparison_data
        })
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        return jsonify({'error': f'Файл не найден: {str(e)}'}), 404
    except ValueError as e:
        logger.error(f"Ошибка валидации данных: {e}")
        return jsonify({'error': f'Неверный формат данных: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'Ошибка обработки файла: {str(e)}'}), 500


@app.route('/api/cohorts', methods=['GET'])
def get_cohorts():
    """Получить когортный анализ"""
    try:
        sync_data()
        
        # Получаем параметры периода из запроса
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        cohorts_data = analytics.get_cohort_analysis(date_from, date_to)
        
        # Очищаем от NaN/Infinity для валидного JSON
        cohorts_data = sanitize_for_json(cohorts_data)
        
        return jsonify({
            'success': True,
            'data': cohorts_data,
            'period': {
                'date_from': date_from,
                'date_to': date_to
            }
        })
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        return jsonify({'error': f'Файл не найден: {str(e)}'}), 404
    except ValueError as e:
        logger.error(f"Ошибка валидации данных: {e}")
        return jsonify({'error': f'Неверный формат данных: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'Ошибка обработки файла: {str(e)}'}), 500


@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    """Получить рекомендации по улучшению показателей"""
    try:
        sync_data()
        
        # Получаем параметры периода из запроса
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Устанавливаем период фильтрации в аналитике
        analytics.set_date_filter(date_from, date_to)
        
        recs = recommendations.generate_recommendations()
        
        # Добавляем рекомендации по настройкам кабинета
        try:
            analytics_data = analytics.get_full_analytics()
            store_data = {}
            if config.STORE_DATA_FILE.exists():
                with open(config.STORE_DATA_FILE, 'r', encoding='utf-8') as f:
                    store_data = json.load(f)
            
            cabinet_recs = cabinet_analyzer.analyze_cabinet_settings(
                analytics_data=analytics_data,
                store_data=store_data
            )
            recs.extend(cabinet_recs)
        except Exception as e:
            logger.error(f"Ошибка анализа кабинета: {e}\n{traceback.format_exc()}")
        
        # Очищаем от NaN/Infinity для валидного JSON
        recs = sanitize_for_json(recs)
        
        return jsonify({
            'success': True,
            'data': recs,
            'period': {
                'date_from': date_from,
                'date_to': date_to
            }
        })
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        return jsonify({'error': f'Файл не найден: {str(e)}'}), 404
    except ValueError as e:
        logger.error(f"Ошибка валидации данных: {e}")
        return jsonify({'error': f'Неверный формат данных: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'Ошибка обработки файла: {str(e)}'}), 500


@app.route('/api/reports/list', methods=['GET'])
def list_reports():
    """Список всех загруженных отчетов"""
    try:
        reports = file_processor.get_processed_reports()
        return jsonify({
            'success': True,
            'data': sanitize_for_json(reports)
        })
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        return jsonify({'error': f'Файл не найден: {str(e)}'}), 404
    except ValueError as e:
        logger.error(f"Ошибка валидации данных: {e}")
        return jsonify({'error': f'Неверный формат данных: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'Ошибка обработки файла: {str(e)}'}), 500


# ==================== API для управления себестоимостью (юнит-экономика) ====================

@app.route('/api/unit-economics/costs', methods=['GET'])
def get_costs():
    """Получить все себестоимости по SKU"""
    try:
        costs = unit_economics_manager.get_costs_with_names()
        stats = unit_economics_manager.get_statistics()
        return jsonify({
            'success': True,
            'data': costs,
            'statistics': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/unit-economics/cost/<sku>', methods=['GET'])
def get_cost(sku):
    """Получить себестоимость для конкретного SKU"""
    try:
        cost = unit_economics_manager.get_cost(sku)
        if cost is None:
            return jsonify({'success': False, 'error': 'Себестоимость не найдена'}), 404
        return jsonify({
            'success': True,
            'sku': sku,
            'cost': cost
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/unit-economics/cost', methods=['POST'])
def set_cost():
    """Установить себестоимость для SKU"""
    try:
        data = request.get_json() or {}
        sku = data.get('sku')
        cost = data.get('cost')
        product_name = data.get('product_name')
        
        if not sku:
            return jsonify({'success': False, 'error': 'SKU не указан'}), 400
        if cost is None:
            return jsonify({'success': False, 'error': 'Себестоимость не указана'}), 400
        
        try:
            cost_float = float(cost)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Неверный формат себестоимости'}), 400
        
        unit_economics_manager.set_cost(sku, cost_float, product_name)
        return jsonify({
            'success': True,
            'message': 'Себестоимость сохранена',
            'sku': sku,
            'cost': cost_float
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/unit-economics/cost/<sku>', methods=['DELETE'])
def delete_cost(sku):
    """Удалить себестоимость для SKU"""
    try:
        if unit_economics_manager.delete_cost(sku):
            return jsonify({
                'success': True,
                'message': 'Себестоимость удалена',
                'sku': sku
            })
        else:
            return jsonify({'success': False, 'error': 'Себестоимость не найдена'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/unit-economics/costs/bulk', methods=['POST'])
def bulk_set_costs():
    """Массовое обновление себестоимости"""
    try:
        data = request.get_json() or {}
        costs = data.get('costs', {})
        
        if not costs or not isinstance(costs, dict):
            return jsonify({'success': False, 'error': 'Неверный формат данных'}), 400
        
        unit_economics_manager.bulk_set_costs(costs)
        return jsonify({
            'success': True,
            'message': f'Обновлено {len(costs)} SKU',
            'count': len(costs)
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/unit-economics/statistics', methods=['GET'])
def get_unit_economics_statistics():
    """Получить статистику по себестоимости"""
    try:
        stats = unit_economics_manager.get_statistics()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/products/skus', methods=['GET'])
def get_products_skus():
    """Получить список всех SKU из загруженных заказов с названиями товаров"""
    try:
        sync_data()
        
        if not analytics.orders:
            return jsonify({
                'success': True,
                'data': [],
                'message': 'Нет загруженных заказов'
            })
        
        import pandas as pd
        df = pd.DataFrame(analytics.orders)
        
        # Получаем уникальные SKU с названиями товаров
        sku_data = {}
        for _, row in df.iterrows():
            sku = str(row.get('sku', '')).strip()
            if sku and sku != 'nan' and sku != '':
                product_name = str(row.get('product_name', '')).strip()
                if sku not in sku_data:
                    sku_data[sku] = {
                        'sku': sku,
                        'product_name': product_name if product_name and product_name != 'nan' else None,
                        'revenue': 0,
                        'quantity': 0
                    }
                # Агрегируем выручку и количество
                sku_data[sku]['revenue'] += float(row.get('paid_by_customer', 0) or 0)
                sku_data[sku]['quantity'] += float(row.get('quantity', 0) or 0)
        
        # Преобразуем в список и сортируем по выручке (по убыванию)
        sku_list = list(sku_data.values())
        sku_list.sort(key=lambda x: x['revenue'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': sku_list,
            'count': len(sku_list)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/store/collect', methods=['POST'])
def collect_store_data():
    """Сбор данных с магазина Ozon"""
    try:
        data = request.get_json() or {}
        brand = config.get_brand_defaults()
        seller_id = data.get('seller_id') or brand.get('seller_id')
        seller_url = data.get('seller_url') or brand.get('seller_url')
        
        if not seller_id and not seller_url:
            return jsonify({'error': 'Не указан seller_id или seller_url'}), 400
        
        collector = OzonStoreCollector(seller_id=seller_id, seller_url=seller_url)
        
        try:
            store_data = collector.collect_all()
        except Exception as e:
            print(f"Ошибка при сборе данных: {e}")
            store_data = {
                'seller_id': collector.seller_id or brand.get('seller_id'),
                'seller_url': seller_url or (f"https://www.ozon.ru/seller/{brand.get('seller_id')}/" if brand.get('seller_id') else None),
                'collected_at': datetime.now().isoformat(),
                'seller_info': collector._get_fallback_seller_info(),
                'products_info': collector._get_products_from_brand_docs(),
                'reviews_info': {'total_reviews': None, 'note': 'Используйте отчеты Ozon'},
                'rating_info': {'overall_rating': None, 'note': 'Используйте кабинет продавца'},
                'competitors_info': {'note': 'Требуется дополнительная реализация'},
                'collection_method': 'fallback_from_brand_docs',
                'note': 'Данные получены из документации бренда. Ozon блокирует простые HTTP запросы. Для полных данных используйте отчеты Ozon или Ozon Seller API.'
            }
        
        try:
            collector.save_to_file(str(config.STORE_DATA_FILE))
        except Exception as e:
            print(f"Ошибка сохранения данных: {e}")
        
        # Загружаем в аналитику
        try:
            store_analytics.load_store_data(store_data)
        except Exception as e:
            print(f"Ошибка загрузки в аналитику: {e}")
        
        # Анализируем карточки товаров после сбора данных
        try:
            # Загружаем данные для анализа карточек
            product_card_analyzer.load_data(
                store_data=store_data,
                orders=analytics.orders if hasattr(analytics, 'orders') else []
            )
            cards_analysis = product_card_analyzer.analyze_all_products()
            store_data['products_cards_analysis'] = cards_analysis
            logger.info(f"Проанализировано карточек товаров: {cards_analysis.get('total_products', 0)}")
        except Exception as e:
            logger.warning(f"Ошибка анализа карточек при сборе данных: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Данные магазина собраны (часть данных из документации бренда)',
            'data': sanitize_for_json(store_data),
            'warning': 'Ozon блокирует простые HTTP запросы. Для полных данных используйте отчеты Ozon или Ozon Seller API.'
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Критическая ошибка при сборе данных магазина: {error_details}")
        return jsonify({
            'error': str(e),
            'details': 'Попробуйте использовать данные из отчетов Ozon или подключите Ozon Seller API'
        }), 500


@app.route('/api/store/metrics', methods=['GET'])
def get_store_metrics():
    """Получить метрики магазина"""
    try:
        metrics = store_analytics.get_store_metrics()
        recommendations = store_analytics.get_store_recommendations()
        
        return jsonify({
            'success': True,
            'data': sanitize_for_json({
                'metrics': metrics,
                'recommendations': recommendations
            })
        })
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        return jsonify({'error': f'Файл не найден: {str(e)}'}), 404
    except ValueError as e:
        logger.error(f"Ошибка валидации данных: {e}")
        return jsonify({'error': f'Неверный формат данных: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'Ошибка обработки файла: {str(e)}'}), 500


@app.route('/api/cabinet/analyze', methods=['GET'])
def analyze_cabinet():
    """Анализ настроек кабинета"""
    try:
        analytics_data = analytics.get_full_analytics()
        store_data = {}
        if config.STORE_DATA_FILE.exists():
            with open(config.STORE_DATA_FILE, 'r', encoding='utf-8') as f:
                store_data = json.load(f)
        
        cabinet_recs = cabinet_analyzer.analyze_cabinet_settings(
            analytics_data=analytics_data,
            store_data=store_data
        )
        
        return jsonify({
            'success': True,
            'data': sanitize_for_json(cabinet_recs)
        })
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        return jsonify({'error': f'Файл не найден: {str(e)}'}), 404
    except ValueError as e:
        logger.error(f"Ошибка валидации данных: {e}")
        return jsonify({'error': f'Неверный формат данных: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'Ошибка обработки файла: {str(e)}'}), 500


@app.route('/api/config/defaults', methods=['GET'])
def get_config_defaults():
    """Дефолты для UI (seller_id, seller_url и т.п.) из бренда. Без ключей API."""
    try:
        d = config.get_brand_defaults()
        return jsonify({
            'success': True,
            'data': {
                'seller_id': d.get('seller_id'),
                'seller_url': d.get('seller_url'),
                'seller_name': d.get('seller_name'),
            }
        })
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        return jsonify({'error': f'Файл не найден: {str(e)}'}), 404
    except ValueError as e:
        logger.error(f"Ошибка валидации данных: {e}")
        return jsonify({'error': f'Неверный формат данных: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'Ошибка обработки файла: {str(e)}'}), 500


@app.route('/api/brand/info', methods=['GET'])
def get_brand_info():
    """Получить информацию о бренде"""
    try:
        if config.BRAND_DOCUMENTATION_PATH.exists():
            with open(config.BRAND_DOCUMENTATION_PATH, 'r', encoding='utf-8') as f:
                brand_info = json.load(f)
                return jsonify({
                    'success': True,
                    'data': brand_info
                })
        return jsonify({'success': False, 'error': 'Информация о бренде не найдена'}), 404
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        return jsonify({'error': f'Файл не найден: {str(e)}'}), 404
    except ValueError as e:
        logger.error(f"Ошибка валидации данных: {e}")
        return jsonify({'error': f'Неверный формат данных: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'Ошибка обработки файла: {str(e)}'}), 500


@app.route('/api/products/cards', methods=['GET'])
def get_product_cards_analysis():
    """Получить анализ всех карточек товаров"""
    try:
        sync_data()
        
        # Получаем Ozon API клиент если доступен
        ozon_api_client = None
        try:
            client_id = session.get('ozon_client_id')
            api_key = session.get('ozon_api_key')
            if client_id and api_key:
                ozon_api_client = OzonAPIClient(client_id, api_key)
                # Обновляем клиент в analyzer
                product_card_analyzer.ozon_api_client = ozon_api_client
        except Exception as e:
            logger.debug(f"Ozon API не доступен: {e}")
        
        # Анализируем все карточки (сбор изображений и отзывов происходит внутри)
        analysis = product_card_analyzer.analyze_all_products()
        
        return jsonify({
            'success': True,
            'data': sanitize_for_json(analysis)
        })
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        return jsonify({'error': f'Файл не найден: {str(e)}'}), 404
    except ValueError as e:
        logger.error(f"Ошибка валидации данных: {e}")
        return jsonify({'error': f'Неверный формат данных: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Ошибка анализа карточек товаров: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/products/card/<sku>', methods=['GET'])
def get_product_card_summary(sku):
    """Получить сводку по конкретной карточке товара"""
    try:
        sync_data()
        
        # Анализируем конкретную карточку
        summary = product_card_analyzer.get_product_summary(sku)
        
        if not summary:
            return jsonify({
                'success': False,
                'error': f'Товар с SKU {sku} не найден'
            }), 404
        
        return jsonify({
            'success': True,
            'data': sanitize_for_json(summary)
        })
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        return jsonify({'error': f'Файл не найден: {str(e)}'}), 404
    except ValueError as e:
        logger.error(f"Ошибка валидации данных: {e}")
        return jsonify({'error': f'Неверный формат данных: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Ошибка получения сводки по карточке {sku}: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/products/cards/export', methods=['GET'])
def export_product_cards():
    """Экспортировать анализ карточек товаров в Excel"""
    try:
        sync_data()
        
        # Анализируем все карточки
        analysis = product_card_analyzer.analyze_all_products()
        
        # Экспортируем
        exporter = ReportExporter()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"product_cards_analysis_{timestamp}.xlsx"
        filepath = os.path.join(str(config.UPLOAD_DIR), filename)
        
        exporter.export_product_cards_to_excel(analysis, filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'path': filepath,
            'message': f'Анализ карточек сохранен: {filename}'
        })
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        return jsonify({'error': f'Файл не найден: {str(e)}'}), 404
    except ValueError as e:
        logger.error(f"Ошибка валидации данных: {e}")
        return jsonify({'error': f'Неверный формат данных: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Ошибка экспорта карточек: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


def _ozon_credentials():
    """Ключи из сессии (не хранятся в репозитории)."""
    cid = session.get('ozon_client_id')
    key = session.get('ozon_api_key')
    return cid, key


@app.route('/api/ozon/connected', methods=['GET'])
def ozon_connected():
    """Проверка: есть ли сохранённые ключи в сессии (без их раскрытия)."""
    cid, _ = _ozon_credentials()
    return jsonify({'success': True, 'connected': bool(cid)})


@app.route('/api/ozon/connect', methods=['POST'])
def ozon_connect():
    """Подключение к OZON API: сохранить Client-Id и Api-Key в сессии."""
    try:
        data = request.get_json() or {}
        client_id = (data.get('client_id') or '').strip()
        api_key = (data.get('api_key') or '').strip()
        if not client_id or not api_key:
            return jsonify({'success': False, 'error': 'Укажите client_id и api_key'}), 400
        session['ozon_client_id'] = client_id
        session['ozon_api_key'] = api_key
        return jsonify({'success': True, 'message': 'Ключи сохранены в сессии'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/ozon/report/create', methods=['POST'])
def ozon_report_create():
    """Создать отчёт OZON (эндпоинты — по документации https://docs.ozon.ru/api/seller/)."""
    cid, key = _ozon_credentials()
    if not cid or not key:
        return jsonify({'success': False, 'error': 'Сначала подключитесь: укажите Client-Id и Api-Key'}), 401
    try:
        data = request.get_json() or {}
        report_type = (data.get('report_type') or '').strip()
        date_from = (data.get('date_from') or '').strip()
        date_to = (data.get('date_to') or '').strip()
        if not report_type or not date_from or not date_to:
            return jsonify({'success': False, 'error': 'Укажите report_type, date_from, date_to'}), 400
        client = OzonAPIClient(cid, key)
        out = client.report_create(report_type, date_from, date_to)
        return jsonify({'success': True, 'data': out})
    except OzonAPIError as e:
        logger.error(f"Ошибка Ozon API: {e.args[0]}, status_code: {e.status_code}")
        return jsonify({'success': False, 'error': e.args[0], 'status_code': e.status_code}), 502
    except ValueError as e:
        logger.error(f"Ошибка валидации: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/ozon/report/status/<code>', methods=['GET'])
def ozon_report_status(code):
    """Статус отчёта OZON."""
    cid, key = _ozon_credentials()
    if not cid or not key:
        return jsonify({'success': False, 'error': 'Сначала подключитесь'}), 401
    try:
        client = OzonAPIClient(cid, key)
        out = client.report_info(code)
        return jsonify({'success': True, 'data': out})
    except OzonAPIError as e:
        logger.error(f"Ошибка Ozon API: {e.args[0]}, status_code: {e.status_code}")
        return jsonify({'success': False, 'error': e.args[0], 'status_code': e.status_code}), 502
    except ValueError as e:
        logger.error(f"Ошибка валидации: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/ozon/report/download/<code>', methods=['GET'])
def ozon_report_download(code):
    """Скачать отчёт OZON и сохранить в upload/."""
    cid, key = _ozon_credentials()
    if not cid or not key:
        return jsonify({'success': False, 'error': 'Сначала подключитесь'}), 401
    try:
        client = OzonAPIClient(cid, key)
        raw = client.report_download(code)
        report_type = request.args.get('report_type', 'report')
        safe_type = "".join(c if c.isalnum() or c in '-_' else '_' for c in report_type)[:50]
        ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        ext = request.args.get('format', 'xlsx')
        if ext not in ('xlsx', 'xls', 'csv'):
            ext = 'xlsx'
        filename = f"ozon_api_{safe_type}_{ts}.{ext}"
        filepath = os.path.join(str(config.UPLOAD_DIR), filename)
        with open(filepath, 'wb') as f:
            f.write(raw)
        return jsonify({
            'success': True,
            'filename': filename,
            'path': filepath,
            'message': f'Сохранено в upload/{filename}',
        })
    except OzonAPIError as e:
        logger.error(f"Ошибка Ozon API: {e.args[0]}, status_code: {e.status_code}")
        return jsonify({'success': False, 'error': e.args[0], 'status_code': e.status_code}), 502
    except ValueError as e:
        logger.error(f"Ошибка валидации: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/ozon/report-types', methods=['GET'])
def ozon_report_types():
    """Получить список доступных типов отчётов для автозагрузки."""
    return jsonify({
        'success': True,
        'data': OZON_AUTO_REPORT_TYPES
    })


@app.route('/api/ozon/reports/auto-download', methods=['POST'])
def ozon_reports_auto_download():
    """
    Автоматическая загрузка данных за последние N месяцев (по умолчанию 3).
    
    Параметры:
        - months: количество месяцев (по умолчанию 3)
        - report_types: список типов данных (по умолчанию все из OZON_AUTO_REPORT_TYPES)
        - process_after: обработать файлы после загрузки (по умолчанию true)
    
    Использует прямые API-эндпоинты Ozon для получения данных помесячно,
    сохраняет в upload/ как JSON, затем обрабатывает для аналитики.
    """
    cid, key = _ozon_credentials()
    if not cid or not key:
        return jsonify({'success': False, 'error': 'Сначала подключитесь: укажите Client-Id и Api-Key'}), 401
    
    try:
        data = request.get_json() or {}
        months = int(data.get('months', 3))
        if months < 1:
            months = 1
        if months > 12:
            months = 12
        
        requested_types = data.get('report_types')
        if requested_types and isinstance(requested_types, list):
            report_types = [t for t in requested_types if t in OZON_AUTO_REPORT_TYPES]
        else:
            report_types = OZON_AUTO_REPORT_TYPES.copy()
        
        process_after = data.get('process_after', True)
        
        # Получаем диапазоны месяцев
        month_ranges = get_last_n_months_ranges(months)
        
        client = OzonAPIClient(cid, key)
        
        results = []
        errors = []
        downloaded_files = []
        
        for month_label, date_from, date_to in month_ranges:
            for data_type in report_types:
                task_id = f"{data_type}_{month_label}"
                logger.info(f"Запрос данных: {data_type} за {month_label} ({date_from} - {date_to})")
                
                try:
                    # Получаем данные через прямой API
                    api_data = client.fetch_data_for_period(data_type, date_from, date_to)
                    
                    # Проверяем, есть ли данные
                    items = []
                    if isinstance(api_data, dict):
                        # Разные форматы ответа API
                        items = api_data.get('result', api_data.get('items', api_data.get('returns', api_data.get('operations', []))))
                        if isinstance(items, dict):
                            items = items.get('items', items.get('postings', items.get('returns', [items])))
                    
                    if not items:
                        logger.info(f"Нет данных для {task_id}")
                        results.append({
                            'task': task_id,
                            'filename': None,
                            'period': f"{date_from} - {date_to}",
                            'status': 'no_data',
                            'count': 0
                        })
                        continue
                    
                    # Сохраняем как JSON
                    safe_type = "".join(c if c.isalnum() or c in '-_' else '_' for c in data_type)[:50]
                    filename = f"ozon_api_{safe_type}_{month_label}.json"
                    filepath = os.path.join(str(config.UPLOAD_DIR), filename)
                    
                    # Добавляем метаданные
                    export_data = {
                        'data_type': data_type,
                        'period': {'from': date_from, 'to': date_to},
                        'downloaded_at': datetime.now().isoformat(),
                        'items': items if isinstance(items, list) else [items],
                        'raw_response': api_data
                    }
                    
                    # Очищаем от NaN/Infinity для валидного JSON
                    export_data = sanitize_for_json(export_data)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(export_data, f, ensure_ascii=False, indent=2)
                    
                    item_count = len(items) if isinstance(items, list) else 1
                    downloaded_files.append(filename)
                    results.append({
                        'task': task_id,
                        'filename': filename,
                        'period': f"{date_from} - {date_to}",
                        'status': 'downloaded',
                        'count': item_count
                    })
                    logger.info(f"Данные сохранены: {filename} ({item_count} записей)")
                    
                except OzonAPIError as e:
                    err_msg = str(e)
                    # Некоторые ошибки могут быть некритичными (нет данных за период)
                    if e.status_code == 400 or 'not found' in err_msg.lower():
                        results.append({
                            'task': task_id,
                            'filename': None,
                            'period': f"{date_from} - {date_to}",
                            'status': 'no_data',
                            'count': 0
                        })
                    else:
                        errors.append({
                            'task': task_id,
                            'error': err_msg,
                            'status_code': e.status_code
                        })
                except Exception as e:
                    errors.append({
                        'task': task_id,
                        'error': str(e)
                    })
        
        # Обрабатываем загруженные файлы для аналитики
        processed_count = 0
        if process_after and downloaded_files:
            try:
                process_results = file_processor.process_folder(config.UPLOAD_DIR)
                parser.parsed_data = file_processor.parser.get_parsed_data()
                sync_data()
                processed_count = len(process_results)
            except Exception as e:
                errors.append({
                    'task': 'process_folder',
                    'error': f'Ошибка обработки файлов: {e}'
                })
        
        total_items = sum(r.get('count', 0) for r in results)
        
        return jsonify(sanitize_for_json({
            'success': True,
            'message': f'Загружено файлов: {len(downloaded_files)}, записей: {total_items}, обработано: {processed_count}',
            'data': {
                'downloaded': results,
                'downloaded_count': len(downloaded_files),
                'total_items': total_items,
                'processed_count': processed_count,
                'months': months,
                'month_ranges': [{'label': m[0], 'from': m[1], 'to': m[2]} for m in month_ranges],
                'report_types': report_types
            },
            'errors': errors if errors else None
        }))
        
    except Exception as e:
        logger.exception("Ошибка автозагрузки данных")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/ozon/data/<data_type>', methods=['POST'])
def ozon_fetch_data(data_type):
    """
    Получить данные определённого типа за указанный период.
    
    Параметры в body:
        - date_from: дата начала (YYYY-MM-DD)
        - date_to: дата окончания (YYYY-MM-DD)
    """
    cid, key = _ozon_credentials()
    if not cid or not key:
        return jsonify({'success': False, 'error': 'Сначала подключитесь'}), 401
    
    if data_type not in OZON_AUTO_REPORT_TYPES:
        return jsonify({
            'success': False, 
            'error': f'Неизвестный тип данных: {data_type}',
            'available_types': OZON_AUTO_REPORT_TYPES
        }), 400
    
    try:
        data = request.get_json() or {}
        date_from = data.get('date_from', '')
        date_to = data.get('date_to', '')
        
        if not date_from or not date_to:
            return jsonify({'success': False, 'error': 'Укажите date_from и date_to'}), 400
        
        client = OzonAPIClient(cid, key)
        result = client.fetch_data_for_period(data_type, date_from, date_to)
        
        # Очищаем от NaN для валидного JSON
        result = sanitize_for_json(result)
        
        return jsonify({
            'success': True,
            'data_type': data_type,
            'period': {'from': date_from, 'to': date_to},
            'data': result
        })
    except OzonAPIError as e:
        logger.error(f"Ошибка Ozon API: {e.args[0]}, status_code: {e.status_code}")
        return jsonify({'success': False, 'error': e.args[0], 'status_code': e.status_code}), 502
    except ValueError as e:
        logger.error(f"Ошибка валидации: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    # Автоматически обрабатываем файлы из папки при запуске (в фоне, чтобы не блокировать)
    import threading
    def process_files_background():
        print("Обработка файлов из папки upload...")
        try:
            file_processor.process_folder(config.UPLOAD_DIR)
            # Синхронизируем данные после обработки
            parser.parsed_data = file_processor.parser.get_parsed_data()
            sync_data()
            print(f"Обработано файлов: {len(file_processor.processed_files)}")
        except Exception as e:
            print(f"Ошибка при обработке файлов: {e}")
            import traceback
            traceback.print_exc()
    
    # Запускаем обработку файлов в фоне
    threading.Thread(target=process_files_background, daemon=True).start()
    
    print("Запуск сервера на http://localhost:5000")
    try:
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
    except Exception as e:
        print(f"Ошибка запуска сервера: {e}")
        import traceback
        traceback.print_exc()
