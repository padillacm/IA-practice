"""Builder del módulo 15 · Experimentación online para sistemas de recomendación.

Ejecutar desde la raíz del repo:  python recsys-course/_tools/builders/build_15.py
Genera:
  recsys-course/15_online_experimentation/15_online_experimentation.ipynb           (lección)
  recsys-course/15_online_experimentation/15_proyecto_ab_interleaving.ipynb         (proyecto)
"""
import os
import sys

sys.path.insert(0, "recsys-course/_tools")
from nbbuild import Notebook  # noqa: E402

MOD = "15_online_experimentation"
os.makedirs(f"recsys-course/{MOD}", exist_ok=True)
LESSON = f"recsys-course/{MOD}/{MOD}.ipynb"
PROJECT = f"recsys-course/{MOD}/15_proyecto_ab_interleaving.ipynb"

SETUP = r'''
import warnings, time, math, hashlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.power import NormalIndPower, TTestIndPower

warnings.filterwarnings("ignore")
seed = 42
rng = np.random.default_rng(seed)
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3,
                     "axes.spines.top": False, "axes.spines.right": False})
C = {"ctrl": "#9e9e9e", "trt": "#0072b2", "cuped": "#009e73", "cupac": "#cc79a7", "il": "#d55e00",
     "naive": "#c53030", "delta": "#2b6cb0", "seq": "#e69f00"}

FAST_DEV_RUN = True        # True: ~5-8 min en CPU; False: más repeticiones Monte Carlo (~20 min)
R_SIM = 300 if FAST_DEV_RUN else 1500   # nº de experimentos simulados en los estudios Monte Carlo
print("FAST_DEV_RUN =", FAST_DEV_RUN)
'''

DRAW = r'''
def box(ax, xy, w, h, text, fc="#e8f1fb", ec="#2b6cb0", fs=10):
    ax.add_patch(FancyBboxPatch(xy, w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.5))
    ax.text(xy[0] + w / 2, xy[1] + h / 2, text, ha="center", va="center", fontsize=fs)

def arrow(ax, p0, p1, text="", color="#444", fs=9, rad=0.0):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=15, color=color, lw=1.6,
                                 connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 + 0.1, text, ha="center", va="bottom", fontsize=fs, color=color)
'''

# Funciones estadísticas compartidas (lección + proyecto)
STATS_LIB = r'''
def welch_test(y_t, y_c, alpha=0.05):
    """Diferencia de medias, IC (Welch) y p-valor."""
    d = y_t.mean() - y_c.mean()
    se = np.sqrt(y_t.var(ddof=1) / len(y_t) + y_c.var(ddof=1) / len(y_c))
    z = stats.norm.ppf(1 - alpha / 2)
    p = stats.ttest_ind(y_t, y_c, equal_var=False).pvalue
    return dict(diff=d, se=se, lo=d - z * se, hi=d + z * se, p=p, lift=d / y_c.mean())

def cuped_adjust(y, x, theta=None):
    """CUPED: y - θ (x - mean(x)), θ = cov(y,x)/var(x) estimado con TODOS los usuarios (ambos grupos)."""
    if theta is None:
        theta = np.cov(y, x)[0, 1] / np.var(x, ddof=1)
    return y - theta * (x - x.mean()), theta

def srm_test(n_t, n_c, expected_ratio=0.5):
    """Sample Ratio Mismatch: chi-cuadrado de bondad de ajuste."""
    n = n_t + n_c
    return stats.chisquare([n_t, n_c], f_exp=[n * expected_ratio, n * (1 - expected_ratio)]).pvalue

def assign_bucket(user_ids, salt: str, n_buckets: int = 1000):
    """Asignación determinista por hash (como en producción): mismo usuario → mismo grupo siempre."""
    return np.array([int(hashlib.md5(f"{salt}:{u}".encode()).hexdigest()[:8], 16) % n_buckets for u in user_ids])

def team_draft_interleave(list_a, list_b, k, rng):
    """Team Draft Interleaving (Radlinski et al., 2008). Devuelve (lista, equipo) con equipo ∈ {0=A, 1=B}."""
    out, team, used = [], [], set()
    ia = ib = 0; n_a = n_b = 0
    while len(out) < k and (ia < len(list_a) or ib < len(list_b)):
        pick_a = (n_a < n_b) or (n_a == n_b and rng.random() < 0.5)   # el equipo con menos picks elige; empate → moneda
        src, idx = (list_a, ia) if pick_a else (list_b, ib)
        while idx < len(src) and src[idx] in used:
            idx += 1
        if idx >= len(src):                    # ese ranker se quedó sin ítems: elige el otro
            pick_a = not pick_a
            src, idx = (list_a, ia) if pick_a else (list_b, ib)
            while idx < len(src) and src[idx] in used:
                idx += 1
            if idx >= len(src):
                break
        out.append(src[idx]); used.add(src[idx]); team.append(0 if pick_a else 1)
        if pick_a: ia = idx + 1; n_a += 1
        else: ib = idx + 1; n_b += 1
    return out, team

def msprt_pvalues(diffs, var_diffs, tau2):
    """p-valores siempre válidos (mSPRT con mezcla normal N(0, τ²)) para una secuencia de
    estimaciones de la diferencia de medias y sus varianzas (Johari et al., 2017/2022)."""
    V = np.asarray(var_diffs); d = np.asarray(diffs)
    lam = np.sqrt(V / (V + tau2)) * np.exp(tau2 * d ** 2 / (2 * V * (V + tau2)))
    return np.minimum.accumulate(np.minimum(1.0, 1.0 / lam))
'''


