# Progreso: autor-A7
Agente: Autor A7 · Módulos: 18–20 + extras
- [x] Módulo 18_produccion: README + lección + proyecto + build_18.py OK + commit/push
- [x] Módulo 19_playbook_elite: README + lección + proyecto + build_19.py OK + commit/push
- [x] extras/GUIA_ENTREVISTAS.md + commit/push
- [ ] extras/LECTURA_PAPERS.md + commit/push
- [ ] Módulo 20_capstone: README + lección + proyecto + build_20.py OK + commit/push
- [ ] check_course.py OK + informe final

## Notas para retomar
- Builders propios: `_tools/builders/_a7_common.py` (celdas compartidas: setup, versiones v1/v2, caché, ServicioPoliglota, adaptador, FastAPI),
  `_a7_l18.py` (lección 18), `_a7_p18.py` (proyecto 18 + README), `build_18.py`.
- Prueba: script de ejecución con nbclient en el scratchpad (`run_nb.py`, quita las celdas `!pip`). 18 lección ≈ 40 s, proyecto ≈ 45 s, 0 errores.
- REF del proyecto 18 (sintético + fallbacks): híbrido 0.864, +filtro 0.882, hit Zipf 0.805, adaptador 50 % 0.817, v1 0.786, v2 0.861.
- Precios verificados (oct-2026): OpenAI 3-small 0.02, 3-large 0.13 (página del modelo); gemini-embedding-001 0.15 (blog GA 14-jul-2025). GPU = supuestos.
- 19: `_a7_l19.py` (lección, ≈ 85 s), `_a7_p19.py` (proyecto 3 casos + README, < 5 s), `build_19.py`. Soluciones 100/100; becario 24/100.
- GUIA_ENTREVISTAS: 50 preguntas (A tokenización 1–14, B embeddings 15–30, C retrieval/eval 31–40, D producción 41–44, E system design 45–50); IDs arXiv verificados con arxiv.org/abs.
