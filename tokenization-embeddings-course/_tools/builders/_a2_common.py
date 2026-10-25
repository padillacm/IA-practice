"""Celdas comunes (strings) de los builders del autor A2 (módulos 03-05).

Cada notebook es autocontenido: estas celdas se COPIAN dentro de cada notebook.
No es un módulo del curso; solo evita repetir texto entre build_03/04/05.
"""

SETUP = '''
import os, sys, re, math, json, random, time, unicodedata, collections, itertools, warnings
os.environ.setdefault("OMP_NUM_THREADS", "1")          # evita sobre-suscripción de hilos
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
warnings.filterwarnings("ignore")
import numpy as np
import matplotlib.pyplot as plt

SEED = 42
FAST_DEV_RUN = True      # True: tamaños diminutos (CPU, minutos). False: escala completa (Colab Pro)
random.seed(SEED); np.random.seed(SEED)
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.25, "axes.spines.top": False, "axes.spines.right": False})
COL = {"azul": "#1F6FEB", "naranja": "#F28E2B", "verde": "#2CA02C", "gris": "#6B7280", "rojo": "#D62728"}
try:
    import torch
    torch.set_num_threads(1); torch.manual_seed(SEED)
    device = "cuda" if torch.cuda.is_available() else "cpu"
except ImportError:
    device = "cpu"
print("device:", device, "| FAST_DEV_RUN:", FAST_DEV_RUN)
'''

CORPUS_1 = '''
# ---- Utilidades de corpus Políglota (copia local; contrato: carga_corpus(fast_dev) -> dict) ----
import urllib.request, urllib.error, zipfile, io, inspect, ast

def hay_red(url: str, timeout: float = 6.0) -> bool:
    """Sonda rápida para no esperar minutos si el host está bloqueado (proxy corporativo, etc.)."""
    try:
        urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=timeout)
        return True
    except urllib.error.HTTPError:
        return True          # el servidor respondió (aunque sea 4xx): hay ruta de red
    except Exception:
        return False         # túnel bloqueado, DNS, timeout...

def _hf_wikipedia(lang: str, n: int, max_chars: int):
    from datasets import load_dataset
    ds = load_dataset("wikimedia/wikipedia", f"20231101.{lang}", split="train", streaming=True)
    out = []
    for ex in ds:
        if len(ex["text"]) > 400:
            out.append({"id": f"wiki_{lang}_{len(out)}", "lang": lang, "text": ex["text"][:max_chars]})
        if len(out) >= n:
            break
    return out

def _hf_codesearchnet(n: int):
    from datasets import load_dataset
    for repo, kw in [("code-search-net/code_search_net", {"name": "python"}), ("claudios/code_search_net", {"name": "python"}),
                     ("Nan-Do/code-search-net-python", {})]:
        try:
            ds = load_dataset(repo, split="train", streaming=True, **kw)
            out = []
            for ex in ds:
                code = ex.get("func_code_string") or ex.get("code") or ex.get("original_string")
                if code and 80 < len(code) < 3000:
                    out.append({"id": f"csn_{len(out)}", "lang": "code", "text": code})
                if len(out) >= n:
                    return out
        except Exception as e:
            print("   (CodeSearchNet vía", repo, "falló:", type(e).__name__, ")")
    raise RuntimeError("CodeSearchNet no disponible")

def _detok(s: str) -> str:
    s = re.sub(r"\\s+([,.;:!?%)\\]])", r"\\1", s)
    s = re.sub(r"([(\\[¿¡])\\s+", r"\\1", s)
    return re.sub(r"\\s+", " ", s).strip()

#---SPLIT---
def _espejo_nltk(n: int):
    """Espejo público: muestra de Europarl (ES/EN) del repositorio nltk_data en GitHub (CC/uso de investigación)."""
    url = "https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/europarl_raw.zip"
    z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(url, timeout=60).read()))
    docs = []
    for lang, folder, ext in [("es", "spanish", ".es"), ("en", "english", ".en")]:
        lines = []
        for name in sorted(z.namelist()):
            if f"/{folder}/" in name and name.endswith(ext):
                lines += [_detok(l) for l in z.read(name).decode("utf-8", "ignore").splitlines() if len(l.split()) > 6]
        step = 8
        chunks = [" ".join(lines[i:i + step]) for i in range(0, len(lines), step)]
        random.Random(SEED).shuffle(chunks)
        docs += [{"id": f"ep_{lang}_{i}", "lang": lang, "text": c[:2000]} for i, c in enumerate(chunks[:n])]
    return docs

def _codigo_stdlib(n: int):
    """Código Python real de la biblioteca estándar (siempre disponible, sin red)."""
    import json, re as _re, argparse, textwrap, collections as _c, itertools as _i, functools, pathlib, csv, heapq, bisect
    import statistics, difflib, string, shutil, tempfile, fractions, random as _r, datetime, calendar, glob, fnmatch, logging
    out = []
    for mod in [json.decoder, json.encoder, _re, argparse, textwrap, functools, pathlib, csv, heapq, bisect, statistics, difflib,
                shutil, tempfile, fractions, datetime, calendar, glob, fnmatch, logging, _c, _r]:
        try:
            tree = ast.parse(inspect.getsource(mod)); src = inspect.getsource(mod).splitlines()
        except (OSError, TypeError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef,)) and 4 <= (node.end_lineno - node.lineno) <= 40:
                code = "\\n".join(src[node.lineno - 1: node.end_lineno])
                if 80 < len(code) < 3000:
                    out.append({"id": f"std_{len(out)}", "lang": "code", "text": code})
    random.Random(SEED).shuffle(out)
    return out[:n]
'''