# =============================================================================
# LECCIÓN
# =============================================================================
def build_lesson() -> None:
    nb = Notebook("Módulo 15 · Experimentación online", colab_path=LESSON)

    nb.md(f"""
{nb.badge()}

# Módulo 15 · Experimentación online para sistemas de recomendación

**Nivel:** 🟠 Avanzado → 🔴 Experto (interferencia, surrogate index, sequential testing)
**Duración estimada:** 5–6 h (lección) + 4 h (proyecto)
**Hardware:** CPU estándar de Colab (todo son simulaciones NumPy/SciPy/statsmodels). **Unidades de Colab:** < 1.
**Prerrequisitos:** 02 (evaluación offline, bootstrap), 13 (métricas beyond-accuracy), 14 (bandits y OPE).

> 💡 Ninguna métrica offline (módulo 02) ni ninguna OPE (módulo 14) decide un lanzamiento en Netflix, Spotify o Booking: decide un **experimento controlado online**. Este módulo te enseña a diseñarlo, a no engañarte al analizarlo y a resolver los problemas propios de recomendación: efectos que cambian con el tiempo, usuarios que interactúan entre sí, y métricas de negocio que tardan meses en moverse.
""")

    nb.md("""
## 🎯 Objetivos de aprendizaje

1. **Diseñar** un A/B test para un recomendador: unidad de aleatorización, métrica principal, guardrails, tamaño muestral (power analysis) y MDE.
2. **Analizar** correctamente métricas de ratio con el **método delta** y detectar *Sample Ratio Mismatch* (SRM).
3. **Reducir la varianza** con CUPED y CUPAC y cuantificar la ganancia en tamaño muestral.
4. **Implementar** Team Draft Interleaving y **medir** su sensibilidad frente a un A/B, replicando el razonamiento del blog de Netflix (2017).
5. **Explicar y corregir** el problema del *peeking* con tests secuenciales (mSPRT / *always-valid*, group sequential).
6. **Diagnosticar** efectos novelty/primacy, interferencia en marketplaces de dos lados y efectos a largo plazo con un **surrogate index**.
7. **Estimar** efectos heterogéneos (HTE) y **aplicar** un diff-in-diff cuando no se puede aleatorizar.
""")

    nb.md("""
### 🗺️ Índice
1. Intuición: por qué experimentar y cómo se organiza un programa de experimentación
2. Fundamentos estadísticos: resultados potenciales, t-test y distribuciones reales de engagement
3. Unidad de aleatorización, métricas de ratio (método delta) y SRM
4. Potencia, tamaño muestral y MDE
5. Reducción de varianza: CUPED y CUPAC
6. Métricas: north-star, proxies, guardrails
7. Novelty y primacy
8. Interleaving (Team Draft) y su sensibilidad
9. Peeking y tests secuenciales
10. Interferencia y marketplaces de dos lados
11. Efectos a largo plazo y surrogate index
12. Efectos heterogéneos (HTE)
13. Cuasi-experimentos (diff-in-diff)
14. Herramientas · 🏭 Producción · 🧠 Secretos · ⚠️ Errores · Autoevaluación · Referencias
""")

    nb.code("!pip install -q statsmodels scipy  # ya vienen en Colab; la línea asegura versiones recientes")
    nb.code(SETUP)
    nb.code(DRAW)
    nb.code(STATS_LIB)

    # --------------------------------------------------------------- 1
    nb.md("""
---
## 1 · Intuición: por qué experimentar

Un nuevo ranker gana +3 % de NDCG@10 offline. ¿Lo lanzas? En la industria la respuesta es "**depende del A/B**", porque:

- La evaluación offline mide si predices bien **lo que el sistema antiguo mostró** (sesgo de exposición, módulo 01), no cómo reaccionarán los usuarios a **lo que mostrará el nuevo**.
- Lo que importa al negocio (retención, satisfacción, horas de visionado) no es lo que optimiza el modelo (clics, NDCG). La correlación offline–online es débil y hay que medirla, no suponerla (Gomez-Uribe & Hunt, 2015, describen que en Netflix las métricas offline sirven para filtrar y el A/B decide).
- Los efectos son **pequeños** (+0,1 %–1 % en métricas de engagement es un gran lanzamiento) y la variabilidad entre usuarios es **enorme**. Sin estadística seria, el ruido parece señal.

> 💡 Analogía con ML: un A/B test es un **conjunto de test con intervención**. La aleatorización es el equivalente a que train y test vengan de la misma distribución: garantiza que la única diferencia sistemática entre grupos es el tratamiento.

El ciclo de un experimento y la jerarquía de métricas:
""")

    nb.code(r'''
fig, axes = plt.subplots(1, 2, figsize=(15, 4.6), gridspec_kw={"width_ratios": [1.35, 1]})
ax = axes[0]; ax.set_xlim(0, 12); ax.set_ylim(0, 5); ax.axis("off")
steps = [("Hipótesis\n+ métrica\nprincipal", "#eef6ee", "#2f855a"), ("Diseño:\nunidad, n,\nMDE, duración", "#e8f1fb", "#2b6cb0"),
         ("Aleatorizar\n(hash + salt)\nA/A previo", "#e8f1fb", "#2b6cb0"), ("Correr\nsin peeking\n(o secuencial)", "#fdf2e9", "#c05621"),
         ("Analizar:\nSRM, delta,\nCUPED, HTE", "#fdf2e9", "#c05621"), ("Decidir:\nnorth-star +\nguardrails", "#fff5f5", "#c53030")]
for i, (txt, fc, ec) in enumerate(steps):
    x = 0.1 + i * 2.0; box(ax, (x, 1.9), 1.7, 1.5, txt, fc=fc, ec=ec, fs=9)
    if i < len(steps) - 1: arrow(ax, (x + 1.7, 2.65), (x + 2.0, 2.65))
arrow(ax, (11.0, 1.9), (1.0, 1.9), "aprendizaje → nueva hipótesis", rad=0.25)
ax.set_title("Ciclo de vida de un experimento online", fontsize=12)

ax = axes[1]; ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
levels = [("North-star / OEC\nretención, satisfacción a largo plazo", "#2b6cb0", 7.2),
          ("Proxies y surrogates\nhoras vistas, plays cualificados, días activos", "#4299e1", 4.9),
          ("Guardrails\nlatencia, errores de playback, cancelaciones, SRM", "#c05621", 2.6),
          ("Métricas de diagnóstico\nCTR por fila, cobertura, diversidad", "#a0aec0", 0.3)]
for i, (txt, col, y) in enumerate(levels):
    half = 1.3 + i * 1.15
    ax.add_patch(Polygon([[5 - half, y], [5 + half, y], [5 + half - 0.5, y + 2.1], [5 - half + 0.5, y + 2.1]], color=col, alpha=0.85))
    ax.text(5, y + 1.05, txt, ha="center", va="center", fontsize=8.5, color="white", weight="bold")
ax.set_title("Jerarquía de métricas (más arriba = más lenta y más importante)", fontsize=11)
plt.tight_layout(); plt.show()
''')

    # --------------------------------------------------------------- 2
    nb.md(r"""
---
## 2 · Fundamentos estadísticos

### 📐 Resultados potenciales (Neyman–Rubin)
Cada usuario $i$ tiene dos resultados potenciales: $Y_i(1)$ si ve el tratamiento (ranker nuevo) y $Y_i(0)$ si ve el control. Solo observamos uno. El **efecto medio del tratamiento** es $\tau = \mathbb{E}[Y(1) - Y(0)]$. Con asignación aleatoria $T_i \perp (Y_i(0), Y_i(1))$, la diferencia de medias es insesgada:

$$\hat\tau = \bar Y_T - \bar Y_C, \qquad \widehat{\mathrm{SE}}(\hat\tau) = \sqrt{\frac{s_T^2}{n_T} + \frac{s_C^2}{n_C}}.$$

Por el **teorema central del límite**, $\hat\tau$ es aproximadamente normal aunque $Y$ no lo sea → test $z$/Welch, IC $\hat\tau \pm 1{,}96\,\widehat{\mathrm{SE}}$.

**SUTVA** (*stable unit treatment value assumption*): el resultado de un usuario no depende del tratamiento de otros. En marketplaces y redes sociales **se rompe** (sección 10).

### Cómo son de verdad las métricas de engagement
Las horas vistas por usuario en 2 semanas tienen muchos ceros (gente que no entra) y una cola larga (los *heavy users*). La varianza la dominan unos pocos usuarios: por eso los A/B de recomendación necesitan cientos de miles de usuarios.
""")

    nb.code(r'''
def simulate_watch_hours(n, g, lift=0.0, engagement=None):
    """Horas vistas por usuario en 2 semanas: 25 % ceros + lognormal con cola larga.
    `lift` es un efecto multiplicativo del tratamiento sobre los usuarios activos."""
    if engagement is None:
        engagement = g.normal(1.6, 1.0, n)               # nivel latente de cada usuario (log-horas)
    active = g.random(n) > 0.25
    hours = np.exp(engagement + g.normal(0, 0.5, n)) * (1 + lift)
    return np.where(active, hours, 0.0)

g = np.random.default_rng(seed)
y_c = simulate_watch_hours(20000, g); y_t = simulate_watch_hours(20000, g, lift=0.02)
res = welch_test(y_t, y_c)
print(f"media control={y_c.mean():.2f} h, sd={y_c.std():.2f} h (CV={y_c.std()/y_c.mean():.2f})")
print(f"efecto: {res['diff']:+.3f} h ({res['lift']:+.2%}), IC95 [{res['lo']:+.3f}, {res['hi']:+.3f}], p={res['p']:.3f}")

fig, axes = plt.subplots(1, 3, figsize=(15, 3.8))
axes[0].hist(y_c, bins=np.linspace(0, 80, 80), color=C["ctrl"]); axes[0].set(title="Horas por usuario (control)", xlabel="horas en 2 semanas", ylabel="usuarios")
srt = np.sort(y_c)[::-1]; axes[1].plot(np.arange(1, len(srt) + 1) / len(srt) * 100, np.cumsum(srt) / srt.sum() * 100, color=C["trt"], lw=2)
axes[1].set(title="Concentración: % de horas vs % de usuarios", xlabel="% de usuarios (más activos primero)", ylabel="% de horas acumuladas")
diffs = [simulate_watch_hours(5000, g, 0.02).mean() - simulate_watch_hours(5000, g).mean() for _ in range(R_SIM)]
axes[2].hist(diffs, bins=40, color=C["trt"], density=True, alpha=0.7, label="diferencias simuladas")
xs = np.linspace(min(diffs), max(diffs), 200); axes[2].plot(xs, stats.norm.pdf(xs, np.mean(diffs), np.std(diffs)), "k--", label="normal (TCL)")
axes[2].axvline(0, color=C["naive"], ls=":"); axes[2].set(title="Distribución muestral de τ̂ (n=5000/grupo)", xlabel="diferencia de medias (h)")
axes[2].legend(fontsize=8); plt.tight_layout(); plt.show()
''')

    nb.md("""
> ⚠️ Fíjate en el tercer panel: con 5.000 usuarios por grupo, un efecto real del +2 % produce estimaciones **negativas** una fracción importante de las veces. Antes de lanzar un experimento hay que calcular si tiene potencia para detectar el efecto que esperas (sección 4).
""")

    # --------------------------------------------------------------- 3
    nb.md(r"""
---
## 3 · Unidad de aleatorización, métricas de ratio y SRM

### ¿Qué aleatorizas?
| Unidad | Pros | Contras | Uso típico en recsys |
|---|---|---|---|
| **Usuario / perfil** | Experiencia consistente, mide efectos acumulados | Menos unidades → más varianza | Por defecto (Netflix: perfil o cuenta) |
| Cuenta / hogar | Evita contaminación entre perfiles que comparten pantalla | Aún menos unidades | Precios, planes, cambios de UI de cuenta |
| Sesión / petición | Muchas unidades, mucha potencia | El usuario ve ambas variantes: inconsistente; arrastre (*carry-over*) | Cambios de latencia/infra invisibles |
| Clúster (mercado, ciudad, tiempo) | Captura interferencia | Muy pocas unidades | Marketplaces, *switchbacks* (sección 10) |

**Regla de oro: analiza a la misma granularidad a la que aleatorizas.** Si aleatorizas por usuario y calculas el CTR como `clics totales / impresiones totales` tratando cada impresión como independiente, **subestimas la varianza**: las impresiones de un mismo usuario están correlacionadas.

### 📐 Método delta para métricas de ratio
Métrica $R = \frac{\sum_i X_i}{\sum_i Y_i} = \bar X/\bar Y$ (p. ej. $X_i$ clics del usuario $i$, $Y_i$ sus impresiones). Con una expansión de Taylor de primer orden alrededor de $(\mu_X, \mu_Y)$:

$$\mathrm{Var}\Big(\frac{\bar X}{\bar Y}\Big) \approx \frac{1}{n\,\mu_Y^2}\Big(\sigma_X^2 - 2\frac{\mu_X}{\mu_Y}\sigma_{XY} + \frac{\mu_X^2}{\mu_Y^2}\sigma_Y^2\Big).$$

(Deng, Knoblich & Lu, KDD 2018.) Lo comprobamos con **A/A tests**: dos grupos con el mismo tratamiento; un método correcto debe dar "significativo" solo el 5 % de las veces.
""")

    nb.code(r'''
def simulate_ctr_users(n, g):
    """Usuarios con actividad y CTR heterogéneos: impresiones ~ NegBin, CTR_u ~ Beta."""
    impressions = g.negative_binomial(2, 2 / (2 + 40), n) + 1     # media ≈ 40, muy dispersa
    ctr_u = g.beta(2, 30, n)                                        # media ≈ 6 %
    clicks = g.binomial(impressions, ctr_u)
    return clicks, impressions

def ratio_delta_se(x, y):
    n = len(x); mx, my = x.mean(), y.mean()
    vx, vy, cxy = x.var(ddof=1), y.var(ddof=1), np.cov(x, y)[0, 1]
    return np.sqrt((vx - 2 * mx / my * cxy + mx ** 2 / my ** 2 * vy) / (n * my ** 2))

g = np.random.default_rng(1); pv_naive, pv_delta = [], []
for _ in range(R_SIM):
    (xa, ya), (xb, yb) = simulate_ctr_users(3000, g), simulate_ctr_users(3000, g)
    ra, rb = xa.sum() / ya.sum(), xb.sum() / yb.sum()
    se_naive = np.sqrt(ra * (1 - ra) / ya.sum() + rb * (1 - rb) / yb.sum())      # impresiones iid (MAL)
    se_delta = np.sqrt(ratio_delta_se(xa, ya) ** 2 + ratio_delta_se(xb, yb) ** 2)
    pv_naive.append(2 * stats.norm.sf(abs(rb - ra) / se_naive)); pv_delta.append(2 * stats.norm.sf(abs(rb - ra) / se_delta))
fpr = {"Naive (impresión = unidad)": np.mean(np.array(pv_naive) < 0.05), "Método delta (usuario = unidad)": np.mean(np.array(pv_delta) < 0.05)}

fig, axes = plt.subplots(1, 2, figsize=(12, 3.8))
axes[0].bar(fpr.keys(), fpr.values(), color=[C["naive"], C["delta"]]); axes[0].axhline(0.05, color="k", ls="--", label="α = 5 %")
axes[0].set(title=f"Tasa de falsos positivos en {R_SIM} A/A tests (CTR)", ylabel="P(p < 0,05)"); axes[0].legend()
axes[1].hist(pv_naive, bins=20, alpha=0.6, color=C["naive"], label="naive", density=True)
axes[1].hist(pv_delta, bins=20, alpha=0.6, color=C["delta"], label="delta", density=True)
axes[1].set(title="p-valores en A/A: deberían ser uniformes", xlabel="p-valor"); axes[1].legend()
plt.tight_layout(); plt.show(); print({k: round(v, 3) for k, v in fpr.items()})
''')

    nb.md("""
### Sample Ratio Mismatch (SRM): el primer check de cualquier análisis

Si diseñaste 50/50 y obtienes 50.000 vs 49.000 usuarios, **algo está roto** (un bug de asignación, un redirect que pierde usuarios en tratamiento, bots filtrados de forma desigual, el tratamiento hace crashear la app antes de loguear…). Un test χ² con umbral estricto (p. ej. p < 0,001) detecta el SRM; si salta, **no se analiza el experimento**: se busca la causa. Microsoft reporta que el SRM es uno de los problemas de calidad más frecuentes en su plataforma (Fabijan et al., KDD 2019).

En producción la asignación es **determinista por hash** (`hash(salt + user_id) mod 1000`), con una *salt* por experimento para que los experimentos sean ortogonales entre sí.
""")

    nb.code(r'''
user_ids = np.arange(100_000)
bucket = assign_bucket(user_ids, salt="exp_ranker_v7")
is_t = bucket < 500
print(f"Asignación por hash: tratamiento={is_t.sum():,}, control={(~is_t).sum():,}, p_SRM={srm_test(is_t.sum(), (~is_t).sum()):.3f}")
# Simulamos un bug: el tratamiento crashea para el 4 % de usuarios antes de enviar el evento de exposición
logged_t = is_t & (np.random.default_rng(0).random(len(user_ids)) > 0.04)
print(f"Con bug de logging: tratamiento={logged_t.sum():,}, control={(~is_t).sum():,}, p_SRM={srm_test(logged_t.sum(), (~is_t).sum()):.2e}  ← ¡SRM!")
# Ortogonalidad: otra salt → asignaciones independientes
other = assign_bucket(user_ids, salt="exp_artwork_v2") < 500
print("Tabla cruzada de dos experimentos (deberían ser ~25 % cada celda):")
display(pd.crosstab(is_t, other, normalize=True).round(3))
''')

    # --------------------------------------------------------------- 4
    nb.md(r"""
---
## 4 · Potencia, tamaño muestral y MDE

### 📐 La fórmula que debes saber de memoria
Para un test bilateral a nivel $\alpha$ con potencia $1-\beta$ y grupos iguales de tamaño $n$, con desviación típica $\sigma$ de la métrica, el **efecto mínimo detectable** (MDE) es

$$\text{MDE} = (z_{1-\alpha/2} + z_{1-\beta})\,\sqrt{\frac{2\sigma^2}{n}} \quad\Longleftrightarrow\quad n = \frac{2\,(z_{1-\alpha/2} + z_{1-\beta})^2\,\sigma^2}{\text{MDE}^2}.$$

Con $\alpha=0{,}05$ y potencia $0{,}8$: $(1{,}96+0{,}84)^2 \approx 7{,}85$, así que $n \approx 16\,\sigma^2/\text{MDE}^2$ por grupo (la "regla del 16" de Kohavi et al.).

Consecuencias prácticas:
- Detectar un efecto **la mitad de grande** exige **4×** usuarios.
- Lo que manda es el **coeficiente de variación** $\sigma/\mu$: con CV ≈ 2 (típico de horas vistas), detectar +1 % relativo exige $16\cdot 2^2/0{,}01^2 = 640.000$ usuarios por grupo.
- La duración se deriva del tráfico: $n$ / usuarios elegibles por día, redondeando a **semanas completas** (estacionalidad semanal).
""")

    nb.code(r'''
g = np.random.default_rng(2)
pilot = simulate_watch_hours(200_000, g)
mu, sigma = pilot.mean(), pilot.std()
power_calc = NormalIndPower()
rows = []
for mde_rel in [0.005, 0.01, 0.02, 0.05]:
    es = mde_rel * mu / sigma                                    # tamaño de efecto estandarizado (d de Cohen)
    n = power_calc.solve_power(effect_size=es, alpha=0.05, power=0.8, ratio=1.0, alternative="two-sided")
    rows.append(dict(MDE_relativo=f"{mde_rel:.1%}", n_por_grupo=int(np.ceil(n)), regla_16=int(16 * sigma**2 / (mde_rel * mu)**2)))
display(pd.DataFrame(rows))

fig, axes = plt.subplots(1, 2, figsize=(13, 4))
ns = np.logspace(3, 6.5, 60)
for mde_rel, col in zip([0.005, 0.01, 0.02, 0.05], ["#1a365d", "#2b6cb0", "#63b3ed", "#bee3f8"]):
    pw = power_calc.power(effect_size=mde_rel * mu / sigma, nobs1=ns, alpha=0.05)
    axes[0].semilogx(ns, pw, lw=2, color=col, label=f"efecto +{mde_rel:.1%}")
axes[0].axhline(0.8, ls="--", color="k"); axes[0].set(title="Potencia vs usuarios por grupo (horas vistas)", xlabel="n por grupo (log)", ylabel="potencia"); axes[0].legend()
daily = 40_000                                                    # usuarios elegibles nuevos por día y grupo
days = np.arange(1, 43)
mde_days = (stats.norm.ppf(0.975) + stats.norm.ppf(0.8)) * np.sqrt(2 * sigma**2 / (daily * days)) / mu
axes[1].plot(days, mde_days * 100, lw=2, color=C["trt"])
for wk in [7, 14, 21, 28]: axes[1].axvline(wk, color="#cbd5e0", ls=":")
axes[1].set(title=f"MDE relativo vs duración ({daily:,} usuarios/día/grupo)", xlabel="días", ylabel="MDE (%)")
plt.tight_layout(); plt.show()
''')

    nb.code(r'''
# Verificación por simulación: ¿la potencia teórica coincide con la empírica?
n_sim, mde_rel = 20_000, 0.03
es = mde_rel * mu / sigma
theory = power_calc.power(effect_size=es, nobs1=n_sim, alpha=0.05)
g = np.random.default_rng(3)
hits = [welch_test(simulate_watch_hours(n_sim, g, lift=mde_rel), simulate_watch_hours(n_sim, g))["p"] < 0.05
        for _ in range(R_SIM // 2)]
print(f"Potencia teórica={theory:.2f} | empírica={np.mean(hits):.2f}  (n={n_sim:,}/grupo, efecto +{mde_rel:.0%} sobre activos)")
print("El lift multiplica las horas de los activos; como los ceros siguen siendo ceros, la media también sube exactamente un +3 %.")
''')

    # --------------------------------------------------------------- 5
    nb.md(r"""
---
## 5 · Reducción de varianza: CUPED y CUPAC

### 📐 CUPED (Deng, Xu, Kohavi & Walker, WSDM 2013 — Microsoft Bing)
Idea: buena parte de la varianza de $Y$ (horas durante el experimento) se explica por **cuánto veía el usuario antes** ($X$, periodo pre-experimento). Como $X$ es anterior a la aleatorización, es independiente del tratamiento, y podemos restarlo sin introducir sesgo:

$$Y^{\text{cuped}}_i = Y_i - \theta\,(X_i - \bar X), \qquad \theta^* = \frac{\mathrm{Cov}(Y,X)}{\mathrm{Var}(X)}, \qquad \mathrm{Var}(Y^{\text{cuped}}) = (1-\rho^2)\,\mathrm{Var}(Y).$$

Con correlación $\rho = 0{,}7$ la varianza baja un 51 % → **mitad de usuarios o mitad de duración** para la misma potencia. Es exactamente una **regresión con covariable** (ANCOVA): $Y \sim T + X$. El paper reporta reducciones de varianza de ~50 % en métricas de Bing.

- Usuarios nuevos sin historial: $X=0$ con un indicador, o $X$ = media del segmento.
- $\theta$ se estima con **todos** los usuarios (ambos grupos juntos).

### CUPAC (DoorDash, 2020)
Sustituye $X$ por la **predicción de un modelo de ML** de $Y$ a partir de muchas features pre-experimento (horas previas, días activos, antigüedad, dispositivo…). Más $\rho^2$ → más reducción. Requisito: el modelo usa **solo** información anterior a la aleatorización (si no, puede absorber el efecto del tratamiento).
""")

    nb.code(r'''
def simulate_pre_post(n, g, lift=0.0, noise_pre=0.6):
    """Usuarios con engagement latente persistente: X (pre) e Y (durante) comparten el nivel latente."""
    eng = g.normal(1.6, 1.0, n)
    tenure = g.exponential(2.0, n); device_tv = g.random(n) < 0.4
    eng_eff = eng + 0.3 * device_tv
    x_pre = np.exp(eng_eff + g.normal(0, noise_pre, n)) * (g.random(n) > 0.2)
    days_active_pre = np.clip(np.round(2 * eng_eff + g.normal(0, 1.5, n)), 0, 14)
    y = simulate_watch_hours(n, g, lift=lift, engagement=eng_eff + 0.05 * np.log1p(tenure))
    feats = np.column_stack([x_pre, days_active_pre, tenure, device_tv])
    return x_pre, feats, y

g = np.random.default_rng(4)
# CUPAC: modelo entrenado en datos HISTÓRICOS (antes del experimento), nunca con los del experimento
from sklearn.ensemble import GradientBoostingRegressor
_, F_hist, y_hist = simulate_pre_post(30_000, g)
cupac_model = GradientBoostingRegressor(n_estimators=150, max_depth=3, learning_rate=0.1, random_state=seed).fit(F_hist, y_hist)

# Para que el Monte Carlo sea rápido: un "pool" grande de usuarios con sus covariables pre-experimento y su
# predicción CUPAC calculada UNA vez; cada experimento simulado muestrea usuarios del pool.
x_pool, F_pool, y_pool = simulate_pre_post(200_000, g)
p_pool = cupac_model.predict(F_pool)
est = {"Diferencia de medias": [], "CUPED (horas pre)": [], "CUPAC (GBM sobre 4 features)": []}
n_exp, lift = 8000, 0.02
for _ in range(R_SIM):
    idx = g.choice(len(y_pool), 2 * n_exp, replace=False); T = np.r_[np.ones(n_exp), np.zeros(n_exp)].astype(bool)
    y_all = y_pool[idx] * np.where(T, 1 + lift, 1.0); x_all, p_all = x_pool[idx], p_pool[idx]
    est["Diferencia de medias"].append(y_all[T].mean() - y_all[~T].mean())
    y_cuped, _ = cuped_adjust(y_all, x_all); est["CUPED (horas pre)"].append(y_cuped[T].mean() - y_cuped[~T].mean())
    y_cupac, _ = cuped_adjust(y_all, p_all); est["CUPAC (GBM sobre 4 features)"].append(y_cupac[T].mean() - y_cupac[~T].mean())
est = {k: np.array(v) for k, v in est.items()}
base_var = est["Diferencia de medias"].var()
for k, v in est.items():
    print(f"{k:32s} media={v.mean():+.3f}  sd={v.std():.3f}  reducción de varianza={1 - v.var() / base_var:.0%}  potencia={np.mean(np.abs(v / v.std()) > 1.96):.2f}")
''')

    nb.code(r'''
fig, axes = plt.subplots(1, 2, figsize=(14, 4.2))
for (k, v), col in zip(est.items(), [C["ctrl"], C["cuped"], C["cupac"]]):
    axes[0].hist(v, bins=40, alpha=0.55, color=col, label=f"{k} (sd={v.std():.3f})", density=True)
axes[0].axvline(0, color="k", ls=":"); axes[0].set(title=f"Estimaciones del efecto en {R_SIM} experimentos (n={n_exp}/grupo)", xlabel="τ̂ (horas)")
axes[0].legend(fontsize=8)
# Reducción de varianza vs correlación: teoría 1-ρ² vs empírica
rows = []
for noise in [2.0, 1.4, 1.0, 0.7, 0.45, 0.3, 0.15]:
    x, _, y = simulate_pre_post(60_000, g, noise_pre=noise)
    rho = np.corrcoef(x, y)[0, 1]; y_adj, _ = cuped_adjust(y, x)
    rows.append((rho, 1 - y_adj.var() / y.var()))
rows = np.array(rows); rr = np.linspace(0, 1, 100)
axes[1].plot(rr, rr ** 2 * 100, "k--", label="teoría: ρ²"); axes[1].scatter(rows[:, 0], rows[:, 1] * 100, color=C["cuped"], s=50, zorder=3, label="empírica")
axes[1].set(title="CUPED: reducción de varianza vs correlación pre/post", xlabel="ρ(X_pre, Y)", ylabel="reducción de varianza (%)"); axes[1].legend()
plt.tight_layout(); plt.show()
''')

    nb.code(r'''
# CUPED ≡ regresión con covariable (ANCOVA) — así lo harías con statsmodels
xt, _, yt = simulate_pre_post(n_exp, g, lift=0.02); xc, _, yc = simulate_pre_post(n_exp, g)
df = pd.DataFrame({"y": np.r_[yt, yc], "x_pre": np.r_[xt, xc], "T": np.r_[np.ones(n_exp), np.zeros(n_exp)]})
df["x_c"] = df.x_pre - df.x_pre.mean()
m0 = smf.ols("y ~ T", df).fit(cov_type="HC1"); m1 = smf.ols("y ~ T + x_c", df).fit(cov_type="HC1")
print(f"Sin covariable: τ̂={m0.params['T']:+.3f} (se {m0.bse['T']:.3f}) | Con covariable: τ̂={m1.params['T']:+.3f} (se {m1.bse['T']:.3f})")
''')

    # --------------------------------------------------------------- 6
    nb.md("""
---
## 6 · Métricas: north-star, proxies y guardrails

- **North-star / OEC** (*Overall Evaluation Criterion*, Kohavi et al.): la métrica que define "mejor" a largo plazo. En suscripción (Netflix, Spotify) es la **retención** / satisfacción del miembro; pero se mueve lento y con poca señal.
- **Proxies / surrogates**: métricas de corto plazo **validadas** como predictoras de la north-star (horas vistas, días activos, "plays cualificados" que superan unos minutos). Netflix trabaja activamente en aprender proxies a partir de cientos de A/Bs históricos (Bibaut et al., 2024; Zhang et al., 2023 — sección 11).
- **Guardrails**: lo que no puede empeorar aunque la principal mejore: latencia p99, errores de playback, cancelaciones, quejas, SRM. Un ranker que sube +0,5 % las horas pero añade 80 ms de latencia puede perder en conjunto.
- **Diagnóstico**: CTR por fila, cobertura del catálogo, diversidad, tasa de "abandono de la home sin play". Explican *por qué* se movió la principal.

> 🧠 **Goodhart en recsys:** si la métrica principal es CTR, el sistema aprende clickbait (módulo 14). Por eso las métricas de engagement "de calidad" (minutos tras el clic, completar el título, volver al día siguiente) dominan a las de clic.

**Comparaciones múltiples.** Con 20 métricas y α=5 %, esperas un falso positivo por experimento. Pre-registra **una** principal; para las secundarias controla FDR (Benjamini–Hochberg, `statsmodels.stats.multitest.multipletests`) o trátalas como diagnóstico. Spotify describe un marco de decisión con métricas de éxito, guardrails y de deterioro con correcciones explícitas ("Risk-aware product decisions in A/B tests with multiple metrics", 2024).
""")

    # --------------------------------------------------------------- 7
    nb.md("""
---
## 7 · Novelty y primacy

- **Novelty effect:** el cambio llama la atención y los usuarios interactúan más **al principio**; el efecto decae (p. ej. una fila nueva brillante en la home).
- **Primacy effect (change aversion):** los usuarios están acostumbrados a lo anterior y el cambio **empeora al principio** hasta que aprenden (p. ej. un nuevo orden de filas).

Diagnósticos: (1) graficar el efecto **por día desde la exposición**; (2) comparar **usuarios nuevos** (no tienen hábitos previos, no hay novelty) frente a **existentes**; (3) mantener *holdouts* de larga duración. Google mostró en anuncios que los efectos de largo plazo pueden diferir del corto plazo por aprendizaje del usuario (Hohnhold, O'Brien & Tang, KDD 2015).
""")

    nb.code(r'''
days = np.arange(1, 36); g = np.random.default_rng(5)
n_day = 15000
def daily_effects(tau_inf, tau_0, kappa):
    """Efecto relativo verdadero por día: τ(d) = τ∞ + (τ0 - τ∞) e^{-d/κ}, y su estimación ruidosa."""
    true = tau_inf + (tau_0 - tau_inf) * np.exp(-days / kappa)
    se = 1.9 * np.sqrt(2 / n_day)                     # CV≈1,9 de la métrica diaria
    return true, true + g.normal(0, se, len(days)), se

fig, axes = plt.subplots(1, 2, figsize=(14, 4.2))
for ax, (name, ti, t0, k, col) in zip(axes, [("Novelty: +6 % inicial → +0,5 % estable", 0.005, 0.06, 5, C["il"]),
                                             ("Primacy: −4 % inicial → +1,5 % estable", 0.015, -0.04, 7, C["cuped"])]):
    true, est_d, se = daily_effects(ti, t0, k)
    cum = np.cumsum(est_d) / np.arange(1, len(days) + 1)          # estimación acumulada (simplificada)
    ax.errorbar(days, est_d * 100, yerr=1.96 * se * 100, fmt="o", ms=3, color=col, alpha=0.6, label="efecto diario estimado ± IC95")
    ax.plot(days, true * 100, "k-", lw=2, label="efecto real")
    ax.plot(days, cum * 100, "--", color="#2d3748", lw=2, label="estimación acumulada")
    ax.axhline(ti * 100, color="#718096", ls=":"); ax.axhline(0, color="k", lw=0.5)
    for d in [7, 14]: ax.axvline(d, color="#cbd5e0", ls=":")
    ax.set(title=name, xlabel="día desde la exposición", ylabel="efecto relativo (%)"); ax.legend(fontsize=8)
plt.tight_layout(); plt.show()
print("Si paras el experimento novelty en el día 7, la estimación acumulada sobreestima varias veces el efecto estable.")
''')

    # --------------------------------------------------------------- 8
    nb.md("""
---
## 8 · Interleaving: comparar rankers con 10–100× menos usuarios

### 💡 La idea
En un A/B, el usuario $i$ ve el ranker A **o** el B, y comparamos medias entre **personas distintas**: la varianza entre usuarios (unos ven 1 h, otros 40 h) ahoga la diferencia. En **interleaving** cada usuario ve **una sola lista que mezcla A y B** y medimos **qué ranker aporta los ítems que elige**. Es una comparación **dentro del usuario**: como un test pareado frente a uno no pareado.

### Team Draft Interleaving (Radlinski, Kurup & Joachims, CIKM 2008)
Como elegir equipos en el patio: en cada ronda, el "capitán" con menos jugadores (o, si empatan, quien gane una moneda) añade su ítem mejor rankeado aún no elegido. Cada posición queda acreditada a un equipo. Los clics/plays en ítems del equipo B cuentan para B. La preferencia del usuario es, p. ej., $\\Delta_i = \\text{plays}_B - \\text{plays}_A$, y se testea $\\mathbb{E}[\\Delta] \\neq 0$.

### 🏭 Netflix (Parks, Aurisset & Ramm, 2017)
En "Innovating Faster on Personalization Algorithms at Netflix Using Interleaving" describen un proceso **en dos fases**: (1) interleaving para **podar rápidamente** muchas variantes de algoritmos de ranking con pocos usuarios, y (2) A/B test clásico con las ganadoras para medir el impacto en las métricas de negocio. Reportan que, para dos rankers de calidad conocida, interleaving necesitó **más de 100× menos usuarios** que su métrica A/B más sensible para alcanzar potencia del 95 % (medido con *bootstrap subsampling*), y que la preferencia de interleaving **correlaciona fuertemente** con las métricas del A/B. Airbnb publicó en 2025 su experiencia combinando interleaving y evaluación contrafactual para el ranking de búsqueda (arXiv:2508.00751).

> ⚠️ Interleaving mide **preferencia relativa entre dos rankings** en una misma superficie. No mide efectos sobre métricas de negocio (retención), no sirve para cambios de UI ni para efectos de largo plazo, y requiere que ambos rankers puedan servirse a la vez (doble coste de inferencia).
""")

    nb.code(r'''
# Demostración del algoritmo con dos rankings pequeños
g = np.random.default_rng(0)
A = ["Dark", "Narcos", "Ozark", "Mindhunter", "Lupin", "Elite"]
B = ["Narcos", "Lupin", "The Crown", "Dark", "Wednesday", "Ozark"]
lst, team = team_draft_interleave(A, B, 6, g)
fig, ax = plt.subplots(figsize=(12, 2.8)); ax.axis("off"); ax.set_xlim(0, 13); ax.set_ylim(0, 3.2)
for j, (it_a, it_b) in enumerate(zip(A, B)):
    box(ax, (0.2, 2.6 - j * 0.42), 2.2, 0.35, f"A{j+1}: {it_a}", fc="#fdf2e9", ec="#c05621", fs=8)
    box(ax, (10.5, 2.6 - j * 0.42), 2.2, 0.35, f"B{j+1}: {it_b}", fc="#e8f1fb", ec="#2b6cb0", fs=8)
for j, (it, tm) in enumerate(zip(lst, team)):
    box(ax, (5.2, 2.6 - j * 0.42), 2.6, 0.35, f"{j+1}. {it}  ← {'A' if tm == 0 else 'B'}",
        fc="#fdf2e9" if tm == 0 else "#e8f1fb", ec="#c05621" if tm == 0 else "#2b6cb0", fs=8)
ax.text(1.3, 3.1, "Ranker A", ha="center", weight="bold"); ax.text(11.6, 3.1, "Ranker B", ha="center", weight="bold")
ax.text(6.5, 3.1, "Lista interleaved (Team Draft)", ha="center", weight="bold"); plt.show()
''')

    nb.code(r'''
# Mundo simulado: 300 títulos, usuarios con gustos y ACTIVIDAD muy heterogénea (lo que hace ruidoso al A/B)
N_ITEMS_IL, D_IL, TOPK = 300, 8, 10
gw = np.random.default_rng(10)
V_il = gw.normal(0, 1, (N_ITEMS_IL, D_IL)) / np.sqrt(D_IL); b_il = gw.normal(-1.0, 0.8, N_ITEMS_IL)
EXAM = 1 / np.log2(np.arange(2, TOPK + 2))                       # probabilidad de examinar cada posición (PBM)

def user_batch(n, g):
    U = g.normal(0, 1.4, (n, D_IL)); sessions = g.poisson(np.exp(g.normal(1.0, 0.9, n))) + 1
    return U, sessions

def rankers(U, g, noise_a=1.0, noise_b=0.85):
    """Dos rankers que estiman la relevancia con distinto ruido (B es algo mejor). Devuelven top-K."""
    rel = U @ V_il.T + b_il
    top_a = np.argsort(-(rel + g.normal(0, noise_a, rel.shape)), 1)[:, :TOPK]
    top_b = np.argsort(-(rel + g.normal(0, noise_b, rel.shape)), 1)[:, :TOPK]
    return 1 / (1 + np.exp(-rel)), top_a, top_b

def plays_for_list(p_rel_row, lst, sessions, g):
    """Plays por posición acumulados en `sessions` sesiones (modelo de examen por posición)."""
    p = EXAM[:len(lst)] * p_rel_row[lst] * 0.3
    return g.binomial(sessions, p)

def simulate_pool(n, g):
    """Para cada usuario: plays si estuviera en A, plays si estuviera en B (resultados potenciales)
    y Δ de interleaving (plays de B − plays de A en la lista mezclada)."""
    U, S = user_batch(n, g); P, TA, TB = rankers(U, g)
    ya, yb, d_il = np.empty(n), np.empty(n), np.empty(n)
    for i in range(n):
        ya[i] = plays_for_list(P[i], TA[i], S[i], g).sum(); yb[i] = plays_for_list(P[i], TB[i], S[i], g).sum()
        lst, team = team_draft_interleave(list(TA[i]), list(TB[i]), TOPK, g)
        pl = plays_for_list(P[i], np.array(lst), S[i], g); team = np.array(team)
        d_il[i] = pl[team == 1].sum() - pl[team == 0].sum()
    return ya, yb, d_il

t0 = time.time(); N_POOL = 40_000 if FAST_DEV_RUN else 150_000
ya_pool, yb_pool, dil_pool = simulate_pool(N_POOL, np.random.default_rng(11))
print(f"{time.time()-t0:.1f}s | plays/usuario A={ya_pool.mean():.3f} B={yb_pool.mean():.3f} (lift real {yb_pool.mean()/ya_pool.mean()-1:+.2%})"
      f" | Δ interleaving medio={dil_pool.mean():+.4f}, usuarios con preferencia ≠ 0: {(dil_pool != 0).mean():.0%}")
''')

    nb.md("""
🧪 **Sensibilidad por *bootstrap subsampling*** (el método del post de Netflix): para cada tamaño de muestra $n$ remuestreamos usuarios del *pool*, corremos el test y contamos con qué frecuencia detecta que B es mejor (p < 0,05 y efecto en la dirección correcta).
- **A/B:** $n/2$ usuarios en A y $n/2$ distintos en B, Welch sobre plays por usuario.
- **Interleaving:** $n$ usuarios, t-test de una muestra sobre $\\Delta_i$ (equivalente a un test pareado).
""")

    nb.code(r'''
def power_ab(n_total, g, reps):
    hits = 0
    for _ in range(reps):
        idx = g.choice(N_POOL, n_total, replace=True); half = n_total // 2
        r = welch_test(yb_pool[idx[:half]], ya_pool[idx[half:]])
        hits += (r["p"] < 0.05) and (r["diff"] > 0)
    return hits / reps

def power_il(n_total, g, reps):
    hits = 0
    for _ in range(reps):
        d = dil_pool[g.choice(N_POOL, n_total, replace=True)]
        p = stats.ttest_1samp(d, 0).pvalue
        hits += (p < 0.05) and (d.mean() > 0)
    return hits / reps

g = np.random.default_rng(12); reps = 200 if FAST_DEV_RUN else 600
n_grid = np.unique(np.logspace(1.7, np.log10(N_POOL), 14).astype(int))
pw_ab = [power_ab(n, g, reps) for n in n_grid]; pw_il = [power_il(n, g, reps) for n in n_grid]
def n_at(pw, target=0.8):
    pw = np.array(pw); return n_grid[np.argmax(pw >= target)] if (pw >= target).any() else np.nan
n80_ab, n80_il = n_at(pw_ab), n_at(pw_il)
plt.figure(figsize=(9, 4.3))
plt.semilogx(n_grid, pw_ab, "o-", color=C["trt"], lw=2, label="A/B test (plays por usuario)")
plt.semilogx(n_grid, pw_il, "o-", color=C["il"], lw=2, label="Team Draft Interleaving")
plt.axhline(0.8, ls="--", color="k")
plt.title("Sensibilidad: potencia vs nº total de usuarios (bootstrap subsampling)"); plt.xlabel("usuarios en el experimento (log)"); plt.ylabel("potencia")
plt.legend(); plt.show()
ratio = n80_ab / n80_il if np.isfinite(n80_ab) else float("nan")
print(f"Usuarios para 80 % de potencia → interleaving ≈ {n80_il:,}, A/B ≈ {n80_ab if np.isfinite(n80_ab) else '> pool'}"
      f"  ⇒ ~{ratio:.0f}× menos usuarios con interleaving (en ESTE mundo simulado)")
''')

    nb.md("""
> 🧠 La ganancia exacta depende de la heterogeneidad de usuarios y de cuánto difieren las listas; en nuestro mundo sale del orden de decenas de veces, en Netflix (2017) más de 100×. Dos sutilezas de élite: (1) si los rankers devuelven listas casi idénticas, la mayoría de usuarios tienen $\\Delta=0$ y la sensibilidad cae; (2) Team Draft puede tener sesgos cuando un ranker pone en lo alto ítems "atractivos" pero irrelevantes; existen variantes (*optimized interleaving*, Radlinski & Craswell 2013; *multileaving* para comparar N rankers a la vez, Schuth et al.).
""")

    # --------------------------------------------------------------- 9
    nb.md(r"""
---
## 9 · Peeking y tests secuenciales

**El problema.** Un test de horizonte fijo garantiza 5 % de falsos positivos **si miras una sola vez, al final**. Si miras cada día y paras en cuanto $p<0{,}05$, tienes muchas oportunidades de que el ruido cruce el umbral: la tasa de falsos positivos se dispara (Johari, Koomen, Pekelis & Walsh, KDD 2017).

**Soluciones:**
1. **No mirar** (o mirar solo guardrails con umbrales muy estrictos). Disciplina difícil.
2. **Group sequential tests (GST)**: número de análisis intermedios planificado; umbrales más exigentes al principio (O'Brien–Fleming: $c_k = c\sqrt{K/k}$) y gasto de α (*alpha spending*, Lan–DeMets). Spotify los eligió porque sus datos llegan en lotes y, si puedes estimar el tamaño máximo, son los de mayor potencia (Schultzberg & Ankargren, 2023).
3. **Inferencia siempre válida (*always-valid*)**: mSPRT y *confidence sequences*. Puedes mirar cuando quieras y parar cuando quieras. Optimizely, Eppo y Netflix (para canarios de software y *play-delay*, Lindon et al. 2022/2024) usan variantes.

### 📐 mSPRT con mezcla normal
Con $\hat\delta_n$ la diferencia estimada y $V_n$ su varianza, y una prior de mezcla $\delta\sim\mathcal N(0,\tau^2)$ sobre el efecto bajo la alternativa:

$$\Lambda_n = \sqrt{\frac{V_n}{V_n+\tau^2}}\,\exp\!\Big(\frac{\tau^2\,\hat\delta_n^2}{2V_n(V_n+\tau^2)}\Big), \qquad p_n^{\text{AV}} = \min\Big(1, \frac{1}{\max_{m\le n}\Lambda_m}\Big).$$

Por la desigualdad de Ville (martingalas), $P(\exists n: p_n^{AV}\le\alpha)\le\alpha$ bajo $H_0$.
""")

    nb.code(r'''
def aa_sequential(n_days=28, n_per_day=400, g=None, tau2=None):
    """Un A/A test con datos diarios. Devuelve (z_k, p_naive_k, p_msprt_k) en cada día k."""
    xt = g.normal(0, 1, (n_days, n_per_day)); xc = g.normal(0, 1, (n_days, n_per_day))
    n_cum = n_per_day * np.arange(1, n_days + 1)
    d = xt.sum(1).cumsum() / n_cum - xc.sum(1).cumsum() / n_cum
    V = 2.0 / n_cum
    z = d / np.sqrt(V); p_naive = 2 * stats.norm.sf(np.abs(z))
    return z, p_naive, msprt_pvalues(d, V, tau2=tau2 if tau2 else (0.05) ** 2)

g = np.random.default_rng(13); n_days = 28; R_seq = R_SIM * 3
Z, PN, PM = zip(*[aa_sequential(n_days, g=g) for _ in range(R_seq)]); Z, PN, PM = map(np.array, (Z, PN, PM))
looks_options = [1, 2, 4, 7, 14, 28]
fpr_peek = [np.mean((PN[:, np.linspace(n_days - 1, 0, L, dtype=int)[::-1]] < 0.05).any(1)) for L in looks_options]
# O'Brien–Fleming con 28 análisis: calibramos c por simulación (sobre las mismas trayectorias, solo ilustrativo)
k = np.arange(1, n_days + 1); cs = np.linspace(1.9, 2.6, 71)
c_obf = cs[np.argmax([np.mean((np.abs(Z) >= c * np.sqrt(n_days / k)).any(1)) <= 0.05 for c in cs])]
fpr_obf = np.mean((np.abs(Z) >= c_obf * np.sqrt(n_days / k)).any(1)); fpr_msprt = np.mean((PM < 0.05).any(1))
print(f"FPR mirando cada día con test fijo: {fpr_peek[-1]:.1%} | O'Brien–Fleming (c={c_obf:.2f}): {fpr_obf:.1%} | mSPRT: {fpr_msprt:.1%}")
''')

    nb.code(r'''
fig, axes = plt.subplots(1, 2, figsize=(14, 4.2))
axes[0].plot(looks_options, np.array(fpr_peek) * 100, "o-", color=C["naive"], lw=2, label="test fijo + peeking")
axes[0].axhline(5, ls="--", color="k", label="α nominal 5 %")
axes[0].scatter([28], [fpr_obf * 100], color=C["seq"], s=80, zorder=3, label="O'Brien–Fleming (28 looks)")
axes[0].scatter([28], [fpr_msprt * 100], color=C["cuped"], s=80, zorder=3, marker="s", label="mSPRT always-valid")
axes[0].set(title=f"A/A tests: falsos positivos vs nº de miradas ({R_seq} sims)", xlabel="nº de análisis intermedios", ylabel="FPR (%)"); axes[0].legend(fontsize=8)
for j in range(25): axes[1].plot(k, Z[j], color="#a0aec0", lw=0.8, alpha=0.7)
bad = np.where((np.abs(Z) > 1.96).any(1))[0][:3]
for j in bad: axes[1].plot(k, Z[j], color=C["naive"], lw=1.6)
axes[1].plot(k, np.full(n_days, 1.96), "k--", label="±1,96 (horizonte fijo)"); axes[1].plot(k, -np.full(n_days, 1.96), "k--")
axes[1].plot(k, c_obf * np.sqrt(n_days / k), color=C["seq"], lw=2, label="frontera O'Brien–Fleming"); axes[1].plot(k, -c_obf * np.sqrt(n_days / k), color=C["seq"], lw=2)
axes[1].set_ylim(-5, 5); axes[1].set(title="Trayectorias de z en A/A (rojo: cruzan 1,96 algún día)", xlabel="día", ylabel="z"); axes[1].legend(fontsize=8)
plt.tight_layout(); plt.show()
''')

    nb.md("""
> 🧠 El precio de la validez siempre-válida es potencia: con el mismo $n$ final, mSPRT detecta menos que un test fijo. La elección de $\\tau^2$ (anchura de la mezcla) es un hiperparámetro: ajústalo al tamaño de efecto típico de tus experimentos históricos.
""")

    # --------------------------------------------------------------- 10
    nb.md("""
---
## 10 · Interferencia y marketplaces de dos lados

SUTVA se rompe cuando el tratamiento de un usuario afecta al resultado de otro:
- **Marketplaces con oferta limitada** (Airbnb, Uber, DoorDash, eBay): si el tratamiento hace que los usuarios tratados reserven más, **se quedan la oferta** que habrían usado los de control → el control empeora artificialmente y el A/B **sobreestima** el efecto global (Blake & Coey, 2014; Johari et al., 2022).
- **Redes sociales** (LinkedIn, Facebook): el tratamiento se "contagia" a amigos del control → sesgo hacia cero.
- **Recomendación con creadores** (YouTube, TikTok, Spotify): un ranker que concentra exposición en ciertos creadores cambia los incentivos de **todos** los creadores, tratados o no.
- **Streaming**: perfiles que comparten cuenta y pantalla; presupuesto de **ancho de banda**/caché compartidos.

**Diseños para mitigarlo:** aleatorización por **clúster** (mercado, ciudad, ego-clusters de LinkedIn — Saint-Jacques et al., 2019), **switchbacks** (alternar tratamiento por franjas de tiempo y región — DoorDash; Bojinov, Simchi-Levi & Zhao, 2023), **budget-split** en anuncios, y aleatorización en ambos lados del mercado.

🧪 **Simulación.** 120 mercados, cada uno con una oferta limitada de reservas. El tratamiento sube la intención de reservar del 30 % al 36 %. Comparamos el efecto **global real** (todos tratados vs todos control) con lo que estima un A/B por usuario y uno por mercado.
""")

    nb.code(r'''
M, USERS_PER_M = 120, 200
def market_bookings(intent, capacity, g):
    """Los usuarios llegan en orden aleatorio; reservan si quieren y queda oferta."""
    wants = g.random(len(intent)) < intent
    order = g.permutation(len(intent)); booked = np.zeros(len(intent))
    cum = np.cumsum(wants[order]); ok = wants[order] & (cum <= capacity)
    booked[order[ok]] = 1
    return booked

def run_marketplace(design, g, p_c=0.30, p_t=0.36):
    caps = g.poisson(62, M)                                   # oferta por mercado (≈ demanda de control)
    y_t, y_c = [], []
    treated_markets = g.random(M) < 0.5
    for m in range(M):
        if design == "usuario":
            T = g.random(USERS_PER_M) < 0.5
        else:                                                 # cluster: todo el mercado igual
            T = np.full(USERS_PER_M, treated_markets[m])
        b = market_bookings(np.where(T, p_t, p_c), caps[m], g)
        y_t.append(b[T]); y_c.append(b[~T])
    return np.concatenate(y_t).mean() - np.concatenate(y_c).mean()

def global_effect(g, reps=200):
    caps_eff = []
    for _ in range(reps):
        caps = g.poisson(62, M)
        all_t = np.mean([market_bookings(np.full(USERS_PER_M, 0.36), c, g).mean() for c in caps])
        all_c = np.mean([market_bookings(np.full(USERS_PER_M, 0.30), c, g).mean() for c in caps])
        caps_eff.append(all_t - all_c)
    return np.mean(caps_eff)

g = np.random.default_rng(14); R_mk = R_SIM // 2
gte = global_effect(g, reps=60)
est_user = np.array([run_marketplace("usuario", g) for _ in range(R_mk)])
est_cluster = np.array([run_marketplace("mercado", g) for _ in range(R_mk)])
plt.figure(figsize=(9, 4))
plt.hist(est_user, bins=30, alpha=0.6, color=C["naive"], label=f"A/B por usuario (media {est_user.mean():+.3f})", density=True)
plt.hist(est_cluster, bins=30, alpha=0.6, color=C["delta"], label=f"A/B por mercado (media {est_cluster.mean():+.3f})", density=True)
plt.axvline(gte, color="k", lw=2, ls="--", label=f"efecto global real {gte:+.3f}")
plt.axvline(0.06, color="#718096", ls=":", label="efecto sin restricción de oferta (+0,06)")
plt.title("Interferencia en un marketplace con oferta limitada"); plt.xlabel("efecto estimado en reservas por usuario"); plt.legend(fontsize=8); plt.show()
print(f"Sesgo A/B por usuario: {est_user.mean() - gte:+.3f} | sd usuario={est_user.std():.4f} vs mercado={est_cluster.std():.4f}")
''')

    nb.md("""
**Lectura.** El A/B por usuario es preciso… y está **sesgado**: mide sobre todo cuánto le "roban" los tratados al control. El A/B por mercado está centrado en el efecto global real pero es mucho más ruidoso (120 unidades en lugar de 24.000). Ese es el *trade-off* sesgo–varianza de todo diseño con interferencia.
""")

    # --------------------------------------------------------------- 11
    nb.md(r"""
---
## 11 · Efectos a largo plazo y surrogate index

La métrica que importa en suscripción (retención a 3–12 meses) **no cabe** en un experimento de 2–4 semanas. Opciones:
1. **Holdouts de larga duración** (un % pequeño de usuarios sin la funcionalidad durante meses). Caros y con problemas de contaminación.
2. **Proxies** validados: horas vistas a 2 semanas. Riesgo: optimizar un proxy que no causa la north-star.
3. **Surrogate index** (Athey, Chetty, Imbens & Kang, 2019/2025): combina **varios** resultados de corto plazo $S$ en una predicción del largo plazo $\hat Y = h(S)$, aprendida en datos **observacionales/históricos** donde sí se observó $Y$. El efecto del tratamiento sobre el índice estima el efecto sobre $Y$ **si se cumple la *surrogacy***: $Y \perp T \mid S$ (todo el efecto del tratamiento sobre $Y$ pasa por $S$).

$$\hat\tau_{\text{LP}} = \frac{1}{n_T}\sum_{i\in T} h(S_i) - \frac{1}{n_C}\sum_{i\in C} h(S_i).$$

🏭 **Netflix** evaluó el surrogate index sobre **200 A/B tests** reales (más de 1.000 brazos): con 14 días de datos predecir el efecto a 63 días llevó a decisiones estadísticamente consistentes con las del efecto directo en ~95 % de los casos con los modelos lineales (Zhang, Zhao, Le, Dimakopoulou & Kallus, 2023, arXiv:2311.11922). La recall sobre los tests que sí se habrían lanzado fue menor (~65–79 %): el índice es útil pero no perfecto.
""")

    nb.code(r'''
from sklearn.linear_model import LogisticRegression
def simulate_long_term(n, g, eng_shift=0.0, direct_effect=0.0):
    """Corto plazo S (2 semanas) y largo plazo Y (retención a 3 meses). La retención depende del
    engagement solo a través de S, salvo que haya un efecto directo (viola surrogacy)."""
    eng = g.normal(0, 1, n) + eng_shift
    s_hours = np.exp(1.5 + 0.8 * eng + g.normal(0, 0.5, n))
    s_days = np.clip(np.round(5 + 2.5 * eng + g.normal(0, 1.5, n)), 0, 14)
    s_titles = g.poisson(np.exp(0.8 + 0.5 * eng))
    S = np.column_stack([np.log1p(s_hours), s_days, np.log1p(s_titles)])
    logit = -0.5 + 0.6 * S[:, 0] + 0.15 * S[:, 1] + 0.4 * S[:, 2] - 2.2 + direct_effect
    Y = (g.random(n) < 1 / (1 + np.exp(-logit))).astype(float)
    return S, Y

g = np.random.default_rng(15)
S_hist, Y_hist = simulate_long_term(80_000, g)                      # datos históricos con Y observado
h = LogisticRegression(max_iter=1000).fit(S_hist, Y_hist)            # surrogate index h(S)
proxy_scale = np.polyfit(S_hist[:, 0], Y_hist, 1)[0]                 # proxy único: horas (pendiente lineal)

def analyze(eng_shift, direct, n=30_000, reps=30):
    out = []
    for _ in range(reps):
        St, Yt = simulate_long_term(n, g, eng_shift, direct); Sc, Yc = simulate_long_term(n, g)
        out.append(dict(real=Yt.mean() - Yc.mean(), indice=h.predict_proba(St)[:, 1].mean() - h.predict_proba(Sc)[:, 1].mean(),
                        proxy_horas=proxy_scale * (St[:, 0].mean() - Sc[:, 0].mean())))
    return pd.DataFrame(out)

cases = {"Mejor ranker\n(efecto vía engagement)": analyze(0.05, 0.0),
         "Subida de precio\n(efecto directo en churn)": analyze(0.0, -0.08)}
fig, ax = plt.subplots(figsize=(10, 4)); w = 0.25
for j, (name, df_) in enumerate(cases.items()):
    for k_, (col, c_) in enumerate(zip(["real", "indice", "proxy_horas"], ["#2d3748", C["cuped"], C["il"]])):
        ax.bar(j + (k_ - 1) * w, df_[col].mean() * 100, w, yerr=1.96 * df_[col].std() * 100, capsize=4, color=c_,
               label=["Efecto real en retención (3 meses)", "Surrogate index (2 semanas)", "Proxy único: horas"][k_] if j == 0 else None)
ax.set_xticks(range(len(cases)), cases.keys()); ax.axhline(0, color="k", lw=0.6)
ax.set(title="Estimar el efecto a largo plazo con datos de corto plazo", ylabel="Δ retención (p.p.)"); ax.legend(fontsize=8)
plt.show()
''')

    nb.md("""
**Lectura.** Cuando el tratamiento actúa *a través* del engagement, el surrogate index recupera el efecto en retención con datos de 2 semanas. Cuando el tratamiento tiene un **efecto directo** (precio, cambio de plan, una notificación molesta que hace cancelar sin cambiar el visionado), los surrogates no lo ven: la *surrogacy* falla. Conclusión: el índice se valida por **familia de intervenciones** (cambios de ranking ≠ cambios de precio).
""")

    # --------------------------------------------------------------- 12
    nb.md(r"""
---
## 12 · Efectos heterogéneos (HTE)

El efecto medio puede esconder que el nuevo ranker **ayuda a los usuarios nuevos y perjudica a los veteranos**. El efecto condicional $\tau(x) = \mathbb{E}[Y(1)-Y(0)\mid X=x]$ (CATE) se estima con *meta-learners* (Künzel et al., 2019):
- **S-learner**: un modelo $\hat\mu(x, T)$, $\hat\tau(x) = \hat\mu(x,1)-\hat\mu(x,0)$.
- **T-learner**: dos modelos, uno por grupo.
- **X-learner, DR-learner, causal forests** (Wager & Athey, 2018): mejores con grupos desbalanceados o efectos pequeños. Librerías: **EconML** (Microsoft), **CausalML** (Uber).

> ⚠️ Mirar 30 segmentos y quedarte con el que "salió significativo" es *p-hacking*. Pre-registra los segmentos, corrige por comparaciones múltiples y confirma en un experimento nuevo.
""")

    nb.code(r'''
from sklearn.ensemble import GradientBoostingRegressor
g = np.random.default_rng(16); n = 40_000
tenure = g.exponential(1.5, n); is_tv = (g.random(n) < 0.4).astype(float); age_grp = g.integers(0, 4, n)
X_h = np.column_stack([tenure, is_tv, age_grp])
true_cate = 0.6 * np.exp(-tenure) - 0.15 + 0.2 * is_tv              # ayuda a nuevos y en TV; perjudica a veteranos móviles
T = g.random(n) < 0.5
y = 3 + 0.5 * tenure + 0.8 * is_tv + g.normal(0, 2.0, n) + T * true_cate
m1 = GradientBoostingRegressor(n_estimators=150, max_depth=3, random_state=0).fit(X_h[T], y[T])   # T-learner:
m0 = GradientBoostingRegressor(n_estimators=150, max_depth=3, random_state=0).fit(X_h[~T], y[~T])  # un modelo por grupo
cate_hat = m1.predict(X_h) - m0.predict(X_h)

bins = pd.cut(tenure, [0, 0.25, 0.5, 1, 2, 4, 20]); dfh = pd.DataFrame(dict(bin=bins, tv=is_tv, true=true_cate, hat=cate_hat, T=T, y=y))
seg = dfh.groupby(["bin", "tv"], observed=True).apply(lambda d: pd.Series(dict(
    real=d.true.mean(), t_learner=d.hat.mean(), diff_medias=d.y[d["T"]].mean() - d.y[~d["T"]].mean(),
    se=np.sqrt(d.y[d["T"]].var() / d["T"].sum() + d.y[~d["T"]].var() / (~d["T"]).sum())))).reset_index()
fig, axes = plt.subplots(1, 2, figsize=(14, 4.2))
for tv, mk in [(0.0, "o"), (1.0, "s")]:
    s_ = seg[seg.tv == tv]; xs = np.arange(len(s_)) + (0.1 if tv else -0.1)
    axes[0].errorbar(xs, s_.diff_medias, yerr=1.96 * s_.se, fmt=mk, capsize=3, label=f"{'TV' if tv else 'móvil/web'}: diferencia de medias ± IC")
    axes[0].plot(xs, s_.real, mk + "--", color="k", alpha=0.6)
axes[0].set_xticks(range(len(seg.bin.unique())), [str(b) for b in seg.bin.unique()], rotation=15)
axes[0].axhline(0, color="k", lw=0.6); axes[0].set(title="Efecto por segmento (negro: real)", xlabel="antigüedad (años)", ylabel="efecto"); axes[0].legend(fontsize=8)
axes[1].scatter(true_cate[:4000], cate_hat[:4000], s=4, alpha=0.4, color=C["trt"]); axes[1].plot([-0.3, 0.7], [-0.3, 0.7], "k--")
axes[1].set(title=f"T-learner: CATE estimado vs real (corr={np.corrcoef(true_cate, cate_hat)[0,1]:.2f})", xlabel="τ(x) real", ylabel="τ̂(x)")
plt.tight_layout(); plt.show()
print(f"Efecto medio (ATE) estimado: {y[T].mean() - y[~T].mean():+.3f} | real: {true_cate.mean():+.3f}  ← positivo, pero negativo para veteranos en móvil")
''')

    # --------------------------------------------------------------- 13
    nb.md("""
---
## 13 · Cuasi-experimentos: cuando no puedes aleatorizar

A veces no se puede hacer un A/B: lanzamientos por país (licencias, marketing, TV), cambios en dispositivos de terceros, o algo que ya ocurrió. Netflix tiene un post entero sobre esto ("Quasi Experimentation at Netflix", Netflix TechBlog) y usa diff-in-diff y controles sintéticos para lanzamientos regionales.

**Diferencias en diferencias (DiD):** comparar la evolución de las regiones tratadas con la de las no tratadas, antes y después:
$$\\hat\\tau_{DiD} = (\\bar Y_{T,\\text{post}} - \\bar Y_{T,\\text{pre}}) - (\\bar Y_{C,\\text{post}} - \\bar Y_{C,\\text{pre}}).$$
Supuesto clave: **tendencias paralelas** (sin tratamiento, ambas habrían evolucionado igual). Se estima con una regresión con efectos fijos de región y semana y errores agrupados por región. Alternativas: **control sintético** (Abadie et al., 2010), **CausalImpact** (Brodersen et al., 2015, series temporales bayesianas), **regresión en discontinuidad**.
""")

    nb.code(r'''
g = np.random.default_rng(17); n_reg, n_wk, launch = 24, 20, 12
treated_regions = np.arange(n_reg) < 6
reg_fe = g.normal(10, 2, n_reg); wk_fe = 0.15 * np.arange(n_wk) + 0.6 * np.sin(np.arange(n_wk) / 2)   # tendencia + estacionalidad comunes
rows = []
for r_ in range(n_reg):
    for w_ in range(n_wk):
        eff = 0.5 if (treated_regions[r_] and w_ >= launch) else 0.0
        rows.append(dict(region=r_, week=w_, treated=int(treated_regions[r_]), post=int(w_ >= launch),
                         y=reg_fe[r_] + wk_fe[w_] + eff + g.normal(0, 0.3)))
panel = pd.DataFrame(rows); panel["did"] = panel.treated * panel.post
fit = smf.ols("y ~ did + C(region) + C(week)", panel).fit(cov_type="cluster", cov_kwds={"groups": panel.region})
naive = panel[(panel.treated == 1) & (panel.post == 1)].y.mean() - panel[(panel.treated == 1) & (panel.post == 0)].y.mean()
print(f"DiD: τ̂={fit.params['did']:.3f} (IC95 {fit.conf_int().loc['did'].round(3).tolist()}) | real=0,5 | antes-después ingenuo={naive:.3f}")

avg = panel.groupby(["treated", "week"]).y.mean().unstack(0)
plt.figure(figsize=(9, 4))
plt.plot(avg.index, avg[1], "o-", color=C["trt"], label="regiones con lanzamiento")
plt.plot(avg.index, avg[0], "o-", color=C["ctrl"], label="regiones control")
plt.plot(avg.index[launch:], avg[0][launch:] + (avg[1][:launch] - avg[0][:launch]).mean(), "--", color=C["trt"], alpha=0.6, label="contrafactual (tendencias paralelas)")
plt.axvline(launch - 0.5, color="k", ls=":"); plt.title("Diff-in-diff: lanzamiento regional de una nueva home"); plt.xlabel("semana"); plt.ylabel("horas/usuario")
plt.legend(fontsize=8); plt.show()
''')

    # --------------------------------------------------------------- 14
    nb.md("""
---
## 14 · Herramientas

| Herramienta | Tipo | Qué aporta |
|---|---|---|
| **statsmodels** | Librería Python | Potencia (`NormalIndPower`, `TTestIndPower`), OLS con errores robustos/agrupados (CUPED como ANCOVA, DiD), corrección múltiple (`multipletests`). |
| **SciPy** | Librería Python | Tests (`ttest_ind`, `chisquare` para SRM, `mannwhitneyu`), distribuciones. |
| **GrowthBook** | Plataforma *open source* | Feature flags + análisis sobre tu data warehouse; motores frecuentista y bayesiano, CUPED, tests secuenciales, chequeo de SRM. |
| **Eppo** (Datadog desde 2025) | SaaS *warehouse-native* | CUPED++, tests secuenciales, métricas de ratio con método delta, guardrails. |
| **Statsig** (adquirida por OpenAI en 2025) | SaaS | Feature gates, CUPED, sequential testing, holdouts, detección de SRM. |
| **Spotify Confidence** | SaaS + librería `confidence` (Python) | Group sequential tests, decisiones con múltiples métricas. |
| Plataformas internas | — | Netflix (XP), Microsoft (ExP), Booking, LinkedIn (T-REX), Uber, Airbnb (ERF). Si llegas a una de estas empresas, usarás la suya. |

Para causalidad: **EconML**, **CausalML**, **DoWhy**; para series: **CausalImpact** (R/`tfcausalimpact`).
""")

    nb.md("""
## 🏭 En producción

- **Netflix**: prácticamente todo cambio de producto pasa por A/B; la métrica principal histórica se ancla en retención y engagement de calidad (Gomez-Uribe & Hunt, 2015). Interleaving en dos fases para rankers (2017); *Improving the sensitivity of online controlled experiments* con estratificación y variantes de CUPED (Xie & Aurisset, KDD 2016); tests secuenciales *anytime-valid* para despliegues de software (Lindon et al., 2022; TechBlog 2024); surrogate index y proxies aprendidos de cientos de A/Bs (Zhang et al., 2023; Bibaut et al., 2024); serie "Decision Making at Netflix" en el TechBlog (2021).
- **Microsoft ExP / Bing**: CUPED (2013), método delta (2018), SRM (2019), "Trustworthy Online Controlled Experiments" (Kohavi, Tang & Xu, 2020).
- **Booking.com**: cientos o miles de experimentos concurrentes y democratización de la experimentación (Kaufman, Pitchforth & Vermeer, 2017); su blog explica CUPED en producción (Jackson, 2018).
- **Spotify**: group sequential tests y marco de decisión con múltiples métricas (blog de ingeniería, 2023–2024).
- **DoorDash**: CUPAC (2020) y *switchback experiments* para la interferencia del marketplace.
- **LinkedIn**: *ego-cluster randomization* para efectos de red (Saint-Jacques et al., 2019).
- **Airbnb**: interferencia en precios de marketplace (Holtz et al., 2020) e interleaving en búsqueda (2025).
""")

    nb.md("""
## 🧠 Secretos de la élite

1. **Haz A/A tests continuamente.** Si tu plataforma da "significativo" en más del 5 % de A/As, todo lo demás es ruido. Es la forma más barata de detectar bugs de asignación, de métricas o de varianza mal calculada (Kohavi et al., 2020).
2. **SRM antes que nada**: un SRM invalida el experimento aunque el resultado "tenga sentido". Usa umbrales muy estrictos (p < 0,001) porque lo compruebas en todos los experimentos.
3. **El denominador manda**: analiza a nivel de la unidad de aleatorización. CTR por impresión con usuarios aleatorizados → método delta o bootstrap por usuario.
4. **Triggering**: analiza solo a los usuarios que **pudieron** ver la diferencia (p. ej. los que llegaron a la fila cambiada) y luego diluye el efecto al total. Aumenta la sensibilidad muchísimo; es estándar en Microsoft y Netflix.
5. **CUPED es gratis**: en métricas de engagement con historial suele recortar 30–60 % de la varianza. Si tu plataforma no lo usa por defecto, estás tirando semanas de experimento.
6. **Winsoriza/capa las métricas de cola larga** (p. ej. al percentil 99,9) antes de analizar: un puñado de cuentas compartidas o bots puede dominar la varianza. Decide la regla **antes** de ver datos.
7. **Interleaving para podar, A/B para decidir**: el patrón de Netflix. La OPE (módulo 14) y el interleaving filtran candidatos; el A/B mide negocio y guardrails.
8. **Desconfía de los resultados sorprendentes** (*Twyman's law*: "cualquier cifra que parezca interesante o diferente suele estar mal"). Antes de celebrar un +10 %, busca el bug.
""")

    nb.md("""
## ⚠️ Errores comunes

- Parar el experimento en cuanto sale p < 0,05 (peeking) sin método secuencial.
- Elegir la métrica principal **después** de ver los resultados.
- Aleatorizar por usuario y analizar por impresión/sesión como si fueran independientes.
- Correr experimentos de 3 días: ni se cubre la estacionalidad semanal ni se ve el decaimiento de novelty.
- Ignorar la interferencia en marketplaces o con oferta limitada (sobreestima el efecto).
- Usar CUPED con una covariable medida **después** de la exposición (puede absorber el efecto).
- Interpretar "no significativo" como "no hay efecto" (puede ser falta de potencia: mira el IC y el MDE).
- Reportar el segmento que salió significativo entre 30 sin corrección ni réplica.
""")

    nb.md("""
## 📝 Autoevaluación

**1.** Con CV = 2 en horas vistas, ¿cuántos usuarios por grupo necesitas para detectar +1 % relativo con α=0,05 y potencia 0,8?
<details><summary>Respuesta</summary>n ≈ 16·σ²/δ² = 16·(CV·μ)²/(0,01·μ)² = 16·4/0,0001 = 640.000 por grupo.</details>

**2.** ¿Por qué el CTR "clics totales / impresiones totales" con un test binomial sobre impresiones da demasiados falsos positivos si aleatorizas por usuario?
<details><summary>Respuesta</summary>Las impresiones de un mismo usuario están correlacionadas (usuarios con CTR alto o bajo), así que la varianza real es mayor que la binomial; hay que usar el método delta o un bootstrap por usuario.</details>

**3.** CUPED con ρ = 0,6 entre el periodo previo y el experimento: ¿cuánto se reduce el tamaño muestral necesario?
<details><summary>Respuesta</summary>La varianza se multiplica por 1−ρ² = 0,64, así que el tamaño muestral baja un 36 %.</details>

**4.** ¿Por qué interleaving es más sensible que un A/B y qué no puede medir?
<details><summary>Respuesta</summary>Compara los dos rankers dentro del mismo usuario (diseño pareado) y elimina la varianza entre usuarios. No mide efectos en métricas de negocio a largo plazo (retención), cambios de UI ni efectos en el ecosistema; solo la preferencia relativa entre dos rankings.</details>

**5.** Miras tu A/B cada día durante 4 semanas y paras cuando p < 0,05. ¿Qué pasa con la tasa de falsos positivos y qué harías?
<details><summary>Respuesta</summary>Sube muy por encima del 5 % (en la simulación, 20–30 % con 28 miradas). Soluciones: no mirar, group sequential con fronteras O'Brien–Fleming/alpha spending, o p-valores siempre válidos (mSPRT, confidence sequences).</details>

**6.** En un marketplace con oferta limitada, ¿en qué dirección sesga un A/B por usuario y qué diseño lo arregla?
<details><summary>Respuesta</summary>Sobreestima el efecto global, porque los tratados consumen la oferta del control. Lo arreglan la aleatorización por clúster/mercado o los switchbacks, a cambio de más varianza.</details>

**7.** ¿Qué supuesto necesita el surrogate index y da un ejemplo en el que falla?
<details><summary>Respuesta</summary>Surrogacy: Y ⊥ T | S, es decir, todo el efecto del tratamiento sobre el largo plazo pasa por los surrogates. Falla, por ejemplo, con una subida de precio que aumenta la cancelación sin cambiar el visionado de las dos primeras semanas.</details>

**8.** ¿Cuándo usarías diff-in-diff y cuál es su supuesto clave?
<details><summary>Respuesta</summary>Cuando no se puede aleatorizar (p. ej. lanzamiento por país). Supuesto: tendencias paralelas; sin tratamiento, tratados y controles habrían evolucionado igual. Se comprueba con las tendencias pre-tratamiento y con placebos.</details>
""")

    nb.md("""
## 📚 Referencias

**Libros y fundamentos**
- Kohavi, Tang & Xu (2020). *Trustworthy Online Controlled Experiments: A Practical Guide to A/B Testing.* Cambridge University Press.
- Kohavi, Longbotham, Sommerfield & Henne (2009). *Controlled experiments on the web: survey and practical guide.* Data Mining and Knowledge Discovery 18.
- Imbens & Rubin (2015). *Causal Inference for Statistics, Social, and Biomedical Sciences.* Cambridge University Press.

**Varianza, métricas y calidad**
- Deng, Xu, Kohavi & Walker (2013). *Improving the Sensitivity of Online Controlled Experiments by Utilizing Pre-Experiment Data* (CUPED). WSDM.
- Li, J. (2020). *Improving Experimental Power through Control Using Predictions as Covariate (CUPAC).* DoorDash Engineering Blog.
- Jackson, S. (2018). *How Booking.com increases the power of online experiments with CUPED.* Booking.com Data Science blog.
- Xie & Aurisset (2016). *Improving the Sensitivity of Online Controlled Experiments: Case Studies at Netflix.* KDD.
- Deng, Knoblich & Lu (2018). *Applying the Delta Method in Metric Analytics: A Practical Guide with Novel Ideas.* KDD. [arXiv:1803.06336](https://arxiv.org/abs/1803.06336)
- Fabijan et al. (2019). *Diagnosing Sample Ratio Mismatch in Online Controlled Experiments.* KDD.
- Kaufman, Pitchforth & Vermeer (2017). *Democratizing online controlled experiments at Booking.com.* [arXiv:1710.08217](https://arxiv.org/abs/1710.08217)
- Gomez-Uribe & Hunt (2015). *The Netflix Recommender System: Algorithms, Business Value, and Innovation.* ACM TMIS.

**Interleaving**
- Radlinski, Kurup & Joachims (2008). *How Does Clickthrough Data Reflect Retrieval Quality?* CIKM.
- Chapelle, Joachims, Radlinski & Yue (2012). *Large-scale validation and analysis of interleaved search evaluation.* ACM TOIS.
- Parks, Aurisset & Ramm (2017). *Innovating Faster on Personalization Algorithms at Netflix Using Interleaving.* Netflix TechBlog. https://netflixtechblog.com/using-interleaving-in-online-experiments-to-accelerate-algorithm-innovation-at-netflix-a04ee392ec55
- Airbnb (2025). *Harnessing the Power of Interleaving and Counterfactual Evaluation for Airbnb Search Ranking.* [arXiv:2508.00751](https://arxiv.org/abs/2508.00751)

**Tests secuenciales**
- Johari, Koomen, Pekelis & Walsh (2017). *Peeking at A/B Tests: Why it matters, and what to do about it.* KDD.
- Johari, Pekelis & Walsh (2015/2022). *Always Valid Inference: Bringing Sequential Analysis to A/B Testing.* [arXiv:1512.04922](https://arxiv.org/abs/1512.04922)
- Schultzberg & Ankargren (2023). *Choosing a Sequential Testing Framework — Comparisons and Discussions.* Spotify Engineering. https://engineering.atspotify.com/2023/3/choosing-sequential-testing-framework-comparisons-and-discussions
- Lindon et al. (2024). *Sequential A/B Testing Keeps the World Streaming Netflix, Part 1: Continuous Data.* Netflix TechBlog.
- Howard, Ramdas, McAuliffe & Sekhon (2021). *Time-uniform, nonparametric, nonasymptotic confidence sequences.* Annals of Statistics.

**Interferencia**
- Blake & Coey (2014). *Why Marketplace Experimentation Is Harder than it Seems: The Role of Test-Control Interference.* ACM EC.
- Johari, Li, Liskovich & Weintraub (2022). *Experimental Design in Two-Sided Platforms: An Analysis of Bias.* Management Science. [arXiv:2002.05670](https://arxiv.org/abs/2002.05670)
- Saint-Jacques et al. (2019). *Using Ego-Clusters to Measure Network Effects at LinkedIn.* [arXiv:1903.08755](https://arxiv.org/abs/1903.08755)
- Bojinov, Simchi-Levi & Zhao (2023). *Design and Analysis of Switchback Experiments.* Management Science. [arXiv:2009.00148](https://arxiv.org/abs/2009.00148)
- Holtz et al. (2020). *Reducing Interference Bias in Online Marketplace Pricing Experiments.* [arXiv:2004.12489](https://arxiv.org/abs/2004.12489)

**Largo plazo y heterogeneidad**
- Athey, Chetty, Imbens & Kang (2019/2025). *The Surrogate Index: Combining Short-Term Proxies to Estimate Long-Term Treatment Effects More Rapidly and Precisely.* NBER WP 26463; Review of Economic Studies. [arXiv:1603.09326](https://arxiv.org/abs/1603.09326)
- Zhang, Zhao, Le, Dimakopoulou & Kallus (2023). *Evaluating the Surrogate Index as a Decision-Making Tool Using 200 A/B Tests at Netflix.* [arXiv:2311.11922](https://arxiv.org/abs/2311.11922)
- Bibaut, Chou, Ejdemyr & Kallus (2024). *Learning the Covariance of Treatment Effects Across Many Weak Experiments* (proxies en Netflix). KDD.
- Hohnhold, O'Brien & Tang (2015). *Focusing on the Long-term: It's Good for Users and Business.* KDD.
- Künzel, Sekhon, Bickel & Yu (2019). *Metalearners for estimating heterogeneous treatment effects using machine learning.* PNAS. [arXiv:1706.03461](https://arxiv.org/abs/1706.03461)
- Wager & Athey (2018). *Estimation and Inference of Heterogeneous Treatment Effects using Random Forests.* JASA. [arXiv:1510.04342](https://arxiv.org/abs/1510.04342)

**Cuasi-experimentos**
- Abadie, Diamond & Hainmueller (2010). *Synthetic Control Methods for Comparative Case Studies.* JASA.
- Brodersen et al. (2015). *Inferring causal impact using Bayesian structural time-series models.* Annals of Applied Statistics.
- Netflix TechBlog. *Quasi Experimentation at Netflix.*

**Herramientas**: [statsmodels](https://www.statsmodels.org) · [SciPy](https://scipy.org) · [GrowthBook](https://www.growthbook.io) · [Eppo](https://www.geteppo.com) · [Statsig](https://www.statsig.com) · [Spotify Confidence](https://confidence.spotify.com) · [EconML](https://github.com/py-why/EconML) · [CausalML](https://github.com/uber/causalml)
""")

    nb.save(LESSON)


