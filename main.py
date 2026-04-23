from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import requests
import time
import logging

app = Flask(__name__)

# ВКЛЮЧАЕМ CORS ДЛЯ ВСЕХ ДОМЕНОВ БЕЗ ОГРАНИЧЕНИЙ
CORS(app, resources={r"/*": {"origins": "*"}})

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

API_KEY = "06ff2425-dcf0-42ed-85d3-419bb4bbe927"
API_SECRET = "8e280987-ebba-4c95-af1c-90934e372774"

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

@app.route('/create_invoice_get', methods=['GET', 'OPTIONS'])
def create_invoice_get():
    """
    Версия для GET запросов (для PuzzleBot)
    """
    # ЛОГИРУЕМ ВСЕ ДЕТАЛИ ЗАПРОСА
    logger.info("=" * 50)
    logger.info(f"МЕТОД: {request.method}")
    logger.info(f"URL: {request.url}")
    logger.info(f"ЗАГОЛОВКИ: {dict(request.headers)}")
    logger.info(f"АРГУМЕНТЫ: {request.args}")
    logger.info(f"USER-AGENT: {request.user_agent}")
    logger.info("=" * 50)
    
    # ОБРАБОТКА OPTIONS ДЛЯ CORS
    if request.method == 'OPTIONS':
        logger.info("ОБРАБОТКА OPTIONS ЗАПРОСА ДЛЯ CORS")
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
    
    # Получаем параметры из URL
    amount = request.args.get('amount', 500, type=int)
    external_id = request.args.get('externalId', f'test_{int(time.time())}')
    description = request.args.get('description', 'VPN payment')
    
    logger.info(f"ПАРАМЕТРЫ: amount={amount}, externalId={external_id}, description={description}")
    
    # ПОДГОТАВЛИВАЕМ ЗАПРОС К LPAY
    headers = {
        "x-api-key": API_KEY,
        "x-api-secret": API_SECRET,
        "Content-Type": "application/json",
        "User-Agent": str(request.user_agent)  # Передаем User-Agent от клиента
    }
    
    payload = {
        "amount": amount,
        "externalId": external_id,
        "description": description
    }
    
    try:
        logger.info(f"ОТПРАВКА В LPAY: {payload}")
        
        response = requests.post(
            "https://api.lpayapp.xyz/invoices",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        result = response.json()
        logger.info(f"ОТВЕТ LPAY: status={response.status_code}, result={result}")
        
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
            logger.info(f"УСПЕШНЫЙ ОТВЕТ: {response_data}")
            return jsonify(response_data)
        
        # Ошибка No available traders
        if "No available traders" in str(result):
            response_data = {
                "success": False,
                "message": "❌ Платёжный сервис временно недоступен. Попробуйте другую сумму или повторите через 10-15 минут.",
                "error": "no_traders"
            }
            logger.warning(f"НЕТ ТРЕЙДЕРОВ: {response_data}")
            return jsonify(response_data)
        
        # Любая другая ошибка
        response_data = {
            "success": False,
            "message": f"❌ Ошибка платежного сервиса: {result.get('message', 'Попробуйте позже')}",
            "error": "lpay_error"
        }
        logger.error(f"ОШИБКА LPAY: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"ИСКЛЮЧЕНИЕ: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "❌ Техническая ошибка. Попробуйте позже.",
            "error": "server_error"
        })

@app.route('/health', methods=['GET', 'OPTIONS'])
def health():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    return "OK"

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
    app.run(host='0.0.0.0', port=5000, debug=True)
# ... (остальной код)

@app.route('/check_payment', methods=['GET'])
def check_payment():
    from flask import make_response
    
    ext_id = request.args.get('externalId')
    if not ext_id:
        return make_response("❌ Ошибка: не указан externalId")

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
                msg = "✅ ОПЛАЧЕНО! Ваш VPN ключ будет выдан."
            elif status == 'expired':
                msg = "❌ Время оплаты вышло. Пожалуйста, создайте новый платёж."
            elif status == 'cancelled':
                msg = "❌ Платёж отменён."
            else:
                msg = f"⏳ Платёж не подтверждён. Статус: {status}. Попробуйте позже."
        else:
            msg = "❌ Платёж не найден. Проверьте ссылку или создайте новый."
            
        # Возвращаем только текст (PuzzleBot его точно поймёт)
        return make_response(msg)
        
    except Exception as e:
        return make_response("❌ Ошибка при проверке платежа. Сервер Lpay может быть недоступен.")
