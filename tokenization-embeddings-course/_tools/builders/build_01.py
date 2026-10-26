"""Genera el módulo 01_unicode_bytes: README + lección + proyecto.   Ejecutar desde la raíz del repo:
    python tokenization-embeddings-course/_tools/builders/build_01.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "_tools"))
sys.path.insert(0, str(ROOT / "_tools" / "builders"))
from a1_common import SRC_GPT2, SRC_PLOT_STYLE, caja, details, mapa_madurez, obs, pista, preguntas  # noqa: E402
from nbbuild import Notebook  # noqa: E402
from poliglota_utils import SRC_BM25, SRC_METRICS, src_corpus_cells  # noqa: E402

MOD = ROOT / "01_unicode_bytes"
MOD.mkdir(exist_ok=True)
(MOD / "assets").mkdir(exist_ok=True)
(MOD / "assets" / ".gitkeep").touch()
REL = "tokenization-embeddings-course/01_unicode_bytes"

# ════════════════════════════════════════════════════════════════════════════
#  LECCIÓN
# ════════════════════════════════════════════════════════════════════════════
LPATH = f"{REL}/01_unicode_bytes.ipynb"
nb = Notebook("Módulo 01 · Texto como bytes: Unicode, UTF-8, normalización", colab_path=LPATH)

nb.md(nb.badge() + r"""

# Módulo 01 · Texto como bytes: Unicode, UTF-8, normalización
**Tokenización y Embeddings: de BPE a los modelos modernos**

| | |
|---|---|
| **Nivel** | 🟢 Básico |
| **Duración** | ≈ 4 h (lección ≈ 2.5 h + proyecto ≈ 1.5 h) |
| **GPU / coste** | Ninguna: CPU (0 unidades de Colab Pro) |
| **Prerrequisitos** | Módulo 00 (corpus Políglota, métricas, BM25). Python sólido |

> **Estado del arte de referencia: octubre de 2026.** Las cifras sujetas a cambio llevan fecha; las técnicas se etiquetan 🟢 / 🟡 / 🔴.
""")

nb.md(r"""
## Objetivos de aprendizaje
Al terminar este módulo podrás:

1. **Distinguir** y **contar** grafemas, code points y bytes de un texto, y explicar por qué `len()` significa cosas distintas en Python, JavaScript y Go/Rust.
2. **Implementar** un codificador y decodificador de **UTF-8** a mano (con validación estricta) y **verificarlo** contra el de Python en todo el espacio Unicode y con *fuzzing*.
3. **Explicar** UTF-16/UTF-32, pares sustitutos y el almacenamiento de `str` en CPython.
4. **Aplicar** NFC/NFD/NFKC/NFKD, **implementar** NFD a mano y **medir** cómo la forma de normalización cambia bytes, tokens y resultados de búsqueda.
5. **Detectar** homoglifos, caracteres invisibles y controles bidireccionales, y **explicar** el riesgo de seguridad.
6. **Cuantificar** los bytes por carácter en 12 idiomas y **relacionarlo** con el costo posterior de tokenizar (analogías con compresión y con tipología lingüística).
7. **Diagnosticar** y **reparar** *mojibake*, y elegir el manejador de errores de codificación correcto.
""")

nb.md(caja("🧭 Ruta núcleo vs ampliación", r"""
La lección tiene ≈ 74 celdas. **Ruta núcleo (≈ 2 h):** secciones 1, 2, 3 (UTF-8), 6 (normalización: tabla, impacto en tokens y en búsqueda), 8 (bytes por idioma) y 10 (mojibake). **Ampliación (≈ 0.5 h extra):** 4 (UTF-16 y `str` de CPython), 5 (grafemas), 7 (homoglifos y seguridad), 9 (compresión) y 11 (escrituras del corpus), además de la verificación exhaustiva de NFD. El proyecto asume la ruta núcleo más la sección 7.
"""))

nb.md(r"""
## 🔁 Conexión con módulos anteriores
Antes de empezar, responde de memoria (despliega para comprobar):

""" + preguntas([
    ("", "¿Qué diferencia hay entre el «token» de `tokenize_simple` (módulo 00) y el token de un LLM?",
     "`tokenize_simple` produce *términos léxicos* (palabras minúsculas) para un índice invertido; un token de LLM es una unidad de un vocabulario fijo (a menudo sub-palabra o secuencia de bytes) con un id entero. El primero es parte del *retrieval léxico*; el segundo, del *modelo*."),
    ("", "En la frase de GPT-2 del módulo 00, ¿por qué el español costaba más tokens que el inglés? Da dos hipótesis.",
     "(1) El vocabulario se aprendió con mayoría de inglés, así que hay menos fusiones para español. (2) «ñ», «ú», «é» ocupan 2 bytes y, sin un token para ellas, se parten en bytes. Este módulo cuantifica la hipótesis 2."),
    ("", "¿Qué hace `evaluate()` con las consultas sin documentos relevantes, y por qué?",
     "Las excluye del promedio (convención `trec_eval`): su nDCG sería 0/0. Devolver 0 las hundiría artificialmente."),
    ("", "¿Qué contrato de datos devuelve `carga_corpus()`?",
     "Un dict con `docs` (`id`, `lang`, `text`), `queries` (`qid`, `lang`, `text`), `qrels` (`qid → {doc_id: 1}`) y `source` (`real`/`synthetic`)."),
]))

nb.md(r"""
## 1. Intuición primero: el texto tiene tres capas

Cuando escribes «👨‍👩‍👧‍👦» ves **un** símbolo. Python dirá `len(...) == 7`. El disco guarda **25** bytes. Las tres cifras son correctas porque hablan de capas distintas:

| Capa | ¿Qué es? | Quién la define | Ejemplo «é» | Ejemplo 👨‍👩‍👧‍👦 |
|---|---|---|---|---|
| **Grafema** (*extended grapheme cluster*) | lo que el lector percibe como «un carácter» | UAX #29 | 1 | 1 |
| **Code point** | un número del catálogo Unicode (U+0000…U+10FFFF) | el estándar Unicode | 1 (U+00E9) o 2 (`e` + U+0301) | 7 |
| **Byte** | un octeto en memoria/disco, según una *codificación* | UTF-8 (RFC 3629) | 2 (`C3 A9`) | 25 |

Un tokenizer de LLM actúa sobre **bytes** (byte-level BPE, módulo 02) o sobre **code points** (SentencePiece, módulo 03); ninguno ve grafemas. Si el texto llega con una representación inesperada (é descompuesta, un carácter invisible, un homoglifo), **el modelo ve otra cosa**.
""")

nb.gemini(
    "imagen", "M01-IMG-01", "Las tres capas del texto: grafema, code points, bytes",
    "Un único emoji de familia descompuesto en sus tres capas: 1 grafema, 7 code points (con 3 ZWJ) y 25 bytes UTF-8. Fija la diferencia entre lo que ves, lo que dice Unicode y lo que guarda el disco.",
    """Diagrama técnico limpio, fondo blanco, 16:9. Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Tipografía sans-serif legible, sin ilustraciones decorativas.
Composición vertical en tres franjas horizontales apiladas, unidas por flechas verticales grises que bajan de una franja a la siguiente, con la etiqueta «se descompone en» sobre cada flecha.
Franja 1 (borde azul), título «Grafema (lo que ves): 1». Contenido: el emoji de familia «👨‍👩‍👧‍👦» en tamaño grande, centrado.
Franja 2 (borde naranja), título «Code points (Unicode): 7». Contenido: siete cajas en fila con estos textos EXACTOS, de izquierda a derecha: «U+1F468 👨», «U+200D ZWJ», «U+1F469 👩», «U+200D ZWJ», «U+1F467 👧», «U+200D ZWJ», «U+1F466 👦». Las tres cajas ZWJ en gris con la nota «unión de ancho cero».
Franja 3 (borde verde), título «Bytes UTF-8: 25». Contenido: siete grupos de bytes en hexadecimal bajo cada code point, EXACTOS y en este orden: «F0 9F 91 A8», «E2 80 8D», «F0 9F 91 A9», «E2 80 8D», «F0 9F 91 A7», «E2 80 8D», «F0 9F 91 A6». Bajo cada grupo, el número de bytes: «4», «3», «4», «3», «4», «3», «4».
Título superior: «Un símbolo, tres capas». Nota inferior en gris: «len() de Python cuenta la capa 2; el disco guarda la capa 3».
Evita: cambiar los números o los códigos, texto ilegible, iconos decorativos, flechas ambiguas, más de tres franjas.""",
    "Emoji de familia descompuesto: 1 grafema, 7 code points y 25 bytes UTF-8",
    """Grafema (1):        👨‍👩‍👧‍👦
                      │ se descompone en
Code points (7):    U+1F468  U+200D  U+1F469  U+200D  U+1F467  U+200D  U+1F466
                      👨      ZWJ      👩      ZWJ      👧      ZWJ      👦
                      │ se codifica en UTF-8
Bytes (25):        F0 9F 91 A8|E2 80 8D|F0 9F 91 A9|E2 80 8D|F0 9F 91 A7|E2 80 8D|F0 9F 91 A6
                       4          3          4          3          4          3          4""",
)
nb.md(obs(r"""Cuenta de izquierda a derecha: 4+3+4+3+4+3+4 = **25** bytes. Los tres `ZWJ` (U+200D) **no se ven** pero ocupan 3 bytes cada uno y son code points de pleno derecho: un tokenizer byte-level tiene que pagar por ellos. En este emoji, 9 de los 25 bytes (3 ZWJ × 3 bytes) son «pegamento» invisible y los otros 16 son los cuatro emojis (4 × 4 bytes)."""))

nb.md(r"""
## 2. Code points: Unicode como catálogo

Unicode asigna a cada carácter abstracto un **code point**: un entero entre $0$ y $10FFFF_{16}$ ($1\,114\,112$ valores, repartidos en 17 *planos* de 65 536). Se escribe `U+0041` (letra A). Cada code point tiene **nombre**, **categoría general** (L=letra, M=marca, N=número, P=puntuación, S=símbolo, Z=separador, C=otros) y propiedades (escritura, ancho, comportamiento bidireccional…). Unicode **no** dice cómo se guarda en bytes: eso lo hacen las *codificaciones* (UTF-8, UTF-16, UTF-32).

Los code points `U+D800…U+DFFF` (2 048) son *surrogates*, reservados para UTF-16 y **no** son caracteres válidos: los **valores escalares** Unicode son los otros $1\,112\,064$.
""")

nb.code(r'''
!pip install -q numpy pandas matplotlib regex tiktoken rank_bm25 ftfy
''')
nb.code(SRC_PLOT_STYLE + r'''

import random, sys, time, unicodedata, collections, math, re
import numpy as np, pandas as pd, regex

SEED = 42
random.seed(SEED); np.random.seed(SEED)
FAST_DEV_RUN = True
print(f"python {sys.version.split()[0]} | Unicode (unicodedata) {unicodedata.unidata_version} | regex {regex.__version__}")
''')

nb.code(r'''
def inspecciona(s: str) -> pd.DataFrame:
    filas = []
    for ch in s:
        filas.append({"carácter": ch, "code point": f"U+{ord(ch):04X}", "nombre": unicodedata.name(ch, "(sin nombre)"),
                      "categoría": unicodedata.category(ch), "bytes UTF-8": ch.encode("utf-8").hex(" ").upper()})
    return pd.DataFrame(filas)

display(inspecciona("Añ€😀한"))
asignados = sum(unicodedata.category(chr(c)) not in ("Cn", "Co", "Cs") for c in range(0x110000))
print(f"Code points con carácter asignado (sin privados ni surrogates) en Unicode {unicodedata.unidata_version}: {asignados:,}")
''')

nb.md(r"""
## 3. UTF-8 desde cero

### Diseño
UTF-8 (diseñado por Pike y Thompson en 1992, publicado en Pike & Thompson 1993; hoy RFC 3629) codifica cada code point en **1 a 4 bytes**. Es un **código de prefijo de longitud variable** (como los de Huffman, pero con una tabla fija y pensada para ASCII): el **primer byte** dice cuántos bytes tiene la secuencia, los demás son *bytes de continuación* `10xxxxxx`.

| Rango de code points | Bytes | Patrón binario | Bits útiles |
|---|---|---|---|
| `U+0000…U+007F` | 1 | `0xxxxxxx` | 7 |
| `U+0080…U+07FF` | 2 | `110xxxxx 10xxxxxx` | 11 |
| `U+0800…U+FFFF` | 3 | `1110xxxx 10xxxxxx 10xxxxxx` | 16 |
| `U+10000…U+10FFFF` | 4 | `11110xxx 10xxxxxx 10xxxxxx 10xxxxxx` | 21 |

**Ejemplo a mano:** `€` = `U+20AC` = `0010 0000 1010 1100` (16 bits). Rango de 3 bytes: parte los 16 bits en 4 + 6 + 6 → `0010 | 000010 | 101100` → `11100010 | 10000010 | 10101100` = **`E2 82 AC`**.

