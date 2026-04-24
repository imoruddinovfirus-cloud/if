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
    
    # Логируем входящий запрос
    logger.info(f"=== ВХОДЯЩИЙ ЗАПРОС check_payment ===")
    logger.info(f"Время: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Полный URL: {request.url}")
    logger.info(f"ExternalId: '{external_id}'")
    logger.info(f"User-Agent: {request.headers.get('User-Agent', 'Не указан')}")
    
    if not external_id:
        logger.warning("ExternalId не указан")
        return jsonify({
            "success": False,
            "message": "❌ Ошибка: externalId не указан",
            "errorCode": "MISSING_EXTERNAL_ID"
        }), 400
    
    external_id_str = str(external_id).strip()
    
    # СПЕЦИАЛЬНАЯ ОБРАБОТКА ДЛЯ {{USER_ID}} - ВОЗВРАЩАЕМ УСПЕХ ДЛЯ ТЕСТИРОВАНИЯ
    if '{{USER_ID}}' in external_id_str:
        logger.info(f"⚠️ Обнаружена тестовая переменная {{USER_ID}} в externalId: '{external_id_str}'")
        logger.info(f"   Возвращаем тестовый успешный ответ")
        
        # Определяем User-Agent
        user_agent = request.headers.get('User-Agent', '').lower()
        is_telegram_bot = 'telegram' in user_agent or 'bot' in user_agent
        
        # Возвращаем успешный ответ для тестирования
        return jsonify({
            "success": True,
            "message": "✅ ТЕСТОВЫЙ РЕЖИМ: Оплата подтверждена! (используется {{USER_ID}})",
            "status": "confirmed",
            "testMode": True,
            "templateFound": "{{USER_ID}}",
            "isTelegramBot": is_telegram_bot,
            "note": "Это тестовый ответ. Для реальной проверки используйте реальный externalId."
        })
    
    # Проверка на другие шаблонные переменные (кроме {{USER_ID}})
    if '{{' in external_id_str and '}}' in external_id_str:
        logger.warning(f"⚠️ Обнаружены шаблонные переменные в externalId: '{external_id_str}'")
        
        error_message = (
            "❌ Ошибка: externalId содержит шаблонные переменные {{...}}.\n"
            "Используйте реальный externalId из созданного платежа.\n"
            "Для тестирования можно использовать {{USER_ID}}."
        )
        
        return jsonify({
            "success": False,
            "message": error_message,
            "errorCode": "TEMPLATE_VARIABLE_IN_ID",
            "receivedExternalId": external_id_str
        }), 400
    
    # Проверка формата
    if not external_id_str.startswith('fin_'):
        logger.warning(f"Некорректный формат: '{external_id_str}'")
        return jsonify({
            "success": False,
            "message": f"❌ Некорректный формат externalId. Должен начинаться с 'fin_'",
            "errorCode": "INVALID_FORMAT",
            "receivedExternalId": external_id_str
        }), 400
    
    # Дальнейшая проверка платежа через API LPay (реальная проверка)
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
                
                # Нормализуем статус
                status_str = str(status).strip().lower() if status else ""
                
                # Обработка статусов
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
                    # Все остальные статусы - не оплачено
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
        logger.error(f"Ошибка при проверке платежа: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"❌ Внутренняя ошибка сервера: {str(e)}",
            "status": "server_error",
            "paid": False
        }), 500
    finally:
        logger.info(f"Завершена проверка для: {external_id_str}")

