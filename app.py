import base64
from datetime import datetime, timedelta
import os
import random
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

app = Flask(__name__)
CORS(app)  # Esto evita cualquier bloqueo entre puertos

# Configuración de remitente profesional con Resend
REMITENTE = "Kreo Finanzas <contacto@acreditmh.store>"


def enviar_email_resend(
    destinatario, asunto, contenido_html, pdf_path=None, nombre_pdf=None
):
  """Función universal para enviar correos transaccionales (PINs y Contratos)

  a través de la API HTTP de Resend, evitando bloqueos en la nube.
  """
  api_key = os.environ.get("RESEND_API_KEY")
  url = "https://api.resend.com/emails"

  headers = {
      "Authorization": f"Bearer {api_key}",
      "Content-Type": "application/json",
  }

  payload = {
      "from": REMITENTE,
      "to": [destinatario],
      "subject": asunto,
      "html": contenido_html,
  }

  # Si se adjunta un contrato en PDF, se convierte a Base64 para enviarlo por la API
  if pdf_path and os.path.exists(pdf_path):
    with open(pdf_path, "rb") as f:
      pdf_bytes = f.read()
      pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

    payload["attachments"] = [{
        "filename": nombre_pdf or "Contrato_Kreo_Finanzas.pdf",
        "content": pdf_base64,
    }]

  try:
    response = requests.post(url, json=payload, headers=headers)
    return response.json()
  except Exception as e:
    print(f"Error al conectar con la API de Resend: {e}")
    return {"error": str(e)}


