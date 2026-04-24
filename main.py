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
            
            # Сохраняем связку
            payments = load_payments()
            payments[external_id] = invoice_id
            save_payments(payments)
            
            # Увеличенный текст через <big> или <span style="font-size:1.3em">
            message = f"""<big><big><b>🎫 Счет на оплату</b>

✅ Успешно создан!
💳 Сумма: {amount} руб.
📝 Описание: {description}
🔗 Ссылка: <a href="{payment_url}">Оплатить</a>
🆔 ID платежа: <code>{external_id}</code>

⏱ Ссылка действительна 60 минут.</big></big>"""
            
            return message
        else:
            return f"❌ Ошибка: {data.get('message', 'Попробуйте другую сумму')}", 400
    except Exception as e:
        return f"❌ Ошибка сервера: {str(e)}", 500

@app.route('/health', methods=['GET'])
def health():
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
