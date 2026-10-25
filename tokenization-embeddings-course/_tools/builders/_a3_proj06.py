"""Proyecto del módulo 06: mini patcher entrópico vs BPE. build() lo llama build_06.py."""
import os, sys, re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from nbbuild import Notebook  # noqa: E402
import a3_common as C  # noqa: E402
import _a3_src06 as S  # noqa: E402

# Umbrales de la rúbrica: calibrados con lo MEDIDO por la solución de referencia (corpus sintético, FAST_DEV_RUN=True).
T = {
    "ps_obj": 4.5, "ps_tol": 0.10,
    "frag_ent_max": 1.10, "estab_ent_min": 0.95,
    "estab_bpe_min": 0.98,
    "ahorro_ps_max": 6.5,
}

NGRAM_CLASS = S.NGRAM.split("t0 = time.time()")[0].replace(
    "H = np.zeros(len(b), np.float32)\n        for i in range(len(b)):\n            p = self.probs(b[max(0, i - self.orden):i]); H[i] = -(p * np.log2(p + 1e-12)).sum()",
    "H = np.zeros(len(b), np.float32)\n        for i in range(len(b)):\n            H[i] = entropia_bits(self.probs(b[max(0, i - self.orden):i]))   # <- tu TODO 1")

FLOPS_FN = S.FLOPS.split("base = flops_por_byte")[0]
SCHEMES_FN = S.SCHEMES_TEXT.split('mb = MUESTRA.encode()')[0]
BPE_FN = S.BPE_LEN.split("VOCABS = ")[0]

TYPOS = r'''
def inyecta_erratas(texto, p, rng):
    """Sustituye UNA letra ASCII de cada palabra afectada (prob. p, palabras ASCII de >=4 letras). Longitud en bytes intacta.
    Devuelve (texto_ruidoso, [(ini, fin) de las palabras corrompidas en bytes])."""
    out, malas = list(texto), []
    for m in re.finditer(r"[A-Za-z]{4,}", texto):
        if rng.random() < p:
            i = rng.randrange(m.start(), m.end())
            out[i] = rng.choice([c for c in "abcdefghijklmnopqrstuvwxyz" if c != texto[i].lower()])
            malas.append((m.start(), m.end()))
    return "".join(out), malas

def palabras_ascii(texto):
    return [(m.start(), m.end()) for m in re.finditer(r"[A-Za-z]{4,}", texto)]
'''

TODO1 = r'''
def entropia_bits(p):
    """Entropía de Shannon, en bits, de un vector de probabilidades p (256 posiciones; puede haber ceros)."""
    # TODO 1: H = - sum_v p_v log2 p_v ignorando p_v = 0
    raise NotImplementedError("TODO 1")
'''
SOL1 = r'''
def entropia_bits(p):
    p = np.asarray(p, dtype=np.float64); p = p[p > 0]
    return float(-(p * np.log2(p)).sum())
'''

TODO2 = r'''
def inicios_global(H, theta):
    """H: array de entropías por byte. Devuelve bool[len(H)]: True si el byte ABRE un parche (regla global)."""
    # TODO 2a: H[i] > theta; el primer byte siempre abre parche
    raise NotImplementedError("TODO 2a")

def inicios_monotono(H, theta_r):
    """Regla de restricción monótona aproximada: H[i] - H[i-1] > theta_r (el primer byte siempre abre parche)."""
    # TODO 2b
    raise NotImplementedError("TODO 2b")
'''
SOL2 = S.PATCHING.split("def calibra")[0].split("def inicios_global")[1]
SOL2 = "def inicios_global" + SOL2

TODO3 = r'''
def calibra(H, objetivo, fn, lo=-6.0, hi=9.0, iters=40):
    """Busca por bisección el umbral theta tal que el tamaño medio de parche (len(H) / nº de parches) sea `objetivo`.
    `fn(H, theta)` devuelve los inicios. Pista de monotonía: a mayor umbral, menos parches, parches más largos."""
    # TODO 3
    raise NotImplementedError("TODO 3")
'''
SOL3 = "def calibra" + S.PATCHING.split("def calibra")[1].split("def longitudes")[0] + '''
def longitudes(starts):
    idx = np.flatnonzero(starts); return np.diff(np.r_[idx, len(starts)])
'''

