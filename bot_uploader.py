import os
import telebot
from keys import TELEGRAM_TOKEN, USUARIO_AUTORIZADO
from notion_image_uploader import analizar_imagen_cerveza, enviar_cervezas_a_notion

# Inicializar bot
bot = telebot.TeleBot(TELEGRAM_TOKEN)

usuarios = {}

# Restricción de acceso
def es_usuario_autorizado(message):
    return message.from_user.id == int(USUARIO_AUTORIZADO)

def acceso_restringido(func):
    def wrapper(message):
        if not es_usuario_autorizado(message):
            bot.reply_to(message, "⛔ No estás autorizado para usar este bot.")
            return
        return func(message)
    return wrapper

# Comando /start
@bot.message_handler(commands=['start'])
@acceso_restringido
def start(message):
    bot.send_message(message.chat.id, "🍻 ¿Dónde estás probando las cervezas? (v1.1)")
    usuarios[message.chat.id] = {"estado": "esperando_lugar"}

# Capturar el lugar
@bot.message_handler(func=lambda msg: msg.chat.id in usuarios and usuarios[msg.chat.id]["estado"] == "esperando_lugar")
@acceso_restringido
def recibir_lugar(message):
    usuarios[message.chat.id]["lugar"] = message.text.strip()
    usuarios[message.chat.id]["estado"] = "esperando_foto"
    bot.send_message(message.chat.id, "📷 Ahora envíame una foto de la carta o etiquetas de cervezas.")

# Capturar imagen
@bot.message_handler(content_types=['photo'])
@acceso_restringido
def recibir_foto(message):
    estado = usuarios.get(message.chat.id, {})
    if estado.get("estado") != "esperando_foto":
        bot.reply_to(message, "Primero dime dónde estás (usa /start).")
        return

    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    ruta_img = f"imagenes/{file_id}.jpg"
    os.makedirs("imagenes", exist_ok=True)
    with open(ruta_img, 'wb') as f:
        f.write(downloaded_file)

    bot.send_message(message.chat.id, "🔍 Procesando la imagen...")

    try:
        datos = analizar_imagen_cerveza(ruta_img) 
        lugar = usuarios[message.chat.id]["lugar"]
        enviar_cervezas_a_notion(datos, lugar)  
        bot.send_message(message.chat.id, "✅ Cervezas registradas exitosamente en Notion.")
        bot.send_message(message.chat.id, "Califica las cervezas aquí: https://www.notion.so/a5e415e423764b9cbe76ff6834f09e1d?v=ec1be78074934557979a77428b38abab")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error al procesar la imagen: {str(e)}")

    usuarios.pop(message.chat.id, None)

# Fallback
@bot.message_handler(func=lambda message: True)
def fallback(message):
    if not es_usuario_autorizado(message):
        return
    bot.reply_to(message, "Por favor, inicia con /start para registrar una cerveza.")

# Iniciar el bot
if __name__ == "__main__":
    print("🤖 Bot en ejecución...")
    bot.polling()