WORLD_CODE = r'''
# === Mundo simulado de CineMatch construido sobre MovieLens-100K ("gemelo digital") ===
import io, zipfile, urllib.request
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds

def load_ml100k():
    """MovieLens-100K oficial de GroupLens; si no hay red, ratings sintéticos con la misma forma."""
    try:
        raw = urllib.request.urlopen("https://files.grouplens.org/datasets/movielens/ml-100k.zip", timeout=60).read()
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            df = pd.read_csv(z.open("ml-100k/u.data"), sep="\t", names=["user", "item", "rating", "ts"])
        return df, "movielens-100k"
    except Exception as e:
        print(f"⚠️ No se pudo descargar MovieLens ({type(e).__name__}); uso ratings SINTÉTICOS con la misma forma.")
        g = np.random.default_rng(seed); nu, ni, k = 943, 1682, 8
        Pu, Qi = g.normal(0, 1, (nu, k)), g.normal(0, 1, (ni, k))
        pop_w = g.zipf(1.3, ni).clip(1, 600).astype(float); pop_w /= pop_w.sum()
        act = np.exp(g.normal(4.2, 0.9, nu)).astype(int).clip(20, 700)
        rows = []
        for u in range(nu):
            its = g.choice(ni, act[u], replace=False, p=pop_w)
            r = np.clip(np.round(3.5 + 1.2 * (Qi[its] @ Pu[u]) / np.sqrt(k) + g.normal(0, 0.8, len(its))), 1, 5)
            rows.append(pd.DataFrame(dict(user=u + 1, item=its + 1, rating=r, ts=0)))
        return pd.concat(rows, ignore_index=True), "synthetic"

ratings, DATA_SOURCE = load_ml100k()
n_u, n_i = ratings.user.max(), ratings.item.max()
centered = ratings.rating - ratings.groupby("user").rating.transform("mean")
R = csr_matrix((centered, (ratings.user - 1, ratings.item - 1)), shape=(n_u, n_i)).astype(float)
U_, s_, Vt_ = svds(R, k=16)                                   # factores latentes "reales" de MovieLens
P_ML, Q_ML = U_ * np.sqrt(s_), Vt_.T * np.sqrt(s_)
pop_all = np.bincount(ratings.item - 1, minlength=n_i)
acts_ml = np.bincount(ratings.user - 1, minlength=n_u)
print(f"Fuente: {DATA_SOURCE} | {len(ratings):,} ratings, {n_u} usuarios, {n_i} películas")
'''

