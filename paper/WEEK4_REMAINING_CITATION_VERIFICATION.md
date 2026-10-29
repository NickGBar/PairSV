# Week 4 — верификация пяти оставшихся вопросов §3

**Дата:** 2026-08-08
**Режим:** только верификация. **Ничего не изменено** — ни manuscript, ни source drafts, ни merge script, ни библиография.
**Frozen artifacts, thresholds, checkpoints, datasets, evaluation definitions:** не затрагивались.

---

## Пункт 1 — «standard community reference»

**Точная цитата:**
> «The Genome in a Bottle Consortium's HG002 truth sets — the mature, GRCh37-native NIST SV v0.6 [zook2020giabsv] and the newer, GRCh38-native, assembly-based v5.0q Draft release [giab-v5.0q-release] — **are the standard community reference for SV caller benchmarking via Truvari** [english2022truvari].»

**Что источники подтверждают.** [zook2020giabsv] описывает построение бенчмарка v0.6 и его назначение для оценки SV-callers. [english2022truvari] описывает Truvari как инструмент сравнения SV. Оба подтверждают существование и назначение ресурсов.

**Что источники не подтверждают.** Ни один не устанавливает, что эти наборы являются **стандартом сообщества**. Это утверждение о практике поля, а не о свойстве ресурса. Его нельзя подтвердить одной первичной публикацией; для него потребовалось бы обзорное или библиометрическое свидетельство, которого у нас нет.

**Тип claim:** interpretive (оценка распространённости), с оценочным словом «standard».

**Минимальная безопасная редакция.** Заменить оценку на проверяемое описание назначения — например: «are widely used reference truth sets for SV caller benchmarking; comparisons here use Truvari [english2022truvari]». Слово «standard» убирается, научное содержание не теряется: важно, что мы использовали именно эти наборы и именно этот инструмент, а не то, насколько они популярны.

---

## Пункт 2 — «methodologically closer to a ground truth»

**Точная цитата:**
> «This paper uses v5.0q as its primary external truth source specifically because it is GRCh38-native (…) and assembly-based (**methodologically closer to a ground truth than earlier read-support-consensus callsets**)»

**Что именно сравнивается.** Два способа построения truth set: (а) assembly-based — v5.0q получен dipcall по диплоидной сборке T2T-HG002-Q100-v1.1; (б) read-support-consensus — v0.6 построен как консенсус нескольких технологий и callers (описано в [zook2020giabsv]).

**Что источники подтверждают.** Различие в способе построения — фактическое и документировано в обоих источниках.

**Что источники не подтверждают.** Ни [zook2020giabsv], ни релиз v5.0q не утверждают, что assembly-based построение **ближе к истине**. Это ранжирование двух методологий по близости к ground truth — наша оценка. Более того, она находится в напряжении с тем, что статья говорит в других местах: §15.10 явно отказывается адъюдицировать между v5.0q и v0.6, а §13 фиксирует, что v5.0q даёт **самую высокую** specificity среди трёх измеренных уровней, то есть выглядит как выброс, а не как эталон.

**Тип claim:** interpretive. Оценочная характеристика, выданная за обоснование выбора.

**Минимальная безопасная редакция.** Изложить различие буквально, без ранжирования: «…and assembly-based, whereas v0.6 was built as a consensus of read-based callers». Причина выбора при этом сохраняется (GRCh38-native + иной способ построения), но исчезает непроверяемое утверждение о близости к истине. Это **усиливает** согласованность с §15.10.

---

## Пункт 3 — «1000 Genomes phase-3 integrated SV map»

**Точная цитата:**
> «Samplot-ML [belyeu2021samplot] classifies putative deletions … with genotype-class labels (0/0, 0/1, 1/1) drawn from the **1000 Genomes phase-3 integrated SV map** across many individuals.»

**Происхождение названия — установлено.** Первичная публикация ресурса:
Sudmant PH, Rausch T, Gardner EJ, Handsaker RE, Abyzov A, Huddleston J, Zhang Y, Ye K, et al.; 1000 Genomes Project Consortium. **An integrated map of structural variation in 2,504 human genomes.** *Nature.* 2015;526(7571):75-81. doi:10.1038/nature15394. PMID: 26432246. Формулировка в manuscript почти дословно воспроизводит название ресурса.

