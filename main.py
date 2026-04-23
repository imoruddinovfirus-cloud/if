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
    # ОБРАБОТКА OPTIONS ДЛЯ CORS
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
    
    # Получаем параметры из URL
    amount = request.args.get('amount', 500, type=int)
    external_id = request.args.get('externalId', f'test_{int(time.time())}')
    description = request.args.get('description', 'VPN payment')
    
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
        response_lpay = requests.post(
            "https://api.lpayapp.xyz/invoices",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        result = response_lpay.json()
        
        # Успех — возвращаем ссылку
        if response_lpay.status_code == 201:
            payment_url = result.get("paymentUrl")
            invoice_id = result.get("invoiceId")
            response_data = {
                "success": True,
                "paymentUrl": payment_url,
                "invoiceId": invoice_id,
                "externalId": external_id,
                "message": f"✅ Ссылка на оплату: {payment_url}\n\nСсылка действительна 60 минут."
            }
            return jsonify(response_data)
        
        # Ошибка No available traders
        if "No available traders" in str(result):
            response_data = {
                "success": False,
                "message": "❌ Платёжный сервис временно недоступен. Попробуйте 2-3 минуты.",
                "error": "no_traders"
            }
            return jsonify(response_data)
        
        # Любая другая ошибка
        response_data = {
            "success": False,
            "message": f"❌ Ошибка платежного сервиса: {result.get('message', 'Попробуйте позже')}",
            "error": "lpay_error"
        }
        return jsonify(response_data)
        
    except Exception as e:
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


@app.route('/check_by_link', methods=['GET'])
def check_by_link():
    payment_link = request.args.get('link')
    if not payment_link:
        return make_response("❌ Ошибка: ссылка не передана")
    
    # Извлекаем invoiceId из ссылки
    match = re.search(r'pay\.lpayapp\.xyz/([a-f0-9-]+)', payment_link)
    if not match:
        return make_response("❌ Ошибка: неверный формат ссылки")
    
    invoice_id = match.group(1)
    
    headers = {
        "x-api-key": API_KEY,
        "x-api-secret": API_SECRET
    }
    
    try:
        resp = requests.get(
            f"https://api.lpayapp.xyz/invoices/{invoice_id}",
            headers=headers,
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            status = data.get('status')
            
            if status == 'confirmed':
                return make_response("✅ Оплата подтверждена!")
            elif status == 'expired':
                return make_response("❌ Время оплаты вышло")
            elif status == 'cancelled':
                return make_response("❌ Платёж отменён")
            else:
                return make_response(f"⏳ Ожидаем оплату... Статус: {status}")
        else:
            return make_response("❌ Платёж не найден")
    except Exception as e:
        return make_response("❌ Ошибка при проверке")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
