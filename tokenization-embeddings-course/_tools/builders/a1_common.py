"""Helpers de texto compartidos por build_00/01/02 (autor A1). No cambian nbbuild.py."""
import hashlib  # noqa: F401  (solo para que el helper de tiktoken sea copiable)

OBS = "> 👀 **Qué debes observar.** "


def obs(texto: str) -> str:
    """Caja «👀 Qué debes observar» (se coloca tras un gráfico o celda Gemini)."""
    lines = texto.strip().splitlines()
    return "> 👀 **Qué debes observar.** " + lines[0] + "".join("\n> " + ln for ln in lines[1:])


def caja(emoji_titulo: str, texto: str) -> str:
    """Caja destacada de blockquote: caja('💡 Intuición', '...')."""
    lines = texto.strip().splitlines()
    return f"> **{emoji_titulo}.** " + lines[0] + "".join("\n> " + ln for ln in lines[1:])


def details(resumen: str, cuerpo: str) -> str:
    return f"<details>\n<summary>{resumen}</summary>\n\n{cuerpo.strip()}\n\n</details>"


def preguntas(items: list[tuple[str, str, str]]) -> str:
    """items: (etiqueta, pregunta, respuesta). etiqueta p. ej. '(Cálculo)', '(Diagnóstico)', '(Transferencia)', ''."""
    out = []
    for i, (tag, q, a) in enumerate(items, 1):
        t = f" **{tag}**" if tag else ""
        out.append(f"**{i}.**{t} {q.strip()}\n\n" + details("Ver respuesta", a))
    return "\n\n".join(out)


def pista(n: int, texto: str) -> str:
    return details(f"🪜 Pista {n}", texto)


def mapa_madurez(filas: list[tuple[str, str, str, str]]) -> str:
    """filas: (técnica, etiqueta 🟢/🟡/🔴, quién la usa, fuente)."""
    out = ["| Técnica | Madurez (oct-2026) | Quién la usa (respaldado) | Fuente |", "|---|---|---|---|"]
    out += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in filas]
    return "\n".join(out)


# Celda robusta para obtener el tokenizer GPT-2 de tiktoken: oficial -> espejo GitHub verificado por SHA-256 -> None
SRC_GPT2 = '''
import hashlib
import os
import tempfile
import urllib.request


def get_gpt2_encoding():
    """tiktoken 'gpt2'. 1) oficial (openaipublic); 2) espejo en GitHub (graykode/gpt-2-Pytorch) verificado con los
    mismos SHA-256 que exige tiktoken; 3) None (las celdas que lo usan se omiten con un aviso)."""
    import tiktoken
    try:
        return tiktoken.get_encoding("gpt2")
    except Exception as e:  # noqa: BLE001
        print(f"[tiktoken] descarga oficial no disponible ({type(e).__name__}); pruebo el espejo de GitHub...")
    try:
        import tiktoken_ext.openai_public as op
        from tiktoken.load import data_gym_to_mergeable_bpe_ranks
        base = "https://raw.githubusercontent.com/graykode/gpt-2-Pytorch/master/GPT2/"
        sha = {"vocab.bpe": "1ce1664773c50f3e0cc8842619a93edc4624525b728b188a9e0be33b7726adc5",
               "encoder.json": "196139668be63f3b5d6574427317ae82f612a97c5d1cdaf36ed2256dbf636783"}
        paths = {}
        for name, h in sha.items():
            data = urllib.request.urlopen(base + name, timeout=60).read()
            assert hashlib.sha256(data).hexdigest() == h, f"hash de {name} no coincide"
            paths[name] = os.path.join(tempfile.gettempdir(), "gpt2_" + name)
            with open(paths[name], "wb") as f:
                f.write(data)
        ranks = data_gym_to_mergeable_bpe_ranks(vocab_bpe_file=paths["vocab.bpe"], encoder_json_file=paths["encoder.json"])
        print("[tiktoken] GPT-2 cargado desde el espejo de GitHub (hashes verificados)")
        return tiktoken.Encoding("gpt2", pat_str=op.r50k_pat_str, mergeable_ranks=ranks,
                                 special_tokens={"<|endoftext|>": 50256})
    except Exception as e:  # noqa: BLE001
        print(f"[tiktoken] sin GPT-2 ({type(e).__name__}: {str(e)[:80]}). Las comparaciones con tiktoken se omiten.")
        return None
'''.strip("\n")

# Estilo de gráficos común
SRC_PLOT_STYLE = '''
import matplotlib.pyplot as plt

AZUL, NARANJA, VERDE, GRIS, ROJO = "#1F6FEB", "#F28E2B", "#2CA02C", "#6B7280", "#D62728"
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.25, "axes.spines.top": False,
                     "axes.spines.right": False, "font.size": 10, "axes.titlesize": 11})
'''.strip("\n")
