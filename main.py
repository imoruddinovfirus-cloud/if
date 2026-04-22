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
        "description": data.get("description", "VPN payment"),
        "callbackUrl": ""
    }
    
    response = requests.post(
        "https://api.lpayapp.xyz/invoices",
        headers=headers,
        json=payload
    )
    
    return jsonify(response.json()), response.status_code

@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
