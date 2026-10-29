# Week 4 — финальный редакторский аудит канонического manuscript

**Дата:** 2026-08-08
**Аудируемый файл:** `paper/PAIR_SV_v1_manuscript.md` (593 строки, sha256 `423fcdf0…af2a`)
**Роль:** независимый технический редактор
**Изменения применены:** нет. Только предложения.
**Научное содержание, числа, методы, thresholds, evaluation definitions, frozen artifacts:** не затрагиваются ни одним предложением ниже.

---

## Таблица найденных мест

| # | Location | Current wording | Problem | Proposed wording | Reason |
|---|---|---|---|---|---|
| E1 | §2, L71 | "**the full multimodal model (M4) is not uniformly the best-performing variant.**" | "best-performing" — оценочная категория, которой нет в эксперименте. Данные дают направление и descriptive advantage, не ранжирование | "M4 is not consistently ahead of the simpler variants. On the internal test it is statistically indistinguishable from M2 (§9.2); on the 5-person POC the three are within 0.212-0.240 specificity (§12); on the cohort M2 and M4 differ in recall by 0.000176 (§15.12)." | Принцип 5 и 1: заменяет оценку измерением |
| E2 | §2, L71 | "a central claim of this paper is that specificity gains are not interchangeable with meeting a pre-registered recall target" | Под Narrative B центральный тезис — "one genome is not enough". Здесь объявлен другой центральный тезис. Два конкурирующих "central claim" в одной статье | Понизить до наблюдения внутри §15.4 и убрать слово "central claim" из §2; в §2 оставить только вопрос об одном геноме | Нарратив: один центральный тезис |
| E3 | §2, L71 | "A recurring theme across these four layers, stated plainly rather than smoothed over:" / "We report this without reframing it as a qualified success" | Defensive prose. Текст сообщает читателю, что он честен, вместо того чтобы просто быть честным | Удалить обе рамки; оставить факты | Принцип 8 |
| E4 | §13, L361 | "**Honest reporting of a genuine, non-tuned finding:**" | То же: ярлык честности вместо содержания. Плюс "genuine" — интенсификатор | "At the frozen threshold:" | Принцип 8 и 4 |
| E5 | §2, L71 | "M4 achieves the *highest* specificity … while *missing* the pre-specified 95% recall deployment target that M2 meets (§13)" | Результат HG002 подан во Введении без немедленной пометки, что он не воспроизвёлся. Читатель встречает опровергнутое утверждение как тезис статьи | Добавить в то же предложение: "on HG002; across 30 people the M2/M4 recall difference is 0.000176 (§15.12)" | Принцип 2 и нарратив: HG002 — исходное наблюдение, не вывод |
| E6 | сквозное | "0.000176" — 6 раз (L50, 75, 417, 451, 517, 581); "95% recall target" — 9 раз; "0.9453" — 5 раз | Один результат повторён риторически многократно. Повтор создаёт впечатление силы, которой у числа нет | Оставить: Abstract (1), §13-переход (1), §15.12 (1), §18 (1). Убрать из §2-Contributions и §15.2 — там достаточно ссылки на §15.12 | Принцип 9 |
| E7 | §2, L64 | "a supervision structure not available from single-individual training" | Формально верно, но соседствует с §3, где сказано, что same-site supervision не нова. Читатель воспримет как претензию на новизну | "This pairing is only possible when training spans several individuals; §3 describes prior work that also learns from same-site examples across people." | Принцип 1; согласование с §3 |
| E8 | §15.4, L455 | "It would be a mistake to read this as M4 'winning' on balance." | Спор с воображаемым оппонентом. Defensive prose | "M4's specificity is higher; its recall is lower. The deployment criterion fixes recall first, so the two are not interchangeable here." | Принцип 8 и 3 |
| E9 | §13, L405 | "**This is a genuinely different pattern from v5.0q, not a replication of it — exactly why the two are never pooled.**" | "genuinely", "exactly why" — интенсификаторы. Причина непуления должна быть изложена один раз в методах, а не как риторическое усиление | "The v0.6 pattern differs from v5.0q. The two are reported separately (§ evidence-tier index)." | Принцип 4 и 9 |
| E10 | §15.12, L515 | "This is the cleanest statement the study can make about the frozen operating point" | Оценка собственного результата ("cleanest") | Удалить фразу; оставить следующее за ней измерение | Принцип 3 и 8 |
| E11 | §15.12, L513 | "This is arithmetic, not a separate failure." | Верно по сути, но звучит оборонительно. Формулировка "not a failure" вводит категорию неудачи, которую затем отрицает | "This follows from the prevalence: at 88.3% positives, a rule that keeps every candidate scores high F1 by construction." | Принцип 8; F1 как trade-off, а не как оценка |
| E12 | сквозное | "genuinely" ×10 (L68, 94, 343, 361, 405, …) | Интенсификатор без содержания | Удалить во всех случаях, кроме L343 ("genuinely untouched until this evaluation"), где он несёт смысл "до этого момента не открывался" | Принцип 4 |
| E13 | §15.2, L~412 | "M2 and M4 sit close together on recall and F1 at every evaluation layer." | "at every evaluation layer" — обобщение на все слои, тогда как §9.2 даёт CI, а §12 и §15.12 — точечные оценки. Слои измеряют разное | "M2 and M4 are close on recall and F1 in each of the four measurements listed below; the measurements are not directly comparable to one another." | Принцип 1 и разделение tiers |
| E14 | §18, L585 | "This is where the study contributes most." | Само-оценка вклада | "The evaluation result is the part of this study we consider transferable to other work." — или удалить, оставив содержание | Принцип 8 |
| E15 | §18, L583 | "A single external genome, frozen and reported honestly, was enough to support a conclusion that thirty genomes did not reproduce." | "reported honestly" — снова декларация честности | "A single external genome, evaluated once under a fixed protocol, supported a conclusion that thirty genomes did not reproduce." | Принцип 8 |
| E16 | §16 | "the evaluation is less informative for African-ancestry genomes, and the measured benefit of the filter on them is smaller" | Формулировка корректна, но стоит после объяснения; наблюдение должно идти первым | Переставить: сначала числа (0.174-0.183 против 0.223-0.243), затем следствие, затем гипотеза о панели | Принцип 6 |
| E17 | §11, L~333 | "This did not reach the predefined 'strong success' bar (30-40% specificity at ~95% recall)" | "strong success" — цитата собственного предрегистрированного критерия, это допустимо, но кавычки стоит сохранить и добавить, что это ярлык критерия, а не оценка | Оставить, но добавить: "(the label used in the pre-registered decision rule)" | Принцип 4; сохранение предрегистрации |
| E18 | §3 | "We are not aware of prior SV work that quantifies a locus-memorisation shortcut in this way, though we have not reviewed the field exhaustively." | Корректно. Но за этим следует, что отсутствие находки не превращается в утверждение отсутствия — сейчас это выражено, менять не нужно | — | Принцип 7 уже соблюдён |