WORLD_SIM = r'''
TOPK, N_CAT = 10, 600
EXAM = (1 / np.log2(np.arange(2, TOPK + 2))).astype(np.float32)     # P(examinar posición k)
CATALOG = np.argsort(-pop_all)[:N_CAT]                              # las 600 películas más vistas
Qc = Q_ML[CATALOG].astype(np.float32)
lp = np.log1p(pop_all[CATALOG]); lp = ((lp - lp.mean()) / lp.std()).astype(np.float32)
AFF_SCALE = float((P_ML @ Q_ML[CATALOG].T).std())
PLAY_SCALE = 0.25

def topk(S):
    idx = np.argpartition(-S, TOPK, axis=1)[:, :TOPK]
    order = np.argsort(-np.take_along_axis(S, idx, 1), 1)
    return np.take_along_axis(idx, order, 1)

def build_population(n, seed=7, noise_a=1.0, noise_b=0.6):
    """Población de n usuarios 'gemelos' de usuarios de MovieLens (embedding + ruido; actividad
    heterogénea derivada del nº de ratings). Devuelve un dict con resultados potenciales:
      x_pre: plays en las 2 semanas PREVIAS (todos con el ranker A de producción)
      y_a / y_b: plays en las 2 semanas del experimento si el usuario estuviera en A / en B
      day: día (1-14) en que el usuario entra por primera vez en el experimento
      lists_a / lists_b / p_a / p_b: top-10 de cada ranker y probabilidad de play de cada ítem
    Ranker A = producción (MF + popularidad, ruidoso). Ranker B = candidato (mismo modelo, menos ruido)."""
    g = np.random.default_rng(seed)
    base = g.integers(0, n_u, n)
    emb = (P_ML[base] + g.normal(0, 0.5 * P_ML.std(), (n, P_ML.shape[1]))).astype(np.float32)
    la = np.log(acts_ml[base])
    sess_rate = np.exp(0.9 * (la - np.log(acts_ml).mean()) + g.normal(0, 0.5, n) + np.log(4))
    sess_pre, sess_exp = g.poisson(sess_rate), g.poisson(sess_rate)
    out = {k: np.zeros(n) for k in ["x_pre", "y_a", "y_b", "zero_a", "zero_b"]}
    out.update(lists_a=np.zeros((n, TOPK), np.int32), lists_b=np.zeros((n, TOPK), np.int32),
               p_a=np.zeros((n, TOPK), np.float32), p_b=np.zeros((n, TOPK), np.float32))
    for st in range(0, n, 20_000):
        sl = slice(st, st + 20_000); z = (emb[sl] @ Qc.T) / AFF_SCALE
        P = 1 / (1 + np.exp(-(1.2 * z + 0.3 * lp - 1.0)))                   # P(play | examinado) real
        A = topk(z + 0.6 * lp + noise_a * g.standard_normal(z.shape, dtype=np.float32))
        B = topk(z + 0.6 * lp + noise_b * g.standard_normal(z.shape, dtype=np.float32))
        rows = np.arange(z.shape[0])[:, None]
        out["p_a"][sl], out["p_b"][sl] = P[rows, A], P[rows, B]
        out["lists_a"][sl], out["lists_b"][sl] = A, B
        pa, pb = out["p_a"][sl] * EXAM * PLAY_SCALE, out["p_b"][sl] * EXAM * PLAY_SCALE
        out["x_pre"][sl] = g.binomial(sess_pre[sl][:, None], pa).sum(1)
        out["y_a"][sl] = g.binomial(sess_exp[sl][:, None], pa).sum(1)
        out["y_b"][sl] = g.binomial(sess_exp[sl][:, None], pb).sum(1)
        # guardrail: sesiones sin ningún play ("abandono de la home")
        p0a, p0b = np.prod(1 - pa, 1), np.prod(1 - pb, 1)
        out["zero_a"][sl] = g.binomial(sess_exp[sl], p0a) / np.maximum(sess_exp[sl], 1)
        out["zero_b"][sl] = g.binomial(sess_exp[sl], p0b) / np.maximum(sess_exp[sl], 1)
    out["sessions"] = sess_exp; out["day"] = g.integers(1, 15, n); out["user_id"] = np.arange(n) + 10_000_000
    return out

t0 = time.time()
pop_sim = build_population(N_POP)
print(f"Población simulada: {N_POP:,} usuarios en {time.time() - t0:.0f}s | plays medios A={pop_sim['y_a'].mean():.3f}, "
      f"B={pop_sim['y_b'].mean():.3f} (lift real oculto: {pop_sim['y_b'].mean() / pop_sim['y_a'].mean() - 1:+.2%})")
'''


