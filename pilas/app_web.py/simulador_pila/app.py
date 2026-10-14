
import base64
import binascii
import os
import uuid
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    session,
    flash,
    redirect,
    url_for,
)

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "clave-local-solo-para-desarrollo"
)

UPLOAD_FOLDER = Path(app.root_path) / "static" / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

DEFAULT_CAPACITY = 5
MAX_CAPACITY = 100
MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_TEXT_LENGTH = 100


@app.before_request
def initialize_structures():
    session.setdefault("queue", [])
    session.setdefault("stack", [])
    session.setdefault("queue_capacity", DEFAULT_CAPACITY)
    session.setdefault("stack_capacity", DEFAULT_CAPACITY)


def save_photo(photo_data):
    prefix = "data:image/jpeg;base64,"

    if not photo_data.startswith(prefix):
        raise ValueError("Formato de fotografía no válido.")

    try:
        image_bytes = base64.b64decode(
            photo_data[len(prefix):],
            validate=True
        )
    except (ValueError, binascii.Error) as error:
        raise ValueError(
            "No se pudo procesar la fotografía."
        ) from error

    if not image_bytes or len(image_bytes) > MAX_IMAGE_SIZE:
        raise ValueError(
            "La fotografía está vacía o supera los 5 MB."
        )

    if not image_bytes.startswith(b"\xff\xd8\xff"):
        raise ValueError(
            "El archivo no es una imagen JPEG válida."
        )

    filename = f"{uuid.uuid4().hex}.jpg"
    (UPLOAD_FOLDER / filename).write_bytes(image_bytes)

    return filename


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        mode = request.form.get("mode", "queue")
    else:
        mode = request.args.get("mode", "queue")

    if mode not in ("queue", "stack"):
        mode = "queue"

    items_key = "queue" if mode == "queue" else "stack"
    capacity_key = (
        "queue_capacity" if mode == "queue"
        else "stack_capacity"
    )

    if request.method == "POST":
        action = request.form.get("action", "")
        items = session[items_key]
        capacity = session[capacity_key]

        # Configurar capacidad
        if action == "set_capacity":
            try:
                new_capacity = int(
                    request.form.get("capacity", "")
                )

                if not 1 <= new_capacity <= MAX_CAPACITY:
                    raise ValueError

                if new_capacity < len(items):
                    flash(
                        "La capacidad no puede ser menor "
                        "que la cantidad actual de elementos.",
                        "warning"
                    )
                else:
                    session[capacity_key] = new_capacity
                    flash("Capacidad actualizada.", "success")

            except ValueError:
                flash(
                    f"Introduce un número entre 1 y {MAX_CAPACITY}.",
                    "danger"
                )

        # Agregar texto
        elif action == "add_text":
            item = request.form.get("item", "").strip()

            if not item:
                flash("Escribe un elemento.", "warning")
            elif len(item) > MAX_TEXT_LENGTH:
                flash(
                    "El texto no puede superar 100 caracteres.",
                    "warning"
                )
            elif len(items) >= capacity:
                flash(
                    "La estructura está llena.",
                    "warning"
                )
            else:
                items.append({
                    "type": "text",
                    "value": item
                })
                session[items_key] = items

                if mode == "queue":
                    flash("Elemento agregado al final de la cola.", "success")
                else:
                    flash("Elemento agregado a la cima de la pila.", "success")

        # Agregar fotografía
        elif action == "add_photo":
            photo_data = request.form.get("photo_data", "")

            if len(items) >= capacity:
                flash("La estructura está llena.", "warning")
            elif not photo_data:
                flash(
                    "Primero debes tomar una fotografía.",
                    "warning"
                )
            else:
                try:
                    filename = save_photo(photo_data)

                    items.append({
                        "type": "image",
                        "value": filename
                    })
                    session[items_key] = items

                    flash("Fotografía agregada correctamente.", "success")

                except ValueError as error:
                    flash(str(error), "danger")

        # Consultar el próximo elemento
        elif action == "peek":
            if items:
                next_item = items[0] if mode == "queue" else items[-1]

                if next_item["type"] == "image":
                    description = "una fotografía"
                else:
                    description = next_item["value"]

                label = (
                    "Primer elemento de la cola"
                    if mode == "queue"
                    else "Elemento en la cima de la pila"
                )

                flash(f"{label}: {description}", "info")
            else:
                flash("La estructura está vacía.", "warning")

        # Retirar elemento según el tipo de estructura
        elif action == "remove":
            if items:
                if mode == "queue":
                    removed = items.pop(0)
                else:
                    removed = items.pop()

                session[items_key] = items

                if removed["type"] == "image":
                    description = "fotografía"
                else:
                    description = removed["value"]

                flash(f"Elemento retirado: {description}", "success")
            else:
                flash("La estructura está vacía.", "warning")

        # Vaciar únicamente la estructura activa
        elif action == "clear":
            session[items_key] = []
            flash("La estructura se ha vaciado.", "success")

        else:
            flash("Operación no válida.", "danger")

        return redirect(url_for("index", mode=mode))

    return render_template(
        "index.html",
        mode=mode,
        items=session[items_key],
        capacity=session[capacity_key]
    )


@app.errorhandler(413)
def file_too_large(error):
    flash(
        "La solicitud es demasiado grande. "
        "Intenta tomar una fotografía más pequeña.",
        "danger"
    )
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
