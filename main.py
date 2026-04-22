from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import time
import logging

app = Flask(__name__)

# Включаем CORS для всех доменов и всех методов
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization", "Accept", "Origin", "User-Agent"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": 3600
    }
})

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = "06ff2425-dcf0-42ed-85d3-419bb4bbe927"
API_SECRET = "8e280987-ebba-4c95-af1c-90934e372774"

@app.route('/create_invoice_get', methods=['GET', 'OPTIONS'])
def create_invoice_get():
    """
    Версия для GET запросов (для PuzzleBot)
    """
    # Логируем входящий запрос
    logger.info(f"Входящий запрос: {request.method} {request.url}")
    logger.info(f"Заголовки: {dict(request.headers)}")
    logger.info(f"Аргументы: {request.args}")
    
    # Обработка preflight запросов CORS (OPTIONS)
    if request.method == 'OPTIONS':
        logger.info("Обработка OPTIONS запроса")
        return '', 200
    
    # Получаем параметры из URL
    amount = request.args.get('amount', 500, type=int)
    external_id = request.args.get('externalId', f'test_{int(time.time())}')
    description = request.args.get('description', 'VPN payment')
    
    logger.info(f"Параметры: amount={amount}, externalId={external_id}, description={description}")
    
    headers = {
        "x-api-key": API_KEY,
        "x-api-secret": API_SECRET,
        "Content-Type": "application/json",
        "User-Agent": "PuzzleBot/1.0"
    }
    
    payload = {
        "amount": amount,
        "externalId": external_id,
        "description": description
    }
    
    try:
        logger.info(f"Отправка запроса в Lpay: {payload}")
        
        response = requests.post(
            "https://api.lpayapp.xyz/invoices",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        result = response.json()
        logger.info(f"Ответ Lpay: status={response.status_code}, result={result}")
        
        # Успех — возвращаем ссылку
        if response.status_code == 201:
            payment_url = result.get("paymentUrl")
            response_data = {
                "success": True,
                "message": f"✅ Ссылка на оплату: {payment_url}\n\nСсылка действительна 60 минут.",
                "paymentUrl": payment_url,
                "invoiceId": result.get("invoiceId"),
                "externalId": external_id
            }
            logger.info(f"Успешный ответ: {response_data}")
            return jsonify(response_data)
        
        # Ошибка No available traders
        if "No available traders" in str(result):
            response_data = {
                "success": False,
                "message": "❌ Платёжный сервис временно недоступен. Попробуйте другую сумму или повторите через 10-15 минут.",
                "error": "no_traders"
            }
            logger.warning(f"Нет трейдеров: {response_data}")
            return jsonify(response_data)
        
        # Любая другая ошибка
        response_data = {
            "success": False,
            "message": f"❌ Ошибка платежного сервиса: {result.get('message', 'Попробуйте позже')}",
            "error": "lpay_error"
        }
        logger.error(f"Ошибка Lpay: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Исключение: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "❌ Техническая ошибка. Попробуйте позже.",
            "error": "server_error"
        })

@app.route('/health', methods=['GET', 'OPTIONS'])
def health():
    if request.method == 'OPTIONS':
        return '', 200
    return "OK"

@app.route('/debug', methods=['GET', 'OPTIONS'])
def debug():
    """
    Эндпоинт для отладки - возвращает информацию о запросе
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    return jsonify({
        "method": request.method,
        "headers": dict(request.headers),
        "args": dict(request.args),
        "url": request.url,
        "remote_addr": request.remote_addr,
        "user_agent": str(request.user_agent)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
