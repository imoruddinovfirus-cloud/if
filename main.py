from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# --- ЭТА ЧАСТЬ ДОБАВЛЯЕТ ПРАВИЛЬНЫЕ ЗАГОЛОВКИ ДЛЯ PUZZLEBOT ---
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST')
    return response
# -------------------------------------------------------------

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
        
        if response.status_code == 400 and "No available traders" in str(result):
            return "❌ Платёжный сервис временно недоступен. Попробуйте другую сумму или повторите через 10-15 минут."
        
        if response.status_code != 201:
            return f"❌ Ошибка: {result.get('message', 'Попробуйте позже')}"
        
        return result.get("paymentUrl", "Ссылка не получена")
        
    except Exception as e:
        return "❌ Техническая ошибка. Попробуйте позже."

@app.route('/health', methods=['GET'])
def health():
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