---

## A. Десять наиболее важных редакторских проблем

1. **E2 — два конкурирующих "центральных тезиса".** §2 объявляет центральным утверждением "specificity gains ≠ recall target", тогда как Narrative B — "one genome is not enough". Это единственная проблема, которая ломает нарратив, а не только стиль.
2. **E5 — HG002-результат во Введении подан без пометки о невоспроизведении.** Читатель, дочитавший только Введение, унесёт опровергнутое утверждение.
3. **E6 — шестикратный повтор 0.000176.** Главный результат повторён столько раз, что начинает выглядеть как аргументация, а не как измерение.
4. **E1 — "best-performing variant".** Прямое нарушение принципа 5 в жирном шрифте.
5. **E3/E4/E15 — декларации честности.** «stated plainly rather than smoothed over», «Honest reporting of a genuine, non-tuned finding», «reported honestly». Статья трижды сообщает, что она честная. Рецензент читает это как защитную реакцию.
6. **E7 — рассогласование §2 и §3 по новизне.** §2 говорит «structure not available from single-individual training», §3 говорит «same-site supervision is not new». Формально совместимо, но выглядит как непроработанная правка.
7. **E12 — "genuinely" ×10.** Самый частый пустой интенсификатор в тексте.
8. **E8 — спор с воображаемым читателем** («It would be a mistake to read this as…»).
9. **E13 — "at every evaluation layer"** — обобщение поверх несопоставимых tiers.
10. **E10/E14 — само-оценка собственных результатов** («cleanest statement», «where the study contributes most»).

---

## B. Места, которые лучше не трогать

| Место | Почему не трогать |
|---|---|
| §15.3 структура «Observation / Interpretation we drew at the time, now superseded / What the cohort showed» | Это лучший фрагмент статьи с точки зрения принципа 6. Разделение наблюдения, интерпретации и вывода сделано явно и подписано |
| Сохранённая опровергнутая гипотеза в §15.3 | Удаление сделало бы текст чище и хуже. Она — часть аргумента |
| §8 таблица leakage-проб с предрегистрированным порогом 0.65 | Числа и формулировки точные, оценок нет |
| Evidence-tier index (§ перед §9) | Единственное место, где явно запрещено пулить tiers. Трогать нельзя |
| §15.10 отказ выбирать между чтениями (a) и (b) | Правильное применение принципа 7 |
| Все `[ref]` | Помечены как неразрешённые; удаление скроет незавершённость |
| §17 «No end-to-end artifact manifest … was produced for the v0.6 pass» | Прямое признание пробела. Ценнее, чем гладкость |
| Формулировка про AFR «consistent with … though the analysis does not establish a cause» | Точная граница между наблюдением и гипотезой |
| Erratum-документ и его упоминание | Признание собственной ошибки в описательном поле |

