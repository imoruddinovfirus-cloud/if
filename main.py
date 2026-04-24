from flask import Flask, request
import requests
import json
import os

app = Flask(__name__)

API_KEY = "06ff2425-dcf0-42ed-85d3-419bb4bbe927"
API_SECRET = "8e280987-ebba-4c95-af1c-90934e372774"

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
    amount = request.args.get('amount', 150, type=int)
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
            
            # Огромные буквы (font-size: 2.5em) и строго в столбик
            message = f"""<div style="font-size: 2.5em;">
✅ Успешно создан!<br>
💳 Сумма: {amount} руб.<br>
🔗 Ссылка: <a href="{payment_url}">Оплатить</a>
</div>"""
            
            return message
        else:
            return f"❌ Ошибка: {data.get('message', 'Попробуйте другую сумму')}", 400
    except Exception as e:
        return f"❌ Ошибка сервера: {str(e)}", 500

@app.route('/check_payment', methods=['GET'])
def check_payment():
    external_id = request.args.get('externalId')
    if not external_id:
        return "❌ Нет externalId", 400
    
    payments = load_payments()
    invoice_id = payments.get(external_id)
    if not invoice_id:
        return f"❌ Платёж с ID {external_id} не найден."
    
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
                return "❌ Время оплаты вышло."
            else:
                return f"⏳ Статус: {status}. Ожидаем оплаты..."
        else:
            return "❌ Не удалось проверить статус платежа."
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"

@app.route('/health', methods=['GET'])
def health():
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
