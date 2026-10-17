# Protocolo de checkpoints para agentes

Las sesiones pueden caerse (límites de API, reinicios del contenedor) y **lo que no esté en git se pierde**.

1. Cada agente tiene su archivo `recsys-course/_tools/progress/<tarea>.md` con: objetivo, lista de subtareas con `[x]`/`[ ]`, y notas para retomar (qué archivo, qué celda, qué falta, decisiones tomadas).
2. Al empezar: lee tu archivo de progreso (si existe) y `git log --oneline -15`; retoma desde la primera subtarea sin marcar. No rehagas lo marcado.
3. Tras **cada subtarea completada** (p. ej. un módulo revisado, una sección escrita): actualiza tu archivo de progreso, ejecuta el builder afectado hasta OK y haz commit + push **solo de tus archivos**:
   ```bash
   cd /home/user/IA-practice
   git add <tus rutas> recsys-course/_tools/progress/<tarea>.md
   git commit -m "<mensaje>" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
   Claude-Session: https://claude.ai/code/session_0196aNFuQmuEykCu8ZZk65kj"
   git pull --rebase -q origin claude/recommendation-systems-course-s08zlj; git push -q origin claude/recommendation-systems-course-s08zlj
   ```
   Si falla por `index.lock` u otro agente empujando a la vez, espera unos segundos y reintenta (hasta 4 veces). Nunca uses `git add -A`, `--force` ni reescribas historia.
4. Para trabajos largos (ejecuciones con nbclient), anota en el progreso qué comando lanzaste y su resultado antes de seguir.