TODO4 = r'''
def prueba_incremental(f_inicios, items, n_pruebas=300, seed=SEED):
    """Fracción de cortes aleatorios i en los que f(x[:i]) == f(x)[:i]  (propiedad de parcheo incremental).
    `items`: lista de str (para BPE) o de bytes (para entropía); `f_inicios` acepta el mismo tipo."""
    # TODO 4: elige un item y un corte i; compara f(prefijo) con f(completo)[:len(prefijo)]
    raise NotImplementedError("TODO 4")
'''
SOL4 = "def prueba_incremental" + S.INCREMENTAL.split("def prueba_incremental")[1].split("textos_prueba")[0]

TODO5 = r'''
def metricas_robustez(f_seg, textos, p=0.05, seed=SEED):
    """Compara la segmentación de textos limpios y con erratas (usa `inyecta_erratas`).
    Devuelve {"frag": unidades_ruidoso / unidades_limpio,   # inflación del nº de parches/tokens (coste) por el ruido
              "estab": fracción de palabras INTACTAS cuya segmentación interna (bool por byte) no cambia}."""
    # TODO 5: f_seg(texto) -> bool por byte. Suma unidades sobre todos los textos; para 'estab' compara
    #         sc[a:b] con sn[a:b] en palabras (a, b) de `palabras_ascii(texto)` que NO estén en `malas`.
    raise NotImplementedError("TODO 5")
'''
SOL5 = r'''
def metricas_robustez(f_seg, textos, p=0.05, seed=SEED):
    r = random.Random(seed); u_c = u_n = ok = tot = 0
    for t in textos:
        ruido, malas = inyecta_erratas(t, p, r)
        sc, sn = f_seg(t), f_seg(ruido)
        u_c += int(sc.sum()); u_n += int(sn.sum())
        for (a, b) in palabras_ascii(t):
            if (a, b) not in malas and b <= min(len(sc), len(sn)):
                tot += 1; ok += int(np.array_equal(sc[a:b], sn[a:b]))
    return {"frag": u_n / u_c, "estab": ok / max(1, tot)}
'''

TODO6 = r'''
def ps_para_ahorro(ahorro, bpt, grid=np.arange(3.0, 16.0, 0.25)):
    """Menor tamaño medio de parche `ps` para el que BLT gasta al menos `ahorro` (p. ej. 0.25 = 25 %) menos FLOPs/byte que BPE
    con `bpt` bytes/token. Usa flops_por_byte("blt", ps=...) y flops_por_byte("bpe", bpt=...)."""
    # TODO 6
    raise NotImplementedError("TODO 6")
'''
SOL6 = r'''
def ps_para_ahorro(ahorro, bpt, grid=np.arange(3.0, 16.0, 0.25)):
    ref = flops_por_byte("bpe", bpt=bpt)
    for ps in grid:
        if flops_por_byte("blt", ps=float(ps)) <= (1 - ahorro) * ref:
            return float(ps)
    return float("nan")
'''

FLOW_ENT = r'''
# --- Flujo (no lo cambies): modelo de entropía + calibración de umbrales ---
RES = {}
try:
    NG4 = NgramByteLM(4).fit(TR)
    H_TR, H_VA = NG4.entropias(TR), NG4.entropias(VA)
    print("sanity: H(uniforme 256) =", entropia_bits(np.full(256, 1 / 256)), "bits (debe ser 8.0)")
    OBJ = 4.5
    TH_G = calibra(H_TR, OBJ, inicios_global); TH_M = calibra(H_TR, OBJ, inicios_monotono)
    ps_g = len(H_VA) / inicios_global(H_VA, TH_G).sum(); ps_m = len(H_VA) / inicios_monotono(H_VA, TH_M).sum()
    RES.update(th_g=TH_G, th_m=TH_M, ps_g=ps_g, ps_m=ps_m)
    print(f"θ_global={TH_G:.3f} -> ps(val)={ps_g:.2f} | θ_monótono={TH_M:.3f} -> ps(val)={ps_m:.2f}  (objetivo {OBJ})")
except NotImplementedError as e:
    print("Pendiente:", e)
'''

