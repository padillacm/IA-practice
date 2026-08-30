"""Construye `data/kb/` a partir de la documentación oficial de LangChain/LangGraph.

Fuente: https://github.com/langchain-ai/docs (licencia MIT, (c) 2025 LangChain).
Se conserva solo la variante Python de cada página, se resuelven los componentes
de fragmento (`<XxxPy />`) y se recorta el ruido de MDX. El resultado es el corpus
que usan los notebooks de RAG del módulo 5.

Uso:  python _tools/preparar_kb.py /ruta/al/clon/de/langchain-ai-docs
"""

from __future__ import annotations

import pathlib
import re
import sys

PAGINAS = [
    ("langgraph/overview.mdx", "Qué es LangGraph"),
    ("langgraph/graph-api.mdx", "La Graph API: estado, nodos y aristas"),
    ("langgraph/persistence.mdx", "Persistencia: checkpointers, hilos y time travel"),
    ("langgraph/checkpointers.mdx", "Checkpointers disponibles"),
    ("langgraph/interrupts.mdx", "Interrupciones y human-in-the-loop"),
    ("langgraph/streaming.mdx", "Streaming"),
    ("langgraph/stores.mdx", "Stores y memoria de largo plazo"),
    ("langgraph/use-subgraphs.mdx", "Subgrafos"),
    ("langgraph/functional-api.mdx", "Functional API"),
    ("langgraph/fault-tolerance.mdx", "Tolerancia a fallos"),
    ("langgraph/workflows-agents.mdx", "Workflows y agentes"),
    ("langgraph/pregel.mdx", "Pregel: el runtime de LangGraph"),
    ("langgraph/thinking-in-langgraph.mdx", "Pensar en LangGraph"),
    ("langgraph/agentic-rag.mdx", "RAG agéntico"),
    ("langchain/agents.mdx", "Agentes con create_agent"),
    ("langchain/middleware/custom.mdx", "Middleware propio"),
    ("langchain/multi-agent/handoffs.mdx", "Handoffs entre agentes"),
    ("langchain/context-engineering.mdx", "Ingeniería de contexto"),
]

CABECERA = (
    "<!-- Fuente: https://github.com/langchain-ai/docs — documentación oficial de "
    "LangChain/LangGraph, licencia MIT, (c) 2025 LangChain.\n"
    "     Extracto reformateado para uso didáctico en el corpus RAG de este curso. -->\n"
)


def quitar_js(t: str) -> str:
    t = re.sub(r":::js\b.*?\n:::", "", t, flags=re.S)
    t = re.sub(r":::python\b", "", t)
    t = re.sub(r"^:::\s*$", "", t, flags=re.M)
    return t


def resolver_fragmentos(t: str, snip: pathlib.Path, prof: int = 0) -> str:
    if prof > 2:
        return t

    def rep(m: re.Match[str]) -> str:
        nombre = m.group(1)
        if nombre.endswith("Js"):
            return ""
        kebab = re.sub(r"(?<!^)(?=[A-Z])", "-", nombre).lower()
        f = snip / f"{kebab}.mdx"
        if not f.exists():
            return ""
        cuerpo = re.sub(r"^---\n.*?\n---\n", "", f.read_text(encoding="utf-8"), flags=re.S)
        return "\n" + resolver_fragmentos(quitar_js(cuerpo), snip, prof + 1) + "\n"

    return re.sub(r"<([A-Z][A-Za-z0-9]+)\s*/>", rep, t)


def limpiar(t: str) -> str:
    t = re.sub(r"^---\n.*?\n---\n", "", t, flags=re.S)          # frontmatter
    t = re.sub(r"</?(Note|Tip|Info|Warning|Card|CardGroup|Accordion|AccordionGroup|"
               r"Steps|Step|Tabs|Tab|Expandable|Frame|Columns|Column|Check|Danger)[^>]*>", "", t)
    t = re.sub(r"```(typescript|javascript|ts|js|tsx|jsx)[^\n]*\n.*?```", "", t, flags=re.S)
    t = re.sub(r"@\[`([^`]+)`\]", r"`\1`", t)                    # enlaces a la referencia
    t = re.sub(r"\[!code[^\]]*\]", "", t)
    t = re.sub(r"\{/\*.*?\*/\}", "", t, flags=re.S)              # comentarios MDX
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip() + "\n"


def main(raiz_docs: pathlib.Path) -> None:
    src = raiz_docs / "src"
    snip = src / "snippets" / "code-samples"
    destino = pathlib.Path(__file__).resolve().parent.parent / "data" / "kb"
    destino.mkdir(parents=True, exist_ok=True)

    total = 0
    for rel, titulo in PAGINAS:
        f = src / "oss" / rel
        if not f.exists():
            print(f"  [saltado] no existe {f}")
            continue
        cuerpo = limpiar(resolver_fragmentos(quitar_js(f.read_text(encoding="utf-8")), snip))
        nombre = rel.replace("/", "-").replace(".mdx", ".md")
        texto = f"{CABECERA}\n# {titulo}\n\n> Página original: `{rel}`\n\n{cuerpo}"
        (destino / nombre).write_text(texto, encoding="utf-8")
        total += len(texto)
        print(f"  {nombre:<46} {len(texto):>7} caracteres")
    print(f"\n{len(PAGINAS)} páginas, {total/1000:.0f} KB en {destino}")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/lcdocs"))