**Проверка соседней citation.** [belyeu2021samplot] подтверждает, что samplot-ML **использовал** этот ресурс как источник меток. Он **не** является публикацией самого ресурса. То есть соседняя ссылка покрывает утверждение «samplot-ML взял метки оттуда», но не покрывает сам ресурс, названный по имени.

**Что источники не подтверждают.** Ничего сверх этого; расхождений не найдено.

**Тип claim:** factual (описание чужого метода + именование ресурса).

**Минимальная безопасная редакция.** Либо добавить `[sudmant2015sv]` к названию ресурса, либо снять имя собственное и написать «from a 1000 Genomes phase-3 structural-variant callset», оставив [belyeu2021samplot]. Первое точнее; второе не требует новой ссылки. Обе безопасны.

---

## Пункт 4 — «≤50% genome-wide SV coverage»

Вопрос считается установленным: число происходит из README релиза v0.6. **Проверено дополнительно и подтверждено отрицательно:** полный текст [zook2020giabsv] (Nature Biotechnology 2020;38(11):1347-1355) **не содержит процента покрытия genome-wide SV**. Статья указывает, что регионы Tier 1 покрывают 2.51 Gbp, но не выражает это как долю SV в геноме. Приписывать число Zook нельзя — подтверждено.

**Провенанс числа** зафиксирован в собственном документе проекта `manta_poc/EXTERNAL_TRUTH_SOURCE_DECISION.md`, где README процитирован дословно: *«it likely only includes 50% or less of the total SVs in the genome, and is likely biased towards easier SVs»*.

**Как корректно сослаться в текущей системе библиографии.** В §3 уже существует прецедент для не-статейного источника: `[giab-v5.0q-release]`, помеченный как «NIST data release, not a peer-reviewed publication … must be cited with its version and access date». Формат существует и симметричен. Соответствующий ключ для v0.6 — например `[giab-v0.6-release]` — вписывается без изобретения новой схемы.

**Ограничение.** Точная версия и дата обращения README в проектных документах не зафиксированы; зафиксирована только дословная цитата и checksum самого VCF. Без версии/даты релизная ссылка будет неполной по собственному правилу §3.

**Тип claim:** factual (цитата из документации релиза), правильно помеченный словом «self-reported».

**Статус: UNRESOLVED.** Формат существует, но недостаёт метаданных релиза. Ничего не выдумано.

---

## Пункт 5 — полные библиографические данные

### `zook2020giabsv` — **найдено расхождение с текущей записью**

Проверено по PubMed:

> Zook JM, Hansen NF, Olson ND, Chapman L, Mullikin JC, Xiao C, Sherry S, Koren S, Phillippy AM, Boutros PC, Sahraeian SME, Huang V, Rouette A, Alexander N, Mason CE, Hajirasouliha I, Ricketts C, Lee J, Tearle R, Fiddes IT, Martinez Barrio A, Wala J, Carroll A, Ghaffari N, Rodriguez OL, Bashir A, Jackman S, Farrell JJ, Wenger AM, Alkan C, Soylev A, Schatz MC, Garg S, Church G, Marschall T, Chen K, Fan X, English AC, Rosenfeld JA, Zhou W, Mills RE, Sage JM, Davis JR, Kaiser MD, Oliver JS, Catalano AP, Chaisson MJP, Spies N, Sedlazeck FJ, Salit M. **A robust benchmark for detection of germline large deletions and insertions.** *Nature Biotechnology.* 2020;**38(11):1347-1355.** doi:10.1038/s41587-020-0538-8. **PMID: 32541955**

**Текущая запись в библиографии неполна:** «Zook JM, et al. … *Nature Biotechnology.* 2020. doi:… *(Full author list not yet confirmed.)*» — отсутствуют том, выпуск, страницы и PMID. Теперь все подтверждены. Соответствие ключа источнику — верное.

### `byrska-bishop2022` — подтверждено полностью

> Byrska-Bishop M, Evani US, Zhao X, Basile AO, Abel HJ, Regier AA, Corvelo A, Clarke WE, Musunuri R, Nagulapalli K, Fairley S, Runnels A, Winterkorn L, Lowy E, Flicek P, Germer S, Brand H, Hall IM, Talkowski ME, Narzisi G, Zody MC. **High-coverage whole-genome sequencing of the expanded 1000 Genomes Project cohort including 602 trios.** *Cell.* 2022;185(18):3426-3440.e19. doi:10.1016/j.cell.2022.08.004. PMID: 36055201

