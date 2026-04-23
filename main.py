from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import requests
import time
import logging
import os

app = Flask(__name__)

# ВКЛЮЧАЕМ CORS ДЛЯ ВСЕХ ДОМЕНОВ БЕЗ ОГРАНИЧЕНИЙ
CORS(app, resources={r"/*": {"origins": "*"}})

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Ключи API Lpay (в продакшене используйте переменные окружения)
API_KEY = os.environ.get('LPAY_API_KEY', "06ff2425-dcf0-42ed-85d3-419bb4bbe927")
API_SECRET = os.environ.get('LPAY_API_SECRET', "8e280987-ebba-4c95-af1c-90934e372774")

@app.after_request
def after_request(response):
    """
    ДОБАВЛЯЕМ CORS ЗАГОЛОВКИ К КАЖДОМУ ОТВЕТУ
    """
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept,Origin,User-Agent,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Max-Age', '3600')
    return response

@app.route('/health', methods=['GET'])
def health_check():
    """
    Healthcheck эндпоинт для Railway
    """
    return make_response("OK", 200, {'Content-Type': 'text/plain; charset=utf-8'})

@app.route('/create_invoice_get', methods=['GET'])
def create_invoice_get():
    """
    Максимально упрощенная версия для PuzzleBot
    """
    # Получаем параметры из URL
    amount = request.args.get('amount', 20, type=int)
    external_id = request.args.get('externalId', 'test')
    description = request.args.get('description', 'VPN')
    
    # ПОДГОТАВЛИВАЕМ ЗАПРОС К LPAY
    headers = {
        "x-api-key": API_KEY,
        "x-api-secret": API_SECRET,
        "Content-Type": "application/json"
    }
    
    payload = {
        "amount": amount,
        "externalId": external_id,
        "description": description
    }
    
    try:
        response = requests.post(
            "https://api.lpayapp.xyz/invoices",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 201:
            result = response.json()
            payment_url = result.get("paymentUrl")
            if payment_url:
                # ВОЗВРАЩАЕМ ТОЛЬКО ССЫЛКУ БЕЗ ЛЮБОГО ТЕКСТА
                return payment_url
        
        # Если ошибка - возвращаем простой текст
        return "Ошибка при создании платежа"
        
    except Exception as e:
        return "Техническая ошибка"

@app.route('/check_payment', methods=['GET'])
def check_payment():
    """
    Проверка статуса платежа
    Возвращает простой текст для PuzzleBot в формате: message {текст}
    """
    ext_id = request.args.get('externalId')
    if not ext_id:
        return make_response(" Ошибка: не указан externalId", 400, {'Content-Type': 'text/plain; charset=utf-8'})

    # Заголовки для Lpay
    headers = {
        "x-api-key": API_KEY,
        "x-api-secret": API_SECRET,
        "Content-Type": "application/json"
    }
    
    try:
        # Запрос к API Lpay
        resp = requests.get(
            f"https://api.lpayapp.xyz/invoices?externalId={ext_id}",
            headers=headers,
            timeout=15
        )
        data = resp.json()
        
        if resp.status_code == 200 and data.get('items'):
            status = data['items'][0].get('status')
            if status == 'confirmed':
                msg = " ОПЛАЧЕНО! Ваш VPN ключ будет выдан."
            elif status == 'expired':
                msg = " Время оплаты вышло. Пожалуйста, создайте новый платёж."
            elif status == 'cancelled':
                msg = " Платёж отменён."
            else:
                msg = f" Платёж не подтверждён. Статус: {status}. Попробуйте позже."
        else:
            msg = " Платёж не найден. Проверьте ссылку или создайте новый."
            
        # Возвращаем только текст в формате для PuzzleBot
        return make_response(msg, 200, {'Content-Type': 'text/plain; charset=utf-8'})
        
    except Exception as e:
        logger.error(f"Ошибка при проверке платежа: {str(e)}")
        return make_response(" Ошибка при проверке платежа. Сервер Lpay может быть недоступен.", 500, {'Content-Type': 'text/plain; charset=utf-8'})

@app.route('/test_cors', methods=['GET', 'OPTIONS', 'POST'])
def test_cors():
    """
    Тестовый эндпоинт для проверки CORS
    """
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
    
    return jsonify({
        "status": "success",
        "message": "CORS работает!",
        "method": request.method,
        "user_agent": str(request.user_agent),
        "headers": {k: v for k, v in request.headers},
        "args": dict(request.args)
    })

if __name__ == '__main__':
    # Используем порт из переменной окружения или 5000 по умолчанию
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
