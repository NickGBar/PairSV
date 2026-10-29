# PAIR-SV

Код и материалы двух работ о проверке классификатора делеций и о выборе порога
с гарантией. English summary below.

---

## О чём это

**PAIR-SV** перепроверяет кандидатов на делецию (потерю участка ДНК длиной
50–10 000 пар оснований), которых предложил детектор Manta. Программа ничего не
ищет заново: она получает находку детектора вместе с прочтениями ДНК конкретного
человека и оценивает, настоящая это делеция или ложное срабатывание.

Пять вложенных версий (M0–M4) используют общий кодировщик изображения прочтений
вокруг двух точек разрыва и различаются только подключёнными источниками данных:
последовательность ДНК в месте кандидата (через готовую модель HyenaDNA),
представления отдельных прочтений, 17 числовых признаков поддержки.

### Статья 1 — проверка на 30 геномах

> *Evaluating a deletion-candidate classifier across 30 genomes: a single-genome
> result that did not replicate*

Главный результат относится к методике оценки, а не к сравнению версий
программы. На эталонном геноме HG002 одна версия (M2) достигла заявленной цели
в 95% чувствительности, а более сложная M4 — нет. На 30 нетронутых людях это
различие не воспроизвелось: разница составила 0,000176 при разбросе между
людьми 0,0062, то есть примерно в 35 раз меньше шума. Замороженной, заранее
зарегистрированной проверки на одном геноме оказалось достаточно, чтобы
обосновать вывод, который не подтвердился на выборке людей.

Попутно: быстрый способ оценить вклад источника данных (обнуление входа у
готовой модели) завышает его в 5–10 раз по сравнению с переобучением модели без
этой ветви.

Тексты: [`paper/PAIR_SV_v1_manuscript.md`](paper/PAIR_SV_v1_manuscript.md)
(английский, для подачи) · [`paper/PAIR_SV_v1_manuscript_RU.md`](paper/PAIR_SV_v1_manuscript_RU.md)
и [PDF](paper/PAIR_SV_v1_manuscript_RU.pdf) (русская версия, все числа
совпадают) · [`paper/PAIR_SV_v1_plain_russian_explainer.md`](paper/PAIR_SV_v1_plain_russian_explainer.md)
(пересказ простым языком).

### Статья 2 — порог с гарантией (в работе)

Процедура подбора порога из статьи 1 держит заявленную чувствительность у нового
человека примерно в половине случаев (15–18 из 30). Работа проверяет замену —
конформный контроль риска.

Результат оказался тоньше ожидаемого. Метод действительно даёт надёжность 30 из
30, но **не эффективнее** старой эвристики: при равной надёжности эвристика
отсеивает больше ложных находок. Причина установлена точно: поправка на конечный
размер выборки съедает 67% бюджета ошибки при N = 29, из-за чего процедура,
которую просили о чувствительности 0,95, фактически работает на 0,98276 —
совпадение формулы `1 − [α(N+1) − B] / N` с измерением до пятого знака. Тот же
член формулы при 6 людях в группе делает гарантию недостижимой вовсе
(граница `N/(N+1)`: для цели 95% нужно не меньше 19 человек).

Состояние и план: [`PAPER2_RESEARCH_PLAN.md`](PAPER2_RESEARCH_PLAN.md).
Код: [`paper2_conformal/`](paper2_conformal/).

---

## Как устроен репозиторий

| Каталог | Что внутри |
|---|---|
| `paper/` | Тексты статей, черновики разделов, рисунки, сборка PDF, пакет для подачи |
| `paper2_conformal/` | Код второй работы: конформный контроль риска, 8 пронумерованных шагов |
| `deepsv/` | Модель PAIR-SV, датасеты, обучение |
| `scripts/` | Обучение, извлечение признаков, вызов делеций |
| `manta_poc/` | Конвейер Manta, замороженные протоколы и отчёты об оценке |
| `reports/` | Агрегированные результаты обучения и внутреннего теста |
| `presentation/` | Доклад о работе: сборка презентации из тех же файлов с результатами |
| `docs/`, `tests/` | Документация разработчика, тесты |

## Воспроизводимость

Принцип всей работы: ни одно число в текстах и на слайдах не набрано вручную.
Каждое извлекается скриптом из файла с результатами, а источник проверяется по
контрольной сумме SHA-256 перед чтением.

```bash
pip install -r requirements.txt

# Рисунки статьи 1 (10 штук). Figure 8 проверяет SHA-256 отчёта по 30 людям
# и прекращает работу при несовпадении.
python3 paper/build_figures.py

# Числа §15.12 из замороженного отчёта -> paper/cohort_numbers_for_manuscript.json
python3 paper/extract_cohort_numbers.py

# Пересборка канонического текста статьи 1 из четырёх черновиков разделов
python3 paper/merge_manuscript.py

# PDF русской версии (нужен tectonic; шрифты Times New Roman и PT Mono)
python3 paper/md2tex_ru.py paper/PAIR_SV_v1_manuscript_RU.md build/m.tex
cp -r paper/figures build/ && cd build && tectonic m.tex

# Числа и презентация доклада
python3 presentation/extract_deck_data.py
node presentation/build_deck.js      # нужен pptxgenjs
```