def build_project() -> None:
    nb = Notebook("Proyecto 15 · Simulador de A/B + interleaving para CineMatch", colab_path=PROJECT)

    nb.md(f"""
{nb.badge()}

# Proyecto 15 · Simulador de A/B test + interleaving y análisis estadístico completo

**Nivel:** 🟠 Avanzado / 🔴 Experto · **Duración:** 4 h · **Hardware:** CPU (sin GPU) · **Unidades de Colab:** < 1
**Prerrequisitos:** lección 15. Conecta con el proyecto 14 (el dossier OPE decide qué va a A/B) y con 17 (monitoreo post-lanzamiento).
""")

    nb.md("""
## 🎬 Contexto de negocio

Eres el/la *data scientist* de experimentación de **CineMatch**. El equipo de ranking tiene un **ranker B** (nueva versión del modelo de factorización, menos ruidoso) que quiere sustituir al **ranker A** de producción en la fila "Top 10 para ti". El VP de producto pregunta:

1. ¿Cuántos usuarios y cuántos días necesitamos para un A/B fiable?
2. ¿B es mejor? ¿Cuánto, con qué incertidumbre, y rompe algún guardrail?
3. ¿Podríamos haberlo sabido antes y con menos usuarios (CUPED, interleaving)?
4. Si el equipo mira el dashboard cada día, ¿nos engañaremos?

Como no tienes usuarios reales, construyes un **simulador**: una población de usuarios "gemelos" de MovieLens-100K (sus factores latentes y su actividad heterogénea vienen de los ratings reales), con un modelo de examen por posición. El simulador conoce los **resultados potenciales** de cada usuario con A y con B: puedes calificar tus estimadores contra la verdad, cosa imposible en producción.
""")

    nb.md("""
## 📦 Dataset

**MovieLens-100K** (GroupLens; Harper & Konstan, 2015): 100.000 ratings de 943 usuarios sobre 1.682 películas. Se descarga de `files.grouplens.org` (si no hay red, el notebook genera ratings sintéticos con la misma forma para no bloquearse). De él extraemos factores latentes (SVD truncada) y la distribución de actividad, y con ellos simulamos `N_POP` usuarios.

## ✅ Entregables y rúbrica

| # | Entregable | Criterio |
|---|---|---|
| E1 | Power analysis con la varianza del periodo previo | n por grupo para MDE = 2 % (analítico y `statsmodels`, que deben coincidir ±1 %) y duración en días |
| E2 | Asignación por hash + SRM | p-valor SRM > 0,001 con tu asignación; detectar un SRM inyectado (p < 0,001) |
| E3 | Análisis del A/B | Lift relativo de B con IC 95 % (método delta para el ratio de medias); el IC **cubre** el lift real del simulador; guardrail "sesiones sin play" analizado |
| E4 | CUPED | Reducción de varianza ≥ 30 % y estimación compatible con la de E3 |
| E5 | Team Draft Interleaving | Implementación propia, test de preferencia sobre ≥ 5.000 usuarios con p < 0,01 a favor de B |
| E6 | Curvas de sensibilidad (bootstrap subsampling) | n para 80 % de potencia en A/B, A/B+CUPED e interleaving; interleaving necesita **≥ 5× menos** usuarios que el A/B |
| E7 | Peeking | En 200 A/A con análisis diario: FPR del test fijo con peeking > 10 % y del mSPRT ≤ 5 % |
| E8 | Memo de decisión | 6–10 líneas: decisión, efecto con IC, guardrails, riesgos (novelty, interferencia) |
""")

    nb.code("!pip install -q statsmodels scipy")
    nb.code(r'''
import warnings, time, hashlib
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from scipy import stats
from statsmodels.stats.power import NormalIndPower
warnings.filterwarnings("ignore")
seed = 42; rng = np.random.default_rng(seed)
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3})

SCALE = "small"                                      # "small" ≈ 2-4 min en CPU | "full" más usuarios y repeticiones
N_POP = 100_000 if SCALE == "small" else 300_000     # usuarios elegibles durante las 2 semanas del experimento
N_BOOT = 150 if SCALE == "small" else 500            # repeticiones de bootstrap subsampling

def todo_guard(fn, *args, **kw):
    try:
        return fn(*args, **kw)
    except NotImplementedError:
        print(f"⏳ {fn.__name__}: TODO pendiente (solución de referencia al final)")
        return None
''')
    nb.code(WORLD_CODE)
    nb.code(WORLD_SIM)

    nb.md("""
> 🔒 **Regla del juego:** en las partes de análisis solo puedes usar lo que verías en producción: para cada usuario, su grupo asignado, `x_pre` (plays previos), el resultado **del grupo en el que está** y su día de entrada. Las columnas `y_a` e `y_b` juntas (resultados potenciales) solo se usan para **calificar**. La celda siguiente crea esa vista "observable".
""")

    nb.code(r'''
def observe(pop, treated: np.ndarray) -> pd.DataFrame:
    """Lo que vería la plataforma: resultado solo del brazo asignado."""
    return pd.DataFrame({"user_id": pop["user_id"], "treated": treated.astype(int), "x_pre": pop["x_pre"],
                         "y": np.where(treated, pop["y_b"], pop["y_a"]),
                         "zero_rate": np.where(treated, pop["zero_b"], pop["zero_a"]), "day": pop["day"]})
TRUE_LIFT = pop_sim["y_b"].mean() / pop_sim["y_a"].mean() - 1      # ¡solo para calificar!
''')

    # ------------------------------------------------------------- TODOs
    nb.md("""
---
## Parte 1 · Diseño: power analysis (E1)

### TODO 1
Con los datos del **periodo previo** (`x_pre`, todos con A) estima μ y σ de "plays por usuario en 2 semanas". Calcula el **n por grupo** para detectar un MDE relativo del 2 % (α=0,05, potencia 0,8) con la fórmula y con `NormalIndPower`, y cuántos días harían falta si entran `N_POP/14` usuarios nuevos al día repartidos en dos grupos.
""")
    nb.code(r'''
def power_analysis(x_pre: np.ndarray, mde_rel: float = 0.02, alpha=0.05, power=0.8) -> dict:
    """Devuelve {'mu','sigma','n_formula','n_statsmodels','dias'}."""
    # TODO
    raise NotImplementedError
design = todo_guard(power_analysis, pop_sim["x_pre"])
''')

    nb.md("""
## Parte 2 · Asignación y SRM (E2)

### TODO 2
1. `assign(user_ids, salt)`: hash MD5 de `f"{salt}:{user_id}"` → bucket 0–999 → tratamiento si bucket < 500.
2. `srm_pvalue(n_t, n_c)`: χ² de bondad de ajuste contra 50/50.
3. Simula un bug: el 3 % de los usuarios tratados no registra la exposición. ¿Lo detecta tu SRM?
""")
    nb.code(r'''
def assign(user_ids, salt: str) -> np.ndarray:
    # TODO
    raise NotImplementedError

def srm_pvalue(n_t: int, n_c: int) -> float:
    # TODO
    raise NotImplementedError

treated = todo_guard(assign, pop_sim["user_id"], "cinematch_top10_rankerB_v2")
''')

    nb.md("""
## Parte 3 · Análisis del A/B (E3)

### TODO 3
- `ab_analysis(df)`: diferencia de medias con Welch, IC 95 %, p-valor y **lift relativo** $\\bar Y_T/\\bar Y_C - 1$ con IC por **método delta** (varianza del ratio de dos medias independientes: $\\mathrm{Var}(\\bar Y_T/\\bar Y_C) \\approx \\frac{1}{\\bar Y_C^2}\\mathrm{Var}(\\bar Y_T) + \\frac{\\bar Y_T^2}{\\bar Y_C^4}\\mathrm{Var}(\\bar Y_C)$).
- Repite para el guardrail `zero_rate` (fracción de sesiones sin ningún play: **menos es mejor**).
""")
    nb.code(r'''
def ab_analysis(y_t: np.ndarray, y_c: np.ndarray) -> dict:
    """Devuelve {'diff','se','p','lift','lift_lo','lift_hi'}."""
    # TODO
    raise NotImplementedError
''')

    nb.md("""
## Parte 4 · CUPED (E4)

### TODO 4
Implementa `cuped(y, x)` con θ estimado sobre todos los usuarios y repite el análisis de la Parte 3 con la métrica ajustada. Reporta la reducción de varianza $1 - \\mathrm{Var}(Y^{cuped})/\\mathrm{Var}(Y)$ y compárala con $\\rho^2$.
""")
    nb.code(r'''
def cuped(y: np.ndarray, x: np.ndarray) -> tuple:
    """Devuelve (y_ajustada, theta)."""
    # TODO
    raise NotImplementedError
''')

    nb.md("""
## Parte 5 · Team Draft Interleaving (E5)

### TODO 5
1. Implementa `team_draft(list_a, list_b, k, rng)` → `(lista, equipos)`.
2. `interleaving_deltas(pop, idx, rng)`: para cada usuario de `idx`, construye la lista mezclada de `lists_a`/`lists_b`, simula sus plays en `sessions` sesiones con `EXAM * p * PLAY_SCALE` (la `p` de cada ítem está en `p_a`/`p_b`) y devuelve $\\Delta_i = \\text{plays}_B - \\text{plays}_A$.
3. Test t de una muestra sobre Δ con 5.000 usuarios **distintos** de los del A/B (aquí: una muestra aleatoria de la población).
""")
    nb.code(r'''
def team_draft(list_a, list_b, k, rng):
    # TODO
    raise NotImplementedError

def interleaving_deltas(pop, idx: np.ndarray, rng) -> np.ndarray:
    # TODO
    raise NotImplementedError
''')

    nb.md("""
## Parte 6 · Sensibilidad: ¿cuántos usuarios necesita cada método? (E6)

### TODO 6
Con *bootstrap subsampling* (como el post de Netflix de 2017) estima la potencia para varios tamaños totales $n$: A/B (Welch), A/B + CUPED e interleaving (t de una muestra). Dibuja las tres curvas, calcula el $n$ para 80 % de potencia y el **ratio A/B / interleaving**.

Pista: para el A/B, toma $n/2$ usuarios al azar en tratamiento (usa `y_b`) y $n/2$ **distintos** en control (usa `y_a`).
""")
    nb.code(r'''
def sensitivity_curves(pop, deltas_pool: np.ndarray, n_grid, n_boot, rng) -> pd.DataFrame:
    """DataFrame con columnas n, power_ab, power_cuped, power_il."""
    # TODO
    raise NotImplementedError
''')

    nb.md("""
## Parte 7 · El dashboard diario: peeking (E7)

### TODO 7
Simula **200 A/A tests** con la población (asignación aleatoria 50/50, ambos con A: usa `y_a`). Cada día $d=1..14$ analiza a los usuarios con `day ≤ d` (los que ya han entrado). Calcula la tasa de A/As en los que **algún día** p < 0,05 con el test fijo, y con p-valores **mSPRT** (mezcla normal, $\\tau^2$ = (2 % de la media)²).
""")
    nb.code(r'''
def peeking_study(pop, n_aa: int, rng) -> dict:
    """Devuelve {'fpr_fixed_last_day','fpr_peeking','fpr_msprt'}."""
    # TODO
    raise NotImplementedError
''')

    nb.md("""
## Parte 8 · Memo de decisión (E8)

### TODO 8 — escribe aquí tu memo
*Decisión (lanzar / no lanzar / iterar), efecto en plays con IC, guardrail, qué aportaron CUPED e interleaving, riesgos (novelty: solo 2 semanas; interferencia: ninguna aparente en este producto; efecto a largo plazo en retención: ¿qué surrogate usarías?).*
""")

    # ------------------------------------------------------------- SOLUCIÓN
    nb.md("""
---
# ⛔ SPOILER — intenta resolverlo primero

Solución de referencia completa. Redefine cada función y ejecuta las comprobaciones de la rúbrica.
""")

    nb.md("### Solución · Partes 1–2")
    nb.code(r'''
def power_analysis(x_pre, mde_rel=0.02, alpha=0.05, power=0.8) -> dict:
    mu, sigma = x_pre.mean(), x_pre.std(ddof=1)
    delta = mde_rel * mu
    n_formula = 2 * (stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)) ** 2 * sigma ** 2 / delta ** 2
    n_sm = NormalIndPower().solve_power(effect_size=delta / sigma, alpha=alpha, power=power, ratio=1.0)
    per_day_per_group = N_POP / 14 / 2
    return dict(mu=mu, sigma=sigma, n_formula=int(np.ceil(n_formula)), n_statsmodels=int(np.ceil(n_sm)),
                dias=int(np.ceil(n_formula / per_day_per_group)))

design = power_analysis(pop_sim["x_pre"])
print(design, "| E1", "✅" if abs(design["n_formula"] / design["n_statsmodels"] - 1) < 0.01 else "❌")
print(f"Con CV={design['sigma']/design['mu']:.2f}, MDE 2 % ⇒ {design['n_formula']:,} usuarios/grupo ≈ {design['dias']} días "
      "(redondea a semanas completas por la estacionalidad semanal).")

def assign(user_ids, salt):
    b = np.array([int(hashlib.md5(f"{salt}:{u}".encode()).hexdigest()[:8], 16) % 1000 for u in user_ids])
    return b < 500

def srm_pvalue(n_t, n_c):
    n = n_t + n_c
    return stats.chisquare([n_t, n_c], f_exp=[n / 2, n / 2]).pvalue

treated = assign(pop_sim["user_id"], "cinematch_top10_rankerB_v2")
p_ok = srm_pvalue(treated.sum(), (~treated).sum())
lost = treated & (np.random.default_rng(1).random(N_POP) < 0.03)
p_bug = srm_pvalue((treated & ~lost).sum(), (~treated).sum())
print(f"SRM limpio p={p_ok:.3f} | con bug p={p_bug:.1e}  →  E2 {'✅' if (p_ok > 1e-3 and p_bug < 1e-3) else '❌'}")
obs = observe(pop_sim, treated)
''')

    nb.md("### Solución · Partes 3–4")
    nb.code(r'''
def ab_analysis(y_t, y_c) -> dict:
    mt, mc = y_t.mean(), y_c.mean()
    vt, vc = y_t.var(ddof=1) / len(y_t), y_c.var(ddof=1) / len(y_c)
    se = np.sqrt(vt + vc); p = stats.ttest_ind(y_t, y_c, equal_var=False).pvalue
    lift = mt / mc - 1
    se_lift = np.sqrt(vt / mc ** 2 + mt ** 2 * vc / mc ** 4)              # método delta
    return dict(diff=mt - mc, se=se, p=p, lift=lift, lift_lo=lift - 1.96 * se_lift, lift_hi=lift + 1.96 * se_lift)

def cuped(y, x):
    theta = np.cov(y, x)[0, 1] / np.var(x, ddof=1)
    return y - theta * (x - x.mean()), theta

T = obs.treated.values == 1
res = ab_analysis(obs.y.values[T], obs.y.values[~T])
grd = ab_analysis(obs.zero_rate.values[T], obs.zero_rate.values[~T])
y_cu, theta = cuped(obs.y.values, obs.x_pre.values)
# Para el lift relativo con CUPED usamos como denominador la media de control sin ajustar:
lift_cu = (y_cu[T].mean() - y_cu[~T].mean()) / obs.y.values[~T].mean()
se_cu = np.sqrt(y_cu[T].var(ddof=1) / T.sum() + y_cu[~T].var(ddof=1) / (~T).sum()) / obs.y.values[~T].mean()
var_red = 1 - y_cu.var() / obs.y.values.var(); rho2 = np.corrcoef(obs.y, obs.x_pre)[0, 1] ** 2

tab = pd.DataFrame({"A/B": [res["lift"], res["lift_lo"], res["lift_hi"], res["p"]],
                    "A/B + CUPED": [lift_cu, lift_cu - 1.96 * se_cu, lift_cu + 1.96 * se_cu, 2 * stats.norm.sf(abs(lift_cu / se_cu))],
                    "Guardrail: sesiones sin play": [grd["lift"], grd["lift_lo"], grd["lift_hi"], grd["p"]]},
                   index=["lift", "IC95 inf", "IC95 sup", "p"]).T
display(tab.round(4)); print(f"Lift REAL del simulador: {TRUE_LIFT:+.2%}")
print("E3", "✅" if res["lift_lo"] <= TRUE_LIFT <= res["lift_hi"] else "❌",
      f"| E4 reducción de varianza {var_red:.0%} (ρ²={rho2:.0%}) θ={theta:.2f}", "✅" if var_red >= 0.30 else "❌")
''')

    nb.md("### Solución · Parte 5")
    nb.code(r'''
def team_draft(list_a, list_b, k, rng):
    out, team, used = [], [], set(); ia = ib = na = nb = 0
    while len(out) < k:
        pick_a = (na < nb) or (na == nb and rng.random() < 0.5)
        for attempt in range(2):
            src, i = (list_a, ia) if pick_a else (list_b, ib)
            while i < len(src) and src[i] in used: i += 1
            if i < len(src): break
            pick_a = not pick_a                                     # ese ranker se quedó sin ítems
        else:
            break
        out.append(src[i]); used.add(src[i]); team.append(0 if pick_a else 1)
        if pick_a: ia, na = i + 1, na + 1
        else: ib, nb = i + 1, nb + 1
    return out, team

def interleaving_deltas(pop, idx, rng):
    d = np.empty(len(idx))
    for j, u in enumerate(idx):
        la, lb = pop["lists_a"][u].tolist(), pop["lists_b"][u].tolist()
        lst, team = team_draft(la, lb, TOPK, rng)
        pmap = dict(zip(la, pop["p_a"][u])); pmap.update(zip(lb, pop["p_b"][u]))
        p = np.array([pmap[i] for i in lst]) * EXAM[:len(lst)] * PLAY_SCALE
        plays = rng.binomial(pop["sessions"][u], p); team = np.array(team)
        d[j] = plays[team == 1].sum() - plays[team == 0].sum()
    return d

g_il = np.random.default_rng(3)
il_idx = g_il.choice(N_POP, 5000, replace=False)
d5k = interleaving_deltas(pop_sim, il_idx, g_il)
t_il = stats.ttest_1samp(d5k, 0)
print(f"Interleaving (5.000 usuarios): Δ medio={d5k.mean():+.4f}, usuarios con preferencia≠0 = {(d5k != 0).mean():.0%},"
      f" p={t_il.pvalue:.1e}  →  E5 {'✅' if (t_il.pvalue < 0.01 and d5k.mean() > 0) else '❌'}")
''')

    nb.md("### Solución · Parte 6")
    nb.code(r'''
def sensitivity_curves(pop, deltas_pool, n_grid, n_boot, rng) -> pd.DataFrame:
    ya, yb, x = pop["y_a"], pop["y_b"], pop["x_pre"]
    theta = np.cov(ya, x)[0, 1] / np.var(x, ddof=1); xm = x.mean()
    rows = []
    for n in n_grid:
        h = n // 2; hits = np.zeros(3)
        for _ in range(n_boot):
            it, ic = rng.choice(len(ya), h), rng.choice(len(ya), h)
            r = stats.ttest_ind(yb[it], ya[ic], equal_var=False)
            hits[0] += (r.pvalue < 0.05) and (r.statistic > 0)
            rc = stats.ttest_ind(yb[it] - theta * (x[it] - xm), ya[ic] - theta * (x[ic] - xm), equal_var=False)
            hits[1] += (rc.pvalue < 0.05) and (rc.statistic > 0)
            d = deltas_pool[rng.choice(len(deltas_pool), n)]
            ri = stats.ttest_1samp(d, 0)
            hits[2] += (ri.pvalue < 0.05) and (ri.statistic > 0)
        rows.append(dict(n=n, power_ab=hits[0] / n_boot, power_cuped=hits[1] / n_boot, power_il=hits[2] / n_boot))
    return pd.DataFrame(rows)

t0 = time.time(); g_s = np.random.default_rng(4)
pool_idx = g_s.choice(N_POP, 20_000, replace=False)
deltas_pool = interleaving_deltas(pop_sim, pool_idx, g_s)
n_grid = np.unique(np.logspace(2, np.log10(N_POP), 12).astype(int))
curves = sensitivity_curves(pop_sim, deltas_pool, n_grid, N_BOOT, g_s)
print(f"{time.time() - t0:.0f}s")
def n80(col):
    ok = curves[col] >= 0.8
    return int(curves.n[ok].iloc[0]) if ok.any() else np.inf
n_ab, n_cu, n_il = n80("power_ab"), n80("power_cuped"), n80("power_il")
plt.figure(figsize=(9, 4.3))
for col, lab, c in [("power_ab", "A/B", "#0072b2"), ("power_cuped", "A/B + CUPED", "#009e73"), ("power_il", "Interleaving (Team Draft)", "#d55e00")]:
    plt.semilogx(curves.n, curves[col], "o-", lw=2, label=lab, color=c)
plt.axhline(0.8, ls="--", color="k"); plt.xlabel("usuarios totales en el experimento (log)"); plt.ylabel("potencia")
plt.title("Sensibilidad por bootstrap subsampling (ranker B vs A)"); plt.legend(); plt.show()
print(f"n para 80 % de potencia → A/B: {n_ab:,} | A/B+CUPED: {n_cu:,} | interleaving: {n_il:,}  ⇒ ratio A/B/IL ≈ {n_ab / n_il:.0f}×"
      f"  →  E6 {'✅' if n_ab / n_il >= 5 else '❌'}")
''')

    nb.md("### Solución · Parte 7")
    nb.code(r'''
def peeking_study(pop, n_aa, rng) -> dict:
    y, day = pop["y_a"], pop["day"]
    tau2 = (0.02 * y.mean()) ** 2
    any_fixed, any_msprt, last_fixed = 0, 0, 0
    for _ in range(n_aa):
        grp = rng.random(len(y)) < 0.5
        p_days, diffs, vars_ = [], [], []
        for d in range(1, 15):
            m = day <= d; yt, yc = y[m & grp], y[m & ~grp]
            diff = yt.mean() - yc.mean(); v = yt.var(ddof=1) / len(yt) + yc.var(ddof=1) / len(yc)
            diffs.append(diff); vars_.append(v); p_days.append(2 * stats.norm.sf(abs(diff) / np.sqrt(v)))
        V, D = np.array(vars_), np.array(diffs)
        lam = np.sqrt(V / (V + tau2)) * np.exp(tau2 * D ** 2 / (2 * V * (V + tau2)))
        p_av = np.minimum.accumulate(np.minimum(1, 1 / lam))
        any_fixed += min(p_days) < 0.05; last_fixed += p_days[-1] < 0.05; any_msprt += p_av.min() < 0.05
    return dict(fpr_fixed_last_day=last_fixed / n_aa, fpr_peeking=any_fixed / n_aa, fpr_msprt=any_msprt / n_aa)

t0 = time.time(); peek = peeking_study(pop_sim, 200, np.random.default_rng(5)); print(f"{time.time() - t0:.0f}s", peek)
plt.figure(figsize=(6.5, 3.6))
plt.bar(["Test fijo\n(solo día 14)", "Test fijo\n+ peeking diario", "mSPRT\n+ peeking diario"],
        [peek["fpr_fixed_last_day"] * 100, peek["fpr_peeking"] * 100, peek["fpr_msprt"] * 100], color=["#9e9e9e", "#c53030", "#009e73"])
plt.axhline(5, ls="--", color="k"); plt.ylabel("falsos positivos en A/A (%)"); plt.title("El coste de mirar el dashboard cada día"); plt.show()
print("E7", "✅" if (peek["fpr_peeking"] > 0.10 and peek["fpr_msprt"] <= 0.05) else "❌")
''')

    nb.code(r'''
# Resumen visual del experimento: efecto acumulado día a día (lo que vería el dashboard) con IC fijo e IC "siempre válido"
days_, est_, lo_, hi_ = [], [], [], []
for d in range(1, 15):
    m = obs.day.values <= d
    r = ab_analysis(obs.y.values[m & T], obs.y.values[m & ~T]); days_.append(d); est_.append(r["lift"]); lo_.append(r["lift_lo"]); hi_.append(r["lift_hi"])
plt.figure(figsize=(8, 3.8))
plt.fill_between(days_, np.array(lo_) * 100, np.array(hi_) * 100, alpha=0.25, color="#0072b2", label="IC 95 % (horizonte fijo)")
plt.plot(days_, np.array(est_) * 100, "o-", color="#0072b2", label="lift estimado acumulado")
plt.axhline(TRUE_LIFT * 100, color="k", ls="--", label="lift real (simulador)"); plt.axhline(0, color="k", lw=0.5)
plt.xlabel("día del experimento"); plt.ylabel("lift en plays (%)"); plt.title("Evolución del A/B ranker B vs A"); plt.legend(fontsize=8); plt.show()
''')

    nb.md("""
### Solución · Memo de decisión (ejemplo; ajusta las cifras a tu ejecución)

> **Decisión: lanzar el ranker B en la fila "Top 10 para ti".** El A/B con N_POP usuarios durante 14 días muestra un aumento de plays por usuario del orden de +4–5 % (IC 95 % excluye el 0; con CUPED el IC es ~2× más estrecho porque la varianza baja >50 %). El guardrail "sesiones sin play" mejora (baja), no empeora. Interleaving habría detectado la preferencia por B con un orden de magnitud menos usuarios: para la próxima iteración del ranker, usaremos interleaving como primera fase de poda y reservaremos el A/B para medir el impacto en negocio. El dashboard diario se analizará con p-valores siempre válidos (mSPRT) para evitar decisiones precipitadas. **Riesgos:** 2 semanas no permiten descartar novelty (mirar el efecto por cohorte de entrada); el efecto en retención a 3 meses no se observa: mantener un *holdout* del 1 % con A durante 8 semanas y estimar el efecto con un surrogate index validado (horas, días activos, títulos distintos).
""")

    nb.md("""
---
## 🚀 Retos extra (nivel experto)

1. **Novelty:** añade al simulador un efecto que decae ($\\tau_d = \\tau_\\infty + (\\tau_0 - \\tau_\\infty)e^{-d/\\kappa}$) y detecta el decaimiento comparando cohortes por día de entrada.
2. **Group sequential:** implementa fronteras O'Brien–Fleming con *alpha spending* de Lan–DeMets para 2 análisis intermedios + el final, y compara potencia con mSPRT.
3. **Multileaving:** compara 4 rankers a la vez con *Team Draft Multileaving* (Schuth et al.) y estima cuántos usuarios necesitas para ordenar los 4.
4. **Interferencia:** introduce un catálogo "de estreno" con licencias limitadas (cada título solo puede reproducirse N veces al día) y mide el sesgo del A/B por usuario frente a un *switchback* por días.
5. **HTE:** estima el efecto de B por cuartil de actividad con un T-learner y con `econml` (`CausalForestDML`); ¿a quién ayuda más?
6. **Herramientas:** reproduce el análisis con GrowthBook (open source) apuntando a un DuckDB con las tablas `exposures` y `events` que generas desde el simulador.

## 🤔 Reflexión (producción / MLOps)

- ¿Dónde vive la lógica de asignación (hash + salt) en vuestra arquitectura, y cómo garantizas que el servicio de recomendación y el pipeline de análisis usan **la misma**?
- ¿Cómo versionarías la definición de métricas (SQL) para que un experimento de hoy sea comparable con uno de hace un año?
- ¿Qué alertas automáticas pondrías (SRM, guardrails, A/A continuos) y quién recibe la alerta?
- Tras lanzar B, ¿cómo conectas el resultado del A/B con el monitoreo del módulo 17 (deriva de las métricas online frente a las del experimento)?
""")

    nb.save(PROJECT)


if __name__ == "__main__":
    build_lesson()
    build_project()
