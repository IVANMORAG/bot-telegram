import os
import logging
import requests
import base64
import plotly.graph_objects as go
import plotly.express as px
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from PIL import Image
import io
import uuid
import math
from dotenv import load_dotenv
import aiohttp
import asyncio
from aiohttp import FormData
from dotenv import load_dotenv


load_dotenv()

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Endpoints de tus aplicaciones
BRAIN_MRI_URL = "https://mri-tumor.onrender.com/predict"
MARKETING_MRI_REPORT_URL = "https://marketing-m28z.onrender.com/api/mri-report"
MARKETING_BASE_URL = "https://marketing-m28z.onrender.com/api"
STATIC_URL = "https://marketing-m28z.onrender.com/static"

# Directorios
UPLOADS_DIR = "uploads"
STATIC_DIR = "static"
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Debug: Verifica la ruta actual y archivos
print(f"\nDirectorio actual: {os.getcwd()}")
print(f"Archivos en el directorio: {os.listdir()}\n")

# Fuerza la carga del .env
load_dotenv(override=True)  # ¡Esta línea es crucial!

# Debug: Muestra el token leído
token = os.getenv("TELEGRAM_BOT_TOKEN")
print(f"Token leído: {token}\n")

if not token:
    raise ValueError("ERROR: Token no encontrado. Verifica tu archivo .env")

