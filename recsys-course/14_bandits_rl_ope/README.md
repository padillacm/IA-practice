# Módulo 14 · Bandits, Reinforcement Learning y Off-Policy Evaluation

**Nivel:** 🟠 Avanzado → 🔴 Experto · **Duración:** 5–6 h (lección) + 3–4 h (proyecto) · **Hardware:** CPU de Colab (sin GPU), < 1 unidad

Hasta ahora hemos tratado la recomendación como aprendizaje supervisado sobre logs. Pero los logs los genera tu propio sistema: solo ves la reacción a lo que mostraste (*bandit feedback*). Este módulo enseña a **decidir qué mostrar explorando de forma controlada** (bandits), a **evaluar políticas nuevas sin desplegarlas** (*off-policy evaluation*, OPE) y a optimizar **valor a largo plazo** (RL), con los casos reales de Netflix, Yahoo!, YouTube y ZOZOTOWN.

| Notebook | Contenido |
|---|---|
| [`14_bandits_rl_ope.ipynb`](14_bandits_rl_ope.ipynb) | Lección: ε-greedy, UCB1, Thompson Sampling, LinUCB, Thompson lineal (desde cero, con regret); personalización de *artwork* de Netflix y estimador *replay*; DM, IPS, SNIPS, DR y Switch-DR desde cero con estudio Monte Carlo de sesgo/varianza; Open Bandit Pipeline sobre el Open Bandit Dataset; MDP, Q-learning, REINFORCE con corrección top-K off-policy (YouTube), SlateQ, simuladores (RecSim, RecSim NG, KuaiSim) y por qué el RL en recsys es difícil. |
| [`14_proyecto_artwork_bandit_ope.ipynb`](14_proyecto_artwork_bandit_ope.ipynb) | Proyecto: bandit contextual de *artwork* para **CineMatch** + dossier OPE. Validar estimadores contra `obp` en el OBD real (benchmark Random → BTS), simulación online LinUCB/Thompson lineal, políticas aprendidas offline y estimación de su valor con intervalos y ESS. Plantilla con TODOs y solución de referencia. |

## 🎯 Objetivos

1. Formalizar recomendación como MAB, bandit contextual y MDP; definir regret.
2. Implementar desde cero ε-greedy, UCB1, Thompson (Beta-Bernoulli), LinUCB y Thompson lineal y comparar su regret acumulado.
3. Explicar la personalización de artwork de Netflix y su evaluación offline por *replay*.
4. Derivar e implementar DM, IPS, SNIPS, DR y Switch-DR; medir sesgo, varianza, MSE y ESS.
5. Usar Open Bandit Pipeline sobre el Open Bandit Dataset.
6. Implementar REINFORCE con corrección top-K off-policy y explicar SlateQ.
7. Argumentar cuándo NO usar RL en recomendación.

## 📦 Datos

- **Open Bandit Dataset** (ZOZOTOWN; Saito et al., NeurIPS 2021 D&B, [arXiv:2008.07146](https://arxiv.org/abs/2008.07146)). La muestra de 10.000 filas por política viene **incluida en el paquete `obp`**, así que no hay que descargar nada. La versión completa (~26 M filas, CC BY 4.0) está en [research.zozo.com/data.html](https://research.zozo.com/data.html); el proyecto la usa con `SCALE="full"` y `OBD_PATH`.
- **Simulador de artwork de CineMatch** (`ArtworkWorld`, sintético, con la probabilidad real de *play* conocida) y mundos sintéticos para el estudio de estimadores y RL.

## ⚙️ Nota de instalación: `obp`

`obp` 0.5.7 (la última versión) declara `python<3.11` y fija versiones antiguas (torch 1.12, sklearn 1.1…), por lo que `pip install obp` falla en el Colab actual (Python 3.12). El código funciona con las librerías modernas que ya trae Colab, así que los notebooks lo instalan así:

```bash
pip install -q --no-deps --ignore-requires-python obp==0.5.7
```

## 🔗 Conexión con CineMatch

El proyecto sustituye el selector de imágenes de producción, que no personaliza, por un bandit contextual, y prepara el dossier OPE que justifica el A/B del **módulo 15**. El logging de propensiones y el re-entreno del bandit se integran en el serving (**16**) y el monitoreo (**17**).

## 📚 Lecturas esenciales

- Chandrashekar, Amat, Basilico & Jebara (2017). *Artwork Personalization at Netflix.* Netflix TechBlog.
- Li, Chu, Langford & Schapire (2010). *A Contextual-Bandit Approach to Personalized News Article Recommendation.* WWW. [arXiv:1003.0146](https://arxiv.org/abs/1003.0146)
- Dudík, Langford & Li (2011). *Doubly Robust Policy Evaluation and Learning.* ICML. [arXiv:1103.4601](https://arxiv.org/abs/1103.4601)
- Saito et al. (2021). *Open Bandit Dataset and Pipeline.* [arXiv:2008.07146](https://arxiv.org/abs/2008.07146) · [zr-obp](https://github.com/st-tech/zr-obp)
- Chen et al. (2019). *Top-K Off-Policy Correction for a REINFORCE Recommender System.* WSDM. [arXiv:1812.02353](https://arxiv.org/abs/1812.02353)
- Ie et al. (2019). *SlateQ.* IJCAI · [arXiv:1905.12767](https://arxiv.org/abs/1905.12767)
- Lattimore & Szepesvári (2020). *Bandit Algorithms.* Cambridge University Press.

Prerrequisitos: módulos 01, 02, 06, 07 y 13. Siguiente: **15 · Experimentación online**.
