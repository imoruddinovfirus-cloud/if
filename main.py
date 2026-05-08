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
        print(f"📦 Ответ Platega: {data}")
        
        if resp.status_code == 200 and 'url' in data:
            transaction_id = data.get('transactionId')
            payment_url = data.get('url')
            
            # Сохраняем транзакцию
            transactions = load_transactions()
            transactions[external_id] = {
                "transactionId": transaction_id,
                "status": "PENDING"
            }
            save_transactions(transactions)
            
            # Формируем красивую страницу (как было)
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
                message = f"""✅ Оплата подтверждена! Спасибо за покупку.

🔑 Ваш ключ: <span id="vpnKey" style="font-family: monospace; font-size: 1em;">{VPN_KEY}</span>
<br><br>
<button onclick="copyToClipboard()" style="
    background-color: #FFD700;
    color: black;
    font-weight: bold;
    font-size: 1.2em;
    padding: 10px 20px;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    box-shadow: 2px 2px 4px rgba(0,0,0,0.2);
">📋 Копировать ключ</button>

<script>
function copyToClipboard() {{
    const key = document.getElementById('vpnKey').innerText;
    navigator.clipboard.writeText(key).then(() => {{
        const btn = event.target;
        const originalText = btn.innerText;
        btn.innerText = '✅ Скопировано!';
        setTimeout(() => {{
            btn.innerText = originalText;
        }}, 2000);
    }}).catch(() => {{
        alert('Не удалось скопировать. Выделите ключ вручную.');
    }});
}}
</script>"""
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