Текущая запись содержала «Byrska-Bishop M, Abel HJ, et al.» — **порядок авторов был неверен**: Abel HJ является пятым автором, а не вторым. Второй автор — Evani US. Соответствие ключа источнику верное; список авторов требует замены.

---

## Отдельно: не оставило ли удаление conformal prediction логический разрыв

**Оставило — и это самая существенная находка прохода.**

Текущий абзац целиком:

> «**Calibration and distribution shift.** PAIR-SV separates model fitting from deployment-threshold selection: the threshold is chosen by leave-one-person-out on held-out development people, targeting a fixed recall operating point (§12). This paper's finding — … — is offered as a cautionary data point for any pipeline that treats a POC-calibrated threshold as automatically valid on new data, rather than as evidence against calibration as a strategy per se (…).»

**Проблема.** Абзац находится в разделе **Related Work**, но после удаления сравнения с conformal prediction он **не содержит ни одной ссылки на чужую работу**. Он полностью описывает наш собственный метод (первое предложение) и наш собственный результат (второе). Подраздел Related Work, не относящийся ни к какой related work, — структурный разрыв, который рецензент заметит.

**Дополнительно:** содержание этого абзаца дублируется §15.7 «Calibration shift between curated candidates and real Manta candidates», где та же мысль изложена подробнее и на месте.

**Три варианта, по возрастанию вмешательства:**

1. **REMOVE** — удалить абзац из §3 целиком. Научное содержание не теряется: описание процедуры принадлежит §12, обсуждение переноса порога — §15.7. Наименьшее вмешательство и наиболее честное: у нас нет проверенной related work для этого места.
2. **CITE** — вернуть литературный якорь с проверенной ссылкой на person-level calibration / threshold transfer. Требует новой верификации и риска повторить ошибку «подгонки источника».
3. **KEEP** — оставить как есть. Не рекомендуется: раздел Related Work без related work.

**Рекомендация: вариант 1.** Он согласуется с принципом «если утверждение можно ослабить без потери научного содержания — ослабить».

---

## Сводная таблица

| # | Место | Тип | Решение | Обоснование |
|---|---|---|---|---|
| 1 | «standard community reference» | interpretive | **REWRITE** | «standard» не подтверждается источником; заменить на «widely used», содержание сохраняется |
| 2 | «methodologically closer to a ground truth» | interpretive | **REWRITE** | Ранжирование методологий — наша оценка; изложить различие построения буквально. Устраняет напряжение с §15.10 |
| 3 | «1000 Genomes phase-3 integrated SV map» | factual | **CITE** (или REWRITE) | Ресурс = Sudmant 2015, PMID 26432246, верифицирован. [belyeu2021samplot] его не покрывает. Альтернатива без новой ссылки — снять имя собственное |
| 4 | «≤50% genome-wide SV coverage» | factual | **UNRESOLVED** | Формат `[giab-v0.6-release]` существует по образцу v5.0q, но версия и дата обращения README не зафиксированы. Подтверждено, что Zook 2020 число не содержит |
| 5a | `zook2020giabsv` | factual | **CITE** (дополнить) | Полные метаданные верифицированы: 38(11):1347-1355, PMID 32541955, 48 авторов |
| 5b | `byrska-bishop2022` | factual | **CITE** (исправить) | Полный список верифицирован; **порядок авторов в текущей записи неверен** (Abel HJ — пятый, не второй) |
| 6 | Абзац «Calibration and distribution shift» в §3 | structural | **REMOVE** | После удаления conformal prediction не содержит related work; дублирует §15.7 |

**Оставить без изменений (KEEP):** все верифицированные ключи в тексте (`chen2016manta`, `rausch2012delly`, `layer2014lumpy`, `sedlazeck2018sniffles`, `nguyen2023hyenadna`, `english2022truvari`, `liu2021deepsvfilter`, `belyeu2021samplot`, `popic2023cue`, `xia2024csvfilter`, `ebert2021`, `ebler2022`); формулировку «self-reported» перед числом ≤50% (она корректно атрибутирует источник); `[software-ref]` для pbsv.

---

**Ничего не изменено.** Manuscript, source drafts, merge script, библиография и все вычислительные артефакты остались в состоянии до начала прохода.
