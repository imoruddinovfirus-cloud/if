from flask import Flask, request
import requests
import json
import os
import time

app = Flask(__name__)

# ==================== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ====================
PLATEGA_MERCHANT_ID = os.getenv('PLATEGA_MERCHANT_ID')
PLATEGA_SECRET = os.getenv('PLATEGA_SECRET')
BOT_TOKEN = os.getenv('BOT_TOKEN')
VPN_KEY = os.getenv('VPN_KEY')

# Файл для хранения соответствий externalId -> transactionId и статусов
TRANSACTIONS_FILE = "transactions.json"

# ==================== ФУНКЦИИ ====================
def load_transactions():
    if os.path.exists(TRANSACTIONS_FILE):
        with open(TRANSACTIONS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_transactions(transactions):
    with open(TRANSACTIONS_FILE, 'w') as f:
        json.dump(transactions, f)

def send_telegram_message(chat_id, text):
    """Отправляет сообщение пользователю в Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10)
        print(f"✅ Сообщение отправлено пользователю {chat_id}")
    except Exception as e:
        print(f"❌ Ошибка отправки сообщения: {e}")

# ==================== ЭНДПОИНТЫ ====================
@app.route('/create_invoice_get', methods=['GET'])
def create_invoice_get():
    amount = 150.0
    external_id = request.args.get('externalId')
    description = request.args.get('description', 'VPN payment')
    
    if not external_id:
        return "❌ Нет externalId", 400
    
    # Заголовки для Platega
    headers = {
        "Content-Type": "application/json",
        "X-MerchantId": PLATEGA_MERCHANT_ID,
        "X-Secret": PLATEGA_SECRET
    }
    
    # Тело запроса (без заданного метода)
    payload = {
        "paymentDetails": {
            "amount": amount,
            "currency": "RUB"
        },
        "description": description,
        "return": f"https://t.me/твойбот?start=success_{external_id}",
        "failedUrl": f"https://t.me/твойбот?start=fail_{external_id}",
        "callbackUrl": "https://if-production.up.railway.app/platega_callback",
        "payload": external_id
    }
    
    try:
        resp = requests.post(
            "https://app.platega.io/v2/transaction/process",
            headers=headers,
            json=payload,
            timeout=30
        )
        data = resp.json()
        print(f"📦 Ответ Platega: {data}")
        
        if resp.status_code == 200 and 'url' in data:
            transaction_id = data.get('transactionId')
            payment_url = data.get('url')
            
            # Сохраняем транзакцию
            transactions = load_transactions()
            transactions[external_id] = {
                "transactionId": transaction_id,
                "status": "PENDING",
                "created_at": time.time()
            }
            save_transactions(transactions)
            
            # Формируем красивую страницу
            message = f"""<div style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-image: url('https://i.ibb.co/Xxvy6CfL/HNn0xmy9j-LRQjy-xbu8l-VUu-Jpw-DVaj-NE6-KTh-Zn-Cyhcy-Gbs-Ymw83-G0-Mp3-L-V9h7kyfu-JDi-OVHm7-YPAv-IRw-Mo6-k.jpg');
                background-size: cover;
                background-position: center;
                font-family: Arial, sans-serif;
                font-size: 2.5em;
                line-height: 1.3;
                color: black;
                font-weight: bold;
                padding: 40px;
            ">
                ОРДЕР ГОТОВ<br>
                СУММА: {amount} РУБ.<br>
                ССЫЛКА: <a href="{payment_url}" style="color: #FFD700; text-decoration: underline;">ОПЛАТИТЬ</a>
            </div>"""
            
            return message
        else:
            return f"ОШИБКА Platega: {data}", 400
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return f"ОШИБКА СЕРВЕРА: {str(e)}", 500


@app.route('/platega_callback', methods=['POST'])
def platega_callback():
    try:
        data = request.json
        print(f"📩 Вебхук: {data}")
        
        if data.get('status') == 'CONFIRMED':
            payload = data.get('payload')
            if not payload:
                return "❌ Нет payload", 400
            
            # Обновляем статус транзакции
            transactions = load_transactions()
            if payload in transactions:
                transactions[payload]['status'] = 'CONFIRMED'
                save_transactions(transactions)
                
                # Отправляем ключ пользователю
                user_id = payload.split('_')[1] if '_' in payload else None
                if user_id:
                    send_telegram_message(user_id, f"✅ Оплата подтверждена!\n\n🔑 Ваш ключ: {VPN_KEY}")
                else:
                    print(f"❌ Не удалось извлечь user_id из {payload}")
            else:
                print(f"⚠️ Платёж с payload {payload} не найден")
            
            return "OK", 200
        else:
            print(f"ℹ️ Статус: {data.get('status')}")
            return "OK", 200
    except Exception as e:
        print(f"❌ Ошибка в вебхуке: {e}")
        return "Internal Server Error", 500


@app.route('/check_payment', methods=['GET'])
def check_payment():
    external_id = request.args.get('externalId')
    if not external_id:
        return "❌ Нет externalId", 400
    
    transactions = load_transactions()
    trans = transactions.get(external_id)
    if not trans:
        return f"""<div style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: url('https://i.ibb.co/Xxvy6CfL/HNn0xmy9j-LRQjy-xbu8l-VUu-Jpw-DVaj-NE6-KTh-Zn-Cyhcy-Gbs-Ymw83-G0-Mp3-L-V9h7kyfu-JDi-OVHm7-YPAv-IRw-Mo6-k.jpg');
            background-size: cover;
            background-position: center;
            font-family: Arial, sans-serif;
            font-size: 2.5em;
            line-height: 1.3;
            color: black;
            font-weight: bold;
            padding: 40px;
        ">
            Ваш платёж не найден 😥
        </div>"""
    
    status = trans.get('status')
    if status == 'CONFIRMED':
        message = f"✅ Оплата подтверждена!\n\n🔑 Ваш ключ: {VPN_KEY}"
    elif status == 'PENDING':
        message = "⏳ Статус: PENDING. Ожидаем оплаты..."
    elif status == 'CANCELED':
        message = "❌ Платёж отменён."
    elif status == 'CHARGEBACKED':
        message = "❌ Произошёл чарджбэк."
    else:
        message = f"❌ Неизвестный статус: {status}"
    
    return f"""<div style="
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: url('https://i.ibb.co/20DD0N2s/Fba-VTc-Sz-D-x-GLM6-ZV26k-Omk-Eyq5-Rs-Tsw-ZWTWj-Nf9-VCh-L8f-W6l-YZ3-FIn-Rw-N3y-Yg-Z-yy-Zy-Xza-Aj-Kw-Ta-O.jpg');
        background-size: cover;
        background-position: center;
        font-family: Arial, sans-serif;
        font-size: 2.5em;
        line-height: 1.3;
        color: black;
        font-weight: bold;
        padding: 40px;
    ">
        {message}
    </div>"""


@app.route('/health', methods=['GET'])
def health():
    return "OK", 200
