"""
Экспорт отчетов в Excel и PDF
"""
from datetime import datetime
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import os


class ReportExporter:
    """Класс для экспорта отчетов"""
    
    def __init__(self):
        self.wb = None
        self.ws = None
    
    def export_analytics_to_excel(self, analytics_data, filename=None):
        """
        Экспортирует аналитику в Excel
        
        Args:
            analytics_data: данные аналитики
            filename: имя файла (опционально)
        
        Returns:
            путь к сохраненному файлу
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"analytics_report_{timestamp}.xlsx"
        
        wb = Workbook()
        wb.remove(wb.active)  # Удаляем дефолтный лист
        
        # Лист с метриками продаж
        if 'sales_metrics' in analytics_data:
            self._add_sales_metrics_sheet(wb, analytics_data['sales_metrics'])
        
        # Лист с финансовыми метриками
        if 'financial_metrics' in analytics_data:
            self._add_financial_metrics_sheet(wb, analytics_data['financial_metrics'])
        
        # Лист с метриками клиентов
        if 'customer_metrics' in analytics_data:
            self._add_customer_metrics_sheet(wb, analytics_data['customer_metrics'])
        
        # Лист с метриками остатков
        if 'inventory_metrics' in analytics_data:
            self._add_inventory_metrics_sheet(wb, analytics_data['inventory_metrics'])
        
        # Лист с расширенными метриками маркетплейса
        if 'marketplace_metrics' in analytics_data:
            self._add_marketplace_metrics_sheet(wb, analytics_data['marketplace_metrics'])
        
        # Лист с временными рядами
        if 'time_series' in analytics_data:
            self._add_time_series_sheet(wb, analytics_data['time_series'])
        
        # Сохраняем файл
        wb.save(filename)
        return filename
    
    def _add_sales_metrics_sheet(self, wb, sales_metrics):
        """Добавляет лист с метриками продаж"""
        ws = wb.create_sheet("Метрики продаж")
        
        # Заголовок
        ws['A1'] = 'Метрики продаж'
        ws['A1'].font = Font(bold=True, size=14)
        ws.merge_cells('A1:B1')
        
        row = 3
        metrics = [
            ('Общая выручка', sales_metrics.get('total_revenue', 0)),
            ('Всего заказов', sales_metrics.get('total_orders', 0)),
            ('Средний чек', sales_metrics.get('avg_order_value', 0)),
            ('Конверсия (%)', sales_metrics.get('conversion_rate', 0)),
            ('Процент отмен (%)', sales_metrics.get('cancellation_rate', 0))
        ]
        
        for metric_name, metric_value in metrics:
            ws[f'A{row}'] = metric_name
            ws[f'B{row}'] = metric_value
            row += 1
        
        # Топ товары
        if 'top_products' in sales_metrics:
            row += 2
            ws[f'A{row}'] = 'Топ-10 товаров'
            ws[f'A{row}'].font = Font(bold=True, size=12)
            row += 1
            
            ws[f'A{row}'] = 'SKU'
            ws[f'B{row}'] = 'Выручка'
            ws[f'C{row}'] = 'Количество'
            self._style_header_row(ws, row)
            row += 1
            
            for sku, data in list(sales_metrics['top_products'].items())[:10]:
                ws[f'A{row}'] = sku
                ws[f'B{row}'] = data.get('revenue', 0)
                ws[f'C{row}'] = data.get('quantity', 0)
                row += 1
        
        self._auto_adjust_columns(ws)
    
    def _add_financial_metrics_sheet(self, wb, financial_metrics):
        """Добавляет лист с финансовыми метриками"""
        ws = wb.create_sheet("Финансовые метрики")
        
        ws['A1'] = 'Финансовые метрики'
        ws['A1'].font = Font(bold=True, size=14)
        ws.merge_cells('A1:B1')
        
        row = 3
        metrics = [
            ('Общая выручка', financial_metrics.get('total_revenue', 0)),
            ('Цена продавца (до скидок)', financial_metrics.get('seller_price_total', 0)),
            ('Общие скидки', financial_metrics.get('total_discounts', 0)),
            ('Маржа', financial_metrics.get('margin', 0)),
            ('Маржа (%)', financial_metrics.get('margin_percent', 0))
        ]
        
        for metric_name, metric_value in metrics:
            ws[f'A{row}'] = metric_name
            ws[f'B{row}'] = metric_value
            row += 1
        
        self._auto_adjust_columns(ws)
    
    def _add_customer_metrics_sheet(self, wb, customer_metrics):
        """Добавляет лист с метриками клиентов"""
        ws = wb.create_sheet("Метрики клиентов")
        
        ws['A1'] = 'Метрики клиентов'
        ws['A1'].font = Font(bold=True, size=14)
        ws.merge_cells('A1:B1')
        
        row = 3
        metrics = [
            ('Премиум клиенты', customer_metrics.get('premium_customers', 0)),
            ('Обычные клиенты', customer_metrics.get('regular_customers', 0)),
            ('Доля премиум (%)', customer_metrics.get('premium_ratio', 0))
        ]
        
        for metric_name, metric_value in metrics:
            ws[f'A{row}'] = metric_name
            ws[f'B{row}'] = metric_value
            row += 1
        
        self._auto_adjust_columns(ws)
    
    def _add_inventory_metrics_sheet(self, wb, inventory_metrics):
        """Добавляет лист с метриками остатков"""
        ws = wb.create_sheet("Метрики остатков")
        
        ws['A1'] = 'Метрики остатков'
        ws['A1'].font = Font(bold=True, size=14)
        ws.merge_cells('A1:B1')
        
        row = 3
        metrics = [
            ('Доступно', inventory_metrics.get('total_available', 0)),
            ('Зарезервировано', inventory_metrics.get('total_reserved', 0)),
            ('В пути', inventory_metrics.get('total_in_transit', 0)),
            ('Товаров без остатков', inventory_metrics.get('out_of_stock_count', 0))
        ]
        
        for metric_name, metric_value in metrics:
            ws[f'A{row}'] = metric_name
            ws[f'B{row}'] = metric_value
            row += 1
        
        self._auto_adjust_columns(ws)
    
    def _add_marketplace_metrics_sheet(self, wb, marketplace_metrics):
        """Добавляет лист с расширенными метриками маркетплейса"""
        ws = wb.create_sheet("Метрики маркетплейса")
        
        ws['A1'] = 'Расширенные метрики маркетплейса'
        ws['A1'].font = Font(bold=True, size=14)
        ws.merge_cells('A1:C1')
        
        row = 3
        
        # Метрики продаж
        if 'sales_metrics' in marketplace_metrics:
            ws[f'A{row}'] = 'Метрики продаж'
            ws[f'A{row}'].font = Font(bold=True, size=12)
            row += 1
            
            sales = marketplace_metrics['sales_metrics']
            metrics = [
                ('GMV', sales.get('gmv', 0)),
                ('Net GMV', sales.get('net_gmv', 0)),
                ('Basket Size', sales.get('basket_size', 0))
            ]
            
            for metric_name, metric_value in metrics:
                ws[f'A{row}'] = metric_name
                ws[f'B{row}'] = metric_value
                row += 1
        
        # Метрики клиентов
        if 'customer_metrics' in marketplace_metrics:
            row += 1
            ws[f'A{row}'] = 'Метрики клиентов'
            ws[f'A{row}'].font = Font(bold=True, size=12)
            row += 1
            
            customers = marketplace_metrics['customer_metrics']
            metrics = [
                ('LTV', customers.get('ltv', 0)),
                ('CAC', customers.get('cac')),
                ('LTV/CAC Ratio', customers.get('ltv_cac_ratio')),
                ('Repeat Purchase Rate (%)', customers.get('repeat_purchase_rate', 0)),
                ('Retention Rate (%)', customers.get('retention_rate', 0))
            ]
            
            for metric_name, metric_value in metrics:
                ws[f'A{row}'] = metric_name
                if metric_value is not None:
                    ws[f'B{row}'] = metric_value
                row += 1
        
        # Метрики остатков
        if 'inventory_metrics' in marketplace_metrics:
            row += 1
            ws[f'A{row}'] = 'Метрики остатков'
            ws[f'A{row}'].font = Font(bold=True, size=12)
            row += 1
            
            inventory = marketplace_metrics['inventory_metrics']
            metrics = [
                ('Inventory Turnover', inventory.get('inventory_turnover', 0)),
                ('Days of Inventory', inventory.get('days_of_inventory', 0)),
                ('Sell-through Rate (%)', inventory.get('sell_through_rate', 0)),
                ('Stockout Rate (%)', inventory.get('stockout_rate', 0))
            ]
            
            for metric_name, metric_value in metrics:
                ws[f'A{row}'] = metric_name
                ws[f'B{row}'] = metric_value
                row += 1
        
        self._auto_adjust_columns(ws)
    
    def _add_time_series_sheet(self, wb, time_series):
        """Добавляет лист с временными рядами"""
        ws = wb.create_sheet("Временные ряды")
        
        ws['A1'] = 'Продажи по дням'
        ws['A1'].font = Font(bold=True, size=14)
        
        if 'daily_revenue' in time_series:
            row = 3
            ws[f'A{row}'] = 'Дата'
            ws[f'B{row}'] = 'Выручка'
            self._style_header_row(ws, row)
            row += 1
            
            for item in time_series['daily_revenue']:
                ws[f'A{row}'] = item.get('date', '')
                ws[f'B{row}'] = item.get('paid_by_customer', 0)
                row += 1
        
        self._auto_adjust_columns(ws)
    
    def _style_header_row(self, ws, row):
        """Стилизует строку заголовка"""
        fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        font = Font(bold=True, color="FFFFFF")
        
        for col in range(1, ws.max_column + 1):
            cell = ws.cell(row=row, column=col)
            cell.fill = fill
            cell.font = font
            cell.alignment = Alignment(horizontal='center', vertical='center')
    
    def _auto_adjust_columns(self, ws):
        """Автоматически подстраивает ширину колонок"""
        for column in ws.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
    
    def export_recommendations_to_excel(self, recommendations, filename=None):
        """Экспортирует рекомендации в Excel"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"recommendations_{timestamp}.xlsx"
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Рекомендации"
        
        # Заголовок
        ws['A1'] = 'Рекомендации по улучшению показателей'
        ws['A1'].font = Font(bold=True, size=14)
        ws.merge_cells('A1:E1')
        
        # Заголовки таблицы
        headers = ['Ранг', 'Категория', 'Приоритет', 'Заголовок', 'Описание', 'Действие']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col)
            cell.value = header
            self._style_header_row(ws, 3)
        
        # Данные
        row = 4
        for rec in recommendations:
            ws.cell(row=row, column=1, value=rec.get('rank', ''))
            ws.cell(row=row, column=2, value=rec.get('category', ''))
            ws.cell(row=row, column=3, value=rec.get('priority', ''))
            ws.cell(row=row, column=4, value=rec.get('title', ''))
            ws.cell(row=row, column=5, value=rec.get('description', ''))
            ws.cell(row=row, column=6, value=rec.get('action', ''))
            row += 1
        
        self._auto_adjust_columns(ws)
        wb.save(filename)
        return filename
    
    def export_product_cards_to_excel(self, cards_analysis, filename=None):
        """Экспортирует анализ карточек товаров в Excel"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"product_cards_analysis_{timestamp}.xlsx"
        
        wb = Workbook()
        wb.remove(wb.active)  # Удаляем дефолтный лист
        
        # Сводный лист
        if 'summary' in cards_analysis:
            self._add_cards_summary_sheet(wb, cards_analysis)
        
        # Лист с детальным анализом каждой карточки
        if 'products' in cards_analysis:
            self._add_cards_details_sheet(wb, cards_analysis['products'])
        
        wb.save(filename)
        return filename
    
    def _add_cards_summary_sheet(self, wb, cards_analysis):
        """Добавляет сводный лист по карточкам"""
        ws = wb.create_sheet("Сводка")
        
        ws['A1'] = 'Сводка по карточкам товаров'
        ws['A1'].font = Font(bold=True, size=14)
        ws.merge_cells('A1:B1')
        
        summary = cards_analysis.get('summary', {})
        row = 3
        
        ws[f'A{row}'] = 'Всего товаров'
        ws[f'B{row}'] = cards_analysis.get('total_products', 0)
        row += 1
        
        ws[f'A{row}'] = 'Средний score'
        ws[f'B{row}'] = cards_analysis.get('average_score', 0)
        row += 2
        
        # Распределение по статусам
        if 'status_distribution' in summary:
            ws[f'A{row}'] = 'Распределение по статусам'
            ws[f'A{row}'].font = Font(bold=True, size=12)
            row += 1
            
            ws[f'A{row}'] = 'Статус'
            ws[f'B{row}'] = 'Количество'
            self._style_header_row(ws, row)
            row += 1
            
            for status, count in summary['status_distribution'].items():
                ws[f'A{row}'] = status
                ws[f'B{row}'] = count
                row += 1
        
        # Распределение по SEO уровням
        if 'seo_levels_distribution' in summary:
            row += 1
            ws[f'A{row}'] = 'Распределение по SEO уровням'
            ws[f'A{row}'].font = Font(bold=True, size=12)
            row += 1
            
            ws[f'A{row}'] = 'SEO Уровень'
            ws[f'B{row}'] = 'Количество'
            self._style_header_row(ws, row)
            row += 1
            
            for level, count in summary['seo_levels_distribution'].items():
                ws[f'A{row}'] = level
                ws[f'B{row}'] = count
                row += 1
        
        # Топ проблем
        if 'top_issues' in summary:
            row += 1
            ws[f'A{row}'] = 'Топ-5 проблем'
            ws[f'A{row}'].font = Font(bold=True, size=12)
            row += 1
            
            for i, issue in enumerate(summary['top_issues'], 1):
                ws[f'A{row}'] = f'{i}. {issue}'
                row += 1
        
        self._auto_adjust_columns(ws)
    
    def _add_cards_details_sheet(self, wb, products):
        """Добавляет детальный лист по каждой карточке"""
        ws = wb.create_sheet("Карточки товаров")
        
        # Заголовок
        ws['A1'] = 'Детальный анализ карточек товаров'
        ws['A1'].font = Font(bold=True, size=14)
        ws.merge_cells('A1:J1')
        
        # Заголовки
        headers = [
            'SKU', 'Название', 'Общий Score', 'Статус',
            'SEO Score', 'SEO Уровень', 'Продажи', 'Рейтинг',
            'Проблемы', 'Рекомендации'
        ]
        row = 3
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col)
            cell.value = header
        self._style_header_row(ws, row)
        row += 1
        
        # Данные по каждой карточке
        for product in products:
            seo_analysis = product.get('seo_analysis', {})
            sales_analysis = product.get('sales_analysis', {})
            reviews_analysis = product.get('reviews_analysis', {})
            
            # SKU
            ws.cell(row=row, column=1, value=product.get('sku', ''))
            
            # Название
            ws.cell(row=row, column=2, value=product.get('product_name', ''))
            
            # Общий Score
            ws.cell(row=row, column=3, value=product.get('overall_score', 0))
            
            # Статус
            status = product.get('status', '')
            ws.cell(row=row, column=4, value=status)
            
            # SEO Score
            ws.cell(row=row, column=5, value=seo_analysis.get('score', 0))
            
            # SEO Уровень
            ws.cell(row=row, column=6, value=seo_analysis.get('level', ''))
            
            # Продажи
            if sales_analysis.get('has_data'):
                sales_text = f"Выручка: {sales_analysis.get('total_revenue', 0):,.0f} руб"
            else:
                sales_text = "Нет данных"
            ws.cell(row=row, column=7, value=sales_text)
            
            # Рейтинг
            if reviews_analysis.get('has_data'):
                rating = reviews_analysis.get('average_rating', 0) or 0
                rating_text = f"{rating:.2f}/5.0" if rating > 0 else "Нет данных"
            else:
                rating_text = "Нет данных"
            ws.cell(row=row, column=8, value=rating_text)
            
            # Проблемы
            issues = seo_analysis.get('issues', [])
            issues_text = '; '.join(issues[:3]) if issues else 'Нет проблем'
            ws.cell(row=row, column=9, value=issues_text)
            
            # Рекомендации
            recommendations = product.get('recommendations', [])
            recs_text = '; '.join([r.get('title', '') for r in recommendations[:2]]) if recommendations else 'Нет рекомендаций'
            ws.cell(row=row, column=10, value=recs_text)
            
            row += 1
        
        self._auto_adjust_columns(ws)
