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
    
    if not external_id:
        return jsonify({
            "success": False,
            "message": "❌ Ошибка: externalId не указан"
        }), 400
    
    # Проверка формата externalId (опционально, для отладки)
    if '{{' in external_id or '}}' in external_id:
        return jsonify({
            "success": False,
            "message": "❌ Ошибка: externalId содержит шаблонные переменные. Используйте реальный externalId из созданного платежа."
        }), 400
    
    headers = {
        "x-api-key": API_KEY,
        "x-api-secret": API_SECRET
    }
    
    try:
        # Кодируем externalId для безопасной передачи в URL
        encoded_external_id = requests.utils.quote(external_id)
        url = f"https://api.lpayapp.xyz/invoices?externalId={encoded_external_id}"
        
        logger.info(f"=== НАЧАЛО ПРОВЕРКИ ПЛАТЕЖА ===")
        logger.info(f"ExternalId: {external_id}")
        logger.info(f"Encoded externalId: {encoded_external_id}")
        logger.info(f"URL запроса: {url}")
        
        resp = requests.get(
            url,
            headers=headers,
            timeout=30
        )
        
        # Логируем полный ответ для отладки
        logger.info(f"Статус ответа API: {resp.status_code}")
        logger.info(f"Заголовки ответа: {dict(resp.headers)}")
        logger.info(f"Текст ответа: {resp.text}")
        
        result = resp.json()
        logger.info(f"JSON ответа: {result}")
        
        if resp.status_code == 200 and result.get('items'):
            items = result.get('items', [])
            logger.info(f"Найдено инвойсов: {len(items)}")
            
            if len(items) > 0:
                invoice = items[0]
                status = invoice.get('status')
                amount = invoice.get('amount')
                created_at = invoice.get('createdAt')
                invoice_id = invoice.get('id')
                description = invoice.get('description')
                
                logger.info(f"=== ДАННЫЕ ИНВОЙСА ===")
                logger.info(f"ID инвойса: {invoice_id}")
                logger.info(f"Статус: {status} (тип: {type(status)})")
                logger.info(f"Сумма: {amount}")
                logger.info(f"Дата создания: {created_at}")
                logger.info(f"Описание: {description}")
                logger.info(f"Весь инвойс: {invoice}")
                
                # ВАЖНО: Проверяем тип и значение статуса
                if not isinstance(status, str):
                    logger.warning(f"Статус не является строкой! Тип: {type(status)}, значение: {status}")
                
                # Строгая проверка статуса
                status_str = str(status).strip().lower() if status else ""
                logger.info(f"Обработанный статус (нижний регистр): '{status_str}'")
                
                # Обработка всех возможных статусов
                if status_str == 'confirmed':
                    logger.info("Статус 'confirmed' - оплата подтверждена")
                    return jsonify({
                        "success": True,
                        "message": "✅ Оплата подтверждена!",
                        "status": status,
                        "amount": amount,
                        "invoiceId": invoice_id
                    })
                elif status_str == 'expired':
                    logger.info("Статус 'expired' - время оплаты вышло")
                    return jsonify({
                        "success": False,
                        "message": "❌ Время оплаты вышло",
                        "status": status
                    })
                elif status_str == 'cancelled':
                    logger.info("Статус 'cancelled' - платёж отменён")
                    return jsonify({
                        "success": False,
                        "message": "❌ Платёж отменён",
                        "status": status
                    })
                elif status_str == 'assigned':
                    logger.info("Статус 'assigned' - платёж создан, но не оплачен")
                    return jsonify({
                        "success": False,
                        "message": "⏳ Платёж создан, но ещё не оплачен",
                        "status": status,
                        "note": "Статус 'assigned' означает, что инвойс создан, но оплата не произведена"
                    })
                elif status_str == 'pending':
                    logger.info("Статус 'pending' - ожидаем оплату")
                    return jsonify({
                        "success": False,
                        "message": "⏳ Ожидаем оплату...",
                        "status": status
                    })
                elif status_str == 'processing':
                    logger.info("Статус 'processing' - платёж обрабатывается")
                    return jsonify({
                        "success": False,
                        "message": "⏳ Платёж обрабатывается...",
                        "status": status
                    })
                elif status_str == 'failed':
                    logger.info("Статус 'failed' - платёж не удался")
                    return jsonify({
                        "success": False,
                        "message": "❌ Платёж не удался",
                        "status": status
                    })
                else:
                    # Для неизвестных статусов
                    logger.warning(f"Неизвестный статус: '{status}' (обработан как '{status_str}')")
                    return jsonify({
                        "success": False,
                        "message": f"⏳ Статус платежа: {status}",
                        "status": status,
                        "note": "Неизвестный статус платежа",
                        "rawStatus": status
                    })
            else:
                logger.warning(f"Массив items пуст для externalId: {external_id}")
                return jsonify({
                    "success": False,
                    "message": f"❌ Инвойс не найден в массиве items",
                    "status": "not_found_in_items"
                }), 404
        elif resp.status_code == 404:
            logger.warning(f"API вернуло 404 для externalId: {external_id}")
            return jsonify({
                "success": False,
                "message": f"❌ Платёж с externalId '{external_id}' не найден. Убедитесь, что externalId корректен.",
                "status": "not_found"
            }), 404
        else:
            error_msg = result.get('message', 'Неизвестная ошибка')
            logger.error(f"API LPay error: {error_msg}, статус: {resp.status_code}")
            return jsonify({
                "success": False,
                "message": f"❌ Ошибка API LPay: {error_msg}",
                "status": "api_error",
                "httpStatus": resp.status_code
            }), resp.status_code
            
    except requests.exceptions.Timeout:
        logger.error("Timeout connecting to LPay API")
        return jsonify({
            "success": False,
            "message": "❌ Таймаут при подключении к платежной системе",
            "status": "timeout"
        }), 504
    except requests.exceptions.ConnectionError:
        logger.error("Connection error to LPay API")
        return jsonify({
            "success": False,
            "message": "❌ Ошибка подключения к платежной системе",
            "status": "connection_error"
        }), 502
    except Exception as e:
        logger.error(f"Error checking payment: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"❌ Внутренняя ошибка сервера: {str(e)}",
            "status": "server_error"
        }), 500
    finally:
        logger.info(f"=== ЗАВЕРШЕНИЕ ПРОВЕРКИ ПЛАТЕЖА для externalId: {external_id} ===")
