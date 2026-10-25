"""Proyecto del módulo 07: cambiar el tokenizer de un modelo pequeño. build() lo llama build_07.py."""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from nbbuild import Notebook  # noqa: E402
import a3_common as C  # noqa: E402
import _a3_src07 as S  # noqa: E402

# Umbrales de la rúbrica: calibrados con lo MEDIDO por la solución de referencia (corpus sintético, FAST_DEV_RUN=True).
T = {
    "fert_min": 1.6,            # bytes/token de B dividido por el de A, sobre ES (val)
    "mejora_cero_shot": 0.0,    # bpb0(FVT) <= bpb0(aleatoria) - mejora_cero_shot
    "bpb_final_max": 1.0,       # bpb en ES tras la adaptación con la mejor init (<= medido + margen)
    "regresion_max": 0.30,      # aumento relativo máximo de bpb en EN+código tras adaptarse al ES
}

GIVEN_TT = S.TT_DATA.split("print(f\"vocab A=")[0]

# En el proyecto el modelo base y las utilidades ya vienen dados
SPARSEMAX_AUX = S.TT_INITS.split("def init_aleatoria")[0] + "\n" + S.TT_AUX.split("def init_focus")[0]
BASE_FN = S.TT_MODEL

TODO1 = r'''
def init_media(E_A, tkA, tkB):
    """Matriz [V_B, d]: los tokens COMPARTIDOS se copian; los NUEVOS reciben la media de todas las filas de E_A."""
    E, nuevo = base_copia(E_A, tkA, tkB)          # E: [V_B, d] con los compartidos copiados; `nuevo`: índices por inicializar
    # TODO 1: rellena E[nuevo] con la media de E_A sobre el vocabulario antiguo
    raise NotImplementedError("TODO 1")
'''
SOL1 = r'''
def init_media(E_A, tkA, tkB):
    E, nuevo = base_copia(E_A, tkA, tkB)
    E[nuevo] = E_A.mean(0); return E
'''
TODO2 = r'''
def init_fvt(E_A, tkA, tkB):
    """Fast Vocabulary Transfer: cada token nuevo = media de los embeddings de su descomposición con el tokenizer ANTIGUO."""
    E, nuevo = base_copia(E_A, tkA, tkB); VB = vocab_ordenado(tkB)
    # TODO 2: para cada i en `nuevo`: ids = descomposicion(tkA, VB[i])  ->  E[i] = media de E_A[ids]
    raise NotImplementedError("TODO 2")
'''
SOL2 = r'''
def init_fvt(E_A, tkA, tkB):
    E, nuevo = base_copia(E_A, tkA, tkB); VB = vocab_ordenado(tkB)
    for i in nuevo:
        E[i] = E_A[descomposicion(tkA, VB[i])].mean(0)
    return E
'''
TODO3 = r'''
def init_focus(E_A, tkA, tkB, aux_B):
    """FOCUS-lite: cada token nuevo = combinación sparsemax de los tokens COMPARTIDOS.
    aux_B: [V_B, k] embeddings auxiliares NORMALIZADOS de los tokens de B (entrenados con texto del destino)."""
    E, nuevo = base_copia(E_A, tkA, tkB); vA, VB = tkA.get_vocab(), vocab_ordenado(tkB)
    comp = [i for i, t in enumerate(VB) if t in vA]            # índices (en B) de los tokens compartidos
    # TODO 3: para cada i en `nuevo`: w = sparsemax(aux_B[comp] @ aux_B[i])  ->  E[i] = suma_j w_j * E[comp[j]]
    raise NotImplementedError("TODO 3")
'''
SOL3 = r'''
def init_focus(E_A, tkA, tkB, aux_B):
    E, nuevo = base_copia(E_A, tkA, tkB); vA, VB = tkA.get_vocab(), vocab_ordenado(tkB)
    comp = [i for i, t in enumerate(VB) if t in vA]; Ec = E[comp]; Ac = aux_B[comp]
    for i in nuevo:
        w = sparsemax(Ac @ aux_B[i])
        E[i] = (w[:, None] * Ec).sum(0) if w.sum() > 0 else E_A.mean(0)
    return E
'''
TODO4 = r'''
def adapta(base, E_new, ids, K1, K2, evalfn, log_cada=25):
    """Instala E_new como matriz de embeddings (instala_vocab), entrena K1 pasos SOLO embeddings (lr 3e-3) y luego K2 pasos
    con todo el modelo (lr 1e-3). Devuelve (modelo, curva) con curva = [(paso, bpb), ...] (usa entrena_lm con log_cada y evalfn)."""
    m = instala_vocab(base, E_new)
    # TODO 4a: congela todos los parámetros salvo m.get_input_embeddings().weight (la cabeza está atada) y entrena K1 pasos
    # TODO 4b: descongela todo y entrena K2 pasos; concatena las curvas (desplaza los pasos de la 2ª fase en K1)
    raise NotImplementedError("TODO 4")
'''
SOL4 = r'''
def adapta(base, E_new, ids, K1, K2, evalfn, log_cada=25):
    m = instala_vocab(base, E_new)
    for p_ in m.parameters(): p_.requires_grad = False
    m.get_input_embeddings().weight.requires_grad = True
    c1 = entrena_lm(m, ids, K1, lr=3e-3, params=[m.get_input_embeddings().weight], log_cada=log_cada, evalfn=evalfn)
    for p_ in m.parameters(): p_.requires_grad = True
    c2 = entrena_lm(m, ids, K2, lr=1e-3, log_cada=log_cada, evalfn=evalfn)
    return m, c1[:-1] + [(s + K1, v) for s, v in c2]
'''