Вторая работа выполняется по шагам в порядке нумерации:

```bash
cd paper2_conformal
python3 01_build_person_level_scores.py      # подготовка оценок на уровне человека
python3 02_crc_pooled.py --target-recall 0.95
python3 03_crc_group_conditional.py          # по группам происхождения
python3 04_compare_vs_heuristic_lopo.py      # сравнение со старой процедурой
python3 05_small_n_stress_test.py            # поведение при малых выборках
python3 06_compare_vs_heuristic_lopo_cohort.py
python3 07_group_vs_pooled_same_heldout.py
python3 08_matched_reliability_control.py    # контроль при равной надёжности
```

### Замороженные артефакты

Результаты, на которые опираются тексты, зафиксированы с контрольными суммами:

- `manta_poc/cohort_final_evaluation_report.json` — оценка 30 человек, открыта
  ровно один раз (SHA-256 `84f571b6…b3d1`)
- `manta_poc/COHORT_PRE_EVALUATION_MANIFEST.json` — состояние, замороженное до
  запуска оценки
- `manta_poc/hg002_external/` — внешняя проверка на HG002 по двум независимым
  источникам эталонных ответов
- `manta_poc/EXTERNAL_EVAL_PROTOCOL_FROZEN.md` — протокол, зафиксированный до
  открытия данных
- `manta_poc/COHORT_EVALUATION_ERRATUM.md` — известная ошибка в описательном
  поле отчёта, не влияющая ни на одну метрику

## Чего здесь нет

**Данных уровня образца.** Исходные прочтения (1000 Genomes, GIAB HG002)
общедоступны по адресам, записанным в файлах происхождения, но здесь не
дублируются. Не выкладываются и выгруженные с кластера предсказания по 30 людям
(155 МБ) — это соответствует §17 статьи 1. В репозитории только производные
артефакты: таблицы кандидатов, предсказания в агрегированном виде, отчёты об
оценке.

**Обученных моделей.** 15 замороженных моделей (5 версий × 3 повтора) хранятся
отдельно; их контрольные суммы — в `reports/train40/frozen_checkpoint_checksums.json`.

## Известные расхождения, которые нужно исправить до подачи

1. **Коэффициент завышения для ветви прочтений: в тексте 10,4×, верно 10,5×.**
   Отношение посчитано по уже округлённым числам таблицы. Рисунок 4 считает из
   исходных данных и подписывает 10,5×, поэтому текст и рисунок сейчас
   расходятся. Затронуты `paper/results_v1_draft.md` и
   `paper/discussion_limitations_conclusion_v1_draft.md`, а через них — собранный
   текст и переводы.
2. **«M4 на 2,2 пункта ниже цели 95%» — неверная привязка.** До цели M4 не
   хватает 1,7 пункта (0,95 − 0,9327); 2,2 — это разрыв с M2. Затронуты
   `paper/intro_related_work_v1_draft.md` и
   `paper/discussion_limitations_conclusion_v1_draft.md`.

Черновики разделов — редактируемый источник; собранный текст получается из них
скриптом `paper/merge_manuscript.py`.

## Прочее

Часть скриптов содержит абсолютные пути вида `/Users/nikolai/DNA/...` — при
запуске на другой машине их нужно заменить.

Лицензия: [MIT](LICENSE).

---

## English summary

**PAIR-SV** verifies deletion candidates (50–10,000 bp) proposed by the Manta
caller. It does not discover deletions: it scores an existing candidate against
one individual's aligned reads. Five nested variants (M0–M4) share a tied
dual-breakpoint pileup encoder and differ only in which evidence branches are
active.

**Paper 1** — *Evaluating a deletion-candidate classifier across 30 genomes: a
single-genome result that did not replicate.* On GIAB HG002 one variant (M2) met
the pre-specified 95% recall target and the fuller M4 did not. Across 30
untouched people that ordering did not replicate: the recall difference is
0.000176 against a between-person standard deviation of 0.0062, roughly 35×
smaller than the noise. A separate control in the same study shows post-hoc
zero-ablation overstating each modality's contribution by 5–10× relative to
retrained branch-removal. Manuscript:
[`paper/PAIR_SV_v1_manuscript.md`](paper/PAIR_SV_v1_manuscript.md).

**Paper 2** (in progress) — conformal risk control for threshold calibration.
The honest finding is that the method is *not* more efficient than the heuristic
at matched reliability; its finite-sample correction consumes 67% of the error
budget at N = 29, shifting the effective operating point to 0.98276 (predicted by
`1 − [α(N+1) − B] / N`, matched to five decimals), and the same term makes the
guarantee unreachable at n = 6 per group (`N/(N+1)` bound: N ≥ 19 for a 95%
target). See [`PAPER2_RESEARCH_PLAN.md`](PAPER2_RESEARCH_PLAN.md).

No number in either manuscript is hand-typed: each is extracted by script from a
result file whose SHA-256 is verified before reading. Sample-level data and
trained checkpoints are not redistributed here; see *Чего здесь нет* above.
Two known numerical discrepancies to fix before submission are listed in
*Известные расхождения*.

Licensed under [MIT](LICENSE).
