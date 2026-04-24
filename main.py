from flask import Flask, request
import requests
import json
import os

app = Flask(__name__)

API_KEY = os.getenv('LPAY_API_KEY')
API_SECRET = os.getenv('LPAY_API_SECRET')

PAYMENTS_FILE = "payments.json"

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
    amount = 150
    external_id = request.args.get('externalId')
    description = request.args.get('description', 'VPN payment')
    
    if not external_id:
        return "❌ Нет externalId", 400
    
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
            
            # Текст сверху слева, ссылка золотистая
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
            return f"ОШИБКА: {data.get('message', 'Попробуйте другую сумму')}", 400
    except Exception as e:
        return f"ОШИБКА СЕРВЕРА: {str(e)}", 500

        
@app.route('/check_payment', methods=['GET'])
def check_payment():
    external_id = request.args.get('externalId')
    if not external_id:
        return "❌ Нет externalId", 400
    
    payments = load_payments()
    invoice_id = payments.get(external_id)
    if not invoice_id:
        return f"Ваш платёж не найден 😥"
    
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
                return "✅ Оплата подтверждена! Спасибо за покупку."
            elif status == 'expired':
                return "❌ Время на оплату вышло."
            else:
                return f"⏳ Статус: {status}. Ожидаем оплаты..."
        else:
            return "❌ Не удалось проверить статус платежа."
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"

@app.route('/health', methods=['GET'])
def health():
    return "OK"

