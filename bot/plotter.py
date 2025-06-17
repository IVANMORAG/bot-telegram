import os
import math
import io
import logging
import plotly.graph_objects as go
from bot.config import STATIC_DIR, logger

def generate_plot(task_number, task_result):
    """Genera una gráfica Plotly según la tarea, alineada con app.js"""
    figs = []

    try:
        if task_number == "1":
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