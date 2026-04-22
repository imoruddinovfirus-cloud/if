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
        
        # Если Lpay вернул ошибку 400 No available traders
        if response.status_code == 400 and "No available traders" in str(result):
            return jsonify({
                "error": "no_traders",
                "message": "❌ Платёжный сервис временно недоступен. Попробуйте другую сумму или повторите через 10-15 минут."
            }), 200
        
        # Любая другая ошибка от Lpay
        if response.status_code != 201:
            return jsonify({
                "error": "lpay_error",
                "message": f"Ошибка платежного сервиса: {result.get('message', 'Неизвестная ошибка')}"
            }), 200
        
        # Успех — возвращаем paymentUrl
        return jsonify({
            "success": True,
            "paymentUrl": result.get("paymentUrl"),
            "invoiceId": result.get("invoiceId")
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": "server_error",
            "message": "❌ Техническая ошибка. Попробуйте позже."
        }), 200

@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