# Crear el menú principal
def build_main_menu():
    keyboard = [
        [InlineKeyboardButton("📸 Subir Imagen MRI", callback_data="upload_image")],
        [InlineKeyboardButton("📊 Seleccionar Tarea", callback_data="select_task")],
        [InlineKeyboardButton("❓ Ayuda", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)

# Crear el menú de tareas
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /start"""
    await update.message.reply_text(
        "¡Bienvenido a MRI Analysis Bot! 🧠\n"
        "Usa los botones para subir una imagen MRI o explorar las tareas (Task 1-9).",
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
        "Si tienes problemas, escribe a @Fer2222.",
        reply_markup=build_main_menu(),
    )

async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /tasks"""
    await update.message.reply_text(
        "Selecciona una tarea para ver sus resultados:", reply_markup=build_task_menu()
    )

def generate_plot(task_number, task_result):
    """Genera una gráfica Plotly según la tarea, alineada con app.js"""
    figs = []
    
    try:
        if task_number == "1":
            # Diagrama conceptual (similar a renderTask1)
            nodes = task_result["nodes"]
            edge_x = []
            edge_y = []
            for link in task_result["links"]:
                source = next(n for n in nodes if n["id"] == link["source"])
                target = next(n for n in nodes if n["id"] == link["target"])
                edge_x.extend([source["x"], target["x"], None])
                edge_y.extend([source["y"], target["y"], None])
            
            fig = go.Figure(data=[
                go.Scatter(
                    x=[n["x"] for n in nodes],
                    y=[n["y"] for n in nodes],
                    mode="markers+text",
                    text=[n["label"] for n in nodes],
                    textposition="middle center",
                    marker=dict(size=30, color=["#4CA1AF", "#2C3E50", "#D4B483"][n["level"] % 3], line=dict(width=2, color="white")),
                    textfont=dict(size=12, color="white"),
                ),
                go.Scatter(
                    x=edge_x,
                    y=edge_y,
                    mode="lines",
                    line=dict(width=2, color="#888"),
                    hoverinfo="none",
                ),
            ])
            fig.update_layout(
                title="Diagrama Conceptual del Proyecto",
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.1, 1.2]),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.1, 1.1]),
                showlegend=False,
                height=400,
                width=600,
            )
            figs.append(fig)
        
        elif task_number == "2":
            # Gráficos de tipos de datos y valores nulos (similar a renderTask2)
            fig1 = go.Figure(data=[
                go.Bar(
                    x=[d["type"] for d in task_result["dtypes"]],
                    y=[d["count"] for d in task_result["dtypes"]],
                    marker_color="#4CA1AF",
                )
            ])
            fig1.update_layout(
                title="Distribución de Tipos de Datos",
                xaxis_title="Tipo de dato",
                yaxis_title="Cantidad",
                height=400,
                width=600,
            )
            figs.append(fig1)
            
            fig2 = go.Figure(data=[
                go.Bar(
                    x=[n["column"] for n in task_result["nulls"]],
                    y=[n["null_count"] for n in task_result["nulls"]],
                    marker_color="#2C3E50",
                )
            ])
            fig2.update_layout(
                title="Valores Nulos por Columna",
                xaxis_title="Columna",
                yaxis_title="Valores nulos",
                height=400,
                width=600,
            )
            figs.append(fig2)
        
        elif task_number == "3":
            # Gráficos por país, línea de producto, y tamaño de trato (similar a renderTask3)
            fig1 = go.Figure(data=[
                go.Bar(
                    x=[c["country"] for c in task_result["country"]],
                    y=[c["count"] for c in task_result["country"]],
                    marker_color="#4CA1AF",
                )
            ])
            fig1.update_layout(
                title="Distribución por País",
                xaxis_title="País",
                yaxis_title="Conteo",
                height=400,
                width=600,
            )
            figs.append(fig1)
            
            fig2 = go.Figure(data=[
                go.Bar(
                    x=[p["productline"] for p in task_result["productline"]],
                    y=[p["count"] for p in task_result["productline"]],
                    marker_color="#2C3E50",
                )
            ])
            fig2.update_layout(
                title="Distribución por Línea de Producto",
                xaxis_title="Línea de Producto",
                yaxis_title="Conteo",
                height=400,
                width=600,
            )
            figs.append(fig2)
            
            fig3 = go.Figure(data=[
                go.Bar(
                    x=[d["dealsize"] for d in task_result["dealsize"]],
                    y=[d["count"] for d in task_result["dealsize"]],
                    marker_color="#D4B483",
                )
            ])
            fig3.update_layout(
                title="Distribución por Tamaño de Trato",
                xaxis_title="Tamaño de Trato",
                yaxis_title="Conteo",
                height=400,
                width=600,
            )
            figs.append(fig3)
        
        elif task_number == "4":
            # Matriz de correlación y distribución de ventas (similar a renderTask4)
            columns = [c["index"] for c in task_result["correlation"]]
            z_values = [[c.get(col, 0) for col in columns] for c in task_result["correlation"]]
            
            fig1 = go.Figure(data=[
                go.Heatmap(
                    x=columns,
                    y=columns,
                    z=z_values,
                    colorscale="Blues",
                    zmin=-1,
                    zmax=1,
                )
            ])
            fig1.update_layout(
                title="Matriz de Correlación",
                height=400,
                width=600,
            )
            figs.append(fig1)
            
            fig2 = go.Figure(data=[
                go.Histogram(
                    x=list(task_result["sales_dist"].values())[:-1],
                    marker_color="#4CA1AF",
                )
            ])
            fig2.update_layout(
                title="Distribución de Ventas",
                xaxis_title="Ventas",
                yaxis_title="Frecuencia",
                height=400,
                width=600,
            )
            figs.append(fig2)
        
        elif task_number == "5":
            # Diagrama de K-Means (similar a renderTask5)
            cluster_colors = ["#4CA1AF", "#2C3E50", "#D4B483"]
            traces = []
            for point in task_result["points"]:
                traces.append(go.Scatter(
                    x=[point["x"]],
                    y=[point["y"]],
                    mode="markers",
                    marker=dict(size=12, color=cluster_colors[point["cluster"]]),
                    showlegend=False,
                ))
            
            traces.append(go.Scatter(
                x=[c["x"] for c in task_result["centroids"]],
                y=[c["y"] for c in task_result["centroids"]],
                mode="markers",
                marker=dict(size=20, color=cluster_colors, symbol="x", line=dict(width=2)),
                name="Centroides",
            ))
            
            for point in task_result["points"]:
                centroid = task_result["centroids"][point["cluster"]]
                traces.append(go.Scatter(
                    x=[point["x"], centroid["x"]],
                    y=[point["y"], centroid["y"]],
                    mode="lines",
                    line=dict(color="#aaa", width=1, dash="dot"),
                    showlegend=False,
                ))
            
            fig = go.Figure(data=traces)
            fig.update_layout(
                title="Diagrama Conceptual de K-Means",
                xaxis=dict(showgrid=False, zeroline=False, range=[0, 7]),
                yaxis=dict(showgrid=False, zeroline=False, range=[1.5, 4.5]),
                height=400,
                width=600,
            )
            figs.append(fig)
        
        elif task_number == "6":
            # Método del codo (similar a renderTask6)
            fig = go.Figure(data=[
                go.Scatter(
                    x=task_result["range"],
                    y=task_result["scores"],
                    mode="lines+markers",
                    line=dict(color="#4CA1AF", width=3),
                    marker=dict(size=8, color="#2C3E50"),
                ),
                go.Scatter(
                    x=[task_result["optimal_k"], task_result["optimal_k"]],
                    y=[min(task_result["scores"]), max(task_result["scores"])],
                    mode="lines",
                    line=dict(color="#D4B483", width=2, dash="dash"),
                    name="K óptimo",
                ),
            ])
            fig.update_layout(
                title="Método del Codo para K-Means",
                xaxis_title="Número de Clusters (K)",
                yaxis_title="Inercia",
                height=400,
                width=600,
                showlegend=True,
            )
            figs.append(fig)
        
        elif task_number == "7":
            # Clusters 2D (similar a renderTask7)
            cluster_colors = ["#4CA1AF", "#2C3E50", "#D4B483", "#C1666B", "#7A9CC6"]
            traces = []
            for i in range(5):
                cluster_points = [p for p in task_result["clusters"] if p["cluster"] == i]
                traces.append(go.Scatter(
                    x=[p["x"] for p in cluster_points],
                    y=[p["y"] for p in cluster_points],
                    mode="markers",
                    name=f"Cluster {i}",
                    marker=dict(size=8, color=cluster_colors[i]),
                ))
            
            traces.append(go.Scatter(
                x=[c["x"] for c in task_result["centroids"]],
                y=[c["y"] for c in task_result["centroids"]],
                mode="markers",
                name="Centroides",
                marker=dict(size=12, color=cluster_colors, symbol="x", line=dict(width=2)),
            ))
            
            fig = go.Figure(data=traces)
            fig.update_layout(
                title="Visualización 2D de Clusters (PCA)",
                xaxis_title="Componente Principal 1",
                yaxis_title="Componente Principal 2",
                height=400,
                width=600,
            )
            figs.append(fig)
        
        elif task_number == "8":
            # Visualización 3D (similar a renderTask8)
            cluster_colors = ["#4CA1AF", "#2C3E50", "#D4B483", "#C1666B", "#7A9CC6"]
            traces = []
            for i in range(5):
                cluster_points = [p for p in task_result["points"] if p["cluster"] == i]
                traces.append(go.Scatter3d(
                    x=[p["x"] for p in cluster_points],
                    y=[p["y"] for p in cluster_points],
                    z=[p["z"] for p in cluster_points],
                    mode="markers",
                    name=f"Cluster {i}",
                    marker=dict(size=5, color=cluster_colors[i], opacity=0.8),
                ))
            
            fig = go.Figure(data=traces)
            fig.update_layout(
                title="Visualización 3D de Clusters (PCA)",
                scene=dict(
                    xaxis_title="PC1",
                    yaxis_title="PC2",
                    zaxis_title="PC3",
                ),
                height=400,
                width=600,
            )
            figs.append(fig)
        
        elif task_number == "9":
            # Diagrama de Autoencoder (similar a renderTask9)
            layers = task_result["data"]["layers"]
            connections = task_result["data"]["connections"]
            node_x = [layer["x"] for layer in layers]
            node_y = [layer["y"] for layer in layers]
            node_text = [f"{layer['name']}\n({layer['units']})" for layer in layers]
            node_size = [max(10, min(30, math.sqrt(layer["units"]) * 3)) for layer in layers]
            
            edge_x = []
            edge_y = []
            for conn in connections:
                source = next(l for l in layers if l["id"] == conn["source"])
                target = next(l for l in layers if l["id"] == conn["target"])
                edge_x.extend([source["x"], target["x"], None])
                edge_y.extend([source["y"], target["y"], None])
            
            fig = go.Figure(data=[
                go.Scatter(
                    x=node_x,
                    y=node_y,
                    mode="markers+text",
                    text=node_text,
                    textposition="middle center",
                    marker=dict(size=node_size, color="#4CA1AF", line=dict(width=2, color="white")),
                    textfont=dict(size=12, color="white"),
                ),
                go.Scatter(
                    x=edge_x,
                    y=edge_y,
                    mode="lines",
                    line=dict(width=2, color="#888"),
                    hoverinfo="none",
                ),
            ])
            fig.update_layout(
                title="Diagrama de Autoencoder",
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 1.2]),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0.3, 0.7]),
                showlegend=False,
                height=400,
                width=600,
            )
            figs.append(fig)
        
        # Guardar todas las figuras como PNG
        image_paths = []
        for i, fig in enumerate(figs):
            try:
                buffer = io.BytesIO()
                fig.write_image(buffer, format="png", scale=1)
                buffer.seek(0)
                file_path = os.path.join(STATIC_DIR, f"task{task_number}_{i}.png")
                with open(file_path, "wb") as f:
                    f.write(buffer.getvalue())
                image_paths.append(file_path)
                logger.info(f"Gráfica generada: {file_path}")
            except Exception as e:
                logger.error(f"Error al guardar gráfica para Task {task_number}, índice {i}: {e}")
                continue
        
        return image_paths
    
    except Exception as e:
        logger.error(f"Error en generate_plot para Task {task_number}: {e}")
        return []

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja imágenes enviadas por el usuario"""
    await update.message.reply_text("⏳ Procesando tu imagen MRI...")
    if context.user_data.get("state") != "awaiting_image":
        await update.message.reply_text(
            "Por favor, usa /upload primero para subir una imagen.",
            reply_markup=build_main_menu(),
        )
        return

    # Obtener la imagen
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_name = f"{uuid.uuid4()}.png"
    file_path = os.path.join(UPLOADS_DIR, file_name)
    chat_id = update.message.chat_id

    # Descargar la imagen
    await file.download_to_drive(file_path)
    logger.info(f"Imagen descargada: {file_path}")

    try:
        # Intentar con n8n primero
        try:
            n8n_webhook_url = "http://localhost:5678/webhook/mri-upload"  # URL de producción
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f, "image/png")}  # Especificar nombre y MIME
                data = {"chat_id": str(chat_id)}
                response = requests.post(n8n_webhook_url, files=files, data=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Respuesta de n8n: {result}")
            source = "n8n"
        except requests.exceptions.RequestException as n8n_error:
            logger.error(f"Error al conectar con n8n: {n8n_error}")
            # Fallback a brain-mri-app y marketing
            with open(file_path, "rb") as f:
                response = requests.post(BRAIN_MRI_URL, files={"file": f}, timeout=60)
            response.raise_for_status()
            brain_result = response.json()
            logger.info(f"Respuesta de brain-mri (fallback): {brain_result}")

            diagnosis = brain_result.get("result", "No disponible")
            confidence = brain_result.get("confidence", 0)
            img_tumor_url = brain_result.get("img_tumor", "")

            mri_report_response = requests.post(
                MARKETING_MRI_REPORT_URL,
                data={"diagnosis": diagnosis, "confidence": confidence},
                timeout=60,
            )
            mri_report_response.raise_for_status()
            mri_report_result = mri_report_response.json()
            logger.info(f"Respuesta de mri-report (fallback): {mri_report_result}")

            result = {
                "diagnosis": diagnosis,
                "confidence": confidence,
                "img_tumor": img_tumor_url,
                "mri_report": f"{STATIC_URL}/mri-report.png"
            }
            source = "fallback"

        # Procesar resultados (de n8n o fallback)
        diagnosis = result.get("diagnosis", "No disponible")
        confidence = float(result.get("confidence", 0)) * 100  # Convertir a porcentaje
        img_tumor_url = result.get("img_tumor", "")
        mri_report_url = result.get("mri_report", "")

        # Preparar mensaje
        message = (
            f"🧠 **Resultado del Análisis MRI ({source})**\n"
            f"**Diagnóstico**: {diagnosis}\n"
            f"**Confianza**: {confidence:.2f}%\n\n"
            "📈 **Gráfica de Confianza**:"
        )

        # Enviar mensaje con gráfica
        if mri_report_url:
            try:
                await update.message.reply_photo(
                    photo=mri_report_url, caption=message, parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Error enviando mri-report.png: {e}")
                await update.message.reply_text(message, parse_mode="Markdown")
        else:
            await update.message.reply_text(message, parse_mode="Markdown")

        # Enviar imagen con tumor si existe
        if img_tumor_url and diagnosis == "Tumor detectado":
            try:
                if img_tumor_url.startswith("data:image"):  # Manejar base64
                    img_tumor_data = img_tumor_url.split(",")[1]
                    img_tumor = Image.open(io.BytesIO(base64.b64decode(img_tumor_data)))
                    tumor_file_path = os.path.join(STATIC_DIR, "tumor.png")
                    img_tumor.save(tumor_file_path)
                    with open(tumor_file_path, "rb") as tumor_file:
                        await update.message.reply_photo(
                            photo=tumor_file,
                            caption="🩻 Imagen con zona del tumor marcada",
                        )
                else:  # Manejar URL
                    img_response = requests.get(img_tumor_url, timeout=10)
                    img_response.raise_for_status()
                    img_buffer = io.BytesIO(img_response.content)
                    await update.message.reply_photo(
                        photo=img_buffer,
                        caption="🩻 Imagen con zona del tumor marcada",
                    )
            except Exception as e:
                logger.error(f"Error procesando imagen del tumor: {e}")

        # Mostrar menú de tareas
        context.user_data["state"] = None
        context.user_data["image_path"] = file_path
        await update.message.reply_text(
            "Selecciona una tarea para ver más análisis:", reply_markup=build_task_menu()
        )

    except requests.exceptions.RequestException as e:
        logger.error(f"Error al procesar la imagen: {e}")
        await update.message.reply_text(
            "⚠️ Error al procesar la imagen. Intenta de nuevo más tarde.",
            reply_markup=build_main_menu(),
        )
    except Exception as e:
        logger.error(f"Error procesando imagen: {e}")
        await update.message.reply_text(
            "⚠️ Error interno. Por favor, intenta de nuevo.",
            reply_markup=build_main_menu(),
        )
    finally:
        context.user_data["state"] = None
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Error al eliminar {file_path}: {e}")
        if "image_path" in context.user_data:
            if os.path.exists(context.user_data["image_path"]):
                try:
                    os.remove(context.user_data["image_path"])
                except Exception as e:
                    logger.error(f"Error al eliminar {context.user_data['image_path']}: {e}")
            del context.user_data["image_path"]

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
    elif query.data == "select_task":
        await query.message.edit_text(
            "Selecciona una tarea:", reply_markup=build_task_menu()
        )
    elif query.data == "help":
        await query.message.edit_text(
            "📚 **Ayuda de MRI Analysis Bot**\n"
            "- Usa 'Subir Imagen MRI' para analizar una imagen.\n"
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

            # Formatear mensaje y tabla
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
            
            # Para Task 9, intentar con autoencoder.png y usar generate_plot como respaldo
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
                    image_paths = generate_plot(task_number, task_result)  # Respaldo
            
            # Enviar mensaje y imágenes
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
            
            # Si no se envió ninguna imagen, enviar solo el mensaje
            if not sent_message:
                logger.warning(f"No se enviaron imágenes para Task {task_number}")
                await query.message.reply_text(
                    message, reply_markup=build_task_menu(), parse_mode="Markdown"
                )
            
            # Enviar tabla
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

def main():
    """Inicia el bot"""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN no está configurado")

    application = Application.builder().token(token).build()

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