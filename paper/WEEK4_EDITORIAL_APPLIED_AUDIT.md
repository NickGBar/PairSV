# Week 4 — применённая редакторская правка: аудит

**Дата:** 2026-08-08
**Основание:** `paper/WEEK4_EDITORIAL_AUDIT.md`, пункты E1-E17, плюс две содержательные вставки D3 и D8
**Канонический manuscript:** перегенерирован через `paper/merge_manuscript.py`, 602 строки, sha256 `186e21864e9729cef266954611b54e8dc039489f4ad7236d3524b3b592c75259`
**Frozen artifacts:** не изменялись. Evaluation не запускалась.

---

## 1. Применённые изменения

### Introduction / Related Work (`intro_related_work_v1_draft.md`)

| ID | Было | Стало | Тип |
|---|---|---|---|
| **E1** | "**the full multimodal model (M4) is not uniformly the best-performing variant.**" | "M4 is not consistently ahead of the simpler variants." + три измерения (§9.2 CI, §12 диапазон 0.212-0.240, §15.12) | оценка → измерение |
| **E2** | "a central claim of this paper is that specificity gains are not interchangeable with meeting a pre-registered recall target" | Удалено из §2. Утверждение сохранено как наблюдение в §15.4, где оно относится к конкретному результату HG002 | устранение конкурирующего тезиса |
| **E3** | "stated plainly rather than smoothed over"; "We report this without reframing it as a qualified success" | Обе рамки удалены | декларация честности |
| **E5** | Результат HG002 во Введении без пометки | Добавлено в то же предложение: "across 30 people that recall ordering does not persist (§15.12)" | наблюдение ≠ вывод |
| **E6** | Contributions повторяли "0.000176 … 0.0062" | Заменено на "Across 30 untouched people that ordering does not persist (§15.12)" | повтор |
| **E7** | "a supervision structure not available from single-individual training" | "This pairing requires training data spanning several individuals; §3 describes prior work that also learns from same-site examples across people." | согласование с §3 |
| **E12** | "the first genuinely out-of-sample test"; "a genuinely untouched person" | "the first out-of-sample test"; "one untouched person" | интенсификатор |

### Results (`results_v1_draft.md`)

| ID | Было | Стало | Тип |
|---|---|---|---|
| **E4** | "**Honest reporting of a genuine, non-tuned finding:**" | "**At the frozen threshold:**" | декларация честности |
| **E9** | "**This is a genuinely different pattern from v5.0q, not a replication of it — exactly why the two are never pooled.**" | "**The v0.6 pattern differs from v5.0q.** The two are reported separately, per the evidence-tier index." | интенсификатор + повтор обоснования |
| **E12** | "genuinely untouched until this evaluation"; "on genuinely untouched external data"; "replicated on genuinely external data" | "was untouched until this evaluation"; "on untouched external data"; "replicated on external data" | интенсификатор |
| **E17** | "the predefined \"strong success\" bar" | "the \"strong success\" bar of the pre-registered decision rule (…; the label is the rule's own)" | ярлык предрегистрации помечен как таковой |
| **D3** | — | Новый абзац в §13-переходе: различение non-replication и доказательства того, что эффект HG002 был шумом | содержательная вставка |

### Discussion / Limitations / Conclusion (`discussion_limitations_conclusion_v1_draft.md`)

| ID | Было | Стало | Тип |
|---|---|---|---|
| **E13** | Заголовок §15.2: "…it recurs at every evaluation layer"; текст: "at every evaluation layer" | Заголовок: "M2 and M4 are close in each of the four measurements"; текст: "in each of the four measurements below. The measurements are not directly comparable to one another…" | обобщение поверх несопоставимых tiers |
| **E6** | §15.3 повторяла "0.000176 … 0.0062" | "a difference far inside the between-person spread (§15.12 gives the figures)". **Структура Observation → superseded Interpretation → What the cohort showed сохранена** | повтор |
| **E8** | "It would be a mistake to read this as M4 \"winning\" on balance." | "M4 had the highest specificity … and the lowest recall (0.9327). … Under that criterion the two quantities are not interchangeable" | спор с воображаемым читателем |
| **E10** | "This is the cleanest statement the study can make about the frozen operating point" | Удалено; оставлено измерение | самооценка |
| **E11** | "This is arithmetic, not a separate failure." | "This follows from the prevalence. At 88.3% positives, a rule that keeps every candidate holds recall at 1.0, and the recall term dominates F1…" | F1 как trade-off, без категории «неудача» |
| **E14** | "This is where the study contributes most." | Удалено | самооценка вклада |
| **E15** | "A single external genome, frozen and reported honestly, was enough…" | "A single external genome, evaluated once under a fixed protocol, supported a conclusion…" | декларация честности |
| **E16** | AFR: объяснение перед следствием | Порядок: числа → следствие для читателя → интерпретация с явной пометкой | observation перед interpretation |
| **E12** | "a genuinely novel benchmark" | "a new benchmark" | интенсификатор |
| **D8** | — | Три вставки: §15.9 (полный абзац о зависимости от PanGenie), §15.12 (**Truth source.** в начале раздела), §16 (буллет-ограничение) | содержательная вставка |