def generar_pdf_contrato(
    nombre,
    dni,
    monto,
    plazo,
    fecha_vencimiento,
    total,
    nro_contrato,
    fecha_emision,
    archivo_salida,
    pin_firma="",
):
  doc = SimpleDocTemplate(
      archivo_salida,
      pagesize=letter,
      rightMargin=35,
      leftMargin=35,
      topMargin=25,
      bottomMargin=25,
  )
  story = []
  styles = getSampleStyleSheet()

  estilo_texto = ParagraphStyle(
      "TextoNormal",
      parent=styles["Normal"],
      fontName="Helvetica",
      fontSize=7.2,
      textColor=colors.HexColor("#1E293B"),
      leading=9.2,
  )

  estilo_der = ParagraphStyle("TextoDerecha", parent=estilo_texto, alignment=2)

  estilo_bold_der = ParagraphStyle(
      "BoldDerecha", parent=estilo_texto, fontName="Helvetica-Bold", alignment=2
  )

  try:
    monto_val = float(monto)
  except:
    monto_val = 100.0
  try:
    plazo_val = float(plazo)
  except:
    plazo_val = 30.0
  try:
    total_val = float(total)
  except:
    total_val = 113.50

  cuotas_count = int(plazo_val / 15)
  if cuotas_count < 1:
    cuotas_count = 1

  meses = plazo_val / 30.0

  # MATRIZ DE TOTALES EXACTOS PARA 1 MES (30 DÍAS)
  totales_un_mes = {
      100: 113.50,
      200: 223.50,
      300: 333.50,
      400: 443.50,
      500: 553.50,
      600: 663.50,
      700: 773.50,
      800: 883.50,
      900: 993.50,
      1000: 1103.50,
  }

  monto_int = int(monto_val)
  base_un_mes = totales_un_mes.get(
      monto_int, monto_val + 13.50 * (monto_val / 100.0)
  )
  ganancia_un_mes = base_un_mes - monto_val

  # Total real proporcional a los meses
  total_calculado_real = monto_val + (ganancia_un_mes * meses)
  if total_val <= monto_val:
    total_val = total_calculado_real

  # Desglose transparente legal
  interes_calculado = round(monto_val * 0.045 * meses, 2)
  comision_calculada = round(
      (ganancia_un_mes * meses) - interes_calculado, 2
  )
  if comision_calculada < 0:
    comision_calculada = 0.00

  # TCEA y TCEM según el plazo
  if meses == 1.0:
    tcea_str = "48.20 %"
    tcem_str = "4.50 %"
  elif meses == 2.0:
    tcea_str = "52.10 %"
    tcem_str = "4.75 %"
  else:
    tcea_str = "55.40 %"
    tcem_str = "4.90 %"

  # --- CABECERA ---
  header_data = [
      [
          Paragraph(
              "<b><font color='#4B2E83' size='14'>kreo</font><font"
              " color='#FF6B5A' size='14'>finanzas</font></b><br/><font"
              " size='7' color='#4B2E83'><b>Kreo Finanzas</b><br/>Inversiones MH"
              " S.A.C.S.</font>",
              estilo_texto,
          ),
          Paragraph(
              f"<b>Contrato de Préstamo N.°</b><br/><b>{nro_contrato}</b><br/><font"
              f" size='7' color='#64748B'>Fecha: {fecha_emision}</font>",
              estilo_der,
          ),
      ]
  ]
  t_header = Table(header_data, colWidths=[260, 280])
  t_header.setStyle(
      TableStyle([
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
      ])
  )
  story.append(t_header)
  story.append(Spacer(1, 4))

  intro_str = (
      f"Mediante el presente documento, Inversiones MH S.A.C.S. se obliga a"
      f" efectuar el desembolso de {monto_val:.2f} PEN a favor de {nombre},"
      f' identificado con D.N.I. N° {dni} (el "Usuario"), y el Usuario se'
      f" compromete a devolver dicho monto en **{cuotas_count} cuotas"
      f" sucesivas de carácter quincenal** a Inversiones MH S.A.C.S., más los"
      f" intereses generados de acuerdo con las condiciones siguientes."
  )
  story.append(Paragraph(intro_str, estilo_texto))
  story.append(Spacer(1, 4))

  partes_data = [
      [
          Paragraph("Nombre", estilo_texto),
          Paragraph("Inversiones MH S.A.C.S.", estilo_texto),
      ],
      [
          Paragraph("R.U.C. N.°", estilo_texto),
          Paragraph("20473766987", estilo_texto),
      ],
      [
          Paragraph(
              "<b>Prestatario</b>",
              ParagraphStyle(
                  "Sub",
                  parent=estilo_texto,
                  fontName="Helvetica-Bold",
                  fontSize=8,
              ),
          ),
          Paragraph("", estilo_texto),
      ],
      [
          Paragraph("Nombre y apellidos:", estilo_texto),
          Paragraph(f"{nombre}", estilo_texto),
      ],
      [
          Paragraph("D.N.I. :", estilo_texto),
          Paragraph(f"{dni}", estilo_texto),
      ],
  ]
  t_partes = Table(partes_data, colWidths=[140, 400])
  t_partes.setStyle(
      TableStyle([
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 1.5),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
          ("LINEBELOW", (0, 1), (-1, 1), 0.8, colors.HexColor("#CBD5E1")),
          ("LINEBELOW", (0, 4), (-1, 4), 0.8, colors.HexColor("#CBD5E1")),
      ])
  )
  story.append(t_partes)
  story.append(Spacer(1, 4))

  story.append(
      Paragraph(
          "Suscriben un Contrato de Préstamo Rápido al Consumo con las"
          " siguientes condiciones, previamente conocidas y aceptadas por las"
          " partes",
          estilo_texto,
      )
  )
  story.append(Spacer(1, 3))

  story.append(
      Paragraph(
          "<b>Condiciones del Contrato de Préstamo</b>",
          ParagraphStyle(
              "CondT",
              parent=estilo_texto,
              fontName="Helvetica-Bold",
              fontSize=8.5,
          ),
      )
  )
  story.append(Spacer(1, 2))

  cond_data = [
      [
          Paragraph("Monto del capital:", estilo_texto),
          Paragraph(f"{monto_val:.2f} PEN", estilo_der),
      ],
      [
          Paragraph("Tasa de interés compensatorio:", estilo_texto),
          Paragraph("4.50 % mensual", estilo_der),
      ],
      [
          Paragraph("Tasa de interés moratorio:", estilo_texto),
          Paragraph("15.00 %", estilo_der),
      ],
      [
          Paragraph("Comisión de Administración y Soporte:", estilo_texto),
          Paragraph(f"{comision_calculada:.2f} PEN", estilo_der),
      ],
      [
          Paragraph("TCEA:", estilo_texto),
          Paragraph(tcea_str, estilo_der),
      ],
      [
          Paragraph("TCEM:", estilo_texto),
          Paragraph(tcem_str, estilo_der),
      ],
      [
          Paragraph("Plazo y Modalidad:", estilo_texto),
          Paragraph(
              f"{plazo} días ({cuotas_count} cuotas quincenales)", estilo_der
          ),
      ],
      [
          Paragraph("Fecha de Vencimiento Final:", estilo_texto),
          Paragraph(f"{fecha_vencimiento}", estilo_der),
      ],
      [
          Paragraph("Penalidad por atraso:", estilo_texto),
          Paragraph("20.00 PEN<br/>por cada cinco (5) días", estilo_der),
      ],
      [
          Paragraph("Monto Total a Pagar:", estilo_texto),
          Paragraph(
              f"{total_val:.2f} PEN<br/>por concepto de capital:"
              f" {monto_val:.2f}<br/>por concepto de intereses:"
              f" {interes_calculado:.2f}<br/>por concepto de comisión:"
              f" {comision_calculada:.2f}",
              estilo_der,
          ),
      ],
      [
          Paragraph("IGV:", estilo_texto),
          Paragraph("0.00 PEN / [no aplica]", estilo_der),
      ],
      [
          Paragraph(f"<b>Total general:</b>", estilo_texto),
          Paragraph(f"<b>{total_val:.2f} PEN</b>", estilo_bold_der),
      ],
      [
          Paragraph("Pago anticipado:", estilo_texto),
          Paragraph(
              "Aplicable sin comisiones ni penalidades adicionales", estilo_der
          ),
      ],
  ]

  t_cond = Table(cond_data, colWidths=[220, 320])
  t_cond.setStyle(
      TableStyle([
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 1),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
          ("LINEABOVE", (0, 0), (-1, 0), 0.8, colors.HexColor("#CBD5E1")),
          ("LINEBELOW", (0, -1), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
      ])
  )
  story.append(t_cond)
  story.append(Spacer(1, 6))

  story.append(
      Paragraph(
          f"<b>Cronograma de Pagos ({cuotas_count} Cuotas Quincenales)</b>",
          ParagraphStyle(
              "CronT",
              parent=estilo_texto,
              fontName="Helvetica-Bold",
              fontSize=8.5,
          ),
      )
  )
  story.append(Spacer(1, 2))

  cronograma_rows = [
      [
          Paragraph(
              "<b>N.° Cuota</b>",
              ParagraphStyle("Th1", parent=estilo_texto, fontName="Helvetica-Bold"),
          ),
          Paragraph(
              "<b>Fecha de Vencimiento</b>",
              ParagraphStyle("Th2", parent=estilo_texto, fontName="Helvetica-Bold"),
          ),
          Paragraph(
              "<b>Monto a Pagar (PEN)</b>",
              ParagraphStyle(
                  "Th3", parent=estilo_der, fontName="Helvetica-Bold"
              ),
          ),
      ]
  ]

  try:
    dt_emision = datetime.strptime(fecha_emision, "%d.%m.%Y")
  except:
    dt_emision = datetime.now()

  monto_cuota_base = round(total_val / cuotas_count, 2)
  acumulado = 0.0

  for i in range(1, cuotas_count + 1):
    fecha_cuota = dt_emision + timedelta(days=15 * i)
    fecha_cuota_str = fecha_cuota.strftime("%d.%m.%Y")

    if i == cuotas_count:
      monto_cuota = round(total_val - acumulado, 2)
    else:
      monto_cuota = monto_cuota_base
      acumulado += monto_cuota

    cronograma_rows.append([
        Paragraph(f"Cuota {i}", estilo_texto),
        Paragraph(fecha_cuota_str, estilo_texto),
        Paragraph(f"{monto_cuota:.2f} PEN", estilo_der),
    ])

  t_cronograma = Table(cronograma_rows, colWidths=[100, 200, 240])
  t_cronograma.setStyle(
      TableStyle([
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 1.5),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
          ("LINEABOVE", (0, 0), (-1, 0), 0.8, colors.HexColor("#CBD5E1")),
          ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
          ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
          ("LINEBELOW", (0, -1), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
      ])
  )
  story.append(t_cronograma)
  story.append(Spacer(1, 6))

  final_str = (
      f"El prestatario declara conocer y aceptar las condiciones del presente"
      f" Contrato de Préstamo celebrado con Kreo Finanzas e Inversiones MH"
      f" S.A.C.S. y confirma su firma electrónica mediante el PIN enviado a su"
      f" teléfono, correo o plataforma. Asimismo, declara que la información"
      f" proporcionada es correcta y que, desde la fecha {fecha_emision}, conoce"
      f" y acepta los términos y condiciones generales aplicables al"
      f" Prestatario, incluyendo el cumplimiento del cronograma de pagos"
      f" quincenales detallado. Dichos términos y condiciones forman parte"
      f" integral del presente contrato, obligan a las partes y se entienden"
      f" aceptados mediante el mecanismo de firma electrónica indicado."
  )
  story.append(
      Paragraph(
          final_str,
          ParagraphStyle(
              "Final",
              parent=estilo_texto,
              fontSize=6.5,
              leading=8.5,
              textColor=colors.HexColor("#334155"),
          ),
      )
  )

  # --- BLOQUE DE FIRMAS CON EL PIN DEL CLIENTE EN EL PDF ---
  story.append(Spacer(1, 12))
  firma_data = [
      [
          Paragraph(
              "___________________________________<br/><b>Inversiones MH"
              " S.A.C.S.</b><br/>Prestamista / Representante Legal",
              estilo_texto,
          ),
          Paragraph(
              f"___________________________________<br/><b>{nombre}</b><br/>D.N.I.:"
              f" {dni}<br/><font color='#4B2E83'><b>Firma Electrónica Válida</b><br/>PIN"
              f" de Seguridad: <b>{pin_firma}</b></font>",
              estilo_texto,
          ),
      ]
  ]
  t_firmas = Table(firma_data, colWidths=[260, 260])
  t_firmas.setStyle(
      TableStyle([
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 3),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
      ])
  )
  story.append(t_firmas)

  doc.build(story)