FLOW_INC = r'''
# --- Flujo: parcheo incremental ---
try:
    textos_prueba = [d["text"][:300] for d in DOCS_VA if d["lang"] != "code"][:60]
    bytes_prueba = [t.encode() for t in textos_prueba]
    f_ent_b = lambda b: inicios_global(NG4.entropias(np.frombuffer(b, np.uint8)), TH_G)
    f_bpe_t = lambda t: inicios_bpe(TK, t)
    RES["inc_ent"] = prueba_incremental(f_ent_b, bytes_prueba)
    RES["inc_bpe"] = prueba_incremental(f_bpe_t, textos_prueba)
    print(f"incremental: entropía {RES['inc_ent']*100:.1f}% | BPE {RES['inc_bpe']*100:.1f}%")
except (NotImplementedError, NameError) as e:
    print("Pendiente:", e)
'''

FLOW_ROB = r'''
# --- Flujo: robustez a erratas (5 % de las palabras) ---
try:
    textos_rob = [d["text"][:400] for d in DOCS_VA if d["lang"] in ("es", "en")][:40]
    seg_ent = lambda t: inicios_global(NG4.entropias(np.frombuffer(t.encode(), np.uint8)), TH_G)
    seg_bpe = lambda t: inicios_bpe(TK, t)
    RES["rob_ent"] = metricas_robustez(seg_ent, textos_rob)
    RES["rob_bpe"] = metricas_robustez(seg_bpe, textos_rob)
    RES["ps_bpe"] = float(np.mean(L_BPE)) if "L_BPE" in globals() else None
    print("entropía:", {k: round(v, 3) for k, v in RES["rob_ent"].items()})
    print("BPE     :", {k: round(v, 3) for k, v in RES["rob_bpe"].items()})
except (NotImplementedError, NameError) as e:
    print("Pendiente:", e)
'''

FLOW_COST = r'''
# --- Flujo: ¿qué parche medio necesito para ahorrar un 25 % de FLOPs/byte frente a un BPE "industrial"? ---
try:
    BPT_IND = 4.4          # bytes/token de Llama 3 (BLT, §2.4); la referencia usa un vocabulario de 128K en flops_por_byte("bpe")
    RES["bpt_propio"] = len(TXT_TR.encode()) / len(TK.encode(TXT_TR).ids)
    RES["ps_25"] = ps_para_ahorro(0.25, BPT_IND)
    print(f"tu BPE de {TK.get_vocab_size()} tokens da {RES['bpt_propio']:.2f} bytes/token (un vocabulario de 128K da ~4.4)")
    print(f"ps mínimo para -25% FLOPs/byte frente a BPE industrial (4.4 B/token, config ilustrativa tipo 8B): {RES['ps_25']:.2f}")
except (NotImplementedError, NameError) as e:
    print("Pendiente:", e)
'''

PLOT = r'''
# --- Figura de resumen (no la cambies) ---
if all(k in RES for k in ["rob_ent", "rob_bpe", "inc_ent"]):
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.6))
    axs[0].bar(["entropía", "BPE"], [RES["inc_ent"], RES["inc_bpe"]], color=[AZUL, NARANJA]); axs[0].set_ylim(0, 1.05); axs[0].set_title("Parcheo incremental (fracción de cortes)")
    axs[1].bar(["entropía", "BPE"], [RES["rob_ent"]["estab"], RES["rob_bpe"]["estab"]], color=[AZUL, NARANJA]); axs[1].set_ylim(0, 1.05); axs[1].set_title("Palabras intactas igual segmentadas")
    axs[2].bar(["entropía", "BPE"], [RES["rob_ent"]["frag"], RES["rob_bpe"]["frag"]], color=[AZUL, NARANJA]); axs[2].axhline(1, color=GRIS, ls=":"); axs[2].set_title("Inflación de unidades con 5 % de erratas")
    plt.tight_layout(); plt.show()
else:
    print("Completa los TODO 1-5 para ver la figura.")
'''

