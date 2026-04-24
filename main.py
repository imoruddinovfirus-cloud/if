from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import requests
import time
import logging
import uuid

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

API_KEY = "06ff2425-dcf0-42ed-85d3-419bb4bbe927"
API_SECRET = "8e280987-ebba-4c95-af1c-90934e372774"

# Хранилище последнего платежа для каждого пользователя
# { "123456789": "fin_1777026320_6857350c" }
user_last_external_id = {}

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', '*')
    response.headers.add('Access-Control-Allow-Methods', '*')
    return response

@app.route('/create_invoice_get', methods=['GET', 'OPTIONS'])
def create_invoice_get():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    amount = request.args.get('amount', 50, type=int)
    description = request.args.get('description', 'VPN payment')
    user_id = request.args.get('userId')
    
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
            
            # СОХРАНЯЕМ ПОСЛЕДНИЙ EXTERNALID ДЛЯ ПОЛЬЗОВАТЕЛЯ
            if user_id:
                user_last_external_id[user_id] = unique_id
                logger.info(f"Сохранён externalId {unique_id} для пользователя {user_id}")
            
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

@app.route('/check_payment', methods=['GET'])
def check_payment():
    user_id = request.args.get('userId')
    
    if not user_id:
        return jsonify({
            "success": False,
            "message": "❌ Ошибка: userId не указан"
        }), 400
    
    # БЕРЁМ СОХРАНЁННЫЙ EXTERNALID ПОСЛЕДНЕГО ПЛАТЕЖА
    external_id = user_last_external_id.get(user_id)
    
    if not external_id:
        return jsonify({
            "success": False,
            "message": "❌ У вас нет активных платежей. Сначала создайте платёж через /pay_fin"
        }), 404
    
    headers = {
        "x-api-key": API_KEY,
        "x-api-secret": API_SECRET
    }
    
    try:
        resp = requests.get(
            f"https://api.lpayapp.xyz/invoices?externalId={external_id}",
            headers=headers,
            timeout=30
        )
        
        result = resp.json()
        
        if resp.status_code == 200 and result.get('items'):
            status = result['items'][0].get('status')
            if status == 'confirmed':
                return jsonify({
                    "success": True,
                    "message": "✅ Оплата подтверждена!",
                    "status": status
                })
            elif status == 'expired':
                return jsonify({
                    "success": False,
                    "message": "❌ Время оплаты вышло",
                    "status": status
                })
            else:
                return jsonify({
                    "success": False,
                    "message": f"⏳ Ожидаем оплату... Статус: {status}",
                    "status": status
                })
        else:
            return jsonify({
                "success": False,
                "message": "❌ Платёж не найден"
            }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "❌ Ошибка при проверке"
        }), 500

@app.route('/health', methods=['GET'])
def health():
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