CORPUS_2 = '''
_ES_S = ["el sistema", "la base de datos", "el servidor", "la aplicación", "el modelo", "la biblioteca", "el usuario", "la función", "el módulo", "la consulta"]
_ES_V = ["procesa", "almacena", "devuelve", "actualiza", "valida", "descarga", "ejecuta", "registra", "indexa", "compara"]
_ES_O = ["los documentos relevantes", "una lista de resultados", "los parámetros de configuración", "las peticiones entrantes", "la información almacenada",
         "varias tablas de forma eficiente", "los errores más frecuentes", "las versiones anteriores", "los textos en diferentes idiomas", "un conjunto de datos nuevo"]
_ES_A = ["rápidamente", "automáticamente", "correctamente", "de manera incremental", "sin interrupciones", "cada vez que cambia la configuración", "antes de la instalación", "durante la inicialización"]
_EN_S = ["the system", "the database", "the server", "the application", "the model", "the library", "the user", "the function", "the module", "the query"]
_EN_V = ["processes", "stores", "returns", "updates", "validates", "downloads", "executes", "logs", "indexes", "compares"]
_EN_O = ["the relevant documents", "a list of results", "the configuration parameters", "the incoming requests", "the stored information",
         "several tables efficiently", "the most frequent errors", "the previous versions", "texts in different languages", "a new dataset"]
_EN_A = ["quickly", "automatically", "correctly", "incrementally", "without interruptions", "whenever the configuration changes", "before the installation", "during initialization"]

def _sintetico(n: int):
    """Último recurso: texto ES/EN generado por plantillas + funciones Python plantilla (mismo esquema)."""
    rng = random.Random(SEED); docs = []
    for lang, S, V, O, A in [("es", _ES_S, _ES_V, _ES_O, _ES_A), ("en", _EN_S, _EN_V, _EN_O, _EN_A)]:
        for i in range(n):
            sents = []
            for _ in range(rng.randint(4, 8)):
                s = f"{rng.choice(S)} {rng.choice(V)} {rng.choice(O)} {rng.choice(A)}."
                sents.append(s[0].upper() + s[1:])
            docs.append({"id": f"syn_{lang}_{i}", "lang": lang, "text": " ".join(sents)})
    names = ["load", "parse", "merge", "filter", "count", "split", "encode", "decode", "score", "rank"]
    things = ["items", "tokens", "rows", "words", "records", "paths", "values", "pairs"]
    for i in range(n):
        f, t = rng.choice(names), rng.choice(things)
        docs.append({"id": f"syn_code_{i}", "lang": "code", "text":
            f"def {f}_{t}({t}, limit={rng.randint(2, 99)}):\\n    \\"\\"\\"{f.capitalize()} the {t} and return at most limit results.\\"\\"\\"\\n"
            f"    result = []\\n    for x in {t}:\\n        if len(result) >= limit:\\n            break\\n        result.append(x)\\n    return result\\n"})
    return docs

#---SPLIT---
def _mini_golden(docs, n_q: int = 24):
    """Mini golden set: la consulta es la primera frase (≤ 12 palabras) del documento; qrels {qid: {doc_id: 1}}."""
    rng = random.Random(SEED); queries, qrels = [], {}
    for lang in ["es", "en", "code"]:
        pool = [d for d in docs if d["lang"] == lang]; rng.shuffle(pool)
        for d in pool[: n_q // 3]:
            if lang == "code":
                try:
                    q = (ast.get_docstring(ast.parse(d["text"]).body[0]) or "").split("\\n")[0]
                except SyntaxError:
                    q = ""
                q = q or re.sub(r"[_(].*", "", d["text"].split("def ")[-1]).replace("_", " ")
            else:
                q = " ".join(re.split(r"(?<=[.!?])\\s", d["text"])[0].split()[:12])
            qid = f"q{len(queries)}"; queries.append({"qid": qid, "lang": lang, "text": q}); qrels[qid] = {d["id"]: 1}
    return queries, qrels

#---SPLIT---
def carga_corpus(fast_dev: bool = True) -> dict:
    """Corpus Políglota. Cadena: oficial (HF Wikipedia + CodeSearchNet) -> espejo (Europarl vía GitHub + stdlib) -> sintético.
    Devuelve {"docs", "queries", "qrels", "source": "real"|"synthetic", "detail": {...}}."""
    n = 150 if fast_dev else 3000
    max_chars = 2000 if fast_dev else 6000
    docs, detail = [], {}
    hf_ok = hay_red("https://huggingface.co")
    for lang in ["es", "en"]:
        got = None
        if hf_ok:
            try: got, detail[lang] = _hf_wikipedia(lang, n, max_chars), "hf:wikimedia/wikipedia"
            except Exception as e: print(f"   (Wikipedia {lang} falló: {type(e).__name__})")
        if got is None and hay_red("https://raw.githubusercontent.com"):
            try:
                mirror = _espejo_nltk(n); got = [d for d in mirror if d["lang"] == lang]; detail[lang] = "espejo:nltk-europarl"
            except Exception as e: print(f"   (espejo {lang} falló: {type(e).__name__})")
        if got is None: got, detail[lang] = [d for d in _sintetico(n) if d["lang"] == lang], "sintetico"
        docs += got
    code = None
    if hf_ok:
        try: code, detail["code"] = _hf_codesearchnet(n), "hf:code_search_net"
        except Exception as e: print(f"   (CodeSearchNet falló: {type(e).__name__})")
    if code is None:
        code = _codigo_stdlib(n); detail["code"] = "espejo:stdlib-python"
        if len(code) < 10: code, detail["code"] = [d for d in _sintetico(n) if d["lang"] == "code"], "sintetico"
    docs += code
    queries, qrels = _mini_golden(docs)
    real = all(not v.startswith("sintetico") for v in detail.values())
    if not real: print("AVISO: parte del corpus es SINTÉTICA (sin acceso a los datasets). Las cifras absolutas cambiarán con datos reales.")
    return {"docs": docs, "queries": queries, "qrels": qrels, "source": "real" if real else "synthetic", "detail": detail}
'''

