# Week 4 — литературная работа: закрытие U3 и верификация цитат

**Дата:** 2026-08-08
**Статус manuscript:** не изменялся в этом проходе. Все предложения ниже требуют подтверждения.
**Frozen artifacts:** не затрагивались. Evaluation не запускалась.

---

## 1. U3 закрыт — CSV-Filter прочитан

Единственный «наиболее вероятный источник неожиданности» из литературного аудита проверен по первоисточнику. **Неожиданности нет: утверждения §3 остаются в силе.**

**Xia Z, Xiang W, Wang Q, Li X, Li Y, Gao J, Tang T, Yang C, Cui Y.** CSV-Filter: a deep learning-based comprehensive structural variant filtering method for both short and long reads. *Bioinformatics.* 2024;40(9):btae539. doi:10.1093/bioinformatics/btae539.

| Признак | CSV-Filter | Отношение к PAIR-SV |
|---|---|---|
| Задача | Фильтрация SV-вызовов (true/false positive), не discovery и не genotyping | **Та же задача**, что и у PAIR-SV |
| Позитивы | Высокодостоверный callset GIAB для HG002 (4 199 делеций, 5 442 инсерции) | — |
| Негативы | **Синтетические**, генерируются по распределению Пуассона; сэмпл отбрасывается, если перекрывается более чем наполовину с соседним SV | Позитивы и негативы из **несвязанных локусов** |
| Обучающая выборка | **Только HG002** (PacBio HiFi), разбиение 80/20 внутри одного генома | — |
| Same-site matched supervision | **Нет** | Сужённое утверждение §3 не требует дальнейшего ослабления |
| Представление / модель | Полутоновые изображения 224×224 из CIGAR-строк; ResNet50(×2), self-supervised pre-training с VICReg | — |

**Два следствия.**

1. **Для §3.** Ни DeepSVFilter, ни CSV-Filter не используют same-site matched supervision. Единственная работа, где такие примеры возникают, — samplot-ML, и там это следствие формулировки задачи генотипирования. Сужённая формулировка §3, принятая после литературного аудита, оказывается точной и не нуждается в дальнейшем ослаблении.
2. **Для Narrative B.** CSV-Filter обучается и тестируется на **одном геноме** (HG002, разбиение 80/20 внутри него). Это третий пример односеномной зависимости в ближайшей смежной литературе — после DeepSVFilter (обучение на HG002) и общей практики валидации на HG002. Формулировать это следует осторожно: у CSV-Filter один геном используется для обучения и внутреннего тестирования, тогда как критика Narrative B касается односеномной **внешней валидации**. Это разные вещи, и смешивать их нельзя.

### Предлагаемая вставка в §3 (не применена)

> CSV-Filter [xia2024csvfilter] addresses the same filtering task for both short and long reads, encoding CIGAR strings as grayscale images and classifying them with a ResNet-50 pair pre-trained by self-supervision. Its positives are taken from the GIAB HG002 high-confidence callset and its negatives are generated synthetically from a length distribution, so positives and negatives again occupy unrelated loci; training and internal testing both use HG002.

Одно предложение, без оценочных слов, без утверждения о превосходстве и без переноса критики односеномной внешней валидации на работу, которая её не заявляла.

---

## 2. Верифицированные цитаты — 8

Каждая проверена по записи издателя или PubMed в этом или предыдущем проходе. **Ни одна не записана по памяти.**

