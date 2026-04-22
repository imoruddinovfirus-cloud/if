from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

API_KEY = "06ff2425-dcf0-42ed-85d3-419bb4bbe927"
API_SECRET = "8e280987-ebba-4c95-af1c-90934e372774"

@app.route('/create_invoice', methods=['POST'])
def create_invoice():
    data = request.json
    
    headers = {
        "x-api-key": API_KEY,
        "x-api-secret": API_SECRET,
        "Content-Type": "application/json"
    }
    
    payload = {
        "amount": data.get("amount", 500),
        "externalId": data.get("externalId", "test_123"),
        "description": data.get("description", "VPN payment")
    }
    
    try:
        response = requests.post(
            "https://api.lpayapp.xyz/invoices",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        result = response.json()
        
        # Успех — возвращаем ссылку
        if response.status_code == 201:
            payment_url = result.get("paymentUrl")
            return f"✅ Ссылка на оплату: {payment_url}\n\nСсылка действительна 60 минут. После оплаты нажмите «Оплатил»."
        
        # Ошибка No available traders
        if "No available traders" in str(result):
            return "❌ Платёжный сервис временно недоступен. Попробуйте другую сумму или повторите через 10-15 минут."
        
        # Любая другая ошибка
        return f"❌ Ошибка платежного сервиса: {result.get('message', 'Попробуйте позже')}"
        
    except Exception as e:
        return "❌ Техническая ошибка. Попробуйте позже."

@app.route('/health', methods=['GET'])
def health():
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
