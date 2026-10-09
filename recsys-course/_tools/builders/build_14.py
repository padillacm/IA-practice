"""Builder del módulo 14 · Bandits, RL y Off-Policy Evaluation.

Ejecutar desde la raíz del repo:  python recsys-course/_tools/builders/build_14.py
Genera:
  recsys-course/14_bandits_rl_ope/14_bandits_rl_ope.ipynb          (lección)
  recsys-course/14_bandits_rl_ope/14_proyecto_artwork_bandit_ope.ipynb (proyecto)
"""
import os
import sys

sys.path.insert(0, "recsys-course/_tools")
from nbbuild import Notebook  # noqa: E402

MOD = "14_bandits_rl_ope"
os.makedirs(f"recsys-course/{MOD}", exist_ok=True)
LESSON = f"recsys-course/{MOD}/{MOD}.ipynb"
PROJECT = f"recsys-course/{MOD}/14_proyecto_artwork_bandit_ope.ipynb"

# -----------------------------------------------------------------------------
# Celdas compartidas
# -----------------------------------------------------------------------------
PIP_OBP = r'''
# obp (Open Bandit Pipeline) declara python<3.11 y fija versiones antiguas (torch 1.12,
# sklearn 1.1...). En el Colab actual (Python 3.12) `pip install obp` falla al resolver.
# Su código funciona con numpy/pandas/sklearn/torch modernos, así que lo instalamos SIN
# dependencias (Colab ya trae todas las que usa: numpy, scipy, sklearn, pandas, torch,
# matplotlib, seaborn, tqdm, pyyaml). Probado con obp 0.5.7 (última versión publicada).
!pip install -q --no-deps --ignore-requires-python obp==0.5.7
'''

SETUP = r'''
import warnings, time, math
from dataclasses import dataclass
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

warnings.filterwarnings("ignore")
seed = 42
rng = np.random.default_rng(seed)
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3,
                     "axes.spines.top": False, "axes.spines.right": False})
COLORS = {"random": "#9e9e9e", "eps": "#e69f00", "ucb": "#0072b2", "ts": "#d55e00",
          "linucb": "#009e73", "lints": "#cc79a7", "dm": "#56b4e9", "ips": "#e69f00",
          "snips": "#f0e442", "dr": "#009e73", "switch": "#cc79a7"}

FAST_DEV_RUN = True   # True: simulaciones cortas (~5 min en CPU). False: curvas más suaves (~20 min).
N_RUNS = 20 if FAST_DEV_RUN else 100     # repeticiones Monte Carlo de cada bandit
T_MAB = 3000 if FAST_DEV_RUN else 10000   # pasos por simulación
print("FAST_DEV_RUN =", FAST_DEV_RUN)
'''

DRAW = r'''
def box(ax, xy, w, h, text, fc="#e8f1fb", ec="#2b6cb0", fs=10, bold=False):
    """Caja redondeada con texto centrado (para diagramas)."""
    p = FancyBboxPatch(xy, w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                       fc=fc, ec=ec, lw=1.5)
    ax.add_patch(p)
    ax.text(xy[0] + w / 2, xy[1] + h / 2, text, ha="center", va="center", fontsize=fs,
            weight="bold" if bold else "normal", wrap=True)

def arrow(ax, p0, p1, text="", color="#444", fs=9, rad=0.0, offset=(0, 0.08)):
    a = FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=15, color=color, lw=1.6,
                        connectionstyle=f"arc3,rad={rad}")
    ax.add_patch(a)
    if text:
        mx, my = (p0[0] + p1[0]) / 2 + offset[0], (p0[1] + p1[1]) / 2 + offset[1]
        ax.text(mx, my, text, ha="center", va="bottom", fontsize=fs, color=color)
'''

# Simulador de artwork de CineMatch (lo usan lección y proyecto)
ARTWORK_ENV = r'''
THEMES = ["romance", "comedia", "acción", "estrella"]   # "temas" visuales de una imagen

@dataclass
class ArtworkWorld:
    """Mundo sintético de CineMatch: por cada (usuario, título) elegimos 1 de K imágenes.

    - Cada usuario tiene un vector de gustos u ∈ R^4 sobre los temas visuales.
    - Cada imagen k de un título tiene un vector de temas φ_k ∈ {0,1}^4.
    - P(play | u, título, k) = σ(b_título + u·W·φ_k)  ← verdad oculta.
    """
    n_titles: int = 30
    n_art: int = 4
    d_user: int = 6
    seed: int = 0

    def __post_init__(self):
        g = np.random.default_rng(self.seed)
        self.title_bias = g.normal(-3.0, 0.4, self.n_titles)
        # imágenes: cada una resalta 1-2 temas
        self.art = np.zeros((self.n_titles, self.n_art, 4))
        for t in range(self.n_titles):
            for k in range(self.n_art):
                self.art[t, k, k % 4] = 1.0
                if g.random() < 0.3:
                    self.art[t, k, g.integers(4)] = 1.0
        self.W = g.normal(0, 0.9, (self.d_user, 4))    # cómo los rasgos de usuario activan temas
        self.art_quality = g.normal(0, 0.25, (self.n_titles, self.n_art))

    def sample_users(self, n, g):
        """Rasgos de usuario: segmento de gusto dominante + ruido (one-hot suave + continuo)."""
        seg = g.integers(0, 4, n)
        X = g.normal(0, 0.5, (n, self.d_user))
        X[np.arange(n), seg] += 1.5
        return X, seg

    def logits(self, X, t):
        """Logit verdadero para cada imagen del título t. X: (n,d) -> (n,K)."""
        return (self.title_bias[t][:, None] + self.art_quality[t]
                + np.einsum("nd,dj,nkj->nk", X, self.W, self.art[t]))

    def p_play(self, X, t):
        return 1.0 / (1.0 + np.exp(-self.logits(X, t)))

    def features(self, X, t):
        """Features (usuario ⊗ imagen) para un bandit lineal con parámetros compartidos.
        Devuelve (n, K, d_user*4 + 4): producto exterior + temas de la imagen (sesgo por tema)."""
        A = self.art[t]                                   # (n,K,4)
        outer = np.einsum("nd,nkj->nkdj", X, A).reshape(len(X), self.n_art, -1)
        return np.concatenate([outer, A], axis=2)
'''


