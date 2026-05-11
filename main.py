from flask import Flask, request
import requests
import json
import os

app = Flask(__name__)

# ==================== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ====================
PLATEGA_MERCHANT_ID = os.getenv('PLATEGA_MERCHANT_ID')
PLATEGA_SECRET = os.getenv('PLATEGA_SECRET')
VPN_KEY = os.getenv('VPN_KEY')
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Файл для хранения соответствий externalId -> transactionId и статуса
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
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не задан в переменных окружения")
        return
    
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

def create_platega_payment(amount, external_id, description, payment_method_name, callback_url):
    """Общая функция для создания платежа в Platega с webhook"""
    headers = {
        "Content-Type": "application/json",
        "X-MerchantId": PLATEGA_MERCHANT_ID,
        "X-Secret": PLATEGA_SECRET
    }
    
    payload = {
        "paymentDetails": {
            "amount": amount,
            "currency": "RUB"
        },
        "description": description,
        "return": "https://t.me/ваш_бот?start=success",
        "failedUrl": "https://t.me/ваш_бот?start=fail",
        "callbackUrl": callback_url,
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
        print(f"📦 Ответ Platega ({payment_method_name}): {data}")
        
        if resp.status_code == 200 and 'url' in data:
            transaction_id = data.get('transactionId')
            payment_url = data.get('url')
            
            # Сохраняем транзакцию
            transactions = load_transactions()
            transactions[external_id] = {
                "transactionId": transaction_id,
                "status": "PENDING",
                "method": payment_method_name
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
                МЕТОД: {payment_method_name}<br>
                ССЫЛКА: <a href="{payment_url}" style="color: #FFD700; text-decoration: underline;">ОПЛАТИТЬ</a>
            </div>"""
            
            return message
        else:
            return f"ОШИБКА Platega ({payment_method_name}): {data}", 400
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return f"ОШИБКА СЕРВЕРА: {str(e)}", 500

# ==================== ЭНДПОИНТЫ ДЛЯ РАЗНЫХ СПОСОБОВ ОПЛАТЫ ====================
CALLBACK_URL = "https://if-production.up.railway.app/platega_webhook"

@app.route('/create_card_payment', methods=['GET'])
def create_card_payment():
    amount = 165.0
    external_id = request.args.get('externalId')
    description = request.args.get('description', 'VPN payment')
    if not external_id:
        return "❌ Нет externalId", 400
    return create_platega_payment(amount, external_id, description, "Банковская карта", CALLBACK_URL)

@app.route('/create_sbp_payment', methods=['GET'])
def create_sbp_payment():
    amount = 163.0
    external_id = request.args.get('externalId')
    description = request.args.get('description', 'VPN payment')
    if not external_id:
        return "❌ Нет externalId", 400
    return create_platega_payment(amount, external_id, description, "СБП", CALLBACK_URL)

@app.route('/create_crypto_payment', methods=['GET'])
def create_crypto_payment():
    amount = 154.5
    external_id = request.args.get('externalId')
    description = request.args.get('description', 'VPN payment')
    if not external_id:
        return "❌ Нет externalId", 400
    return create_platega_payment(amount, external_id, description, "Криптовалюта", CALLBACK_URL)

# ==================== ВЕБХУК ОТ PLATEGA ====================
@app.route('/platega_webhook', methods=['POST'])
def platega_webhook():
    try:
        data = request.json
        print(f"📩 Получен вебхук от Platega: {data}")
        
        if data.get('status') == 'CONFIRMED':
            payload = data.get('payload')
            if not payload:
                return "❌ Нет payload", 400
            
            transactions = load_transactions()
            if payload in transactions:
                transactions[payload]['status'] = 'CONFIRMED'
                save_transactions(transactions)
                
                user_id = payload.split('_')[1] if '_' in payload else None
                if user_id:
                    send_telegram_message(user_id, f"✅ Оплата подтверждена!\n\n🔑 Ваш ключ: {VPN_KEY}")
                else:
                    print(f"❌ Не удалось извлечь user_id из payload: {payload}")
            else:
                print(f"⚠️ Платёж с payload {payload} не найден в транзакциях")
            
            return "OK", 200
        else:
            print(f"ℹ️ Статус не CONFIRMED: {data.get('status')}")
            return "OK", 200
    except Exception as e:
        print(f"❌ Ошибка в вебхуке: {e}")
        return "Internal Server Error", 500

# ==================== ПРОВЕРКА СТАТУСА (резервная) ====================
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
    
    transaction_id = trans.get('transactionId')
    headers = {
        "X-MerchantId": PLATEGA_MERCHANT_ID,
        "X-Secret": PLATEGA_SECRET
    }
    
    try:
        resp = requests.get(
            f"https://app.platega.io/transaction/{transaction_id}",
            headers=headers,
            timeout=30
        )
        data = resp.json()
        print(f"📦 Статус от Platega: {data}")
        
        if resp.status_code == 200:
            status = data.get('status')
            trans['status'] = status
            save_transactions(transactions)
            
            if status == 'CONFIRMED':
                message = f"✅ Оплата подтверждена!\n\n🔑 Ваш ключ: {VPN_KEY}"
            elif status == 'PENDING':
                message = "⏳ Статус: PENDING. Ожидаем оплаты..."
            elif status == 'CANCELED':
                message = "❌ Платёж отменён."
            else:
                message = f"❌ Статус: {status}"
        else:
            message = f"❌ Ошибка при проверке: {data}"
    except Exception as e:
        message = f"❌ Ошибка сервера: {str(e)}"
    
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
