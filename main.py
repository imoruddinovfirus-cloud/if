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

# Файл для хранения транзакций
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
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не задан")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
        print(f"✅ Сообщение отправлено {chat_id}")
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")

def create_platega_payment(amount, external_id, user_id, method_name, payment_method):
    if not external_id or not user_id:
        return "❌ Нет externalId или userId", 400
    
    headers = {
        "Content-Type": "application/json",
        "X-MerchantId": PLATEGA_MERCHANT_ID,
        "X-Secret": PLATEGA_SECRET
    }
    payload = {
        "paymentMethod": payment_method,
        "paymentDetails": {"amount": amount, "currency": "RUB"},
        "description": f"VPN payment ({method_name})",
        "return": "https://t.me/ваш_бот?start=success",
        "failedUrl": "https://t.me/ваш_бот?start=fail",
        "callbackUrl": "https://if-production.up.railway.app/platega_webhook",
        "payload": external_id
    }
    
    try:
        resp = requests.post("https://app.platega.io/transaction/process", headers=headers, json=payload, timeout=30)
        data = resp.json()
        
        if resp.status_code == 200 and 'redirect' in data:
            payment_url = data.get('redirect')
            transaction_id = data.get('transactionId')
            
            transactions = load_transactions()
            transactions[external_id] = {
                "transactionId": transaction_id,
                "status": "PENDING",
                "method": method_name
            }
            save_transactions(transactions)
            
            send_telegram_message(user_id, f"🔗 Ссылка на оплату {method_name}: {payment_url}\n\nСумма: 150 руб.")
            return "OK", 200
        else:
            return f"Ошибка Platega: {data}", 400
    except Exception as e:
        return f"Ошибка сервера: {str(e)}", 500

# 1. Карта (paymentMethod = 11)
@app.route('/create_card_payment', methods=['GET'])
def create_card_payment():
    amount = 137.6125  # 150 / 1.09
    external_id = request.args.get('externalId')
    user_id = request.args.get('userId')
    return create_platega_payment(amount, external_id, user_id, "картой", payment_method=11)

# 2. СБП (paymentMethod = 2)
@app.route('/create_sbp_payment', methods=['GET'])
def create_sbp_payment():
    amount = 138.89  # 150 / 1.08
    external_id = request.args.get('externalId')
    user_id = request.args.get('userId')
    return create_platega_payment(amount, external_id, user_id, "СБП", payment_method=2)

# 3. Криптовалюта (paymentMethod = 13)
@app.route('/create_crypto_payment', methods=['GET'])
def create_crypto_payment():
    amount = 145.63  # 150 / 1.03
    external_id = request.args.get('externalId')
    user_id = request.args.get('userId')
    return create_platega_payment(amount, external_id, user_id, "криптовалютой", payment_method=13)
# ==================== ОСТАЛЬНЫЕ ЭНДПОИНТЫ ====================

@app.route('/platega_webhook', methods=['POST'])
def platega_webhook():
    try:
        data = request.json
        print(f"📩 Вебхук: {data}")
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
                    send_telegram_message(
                        user_id,
                        f"✅ Оплата подтверждена!\n\n🔑 Ваш ключ:\n<code>{VPN_KEY}</code>\n\nНажмите на ключ, чтобы скопировать."
                    )
        return "OK", 200
    except Exception as e:
        print(f"❌ Ошибка вебхука: {e}")
        return "Internal Server Error", 500

@app.route('/health', methods=['GET'])
def health():
    return "OK", 200