**Propiedades que lo hicieron ganar:**
* **Compatible con ASCII**: un archivo ASCII *ya es* UTF-8 válido.
* **Autosincronizante**: un byte `10xxxxxx` nunca puede iniciar un carácter, así que si pierdes bytes, resincronizas en el siguiente byte que no sea de continuación.
* **Prefix-free**: ninguna secuencia válida es prefijo de otra → se decodifica sin ambigüedad.
* **Ordenación**: comparar bytes equivale a comparar code points.
* **Sin *overlongs***: cada code point tiene **una sola** codificación válida (la más corta); `C0 80` para U+0000 está *prohibido*: aceptarlo fue una fuente histórica de fallos de seguridad al saltarse filtros.
""")

nb.code(r'''
def utf8_encode_cp(cp: int) -> bytes:
    """Codifica UN valor escalar Unicode a bytes UTF-8 (a mano, con máscaras de bits)."""
    if not (0 <= cp <= 0x10FFFF) or 0xD800 <= cp <= 0xDFFF:
        raise ValueError(f"U+{cp:X} no es un valor escalar Unicode")
    if cp < 0x80:
        return bytes([cp])
    if cp < 0x800:
        return bytes([0xC0 | cp >> 6, 0x80 | cp & 0x3F])
    if cp < 0x10000:
        return bytes([0xE0 | cp >> 12, 0x80 | (cp >> 6) & 0x3F, 0x80 | cp & 0x3F])
    return bytes([0xF0 | cp >> 18, 0x80 | (cp >> 12) & 0x3F, 0x80 | (cp >> 6) & 0x3F, 0x80 | cp & 0x3F])

def utf8_encode(s: str) -> bytes:
    return b"".join(utf8_encode_cp(ord(c)) for c in s)

def utf8_decode(b: bytes) -> str:
    """Decodificador ESTRICTO: rechaza bytes iniciales inválidos, continuaciones erróneas, truncados, overlongs y surrogates."""
    out, i, n = [], 0, len(b)
    while i < n:
        b0 = b[i]
        if b0 < 0x80:                 need, cp, minimo = 0, b0, 0
        elif 0xC2 <= b0 <= 0xDF:      need, cp, minimo = 1, b0 & 0x1F, 0x80      # C0 y C1 solo darían overlongs
        elif 0xE0 <= b0 <= 0xEF:      need, cp, minimo = 2, b0 & 0x0F, 0x800
        elif 0xF0 <= b0 <= 0xF4:      need, cp, minimo = 3, b0 & 0x07, 0x10000   # F5..FF superan U+10FFFF
        else:
            raise ValueError(f"byte inicial inválido 0x{b0:02X} en la posición {i}")
        for k in range(1, need + 1):
            if i + k >= n or (b[i + k] & 0xC0) != 0x80:
                raise ValueError(f"continuación inválida o secuencia truncada en {i + k}")
            cp = cp << 6 | (b[i + k] & 0x3F)
        if cp < minimo:
            raise ValueError(f"codificación demasiado larga (overlong) en {i}")
        if 0xD800 <= cp <= 0xDFFF or cp > 0x10FFFF:
            raise ValueError(f"valor escalar inválido U+{cp:X} en {i}")
        out.append(chr(cp)); i += need + 1
    return "".join(out)

print("€ →", utf8_encode("€").hex(" ").upper(), "| 😀 →", utf8_encode("😀").hex(" ").upper(), "| ñ →", utf8_encode("ñ").hex(" ").upper())
assert utf8_decode(utf8_encode("Añ€😀한")) == "Añ€😀한"
''')

nb.md(r"""
### Verificación contra Python
Una implementación «parece correcta» con 5 ejemplos; la **verificamos** de dos formas: (1) **exhaustiva** sobre los 1 112 064 valores escalares (codificar y decodificar), y (2) **fuzzing**: 50 000 secuencias de bytes aleatorias (con bytes elegidos para provocar overlongs, surrogates, truncados y continuaciones sueltas) donde mi decodificador debe aceptar **exactamente** lo mismo que el de Python y producir el mismo texto.
""")

nb.code(r'''
t0 = time.time()
todos = [chr(c) for c in range(0x110000) if not 0xD800 <= c <= 0xDFFF]
mal = sum(utf8_encode_cp(ord(c)) != c.encode("utf-8") for c in todos)
texto = "".join(todos)
assert utf8_decode(texto.encode("utf-8")) == texto
print(f"exhaustivo: {len(todos):,} valores escalares, discrepancias de codificación = {mal}  ({time.time() - t0:.1f} s)")

rng = random.Random(SEED); discrep = 0; casos = collections.Counter()
alfabeto = [0x41, 0xC0, 0xC1, 0xC2, 0xC3, 0xE0, 0xE2, 0xED, 0xF0, 0xF4, 0xF5, 0x80, 0xA9, 0xBF, 0x9F, 0x8F]
for _ in range(50_000):
    b = bytes(rng.choice(alfabeto) for _ in range(rng.randint(1, 5)))
    try: mio = utf8_decode(b)
    except ValueError: mio = None
    try: ref = b.decode("utf-8")
    except UnicodeDecodeError: ref = None
    casos["válido" if ref is not None else "inválido"] += 1
    discrep += mio != ref
print(f"fuzzing: {sum(casos.values()):,} secuencias ({dict(casos)}), discrepancias = {discrep}")
assert mal == 0 and discrep == 0
''')

nb.code(r'''
# Rangos de UTF-8: cuántos code points caben en 1, 2, 3 y 4 bytes (y cuántos son válidos)
rangos = [("1 byte\n(U+0000–U+007F)", 0x80, 7), ("2 bytes\n(U+0080–U+07FF)", 0x800 - 0x80, 11),
          ("3 bytes\n(U+0800–U+FFFF)", 0x10000 - 0x800 - 2048, 16), ("4 bytes\n(U+10000–U+10FFFF)", 0x110000 - 0x10000, 21)]
fig, ax = plt.subplots(figsize=(8, 3.8))
b = ax.bar([r[0] for r in rangos], [r[1] for r in rangos], color=[VERDE, AZUL, NARANJA, GRIS])
ax.set_yscale("log"); ax.set_ylabel("valores escalares (escala log)"); ax.set_title("Capacidad de cada longitud de UTF-8")
for rect, (_, n, bits) in zip(b, rangos):
    ax.text(rect.get_x() + rect.get_width() / 2, n * 1.2, f"{n:,}\n{bits} bits útiles", ha="center", fontsize=8)
ax.set_ylim(50, 4e6); plt.tight_layout(); plt.show()
''')

nb.md(obs(r"""Con la escala logarítmica ves lo asimétrico del diseño: **128** valores en 1 byte (ASCII), pero más de **un millón** en 4 bytes. Un texto en inglés casi no usa los rangos largos; un texto en chino vive en los 3 bytes. Esa asimetría es, literalmente, el «impuesto de bytes» de muchos idiomas."""))

nb.gemini(
    "imagen", "M01-IMG-02", "Estructura de bits de UTF-8 con un ejemplo resuelto",
    "La tabla de patrones de bits de UTF-8 y la codificación paso a paso del símbolo € (U+20AC → E2 82 AC), para consultarla mientras implementas el codificador.",
    """Diagrama técnico limpio, fondo blanco, 16:9. Paleta: azul #1F6FEB para bits de payload, naranja #F28E2B para bits de encabezado (prefijos), verde #2CA02C para el resultado, gris #6B7280 para anotaciones. Tipografía monoespaciada para los bits y sans-serif para títulos, sin ilustraciones decorativas.
Mitad superior: una tabla de 4 filas, cada una con una celda por byte, con los prefijos en naranja y los bits «x» en azul. Textos EXACTOS por fila:
Fila 1: «1 byte · U+0000–U+007F» y «0xxxxxxx» (7 bits útiles).
Fila 2: «2 bytes · U+0080–U+07FF» y «110xxxxx | 10xxxxxx» (11 bits útiles).
Fila 3: «3 bytes · U+0800–U+FFFF» y «1110xxxx | 10xxxxxx | 10xxxxxx» (16 bits útiles).
Fila 4: «4 bytes · U+10000–U+10FFFF» y «11110xxx | 10xxxxxx | 10xxxxxx | 10xxxxxx» (21 bits útiles).
Mitad inferior, título «Ejemplo: € = U+20AC»: una cadena de tres pasos de izquierda a derecha con flechas:
Paso 1: «U+20AC = 0010 0000 1010 1100 (16 bits)».
Paso 2: «Reparte en 4 + 6 + 6 bits: 0010 | 000010 | 101100».
Paso 3: «Añade prefijos: 11100010 | 10000010 | 10101100 = E2 82 AC», con los prefijos «1110», «10» y «10» en naranja y el resultado en un recuadro verde.
Título superior: «Cómo se codifica un code point en UTF-8».
Evita: cambiar bits o rangos, texto ilegible, elementos decorativos, mezclar los colores de prefijo y payload.""",
    "Tabla de patrones de bits de UTF-8 y codificación del símbolo euro paso a paso",
    """1 byte  U+0000–U+007F      0xxxxxxx
2 bytes U+0080–U+07FF      110xxxxx 10xxxxxx
3 bytes U+0800–U+FFFF      1110xxxx 10xxxxxx 10xxxxxx
4 bytes U+10000–U+10FFFF   11110xxx 10xxxxxx 10xxxxxx 10xxxxxx

€ = U+20AC = 0010 0000 1010 1100
  → 0010 | 000010 | 101100
  → 11100010 | 10000010 | 10101100 = E2 82 AC""",
)
nb.md(obs(r"""Comprueba que los 3 bytes de `€` coinciden con la salida de `utf8_encode("€")` (E2 82 AC). Fíjate en que los prefijos (`1110`, `10`, `10`) **nunca** aparecen como payload: por eso un byte `10xxxxxx` suelto delata que estás a mitad de un carácter."""))

nb.code(r'''
# Autosincronización: arranca la lectura en mitad de una secuencia y resincroniza en el siguiente byte que no sea de continuación
def resincroniza(b: bytes) -> str:
    i = 0
    while i < len(b) and (b[i] & 0xC0) == 0x80:      # descarta continuaciones huérfanas
        i += 1
    return utf8_decode(b[i:])

datos = "señal 😀 niño".encode("utf-8")
print("completo        :", datos.decode("utf-8"))
print("cortado en 'ñ'  :", datos[3:].decode("utf-8", errors="replace"), "(Python reemplaza con U+FFFD)")
print("resincronizado  :", resincroniza(datos[3:]))
# Prefijo único: el primer byte determina la longitud (código de prefijo)
longitud = lambda b0: 1 if b0 < 0x80 else 2 if 0xC2 <= b0 <= 0xDF else 3 if 0xE0 <= b0 <= 0xEF else 4 if 0xF0 <= b0 <= 0xF4 else 0
print("longitudes por byte inicial:", {hex(b): longitud(b) for b in (0x41, 0xC3, 0xE2, 0xF0, 0x80, 0xC0)})
''')

nb.md(r"""
> ### 🧪 Mini-experimento: los *overlongs* y por qué un decodificador estricto importa
> `C0 80` sería una forma «larga» de escribir `U+0000`. Un decodificador permisivo la aceptaría, y un filtro de seguridad que busque el byte `00` (o `/`, que se podría escribir `C0 AF`) no la vería. Probémoslo con nuestro decodificador y con el de Python.
""")
nb.code(r'''
for b in (b"\xc0\x80", b"\xc0\xaf", b"\xed\xa0\x80", b"\xf4\x90\x80\x80", b"\xe2\x82"):
    try: r = repr(utf8_decode(b))
    except ValueError as e: r = f"✗ {e}"
    try: p = repr(b.decode("utf-8"))
    except UnicodeDecodeError as e: p = f"✗ {e.reason}"
    print(b.hex(" ").upper().ljust(12), "| mío:", r.ljust(55)[:55], "| Python:", p)
''')

nb.md(r"""
## 4. UTF-16, UTF-32, *surrogates* y cómo guarda Python un `str`

* **UTF-32**: 4 bytes por code point, simple y desperdiciado.
* **UTF-16**: 2 bytes por code point del plano básico (BMP, `U+0000…U+FFFF`) y **4** (un *par sustituto*) para el resto. Fórmula: si $v = cp - 10000_{16}$, entonces $\text{alto}=D800_{16}+(v \gg 10)$ y $\text{bajo}=DC00_{16}+(v \,\&\, 3FF_{16})$. Por eso los *surrogates* no son caracteres válidos: son la «codificación» de UTF-16.
* **BOM** (`U+FEFF`): marca de orden de bytes al inicio de un archivo UTF-16; en UTF-8 es innecesario y suele ser un *bug* (aparece como un carácter invisible pegado a la primera palabra).
* **JavaScript** y Java miden `length` en **unidades UTF-16**: `"😀".length === 2`. Go y Rust miden `len` en **bytes**. Python mide **code points**. Truncar «a 100 caracteres» en cada lenguaje corta en sitios distintos.
* **CPython** (PEP 393) guarda cada `str` con **1, 2 o 4 bytes por code point** según el code point más grande que contenga.
""")
nb.code(r'''
def surrogados(cp):
    v = cp - 0x10000
    return 0xD800 + (v >> 10), 0xDC00 + (v & 0x3FF)
alto, bajo = surrogados(ord("😀"))
print(f"😀 U+1F600 → UTF-16: {alto:04X} {bajo:04X}  | Python: {'😀'.encode('utf-16-be').hex(' ').upper()}")
assert f"{alto:04X}{bajo:04X}" == "😀".encode("utf-16-be").hex().upper()

filas = []
for nombre, ch in [("ASCII 'a'", "a"), ("Latin-1 'é'", "é"), ("BMP 'ā'", "ā"), ("BMP '€'", "€"), ("Plano 1 '😀'", "😀")]:
    s = ch * 1000
    filas.append({"carácter": nombre, "UTF-8 (bytes)": len(s.encode("utf-8")), "UTF-16 (bytes)": len(s.encode("utf-16-le")),
                  "UTF-32 (bytes)": len(s.encode("utf-32-le")), "RAM de str en CPython": sys.getsizeof(s)})
display(pd.DataFrame(filas).set_index("carácter"))
''')
nb.md(obs(r"""La RAM de `str` en CPython salta a ≈ 1 B/carácter para ASCII y Latin-1, ≈ 2 B para BMP y ≈ 4 B en cuanto aparece **un** emoji: un solo carácter «grande» en un texto largo multiplica por 4 la memoria de **todo** el `str`. Y fíjate en que UTF-8 es la más compacta para ASCII pero la más cara que UTF-16 para `€` (3 vs 2 bytes): ninguna codificación es óptima para todos los idiomas."""))

nb.md(r"""
## 5. Grafemas: lo que el lector percibe como «un carácter»

