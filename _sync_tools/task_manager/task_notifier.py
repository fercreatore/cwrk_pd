# -*- coding: utf-8 -*-
"""
Task Notifier — Lee AGENDA.md y genera/envia notificaciones por persona
Para el Task Manager de H4/Calzalindo

Uso:
    python3 task_notifier.py plan          # Muestra plan del dia (stdout)
    python3 task_notifier.py plan --enviar # Muestra + envia por WhatsApp
    python3 task_notifier.py checkpoint    # Genera mensaje checkpoint miercoles
    python3 task_notifier.py cierre        # Genera mensaje cierre viernes
    python3 task_notifier.py tareas Mati   # Tareas de una persona
"""
import re
import os
import sys
from datetime import datetime

AGENDA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "AGENDA.md")

# Contactos del equipo (telefono sin +)
CONTACTOS = {
    "Fernando":  "5493462672330",
    "Mati":      "5493462508491",
    "Mariana":   "5493462317470",
    "Gonza":     "5493462317553",
    "Emanuel":   "5493462317342",
    "Tamara":    "5493462677067",
    "Guille":    "5493462610216",
    "Lucia":     "5493462637251",
    "Maitena":   None,   # completar
}


def leer_agenda():
    """Lee AGENDA.md y retorna contenido."""
    path = os.path.abspath(AGENDA_PATH)
    if not os.path.exists(path):
        print(f"ERROR: No se encuentra {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def extraer_tareas_persona(contenido, nombre):
    """Extrae tareas de una persona desde la seccion '### NOMBRE'."""
    # Buscar seccion de la persona
    pattern = rf"### {nombre.upper()}.*?\n(.*?)(?=\n### |\n## |\Z)"
    match = re.search(pattern, contenido, re.DOTALL | re.IGNORECASE)
    if not match:
        # Intentar con nombre parcial
        for line_pattern in [rf"### .*{nombre}.*\n(.*?)(?=\n### |\n## |\Z)"]:
            match = re.search(line_pattern, contenido, re.DOTALL | re.IGNORECASE)
            if match:
                break
    if not match:
        return []

    seccion = match.group(1)
    tareas = []

    # Parsear tabla de tareas
    for line in seccion.split("\n"):
        line = line.strip()
        if not line.startswith("|") or line.startswith("| Pri") or line.startswith("|--"):
            continue
        cols = [c.strip() for c in line.split("|")[1:-1]]
        if len(cols) >= 5:
            pri, tarea, deadline, entregable, estado = cols[0], cols[1], cols[2], cols[3], cols[4]
            if "~~" in tarea or "[x]" in estado:
                continue  # saltear completadas
            tareas.append({
                "prioridad": pri,
                "tarea": tarea,
                "deadline": deadline,
                "entregable": entregable,
                "estado": estado,
            })
    return tareas


def generar_plan_dia(contenido):
    """Genera plan del dia para cada persona con tareas pendientes."""
    hoy = datetime.now()
    dia_semana = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"][hoy.weekday()]
    fecha = hoy.strftime("%d/%m/%Y")

    planes = {}
    for nombre in CONTACTOS:
        tareas = extraer_tareas_persona(contenido, nombre)
        if not tareas:
            continue

        # Filtrar P0 y P1
        urgentes = [t for t in tareas if t["prioridad"] in ("P0", "P1")]
        if not urgentes:
            continue

        lineas = [f"Buenos dias {nombre}! {dia_semana} {fecha}\n"]
        lineas.append("Tus tareas de esta semana:\n")
        for i, t in enumerate(urgentes, 1):
            emoji = "🔴" if t["prioridad"] == "P0" else "🟡"
            lineas.append(f"{emoji} {t['tarea']}")
            lineas.append(f"   Deadline: {t['deadline']}")
            lineas.append(f"   Entregable: {t['entregable']}\n")

        lineas.append("Responde OK para confirmar que lo viste.")
        planes[nombre] = "\n".join(lineas)

    return planes


def generar_checkpoint(contenido):
    """Genera mensaje de checkpoint (miercoles)."""
    lineas = ["Equipo, update mitad de semana:\n"]

    for nombre in CONTACTOS:
        tareas = extraer_tareas_persona(contenido, nombre)
        pendientes = [t for t in tareas if t["prioridad"] in ("P0", "P1") and "[x]" not in t["estado"]]
        if pendientes:
            tareas_str = ", ".join([t["tarea"] for t in pendientes[:2]])
            lineas.append(f"@{nombre}: como vas con {tareas_str}?")

    lineas.append("\nContesten: OK / 70% / BLOQ")
    return "\n".join(lineas)


def generar_cierre(contenido):
    """Genera mensaje de cierre semanal (viernes)."""
    hoy = datetime.now()
    lineas = [f"Cierre semana {hoy.strftime('%d/%m/%Y')}:\n"]

    completadas = []
    pendientes = []

    for nombre in CONTACTOS:
        tareas = extraer_tareas_persona(contenido, nombre)
        for t in tareas:
            if "[x]" in t["estado"] or "~~" in t["tarea"]:
                completadas.append(f"  {t['tarea']} ({nombre})")
            elif t["prioridad"] in ("P0", "P1"):
                pendientes.append(f"  {t['tarea']} ({nombre})")

    if completadas:
        lineas.append("COMPLETADO:")
        lineas.extend(completadas)
    else:
        lineas.append("COMPLETADO: (nada marcado esta semana)")

    if pendientes:
        lineas.append("\nPENDIENTE prox semana:")
        lineas.extend(pendientes)

    lineas.append("\nBuen finde!")
    return "\n".join(lineas)


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 task_notifier.py [plan|checkpoint|cierre|tareas <nombre>] [--enviar]")
        sys.exit(1)

    comando = sys.argv[1].lower()
    enviar = "--enviar" in sys.argv
    contenido = leer_agenda()

    if comando == "plan":
        planes = generar_plan_dia(contenido)
        for nombre, mensaje in planes.items():
            print(f"\n{'='*50}")
            print(f"PARA: {nombre}")
            print(f"{'='*50}")
            print(mensaje)

        if enviar:
            from meta_whatsapp import enviar_texto
            enviados = 0
            for nombre, mensaje in planes.items():
                tel = CONTACTOS.get(nombre)
                if tel:
                    r = enviar_texto(tel, mensaje)
                    estado = "OK" if r.get("ok") else f"ERROR: {r.get('error', 'desconocido')}"
                    print(f"\n>> Enviado a {nombre} ({tel}): {estado}")
                    enviados += 1
                else:
                    print(f"\n>> {nombre}: sin telefono configurado, saltando")
            print(f"\nTotal enviados: {enviados}/{len(planes)}")

    elif comando == "checkpoint":
        msg = generar_checkpoint(contenido)
        print(msg)
        if enviar:
            from meta_whatsapp import enviar_texto
            # Enviar a Fernando para que copie/pegue o reenvie
            r = enviar_texto(CONTACTOS["Fernando"], msg)
            print(f"\nEnviado a Fernando: {'OK' if r.get('ok') else r.get('error')}")

    elif comando == "cierre":
        msg = generar_cierre(contenido)
        print(msg)
        if enviar:
            from meta_whatsapp import enviar_texto
            r = enviar_texto(CONTACTOS["Fernando"], msg)
            print(f"\nEnviado a Fernando: {'OK' if r.get('ok') else r.get('error')}")

    elif comando == "tareas":
        if len(sys.argv) < 3:
            print("Uso: python3 task_notifier.py tareas <nombre>")
            sys.exit(1)
        nombre = sys.argv[2]
        tareas = extraer_tareas_persona(contenido, nombre)
        if not tareas:
            print(f"No se encontraron tareas para '{nombre}'")
        else:
            print(f"\nTareas de {nombre}:")
            for t in tareas:
                estado = "DONE" if "[x]" in t["estado"] else "PEND"
                print(f"  [{t['prioridad']}] {t['tarea']} — {t['deadline']} ({estado})")

    else:
        print(f"Comando desconocido: {comando}")
        print("Usar: plan | checkpoint | cierre | tareas <nombre>")


if __name__ == "__main__":
    main()
