from flask import Flask, request
import requests
import json
import os
import time

app = Flask(__name__)

API_KEY = os.getenv('LPAY_API_KEY')
API_SECRET = os.getenv('LPAY_API_SECRET')
VPN_KEY = os.getenv('VPN_KEY')

PAYMENTS_FILE = "payments.json"
user_last_external = {}  # user_id -> последний externalId

def load_payments():
    if os.path.exists(PAYMENTS_FILE):
        with open(PAYMENTS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_payments(payments):
    with open(PAYMENTS_FILE, 'w') as f:
        json.dump(payments, f)

@app.route('/create_invoice_get', methods=['GET'])
def create_invoice_get():
    amount = 40
    external_id = request.args.get('externalId')
    user_id = request.args.get('userId')
    description = request.args.get('description', 'VPN payment')
    
    if not external_id:
        return "❌ Нет externalId", 400
    
    # Сохраняем последний externalId для этого пользователя
    if user_id:
        user_last_external[user_id] = external_id
    
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
        resp = requests.post(
            "https://api.lpayapp.xyz/invoices",
            headers=headers,
            json=payload,
            timeout=30
        )
        data = resp.json()
        
        if resp.status_code == 201:
            invoice_id = data.get("invoiceId")
            payment_url = data.get("paymentUrl")
            
            payments = load_payments()
            payments[external_id] = invoice_id
            save_payments(payments)
            
            message = f"""<div style="
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
                ОРДЕР ГОТОВ<br>
                СУММА: {amount} РУБ.<br>
                ССЫЛКА: <a href="{payment_url}" style="color: #FFD700;">ОПЛАТИТЬ</a>
            </div>"""
            
            return message
        else:
            return f"ОШИБКА: {data.get('message', 'Попробуйте другую сумму')}", 400
    except Exception as e:
        return f"ОШИБКА СЕРВЕРА: {str(e)}", 500

@app.route('/check_payment', methods=['GET'])
def check_payment():
    user_id = request.args.get('userId')
    external_id = request.args.get('externalId')
    
    # Если передан userId, берём последний externalId из хранилища
    if user_id and not external_id:
        external_id = user_last_external.get(user_id)
        if not external_id:
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
                Ваш платёж не найден 😥
            </div>"""
    
    if not external_id:
        return "❌ Нет externalId", 400
    
    payments = load_payments()
    invoice_id = payments.get(external_id)
    if not invoice_id:
        return f"""<div style="...">Ваш платёж не найден 😥</div>"""
    
    headers = {
        "x-api-key": API_KEY,
        "x-api-secret": API_SECRET
    }
    
    try:
        resp = requests.get(
            f"https://api.lpayapp.xyz/invoices/{invoice_id}",
            headers=headers,
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            status = data.get('status')
            if status == 'confirmed':
                message = f"✅ Оплата подтверждена! Спасибо за покупку.\n\n🔑 Ваш ключ: {VPN_KEY}"
            elif status == 'expired':
                message = "❌ Время на оплату вышло. Создайте новый платёж."
            else:
                message = f"⏳ Статус: {status}. Ожидаем оплаты..."
        else:
            message = "❌ Не удалось проверить статус платежа."
    except Exception as e:
        message = f"❌ Ошибка: {str(e)}"
    
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
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
