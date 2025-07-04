import os
import logging
import requests
import base64
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from PIL import Image
import io
import uuid
from bot.config import (
    BRAIN_MRI_URL,
    MARKETING_MRI_REPORT_URL,
    MARKETING_BASE_URL,
    STATIC_URL,
    EMOTION_API_URL,
    UPLOADS_DIR,
    STATIC_DIR,
    logger,
)
from bot.menus import build_main_menu, build_task_menu, build_emotion_menu
from bot.plotter import generate_plot

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /start"""
    await update.message.reply_text(
        "¡Bienvenido a MRI Analysis Bot! 🧠\n"
        "Usa los botones para subir una imagen MRI, analizar emociones o explorar las tareas (Task 1-9).",
        reply_markup=build_main_menu(),
    )

async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /upload"""
    context.user_data["state"] = "awaiting_image"
    await update.message.reply_text(
        "Por favor, sube una imagen MRI (PNG/JPG).",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Cancelar", callback_data="main_menu")]
        ]),
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /help"""
    await update.message.reply_text(
        "📚 **Ayuda de MRI Analysis Bot**\n"
        "- `/start`: Inicia el bot y muestra el menú.\n"
        "- `/upload`: Sube una imagen MRI para análisis.\n"
        "- `/tasks`: Muestra las tareas (Task 1-9).\n"
        "- Usa los botones para interactuar.\n"
        "- Nueva opción: Reconoce emociones en imágenes faciales.\n"
        "Si tienes problemas, escribe a @Fer2222.",
        reply_markup=build_main_menu(),
    )

async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /tasks"""
    await update.message.reply_text(
        "Selecciona una tarea para ver sus resultados:", reply_markup=build_task_menu()
    )

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja imágenes enviadas por el usuario"""
    state = context.user_data.get("state")
    if state not in ["awaiting_image", "awaiting_emotion_image"]:
        await update.message.reply_text(
            "Por favor, usa /upload para MRI o selecciona 'Reconocer Emociones' primero.",
            reply_markup=build_main_menu(),
        )
        return

    await update.message.reply_text("⏳ Procesando tu imagen...")

    # Obtener la imagen
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_name = f"{uuid.uuid4()}.jpg"
    file_path = os.path.join(UPLOADS_DIR, file_name)
    chat_id = update.message.chat_id

    # Descargar la imagen
    await file.download_to_drive(file_path)
    logger.info(f"Imagen descargada: {file_path}")

    try:
        if state == "awaiting_image":
            # Procesar imagen MRI con tu API directamente
            try:
                # Usar tu API directamente
                with open(file_path, "rb") as f:
                    files = {"file": (file_name, f, "image/png")}
                    response = requests.post(BRAIN_MRI_URL, files=files, timeout=120)
                response.raise_for_status()
                brain_result = response.json()
                logger.info(f"Respuesta de API de tumores: {brain_result}")
                
                # Procesar respuesta de tu API
                has_tumor = brain_result.get("has_tumor", False)
                tumor_probability = float(brain_result.get("tumor_probability", 0))
                
                # Determinar diagnóstico basado en has_tumor
                if has_tumor:
                    diagnosis = "Tumor detectado"
                    confidence = tumor_probability * 100
                else:
                    diagnosis = "Sin tumor"
                    confidence = (1 - tumor_probability) * 100
                
                # Procesar imágenes de la respuesta (en base64)
                original_image_b64 = brain_result.get("original_image", "")
                mask_image_b64 = brain_result.get("mask_image", "")
                overlay_image_b64 = brain_result.get("overlay_image", "")
                
                # Convertir overlay_image de base64 a archivo temporal si hay tumor
                tumor_file_path = None
                if has_tumor and overlay_image_b64:
                    try:
                        # Decodificar la imagen base64
                        img_data = base64.b64decode(overlay_image_b64)
                        overlay_image = Image.open(io.BytesIO(img_data))
                        
                        # Guardar imagen temporalmente
                        tumor_file_path = os.path.join(STATIC_DIR, f"tumor_{chat_id}.png")
                        overlay_image.save(tumor_file_path)
                        logger.info(f"Imagen de tumor guardada en: {tumor_file_path}")
                    except Exception as e:
                        logger.error(f"Error procesando imagen de tumor: {e}")
                
                # Generar reporte MRI con los nuevos datos
                mri_report_url = ""
                try:
                    mri_report_response = requests.post(
                        MARKETING_MRI_REPORT_URL,
                        data={"diagnosis": diagnosis, "confidence": confidence},
                        timeout=60,
                    )
                    mri_report_response.raise_for_status()
                    mri_report_result = mri_report_response.json()
                    logger.info(f"Respuesta de mri-report: {mri_report_result}")
                    mri_report_url = f"{STATIC_URL}/mri-report.png"
                except Exception as e:
                    logger.error(f"Error generando reporte MRI: {e}")
                
                # Construir mensaje de respuesta (sin caracteres especiales problemáticos)
                message = (
                    f"🧠 Resultado del Analisis MRI\n"
                    f"Diagnostico: {diagnosis}\n"
                    f"Confianza: {confidence:.2f}%\n\n"
                    "📈 Grafica de Confianza:"
                )

                # Enviar reporte de confianza si está disponible
                if mri_report_url:
                    try:
                        await update.message.reply_photo(
                            photo=mri_report_url, 
                            caption=message
                        )
                    except Exception as e:
                        logger.error(f"Error enviando mri-report.png: {e}")
                        await update.message.reply_text(message)
                else:
                    await update.message.reply_text(message)

                # Enviar imagen con tumor marcado si se detectó tumor
                if has_tumor and tumor_file_path and os.path.exists(tumor_file_path):
                    try:
                        with open(tumor_file_path, "rb") as tumor_file:
                            await update.message.reply_photo(
                                photo=tumor_file,
                                caption="🩻 Imagen con zona del tumor marcada",
                            )
                    except Exception as e:
                        logger.error(f"Error enviando imagen del tumor: {e}")

                # Enviar datos a n8n para el correo (opcional, no afecta el flujo principal)
                try:
                    n8n_webhook_url = "https://ivanmorag12.app.n8n.cloud/webhook-test/mri-upload"
                    n8n_data = {
                        "diagnosis": diagnosis,
                        "confidence": confidence,
                        "chat_id": str(chat_id),
                        "has_tumor": has_tumor
                    }
                    n8n_response = requests.post(n8n_webhook_url, json=n8n_data, timeout=30)
                    logger.info(f"Datos enviados a n8n: {n8n_response.status_code}")
                except Exception as n8n_error:
                    logger.error(f"Error enviando a n8n (no crítico): {n8n_error}")

                context.user_data["state"] = None
                await update.message.reply_text(
                    "Selecciona una tarea para ver mas analisis:", reply_markup=build_task_menu()
                )
                
            except requests.exceptions.RequestException as api_error:
                logger.error(f"Error al conectar con API de tumores: {api_error}")
                await update.message.reply_text(
                    "⚠️ Error al procesar la imagen MRI. Intenta de nuevo.",
                    reply_markup=build_main_menu(),
                )

        elif state == "awaiting_emotion_image":
            # Procesar imagen para reconocimiento de emociones (SIN CAMBIOS)
            try:
                with open(file_path, "rb") as f:
                    files = {"image": (file_name, f, "image/jpeg")}
                    response = requests.post(f"{EMOTION_API_URL}/upload", files=files, timeout=60)
                response.raise_for_status()
                result = response.json()
                logger.info(f"Respuesta de la API de emociones: {result}")

                if "error" in result:
                    raise Exception(result["error"])

                # Obtener las imágenes procesadas
                processed_images = result.get("images", [])
                if not processed_images:
                    raise Exception("No se recibieron imágenes procesadas")

                # Enviar la primera imagen (que incluye la emoción detectada)
                first_image_url = f"{EMOTION_API_URL}{processed_images[0]}"
                img_response = requests.get(first_image_url, timeout=10)
                img_response.raise_for_status()
                img_buffer = io.BytesIO(img_response.content)

                message = (
                    f"😊 **Resultado del Análisis de Emociones**\n"
                    f"Emoción detectada: Ver en la imagen\n"
                    f"Imágenes procesadas: {len(processed_images)}\n"
                    f"Resultados enviados por correo."
                )

                await update.message.reply_photo(
                    photo=img_buffer,
                    caption=message,
                    parse_mode="Markdown"
                )

                # Enviar las imágenes adicionales
                for img_path in processed_images[1:]:
                    img_url = f"{EMOTION_API_URL}{img_path}"
                    img_response = requests.get(img_url, timeout=10)
                    img_response.raise_for_status()
                    img_buffer = io.BytesIO(img_response.content)
                    await update.message.reply_photo(
                        photo=img_buffer,
                        caption="Imagen procesada adicional",
                    )

                # Enviar los datos a n8n para el correo
                try:
                    n8n_emotion_webhook_url = "https://ivanmorag12.app.n8n.cloud/webhook-test/emotion-upload"
                    
                    n8n_data = {
                        "images": processed_images, 
                        "chat_id": str(chat_id),
                        "emotion": "Ver en imagen"
                    }
                    n8n_response = requests.post(n8n_emotion_webhook_url, json=n8n_data, timeout=30)
                    n8n_response.raise_for_status()
                    logger.info(f"Respuesta de n8n para emociones: {n8n_response.json()}")
                except requests.exceptions.RequestException as n8n_error:
                    logger.error(f"Error al enviar datos a n8n: {n8n_error}")

                # Mostrar el menú de emociones
                context.user_data["state"] = None
                await update.message.reply_text(
                    "Opciones de reconocimiento de emociones:", reply_markup=build_emotion_menu()
                )

            except Exception as e:
                logger.error(f"Error al procesar imagen de emociones: {e}")
                await update.message.reply_text(
                    "⚠️ Error al procesar la imagen para emociones. Intenta de nuevo.",
                    reply_markup=build_emotion_menu(),
                )

    except Exception as e:
        logger.error(f"Error procesando imagen: {e}")
        await update.message.reply_text(
            "⚠️ Error interno. Por favor, intenta de nuevo.",
            reply_markup=build_main_menu(),
        )
    finally:
        context.user_data["state"] = None
        # Limpiar archivos temporales
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Error al eliminar {file_path}: {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception as e:
        logger.error(f"Error responding to callback query: {e}")
        return

    if query.data == "main_menu":
        await query.message.edit_text("Menú principal:", reply_markup=build_main_menu())
    elif query.data == "upload_image":
        context.user_data["state"] = "awaiting_image"
        await query.message.edit_text(
            "Por favor, sube una imagen MRI (PNG/JPG).",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Cancelar", callback_data="main_menu")]
            ]),
        )
    elif query.data == "upload_emotion_image":
        context.user_data["state"] = "awaiting_emotion_image"
        await query.message.edit_text(
            "Por favor, sube una imagen facial (JPG) para reconocer emociones.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Cancelar", callback_data="main_menu")]
            ]),
        )
    elif query.data == "view_emotion_history":
        try:
            response = requests.get(f"{EMOTION_API_URL}/historico_imagenes", timeout=60)
            response.raise_for_status()
            result = response.json()
            images = result.get("imagenes", [])

            if not images:
                await query.message.edit_text(
                    "No hay imágenes en el historial.", reply_markup=build_emotion_menu()
                )
                return

            message = "📜 **Historial de Imágenes**\nSelecciona una imagen para reprocesar:"
            keyboard = [
                [InlineKeyboardButton(f"Imagen {i+1}", callback_data=f"reprocess_{img}")]
                for i, img in enumerate(images[:5])
            ]
            keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data="emotion_menu")])
            await query.message.edit_text(
                message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error al obtener historial de emociones: {e}")
            await query.message.edit_text(
                "⚠️ Error al obtener el historial. Intenta de nuevo.",
                reply_markup=build_emotion_menu(),
            )
    elif query.data == "emotion_menu":
        await query.message.edit_text(
            "Opciones de reconocimiento de emociones:", reply_markup=build_emotion_menu()
        )
    elif query.data.startswith("reprocess_"):
        image_path = query.data.split("reprocess_")[1]
        try:
            n8n_reprocess_webhook_url = "https://ivanmorag12.app.n8n.cloud/webhook-test/emotion-reprocess"
            n8n_data = {"imageUrl": image_path}
            response = requests.post(n8n_reprocess_webhook_url, json=n8n_data, timeout=60)
            response.raise_for_status()
            
            await query.message.reply_text(
                "✅ **Reprocesamiento iniciado**\n"
                "Las imágenes reprocesadas se enviarán por correo electrónico.",
                parse_mode="Markdown"
            )
            
            await query.message.reply_text(
                "Opciones de reconocimiento de emociones:", reply_markup=build_emotion_menu()
            )
        except Exception as e:
            logger.error(f"Error al reprocesar imagen: {e}")
            await query.message.reply_text(
                "⚠️ Error al reprocesar la imagen. Intenta de nuevo.",
                reply_markup=build_emotion_menu(),
            )
    elif query.data == "select_task":
        await query.message.edit_text(
            "Selecciona una tarea:", reply_markup=build_task_menu()
        )
    elif query.data == "help":
        await query.message.edit_text(
            "📚 **Ayuda de MRI Analysis Bot**\n"
            "- Usa 'Subir Imagen MRI' para analizar una imagen.\n"
            "- Usa 'Reconocer Emociones' para analizar emociones faciales.\n"
            "- Usa 'Seleccionar Tarea' para ver análisis (Task 1-9).\n"
            "- Escribe /start para volver al menú.\n"
            "Contacta a @Fer2222 para soporte.",
            reply_markup=build_main_menu(),
        )
    elif query.data.startswith("task_"):
        task_number = query.data.split("_")[1]
        try:
            endpoint = (
                f"{MARKETING_BASE_URL}/task{task_number}-visualization"
                if task_number == "9"
                else f"{MARKETING_BASE_URL}/task{task_number}"
            )
            task_response = requests.get(endpoint, timeout=60)
            task_response.raise_for_status()
            task_result = task_response.json()
            logger.info(f"Respuesta de task{task_number}: {task_result}")

            # Formatear mensaje y tabla (resto del código igual...)
            if task_number == "1":
                nodes = ", ".join([node["label"] for node in task_result["nodes"]])
                message = f"📊 **Task 1: Diagrama Conceptual**\nFlujo: {nodes}"
                table = (
                    "```\nNodo | Nivel\n"
                    "-----|------\n" +
                    "\n".join(
                        [f"{node['label'].replace('\n', ' ')} | {node['level']}"
                         for node in task_result["nodes"]]
                    ) +
                    "\n```"
                )
            elif task_number == "2":
                dtypes = ", ".join(
                    [f"{t['type']}: {t['count']}" for t in task_result["dtypes"]]
                )
                message = (
                    f"📊 **Task 2: Análisis de Datos**\nTipos: {dtypes}\n"
                    f"Filas: {task_result['data_info']['rows']}"
                )
                table = (
                    "```\nColumna | Nulos\n"
                    "--------|------\n" +
                    "\n".join(
                        [f"{n['column']} | {n['null_count']}"
                         for n in task_result["nulls"][:5]]
                    ) +
                    "\n```"
                )
            elif task_number == "3":
                countries = ", ".join(
                    [f"{c['country']}: {c['count']}" for c in task_result["country"][:3]]
                )
                message = (
                    f"📊 **Task 3: Conteos Categóricos**\nPaíses (top 3): {countries}"
                )
                table = (
                    "```\nCategoría | Conteo\n"
                    "----------|-------\n" +
                    "\n".join(
                        [f"{d['dealsize']} | {d['count']}"
                         for d in task_result["dealsize"]]
                    ) +
                    "\n```"
                )
            elif task_number == "4":
                message = (
                    f"📊 **Task 4: Correlaciones**\n"
                    f"Ventas - Media: {task_result['sales_dist']['mean']:.2f}"
                )
                table = (
                    "```\nVariable | Correlación con Ventas\n"
                    "---------|----------------------\n" +
                    "\n".join(
                        [f"{row['index']} | {row['SALES']:.2f}"
                         for row in task_result["correlation"][:3]]
                    ) +
                    "\n```"
                )
            elif task_number == "5":
                steps = ", ".join(task_result["description"]["steps"])
                message = (
                    f"📊 **Task 5: K-Means**\n{task_result['description']['what_is']}\n"
                    f"Pasos: {steps}"
                )
                table = (
                    "```\nPunto | Cluster\n"
                    "------|--------\n" +
                    "\n".join(
                        [f"({p['x']}, {p['y']}) | {p['cluster']}"
                         for p in task_result["points"][:3]]
                    ) +
                    "\n```"
                )
            elif task_number == "6":
                message = f"📊 **Task 6: Método del Codo**\nK óptimo: {task_result['optimal_k']}"
                table = (
                    "```\nK | Inercia\n"
                    "---|--------\n" +
                    "\n".join(
                        [f"{r} | {s:.2f}" for r, s in zip(task_result["range"][:3], task_result["scores"][:3])]
                    ) +
                    "\n```"
                )
            elif task_number == "7":
                message = (
                    f"📊 **Task 7: Clusters K-Means**\n"
                    f"Cluster 0 - Tamaño: {task_result['cluster_stats'][0]['size']}"
                )
                table = (
                    "```\nCluster | Tamaño | Ventas Totales\n"
                    "--------|--------|---------------\n" +
                    "\n".join(
                        [f"{s['cluster']} | {s['size']} | {s['total_sales']:.2f}"
                         for s in task_result["cluster_stats"][:3]]
                    ) +
                    "\n```"
                )
            elif task_number == "8":
                message = (
                    f"📊 **Task 8: PCA 3D**\n"
                    f"Varianza explicada: {task_result['variance'][2]:.2%}"
                )
                table = (
                    "```\nPunto | X | Y | Z | Cluster\n"
                    "------|---|--|---|--------\n" +
                    "\n".join(
                        [f"Point {i} | {p['x']:.2f} | {p['y']:.2f} | {p['z']:.2f} | {p['cluster']}"
                         for i, p in enumerate(task_result["points"][:3])]
                    ) +
                    "\n```"
                )
            elif task_number == "9":
                message = (
                    f"📊 **Task 9: Autoencoder**\n"
                    f"{task_result['data']['description']['what_is']}\n\n"
                    "📈 **Gráfica de Arquitectura**:"
                )
                table = f"```\n{task_result['plain_table']}\n```"

            # Generar imágenes
            image_paths = generate_plot(task_number, task_result)

            if task_number == "9" and not image_paths:
                try:
                    autoencoder_url = f"{STATIC_URL}/autoencoder.png"
                    img_response = requests.get(autoencoder_url, timeout=10)
                    img_response.raise_for_status()
                    content_type = img_response.headers.get("Content-Type", "")
                    if "image/png" not in content_type:
                        logger.warning(f"Content-Type inválido para {autoencoder_url}: {content_type}")
                        raise ValueError("No es una imagen PNG")
                    image_paths = [autoencoder_url]
                except Exception as e:
                    logger.error(f"Error al descargar autoencoder.png: {e}")
                    image_paths = generate_plot(task_number, task_result)

            sent_message = False
            for i, image_path in enumerate(image_paths):
                try:
                    if image_path.startswith("http"):
                        img_response = requests.get(image_path, timeout=10)
                        img_response.raise_for_status()
                        img_buffer = io.BytesIO(img_response.content)
                        await query.message.reply_photo(
                            photo=img_buffer,
                            caption=message if i == 0 else f"Gráfica adicional para Task {task_number}",
                            parse_mode="Markdown",
                        )
                    else:
                        if not os.path.exists(image_path):
                            logger.error(f"Archivo no encontrado: {image_path}")
                            raise FileNotFoundError(f"Archivo no encontrado: {image_path}")
                        with open(image_path, "rb") as img_file:
                            await query.message.reply_photo(
                                photo=img_file,
                                caption=message if i == 0 else f"Gráfica adicional para Task {task_number}",
                                parse_mode="Markdown",
                            )
                    sent_message = True
                    logger.info(f"Imagen enviada para Task {task_number}: {image_path}")
                except Exception as e:
                    logger.error(f"Error enviando imagen para Task {task_number}, índice {i}: {e}")
                    continue

            if not sent_message:
                logger.warning(f"No se enviaron imágenes para Task {task_number}")
                await query.message.reply_text(
                    message, reply_markup=build_task_menu(), parse_mode="Markdown"
                )

            await query.message.reply_text(table, parse_mode="Markdown", reply_markup=build_task_menu())

        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener task{task_number}: {e}")
            await query.message.reply_text(
                f"⚠️ Error al obtener Task {task_number}. Intenta de nuevo.",
                reply_markup=build_task_menu(),
            )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja errores globales"""
    logger.error(f"Error: {context.error}")
    if update and update.message:
        await update.message.reply_text(
            "⚠️ Ocurrió un error. Por favor, intenta de nuevo.",
            reply_markup=build_main_menu(),
        )