# =============================================================================
# LECCIÓN
# =============================================================================
def build_lesson() -> None:
    nb = Notebook("Módulo 14 · Bandits, RL y Off-Policy Evaluation", colab_path=LESSON)

    nb.md(f"""
{nb.badge()}

# Módulo 14 · Bandits, Reinforcement Learning y Off-Policy Evaluation

**Nivel:** 🟠 Avanzado → 🔴 Experto (secciones de OPE doblemente robusta y RL off-policy)
**Duración estimada:** 5–6 h (lección) + 4 h (proyecto)
**Hardware:** CPU estándar de Colab es suficiente (todo es NumPy/sklearn). **Unidades de Colab estimadas:** < 1 (sin GPU).
**Prerrequisitos:** 01 (sesgos de exposición y MNAR), 02 (evaluación offline), 06 (predicción de CTR), 07 (IPS en *unbiased LTR*), 13 (feedback loops).

> 💡 Hasta ahora hemos tratado la recomendación como **aprendizaje supervisado sobre logs**. Pero esos logs los generó *tu propio sistema*: solo sabes qué pasa con lo que **mostraste**. Este módulo trata de decidir qué mostrar sabiendo que tu decisión condiciona los datos con los que aprenderás mañana.
""")

    nb.md("""
## 🎯 Objetivos de aprendizaje

Al terminar este módulo serás capaz de:

1. **Formalizar** la recomendación como un problema de *multi-armed bandit* (MAB), *contextual bandit* y *Markov Decision Process* (MDP), y definir el **regret**.
2. **Implementar desde cero** ε-greedy, UCB1, Thompson Sampling (Beta-Bernoulli), LinUCB y Thompson lineal, y **comparar** su regret acumulado.
3. **Explicar** cómo Netflix personaliza el *artwork* de cada título con bandits contextuales y cómo lo evalúa offline con *replay*.
4. **Derivar e implementar** los estimadores de *off-policy evaluation* (OPE): Direct Method, IPS, SNIPS, Doubly Robust y Switch-DR, y **medir** empíricamente su sesgo, varianza y MSE.
5. **Usar Open Bandit Pipeline (obp)** sobre el **Open Bandit Dataset** de ZOZOTOWN para evaluar una política real contra su valor *on-policy*.
6. **Implementar** REINFORCE con la corrección *top-K off-policy* de YouTube (Chen et al., 2019) y **explicar** la descomposición de SlateQ (Ie et al., 2019).
7. **Argumentar** por qué el RL en recomendación es difícil (varianza de importance weights, simuladores, recompensas retardadas) y cuándo NO usarlo.
""")

    nb.md("""
### 🗺️ Índice

1. Intuición: explorar vs explotar
2. Multi-armed bandits: teoría, ε-greedy, UCB1, Thompson Sampling
3. Bandits contextuales: LinUCB y Thompson lineal
4. Caso Netflix: personalización de *artwork*
5. Off-policy evaluation desde cero: DM, IPS, SNIPS, DR, Switch-DR
6. OPE en la industria: Open Bandit Pipeline + Open Bandit Dataset
7. RL para recomendación: MDP, REINFORCE top-K, SlateQ, simuladores
8. 🏭 En producción · 🧠 Secretos de la élite · ⚠️ Errores comunes · Autoevaluación · Referencias
""")

    nb.code(PIP_OBP)
    nb.code(SETUP)
    nb.code(DRAW)

    # ------------------------------------------------------------------ 1
    nb.md("""
---
## 1 · Intuición primero: el dilema explorar–explotar

Imagina que acabas de mudarte a una ciudad con 10 restaurantes. Cada noche eliges uno.
- Si siempre vas al que mejor te ha ido hasta hoy (**explotar**), quizá nunca descubras que el tercero que probaste una sola vez (y un mal día) era el mejor.
- Si cada noche pruebas uno al azar (**explorar**), aprenderás mucho… y cenarás mal muy a menudo.

En recomendación pasa exactamente lo mismo, pero con un giro que lo hace **más grave que en ML supervisado**:

| ML supervisado (lo que ya conoces) | Recomendación interactiva |
|---|---|
| Los datos de entrenamiento existen *antes* del modelo. | Los datos los **genera el propio modelo**: solo observas la reacción a lo que mostraste. |
| Etiqueta completa: sabes la clase correcta. | **Feedback parcial (bandit feedback)**: sabes si el usuario hizo clic en la película mostrada, no qué habría hecho con las otras 9.999. |
| El error de hoy no cambia los datos de mañana. | Un modelo que nunca muestra un ítem **nunca aprenderá** que era bueno → *feedback loop* (módulo 13). |

> 💡 Un *bandit* es como un clasificador en el que solo ves la etiqueta de **la clase que predijiste**, y cada predicción te cuesta dinero.

El siguiente diagrama compara ambos bucles.
""")

    nb.code(r'''
fig, axes = plt.subplots(1, 2, figsize=(13, 4.2))
for ax in axes:
    ax.set_xlim(0, 10); ax.set_ylim(0, 5); ax.axis("off")

ax = axes[0]; ax.set_title("ML supervisado: datos fijos → modelo", fontsize=12)
box(ax, (0.3, 2.0), 2.6, 1.2, "Dataset\n(x, y) completo", fc="#eef6ee", ec="#2f855a")
box(ax, (3.9, 2.0), 2.4, 1.2, "Entrenar\nf(x) ≈ y")
box(ax, (7.2, 2.0), 2.4, 1.2, "Predecir\n(no cambia\nlos datos)", fc="#fdf2e9", ec="#c05621")
arrow(ax, (2.9, 2.6), (3.9, 2.6)); arrow(ax, (6.3, 2.6), (7.2, 2.6))

ax = axes[1]; ax.set_title("Bandit / RL: el modelo genera sus propios datos", fontsize=12)
box(ax, (0.3, 3.3), 2.8, 1.2, "Contexto x_t\n(usuario, hora,\ndispositivo)", fc="#eef6ee", ec="#2f855a")
box(ax, (3.8, 3.3), 2.6, 1.2, "Política π(a|x)\nelige acción a_t", fc="#e8f1fb")
box(ax, (7.1, 3.3), 2.6, 1.2, "Usuario\n(entorno)", fc="#fdf2e9", ec="#c05621")
box(ax, (3.8, 0.4), 2.6, 1.2, "Log: (x, a, r, π(a|x))\n¡solo la acción\nmostrada!", fc="#fff5f5", ec="#c53030")
arrow(ax, (3.1, 3.9), (3.8, 3.9)); arrow(ax, (6.4, 3.9), (7.1, 3.9), "muestra a_t")
arrow(ax, (8.4, 3.3), (6.4, 1.0), "recompensa r_t\n(clic / play)", rad=-0.2, offset=(0.6, -0.3))
arrow(ax, (3.8, 1.0), (2.2, 3.3), "re-entrena", rad=-0.3, offset=(-0.6, -0.2))
plt.tight_layout(); plt.show()
''')

    nb.md("""
### A/B test vs bandit: dos formas de repartir tráfico

Un **A/B test** reparte el tráfico 50/50 durante todo el experimento para *medir* con precisión (módulo 15). Un **bandit** desplaza el tráfico hacia el brazo ganador a medida que aprende, para *ganar* durante el experimento. El precio: estimaciones más ruidosas del brazo perdedor y menos garantías estadísticas.

El área entre la recompensa óptima y la obtenida es el **regret** (arrepentimiento): cuánto dejaste de ganar por no saber de antemano cuál era el mejor brazo.
""")

    nb.code(r'''
# Ilustración: 2 variantes de artwork con CTR 4 % y 5 %. A/B fijo vs Thompson Sampling.
p_true = np.array([0.04, 0.05]); T = 20000
g = np.random.default_rng(seed)
alpha, beta_ = np.ones(2), np.ones(2); share_b, reward_ab, reward_ts = [], [], []
for t in range(T):
    a = int(np.argmax(g.beta(alpha, beta_)))
    r = g.random() < p_true[a]; alpha[a] += r; beta_[a] += 1 - r
    share_b.append(a == 1); reward_ts.append(p_true[a])
    reward_ab.append(p_true[t % 2])

w = 500
share_b = np.convolve(share_b, np.ones(w) / w, mode="valid")
fig, axes = plt.subplots(1, 2, figsize=(13, 4))
axes[0].plot(np.full(T, 0.5), label="A/B test (50/50 fijo)", color=COLORS["random"], lw=2)
axes[0].plot(np.arange(len(share_b)) + w, share_b, label="Thompson Sampling", color=COLORS["ts"], lw=2)
axes[0].set(title="Fracción de tráfico enviado a la variante B (mejor)", xlabel="usuario t", ylabel="fracción", ylim=(0, 1.05))
axes[0].legend()
regret_ab = np.cumsum(p_true.max() - np.array(reward_ab))
regret_ts = np.cumsum(p_true.max() - np.array(reward_ts))
axes[1].plot(regret_ab, label="A/B test", color=COLORS["random"], lw=2)
axes[1].plot(regret_ts, label="Thompson Sampling", color=COLORS["ts"], lw=2)
axes[1].set(title="Regret acumulado (plays perdidos esperados)", xlabel="usuario t", ylabel="regret")
axes[1].legend(); plt.tight_layout(); plt.show()
print(f"Plays perdidos: A/B ≈ {regret_ab[-1]:.0f}  vs  TS ≈ {regret_ts[-1]:.0f}")
''')

    nb.md("""
> ⚠️ **Cuándo NO usar un bandit en lugar de un A/B test:** cuando necesitas una estimación insesgada y con intervalo de confianza del efecto (decisión de producto, métricas a largo plazo, guardrails), o cuando la recompensa tarda semanas en llegar (retención). Los bandits brillan en decisiones **repetidas, de recompensa rápida y con muchas variantes**: artwork, titulares, orden de filas, cold start de ítems nuevos.
""")

    # ------------------------------------------------------------------ 2
    nb.md(r"""
---
## 2 · Multi-armed bandits (MAB)

### 📐 Formalización

- Hay $K$ brazos (acciones): p. ej. $K$ imágenes candidatas para un título.
- En cada ronda $t = 1,\dots,T$ la política elige un brazo $a_t \in \{1,\dots,K\}$ y observa una recompensa $r_t \sim \text{Bernoulli}(\mu_{a_t})$ (play / no play).
- $\mu_a$ es la recompensa esperada (desconocida) del brazo $a$; $\mu^* = \max_a \mu_a$; el *gap* es $\Delta_a = \mu^* - \mu_a$.

El **regret (pseudo-regret) acumulado** tras $T$ rondas es

$$
R_T \;=\; T\mu^* - \mathbb{E}\Big[\sum_{t=1}^{T} \mu_{a_t}\Big] \;=\; \sum_{a} \Delta_a\, \mathbb{E}[N_a(T)],
$$

donde $N_a(T)$ es cuántas veces se eligió el brazo $a$. Minimizar regret = no gastar demasiadas rondas en brazos malos, pero las suficientes para estar seguro de que son malos.

**Cota inferior (Lai & Robbins, 1985):** cualquier política "razonable" cumple $\mathbb{E}[N_a(T)] \gtrsim \frac{\ln T}{\mathrm{KL}(\mu_a \,\|\, \mu^*)}$, es decir, el regret crece **al menos logarítmicamente** en $T$. Una política que se queda con un brazo malo para siempre tiene regret **lineal**.

### Las tres políticas clásicas

**ε-greedy.** Con probabilidad $\varepsilon$ elige un brazo al azar; si no, el de mayor media empírica $\hat\mu_a$. Simple, pero explora "a ciegas" (igual de a menudo un brazo claramente malo que uno dudoso) → regret lineal con $\varepsilon$ fijo; con $\varepsilon_t \propto 1/t$ puede ser logarítmico.

**UCB1 (Auer et al., 2002) — optimismo ante la incertidumbre.** Por la desigualdad de Hoeffding, para recompensas en $[0,1]$:
$P\big(\mu_a > \hat\mu_a + u\big) \le e^{-2 N_a u^2}$. Si exigimos que esa probabilidad sea $t^{-4}$ y despejamos $u$:

$$
e^{-2N_a u^2} = t^{-4} \;\Rightarrow\; u = \sqrt{\frac{2\ln t}{N_a}}
\qquad\Rightarrow\qquad
a_t = \arg\max_a \Big[\hat\mu_a + \sqrt{\tfrac{2\ln t}{N_a}}\Big].
$$

El bonus es grande para brazos poco probados: o el brazo es bueno, o lo descartas rápido. Regret $O\big(\sum_a \frac{\ln T}{\Delta_a}\big)$.

**Thompson Sampling (Thompson, 1933; Chapelle & Li, 2011) — *probability matching*.** Mantén una posterior sobre cada $\mu_a$. Con prior $\text{Beta}(1,1)$ y likelihood Bernoulli, la posterior es conjugada:

$$
\mu_a \mid \text{datos} \sim \text{Beta}(1 + S_a,\; 1 + F_a),
$$

con $S_a$ éxitos y $F_a$ fracasos. En cada ronda **muestrea** $\tilde\mu_a$ de cada posterior y juega $\arg\max_a \tilde\mu_a$. Así, cada brazo se elige con probabilidad igual a la probabilidad (posterior) de ser el mejor. Es asintóticamente óptimo para Bernoulli (Kaufmann et al., 2012; Agrawal & Goyal, 2012) y en la práctica suele ganar a UCB.
""")

    nb.code(r'''
class BernoulliBandit:
    """Entorno: K brazos con probabilidad de éxito mu (desconocida para la política)."""
    def __init__(self, mu, rng):
        self.mu, self.rng = np.asarray(mu), rng
        self.best = self.mu.max()
    def pull(self, a: int) -> float:
        return float(self.rng.random() < self.mu[a])

class EpsilonGreedy:
    name = "ε-greedy (ε=0.1)"
    def __init__(self, K, rng, eps=0.1):
        self.eps, self.rng = eps, rng
        self.n, self.s = np.zeros(K), np.zeros(K)
    def select(self, t):
        if self.rng.random() < self.eps or t < len(self.n):
            return int(self.rng.integers(len(self.n)))
        return int(np.argmax(self.s / np.maximum(self.n, 1)))
    def update(self, a, r):
        self.n[a] += 1; self.s[a] += r

class UCB1:
    name = "UCB1"
    def __init__(self, K, rng):
        self.n, self.s = np.zeros(K), np.zeros(K)
    def select(self, t):
        if t < len(self.n):                      # jugar cada brazo una vez
            return t
        ucb = self.s / self.n + np.sqrt(2 * np.log(t + 1) / self.n)
        return int(np.argmax(ucb))
    def update(self, a, r):
        self.n[a] += 1; self.s[a] += r

class ThompsonBeta:
    name = "Thompson Sampling"
    def __init__(self, K, rng, a0=1.0, b0=1.0):
        self.a, self.b, self.rng = np.full(K, a0), np.full(K, b0), rng
    def select(self, t):
        return int(np.argmax(self.rng.beta(self.a, self.b)))
    def update(self, a, r):
        self.a[a] += r; self.b[a] += 1 - r

def run_mab(policy_cls, mu, T, n_runs, seed=0, **kw):
    """Devuelve matriz (n_runs, T) de regret acumulado y conteos finales por brazo."""
    regrets, counts = np.zeros((n_runs, T)), np.zeros((n_runs, len(mu)))
    for run in range(n_runs):
        g = np.random.default_rng(seed + run)
        env, pol = BernoulliBandit(mu, g), policy_cls(len(mu), g, **kw)
        inst = np.empty(T)
        for t in range(T):
            a = pol.select(t); r = env.pull(a); pol.update(a, r)
            inst[t] = env.best - mu[a]; counts[run, a] += 1
        regrets[run] = np.cumsum(inst)
    return regrets, counts
''')

    nb.md("""
🧪 **Experimento.** 8 imágenes candidatas para la ficha de un título, con tasas de *play* entre 2 % y 6 % (órdenes de magnitud realistas para un *take rate* por impresión). Comparamos regret acumulado medio ± 1 desviación estándar sobre `N_RUNS` repeticiones, con una política aleatoria como referencia.
""")

    nb.code(r'''
mu = np.array([0.020, 0.025, 0.030, 0.035, 0.040, 0.045, 0.050, 0.060])

class RandomPolicy:
    name = "Aleatoria"
    def __init__(self, K, rng): self.K, self.rng = K, rng
    def select(self, t): return int(self.rng.integers(self.K))
    def update(self, a, r): pass

t0 = time.time()
results = {}
for cls, key in [(RandomPolicy, "random"), (EpsilonGreedy, "eps"), (UCB1, "ucb"), (ThompsonBeta, "ts")]:
    results[key] = (cls.name, *run_mab(cls, mu, T_MAB, N_RUNS))
print(f"Simulación: {time.time() - t0:.1f}s")

fig, axes = plt.subplots(1, 2, figsize=(13, 4.3))
for key, (name, reg, cnt) in results.items():
    m, s = reg.mean(0), reg.std(0)
    axes[0].plot(m, label=name, color=COLORS[key], lw=2)
    axes[0].fill_between(np.arange(T_MAB), m - s, m + s, color=COLORS[key], alpha=0.15)
axes[0].set(title="Regret acumulado (media ± 1 σ)", xlabel="ronda t", ylabel="R_t"); axes[0].legend()
width = 0.2
for i, key in enumerate(["eps", "ucb", "ts"]):
    name, reg, cnt = results[key]
    axes[1].bar(np.arange(len(mu)) + (i - 1) * width, cnt.mean(0) / T_MAB, width, label=name, color=COLORS[key])
axes[1].set_xticks(range(len(mu)), [f"{m:.1%}" for m in mu])
axes[1].set(title="Fracción de tiradas por brazo (μ real en el eje x)", xlabel="μ del brazo", ylabel="fracción")
axes[1].legend(); plt.tight_layout(); plt.show()
''')

    nb.md("""
**Lectura del gráfico.**
- La política aleatoria y ε-greedy con ε fijo tienen **regret lineal**: siguen pagando la exploración para siempre (ε-greedy paga ε·Δ̄ por ronda).
- UCB1 y Thompson tienen regret **sublineal** (curvan). UCB1 es conservador con brazos cercanos (2 % vs 6 % es fácil; 5 % vs 6 % no), Thompson concentra antes el tráfico.
- La varianza entre ejecuciones de ε-greedy es grande: si al principio "se casa" con un brazo malo, tarda en salir.

Veamos *por qué* Thompson funciona: la evolución de sus posteriores Beta.
""")

    nb.code(r'''
from scipy import stats
g = np.random.default_rng(7)
env, pol = BernoulliBandit(mu[[0, 4, 6, 7]], g), ThompsonBeta(4, g)
snapshots, checkpoints = {}, [10, 200, 1000, 5000]
for t in range(max(checkpoints)):
    a = pol.select(t); pol.update(a, env.pull(a))
    if t + 1 in checkpoints:
        snapshots[t + 1] = (pol.a.copy(), pol.b.copy())

xs = np.linspace(0, 0.15, 500)
fig, axes = plt.subplots(1, 4, figsize=(15, 3.4), sharey=False)
for ax, (t, (a_, b_)) in zip(axes, snapshots.items()):
    for k in range(4):
        ax.plot(xs, stats.beta.pdf(xs, a_[k], b_[k]), lw=2, label=f"μ={env.mu[k]:.0%} (n={int(a_[k]+b_[k]-2)})")
        ax.axvline(env.mu[k], ls=":", color=f"C{k}")
    ax.set(title=f"t = {t}", xlabel="μ"); ax.legend(fontsize=7)
fig.suptitle("Posteriores Beta de Thompson Sampling: se estrechan donde merece la pena", y=1.03)
plt.tight_layout(); plt.show()
''')

    nb.md("""
> 💡 Observa que el brazo malo (2 %) **nunca** llega a tener una posterior estrecha: Thompson deja de jugarlo en cuanto es improbable que sea el mejor. No necesita saber *cuánto* de malo es, solo que no es el mejor. Esto es exactamente lo que quieres en producción: no malgastar impresiones en caracterizar perdedores.
""")

    # ------------------------------------------------------------------ 3
    nb.md(r"""
---
## 3 · Bandits contextuales: LinUCB y Thompson lineal

En recomendación la mejor imagen **depende del usuario**: el fan de la comedia responde a otra imagen que el fan del romance. Un *contextual bandit* observa un contexto $x_t$ antes de decidir.

### 📐 LinUCB (Li, Chu, Langford & Schapire, 2010 — noticias de Yahoo!)

Supuesto: la recompensa esperada es lineal en las features, $\mathbb{E}[r \mid x, a] = x_{t,a}^\top \theta^*$. Aquí $x_{t,a}\in\mathbb{R}^d$ son features de (contexto, acción), por ejemplo el producto exterior usuario ⊗ imagen (variante *shared*, un solo $\theta$; la variante *disjoint* del paper tiene un $\theta_a$ por brazo).

Estimación por **ridge regression** con todo lo observado:

$$
A_t = \lambda I + \sum_{s<t} x_{s,a_s} x_{s,a_s}^\top, \qquad b_t = \sum_{s<t} r_s\, x_{s,a_s}, \qquad \hat\theta_t = A_t^{-1} b_t .
$$

La incertidumbre de la predicción en la dirección $x$ es $\sqrt{x^\top A_t^{-1} x}$ (es la desviación estándar de $x^\top\hat\theta$ salvo un factor $\sigma$). LinUCB elige

$$
a_t = \arg\max_a \; x_{t,a}^\top \hat\theta_t + \alpha \sqrt{x_{t,a}^\top A_t^{-1} x_{t,a}} .
$$

Para no invertir $A$ en cada paso usamos **Sherman–Morrison**: $(A + xx^\top)^{-1} = A^{-1} - \frac{A^{-1}x x^\top A^{-1}}{1 + x^\top A^{-1} x}$, coste $O(d^2)$ por actualización.

### 📐 Thompson Sampling lineal (Agrawal & Goyal, 2013)

Con prior gaussiano, la posterior de $\theta$ es aproximadamente $\mathcal{N}(\hat\theta_t,\, v^2 A_t^{-1})$. En cada ronda: muestrea $\tilde\theta \sim \mathcal{N}(\hat\theta_t, v^2 A_t^{-1})$ y elige $\arg\max_a x_{t,a}^\top\tilde\theta$. Igual de barato que LinUCB y suele explorar mejor en práctica.

> 💡 Conexión con lo que sabes: LinUCB es **una regresión lineal online** cuyo intervalo de confianza decide a quién mostrar qué. Cualquier modelo que dé incertidumbre calibrada (ensembles, dropout bayesiano, *neural-linear*: red neuronal + última capa bayesiana — Riquelme et al., 2018) puede jugar el mismo papel.
""")

    nb.code(ARTWORK_ENV)

    nb.code(r'''
class LinearBandit:
    """Bandit lineal con parámetros compartidos. mode='ucb' (LinUCB) o 'ts' (Thompson lineal)."""
    def __init__(self, d, mode="ucb", alpha=1.0, v=0.5, lam=1.0, rng=None):
        self.mode, self.alpha, self.v = mode, alpha, v
        self.A_inv = np.eye(d) / lam
        self.b = np.zeros(d)
        self.rng = rng or np.random.default_rng(0)
    @property
    def theta(self):
        return self.A_inv @ self.b
    def select(self, Xa):
        """Xa: (K, d) features de cada acción para el contexto actual."""
        if self.mode == "ucb":
            mean = Xa @ self.theta
            bonus = np.sqrt(np.einsum("kd,de,ke->k", Xa, self.A_inv, Xa))
            return int(np.argmax(mean + self.alpha * bonus))
        L = np.linalg.cholesky(self.v ** 2 * self.A_inv + 1e-10 * np.eye(len(self.b)))
        theta_s = self.theta + L @ self.rng.standard_normal(len(self.b))
        return int(np.argmax(Xa @ theta_s))
    def update(self, x, r):
        Ax = self.A_inv @ x                                   # Sherman–Morrison
        self.A_inv -= np.outer(Ax, Ax) / (1.0 + x @ Ax)
        self.b += r * x

def run_contextual(world, policy_name, T, seed=0, **kw):
    """Simula T usuarios llegando a la ficha de títulos aleatorios. Devuelve regret por paso."""
    g = np.random.default_rng(seed)
    X, _ = world.sample_users(T, g); titles = g.integers(0, world.n_titles, T)
    d = world.d_user * 4 + 4
    pol = None if policy_name in ("random", "eps", "global_ts") else LinearBandit(d, rng=g, **kw)
    S = np.ones((world.n_titles, world.n_art)); F = np.ones((world.n_titles, world.n_art))
    eps_model = LinearBandit(d, mode="ucb", alpha=0.0, rng=g)  # ridge "greedy" para ε-greedy
    inst = np.empty(T)
    for t in range(T):
        x, ti = X[t:t + 1], titles[t:t + 1]
        p = world.p_play(x, ti)[0]; Xa = world.features(x, ti)[0]
        if policy_name == "random":
            a = int(g.integers(world.n_art))
        elif policy_name == "eps":
            a = int(g.integers(world.n_art)) if g.random() < 0.1 else eps_model.select(Xa)
        elif policy_name == "global_ts":           # MAB por título, sin personalizar
            a = int(np.argmax(g.beta(S[ti[0]], F[ti[0]])))
        else:
            a = pol.select(Xa)
        r = float(g.random() < p[a])
        if policy_name == "eps": eps_model.update(Xa[a], r)
        elif policy_name == "global_ts": S[ti[0], a] += r; F[ti[0], a] += 1 - r
        elif pol is not None: pol.update(Xa[a], r)
        inst[t] = p.max() - p[a]
    return inst
''')

    nb.code(r'''
world = ArtworkWorld(seed=1)
T_CTX = 6000 if FAST_DEV_RUN else 20000
R_CTX = 4 if FAST_DEV_RUN else 10
configs = [("random", "Aleatoria", {}, "random"), ("eps", "ε-greedy lineal (ε=0.1)", {}, "eps"),
           ("global_ts", "Thompson por título (no personaliza)", {}, "ts"),
           ("lin", "LinUCB (α=0.5)", dict(mode="ucb", alpha=0.5), "linucb"),
           ("lin", "Thompson lineal (v=0.3)", dict(mode="ts", v=0.3), "lints")]
t0 = time.time(); ctx_res = {}
for pname, label, kw, ckey in configs:
    regs = np.stack([np.cumsum(run_contextual(world, pname, T_CTX, seed=s, **kw)) for s in range(R_CTX)])
    ctx_res[label] = (regs, ckey)
print(f"Simulación contextual: {time.time() - t0:.1f}s")

plt.figure(figsize=(9, 4.5))
for label, (regs, ckey) in ctx_res.items():
    m = regs.mean(0); plt.plot(m, label=label, color=COLORS[ckey], lw=2)
    plt.fill_between(np.arange(T_CTX), regs.min(0), regs.max(0), color=COLORS[ckey], alpha=0.12)
plt.title("Artwork de CineMatch: regret acumulado de bandits contextuales")
plt.xlabel("impresión t"); plt.ylabel("plays perdidos esperados"); plt.legend(); plt.show()
''')

    nb.md("""
**Lectura.** El Thompson por título (el enfoque "encuentra la mejor imagen *global* de cada título", que según el blog de Netflix fue su primer paso) aprende rápido pero se estanca: su regret sigue creciendo porque **la mejor imagen depende del usuario**. Los bandits lineales comparten información entre títulos e imágenes a través de las features (usuario ⊗ temas) y siguen bajando el regret instantáneo.

🧪 **Sensibilidad a α (LinUCB):** α controla cuánta exploración haces. Demasiado poca → te quedas en un óptimo local; demasiada → pagas exploración innecesaria.
""")

    nb.code(r'''
alphas = [0.0, 0.1, 0.5, 1.0, 2.0, 4.0]
final = []
for al in alphas:
    regs = [run_contextual(world, "lin", T_CTX // 2, seed=s, mode="ucb", alpha=al).sum() for s in range(R_CTX)]
    final.append((np.mean(regs), np.std(regs)))
final = np.array(final)
plt.figure(figsize=(7, 3.8))
plt.errorbar(alphas, final[:, 0], yerr=final[:, 1], marker="o", capsize=4, color=COLORS["linucb"])
plt.xscale("symlog", linthresh=0.1)
plt.title(f"LinUCB: regret tras {T_CTX//2} impresiones vs α"); plt.xlabel("α (symlog)"); plt.ylabel("regret")
plt.show()
''')

    # ------------------------------------------------------------------ 4
    nb.md(r"""
---
## 4 · 🏭 Caso Netflix: personalización de *artwork*

En diciembre de 2017 Netflix publicó *"Artwork Personalization at Netflix"* (Chandrashekar, Amat, Basilico y Jebara). Ideas clave del post, que conviene leer entero:

- **El problema.** Para cada par (miembro, título) hay que elegir **una** imagen entre varias candidatas. La imagen es *evidencia visual* de por qué ese título podría interesarte. Ejemplos del post: para *Good Will Hunting*, a alguien que ve mucho romance quizá le funcione una imagen de Matt Damon y Minnie Driver; a alguien de comedias, una con Robin Williams. Para *Pulp Fiction*, una imagen de Uma Thurman o de John Travolta según los actores que hayas visto.
- **Primer paso (no personalizado):** bandits para encontrar la mejor imagen *de cada título para todos* (lo que hemos llamado "Thompson por título").
- **Por qué bandits contextuales:** el contexto incluye historial de visionado, país, idioma, dispositivo, hora…; la política aprende de los datos de **exploración aleatorizada controlada** que ella misma inyecta. Un enfoque por lotes clásico (entrenar un clasificador sobre logs) no funcionaría bien porque los logs sin aleatorizar están sesgados por la política anterior.
- **Escala:** el post habla de un pico de más de **20 millones de peticiones de imágenes personalizadas por segundo**, con baja latencia. Por eso la selección se precalcula en gran parte (*offline/nearline*, módulo 16) y se sirve desde caché.
- **Evaluación offline por *replay*** (Li et al., 2011) sobre los datos de exploración: se cuentan solo las impresiones en las que la imagen que habría elegido el nuevo modelo **coincide** con la que se mostró al azar. La métrica es el *take fraction*: plays / impresiones.
- **Dificultades reconocidas en el post:** atribución (¿el play viene de la recomendación del título o de la imagen?), interacción con el resto del sistema de recomendación, y evitar *clickbait*: una imagen que engaña sube los plays pero deja usuarios insatisfechos.

> ⚠️ Los detalles exactos del modelo de producción (features, arquitectura, ganancias) no son públicos más allá de lo descrito en el post y en la charla de Justin Basilico en QCon SF 2018. No inventes cifras en entrevistas.

### 📐 El estimador *replay* (Li, Chu, Langford & Wang, WSDM 2011)

Si la política de logging fue **uniforme** sobre $K$ acciones, entonces

$$
\hat V_{\text{replay}}(\pi) = \frac{\sum_i r_i\, \mathbb{1}\{\pi(x_i) = a_i\}}{\sum_i \mathbb{1}\{\pi(x_i) = a_i\}}
$$

es insesgado para el valor de $\pi$ (determinista). Usa solo ~$1/K$ de los datos. Es un caso particular de IPS (sección 5) con propensión $1/K$ y auto-normalizado.
""")

    nb.code(r'''
def log_uniform(world, n, g):
    """Datos de exploración: imagen uniformemente al azar (propensión 1/K)."""
    X, seg = world.sample_users(n, g); t = g.integers(0, world.n_titles, n)
    a = g.integers(0, world.n_art, n)
    p = world.p_play(X, t); r = (g.random(n) < p[np.arange(n), a]).astype(float)
    return dict(X=X, seg=seg, t=t, a=a, r=r, p=p)

def replay_estimate(logs, chosen):
    m = chosen == logs["a"]
    return logs["r"][m].mean(), m.sum()

g = np.random.default_rng(3)
train = log_uniform(world, 40000, g); test = log_uniform(world, 40000, g)

# Política personalizada aprendida OFFLINE con regresión logística sobre features usuario⊗imagen
from sklearn.linear_model import LogisticRegression
F_tr = world.features(train["X"], train["t"])[np.arange(len(train["a"])), train["a"]]
clf = LogisticRegression(C=1.0, max_iter=2000).fit(F_tr, train["r"])
F_te = world.features(test["X"], test["t"])                       # (n,K,d)
scores = clf.decision_function(F_te.reshape(-1, F_te.shape[-1])).reshape(F_te.shape[:2])
pi_personal = scores.argmax(1)
# Política global: la imagen con mayor take-rate empírico por título (sin personalizar)
tr_df = pd.DataFrame(dict(t=train["t"], a=train["a"], r=train["r"]))
best_global = tr_df.groupby(["t", "a"]).r.mean().unstack().values.argmax(1)
pi_global = best_global[test["t"]]
pi_random = g.integers(0, world.n_art, len(test["a"]))

rows = []
for name, pi in [("Aleatoria", pi_random), ("Mejor global por título", pi_global), ("Personalizada (logística)", pi_personal)]:
    v_true = test["p"][np.arange(len(pi)), pi].mean()
    v_rep, n_match = replay_estimate(test, pi)
    rows.append(dict(política=name, take_rate_real=v_true, replay=v_rep, n_match=n_match))
replay_df = pd.DataFrame(rows); display(replay_df.round(4))
''')

    nb.code(r'''
fig, axes = plt.subplots(1, 2, figsize=(13, 4))
x = np.arange(len(replay_df)); w = 0.35
axes[0].bar(x - w/2, replay_df.take_rate_real, w, label="valor real (oráculo)", color="#4a5568")
axes[0].bar(x + w/2, replay_df.replay, w, label="estimación replay", color=COLORS["ts"])
axes[0].set_xticks(x, replay_df.política, rotation=10); axes[0].set(title="Replay ≈ valor real (logs uniformes)", ylabel="take rate")
axes[0].legend()
# Take rate real por segmento de gusto
seg_rows = []
for name, pi in [("Mejor global", pi_global), ("Personalizada", pi_personal)]:
    v = test["p"][np.arange(len(pi)), pi]
    for s in range(4):
        seg_rows.append(dict(política=name, segmento=THEMES[s], take=v[test["seg"] == s].mean()))
seg_df = pd.DataFrame(seg_rows).pivot(index="segmento", columns="política", values="take").loc[THEMES]
seg_df.plot.bar(ax=axes[1], color=["#9e9e9e", COLORS["linucb"]], rot=0)
axes[1].set(title="Take rate real por segmento de gusto", ylabel="take rate", xlabel="gusto dominante del usuario")
plt.tight_layout(); plt.show()
''')

    nb.md("""
> 🧠 Fíjate en el *trade-off* del replay: con $K=4$ solo usamos ~25 % de las impresiones. Con $K=20$ imágenes, el 5 %. Por eso Netflix (y todo el mundo) pasa de *replay* a **IPS / Doubly Robust**, que usan *todos* los datos y admiten políticas de logging no uniformes. Es lo que viene ahora.
""")

    # ------------------------------------------------------------------ 5
    nb.md(r"""
---
## 5 · Off-Policy Evaluation (OPE) desde cero

**Pregunta:** tengo logs generados por la política de producción $\pi_0$ (*logging / behavior policy*). ¿Cuál sería el valor (CTR, plays…) de una política nueva $\pi_e$ (*evaluation / target policy*) **sin desplegarla**?

Es el equivalente bandit de la "evaluación offline" del módulo 02, pero hecha bien: el módulo 02 evaluaba sobre lo que el usuario *vio*, lo cual favorece a modelos que imitan a la política de producción.

### 📐 Notación
- Logs $\mathcal{D} = \{(x_i, a_i, r_i, p_i)\}_{i=1}^n$ con $x_i \sim p(x)$, $a_i \sim \pi_0(\cdot \mid x_i)$, $r_i \sim p(r \mid x_i, a_i)$ y **propensión registrada** $p_i = \pi_0(a_i \mid x_i)$.
- Recompensa esperada $q(x,a) = \mathbb{E}[r\mid x,a]$; un modelo de ella $\hat q(x,a)$.
- Valor objetivo: $V(\pi_e) = \mathbb{E}_{x}\,\mathbb{E}_{a\sim\pi_e(\cdot|x)}[q(x,a)]$.
- *Importance weight*: $w_i = \pi_e(a_i\mid x_i) / \pi_0(a_i \mid x_i)$.

### Los estimadores

| Estimador | Fórmula | Sesgo | Varianza |
|---|---|---|---|
| **Direct Method (DM)** | $\hat V_{DM} = \frac1n\sum_i \sum_a \pi_e(a\mid x_i)\,\hat q(x_i,a)$ | Alto si $\hat q$ está mal especificado | Baja |
| **IPS** (Horvitz–Thompson) | $\hat V_{IPS} = \frac1n \sum_i w_i\, r_i$ | 0 (si soporte completo) | Alta, explota con $w$ grandes |
| **SNIPS** (Swaminathan & Joachims, 2015) | $\hat V_{SNIPS} = \frac{\sum_i w_i r_i}{\sum_i w_i}$ | $O(1/n)$ | Menor que IPS |
| **Doubly Robust (DR)** (Dudík et al., 2011) | $\hat V_{DR} = \frac1n\sum_i \Big[\sum_a \pi_e(a\mid x_i)\hat q(x_i,a) + w_i\,(r_i - \hat q(x_i,a_i))\Big]$ | 0 si propensiones **o** $\hat q$ son correctos | Menor que IPS si $\hat q$ es bueno |
| **Switch-DR** (Wang, Agarwal & Dudík, 2017) | DR, pero el término de corrección solo si $w_i \le \tau$; si no, solo DM | Controlado por $\tau$ | Controlada por $\tau$ |

**Insesgadez de IPS (derivación en una línea).** Si $\pi_0(a\mid x) > 0$ siempre que $\pi_e(a\mid x)>0$ (*soporte común*):

$$
\mathbb{E}_{a\sim\pi_0}\Big[\tfrac{\pi_e(a|x)}{\pi_0(a|x)}\, r\Big] = \sum_a \pi_0(a|x)\,\tfrac{\pi_e(a|x)}{\pi_0(a|x)}\, q(x,a) = \sum_a \pi_e(a|x)\,q(x,a). \;\checkmark
$$

**Por qué DR es "doblemente robusto".** Reescribe el término de cada ronda como $\text{DM}_i + w_i(r_i - \hat q_i)$. Si $\hat q = q$, la corrección tiene esperanza 0 → DR = DM insesgado. Si las propensiones son correctas, el término $w_i\,\hat q(x_i,a_i)$ tiene la misma esperanza que $\sum_a \pi_e \hat q$ y se cancela → DR = IPS insesgado. La varianza de DR depende de $w_i (r_i - \hat q_i)$: **cuanto mejor es $\hat q$, más pequeños los residuos** y menos amplifica $w$.

**Effective sample size** (diagnóstico obligatorio): $\text{ESS} = \frac{(\sum_i w_i)^2}{\sum_i w_i^2}$. Si tienes 1M de logs y ESS = 800, tu estimación IPS vale lo que un A/B de 800 usuarios.
""")

    nb.code(r'''
def softmax(z, temp=1.0, axis=-1):
    z = z / temp; z = z - z.max(axis=axis, keepdims=True); e = np.exp(z)
    return e / e.sum(axis=axis, keepdims=True)

@dataclass
class SyntheticBanditWorld:
    """Bandit contextual sintético con verdad conocida para estudiar estimadores OPE."""
    K: int = 10
    d: int = 5
    seed: int = 0
    def __post_init__(self):
        g = np.random.default_rng(self.seed)
        self.theta = g.normal(0, 1, (self.d, self.K)); self.bias = g.normal(-1.5, 0.5, self.K)
        self.noise_dir = g.normal(0, 1, (self.d, self.K))     # sesgo del modelo "antiguo"
    def q(self, X):                                            # E[r|x,a]
        z = X @ self.theta + self.bias + 0.6 * np.sin(2 * X[:, :1])   # no-linealidad → DM sesgado
        return 1 / (1 + np.exp(-z))
    def contexts(self, n, g):
        return g.normal(0, 1, (n, self.d))
    def pi_logging(self, X, eps=0.1):
        """Producción: softmax de un modelo antiguo y ruidoso + ε de exploración uniforme."""
        old = X @ (0.5 * self.theta + 0.8 * self.noise_dir) + self.bias
        return (1 - eps) * softmax(old, temp=0.7) + eps / self.K
    def pi_eval(self, X, temp=0.3):
        """Nueva política: softmax (temperatura baja ⇒ casi determinista) de un modelo mejor."""
        return softmax(X @ self.theta + self.bias, temp=temp)
    def log(self, n, g):
        X = self.contexts(n, g); P0 = self.pi_logging(X)
        a = (P0.cumsum(1) > g.random((n, 1))).argmax(1)
        r = (g.random(n) < self.q(X)[np.arange(n), a]).astype(float)
        return X, a, r, P0[np.arange(n), a]
    def true_value(self, temp=0.3, n=400_000, seed=999):
        X = self.contexts(n, np.random.default_rng(seed))
        return float((self.pi_eval(X, temp) * self.q(X)).sum(1).mean())

sbw = SyntheticBanditWorld()
print("V(π_e) real =", round(sbw.true_value(), 4))
X, a, r, p0 = sbw.log(5, np.random.default_rng(0)); print("ejemplo de log:", a, r, p0.round(3))
''')

    nb.code(r'''
def fit_q_model(X, a, r, K, lam=1.0):
    """Modelo de recompensa sencillo (a propósito LINEAL → mal especificado): ridge por acción.
    Devuelve una función q_hat(X) -> (n,K)."""
    Xb = np.hstack([X, np.ones((len(X), 1))]); W = np.zeros((Xb.shape[1], K))
    for k in range(K):
        m = a == k
        A_ = Xb[m].T @ Xb[m] + lam * np.eye(Xb.shape[1]); W[:, k] = np.linalg.solve(A_, Xb[m].T @ r[m])
    return lambda Xn: np.clip(np.hstack([Xn, np.ones((len(Xn), 1))]) @ W, 0, 1)

def ope_estimates(X, a, r, p0, pi_e, q_hat, tau=None):
    """Calcula DM, IPS, SNIPS, DR y Switch-DR. pi_e: (n,K) probabilidades de la política evaluada."""
    n = len(r); idx = np.arange(n)
    w = pi_e[idx, a] / p0
    qh = q_hat(X); qh_a = qh[idx, a]; dm_i = (pi_e * qh).sum(1)
    est = {"DM": dm_i.mean(), "IPS": (w * r).mean(), "SNIPS": (w * r).sum() / w.sum(),
           "DR": (dm_i + w * (r - qh_a)).mean()}
    if tau is not None:
        est["Switch-DR"] = (dm_i + (w <= tau) * w * (r - qh_a)).mean()
    est["ESS"] = w.sum() ** 2 / (w ** 2).sum()
    return est

def crossfit_q(X, a, r, K, n_folds=2, seed=0):
    """Cross-fitting: q̂ para cada fila se entrena en los OTROS folds (evita sobreajuste en DR)."""
    folds = np.random.default_rng(seed).integers(0, n_folds, len(r)); out = np.zeros((len(r), K))
    for f in range(n_folds):
        q_f = fit_q_model(X[folds != f], a[folds != f], r[folds != f], K); out[folds == f] = q_f(X[folds == f])
    return lambda Xn, _o=out: _o            # solo se usa sobre las mismas X de los logs

g = np.random.default_rng(1)
X, a, r, p0 = sbw.log(5000, g)
est = ope_estimates(X, a, r, p0, sbw.pi_eval(X), crossfit_q(X, a, r, sbw.K), tau=20)
print({k: round(v, 4) for k, v in est.items()}, "| real:", round(sbw.true_value(), 4))
''')

    nb.md("""
🧪 **Estudio Monte Carlo de sesgo y varianza.** Una sola estimación no dice nada: repetimos el experimento de logging `R` veces y miramos la **distribución** de cada estimador alrededor del valor real. Descomponemos $\\text{MSE} = \\text{sesgo}^2 + \\text{varianza}$.
""")

    nb.code(r'''
def mc_study(world, n, R, temp=0.3, tau=20, seed=0):
    rows = []
    for rep in range(R):
        g = np.random.default_rng(seed + rep)
        X, a, r, p0 = world.log(n, g)
        e = ope_estimates(X, a, r, p0, world.pi_eval(X, temp), crossfit_q(X, a, r, world.K, seed=rep), tau=tau)
        rows.append(e)
    return pd.DataFrame(rows)

R_MC = 150 if FAST_DEV_RUN else 500
V_true = sbw.true_value()
t0 = time.time(); mc = mc_study(sbw, n=3000, R=R_MC); print(f"{time.time()-t0:.1f}s")
ests = ["DM", "IPS", "SNIPS", "DR", "Switch-DR"]
summary = pd.DataFrame({"sesgo": mc[ests].mean() - V_true, "varianza": mc[ests].var(),
                        "MSE": ((mc[ests] - V_true) ** 2).mean()})
summary["sesgo²"] = summary.sesgo ** 2
display(summary.style.format("{:.2e}"))
print(f"ESS medio: {mc.ESS.mean():.0f} de 3000 logs")
''')

    nb.code(r'''
fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))
cols = [COLORS[k] for k in ["dm", "ips", "snips", "dr", "switch"]]
parts = axes[0].violinplot([mc[e] for e in ests], showmedians=True)
for pc, c in zip(parts["bodies"], cols): pc.set_facecolor(c); pc.set_alpha(0.6)
axes[0].axhline(V_true, color="k", ls="--", label=f"V(π_e) real = {V_true:.3f}")
axes[0].set_xticks(range(1, 6), ests); axes[0].set(title=f"Distribución de las estimaciones (n=3000, R={R_MC})", ylabel="valor estimado")
axes[0].legend()
xb = np.arange(len(ests))
axes[1].bar(xb, summary["sesgo²"], color="#4a5568", label="sesgo²")
axes[1].bar(xb, summary["varianza"], bottom=summary["sesgo²"], color=cols, label="varianza")
axes[1].set_xticks(xb, ests); axes[1].set(title="MSE = sesgo² + varianza", ylabel="MSE"); axes[1].legend()
plt.tight_layout(); plt.show()
''')

    nb.md("""
**Lectura.**
- **DM** es la más estable pero está **descentrada**: nuestro $\\hat q$ lineal no captura la no-linealidad del mundo. Más datos no arreglan un sesgo de especificación.
- **IPS** está centrado pero con colas largas: unas pocas filas con $w$ enorme dominan la media.
- **SNIPS** recorta mucha varianza a cambio de un sesgo despreciable.
- **DR** combina ambos: centrado (propensiones correctas) y con menos varianza que IPS porque solo pondera los **residuos**.
- **Switch-DR** sacrifica un poco de sesgo (usa DM donde $w>\\tau$) para ganar varianza.

Ahora, ¿cómo evoluciona el MSE con el tamaño de los logs?
""")

    nb.code(r'''
ns = [500, 1000, 3000, 10000] if FAST_DEV_RUN else [500, 1000, 2000, 5000, 10000, 30000]
R_n = 60 if FAST_DEV_RUN else 200
mse_n = {e: [] for e in ests}
for n in ns:
    d_ = mc_study(sbw, n=n, R=R_n, seed=10_000)
    for e in ests: mse_n[e].append(((d_[e] - V_true) ** 2).mean())
plt.figure(figsize=(8, 4.5))
for e, c in zip(ests, cols): plt.loglog(ns, mse_n[e], marker="o", label=e, color=c, lw=2)
plt.title("MSE vs tamaño de los logs: el sesgo de DM no desaparece con más datos")
plt.xlabel("n logs (log)"); plt.ylabel("MSE (log)"); plt.legend(); plt.show()
''')

    nb.md("""
🧪 **El gran enemigo: la divergencia entre políticas.** Cuanto más distinta es $\\pi_e$ de $\\pi_0$ (aquí: temperatura más baja → política más determinista), mayores los *importance weights*, menor el ESS y mayor la varianza de IPS. Y el **umbral τ** de Switch-DR permite movernos en la frontera sesgo–varianza.
""")

    nb.code(r'''
temps = [2.0, 1.0, 0.5, 0.3, 0.15, 0.07]
rows = []
for tp in temps:
    d_ = mc_study(sbw, n=3000, R=R_n, temp=tp, seed=20_000); vt = sbw.true_value(temp=tp)
    rows.append(dict(temp=tp, ESS=d_.ESS.mean(), **{f"sd_{e}": d_[e].std() for e in ["IPS", "SNIPS", "DR"]},
                     **{f"bias_{e}": d_[e].mean() - vt for e in ["DM"]}))
div = pd.DataFrame(rows)
taus = [1, 2, 5, 10, 20, 50, 100, 1e9]
sw = []
for tau in taus:
    d_ = mc_study(sbw, n=3000, R=R_n, temp=0.15, tau=tau, seed=30_000); vt = sbw.true_value(temp=0.15)
    sw.append(dict(tau=tau, bias2=(d_["Switch-DR"].mean() - vt) ** 2, var=d_["Switch-DR"].var()))
sw = pd.DataFrame(sw)

fig, axes = plt.subplots(1, 2, figsize=(14, 4.3))
ax = axes[0]; ax2 = ax.twinx()
for e in ["IPS", "SNIPS", "DR"]:
    ax.plot(div.temp, div[f"sd_{e}"], marker="o", label=f"desv. típica {e}", color=COLORS[e.lower()], lw=2)
ax2.plot(div.temp, div.ESS, "k--", marker="s", label="ESS (eje dcho.)")
ax.set_xscale("log"); ax.invert_xaxis(); ax.set(title="Más determinista π_e ⇒ menos ESS, más varianza", xlabel="temperatura de π_e (← más determinista)", ylabel="desv. típica")
ax2.set_ylabel("ESS"); ax2.grid(False)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, fontsize=8)
lbl = [str(int(t)) if t < 1e8 else "∞ (=DR)" for t in taus]
axes[1].plot(lbl, sw.bias2, marker="o", label="sesgo²", color="#4a5568", lw=2)
axes[1].plot(lbl, sw["var"], marker="o", label="varianza", color=COLORS["switch"], lw=2)
axes[1].plot(lbl, sw.bias2 + sw["var"], marker="o", label="MSE", color="k", lw=2, ls="--")
axes[1].set_yscale("log"); axes[1].set(title="Switch-DR: frontera sesgo–varianza según τ (temp=0.15)", xlabel="τ", ylabel="(log)")
axes[1].legend(); plt.tight_layout(); plt.show()
''')

    nb.md("""
> 🧠 **En la práctica** no eliges τ a ojo: obp implementa selección automática de hiperparámetros de estimadores (SLOPE, Su et al., 2020) y estimadores con *shrinkage* (DRos, Su et al., 2020). Y antes de fiarte de cualquier OPE, compara con un A/B real al menos una vez por familia de modelos (*OPE-vs-online calibration*).
""")

    # ------------------------------------------------------------------ 6
    nb.md("""
---
## 6 · OPE en la industria: Open Bandit Pipeline + Open Bandit Dataset

El **Open Bandit Dataset (OBD)** (Saito, Aihara, Matsutani & Narita — NeurIPS 2021 Datasets & Benchmarks, arXiv:2008.07146) es el único dataset público grande con **propensiones reales** de un sistema en producción: el carrusel de recomendaciones de moda de **ZOZOTOWN** (el mayor e-commerce de moda de Japón).

- 80 ítems (34 en *men*, 46 en *women*; campaña *all* = 80), **3 posiciones** por impresión, recompensa = clic.
- Recogido con **dos políticas en paralelo** durante 7 días: **Random** (uniforme) y **Bernoulli Thompson Sampling (BTS)**. Eso permite un benchmark honesto: estimar con logs de Random el valor de BTS y compararlo con el valor *on-policy* de BTS medido en sus propios logs.
- Versión completa: ~26 M filas, descargable desde la página oficial [research.zozo.com/data.html](https://research.zozo.com/data.html) (licencia CC BY 4.0, pide citar el paper). **El paquete `obp` trae una muestra de 10.000 filas por política/campaña** que usamos aquí (no requiere descarga).

**Open Bandit Pipeline (obp)** — [github.com/st-tech/zr-obp](https://github.com/st-tech/zr-obp) — implementa carga de datos, políticas (online y off-policy learners), modelos de regresión con *cross-fitting* y una docena de estimadores OPE.
""")

    nb.code(r'''
import logging; logging.getLogger("obp").setLevel(logging.WARNING)
from obp.dataset import OpenBanditDataset

datasets = {bp: OpenBanditDataset(behavior_policy=bp, campaign="all") for bp in ["random", "bts"]}
bf = {bp: ds.obtain_batch_bandit_feedback() for bp, ds in datasets.items()}
for bp, b in bf.items():
    print(f"{bp:6s}: n={b['n_rounds']:,}  ítems={b['n_actions']}  posiciones={datasets[bp].len_list}  "
          f"CTR={b['reward'].mean():.4f}  dim(contexto)={b['context'].shape[1]}  "
          f"pscore∈[{b['pscore'].min():.1e}, {b['pscore'].max():.2f}]")
raw = datasets["random"].data; display(raw.iloc[:3, :8])
''')

    nb.code(r'''
fig, axes = plt.subplots(1, 3, figsize=(15, 3.8))
for bp, c in [("random", COLORS["random"]), ("bts", COLORS["ts"])]:
    b = bf[bp]
    ctr_pos = [b["reward"][b["position"] == k].mean() for k in range(3)]
    axes[0].plot(range(1, 4), ctr_pos, marker="o", label=bp, color=c, lw=2)
    cnt = np.bincount(b["action"], minlength=80)
    axes[1].plot(np.sort(cnt)[::-1], label=bp, color=c, lw=2)
axes[0].set(title="CTR por posición (sesgo de posición)", xlabel="posición", ylabel="CTR", xticks=[1, 2, 3]); axes[0].legend()
axes[1].set(title="Impresiones por ítem (ordenado)", xlabel="rango del ítem", ylabel="impresiones"); axes[1].legend()
axes[2].hist(np.log10(bf["bts"]["pscore"]), bins=40, color=COLORS["ts"])
axes[2].axvline(np.log10(1 / 80), color="k", ls="--", label="Random: 1/80")
axes[2].set(title="Propensiones registradas de BTS", xlabel="log10 π_0(a|x)", ylabel="frecuencia"); axes[2].legend()
plt.tight_layout(); plt.show()
print(f"Clics totales en la muestra Random: {int(bf['random']['reward'].sum())}  ← ¡muy pocos! (CTR ~0,4 %)")
''')

    nb.md("""
**Benchmark de estimadores (el experimento del paper).** Usamos logs de **Random** para estimar el valor de **BTS**. La política de evaluación BTS de obp reproduce la de producción (`is_zozotown_prior=True` carga los priors reales) y `compute_batch_action_dist` nos da $\\pi_e(a \\mid x, k)$ para cada posición $k$ por simulación Monte Carlo. La "verdad" es el CTR on-policy de los logs de BTS.
""")

    nb.code(r'''
from sklearn.linear_model import LogisticRegression
from obp.policy import BernoulliTS
from obp.ope import (OffPolicyEvaluation, RegressionModel, DirectMethod, InverseProbabilityWeighting,
                     SelfNormalizedInverseProbabilityWeighting, DoublyRobust, SwitchDoublyRobust)

b_rand = bf["random"]; ds_rand = datasets["random"]
bts = BernoulliTS(n_actions=ds_rand.n_actions, len_list=ds_rand.len_list, is_zozotown_prior=True,
                  campaign="all", random_state=seed)
action_dist = bts.compute_batch_action_dist(n_sim=100_000, n_rounds=b_rand["n_rounds"])   # (n, 80, 3)

reg = RegressionModel(n_actions=ds_rand.n_actions, len_list=ds_rand.len_list, action_context=ds_rand.action_context,
                      base_model=LogisticRegression(C=100, max_iter=1000, random_state=seed))
q_hat_obd = reg.fit_predict(context=b_rand["context"], action=b_rand["action"], reward=b_rand["reward"],
                            position=b_rand["position"], pscore=b_rand["pscore"], n_folds=3, random_state=seed)

ope = OffPolicyEvaluation(bandit_feedback=b_rand, ope_estimators=[
    DirectMethod(), InverseProbabilityWeighting(), SelfNormalizedInverseProbabilityWeighting(),
    DoublyRobust(), SwitchDoublyRobust(lambda_=50, estimator_name="switch-dr(τ=50)")])
point, ci = ope.summarize_off_policy_estimates(action_dist=action_dist, estimated_rewards_by_reg_model=q_hat_obd,
                                               n_bootstrap_samples=500, random_state=seed)
V_bts = OpenBanditDataset.calc_on_policy_policy_value_estimate(behavior_policy="bts", campaign="all")
print(f"Valor on-policy de BTS (verdad): {V_bts:.4f} | CTR de Random: {b_rand['reward'].mean():.4f}")
display(ci.round(5))
''')

    nb.code(r'''
# Nuestra implementación desde cero aplicada a OBD (por posición) — debe coincidir con obp.
n = b_rand["n_rounds"]; idx = np.arange(n); pos = b_rand["position"]; act = b_rand["action"]
pi_e_obs = action_dist[idx, act, pos]                    # π_e(a_i | x_i, k_i)
w_obd = pi_e_obs / b_rand["pscore"]
qh_pos = q_hat_obd[idx, :, pos]                          # (n, 80) q̂(x_i, a, k_i)
dm_i = (action_dist[idx, :, pos] * qh_pos).sum(1)
mine = {"dm": dm_i.mean(), "ipw": (w_obd * b_rand["reward"]).mean(),
        "snipw": (w_obd * b_rand["reward"]).sum() / w_obd.sum(),
        "dr": (dm_i + w_obd * (b_rand["reward"] - qh_pos[idx, act])).mean()}
check = pd.DataFrame({"desde_cero": mine, "obp": point["estimated_policy_value"].reindex(mine.keys())})
check["dif_abs"] = (check.desde_cero - check.obp).abs(); display(check)
print(f"ESS = {w_obd.sum()**2 / (w_obd**2).sum():.0f} de {n} filas")

fig, ax = plt.subplots(figsize=(8, 3.8))
names = ci.index.tolist(); yv = np.arange(len(names))
ax.errorbar(ci["mean"], yv, xerr=[ci["mean"] - ci["95.0% CI (lower)"], ci["95.0% CI (upper)"] - ci["mean"]],
            fmt="o", capsize=4, color="#2b6cb0")
ax.axvline(V_bts, color=COLORS["ts"], ls="--", label="BTS on-policy (verdad)")
ax.axvline(b_rand["reward"].mean(), color=COLORS["random"], ls=":", label="Random (logging)")
ax.set_yticks(yv, names); ax.set(title="OBD (muestra 10k): estimación del CTR de BTS con logs de Random (IC 95 % bootstrap)", xlabel="CTR")
ax.legend(fontsize=8); plt.tight_layout(); plt.show()
''')

    nb.md("""
**Lectura honesta.** Con 10.000 filas y ~40 clics, los intervalos de IPS/DR son enormes y casi todo es compatible con todo. DM tiene un intervalo estrechísimo… y no por ello es correcto (es el intervalo de un modelo, no de la incertidumbre causal). Este gráfico es la mejor lección del módulo: **la OPE en recomendación está limitada por la señal** (CTR bajo, muchas acciones). Con el dataset completo (~1,4 M filas en Random/all) los intervalos se estrechan ~12× (√(n_full/n_muestra)) y el benchmark se vuelve informativo: es el experimento que hace el paper de Saito et al.

> 📚 Para hacerlo a escala: `OpenBanditDataset(behavior_policy="random", campaign="all", data_path=Path("open_bandit_dataset"))` tras descargar y descomprimir el zip de la página oficial.
""")

    # ------------------------------------------------------------------ 7
    nb.md(r"""
---
## 7 · Reinforcement Learning para recomendación

Un bandit optimiza la **recompensa inmediata** de cada decisión. Pero una recomendación cambia al usuario: lo que le enseñas hoy cambia lo que le interesará mañana, si se aburre, si vuelve la semana que viene. Para optimizar **valor a largo plazo** (sesiones, retención) modelamos la recomendación como un **MDP**.

### 📐 MDP para recsys
- **Estado** $s_t$: representación del usuario en el instante $t$ (historial de interacciones, embedding secuencial de SASRec del módulo 09, satisfacción, fatiga…).
- **Acción** $a_t$: el ítem (o *slate* / fila) recomendado. Espacio enorme: millones de ítems; combinatorio si es una lista.
- **Recompensa** $r_t$: clic, minutos vistos, like…
- **Transición** $P(s_{t+1}\mid s_t,a_t)$: cómo cambia el usuario (incluye la probabilidad de **abandonar**: estado terminal).
- **Objetivo**: $\max_\pi \mathbb{E}_\pi\big[\sum_{t\ge0}\gamma^t r_t\big]$ con descuento $\gamma\in[0,1)$.

La función de valor de acción cumple Bellman: $Q^\pi(s,a) = \mathbb{E}[r + \gamma\, \mathbb{E}_{a'\sim\pi} Q^\pi(s',a')]$.
""")

    nb.code(r'''
fig, ax = plt.subplots(figsize=(12, 3.8)); ax.set_xlim(0, 12); ax.set_ylim(0, 4); ax.axis("off")
for i, (t, txt) in enumerate([(0, "s_t\nhistorial,\nsatisfacción"), (1, "s_{t+1}\n(más aburrido\no más fiel)"), (2, "s_{t+2}")]):
    box(ax, (0.3 + 4.2 * i, 1.5), 2.0, 1.3, txt, fc="#eef6ee", ec="#2f855a")
for i in range(2):
    x0 = 2.3 + 4.2 * i
    box(ax, (x0 + 0.35, 2.9), 1.5, 0.8, f"a_{'t' if i == 0 else 't+1'}: slate", fc="#e8f1fb", fs=9)
    arrow(ax, (x0, 2.15), (x0 + 1.9, 2.15), "P(s'|s,a)")
    ax.text(x0 + 1.1, 1.0, f"r_{'t' if i == 0 else 't+1'} = clic / minutos", ha="center", fontsize=9, color="#c05621")
box(ax, (9.3, 0.15), 2.5, 0.9, "abandono (terminal)", fc="#fff5f5", ec="#c53030", fs=9)
arrow(ax, (9.4, 1.5), (10.3, 1.05), color="#c53030")
ax.set_title("La recomendación como MDP: la acción de hoy cambia el estado del usuario mañana")
plt.show()
''')

    nb.md("""
🧪 **Experimento: bandit miope vs RL en un mundo con *clickbait*.** Un usuario tiene un nivel de satisfacción $s\\in\\{0,\\dots,9\\}$. Hay tres tipos de contenido:

| Tipo | P(clic) inmediata | Efecto en satisfacción | |
|---|---|---|---|
| *clickbait* | alta (0,55) | −1 | engancha hoy, quema mañana |
| calidad | media (0,40) | +1 si hay clic | construye relación |
| nicho | baja (0,20) | +2 si hay clic | descubrimiento |

La probabilidad de abandonar la sesión/plataforma tras cada paso es mayor cuanto menor es la satisfacción. Un bandit que maximiza el clic inmediato elegirá siempre *clickbait*. Resolvemos el MDP con **Q-learning tabular** (sin conocer el modelo) y lo comparamos.
""")

    nb.code(r'''
P_CLICK = np.array([0.55, 0.40, 0.20]); D_SAT = np.array([-1, 1, 2]); S_MAX = 9
def churn_prob(s): return 0.35 - 0.035 * s           # s=0 → 35 %, s=9 → 3,5 % de abandono por paso

def step(s, a, g):
    click = g.random() < P_CLICK[a]
    s2 = int(np.clip(s + (D_SAT[a] if (click or a == 0) else 0), 0, S_MAX))
    done = g.random() < churn_prob(s2)
    return s2, float(click), done

def run_episode(policy, g, s0=5, max_len=300, Q=None, N=None, eps=0.0, gamma=0.97):
    """Un usuario = un episodio. Si se pasa Q, se actualiza con Q-learning tabular."""
    s, total, length = s0, 0.0, 0
    while length < max_len:
        a = int(g.integers(3)) if (Q is not None and g.random() < eps) else policy(s)
        s2, r, done = step(s, a, g); total += r; length += 1
        if Q is not None:
            N[s, a] += 1; alpha = 1.0 / N[s, a] ** 0.6       # learning rate decreciente por visita
            target = r + (0.0 if done else gamma * Q[s2].max())
            Q[s, a] += alpha * (target - Q[s, a])
        s = s2
        if done: break
    return total, length

g = np.random.default_rng(seed); Q = np.zeros((S_MAX + 1, 3)); N_sa = np.zeros_like(Q); hist = []
N_EP = 20000 if FAST_DEV_RUN else 60000
for ep in range(N_EP):
    eps = max(0.1, 1 - ep / (0.5 * N_EP))
    hist.append(run_episode(lambda s: int(np.argmax(Q[s])), g, s0=int(g.integers(S_MAX + 1)), Q=Q, N=N_sa, eps=eps)[0])
policies = {"Bandit miope (siempre clickbait)": lambda s: 0, "Siempre calidad": lambda s: 1,
            "Q-learning (greedy)": lambda s: int(np.argmax(Q[s]))}
evals = {k: np.array([run_episode(p, np.random.default_rng(10_000 + i)) for i in range(4000)]) for k, p in policies.items()}
display(pd.DataFrame({k: {"clics por usuario": v[:, 0].mean(), "duración media": v[:, 1].mean(),
                          "CTR por paso": v[:, 0].sum() / v[:, 1].sum()} for k, v in evals.items()}).T.round(3))
print("Acción de Q-learning por nivel de satisfacción:", [["clickbait", "calidad", "nicho"][i] for i in Q.argmax(1)])
''')

    nb.code(r'''
fig, axes = plt.subplots(1, 2, figsize=(13, 4))
k = 500; axes[0].plot(np.convolve(hist, np.ones(k) / k, mode="valid"), color=COLORS["lints"], lw=2, label="Q-learning durante el aprendizaje\n(ε-greedy, estado inicial aleatorio)")
for (name, v), c in zip(evals.items(), ["#c53030", "#9e9e9e", COLORS["linucb"]]):
    axes[0].axhline(v[:, 0].mean(), ls="--", color=c, label=name)
axes[0].set(title="Clics totales por usuario (episodio)", xlabel="episodio", ylabel="clics/usuario"); axes[0].legend(fontsize=8)
im = axes[1].imshow(Q.T, aspect="auto", cmap="viridis"); plt.colorbar(im, ax=axes[1])
axes[1].set(title="Q(s, a) aprendida", xlabel="satisfacción s", yticks=[0, 1, 2]); axes[1].set_yticklabels(["clickbait", "calidad", "nicho"])
plt.tight_layout(); plt.show()
''')

    nb.md("""
**Lectura.** El bandit miope tiene **el mayor CTR por paso** y el **menor valor total**: sus usuarios se van antes. Esta es la razón de negocio del RL en recomendación (y la razón por la que Netflix optimiza retención y satisfacción a largo plazo, no clics; módulo 15). Ojo: este mundo es de juguete; en la vida real **no conoces la dinámica** y no puedes hacer 20.000 episodios de exploración con usuarios reales.

### 📐 REINFORCE con corrección *top-K off-policy* (Chen et al., WSDM 2019 — YouTube)

YouTube entrenó una política softmax $\\pi_\\theta(a\\mid s)$ sobre **millones de vídeos** con REINFORCE, pero **a partir de logs** de otras políticas (los recomendadores existentes), $\\beta$. Tres ingredientes:

1. **Gradiente de política off-policy con importance weighting** (truncado a un paso para controlar varianza):
$$\\nabla_\\theta J \\approx \\sum_{(s,a,R)\\in\\mathcal{D}} \\frac{\\pi_\\theta(a\\mid s)}{\\beta(a\\mid s)}\\, R\\, \\nabla_\\theta \\log \\pi_\\theta(a\\mid s),$$
con $R$ el retorno descontado desde ese paso.
2. **β desconocida → se estima** con otra cabeza softmax que comparte el estado pero **no** propaga gradiente al tronco (*stop-gradient*), entrenada por máxima verosimilitud sobre las acciones logueadas.
3. **Corrección top-K.** La política real muestra $K$ ítems a la vez. Si la *slate* se forma muestreando $K$ veces de $\\pi$, la probabilidad de que $a$ aparezca es $\\alpha(a\\mid s) = 1-(1-\\pi(a\\mid s))^K$. Optimizar esa cantidad da el gradiente
$$\\nabla_\\theta J \\approx \\sum \\underbrace{\\frac{\\pi_\\theta(a\\mid s)}{\\beta(a\\mid s)}}_{\\text{off-policy}}\\; \\underbrace{K\\big(1-\\pi_\\theta(a\\mid s)\\big)^{K-1}}_{\\lambda_K(s,a)}\\; R\\, \\nabla_\\theta \\log\\pi_\\theta(a\\mid s).$$
$\\lambda_K$ **≈ K** cuando $\\pi(a)$ es pequeña (empuja a subir ítems buenos aún no en la slate) y **→ 0** cuando $\\pi(a)$ ya es grande (ese ítem ya entra en el top-K: no gastes más masa en él). Además se usan *weight capping* y normalización para controlar la varianza.

Lo implementamos en NumPy sobre un problema pequeño: 60 ítems, contexto de usuario de 6 dimensiones, logs de una política de producción sesgada a la popularidad.
""")

    nb.code(r'''
N_ITEMS, D_U, K_SLATE = 60, 6, 5
gw = np.random.default_rng(5)
V_item = gw.normal(0, 1, (D_U, N_ITEMS)); pop = gw.normal(0, 1.2, N_ITEMS)
true_bias = gw.normal(-2.0, 0.6, N_ITEMS) - 0.4 * pop       # lo popular no es lo que más gusta
def aug(U): return np.hstack([U, np.ones((len(U), 1))])      # columna de 1s → sesgo por ítem
def q_true(U): return 1 / (1 + np.exp(-(U @ V_item + true_bias)))
W_BETA = np.vstack([0.4 * V_item, 1.5 * pop])               # producción: muy guiada por popularidad
def beta_policy(U): return softmax(aug(U) @ W_BETA)

def make_logs(n, g):
    U = g.normal(0, 1, (n, D_U)); B = beta_policy(U)
    a = (B.cumsum(1) > g.random((n, 1))).argmax(1)
    r = (g.random(n) < q_true(U)[np.arange(n), a]).astype(float)
    return U, a, r, B[np.arange(n), a]

def topk_value(W, U, K=K_SLATE):
    """Valor REAL de la slate determinista top-K de la política: clics esperados por slate."""
    top = np.argsort(-(aug(U) @ W), axis=1)[:, :K]
    return q_true(U)[np.arange(len(U))[:, None], top].sum(1).mean()

def train_reinforce(U, a, r, b, variant, epochs=30, lr=0.5, bs=512, cap=10.0, seed=0):
    """REINFORCE de un paso sobre logs. variant: 'none' | 'is' | 'topk'."""
    g = np.random.default_rng(seed); Ua = aug(U); W = np.zeros((D_U + 1, N_ITEMS)); n = len(r); curve = []
    for ep in range(epochs):
        perm = g.permutation(n)
        for start in range(0, n, bs):
            i = perm[start:start + bs]
            P = softmax(Ua[i] @ W); pa = P[np.arange(len(i)), a[i]]
            wgt = np.ones(len(i))
            if variant in ("is", "topk"): wgt = np.minimum(pa / b[i], cap)           # IS con capping
            if variant == "topk": wgt = wgt * K_SLATE * (1 - pa) ** (K_SLATE - 1)   # λ_K
            G = -P; G[np.arange(len(i)), a[i]] += 1                                  # ∇_logits log softmax
            W += lr * Ua[i].T @ (G * (wgt * r[i])[:, None]) / len(i)
        curve.append(topk_value(W, U_eval))
    return W, curve

g = np.random.default_rng(0); U_log, a_log, r_log, b_log = make_logs(60000 if FAST_DEV_RUN else 200000, g)
U_eval = np.random.default_rng(1).normal(0, 1, (5000, D_U))
beta_val, oracle = topk_value(W_BETA, U_eval), np.sort(q_true(U_eval), 1)[:, -K_SLATE:].sum(1).mean()
print(f"Valor top-{K_SLATE} de β (producción): {beta_val:.3f} clics/slate | óptimo (oráculo): {oracle:.3f}")
''')

    nb.code(r'''
t0 = time.time(); curves = {}
for variant, label in [("none", "REINFORCE sin corrección"), ("is", "+ importance weighting"), ("topk", "+ corrección top-K")]:
    _, curves[label] = train_reinforce(U_log, a_log, r_log, b_log, variant)
print(f"{time.time() - t0:.1f}s")
plt.figure(figsize=(9, 4.3))
for (label, c), col in zip(curves.items(), ["#9e9e9e", COLORS["ips"], COLORS["dr"]]):
    plt.plot(range(1, len(c) + 1), c, marker=".", label=label, color=col, lw=2)
plt.axhline(beta_val, ls=":", color="#c53030", label="política de logging β (top-K)")
plt.axhline(oracle, ls="--", color="k", label="óptimo (oráculo)")
plt.title(f"Off-policy REINFORCE: clics esperados por slate top-{K_SLATE} (valor REAL)")
plt.xlabel("época sobre los logs"); plt.ylabel("clics esperados / slate"); plt.legend(fontsize=8); plt.show()
print({k: round(v[-1], 3) for k, v in curves.items()})
''')

    nb.md("""
**Lectura.** Sin corrección, REINFORCE sobre logs aprende "lo que β mostraba y funcionó", heredando su sesgo de popularidad. Los *importance weights* deshacen ese sesgo; la corrección top-K ayuda a repartir la masa de probabilidad para que **los K mejores** queden arriba, en lugar de concentrarse en uno solo. En el paper, la corrección top-K aportó mejoras significativas en experimentos *live* de YouTube frente a la versión sin ella (consulta las tablas del paper para las cifras exactas).

> ⚠️ En este juguete β es **conocida**. En producción hay que estimarla, y los errores en $\\hat\\beta$ (sobre todo para ítems raros, donde $\\hat\\beta\\to 0$ y el peso explota) son la principal fuente de inestabilidad: de ahí el *capping*.

### 📐 SlateQ (Ie et al., IJCAI 2019 — Google/YouTube)

Problema: el valor de una **slate** $A$ (lista de $K$ ítems) depende de qué ítem elija el usuario, y el número de slates posibles es $\\binom{N}{K}$. SlateQ asume que (1) el usuario consume **un** ítem de la slate (o ninguno) y (2) la recompensa y la transición solo dependen del ítem consumido. Entonces el Q de la slate **se descompone** en Q's de ítems:

$$Q(s, A) = \\sum_{i\\in A} P(i\\mid s, A)\\, \\bar Q(s, i), \\qquad P(i\\mid s,A) = \\frac{v(s,i)}{v_\\varnothing(s) + \\sum_{j\\in A} v(s,j)} \\;\\;(\\text{logit condicional}),$$

donde $\\bar Q(s,i)$ es el valor a largo plazo de que el usuario consuma $i$ y se aprende con TD/Q-learning **a nivel de ítem** (tratable). Elegir la mejor slate es un problema fraccional que se resuelve con un LP, o casi igual de bien con heurísticas: **top-K por $v(s,i)\\,\\bar Q(s,i)$** o *greedy*. YouTube validó SlateQ en experimentos *live*.
""")

    nb.code(r'''
from itertools import combinations
def slate_value(A, v, Qbar, v_null):
    A = list(A); den = v_null + v[A].sum()
    return float((v[A] * Qbar[A]).sum() / den)

g = np.random.default_rng(11); N_, K_ = 14, 3; rows = []
for inst in range(200):
    v = np.exp(g.normal(0, 1, N_)); immediate = g.uniform(0.2, 1, N_)
    future = g.normal(0, 1.0, N_)                          # valor de largo plazo (puede contradecir al inmediato)
    Qbar = immediate + 0.9 * np.maximum(future + 1.5, 0); v_null = 2.0
    best = max(combinations(range(N_), K_), key=lambda A: slate_value(A, v, Qbar, v_null))
    opt = slate_value(best, v, Qbar, v_null)
    myopic = np.argsort(-(v * immediate))[:K_]                                  # maximiza recompensa inmediata
    topk = np.argsort(-(v * Qbar))[:K_]                                         # heurística SlateQ top-K
    greedy = []                                                                  # greedy: añade el que más sube Q(s,A)
    for _ in range(K_):
        cand = [i for i in range(N_) if i not in greedy]
        greedy.append(max(cand, key=lambda i: slate_value(greedy + [i], v, Qbar, v_null)))
    rows.append(dict(miope=slate_value(myopic, v, Qbar, v_null) / opt, topk=slate_value(topk, v, Qbar, v_null) / opt,
                     greedy=slate_value(greedy, v, Qbar, v_null) / opt))
sq = pd.DataFrame(rows)
plt.figure(figsize=(7.5, 3.8))
plt.bar(["Miope\n(top-K por v·r inmediata)", "SlateQ top-K\n(por v·Q̄)", "SlateQ greedy"], sq.mean(),
        yerr=sq.std(), capsize=5, color=["#c53030", COLORS["linucb"], COLORS["ucb"]])
plt.ylim(0.6, 1.02); plt.ylabel("Q(s,A) / Q(s,A*)"); plt.title(f"Valor a largo plazo de la slate vs óptimo exhaustivo ({N_} ítems, K={K_})")
plt.show(); print(sq.mean().round(3).to_dict())
''')

    nb.md("""
### Simuladores: el gimnasio del RL en recomendación

Como no puedes explorar libremente con usuarios reales, la investigación se apoya en simuladores:

| Simulador | Quién / año | Qué modela | Notas |
|---|---|---|---|
| **RecSim** | Google, Ie et al. 2019 (arXiv:1909.04847) | Usuarios con estado latente, documentos, modelo de elección, *slates* | Basado en OpenAI Gym + Dopamine; usado en SlateQ. |
| **RecSim NG** | Google, Mladenov et al. 2021 (arXiv:2103.08057) | Ecosistemas multi-agente (usuarios **y** creadores), probabilístico y diferenciable | Edward2/TensorFlow; permite inferencia y aprender parámetros del simulador. |
| **Virtual-Taobao** | Alibaba, Shi et al. AAAI 2019 | Usuarios simulados aprendidos de logs con GAN + imitación | Entrenaron políticas RL en el simulador y las desplegaron. |
| **KuaiSim** | Kuaishou + CityU, Zhao et al. NeurIPS 2023 (arXiv:2309.12645) | Respuesta inmediata, abandono de sesión y **retención entre sesiones**, entrenado con KuaiRand | Tres niveles de tarea (lista, sesión, retención) con benchmarks. |
| Simuladores con LLMs | RecAgent, Agent4Rec (2023-24) | Usuarios como agentes LLM | Ver módulo 12; útiles para *sanity checks*, no para cifras. |

> ⚠️ **El *sim-to-real gap* es el talón de Aquiles**: una política que explota un defecto del simulador (p. ej. un usuario simulado que nunca se cansa) gana en el simulador y pierde en producción. Valida siempre con OPE sobre logs reales y, al final, con un A/B.
""")

    nb.md(r"""
### Por qué el RL en recomendación es difícil

1. **Espacio de acciones gigantesco y combinatorio** (millones de ítems, slates de K): exige softmax muestreado, descomposiciones (SlateQ) o actuar en espacio de embeddings.
2. **Off-policy por obligación**: aprendes de logs de otras políticas → *importance weights* cuya varianza **crece exponencialmente con el horizonte** (producto de ratios por paso). Ver gráfico siguiente.
3. **Recompensa retardada y ruidosa**: la retención se observa semanas después; el crédito se reparte entre cientos de recomendaciones y otros factores (marketing, estrenos).
4. **Estado parcialmente observable y no estacionario**: el usuario cambia, el catálogo cambia, y el propio sistema cambia al usuario.
5. **Evaluación**: no hay "entorno" donde probar barato; OPE de largo horizonte es muy ruidosa; los A/B de retención son lentos (módulo 15).
6. **Riesgo**: una política RL puede descubrir atajos indeseados (clickbait, polarización) que ninguna métrica de corto plazo detecta.

Por eso la mayoría de los "RL en producción" publicados son **bandits contextuales o REINFORCE de un paso con corrección off-policy**, más que RL de horizonte largo de verdad.
""")

    nb.code(r'''
# Varianza del importance weight de trayectoria w_{1:H} = Π_t π(a_t|s_t)/β(a_t|s_t)
g = np.random.default_rng(0); n_traj = 20000; Hs = [1, 2, 3, 5, 8, 12, 16, 20]; K_a = 10
var_w, ess_frac = [], []
for H in Hs:
    w_traj = np.ones(n_traj)
    for t in range(H):
        logits_b = g.normal(0, 1, (n_traj, K_a)); B = softmax(logits_b)
        Pi = softmax(logits_b + g.normal(0, 0.8, (n_traj, K_a)))        # π algo distinta de β
        a_ = (B.cumsum(1) > g.random((n_traj, 1))).argmax(1)
        w_traj *= Pi[np.arange(n_traj), a_] / B[np.arange(n_traj), a_]
    var_w.append(w_traj.var()); ess_frac.append(w_traj.sum() ** 2 / (w_traj ** 2).sum() / n_traj)
fig, axes = plt.subplots(1, 2, figsize=(12, 3.8))
axes[0].semilogy(Hs, var_w, marker="o", color="#c53030", lw=2); axes[0].set(title="Var[w] de trayectoria vs horizonte", xlabel="horizonte H", ylabel="Var (log)")
axes[1].plot(Hs, np.array(ess_frac) * 100, marker="o", color="#2b6cb0", lw=2); axes[1].set(title="ESS como % de las trayectorias", xlabel="horizonte H", ylabel="ESS %")
plt.tight_layout(); plt.show()
''')

    # ------------------------------------------------------------------ 8
    nb.md("""
---
## 🏭 En producción

- **Netflix — artwork y más.** Bandits contextuales para elegir la imagen de cada título por miembro ("Artwork Personalization at Netflix", 2017), con exploración aleatorizada controlada y evaluación offline por *replay*. Netflix también ha presentado bandits para la *billboard* de la home y para elegir qué títulos promocionar (charlas de Jaya Kawale y Justin Basilico, 2018).
- **Yahoo! — LinUCB en noticias (Li et al., WWW 2010).** Portada de Yahoo! Front Page Today Module; el paper reporta un **12,5 % de mejora en clics** frente a un bandit sin contexto, evaluado con el estimador *replay* sobre tráfico aleatorizado (Li et al., WSDM 2011).
- **YouTube — REINFORCE top-K (Chen et al., WSDM 2019)** sobre millones de candidatos, entrenado off-policy desde logs, y **SlateQ (Ie et al., IJCAI 2019)** validado en experimentos live. Seguimiento: *off-policy actor-critic* (Chen et al., 2022).
- **Microsoft — Decision Service / Azure Personalizer** (Agarwal et al., 2016, "Making Contextual Decisions with Low Technical Debt"), construido sobre **Vowpal Wabbit**: logging de propensiones como requisito de diseño, OPE continua y *counterfactual* "what-if". (Azure anunció la retirada de Personalizer; el diseño del paper sigue siendo la referencia.)
- **Spotify — bandits en la home** (McInerney et al., RecSys 2018, "Explore, Exploit, and Explain"): bandit contextual que elige recomendaciones **y** su explicación, con OPE para evaluar offline.
- **ZOZOTOWN** — el Open Bandit Dataset sale de su carrusel en producción con BTS y Random en paralelo.
- **Kuaishou** — RL para optimizar **retención** en vídeo corto a escala de cientos de millones de usuarios (Cai et al., WWW 2023, "Reinforcing User Retention in a Billion Scale Short Video Recommender System").

**Latencia y escala.** Un bandit lineal cuesta un producto escalar por acción → trivial online. El cuello de botella es la **infraestructura de logging** (propensiones exactas por impresión, unión con recompensas retardadas) y el **re-entreno frecuente** (cada hora/día) sin romper el pipeline (módulos 16–17).
""")

    nb.md("""
## 🧠 Secretos de la élite

1. **Registra la propensión en el momento de servir, nunca la reconstruyas después.** Sin $\\pi_0(a\\mid x)$ exacta (incluidas reglas de negocio, deduplicación, filtros), toda la OPE es papel mojado. Diseño de Microsoft Decision Service y del OBD.
2. **Una política de logging determinista hace imposible la OPE** (soporte nulo para cualquier acción que no habría elegido). Reserva un **presupuesto de exploración** pequeño y explícito (1–5 % de tráfico, o softmax con temperatura en vez de argmax). Es exactamente lo que hizo Netflix con la "aleatorización controlada" del artwork.
3. **DR con cross-fitting por defecto, SNIPS como sanity check, y mira siempre el ESS.** Si el ESS es < 1 % de n, la cifra no vale; reporta intervalos (bootstrap) y no puntos.
4. **Calibra la OPE contra A/Bs reales.** Mantén un registro de (estimación OPE, resultado A/B) por familia de modelos; si la correlación es mala, la OPE no está lista para decidir lanzamientos. La OPE se usa para **filtrar** candidatos y decidir qué va a A/B, no para sustituirlo.
5. **Para slates/rankings, IPS por ítem-posición** (como el OBD, que evalúa por posición) o estimadores para *slates* (*pseudo-inverse*, Swaminathan et al. 2017; IIPS/RIPS en obp) — el IPS sobre la slate completa tiene varianza astronómica.
6. **La recompensa importa más que el algoritmo.** Optimizar *take rate* de artwork sin vigilar la finalización o la satisfacción posterior premia el clickbait. Netflix lo menciona explícitamente como riesgo.
7. **Thompson Sampling con *delayed feedback* y por lotes** funciona mejor que UCB: UCB es determinista y, si actualizas cada hora, envía *todo* el tráfico de esa hora al mismo brazo; TS aleatoriza de forma natural (Chapelle & Li, 2011).
8. **No estacionariedad**: usa ventanas deslizantes o *discounting* de las estadísticas; los gustos y el catálogo cambian (estrenos semanales).
""")

    nb.md("""
## ⚠️ Errores comunes

- Evaluar una política nueva con la "precisión offline" sobre logs de la política vieja (sesgo de selección) en lugar de con OPE.
- Usar IPS con propensiones **estimadas** sin calibrar, o con propensiones de una versión distinta del modelo de producción.
- Olvidar que con ε-greedy la propensión es $(1-\\varepsilon)\\,\\mathbb{1}\\{a=\\arg\\max\\} + \\varepsilon/K$, no $1$.
- Entrenar $\\hat q$ para DR con los mismos datos sobre los que se evalúa sin cross-fitting → DR hereda el sobreajuste.
- Comparar bandits sin repetir la simulación muchas veces (una sola semilla miente) o sin baseline aleatoria.
- Lanzar un bandit sin un A/B que lo compare con el sistema actual: el bandit maximiza su recompensa, no tus métricas de negocio.
- Pensar que "RL" implica horizonte largo: muchas veces un bandit contextual bien hecho captura el 90 % del valor con el 10 % del riesgo.
""")

    nb.md("""
## 📝 Autoevaluación

**1.** ¿Por qué ε-greedy con ε fijo tiene regret lineal?
<details><summary>Respuesta</summary>Porque en cada ronda, con probabilidad ε, elige un brazo al azar sin importar cuánto sepa; el coste esperado por ronda es ≥ ε·(Δ medio) > 0 para siempre, así que el regret crece como O(εT).</details>

**2.** Deriva el bonus de UCB1 a partir de Hoeffding.
<details><summary>Respuesta</summary>P(μ > μ̂ + u) ≤ exp(−2 n u²). Igualando a t⁻⁴ y despejando: u = sqrt(2 ln t / n). Se elige argmax μ̂ + u.</details>

**3.** En Thompson Beta-Bernoulli, ¿qué posterior tienes tras 3 plays y 97 no-plays con prior Beta(1,1)? ¿Y su media?
<details><summary>Respuesta</summary>Beta(4, 98); media 4/102 ≈ 3,9 %.</details>

**4.** ¿Qué condición necesita IPS para ser insesgado y qué diagnóstico te avisa de que su varianza es inaceptable?
<details><summary>Respuesta</summary>Soporte común: π₀(a|x) > 0 siempre que π_e(a|x) > 0, y propensiones correctas. El diagnóstico es el effective sample size ESS = (Σw)²/Σw² (y la distribución de w).</details>

**5.** Explica en dos frases por qué DR es "doblemente robusto".
<details><summary>Respuesta</summary>Si q̂ es correcto, el término de corrección tiene esperanza cero y DR = DM insesgado; si las propensiones son correctas, el término w·q̂(x,a) cancela en esperanza al término DM y DR = IPS insesgado. Basta con que una de las dos piezas sea correcta.</details>

**6.** ¿Qué hace el factor λ_K = K(1−π)^{K−1} de la corrección top-K de YouTube cuando π(a|s) es ya grande?
<details><summary>Respuesta</summary>Tiende a 0: el ítem ya tiene casi garantizado aparecer en la slate de K, así que el gradiente deja de empujar su probabilidad y redistribuye la masa hacia otros ítems buenos.</details>

**7.** ¿Qué supuestos permiten a SlateQ descomponer Q(s, A)?
<details><summary>Respuesta</summary>(1) El usuario consume como mucho un ítem de la slate (modelo de elección, p. ej. logit condicional) y (2) la recompensa y la transición dependen solo del ítem consumido (o de ninguno). Con eso Q(s,A) = Σ_i P(i|s,A) Q̄(s,i).</details>

**8.** Tu equipo quiere optimizar retención a 90 días con RL entrenado en un simulador. Da tres riesgos.
<details><summary>Respuesta</summary>Sim-to-real gap (la política explota defectos del simulador); varianza enorme de la OPE de largo horizonte para validar; recompensa retardada/confundida (estacionalidad, marketing) y riesgo de atajos indeseados que las métricas de corto plazo no ven. Mitigación: bandits/REINFORCE de un paso con proxies validados (surrogate index, módulo 15) y A/B final.</details>
""")

    nb.md("""
## 📚 Referencias

**Bandits**
- Auer, Cesa-Bianchi & Fischer (2002). *Finite-time Analysis of the Multiarmed Bandit Problem.* Machine Learning 47.
- Chapelle & Li (2011). *An Empirical Evaluation of Thompson Sampling.* NeurIPS.
- Li, Chu, Langford & Schapire (2010). *A Contextual-Bandit Approach to Personalized News Article Recommendation.* WWW. [arXiv:1003.0146](https://arxiv.org/abs/1003.0146)
- Li, Chu, Langford & Wang (2011). *Unbiased Offline Evaluation of Contextual-bandit-based News Article Recommendation Algorithms.* WSDM. [arXiv:1003.5956](https://arxiv.org/abs/1003.5956)
- Agrawal & Goyal (2013). *Thompson Sampling for Contextual Bandits with Linear Payoffs.* ICML. [arXiv:1209.3352](https://arxiv.org/abs/1209.3352)
- Russo, Van Roy, Kazerouni, Osband & Wen (2018). *A Tutorial on Thompson Sampling.* [arXiv:1707.02038](https://arxiv.org/abs/1707.02038)
- Riquelme, Tucker & Snoek (2018). *Deep Bayesian Bandits Showdown.* ICLR. [arXiv:1802.09127](https://arxiv.org/abs/1802.09127)
- Lattimore & Szepesvári (2020). *Bandit Algorithms.* Cambridge University Press (PDF libre en tor-lattimore.com).

**Netflix y otras empresas**
- Chandrashekar, Amat, Basilico & Jebara (2017). *Artwork Personalization at Netflix.* Netflix TechBlog. https://netflixtechblog.com/artwork-personalization-c589f074ad76
- Basilico (2018). *Artwork Personalization @ Netflix.* QCon San Francisco.
- Agarwal et al. (2016). *Making Contextual Decisions with Low Technical Debt* (Decision Service). [arXiv:1606.03966](https://arxiv.org/abs/1606.03966)
- McInerney et al. (2018). *Explore, Exploit, and Explain: Personalizing Explainable Recommendations with Bandits.* RecSys.
- Cai et al. (2023). *Reinforcing User Retention in a Billion Scale Short Video Recommender System.* WWW. [arXiv:2302.01724](https://arxiv.org/abs/2302.01724)

**Off-policy evaluation**
- Dudík, Langford & Li (2011). *Doubly Robust Policy Evaluation and Learning.* ICML. [arXiv:1103.4601](https://arxiv.org/abs/1103.4601)
- Swaminathan & Joachims (2015). *The Self-Normalized Estimator for Counterfactual Learning.* NeurIPS.
- Wang, Agarwal & Dudík (2017). *Optimal and Adaptive Off-policy Evaluation in Contextual Bandits* (Switch). ICML. [arXiv:1612.01205](https://arxiv.org/abs/1612.01205)
- Swaminathan et al. (2017). *Off-policy Evaluation for Slate Recommendation.* NeurIPS. [arXiv:1605.04812](https://arxiv.org/abs/1605.04812)
- Su, Dimakopoulou, Krishnamurthy & Dudík (2020). *Doubly Robust Off-policy Evaluation with Shrinkage.* ICML. [arXiv:1907.09623](https://arxiv.org/abs/1907.09623)
- Saito, Aihara, Matsutani & Narita (2021). *Open Bandit Dataset and Pipeline: Towards Realistic and Reproducible Off-Policy Evaluation.* NeurIPS Datasets & Benchmarks. [arXiv:2008.07146](https://arxiv.org/abs/2008.07146) · Código: https://github.com/st-tech/zr-obp · Datos: https://research.zozo.com/data.html
- Saito & Joachims (2021). *Counterfactual Learning and Evaluation for Recommender Systems* (tutorial RecSys 2021). https://sites.google.com/cornell.edu/recsys2021tutorial

**Reinforcement learning para recsys**
- Chen, Beutel, Covington, Jain, Belletti & Chi (2019). *Top-K Off-Policy Correction for a REINFORCE Recommender System.* WSDM. [arXiv:1812.02353](https://arxiv.org/abs/1812.02353)
- Ie et al. (2019). *SlateQ: A Tractable Decomposition for Reinforcement Learning with Recommendation Sets.* IJCAI. Versión extendida: [arXiv:1905.12767](https://arxiv.org/abs/1905.12767)
- Ie et al. (2019). *RecSim: A Configurable Simulation Platform for Recommender Systems.* [arXiv:1909.04847](https://arxiv.org/abs/1909.04847)
- Mladenov et al. (2021). *RecSim NG: Toward Principled Uncertainty Modeling for Recommender Ecosystems.* [arXiv:2103.08057](https://arxiv.org/abs/2103.08057)
- Shi et al. (2019). *Virtual-Taobao: Virtualizing Real-world Online Retail Environment for Reinforcement Learning.* AAAI. [arXiv:1805.10000](https://arxiv.org/abs/1805.10000)
- Zhao et al. (2023). *KuaiSim: A Comprehensive Simulator for Recommender Systems.* NeurIPS Datasets & Benchmarks. [arXiv:2309.12645](https://arxiv.org/abs/2309.12645)
- Afsar, Crump & Far (2022). *Reinforcement Learning based Recommender Systems: A Survey.* ACM Computing Surveys. [arXiv:2101.06286](https://arxiv.org/abs/2101.06286)

**Librerías**: [obp](https://github.com/st-tech/zr-obp) · [Vowpal Wabbit](https://vowpalwabbit.org) · [RecSim](https://github.com/google-research/recsim) · [KuaiSim](https://github.com/Applied-Machine-Learning-Lab/KuaiSim) · [scikit-learn](https://scikit-learn.org)
""")

    nb.save(LESSON)


