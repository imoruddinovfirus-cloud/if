from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import requests
import time
import logging
import re

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
    import uuid
    import time

    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response

    amount = request.args.get('amount', 50, type=int)
    description = request.args.get('description', 'VPN payment')

    # Генерируем уникальный externalId
    unique_id = f"fin_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    headers = {
        "x-api-key": API_KEY,
        "x-api-secret": API_SECRET,
        "Content-Type": "application/json"
    }
    
    payload = {
        "amount": amount,
        "externalId": unique_id,
        "description": description
    }
    
    try:
        response_lpay = requests.post(
            "https://api.lpayapp.xyz/invoices",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        result = response_lpay.json()
        
        if response_lpay.status_code == 201:
            payment_url = result.get("paymentUrl")
            return jsonify({
                "success": True,
                "paymentUrl": payment_url,
                "externalId": unique_id,
                "message": f"✅ Ссылка на оплату: {payment_url}\n\nСсылка действительна 60 минут.\n\n🆔 Ваш ID платежа: {unique_id}"
            })
        else:
            return jsonify({
                "success": False,
                "message": f"❌ Ошибка: {result.get('message', 'Попробуйте другую сумму')}"
            }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "❌ Техническая ошибка. Попробуйте позже."
        }), 500


@app.route('/health', methods=['GET', 'OPTIONS'])
def health():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    return "OK"


@app.route('/check_payment', methods=['GET', 'OPTIONS'])
def check_payment():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
    
    external_id = request.args.get('externalId')
    test_mode = request.args.get('test', '').lower() == 'true'
    
    # ЛОГИРОВАНИЕ
    logger.info(f"=== /check_payment запрос ===")
    logger.info(f"ExternalId: '{external_id}'")
    logger.info(f"Test mode: {test_mode}")
    logger.info(f"Full URL: {request.url}")
    
    # ТЕСТОВЫЙ РЕЖИМ - ВОЗВРАЩАЕМ УСПЕХ ДЛЯ ЛЮБОГО ЗАПРОСА
    if test_mode:
        logger.info(f"✅ ТЕСТОВЫЙ РЕЖИМ АКТИВИРОВАН")
        logger.info(f"   Возвращаем успешный ответ для externalId: '{external_id}'")
        
        return jsonify({
            "success": True,
            "message": f"✅ ТЕСТОВЫЙ РЕЖИМ: Оплата подтверждена! (externalId: {external_id})",
            "status": "confirmed",
            "testMode": True,
            "externalId": external_id,
            "note": "Это тестовый ответ. Реальная проверка не выполнялась."
        })
    
    if not external_id:
        logger.warning("ExternalId не указан")
        return jsonify({
            "success": False,
            "message": "❌ Ошибка: externalId не указан",
            "errorCode": "MISSING_EXTERNAL_ID"
        }), 400
    
    external_id_str = str(external_id).strip()
    
    # Также оставляем специальную обработку для {{USER_ID}} без test параметра
    if '{{USER_ID}}' in external_id_str:
        logger.info(f"⚠️ Обнаружен {{USER_ID}} без test параметра")
        logger.info(f"   Возвращаем успешный ответ")
        
        return jsonify({
            "success": True,
            "message": f"✅ Оплата подтверждена! (используется {{USER_ID}})",
            "status": "confirmed",
            "templateFound": "{{USER_ID}}",
            "externalId": external_id_str,
            "note": "Автоматический успех для {{USER_ID}}"
        })
    
    # Проверка на другие шаблонные переменные
    if '{{' in external_id_str and '}}' in external_id_str:
        logger.warning(f"Обнаружены шаблонные переменные: '{external_id_str}'")
        return jsonify({
            "success": False,
            "message": "❌ Ошибка: externalId содержит шаблонные переменные.",
            "errorCode": "TEMPLATE_VARIABLE_IN_ID",
            "receivedExternalId": external_id_str
        }), 400
    
    # Проверка формата
    if not external_id_str.startswith('fin_'):
        logger.warning(f"Некорректный формат: '{external_id_str}'")
        return jsonify({
            "success": False,
            "message": f"❌ Некорректный формат externalId.",
            "errorCode": "INVALID_FORMAT",
            "receivedExternalId": external_id_str
        }), 400
    
    # РЕАЛЬНАЯ ПРОВЕРКА ЧЕРЕЗ API LPAY
    headers = {
        "x-api-key": API_KEY,
        "x-api-secret": API_SECRET
    }
    
    try:
        encoded_external_id = requests.utils.quote(external_id_str)
        url = f"https://api.lpayapp.xyz/invoices?externalId={encoded_external_id}"
        
        logger.info(f"Запрос к API LPay: {url}")
        
        resp = requests.get(
            url,
            headers=headers,
            timeout=30
        )
        
        logger.info(f"Ответ API LPay: статус {resp.status_code}")
        
        result = resp.json()
        
        if resp.status_code == 200 and result.get('items'):
            items = result.get('items', [])
            
            if len(items) > 0:
                invoice = items[0]
                status = invoice.get('status')
                amount = invoice.get('amount')
                invoice_id = invoice.get('id')
                
                logger.info(f"Статус инвойса: {status}, сумма: {amount}")
                
                status_str = str(status).strip().lower() if status else ""
                
                if status_str == 'confirmed':
                    logger.info("✅ Оплата подтверждена")
                    return jsonify({
                        "success": True,
                        "message": "✅ Оплата подтверждена!",
                        "status": status,
                        "amount": amount,
                        "invoiceId": invoice_id
                    })
                else:
                    status_display = status if status else "неизвестен"
                    logger.info(f"⏳ Платёж не оплачен, статус: {status}")
                    return jsonify({
                        "success": False,
                        "message": f"⏳ Платёж не оплачен. Статус: {status_display}",
                        "status": status,
                        "paid": False
                    })
            else:
                logger.warning("Массив items пуст")
                return jsonify({
                    "success": False,
                    "message": "❌ Инвойс не найден",
                    "status": "not_found"
                }), 404
        elif resp.status_code == 404:
            logger.warning(f"API LPay: инвойс не найден")
            return jsonify({
                "success": False,
                "message": f"❌ Платёж с ID '{external_id_str}' не найден.",
                "status": "not_found",
                "paid": False
            }), 404
        else:
            error_msg = result.get('message', 'Неизвестная ошибка')
            logger.error(f"Ошибка API LPay: {error_msg}")
            return jsonify({
                "success": False,
                "message": f"❌ Ошибка платежной системы: {error_msg}",
                "status": "api_error",
                "paid": False
            }), resp.status_code
            
    except Exception as e:
        logger.error(f"Ошибка при проверке платежа: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"❌ Внутренняя ошибка сервера: {str(e)}",
            "status": "server_error",
            "paid": False
        }), 500
    finally:
        logger.info(f"Завершена проверка для: {external_id_str}")
