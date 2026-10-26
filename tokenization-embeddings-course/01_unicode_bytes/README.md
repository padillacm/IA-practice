# Módulo 01 · Texto como bytes: Unicode, UTF-8, normalización

**Nivel:** 🟢 Básico · **Duración:** ≈ 4 h (lección ≈ 2.5 h + proyecto ≈ 1.5 h) · **Cómputo:** CPU (0 unidades de Colab)

| Archivo | Contenido |
|---|---|
| `01_unicode_bytes.ipynb` | Lección: grafemas vs code points vs bytes, UTF-8 a mano (verificado en todo el espacio Unicode y con fuzzing), UTF-16/32 y `str` en CPython, NFC/NFD/NFKC/NFKD (NFD a mano), homoglifos e invisibles, bytes por carácter en 12 idiomas, bits por byte, mojibake |
| `01_proyecto_unicode_bytes.ipynb` | Proyecto: auditoría Unicode del corpus Políglota (con inyector de ruido de verdad conocida) + normalizador `normalizar` + informe `poliglota_unicode.json` |
| `assets/` | Carpeta (con `.gitkeep`) para `M01-IMG-01.png` … `M01-IMG-04.png` (celdas Gemini) |

## Objetivos
1. Distinguir y contar grafemas, code points y bytes; saber qué mide `len()` en Python, JS y Go/Rust.
2. Implementar UTF-8 (codificación y decodificación estricta) y verificarlo contra Python.
3. Entender UTF-16/32, pares sustitutos y la representación de `str` en CPython (PEP 393).
4. Aplicar y medir NFC/NFD/NFKC/NFKD; implementar NFD; ver su efecto en bytes, tokens (GPT-2) y búsqueda (BM25).
5. Detectar homoglifos, invisibles y controles bidi; entender Trojan Source y «ASCII smuggling».
6. Cuantificar bytes y tokens por idioma (12 idiomas) y relacionarlo con compresión y tipología lingüística.
7. Diagnosticar y reparar mojibake; elegir el manejador de errores correcto.

## Prerrequisitos
Módulo 00 (`carga_corpus`, métricas canónicas, BM25). Se reutilizan copiando las celdas.

## Convenciones que este módulo aporta al resto del curso
* **`get_gpt2_encoding()`** (celda en lección y proyecto): `tiktoken.get_encoding("gpt2")` → espejo en GitHub (`graykode/gpt-2-Pytorch`) verificado con los SHA-256 que exige `tiktoken` → `None`. Útil cuando el CDN de OpenAI está bloqueado.
* **`normalizar(t)`** (solución del proyecto): NFC + arreglo de mojibake + pliegue de ancho completo + invisibles/bidi + espacios + homoglifos en palabras mixtas. El módulo 02 lo usa como primer paso antes de entrenar BPE.
* **Inyector de ruido `contaminar(docs, tasa, seed)`** con verdad conocida: reutilizable para probar robustez (módulo 05).

## Datos
Corpus Políglota del módulo 00 (Wikipedia ES/EN + código Python; cadena oficial → espejo → sintético). Frases paralelas escritas a mano (12 idiomas) para la tabla de bytes/tokens.

## Estado de pruebas (entorno de autoría)
Ejecutado de principio a fin con `nbclient` con el corpus **sintético** (+ funciones reales de la stdlib); Hugging Face, Wikipedia y `unicode.org` estaban bloqueados. GPT-2 se obtuvo del espejo de GitHub (hashes verificados). Los umbrales de la rúbrica están calibrados con la solución sobre datos sintéticos.

## Lecturas
UAX #15 (normalización), UAX #29 (grafemas), UTS #39 (seguridad), RFC 3629 (UTF-8), Boucher & Anderson 2021 (Trojan Source, arXiv:2111.00169), Petrov et al. 2023 (arXiv:2305.15425), Ahia et al. 2023 (arXiv:2305.13707), Mielke et al. 2021 (arXiv:2112.10508).

## Siguiente módulo
**02 · BPE desde cero** — Byte Pair Encoding (Gage 1994; Sennrich et al. 2016), byte-level BPE (GPT-2), regex de pre-tokenización y verificación contra `tiktoken`.