RUBRIC = r'''
def rubrica(RES, th=THR):
    filas = []
    def chk(nombre, ok, detalle): filas.append((nombre, ok, detalle))
    g = lambda k: RES.get(k)
    chk("R1 tamaño medio de parche (global y monótono) dentro de ±%d%% del objetivo" % (th["ps_tol"] * 100),
        g("ps_g") is not None and abs(g("ps_g") - 4.5) / 4.5 <= th["ps_tol"] and abs(g("ps_m") - 4.5) / 4.5 <= th["ps_tol"],
        f"ps_g={g('ps_g')}, ps_m={g('ps_m')}")
    chk("R2 parcheo incremental por entropía = 100 % y BPE < 100 %",
        g("inc_ent") is not None and g("inc_ent") == 1.0 and g("inc_bpe") < 1.0, f"ent={g('inc_ent')}, bpe={g('inc_bpe')}")
    re_, rb = g("rob_ent") or {}, g("rob_bpe") or {}
    chk("R3 inflación con erratas (entropía) <= %.2f" % th["frag_ent_max"], re_.get("frag", 9) <= th["frag_ent_max"], f"{re_}")
    chk("R4 estabilidad de palabras intactas (entropía) >= %.2f" % th["estab_ent_min"], re_.get("estab", 0) >= th["estab_ent_min"], f"{re_}")
    chk("R5 estabilidad de palabras intactas (BPE) >= %.2f (sanity de tu métrica)" % th["estab_bpe_min"], rb.get("estab", 0) >= th["estab_bpe_min"], f"{rb}")
    chk("R6 ps mínimo para -25%% FLOPs/byte <= %.1f" % th["ahorro_ps_max"], g("ps_25") is not None and g("ps_25") <= th["ahorro_ps_max"], f"ps_25={g('ps_25')}")
    chk("R7 conclusión escrita (>= 300 caracteres) en CONCLUSION", len(globals().get("CONCLUSION", "")) >= 300, f"{len(globals().get('CONCLUSION', ''))} caracteres")
    for n, ok, d in filas:
        print(("✅" if ok else "❌"), n, "|", d)
    print(f"\n{sum(o for _, o, _ in filas)}/{len(filas)} criterios")
'''


