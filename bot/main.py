from telegram import Update  # Agrega esta línea
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from bot.config import TOKEN
from bot.handlers import (
    start,
    upload_command,
    help_command,
    tasks_command,
    handle_image,
    button_callback,
    error_handler,
)

def main():
    """Inicia el bot"""
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN no está configurado")

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("upload", upload_command))
    application.add_handler(CommandHandler("tasks", tasks_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_error_handler(error_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()