CORPUS_USE = '''
corpus = carga_corpus(fast_dev=FAST_DEV_RUN)
docs = corpus["docs"]
print("fuente:", corpus["source"], corpus["detail"])
by_lang = {l: [d["text"] for d in docs if d["lang"] == l] for l in ["es", "en", "code"]}
for l, ts in by_lang.items():
    print(f"{l:>4}: {len(ts):4d} docs | {sum(len(t) for t in ts)/1e3:8.1f} k caracteres | {sum(len(t.encode()) for t in ts)/1e3:8.1f} k bytes")
print("\\nEjemplo ES:", by_lang["es"][0][:160].replace("\\n", " "))
print("Ejemplo código:\\n", by_lang["code"][0][:200])
'''

# Métricas canónicas del módulo 00 (ganancia lineal como trec_eval, dedup, empates deterministas): fuente única
import pathlib as _pl
METRICS = (
    _pl.Path(__file__).parent / "poliglota_src" / "metrics.py").read_text(encoding="utf-8")

TOKMETRICS = '''
WORD_RE = re.compile(r"\\w+(?:['’]\\w+)?|[^\\w\\s]", re.UNICODE)
def palabras(text: str): return WORD_RE.findall(text)

def metricas_tokenizacion(encode, textos) -> dict:
    """encode: str -> list[str|int]. Devuelve fertilidad (tokens/palabra), bytes/token y caracteres/token."""
    n_tok = n_pal = n_byte = n_chr = 0
    for t in textos:
        n_tok += len(encode(t)); n_pal += len(palabras(t)); n_byte += len(t.encode("utf-8")); n_chr += len(t)
    return {"fertilidad": n_tok / max(n_pal, 1), "bytes_por_token": n_byte / max(n_tok, 1), "chars_por_token": n_chr / max(n_tok, 1), "tokens": n_tok}
'''