TESTS = r'''
# --- Comprobaciones unitarias de tus inicializaciones (no las cambies) ---
def comprueba_inits():
    ok = {}
    E_A = BASE.get_input_embeddings().weight.detach().cpu().float(); vA = TK_A.get_vocab(); VB = vocab_ordenado(TK_B)
    comp = next(i for i, t in enumerate(VB) if t in vA and len(t) > 1); nue = next(i for i, t in enumerate(VB) if t not in vA and len(t) > 2)
    try:
        Em = init_media(E_A, TK_A, TK_B)
        ok["media: compartidos copiados"] = bool(torch.allclose(Em[comp], E_A[vA[VB[comp]]]))
        ok["media: nuevos = media de E_A"] = bool(torch.allclose(Em[nue], E_A.mean(0), atol=1e-6))
    except NotImplementedError: pass
    try:
        Ef = init_fvt(E_A, TK_A, TK_B); ids = descomposicion(TK_A, VB[nue])
        ok["FVT: nuevo = media de su descomposición"] = bool(torch.allclose(Ef[nue], E_A[ids].mean(0), atol=1e-6))
    except NotImplementedError: pass
    try:
        Eo = init_focus(E_A, TK_A, TK_B, aux_B)
        ok["FOCUS: compartidos copiados"] = bool(torch.allclose(Eo[comp], E_A[vA[VB[comp]]]))
        ok["FOCUS: nuevos dentro de la envolvente convexa (norma <= máx de los compartidos)"] = bool(Eo[nue].norm() <= E_A.norm(dim=1).max() + 1e-4)
    except NotImplementedError: pass
    for k, v in ok.items(): print("✅" if v else "❌", k)
    if not ok: print("Pendiente: implementa los TODO 1-3")
    return ok
'''

SETUP_RUN = r'''
E_A = BASE.get_input_embeddings().weight.detach().cpu().float()
IDS_B_TGT = ids_stream(TK_B, TGT); IDS_A_TGT = ids_stream(TK_A, TGT)
aux_B = aux_embeddings(IDS_B_TGT, TK_B.get_vocab_size())
eval_B = lambda m: bpb(m, TK_B, VA_ES)
K1, K2 = (100, 200) if FAST_DEV_RUN else (500, 2000)
RES = {"bpb_A_sin_adaptar": bpb(BASE, TK_A, VA_ES),
       "fert": bytes_x_token(TK_B, VA_ES) / bytes_x_token(TK_A, VA_ES),
       "bpb_src_antes": bpb(BASE, TK_A, VA_SRC)}
print(f"modelo base con A sobre ES (sin adaptar): {RES['bpb_A_sin_adaptar']:.3f} bpb | fertilidad B/A = {RES['fert']:.2f}x bytes por token")
comprueba_inits()
'''

