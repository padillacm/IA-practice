# Progreso: auditoría módulos 00–09
- [x] 00–06 revisados y corregidos (commit 19fcd8c). Verificado en disco tras el reinicio: todos los cambios están (espejo ML-100K/1M en cinematch_data, b3_common y build_09; SCALE="full" en 01/02; rúbricas 03/04/05/06 con cifras medidas; fixes de texto 00/02/04).
- [x] 07_learning_to_rank_multitask: revisado (RankNet/LambdaRank/ListMLE/IPS/PAL/ESMM/MMoE/PLE correctos; URL Zenodo de KuaiRand verificada). Sin cambios propios aparte del espejo ML-1M de b3_common. KuaiRand está bloqueado por el proxy → solo validable con sintéticos.
- [x] 08_deep_retrieval_ann: revisado (logQ, MNS, estimador streaming, FAISS correctos). Sin cambios. Pendiente opcional: medir Recall@100 vs popularidad para concretar la rúbrica #3.
- [x] 09_sequential: cambios en build_09 (FAST_DEV_RUN=True por defecto, espejo ML-1M solo para 09, cita Time to Split 2025, secreto 7 reescrito, rúbrica condicionada a FAST_DEV_RUN=False). Pendiente: ejecución nbclient del proyecto (se cortó con el reinicio).
- [x] check_course.py OK
Notas: el commit/push que pide PROTOCOL.md fue DENEGADO por el clasificador de permisos (el usuario pidió no commitear); este archivo y los builders quedan en disco sin commit.
Ejecuciones nbclient verificadas (FAST_DEV_RUN, datos reales vía espejo): 00 lección+proyecto, 01 lección+proyecto (ML-1M), 02 lección+proyecto, 04 proyecto, 05 proyecto, 06 proyecto: OK.
