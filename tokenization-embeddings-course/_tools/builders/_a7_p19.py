"""Proyecto 19 · Tres casos de system design resueltos y revisados contra rúbrica + README del módulo 19."""
import _a7_common as C
from _a7_common import hint

SETUP = r'''
import math, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
AZUL, NARANJA, VERDE, GRIS, ROJO = "#1F6FEB", "#F28E2B", "#2CA02C", "#6B7280", "#D62728"
plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": .25})

# Supuestos comunes (los mismos de los módulos 18-19; cámbialos si tu proveedor/hardware es otro)
SUP = dict(precio_api=0.02,            # USD / 1M tokens (OpenAI text-embedding-3-small, tarifa estándar oct-2026)
           gpu_usd_h=0.80, gpu_tok_s=20_000, gpu_util=0.6,   # SUPUESTOS de GPU propia (módulo 18)
           qps_por_replica=500, replicas_min=2, grafo_b=256, margen_ram=0.7,
           vec_visual=1030, d_visual=128, bytes_visual=2)   # ColPali-like: ~1030 vectores x 128 d en fp16 por página (módulo 16)
'''

CASOS = r'''
CASOS = {
 "C1_docs_global": dict(
    titulo="Políglota Docs Global", docs=5_000_000, tokens_por_doc=2_400, tokens_por_chunk=400, d=768,
    idiomas=["es", "en", "pt", "código"], qps_pico=300, sla_p99_ms=150, ram_gb_maquina=64,
    on_prem=False, identificadores_exactos=True, acl_selectiva=False, actualizaciones="1 % diario", multimodal=False,
    notas="Documentación técnica pública; los usuarios pegan códigos de error (E1234) y nombres de función."),
 "C2_codigo_interno": dict(
    titulo="Búsqueda de código interna con permisos", docs=800_000, chunks_por_doc=5, tokens_por_chunk=300, d=1024,
    idiomas=["en", "código"], qps_pico=50, sla_p99_ms=300, ram_gb_maquina=32,
    on_prem=True, identificadores_exactos=True, acl_selectiva=True, actualizaciones="streaming (commits cada minuto)", multimodal=False,
    notas="Código propietario: no puede salir de la red. Cada usuario ve ~2 % de los repositorios."),
 "C3_soporte_pdfs": dict(
    titulo="Soporte sobre PDFs escaneados (salud, UE)", docs=200_000, paginas_por_doc=20, tokens_por_pagina=500, d=1024,
    idiomas=["es", "en", "de", "fr"], qps_pico=20, sla_p99_ms=400, ram_gb_maquina=128,
    on_prem=True, identificadores_exactos=False, acl_selectiva=False, actualizaciones="semanal", multimodal=True,
    notas="Escaneos con tablas y diagramas; datos de salud (residencia UE, borrado en 30 días)."),
}
for k, c in CASOS.items():
    print(f"{k}: {c['titulo']} · {c['notas']}")
'''

