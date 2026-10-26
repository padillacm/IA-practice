"""Lección 17 · parte 2: superposición, SAE TopK, features sobre Políglota, steering, inversión, cierre."""
from _a6_src17 import SAE_SRC


def part2(nb):
    nb.md("""
    ## 6. Superposición y sparse autoencoders (SAE)

    ### 6.1 Por qué los ejes no significan nada: superposición
    Un espacio de $d$ dimensiones solo tiene $d$ direcciones ortogonales, pero un modelo quiere representar **muchos más** conceptos ($n\\gg d$). **Elhage et al. (Anthropic, 2022, *Toy Models of Superposition*)** muestran que, si los conceptos son **dispersos** (rara vez activos a la vez), el modelo los almacena en direcciones **casi ortogonales** que se interfieren poco: *superposición*. Resultado: una neurona/dimensión mezcla varios conceptos (*polisemantismo*), y por eso mirar ejes individuales no funciona.
    Reproduzcamos el juguete: 5 características en 2 dimensiones, variando la **dispersión** $S$ (probabilidad de que una característica esté apagada).
    """)
    nb.code(r'''
    import torch.nn as nn, torch.nn.functional as F
    def juguete_superposicion(S, n=5, m=2, pasos=2500, seed=0):
        """Entrena x_hat = ReLU(W^T W x + b) con entradas dispersas (cada una apagada con prob. S). W: (m, n) -> columnas = direcciones."""
        torch.manual_seed(seed); W = nn.Parameter(torch.randn(m, n) * .3); b = nn.Parameter(torch.zeros(n)); opt = torch.optim.Adam([W, b], lr=5e-3)
        for _ in range(pasos):
            x = torch.rand(1024, n) * (torch.rand(1024, n) > S); xh = F.relu((x @ W.T) @ W + b); loss = ((x - xh) ** 2).mean() * n
            opt.zero_grad(); loss.backward(); opt.step()
        return W.detach().numpy(), loss.item()
    fig, ax = plt.subplots(1, 4, figsize=(14, 3.5)); cols5 = [AZUL, NARANJA, VERDE, ROJO, GRIS]
    for a, S in zip(ax, (0.0, 0.7, 0.9, 0.97)):
        W, l = juguete_superposicion(S)
        for j in range(5): a.annotate("", xy=W[:, j], xytext=(0, 0), arrowprops=dict(arrowstyle="->", color=cols5[j], lw=2)); a.text(*(W[:, j] * 1.12), f"f{j+1}", color=cols5[j], fontsize=9)
        a.set_xlim(-1.4, 1.4); a.set_ylim(-1.4, 1.4); a.set_aspect("equal"); a.set_title(f"dispersión S={S}\n(normas: {np.linalg.norm(W, axis=0).round(1)})", fontsize=8)
    plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** Con características **densas** (S=0) el modelo solo representa bien ~2 de las 5 (normas de longitud muy desigual: las demás se sacrifican). Al aumentar la dispersión, las **cinco** flechas aparecen con norma ≈ 1 y se reparten por el plano como un **pentágono**: 5 características en 2 dimensiones. *Superposición*: más conceptos que ejes, pagando interferencia.
    """)
    nb.gemini(
        "imagen", "M17-IMG-02", "Superposición: cinco características en dos dimensiones",
        "Imagen conceptual de la geometría de la superposición: con características dispersas, cinco direcciones forman un pentágono en un plano de 2 dimensiones; con características densas solo caben dos.",
        """
        Diagrama técnico limpio, fondo blanco, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280), tipografía sans-serif legible, flechas claras, sin ilustraciones decorativas. 16:9.
        Dos paneles lado a lado, cada uno un plano 2D con un círculo gris fino de radio 1 y ejes grises sin números.
        Panel izquierdo, título «Características DENSAS (S = 0)»: solo dos flechas largas, azul «f1» y naranja «f2», perpendiculares; tres flechas muy cortas casi invisibles en gris «f3, f4, f5». Debajo: «Solo 2 características caben bien».
        Panel derecho, título «Características DISPERSAS (S = 0.97)»: cinco flechas de igual longitud desde el origen formando un pentágono regular, con colores azul «f1», naranja «f2», verde «f3», gris «f4», azul con trazo discontinuo «f5», y líneas finas punteadas uniendo las puntas. Debajo: «5 características en 2 dimensiones: superposición».
        Entre los dos paneles una flecha gris con el texto «más dispersión».
        Evita: texto ilegible o inventado, ilustraciones decorativas, sombras 3D, más de cinco flechas, ejes con números.
        """,
        "Dos planos: con características densas solo caben dos direcciones; con características dispersas cinco direcciones forman un pentágono.",
        """
        S=0:    f1 ──►  f2 │  (3 casi sin norma)         S=0.97:  pentágono: f1..f5 con |f|≈1 en 2D
        """,
    )
    nb.md("""
    > 👀 **Qué debes observar:** a la izquierda (densas) solo dos flechas largas, ortogonales: el modelo sacrifica tres características. A la derecha (dispersas) cinco flechas en pentágono: caben más conceptos que dimensiones a cambio de **interferencia** (coseno 0.31 entre flechas vecinas y −0.81 entre no vecinas; la ReLU y el sesgo absorben la interferencia negativa). Conclusión para embeddings: un eje del vector no tiene por qué ser un concepto; buscar «la neurona del español» puede no tener sentido, y por eso se entrena un diccionario (6.2). Compáralo con la figura de código de arriba.
    """)
    nb.md("""
    ### 6.2 Sparse autoencoders: deshacer la superposición
    Si los conceptos están en superposición, buscamos un **diccionario sobrecompleto** $\\{a_j\\}_{j=1}^{m}$ ($m>d$) tal que cada vector se reconstruya con **pocos átomos**:
    $$\\hat x = W_{dec}\\,z + b_{dec},\\qquad z=\\text{codificación dispersa}(x)$$
    - **ReLU + L1** (Bricken et al., Anthropic 2023; Cunningham et al. 2023): $z=\\mathrm{ReLU}(W_{enc}(x-b_{dec})+b_{enc})$ y pérdida $\\lVert x-\\hat x\\rVert^2+\\lambda\\lVert z\\rVert_1$. Hay que ajustar $\\lambda$ para el $L_0$ deseado y la penalización L1 **encoge** los valores (sesgo).
    - **TopK** (Gao et al., OpenAI 2024; ya en el *k-sparse autoencoder* de Makhzani & Frey, 2013): $z=\\mathrm{TopK}(W_{enc}(x-b_{dec})+b_{enc})$ conserva solo las $k$ mayores activaciones. **$L_0=k$ exacto**, sin $\\lambda$, mejor frontera reconstrucción–dispersión y pocos latentes muertos con inicialización y pérdida auxiliar adecuadas.
    - **AuxK** (Gao et al.): los latentes *muertos* (sin activarse en mucho tiempo) intentan reconstruir el **residuo** con sus top-$k_{aux}$ preactivaciones; resucita átomos.
    - Columnas de $W_{dec}$ con **norma 1** (si no, el modelo «hace trampa» escalando).
    Medimos **NMSE** $=\\lVert X-\\hat X\\rVert^2/\\lVert X-\\bar X\\rVert^2$. (JumpReLU, Rajamanoharan et al. 2024, es otra variante que aprende un umbral por latente; no la implementamos.)
    """)
    nb.gemini(
        "imagen", "M17-IMG-03", "Arquitectura de un sparse autoencoder TopK",
        "Flujo x → encoder lineal → TopK (solo k activos) → decoder con átomos unitarios → x̂, con pérdida de reconstrucción, y la interpretación de cada átomo como una característica.",
        """
        Diagrama técnico limpio, fondo blanco, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280), tipografía sans-serif legible, flechas claras, sin ilustraciones decorativas. 16:9.
        De izquierda a derecha cinco bloques conectados por flechas:
        1) Caja azul «x ∈ R^64 (embedding del documento)» dibujada como una fila de 12 celdas.
        2) Caja azul «Encoder lineal W_enc (x − b_dec) + b_enc → 96 preactivaciones» dibujada como una fila larga de 24 celdas grises.
        3) Caja naranja «TopK (k = 4)»: de la fila larga solo 4 celdas quedan en naranja intenso con valores «0.9, 0.6, 0.4, 0.3» y el resto tachado en gris; etiqueta «z: dispersa, L0 = k».
        4) Caja verde «Decoder W_dec (96 átomos de norma 1) z + b_dec» con un pequeño abanico de 4 flechas verdes que se suman.
        5) Caja azul «x̂ ≈ x» con una flecha de retorno punteada gris hacia 1 con el texto «pérdida: ‖x − x̂‖² / varianza».
        Debajo del bloque 4, un recuadro gris: «Cada átomo = una característica: se interpreta por sus documentos más activos y por sus términos». Un recuadro más pequeño naranja: «AuxK: los latentes muertos reconstruyen el residuo».
        Título superior: «Sparse autoencoder TopK sobre embeddings».
        Evita: texto ilegible o inventado, ilustraciones decorativas, sombras 3D, más de cinco bloques, flechas ambiguas.
        """,
        "Un embedding pasa por un encoder lineal, una activación TopK que deja pocos latentes activos y un decoder de átomos unitarios que reconstruye el vector.",
        """
        x(64) -> [W_enc] -> 96 preact -> [TopK k=4] -> z dispersa -> [W_dec, átomos |a|=1] -> x_hat
                                                      pérdida NMSE (+ AuxK en latentes muertos)
        """,
    )
    nb.md("""
    > 👀 **Qué debes observar:** el cuello no es estrecho sino **ancho** ($m > d$, sobrecompleto) y lo que obliga a separar conceptos es el TopK: solo $k$ átomos activos por vector. Cada columna del decoder (unitaria) es una característica candidata; la pérdida es solo de reconstrucción, así que la interpretabilidad **no** está garantizada: se mide (sección 7 y proyecto). Es un *dictionary learning* clásico, pariente del codebook VQ del módulo 08 (allí 1 átomo por vector; aquí $k$).
    """)
    nb.md("### 6.3 Implementación desde cero (PyTorch)\nTopK SAE con inicialización *tied*, `b_dec` = media de los datos, decoder normalizado en cada paso y AuxK; más el SAE ReLU+L1 para comparar.")
    nb.code(SAE_SRC)
    nb.md("""
    ### 6.4 ¿Recupera características *conocidas*? (verdad terreno)
    Antes de interpretar *features* de un embedding real necesitamos saber si el método **recupera lo que hay**. Generamos datos con **64 direcciones reales** en 24 dimensiones (superposición: $64>24$), cada muestra mezcla **3** al azar. Medimos, para cada dirección real, el coseno con el mejor átomo aprendido.
    """)
    nb.code(r'''
    def datos_plantados(n_true=64, d=24, k_act=3, n=6000, seed=0):
        g = torch.Generator().manual_seed(seed); Dtrue = F.normalize(torch.randn(n_true, d, generator=g), dim=1)
        idx = torch.stack([torch.randperm(n_true, generator=g)[:k_act] for _ in range(n)]); coef = torch.rand(n, k_act, generator=g) * 1.5 + .5
        return torch.zeros(n, n_true).scatter(1, idx, coef) @ Dtrue + 0.01 * torch.randn(n, d, generator=g), Dtrue
    Xp, Dtrue = datos_plantados()
    from sklearn.decomposition import PCA
    pasos = 2500 if FAST_DEV_RUN else 6000; resultados = {}
    s_tk, _ = entrena_topk(Xp.numpy(), n_lat=128, k=3, pasos=pasos); zt, xt = codifica(s_tk, Xp); resultados["TopK (k=3)"] = (s_tk.W_dec.data.T, nmse(Xp, xt), float((zt > 0).float().sum(1).mean()))
    for lam in (3e-2, 1e-1):
        s_l1 = entrena_relu_l1(Xp.numpy(), 128, lam, pasos); zl, xl = codifica(s_l1, Xp); resultados[f"ReLU+L1 (λ={lam})"] = (s_l1.W_dec.data.T, nmse(Xp, xl), float((zl > 0).float().sum(1).mean()))
    pca = PCA(24).fit(Xp.numpy()); resultados["PCA (24 comp.)"] = (torch.tensor(pca.components_), nmse(Xp, torch.tensor(pca.inverse_transform(pca.transform(Xp.numpy())))), 24.0)
    filas = []
    for n, (W, e, l0) in resultados.items():
        mejor = (W @ Dtrue.T).abs().max(0).values; filas.append({"método": n, "características recuperadas (cos>0.9)": float((mejor > .9).float().mean()), "cos medio con el mejor átomo": float(mejor.mean()), "NMSE": e, "L0": l0})
    rec = pd.DataFrame(filas).set_index("método"); display(rec.round(3))
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.5)); rec["características recuperadas (cos>0.9)"].plot(kind="bar", ax=ax[0], color=[VERDE, AZUL, AZUL, GRIS], rot=15); ax[0].set_ylabel("fracción de las 64 recuperadas"); ax[0].set_title("Recuperación de características plantadas")
    for n, c in zip(rec.index, [VERDE, AZUL, AZUL, GRIS]): ax[1].scatter(rec.loc[n, "L0"], rec.loc[n, "NMSE"], s=70, color=c); ax[1].annotate(n, (rec.loc[n, "L0"], rec.loc[n, "NMSE"]), fontsize=7, xytext=(4, 4), textcoords="offset points")
    ax[1].set_xscale("log"); ax[1].set_xlabel("L0 (átomos activos por muestra, log)"); ax[1].set_ylabel("NMSE"); ax[1].set_title("Frontera reconstrucción–dispersión"); plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** (1) **PCA no recupera ninguna** característica (no puede: solo hay 24 ejes y 64 conceptos). (2) TopK con $k=3$ (el $L_0$ verdadero) recupera casi todas con **NMSE bajo**. (3) ReLU+L1 con $\\lambda$ pequeño es denso y **no recupera**; con $\\lambda$ mayor recupera pero a costa de **NMSE más alto** (el encogimiento L1) y $L_0$ difícil de fijar. Es el resultado cualitativo que motivó TopK en Gao et al. 2024. ⚠️ Es un problema **sintético y fácil** (ortogonalidad casi perfecta, dispersión exacta): en datos reales hay mucho menos margen.
    """)
    nb.md("### 6.5 Frontera reconstrucción–dispersión y latentes muertos en los embeddings de Políglota")
    nb.code(r'''
    pasos = 1500 if FAST_DEV_RUN else 4000; ks = [2, 4, 8, 16]; fr_topk, fr_l1 = [], []
    for k in ks:
        s, _ = entrena_topk(E, n_lat=96, k=k, pasos=pasos // 2); z, xh = codifica(s, E); fr_topk.append((k, nmse(E, xh)))
    for lam in (3e-3, 1e-2, 3e-2, 1e-1):
        s = entrena_relu_l1(E, 96, lam, pasos // 2); z, xh = codifica(s, E); fr_l1.append((float((z > 0).float().sum(1).mean()), nmse(E, xh)))
    hist_aux = {a: entrena_topk(E, n_lat=96, k=4, pasos=pasos, lr=8e-3, auxk=a)[1] for a in (False, True)}
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 3.6))
    ax[0].plot(*zip(*fr_topk), "o-", color=VERDE, label="TopK"); ax[0].plot(*zip(*fr_l1), "s-", color=AZUL, label="ReLU + L1 (variando λ)"); ax[0].set_xscale("log"); ax[0].set_yscale("log")
    ax[0].set_xlabel("L0 medio (log)"); ax[0].set_ylabel("NMSE (log)"); ax[0].legend(frameon=False); ax[0].set_title("Frontera sobre embeddings de Políglota (96 latentes)")
    for a, c in ((False, ROJO), (True, VERDE)): ax[1].plot(np.arange(len(hist_aux[a]["muertos"])) * 25, hist_aux[a]["muertos"], color=c, label="con AuxK" if a else "sin AuxK")
    ax[1].set_xlabel("paso de entrenamiento"); ax[1].set_ylabel("latentes muertos (sin activarse en 200 pasos)"); ax[1].legend(frameon=False); ax[1].set_title("Latentes muertos (lr alto = 8e-3)")
    plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** (1) A igual $L_0$, TopK reconstruye mejor (curva por debajo) y no necesita ajustar $\\lambda$. (2) Los latentes muertos aparecen con $lr$ alto; **AuxK no siempre los evita en un problema pequeño** como este (los datos solo tienen 36 facetas: sobran átomos): la mitigación efectiva depende de tamaño del diccionario, datos y *lr*. En los LLM de Gao et al., con el AuxK y la inicialización adecuada, reportan muy pocos latentes muertos incluso a gran escala.
    """)

    # ───────── 7. SAE sobre Políglota ─────────
    nb.md("""
    ## 7. Un SAE sobre los embeddings de Políglota: ¿son interpretables sus *features*?
    Entrenamos un TopK SAE ($m=96$ latentes, $k=4$) sobre LSI-64. Interpretamos una *feature* de dos maneras: (a) sus **documentos más activos** y (b) como el embedding LSI es lineal en los términos, **proyectamos su átomo del decoder al espacio de términos** ($a^\\top V_k$, con $V_k$ los componentes SVD) para leer sus **palabras** — algo imposible con embedders de transformer (ahí solo (a)).
    **Medida cuantitativa de interpretabilidad (con verdad terreno):** *pureza* = fracción de los 20 documentos más activos de una *feature* que comparten la **misma faceta**; comparamos con las direcciones de **k-means** y de **PCA**.
    """)
    nb.code(r'''
    pasos = 2000 if FAST_DEV_RUN else 5000
    sae, hist = entrena_topk(E, n_lat=96, k=4, pasos=pasos, auxk=True); Z, Xh = codifica(sae, E); Z = Z.numpy()
    activos = (Z > 0).sum(0) >= 10
    def pureza(scores, etiquetas, top=20): return np.array([np.bincount(etiquetas[np.argsort(-scores[:, j])[:top]]).max() / top for j in range(scores.shape[1])])
    from sklearn.cluster import KMeans
    n_f = int(activos.sum()); km = KMeans(n_f, n_init=3, random_state=0).fit(E); Ck = km.cluster_centers_; sc_km = E @ Ck.T / (np.linalg.norm(Ck, axis=1) + 1e-9)
    pc = PCA(min(n_f, 64)).fit(E); sc_pc = np.abs((E - pc.mean_) @ pc.components_.T)
    P = {"SAE TopK": pureza(Z[:, activos], fac_id), "k-means": pureza(sc_km, fac_id), "PCA": pureza(sc_pc, fac_id)}
    print(f"SAE: {n_f} latentes activos de 96 · NMSE={nmse(E, Xh):.3f} · L0=4 · facetas cubiertas por alguna feature con pureza ≥ 0.8: "
          f"{len({np.bincount(fac_id[np.argsort(-Z[:, j])[:20]]).argmax() for j in np.where(activos)[0] if P['SAE TopK'][list(np.where(activos)[0]).index(j)] >= .8})}/36")
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 3.5)); ax[0].bar(list(P), [v.mean() for v in P.values()], color=[VERDE, AZUL, GRIS]); ax[0].set_ylabel("pureza media (misma faceta en el top-20)"); ax[0].set_title("Interpretabilidad medida")
    for (n, v), c in zip(P.items(), (VERDE, AZUL, GRIS)): ax[1].hist(v, bins=np.linspace(0, 1, 11), alpha=.55, color=c, label=n)
    ax[1].set_xlabel("pureza por feature"); ax[1].set_ylabel("nº de features"); ax[1].legend(frameon=False); ax[1].set_title("Distribución de la pureza"); plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** Las *features* del SAE son más **monosemánticas** que las componentes de **PCA** (pureza media más alta) pero **no necesariamente que los centroides de k-means**, que optimizan directamente agrupar documentos. La ventaja del SAE no es ganar a k-means en pureza, sino que cada documento es una **suma de pocos átomos** (composicionalidad), lo que permite descomponer un vector en varios conceptos y editar uno de ellos. Mira también la cola: hay *features* mezcladas (pureza baja).
    """)
    nb.code(r'''
    cols = np.where(activos)[0]; pur = P["SAE TopK"]; orden = cols[np.argsort(-pur)][:8]
    inv_voc = {j: t for t, j in lsi.tf.vocabulary_.items()} if lsi is not None else None
    filas = []
    for j in orden:
        top_docs = np.argsort(-Z[:, j])[:20]; faceta_dom = np.bincount(fac_id[top_docs]).argmax(); nombre_f = np.unique(facet)[faceta_dom]
        palabras = ""
        if lsi is not None:
            w = sae.W_dec.data[:, j].numpy() @ lsi.svd.components_; palabras = ", ".join(inv_voc[t] for t in np.argsort(-w)[:6])
        filas.append({"feature": int(j), "pureza": pur[list(cols).index(j)], "faceta dominante": nombre_f, "idioma dominante": pd.Series(lang[top_docs]).mode()[0], "términos del átomo (decoder × SVD)": palabras, "activa en %docs": 100 * float((Z[:, j] > 0).mean())})
    display(pd.DataFrame(filas).set_index("feature").round(2))
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** Las mejores *features* se leen como conceptos de la documentación («expiración, ttl, vencimiento…» ↔ faceta `cache.ttl`) y, según el átomo, agrupan términos de **uno o de los dos idiomas** (compara la columna de términos con la de idioma dominante: que el espacio comparta direcciones entre ES y EN es una propiedad del embedder, no del SAE). Esto es un **auto-etiquetado manual**: en la práctica se automatiza con un LLM («auto-interpretabilidad») que *también* hay que validar.
    """)
    nb.code(r'''
    # ¿Son estables las features entre semillas? (Paulo & Belrose 2025 lo midieron en LLMs; aquí en pequeño)
    sae_b, _ = entrena_topk(E, n_lat=96, k=4, pasos=pasos, auxk=True, seed=1); Za, _ = codifica(sae_b, E)
    Wa, Wb = sae.W_dec.data.T[activos], sae_b.W_dec.data.T[(Za.numpy() > 0).sum(0) >= 10]; cos = (Wa @ Wb.T).abs().max(1).values.numpy()
    fig, ax = plt.subplots(figsize=(6, 3.2)); ax.hist(cos, bins=np.linspace(0, 1, 21), color=AZUL); ax.axvline(.9, color=ROJO, ls="--")
    ax.set_xlabel("coseno máximo del átomo con los átomos de otra semilla"); ax.set_ylabel("nº de features"); ax.set_title(f"Estabilidad entre semillas: {np.mean(cos > .9):.0%} con coseno > 0.9"); plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** **No todas** las features se reproducen entre semillas. Paulo & Belrose (2025) midieron en un SAE de 131 K latentes sobre Llama 3 8B que solo ≈ 30 % de las features se comparten entre semillas, y concluyen que el conjunto aprendido es *una* descomposición útil, **no la lista completa de lo que usa el modelo**. En nuestro juguete se reproduce **menos de la mitad** (≈ 0.4–0.5 según pasos y semilla; el título de la figura da el valor de tu ejecución) aunque los datos tengan solo 36 clústeres; la lección es la misma: **reporta varias semillas** antes de afirmar «el modelo tiene la feature X».
    """)
    nb.md("### 7.1 Steering con una *feature* del SAE (y comparación con la diferencia de medias)")
    nb.code(r'''
    j_git = max(cols, key=lambda j: np.mean(topic[np.argsort(-Z[:, j])[:20]] == "git"))              # la feature más "git"
    w_sae = sae.W_dec.data[:, j_git].numpy(); w_dm = (mu["git"] - mu["cache"]); w_dm = w_dm / np.linalg.norm(w_dm)
    En_ = E / np.linalg.norm(E, axis=1, keepdims=True); res = {"átomo del SAE": [], "diferencia de medias": []}; alphas2 = [0, .25, .5, .75, 1, 1.5, 2]
    for a in alphas2:
        for nombre, w in (("átomo del SAE", w_sae), ("diferencia de medias", w_dm)):
            q = En_[qs] + a * w; q /= np.linalg.norm(q, axis=1, keepdims=True); sc = q @ En_.T; sc[np.arange(len(qs)), qs] = -9
            res[nombre].append(float((topic[np.argsort(-sc, axis=1)[:, :10]] == "git").mean()))
    fig, ax = plt.subplots(figsize=(6.8, 3.4)); ax.plot(alphas2, res["átomo del SAE"], "o-", color=VERDE, label=f"átomo SAE (feature {j_git})"); ax.plot(alphas2, res["diferencia de medias"], "s--", color=AZUL, label="diferencia de medias (git − cache)")
    ax.set_xlabel("α (misma escala: vectores unitarios)"); ax.set_ylabel("% del top-10 que es «git»"); ax.legend(frameon=False); ax.set_title("Steering: ¿una feature aprendida gana a una media?"); plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** La *feature* del SAE sí empuja los resultados hacia «git», pero **la diferencia de medias (sin entrenar nada) es igual o mejor**: coherente con *AxBench* (Wu et al., 2025), donde los SAE **no superan** a líneas base simples para steering/detección. Un SAE aporta **descomposición y legibilidad**, no necesariamente un mejor mando de control. 🔴 No lo vendas como lo segundo sin medirlo.
    """)

    # ───────── 8. Qué codifica ─────────
    nb.md("""
    ## 8. ¿Qué codifica un embedding de texto? Longitud y orden
    Dos propiedades que a menudo se asumen: **longitud** y **orden de las palabras**. En LSI (bolsa de palabras) sabemos la respuesta *por construcción*; con un embedder real se mide igual.
    """)
    nb.code(r'''
    es_ = lang == "es"; lon = np.array([len(t.split()) for t in txt]); y_len = np.digitize(lon[es_], np.quantile(lon[es_], [1/3, 2/3]))
    acc_len = sonda(E[es_], y_len)
    # ¿POR QUÉ se lee la longitud? Confusor: la longitud depende de qué plantillas de frase salieron, y eso es léxico (palabras de función)
    rng = np.random.default_rng(0); idx = rng.choice(len(txt), 200, replace=False); barajado = [" ".join(rng.permutation(txt[i].split())) for i in idx]
    if lsi is not None:
        Zb = lsi.svd.transform(lsi.tf.transform(barajado)); Zb /= np.linalg.norm(Zb, axis=1, keepdims=True); cos_orden = float(np.mean(np.sum(Zb * E[idx], axis=1)))
    else:
        cos_orden = float("nan")
    print(f"sonda de LONGITUD en docs ES (3 terciles, azar 0.33): {acc_len:.2f}")
    print(f"coseno entre un documento y el MISMO documento con las palabras barajadas: {cos_orden:.3f}  (1.0 = ciego al orden)")
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** (1) La sonda **sí lee la longitud** (≈ 0.99, azar 0.33). ¿Significa que el embedding «codifica la longitud»? **No necesariamente**: en nuestro corpus la longitud depende de qué *plantillas de frase* se usaron (diferentes palabras de función), así que la sonda puede estar leyendo **léxico confundido con longitud**. Es el problema central del probing: **correlación ≠ lo que el modelo codifica por la razón que crees**; hace falta un control (p. ej. igualar el léxico y variar solo la longitud). (2) El **orden es invisible por construcción** (coseno 1.0): un embedder de bolsa de palabras no distingue «A antes de B». Los embedders de transformer sí codifican algo de orden y longitud (varía por modelo): **mídelo** con sondas controladas y con tests de permutación.
    """)

    # ───────── 9. vec2text ─────────
    nb.md("""
    ## 9. vec2text y qué revela un embedding (puente a privacidad)
    **Morris, Kuleshov, Shmatikov y Rush (EMNLP 2023, *Text Embeddings Reveal (Almost) As Much As Text*)** muestran que se puede **reconstruir el texto** casi exactamente a partir de su embedding denso: su método multi-paso (generar, re-embeber, **corregir** iterativamente) recupera **el 92 % de textos de 32 tokens exactamente** y llega a reconstruir **nombres completos** en un conjunto de notas clínicas. **Zhang, Morris y Shmatikov (2025)** proponen inversión *zero-shot* universal entre embedders. Implicación: **un vector no es un hash**: guardar embeddings de datos sensibles equivale, en el peor caso, a guardar el texto.
    Nuestro LSI es lineal: la inversión es una **multiplicación** ($x\\approx V^\\top z$). Medimos qué fracción de los 10 términos más altos recuperados **aparece realmente** en el documento y cómo cambia con **ruido** añadido a los embeddings (defensa) frente a la utilidad de retrieval.
    """)
    nb.code(r'''
    Vk = lsi.svd.components_ if lsi is not None else None
    inv_voc = {j: t for t, j in lsi.tf.vocabulary_.items()} if lsi is not None else None
    def prec_inversion(Zmat, idx, n_top=10):
        out = []
        for i in idx:
            est = Zmat[i] @ Vk; top = np.argsort(-est)[:n_top]; palabras = set(re.findall(r"\w+", txt[i].lower())); out.append(np.mean([inv_voc[j] in palabras for j in top]))
        return float(np.mean(out))
    idx_i = np.random.default_rng(0).choice(len(txt), 200, replace=False); sigmas = [0, .02, .05, .1, .2, .4]; inv_p, util = [], []
    rng_n = np.random.default_rng(1)
    for s in sigmas:
        Zn = E + s * rng_n.standard_normal(E.shape).astype(np.float32); Znn = Zn / np.linalg.norm(Zn, axis=1, keepdims=True)
        inv_p.append(prec_inversion(Zn, idx_i)); qi = np.random.default_rng(2).choice(len(E), 300, replace=False); sc = E[qi] @ Znn.T; sc[np.arange(300), qi] = -9
        util.append(float((facet[np.argsort(-sc, axis=1)[:, :10]] == facet[qi][:, None]).mean()))
    fig, ax = plt.subplots(figsize=(7, 3.6)); ax.plot(sigmas, inv_p, "o-", color=ROJO, label="inversión: precisión@10 de términos recuperados"); ax.plot(sigmas, util, "s-", color=VERDE, label="utilidad: precisión@10 de faceta (retrieval)")
    ax.set_xlabel("desviación del ruido gaussiano por dimensión (embeddings de norma ≈ 1)"); ax.set_ylabel("valor"); ax.legend(frameon=False, fontsize=8); ax.set_ylim(0, 1.02); ax.set_title("Ruido como defensa: ¿cuánto cuesta?"); plt.tight_layout(); plt.show()
    print(dict(zip(sigmas, zip(np.round(inv_p, 2), np.round(util, 2)))))
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** Sin ruido, **≈ 90 % de los 10 términos recuperados están realmente en el documento** (el azar sería ≈ 1 %): el embedding filtra el vocabulario. Añadir ruido reduce la inversión, pero **también reduce la utilidad** de retrieval: es un **trade-off privacidad–utilidad** que debes medir con tu embedder y tu métrica (módulo 15). En un embedder real la inversión no es una multiplicación sino un modelo entrenado (vec2text) y las defensas se evalúan contra *ese* atacante, no contra el nuestro.
    > 📌 Puente al **módulo 18**: política de qué datos se embeben, cifrado en reposo del índice, control de acceso, y no tratar los vectores como «anonimizados».
    """)
    nb.code(r'''
    RUN_VEC2TEXT = False    # True en Colab (GPU recomendada): pip install -q vec2text. NO probada en el entorno de desarrollo.
    if RUN_VEC2TEXT:
        import vec2text
        corrector = vec2text.load_pretrained_corrector("gtr-base")                      # corrector para embeddings GTR-base (README del proyecto vec2text)
        recon = vec2text.invert_strings(["La caché expira tras un TTL de 60 segundos."], corrector=corrector, num_steps=20)
        print(recon)                                                                    # verifica nombres/argumentos en el README de la versión instalada
    else:
        print("RUN_VEC2TEXT=False: celda omitida (opcional).")
    ''')

    nb.md("""
    ## 🗺️ Mapa de madurez (estado a oct-2026)
    Ya has hecho probing, steering, un SAE TopK y una auditoría de inversión; la tabla separa lo que sirve como diagnóstico fiable de lo que todavía es investigación antes de ver su uso en producción.


    | Técnica | Madurez | Quién / dónde | Fuente |
    |---|---|---|---|
    | Probing con control tasks / selectividad | 🟢 sólido (como diagnóstico); 🟡 como *prueba causal* | NLP; probing crítico | Hewitt & Liang 2019; Belinkov 2022 |
    | Structural probe (sintaxis en la geometría) | 🟢 sólido como resultado de 2019 en BERT/ELMo | Investigación | Hewitt & Manning 2019 |
    | Hipótesis de representación lineal / direcciones de concepto | 🟡 emergente (evidencia fuerte, formalización reciente) | Representation engineering, steering | Park et al. 2023; Zou et al. 2023 |
    | Steering por activaciones (suma de vectores) | 🟡 emergente | Investigación | Turner et al. 2023; Arditi et al. 2024 |
    | Dimensiones dominantes / outliers en encoders | 🟢 sólido | BERT, GPT-2 | Timkey & van Schijndel 2021; Kovaleva et al. 2021 |
    | **Sparse autoencoders** en LLMs (monosemanticidad, TopK, JumpReLU) | 🟡 emergente | Anthropic, OpenAI, Google DeepMind (Gemma Scope) | Bricken 2023; Gao et al. 2024; Rajamanoharan 2024; Lieberum 2024 |
    | SAE sobre **embeddings de retrieval** | 🔴 experimental | Trabajos recientes (workshop/EMNLP) | Kang et al. 2024; Park et al. 2025 |
    | SAE como método de steering/detección frente a baselines simples | 🔴 resultados negativos reportados | AxBench | Wu et al. 2025 |
    | Inversión de embeddings (vec2text) | 🟡 emergente, amenaza **demostrada** en 32 tokens | Seguridad/privacidad | Morris et al. 2023; Zhang et al. 2025 |
    """)
    nb.md("""
    ## 🏭 En producción
    - **Diagnóstico geométrico barato en cada migración de embedder:** varianza por dimensión, coseno medio entre textos al azar, sondas de idioma/dominio. Un cambio de modelo que introduce una dimensión dominante o anisotropía extrema es una causa frecuente de regresiones silenciosas.
    - **Filtros y routing con sondas:** una sonda lineal sobre el embedding (idioma, tema, PII) es una forma barata de enrutar o filtrar sin llamar a otro modelo; la selectividad y la deriva de la sonda se monitorizan como cualquier modelo.
    - **Interpretabilidad de resultados:** con un SAE (o con k-means) puedes explicar *por qué* dos documentos se parecen («comparten las features expiración + ttl»); es una herramienta de **depuración y auditoría**, no una garantía causal.
    - **Privacidad:** trata los embeddings como datos sensibles (inversión demostrada en 32 tokens). Control de acceso al índice, minimización de PII antes de embeber, y pruebas de inversión sobre tu propio embedder antes de afirmar «anonimizado».
    - **Steering:** en producción rara vez se «gobierna» el retrieval con una feature: es más seguro usar filtros por metadatos o reranking. Considéralo experimental.
    """)
    nb.md("""
    ## 🧠 Secretos de la élite
    1. **Siempre reporta la tarea de control y la selectividad** (Hewitt & Liang). Una sonda MLP «lee» hasta etiquetas aleatorias por tipo (nuestro experimento: ≈ 0.95 en el control).
    2. **Probar que se puede leer no prueba que se use.** Borrar linealmente el idioma dejó la sonda en el azar y el retrieval **intacto** (§4). Lo causal exige intervenir y medir comportamiento.
    3. **Compara siempre con la diferencia de medias.** En *AxBench* los SAE no superaron a baselines simples en steering y detección; en nuestro juguete la media también igualó al átomo del SAE.
    4. **Más latentes ≠ más verdad.** Las features dependen de tamaño del diccionario, $k$ y **semilla** (Paulo & Belrose: ≈ 30 % compartidas en un SAE de 131 K latentes sobre Llama 3 8B). Entrena ≥ 3 semillas y reporta la fracción estable.
    5. **TopK te quita un hiperparámetro difícil** ($\\lambda$ de L1) y fija $L_0$; mide siempre la frontera NMSE–$L_0$ y los latentes muertos (AuxK, inicialización *tied*, decoder normalizado).
    6. **Una dimensión dominante puede arruinar el coseno.** Diagnostica `var_top1` y el coseno medio de pares al azar al elegir/migrar embedder (Timkey & van Schijndel; Kovaleva et al.: esas dimensiones son críticas para el modelo, no «basura» que se pueda borrar). Su primo en retrieval es la **hubness** (§5b): documentos que salen en todas las listas y anti-hubs que nadie encuentra; mide la cola de $N_k$ y prueba centrado o CSLS antes de culpar al modelo.
    7. **Un embedding no es un hash.** vec2text reconstruye el 92 % de textos de 32 tokens (Morris et al.); evalúa ruido/cuantización como defensa **contra un atacante real**, no con una heurística.
    8. **Valida los auto-etiquetados.** Etiquetar features con un LLM es útil pero debe contrastarse con pureza medida sobre etiquetas conocidas, como hicimos con las facetas.
    """)
    nb.md("""
    ## ⚠️ Errores comunes
    - Concluir que «el embedding codifica sintaxis/tema» con una sonda sobreparametrizada y sin control task.
    - Interpretar los **ejes** del embedding como conceptos (están rotados y en superposición).
    - Medir interpretabilidad de un SAE con *ejemplos elegidos a mano* en lugar de una métrica con verdad terreno o muestreo aleatorio de features.
    - Olvidar normalizar las columnas del decoder (el SAE «hace trampa» escalando).
    - Comparar SAEs con distinto $L_0$ sin igualar la frontera.
    - Tratar la dirección de un concepto como **causal** sin intervención ni baseline.
    - Dar por «anónimos» los embeddings de datos con PII.
    """)
    nb.md("""
    ## 📝 Autoevaluación
    <details><summary><b>1. (Cálculo)</b> Una sonda lineal saca 0.97 en la tarea real y 0.55 en la de control; una MLP 0.995 y 0.95. Calcula la selectividad de cada una e interpreta.</summary>

    Lineal: 0.97 − 0.55 = **0.42**. MLP: 0.995 − 0.95 = **0.045**. La MLP memoriza (tiene capacidad para aprender la tarea sin ayuda del embedding): su acierto no prueba que el embedding codifique el concepto; la lineal es más fiable.
    </details>

    <details><summary><b>2. (Cálculo)</b> Un SAE TopK con 256 latentes y k=4 sobre vectores de 64 dimensiones: ¿cuántos parámetros tiene (sin sesgos) y cuántos valores no nulos por muestra?</summary>

    $W_{enc}$: $256\\times64=16\\,384$; $W_{dec}$: $64\\times256=16\\,384$ ⇒ 32 768 parámetros (más sesgos: 256 + 64). **4** no nulos por muestra: $L_0=k$ exacto.
    </details>

    <details><summary><b>3. (Diagnóstico)</b> Tras migrar de embedder, el coseno medio entre textos aleatorios pasa de 0.15 a 0.85 y nDCG@10 cae 6 puntos. Hipótesis y comprobación.</summary>

    Anisotropía por una o pocas **dimensiones dominantes** (Timkey & van Schijndel). Comprueba `var_top1`, el coseno medio estandarizado y el nDCG tras **estandarizar/whitening**. Si se recupera, la causa era la geometría y no el contenido semántico.
    </details>

    <details><summary><b>4. (Diagnóstico)</b> Tu SAE tiene una feature «refund policy» muy interpretable, pero al sumar su átomo a la consulta el retrieval casi no cambia. ¿Por qué podría pasar?</summary>

    Interpretable ≠ causal. El átomo puede describir la actividad pero no ser la dirección que usa la similitud; la escala del átomo puede ser pequeña respecto a la norma de la consulta; y una dirección de **diferencia de medias** podría funcionar mejor (AxBench). Mide la intervención y compara con baselines.
    </details>

    <details><summary><b>5. (Transferencia)</b> Un cliente legal quiere embeber contratos con datos personales. ¿Qué le recomiendas a la luz de vec2text?</summary>

    Tratar los vectores como datos sensibles: minimizar/redactar PII antes de embeber, cifrar el índice y limitar acceso, evaluar la inversión sobre *su* embedder (vec2text y variantes), considerar embeber solo fragmentos sin identificadores, y medir el trade-off ruido/utilidad (módulo 18).
    </details>

    <details><summary><b>6. (Transferencia)</b> ¿Cómo comprobarías si una feature de un SAE entrenado sobre un embedder real es «la misma» que otra de un SAE con otra semilla?</summary>

    Compara los átomos del decoder por coseno máximo (y sus activaciones sobre un conjunto común); marca como estables las de coseno > 0.9 y compara su *top-activating* examples. Reporta la fracción estable y repite con ≥ 3 semillas.
    </details>
    """)
    nb.md("""
    ## 📚 Referencias
    - Hewitt & Manning (2019). *A Structural Probe for Finding Syntax in Word Representations*. NAACL 2019. <https://aclanthology.org/N19-1419/>
    - Hewitt & Liang (2019). *Designing and Interpreting Probes with Control Tasks*. EMNLP-IJCNLP 2019. <https://arxiv.org/abs/1909.03368>
    - Belinkov (2022). *Probing Classifiers: Promises, Shortcomings, and Advances*. Computational Linguistics 48(1). <https://arxiv.org/abs/2102.12452>
    - Park, Choe, Veitch (2023/2024). *The Linear Representation Hypothesis and the Geometry of Large Language Models*. ICML 2024. <https://arxiv.org/abs/2311.03658>
    - Turner et al. (2023). *Steering Language Models With Activation Engineering*. Preprint. <https://arxiv.org/abs/2308.10248> · Zou et al. (2023). *Representation Engineering: A Top-Down Approach to AI Transparency*. Preprint. <https://arxiv.org/abs/2310.01405> · Arditi et al. (2024). *Refusal in Language Models Is Mediated by a Single Direction*. NeurIPS 2024. <https://arxiv.org/abs/2406.11717>
    - Belrose et al. (2023). *LEACE: Perfect linear concept erasure in closed form*. NeurIPS 2023. <https://arxiv.org/abs/2306.03819>
    - Timkey & van Schijndel (2021). *All Bark and No Bite: Rogue Dimensions in Transformer Language Models Obscure Representational Quality*. EMNLP 2021. <https://arxiv.org/abs/2109.04404> · Kovaleva et al. (2021). *BERT Busters: Outlier Dimensions that Disrupt Transformers*. Findings of ACL 2021. <https://arxiv.org/abs/2105.06990> · Ethayarajh (2019). *How Contextual are Contextualized Word Representations?* EMNLP-IJCNLP 2019. <https://arxiv.org/abs/1909.00512> · Mu, Bhat, Viswanath (2018). *All-but-the-Top: Simple and Effective Postprocessing for Word Representations*. ICLR 2018. <https://arxiv.org/abs/1702.01417>
    - Radovanović, Nanopoulos, Ivanović (2010). *Hubs in Space: Popular Nearest Neighbors in High-Dimensional Data*. JMLR 11. <https://jmlr.org/papers/v11/radovanovic10a.html>
    - Conneau, Lample, Ranzato, Denoyer, Jégou (2018). *Word Translation Without Parallel Data* (CSLS). ICLR 2018. <https://arxiv.org/abs/1710.04087>
    - Elhage et al. (2022). *Toy Models of Superposition*. Transformer Circuits Thread (Anthropic). <https://arxiv.org/abs/2209.10652>
    - Bricken et al. (2023). *Towards Monosemanticity: Decomposing Language Models With Dictionary Learning*. Anthropic. <https://transformer-circuits.pub/2023/monosemantic-features> · Templeton et al. (2024). *Scaling Monosemanticity*. Anthropic. <https://transformer-circuits.pub/2024/scaling-monosemanticity/>
    - Cunningham et al. (2023). *Sparse Autoencoders Find Highly Interpretable Features in Language Models*. ICLR 2024. <https://arxiv.org/abs/2309.08600>
    - Makhzani & Frey (2013). *k-Sparse Autoencoders*. ICLR 2014. <https://arxiv.org/abs/1312.5663> · Gao et al. (2024). *Scaling and evaluating sparse autoencoders* (OpenAI). ICLR 2025. <https://arxiv.org/abs/2406.04093> · Rajamanoharan et al. (2024). *Jumping Ahead: Improving Reconstruction Fidelity with JumpReLU Sparse Autoencoders*. Preprint. <https://arxiv.org/abs/2407.14435> · Lieberum et al. (2024). *Gemma Scope: Open Sparse Autoencoders Everywhere All At Once on Gemma 2*. Preprint. <https://arxiv.org/abs/2408.05147>
    - Paulo & Belrose (2025). *Sparse Autoencoders Trained on the Same Data Learn Different Features*. Preprint. <https://arxiv.org/abs/2501.16615> · Wu et al. (2025). *AxBench: Steering LLMs? Even Simple Baselines Outperform Sparse Autoencoders*. ICML 2025. <https://arxiv.org/abs/2501.17148> · Karvonen et al. (2025). *SAEBench: A Comprehensive Benchmark for Sparse Autoencoders in Language Model Interpretability*. ICML 2025. <https://arxiv.org/abs/2503.09532>
    - SAE sobre embeddings de retrieval: Kang, Wang, Xiong (2024). *Interpret and Control Dense Retrieval with Sparse Latent Features*. Preprint. <https://arxiv.org/abs/2411.00786> · Park, Kim, Ko (2025). *Decoding Dense Embeddings: Sparse Autoencoders for Interpreting and Discretizing Dense Retrieval*. EMNLP 2025. <https://arxiv.org/abs/2506.00041>
    - Morris, Kuleshov, Shmatikov, Rush (2023). *Text Embeddings Reveal (Almost) As Much As Text*. EMNLP 2023. <https://arxiv.org/abs/2310.06816> · Li, Xu, Song (2023). *Sentence Embedding Leaks More Information than You Expect: Generative Embedding Inversion Attack to Recover the Whole Sentence*. Findings of ACL 2023. <https://arxiv.org/abs/2305.03010> · Zhang, Morris, Shmatikov (2025). *Universal Zero-shot Embedding Inversion*. Preprint. <https://arxiv.org/abs/2504.00147>
    - Material del curso: módulos 09–12 (geometría y embedders), 15 (`poliglota_eval.py`), 18 (privacidad y producción).
    """)