FLOW = r'''
# --- Flujo (no lo cambies): corre las inicializaciones y la adaptación ---
try:
    torch.manual_seed(SEED)
    E_rand = torch.randn(TK_B.get_vocab_size(), E_A.shape[1]) * E_A.std()                    # control: todo aleatorio (sin copiar compartidos)
    m_r, c_r = adapta(BASE, E_rand, IDS_B_TGT, K1, K2, eval_B)
    RES["curva_aleatoria"] = c_r; RES["bpb0_aleatoria"] = c_r[0][1]
    RES["modelos"], RES["E"] = {}, {}
    for nombre, E_new in [("media", init_media(E_A, TK_A, TK_B)), ("FVT", init_fvt(E_A, TK_A, TK_B)), ("FOCUS-lite", init_focus(E_A, TK_A, TK_B, aux_B))]:
        m, c = adapta(BASE, E_new, IDS_B_TGT, K1, K2, eval_B)
        RES["modelos"][nombre] = m; RES["E"][nombre] = E_new; RES.setdefault("curvas", {})[nombre] = c
        print(f"{nombre:11s} bpb 0-shot={c[0][1]:.3f} | tras {K1} pasos (emb) = {[v for s, v in c if s == K1][0]:.3f} | final={c[-1][1]:.3f}")
    print(f"{'aleatoria':11s} bpb 0-shot={c_r[0][1]:.3f} | final={c_r[-1][1]:.3f}")
    RES["mejor"] = min(RES["curvas"], key=lambda n: RES["curvas"][n][-1][1])
    RES["bpb_final"] = RES["curvas"][RES["mejor"]][-1][1]
    RES["bpb0_fvt"] = RES["curvas"]["FVT"][0][1]
except NotImplementedError as e:
    print("Pendiente:", e)
'''

REGRESION = r'''
# --- Regresión: ¿cuánto olvida el modelo adaptado del inglés/código? (se mide con el tokenizer B sobre EN+código) ---
if "mejor" in RES:
    RES["bpb_src_despues"] = bpb(RES["modelos"][RES["mejor"]], TK_B, VA_SRC)
    m0 = instala_vocab(BASE, RES["E"][RES["mejor"]])           # misma init, SIN ajuste: referencia justa
    RES["bpb_src_B_sin_adaptar"] = bpb(m0, TK_B, VA_SRC)
    print(f"EN+código con tokenizer B: sin ajustar {RES['bpb_src_B_sin_adaptar']:.3f} -> ajustado al ES {RES['bpb_src_despues']:.3f}")
else:
    print("Completa los TODO para ver la regresión.")
'''

PLOT = r'''
if "curvas" in RES:
    fig, ax = plt.subplots(figsize=(8, 4))
    for n, c in RES["curvas"].items(): ax.plot([s for s, _ in c], [v for _, v in c], lw=2, label=n)
    ax.plot([s for s, _ in RES["curva_aleatoria"]], [v for _, v in RES["curva_aleatoria"]], "k--", label="aleatoria")
    ax.axhline(RES["bpb_A_sin_adaptar"], color="crimson", ls=":", label="base con tokenizer A (sin adaptar)")
    ax.axvline(K1, color="gray", lw=.6, ls=":"); ax.set_ylim(top=min(ax.get_ylim()[1], 6)); ax.set_xlabel("pasos"); ax.set_ylabel("bpb en ES (val)")
    ax.set_title("Adaptación corta tras cambiar de tokenizer"); ax.legend(fontsize=8); plt.show()
else:
    print("Completa los TODO para ver las curvas.")
'''

RUBRIC = r'''
def rubrica(RES, th=THR):
    filas = []
    chk = lambda n, ok, d: filas.append((n, ok, d))
    ok_u = comprueba_inits()
    chk("R1 tus inicializaciones pasan las comprobaciones unitarias (media, FVT, FOCUS)", len(ok_u) >= 5 and all(ok_u.values()), f"{sum(ok_u.values())}/{len(ok_u)}")
    chk("R2 el tokenizer nuevo reduce los tokens en ES (fertilidad B/A >= %.1fx)" % th["fert_min"], RES.get("fert", 0) >= th["fert_min"], f"{RES.get('fert')}")
    chk("R3 FVT mejora a la init aleatoria en cero-shot (bpb0 FVT <= aleatoria - %.2f)" % th["mejora_cero_shot"],
        RES.get("bpb0_fvt") is not None and RES["bpb0_fvt"] <= RES["bpb0_aleatoria"] - th["mejora_cero_shot"], f"FVT={RES.get('bpb0_fvt')} vs aleatoria={RES.get('bpb0_aleatoria')}")
    chk("R4 tras la adaptación, bpb en ES <= %.2f con la mejor init" % th["bpb_final_max"], RES.get("bpb_final", 99) <= th["bpb_final_max"], f"{RES.get('bpb_final')} ({RES.get('mejor')})")
    chk("R5 la adaptación mejora al modelo base sin adaptar con A (menos bpb en ES)", RES.get("bpb_final", 99) < RES.get("bpb_A_sin_adaptar", 0), f"{RES.get('bpb_final')} < {RES.get('bpb_A_sin_adaptar')}")
    reg = None if "bpb_src_despues" not in RES else RES["bpb_src_despues"] / RES["bpb_src_B_sin_adaptar"] - 1
    chk("R6 regresión en EN+código (aumento relativo de bpb) <= %d %%" % (th["regresion_max"] * 100), reg is not None and reg <= th["regresion_max"], f"{reg}")
    chk("R7 conclusión escrita (>= 300 caracteres) en CONCLUSION", len(globals().get("CONCLUSION", "")) >= 300, f"{len(globals().get('CONCLUSION', ''))} caracteres")
    for n, ok, d in filas: print(("✅" if ok else "❌"), n, "|", d)
    print(f"\n{sum(o for _, o, _ in filas)}/{len(filas)} criterios")
'''


