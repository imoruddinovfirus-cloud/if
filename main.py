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
# Поддерживает оба варианта: userId и chatId
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
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response

    amount = request.args.get('amount', 50, type=int)
    description = request.args.get('description', 'VPN payment')
    
    # БЕРЁМ externalId ИЗ ЗАПРОСА
    external_id = request.args.get('externalId')
    
    # Если externalId не передан или пустой — генерируем свой
    if not external_id or external_id == 'fin_{{user_id}}' or external_id == 'fin_{{chat_id}}':
        external_id = f"fin_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        logger.info(f"Сгенерирован новый externalId: {external_id}")
    
    # Сохраняем externalId для пользователя (по userId или chatId)
    user_id = request.args.get('userId')
    chat_id = request.args.get('chatId')
    
    if user_id:
        user_last_external_id[user_id] = external_id
        logger.info(f"Сохранён externalId {external_id} для userId {user_id}")
    if chat_id:
        user_last_external_id[chat_id] = external_id
        logger.info(f"Сохранён externalId {external_id} для chatId {chat_id}")
    
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
        
        if response_lpay.status_code == 201:
            payment_url = result.get("paymentUrl")
            return jsonify({
                "success": True,
                "paymentUrl": payment_url,
                "externalId": external_id,
                "message": f"✅ Ссылка на оплату: {payment_url}\n\nСсылка действительна 60 минут.\n\n🆔 Ваш ID платежа: {external_id}"
            })
        else:
            return jsonify({
                "success": False,
                "message": f"❌ Ошибка: {result.get('message', 'Попробуйте другую сумму')}"
            }), 400
    except Exception as e:
        logger.error(f"Ошибка создания инвойса: {str(e)}")
        return jsonify({
            "success": False,
            "message": "❌ Техническая ошибка. Попробуйте позже."
        }), 500

@app.route('/health', methods=['GET'])
def health():
    return "OK"

@app.route('/check_payment', methods=['GET'])
def check_payment():
    user_id = request.args.get('userId')
    chat_id = request.args.get('chatId')
    external_id = request.args.get('externalId')
    
    # Если передан userId или chatId, берём сохранённый externalId
    if not external_id:
        if user_id:
            external_id = user_last_external_id.get(user_id)
        elif chat_id:
            external_id = user_last_external_id.get(chat_id)
        
        if not external_id:
            return jsonify({
                "success": False,
                "message": "❌ Нет активных платежей. Сначала создайте платёж через /pay_fin"
            }), 404
    
    if not external_id:
        return jsonify({
            "success": False,
            "message": "❌ Ошибка: не передан externalId, userId или chatId"
        }), 400
    
    # Реальная проверка через API Lpay
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
        logger.info(f"Проверка платежа {external_id}: статус {resp.status_code}")
        
        if resp.status_code == 200 and result.get('items'):
            status = result['items'][0].get('status')
            if status == 'confirmed':
                return jsonify({"success": True, "message": "✅ Оплата подтверждена!"})
            elif status == 'expired':
                return jsonify({"success": False, "message": "❌ Время оплаты вышло"})
            else:
                return jsonify({"success": False, "message": f"⏳ Статус: {status}"})
        else:
            return jsonify({"success": False, "message": "❌ Платёж не найден"}), 404
    except Exception as e:
        logger.error(f"Ошибка проверки: {str(e)}")
        return jsonify({"success": False, "message": f"❌ Ошибка: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