| Ключ | Полная ссылка | Верифицировано по |
|---|---|---|
| `chen2016manta` | Chen X, Schulz-Trieglaff O, Shaw R, Barnes B, Schlesinger F, Källberg M, Cox AJ, Kruglyak S, Saunders CT. Manta: rapid detection of structural variants and indels for germline and cancer sequencing applications. *Bioinformatics.* 2016;32(8):1220-2. doi:10.1093/bioinformatics/btv710. PMID: 26647377 | PubMed |
| `english2022truvari` | English AC, Menon VK, Gibbs RA, Metcalf GA, Sedlazeck FJ. Truvari: refined structural variant comparison preserves allelic diversity. *Genome Biology.* 2022;23:271. doi:10.1186/s13059-022-02840-6. PMID: 36575487 | PubMed + издатель |
| `nguyen2023hyenadna` | Nguyen E, Poli M, Faizi M, Thomas A, Wornow M, Birch-Sykes C, Massaroli S, Patel A, Rabideau C, Bengio Y, Ermon S, Ré C, Baccus S. HyenaDNA: Long-Range Genomic Sequence Modeling at Single Nucleotide Resolution. *Advances in Neural Information Processing Systems 36* (NeurIPS 2023), pp. 43177-43201 | NeurIPS / OpenReview |
| `zook2020giabsv` | Zook JM, et al. A robust benchmark for detection of germline large deletions and insertions. *Nature Biotechnology.* 2020. doi:10.1038/s41587-020-0538-8 | Издатель — **полный список авторов в этом проходе не подтверждён** |
| `xia2024csvfilter` | Xia Z, Xiang W, Wang Q, Li X, Li Y, Gao J, Tang T, Yang C, Cui Y. CSV-Filter… *Bioinformatics.* 2024;40(9):btae539. doi:10.1093/bioinformatics/btae539 | Издатель |
| `liu2021deepsvfilter` | Liu Y, Huang Y, Wang G, Wang Y. A deep learning approach for filtering structural variants in short read sequencing data. *Briefings in Bioinformatics.* 2021;22(4):bbaa370. doi:10.1093/bib/bbaa370. PMID: 33378767 | PubMed + издатель |
| `belyeu2021samplot` | Belyeu JR, Chowdhury M, Brown J, Pedersen BS, Cormier MJ, Quinlan AR, Layer RM. Samplot: a platform for structural variant visual validation and automated filtering. *Genome Biology.* 2021;22:161. doi:10.1186/s13059-021-02380-5. PMID: 34034781 | PubMed + PMC |
| `popic2023cue` | Popic V, Rohlicek C, Cunial F, et al. Cue: a deep-learning framework for structural variant discovery and genotyping. *Nature Methods.* 2023;20:559-568. doi:10.1038/s41592-023-01799-x | Издатель |

---

## 3. Остаётся неразрешённым — 7 позиций

| Что | Тип источника | Примечание |
|---|---|---|
| DELLY | Первичная статья | Не проверена в этом проходе |
| LUMPY / smoove | Первичная статья (+ возможно отдельная ссылка на smoove как ПО) | Не проверена |
| Sniffles | Первичная статья | Не проверена |
| **pbsv** | **ПО, не статья** | Первичной публикации не найдено; цитировать как программное обеспечение |
| DeepVariant | Первичная статья | Не проверена; используется как аналогия pileup-изображений |
| **GIAB v5.0q Draft release** | **Релиз NIST, не рецензированная статья** | Цитировать как релиз с версией и датой обращения. От этого зависит формулировка §15.10 о Draft-статусе |
| PanGenie / HGSVC2 (`ebler2022`, `ebert2021`), 1000G NYGC (`byrska-bishop2022`) | Первичные статьи | Ключи присутствуют в тексте, но не развёрнуты в полные ссылки. **Приоритет: PanGenie напрямую поддерживает D8** |
| Литература по калибровке / conformal prediction | Обзор или репрезентативные работы | Не проверена |

Счётчик `[ref]` в manuscript остаётся **12** — плейсхолдеры не трогались.

---

## 4. Что предлагается сделать дальше

| Приоритет | Действие | Требует подтверждения |
|---|---|---|
| 1 | Вставить предложение о CSV-Filter в §3 (текст выше) | да |
| 2 | Заменить 8 верифицированных `[ref]` на ключи и добавить библиографию | да |
| 3 | Верифицировать PanGenie (`ebler2022`) и HGSVC2 (`ebert2021`) — они поддерживают D8, самое уязвимое место статьи | нет, это проверка |
| 4 | Оформить v5.0q и pbsv как не-статейные источники | да |

**Ничего не применено.** Manuscript, frozen artifacts и определения не изменялись.

---

## 5. Выполнено (обновление после применения)