def build(lesson_rel, proj_rel, mod_dir, slug):
    nb = Notebook("Proyecto 07 · Cambia el tokenizer de un modelo pequeño", colab_path=proj_rel, gpu=False)
    obs, details, hint = C.observe, C.details, C.hint
    nb.md(nb.badge() + r"""

# Proyecto 07 · Cambia el tokenizer de un modelo pequeño y mide qué pierdes (y qué ganas)

| | |
|---|---|
| **Nivel** | 🔴 Experto |
| **Duración estimada** | ≈ 2.5 h |
| **GPU recomendada** | `FAST_DEV_RUN=True`: CPU (≈ 5-8 min). Modo completo: **L4** (≈ 6-10 unidades de Colab, estimación) con **GPT-2 small** real (requiere acceso al hub de Hugging Face) |
| **Prerrequisitos** | Lección 07 (tokenizer transfer, FVT, FOCUS, bpb), módulos 02-04 |

## Contexto de negocio

Eres ML engineer en **Políglota Labs**. Tenéis un modelo pequeño preentrenado con **inglés y código** y un tokenizer BPE entrenado en eso: en español produce ~2x más tokens por byte
(más latencia y coste por consulta). El CTO pregunta: *«¿podemos cambiarle el tokenizer por uno entrenado en español sin reentrenar de cero, y cuánto calidad perdemos?»*
Tu trabajo: implementar **tres inicializaciones** del vocabulario nuevo (media, FVT, FOCUS-lite), hacer un **ajuste corto** y **medir bits por byte antes y después**, con un **control de regresión**
en inglés/código.

**Conexión.** Módulo anterior (06) y la primera mitad de la lección 07: ¿tokenizer-free o transfer? Aquí haces la opción pragmática. Módulo siguiente (09): la capa de embedding y la extensión de vocabulario con tokens de dominio — las mismas ideas aplicadas a un encoder de Políglota.

## Dataset
Corpus Políglota vía `carga_corpus()` (módulo 00). *Origen:* inglés + código; *destino:* español. Si imprime «SINTÉTICO», los valores absolutos cambian pero el protocolo es el mismo.

## Entregables y criterios de evaluación

1. `init_media`, `init_fvt`, `init_focus` (TODO 1-3) que pasen las comprobaciones unitarias.
2. `adapta` (TODO 4): ajuste en dos fases (solo embeddings → todo el modelo).
3. Tabla/curvas de bpb en español: **cero-shot**, **tras la fase de embeddings** y **final**, para cada init y para una init aleatoria.
4. **Regresión** en inglés/código tras adaptar al español.
5. Una **conclusión** en `CONCLUSION` (≥ 300 caracteres) con recomendación y límites.

| Criterio | Umbral (calibrado con la solución de referencia) |
|---|---|
| R1 · comprobaciones unitarias de las 3 inits | todas ✅ |
| R2 · fertilidad: bytes/token de B ÷ bytes/token de A en ES | ≥ """ + f"{T['fert_min']}x" + r""" |
| R3 · bpb cero-shot FVT vs aleatoria | FVT ≤ aleatoria − """ + f"{T['mejora_cero_shot']}" + r""" |
| R4 · bpb final en ES con la mejor init | ≤ """ + f"{T['bpb_final_max']}" + r""" |
| R5 · adaptado vs modelo base sin adaptar (tokenizer A) | menos bpb |
| R6 · regresión en EN+código (aumento relativo de bpb) | ≤ """ + f"{int(T['regresion_max']*100)} %" + r""" |
| R7 · conclusión | ≥ 300 caracteres |

> Los umbrales salen de lo **medido** por la solución (FAST_DEV, corpus sintético, una semilla); con datos reales o GPT-2 real, vuelve a medir y ajusta.
""")
    nb.code(S.PIP)
    nb.code(C.SETUP_COMMON + S.SETUP_EXTRA + S.SETUP7)
    for c in C.corpus_cells():
        nb.code(c)
    nb.md("## Paso 0 · Datos, tokenizers y modelo base (dados)\n\nPartimos el corpus (módulo 06), entrenamos el tokenizer A (inglés + código) y el B (español), y preentrenamos —o cargamos— el modelo base.")
    nb.code(S.DATA)
    nb.code(S.BPE_FN)
    nb.code(GIVEN_TT)
    nb.code(BASE_FN)
    nb.md("Utilidades dadas: `sparsemax`, `descomposicion`, `base_copia` (copia los tokens compartidos y devuelve los índices nuevos), `aux_embeddings` (PPMI+SVD) e `instala_vocab` (sustituye la matriz de embeddings del modelo).")
    nb.code(SPARSEMAX_AUX + "\n\ndef instala_vocab(base, E_new):\n    m = copy.deepcopy(base); m.resize_token_embeddings(E_new.shape[0], mean_resizing=False)\n    m.get_input_embeddings().weight.data.copy_(E_new.to(device)); m.tie_weights(); return m\n")

    nb.md("## Paso 1 · TODO 1: inicialización por la media\n\nLos tokens **compartidos** se copian (ya lo hace `base_copia`); los **nuevos** reciben la media de $E_a$. Es la línea base de `transformers`.")
    nb.code(TODO1)
    nb.md(hint(1, "`E[nuevo] = ...` con `E_A.mean(0)` (vector de dimensión d). Pytorch hace *broadcasting* sobre las filas indexadas."))
    nb.md("## Paso 2 · TODO 2: FVT (media de la descomposición)\n\nPara un token nuevo `t`, el tokenizer antiguo lo parte en subtokens: `descomposicion(tkA, VB[i])` devuelve sus ids. El embedding de `t` es la media de los embeddings de esos ids.")
    nb.code(TODO2)
    nb.md(hint(1, "Es un bucle `for i in nuevo:`; `E_A[ids]` con `ids` una lista de enteros devuelve una matriz [len(ids), d].") + "\n\n" +
          hint(2, "`E[i] = E_A[descomposicion(tkA, VB[i])].mean(0)`."))
    nb.md("## Paso 3 · TODO 3: FOCUS-lite (sparsemax sobre los tokens compartidos)\n\nLos pesos salen de la similitud en el espacio auxiliar `aux_B` (ya normalizado): `Ac @ aux_B[i]` son cosenos entre el token nuevo `i` y cada token compartido. `sparsemax` los convierte en pesos que suman 1 con muchos ceros exactos.")
    nb.code(TODO3)
    nb.md(hint(1, "Construye `Ec = E[comp]` (embeddings de compartidos en el orden de `comp`) y `Ac = aux_B[comp]` una vez, fuera del bucle.") + "\n\n" +
          hint(2, "Dentro del bucle: `w = sparsemax(Ac @ aux_B[i])`; `E[i] = (w[:, None] * Ec).sum(0)`. Si `w.sum()==0` (no debería) usa la media."))
    nb.md("## Paso 4 · TODO 4: ajuste en dos fases\n\nPrimero entrenas **solo la matriz de embeddings** (barato; la cabeza está atada), luego **todo** el modelo. `entrena_lm(model, ids, pasos, lr, params, log_cada, evalfn)` devuelve la curva `[(paso, bpb)]`.")
    nb.code(TODO4)
    nb.md(hint(1, "Para congelar: `for p in m.parameters(): p.requires_grad = False` y luego `m.get_input_embeddings().weight.requires_grad = True`; pasa `params=[m.get_input_embeddings().weight]` al optimizador.") + "\n\n" +
          hint(2, "Fase 1: `c1 = entrena_lm(m, ids, K1, lr=3e-3, params=[W], log_cada=log_cada, evalfn=evalfn)`. Fase 2: reactiva `requires_grad` en todo y `c2 = entrena_lm(m, ids, K2, lr=1e-3, ...)`. Devuelve `c1[:-1] + [(s + K1, v) for s, v in c2]` (quita el último punto de c1: es el primero de c2)."))
    nb.code(TESTS)
    nb.code(SETUP_RUN)
    nb.code(FLOW)
    nb.code(REGRESION)
    nb.code(PLOT)

    nb.md("## Paso 5 · Conclusión y rúbrica\n\nEscribe tu recomendación para el CTO: ¿cambiar el tokenizer compensa? ¿qué init usarías? ¿qué **no** puedes concluir con este banco (una semilla, modelo diminuto, datos sintéticos, ~300 pasos)?")
    nb.code('CONCLUSION = ""   # TODO 5: tu nota técnica (>= 300 caracteres)\n')
    nb.code("THR = " + repr(T) + "\n" + RUBRIC + "\nrubrica(RES)")

    nb.md("""---
## ⛔ SPOILER — intenta resolverlo primero

Debajo está la solución de referencia **completa y ejecutable**: redefine las funciones y vuelve a correr el flujo.
""")
    nb.md("### Solución de referencia")
    for src in [SOL1, SOL2, SOL3, SOL4]:
        nb.code(src)
    nb.code(SETUP_RUN)
    nb.code(FLOW + "\n" + REGRESION)
    nb.code(PLOT)
    nb.code(r'''CONCLUSION = (
    f"Recomendación: cambiar el tokenizer compensa si el español es tráfico relevante: los tokens por byte bajan a ~{1/RES['fert']:.2f}x (cada byte necesita menos pasos del transformer). "
    f"Mejor init en nuestro banco: {RES['mejor']}, con bpb en ES de {RES['bpb_final']:.3f} tras el ajuste frente a {RES['bpb_A_sin_adaptar']:.3f} del modelo base sin adaptar (tokenizer A). "
    f"Cero-shot, FVT = {RES['bpb0_fvt']:.3f} vs aleatoria = {RES['bpb0_aleatoria']:.3f} bpb. La regresión en inglés/código con el tokenizer nuevo fue de {RES['bpb_src_despues']/RES['bpb_src_B_sin_adaptar']-1:+.1%}. "
    "Límites: modelo diminuto preentrenado por nosotros, corpus pequeño/sintético, una semilla y ~300 pasos; no sabemos si las diferencias entre inits se mantienen con GPT-2 real ni con datos de Wikipedia. "
    "Siguiente paso: repetir en modo completo (L4) con GPT-2 small, varias semillas y una evaluación de tarea real (no solo bpb)."
)
rubrica(RES)''')
    nb.md("""## Retos extra (nivel experto)

1. Implementa **WECHSEL-lite** (Procrustes entre espacios auxiliares + softmax con τ=0.1 y k=10) y compáralo con FOCUS-lite.
2. Mide cuántos pasos de ajuste necesita cada init para **igualar** al control «seguir con A» (curva de bpb vs pasos): ¿cuál «ahorra» más?
3. Añade **ruido de la covarianza** (Hewitt) a la init por media y mide si acelera la separación de los tokens nuevos.
4. Prueba un vocabulario B **más grande** (p. ej. 1536) y otro **más pequeño**: ¿cómo cambian fertilidad, bpb cero-shot y bpb final?
5. En modo completo (L4): usa **GPT-2 small** real con tokenizer B de 24 000 tokens entrenado en ES+código; compara con `resize_token_embeddings(mean_resizing=True)` de Hugging Face.
6. **ZeTT-mini:** entrena una MLP que prediga el embedding de un token a partir de la media de su descomposición y úsala como init.

## Reflexión

* ¿Qué parte del beneficio viene de **tokens más largos** (eficiencia) y qué parte de una mejor **calidad** del modelo? ¿Cómo lo separarías?
* ¿Qué haría falta para extender esto a un **embedder** de Políglota (encoder + pooling)? ¿Qué cambia si no hay *weight tying*?
* ¿Cuántos tokens de ajuste pagarías para cerrar el hueco? (ZeTT reporta < 1B tokens para decodificadores de 7B.)
* ¿Cómo comunicarías al CTO que *«la pérdida bajó»* no es una prueba de mejora tras un cambio de tokenizer?
""")
    nb.save(os.path.join(mod_dir, "07_proyecto_hnet_tokenizer_transfer.ipynb"))
