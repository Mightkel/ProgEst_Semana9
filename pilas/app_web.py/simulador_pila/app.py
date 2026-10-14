
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
def initialize_queue():
    session.setdefault("queue", [])
    session.setdefault("capacity", DEFAULT_CAPACITY)


def save_photo(photo_data):
    prefix = "data:image/jpeg;base64,"

    if not photo_data.startswith(prefix):
        raise ValueError("Formato de fotografía no válido.")

    encoded_image = photo_data[len(prefix):]

    try:
        image_bytes = base64.b64decode(
            encoded_image,
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
    filepath = UPLOAD_FOLDER / filename
    filepath.write_bytes(image_bytes)

    return filename


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        action = request.form.get("action", "")
        queue = session["queue"]
        capacity = session["capacity"]

        # Cambiar la capacidad de la cola
        if action == "set_capacity":
            try:
                new_capacity = int(
                    request.form.get("capacity", "")
                )

                if not 1 <= new_capacity <= MAX_CAPACITY:
                    raise ValueError

                if new_capacity < len(queue):
                    flash(
                        "La capacidad no puede ser menor "
                        "que la cantidad actual de elementos.",
                        "warning"
                    )
                else:
                    session["capacity"] = new_capacity
                    flash(
                        "Capacidad actualizada.",
                        "success"
                    )

            except ValueError:
                flash(
                    f"Introduce un número entre 1 y {MAX_CAPACITY}.",
                    "danger"
                )

        # Agregar texto al final de la cola
        elif action == "enqueue":
            item = request.form.get("item", "").strip()

            if not item:
                flash(
                    "Escribe un elemento antes de agregarlo.",
                    "warning"
                )

            elif len(item) > MAX_TEXT_LENGTH:
                flash(
                    "El texto no puede superar 100 caracteres.",
                    "warning"
                )

            elif len(queue) >= capacity:
                flash("La cola está llena.", "warning")

            else:
                queue.append({
                    "type": "text",
                    "value": item
                })

                session["queue"] = queue
                flash(
                    "Elemento agregado al final de la cola.",
                    "success"
                )

        # Agregar una fotografía al final de la cola
        elif action == "enqueue_photo":
            photo_data = request.form.get("photo_data", "")

            if len(queue) >= capacity:
                flash("La cola está llena.", "warning")

            elif not photo_data:
                flash(
                    "Primero debes tomar una fotografía.",
                    "warning"
                )

            else:
                try:
                    filename = save_photo(photo_data)

                    queue.append({
                        "type": "image",
                        "value": filename
                    })

                    session["queue"] = queue
                    flash(
                        "Fotografía agregada a la cola.",
                        "success"
                    )

                except ValueError as error:
                    flash(str(error), "danger")

        # Consultar el primer elemento
        elif action == "peek":
            if queue:
                first_item = queue[0]

                if first_item["type"] == "image":
                    flash(
                        "El primer elemento de la cola es una fotografía.",
                        "info"
                    )
                else:
                    flash(
                        f"Primer elemento: {first_item['value']}",
                        "info"
                    )
            else:
                flash("La cola está vacía.", "warning")

        # Retirar el primer elemento (FIFO)
        elif action == "dequeue":
            if queue:
                removed = queue.pop(0)
                session["queue"] = queue

                if removed["type"] == "image":
                    flash(
                        "Fotografía retirada de la cola.",
                        "success"
                    )
                else:
                    flash(
                        f"Elemento retirado: {removed['value']}",
                        "success"
                    )
            else:
                flash(
                    "No puedes retirar elementos de una cola vacía.",
                    "warning"
                )

        # Vaciar la cola
        elif action == "clear":
            session["queue"] = []
            flash("La cola se ha vaciado.", "success")

        else:
            flash("Operación no válida.", "danger")

        return redirect(url_for("index"))

    return render_template(
        "index.html",
        queue=session["queue"],
        capacity=session["capacity"]
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