PARALELO = '''
# Frases paralelas (tipo FLORES): oficial -> espejo -> mini-conjunto escrito a mano (16 frases x 12 idiomas)
_PARALELO_MANO = {
 "en": ["The search engine returns the most relevant documents for each query.", "Please restart the server before installing the new version.",
        "The model was trained on a large collection of texts in several languages.", "Every user must change their password every ninety days.",
        "The function receives a list of numbers and returns their average.", "Yesterday it rained all day, so we stayed at home.",
        "The company opened three new offices in Europe this year.", "Reading the documentation carefully saves a lot of time.",
        "The meeting will begin at nine o'clock in the morning.", "Our system supports more than forty languages and several file formats.",
        "The children are playing in the park near the river.", "To install the library, run the command shown below.",
        "The results show that the new method is faster and more accurate.", "Water boils at one hundred degrees Celsius at sea level.",
        "She asked whether the database could be restored from a backup.", "Errors must be recorded in a log file for later analysis."],
 "es": ["El motor de búsqueda devuelve los documentos más relevantes para cada consulta.", "Reinicie el servidor antes de instalar la nueva versión.",
        "El modelo se entrenó con una gran colección de textos en varios idiomas.", "Cada usuario debe cambiar su contraseña cada noventa días.",
        "La función recibe una lista de números y devuelve su promedio.", "Ayer llovió todo el día, así que nos quedamos en casa.",
        "La empresa abrió tres oficinas nuevas en Europa este año.", "Leer la documentación con atención ahorra mucho tiempo.",
        "La reunión comenzará a las nueve de la mañana.", "Nuestro sistema admite más de cuarenta idiomas y varios formatos de archivo.",
        "Los niños juegan en el parque cerca del río.", "Para instalar la biblioteca, ejecute el comando que se muestra a continuación.",
        "Los resultados muestran que el nuevo método es más rápido y más preciso.", "El agua hierve a cien grados Celsius al nivel del mar.",
        "Ella preguntó si la base de datos se podía restaurar desde una copia de seguridad.", "Los errores deben registrarse en un archivo de registro para su análisis posterior."],
 "fr": ["Le moteur de recherche renvoie les documents les plus pertinents pour chaque requête.", "Veuillez redémarrer le serveur avant d'installer la nouvelle version.",
        "Le modèle a été entraîné sur une grande collection de textes dans plusieurs langues.", "Chaque utilisateur doit changer son mot de passe tous les quatre-vingt-dix jours.",
        "La fonction reçoit une liste de nombres et renvoie leur moyenne.", "Hier, il a plu toute la journée, alors nous sommes restés à la maison.",
        "L'entreprise a ouvert trois nouveaux bureaux en Europe cette année.", "Lire attentivement la documentation fait gagner beaucoup de temps.",
        "La réunion commencera à neuf heures du matin.", "Notre système prend en charge plus de quarante langues et plusieurs formats de fichier.",
        "Les enfants jouent dans le parc près de la rivière.", "Pour installer la bibliothèque, exécutez la commande ci-dessous.",
        "Les résultats montrent que la nouvelle méthode est plus rapide et plus précise.", "L'eau bout à cent degrés Celsius au niveau de la mer.",
        "Elle a demandé si la base de données pouvait être restaurée à partir d'une sauvegarde.", "Les erreurs doivent être enregistrées dans un fichier journal pour une analyse ultérieure."],
 "de": ["Die Suchmaschine liefert für jede Anfrage die relevantesten Dokumente.", "Bitte starten Sie den Server neu, bevor Sie die neue Version installieren.",
        "Das Modell wurde mit einer großen Sammlung von Texten in mehreren Sprachen trainiert.", "Jeder Benutzer muss sein Passwort alle neunzig Tage ändern.",
        "Die Funktion erhält eine Liste von Zahlen und gibt deren Durchschnitt zurück.", "Gestern hat es den ganzen Tag geregnet, deshalb sind wir zu Hause geblieben.",
        "Das Unternehmen hat dieses Jahr drei neue Büros in Europa eröffnet.", "Wer die Dokumentation sorgfältig liest, spart viel Zeit.",
        "Die Besprechung beginnt um neun Uhr morgens.", "Unser System unterstützt mehr als vierzig Sprachen und mehrere Dateiformate.",
        "Die Kinder spielen im Park in der Nähe des Flusses.", "Um die Bibliothek zu installieren, führen Sie den unten gezeigten Befehl aus.",
        "Die Ergebnisse zeigen, dass die neue Methode schneller und genauer ist.", "Wasser kocht auf Meereshöhe bei hundert Grad Celsius.",
        "Sie fragte, ob die Datenbank aus einer Sicherung wiederhergestellt werden könne.", "Fehler müssen für die spätere Analyse in einer Protokolldatei festgehalten werden."],
 "pt": ["O mecanismo de busca devolve os documentos mais relevantes para cada consulta.", "Reinicie o servidor antes de instalar a nova versão.",
        "O modelo foi treinado com uma grande coleção de textos em vários idiomas.", "Cada usuário deve trocar a senha a cada noventa dias.",
        "A função recebe uma lista de números e devolve a média deles.", "Ontem choveu o dia todo, por isso ficamos em casa.",
        "A empresa abriu três novos escritórios na Europa este ano.", "Ler a documentação com atenção poupa muito tempo.",
        "A reunião começará às nove horas da manhã.", "Nosso sistema suporta mais de quarenta idiomas e vários formatos de arquivo.",
        "As crianças estão brincando no parque perto do rio.", "Para instalar a biblioteca, execute o comando mostrado abaixo.",
        "Os resultados mostram que o novo método é mais rápido e mais preciso.", "A água ferve a cem graus Celsius ao nível do mar.",
        "Ela perguntou se o banco de dados poderia ser restaurado a partir de um backup.", "Os erros devem ser registrados em um arquivo de log para análise posterior."],
}
#---SPLIT---
_PARALELO_MANO.update({
 "ru": ["Поисковая система возвращает наиболее релевантные документы для каждого запроса.", "Перезапустите сервер перед установкой новой версии.",
        "Модель была обучена на большой коллекции текстов на нескольких языках.", "Каждый пользователь должен менять пароль каждые девяносто дней.",
        "Функция принимает список чисел и возвращает их среднее значение.", "Вчера целый день шёл дождь, поэтому мы остались дома.",
        "В этом году компания открыла три новых офиса в Европе.", "Внимательное чтение документации экономит много времени.",
        "Совещание начнётся в девять часов утра.", "Наша система поддерживает более сорока языков и несколько форматов файлов.",
        "Дети играют в парке возле реки.", "Чтобы установить библиотеку, выполните команду, приведённую ниже.",
        "Результаты показывают, что новый метод быстрее и точнее.", "Вода кипит при ста градусах Цельсия на уровне моря.",
        "Она спросила, можно ли восстановить базу данных из резервной копии.", "Ошибки необходимо записывать в файл журнала для последующего анализа."],
 "zh": ["搜索引擎会为每个查询返回最相关的文档。", "请在安装新版本之前重新启动服务器。", "该模型是在多种语言的大量文本上训练的。", "每位用户必须每九十天更换一次密码。",
        "该函数接收一个数字列表并返回它们的平均值。", "昨天下了一整天的雨，所以我们待在家里。", "今年公司在欧洲新开了三个办事处。", "仔细阅读文档可以节省很多时间。",
        "会议将于上午九点开始。", "我们的系统支持四十多种语言和多种文件格式。", "孩子们正在河边的公园里玩耍。", "要安装该库，请运行下面显示的命令。",
        "结果表明，新方法更快、更准确。", "在海平面，水在一百摄氏度时沸腾。", "她问是否可以从备份中恢复数据库。", "错误必须记录在日志文件中，以便日后分析。"],
 "ja": ["検索エンジンは、各クエリに対して最も関連性の高い文書を返します。", "新しいバージョンをインストールする前に、サーバーを再起動してください。", "このモデルは、複数の言語による大量のテキストで訓練されました。",
        "すべてのユーザーは九十日ごとにパスワードを変更しなければなりません。", "この関数は数値のリストを受け取り、その平均を返します。", "昨日は一日中雨が降っていたので、私たちは家にいました。",
        "その会社は今年、ヨーロッパに三つの新しいオフィスを開きました。", "ドキュメントを丁寧に読むと、多くの時間を節約できます。", "会議は午前九時に始まります。",
        "私たちのシステムは、四十以上の言語と複数のファイル形式に対応しています。", "子どもたちは川の近くの公園で遊んでいます。", "ライブラリをインストールするには、以下のコマンドを実行してください。",
        "結果は、新しい方法のほうが速く、より正確であることを示しています。", "水は海面の高さで摂氏百度で沸騰します。", "彼女は、データベースをバックアップから復元できるかどうか尋ねました。",
        "エラーは、後で分析できるようにログファイルに記録する必要があります。"],
 "ko": ["검색 엔진은 각 질의에 대해 가장 관련성이 높은 문서를 반환합니다.", "새 버전을 설치하기 전에 서버를 다시 시작하십시오.", "이 모델은 여러 언어로 된 방대한 텍스트 모음으로 학습되었습니다.",
        "모든 사용자는 구십 일마다 비밀번호를 변경해야 합니다.", "이 함수는 숫자 목록을 받아 그 평균을 반환합니다.", "어제는 하루 종일 비가 와서 우리는 집에 있었습니다.",
        "그 회사는 올해 유럽에 새 사무실 세 곳을 열었습니다.", "문서를 꼼꼼히 읽으면 많은 시간을 절약할 수 있습니다.", "회의는 오전 아홉 시에 시작됩니다.",
        "저희 시스템은 마흔 개가 넘는 언어와 여러 파일 형식을 지원합니다.", "아이들이 강 근처 공원에서 놀고 있습니다.", "라이브러리를 설치하려면 아래에 표시된 명령을 실행하십시오.",
        "결과는 새로운 방법이 더 빠르고 더 정확하다는 것을 보여 줍니다.", "물은 해수면에서 섭씨 백 도에 끓습니다.", "그녀는 데이터베이스를 백업에서 복원할 수 있는지 물었습니다.",
        "오류는 나중에 분석할 수 있도록 로그 파일에 기록해야 합니다."],
 "ar": ["يعيد محرك البحث أكثر المستندات صلة بكل استعلام.", "يرجى إعادة تشغيل الخادم قبل تثبيت الإصدار الجديد.", "تم تدريب النموذج على مجموعة كبيرة من النصوص بعدة لغات.",
        "يجب على كل مستخدم تغيير كلمة المرور كل تسعين يومًا.", "تستقبل الدالة قائمة من الأرقام وتعيد متوسطها.", "أمطرت السماء طوال أمس، لذلك بقينا في المنزل.",
        "افتتحت الشركة ثلاثة مكاتب جديدة في أوروبا هذا العام.", "قراءة الوثائق بعناية توفر الكثير من الوقت.", "سيبدأ الاجتماع في الساعة التاسعة صباحًا.",
        "يدعم نظامنا أكثر من أربعين لغة وعدة تنسيقات للملفات.", "الأطفال يلعبون في الحديقة القريبة من النهر.", "لتثبيت المكتبة، شغّل الأمر الموضح أدناه.",
        "تُظهر النتائج أن الطريقة الجديدة أسرع وأكثر دقة.", "يغلي الماء عند مئة درجة مئوية عند مستوى سطح البحر.", "سألت عما إذا كان بالإمكان استعادة قاعدة البيانات من نسخة احتياطية.",
        "يجب تسجيل الأخطاء في ملف سجل لتحليلها لاحقًا."],
 "hi": ["खोज इंजन हर क्वेरी के लिए सबसे प्रासंगिक दस्तावेज़ लौटाता है।", "नया संस्करण इंस्टॉल करने से पहले कृपया सर्वर को पुनः आरंभ करें।", "इस मॉडल को कई भाषाओं के पाठों के एक बड़े संग्रह पर प्रशिक्षित किया गया था।",
        "हर उपयोगकर्ता को हर नब्बे दिन में अपना पासवर्ड बदलना होगा।", "यह फ़ंक्शन संख्याओं की एक सूची लेता है और उनका औसत लौटाता है।", "कल पूरे दिन बारिश हुई, इसलिए हम घर पर ही रहे।",
        "कंपनी ने इस साल यूरोप में तीन नए कार्यालय खोले।", "दस्तावेज़ीकरण को ध्यान से पढ़ने से बहुत समय बचता है।", "बैठक सुबह नौ बजे शुरू होगी।",
        "हमारा सिस्टम चालीस से अधिक भाषाओं और कई फ़ाइल प्रारूपों का समर्थन करता है।", "बच्चे नदी के पास वाले पार्क में खेल रहे हैं।", "लाइब्रेरी इंस्टॉल करने के लिए नीचे दिखाया गया कमांड चलाएँ।",
        "परिणाम दिखाते हैं कि नई विधि अधिक तेज़ और अधिक सटीक है।", "समुद्र तल पर पानी सौ डिग्री सेल्सियस पर उबलता है।", "उसने पूछा कि क्या डेटाबेस को बैकअप से बहाल किया जा सकता है।",
        "बाद में विश्लेषण के लिए त्रुटियों को लॉग फ़ाइल में दर्ज किया जाना चाहिए।"],
 "tr": ["Arama motoru her sorgu için en alakalı belgeleri döndürür.", "Yeni sürümü yüklemeden önce lütfen sunucuyu yeniden başlatın.", "Model, birçok dilde yazılmış büyük bir metin koleksiyonuyla eğitildi.",
        "Her kullanıcı parolasını doksan günde bir değiştirmelidir.", "İşlev bir sayı listesi alır ve bunların ortalamasını döndürür.", "Dün bütün gün yağmur yağdı, bu yüzden evde kaldık.",
        "Şirket bu yıl Avrupa'da üç yeni ofis açtı.", "Belgeleri dikkatle okumak çok zaman kazandırır.", "Toplantı sabah saat dokuzda başlayacak.",
        "Sistemimiz kırktan fazla dili ve birçok dosya biçimini destekliyor.", "Çocuklar nehrin yakınındaki parkta oynuyor.", "Kitaplığı yüklemek için aşağıda gösterilen komutu çalıştırın.",
        "Sonuçlar, yeni yöntemin daha hızlı ve daha doğru olduğunu gösteriyor.", "Su, deniz seviyesinde yüz santigrat derecede kaynar.", "Veritabanının bir yedekten geri yüklenip yüklenemeyeceğini sordu.",
        "Hatalar, daha sonra analiz edilebilmesi için bir günlük dosyasına kaydedilmelidir."],
})
'''

