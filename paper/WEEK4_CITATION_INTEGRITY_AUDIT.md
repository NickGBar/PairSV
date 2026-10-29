# Week 4 — аудит целостности цитирования (§3)

**Дата:** 2026-08-08
**Режим:** только верификация. **Manuscript, библиография и скрипты не изменялись.**
**Frozen evaluation artifacts, report, thresholds, checkpoints, evaluation definitions:** не затрагивались ни в каком виде. Этот проход касается только литературы и цитат.

---

## 1. Таблица аудита

| ID | Manuscript claim | Source | Verified? | Existing key | Required action |
|---|---|---|---|---|---|
| **A1** | «DELLY … represent the first stage of the two-stage pipeline» — DELLY назван как SV-caller | Rausch T, Zichner T, Schlattl A, Stütz AM, Benes V, Korbel JO. DELLY: structural variant discovery by integrated paired-end and split-read analysis. *Bioinformatics.* 2012;28(18):i333-i339. doi:10.1093/bioinformatics/bts378. PMID: 22962449 | **Да** — PubMed. Первичная публикация; интегрирует paired-end и split-read | `[ref]` | Заменить на `rausch2012delly`. Утверждение статьи узкое («DELLY — SV-caller») и полностью поддерживается |
| **A2** | «LUMPY/smoove … represent the first stage» | Layer RM, Chiang C, Quinlan AR, Hall IM. LUMPY: a probabilistic framework for structural variant discovery. *Genome Biology.* 2014;15(6):R84. doi:10.1186/gb-2014-15-6-r84. PMID: 24970577 | **Да** — PubMed. Первичная публикация LUMPY; интегрирует read-pair, split-read, read-depth и prior knowledge | `[ref]` | Заменить на `layer2014lumpy` **только для LUMPY**. **smoove — отдельный инструмент, его публикация не найдена и не проверена**; либо цитировать как ПО, либо убрать «/smoove» из текста |
| **A3** | «long-read callers (Sniffles …)» | Sedlazeck FJ, Rescheneder P, Smolka M, Fang H, Nattestad M, von Haeseler A, Schatz MC. Accurate detection of complex structural variations using single-molecule sequencing. *Nature Methods.* 2018;15(6):461-468. doi:10.1038/s41592-018-0001-7. PMID: 29713083 | **Да** — PubMed. Первичная публикация, вводит NGMLR и Sniffles | `[ref]` | Заменить на `sedlazeck2018sniffles`. Заголовок статьи не содержит слова «Sniffles» — при оформлении важно не исказить название |
| **B1** | `[byrska-bishop2022]` — «50 unrelated individuals sequenced to high coverage (30x) by the expanded 1000 Genomes Project NYGC alignment set» (§4) | Byrska-Bishop M, Abel HJ, et al. High-coverage whole-genome sequencing of the expanded 1000 Genomes Project cohort including 602 trios. *Cell.* 2022;185(18):3426-3440.e19. doi:10.1016/j.cell.2022.08.004. PMID: 36055201 | **Да** — PubMed + издатель. Ресурс: 3 202 образца, 30X Illumina | `byrska-bishop2022` (ключ есть, записи нет) | Добавить полную запись. **Полный список авторов не подтверждён** — подтверждены первый автор, второй автор, название, журнал, год, том, выпуск, страницы, DOI, PMID |
| **C1** | «closest in spirit to **conformal-prediction** and person-level calibration approaches in clinical/genomic ML that separate model training from deployment-threshold selection» (§3) | — | **Нет. Claim не проверяется подбором источника** | нет | **Не цитировать.** См. раздел 2 — утверждение неточно по существу, и правильное действие — сузить его, а не искать под него источник |
| **D1** | DeepVariant | — | **Неприменимо** | нет | **Пометка в библиотеке ошибочна.** DeepVariant в тексте статьи отсутствует: упоминание исчезло вместе с placeholder «[Space for: … DeepVariant's SNV/indel framing]», заменённым реальным related work. Удалить DeepVariant из списка «Still unresolved» |
| **E1** | «genotype-class labels … drawn from the **1000 Genomes phase-3 integrated SV map**» (§3, описание samplot-ML) | Ресурс назван по имени, первичная публикация (Sudmant et al.) **не проверялась** | Нет | нет | Опционально. Это описание источника данных чужой работы и покрывается `[belyeu2021samplot]`. Если ресурс называется по имени — нужна своя ссылка |
| **E2** | «v0.6: GRCh37-only, **self-reported ≤50% genome-wide SV coverage** with an easier-SV bias» (§3); та же величина работает в §15.10 | Источник не помечен. Это утверждение о том, что заявляет документация v0.6 | **Нет** | нет | **Нужна ссылка.** Величина несущая: на ней стоит аргумент §15.10 о неполноте v0.6. Проверить по `zook2020giabsv` или по README релиза v0.6 и пометить |
| **E3** | «are the **standard community reference** for SV caller benchmarking via Truvari» (§3) | Утверждение о практике сообщества | **Нет** | нет | Либо сузить до проверяемого («widely used»), либо снять. Одной ссылкой не поддерживается |
| **E4** | «assembly-based (**methodologically closer to a ground truth** than earlier read-support-consensus callsets)» (§3) | Сравнительное методологическое утверждение | **Нет** | нет | Сузить до фактического различия (assembly-based против read-support-consensus) без оценки «closer to a ground truth», либо поддержать ссылкой |
| **F1** | Заголовок §3: «*[Draft skeleton — full citations to be added; claims here are … **not yet literature-verified against specific papers**.]*» | — | **Устарело** | — | Утверждение теперь ложно: 10 ссылок верифицированы по первоисточникам. Обновить или снять |
| **F2** | Sourcing note в конце §3: «The §3 Related Work citations are placeholders pending a literature pass — do not treat bracketed [ref] tags as verified.» | — | **Частично устарело** | — | Верно только для трёх оставшихся `[ref]`. Переформулировать под фактическое состояние |

---

## 2. Отдельно: claim о conformal prediction (C1)

**Что говорит manuscript:**

> «PAIR-SV's threshold-calibration methodology (leave-one-person-out on realistic Manta candidates, targeting a fixed recall operating point, §12) is closest in spirit to conformal-prediction and person-level calibration approaches in clinical/genomic ML that separate model training from deployment-threshold selection using held-out development data.»

**Почему я не стал искать под это источник.** Conformal prediction — это конкретная рамка, дающая distribution-free гарантии покрытия для конечной выборки. Процедура PAIR-SV — выбор порога по LOPO с целевым уровнем recall — никаких гарантий покрытия не даёт и не претендует на них. Формулировка «closest in spirit to» скрывает это различие: рецензент, знакомый с conformal prediction, может обоснованно возразить, что аналогия неточна.

Подобрать сюда любую работу по conformal prediction означало бы **подогнать источник под неточное утверждение** — ровно то, что запрещает правило 7, и ровно та ошибка, которая уже произошла с PanGenie в D8.

**Что здесь фактически нужно.** Содержательная часть предложения — «мы отделяем обучение модели от выбора порога развёртывания, используя held-out development data» — это описание **нашего собственного метода**, а не утверждение о литературе. Ссылка ему не нужна.

**Минимальное действие:** снять сравнение с conformal prediction, оставив описание процедуры. Ссылка не требуется, и claim при этом не сужается по существу — сужается только декоративное позиционирование.

---

## 3. Что реально проверено в этом проходе

| Проверено по первоисточнику | Результат |
|---|---|
| DELLY (Rausch 2012) | подтверждён, PMID 22962449 |
| LUMPY (Layer 2014) | подтверждён, PMID 24970577; **smoove отдельно не подтверждён** |
| Sniffles (Sedlazeck 2018) | подтверждён, PMID 29713083 |
| Byrska-Bishop 2022 | подтверждён, PMID 36055201; полный список авторов не подтверждён |
| DeepVariant | **claim отсутствует** — цитата не нужна |
| Conformal prediction | **источник не искался намеренно** — claim неточен по существу |

---

## 4. Минимальный набор изменений для submission-ready версии

Разделён по типу: замена ключей — механика; всё остальное затрагивает смысл и требует отдельного решения.

### 4.1 Замена ключей — низкий риск, поддержано первоисточниками

1. `DELLY [ref]` → `DELLY [rausch2012delly]`
2. `Sniffles [ref]` → `Sniffles [sedlazeck2018sniffles]`
3. `LUMPY/smoove [ref]` → `LUMPY [layer2014lumpy]`, **и отдельно решить, что делать со smoove**: либо `[software-ref]`, либо убрать из перечисления
4. Добавить в библиографию три записи (Rausch, Layer, Sedlazeck) и полную запись `byrska-bishop2022`

### 4.2 Исправление устаревших собственных пометок — низкий риск

5. Удалить **DeepVariant** из списка «Still unresolved» (claim не существует)
6. Обновить заголовок §3 (F1) — утверждение «not yet literature-verified» больше не соответствует состоянию
7. Переформулировать sourcing note (F2) под три оставшихся `[ref]`

### 4.3 Затрагивает содержание — требует решения

8. **C1:** снять сравнение с conformal prediction, оставив описание процедуры
9. **E2:** «self-reported ≤50% genome-wide SV coverage» — пометить источник. **Приоритет: величина несущая для §15.10**
10. **E3:** «standard community reference» — сузить или снять
11. **E4:** «methodologically closer to a ground truth» — сузить до фактического различия
12. **E1 (опционально):** решить, нужна ли отдельная ссылка на 1000 Genomes phase-3 SV map

### Не требуется

- Искать источник под claim о conformal prediction.
- Расширять claim ради найденного источника ни в одном из пунктов.

---

**Ничего не изменено.** Manuscript, библиография, скрипты, frozen artifacts, thresholds, checkpoints и определения оценки остались в том состоянии, в каком были до начала прохода.
