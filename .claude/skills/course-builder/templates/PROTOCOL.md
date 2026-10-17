# Protocolo de checkpoints para agentes

Las sesiones pueden caerse (límites de API, reinicios del contenedor) y **lo que no esté en git se pierde**.
Ruta del curso: `<RUTA_CURSO>` · Rama: `<RAMA>`.

1. Cada agente tiene su archivo `<RUTA_CURSO>/_tools/progress/<tarea>.md` con: objetivo, lista de subtareas con `[x]`/`[ ]`, y notas para retomar (qué archivo, qué celda, qué falta, decisiones tomadas).
2. Al empezar: lee tu archivo de progreso (si existe) y `git log --oneline -15`; retoma desde la primera subtarea sin marcar. No rehagas lo marcado.
3. Tras **cada subtarea completada** (p. ej. un módulo escrito o revisado): actualiza tu archivo de progreso, ejecuta el builder afectado hasta OK y haz commit + push **solo de tus archivos** (desde la raíz del repo):
   ```bash
   git add <tus rutas> <RUTA_CURSO>/_tools/progress/<tarea>.md
   git commit -m "<mensaje descriptivo>" -m "<ATRIBUCIÓN>"
   git push -q origin <RAMA> || { git pull --rebase --autostash -q origin <RAMA> && git push -q origin <RAMA>; }
   ```
   Varios agentes comparten el mismo árbol de trabajo: no hagas `git stash`, `checkout` ni `reset` de archivos ajenos. Si falla por `index.lock`, red u otro agente empujando a la vez, espera unos segundos y reintenta (hasta 4 veces, con espera creciente). Nunca uses `git add -A`/`git add .`, `--force` ni reescribas historia.
4. Para trabajos largos (ejecuciones con nbclient), anota en el progreso qué comando lanzaste y su resultado antes de seguir.