PARALELO_LOADER = '''
FLORES_CODES = {"en": "eng_Latn", "es": "spa_Latn", "fr": "fra_Latn", "de": "deu_Latn", "pt": "por_Latn", "ru": "rus_Cyrl", "zh": "zho_Hans",
                "ja": "jpn_Jpan", "ko": "kor_Hang", "ar": "arb_Arab", "hi": "hin_Deva", "tr": "tur_Latn"}

def carga_paralelo(fast_dev: bool = True, langs=None) -> dict:
    """Frases paralelas. Cadena: FLORES+ (HF, puede pedir aceptar términos y token) -> opus-100 en-es -> mini-conjunto a mano.
    Devuelve {"langs": {lang: [frases alineadas]}, "source": "flores+"|"opus-100"|"mano", "n": int}."""
    langs = langs or list(FLORES_CODES)
    n = 100 if fast_dev else 997
    if hay_red("https://huggingface.co"):
        try:
            from datasets import load_dataset
            out = {l: [ex["text"] for ex in load_dataset("openlanguagedata/flores_plus", FLORES_CODES[l], split="devtest")][:n] for l in langs}
            return {"langs": out, "source": "flores+", "n": len(out["en"])}
        except Exception as e:
            print("   (FLORES+ no disponible:", type(e).__name__, "-> intento opus-100 en-es)")
        try:
            from datasets import load_dataset
            ds = load_dataset("Helsinki-NLP/opus-100", "en-es", split="test")
            tr = [ex["translation"] for ex in ds][:n]
            return {"langs": {"en": [t["en"] for t in tr], "es": [t["es"] for t in tr]}, "source": "opus-100", "n": len(tr)}
        except Exception as e:
            print("   (opus-100 no disponible:", type(e).__name__, ")")
    print("AVISO: usando el mini-conjunto paralelo escrito a mano (16 frases). Para cifras fiables usa FLORES+ con acceso a HF.")
    out = {l: _PARALELO_MANO[l] for l in langs if l in _PARALELO_MANO}
    return {"langs": out, "source": "mano", "n": len(out["en"])}
'''