Un **grafema** (*extended grapheme cluster*, UAX #29) agrupa code points que se muestran juntos: una letra base + marcas combinantes, banderas (dos *regional indicators*), emojis con modificadores de tono de piel, secuencias unidas con **ZWJ** (U+200D), teclas (`1️⃣`), sílabas devanagari con conjuntos consonánticos… La librería `regex` implementa `\X`.

> ⚠️ La segmentación de grafemas **depende de la versión de Unicode** del runtime: un emoji nuevo puede partirse en dos grafemas si tu librería es antigua. Anota la versión (`regex` y `unicodedata.unidata_version`) cuando midas.
""")
nb.code(r'''
casos = {"a": "a", "é (NFC)": "é", "é (NFD)": "é", "bandera ES": "🇪🇸", "pulgar tono medio": "👍🏽", "familia": "👨‍👩‍👧‍👦",
         "corazón (VS16)": "❤️", "tecla 1": "1️⃣", "bandera arcoíris": "🏳️‍🌈", "hangul (sílaba)": "한", "devanagari (conjunto)": "क्षि"}
filas = []
for nombre, s in casos.items():
    filas.append({"cadena": nombre, "grafemas": len(regex.findall(r"\X", s)), "code points (len)": len(s),
                  "unidades UTF-16": len(s.encode("utf-16-le")) // 2, "bytes UTF-8": len(s.encode("utf-8"))})
df_g = pd.DataFrame(filas).set_index("cadena")
display(df_g)
ax = df_g.plot.bar(figsize=(10, 4), color=[VERDE, AZUL, NARANJA, GRIS], width=0.8, rot=30)
ax.set_ylabel("unidades"); ax.set_title("Una misma cadena, cuatro formas de contarla"); ax.legend(loc="upper left", fontsize=8)
plt.tight_layout(); plt.show()
''')
nb.md(obs(r"""La columna de **grafemas** es 1 en casi todo (y 1 también para `é` en las dos formas); las demás divergen hasta **25 bytes** en la familia. Consecuencias prácticas: contar «caracteres» para un límite de UI debe hacerse en grafemas; contar *costo* de un LLM se hace en tokens, que dependen de los **bytes** (módulo 02). Y `é (NFD)` demuestra que *el mismo grafema* puede tener 2 representaciones distintas: es el problema que resuelve la normalización."""))

nb.md(r"""
## 6. Normalización Unicode: NFC, NFD, NFKC, NFKD

### El problema
Unicode permite **varias secuencias de code points para el mismo texto visible**: `é` puede ser `U+00E9` (1 code point, **precompuesto**) o `e` + `U+0301` (2 code points, **descompuesto**). Visualmente idénticos; para un programa, cadenas distintas: `"é" == "é"` es `False`, tienen distinto número de bytes y **producen distintos tokens**.

### Dos tipos de equivalencia y cuatro formas
* **Equivalencia canónica**: misma apariencia y significado (`é` ≡ `e`+◌́; también el signo `Å` ANGSTROM U+212B ≡ `Å` U+00C5).
* **Equivalencia de compatibilidad**: parecidas pero con distinción de formato/semántica (`ﬁ`≈`fi`, `²`≈`2`, `①`≈`1`, `Ｈ`≈`H`, `㎏`≈`kg`); aplanarlas **pierde información**.

| Forma | Qué hace | Cuándo |
|---|---|---|
| **NFD** | descompone canónicamente (y ordena las marcas combinantes) | análisis; quitar acentos (descartar marcas `Mn`) |
| **NFC** | NFD + recomposición canónica | **la forma «de intercambio»**: web, bases de datos; es la que recomienda W3C para texto |
| **NFKD** | descompone también por compatibilidad | búsqueda *agresiva* |
| **NFKC** | NFKD + recomposición | normalización de identificadores y de *matching*; SentencePiece usa una variante por defecto |

Algoritmo (UAX #15): **(1)** descomponer cada carácter con su tabla (recursivamente; las sílabas Hangul se descomponen *algorítmicamente* en *jamo*); **(2)** reordenar las marcas combinantes por su *combining class* (de modo estable); **(3)** (NFC/NFKC) recomponer pares evitando las *exclusiones de composición*. Implementamos (1)+(2) —**NFD**— a mano usando las tablas de `unicodedata` y lo verificamos contra la implementación de Python en **todo** el espacio Unicode.
""")

nb.gemini(
    "imagen", "M01-IMG-03", "Las cuatro formas de normalización",
    "Un diagrama de las cuatro formas (NFC, NFD, NFKC, NFKD) con las dos operaciones (descomponer, recomponer) y ejemplos reales: é, Å (signo ångström) y la ligadura ﬁ.",
    """Diagrama técnico limpio, fondo blanco, 16:9. Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Tipografía sans-serif legible, sin ilustraciones decorativas.
Composición: una cuadrícula de 2×2 cajas grandes con flechas entre ellas.
Fila superior (borde azul, etiqueta lateral «Equivalencia canónica»): a la izquierda la caja «NFC (compuesta)», a la derecha la caja «NFD (descompuesta)». Entre ambas, una flecha hacia la derecha etiquetada «descomponer» y una flecha hacia la izquierda etiquetada «recomponer».
Fila inferior (borde naranja, etiqueta lateral «Equivalencia de compatibilidad»): a la izquierda la caja «NFKC (compuesta)», a la derecha la caja «NFKD (descompuesta)», con las mismas dos flechas entre ellas.
Flechas verticales grises de cada caja superior a la inferior de su columna, etiquetadas «+ compatibilidad (pierde formato)».
Dentro de cada caja, tres ejemplos con estos textos EXACTOS:
NFC: «é = U+00E9», «Å (ångström U+212B) → U+00C5», «ﬁ = U+FB01 (se conserva)».
NFD: «é = U+0065 U+0301», «Å → U+0041 U+030A», «ﬁ = U+FB01 (se conserva)».
NFKC: «é = U+00E9», «Å → U+00C5», «ﬁ → fi (U+0066 U+0069)».
NFKD: «é = U+0065 U+0301», «Å → U+0041 U+030A», «ﬁ → fi (U+0066 U+0069)».
Título superior: «Formas de normalización Unicode». Nota inferior en gris: «NFC es la forma recomendada para intercambio de texto; NFKC/NFKD pierden información».
Evita: cambiar los code points indicados, texto ilegible, flechas ambiguas, iconos decorativos.""",
    "Cuadrícula 2x2 con NFC, NFD, NFKC y NFKD y los ejemplos é, Å y la ligadura fi",
    """                    descomponer →
 canónica       [ NFC ]  ──────────►  [ NFD ]
                é = U+00E9            é = U+0065 U+0301
                Å(U+212B)→U+00C5      Å → U+0041 U+030A
                ﬁ = U+FB01            ﬁ = U+FB01
                    ◄── recomponer
        + compatibilidad ↓                 ↓
 compat.        [ NFKC ] ─────────►  [ NFKD ]
                ﬁ → fi (U+0066 U+0069)  ﬁ → fi""",
)
nb.md(obs(r"""Mira la **fila canónica**: NFC y NFD son intercambiables *sin pérdida*. En la **fila de compatibilidad**, `ﬁ` se convierte en `fi` y ya no hay vuelta atrás (por eso NFKC es útil para *buscar* pero peligroso para *almacenar* o para código)."""))

nb.code(r'''
ejemplos = ["é", "é", "Å", "ﬁ", "²", "①", "Ｈｅｌｌｏ", "㎏", "½", "한"]
filas = []
for s in ejemplos:
    fila = {"original": s, "code points": " ".join(f"{ord(c):04X}" for c in s)}
    for forma in ("NFC", "NFD", "NFKC", "NFKD"):
        n = unicodedata.normalize(forma, s)
        fila[forma] = f"{n} ({' '.join(f'{ord(c):04X}' for c in n)})"
    filas.append(fila)
display(pd.DataFrame(filas).set_index("original"))
print("é == e+◌́ ?", "é" == "é", "| tras NFC:", unicodedata.normalize("NFC", "é") == unicodedata.normalize("NFC", "é"))
''')

nb.code(r'''
# NFD «a mano»: descomposición canónica recursiva + Hangul algorítmico + orden canónico de marcas combinantes
SBASE, LBASE, VBASE, TBASE, LCOUNT, VCOUNT, TCOUNT = 0xAC00, 0x1100, 0x1161, 0x11A7, 19, 21, 28
NCOUNT = VCOUNT * TCOUNT; SCOUNT = LCOUNT * NCOUNT

def _decomp_canonica(ch: str) -> str:
    cp = ord(ch)
    if SBASE <= cp < SBASE + SCOUNT:                              # sílaba Hangul → jamo (algoritmo, sin tabla)
        s = cp - SBASE
        partes = [LBASE + s // NCOUNT, VBASE + (s % NCOUNT) // TCOUNT] + ([TBASE + s % TCOUNT] if s % TCOUNT else [])
        return "".join(map(chr, partes))
    d = unicodedata.decomposition(ch)
    if not d or d.startswith("<"):                                # sin descomposición, o de compatibilidad (<font>, <compat>…)
        return ch
    return "".join(_decomp_canonica(chr(int(h, 16))) for h in d.split())

def mi_nfd(s: str) -> str:
    out = [c for ch in s for c in _decomp_canonica(ch)]
    i = 0
    while i < len(out):                                           # ordena cada racha de marcas por su combining class (estable)
        if unicodedata.combining(out[i]) == 0:
            i += 1; continue
        j = i
        while j < len(out) and unicodedata.combining(out[j]) != 0:
            j += 1
        out[i:j] = sorted(out[i:j], key=unicodedata.combining)
        i = j
    return "".join(out)

t0 = time.time()
malos = [cp for cp in range(0x110000) if not 0xD800 <= cp <= 0xDFFF and mi_nfd(chr(cp)) != unicodedata.normalize("NFD", chr(cp))]
rng = random.Random(SEED); marcas = [chr(c) for c in range(0x300, 0x370)] + ["̣", "̛"]; base = list("aeouñ") + ["ệ", "ǖ", "ṩ", "한", "ǆ"]
fallos = sum(mi_nfd(s) != unicodedata.normalize("NFD", s) for s in
             ("".join(rng.choice(base) + "".join(rng.choice(marcas) for _ in range(rng.randint(0, 3))) for _ in range(3)) for _ in range(20_000)))
print(f"mi_nfd vs unicodedata: {0x110000 - 2048:,} caracteres sueltos → {len(malos)} discrepancias; 20 000 cadenas con marcas desordenadas → {fallos} discrepancias ({time.time() - t0:.1f} s)")
print("ṩ  (s + punto debajo + punto encima) en orden inverso →", [f"{ord(c):04X}" for c in mi_nfd("ṩ")], "(el punto de abajo, ccc=220, pasa antes que el de arriba, ccc=230)")
assert not malos and fallos == 0
''')

nb.md(r"""
### ¿Qué normalizan los tokenizers de verdad?
La normalización es **la primera etapa** de un pipeline de tokenización (módulo 03 lo desarrolla con `tokenizers`):

* **`tiktoken`** (GPT-2, cl100k, o200k) **no normaliza**: toma los bytes tal cual (lo verificamos abajo con la librería).
* **SentencePiece** aplica por defecto la regla **`nmt_nfkc`** (NFKC + normalización de espacios); la regla `identity` la desactiva (documentación oficial de SentencePiece).
* **BERT *uncased*** (en Hugging Face `BertTokenizer`) pasa a minúsculas y **elimina acentos** vía NFD + descartar marcas `Mn` (parámetro `strip_accents`).
* **Hugging Face `tokenizers`** ofrece normalizadores componibles (`NFC`, `NFD`, `NFKC`, `NFKD`, `Lowercase`, `StripAccents`, `BertNormalizer`…), con el mismo resultado que `unicodedata`.
""")
nb.code(r'''
from tokenizers import normalizers
muestra = "Canción ﬁnal ① Ｈｏｌａ"
for nombre, norm in [("NFC", normalizers.NFC()), ("NFD", normalizers.NFD()), ("NFKC", normalizers.NFKC()),
                     ("NFD+StripAccents", normalizers.Sequence([normalizers.NFD(), normalizers.StripAccents()]))]:
    r = norm.normalize_str(muestra)
    print(f"{nombre:18}→ {r!r}  (len = {len(r)} code points)")
assert normalizers.NFD().normalize_str("canción") == mi_nfd("canción") == unicodedata.normalize("NFD", "canción")
print("✔ HF tokenizers NFD == mi_nfd == unicodedata NFD")
''')

nb.md(r"""
### Impacto 1: bytes y tokens
Un tokenizer **byte-level** (el de GPT-2) ve los bytes. Misma palabra, dos formas: ¿cuántos bytes y cuántos tokens cuesta cada una? Usamos el vocabulario real de GPT-2 (descargado de `tiktoken` o de un espejo de GitHub verificado con SHA-256).
""")
nb.code(SRC_GPT2)
nb.code(r'''
enc = get_gpt2_encoding()
palabras = ["canción", "número", "información", "más", "año", "niño", "pingüino", "también", "país", "señal"]
filas = []
for w in palabras:
    nfc, nfd = unicodedata.normalize("NFC", w), unicodedata.normalize("NFD", w)
    filas.append({"palabra": w, "bytes NFC": len(nfc.encode()), "bytes NFD": len(nfd.encode()),
                  "tokens NFC": len(enc.encode(nfc)) if enc else np.nan, "tokens NFD": len(enc.encode(nfd)) if enc else np.nan})
df_n = pd.DataFrame(filas).set_index("palabra")
display(df_n)
if enc:
    ax = df_n[["tokens NFC", "tokens NFD"]].plot.bar(figsize=(9, 3.8), color=[AZUL, NARANJA], rot=30, width=0.8)
    ax.set_ylabel("tokens GPT-2"); ax.set_title("La misma palabra visible, dos normalizaciones, dos costos")
    plt.tight_layout(); plt.show()
    print("media de tokens NFC → NFD:", df_n["tokens NFC"].mean(), "→", df_n["tokens NFD"].mean())
    print("tiktoken NO normaliza: encode('é') =", enc.encode("é"), "| encode('e' + U+0301) =", enc.encode("e\u0301"))
    assert enc.encode("é") != enc.encode("e\u0301")
''')
nb.md(obs(r"""Para **cada** palabra, la forma NFD cuesta más bytes (+1 por marca combinante) y **más tokens** (el vocabulario de GPT-2 contiene tokens precompuestos como `ón`, `ás` o `ño` (mira `canción` → `can`·`ci`·`ón`) pero casi ninguno con la marca `U+0301` suelta, así que `o`+◌́ cae a bytes). Si tu corpus mezcla NFC y NFD, el mismo concepto genera **secuencias de tokens distintas**: peor compresión, vocabulario fragmentado y *recall* perdido."""))

nb.md(r"""
### Impacto 2: búsqueda
Volvamos a Políglota. Indexamos los documentos en español con un tokenizador léxico *ingenuo* (`\w+` en minúsculas, **sin** normalizar) y lanzamos las consultas en NFC y en NFD. Después probamos con la normalización NFC dentro del tokenizador. Reutilizamos `carga_corpus`, las métricas y BM25 del módulo 00.
""")
_c = src_corpus_cells()
nb.code("# ── Utilidades canónicas del módulo 00 (1/3): datos del corpus sintético ──\n" + _c[0])
nb.code("# ── Utilidades canónicas del módulo 00 (2/3): generador sintético ──\n" + _c[1])
nb.code("# ── Utilidades canónicas del módulo 00 (3/3): carga_corpus ──\n" + _c[2])
nb.code("# ── Métricas canónicas del módulo 00 ──\n" + SRC_METRICS)
nb.code("# ── BM25 del módulo 00 ──\n" + SRC_BM25)
nb.code(r'''
corpus = carga_corpus(fast_dev=FAST_DEV_RUN)
docs, queries, qrels, source = corpus["docs"], corpus["queries"], corpus["qrels"], corpus["source"]
print(f"source = {source!r} | {len(docs)} docs | {len(queries)} queries")

es_docs = [d for d in docs if d["lang"] == "es"]; es_q = [q for q in queries if q["lang"] == "es"]
qr_es = {q["qid"]: qrels[q["qid"]] for q in es_q}
ingenuo = lambda t: re.findall(r"\w+", t.lower())
nfc = lambda t: unicodedata.normalize("NFC", t); nfd = lambda t: unicodedata.normalize("NFD", t)

def ndcg_es(tok, f_doc=lambda t: t, f_q=lambda t: t):
    bm = BM25().fit([tok(f_doc(d["text"])) for d in es_docs], [d["id"] for d in es_docs])
    run = {q["qid"]: bm.search(tok(f_q(q["text"])), 10) for q in es_q}
    return evaluate(run, qr_es)["ndcg"]

res = {"docs NFC · consulta NFC": ndcg_es(ingenuo), "docs NFC · consulta NFD": ndcg_es(ingenuo, f_q=nfd),
       "docs NFD · consulta NFC": ndcg_es(ingenuo, f_doc=nfd), "docs NFD · consulta NFD": ndcg_es(ingenuo, nfd, nfd),
       "docs NFC · consulta NFD\n(+ NFC en el tokenizador)": ndcg_es(lambda t: ingenuo(nfc(t)), f_q=nfd)}
fig, ax = plt.subplots(figsize=(9, 3.8))
ax.bar(list(res), list(res.values()), color=[VERDE, ROJO, ROJO, VERDE, AZUL]); ax.set_ylim(0, 1.05)
for i, v in enumerate(res.values()): ax.text(i, v + 0.01, f"{v:.3f}", ha="center")
ax.set_ylabel("nDCG@10 (consultas ES)"); ax.set_title(f"Efecto de la forma de normalización en la búsqueda (corpus {source})")
plt.xticks(fontsize=8); plt.tight_layout(); plt.show()
''')
nb.md(obs(r"""Cuando la forma de la consulta **no coincide** con la del índice (barras rojas) el nDCG cae, porque las palabras acentuadas dejan de coincidir como cadenas. Cuando ambas coinciden (verdes) o el tokenizador normaliza (azul), se recupera. La caída depende de la fracción de consultas con tildes en tu corpus (sintético: pequeña; Wikipedia real: mayor). **Regla:** normaliza *al ingerir* y *al consultar* con la misma función."""))

nb.md(caja("🧪 Experimento", r"""
**Python normaliza tus identificadores con NFKC** (PEP 3131). Puedes verificarlo: `ａ = 1` (con «ａ» de ancho completo) define la variable `a`.
"""))
nb.code(r'''
ns = {}
exec("ａ = 1\n", ns)
print("variables definidas:", [k for k in ns if not k.startswith("__")], "| 'a' in ns:", "a" in ns)
''')

nb.md(r"""
## 7. Homoglifos, caracteres invisibles y seguridad

Dos cadenas pueden **verse idénticas** y ser distintas porque Unicode contiene caracteres de aspecto igual en escrituras diferentes (**homoglifos**: la «а» cirílica U+0430 y la «a» latina U+0061) y caracteres **sin apariencia** (espacio de ancho cero U+200B, unión de ancho cero U+200D, BOM U+FEFF, **controles bidireccionales** U+202A–202E y U+2066–2069, y los *tag characters* U+E0000–E007F).

* **Homoglifos** → ataques de *phishing* (IDN homograph), cuentas suplantadas, evasión de filtros.
* **Controles bidireccionales** → *Trojan Source* (Boucher & Anderson, 2021): el código se **ve** de una manera y se **ejecuta** de otra.
* **Tag characters** → «ASCII smuggling»: texto invisible que los modelos pueden leer. Documentado en 2024 por Johann Rehberger contra asistentes con LLM (ver referencias).
""")
nb.gemini(
    "imagen", "M01-IMG-04", "Homoglifos: mismas letras para el ojo, distintos bytes",
    "La palabra «paypal» auténtica frente a «pаypal» con una «а» cirílica: idéntica a la vista, distinta en code points y bytes. Muestra por qué un tokenizer y un filtro ven cosas distintas.",
    """Diagrama técnico limpio, fondo blanco, 16:9. Paleta: azul #1F6FEB para la versión latina, naranja #F28E2B para la versión con el carácter cirílico, rojo sobrio #D62728 solo para resaltar la diferencia, gris #6B7280 para anotaciones. Tipografía sans-serif legible y monoespaciada para los códigos, sin ilustraciones decorativas.
Composición: dos filas horizontales con la misma estructura, una sobre otra, con una línea de comparación entre ellas.
Fila superior (borde azul), título «Todo latino». Muestra la palabra «paypal» en grande; debajo los code points EXACTOS: «U+0070 U+0061 U+0079 U+0070 U+0061 U+006C»; debajo los bytes EXACTOS: «70 61 79 70 61 6C» (6 bytes).
Fila inferior (borde naranja), título «Con una «а» cirílica en la 2ª posición». Muestra «pаypal» en grande, con la segunda letra marcada con un círculo rojo; debajo los code points EXACTOS: «U+0070 U+0430 U+0079 U+0070 U+0061 U+006C»; debajo los bytes EXACTOS: «70 D0 B0 79 70 61 6C» (7 bytes), con «D0 B0» resaltado en rojo.
Entre las filas, un signo «≠» grande con la etiqueta «Se ven igual, son cadenas distintas».
A la derecha, un cuadro gris con el texto «Defensa: detectar palabras con escrituras mezcladas (LATIN + CYRILLIC) y normalizar a un esqueleto».
Título superior: «Homoglifos».
Evita: cambiar los códigos o bytes, texto ilegible, elementos decorativos o alarmistas, flechas ambiguas.""",
    "Dos filas comparando paypal en latino y con una a cirílica: code points y bytes distintos",
    """Todo latino          paypal     U+0070 U+0061 U+0079 U+0070 U+0061 U+006C    70 61 79 70 61 6C        (6 bytes)
                       ≠   se ven igual, son cadenas distintas
Con 'а' cirílica     pаypal     U+0070 U+0430 U+0079 U+0070 U+0061 U+006C    70 D0 B0 79 70 61 6C     (7 bytes)""",
)
nb.md(obs(r"""Compara las dos filas: la diferencia está en **una** posición (`61` → `D0 B0`), pero esa diferencia cambia la longitud en bytes (6 → 7), los tokens de un tokenizer byte-level y el resultado de cualquier comparación exacta."""))

nb.code(r'''
def escritura(ch: str) -> str:
    """Escritura aproximada de un carácter por la primera palabra de su nombre Unicode (LATIN, CYRILLIC, GREEK…)."""
    n = unicodedata.name(ch, "")
    return n.split()[0] if n else "?"

def palabra_mixta(w: str) -> bool:
    return len({escritura(c) for c in w if c.isalpha()} & {"LATIN", "CYRILLIC", "GREEK"}) >= 2

limpio, sucio = "paypal", "pаypal"
print(limpio == sucio, "| mixta:", palabra_mixta(limpio), palabra_mixta(sucio), "| escrituras:", {escritura(c) for c in sucio})
for s in ("a​b", "ho​la", "‮odnum", "A\U000e0042"):
    print(repr(s), "→ tokens GPT-2:", len(enc.encode(s)) if enc else "n/d", "| visibles:", len(s.encode("ascii", "ignore")), "ASCII")
ocultos = "".join(chr(0xE0000 + ord(c)) for c in "hi")
print("texto oculto en tag characters:", repr(ocultos), "| decodificado:", "".join(chr(ord(c) - 0xE0000) for c in ocultos))
''')
nb.md(obs(r"""Un único `U+200B` entre dos letras **cambia el número de tokens**: el tokenizer lo ve (no es «nada»). Por eso la normalización de Políglota (proyecto) elimina los invisibles de ancho cero y los controles bidireccionales, y marca las palabras con escrituras mezcladas. Los *tag characters* ocultan texto que no se ve pero que sí está en la secuencia."""))

nb.md(r"""
## 8. Bytes por carácter según el idioma (y su costo posterior)

La razón por la que el español pagó más tokens que el inglés en el módulo 00 empieza aquí. Medimos la **misma frase** («Hola, ¿cómo estás hoy?») en 12 idiomas: code points, grafemas, bytes UTF-8 y tokens GPT-2. *(Son frases cortas escritas a mano, para ilustrar, no para medir: la comparación rigurosa con Flores-200 es el módulo 04.)*
""")
nb.code(r'''
frases = {
    "inglés": "Hello, how are you today?", "español": "Hola, ¿cómo estás hoy?", "francés": "Bonjour, comment allez-vous aujourd'hui ?",
    "alemán": "Hallo, wie geht es dir heute?", "ruso": "Привет, как дела сегодня?", "griego": "Γεια σου, πώς είσαι σήμερα;",
    "árabe": "مرحبًا، كيف حالك اليوم؟", "hindi": "नमस्ते, आज आप कैसे हैं?", "tailandés": "สวัสดี วันนี้คุณเป็นอย่างไรบ้าง",
    "chino": "你好，你今天好吗？", "japonés": "こんにちは、今日はお元気ですか？", "coreano": "안녕하세요, 오늘 어떻게 지내세요?",
}
filas = []
for idioma, s in frases.items():
    filas.append({"idioma": idioma, "code points": len(s), "grafemas": len(regex.findall(r"\X", s)), "bytes UTF-8": len(s.encode("utf-8")),
                  "bytes/code point": len(s.encode("utf-8")) / len(s), "tokens GPT-2": len(enc.encode(s)) if enc else np.nan})
df_i = pd.DataFrame(filas).set_index("idioma")
df_i["tokens/code point"] = df_i["tokens GPT-2"] / df_i["code points"]
display(df_i.round(2))
fig, axs = plt.subplots(1, 2, figsize=(12, 4))
df_i["bytes/code point"].sort_values().plot.barh(ax=axs[0], color=AZUL); axs[0].set_xlabel("bytes por code point"); axs[0].set_title("Costo en bytes")
if enc:
    df_i["tokens GPT-2"].sort_values().plot.barh(ax=axs[1], color=NARANJA); axs[1].set_xlabel("tokens GPT-2 por frase"); axs[1].set_title("Costo en tokens (vocabulario GPT-2)")
plt.tight_layout(); plt.show()
''')
nb.md(obs(r"""1. **Bytes por code point** (columna izquierda): inglés, francés y alemán ≈ 1.00 (ASCII); español 1.14 por «¿», «ó», «á»; ruso, griego y árabe ≈ 1.8; hindi y coreano ≈ 2.5; tailandés ≈ 2.9; chino y japonés 3.0. Es el **piso** de lo que paga un tokenizer byte-level.
2. **Tokens GPT-2** (columna derecha, vocabulario fijo de GPT-2 verificado con `tiktoken`): el patrón se **amplifica**. La frase en inglés cuesta 7 tokens y la española 13; la del tailandés, **61**; la del coreano, 43. Con un vocabulario aprendido sobre todo en inglés, las escrituras poco vistas caen a bytes sueltos (casi un token por byte). Esta desigualdad la documentan Petrov et al. (2023) y Ahia et al. (2023).
3. Los *grafemas* difieren de los code points en árabe, hindi y tailandés (marcas combinantes): contar «caracteres» en esas escrituras es ambiguo.
4. Son frases cortas escritas a mano: busca la **tendencia**, no la cifra exacta (la comparación rigurosa con Flores es el módulo 04)."""))

nb.md(r"""
### Analogía lingüística: ¿qué unidad representa un carácter?
El costo en bytes no es arbitrario: depende de **qué cubre un code point** en cada sistema de escritura.

| Tipo de escritura | Ejemplo | Un code point ≈ | Bytes UTF-8 típicos |
|---|---|---|---|
| Alfabeto (latino, cirílico, griego) | español, ruso | un fonema | 1–2 |
| *Abjad* (consonantes) | árabe | una consonante (vocales como marcas) | 2 |
| *Abugida* (consonante+vocal) | hindi, tailandés | consonante o signo vocálico (conjuntos con marcas) | 3 |
| Silabario / sílabas compuestas | kana japonés, hangul coreano | una sílaba (hangul: bloque precompuesto) | 3 |
| Logografía | chino (hanzi) | una palabra o morfema | 3 |

Un carácter chino «vale» mucho más información que una `e`, pero cuesta 3 bytes. **Los bytes no miden información**; para eso hace falta *comprimir* (próxima sección).
""")

nb.md(r"""
## 9. Analogía con compresión de datos: bits por byte

Un byte tiene 8 bits pero **no aporta 8 bits de información**. La entropía de orden 0 de la distribución de bytes de un texto, $H_0=-\sum_{b}p(b)\log_2 p(b)$ (bits por byte), es un **límite inferior** para cualquier código que codifique cada byte por separado (Shannon, 1948); un compresor que explota el contexto (`zlib`/DEFLATE = LZ77 + Huffman, `bz2`, `lzma`) baja mucho más. En el módulo 02 verás que **BPE nació como compresor** (Gage, 1994) y que un tokenizer es, en el fondo, un compresor con un vocabulario fijo; la métrica natural es *bits por byte* de texto original.
""")
nb.code(r'''
def bits_por_byte(texto: str) -> dict:
    import bz2, lzma, zlib
    b = texto.encode("utf-8"); n = len(b); cnt = collections.Counter(b)
    H = -sum(v / n * math.log2(v / n) for v in cnt.values())
    return {"bytes": n, "H0 (orden 0)": H, "zlib": len(zlib.compress(b, 9)) * 8 / n, "bz2": len(bz2.compress(b)) * 8 / n, "lzma": len(lzma.compress(b)) * 8 / n}

filas = {lang: bits_por_byte("\n".join(d["text"] for d in docs if d["lang"] == lang)) for lang in ("es", "en", "code")}
df_c = pd.DataFrame(filas).T
display(df_c.round(3))
ax = df_c[["H0 (orden 0)", "zlib", "bz2", "lzma"]].plot.bar(figsize=(8, 3.8), color=[GRIS, AZUL, NARANJA, VERDE], rot=0, width=0.8)
ax.axhline(8, color=ROJO, ls="--", lw=1); ax.text(2.55, 7.7, "8 bits (sin comprimir)", color=ROJO, ha="right", fontsize=8)
ax.set_ylabel("bits por byte de texto"); ax.set_title(f"Entropía y compresión del corpus Políglota ({source})")
plt.tight_layout(); plt.show()
''')
nb.md(obs(r"""1. $H_0$ ≈ **4.5 bits/byte** en los tres corpus de esta ejecución: mirando solo la frecuencia de cada byte, un byte «vale» bastante menos de los 8 bits que ocupa.
2. Los compresores con contexto bajan **mucho** más. Con el corpus **sintético** el resultado es exagerado porque es muy repetitivo (plantillas): con Wikipedia real verás cifras más altas. Lo importante: *comprimir = capturar regularidades de más largo alcance que el byte*, exactamente lo que hará BPE al fusionar pares frecuentes."""))

nb.md(r"""
## 10. Mojibake y manejadores de errores

**Mojibake** (文字化け) es texto cuyos bytes se **decodificaron con la codificación equivocada**. El caso típico en español: UTF-8 leído como Latin-1/cp1252, que convierte `é` (`C3 A9`) en `Ã©`.
""")
nb.code(r'''
original = "Canción: «niño» – ¿qué señal?"
for enc_mal in ("latin-1", "cp1252"):
    roto = original.encode("utf-8").decode(enc_mal, errors="replace")
    print(f"{enc_mal:7}→ {roto}")
roto = original.encode("utf-8").decode("latin-1")
print("reparado :", roto.encode("latin-1").decode("utf-8"))
doble = roto.encode("utf-8").decode("latin-1")
print("doble mojibake:", doble[:40], "…")

import ftfy
print("ftfy.fix_text:", ftfy.fix_text(roto), "|", ftfy.fix_text(doble))
''')
nb.code(r'''
# Manejadores de errores de codificación: qué pasa con bytes que no son UTF-8 válido
crudo = b"abc\xff\xfedef"
for manejador in ("strict", "replace", "ignore", "backslashreplace", "surrogateescape"):
    try:
        s = crudo.decode("utf-8", errors=manejador)
        ida_vuelta = s.encode("utf-8", errors=manejador) == crudo if manejador in ("surrogateescape", "backslashreplace") else "—"
        print(f"{manejador:17}→ {s!r:28} ¿recupera los bytes originales? {ida_vuelta}")
    except UnicodeDecodeError as e:
        print(f"{manejador:17}→ ✗ UnicodeDecodeError ({e.reason})")

# Decodificación incremental: un token byte-level puede terminar a mitad de un carácter UTF-8
import codecs
dec = codecs.getincrementaldecoder("utf-8")()
trozos = "añ😀".encode("utf-8")
print("\nflujo byte a byte:", [dec.decode(trozos[i:i + 1]) for i in range(len(trozos))])
''')
nb.md(obs(r"""`replace` y `ignore` **destruyen información sin avisar** (el mojibake con `�` ya no es reparable); `surrogateescape` permite ida y vuelta sin pérdida de bytes desconocidos. Y el decodificador **incremental** muestra por qué, al hacer *streaming* de un LLM byte-level, a veces el siguiente token «no imprime nada»: sus bytes son solo parte de un carácter. Lo retomarás en el módulo 02."""))

nb.md(r"""
## 11. Políglota: ¿qué escrituras contiene tu corpus?
Cerramos la lección mirando el corpus del módulo 00: ¿qué escrituras aparecen y cuántos bytes por carácter cuesta cada tipo de documento? (En el proyecto harás la auditoría completa y un normalizador.)
""")
nb.code(r'''
def cuenta_escrituras(textos):
    cnt = collections.Counter()
    for t in textos:
        for ch, n in collections.Counter(t[:3000]).items():
            if ch.isalpha():
                cnt[escritura(ch)] += n
    return cnt

por_lang = {lang: cuenta_escrituras(d["text"] for d in docs if d["lang"] == lang) for lang in ("es", "en", "code")}
df_s = pd.DataFrame(por_lang).fillna(0)
df_s = df_s.loc[df_s.sum(axis=1).sort_values(ascending=False).index[:8]]
frac = (df_s / df_s.sum()).T
bpc = {l: sum(len(d["text"].encode()) for d in docs if d["lang"] == l) / sum(len(d["text"]) for d in docs if d["lang"] == l) for l in ("es", "en", "code")}
fig, axs = plt.subplots(1, 2, figsize=(11, 3.6))
frac.plot.bar(stacked=True, ax=axs[0], rot=0, colormap="tab20"); axs[0].set_ylabel("fracción de letras"); axs[0].set_title(f"Escrituras por tipo de documento ({source})"); axs[0].legend(fontsize=7)
axs[1].bar(list(bpc), [(v - 1) * 100 for v in bpc.values()], color=[AZUL, NARANJA, VERDE]); axs[1].set_ylabel("bytes extra por cada 100 caracteres"); axs[1].set_title("Sobrecoste de UTF-8 sobre ASCII")
plt.tight_layout(); plt.show()
print({k: round(v, 4) for k, v in bpc.items()})
''')
nb.md(obs(r"""Con datos **reales** (Wikipedia) verás, además de LATIN, trazas de CYRILLIC, GREEK, CJK y ARABIC en nombres propios dentro de los artículos; con el corpus sintético casi todo es LATIN. El sobrecoste de UTF-8 en español es del orden de **un uno por ciento** de bytes extra: pequeño en bytes, pero (como viste con GPT-2) mucho mayor en **tokens**, porque cada vocal con tilde rompe el patrón de las palabras más frecuentes."""))

nb.md(r"""
## 12. Mapa de madurez
Estado a **octubre de 2026**. 🟢 sólido · 🟡 emergente · 🔴 experimental.
""" + "\n\n" + mapa_madurez([
    ("UTF-8 como codificación universal de texto", "🟢", "Estándar de intercambio; los tokenizers byte-level (GPT-2, `tiktoken`) operan sobre sus bytes", "RFC 3629; Radford et al. 2019; Wang et al. 2019 (arXiv:1909.03341)"),
    ("Normalización NFC/NFKC antes de tokenizar", "🟢", "SentencePiece: `nmt_nfkc` por defecto; BERT *uncased*: NFD + quitar acentos", "Documentación de SentencePiece (`doc/normalization.md`); código de `BertTokenizer` en `transformers`"),
    ("Tokenizar bytes sin normalizar (`tiktoken`)", "🟢", "Encodings de OpenAI (`gpt2`, `cl100k_base`, `o200k_base`)", "Repositorio `openai/tiktoken` (código fuente de `Encoding.encode`)"),
    ("Detección de confusables / escrituras mezcladas", "🟢", "Mecanismos de detección de suplantación (*spoofing*) definidos por el Consorcio Unicode", "Unicode Technical Standard #39 (Unicode Security Mechanisms)"),
    ("Defensa contra Trojan Source y caracteres bidi", "🟢", "Mitigaciones en compiladores y editores descritas tras la divulgación coordinada (2021)", "Boucher & Anderson 2021 (arXiv:2111.00169)"),
    ("Filtrado de *tag characters* y texto invisible en prompts de LLM", "🟡", "Reportado contra asistentes con LLM en 2024; las defensas varían por proveedor", "Cobertura de The Register (ago-2024) sobre el trabajo de J. Rehberger"),
    ("Modelos que consumen bytes directamente (ByT5, BLT)", "🟡 / 🔴", "Investigación de Google (ByT5) y Meta FAIR (BLT); no son el estándar de producción", "Xue et al. 2021 (arXiv:2105.13626); Pagnoni et al. 2024 (arXiv:2412.09871)"),
]) + "\n")

nb.md(r"""
## 13. 🏭 En producción
* **Normaliza en la frontera.** En el pipeline de ingesta de un buscador, normaliza a **NFC** (y aplica la misma función a las consultas), conserva el original para mostrarlo y **guarda la versión de la normalización** junto al índice: cambiarla invalida los índices.
* **Búsqueda léxica con plegado.** Elasticsearch/OpenSearch ofrecen filtros `asciifolding` y, con el plugin ICU, `icu_normalizer`/`icu_folding` para hacer la normalización y el plegado de acentos en el analizador (es el mismo problema que acabas de resolver a mano).
* **Costo de tokens por idioma.** Los proveedores cobran por token; el sobrecoste de bytes de una escritura se traduce en dinero y en menos contexto útil (Petrov et al. 2023; Ahia et al. 2023). Mide *tokens por carácter* de **tu** tráfico real antes de elegir proveedor.
* **Seguridad de entrada.** Antes de pasar texto de usuarios a un LLM: normaliza, elimina controles bidi y tag characters, y registra escrituras mezcladas. Es barato y bloquea una familia entera de ataques.
* **Truncar por grafemas.** Para mostrar «los primeros 100 caracteres» en UI, corta en grafemas (`\X`), no en code points ni en bytes: evitas emojis partidos y marcas huérfanas.
""")

nb.md(r"""
## 14. 🧠 Secretos de la élite
1. **`len()` no significa lo mismo en todos los lenguajes**: Python cuenta code points, JavaScript/Java unidades UTF-16, Go/Rust bytes. Un límite de «N caracteres» validado en el *frontend* (JS) y en el *backend* (Python) puede discrepar en cualquier texto con emojis; compruébalo con la tabla de la sección 5.
2. **NFC y NFD producen secuencias de tokens distintas** en un tokenizer byte-level: mide la tabla de la sección 6 con tu propio tokenizer antes de entrenarlo. Un corpus de preentrenamiento sin normalizar fragmenta el vocabulario.
3. **NFKC es un martillo**: pliega `²`→`2`, `ﬁ`→`fi`, `㎏`→`kg` y rompe código/fórmulas. Úsalo para *matching* y para identificadores (Python lo aplica a los nombres de variables, PEP 3131; lo verificaste arriba) y no para almacenar texto.
4. **La versión de Unicode importa**: `unicodedata.unidata_version` y la de `regex` determinan categorías, normalización y segmentación de grafemas; un emoji nuevo puede partirse en dos en un runtime antiguo. Registra la versión en tus experimentos.
5. **Un solo carácter invisible cambia el número de tokens** (sección 7). Los ataques de *smuggling* explotan que el tokenizer ve lo que el humano no: sanea antes del tokenizer, no después.
6. **`errors="replace"` es destructivo y silencioso**: el `�` (U+FFFD) no es reversible. Para datos de origen desconocido usa `surrogateescape` y arregla la codificación en origen (`ftfy` solo es una red de seguridad).
7. **Un solo emoji multiplica por 4 la RAM de un `str` de CPython** (PEP 393, sección 4): relevante al procesar corpus enormes carácter a carácter en Python.
8. **Los token a mitad de carácter existen**: un token de un BPE byte-level puede ser medio carácter UTF-8; para *streaming* hace falta un decodificador incremental (sección 10) y es la causa de los `�` que a veces ves en salidas parciales.
""")

nb.md(r"""
## 15. ⚠️ Errores comunes
* **Usar `encode("ascii", "ignore")` para «quitar acentos»**: borra *todo* carácter no ASCII (ñ, 中, emojis). Lo correcto: NFD + descartar marcas `Mn` (y solo en escrituras latinas).
* **Comparar cadenas sin normalizar** (`"é" == "é"` es falso) en búsquedas, claves de diccionario o deduplicación.
* **Aplicar NFKC a todo** y romper código, fórmulas y nombres.
* **Abrir archivos sin `encoding="utf-8"`** (el valor por defecto depende de la plataforma) y heredar mojibake.
* **Cortar bytes a ciegas** (`s.encode()[:100].decode()`) y partir caracteres: usa `errors="ignore"` solo conscientemente o corta en límites de code point/grafema.
* **Ignorar caracteres de formato** (BOM, ZWSP) al comparar o tokenizar: aparecen «pegados» a la primera palabra de un archivo.
* **Fiarse de la segmentación de grafemas de un runtime antiguo** con emojis recientes.
""")

nb.md(r"""
## 16. Autoevaluación
""" + "\n" + preguntas([
    ("(Cálculo)", "¿Cuántos code points, grafemas y bytes UTF-8 tiene «Ñandú 😀»? (supón que todo está en NFC).",
     "Code points: `Ñ a n d ú ␣ 😀` = **7**. Grafemas: **7**. Bytes: Ñ(2)+a(1)+n(1)+d(1)+ú(2)+espacio(1)+😀(4) = **12**."),
    ("(Cálculo)", "Codifica a mano `U+00F1` (ñ) en UTF-8 y comprueba el resultado.",
     "`U+00F1` = `0000 0000 1111 0001`; cae en el rango de 2 bytes (11 bits útiles: `00011 110001`). Prefijos: `110` + `00011` = `11000011` = `C3`; `10` + `110001` = `10110001` = `B1`. Resultado **`C3 B1`**. Lo confirma `'ñ'.encode().hex()`."),
    ("(Diagnóstico)", "Tu buscador no encuentra «canción» aunque el documento la contiene, y `\"canción\" == doc_palabra` da `False`. ¿Qué compruebas primero y cómo lo arreglas?",
     "Compara las secuencias de code points (`[hex(ord(c)) for c in ...]`): lo más probable es que una esté en NFD (`o`+`U+0301`) y la otra en NFC (`U+00F3`), o que haya un invisible (`U+200B`). Se arregla normalizando a NFC —y quitando invisibles— en ingesta y consulta con la **misma** función."),
    ("(Diagnóstico)", "Un usuario pega «pаypal.com» (con «а» cirílica) en tu campo de búsqueda y tu filtro de listas de bloqueo no lo detecta. ¿Por qué y qué defensa añadirías?",
     "El filtro compara cadenas/bytes y la «а» cirílica son otros bytes (`D0 B0`). Defensas: detectar palabras con escrituras mezcladas (LATIN+CYRILLIC), mapear a un *esqueleto* de confusables (UTS #39) antes de comparar y, en dominios, usar Punycode/IDN con política de escrituras."),
    ("(Transferencia)", "Vas a entrenar un tokenizer BPE con 50 GB de texto web. ¿Qué decisiones de normalización tomas antes y por qué afectan al vocabulario?",
     "Fijar NFC (o NFKC si el uso es de *matching*) para evitar que `é` y `e`+◌́ generen vocabularios duplicados; decidir qué hacer con invisibles (BOM, ZWSP) y controles; decidir si conservar ZWJ/ZWNJ (necesarios en emojis y en persa/indio); y registrar la forma usada, porque en inferencia hay que aplicar **la misma** normalización o los tokens no coincidirán."),
    ("(Transferencia)", "Diseña una regla para recortar un texto a «no más de 280 caracteres visibles» en una app multiplataforma (web JS, Android Kotlin, backend Python).",
     "Medir y cortar en **grafemas** (UAX #29) con la misma versión de Unicode en todas las plataformas, no en `length` (UTF-16 en JS/Kotlin) ni en bytes. Tests con emojis ZWJ, banderas y marcas combinantes."),
    ("", "¿Por qué UTF-8 prohíbe las codificaciones demasiado largas (*overlongs*)?",
     "Porque cada code point debe tener **una única** codificación; si no, un filtro que busque la forma canónica de un byte peligroso (`/`, `\\0`) podría saltarse con su forma larga (`C0 AF`)."),
]) + "\n")

nb.md(caja("➡️ Siguiente módulo", r"""
**02 · BPE desde cero.** Ya sabes que un tokenizer byte-level ve **bytes UTF-8**. En el módulo 02 implementas el algoritmo de Byte Pair Encoding —nacido como compresor—, la pre-tokenización con regex de GPT-2/cl100k/o200k, el entrenamiento eficiente y la verificación contra `tiktoken`: la normalización que acabas de dominar determina exactamente sobre qué se aprenden las fusiones.
"""))

nb.md(r"""
## 17. Referencias
Referencias de arXiv comprobadas (título y autores) el 25-oct-2026; normas, artículos y enlaces verificados de nuevo el 26-oct-2026 (verificador de referencias). Las normas Unicode se actualizan con cada versión de Unicode: la URL sin número de revisión apunta siempre a la vigente (UAX #15 va por la revisión 57, Unicode 17.0, jul-2025).

* Unicode Consortium (ed. K. Whistler). *Unicode Standard Annex #15: Unicode Normalization Forms* (UAX #15). https://www.unicode.org/reports/tr15/
* Unicode Consortium. *Unicode Standard Annex #29: Unicode Text Segmentation* (UAX #29, grafemas). https://www.unicode.org/reports/tr29/
* Unicode Consortium. *Unicode Technical Standard #39: Unicode Security Mechanisms* (confusables; datos en `confusables.txt`). https://www.unicode.org/reports/tr39/
* Yergeau, F. (2003). *UTF-8, a transformation format of ISO 10646.* RFC 3629 / STD 63 (IETF, Internet Standard; reemplaza a RFC 2279). https://www.rfc-editor.org/rfc/rfc3629
* Pike, R., Thompson, K. (1993). *Hello World or Καλημέρα κόσμε or こんにちは 世界.* USENIX Winter 1993 Conference, San Diego (historia de UTF-8). https://www.usenix.org/conference/usenix-winter-1993-conference/hello-world
* Boucher, N., Anderson, R. (2021). *Trojan Source: Invisible Vulnerabilities.* arXiv:2111.00169. https://arxiv.org/abs/2111.00169
* Wang, C., Cho, K., Gu, J. (2019). *Neural Machine Translation with Byte-Level Subwords.* arXiv:1909.03341. https://arxiv.org/abs/1909.03341
* Petrov, A. et al. (2023). *Language Model Tokenizers Introduce Unfairness Between Languages.* arXiv:2305.15425. https://arxiv.org/abs/2305.15425
* Ahia, O. et al. (2023). *Do All Languages Cost the Same? Tokenization in the Era of Commercial Language Models.* arXiv:2305.13707. https://arxiv.org/abs/2305.13707
* Xue, L. et al. (2021). *ByT5: Towards a token-free future with pre-trained byte-to-byte models.* arXiv:2105.13626. https://arxiv.org/abs/2105.13626
* Pagnoni, A. et al. (2024). *Byte Latent Transformer: Patches Scale Better Than Tokens.* arXiv:2412.09871. https://arxiv.org/abs/2412.09871
* Mielke, S. J. et al. (2021). *Between words and characters: A Brief History of Open-Vocabulary Modeling and Tokenization in NLP.* arXiv:2112.10508. https://arxiv.org/abs/2112.10508
* Shannon, C. E. (1948). *A Mathematical Theory of Communication.* Bell System Technical Journal.
* SentencePiece, documentación de normalización: https://github.com/google/sentencepiece/blob/master/doc/normalization.md
* The Register (28-ago-2024). *From Copilot to Copirate* (cadena de ataques contra Microsoft 365 Copilot con ASCII smuggling, descubierta por J. Rehberger). https://www.theregister.com/2024/08/28/microsoft_copilot_copirate
* Python: `unicodedata`, `codecs`, PEP 393 (representación flexible de `str`) y PEP 3131 (identificadores no ASCII). · `ftfy` (https://pypi.org/project/ftfy/).
""")

nb.save(str(ROOT.parent / LPATH))

# ════════════════════════════════════════════════════════════════════════════
#  PROYECTO · Auditoría Unicode + normalizador
# ════════════════════════════════════════════════════════════════════════════
PPATH = f"{REL}/01_proyecto_unicode_bytes.ipynb"
pb = Notebook("Módulo 01 · Proyecto: auditoría Unicode y normalizador", colab_path=PPATH)

# ---- Código dado (no TODO) ----
GIVEN_CONTAMINAR = r'''
# ── Dado: inyector de ruido con verdad conocida ──
ZW = ["\u200b", "\u2060", "\ufeff"]
BIDI = ["\u202e", "\u202d", "\u2066", "\u2069"]
HOMOGLIFOS = {"a": "\u0430", "e": "\u0435", "o": "\u043e", "p": "\u0440", "c": "\u0441", "x": "\u0445", "i": "\u0456"}  # letras cirílicas
TIPOS = ["nfd", "zero_width", "homoglifo", "mojibake", "nbsp", "ancho_completo", "bidi"]

def _p_nfd(t, r): return unicodedata.normalize("NFD", t)
def _p_zw(t, r):
    ws = list(re.finditer(r"[^\W\d_]{4,}", t)); r.shuffle(ws)
    for m in sorted(ws[:5], key=lambda m: -m.start()):
        k = m.start() + r.randint(1, len(m.group()) - 1); t = t[:k] + r.choice(ZW) + t[k:]
    return t
def _p_homoglifo(t, r):
    ws = [m for m in re.finditer(r"[a-z]{4,}", t) if any(ch in HOMOGLIFOS for ch in m.group())]; r.shuffle(ws)
    for m in sorted(ws[:5], key=lambda m: -m.start()):
        w = m.group(); k = r.choice([i for i, ch in enumerate(w) if ch in HOMOGLIFOS])
        t = t[:m.start()] + w[:k] + HOMOGLIFOS[w[k]] + w[k + 1:] + t[m.end():]
    return t
def _p_mojibake(t, r): return t.encode("utf-8").decode("latin-1")
def _p_nbsp(t, r): return re.sub(r"(?<=\w) (?=\w)", lambda m: "\u00a0" if r.random() < 0.3 else " ", t)
def _p_ancho(t, r): return "".join(chr(ord(c) + 0xFEE0) if "!" <= c <= "~" and r.random() < 0.2 else c for c in t)
def _p_bidi(t, r):
    k = r.randrange(len(t)); return t[:k] + r.choice(BIDI) + t[k:]
_PERT = dict(nfd=_p_nfd, zero_width=_p_zw, homoglifo=_p_homoglifo, mojibake=_p_mojibake, nbsp=_p_nbsp, ancho_completo=_p_ancho, bidi=_p_bidi)

def contaminar(docs, tasa=0.3, seed=42):
    """Copia de `docs` con UNA perturbación en ≈ `tasa` de los documentos (no de código).
    Devuelve (docs_sucios, verdad) con verdad = {doc_id: tipo} solo si el texto realmente cambió."""
    r = random.Random(seed); sucios, verdad = [], {}
    for d in docs:
        d2 = dict(d)
        if d["lang"] != "code" and r.random() < tasa:
            tipos = TIPOS[:]; r.shuffle(tipos)                      # el primer tipo que realmente cambie el texto
            for tipo in tipos:
                nuevo = _PERT[tipo](d["text"], r)
                if nuevo != d["text"]:
                    d2["text"] = nuevo; verdad[d["id"]] = tipo; break
        sucios.append(d2)
    return sucios, verdad
'''
GIVEN_DETECCION = r'''
def evaluar_deteccion(audits, verdad, detectores):
    """Precisión y recall por tipo. `audits`: {doc_id: dict de audit_doc}; `detectores`: {tipo: f(audit) -> bool}."""
    filas = {}
    for tipo, f in detectores.items():
        tp = sum(1 for i, t in verdad.items() if t == tipo and f(audits[i]))
        fn = sum(1 for i, t in verdad.items() if t == tipo and not f(audits[i]))
        fp = sum(1 for i, a in audits.items() if f(a) and i not in verdad)       # marcados pero LIMPIOS (sin inyección)
        filas[tipo] = {"verdaderos": tp + fn, "recall": tp / max(tp + fn, 1), "FP en limpios": fp,
                       "precisión (vs limpios)": tp / max(tp + fp, 1)}
    return pd.DataFrame(filas).T
'''

# ---- Soluciones ----
SOL_ESCRITURA = r'''
def escritura(ch):
    n = unicodedata.name(ch, "")
    return n.split()[0] if n else "?"

def palabra_mixta(w):
    return len({escritura(c) for c in w if c.isalpha()} & {"LATIN", "CYRILLIC", "GREEK"}) >= 2
'''
SOL_MOJIBAKE = r'''
MOJI_RE = re.compile(r"[\u00c2-\u00f4][\u0080-\u00bf]{1,3}")

def parece_mojibake(t):
    for m in MOJI_RE.finditer(t):
        g = m.group()
        for n in range(len(g), 1, -1):                       # prueba prefijos: ¿decodifican como UTF-8 válido?
            try:
                g[:n].encode("latin-1").decode("utf-8"); return True
            except UnicodeError:
                continue
    return "â€" in t                                        # firma típica de cp1252 (comillas, guiones)

def arregla_mojibake(t):
    for _ in range(3):                                       # el doble mojibake necesita 2 pasadas
        if not parece_mojibake(t):
            break
        for enc in ("latin-1", "cp1252"):
            try:
                nuevo = t.encode(enc).decode("utf-8")
            except UnicodeError:
                continue
            if nuevo != t:
                t = nuevo; break
        else:
            break
    return t
'''
SOL_AUDIT = r'''
ZW_CHARS = set("\u200b\u200c\u200d\u2060\ufeff")
BIDI_CHARS = set("\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")

def audit_doc(t):
    palabras = regex.findall(r"\w+", t)
    return {"chars": len(t), "graphemes": len(regex.findall(r"\X", t)), "bytes": len(t.encode("utf-8")),
            "no_nfc": t != unicodedata.normalize("NFC", t), "zero_width": sum(c in ZW_CHARS for c in t),
            "bidi": sum(c in BIDI_CHARS for c in t), "nbsp": sum(unicodedata.category(c) == "Zs" and c != " " for c in t),
            "ancho_completo": sum("\uff01" <= c <= "\uff5e" for c in t), "mixed_words": sum(palabra_mixta(w) for w in palabras),
            "mojibake": parece_mojibake(t), "control": sum(unicodedata.category(c) == "Cc" and c not in "\n\t\r" for c in t),
            "fffd": t.count("\ufffd")}
'''
SOL_NORMALIZAR = r'''
ZW_QUITAR = set("\u200b\u2060\ufeff")
CONFUSABLES = {"\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p", "\u0441": "c", "\u0445": "x", "\u0456": "i",
               "\u03bf": "o", "\u03b1": "a", "\u0455": "s", "\u0458": "j"}

def plegar_ancho(t):
    return "".join(chr(ord(c) - 0xFEE0) if "\uff01" <= c <= "\uff5e" else c for c in t)

def normalizar(t, nfkc=False):
    t = arregla_mojibake(t)
    t = unicodedata.normalize("NFKC" if nfkc else "NFC", t)
    t = plegar_ancho(t)
    t = "".join(c for c in t if c not in ZW_QUITAR and c not in BIDI_CHARS)
    t = re.sub(r"(?<=[A-Za-z0-9])[\u200c\u200d](?=[A-Za-z0-9])", "", t)          # ZWJ/ZWNJ solo se quitan dentro de palabras ASCII
    t = "".join(" " if unicodedata.category(c) == "Zs" else c for c in t)
    t = "".join(c for c in t if not (unicodedata.category(c) == "Cc" and c not in "\n\t\r"))
    return regex.sub(r"\w+", lambda m: "".join(CONFUSABLES.get(c, c) for c in m.group()) if palabra_mixta(m.group()) else m.group(), t)
'''
SOL_DETECTORES = r'''
DETECTORES = {"nfd": lambda a: a["no_nfc"], "zero_width": lambda a: a["zero_width"] > 0, "homoglifo": lambda a: a["mixed_words"] > 0,
              "mojibake": lambda a: a["mojibake"], "nbsp": lambda a: a["nbsp"] > 0, "ancho_completo": lambda a: a["ancho_completo"] > 0,
              "bidi": lambda a: a["bidi"] > 0}
'''
SOL_NDCG = r'''
naive = lambda t: re.findall(r"\w+", t.lower())          # tokenizador léxico SIN normalizar: expone el efecto

def ndcg_variante(docs_v):
    dd = [d for d in docs_v if d["lang"] != "code"]; qs = [q for q in queries if q["lang"] != "code"]
    bm = BM25().fit([naive(d["text"]) for d in dd], [d["id"] for d in dd])
    run = {q["qid"]: bm.search(naive(q["text"]), 10) for q in qs}
    return evaluate(run, {q["qid"]: qrels[q["qid"]] for q in qs})["ndcg"]
'''

pb.md(pb.badge() + r"""

# Proyecto · Auditoría Unicode del corpus Políglota + normalizador
**Módulo 01 · Texto como bytes: Unicode, UTF-8, normalización**

| | |
|---|---|
| **Nivel** | 🟢 Básico |
| **Duración** | ≈ 1.5 h |
| **GPU** | Ninguna (CPU) |
| **Entregable** | funciones `audit_doc`, `normalizar` y el informe `poliglota_unicode.json` |
""")

pb.md(r"""
## Contexto de negocio
Políglota Labs va a ingerir documentación de muchas fuentes (wikis, PDFs convertidos, emails, páginas web). Tu CTO ha visto cosas raras en las pruebas: búsquedas que no encuentran «canción» aunque está en el documento, palabras que parecen iguales y no lo son, texto con «Ã³» en vez de «ó»… Te pide **una auditoría Unicode del corpus** y **un normalizador** que lo deje en una forma canónica *antes* de tokenizar y de indexar.

Como el corpus real (Wikipedia) está bastante limpio, usaremos un **inyector de ruido con verdad conocida** (`contaminar`): sabemos exactamente qué documentos ensuciamos y de qué manera, así que podemos medir **precisión y recall de tus detectores** y **qué fracción del daño repara tu normalizador**.

**Conexión.** *Anterior (módulo 00):* usas `carga_corpus`, las métricas y el BM25 que construiste. *Siguiente (módulo 02):* tu `normalizar` será el primer paso antes de entrenar el BPE propio sobre el corpus; la calidad de la normalización determina el vocabulario de fusiones.
""")

pb.md(r"""
## Dataset
Corpus Políglota (`carga_corpus`, módulo 00): Wikipedia ES/EN + código Python, con cadena **oficial → espejo → sintético** (la celda de carga imprime la fuente). El inyector solo contamina documentos ES/EN (el código tiene reglas propias).
""")

pb.md(r"""
## Entregables y criterios de evaluación (rúbrica)

| # | Criterio | Umbral |
|---|---|---|
| R1 | `escritura` / `palabra_mixta` pasan sus tests (homoglifos latín/cirílico/griego, sin falsos positivos en palabras monoescritura) | tests ✅ |
| R2 | `parece_mojibake` y `arregla_mojibake` pasan sus tests (incluido el **doble mojibake** y el caso de falso positivo «é + NBSP») | tests ✅ |
| R3 | `audit_doc` devuelve las 12 claves y cuenta correctamente en los casos de prueba (emoji de familia, NFD, invisibles) | tests ✅ |
| R4 | `normalizar` pasa sus tests (idempotente; conserva el ZWJ de los emojis; quita invisibles/bidi dentro de palabras; arregla homoglifos y ancho completo) | tests ✅ |
| R5 | **Detección** por tipo de ruido sobre el corpus contaminado | recall ≥ **0.95** y precisión ≥ **0.90** en cada tipo; documentos limpios marcados ≤ **2 %** |
| R6 | **Reparación**: `normalizar(sucio) == normalizar(original)` en los documentos contaminados; idempotencia en todo el corpus; documentos limpios que cambian más que NFC | recuperación ≥ **0.95**; idempotencia = 100 %; limpios sin cambios ≥ **0.99** |
| R7 | **Efecto en búsqueda** (BM25 con tokenizador léxico sin normalizar, consultas ES/EN): nDCG@10 limpio vs sucio vs normalizado | la contaminación baja el nDCG ≥ **0.03** y el corpus normalizado queda a ≤ **0.01** del limpio |
| R8 | **Efecto en costo de tokens** (GPT-2, 150 docs): tokens(sucio) / tokens(normalizado) | ≥ **1.02** (si `tiktoken` no está disponible, se omite) |
| R9 | `poliglota_unicode.json` guardado con las claves requeridas | ✅ |

Umbrales calibrados con **lo que mide la solución de referencia** (corpus **sintético**, `FAST_DEV_RUN=True`, semilla 42, `tasa=0.3`): 93 documentos contaminados; recall = precisión = **1.00** en los 7 tipos; recuperación **93/93**; limpios sin cambios **400/400**; nDCG@10 limpio **0.955**, sucio **0.894**, normalizado **0.955**; tokens sucio/normalizado **1.049**. Los umbrales llevan margen. Con Wikipedia **real** no pudimos medir la solución en el entorno de autoría (Hugging Face bloqueado): es esperable que la precisión baje, porque Wikipedia contiene de forma natural *ZWNJ*, NBSP, mezclas de escrituras legítimas, etc.; en ese caso **inspecciona los «falsos positivos»**: suelen ser anomalías reales, no errores tuyos.
""")

pb.md("## 0. Preparación (celdas dadas)")
pb.code(r'''
!pip install -q numpy pandas matplotlib regex tiktoken rank_bm25
''')
pb.code(r'''
import json, math, pathlib, random, re, sys, time, unicodedata, collections
import numpy as np, pandas as pd, regex
import matplotlib.pyplot as plt

SEED = 42
random.seed(SEED); np.random.seed(SEED)
FAST_DEV_RUN = True
CHECKS: dict = {}

def chequea(nombre, fn):
    """Ejecuta fn() y registra ✅/❌/⏳ sin romper «Ejecutar todo»."""
    try:
        fn(); CHECKS[nombre] = True; print("✅", nombre)
    except NotImplementedError as e:
        CHECKS[nombre] = None; print("⏳ pendiente:", nombre, "→", e)
    except AssertionError as e:
        CHECKS[nombre] = False; print("❌", nombre, "→", e)
    except Exception as e:  # noqa: BLE001
        CHECKS[nombre] = False; print("💥", nombre, "→", type(e).__name__, e)
''')
_c = src_corpus_cells()
pb.code("# ── carga_corpus (1/3) ──\n" + _c[0])
pb.code("# ── carga_corpus (2/3) ──\n" + _c[1])
pb.code("# ── carga_corpus (3/3) ──\n" + _c[2])
pb.code("# ── Métricas canónicas ──\n" + SRC_METRICS)
pb.code("# ── BM25 (módulo 00) ──\n" + SRC_BM25)
pb.code(SRC_GPT2)
pb.code(GIVEN_CONTAMINAR + "\n" + GIVEN_DETECCION)
pb.code(r'''
corpus = carga_corpus(fast_dev=FAST_DEV_RUN)
docs, queries, qrels, source = corpus["docs"], corpus["queries"], corpus["qrels"], corpus["source"]
sucios, verdad = contaminar(docs, tasa=0.3, seed=SEED)
orig = {d["id"]: d for d in docs}
print(f"source = {source!r} | {len(docs)} docs | {len(verdad)} contaminados:", dict(collections.Counter(verdad.values())))
ejemplo = next(i for i, t in verdad.items() if t == "homoglifo")
a, b = orig[ejemplo]["text"], next(d for d in sucios if d["id"] == ejemplo)["text"]
print("\nEjemplo de homoglifo →", [(x, y) for x, y in zip(a.split(), b.split()) if x != y][:2], "(¡se ven iguales!)")
''')

pb.md(r"""
## TODO 1 · Escrituras y palabras mixtas
Implementa `escritura(ch)` (la «escritura» aproximada de un carácter: la **primera palabra de su nombre Unicode**, `LATIN`, `CYRILLIC`, `GREEK`…; `"?"` si no tiene nombre) y `palabra_mixta(w)`: `True` si las **letras** de la palabra pertenecen a **≥ 2** escrituras distintas entre `{LATIN, CYRILLIC, GREEK}`.

""" + pista(1, "`unicodedata.name(ch, '')` devuelve p. ej. `'CYRILLIC SMALL LETTER A'`. Toma la primera palabra con `.split()[0]`.") + "\n\n" + pista(2, "Construye el conjunto `{escritura(c) for c in w if c.isalpha()}` y comprueba que su intersección con `{'LATIN','CYRILLIC','GREEK'}` tiene al menos 2 elementos."))
pb.code(r'''
def escritura(ch):
    # TODO
    raise NotImplementedError("TODO 1a: implementa escritura")

def palabra_mixta(w):
    # TODO
    raise NotImplementedError("TODO 1b: implementa palabra_mixta")

def test_mixta():
    assert escritura("a") == "LATIN" and escritura("а") == "CYRILLIC" and escritura("ο") == "GREEK"
    assert not palabra_mixta("paypal") and palabra_mixta("pаypal") and palabra_mixta("aοb")
    assert not palabra_mixta("привет") and not palabra_mixta("ñandú") and not palabra_mixta("123")
chequea("R1 palabra_mixta", test_mixta)
''')

pb.md(r"""
## TODO 2 · Mojibake: detectar y reparar
`parece_mojibake(t)` debe ser `True` cuando el texto contiene secuencias de **UTF-8 leído como Latin-1/cp1252** (`Ã³`, `Ã±`, `Â¿`, `â€`…) y **`False`** en texto sano, incluido el caso engañoso «é + NBSP» (`"qué es"`: `é`=U+00E9 y NBSP=U+00A0 están en los rangos de «mojibake» pero **no** forman UTF-8 válido). `arregla_mojibake(t)` revierte el error (`encode('latin-1')` o `'cp1252'` + `decode('utf-8')`); debe poder con el **doble mojibake** y dejar intacto el texto sano.

""" + pista(1, "Un patrón candidato: un carácter en `U+00C2…U+00F4` seguido de 1–3 caracteres en `U+0080…U+00BF`. Pero un candidato **solo cuenta** si al pasarlo por `.encode('latin-1').decode('utf-8')` no lanza error (prueba prefijos del candidato, de largo a corto).") + "\n\n" + pista(2, "`arregla_mojibake`: repite hasta 3 veces: si `parece_mojibake`, prueba `for enc in ('latin-1', 'cp1252')` con `t.encode(enc).decode('utf-8')` dentro de un `try/except UnicodeError` y quédate con el primer resultado distinto. Añade la firma `'â€'` (comillas/guiones en cp1252) a la detección."))
pb.code(r'''
def parece_mojibake(t):
    # TODO
    raise NotImplementedError("TODO 2a: implementa parece_mojibake")

def arregla_mojibake(t):
    # TODO
    raise NotImplementedError("TODO 2b: implementa arregla_mojibake")

def test_mojibake():
    assert parece_mojibake("CanciÃ³n") and parece_mojibake("Â¿quÃ©?") and not parece_mojibake("canción ¿qué?")
    assert not parece_mojibake("qué es"), "falso positivo: é + NBSP no es mojibake (no es UTF-8 válido)"
    assert arregla_mojibake("CanciÃ³n") == "Canción" and arregla_mojibake("hola") == "hola"
    doble = "Canción".encode().decode("latin-1").encode().decode("latin-1")
    assert arregla_mojibake(doble) == "Canción", "doble mojibake: necesita 2 pasadas"
    assert arregla_mojibake("“hola".encode().decode("cp1252")) == "“hola"
chequea("R2 mojibake", test_mojibake)
''')

pb.md(r"""
## TODO 3 · Auditoría de un documento
Implementa `audit_doc(t)` → `dict` con estas 12 claves: `chars` (code points), `graphemes` (con `regex` y `\X`), `bytes` (UTF-8), `no_nfc` (¿el texto **no** está en NFC?), `zero_width` (nº de caracteres de `ZW_CHARS`), `bidi` (nº de `BIDI_CHARS`), `nbsp` (nº de separadores `Zs` distintos del espacio normal), `ancho_completo` (nº de caracteres `U+FF01…U+FF5E`), `mixed_words` (nº de palabras `\w+` mixtas), `mojibake` (bool), `control` (nº de caracteres de categoría `Cc` salvo `\n`, `\t`, `\r`) y `fffd` (nº de `U+FFFD`).

""" + pista(1, "Casi todo son cuentas de caracteres con `sum(c in CONJUNTO for c in t)` o con `unicodedata.category(c)`. Las palabras salen de `regex.findall(r'\\w+', t)`.") + "\n\n" + pista(2, "`no_nfc = t != unicodedata.normalize('NFC', t)`; `graphemes = len(regex.findall(r'\\X', t))`; `nbsp = sum(unicodedata.category(c) == 'Zs' and c != ' ' for c in t)`."))
pb.code(r'''
ZW_CHARS = set("​‌‍⁠﻿")                     # ZWSP, ZWNJ, ZWJ, WORD JOINER, BOM
BIDI_CHARS = set("‪‫‬‭‮⁦⁧⁨⁩")   # embeddings/overrides/isolates (Trojan Source)

def audit_doc(t):
    # TODO: devuelve el dict con las 12 claves
    raise NotImplementedError("TODO 3: implementa audit_doc")

CLAVES_AUDIT = {"chars", "graphemes", "bytes", "no_nfc", "zero_width", "bidi", "nbsp", "ancho_completo", "mixed_words", "mojibake", "control", "fffd"}
def test_audit():
    a = audit_doc("👨‍👩‍👧‍👦")
    assert set(a) == CLAVES_AUDIT, f"claves: {set(a) ^ CLAVES_AUDIT}"
    assert (a["chars"], a["graphemes"], a["bytes"], a["zero_width"]) == (7, 1, 25, 3)
    assert audit_doc("é")["no_nfc"] and not audit_doc("é")["no_nfc"]
    assert audit_doc("a​b")["zero_width"] == 1 and audit_doc("a‮b")["bidi"] == 1 and audit_doc("a b")["nbsp"] == 1
    assert audit_doc("ＡＢｃ")["ancho_completo"] == 3 and audit_doc("pаypal")["mixed_words"] == 1 and audit_doc("CanciÃ³n")["mojibake"]
chequea("R3 audit_doc", test_audit)
''')

pb.md(r"""
## TODO 4 · El normalizador
Implementa `normalizar(t, nfkc=False)`. Reglas (en este orden):

1. **Arregla mojibake** (`arregla_mojibake`).
2. **NFC** (o NFKC si `nfkc=True`).
3. **Pliega el ancho completo** (`U+FF01…U+FF5E` → ASCII: `chr(ord(c) - 0xFEE0)`) — mejor que NFKC para todo: es un martillo menos grande.
4. **Quita** los caracteres de `ZW_QUITAR` (`U+200B`, `U+2060`, `U+FEFF`) y los de `BIDI_CHARS`.
5. Quita **ZWJ/ZWNJ** (`U+200D`, `U+200C`) **solo** cuando están entre dos alfanuméricos **ASCII** (los de los emojis y de las escrituras índicas/persa se **conservan**).
6. Convierte cualquier separador `Zs` (NBSP, espacio fino, ideográfico…) en un espacio normal `" "`, y elimina controles `Cc` salvo `\n \t \r`.
7. En cada palabra **mixta** (`palabra_mixta`), sustituye los homoglifos por su letra latina con el diccionario `CONFUSABLES`.

Debe ser **idempotente** (`normalizar(normalizar(x)) == normalizar(x)`) y dejar **intacto** el texto sano salvo la NFC.

""" + pista(1, "Encadena transformaciones simples sobre `t`; para el paso 5 usa `re.sub(r'(?<=[A-Za-z0-9])[\\u200c\\u200d](?=[A-Za-z0-9])', '', t)`; para el 7, `regex.sub(r'\\w+', f, t)` con una función `f` que reciba la coincidencia.") + "\n\n" + pista(2, "Paso 7: `lambda m: ''.join(CONFUSABLES.get(c, c) for c in m.group()) if palabra_mixta(m.group()) else m.group()`. Paso 6: `''.join(' ' if unicodedata.category(c) == 'Zs' else c for c in t)`."))
pb.code(r'''
ZW_QUITAR = set("​⁠﻿")
CONFUSABLES = {"а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "і": "i",
               "ο": "o", "α": "a", "ѕ": "s", "ј": "j"}

def plegar_ancho(t):
    # TODO: U+FF01..U+FF5E -> ASCII
    raise NotImplementedError("TODO 4a: implementa plegar_ancho")

def normalizar(t, nfkc=False):
    # TODO: aplica las 7 reglas en orden
    raise NotImplementedError("TODO 4b: implementa normalizar")

def test_normalizar():
    assert normalizar("é") == "é" and normalizar("１２３ ＡＢＣ") == "123 ABC"
    assert normalizar("ho​la mundo") == "hola mundo" and normalizar("a‮b") == "ab"
    assert normalizar("pаypal") == "paypal" and normalizar("привет") == "привет"
    assert normalizar("👨‍👩‍👧") == "👨‍👩‍👧", "el ZWJ de los emojis se conserva"
    assert normalizar("ab‍cd") == "abcd", "ZWJ entre letras ASCII se elimina"
    assert normalizar("CanciÃ³n") == "Canción"
    for t in ("é​ ＡＢ", "pаypal x", "CanciÃ³n Â¿", "hola mundo"):
        assert normalizar(normalizar(t)) == normalizar(t), f"no idempotente en {t!r}"
    assert normalizar("½ ² ﬁ") == "½ ² ﬁ", "sin nfkc, la compatibilidad se conserva"
chequea("R4 normalizar", test_normalizar)
''')

pb.md(r"""
## TODO 5 · ¿Detecta tu auditoría lo que inyectamos?
Rellena `DETECTORES`: un `dict` `tipo → función(audit) → bool` para los 7 tipos (`nfd`, `zero_width`, `homoglifo`, `mojibake`, `nbsp`, `ancho_completo`, `bidi`) usando solo las claves de `audit_doc`. La función dada `evaluar_deteccion` calcula **recall** (¿detectas los contaminados?) y **precisión frente a los limpios** (¿marcas documentos sin inyección?).

""" + pista(1, "Cada detector es una condición sobre una clave: p. ej. `nfd` ⇒ `a['no_nfc']`; `zero_width` ⇒ `a['zero_width'] > 0`.") + "\n\n" + pista(2, "`homoglifo` ⇒ `a['mixed_words'] > 0`; `ancho_completo` ⇒ `a['ancho_completo'] > 0`; `mojibake` ⇒ `a['mojibake']`."))
pb.code(r'''
DETECTORES = {}   # TODO: {"nfd": lambda a: ..., ...} con los 7 tipos

try:
    audits = {d["id"]: audit_doc(d["text"]) for d in sucios}
    assert set(DETECTORES) == set(TIPOS), f"faltan detectores: {set(TIPOS) - set(DETECTORES)}"
    det = evaluar_deteccion(audits, verdad, DETECTORES)
    display(det.round(3))
except NotImplementedError as e:
    print("⏳ pendiente:", e)
except AssertionError as e:
    print("⏳", e)
''')

pb.md(r"""
## TODO 6 · ¿Repara el normalizador?
Calcula (a) la **tasa de recuperación**: fracción de documentos contaminados cuyo `normalizar(sucio)` es **igual** a `normalizar(original)`; (b) la **idempotencia** en todo el corpus sucio; (c) la fracción de documentos **limpios** que `normalizar` deja igual que su NFC. Guárdalos en `REPARACION = {"recuperacion": ..., "idempotente": bool, "limpios_intactos": ...}`.

""" + pista(1, "Itera sobre `sucios` y compara con `orig[d['id']]['text']`. Para los limpios usa `docs` (el corpus sin contaminar).") + "\n\n" + pista(2, "`recuperacion = mean(normalizar(d['text']) == normalizar(orig[d['id']]['text']) for d in sucios if d['id'] in verdad)`; idempotente con `all(...)`; limpios con `unicodedata.normalize('NFC', t)`."))
pb.code(r'''
REPARACION = {}
def calcula_reparacion():
    # TODO: devuelve {"recuperacion": float, "idempotente": bool, "limpios_intactos": float}
    raise NotImplementedError("TODO 6: implementa calcula_reparacion")

try:
    REPARACION = calcula_reparacion(); print(REPARACION)
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''')

pb.md(r"""
## TODO 7 · Impacto en búsqueda y en costo de tokens
**(a) Búsqueda.** Con el BM25 del módulo 00 y un tokenizador léxico **sin** normalizar (`naive`), calcula el nDCG@10 (consultas ES/EN) sobre tres versiones del corpus: `docs` (limpio), `sucios` y `sucios` normalizados. Rellena `NDCG = {"limpio":…, "sucio":…, "normalizado":…}`.
**(b) Tokens.** Con GPT-2 (`get_gpt2_encoding()`), cuenta los tokens de los primeros 150 documentos no-código de `sucios` **antes y después** de `normalizar`, y guarda `TOKENS = {"sucio": …, "normalizado": …, "ratio": …}`.

""" + pista(1, "Reutiliza `BM25`, `evaluate` y `qrels`. Indexa solo documentos y consultas que no sean `code`. El tokenizador léxico es `re.findall(r'\\w+', t.lower())`.") + "\n\n" + pista(2, "`variante = [dict(d, text=normalizar(d['text'])) for d in sucios]`; después una función `ndcg_variante(docs_v)` que construya el índice, busque las consultas y llame a `evaluate(...)['ndcg']`."))
pb.code(r'''
naive = lambda t: re.findall(r"\w+", t.lower())          # tokenizador léxico SIN normalizar: expone el efecto

def ndcg_variante(docs_v):
    # TODO: BM25 sobre docs_v (sin código) + consultas ES/EN -> nDCG@10
    raise NotImplementedError("TODO 7a: implementa ndcg_variante")

NDCG, TOKENS = {}, {}
try:
    NDCG = {"limpio": ndcg_variante(docs), "sucio": ndcg_variante(sucios),
            "normalizado": ndcg_variante([dict(d, text=normalizar(d["text"])) for d in sucios])}
    print({k: round(v, 4) for k, v in NDCG.items()})
    fig, ax = plt.subplots(figsize=(5.5, 3.4)); ax.bar(list(NDCG), list(NDCG.values()), color=["#2CA02C", "#D62728", "#1F6FEB"])
    ax.set_ylim(0, 1.05); ax.set_ylabel("nDCG@10"); ax.set_title(f"Ruido Unicode y normalización (corpus {source})"); plt.tight_layout(); plt.show()
except NotImplementedError as e:
    print("⏳ pendiente:", e)

enc = get_gpt2_encoding()
try:
    if enc is None:
        print("tiktoken no disponible: R8 se omite")
    else:
        muestra = [d for d in sucios if d["lang"] != "code"][:150]
        ts = sum(len(enc.encode(d["text"])) for d in muestra); tn = sum(len(enc.encode(normalizar(d["text"]))) for d in muestra)
        TOKENS = {"sucio": ts, "normalizado": tn, "ratio": ts / tn}; print(TOKENS)
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''')

pb.md("> 👀 **Qué debes observar.** Tres barras: **limpio** (verde) y **normalizado** (azul) deben quedar prácticamente a la misma altura, y **sucio** (rojo) varios puntos por debajo (la solución mide 0.955 / 0.894 / 0.955 con corpus sintético). Si la azul no alcanza a la verde, tu `normalizar` deja algún tipo de ruido sin reparar: vuelve a la tabla de TODO 5 y mira qué tipo tiene recall bajo. En la salida de tokens, un ratio > 1 es el sobrecoste en tokens que el ruido Unicode añade a la factura de un LLM.")

pb.md(r"""
## TODO 8 · Informe
Guarda `poliglota_unicode.json` con las claves `source`, `n_docs`, `n_contaminados`, `deteccion` (la tabla de TODO 5 como dict), `reparacion`, `ndcg`, `tokens`, `bytes_por_char` (por idioma, del corpus **limpio**, usando tu `audit_doc`) y `version_unicode` (`unicodedata.unidata_version`).
""")
pb.code(r'''
CLAVES_INFORME = ["source", "n_docs", "n_contaminados", "deteccion", "reparacion", "ndcg", "tokens", "bytes_por_char", "version_unicode"]

def guardar_informe(path="poliglota_unicode.json"):
    # TODO: construye el dict con CLAVES_INFORME, guárdalo como JSON y devuélvelo
    raise NotImplementedError("TODO 8: implementa guardar_informe")

def test_informe():
    d = guardar_informe()
    assert all(k in d for k in CLAVES_INFORME), f"faltan: {[k for k in CLAVES_INFORME if k not in d]}"
    assert json.loads(pathlib.Path("poliglota_unicode.json").read_text())["source"] == source
chequea("R9 informe", test_informe)
''')

pb.md("## Rúbrica: comprobación automática")
pb.code(r'''
def rubrica():
    for n, e in CHECKS.items():
        print({True: "✅", False: "❌", None: "⏳"}[e], n)
    if DETECTORES and set(DETECTORES) == set(TIPOS):
        try:
            det = evaluar_deteccion({d["id"]: audit_doc(d["text"]) for d in sucios}, verdad, DETECTORES)
            limpios_marcados = sum(any(f(audit_doc(d["text"])) for f in DETECTORES.values()) for d in docs) / len(docs)
            ok = bool((det["recall"] >= 0.95).all() and (det["precisión (vs limpios)"] >= 0.90).all() and limpios_marcados <= 0.02)
            print("✅" if ok else "❌", f"R5 detección: recall mín {det['recall'].min():.2f} (≥ 0.95), precisión mín {det['precisión (vs limpios)'].min():.2f} (≥ 0.90), limpios marcados {limpios_marcados:.1%} (≤ 2 %)")
        except NotImplementedError:
            print("⏳ R5 detección")
    if REPARACION:
        ok = REPARACION["recuperacion"] >= 0.95 and REPARACION["idempotente"] and REPARACION["limpios_intactos"] >= 0.99
        print("✅" if ok else "❌", f"R6 reparación: {REPARACION}")
    if NDCG:
        ok = NDCG["limpio"] - NDCG["sucio"] >= 0.03 and NDCG["limpio"] - NDCG["normalizado"] <= 0.01
        print("✅" if ok else "❌", f"R7 búsqueda: {({k: round(v, 3) for k, v in NDCG.items()})} (caída ≥ 0.03; normalizado a ≤ 0.01 del limpio)")
    if TOKENS:
        print("✅" if TOKENS["ratio"] >= 1.02 else "❌", f"R8 tokens sucio/normalizado = {TOKENS['ratio']:.3f} (≥ 1.02)")
    print("\n(Con corpus REAL los umbrales de R5–R8 no están calibrados: ver la nota de la rúbrica.)" if source == "real" else "")
rubrica()
''')

pb.md(r"""
## Retos extra (nivel experto)
1. **Esqueleto de confusables completo.** Descarga `confusables.txt` de Unicode (UTS #39) y sustituye `CONFUSABLES` por el mapeo oficial *skeleton*; mide el cambio en falsos positivos sobre Wikipedia real.
2. **NFKC selectivo.** Compara `normalizar(nfkc=True)` con tu versión: ¿qué caracteres de tu corpus cambian? Haz una lista de los que destruirían información (`²`, `ﬁ`, `½`).
3. **Detector de *tag characters*** (`U+E0000–E007F`) y de caracteres de la categoría `Cf`: añade ambos a la auditoría y al normalizador, con tests.
4. **Normalización a nivel de grafemas** para truncado seguro de UI: implementa `trunca_grafemas(t, n)` y compárala con `t[:n]` sobre textos con emojis ZWJ.
5. **Mide el efecto sobre un tokenizer real:** tokens/carácter de GPT-2 y de otro encoding (`cl100k_base` si lo puedes descargar) sobre el corpus sucio vs normalizado por idioma.
""")

pb.md(r"""
## Reflexión
* Tu normalizador elimina ZWJ solo entre letras ASCII. ¿Qué rompería eliminarlo siempre? ¿Y qué rompe **no** eliminar el ZWSP en un corpus de entrenamiento?
* ¿Dónde pondrías la normalización en el pipeline de Políglota (ingesta, tokenizer, consulta)? ¿Qué pasa si indexas con una función y consultas con otra?
* ¿Qué decisiones de este módulo condicionan el **vocabulario** del BPE que entrenarás en el módulo 02 (forma de normalización, invisibles, mojibake residual)?
""")

pb.md(r"""
---
# ⛔ SPOILER — intenta resolverlo primero
Debajo está la solución de referencia, completa y ejecutable. Si «Ejecutar todo» llega hasta aquí, estas celdas **sobrescriben** tus funciones con las de referencia.
""")
pb.code("# ── SOLUCIÓN · TODO 1 ──" + SOL_ESCRITURA)
pb.code("# ── SOLUCIÓN · TODO 2 ──" + SOL_MOJIBAKE)
pb.code("# ── SOLUCIÓN · TODO 3 ──" + SOL_AUDIT)
pb.code("# ── SOLUCIÓN · TODO 4 ──" + SOL_NORMALIZAR)
pb.code("# ── SOLUCIÓN · TODO 5 ──" + SOL_DETECTORES + r'''
audits = {d["id"]: audit_doc(d["text"]) for d in sucios}
det = evaluar_deteccion(audits, verdad, DETECTORES)
display(det.round(3))
''')
pb.code(r'''
# ── SOLUCIÓN · TODO 6, 7, 8 ──
def calcula_reparacion():
    rec = np.mean([normalizar(d["text"]) == normalizar(orig[d["id"]]["text"]) for d in sucios if d["id"] in verdad])
    idem = all(normalizar(normalizar(d["text"])) == normalizar(d["text"]) for d in sucios)
    intactos = np.mean([normalizar(d["text"]) == unicodedata.normalize("NFC", d["text"]) for d in docs])
    return {"recuperacion": float(rec), "idempotente": bool(idem), "limpios_intactos": float(intactos)}
REPARACION = calcula_reparacion(); print(REPARACION)
''')
pb.code(SOL_NDCG + r'''
NDCG = {"limpio": ndcg_variante(docs), "sucio": ndcg_variante(sucios), "normalizado": ndcg_variante([dict(d, text=normalizar(d["text"])) for d in sucios])}
print({k: round(v, 4) for k, v in NDCG.items()})
enc = get_gpt2_encoding()
if enc is not None:
    muestra = [d for d in sucios if d["lang"] != "code"][:150]
    ts = sum(len(enc.encode(d["text"])) for d in muestra); tn = sum(len(enc.encode(normalizar(d["text"]))) for d in muestra)
    TOKENS = {"sucio": ts, "normalizado": tn, "ratio": ts / tn}; print(TOKENS)

def guardar_informe(path="poliglota_unicode.json"):
    bpc = {l: sum(audit_doc(d["text"])["bytes"] for d in docs if d["lang"] == l) / sum(audit_doc(d["text"])["chars"] for d in docs if d["lang"] == l)
           for l in ("es", "en", "code")}
    d = {"source": source, "n_docs": len(docs), "n_contaminados": len(verdad), "deteccion": det.round(4).to_dict(), "reparacion": REPARACION,
         "ndcg": NDCG, "tokens": TOKENS, "bytes_por_char": bpc, "version_unicode": unicodedata.unidata_version}
    pathlib.Path(path).write_text(json.dumps(d, indent=2, ensure_ascii=False, default=float))
    return d
guardar_informe()
for nombre, fn in [("R1 palabra_mixta", test_mixta), ("R2 mojibake", test_mojibake), ("R3 audit_doc", test_audit), ("R4 normalizar", test_normalizar), ("R9 informe", test_informe)]:
    chequea(nombre, fn)
rubrica()
''')
pb.md(caja("📌 Valores de referencia de la solución", r"""
Corpus **sintético**, `FAST_DEV_RUN=True`, semilla 42, `tasa=0.3`: 93 documentos contaminados; recall = precisión = 1.00 en los 7 tipos; recuperación 93/93; nDCG@10 limpio 0.955 / sucio 0.894 / normalizado 0.955; tokens GPT-2 sucio/normalizado 1.049. Con datos **reales** tus números serán distintos (no pudimos medirlos en el entorno de autoría).
"""))

pb.save(str(ROOT.parent / PPATH))
