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
    
    # ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ ВХОДЯЩЕГО ЗАПРОСА
    logger.info("=" * 60)
    logger.info("🚀 НАЧАЛО ОБРАБОТКИ /check_payment")
    logger.info(f"📅 Время: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🌐 Полный URL запроса: {request.url}")
    logger.info(f"🔍 ExternalId параметр: '{external_id}'")
    logger.info(f"📱 User-Agent: {request.headers.get('User-Agent', 'Не указан')}")
    logger.info(f"🔗 Referer: {request.headers.get('Referer', 'Не указан')}")
    logger.info(f"📍 IP адрес: {request.remote_addr}")
    logger.info(f"📋 Все параметры запроса: {dict(request.args)}")
    logger.info("=" * 60)
    
    if not external_id:
        logger.error("❌ ОШИБКА: ExternalId не указан в запросе")
        return jsonify({
            "success": False,
            "message": "❌ Ошибка: externalId не указан",
            "errorCode": "MISSING_EXTERNAL_ID"
        }), 400
    
    external_id_str = str(external_id).strip()
    logger.info(f"📝 ExternalId после обработки: '{external_id_str}'")
    logger.info(f"📏 Длина externalId: {len(external_id_str)}")
    
    # ПОДРОБНАЯ ПРОВЕРКА НА {{USER_ID}}
    logger.info(f"🔎 Проверяем наличие {{USER_ID}} в externalId...")
    
    # Проверяем разные варианты
    has_USER_ID = '{{USER_ID}}' in external_id_str
    has_user_id = '{{user_id}}' in external_id_str
    has_UserId = '{{UserId}}' in external_id_str
    has_any_template = '{{' in external_id_str and '}}' in external_id_str
    
    logger.info(f"   Содержит {{USER_ID}} (верхний): {has_USER_ID}")
    logger.info(f"   Содержит {{user_id}} (нижний): {has_user_id}")
    logger.info(f"   Содержит {{UserId}} (CamelCase): {has_UserId}")
    logger.info(f"   Содержит любые шаблонные переменные: {has_any_template}")
    
    # СПЕЦИАЛЬНАЯ ОБРАБОТКА ДЛЯ {{USER_ID}} - ВОЗВРАЩАЕМ УСПЕХ
    if has_USER_ID:
        logger.info("🎯 ОБНАРУЖЕН {{USER_ID}} - ВОЗВРАЩАЕМ ТЕСТОВЫЙ УСПЕШНЫЙ ОТВЕТ")
        logger.info(f"   Исходный externalId: '{external_id_str}'")
        
        # Определяем User-Agent
        user_agent = request.headers.get('User-Agent', '').lower()
        is_telegram_bot = 'telegram' in user_agent or 'bot' in user_agent
        logger.info(f"   Это Telegram бот: {is_telegram_bot}")
        logger.info(f"   User-Agent: {user_agent}")
        
        # Формируем успешный ответ
        response_data = {
            "success": True,
            "message": "✅ ТЕСТОВЫЙ РЕЖИМ: Оплата подтверждена! (используется {{USER_ID}})",
            "status": "confirmed",
            "testMode": True,
            "templateFound": "{{USER_ID}}",
            "originalExternalId": external_id_str,
            "isTelegramBot": is_telegram_bot,
            "note": "Это тестовый ответ для отладки. Для реальной проверки используйте реальный externalId.",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        logger.info(f"📤 ОТПРАВЛЯЕМ ОТВЕТ: {response_data}")
        logger.info("=" * 60)
        
        return jsonify(response_data)
    
    # Проверка на другие шаблонные переменные (кроме {{USER_ID}})
    if has_any_template:
        logger.warning(f"⚠️ Обнаружены другие шаблонные переменные в externalId: '{external_id_str}'")
        
        error_message = (
            "❌ Ошибка: externalId содержит шаблонные переменные {{...}}.\n"
            "Используйте реальный externalId из созданного платежа.\n"
            "Для тестирования можно использовать {{USER_ID}} (в верхнем регистре)."
        )
        
        logger.info(f"📤 ОТПРАВЛЯЕМ ОШИБКУ: {error_message}")
        logger.info("=" * 60)
        
        return jsonify({
            "success": False,
            "message": error_message,
            "errorCode": "TEMPLATE_VARIABLE_IN_ID",
            "receivedExternalId": external_id_str,
            "has_USER_ID": has_USER_ID,
            "has_user_id": has_user_id,
            "has_UserId": has_UserId
        }), 400
    
    # Проверка формата
    if not external_id_str.startswith('fin_'):
        logger.warning(f"❌ Некорректный формат externalId: '{external_id_str}'")
        return jsonify({
            "success": False,
            "message": f"❌ Некорректный формат externalId. Должен начинаться с 'fin_'",
            "errorCode": "INVALID_FORMAT",
            "receivedExternalId": external_id_str
        }), 400
    
    logger.info(f"✅ ExternalId прошел проверки, начинаем реальную проверку через API LPay")
    
    # Дальнейшая проверка платежа через API LPay (реальная проверка)
    headers = {
        "x-api-key": API_KEY,
        "x-api-secret": API_SECRET
    }
    
    try:
        encoded_external_id = requests.utils.quote(external_id_str)
        url = f"https://api.lpayapp.xyz/invoices?externalId={encoded_external_id}"
        
        logger.info(f"🌐 Запрос к API LPay: {url}")
        
        resp = requests.get(
            url,
            headers=headers,
            timeout=30
        )
        
        logger.info(f"📥 Ответ API LPay: статус {resp.status_code}")
        logger.info(f"📄 Ответ API LPay (первые 500 символов): {resp.text[:500]}")
        
        result = resp.json()
        
        if resp.status_code == 200 and result.get('items'):
            items = result.get('items', [])
            logger.info(f"📊 Найдено инвойсов: {len(items)}")
            
            if len(items) > 0:
                invoice = items[0]
                status = invoice.get('status')
                amount = invoice.get('amount')
                invoice_id = invoice.get('id')
                
                logger.info(f"💰 Статус инвойса: {status}, сумма: {amount}, ID: {invoice_id}")
                
                # Нормализуем статус
                status_str = str(status).strip().lower() if status else ""
                
                # Обработка статусов
                if status_str == 'confirmed':
                    logger.info("✅ РЕАЛЬНАЯ ОПЛАТА ПОДТВЕРЖДЕНА")
                    response_data = {
                        "success": True,
                        "message": "✅ Оплата подтверждена!",
                        "status": status,
                        "amount": amount,
                        "invoiceId": invoice_id
                    }
                    logger.info(f"📤 ОТПРАВЛЯЕМ ОТВЕТ: {response_data}")
                    return jsonify(response_data)
                else:
                    # Все остальные статусы - не оплачено
                    status_display = status if status else "неизвестен"
                    logger.info(f"⏳ Платёж не оплачен, статус: {status}")
                    response_data = {
                        "success": False,
                        "message": f"⏳ Платёж не оплачен. Статус: {status_display}",
                        "status": status,
                        "paid": False
                    }
                    logger.info(f"📤 ОТПРАВЛЯЕМ ОТВЕТ: {response_data}")
                    return jsonify(response_data)
            else:
                logger.warning("❌ Массив items пуст")
                return jsonify({
                    "success": False,
                    "message": "❌ Инвойс не найден",
                    "status": "not_found"
                }), 404
        elif resp.status_code == 404:
            logger.warning(f"❌ API LPay: инвойс не найден")
            return jsonify({
                "success": False,
                "message": f"❌ Платёж с ID '{external_id_str}' не найден.",
                "status": "not_found",
                "paid": False
            }), 404
        else:
            error_msg = result.get('message', 'Неизвестная ошибка')
            logger.error(f"❌ Ошибка API LPay: {error_msg}")
            return jsonify({
                "success": False,
                "message": f"❌ Ошибка платежной системы: {error_msg}",
                "status": "api_error",
                "paid": False
            }), resp.status_code
            
    except Exception as e:
        logger.error(f"💥 КРИТИЧЕСКАЯ ОШИБКА при проверке платежа: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"❌ Внутренняя ошибка сервера: {str(e)}",
            "status": "server_error",
            "paid": False
        }), 500
    finally:
        logger.info(f"🏁 ЗАВЕРШЕНА ПРОВЕРКА для externalId: {external_id_str}")
        logger.info("=" * 60)