def pip_cell(extra: str = "") -> str:
    # Sin -U: en Colab, actualizar solo `tokenizers` puede dejarlo fuera del rango que exige el `transformers`
    # preinstalado (ImportError al importar transformers en 04/05). Las versiones de Colab bastan.
    return f'!pip install -q tokenizers sentencepiece tiktoken datasets matplotlib seaborn scikit-learn {extra}'.strip()


def cells(code: str):
    """Divide un bloque en celdas por el marcador #---SPLIT---."""
    return [c.strip("\n") for c in code.split("#---SPLIT---\n")]


# ---------------------------------------------------------------------------------
# Módulo 05: banco de pruebas "tokenizer + modelo pequeño" (celdas compartidas lección/proyecto)
# ---------------------------------------------------------------------------------
M05_BASE = r'''
import torch, torch.nn as nn, torch.nn.functional as F
from tokenizers import Tokenizer, models, pre_tokenizers, trainers, decoders, Regex
from tokenizers.pre_tokenizers import ByteLevel
from collections import Counter

PAT_GPT2 = r"""'(?:[sdmt]|ll|ve|re)| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""

def bytes_a_unicode() -> dict:
    """Tabla de GPT-2: byte 0-255 -> carácter imprimible (así se escriben los tokens byte-level en los vocabularios HF)."""
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(range(ord("®"), ord("ÿ") + 1))
    cs, n = bs[:], 0
    for b in range(256):
        if b not in bs: bs.append(b); cs.append(256 + n); n += 1
    return dict(zip(bs, map(chr, cs)))
B2U = bytes_a_unicode(); U2B = {v: k for k, v in B2U.items()}
def token_a_bytes(t: str) -> bytes: return bytes(U2B[ch] for ch in t if ch in U2B)
def token_a_texto(t: str) -> str: return token_a_bytes(t).decode("utf-8", "replace")
BYTES_INVALIDOS = list(range(0xF5, 0x100))          # estos bytes NUNCA aparecen en UTF-8 válido: sus tokens son "no usados" de referencia
'''