**Итого:** 17 пунктов E1-E17 применены; E18 правки не требовал (уже соответствовал принципу 7). Две содержательные вставки D3 и D8 добавлены в четырёх местах.

---

## 2. Содержательные вставки

**D3 — non-replication ≠ доказательство шума.** Добавлено в §13-переход и в §15.12:

> "Two claims must be kept apart. The cohort shows that the M2-M4 recall difference seen on HG002 does not persist across 30 people. It does not establish that the HG002 difference was sampling variation rather than a real difference on that individual. No test of whether the HG002 M2-M4 difference was nonzero was pre-specified, and none is run here."

**D8 — зависимость от PanGenie.** Добавлено в §15.9 (развёрнуто), §15.12 (в начале, как рамка для всех чисел раздела) и §16 (буллет):

> "The cohort-level conclusions in §15.12 … are therefore conclusions about model behaviour as measured against this truth source. PanGenie is a silver-standard resource with documented accuracy that varies by locus, mappability, panel composition and population representation …; it is not a weak label set, but it is not GIAB-grade ground truth either. Replication of the cohort result against a stronger independent truth standard was not established here…"

PanGenie не охарактеризована как «слабая», и не утверждается, что зависимость обесценивает когорту.

---

## 3. Верификация

| # | Проверка | Результат |
|---|---|---|
| 1 | Frozen report checksum | **PASS** — `84f571b6…b3d1`, без изменений |
| 2 | Числа когорты | **PASS** — 57/57 ячеек таблиц §15.12 совпадают с отчётом, 0 расхождений; 10/10 ключевых значений присутствуют и совпадают |
| 3 | `[ref]` placeholders | **PASS** — 12, как до правки |
| 4 | E1-E17 применены | **PASS** — все удалённые формулировки дают 0 вхождений; «genuinely» 10 → 2; «0.000176» 6 → 4 |
| 5 | D3 и D8 присутствуют | **PASS** — 5 из 5 маркерных фраз найдены |
| 6 | Новая оценочная лексика | **PASS** — 0 вхождений (clearly, promising, compelling, powerful, decisively, importantly и др.) |
| 7 | Артефакты, thresholds, модели, датасеты, определения | **PASS** — записи только в `paper/` и `manta_poc/*.md`; см. примечание ниже |

**Примечание к пункту 7.** `git status` показывает изменения в `deepsv/models/pairsv.py`, `deepsv/multisample/extraction.py` и др. Эти файлы датированы 25-26 июля и относятся к рабочему дереву до начала сессии — я их не открывал и не записывал. Все мои записи в этой задаче ограничены `paper/*.md`, `paper/*.py` и документами в `manta_poc/`. Ни один вычислительный артефакт, порог, чекпойнт, датасет или определение метрики не затронут.

---

## 4. Оставшиеся вхождения — классификация

| Формулировка | Осталось | Классификация |
|---|---|---|
| "genuinely" | 2 | **Обе валидны:** "genuinely difficult calls" (в противопоставление кажущимся трудными) и "genuinely informative — features" (в противопоставление шумовым). Несут контраст, не усиление |
| "0.000176" | 4 | **По плану E6:** Abstract, §13-переход, §15.12, §18. §15.3 теперь ссылается на §15.12 вместо повтора |
| "strong" | 3 | "strongly additive" (отрицание), "strong success" (ярлык предрегистрированного правила, помечен), "methodologically stronger" (о benchmark, не о наших результатах) |
| "effective" | 2 | Оба — о проверке исключения метаданных ("this exclusion is effective"), технический смысл |
| "validated" / "generaliz*" / "demonstrat*" | как ранее | Все — либо отрицания, либо описание критикуемой практики, либо постановка вопроса. Классифицированы в `WEEK4_NARRATIVE_B_FINAL_AUDIT.md` |

---

## 5. Неоднозначности, оставленные автору

1. **§15.4 сохраняет утверждение о невзаимозаменяемости recall и specificity.** E2 убрал его статус «центрального» из §2, но само утверждение осталось в §15.4 как рассуждение о правиле развёртывания. Это интерпретация, а не измерение, и она помечена привязкой к критерию. Если требуется более строгая позиция, её можно свести к одной фразе о том, что правило фиксирует recall первым.
2. **D3 сформулировано как отказ от теста, а не как оценка вероятности.** Текст говорит, что тест не был предрегистрирован и не проводится. Он не говорит, насколько вероятно, что разница на HG002 была шумом. Добавление такой оценки потребовало бы post-hoc теста, что запрещено.
3. **D8 помещено в три места** (§15.9, §15.12, §16). Это осознанный повтор: §15.12 — рамка для чисел, §15.9 — развёрнутое объяснение, §16 — ограничение в списке. Если это сочтено избыточным по принципу 9, сокращать следует §16, а не §15.12.
4. **Заголовок §15.2 изменён** («M2 and M4 are close in each of the four measurements»). Заголовок теперь описывает наблюдение, а не вывод; прежний заголовок содержал утверждение «it recurs at every evaluation layer», которое E13 признал обобщением.
5. **Фрагмент §13 «At the frozen threshold:»** заменил ярлык, который выполнял роль подзаголовка. Если нужна навигационная разметка, стоит ввести настоящий подзаголовок вместо жирной фразы.
