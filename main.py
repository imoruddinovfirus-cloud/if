from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

API_KEY = "06ff2425-dcf0-42ed-85d3-419bb4bbe927"
API_SECRET = "8e280987-ebba-4c95-af1c-90934e372774"

# Простое хранилище ссылок в памяти сервера
payment_links_store = {}

@app.route('/create_invoice', methods=['POST'])
def create_invoice():
    data = request.json
    external_id = data.get("externalId")

    if not external_id:
        return "❌ Ошибка: нет externalId", 400

    headers = {
        "x-api-key": API_KEY,
        "x-api-secret": API_SECRET,
        "Content-Type": "application/json"
    }

    payload = {
        "amount": data.get("amount", 500),
        "externalId": external_id,
        "description": data.get("description", "VPN payment")
    }

    try:
        response = requests.post(
            "https://api.lpayapp.xyz/invoices",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 201:
            result = response.json()
            payment_url = result.get("paymentUrl")
            # --- СОХРАНЯЕМ ССЫЛКУ ---
            if payment_url:
                payment_links_store[external_id] = payment_url
                return "OK", 200
            else:
                return "❌ Ссылка не получена от Lpay", 400
        else:
            return f"❌ Ошибка Lpay: {response.text}", 400

    except Exception as e:
        print(f"Ошибка: {e}")
        return "❌ Техническая ошибка на сервере", 500


# --- НОВЫЙ GET-МЕТОД ДЛЯ ПОЛУЧЕНИЯ ССЫЛКИ ---
@app.route('/get_payment_link', methods=['GET'])
def get_payment_link():
    external_id = request.args.get('externalId')
    if not external_id:
        return "❌ Ошибка: externalId не указан"

    payment_url = payment_links_store.get(external_id)
    if payment_url:
        return payment_url
    else:
        return "❌ Ссылка не найдена. Попробуйте позже или создайте счёт заново."

# -------------------------------------------------

@app.route('/health', methods=['GET'])
def health():
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