RUBRICA = r'''
BYTES_INDICE = {"flat": lambda d: 4 * d, "hnsw": lambda d: 4 * d + SUP["grafo_b"], "hnsw_int8": lambda d: d + SUP["grafo_b"],
                "diskann": lambda d: 64, "ivfpq": lambda d: 64}
ETAPAS_VALIDAS = {"bm25", "denso", "reranker", "maxsim_visual"}

def referencia_capacidad(c: dict) -> dict:
    """Valores de referencia con las fórmulas de los módulos 18-19 (la rúbrica acepta ±15 %)."""
    if "tokens_por_doc" in c:
        n = c["docs"] * c["tokens_por_doc"] / c["tokens_por_chunk"]; tok = c["docs"] * c["tokens_por_doc"]
    elif "chunks_por_doc" in c:
        n = c["docs"] * c["chunks_por_doc"]; tok = n * c["tokens_por_chunk"]
    else:
        n = c["docs"] * c["paginas_por_doc"]; tok = n * c["tokens_por_pagina"]
    coste = tok / (SUP["gpu_tok_s"] * 3600 * SUP["gpu_util"]) * SUP["gpu_usd_h"] if c["on_prem"] else tok / 1e6 * SUP["precio_api"]
    return {"n_unidades": n, "tokens_totales": tok, "ram_gb_float32": n * 4 * c["d"] / 1e9, "coste_embedding_usd": coste,
            "replicas": max(SUP["replicas_min"], math.ceil(c["qps_pico"] / SUP["qps_por_replica"]))}

def ram_de_diseno(c, dz) -> float:
    n = referencia_capacidad(c)["n_unidades"]
    gb = n * BYTES_INDICE[dz["indice"]](c["d"]) / 1e9
    if dz.get("modalidad") == "visual_multivector" and dz.get("visual_en_ram", True):
        gb += n * SUP["vec_visual"] * SUP["d_visual"] * SUP["bytes_visual"] / 1e9
    return gb

def requisitos_caso(clave, c, dz) -> list:
    et = set(dz["hibrido_etapas"])
    chk = [("tokenizer del modelo preentrenado", dz["tokenizer"] == "del_modelo"),
           ("multilingüe si hay > 2 idiomas naturales", dz["multilingue"] or sum(i != "código" for i in c["idiomas"]) <= 1),
           ("BM25 si hay identificadores exactos", (not c["identificadores_exactos"]) or "bm25" in et),
           ("embedder autohospedado si on-prem", (not c["on_prem"]) or dz["embedder_tipo"] == "open_weights_autohospedado")]
    if c["acl_selectiva"]:
        chk.append(("ACL selectiva: filtro en servidor antes/durante la búsqueda", dz["filtros"] in ("pre_servidor", "grafo")))
    if c["actualizaciones"].startswith("streaming"):
        chk.append(("streaming: índice que admite inserciones (no IVF-PQ)", dz["indice"] != "ivfpq"))
    if c["multimodal"]:
        chk.append(("multimodal: OCR+texto o visual sin multi-vector entero en RAM",
                    dz.get("modalidad") in ("ocr_texto", "hibrido_ocr_visual") or (dz.get("modalidad") == "visual_multivector" and not dz.get("visual_en_ram", True))))
        chk.append(("datos de salud: ≥ 3 controles de privacidad", len(dz.get("privacidad", [])) >= 3))
    return chk

def evalua_diseno(clave: str, dz: dict, verbose: bool = True) -> dict:
    """Rúbrica de 100 puntos: capacidad (30) + restricciones (25) + requisitos del caso (25) + evaluación y operación (20)."""
    c, ref = CASOS[clave], referencia_capacidad(CASOS[clave])
    det = []
    cap = dz["capacidad"]
    for k in ref:
        ok = abs(cap.get(k, -1) - ref[k]) <= 0.15 * ref[k]
        det.append(("A capacidad", k, 6, ok, f"tuyo={cap.get(k)} · ref≈{ref[k]:.3g}"))
    ram = ram_de_diseno(c, dz)
    det.append(("B restricciones", "RAM por réplica ≤ 70 % de la máquina", 10, ram <= SUP["margen_ram"] * c["ram_gb_maquina"], f"{ram:.1f} GB vs {SUP['margen_ram'] * c['ram_gb_maquina']:.1f} GB"))
    lat = sum(dz["latencia_ms"].values())
    det.append(("B restricciones", "presupuesto de latencia ≤ SLA p99", 10, lat <= c["sla_p99_ms"], f"{lat} ms vs {c['sla_p99_ms']} ms"))
    det.append(("B restricciones", "réplicas suficientes", 5, cap.get("replicas", 0) >= ref["replicas"], f"{cap.get('replicas')} vs ≥ {ref['replicas']}"))
    req = requisitos_caso(clave, c, dz)
    for nombre, ok in req:
        det.append(("C requisitos", nombre, 25 / len(req), ok, ""))
    ev = dz["evaluacion"]
    det.append(("D evaluación/operación", "golden set ≥ 200 queries, estratificado y con test ciego", 8, ev["n_queries"] >= 200 and ev["estratificado"] and ev["test_ciego"], ""))
    det.append(("D evaluación/operación", "IC pareado contra el sistema actual", 4, ev["ic_pareado"], ""))
    det.append(("D evaluación/operación", "plan online (interleaving y/o A/B)", 4, ev["online"] in ("interleaving", "A/B", "interleaving+A/B"), ""))
    det.append(("D evaluación/operación", "rollback por alias", 2, dz["rollback_alias"], ""))
    det.append(("D evaluación/operación", "≥ 3 riesgos con mitigación", 2, len(dz["riesgos"]) >= 3, ""))
    assert set(dz["hibrido_etapas"]) <= ETAPAS_VALIDAS, f"etapas no válidas: {set(dz['hibrido_etapas']) - ETAPAS_VALIDAS}"
    df = pd.DataFrame(det, columns=["bloque", "criterio", "pts", "ok", "detalle"])
    total = float((df.pts * df.ok).sum())
    if verbose:
        print(f"── {clave}: {total:.0f}/100 {'✅ APROBADO' if total >= 80 else '❌ por debajo de 80'}")
        for _, r in df[~df.ok].iterrows():
            print(f"   ✗ [{r.bloque}] {r.criterio} {r.detalle}")
    return {"total": total, "por_bloque": df.assign(p=df.pts * df.ok).groupby("bloque").p.sum().to_dict(), "detalle": df}
'''