M05_MINI = r'''
class _Bloque(nn.Module):
    def __init__(s, d, h):
        super().__init__(); s.ln1 = nn.LayerNorm(d); s.att = nn.MultiheadAttention(d, h, batch_first=True); s.ln2 = nn.LayerNorm(d)
        s.mlp = nn.Sequential(nn.Linear(d, 4 * d), nn.GELU(), nn.Linear(4 * d, d))
    def forward(s, x, m):
        a = s.ln1(x); x = x + s.att(a, a, a, attn_mask=m, need_weights=False)[0]; return x + s.mlp(s.ln2(x))

class MiniGPT(nn.Module):
    """GPT diminuto con embeddings ATADOS (como GPT-2): la misma matriz sirve de entrada y de salida."""
    def __init__(s, V, d=64, L=2, h=4, ctx=64):
        super().__init__(); s.emb = nn.Embedding(V, d); s.pos = nn.Embedding(ctx, d); s.ctx = ctx
        s.blocks = nn.ModuleList([_Bloque(d, h) for _ in range(L)]); s.ln = nn.LayerNorm(d); nn.init.normal_(s.emb.weight, std=0.02)
    def forward(s, x):
        T = x.shape[1]; m = torch.triu(torch.ones(T, T, dtype=torch.bool), 1); h = s.emb(x) + s.pos(torch.arange(T))
        for b in s.blocks: h = b(h, m)
        return s.ln(h) @ s.emb.weight.T

SILABAS = ["Mag", "ika", "Gold", "Troll", "Stream", "Bot", "Nitro", "Fan", "Redd", "Pixel", "Quan", "Zed", "Moon", "Karp", "Sol"]
def nombres_intrusos(n: int = 40, semilla: int = SEED) -> list:
    r = random.Random(semilla); return sorted({" " + "".join(r.choice(SILABAS) for _ in range(3)) for _ in range(n * 2)})[:n]

def banco_mini(docs, vocab_size: int = 2000, pasos: int = 500, semilla: int = SEED) -> dict:
    """Banco de pruebas reproducible del fenómeno 'glitch token':
    - el TOKENIZER se entrena con el corpus + un 'hilo de nombres de usuario' (los INTRUSOS, muy repetidos)
    - el MODELO se entrena SOLO con el corpus (nunca ve a los intrusos)  =>  los intrusos son tokens sub-entrenados.
    Devuelve un 'bundle' con la misma interfaz que usaremos para GPT-2 real."""
    torch.manual_seed(semilla); intr = nombres_intrusos()
    textos = [d["text"] for d in docs]
    hilo = [f"u/{n.strip()} posted: {n} {n} {n}\n" * 3 for n in intr for _ in range(120)]
    tk = Tokenizer(models.BPE())
    tk.pre_tokenizer = pre_tokenizers.Sequence([pre_tokenizers.Split(Regex(PAT_GPT2), behavior="isolated"), ByteLevel(add_prefix_space=False, use_regex=False)])
    tk.decoder = decoders.ByteLevel()
    tk.train_from_iterator(textos + hilo, trainers.BpeTrainer(vocab_size=vocab_size, initial_alphabet=ByteLevel.alphabet(), special_tokens=["<|endoftext|>"]))
    V = tk.get_vocab_size(); ids = []
    for t in textos: ids += tk.encode(t).ids + [0]
    ids = torch.tensor(ids); cnt = Counter(ids.tolist())
    model = MiniGPT(V); opt = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=0.0); B, T = 32, 64
    snaps = {}; sin_usar = [i for i in range(V) if cnt[i] == 0]
    for paso in range(pasos + 1):
        if paso % 100 == 0: snaps[paso] = model.emb.weight.detach().numpy().copy()
        if paso == pasos: break
        ix = torch.randint(0, len(ids) - T - 1, (B,)); x = torch.stack([ids[i:i + T] for i in ix]); y = torch.stack([ids[i + 1:i + T + 1] for i in ix])
        loss = F.cross_entropy(model(x).reshape(-1, V), y.reshape(-1)); opt.zero_grad(); loss.backward(); opt.step()
    model.eval()
    vocab = tk.get_vocab(); inv = {i: t for t, i in vocab.items()}
    intr_ids = sorted({i for n in intr for i in tk.encode(n).ids if cnt[i] == 0})
    def logits(x):
        with torch.no_grad(): return model(torch.as_tensor(x))
    return {"nombre": f"MiniGPT (tokenizer {V} con intrusos; modelo sin intrusos)", "E": model.emb.weight.detach().numpy().copy(), "E_out": model.emb.weight.detach().numpy().copy(), "tied": True,
            "tokens": [token_a_bytes(inv[i]) if inv[i] != "<|endoftext|>" else b"<|endoftext|>" for i in range(V)], "encode": lambda s: tk.encode(s).ids,
            "decode": lambda ids_: tk.decode(list(ids_)), "logits": logits, "tok": tk, "ctx": model.ctx, "frecuencias": cnt, "intrusos": intr_ids, "snaps": snaps,
            "ids_entrenamiento": ids, "loss_final": float(loss), "modelo": model}
'''