**Порядок соблюдён: верификация → §3 → ref-ключи, тремя отдельными шагами.**

### Шаг 1 — PanGenie/HGSVC2 верифицированы, и это вскрыло overclaim в D8

Обе работы подтверждены по PubMed:

- **[ebler2022]** Ebler J, Ebert P, Clarke WE, Rausch T, Audano PA, Houwaart T, Mao Y, Korbel JO, Eichler EE, Zody MC, Dilthey AT, Marschall T. *Nature Genetics.* 2022;54(4):518-525. doi:10.1038/s41588-022-01043-w. PMID: 35410384
- **[ebert2021]** Ebert P, Audano PA, Zhu Q, Rodriguez-Martin B, Porubsky D, et al. *Science.* 2021;372(6537):eabf7117. doi:10.1126/science.abf7117. PMID: 33632895

**Найденная проблема.** Формулировка D8 в §15.9 приписывала PanGenie «documented accuracy that varies by locus, mappability, **panel composition and population representation**». Из четырёх свойств первоисточники подтверждают два: конкордантность генотипов ниже в повторяющихся (STR/VNTR) областях, чем в неповторяющихся (Ebler 2022, Fig. 3-4, Extended Data 3-8). **Зависимость точности от состава панели и от представленности популяций в проверенных источниках не документирована.**

Это был overclaim — в разделе ограничений, и именно в той части, на которую опирается интерпретация AFR-разрыва. Исправлено:

> **Было:** "PanGenie is a silver-standard resource with documented accuracy that varies by locus, mappability, panel composition and population representation (the AFR pattern in §16 is one visible consequence)…"
>
> **Стало:** "PanGenie genotypes short-read samples against a haplotype-resolved panel; the HGSVC2 panel used here comprises 64 haplotypes from 32 genomes spanning the 1000 Genomes superpopulations [ebert2021]. Its reported genotype concordance is lower in repetitive (STR/VNTR) regions than in non-repetitive ones [ebler2022]. We are not aware of a published characterisation of how its accuracy depends on the ancestry composition of the panel; the interpretation offered for the AFR pattern in §16 is ours and is not supported by a documented property of the genotyper. PanGenie is not a weak label set, but it is not GIAB-grade ground truth either."

Состав панели (64 гаплотипа / 32 генома, покрытие суперпопуляций 1000G) — проверяемый факт из Ebert 2021. Причинная атрибуция AFR-разрыва остаётся нашей интерпретацией, как и было помечено в §16.

### Шаг 2 — CSV-Filter добавлен в §3

Одно предложение, формулировка из раздела 1 без изменений.

### Шаг 3 — ref-ключи заменены, библиография добавлена

10 верифицированных ключей в тексте; раздел «Verified references» в конце §3.

**Учёт `[ref]`:** было 12. Осталось 6 вхождений строки, из которых **настоящих неразрешённых плейсхолдеров — 3**: DELLY, LUMPY/smoove, Sniffles. Остальные 3 — упоминания самой строки `[ref]` в служебных пометках (статус-блок, sourcing note, преамбула библиографии).

**Нестандартные источники оформлены отдельно:** `[giab-v5.0q-release]` (релиз NIST, не статья — от этого зависит §15.10), `[software-ref]` для pbsv (первичной публикации нет).

### Обнаружено, не исправлено — требует решения

**DeepVariant и литература по калибровке/conformal prediction упоминаются в §3 без маркера цитирования вообще.** То есть место, где нужна ссылка, ничем не помечено, и наборщик его не увидит. То же касается `byrska-bishop2022` — ключ есть, полной ссылки нет. Добавление маркеров — это правка §3, а не замена существующих ключей, поэтому не делал.

### Верификация после обоих шагов

| Проверка | Результат |
|---|---|
| Frozen report checksum | не изменён |
| Таблицы §15.12 | 57/57 ячеек, 0 расхождений |
| D3 и D8 | на месте; overclaim D8 удалён, исправленная формулировка присутствует |
| CSV-Filter в §3 | присутствует |
| 10 верифицированных ключей | все присутствуют |
