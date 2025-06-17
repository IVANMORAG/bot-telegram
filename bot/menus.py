from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def build_main_menu():
    keyboard = [
        [InlineKeyboardButton("📸 Subir Imagen MRI", callback_data="upload_image")],
        [InlineKeyboardButton("😊 Reconocer Emociones", callback_data="upload_emotion_image")],  # Nueva opción
        [InlineKeyboardButton("📊 Seleccionar Tarea", callback_data="select_task")],
        [InlineKeyboardButton("❓ Ayuda", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)

def build_task_menu():
    keyboard = []
    for i in range(1, 10, 2):  # Dos tareas por fila
        row = [
            InlineKeyboardButton(f"Task {i}", callback_data=f"task_{i}"),
            InlineKeyboardButton(f"Task {i+1}", callback_data=f"task_{i+1}") if i < 9 else None,
        ]
        keyboard.append([btn for btn in row if btn])
    keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def build_emotion_menu():
    keyboard = [
        [InlineKeyboardButton("📸 Subir Nueva Imagen", callback_data="upload_emotion_image")],
        [InlineKeyboardButton("📜 Ver Historial", callback_data="view_emotion_history")],
        [InlineKeyboardButton("🔙 Volver", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)