@app.route("/api/enviar-correo-aprobacion", methods=["POST"])
def api_enviar_correo():
  datos = request.get_json() or {}
  print("DATOS RECIBIDOS EN APROBACIÓN:", datos)
  destinatario = datos.get("email")
  nombre = datos.get("nombre", "Cliente")
  dni = datos.get("dni", "00000000")
  monto = datos.get("monto", "100.00")
  plazo = datos.get("plazo", "30")
  total = datos.get("total", "113.50")
  nro_contrato = datos.get("nro_contrato", "6744-7886-002")
  fecha_emision = datos.get("fecha_emision", "24.10.2026")
  pin_firma = datos.get("pin_firma", "PENDIENTE")

  vencimiento = datos.get("vencimiento", "")
  if not vencimiento:
    try:
      dt_emision = datetime.strptime(fecha_emision, "%d.%m.%Y")
      dt_vencimiento = dt_emision + timedelta(days=int(plazo))
      vencimiento = dt_vencimiento.strftime("%d.%m.%Y")
    except:
      vencimiento = "24.11.2026"

  if not destinatario:
    return (
        jsonify({"status": "error", "message": "Falta el correo destinatario"}),
        400,
    )

  pdf_path = f"contrato_{dni}.pdf"

  try:
    generar_pdf_contrato(
        nombre,
        dni,
        monto,
        plazo,
        vencimiento,
        total,
        nro_contrato,
        fecha_emision,
        pdf_path,
        pin_firma,
    )

    asunto = f"Contrato y Cronograma de Préstamo Desembolsado No. {nro_contrato}"
    mensaje_html = f"""
        <div style="font-family: Arial, sans-serif; color: #1E293B;">
            <h2 style="color: #4B2E83;">¡Hola {nombre}!</h2>
            <p>Le informamos que su préstamo ha sido desembolsado exitosamente a través de <b>Kreo Finanzas</b> (Inversiones MH S.A.C.S.).</p>
            <p>Le adjuntamos su contrato de préstamo número <b>{nro_contrato}</b> con su respectivo cronograma quincenal en PDF y su firma electrónica validada.</p>
            <br>
            <p style="font-size: 12px; color: #64748b;">Atentamente,<br><b>Equipo de Kreo Finanzas</b></p>
        </div>
        """

    # Envío mediante Resend API
    resultado = enviar_email_resend(
        destinatario=destinatario,
        asunto=asunto,
        contenido_html=mensaje_html,
        pdf_path=pdf_path,
        nombre_pdf=f"Contrato_Kreo_Finanzas_{dni}.pdf",
    )

    if os.path.exists(pdf_path):
      os.remove(pdf_path)

    print(
        f"¡Correo de desembolso enviado con éxito y contrato PDF adjunto para"
        f" {destinatario} mediante Resend!"
    )
    return jsonify({
        "status": "success",
        "message": "Correo y contrato de desembolso enviados con éxito",
        "resend_response": resultado,
    })
  except Exception as e:
    if os.path.exists(pdf_path):
      os.remove(pdf_path)
    print(f"Error al procesar PDF o enviar correo con Resend: {e}")
    return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/enviar-pin-firma", methods=["POST"])
