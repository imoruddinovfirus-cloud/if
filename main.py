from flask import Flask, request
import requests
import json
import os

app = Flask(__name__)

# Простейший эндпоинт для проверки
@app.route('/create_sbp_payment', methods=['GET'])
def create_sbp_payment():
    external_id = request.args.get('externalId')
    if not external_id:
        return "❌ Нет externalId", 400
    
    # Возвращаем просто тестовую ссылку, без Platega
    return f'✅ Тестовая ссылка для {external_id}: https://example.com/pay'

@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

# НЕТ app.run() !!!
