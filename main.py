from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import requests
import time
import logging
import uuid

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
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept,Origin,User-Agent,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Max-Age', '3600')
    return response


@app.route('/create_invoice_get', methods=['GET', 'OPTIONS'])
def create_invoice_get():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response

    amount = request.args.get('amount', 50, type=int)
    description = request.args.get('description', 'VPN payment')
    external_id_param = request.args.get('externalId')

    # ЛОГИРОВАНИЕ ВХОДЯЩЕГО ЗАПРОСА
    logger.info(f"=== /create_invoice_get запрос ===")
    logger.info(f"Amount: {amount}, Description: {description}")
    logger.info(f"ExternalId параметр: '{external_id_param}'")
    logger.info(f"Полный URL: {request.url}")

    # ВАЖНО: Если externalId содержит шаблонные переменные, генерируем новый
    if external_id_param and ('{{' in external_id_param or '}}' in external_id_param):
        logger.info(f"⚠️ ExternalId содержит шаблонные переменные: '{external_id_param}'")
        logger.info(f"   Генерируем новый externalId вместо шаблона")
        
        # Генерируем уникальный externalId
        unique_id = f"fin_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        was_template = True
    else:
        # Используем переданный externalId или генерируем новый
        if external_id_param:
            unique_id = external_id_param
            was_template = False
        else:
            unique_id = f"fin_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            was_template = False
    
    headers = {
        "x-api-key": API_KEY,
        "x-api-secret": API_SECRET,
        "Content-Type": "application/json"
    }
    
    payload = {
        "amount": amount,
        "externalId": unique_id,  # Используем сгенерированный ID, а не шаблон
        "description": description
    }
    
    logger.info(f"📤 Отправляем в API LPay: externalId={unique_id}, amount={amount}")
    
    try:
        response_lpay = requests.post(
            "https://api.lpayapp.xyz/invoices",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        logger.info(f"📥 Ответ API LPay: статус {response_lpay.status_code}")
        
        result = response_lpay.json()
        
        if response_lpay.status_code == 201:
            payment_url = result.get("paymentUrl")
            
            response_data = {
                "success": True,
                "paymentUrl": payment_url,
                "externalId": unique_id,  # Возвращаем реальный externalId
                "message": f"✅ Ссылка на оплату: {payment_url}\n\nСсылка действительна 60 минут.\n\n🆔 Ваш ID платежа: {unique_id}"
            }
            
            # Добавляем информацию о шаблоне, если был
            if was_template:
                response_data["originalExternalId"] = external_id_param
                response_data["note"] = f"Шаблон {external_id_param} заменен на {unique_id}"
            
            logger.info(f"✅ Успешно создан инвойс: {unique_id}")
            return jsonify(response_data)
        else:
            error_msg = result.get('message', 'Неизвестная ошибка')
            logger.error(f"❌ Ошибка API LPay: {error_msg}")
            return jsonify({
                "success": False,
                "message": f"❌ Ошибка: {error_msg}",
                "apiError": True,
                "externalId": unique_id
            }), 400
    except Exception as e:
        logger.error(f"💥 Ошибка при создании инвойса: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "❌ Техническая ошибка. Попробуйте позже.",
            "exception": str(e)
        }), 500


@app.route('/health', methods=['GET', 'OPTIONS'])
def health():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    return "OK"


@app.route('/check_payment', methods=['GET'])
def check_payment():
    external_id = request.args.get('externalId')
    if not external_id:
        return jsonify({"status": "error", "message": "❌ Ошибка: externalId не указан"}), 400

    # Твои ключи к Lpay API
    headers = {
        "x-api-key": "06ff2425-dcf0-42ed-85d3-419bb4bbe927",
        "x-api-secret": "8e280987-ebba-4c95-af1c-90934e372774"
    }

    try:
        # Запрос к Lpay для получения статуса
        response = requests.get(
            f"https://api.lpayapp.xyz/invoices?externalId={external_id}",
            headers=headers,
            timeout=10
        )
        data = response.json()

        # Логика проверки ответа от Lpay
        if response.status_code == 200 and data.get('items'):
            # Нашли платёж, возвращаем его статус
            status = data['items'][0].get('status')
            if status == 'confirmed':
                return jsonify({"status": "confirmed", "message": "✅ Оплата подтверждена!"})
            elif status == 'expired':
                return jsonify({"status": "expired", "message": "❌ Время оплаты вышло"})
            else:
                return jsonify({"status": status, "message": f"⏳ Статус: {status}"})
        else:
            # Не нашли платёж с таким externalId
            return jsonify({"status": "not_found", "message": "❌ Платёж не найден"}), 404

    except Exception as e:
        return jsonify({"status": "error", "message": f"Ошибка сервера: {str(e)}"}), 5
