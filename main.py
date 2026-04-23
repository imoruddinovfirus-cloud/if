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
    from flask import make_response, jsonify
    
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
    
    amount = request.args.get('amount', 20, type=int)
    external_id = request.args.get('externalId')
    description = request.args.get('description', 'VPN payment')
    
    if not external_id:
        return jsonify({
            "status": "error",
            "message": "externalId is required"
        }), 400
    
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
        response = requests.post(
            "https://api.lpayapp.xyz/invoices",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        result = response.json()
        
        if response.status_code == 201:
            payment_url = result.get('paymentUrl')
            # Возвращаем JSON, который PuzzleBot точно поймёт
            return jsonify({
                "status": "success",
                "paymentUrl": payment_url,
                "message": "Ссылка создана"
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": result.get('message', 'Unknown error')
            }), 400
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "Server error"
        }), 500

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
