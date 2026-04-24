# В начале файла добавь
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Здесь будем хранить связку твоего ID и ID из Lpay
payment_store = {}

API_KEY = "06ff2425-dcf0-42ed-85d3-419bb4bbe927"
API_SECRET = "8e280987-ebba-4c95-af1c-90934e372774"

@app.route('/create_invoice_get', methods=['GET'])
def create_invoice_get():
    amount = request.args.get('amount', 50, type=int)
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
            
            # СОХРАНЯЕМ СВЯЗКУ: твой externalId -> invoiceId из Lpay
            payment_store[external_id] = invoice_id
            
            return jsonify({
                "success": True,
                "paymentUrl": payment_url,
                "externalId": external_id,
                "message": f"✅ Счёт на оплату:\n\n✔ Успешно создан!\n☑ Сумма: {amount} руб.\n☑ Описание: {description}\n✎ Ссылка: {payment_url}\nID платежа: {external_id}\n\nСсылка действительна 60 минут."
            })
        else:
            return jsonify({
                "success": False,
                "message": f"❌ Ошибка: {data.get('message', 'Попробуйте другую сумму')}"
            }), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"❌ Ошибка сервера: {str(e)}"
        }), 500


@app.route('/check_payment', methods=['GET'])
def check_payment():
    external_id = request.args.get('externalId')
    
    if not external_id:
        return "❌ Нет externalId", 400
    
    # Ищем invoiceId по твоему externalId
    invoice_id = payment_store.get(external_id)
    if not invoice_id:
        return f"❌ Платёж с ID {external_id} не найден. Возможно, он был удалён или ещё не создан."
    
    headers = {
        "x-api-key": API_KEY,
        "x-api-secret": API_SECRET
    }
    
    try:
        # Запрашиваем статус по invoiceId из Lpay
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
