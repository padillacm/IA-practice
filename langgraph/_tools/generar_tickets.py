"""Genera `data/tickets_soporte.csv`: tickets de soporte sintéticos y etiquetados.

Por qué sintéticos: los corpus públicos de tickets reales o están en inglés, o
carecen de etiquetas de categoría y prioridad, o no se pueden redistribuir. Aquí
lo que importa es tener **verdad de terreno** (`categoria`, `prioridad`) para poder
*medir* el agente de triaje del Proyecto 1 en vez de mirarlo y decir "parece que va bien".

El generador es determinista (semilla fija), así que el CSV del repositorio se puede
regenerar byte a byte:  python _tools/generar_tickets.py
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib
import random

SEMILLA = 20260830
N_TICKETS = 400

PLANES = [("free", 0.34), ("pro", 0.36), ("business", 0.22), ("enterprise", 0.08)]
CANALES = [("email", 0.42), ("chat", 0.33), ("formulario", 0.17), ("telefono", 0.08)]

# Cada categoría aporta: plantillas de asunto, plantillas de cuerpo y la
# distribución de prioridad base (que luego se corrige por plan y por señales).
CATEGORIAS: dict[str, dict] = {
    "facturacion": {
        # (asunto, cuerpo) emparejados: un ticket incoherente no enseña nada al agente.
        "pares": [
            ("Cobro duplicado en la factura de {mes}",
             "Buenas, revisando el extracto veo dos cargos de {importe} € el mismo día de {mes}. "
             "Solo tengo una suscripción {plan}. ¿Podéis devolver el duplicado?"),
            ("No me llega la factura de {mes}",
             "Hola, no he recibido la factura de {mes} y contabilidad me la está pidiendo para cerrar "
             "el trimestre. Mi cuenta es {correo}."),
            ("Me han cobrado {importe} € de más",
             "En la última renovación se me ha cobrado {importe} € por encima de lo que figura en el plan "
             "{plan}. Adjunto el justificante del cargo."),
            ("Necesito la factura con el CIF de mi empresa",
             "Necesito rehacer la factura de {mes} con los datos fiscales correctos: el CIF que aparece "
             "no es el nuestro y así no la puedo deducir."),
            ("Quiero cambiar la forma de pago",
             "Quiero pasar de pago con tarjeta a domiciliación bancaria antes de la próxima renovación. "
             "¿Qué necesitáis de mi parte?"),
        ],
        "base": [("baja", 0.35), ("media", 0.5), ("alta", 0.15), ("critica", 0.0)],
    },
    "acceso_cuenta": {
        "pares": [
            ("No puedo entrar en mi cuenta",
             "Desde ayer no consigo iniciar sesión con {correo}. Me dice credenciales incorrectas y el "
             "enlace de recuperación no llega ni a la bandeja de spam."),
            ("El doble factor no me envía el código",
             "El SMS del segundo factor no llega desde hace {horas} horas. Tengo una demo con un cliente "
             "y no puedo entrar en la plataforma."),
            ("Usuario bloqueado tras varios intentos",
             "Mi usuario se ha bloqueado tras varios intentos fallidos de inicio de sesión. "
             "¿Podéis desbloquear {correo}?"),
            ("Perdí acceso al correo de recuperación",
             "El correo de recuperación de mi cuenta es una dirección antigua a la que ya no tengo acceso. "
             "¿Cómo puedo recuperar la cuenta {correo}?"),
            ("Necesito revocar el acceso de un empleado",
             "Han salido dos personas del equipo y necesito revocar sus accesos hoy mismo por política "
             "interna de seguridad."),
        ],
        "base": [("baja", 0.1), ("media", 0.4), ("alta", 0.4), ("critica", 0.1)],
    },
    "bug_producto": {
        "pares": [
            ("Error 500 al guardar un informe",
             "Al pulsar Guardar en un informe me devuelve un error 500. Pasa siempre, en Chrome y en "
             "Firefox. El identificador de la petición es {peticion}."),
            ("La exportación a CSV sale vacía",
             "La exportación a CSV descarga un fichero de 0 bytes desde la actualización de {mes}. "
             "Antes funcionaba correctamente."),
            ("Los gráficos no cargan en el panel",
             "El panel principal se queda en blanco y la consola del navegador muestra un error de "
             "JavaScript. Afecta a {afectados} usuarios de mi equipo."),
            ("La app móvil se cierra al abrir un proyecto",
             "La aplicación móvil se cierra sola al abrir cualquier proyecto. La he reinstalado y "
             "sigue igual."),
            ("Se pierden los cambios al recargar",
             "Edito un informe, guardo, y al recargar la página los cambios han desaparecido. "
             "Me ha pasado {afectados} veces esta semana."),
        ],
        "base": [("baja", 0.08), ("media", 0.37), ("alta", 0.4), ("critica", 0.15)],
    },
    "integraciones": {
        "pares": [
            ("El webhook deja de disparar eventos",
             "Nuestro webhook a {dominio} dejó de recibir eventos hace {horas} horas. No hemos cambiado "
             "nada del lado nuestro."),
            ("Fallo al conectar con Salesforce",
             "Al conectar Salesforce el asistente se queda en el paso de autorización y acaba en un "
             "error genérico sin detalle."),
            ("La API devuelve 401 con una clave válida",
             "La API nos devuelve 401 con una clave que generamos ayer y que sigue apareciendo como "
             "activa en el panel."),
            ("Sincronización con Google Sheets parada",
             "La sincronización con Google Sheets lleva {horas} horas sin actualizar. La hoja destino "
             "sigue con los datos de antes."),
            ("Rate limit inesperado en la API",
             "Estamos recibiendo 429 con muy pocas peticiones por minuto, muy por debajo del límite "
             "que anuncia nuestro plan {plan}."),
        ],
        "base": [("baja", 0.1), ("media", 0.4), ("alta", 0.37), ("critica", 0.13)],
    },
    "rendimiento": {
        "pares": [
            ("La plataforma va extremadamente lenta",
             "Desde hace {horas} horas cualquier consulta tarda más de un minuto. Antes eran segundos. "
             "Somos {afectados} personas trabajando y está parado todo el equipo."),
            ("Las consultas tardan más de un minuto",
             "Las consultas que antes iban en segundos ahora superan el minuto de forma sistemática, "
             "sobre todo sobre rangos de fechas amplios."),
            ("Timeouts constantes en el panel",
             "El panel tarda muchísimo en cargar y a menudo acaba en timeout. Ocurre sobre todo a "
             "primera hora de la mañana."),
            ("Los informes grandes no terminan nunca",
             "Los informes grandes ya no terminan: se quedan cargando indefinidamente y hay que "
             "cancelarlos a mano."),
        ],
        "base": [("baja", 0.05), ("media", 0.3), ("alta", 0.45), ("critica", 0.2)],
    },
    "solicitud_funcionalidad": {
        "pares": [
            ("¿Podéis añadir exportación a PDF?",
             "No es urgente, pero nos ahorraría mucho tiempo poder exportar los informes directamente "
             "a PDF sin pasar por el navegador."),
            ("Sugerencia: alertas por Slack",
             "Sería genial recibir las alertas en Slack además de por correo. ¿Está en la hoja de ruta?"),
            ("Falta filtrar por etiquetas",
             "Echamos de menos poder filtrar el listado por etiquetas; ahora hay que buscar a mano "
             "entre cientos de elementos."),
            ("Petición: modo oscuro",
             "Mucha gente del equipo trabaja de noche y agradeceríamos un modo oscuro en la interfaz."),
            ("Nos vendría bien una API de borrado masivo",
             "Para cumplir con nuestra política de retención de datos necesitaríamos una llamada de "
             "borrado masivo por API."),
        ],
        "base": [("baja", 0.68), ("media", 0.3), ("alta", 0.02), ("critica", 0.0)],
    },
    "datos_privacidad": {
        "pares": [
            ("Solicitud de borrado de datos (RGPD)",
             "Ejerciendo el derecho de supresión del RGPD, solicito el borrado de todos los datos "
             "asociados a {correo}."),
            ("¿Dónde se almacenan nuestros datos?",
             "Nuestro departamento legal pregunta en qué región se almacenan los datos y si en algún "
             "momento salen del Espacio Económico Europeo."),
            ("Necesitamos firmar un DPA",
             "Necesitamos firmar un acuerdo de tratamiento de datos antes de renovar el contrato del "
             "plan {plan}. ¿A quién se lo pedimos?"),
            ("Exportación de todos mis datos personales",
             "Solicito una exportación completa de los datos personales asociados a {correo}, en "
             "ejercicio del derecho de portabilidad."),
            ("Posible acceso no autorizado a nuestra cuenta",
             "Hemos detectado accesos desde una IP que no reconocemos. Necesitamos el registro de "
             "auditoría de las últimas {horas} horas."),
        ],
        "base": [("baja", 0.15), ("media", 0.4), ("alta", 0.33), ("critica", 0.12)],
    },
    "otros": {
        "pares": [
            ("Consulta general sobre el plan",
             "Buenas, estamos valorando subir al plan {plan} y quería saber qué incluye exactamente "
             "el soporte."),
            ("¿Tenéis descuento para ONG?",
             "Somos una entidad sin ánimo de lucro, ¿tenéis algún tipo de descuento sobre el plan {plan}?"),
            ("Duda sobre la documentación",
             "En la documentación no queda claro cómo se cuentan los usuarios activos. ¿Me lo podéis aclarar?"),
            ("Quiero hablar con comercial",
             "Me gustaría que me llamase alguien de comercial para valorar un contrato anual."),
        ],
        "base": [("baja", 0.55), ("media", 0.4), ("alta", 0.05), ("critica", 0.0)],
    },
}

PESOS_CATEGORIA = [
    ("facturacion", 0.17), ("acceso_cuenta", 0.15), ("bug_producto", 0.22),
    ("integraciones", 0.14), ("rendimiento", 0.10), ("solicitud_funcionalidad", 0.11),
    ("datos_privacidad", 0.06), ("otros", 0.05),
]

# Frases que un cliente enfadado o bloqueado añade al final. Suben la prioridad:
# el triaje debe aprender a detectarlas, no solo a clasificar el tema.
COLETILLAS_URGENTES = [
    " Esto nos está bloqueando la operación y tenemos un cierre mañana.",
    " Es urgente, por favor. Llevamos todo el día parados.",
    " Si no se resuelve hoy tendremos que valorar cancelar el contrato.",
    " Tenemos una auditoría en curso y esto es crítico.",
]
COLETILLAS_NEUTRAS = ["", "", "", " Gracias de antemano.", " Quedo atento, un saludo.", " Sin prisa."]

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DOMINIOS = ["acme.example", "nimbus.example", "delta-labs.example", "orbita.example"]


def elegir(rng: random.Random, pares: list[tuple[str, float]]) -> str:
    return rng.choices([p[0] for p in pares], weights=[p[1] for p in pares], k=1)[0]


def contexto(rng: random.Random, plan: str) -> dict[str, str]:
    """Un único contexto por ticket: así el asunto y el cuerpo hablan del mismo mes,
    del mismo correo y del mismo plan. Rellenar cada plantilla por separado producía
    tickets sutilmente incoherentes, que es justo el ruido que no queremos aquí."""
    dominio = rng.choice(DOMINIOS)
    return {
        "mes": rng.choice(MESES),
        "importe": str(rng.choice([9, 19, 29, 49, 99, 149, 249])),
        "plan": plan,
        "correo": f"{rng.choice(['ana', 'luis', 'marta', 'javier', 'sofia', 'pablo', 'nuria'])}@{dominio}",
        "horas": str(rng.choice([2, 3, 5, 8, 12, 24, 48])),
        "peticion": f"req_{rng.randrange(10**8, 10**9)}",
        "afectados": str(rng.choice([3, 5, 8, 12, 25, 40])),
        "dominio": dominio,
    }


def escalar(prioridad: str, saltos: int) -> str:
    escala = ["baja", "media", "alta", "critica"]
    i = min(len(escala) - 1, max(0, escala.index(prioridad) + saltos))
    return escala[i]


def generar() -> list[dict]:
    rng = random.Random(SEMILLA)
    inicio = dt.datetime(2026, 1, 5, 8, 0)
    filas = []

    for i in range(1, N_TICKETS + 1):
        categoria = elegir(rng, PESOS_CATEGORIA)
        plan = elegir(rng, PLANES)
        canal = elegir(rng, CANALES)
        cfg = CATEGORIAS[categoria]

        plantilla_asunto, plantilla_cuerpo = rng.choice(cfg["pares"])
        ctx = contexto(rng, plan)
        asunto = plantilla_asunto.format(**ctx)
        cuerpo = plantilla_cuerpo.format(**ctx)

        urgente = rng.random() < 0.22
        cuerpo += rng.choice(COLETILLAS_URGENTES) if urgente else rng.choice(COLETILLAS_NEUTRAS)

        prioridad = elegir(rng, cfg["base"])
        if urgente:
            prioridad = escalar(prioridad, 1)
        if plan == "enterprise":
            prioridad = escalar(prioridad, 1)
        elif plan == "free":
            prioridad = escalar(prioridad, -1)

        if prioridad in ("alta", "critica") or urgente:
            sentimiento = rng.choices(["negativo", "neutro"], weights=[0.75, 0.25])[0]
        elif categoria == "solicitud_funcionalidad":
            sentimiento = rng.choices(["positivo", "neutro"], weights=[0.4, 0.6])[0]
        else:
            sentimiento = rng.choices(["negativo", "neutro", "positivo"], weights=[0.3, 0.55, 0.15])[0]

        minutos = {"critica": (2, 25), "alta": (5, 90), "media": (20, 480), "baja": (60, 2880)}[prioridad]
        filas.append({
            "id_ticket": f"TCK-{i:04d}",
            "fecha": (inicio + dt.timedelta(days=rng.randrange(0, 210),
                                            hours=rng.randrange(0, 24),
                                            minutes=rng.randrange(0, 60))).isoformat(timespec="minutes"),
            "canal": canal,
            "plan_cliente": plan,
            "antiguedad_meses": rng.randrange(1, 60),
            "asunto": asunto,
            "mensaje": cuerpo.strip(),
            "categoria": categoria,
            "prioridad": prioridad,
            "sentimiento": sentimiento,
            "minutos_primera_respuesta": rng.randrange(*minutos),
            "resuelto": rng.random() < (0.94 if prioridad in ("baja", "media") else 0.82),
        })
    return filas


def main() -> None:
    filas = generar()
    destino = pathlib.Path(__file__).resolve().parent.parent / "data" / "tickets_soporte.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)

    from collections import Counter
    print(f"{len(filas)} tickets -> {destino}")
    print("  categorías:", dict(Counter(r["categoria"] for r in filas)))
    print("  prioridad :", dict(Counter(r["prioridad"] for r in filas)))


if __name__ == "__main__":
    main()
