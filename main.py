# Primer proyecto de chatbot musical con IA generativa y persistencia en MySQL
#COMP4480.ARTIFICIAL INTELLIGENCE

#Importamos las librerías necesarias para la aplicación

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
        
# Función para recuperar el historial de mensajes
def obtener_memoria(telefono, limite=6):
    conn = conectar_db()
    contexto = ""
    if conn:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT rol, contenido FROM Historial WHERE telefono_usuario = %s ORDER BY fecha_envio DESC LIMIT %s"
        cursor.execute(query, (telefono, limite))
        filas = cursor.fetchall()
        
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
    
