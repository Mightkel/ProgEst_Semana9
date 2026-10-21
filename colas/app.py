
from collections import deque
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "atencion-clientes-local"

cola = deque()
atendidos = []
cliente_actual = None
siguiente_turno = 1


def agregar(nombre, tipo, descripcion):
    global siguiente_turno

    cliente = {
        "turno": siguiente_turno,
        "nombre": nombre,
        "tipo": tipo,
        "descripcion": descripcion,
        "estado": "Pendiente"
    }

    cola.append(cliente)
    siguiente_turno += 1
    return cliente


def mostrar_pendientes():
    return list(cola)


def llamar_siguiente():
    global cliente_actual

    if cliente_actual is not None:
        return None

    if not cola:
        return None

    cliente_actual = cola.popleft()
    cliente_actual["estado"] = "En atención"
    return cliente_actual


def finalizar_atencion():
    global cliente_actual

    if cliente_actual is None:
        return None

    cliente_actual["estado"] = "Finalizado"
    atendidos.append(cliente_actual)

    resultado = cliente_actual
    cliente_actual = None

    return resultado


def mostrar_atendidos():
    return list(reversed(atendidos))


@app.route("/", methods=["GET", "POST"])
def inicio():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        tipo = request.form.get("tipo", "").strip()
        descripcion = request.form.get("descripcion", "").strip()

        if not nombre or not tipo or not descripcion:
            flash("Completa todos los campos.", "warning")
        elif len(nombre) > 100 or len(descripcion) > 500:
            flash("El nombre o la descripción son demasiado largos.", "warning")
        else:
            cliente = agregar(nombre, tipo, descripcion)
            flash(
                f"Cliente registrado con el turno #{cliente['turno']}.",
                "success"
            )

        return redirect(url_for("inicio"))

    return render_template(
        "index.html",
        pendientes=mostrar_pendientes(),
        atendidos=mostrar_atendidos(),
        actual=cliente_actual
    )


@app.route("/llamar", methods=["POST"])
def llamar():
    cliente = llamar_siguiente()

    if cliente is None:
        if cliente_actual is not None:
            flash("Finaliza la atención actual antes de llamar a otro cliente.",
                  "warning")
        else:
            flash("No hay clientes pendientes.", "warning")
    else:
        flash(
            f"Atendiendo al turno #{cliente['turno']}: {cliente['nombre']}.",
            "success"
        )

    return redirect(url_for("inicio"))


@app.route("/finalizar", methods=["POST"])
def finalizar():
    cliente = finalizar_atencion()

    if cliente is None:
        flash("No hay una atención activa para finalizar.", "warning")
    else:
        flash(
            f"Atención del turno #{cliente['turno']} finalizada.",
            "success"
        )

    return redirect(url_for("inicio"))


@app.route("/reiniciar", methods=["POST"])
def reiniciar():
    global cliente_actual, siguiente_turno

    cola.clear()
    atendidos.clear()
    cliente_actual = None
    siguiente_turno = 1

    flash("El sistema se ha reiniciado.", "info")
    return redirect(url_for("inicio"))


if __name__ == "__main__":
    app.run(debug=True)