ANTIDISENO = r'''
# Propuesta del becario para C1 (dada): ¿qué falla? Ejecuta la rúbrica y lee los ✗.
BECARIO_C1 = dict(
    capacidad={"n_unidades": 5_000_000, "tokens_totales": 1.2e10, "ram_gb_float32": 15.4, "coste_embedding_usd": 240, "replicas": 1},
    tokenizer="bpe_propio", embedder_tipo="api", multilingue=True, indice="hnsw", hibrido_etapas=["denso", "reranker"], filtros="ninguno",
    latencia_ms={"embed_query": 40, "busqueda": 10, "rerank": 120, "red": 20},
    evaluacion=dict(n_queries=100, estratificado=False, test_ciego=False, ic_pareado=False, online="ninguno"),
    rollback_alias=False, riesgos=["el modelo puede cambiar"], privacidad=[])
_ = evalua_diseno("C1_docs_global", BECARIO_C1)
'''


def project(nb):
    nb.md(nb.badge() + r"""

# Proyecto 19 · Tres casos de *system design* resueltos y revisados contra rúbrica

| | |
|---|---|
| **Nivel** | 🔴 Experto |
| **Duración** | ≈ 1.5 h |
| **GPU** | No necesaria (solo cálculo; < 10 s de ejecución) |
| **Requiere** | Lección 19 (árboles de decisión, costes a escala, checklist) · 14 (índices) · 16 (multimodal) · 18 (costes, migración, privacidad) |
| **Conecta con** | `extras/GUIA_ENTREVISTAS.md` (las preguntas de system design usan estos casos) · **Módulo 20** (el capstone aplica la plantilla de diseño a Políglota) |

## 🏢 Contexto de negocio
Políglota Labs firma tres clientes a la vez. Para cada uno, el VP de ingeniería quiere un **documento de diseño de una página** con números, no adjetivos: capacidad, memoria, coste, presupuesto de latencia, arquitectura de retrieval, plan de evaluación, migración y riesgos. Es también exactamente el formato de una entrevista de *system design* de búsqueda/embeddings en un laboratorio top.

## 📦 Datos
No hay dataset: los tres casos son **especificaciones** (`CASOS`). Los supuestos de precios y hardware (`SUP`) son los de los módulos 18–19 (precio de API fechado oct-2026; GPU, RAM y QPS por réplica **supuestos**).

## 🎯 Entregables y rúbrica
Para cada caso, una función `diseno_CX()` que devuelve un `dict` con la plantilla de abajo. `evalua_diseno` lo puntúa sobre 100:

| Bloque | Qué mide | Pts |
|---|---|---|
| A · Capacidad | nº de chunks/páginas, tokens, RAM float32, coste de embedding, réplicas: cada uno a ±15 % de la referencia calculada con las fórmulas de la lección | 30 |
| B · Restricciones | RAM del índice elegido ≤ 70 % de la máquina (recalculada por la rúbrica a partir de tu `indice`); suma del presupuesto de latencia ≤ SLA; réplicas ≥ referencia | 25 |
| C · Requisitos del caso | tokenizer, multilingüe, BM25 si hay identificadores, on-prem, ACL, streaming, multimodal, privacidad (según el caso) | 25 |
| D · Evaluación y operación | golden set ≥ 200 queries estratificado con test ciego, IC pareado, plan online, rollback, ≥ 3 riesgos | 20 |

**Aprobado: ≥ 80/100 en cada caso.** La solución de referencia obtiene 100/100 en los tres (umbral calibrado con ella); la «propuesta del becario» de la sección 1 obtiene menos de 30.

Plantilla del diseño:
```python
dict(capacidad={"n_unidades", "tokens_totales", "ram_gb_float32", "coste_embedding_usd", "replicas"},
     tokenizer="del_modelo" | "bpe_propio" | "byte_level", embedder_tipo="api" | "open_weights_autohospedado", multilingue=bool,
     indice="flat" | "hnsw" | "hnsw_int8" | "diskann" | "ivfpq", hibrido_etapas=[subconjunto de {"bm25","denso","reranker","maxsim_visual"}],
     filtros="ninguno" | "post" | "pre_servidor" | "grafo", modalidad="ocr_texto" | "visual_multivector" | "hibrido_ocr_visual" (solo C3), visual_en_ram=bool (solo C3),
     latencia_ms={"embed_query":..., "busqueda":..., "rerank":..., "red":...},
     evaluacion=dict(n_queries=int, estratificado=bool, test_ciego=bool, ic_pareado=bool, online="interleaving" | "A/B" | "interleaving+A/B" | "ninguno"),
     rollback_alias=bool, riesgos=[...], privacidad=[...], justificacion="texto libre (lo revisa una persona)")
```""")
    nb.md("## 0. Supuestos, casos y rúbrica (celdas dadas)")
    nb.code(SETUP)
    nb.code(CASOS)
    nb.code(RUBRICA)
    nb.code(C.CODE_CORRE)
    nb.md("## 1. Calentamiento: revisa la propuesta del becario\nAntes de diseñar, usa la rúbrica como revisor. Lee cada ✗ y anota **por qué** es un error (no solo que lo es).")
    nb.code(ANTIDISENO)
    nb.md(r"""<details><summary>Comentario del revisor (ábrelo después de pensarlo)</summary>

* **Capacidad**: confundió documentos con chunks (5 M docs × 2 400 tokens / 400 = **30 M** chunks) y por eso calculó la RAM 6 veces por debajo. Con 30 M × 768 × 4 B = 92 GB, float32 + HNSW **no cabe** en 64 GB.
* **Réplicas = 1**: sin redundancia; una caída es una caída del producto.
* **Sin BM25** con usuarios que pegan códigos de error: el denso no sabe que `E1234` ≠ `E1243`.
* **Tokenizer propio** para un embedder preentrenado: imposible sin tokenizer transfer (módulo 07).
* **Latencia**: 40 + 10 + 120 + 20 = 190 ms > 150 ms de SLA; o se baja K del reranker o se usa un reranker más pequeño.
* **Evaluación**: 100 queries sin estratificar ni test ciego no detectan diferencias de 0.02 (módulo 15).
</details>""")

    nb.md("## 2. Caso C1 · Políglota Docs Global (TODO 1)")
    nb.md(hint("Empieza por la capacidad: chunks = docs × tokens/doc ÷ tokens/chunk; RAM = chunks × 4·d B. Compara con 70 % de 64 GB y usa el árbol `elige_indice` de la lección. Presupuesto de latencia: la suma de las cuatro partidas debe caber en 150 ms.",
               "`n = 5e6*2400/400`; `ram = n*4*768/1e9` (≈ 92 GB → no cabe) ⇒ `indice='hnsw_int8'` (≈ 31 GB con grafo). Coste API: `5e6*2400/1e6*0.02`. Etapas: `['bm25','denso','reranker']` con `rerank` ≈ 2 ms × 40 docs."))
    nb.code(r'''
def diseno_C1() -> dict:
    # TODO 1: devuelve el diccionario completo de la plantilla para C1
    raise NotImplementedError("TODO 1: diseno_C1")

corre(lambda: evalua_diseno("C1_docs_global", diseno_C1())["total"])
''')
    nb.md("## 3. Caso C2 · Búsqueda de código interna con permisos (TODO 2)")
    nb.md(hint("Tres requisitos mandan: on-prem (coste con la fórmula de GPU, embedder autohospedado), ACL que deja ~2 % de candidatos (¡post-filtrar devolvería casi siempre < k resultados!) y commits cada minuto.",
               "`filtros='pre_servidor'` (con 2 % de 4 M = 80 k candidatos, la fuerza bruta sobre ellos cabe en el SLA) o `'grafo'` (ACORN); `indice='hnsw'` (16.4 GB + grafo ≈ 17.4 GB ≤ 22.4 GB); coste = `1.2e9/(20000*3600*0.6)*0.8`."))
    nb.code(r'''
def diseno_C2() -> dict:
    # TODO 2
    raise NotImplementedError("TODO 2: diseno_C2")

corre(lambda: evalua_diseno("C2_codigo_interno", diseno_C2())["total"])
''')
    nb.md("## 4. Caso C3 · Soporte sobre PDFs escaneados (TODO 3)")
    nb.md(hint("Calcula cuánto ocuparía el índice multi-vector visual entero: páginas × 1030 vectores × 128 d × 2 B. ¿Cabe en RAM? Si no, ¿qué parte del pipeline puede vivir en disco?",
               "4 M páginas × 1030 × 128 × 2 B ≈ 1 TB ⇒ `modalidad='hibrido_ocr_visual'`: primera etapa con texto OCR denso (+BM25 opcional) en RAM y MaxSim visual (`'maxsim_visual'`) solo sobre las top-K páginas leídas de SSD; `privacidad` con ≥ 3 controles (residencia UE, cifrado y acceso, borrado propagado a índice/caché/backups en 30 días, logs sin PII)."))
    nb.code(r'''
def diseno_C3() -> dict:
    # TODO 3
    raise NotImplementedError("TODO 3: diseno_C3")

corre(lambda: evalua_diseno("C3_soporte_pdfs", diseno_C3())["total"])
''')
    nb.md("## 5. Informe (TODO 4)\nJunta los tres diseños en una tabla comparativa (caso, índice, precisión/modalidad, RAM por réplica recalculada, coste de embedding, latencia presupuestada, nota) y un gráfico de puntos por bloque.")
    nb.md(hint("Recorre `{'C1_docs_global': diseno_C1, ...}`, llama a `evalua_diseno(..., verbose=False)` y a `ram_de_diseno`.",
               "`filas.append({'caso': k, 'indice': dz['indice'], 'RAM GB': ram_de_diseno(CASOS[k], dz), 'coste $': dz['capacidad']['coste_embedding_usd'], 'latencia ms': sum(dz['latencia_ms'].values()), 'nota': r['total']})`; para el gráfico, `pd.DataFrame({k: r['por_bloque']})` y `.plot.bar()`."))
    nb.code(r'''
def informe() -> pd.DataFrame:
    # TODO 4: tabla comparativa + gráfico de barras de puntos por bloque y caso
    raise NotImplementedError("TODO 4: informe")

corre(lambda: display(informe()))
''')

    # ── SPOILER
    nb.md("---\n## ⛔ SPOILER — intenta resolverlo primero\nDiseños de referencia (100/100 cada uno). Fíjate sobre todo en las **justificaciones**: la rúbrica automática no las lee, una persona sí.")
    nb.code(r'''
EVAL_STD = dict(n_queries=300, estratificado=True, test_ciego=True, ic_pareado=True, online="interleaving+A/B")

def diseno_C1() -> dict:
    c = CASOS["C1_docs_global"]; n = c["docs"] * c["tokens_por_doc"] / c["tokens_por_chunk"]; tok = c["docs"] * c["tokens_por_doc"]
    return dict(
        capacidad={"n_unidades": n, "tokens_totales": tok, "ram_gb_float32": n * 4 * c["d"] / 1e9,
                   "coste_embedding_usd": tok / 1e6 * SUP["precio_api"], "replicas": 2},
        tokenizer="del_modelo", embedder_tipo="api", multilingue=True, indice="hnsw_int8",
        hibrido_etapas=["bm25", "denso", "reranker"], filtros="ninguno",
        latencia_ms={"embed_query": 25, "busqueda": 15, "rerank": 80, "red": 20},
        evaluacion=EVAL_STD, rollback_alias=True,
        riesgos=["retirada/cambio del modelo de la API → versión en metadatos + plan de re-embedding (240 $)",
                 "códigos de error mal tokenizados → BM25 con tokenización de identificadores (split_ident, módulo 00)",
                 "PT con menos datos que ES/EN → slice propio en el golden set", "cola de latencia del reranker → K adaptativo y timeout"],
        privacidad=["documentación pública: sin PII; logs de queries con retención limitada"],
        justificacion="30 M chunks: float32 (92 GB) no cabe en 64 GB; int8 + grafo ≈ 31 GB sí (pérdida típica pequeña, módulos 12/18). "
                      "BM25 obligatorio por los identificadores; RRF + reranker sobre top-40 cabe en 150 ms. API: 240 $ por re-embedding completo.")

def diseno_C2() -> dict:
    c = CASOS["C2_codigo_interno"]; n = c["docs"] * c["chunks_por_doc"]; tok = n * c["tokens_por_chunk"]
    return dict(
        capacidad={"n_unidades": n, "tokens_totales": tok, "ram_gb_float32": n * 4 * c["d"] / 1e9,
                   "coste_embedding_usd": tok / (SUP["gpu_tok_s"] * 3600 * SUP["gpu_util"]) * SUP["gpu_usd_h"], "replicas": 2},
        tokenizer="del_modelo", embedder_tipo="open_weights_autohospedado", multilingue=False, indice="hnsw",
        hibrido_etapas=["bm25", "denso", "reranker"], filtros="pre_servidor",
        latencia_ms={"embed_query": 20, "busqueda": 60, "rerank": 150, "red": 20},
        evaluacion=EVAL_STD, rollback_alias=True,
        riesgos=["fuga entre permisos → filtro ACL obligatorio en el servidor + tests de autorización en CI",
                 "índice desactualizado → ingesta en streaming, borrados marcados y compactación nocturna",
                 "identificadores (snake_case/camelCase) → BM25 con split de identificadores",
                 "drift al llegar un lenguaje nuevo → PSI del top-1 por repositorio"],
        privacidad=["código propietario: embedder y servidor en la red interna", "vectores con la ACL del repositorio en el payload"],
        justificacion="4 M chunks × 1024 d float32 = 16.4 GB (+1 GB de grafo) caben en 32 GB → HNSW float32. Con ~2 % de repos visibles el "
                      "post-filtro devolvería < k: pre-filtro en el servidor (80 k candidatos ⇒ fuerza bruta sobre el subconjunto) o grafo con filtros (ACORN). "
                      "Re-embedding en GPU propia ≈ 22 $ (supuestos de SUP).")

def diseno_C3() -> dict:
    c = CASOS["C3_soporte_pdfs"]; n = c["docs"] * c["paginas_por_doc"]; tok = n * c["tokens_por_pagina"]
    return dict(
        capacidad={"n_unidades": n, "tokens_totales": tok, "ram_gb_float32": n * 4 * c["d"] / 1e9,
                   "coste_embedding_usd": tok / (SUP["gpu_tok_s"] * 3600 * SUP["gpu_util"]) * SUP["gpu_usd_h"], "replicas": 2},
        tokenizer="del_modelo", embedder_tipo="open_weights_autohospedado", multilingue=True, indice="hnsw",
        modalidad="hibrido_ocr_visual", visual_en_ram=False, hibrido_etapas=["bm25", "denso", "maxsim_visual"], filtros="ninguno",
        latencia_ms={"embed_query": 30, "busqueda": 20, "rerank": 250, "red": 30},
        evaluacion=EVAL_STD, rollback_alias=True,
        riesgos=["OCR malo en tablas/diagramas → reranking visual MaxSim sobre top-K páginas (módulo 16)",
                 "multi-vector visual ≈ 1 TB → solo en SSD, leído para el top-K", "idiomas DE/FR con menos queries → golden set estratificado",
                 "retención de 30 días → borrado por doc_id en índice, caché, SSD y backups con auditoría"],
        privacidad=["residencia UE: todo autohospedado en la región", "cifrado en reposo y control de acceso por rol",
                    "borrado propagado a índice/caché/backups en ≤ 30 días", "logs sin texto de queries (redacción de PII)"],
        justificacion="El índice visual completo pesaría 4 M × 1030 × 128 × 2 B ≈ 1.05 TB: imposible en RAM. Primera etapa OCR+texto "
                      "(16.4 GB float32 + grafo, cabe en 128 GB) y MaxSim visual solo sobre el top-K leído de SSD: une la precisión visual "
                      "con el coste del texto. Ruido en vectores NO sustituye a los controles de acceso (módulo 18).")

def informe() -> pd.DataFrame:
    fns = {"C1_docs_global": diseno_C1, "C2_codigo_interno": diseno_C2, "C3_soporte_pdfs": diseno_C3}
    filas, bloques = [], {}
    for k, f in fns.items():
        dz = f(); r = evalua_diseno(k, dz, verbose=False); bloques[k] = r["por_bloque"]
        filas.append({"caso": CASOS[k]["titulo"], "índice": dz["indice"], "modalidad": dz.get("modalidad", "texto"),
                      "RAM GB/réplica": round(ram_de_diseno(CASOS[k], dz), 1), "coste embedding $": round(dz["capacidad"]["coste_embedding_usd"], 1),
                      "latencia ms": sum(dz["latencia_ms"].values()), "SLA ms": CASOS[k]["sla_p99_ms"], "nota": r["total"]})
    ax = pd.DataFrame(bloques).T.plot.bar(stacked=True, figsize=(8, 4), color=[AZUL, VERDE, NARANJA, GRIS], rot=0)
    ax.set_ylabel("puntos"); ax.set_title("Rúbrica por bloque y caso (solución de referencia)"); ax.axhline(80, color=ROJO, ls="--")
    plt.tight_layout(); plt.show()
    return pd.DataFrame(filas)
''')
    nb.code(r'''
for k, f in (("C1_docs_global", diseno_C1), ("C2_codigo_interno", diseno_C2), ("C3_soporte_pdfs", diseno_C3)):
    evalua_diseno(k, f())
display(informe())
''')
    nb.md(r"""> 👀 **Qué debes observar:** los tres casos tienen arquitecturas **distintas** por razones medibles: C1 por memoria (int8), C2 por permisos y actualizaciones (pre-filtro + HNSW), C3 por almacenamiento multi-vector (OCR en RAM + visual en SSD). Si tus tres diseños se parecen, probablemente estás eligiendo por costumbre.

## 🚀 Retos extra
1. **Sensibilidad**: ¿con qué `d` (Matryoshka) cabe C1 en float32? ¿Con cuántos GB de RAM pasaría C3 a tener el visual en memoria con binarización (1 bit/dim)?
2. **Cuarto caso**: un marketplace con 300 M de productos, 5 000 QPS y filtros de precio/categoría. Escribe `CASOS['C4']`, amplía `requisitos_caso` y diseña.
3. **Rúbrica más estricta**: añade un criterio de coste mensual de infraestructura con la calculadora `costo_sistema` de la lección.
4. **Entrevista simulada**: toma un caso y explícalo en voz alta en 10 minutos con la estructura de `extras/GUIA_ENTREVISTAS.md` (requisitos → capacidad → arquitectura → evaluación → operación → riesgos).

## 🤔 Reflexión
1. ¿Qué número de tu diseño de C1 te da más miedo que esté mal y cómo lo medirías antes de firmar?
2. En C2, ¿por qué el filtro de permisos **no** puede delegarse al cliente aunque «la API ya lo filtra después»?
3. En C3, ¿qué experimento de una tarde te diría si el MaxSim visual compensa su latencia frente a solo OCR?
""")


