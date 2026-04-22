@app.route('/create_invoice_get', methods=['GET'])
def create_invoice_get():
    """
    Версия для GET запросов (для PuzzleBot)
    """
    # Получаем параметры из URL
    amount = request.args.get('amount', 500, type=int)
    external_id = request.args.get('externalId', f'test_{int(time.time())}')
    description = request.args.get('description', 'VPN payment')
    
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
        
        # Успех — возвращаем ссылку
        if response.status_code == 201:
            payment_url = result.get("paymentUrl")
            return jsonify({
                "success": True,
                "message": f"✅ Ссылка на оплату: {payment_url}\n\nСсылка действительна 60 минут.",
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
