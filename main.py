from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import requests
import time
import logging
import re
import uuid

app = Flask(__name__)

# ВКЛЮЧАЕМ CORS ДЛЯ ВСЕХ ДОМЕНОВ БЕЗ ОГРАНИЧЕНИЙ
CORS(app, resources={r"/*": {"origins": "*"}})

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

API_KEY = "06ff2425-dcf0-42ed-85d3-419bb4bbe927"
API_SECRET = "8e280987-ebba-4c95-af1c-90934e372774"

# Токен твоего бота (ЗАМЕНИ НА СВОЙ!)
BOT_TOKEN = "ТОКЕН_ВАШЕГО_БОТА"

# Хранилище ссылок на оплату (message_id -> payment_url)
payment_messages = {}

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept,Origin,User-Agent,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Max-Age', '3600')
    return response

def send_telegram_message(chat_id, text):
    """Отправляет сообщение пользователю в Telegram"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload, timeout=10)
        return response.ok
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        return False

def extract_chat_id_from_external_id(external_id):
    """Извлекает chat_id из externalId (формат: fin_1234567890_abc)"""
    try:
        parts = external_id.split('_')
        if len(parts) >= 2:
            return int(parts[1])
    except:
        pass
    return None

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
    chat_id = request.args.get('chatId')
    
    # Генерируем уникальный externalId с chat_id
    if chat_id:
        unique_id = f"fin_{chat_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    else:
        unique_id = f"fin_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    headers = {
        "x-api-key": API_KEY,
        "x-api-secret": API_SECRET,
        "Content-Type": "application/json"
    }
    
    payload = {
        "amount": amount,
        "externalId": unique_id,
        "description": description,
        "callbackUrl": "https://if-production.up.railway.app/lpay_webhook"
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


@app.route('/lpay_webhook', methods=['POST'])
def lpay_webhook():
    """Принимает уведомления от Lpay об оплате"""
    try:
        data = request.json
        logger.info(f"Webhook получен: {data}")
        
        # Проверяем, что это уведомление об успешной оплате
        if data.get('event') == 'invoice.status_changed' and data.get('status') == 'confirmed':
            external_id = data.get('externalId')
            
            # Извлекаем chat_id из external_id
            chat_id = extract_chat_id_from_external_id(external_id)
            
            if chat_id:
                # Отправляем сообщение пользователю
                message = (
                    "✅ <b>Оплата подтверждена!</b>\n\n"
                    "Ваш платёж успешно прошёл.\n"
                    "Спасибо за покупку!"
                )
                send_telegram_message(chat_id, message)
                logger.info(f"Сообщение отправлено пользователю {chat_id}")
            else:
                logger.warning(f"Не удалось извлечь chat_id из externalId: {external_id}")
        
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Ошибка в webhook: {e}")
        return jsonify({"status": "error"}), 500


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
            items = result.get('items', [])
            if len(items) > 0:
                status = items[0].get('status')
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
                elif status == 'cancelled':
                    return jsonify({
                        "success": False,
                        "message": "❌ Платёж отменён",
                        "status": status
                    })
                else:
                    return jsonify({
                        "success": False,
                        "message": f"⏳ Ожидаем оплату... Статус: {status}",
                        "status": status
                    })
        
        return jsonify({
            "success": False,
            "message": "❌ Платёж не найден"
        }), 404
        
    except Exception as e:
        logger.error(f"Ошибка проверки: {e}")
        return jsonify({
            "success": False,
            "message": "❌ Ошибка при проверке"
        }), 500


@app.route('/health', methods=['GET', 'OPTIONS'])
def health():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    return "OK"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
