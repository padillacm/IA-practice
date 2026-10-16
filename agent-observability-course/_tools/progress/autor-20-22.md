# Progreso: autor-20-22
Agente: Autor A8 · Módulos: 20–22 + extras
- [x] 20_privacidad_seguridad (lección 33 código/51 md, proyecto 15/19, supportops/privacy.py + tests, dashboard 20; lección ejecutada con nbclient sin stack y con stack; proyecto: rúbrica R1-R7 OK con la solución)
- [ ] 21_elite_playbook (supportops/incidents.py + tests ya escritos; falta build_21.py, dashboard 21, ejecución)
- [ ] 22_capstone
- [ ] extras/ENTREVISTAS_SYSTEM_DESIGN.md
- [ ] extras/RUTA_DE_CARRERA.md
- [ ] README raíz + pyproject (extra mcp) + sección INTERFACES.md
- [ ] check_course.py OK + informe final

## Notas para retomar
- Runner de notebooks: /tmp/claude-0/scr/runnb.py (nbclient); sesión de stack con candado: /tmp/claude-0/scr/live20.sh (se pierde si se reinicia el contenedor; recréalo: flock /tmp/obs-stack.lock + docker compose --profile core --profile metrics up -d + nbclient + down -v).
- Hallazgos 20: la tarjeta sintética del catálogo NO cumple Luhn (card_valid acepta prefijo 4000 0000); redaction procesa también el body string de los logs; OTTL replace_pattern con función SHA256 hashea el *replacement* (usar "$$0"); hmac_key >= 32 bytes; IsValidLuhn existe en OTTL (solo valores completos); backends.tempo_search devuelve dict (["traces"]).
- Mesa de incidentes: supportops/incidents.py (variant="mesa" proyecto, "lesson" ejemplos de la lección); find_window (t-stat sobre ventanas) es el detector de cambio que funciona mejor que CUSUM con n≈4/min.
