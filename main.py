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
        print("❌ BOT_TOKEN не задан")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)
        print(f"✅ Сообщение отправлено {chat_id}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

# ==================== ЕДИНЫЙ ЭНДПОИНТ ДЛЯ ОПЛАТЫ ====================
@app.route('/create_payment', methods=['GET'])
def create_payment():
    amount = 165.0
    external_id = request.args.get('externalId')
    description = request.args.get('description', 'VPN payment')
    
    if not external_id:
        return "❌ Нет externalId", 400
    
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
        "callbackUrl": "https://if-production.up.railway.app/platega_webhook",
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
        
        if resp.status_code == 200 and 'url' in data:
            payment_url = data.get('url')
            
            # Сохраняем транзакцию
            transactions = load_transactions()
            transactions[external_id] = {
                "transactionId": data.get('transactionId'),
                "status": "PENDING"
            }
            save_transactions(transactions)
            
            # Отправляем ссылку пользователю в Telegram
            user_id = external_id.split('_')[1] if '_' in external_id else None
            if user_id:
                send_telegram_message(user_id, f"🔗 Ссылка на оплату:\n{payment_url}\n\nПосле оплаты ключ придёт автоматически.")
            
            # Возвращаем ссылку (для PuzzleBot, если он всё-таки сможет её вывести)
            return payment_url
        else:
            return f"Ошибка: {data}", 400
    except Exception as e:
        return f"Ошибка сервера: {str(e)}", 500

# ==================== ВЕБХУК ОТ PLATEGA ====================
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
                    send_telegram_message(user_id, f"✅ Оплата подтверждена!\n\n🔑 Ваш ключ: {VPN_KEY}")
                else:
                    print(f"❌ Не удалось извлечь user_id из {payload}")
            else:
                print(f"⚠️ Платёж {payload} не найден")
            return "OK", 200
        return "OK", 200
    except Exception as e:
        print(f"❌ Ошибка вебхука: {e}")
        return "OK", 200

@app.route('/health', methods=['GET'])
def health():
    return "OK", 200