---

## C. Места, уже соответствующие принципам Оруэлла

- **§18 «What the cohort does not show is that the models are poor.»** — прямое разграничение performance и generalization. Именно то, что требует Narrative B.
- **§15.12 «We did not pre-specify a test for that difference and make no claim of significance for it.»** — отсутствие доказательства не превращено в доказательство отсутствия (принцип 7), и нет намёка на значимость.
- **Abstract, первый абзац** — начинается с проблемы оценки, не с архитектуры; три коротких предложения; без прилагательных.
- **§13-переход «More analysis of HG002 cannot settle it. More people can.»** — конкретно, коротко, без пафоса.
- **§15.4 «What survives is the principle … not its HG002 instance.»** — явное отделение принципа от конкретного случая.
- **§16 обе новые буллеты** — измерение впереди, интерпретация помечена.
- **§3 «We therefore do not claim that same-site supervision across individuals is new.»** — прямой отказ от претензии.
- **Contributions, буллет 4** — «Same-site supervision across individuals is not itself new (§3); what we add is the explicit construction and the shortcut measurement.»

---

## D. Уязвимости, остающиеся после Narrative B

| # | Атака рецензента | Насколько обоснована | Что можно ответить сейчас |
|---|---|---|---|
| D1 | «Вывод "n=1 недостаточно" известен априори. Вы потратили 30 геномов, чтобы подтвердить статистическую банальность» | **Сильная.** Это главная угроза для C1-фрейминга | Ответ: известен как принцип, но редко демонстрируется на предрегистрированном протоколе с тем же пайплайном; и ближайшая работа по фильтрации (DeepSVFilter) обучена на одном геноме. Но это ответ на рецензии, а не в тексте — стоит подготовить |
| D2 | «Ваш фильтр не достигает собственной цели по recall. Зачем публиковать метод, который не работает?» | **Сильная.** Прямое следствие честного отчёта | В тексте уже разведены performance / generalization / evaluation design. Ответ существует, но рецензент может не принять его |
| D3 | «Разница M2/M4 в 0.000176 — это отсутствие эффекта, а не опровержение. Вы опровергаете то, чего, возможно, и не было» | **Умеренная.** На HG002 разница 2.2 пункта была реальным измерением | Текст уже говорит, что HG002-разница была свойством человека. Но формально «не воспроизвелось» и «не существовало» здесь не различимы — и статья этого не проговаривает. **Рекомендую добавить одно предложение об этом ограничении** |
| D4 | «Почему не пересчитали порог по когорте? Он же промахивается» | **Умеренная** | Ответ: протокол запрещает; порог был заморожен до открытия данных. Это методологическая сила, но требует явного объяснения — сейчас оно есть в §17, но не рядом с результатом |
| D5 | «AFR-разрыв: вы списываете его на панель, но не доказали» | **Слабая** — текст сам это признаёт | Формулировка уже осторожная |
| D6 | «Same-site supervision не нова, а вы построили на ней методологический вклад» | **Слабая после правки** | §3 и Contributions теперь это признают явно |
| D7 | «M4 выигрывает по specificity в трёх оценках — почему вы отказываетесь это признать?» | **Умеренная, зеркальная.** Рецензент может обвинить в чрезмерной осторожности | Ответ: не предрегистрировали тест. Позиция защитима, но стоит быть готовым, что рецензент попросит его добавить — а добавление post hoc нарушит протокол |
| D8 | «Три из восьми tiers используют PanGenie silver-standard, а не GIAB. Ваш главный результат зависит от более слабой truth source» | **Сильная и пока не адресованная.** Когорта размечена PanGenie, а не GIAB | В §15.9 есть общее ограничение PanGenie, но не сказано прямо, что **центральный результат статьи опирается на silver-standard truth**. **Это самый крупный неадресованный пробел, который я нашёл** |
| D9 | «Вы сравниваете specificity между tiers с разными truth sources (0.217-0.225 против 0.250-0.322)» | **Умеренная** | §13 и §15.10 уже помечают сравнение как некорректное в абсолютных величинах, но §15.12 делает его дважды |

---

## Резюме

- Найдено **18 редакторских мест** (E1-E18), из них 17 требуют правки, одно (E18) уже корректно.
- Нарушений научного содержания **не найдено**: все числа, tiers, thresholds и определения согласованы с frozen artifacts.
- Одна проблема — **E2** — затрагивает нарратив, а не стиль: во Введении объявлен центральный тезис, конкурирующий с Narrative B.
- Один пробел не является редакторским и требует решения автора: **D8** — зависимость центрального результата от PanGenie silver-standard truth не проговорена прямо.
- Изменения не применены. Жду подтверждения.
