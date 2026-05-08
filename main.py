from flask import Flask, request
import requests
import json
import os

app = Flask(__name__)

# ==================== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ====================
PLATEGA_MERCHANT_ID = os.getenv('PLATEGA_MERCHANT_ID')
PLATEGA_SECRET = os.getenv('PLATEGA_SECRET')
VPN_KEY = os.getenv('VPN_KEY')

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

def create_platega_payment(amount, external_id, description, payment_method_name):
    """Общая функция для создания платежа в Platega"""
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

# 1. СБП (комиссия ~8%)
@app.route('/create_sbp_payment', methods=['GET'])
def create_sbp_payment():
    amount = 138
    external_id = request.args.get('externalId')
    description = request.args.get('description', 'VPN payment')
    
    if not external_id:
        return "❌ Нет externalId", 400
    
    return create_platega_payment(amount, external_id, description, "СБП")

# 2. Банковская карта (комиссия ~9%)
@app.route('/create_card_payment', methods=['GET'])
def create_card_payment():
    amount = 136.5
    external_id = request.args.get('externalId')
    description = request.args.get('description', 'VPN payment')
    
    if not external_id:
        return "❌ Нет externalId", 400
    
    return create_platega_payment(amount, external_id, description, "Банковская карта")

# 3. Криптовалюта (комиссия ~3%)
@app.route('/create_crypto_payment', methods=['GET'])
def create_crypto_payment():
    amount = 145.5
    external_id = request.args.get('externalId')
    description = request.args.get('description', 'VPN payment')
    
    if not external_id:
        return "❌ Нет externalId", 400
    
    return create_platega_payment(amount, external_id, description, "Криптовалюта")

# ==================== ПРОВЕРКА СТАТУСА (единый эндпоинт) ====================
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
                message = f"✅ Оплата подтверждена! Спасибо за покупку.\n\n🔑 Ваш ключ: {VPN_KEY}"
            elif status == 'PENDING':
                message = "⏳ Статус: PENDING. Ожидаем оплаты..."
            elif status == 'CANCELED':
                message = "❌ Платёж отменён."
            elif status == 'CHARGEBACKED':
                message = "❌ Произошёл чарджбэк."
            else:
                message = f"❌ Неизвестный статус: {status}"
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