def build(lesson_rel, proj_rel, mod_dir, slug):
    nb = Notebook("Proyecto 06 · Mini patcher entrópico vs BPE", colab_path=proj_rel)
    obs, details, hint = C.observe, C.details, C.hint
    nb.md(nb.badge() + r"""

# Proyecto 06 · Mini *patcher* entrópico vs BPE

| | |
|---|---|
| **Nivel** | 🔴 Experto |
| **Duración estimada** | ≈ 2 h |
| **GPU recomendada** | Ninguna (todo en CPU con `FAST_DEV_RUN=True`, ≈ 2-3 min) |
| **Prerrequisitos** | Lección 06 (entropía del siguiente byte, parches, parcheo incremental), módulos 02-03 (BPE con `tokenizers`) |

## Contexto de negocio

Eres ML engineer en **Políglota Labs**. El CTO duda entre mantener el tokenizer BPE que entrenasteis (módulos 02-04) o explorar una ruta «sin vocabulario» para el futuro modelo generativo del
producto. Te pide una **nota técnica con números**: construye un *patcher* por entropía con un modelo de bytes diminuto entrenado en el corpus Políglota y compáralo con BPE en
(i) tamaño medio de unidad, (ii) **propiedad incremental**, (iii) **robustez a erratas** y (iv) **coste de FLOPs**. Con honestidad: es un banco diminuto, no el resultado del paper.

**Conexión.** Módulo anterior (05): glitch tokens y fragilidad ante erratas → aquí mides la fragilidad de la *segmentación*. Módulo siguiente (07): la frontera se **aprende** (H-Net).

## Dataset
Corpus Políglota vía `carga_corpus()` (Wikipedia ES/EN + CodeSearchNet; fallback sintético + funciones reales de la stdlib). Si imprime «SINTÉTICO», los umbrales de la rúbrica (calibrados sobre datos sintéticos) siguen siendo orientativos pero los valores absolutos cambiarán.

## Entregables y criterios de evaluación

1. Entropía de bytes (n-grama de orden 4 ya dado) y **reglas de parcheo** global y monótona (TODO 1-3).
2. Prueba de **parcheo incremental** para entropía y BPE (TODO 4).
3. Métricas de **robustez a erratas** (inflación y estabilidad) para ambos (TODO 5).
4. **Coste**: parche medio necesario para ahorrar un 25 % de FLOPs/byte frente a BPE (TODO 6).
5. Una **conclusión** escrita en la variable `CONCLUSION` (≥ 300 caracteres) que diga qué recomendarías a Políglota y qué no puedes concluir.

| Criterio | Umbral (calibrado con la solución de referencia) |
|---|---|
| R1 · tamaño medio de parche en validación (global y monótono) | objetivo 4.5 B/parche ± """ + f"{int(T['ps_tol']*100)} %" + r""" (medido: 4.27 y 4.48) |
| R2 · parcheo incremental | entropía = 100 %, BPE < 100 % (medido: 100 % y 92.7 %) |
| R3 · inflación de unidades con 5 % de erratas (entropía) | ≤ """ + f"{T['frag_ent_max']}" + r""" (medido: 1.036; BPE 1.005) |
| R4 · estabilidad de palabras intactas (entropía) | ≥ """ + f"{T['estab_ent_min']}" + r""" (medido: 0.993) |
| R5 · estabilidad de palabras intactas (BPE) | ≥ """ + f"{T['estab_bpe_min']}" + r""" (control de que tu métrica está bien; medido: 1.000) |
| R6 · parche medio para −25 % de FLOPs/byte frente a un BPE industrial (4.4 B/token) | ≤ """ + f"{T['ahorro_ps_max']}" + r""" bytes (medido: 6.0) |
| R7 · conclusión escrita | ≥ 300 caracteres |

> Los umbrales salen de lo **medido** por la solución en `FAST_DEV_RUN=True` con corpus sintético (ver celda de rúbrica al final); con datos reales vuelve a medir y ajusta.
""")
    nb.code(S.PIP)
    nb.code(C.SETUP_COMMON + "import re\n" + S.SETUP_EXTRA)
    for c in C.corpus_cells():
        nb.code(c)
    nb.md("## Paso 0 · Datos y utilidades (dados)\n\nPartimos el corpus en entrenamiento/validación por documento, entrenamos un BPE de 512 tokens y definimos las reglas de segmentación «sin modelo» de la lección.")
    nb.code(S.DATA)
    nb.code(BPE_FN + "\nVOCABS = [300, 512, 1024, 2048] if FAST_DEV_RUN else [512, 4096, 16384, 32000]\nTK = entrena_bpe(DOCS_TR, VOCABS[1])\nprint('BPE entrenado, vocab =', TK.get_vocab_size())")
    nb.code(SCHEMES_FN)
    nb.code(FLOPS_FN + TYPOS)
    nb.md("El modelo de bytes de orden 4 (Witten-Bell) es el de la lección; **su método `entropias` llama a tu función `entropia_bits`** (TODO 1).")
    nb.code(NGRAM_CLASS)

    nb.md("## Paso 1 · TODO 1: entropía de Shannon\n\n$$H(p) = -\\sum_{v} p_v \\log_2 p_v$$\n\nSolo se suman los $p_v>0$ (convención $0\\log 0=0$).")
    nb.code(TODO1)
    nb.md("## Paso 2 · TODO 2-3: reglas de parcheo y calibración del umbral")
    nb.code(TODO2)
    nb.md(hint(1, "Regla global: `s = H > theta` y fuerza `s[0] = True`. Cuidado: no modifiques `H` en sitio (`s` es un array nuevo).") + "\n\n" +
          hint(2, "Regla monótona: construye `d` con `d[0] = np.inf` y `d[1:] = H[1:] - H[:-1]`; `s = d > theta_r`; `s[0] = True`."))
    nb.code(TODO3)
    nb.md(hint(1, "Bisección: en cada iteración `mid = (lo+hi)/2`, calcula `ps = len(H) / fn(H, mid).sum()`. Si `ps` es MAYOR que el objetivo hay pocos parches: baja el umbral (`hi = mid`); si no, sube (`lo = mid`).") + "\n\n" +
          hint(2, "`for _ in range(iters): mid = (lo+hi)/2; if len(H)/fn(H, mid).sum() > objetivo: hi = mid  else: lo = mid` y devuelve `(lo+hi)/2`. No olvides la función `longitudes` (dada en la solución) si la necesitas."))
    nb.code(FLOW_ENT)
    nb.md(obs("Los dos umbrales (global y monótono) son distintos pero producen el mismo tamaño medio de parche; la diferencia está en **dónde** cortan. Compáralos mirando las longitudes en la solución de referencia."))

    nb.md("## Paso 3 · TODO 4: parcheo incremental\n\n$f_p(\\boldsymbol{x}_{<i}) = f_p(\\boldsymbol{x})_{<i}$ — mide la fracción de cortes aleatorios en que se cumple.")
    nb.code(TODO4)
    nb.md(hint(1, "Usa `random.Random(seed)`; para cada prueba elige `it`, un corte `i` entre 5 y `len-1` y calcula `full = f(it)` y `pref = f(prefijo)`.") + "\n\n" +
          hint(2, "El prefijo de un `bytes` es `it[:i]`; el de un `str` es `it.encode()[:i].decode('utf-8','ignore')`. Compara `np.array_equal(full[:len(pref)], pref)` y promedia."))
    nb.code(FLOW_INC)

    nb.md("## Paso 4 · TODO 5: robustez a erratas\n\nInyectamos una errata (una letra cambiada) en el 5 % de las palabras. Dos preguntas: ¿**se infla** el número de unidades (= coste)? ¿**cambia** la segmentación de las palabras que *no* tocamos (= inestabilidad de contexto)?")
    nb.code(TODO5)
    nb.md(hint(1, "`sc = f_seg(t)`, `sn = f_seg(ruido)` tienen la misma longitud (la errata no cambia el nº de bytes). `frag = suma(sn) / suma(sc)` sobre todos los textos.") + "\n\n" +
          hint(2, "Para la estabilidad itera `for (a, b) in palabras_ascii(t)`; salta las que estén en `malas`; cuenta `np.array_equal(sc[a:b], sn[a:b])`. Devuelve `{'frag': ..., 'estab': ok/tot}`."))
    nb.code("L_BPE = np.concatenate([[len(t) for t in TK.encode(d['text'][:MAX_CHARS]).tokens] for d in DOCS_VA])   # bytes por token (val)\n" + FLOW_ROB)

    nb.md("## Paso 5 · TODO 6: coste\n\nCon la fórmula de FLOPs/byte de la lección (config. ilustrativa tipo 8B), ¿qué tamaño de parche necesita BLT para gastar ≥ 25 % menos que un BPE industrial (4.4 bytes/token, vocabulario de 128K)? (Tu BPE de 512 tokens es mucho más pequeño que el industrial: por eso la referencia se fija a 4.4.)")
    nb.code(TODO6)
    nb.md(hint(1, "Recorre `grid` de menor a mayor `ps` y devuelve el primero que cumpla `flops_por_byte('blt', ps=ps) <= (1-ahorro) * flops_por_byte('bpe', bpt=bpt)`."))
    nb.code(FLOW_COST)
    nb.code(PLOT)

    nb.md("## Paso 6 · Conclusión y rúbrica\n\nEscribe tu recomendación en `CONCLUSION` (≥ 300 caracteres): ¿qué ventajas/limitaciones ves frente a BPE? ¿qué **no** puedes concluir con este banco? (pista: no hemos entrenado un LM de parches en este proyecto, ni usamos datos reales ni varias semillas).")
    nb.code('CONCLUSION = ""   # TODO 7: escribe aquí tu nota técnica para el CTO (>= 300 caracteres)\n')
    nb.code("THR = " + repr(T) + "\n" + RUBRIC + "\nrubrica(RES)")

    nb.md("""---
## ⛔ SPOILER — intenta resolverlo primero

Debajo está la solución de referencia **completa y ejecutable**. Si la ejecutas, redefine todas las funciones y rellena `RES` y `CONCLUSION`.
Si tu versión ya pasa la rúbrica, compara estilo y casos borde (ceros en `p`, prefijos vacíos, palabras con acentos).
""")
    nb.md("### Solución de referencia")
    for src in [SOL1, SOL2, SOL3, SOL4, SOL5, SOL6]:
        nb.code(src)
    nb.code(FLOW_ENT + "\n" + FLOW_INC)
    nb.code(FLOW_ROB + "\n" + FLOW_COST)
    nb.code(PLOT)
    nb.code(r'''CONCLUSION = (
    "Recomendación: no sustituir BPE todavía para el generativo de Políglota; sí seguir de cerca los parches por entropía. "
    f"A tamaño de unidad similar (~4.5 bytes), el parcheo por entropía es incremental por construcción ({RES['inc_ent']*100:.0f} %), mientras que BPE no lo es ({RES['inc_bpe']*100:.0f} %). "
    f"Ante un 5 % de erratas la segmentación por entropía infla las unidades un {100*(RES['rob_ent']['frag']-1):.1f} % (BPE: {100*(RES['rob_bpe']['frag']-1):.1f} %) y mantiene la segmentación del "
    f"{RES['rob_ent']['estab']*100:.1f} % de las palabras intactas (BPE con pre-tokenización: {RES['rob_bpe']['estab']*100:.1f} %): la dependencia del contexto previo es real pero pequeña aquí. "
    f"Para ahorrar un 25 % de FLOPs/byte frente a un BPE industrial haría falta un parche medio de ~{RES['ps_25']:.1f} bytes. "
    "Limitaciones: modelo de entropía n-grama, corpus pequeño/sintético, una semilla, sin entrenar el LM de parches ni medir bpb ni latencia; "
    "los FLOPs son una fórmula ilustrativa. Siguiente paso: repetir con datos reales y semillas, y medir bpb con un MiniBLT a FLOPs iguales."
)
rubrica(RES)''')

    nb.md("""## Retos extra (nivel experto)

1. Sustituye la tabla n-grama por el **transformer diminuto de la lección** como modelo de entropía y compara F1 de fronteras con las del n-grama.
2. Implementa el **reinicio del contexto en saltos de línea** (BLT §4.4) y mide cuánto cambia el tamaño medio de parche en texto con mucha repetición.
3. Prueba **orden 2, 3, 5 y 6** del n-grama: ¿cómo cambian el bpb del modelo de entropía y la calidad de las fronteras (precisión/recall frente a inicios de palabra)?
4. Mide la estabilidad con **cambios de mayúsculas** y con **espacios dobles** en vez de erratas: ¿qué segmentador sufre más?
5. Escribe un `ParchesEntropicosDataset` que devuelva (bytes, inicios) listos para alimentar el MiniBLT de la lección.

## Reflexión

* ¿Qué significa para un servicio de búsqueda como Políglota que la segmentación de una palabra **dependa del contexto previo**? (cachés, deduplicación, índices léxicos).
* ¿Qué parte de la fragilidad ante erratas que mediste en el módulo 05 es culpa del **vocabulario** y cuál de la **segmentación**?
* ¿Qué experimento harías, con presupuesto de una semana de GPU, para decidir si BLT merece entrar en la hoja de ruta de Políglota?
* ¿Cómo se conecta con el módulo 07? (la frontera de parche pasa de heurística externa a algo que se **entrena**).
""")
    nb.save(os.path.join(mod_dir, "06_proyecto_tokenizer_free_bytes_blt.ipynb"))
