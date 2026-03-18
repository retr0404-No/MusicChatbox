# main.py - Servidor FastAPI para WhatsApp con IA de Gemini
#Acuerdate en lo de ngrok poner el puerto 8000 para que funcione el webhook
#el link de ngrok es el que debes poner en la configuración del webhook de Twilio, con la ruta /whatsapp al final (ejemplo: https://abc123.ngrok.io/whatsapp)
#corre el archivo main.py

import os
import mysql.connector
from mysql.connector import Error
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Response
import uvicorn

# 1. CONFIGURACIÓN DE ENTORNO Y GEMINI
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('models/gemini-2.5-flash') # Actualizado a la versión estable

# 2. CONFIGURACIÓN DE LA BASE DE DATOS
"""
Esta sección maneja la conexión con MySQL. 
Asegúrate de que los datos de host, user y password 
coincidan con tu configuración local.
"""
def conectar_db():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        return connection
    except Error as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None

# 3. FUNCIONES DE PERSISTENCIA
def registrar_interaccion(telefono, rol, contenido):
    # Primero registramos al usuario si no existe
    conn = conectar_db()
    if conn:
        cursor = conn.cursor()
        # Insertar usuario (se ignora si ya existe el teléfono)
        cursor.execute("INSERT IGNORE INTO Usuarios (telefono) VALUES (%s)", (telefono,))
        
        # Insertar el mensaje en el historial
        query = "INSERT INTO Historial (telefono_usuario, rol, contenido) VALUES (%s, %s, %s)"
        cursor.execute(query, (telefono, rol, contenido))
        
        conn.commit()
        cursor.close()
        conn.close()

def obtener_memoria(telefono, limite=6):
    """
    Recupera los últimos mensajes para que la IA
    tenga contexto de la conversación actual.
    """
    conn = conectar_db()
    contexto = ""
    if conn:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT rol, contenido FROM Historial WHERE telefono_usuario = %s ORDER BY fecha_envio DESC LIMIT %s"
        cursor.execute(query, (telefono, limite))
        filas = cursor.fetchall()
        # Invertimos para que el orden sea cronológico
        for msg in reversed(filas):
            contexto += f"{msg['rol']}: {msg['contenido']}\n"
        cursor.close()
        conn.close()
    return contexto

# 4. CONFIGURACIÓN DE FASTAPI
app = FastAPI()

# 5. LÓGICA DE CHAT CON IA
def chatear_con_bot(telefono, mensaje_usuario):
    try:
        # Recuperamos conversaciones pasadas de la DB
        historial_previo = obtener_memoria(telefono)
        
        instruccion = (
            "Eres un asistente experto en música. "
            "Responde de forma breve (máximo 2 párrafos). "
            f"Contexto previo:\n{historial_previo}"
        )
        
        # Generar respuesta
        response = model.generate_content(f"{instruccion}\nUsuario: {mensaje_usuario}")
        texto_final = response.text
        
        if len(texto_final) > 1500:
            texto_final = texto_final[:1500] + "..."
            
        return texto_final
    except Exception as e:
        return f"Error de IA: {str(e)}"

# 6. RUTA PARA EL WEBHOOK DE WHATSAPP
@app.post("/whatsapp")
async def whatsapp_webhook(Body: str = Form(...), From: str = Form(...)):
    print(f"📱 Recibido de {From}: {Body}")
    
    try:
        # A. Guardar lo que dijo el usuario en la DB
        registrar_interaccion(From, "user", Body)

        # B. Obtener respuesta de la IA (incluye memoria)
        respuesta_ia = chatear_con_bot(From, Body)

        # C. Guardar lo que respondió la IA en la DB
        registrar_interaccion(From, "assistant", respuesta_ia)

        print(f"🤖 IA responde: {respuesta_ia[:50]}...") 

        # Formato TwiML para WhatsApp
        twiml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{respuesta_ia}</Message>
</Response>"""
        
        return Response(content=twiml_content, media_type="application/xml")
    
    except Exception as e:
        print(f"❌ Error general: {e}")
        error_msg = "<?xml version='1.0' encoding='UTF-8'?><Response><Message>Lo siento, hubo un error técnico.</Message></Response>"
        return Response(content=error_msg, media_type="application/xml")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
    
    """
 NOTA: Para producción, considera usar un servidor ASGI como Daphne o Uvicorn con Gunicorn, y asegúrate de manejar la configuración de seguridad y escalabilidad adecuadamente.
def obtener_o_crear_usuario(telefono):
    conn = sqlite3.connect('music_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE telefono = ?", (telefono,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO usuarios (telefono) VALUES (?)", (telefono,))
        conn.commit()
        user_id = cursor.lastrowid
    else:
        user_id = user[0]
    conn.close()
    return user_id

Función para guardar mensajes en el historial
def guardar_mensaje(user_id, rol, contenido):
    conn = sqlite3.connect('music_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO historial (usuario_id, rol, contenido) VALUES (?, ?, ?)", 
                   (user_id, rol, contenido))
    conn.commit()
    conn.close()
    """