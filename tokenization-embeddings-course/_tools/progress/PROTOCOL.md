# Protocolo de checkpoints para agentes

Las sesiones pueden caerse (límites de API, reinicios del contenedor) y **lo que no esté en git se pierde**.
Ruta del curso: `tokenization-embeddings-course` · Rama: `claude/tokenization-embeddings-course`.

1. Cada agente tiene su archivo `tokenization-embeddings-course/_tools/progress/<tarea>.md` con: objetivo, lista de subtareas con `[x]`/`[ ]`, y notas para retomar (qué archivo, qué celda, qué falta, decisiones tomadas).
2. Al empezar: lee tu archivo de progreso (si existe) y `git log --oneline -15`; retoma desde la primera subtarea sin marcar. No rehagas lo marcado.
3. Tras **cada subtarea completada** (p. ej. un módulo escrito o revisado): actualiza tu archivo de progreso, ejecuta el builder afectado hasta OK y haz commit + push **solo de tus archivos** (desde la raíz del repo):
   ```bash
   git add <tus rutas> tokenization-embeddings-course/_tools/progress/<tarea>.md
   git commit -m "<mensaje descriptivo>" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012y6p7GSFWMhSrhx94UWEWH"
   git push -q origin claude/tokenization-embeddings-course || { git pull --rebase --autostash -q origin claude/tokenization-embeddings-course && git push -q origin claude/tokenization-embeddings-course; }
   ```
   Varios agentes comparten el mismo árbol de trabajo: no hagas `git stash`, `checkout` ni `reset` de archivos ajenos. Si falla por `index.lock`, red u otro agente empujando a la vez, espera unos segundos y reintenta (hasta 4 veces, con espera creciente). Nunca uses `git add -A`/`git add .`, `--force` ni reescribas historia.
4. Para trabajos largos (ejecuciones con nbclient), anota en el progreso qué comando lanzaste y su resultado antes de seguir.