# =============================================================================
# PROYECTO
# =============================================================================
def build_project() -> None:
    nb = Notebook("Proyecto 14 · Bandit contextual de artwork para CineMatch", colab_path=PROJECT)

    nb.md(f"""
{nb.badge()}

# Proyecto 14 · Bandit contextual de *artwork* para CineMatch, evaluado off-policy

**Nivel:** 🟠 Avanzado / 🔴 Experto · **Duración:** 3–4 h · **Hardware:** CPU (sin GPU) · **Unidades de Colab:** < 1
**Prerrequisitos:** lección 14 (bandits, OPE). Conecta con el módulo 15 (el A/B que vendrá después) y 16 (serving).
""")

    nb.md("""
## 🎬 Contexto de negocio

Eres ML engineer en el equipo de **Personalización Visual de CineMatch**. Hoy cada título tiene 4 imágenes candidatas (*artwork*) y producción elige una con un modelo antiguo **no personalizado**: un softmax sobre la tasa de *play* histórica de cada imagen, más un 10 % de exploración uniforme. Producción **registra la propensión** de cada impresión (¡bien hecho, equipo de plataforma!).

La directora de producto quiere lanzar un **bandit contextual personalizado**. Antes de gastar tráfico en un A/B (módulo 15), te pide un **dossier de off-policy evaluation**:

1. Demostrar que vuestros estimadores OPE son correctos sobre **datos reales** con propensiones reales: el **Open Bandit Dataset** de ZOZOTOWN (benchmark Random → BTS).
2. Comparar **online en el simulador** de CineMatch varias políticas de exploración (regret).
3. Aprender políticas personalizadas **offline** a partir de los logs de producción y estimar su valor con DM / IPS / SNIPS / DR / Switch-DR, con intervalos de confianza y diagnóstico de ESS.
4. Recomendar **qué política va al A/B** y por qué.

> 💡 El simulador de CineMatch tiene **verdad oculta** (sabemos la probabilidad real de *play*), así que podemos comprobar qué estimador acierta. En la vida real no la tendrías: por eso se calibra la OPE contra A/Bs.
""")

    nb.md("""
## 📦 Datos

| Dataset | Origen | Uso |
|---|---|---|
| **Open Bandit Dataset** (muestra de 10.000 impresiones por política, incluida en `obp`) | ZOZOTOWN, Saito et al. 2021 (arXiv:2008.07146). Versión completa (~26 M filas): [research.zozo.com/data.html](https://research.zozo.com/data.html), CC BY 4.0 | Validar estimadores con propensiones reales (Random y Bernoulli TS en paralelo) |
| **Simulador de artwork de CineMatch** | Sintético, mismo `ArtworkWorld` de la lección | Políticas online/offline con valor real conocido |

`SCALE = "small"` usa la muestra incluida en `obp`. `SCALE = "full"` usa el OBD completo: descárgalo de la página oficial, descomprímelo en `./open_bandit_dataset/` (o en Drive) y ajusta `OBD_PATH`. Si la ruta no existe, el notebook vuelve automáticamente a la muestra.

## ✅ Entregables y rúbrica

| # | Entregable | Criterio de aceptación |
|---|---|---|
| E1 | `estimate_policy_value` (DM, IPS, SNIPS, DR, Switch-DR, ESS) | Coincide con `obp` en OBD con diferencia absoluta < 1e-8 |
| E2 | Benchmark OBD Random→BTS con IC 95 % bootstrap | Tabla con error relativo vs valor on-policy e IC; discusión de la anchura del IC |
| E3 | Simulación online: producción vs LinUCB vs Thompson lineal | Regret acumulado de **algún** bandit lineal ≤ 25 % del de producción a T=20.000 |
| E4 | Políticas offline (global, personalizada greedy, personalizada softmax) | La mejor tiene **valor real** ≥ +50 % sobre producción |
| E5 | Dossier OPE | Para cada política: 5 estimadores + IC 95 % de DR + ESS. **Error relativo de DR ≤ 5 %** y el IC de DR **cubre** el valor real |
| E6 | Recomendación | Política elegida, riesgos (soporte, ESS, clickbait) y plan de A/B en 5–8 líneas |
""")

    nb.code(PIP_OBP)
    nb.code(r'''
import warnings, time, logging
from dataclasses import dataclass
from pathlib import Path
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
warnings.filterwarnings("ignore"); logging.getLogger("obp").setLevel(logging.WARNING)
seed = 42; rng = np.random.default_rng(seed)
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3})

SCALE = "small"                          # "small" (muestra incluida en obp) | "full" (OBD completo)
OBD_PATH = Path("open_bandit_dataset")   # carpeta descomprimida del OBD completo (solo SCALE="full")
T_ONLINE = 20_000                        # impresiones de la simulación online
N_LOGS_TRAIN, N_LOGS_TEST = 50_000, 25_000

def softmax(z, temp=1.0, axis=-1):
    z = z / temp; z = z - z.max(axis=axis, keepdims=True); e = np.exp(z)
    return e / e.sum(axis=axis, keepdims=True)

def todo_guard(fn, *args, **kw):
    """Ejecuta fn y, si aún es un TODO, avisa sin romper la ejecución del notebook."""
    try:
        return fn(*args, **kw)
    except NotImplementedError:
        print(f"⏳ {fn.__name__}: TODO pendiente (la solución de referencia está al final)")
        return None
''')

    nb.md("### El simulador de artwork de CineMatch (idéntico a la lección)")
    nb.code(ARTWORK_ENV)

    # ---------------------------------------------------------- Parte 1
    nb.md("""
---
## Parte 1 · Validar los estimadores sobre datos reales (Open Bandit Dataset)

Formato de obp (el que usarás también en el simulador):
- `action_dist`: array `(n, K, L)` con $\\pi_e(a\\mid x_i, \\text{posición } \\ell)$; en el simulador $L=1$.
- `q_hat`: array `(n, K, L)` con $\\hat q(x_i, a, \\ell)$.
- `position`: posición de cada impresión (ceros si $L=1$).
""")

    nb.code(r'''
from obp.dataset import OpenBanditDataset

def load_obd(behavior_policy: str):
    if SCALE == "full" and OBD_PATH.exists():
        return OpenBanditDataset(behavior_policy=behavior_policy, campaign="all", data_path=OBD_PATH)
    if SCALE == "full":
        print(f"⚠️ {OBD_PATH} no existe: uso la muestra pequeña incluida en obp.")
    return OpenBanditDataset(behavior_policy=behavior_policy, campaign="all")

ds_random, ds_bts = load_obd("random"), load_obd("bts")
bf_random = ds_random.obtain_batch_bandit_feedback()
V_BTS_ON_POLICY = OpenBanditDataset.calc_on_policy_policy_value_estimate(
    behavior_policy="bts", campaign="all", data_path=OBD_PATH if (SCALE == "full" and OBD_PATH.exists()) else None)
print(f"Random: n={bf_random['n_rounds']:,}, clics={int(bf_random['reward'].sum())}, K={ds_random.n_actions}, L={ds_random.len_list}")
print(f"Valor on-policy de BTS (verdad del benchmark): {V_BTS_ON_POLICY:.5f}")
''')

    nb.md("""
### TODO 1 · Implementa los estimadores

Implementa `estimate_policy_value` siguiendo las fórmulas de la lección, **por posición** (como obp):
- $w_i = \\pi_e(a_i\\mid x_i,\\ell_i) / p_i$
- DM: $\\frac1n\\sum_i\\sum_a \\pi_e(a\\mid x_i,\\ell_i)\\,\\hat q(x_i,a,\\ell_i)$
- IPS, SNIPS, DR como en la lección; Switch-DR: término de corrección solo si $w_i \\le \\tau$.
- ESS $= (\\sum w)^2/\\sum w^2$.

Pista: indexa con `idx = np.arange(n)` y `action_dist[idx, :, position]` → `(n, K)`.
""")

    nb.code(r'''
def estimate_policy_value(reward, action, pscore, action_dist, q_hat, position=None, tau=50.0) -> dict:
    """Devuelve {'dm','ipw','snipw','dr','switch-dr','ess'} para la política action_dist."""
    # TODO: implementa los cinco estimadores y el ESS
    raise NotImplementedError

def per_round_dr(reward, action, pscore, action_dist, q_hat, position=None) -> np.ndarray:
    """Contribución de cada ronda al estimador DR (útil para el bootstrap)."""
    # TODO
    raise NotImplementedError
''')

    nb.code(r'''
# Política a evaluar: Bernoulli TS de producción de ZOZOTOWN y modelo de recompensa con cross-fitting
from obp.policy import BernoulliTS
from obp.ope import (OffPolicyEvaluation, RegressionModel, DirectMethod, InverseProbabilityWeighting,
                     SelfNormalizedInverseProbabilityWeighting, DoublyRobust, SwitchDoublyRobust)
bts = BernoulliTS(n_actions=ds_random.n_actions, len_list=ds_random.len_list, is_zozotown_prior=True,
                  campaign="all", random_state=seed)
ad_bts = bts.compute_batch_action_dist(n_sim=100_000, n_rounds=bf_random["n_rounds"])
reg = RegressionModel(n_actions=ds_random.n_actions, len_list=ds_random.len_list, action_context=ds_random.action_context,
                      base_model=LogisticRegression(C=100, max_iter=1000, random_state=seed))
qhat_obd = reg.fit_predict(context=bf_random["context"], action=bf_random["action"], reward=bf_random["reward"],
                           position=bf_random["position"], pscore=bf_random["pscore"], n_folds=3, random_state=seed)
ope_obp = OffPolicyEvaluation(bandit_feedback=bf_random, ope_estimators=[
    DirectMethod(), InverseProbabilityWeighting(), SelfNormalizedInverseProbabilityWeighting(),
    DoublyRobust(), SwitchDoublyRobust(lambda_=50.0)])
obp_point = ope_obp.estimate_policy_values(action_dist=ad_bts, estimated_rewards_by_reg_model=qhat_obd)
print({k: round(v, 6) for k, v in obp_point.items()})
''')

    nb.code(r'''
def check_E1():
    mine = estimate_policy_value(bf_random["reward"], bf_random["action"], bf_random["pscore"], ad_bts, qhat_obd,
                                 position=bf_random["position"], tau=50.0)
    diffs = {k: abs(mine[k] - obp_point[k]) for k in obp_point}
    print("Diferencias con obp:", {k: f"{v:.1e}" for k, v in diffs.items()})
    print("E1 ✅" if max(diffs.values()) < 1e-8 else "E1 ❌")
    return mine
_ = todo_guard(check_E1)
''')

    nb.md("""
### TODO 2 · Bootstrap y benchmark Random → BTS

Implementa `bootstrap_ci(values, n_boot, alpha)` (percentil, remuestreo de rondas) y construye la tabla del benchmark: estimación, IC 95 % (para DR), error relativo $|\\hat V - V_{\\text{on}}| / V_{\\text{on}}$.
""")

    nb.code(r'''
def bootstrap_ci(values: np.ndarray, n_boot: int = 1000, alpha: float = 0.05, seed: int = 0) -> tuple:
    """IC percentil de la media de `values` remuestreando filas con reemplazo."""
    # TODO
    raise NotImplementedError

def obd_benchmark() -> pd.DataFrame:
    # TODO: usa estimate_policy_value, per_round_dr y bootstrap_ci; devuelve un DataFrame por estimador
    raise NotImplementedError
_ = todo_guard(obd_benchmark)
''')

    # ---------------------------------------------------------- Parte 2
    nb.md("""
---
## Parte 2 · El mundo CineMatch: política de producción y logs

La política de producción $\\pi_0$ ignora al usuario: softmax (temperatura 0,3) sobre una estimación ruidosa de la calidad global de cada imagen, mezclada con un 10 % de exploración uniforme. **Esta celda está completa**: es la "realidad" que te da el equipo de plataforma.
""")

    nb.code(r'''
world = ArtworkWorld(seed=2024)
K = world.n_art
_g = np.random.default_rng(0)
OLD_SCORE = world.title_bias[:, None] + world.art_quality + _g.normal(0, 0.3, (world.n_titles, K))
EPS_PROD = 0.10

def pi_production(X, t):
    """π0(a|x): (n,K). No usa X (no personaliza)."""
    return (1 - EPS_PROD) * softmax(OLD_SCORE[t], temp=0.3) + EPS_PROD / K

def generate_logs(n, g):
    X, seg = world.sample_users(n, g); t = g.integers(0, world.n_titles, n)
    P0 = pi_production(X, t); a = (P0.cumsum(1) > g.random((n, 1))).argmax(1)
    p = world.p_play(X, t)                                       # verdad oculta (solo para evaluar)
    r = (g.random(n) < p[np.arange(n), a]).astype(float)
    return dict(X=X, seg=seg, t=t, a=a, r=r, pscore=P0[np.arange(n), a], P0=P0, p_true=p)

g_logs = np.random.default_rng(1)
logs_train, logs_test = generate_logs(N_LOGS_TRAIN, g_logs), generate_logs(N_LOGS_TEST, g_logs)
true_value = lambda pi, logs: float((pi * logs["p_true"]).sum(1).mean())   # oráculo del simulador
V0 = true_value(logs_test["P0"], logs_test)
print(f"Take rate de producción (real): {V0:.4f} | observado en logs: {logs_test['r'].mean():.4f}")
print(f"Propensión mínima registrada: {logs_train['pscore'].min():.3f}  (⇒ w máximo ≤ {1/logs_train['pscore'].min():.0f})")
''')

    # ---------------------------------------------------------- Parte 3
    nb.md("""
---
## Parte 3 · Simulación online: ¿cuánto gana explorar con contexto?

### TODO 3 · Bandits lineales online
Implementa `LinearBandit` (LinUCB y Thompson lineal con Sherman–Morrison) y `simulate_online(policy_name, T)` que devuelva el **regret instantáneo** de cada impresión. Usa `world.features(x, t)` como $x_{t,a}$ (dimensión 28). Políticas: `"production"` (muestrea de $\\pi_0$), `"linucb"`, `"lints"`.
""")

    nb.code(r'''
class LinearBandit:
    def __init__(self, d, mode="ucb", alpha=0.5, v=0.3, lam=1.0, rng=None):
        # TODO: guarda A^{-1} (identidad/λ) y b (ceros)
        raise NotImplementedError
    def select(self, Xa):
        # TODO: LinUCB → argmax θ̂ᵀx + α·sqrt(xᵀA⁻¹x);  TS → muestrea θ̃ ~ N(θ̂, v²A⁻¹)
        raise NotImplementedError
    def update(self, x, r):
        # TODO: Sherman–Morrison sobre A^{-1} y b += r x
        raise NotImplementedError

def simulate_online(policy_name: str, T: int, seed: int = 0) -> np.ndarray:
    # TODO: bucle de T impresiones; devuelve regret instantáneo p_max - p[a]
    raise NotImplementedError

online = {name: todo_guard(simulate_online, name, T_ONLINE) for name in ["production", "linucb", "lints"]}
''')

    # ---------------------------------------------------------- Parte 4
    nb.md("""
---
## Parte 4 · Aprender políticas offline a partir de los logs

### TODO 4 · Tres políticas candidatas (todas devuelven `(n, K)` probabilidades)
1. `pi_global`: para cada título, la imagen con mayor valor IPS estimado en `logs_train` (determinista, no personaliza).
2. `pi_personal_greedy`: regresión logística sobre `world.features` de la acción mostrada → argmax.
3. `pi_personal_soft`: mismo modelo, `0.95·softmax(score/0.2) + 0.05/K` (estocástica: mejor soporte para OPE y para seguir explorando).

Pista: las features de la acción logueada son `world.features(X, t)[np.arange(n), a]`.
""")

    nb.code(r'''
def fit_reward_model(logs) -> LogisticRegression:
    # TODO
    raise NotImplementedError

def make_policies(logs_train, logs_eval) -> dict:
    """Devuelve {'global': (n,K), 'personal_greedy': (n,K), 'personal_soft': (n,K)} sobre logs_eval."""
    # TODO
    raise NotImplementedError

policies = todo_guard(make_policies, logs_train, logs_test)
''')

    # ---------------------------------------------------------- Parte 5
    nb.md("""
---
## Parte 5 · Dossier OPE

### TODO 5 · Estima el valor de cada política en `logs_test`
- Modelo $\\hat q$ con **cross-fitting** (2 folds) sobre `logs_test`.
- Para cada política (incluida producción como *sanity check*): DM, IPS, SNIPS, DR, Switch-DR(τ=20), ESS, IC 95 % de DR (bootstrap) y el **valor real** (oráculo) para calificar.
- Comprueba E4 y E5 y dibuja un gráfico de estimaciones con IC vs valor real.
""")

    nb.code(r'''
def crossfit_qhat(logs, n_folds=2, seed=0) -> np.ndarray:
    """q̂(x_i, a) para todas las acciones, (n, K), entrenado fuera del fold de cada fila."""
    # TODO
    raise NotImplementedError

def ope_dossier(logs, policies) -> pd.DataFrame:
    # TODO
    raise NotImplementedError

dossier = todo_guard(ope_dossier, logs_test, policies) if policies is not None else None
''')

    nb.md("""
### TODO 6 · Recomendación (escribe en esta celda)

*¿Qué política mandas al A/B? ¿Con qué exploración residual? ¿Qué guardrails vigilarías (finalización, tiempo hasta play, quejas de clickbait)? ¿Qué harías si el ESS fuese < 1 % de n?*
""")

    # ---------------------------------------------------------- SOLUCIÓN
    nb.md("""
---
# ⛔ SPOILER — intenta resolverlo primero

A partir de aquí está la **solución de referencia** completa. Redefine las funciones de los TODOs y ejecuta todo el pipeline con los criterios de la rúbrica.
""")

    nb.md("### Solución · Parte 1 (E1, E2)")
    nb.code(r'''
def estimate_policy_value(reward, action, pscore, action_dist, q_hat, position=None, tau=50.0) -> dict:
    n = len(reward); idx = np.arange(n)
    pos = np.zeros(n, dtype=int) if position is None else position
    pi_obs = action_dist[idx, action, pos]
    w = pi_obs / pscore
    pi_all, q_all = action_dist[idx, :, pos], q_hat[idx, :, pos]          # (n, K)
    dm_i = (pi_all * q_all).sum(1)
    resid = reward - q_all[idx, action]
    return {"dm": dm_i.mean(), "ipw": (w * reward).mean(), "snipw": (w * reward).sum() / w.sum(),
            "dr": (dm_i + w * resid).mean(), "switch-dr": (dm_i + (w <= tau) * w * resid).mean(),
            "ess": w.sum() ** 2 / (w ** 2).sum()}

def per_round_dr(reward, action, pscore, action_dist, q_hat, position=None) -> np.ndarray:
    n = len(reward); idx = np.arange(n)
    pos = np.zeros(n, dtype=int) if position is None else position
    w = action_dist[idx, action, pos] / pscore
    q_all = q_hat[idx, :, pos]
    return (action_dist[idx, :, pos] * q_all).sum(1) + w * (reward - q_all[idx, action])

def bootstrap_ci(values, n_boot=1000, alpha=0.05, seed=0):
    g = np.random.default_rng(seed); n = len(values)
    means = np.array([values[g.integers(0, n, n)].mean() for _ in range(n_boot)])
    return float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))

mine_obd = check_E1()
''')

    nb.code(r'''
def obd_benchmark() -> pd.DataFrame:
    b = bf_random
    est = estimate_policy_value(b["reward"], b["action"], b["pscore"], ad_bts, qhat_obd, b["position"], tau=50.0)
    lo, hi = bootstrap_ci(per_round_dr(b["reward"], b["action"], b["pscore"], ad_bts, qhat_obd, b["position"]))
    rows = [dict(estimador=k, estimación=v, error_relativo=abs(v - V_BTS_ON_POLICY) / V_BTS_ON_POLICY)
            for k, v in est.items() if k != "ess"]
    df = pd.DataFrame(rows).set_index("estimador")
    print(f"IC 95 % de DR: [{lo:.5f}, {hi:.5f}]  (anchura relativa {(hi - lo) / V_BTS_ON_POLICY:.0%})"
          f" | verdad on-policy {V_BTS_ON_POLICY:.5f} | ESS={est['ess']:.0f}")
    return df

display(obd_benchmark().round(5))
print("""Lectura: con la muestra de 10k filas (~40 clics) el IC de DR abarca un rango enorme; las
estimaciones puntuales son orientativas. Con SCALE='full' (1,4 M filas en Random/all) el IC se estrecha
~12× (√(n_full/n_small)). DM sale estrecho pero sesgado: refleja la incertidumbre de un modelo, no la causal.""")
''')

    nb.md("### Solución · Parte 3 (E3)")
    nb.code(r'''
class LinearBandit:
    def __init__(self, d, mode="ucb", alpha=0.5, v=0.3, lam=1.0, rng=None):
        self.mode, self.alpha, self.v = mode, alpha, v
        self.A_inv, self.b = np.eye(d) / lam, np.zeros(d)
        self.rng = rng or np.random.default_rng(0)
    def select(self, Xa):
        theta = self.A_inv @ self.b
        if self.mode == "ucb":
            bonus = np.sqrt(np.einsum("kd,de,ke->k", Xa, self.A_inv, Xa))
            return int(np.argmax(Xa @ theta + self.alpha * bonus))
        L = np.linalg.cholesky(self.v ** 2 * self.A_inv + 1e-10 * np.eye(len(self.b)))
        return int(np.argmax(Xa @ (theta + L @ self.rng.standard_normal(len(self.b)))))
    def update(self, x, r):
        Ax = self.A_inv @ x
        self.A_inv -= np.outer(Ax, Ax) / (1.0 + x @ Ax)
        self.b += r * x

def simulate_online(policy_name: str, T: int, seed: int = 0) -> np.ndarray:
    g = np.random.default_rng(seed)
    X, _ = world.sample_users(T, g); titles = g.integers(0, world.n_titles, T)
    d = world.d_user * 4 + 4
    bandit = None if policy_name == "production" else LinearBandit(d, mode="ucb" if policy_name == "linucb" else "ts", rng=g)
    regret = np.empty(T)
    for t in range(T):
        x, ti = X[t:t + 1], titles[t:t + 1]
        p = world.p_play(x, ti)[0]
        if bandit is None:
            a = int((pi_production(x, ti)[0].cumsum() > g.random()).argmax())
        else:
            Xa = world.features(x, ti)[0]; a = bandit.select(Xa)
            bandit.update(Xa[a], float(g.random() < p[a]))
        regret[t] = p.max() - p[a]
    return regret

t0 = time.time()
online = {name: simulate_online(name, T_ONLINE) for name in ["production", "linucb", "lints"]}
print(f"{time.time() - t0:.1f}s")
plt.figure(figsize=(8, 4))
for name, c in zip(online, ["#9e9e9e", "#009e73", "#cc79a7"]):
    plt.plot(np.cumsum(online[name]), label=name, color=c, lw=2)
plt.title("Regret acumulado online en CineMatch"); plt.xlabel("impresión"); plt.ylabel("plays perdidos esperados")
plt.legend(); plt.show()
ratio = min(online["linucb"].sum(), online["lints"].sum()) / online["production"].sum()
print(f"Regret mejor bandit / producción = {ratio:.2f}  →  E3 {'✅' if ratio <= 0.25 else '❌'}")
''')

    nb.md("### Solución · Parte 4 (E4)")
    nb.code(r'''
def logged_features(logs):
    F = world.features(logs["X"], logs["t"])
    return F, F[np.arange(len(logs["a"])), logs["a"]]

def fit_reward_model(logs) -> LogisticRegression:
    _, Fa = logged_features(logs)
    return LogisticRegression(C=1.0, max_iter=3000).fit(Fa, logs["r"])

def make_policies(logs_train, logs_eval) -> dict:
    n = len(logs_eval["a"])
    # 1) Global por título con valor IPS por (título, imagen)
    df = pd.DataFrame(dict(t=logs_train["t"], a=logs_train["a"], rw=logs_train["r"] / logs_train["pscore"]))
    ips_ta = (df.groupby(["t", "a"]).rw.sum().unstack().reindex(columns=range(K)).fillna(0)
              / df.groupby("t").size().values[:, None])
    best = ips_ta.values.argmax(1)
    pi_global = np.eye(K)[best[logs_eval["t"]]]
    # 2) y 3) Personalizadas
    clf = fit_reward_model(logs_train)
    F, _ = logged_features(logs_eval)
    S = clf.decision_function(F.reshape(-1, F.shape[-1])).reshape(n, K)
    return {"global": pi_global, "personal_greedy": np.eye(K)[S.argmax(1)],
            "personal_soft": 0.95 * softmax(S, temp=0.2) + 0.05 / K}

policies = make_policies(logs_train, logs_test)
vals = {k: true_value(v, logs_test) for k, v in policies.items()}
print({k: round(v, 4) for k, v in vals.items()}, "| producción:", round(V0, 4))
best_lift = max(vals.values()) / V0 - 1
print(f"Mejor lift real vs producción: {best_lift:+.0%}  →  E4 {'✅' if best_lift >= 0.5 else '❌'}")
''')

    nb.md("### Solución · Parte 5 (E5)")
    nb.code(r'''
def crossfit_qhat(logs, n_folds=2, seed=0) -> np.ndarray:
    n = len(logs["a"]); folds = np.random.default_rng(seed).integers(0, n_folds, n)
    F, Fa = logged_features(logs); out = np.zeros((n, K))
    for f in range(n_folds):
        tr_ = folds != f
        clf = LogisticRegression(C=1.0, max_iter=3000).fit(Fa[tr_], logs["r"][tr_])
        out[~tr_] = clf.predict_proba(F[~tr_].reshape(-1, F.shape[-1]))[:, 1].reshape(-1, K)
    return out

def ope_dossier(logs, policies) -> pd.DataFrame:
    qh = crossfit_qhat(logs)[:, :, None]
    rows = []
    for name, pi in {"production": logs["P0"], **policies}.items():
        ad = pi[:, :, None]
        est = estimate_policy_value(logs["r"], logs["a"], logs["pscore"], ad, qh, tau=20.0)
        lo, hi = bootstrap_ci(per_round_dr(logs["r"], logs["a"], logs["pscore"], ad, qh), n_boot=500)
        v = true_value(pi, logs)
        rows.append(dict(política=name, real=v, **{k: est[k] for k in ["dm", "ipw", "snipw", "dr", "switch-dr"]},
                         dr_lo=lo, dr_hi=hi, ess=est["ess"], err_rel_dr=abs(est["dr"] - v) / v,
                         cubre=lo <= v <= hi))
    return pd.DataFrame(rows).set_index("política")

dossier = ope_dossier(logs_test, policies)
display(dossier.round(4))
ok = (dossier.err_rel_dr <= 0.05).all() and dossier.cubre.all()
print("E5", "✅" if ok else "❌ (revisa: ¿algún IC no cubre? Mira el ESS)")
''')

    nb.code(r'''
fig, ax = plt.subplots(figsize=(10, 4.2))
names = dossier.index.tolist(); x = np.arange(len(names)); offs = np.linspace(-0.3, 0.3, 5)
for o, est, c in zip(offs, ["dm", "ipw", "snipw", "dr", "switch-dr"], ["#56b4e9", "#e69f00", "#c9b200", "#009e73", "#cc79a7"]):
    ax.scatter(x + o, dossier[est], color=c, label=est, zorder=3)
ax.errorbar(x + offs[3], dossier.dr, yerr=[dossier.dr - dossier.dr_lo, dossier.dr_hi - dossier.dr],
            fmt="none", ecolor="#009e73", capsize=4)
ax.scatter(x, dossier.real, marker="_", s=900, color="k", label="valor real (oráculo)", zorder=4)
ax.set_xticks(x, names); ax.set(title="Dossier OPE: estimaciones vs valor real (IC 95 % de DR)", ylabel="take rate")
ax.legend(ncol=3, fontsize=8); plt.tight_layout(); plt.show()
''')

    nb.md("""
### Solución · Recomendación (E6, ejemplo)

> **Recomendación:** llevar `personal_soft` a un A/B 50/50 contra producción. Aunque `personal_greedy` tiene un valor estimado algo mayor, la versión softmax (i) mantiene un 5 % de exploración y propensiones > 0 para todas las imágenes, lo que permite seguir haciendo OPE y re-entrenar sin sesgo; (ii) tiene un ESS mayor, así que su estimación es más fiable; (iii) reduce el riesgo de que el modelo "se case" con una imagen. Guardrails del A/B: tasa de finalización / minutos tras el play (anti-clickbait), tiempo hasta el primer play, abandono de la ficha. Si el ESS fuese < 1 % de n, no decidiríamos con OPE: subiríamos la exploración de producción unas semanas o evaluaríamos solo en el subconjunto de tráfico explorado.
""")

    nb.md("""
---
## 🚀 Retos extra (nivel experto)

1. **OBD completo** (`SCALE="full"`): repite el benchmark Random→BTS por campaña (*all/men/women*) y compara tu error relativo con la tabla del paper de Saito et al.
2. **Estimadores avanzados en obp:** `DoublyRobustWithShrinkage` (DRos), `SelfNormalizedDoublyRobust` y selección automática de τ (`obp.ope` incluye utilidades de *hyperparameter tuning*). ¿Ganan a tu Switch-DR?
3. **Off-policy learning:** entrena `obp.policy.IPWLearner` o un *neural-linear bandit* en PyTorch (GPU) y compáralo con tu `personal_soft` por DR.
4. **Recompensa anti-clickbait:** modifica `ArtworkWorld` para que algunas imágenes suban el *play* pero bajen la finalización; redefine la recompensa como "play con ≥ 70 % visto" y observa cómo cambia la política elegida.
5. **No estacionariedad:** haz que los gustos cambien a mitad de la simulación online y compara LinUCB con ventana deslizante vs sin ventana.

## 🤔 Reflexión (conexión con producción / MLOps)

- ¿Dónde se registra la propensión en vuestra arquitectura (servicio de decisión, Kafka, feature store)? ¿Qué pasa si una regla de negocio filtra una imagen *después* de la política?
- ¿Cómo versionarías juntos política, modelo de recompensa y datasets de OPE en MLflow para que el dossier sea reproducible?
- ¿Con qué frecuencia re-entrenarías el bandit y cómo monitorizarías el ESS y la deriva de propensiones (módulo 17)?
- ¿Qué métrica del A/B del módulo 15 usarías como *north star* para el artwork y cuáles como guardrails?
""")

    nb.save(PROJECT)


if __name__ == "__main__":
    build_lesson()
    build_project()
