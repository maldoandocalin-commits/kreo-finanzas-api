import os
import random
import resend
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

resend.api_key = os.environ.get("RESEND_API_KEY")

@app.route('/api/enviar-pin-firma', methods=['POST'])
def enviar_pin_firma():
    try:
        data = request.get_json()
        email_destino = data.get("email")
        nombre = data.get("nombre", "Cliente")
        
        # Generar PIN aleatorio de 4 dígitos
        pin = str(random.randint(1000, 9999))
        
        params = {
            "from": "Kreo Finanzas <no-reply@acreditmh.store>",
            "to": [email_destino],
            "subject": "Tu código de verificación PIN - Kreo Finanzas",
            "html": f"""
                <div style="font-family: Arial, sans-serif; padding: 20px; color: #2A1B4D;">
                    <h2>Kreo Finanzas - Verificación de Identidad</h2>
                    <p>Hola <b>{nombre}</b>,</p>
                    <p>Tu código PIN de seguridad para firmar el contrato es:</p>
                    <h1 style="color: #4B2E83; letter-spacing: 5px;">{pin}</h1>
                    <p>Si no solicitaste este código, puedes ignorar este mensaje.</p>
                </div>
            """
        }
        
        # Enviar a través de la API de Resend
        response = resend.Emails.send(params)
        print("Respuesta de Resend:", response)
        
        return jsonify({
            "status": "success",
            "pin": pin,
            "message": "Correo enviado correctamente"
        }), 200

    except Exception as e:
        print("Error al enviar correo con Resend:", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
