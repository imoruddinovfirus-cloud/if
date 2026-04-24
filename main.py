from flask import Flask, request, make_response
from flask_cors import CORS
import requests
import time
import logging
import uuid

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

API_KEY = "06ff2425-dcf0-42ed-85d3-419bb4bbe927"
API_SECRET = "8e280987-ebba-4c95-af1c-90934e372774"

# Хранилище последнего платежа для каждого пользователя
user_last_external_id = {}

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', '*')
    response.headers.add('Access-Control-Allow-Methods', '*')
    return response

@app.route('/create_invoice_get', methods=['GET'])
def create_invoice_get():
    amount = request.args.get('amount', 50, type=int)
    description = request.args.get('description', 'VPN payment')
    
    # БЕРЁМ externalId ИЗ ЗАПРОСА
    external_id = request.args.get('externalId')
    
    # Если externalId не передан или содержит шаблонные переменные — генерируем свой
    if not external_id or '{{' in external_id or '}}' in external_id:
        external_id = f"fin_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        logger.info(f"Сгенерирован новый externalId: {external_id}")
    
    # Сохраняем externalId для пользователя (по userId или chatId)
    user_id = request.args.get('userId')
    chat_id = request.args.get('chatId')
    
    if user_id:
        user_last_external_id[user_id] = external_id
        logger.info(f"Сохранён externalId {external_id} для userId {user_id}")
    if chat_id:
        user_last_external_id[chat_id] = external_id
        logger.info(f"Сохранён externalId {external_id} для chatId {chat_id}")
    
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
        response_lpay = requests.post(
            "https://api.lpayapp.xyz/invoices",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        result = response_lpay.json()
        
        if response_lpay.status_code == 201:
            payment_url = result.get("paymentUrl")
            
            # ВОЗВРАЩАЕМ ТЕКСТ ВМЕСТО JSON
            response_text = f"""🎫 *Счет на оплату*

✅ Успешно создан!
💳 Сумма: {amount} руб.
📝 Описание: {description}
🔗 Ссылка: {payment_url}
🆔 ID платежа: {external_id}

Ссылка действительна 60 минут."""
            
            logger.info(f"Успешно создан инвойс: {external_id}")
            return response_text, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            error_msg = result.get('message', 'Попробуйте другую сумму')
            logger.error(f"Ошибка API LPay: {error_msg}")
            
            # ВОЗВРАЩАЕМ ТЕКСТ ОШИБКИ
            error_text = f"""❌ Ошибка создания платежа

{error_msg}

Попробуйте другую сумму или обратитесь в поддержку."""
            return error_text, 400, {'Content-Type': 'text/plain; charset=utf-8'}
            
    except Exception as e:
        logger.error(f"Ошибка создания инвойса: {str(e)}")
        
        # ВОЗВРАЩАЕМ ТЕКСТ ОШИБКИ
        error_text = f"""❌ Техническая ошибка

Не удалось создать платёж.
Попробуйте позже или обратитесь в поддержку.

Ошибка: {str(e)}"""
        return error_text, 500, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/health', methods=['GET'])
def health():
    return "OK"

@app.route('/check_payment', methods=['GET'])
def check_payment():
    user_id = request.args.get('userId')
    chat_id = request.args.get('chatId')
    external_id = request.args.get('externalId')
    
    # Если передан userId или chatId, берём сохранённый externalId
    if not external_id:
        if user_id:
            external_id = user_last_external_id.get(user_id)
        elif chat_id:
            external_id = user_last_external_id.get(chat_id)
        
        if not external_id:
            # ВОЗВРАЩАЕМ ТЕКСТ ОШИБКИ
            error_text = """❌ Нет активных платежей

Сначала создайте платёж через /pay_fin"""
            return error_text, 404, {'Content-Type': 'text/plain; charset=utf-8'}
    
    if not external_id:
        # ВОЗВРАЩАЕМ ТЕКСТ ОШИБКИ
        error_text = """❌ Ошибка параметров

Не передан externalId, userId или chatId"""
        return error_text, 400, {'Content-Type': 'text/plain; charset=utf-8'}
    
    # Реальная проверка через API Lpay
    headers = {
        "x-api-key": API_KEY,
        "x-api-secret": API_SECRET
    }
    
    try:
        resp = requests.get(
            f"https://api.lpayapp.xyz/invoices?externalId={external_id}",
            headers=headers,
            timeout=30
        )
        result = resp.json()
        logger.info(f"Проверка платежа {external_id}: статус {resp.status_code}")
        
        if resp.status_code == 200 and result.get('items'):
            status = result['items'][0].get('status')
            
            if status == 'confirmed':
                # ВОЗВРАЩАЕМ ТЕКСТ УСПЕХА
                success_text = f"""✅ Оплата подтверждена!

Платёж {external_id} успешно оплачен."""
                return success_text, 200, {'Content-Type': 'text/plain; charset=utf-8'}
                
            elif status == 'expired':
                # ВОЗВРАЩАЕМ ТЕКСТ ОШИБКИ
                error_text = f"""❌ Время оплаты вышло

Платёж {external_id} просрочен.
Создайте новый платёж."""
                return error_text, 400, {'Content-Type': 'text/plain; charset=utf-8'}
                
            else:
                # ВОЗВРАЩАЕМ ТЕКСТ СТАТУСА
                status_text = f"""⏳ Ожидание оплаты

Статус платежа {external_id}: {status}
Ожидаем подтверждения оплаты."""
                return status_text, 200, {'Content-Type': 'text/plain; charset=utf-8'}
                
        else:
            # ВОЗВРАЩАЕМ ТЕКСТ ОШИБКИ
            error_text = f"""❌ Платёж не найден

Платёж с ID {external_id} не найден.
Возможно, он был удалён или ещё не создан."""
            return error_text, 404, {'Content-Type': 'text/plain; charset=utf-8'}
            
    except Exception as e:
        logger.error(f"Ошибка проверки: {str(e)}")
        
        # ВОЗВРАЩАЕМ ТЕКСТ ОШИБКИ
        error_text = f"""❌ Ошибка проверки

Не удалось проверить статус платежа.
Попробуйте позже.

Ошибка: {str(e)}"""
        return error_text, 500, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
