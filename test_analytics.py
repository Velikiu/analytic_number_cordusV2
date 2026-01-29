"""
Скрипт для проверки корректности расчетов аналитики
"""
import pandas as pd
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parsers.ozon_parser import OzonReportParser
from analytics.ozon_analytics import OzonAnalytics

def test_analytics_calculations():
    """Проверяет корректность расчетов аналитики"""
    print("=" * 60)
    print("ПРОВЕРКА КОРРЕКТНОСТИ РАСЧЕТОВ АНАЛИТИКИ")
    print("=" * 60)
    
    # Загружаем данные напрямую из CSV для проверки
    print("\n1. Загрузка данных из orders.csv...")
    df_raw = pd.read_csv('upload/orders.csv', sep=';', encoding='utf-8')
    print(f"   Всего строк в файле: {len(df_raw)}")
    
    # Парсим через парсер
    parser = OzonReportParser()
    result = parser.parse_orders('upload/orders.csv')
    print(f"   Распарсено заказов: {result['count']}")
    
    # Загружаем в аналитику
    analytics = OzonAnalytics()
    analytics.load_data(parser.get_parsed_data())
    
    # Получаем метрики
    print("\n2. Расчет метрик продаж...")
    sales_metrics = analytics.get_sales_metrics()
    
    # Проверяем вручную из исходных данных
    delivered_raw = df_raw[df_raw['Статус'] == 'Доставлен']
    cancelled_raw = df_raw[df_raw['Статус'] == 'Отменён']
    
    # Парсим оплату покупателем
    def parse_payment(value):
        try:
            if pd.isna(value) or value == '':
                return 0.0
            val_str = str(value).replace(',', '.').replace('"', '').replace(' ', '')
            return float(val_str)
        except:
            return 0.0
    
    paid_values = delivered_raw['Оплачено покупателем'].apply(parse_payment)
    total_revenue_manual = paid_values.sum()
    avg_order_manual = paid_values.mean() if len(paid_values) > 0 else 0
    
    print(f"\n   РАСЧЕТЫ ИЗ АНАЛИТИКИ:")
    print(f"   - Выручка: {sales_metrics['total_revenue']:,.2f} руб")
    print(f"   - Заказов доставлено: {sales_metrics['total_orders']}")
    print(f"   - Средний чек: {sales_metrics['avg_order_value']:,.2f} руб")
    print(f"   - Конверсия: {sales_metrics['conversion_rate']:.2f}%")
    print(f"   - Отмены: {sales_metrics['cancellation_rate']:.2f}%")
    
    print(f"\n   РУЧНАЯ ПРОВЕРКА ИЗ CSV:")
    print(f"   - Выручка: {total_revenue_manual:,.2f} руб")
    print(f"   - Заказов доставлено: {len(delivered_raw)}")
    print(f"   - Средний чек: {avg_order_manual:,.2f} руб")
    print(f"   - Отменено: {len(cancelled_raw)}")
    
    # Проверка расхождений
    revenue_diff = abs(sales_metrics['total_revenue'] - total_revenue_manual)
    revenue_diff_percent = (revenue_diff / total_revenue_manual * 100) if total_revenue_manual > 0 else 0
    
    print(f"\n   РАСХОЖДЕНИЯ:")
    print(f"   - Разница в выручке: {revenue_diff:,.2f} руб ({revenue_diff_percent:.2f}%)")
    
    if revenue_diff_percent > 1:
        print(f"   ВНИМАНИЕ: Расхождение больше 1%!")
    else:
        print(f"   OK: Расхождение в пределах нормы")
    
    # Проверка финансовых метрик
    print("\n3. Расчет финансовых метрик...")
    financial_metrics = analytics.get_financial_metrics()
    
    # Парсим цены продавца
    seller_prices = delivered_raw['Ваша цена'].apply(parse_payment)
    seller_revenue_manual = seller_prices.sum()
    
    # Парсим скидки
    discount_rub = delivered_raw['Скидка руб'].apply(parse_payment)
    total_discounts_manual = discount_rub.sum()
    
    margin_manual = seller_revenue_manual - total_revenue_manual
    margin_percent_manual = (margin_manual / seller_revenue_manual * 100) if seller_revenue_manual > 0 else 0
    
    print(f"\n   РАСЧЕТЫ ИЗ АНАЛИТИКИ:")
    seller_price_key = 'seller_price_total' if 'seller_price_total' in financial_metrics else 'seller_revenue'
    seller_price_analytics = financial_metrics.get(seller_price_key, 0)
    print(f"   - Цена продавца (до скидок): {seller_price_analytics:,.2f} руб")
    print(f"   - Общие скидки: {financial_metrics['total_discounts']:,.2f} руб")
    print(f"   - Маржа: {financial_metrics['margin']:,.2f} руб")
    print(f"   - Маржа %: {financial_metrics['margin_percent']:.2f}%")
    if 'margin_note' in financial_metrics:
        print(f"   - Примечание: {financial_metrics['margin_note']}")
    
    print(f"\n   РУЧНАЯ ПРОВЕРКА:")
    print(f"   - Цена продавца (до скидок): {seller_revenue_manual:,.2f} руб")
    print(f"   - Общие скидки: {total_discounts_manual:,.2f} руб")
    print(f"   - Разница (скидки): {margin_manual:,.2f} руб")
    print(f"   - Разница %: {margin_percent_manual:.2f}%")
    print(f"   - Примечание: Это разница из-за скидок, не реальная маржа")
    
    # Проверка расхождений
    seller_revenue_diff = abs(seller_price_analytics - seller_revenue_manual)
    seller_revenue_diff_percent = (seller_revenue_diff / seller_revenue_manual * 100) if seller_revenue_manual > 0 else 0
    
    print(f"\n   РАСХОЖДЕНИЯ:")
    print(f"   - Разница в выручке продавца: {seller_revenue_diff:,.2f} руб ({seller_revenue_diff_percent:.2f}%)")
    
    if seller_revenue_diff_percent > 1:
        print(f"   ВНИМАНИЕ: Расхождение больше 1%!")
    else:
        print(f"   OK: Расхождение в пределах нормы")
    
    # Проверка метрик по товарам
    print("\n4. Расчет метрик по товарам...")
    product_metrics = analytics.get_product_metrics()
    
    # Парсим скидки в процентах
    def parse_discount_percent(value):
        try:
            if pd.isna(value) or value == '':
                return 0.0
            val_str = str(value).replace('%', '').replace('"', '').replace(' ', '')
            return float(val_str)
        except:
            return 0.0
    
    discount_percent_values = delivered_raw['Скидка %'].apply(parse_discount_percent)
    avg_discount_manual = discount_percent_values.mean()
    
    unique_articles = delivered_raw['Артикул'].nunique()
    unique_skus = delivered_raw['SKU'].nunique()
    
    print(f"\n   РАСЧЕТЫ ИЗ АНАЛИТИКИ:")
    print(f"   - Уникальных товаров (артикулов): {product_metrics['total_products']}")
    print(f"   - Уникальных SKU: {product_metrics['total_skus']}")
    print(f"   - Средняя скидка: {product_metrics['avg_discount']:.2f}%")
    
    print(f"\n   РУЧНАЯ ПРОВЕРКА:")
    print(f"   - Уникальных товаров (артикулов): {unique_articles}")
    print(f"   - Уникальных SKU: {unique_skus}")
    print(f"   - Средняя скидка: {avg_discount_manual:.2f}%")
    
    # Итоговый отчет
    print("\n" + "=" * 60)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 60)
    
    issues = []
    
    if revenue_diff_percent > 1:
        issues.append(f"Выручка: расхождение {revenue_diff_percent:.2f}%")
    
    if seller_revenue_diff_percent > 1:
        issues.append(f"Выручка продавца: расхождение {seller_revenue_diff_percent:.2f}%")
    
    if abs(product_metrics['total_products'] - unique_articles) > 0:
        issues.append(f"Количество товаров: расхождение {abs(product_metrics['total_products'] - unique_articles)}")
    
    if abs(product_metrics['avg_discount'] - avg_discount_manual) > 1:
        issues.append(f"Средняя скидка: расхождение {abs(product_metrics['avg_discount'] - avg_discount_manual):.2f}%")
    
    if issues:
        print("\nНАЙДЕНЫ ПРОБЛЕМЫ:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("\nOK: Все расчеты корректны!")
    
    return len(issues) == 0

if __name__ == '__main__':
    try:
        is_correct = test_analytics_calculations()
        sys.exit(0 if is_correct else 1)
    except Exception as e:
        print(f"\nОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
