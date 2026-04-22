from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import time  # Добавлен для генерации timestamp

app = Flask(__name__)
# Включаем CORS для всех доменов и методов
CORS(app, resources={r"/*": {"origins": "*"}})

API_KEY = "06ff2425-dcf0-42ed-85d3-419bb4bbe927"
API_SECRET = "8e280987-ebba-4c95-af1c-90934e372774"

# ============================================
# ОРИГИНАЛЬНАЯ POST ВЕРСИЯ (оставляем для совместимости)
# ============================================
@app.route('/create_invoice', methods=['POST', 'OPTIONS'])
def create_invoice():
    """
    Оригинальная версия для POST запросов
    """
    # Обработка preflight запросов CORS
    if request.method == 'OPTIONS':
        return '', 200
    
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
            return jsonify({
                "success": True,
                "message": f"✅ Ссылка на оплату: {payment_url}\n\nСсылка действительна 60 минут. После оплаты нажмите «Оплатил».",
                "paymentUrl": payment_url
            })
        
        # Ошибка No available traders
        if "No available traders" in str(result):
            return jsonify({
                "success": False,
                "message": "❌ Платёжный сервис временно недоступен. Попробуйте другую сумму или повторите через 10-15 минут."
            })
        
        # Любая другая ошибка
        return jsonify({
            "success": False,
            "message": f"❌ Ошибка платежного сервиса: {result.get('message', 'Попробуйте позже')}"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "❌ Техническая ошибка. Попробуйте позже."
        })

# ============================================
# НОВАЯ GET ВЕРСИЯ (для PuzzleBot)
# ============================================
@app.route('/create_invoice_get', methods=['GET', 'OPTIONS'])
def create_invoice_get():
    """
    Новая версия для GET запросов (специально для PuzzleBot)
    Параметры передаются в URL: ?amount=500&externalId=test&description=VPN
    """
    # Обработка preflight запросов CORS
    if request.method == 'OPTIONS':
        return '', 200
    
    # Получаем параметры из URL
    amount = request.args.get('amount', 500, type=int)
    external_id = request.args.get('externalId', f'test_{int(time.time())}')
    description = request.args.get('description', 'VPN payment')
    
    # Логирование для отладки
    print(f"[DEBUG] GET запрос: amount={amount}, externalId={external_id}, description={description}")
    
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
        response = requests.post(
            "https://api.lpayapp.xyz/invoices",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        result = response.json()
        
        # Логирование ответа Lpay
        print(f"[DEBUG] Ответ Lpay: status={response.status_code}, result={result}")
        
        # Успех — возвращаем ссылку
        if response.status_code == 201:
            payment_url = result.get("paymentUrl")
            return jsonify({
                "success": True,
                "message": f"✅ Ссылка на оплату: {payment_url}\n\nСсылка действительна 60 минут.",
                "paymentUrl": payment_url,
                "invoiceId": result.get("invoiceId"),
                "externalId": external_id
            })
        
        # Ошибка No available traders
        if "No available traders" in str(result):
            return jsonify({
                "success": False,
                "message": "❌ Платёжный сервис временно недоступен. Попробуйте другую сумму или повторите через 10-15 минут.",
                "error": "no_traders"
            })
        
        # Любая другая ошибка
        return jsonify({
            "success": False,
            "message": f"❌ Ошибка платежного сервиса: {result.get('message', 'Попробуйте позже')}",
            "error": "lpay_error"
        })
        
    except Exception as e:
        print(f"[ERROR] Исключение: {str(e)}")
        return jsonify({
            "success": False,
            "message": "❌ Техническая ошибка. Попробуйте позже.",
            "error": "server_error"
        })

# ============================================
# ТЕСТОВАЯ GET ВЕРСИЯ (если Lpay не работает)
# ============================================
@app.route('/create_invoice_test', methods=['GET'])
def create_invoice_test():
    """
    Тестовая версия для отладки PuzzleBot
    Всегда возвращает тестовую ссылку
    """
    amount = request.args.get('amount', 500, type=int)
    external_id = request.args.get('externalId', f'test_{int(time.time())}')
    
    # Всегда возвращаем успех с тестовой ссылкой
    return jsonify({
        "success": True,
        "message": f"✅ ТЕСТ: Ссылка на оплату: https://example.com/pay/{external_id}",
        "paymentUrl": f"https://example.com/pay/{external_id}",
        "invoiceId": f"test_{external_id}",
        "externalId": external_id,
        "is_test": True
    })

# ============================================
# HEALTH CHECK (оставляем как есть)
# ============================================
@app.route('/health', methods=['GET'])
def health():
    return "OK"

# ============================================
# ЗАПУСК СЕРВЕРА
# ============================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
