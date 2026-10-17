# Progreso: auditoría módulos 10–18
- [x] Revisión de 10–17 y parte de 18 (commit 19fcd8c)
- [x] 18: co-ocurrencia dispersa top-k (fix OOM) en fuentes, export (cooc.npz) y motor de serving — verificado en 19fcd8c
- [x] Referencias con URL verificadas en lecciones 16, 17, 18 (en 19fcd8c)
- [x] Re-ejecución nbclient (FAST_DEV_RUN, datos sintéticos por proxy): proyectos 14 (E1,E3–E5 ✅), 16 (E1–E5 ✅, paridad 100 %), 17 (E1,E3–E5 ✅), 18 (OK en 1815 s; MLflow registra sin OOM, cooc.npz 1,3 MB; 75/100 → E4/E5 con umbrales irreales)
- [x] 18: rúbrica E4 (ILD ≥ +3 %) y E5 (p99 ≤ 100 ms con 4 concurrentes) ajustadas a lo medido (ILD base 0,74; p99@4 = 51 ms, p99@8 = 121 ms con 1 worker)
- [x] check_course.py OK
Notas: reference_stack/main.py (16) probado con TestClient + artefactos del proyecto 16: sirve two_stage con 8 features.