def api_enviar_pin():
  datos = request.get_json() or {}
  print("--- PETICIÓN RECIBIDA EN /api/enviar-pin-firma ---")
  print("Datos JSON completos:", datos)

  destinatario = datos.get("email")
  nombre = datos.get("nombre", "Cliente")

  if not destinatario:
    print(
        "❌ ERROR 400: El campo 'email' llegó vacío o no se envió desde el"
        " frontend."
    )
    return (
        jsonify({
            "status": "error",
            "message": (
                "Falta el correo destinatario en los datos enviados al servidor"
            ),
        }),
        400,
    )

  pin = str(random.randint(1000, 9999))

  try:
    asunto = "Código de Verificación para Firma de Contrato - kreo finanzas"
    mensaje_html = f"""
        <div style="font-family: Arial, sans-serif; color: #1E293B;">
            <h2 style="color: #4B2E83;">Código de Verificación</h2>
            <p>Hola <b>{nombre}</b>,</p>
            <p>Tu código PIN de seguridad para firmar y validar tu contrato en <b>kreo finanzas</b> es:</p>
            <div style="background: #EFE9F8; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; color: #4B2E83; border-radius: 8px; letter-spacing: 4px; margin: 20px 0;">
                {pin}
            </div>
            <p>Este código es necesario para completar tu solicitud de préstamo. Si no solicitaste este código, puedes ignorar este mensaje.</p>
            <br>
            <p style="font-size: 12px; color: #64748b;">Atentamente,<br><b>Inversiones MH S.A.C.S.</b></p>
        </div>
        """

    # Envío mediante Resend API
    resultado = enviar_email_resend(
        destinatario=destinatario, asunto=asunto, contenido_html=mensaje_html
    )

    print(f"✅ PIN {pin} enviado con éxito a {destinatario} mediante Resend")
    return jsonify({
        "status": "success",
        "pin": pin,
        "message": "PIN enviado con éxito",
        "resend_response": resultado,
    })
  except Exception as e:
    print(f"❌ Error al enviar PIN con Resend: {e}")
    return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port, debug=True)