M05_HF = r'''
def bundle_hf(model, tok, nombre: str) -> dict:
    """Envuelve un modelo causal de HF (p. ej. GPT-2) con la MISMA interfaz que banco_mini. tok: AutoTokenizer byte-level."""
    E = model.get_input_embeddings().weight.detach().cpu().numpy(); Eo = model.get_output_embeddings().weight.detach().cpu().numpy()
    V = E.shape[0]; vocab = tok.convert_ids_to_tokens(list(range(V)))
    def logits(x):
        with torch.no_grad(): return model(torch.as_tensor(x)).logits
    return {"nombre": nombre, "E": E, "E_out": Eo, "tied": model.get_input_embeddings().weight is model.get_output_embeddings().weight,
            "tokens": [token_a_bytes(t) if t else b"" for t in vocab], "encode": lambda s: tok.encode(s), "decode": lambda ids_: tok.decode(list(ids_)),
            "logits": logits, "tok": tok, "ctx": getattr(model.config, "n_positions", 1024), "frecuencias": None, "intrusos": None, "snaps": None, "modelo": model}

def cargar_banco(docs, fast_dev: bool = True) -> dict:
    """Cadena: GPT-2 real de HF (si hay red y fast_dev=False o se pide) -> MiniGPT local con intrusos (siempre disponible)."""
    if not fast_dev and hay_red("https://huggingface.co"):
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            m = AutoModelForCausalLM.from_pretrained("gpt2").eval(); t = AutoTokenizer.from_pretrained("gpt2")
            print("Usando GPT-2 real (124M) de Hugging Face."); return bundle_hf(m, t, "GPT-2 (124M)")
        except Exception as e:
            print("   (GPT-2 no disponible:", type(e).__name__, ") -> MiniGPT local")
    print("Usando el banco MiniGPT local (tokenizer con 'intrusos' + modelo que nunca los ve). Entrenando ~1-2 min en CPU...")
    return banco_mini(docs, vocab_size=2000, pasos=500)
'''

M05_IND = r'''
def ids_referencia(bundle) -> list:
    """Ids de los tokens de bytes 0xF5-0xFF (jamás aparecen en UTF-8 válido): referencia de 'token no usado' (Land & Bartolo 2024)."""
    pos = {b: i for i, b in enumerate(bundle["tokens"]) if len(b) == 1}
    return [pos[bytes([b])] for b in BYTES_INVALIDOS if bytes([b]) in pos]

def ind_coseno(bundle) -> np.ndarray:
    """Distancia coseno entre la fila de salida de cada token y la media de los no-usados (MENOR distancia = más sospechoso)."""
    E = bundle["E_out"]; ref = E[ids_referencia(bundle)].mean(0)
    return 1 - (E @ ref) / (np.linalg.norm(E, axis=1) * np.linalg.norm(ref) + 1e-12)

def ind_norma(bundle) -> np.ndarray:
    """Norma L2 de la fila de ENTRADA (con embeddings no atados, las filas nunca vistas se quedan en su valor inicial o decaen por weight decay)."""
    return np.linalg.norm(bundle["E"], axis=1)

def max_prob_contexto(bundle, n_ctx: int = 200, largo: int = 48, semilla: int = SEED) -> np.ndarray:
    """Verificación por comportamiento: máxima probabilidad que el modelo asigna a cada token sobre n_ctx contextos reales.
    Un token que casi nunca se predice (max_p << el de tokens normales) es candidato confirmado."""
    ids = bundle.get("ids_entrenamiento")
    if ids is None: ids = torch.tensor(bundle["encode"](" ".join(d["text"] for d in docs[:60])))
    r = random.Random(semilla); mp = None
    for _ in range(0, n_ctx, 50):
        starts = [r.randrange(0, len(ids) - largo - 1) for _ in range(50)]
        P = F.softmax(bundle["logits"](torch.stack([ids[s:s + largo] for s in starts])), -1).amax(dim=(0, 1)).numpy()
        mp = P if mp is None else np.maximum(mp, P)
    return mp
'''
