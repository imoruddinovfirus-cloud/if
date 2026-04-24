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
    demo_mode = request.args.get('demo', '').lower() == 'true'
    
    # Активируем тестовый режим если передан test=true или demo=true
    is_test_mode = test_mode or demo_mode
    
    if not external_id:
        return jsonify({
            "success": False,
            "message": "❌ Ошибка: externalId не указан"
        }), 400
    
    # ТЕСТОВЫЙ РЕЖИМ: возвращаем успех без проверки реального платежа
    if is_test_mode:
        logger.info(f"Тестовый режим активирован для externalId: {external_id}")
        return jsonify({
            "success": True,
            "message": f"✅ ТЕСТОВЫЙ РЕЖИМ: Оплата подтверждена! (externalId: {external_id})",
            "testMode": True,
            "externalId": external_id
        })
    
    # Проверка формата externalId (опционально, для отладки)
    if '{{' in external_id or '}}' in external_id:
        return jsonify({
            "success": False,
            "message": "❌ Ошибка: externalId содержит шаблонные переменные. Используйте реальный externalId из созданного платежа или добавьте параметр test=true для тестового режима."
        }), 400
    
    headers = {
        "x-api-key": API_KEY,
        "x-api-secret": API_SECRET
    }
    
    try:
        # Кодируем externalId для безопасной передачи в URL
        encoded_external_id = requests.utils.quote(external_id)
        url = f"https://api.lpayapp.xyz/invoices?externalId={encoded_external_id}"
        
        resp = requests.get(
            url,
            headers=headers,
            timeout=30
        )
        
        # Логируем для отладки
        logger.debug(f"Check payment request: {url}")
        logger.debug(f"Response status: {resp.status_code}")
        logger.debug(f"Response content: {resp.text}")
        
        result = resp.json()
        
        if resp.status_code == 200 and result.get('items'):
            status = result['items'][0].get('status')
            if status == 'confirmed':
                return jsonify({
                    "success": True,
                    "message": "✅ Оплата подтверждена!"
                })
            elif status == 'expired':
                return jsonify({
                    "success": False,
                    "message": "❌ Время оплаты вышло"
                })
            elif status == 'cancelled':
                return jsonify({
                    "success": False,
                    "message": "❌ Платёж отменён"
                })
            else:
                return jsonify({
                    "success": False,
                    "message": f"⏳ Ожидаем оплату... Статус: {status}"
                })
        elif resp.status_code == 404:
            return jsonify({
                "success": False,
                "message": f"❌ Платёж с externalId '{external_id}' не найден. Убедитесь, что externalId корректен."
            }), 404
        else:
            return jsonify({
                "success": False,
                "message": f"❌ Ошибка API LPay: {result.get('message', 'Неизвестная ошибка')}"
            }), resp.status_code
            
    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "message": "❌ Таймаут при подключении к платежной системе"
        }), 504
    except requests.exceptions.ConnectionError:
        return jsonify({
            "success": False,
            "message": "❌ Ошибка подключения к платежной системе"
        }), 502
    except Exception as e:
        logger.error(f"Error checking payment: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"❌ Внутренняя ошибка сервера: {str(e)}"
        }), 500