README = r"""# Módulo 19 · Playbook de élite: decisiones, trampas y revisión

**Nivel:** 🔴 Experto · **Duración:** ≈ 4 h (lección ≈ 2.5 h + proyecto ≈ 1.5 h) · **Cómputo:** CPU (0 unidades de Colab)

| Archivo | Contenido |
|---|---|
| [`19_playbook_elite.ipynb`](19_playbook_elite.ipynb) | Lección: **árboles de decisión ejecutables** (tokenizer, embedder, índice, híbrido) con el umbral Flat→HNSW **medido** con FAISS · **cuatro trampas de evaluación reproducidas** (tuning en test vs CV, *winner's curse*, dependencia del golden set, sesgo de *pooling*) · **gap offline/online** (mezcla de tráfico, interfaz top-3, modelo de clic) · **calculadora de costes a escala** (1 M–1 B docs, float32/int8/binario) · **fallos reales documentados** + galería de 4 fallos silenciosos reproducidos (truncado, producto punto sin normalizar, tildes índice≠query, caché sin versión) · **linter de PRs** · cultura de equipos top |
| [`19_proyecto_playbook_elite.ipynb`](19_proyecto_playbook_elite.ipynb) | Proyecto: **3 casos de system design** (documentación global, código interno con permisos, PDFs escaneados de salud) con plantilla estructurada, rúbrica automática de 100 puntos (capacidad, restricciones, requisitos, evaluación/operación), revisión de una propuesta con errores, TODOs, pistas 🪜 y soluciones de referencia tras ⛔ SPOILER |
| `assets/` | Recursos de Gemini: `M19-IMG-01.png`, `M19-IMG-02.png`, `M19-IMG-03.png` |

Este módulo produce también [`extras/GUIA_ENTREVISTAS.md`](../extras/GUIA_ENTREVISTAS.md) (preguntas de tokenización, embeddings y system design con respuestas modelo y rúbrica) y [`extras/LECTURA_PAPERS.md`](../extras/LECTURA_PAPERS.md) (lectura guiada por módulo).

## Objetivos
1. Codificar y justificar con mediciones árboles de decisión de tokenizer, embedder, índice e híbrido.
2. Reproducir y cuantificar trampas de evaluación.
3. Explicar y recalcular el gap offline/online.
4. Estimar costes de retrieval a escala con supuestos explícitos.
5. Diagnosticar fallos reales y silenciosos; revisar PRs con una checklist ejecutable.
6. Resolver casos de system design con números y defenderlos frente a una rúbrica.

## Datos
Corpus Políglota canónico (`carga_corpus`, módulo 00; sintético + stdlib sin red), mini golden set de paráfrasis (módulo 13), vectores gaussianos para la medición de índices. El proyecto no usa datos: son especificaciones.

## Estado de pruebas (entorno de autoría, oct-2026)
Lección (≈ 1.5 min) y proyecto (< 10 s) ejecutados completos con `nbclient` en CPU, con corpus **sintético** y embedders **fallback** (Hugging Face bloqueado). Las cifras de la lección (trampas, gap, fallos) salen de esa ejecución; con un embedder neuronal real cambian los valores (en especial T3, donde el fallback es léxico) y la lección lo advierte. Precios de infraestructura del módulo: **supuestos** marcados; precio de API verificado (oct-2026).

## Lecturas
Thakur et al. 2021 (BEIR) · Cormack et al. 2009 (RRF) · Bruch et al. 2022 (fusión) · Nogueira & Cho 2019 · Weller et al. 2025 (LIMIT) · Thomas et al. 2023 / Soboroff 2024 (LLM-as-judge) · Smucker et al. 2007 · Land & Bartolo 2024 · Singh & Strouse 2024 · Petrov et al. 2023 · Boucher & Anderson 2021 · Liu et al. 2023 (*Lost in the Middle*) · Patel et al. 2024 (ACORN) · Chapelle et al. 2012 · Kohavi et al. 2020.

## Enlaces
Anterior: [18 · Producción](../18_produccion/) · Siguiente: [20 · Capstone: Políglota completo](../20_capstone/)

*Notebooks generados con `python tokenization-embeddings-course/_tools/builders/build_19.py` (desde la raíz del repo).*
"""
