# Week 4 — provenance audit трёх оставшихся вопросов

**Дата:** 2026-08-08
**Режим:** только верификация. **Manuscript и scripts не изменялись.**
**Frozen artifacts, thresholds, checkpoints, datasets, evaluation definitions:** не затрагивались. Экспериментов не запускалось.

---

## 1. Проверенные claims

| # | Claim | Точное место | Источник | Что источник устанавливает | Формулировка сильнее источника? | Действие |
|---|---|---|---|---|---|---|
| **P1** | «v0.6: GRCh37-only, **self-reported ≤50%** genome-wide SV coverage with an easier-SV bias» | §3, L90 | README релиза NIST_SV_v0.6, дословно: *«it likely only includes 50% or less of the total SVs in the genome, and is likely biased towards easier SVs»* | Что документация релиза **сама заявляет** такую оценку | **Нет.** «self-reported» корректно атрибутирует. Хедж «likely» опущен, но «self-reported» его функционально замещает | **KEEP** |
| **P2** | «GRCh37-only/**known ≤50% coverage** with an easier-SV bias» | §15.10, L508 | тот же README | То же | **Да.** README пишет «likely only includes 50% or less»; здесь — «known», то есть установленный факт. Утрачены и хедж, и атрибуция | **REWRITE** |
| **P3** | «v0.6's **easier-SV-biased** truth set» | §13, L428 | тот же README («likely biased towards easier SVs») | Заявление документации | Пограничное: подано как свойство набора, а не как заявление документации. Но соседнее предложение помечает всё рассуждение как «plausibly … a hypothesis, not a demonstrated mechanism» | **KEEP** |
| **P4** | «(a) v0.6's **own** easier-SV bias…» | §15.10, L510 | тот же README | То же | **Нет.** Слово «own» прямо указывает на самозаявление | **KEEP** |
| **P5** | DELLY как SV-caller | §3 | Rausch 2012, PMID 22962449 | DELLY обнаруживает SV через paired-end + split-read | Нет — claim у́же источника | **KEEP** |
| **P6** | LUMPY как SV-caller | §3 | Layer 2014, PMID 24970577 | LUMPY — вероятностная рамка обнаружения SV | Нет | **KEEP** |
| **P7** | Sniffles как long-read caller | §3 | Sedlazeck 2018, PMID 29713083 | Работа вводит NGMLR (выравниватель) и Sniffles (SV-caller) для long reads | Нет — claim у́же: используется только Sniffles, NGMLR не заявляется | **KEEP** |
| **P8** | `1000 Genomes phase-3 integrated SV map [sudmant2015sv]` | §3 | Sudmant 2015, PMID 26432246 | Название и содержание ресурса (2 504 генома) | Нет | **KEEP** |
| **P9** | `byrska-bishop2022` — порядок авторов | библиография | PubMed 36055201 | 21 автор, Evani US второй, Abel HJ пятый | Соответствует | **KEEP** |
| **P10** | `zook2020giabsv` — метаданные | библиография | PubMed 32541955 | *Nat Biotechnol* 2020;**38(11):1347-1355**, 48 авторов | Запись **неполна**: нет тома, выпуска, страниц, PMID; помечена «Full author list not yet confirmed», хотя список верифицирован | **CITE** (дополнить) |
| **P11** | Generated header: «§3 Related Work — bracketed `[ref]` tags are placeholders pending a literature pass» | `merge_manuscript.py`, стр. 54-56 | — | — | Утверждение **ложно**: в теле §3 не осталось ни одного `[ref]` | **REWRITE** (в генераторе) |
| **P12** | Generated header: «§1 Abstract — deliberately a structured skeleton, to be written last» | `merge_manuscript.py`, стр. 51-53 | — | — | Утверждение **ложно**: Abstract написан полностью (3 611 знаков связной прозы, маркер `[Placeholder` отсутствует) | **REWRITE** (в генераторе) |

---

## 2. Только реальные проблемы

Три. Остальные девять проверенных claims корректны и **не требуют правки**.

### Проблема 1 — §15.10 сильнее источника (P2)

Единственное место, где формулировка превышает то, что говорит документация.

- §3 пишет **«self-reported ≤50%»** — атрибутировано.
- §15.10 пишет **«known ≤50% coverage»** — подано как установленный факт.

README хеджирует: «it **likely** only includes 50% or less». Слово «known» отбрасывает и хедж, и указание на источник. Это тот же класс ошибки, что и уже исправленный overclaim про PanGenie в D8.

### Проблема 2 — generated header содержит два ложных утверждения (P11, P12)

Заголовок в `merge_manuscript.py` утверждает, что (а) `[ref]` в §3 — плейсхолдеры и (б) Abstract — скелет. Оба утверждения были верны при написании генератора и стали ложными после последующих правок. Это метаданные генерируемого артефакта, не научное содержание.

### Проблема 3 — библиографическая запись `zook2020giabsv` неполна (P10)

Том, выпуск, страницы и PMID верифицированы в предыдущем проходе, но в запись не перенесены; пометка «Full author list not yet confirmed» устарела.

---

## 3. Минимальные proposed diffs (не применены)

**D-1 — §15.10 (`discussion_limitations_conclusion_v1_draft.md`)**

```
- (Draft/less field-validated vs. GRCh37-only/known ≤50% coverage with an easier-SV bias)
+ (Draft/less field-validated vs. GRCh37-only, with the release documentation reporting ≤50% genome-wide SV coverage and a bias towards easier SVs)
```
Приводит §15.10 в соответствие с §3 и с источником. Число не меняется.

**D-2 — `merge_manuscript.py`, стр. 51-56**

```
- - **§1 Abstract** — deliberately a structured skeleton, to be written last so
-   it summarises the finished paper rather than anticipating it.
- - **§3 Related Work** — structural claims are final; bracketed `[ref]` tags are
-   placeholders pending a literature pass and must not be read as verified
-   citations.
+ - **§3 Related Work** — no `[ref]` placeholder remains; `[software-ref]` (pbsv)
+   and `[giab-v5.0q-release]` mark sources that are software and a data release
+   rather than articles.
```
Затрагивает только текст заголовка. **Проверка перед применением:** блок `HEADER` конкатенируется перед §1 и не пересекается с содержимым драфтов — правка не может изменить контент. Подтвердить после применения: §15.12 = 57/57, 14/14 замороженных значений, SHA-256 frozen report без изменений.

**D-3 — библиография (`intro_related_work_v1_draft.md`)**

```
- - **[zook2020giabsv]** Zook JM, et al. A robust benchmark … *Nature Biotechnology.* 2020. doi:10.1038/s41587-020-0538-8. *(Full author list not yet confirmed.)*
+ - **[zook2020giabsv]** Zook JM, Hansen NF, Olson ND, Chapman L, Mullikin JC, Xiao C, Sherry S, Koren S,
+   Phillippy AM, Boutros PC, Sahraeian SME, Huang V, Rouette A, Alexander N, Mason CE, Hajirasouliha I,
+   Ricketts C, Lee J, Tearle R, Fiddes IT, Martinez Barrio A, Wala J, Carroll A, Ghaffari N, Rodriguez OL,
+   Bashir A, Jackman S, Farrell JJ, Wenger AM, Alkan C, Soylev A, Schatz MC, Garg S, Church G, Marschall T,
+   Chen K, Fan X, English AC, Rosenfeld JA, Zhou W, Mills RE, Sage JM, Davis JR, Kaiser MD, Oliver JS,
+   Catalano AP, Chaisson MJP, Spies N, Sedlazeck FJ, Salit M. A robust benchmark for detection of germline
+   large deletions and insertions. *Nature Biotechnology.* 2020;38(11):1347-1355.
+   doi:10.1038/s41587-020-0538-8. PMID: 32541955
```
Все данные из проверенной записи PubMed. По памяти ничего не восстановлено.

---

## 4. UNRESOLVED

**Ссылка на релиз v0.6.** Провенанс оказался полнее, чем предполагалось. В `manta_poc/EXTERNAL_TRUTH_SOURCE_DECISION.md` зафиксированы:

- URL: `https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release/AshkenazimTrio/HG002_NA24385_son/NIST_SV_v0.6/`
- версия: `NIST_SV_v0.6` (в самом пути)
- файл: `HG002_SVs_Tier1_v0.6.vcf.gz`, 25 738 211 байт
- MD5: `78bceed7edda5c4ae373f5e4c31f72cd` — **вычислен нами**, NIST для этого релиза checksums не публиковал
- дословная цитата README

**Чего нет:** даты обращения. Она не зафиксирована ни в одном проектном документе. Дата файла решения (2026-08-04) — это дата решения, а не дата загрузки; повторная загрузка на кластер шла позже (task #30). Вывести дату можно только предположением.

**Вывод:** устойчивый идентификатор существует (URL + версия + имя файла + размер + наш MD5) и он воспроизводим. Не хватает единственного элемента — даты обращения, требуемой собственным правилом §3 для `[giab-v5.0q-release]`.

**Рекомендация:** формулировка в §3 уже помечает число как `self-reported`, то есть как заявление документации релиза, а не как результат. Численная оценка **нужна аргументу**: §15.10 опирается на неполноту v0.6 в чтении (a). Поэтому удалять число не следует. Оставить как provenance note до тех пор, пока дата обращения не будет зафиксирована; выдумывать её нельзя.

---

## 5. Проверка по принципам Оруэлла

| Принцип | Результат | Замечание |
|---|---|---|
| Не заявлять честность вместо фактов | **PASS** | Деклараций «honest», «genuinely», «plainly» в §3 не осталось |
| Не использовать оценку там, где хватает измерения | **PASS** после последней правки | «standard community reference» → «widely used»; «methodologically closer to a ground truth» → описание различия построения |
| Не спорить с воображаемым читателем | **PASS** | Конструкций вида «It would be a mistake to read…» в §3 нет |
| Не повторять один результат как аргумент | **PASS** | Удаление абзаца о калибровке убрало дублирование §15.7 |
| Не скрывать неопределённость за сильными словами | **FAIL — один случай** | §15.10: «known ≤50%» вместо «likely / self-reported» (P2) |
| Не делать причинный вывод из описательного результата | **PASS** | §13 и §15.10 помечают объяснение как «plausibly … a hypothesis, not a demonstrated mechanism»; AFR-разрыв помечен как интерпретация |
| Не использовать термин сильнее, чем позволяет evidence tier | **PASS** | Уровни не смешиваются; сравнения между tiers сопровождаются оговоркой о несопоставимости |

---

## 6. PASS / FAIL

| Область | Вердикт | Обоснование |
|---|---|---|
| **Scientific content** | **PASS** | Ни одно научное утверждение не затронуто. 57/57 ячеек §15.12 и 14/14 замороженных значений подтверждены в предыдущем проходе; frozen report без изменений |
| **Citation integrity** | **PASS с одним дополнением** | Все шесть проверенных ключей соответствуют claims, которые они поддерживают, и ни один claim не шире источника. Единственное — запись `zook2020giabsv` неполна (D-3) |
| **Provenance** | **FAIL по одному пункту** | §15.10 «known ≤50%» подано сильнее, чем говорит источник (D-1). Ссылка на релиз v0.6 остаётся UNRESOLVED из-за отсутствующей даты обращения |
| **Orwell-style technical prose** | **FAIL по одному пункту** | Тот же случай: «known» скрывает хедж «likely» источника. Остальные шесть принципов соблюдены |

**Итог: три проблемы, все с готовыми минимальными диффами. Ничего не изменено в этом проходе.**

---

## 7. Применение D-1 – D-3 (запись после правок)

**Дата применения:** 2026-08-08. Применены только три подготовленных диффа. Других правок не вносилось.

### Точный дифф

**D-1 — §15.10** (`discussion_limitations_conclusion_v1_draft.md`) — *provenance correction*

```
- (Draft/less field-validated vs. GRCh37-only/known ≤50% coverage with an easier-SV bias)
+ (Draft/less field-validated vs. GRCh37-only, with the release documentation reporting
+  ≤50% genome-wide SV coverage and a bias towards easier SVs)
```
Восстановлена атрибуция источнику. Число `≤50%` не изменено, новый источник не добавлен. Формулировка §3 (`self-reported ≤50%`) не затронута.

**D-2 — `merge_manuscript.py`, блок `HEADER`** — *generated-metadata correction*

```
- - **§1 Abstract** — deliberately a structured skeleton, to be written last so
-   it summarises the finished paper rather than anticipating it.
- - **§3 Related Work** — structural claims are final; bracketed `[ref]` tags are
-   placeholders pending a literature pass and must not be read as verified
-   citations.
+ - **§3 Related Work** — no `[ref]` placeholder remains; `[software-ref]` (pbsv)
+   and `[giab-v5.0q-release]` mark sources that are software and a data release
+   rather than articles.
```
Изменён только строковый литерал `HEADER`. Логика `strip_preamble`, `SECTIONS`, `main()` и порядок конкатенации не затронуты.

**D-3 — библиография** (`intro_related_work_v1_draft.md`) — *bibliographic completion*

Запись `[zook2020giabsv]` заменена полной верифицированной: 48 авторов в порядке PubMed, *Nature Biotechnology* 2020;**38(11):1347-1355**, doi:10.1038/s41587-020-0538-8, **PMID: 32541955**. Пометка «Full author list not yet confirmed» снята. Все данные — из проверенной записи PubMed 32541955; по памяти ничего не восстанавливалось.

### Классификация изменённых строк

| Файл | Строк | Класс |
|---|---|---|
| `discussion_limitations_conclusion_v1_draft.md` | 1 заменена | provenance / attribution |
| `merge_manuscript.py` | 5 удалены, 3 добавлены (только внутри строкового литерала `HEADER`) | generated metadata |
| `intro_related_work_v1_draft.md` | 1 заменена на 8 (библиографическая запись) | bibliographic metadata |
| `PAIR_SV_v1_manuscript.md` | перегенерирован | derived artifact |

**Ни одна изменённая строка не относится к научному содержанию, числам, tiers, порогам или определениям оценки.**

### Результаты обязательных проверок

| Проверка | Результат |
|---|---|
| Canonical manuscript перегенерирован только через `merge_manuscript.py` | да, 625 строк, sha256 `2d459baa529e2cb6fd486263fe17e802c8a43c055252a4af50dad8f7096c3557` |
| Frozen report SHA-256 | **не изменён** (`84f571b6…b3d1`) |
| §15.12 | **57/57 ячеек, 0 расхождений** |
| 14 замороженных значений | **14/14 присутствуют и совпадают** |
| Старая формулировка `known ≤50%` | **отсутствует** |
| Оба устаревших HEADER-утверждения | **отсутствуют** |
| `[ref]` в теле §3 | 1 вхождение — предложение «No unresolved `[ref]` placeholder remains in this section». **Не плейсхолдер**, а констатация их отсутствия |
| Evaluation artifacts, thresholds, checkpoints, datasets, definitions | **не изменены**; `cohort_evaluate.py`, `extract_cohort_numbers.py`, `build_figures.py`, оба манифеста — checksums и mtime до начала прохода |

### Замечание к проверке `git diff`

`git diff` по этим файлам вернул пустой вывод. Причина установлена: файлы `paper/*.md` и `paper/merge_manuscript.py` **не отслеживаются git** (`git status` показывает `??`), поэтому `git diff` для них принципиально ничего не выводит. Это ограничение самой проверки, а не признак того, что правки не применились. Факт изменения подтверждён независимо — сравнением SHA-256 до и после (см. таблицу классификации выше). Дифф приведён выше по точным строкам замены.

### Дата обращения к README релиза v0.6

**Остаётся неизвестной и не была выдумана.** В проектной провенансной записи зафиксированы URL, версия `NIST_SV_v0.6`, имя файла, размер 25 738 211 байт, самостоятельно вычисленный MD5 `78bceed7edda5c4ae373f5e4c31f72cd` и дословная цитата README. Даты загрузки нет ни в одном документе; дата файла решения (2026-08-04) — это дата решения, а не обращения к ресурсу. Ссылка на релиз v0.6 остаётся **UNRESOLVED** до тех пор, пока дата не будет зафиксирована из фактической записи.
