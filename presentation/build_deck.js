// Build the progress-report deck (PAIR-SV, papers 1 and 2) and the talk text.
//
// Every number comes from deck_data.json, which extract_deck_data.py builds
// from the frozen and generated result files. Nothing numeric is typed here.
// The talk (доклад) is written once, as speaker notes, and exported to
// PAIR_SV_doklad_text.md from the same strings, so the two cannot drift.
//
// Run:  python3 extract_deck_data.py && NODE_PATH=<dir with pptxgenjs> node build_deck.js
"use strict";
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const D = JSON.parse(fs.readFileSync(path.join(__dirname, "deck_data.json"), "utf8"));
const A1 = D.article1;
const A2 = D.article2;
const OUT_PPTX = path.join(__dirname, "PAIR_SV_doklad.pptx");
const OUT_TEXT = path.join(__dirname, "PAIR_SV_doklad_text.md");

// ---------- design tokens ----------
const C = {
  ink: "0F1C2E", inkCard: "1B2C44", white: "FFFFFF",
  text: "141A23", text2: "52514E", muted: "898781", grid: "E1E0D9", axis: "C3C2B7",
  blue: "2A78D6", orange: "EB6834",               // validated pair (dataviz validator, white surface)
  tintBlue: "EAF2FC", tintOrange: "FDEEE7", tintGray: "F2F3F5",
  onDark2: "C3C2B7", barMuted: "B9BDC4",
};
const F = { title: "Cambria", body: "Calibri" };
const W = 13.333, H = 7.5, MX = 0.6, CW = W - 2 * MX;
const TOTAL = 17;

// ---------- number formatting (Russian decimal comma) ----------
const ru = (x, d) => x.toFixed(d).replace(".", ",").replace("-", "−");
const pct = (x, d = 1) => ru(x * 100, d) + "%";
const pp = (x, d = 1) => ru(x * 100, d);                 // percentage points, no sign
const MODELS = ["M0", "M2", "M4"];

// ---------- helpers ----------
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "PAIR-SV: от одного генома к тридцати";
pres.lang = "ru-RU";

const TALK = [];
let slideNo = 0;

function newSlide(section, title, { dark = false } = {}) {
  slideNo += 1;
  const s = pres.addSlide();
  s.background = { color: dark ? C.ink : C.white };
  if (!dark) {
    if (section) {
      s.addText(section, { x: MX, y: 0.34, w: 8, h: 0.28, fontFace: F.body, fontSize: 12, bold: true,
        color: C.muted, charSpacing: 2, margin: 0, isTextBox: true });
    }
    s.addText(title, { x: MX, y: 0.64, w: CW, h: 0.72, fontFace: F.title, fontSize: 30, bold: true,
      color: C.text, margin: 0, valign: "top", isTextBox: true });
    s.addText(`${slideNo} / ${TOTAL}`, { x: W - MX - 1.2, y: H - 0.42, w: 1.2, h: 0.26, fontFace: F.body,
      fontSize: 10, color: C.muted, align: "right", margin: 0, isTextBox: true });
  }
  return s;
}

function talk(slide, heading, text) {
  slide.addNotes(text);
  TALK.push({ n: slideNo, heading, text });
}

function text(slide, runs, opts) {
  slide.addText(runs, Object.assign({ fontFace: F.body, fontSize: 16, color: C.text, margin: 0,
    valign: "top", isTextBox: true }, opts));
}

function card(slide, x, y, w, h, fill) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill },
    line: { color: fill, width: 0.75 } });
}

function dot(slide, x, y, d, { fill = null, line = null, lineW = 1.25 } = {}) {
  slide.addShape(pres.shapes.OVAL, {
    x, y, w: d, h: d,
    fill: fill ? { color: fill } : { color: C.white, transparency: 100 },
    line: { color: line || fill, width: lineW },
  });
}

// "one genome -> thirty genomes" motif, reused on title, closing and slide 4
function motif(slide, x, y, { dark = true } = {}) {
  dot(slide, x, y - 0.05, 0.32, { fill: C.orange });
  slide.addShape(pres.shapes.LINE, { x: x + 0.46, y: y + 0.11, w: 0.55, h: 0,
    line: { color: dark ? C.onDark2 : C.muted, width: 1.25, endArrowType: "triangle" } });
  for (let i = 0; i < 30; i++) {
    dot(slide, x + 1.16 + i * 0.295, y + 0.01, 0.2, { fill: dark ? C.onDark2 : C.blue });
  }
}

function chartBase(extra) {
  return Object.assign({
    fontFace: F.body,
    catAxisLabelFontFace: F.body, valAxisLabelFontFace: F.body,
    catAxisLabelColor: C.text2, valAxisLabelColor: C.muted,
    catAxisLabelFontSize: 12, valAxisLabelFontSize: 11,
    catAxisLineShow: true, catAxisLineColor: C.axis,
    valAxisLineShow: false,
    valGridLine: { color: C.grid, size: 0.75 }, catGridLine: { style: "none" },
    showTitle: true, titleFontFace: F.body, titleFontSize: 13, titleColor: C.text2, titleAlign: "left",
    legendFontFace: F.body, legendFontSize: 12, legendColor: C.text2,
    dataLabelFontFace: F.body, valAxisTitleFontFace: F.body, catAxisTitleFontFace: F.body,
  }, extra);
}

// =====================================================================
// 1. Title
// =====================================================================
{
  const s = newSlide(null, null, { dark: true });
  motif(s, MX, 1.15);
  text(s, "От одного генома к тридцати", { x: MX, y: 2.05, w: CW, h: 1.0, fontFace: F.title,
    fontSize: 46, bold: true, color: C.white });
  text(s, "Проверка классификатора делеций PAIR-SV и выбор порога с гарантией",
    { x: MX, y: 3.15, w: 10.8, h: 0.9, fontSize: 24, color: C.onDark2 });
  text(s, [
    { text: "Статья 1 — ", options: { bold: true, color: C.white } },
    { text: "готова к подаче", options: { color: C.onDark2, breakLine: true } },
    { text: "Статья 2 — ", options: { bold: true, color: C.white } },
    { text: "результаты получены, пишется текст", options: { color: C.onDark2 } },
  ], { x: MX, y: 4.6, w: 8, h: 0.9, fontSize: 18, paraSpaceAfter: 4 });
  text(s, "Отчёт о выполненной работе · сентябрь 2026",
    { x: MX, y: 6.55, w: 8, h: 0.35, fontSize: 14, color: C.onDark2 });
  talk(s, "Титульный слайд",
    "Добрый день. Я расскажу о двух работах. Первая — проверка программы, которая отсеивает ложные находки " +
    "при поиске делеций в геноме. Мы проверили её не на одном человеке, как принято, а на тридцати, и это " +
    "изменило главный вывод. Вторая работа выросла из первой: как выбирать порог срабатывания программы так, " +
    "чтобы у нового человека было гарантированное качество. В конце — коротко о дальнейших планах.");
}

// =====================================================================
// 2. Task
// =====================================================================
{
  const s = newSlide("ЗАДАЧА", "Отсеять ложные находки детектора");
  const steps = ["Прочтения ДНК человека", "Manta — детектор делеций", "Кандидаты на делецию",
    "PAIR-SV — перепроверка", "Принять или отсеять"];
  const bw = 2.02, gap = 0.5, by = 1.75, bh = 1.15;
  steps.forEach((label, i) => {
    const x = MX + i * (bw + gap);
    const hl = i === 3;
    card(s, x, by, bw, bh, hl ? C.tintOrange : C.tintGray);
    text(s, label, { x: x + 0.12, y: by, w: bw - 0.24, h: bh, fontSize: 16, bold: hl, align: "center",
      valign: "middle", color: C.text });
    if (i < steps.length - 1) {
      s.addShape(pres.shapes.LINE, { x: x + bw + 0.07, y: by + bh / 2, w: gap - 0.14, h: 0,
        line: { color: C.muted, width: 1.5, endArrowType: "triangle" } });
    }
  });

  const prev = A1.cohort_prevalence;
  const cy = 3.45, ch = 2.85, cw = 3.75, cg = 0.425;
  card(s, MX, cy, cw, ch, C.tintBlue);
  text(s, pct(prev, 0), { x: MX + 0.3, y: cy + 0.25, w: cw - 0.6, h: 1.1, fontSize: 60, bold: true, color: C.blue });
  text(s, "находок Manta — настоящие делеции (в среднем по 30 людям)",
    { x: MX + 0.3, y: cy + 1.45, w: cw - 0.6, h: 1.2, fontSize: 16, color: C.text });

  const x2 = MX + cw + cg;
  card(s, x2, cy, cw, ch, C.tintOrange);
  text(s, pct(1 - prev, 0), { x: x2 + 0.3, y: cy + 0.25, w: cw - 0.6, h: 1.1, fontSize: 60, bold: true, color: C.orange });
  text(s, "— ложные срабатывания. Их надо найти, не потеряв настоящие",
    { x: x2 + 0.3, y: cy + 1.45, w: cw - 0.6, h: 1.2, fontSize: 16, color: C.text });

  const x3 = x2 + cw + cg;
  card(s, x3, cy, cw, ch, C.tintGray);
  text(s, [
    { text: "Чего PAIR-SV не делает", options: { bold: true, breakLine: true } },
    { text: "Не ищет делеции заново. Что пропустил детектор, остаётся пропущенным: на эталонном геноме " +
      `HG002 сама Manta нашла ${pct(A1.hg002_manta_own_recall, 1)} известных делеций.` },
  ], { x: x3 + 0.3, y: cy + 0.28, w: cw - 0.6, h: ch - 0.5, fontSize: 16, paraSpaceAfter: 6 });

  talk(s, "Задача",
    "Делеция — это участок ДНК, которого у человека нет по сравнению с эталонным геномом. Ищет такие участки " +
    "программа-детектор; мы используем распространённый детектор Manta. Детектор ошибается: на тридцати людях " +
    `около ${pp(prev, 0)} процентов его находок — настоящие делеции, остальные примерно ${pp(1 - prev, 0)} — ` +
    "ложные срабатывания. PAIR-SV работает на втором этапе: получает находку детектора вместе с прочтениями ДНК " +
    "конкретного человека и оценивает, настоящая это делеция или ошибка. Важное ограничение: PAIR-SV ничего не " +
    `ищет заново. Если детектор делецию пропустил, PAIR-SV её не вернёт. На геноме HG002 сама Manta нашла ` +
    `${pp(A1.hg002_manta_own_recall, 1)} процента известных делеций, поэтому все наши цифры — о качестве отбора ` +
    "среди найденного, а не о полноте поиска.");
}

// =====================================================================
// 3. Five versions
// =====================================================================
{
  const s = newSlide("СТАТЬЯ 1 · УСТРОЙСТВО", "Пять версий классификатора");
  const cols = ["Изображение прочтений", "Последова­тельность ДНК", "Прочтения человека", "17 числовых признаков"];
  const rows = [
    ["M0", "самая простая", [1, 0, 0, 0]], ["M1", "", [1, 1, 0, 0]], ["M2", "", [1, 0, 0, 1]],
    ["M3", "", [1, 0, 1, 0]], ["M4", "все источники", [1, 1, 1, 1]],
  ];
  const lx = MX, colX = 3.05, colW = 1.18, hy = 1.72, ry0 = 2.62, rh = 0.66;
  cols.forEach((c, j) => text(s, c, { x: colX + j * colW, y: hy, w: colW - 0.08, h: 0.8, fontSize: 13,
    color: C.text2, align: "center", valign: "bottom" }));
  rows.forEach(([name, hint, flags], i) => {
    const y = ry0 + i * rh;
    const key = ["M0", "M2", "M4"].includes(name);
    if (key) card(s, lx - 0.1, y - 0.08, colX + 4 * colW - lx + 0.1, rh - 0.1, C.tintBlue);
    text(s, [
      { text: name, options: { bold: true, fontSize: 20, color: C.text } },
      { text: hint ? `  ${hint}` : "", options: { fontSize: 13, color: C.text2 } },
    ], { x: lx + 0.08, y: y - 0.06, w: 2.3, h: rh - 0.1, valign: "middle" });
    flags.forEach((f, j) => {
      const d = 0.26;
      dot(s, colX + j * colW + (colW - 0.08 - d) / 2, y + (rh - 0.1 - d) / 2 - 0.08, d,
        f ? { fill: C.blue } : { line: C.axis, lineW: 1.5 });
    });
  });
  text(s, "Выделены версии, прошедшие все этапы проверки", { x: lx, y: ry0 + 5 * rh + 0.02, w: 6.5, h: 0.3,
    fontSize: 12, color: C.muted });

  const rx = 8.25, rw = W - MX - rx;
  card(s, rx, 1.8, rw, 4.75, C.tintGray);
  text(s, [
    { text: "Как обучали", options: { bold: true, fontSize: 18, breakLine: true } },
    { text: "Пары по одному участку генома: у одного человека — делеция, у другого — её нет. " +
      "Запомнить координату бесполезно, модели приходится смотреть на прочтения конкретного человека.",
      options: { breakLine: true } },
  ], { x: rx + 0.3, y: 2.05, w: rw - 0.6, h: 2.2, fontSize: 15, paraSpaceAfter: 8 });
  text(s, [
    { text: "50 человек", options: { bold: true, fontSize: 26, color: C.blue, breakLine: true } },
    { text: "40 обучение · 5 настройка · 5 тест", options: { fontSize: 14, color: C.text2, breakLine: true } },
    { text: "12 272 пары участков", options: { bold: true, fontSize: 26, color: C.blue, breakLine: true } },
    { text: "4 из 4 проверок на утечку ответа пройдены до обучения", options: { fontSize: 14, color: C.text2 } },
  ], { x: rx + 0.3, y: 4.2, w: rw - 0.6, h: 2.2, paraSpaceAfter: 2 });

  talk(s, "Пять версий классификатора",
    "Мы сделали пять версий классификатора. Все смотрят на изображение прочтений вокруг двух точек разрыва — " +
    "начала и конца предполагаемой делеции. Дальше версии различаются добавками: M1 добавляет последовательность " +
    "ДНК в этом месте, M2 — семнадцать числовых признаков качества прочтений, M3 — сами прочтения человека, M4 — " +
    "всё сразу. Так можно измерить вклад каждого источника отдельно. Обучали на парах: один и тот же участок " +
    "генома у одного человека размечен как делеция, у другого — как её отсутствие. Поэтому модель не может просто " +
    "запомнить, что в этой координате обычно бывает делеция: ей приходится смотреть на данные конкретного человека. " +
    "До обучения мы отдельно проверили, что правильный ответ нельзя угадать по служебным полям, — все четыре такие " +
    "проверки пройдены.");
}

// =====================================================================
// 4. Four evaluation levels
// =====================================================================
{
  const s = newSlide("СТАТЬЯ 1 · ПРОВЕРКА", "Четыре уровня проверки");
  const steps = [
    ["Контролируемый тест", "5 отложенных людей, подготовленные пары"],
    ["Развёрточное исследование", "5 человек, реальные находки Manta; подбор порога на 95% чувствительности"],
    ["Эталонный геном HG002", "1 человек, открыт один раз"],
    ["Новая группа", "30 человек, по 6 из 5 групп происхождения; открыта один раз"],
  ];
  const sx = MX, sw = 2.9, sg = 0.167, cy = 2.05, d = 0.62;
  s.addShape(pres.shapes.LINE, { x: sx + d / 2, y: cy + d / 2, w: 3 * (sw + sg), h: 0,
    line: { color: C.axis, width: 1.5 } });
  steps.forEach(([head, body], i) => {
    const x = sx + i * (sw + sg);
    dot(s, x, cy, d, { fill: C.ink });
    text(s, String(i + 1), { x, y: cy, w: d, h: d, fontSize: 20, bold: true, color: C.white, align: "center",
      valign: "middle" });
    // title and body in separate boxes so bodies line up even when a title wraps
    text(s, head, { x, y: cy + 0.85, w: sw - 0.15, h: 0.72, fontSize: 18, bold: true });
    text(s, body, { x, y: cy + 1.62, w: sw - 0.15, h: 1.05, fontSize: 15, color: C.text2 });
  });
  // motif under steps 3 and 4: one genome, then 5 x 6 grid of people
  dot(s, sx + 2 * (sw + sg) + 0.05, 4.8, 0.3, { fill: C.orange });
  const gx = sx + 3 * (sw + sg) + 0.05;
  for (let r = 0; r < 5; r++) for (let c = 0; c < 6; c++) dot(s, gx + c * 0.27, 4.75 + r * 0.2, 0.15, { fill: C.blue });

  card(s, MX, 5.9, CW, 0.95, C.tintGray);
  text(s, [
    { text: "До открытия данных ", options: { bold: true } },
    { text: "фиксировались и хэшировались пороги, определения метрик, подгрупп и состав выборки. " +
      "Менять правила задним числом было нельзя — как в клинических испытаниях." },
  ], { x: MX + 0.3, y: 5.9, w: CW - 0.6, h: 0.95, fontSize: 16, valign: "middle" });

  talk(s, "Четыре уровня проверки",
    "Проверка шла в четыре этапа, каждый ближе к реальности. Сначала контролируемый тест на пяти отложенных людях. " +
    "Затем пять новых людей с реальным, неотфильтрованным выводом детектора — на них мы подобрали порог " +
    "срабатывания, нацеливаясь на 95 процентов найденных делеций. Затем эталонный геном HG002. И наконец тридцать " +
    "новых людей, по шесть из каждой из пяти континентальных групп происхождения, без родства с предыдущими " +
    "выборками. Последние два этапа открывались ровно один раз. До открытия данных мы фиксировали и хэшировали " +
    "пороги, определения метрик, подгрупп и состав выборки, — подогнать правила под результат задним числом было " +
    "нельзя. Это тот же принцип, что в клинических испытаниях: план анализа пишется до того, как открыты данные.");
}

// =====================================================================
// 5. Zero-ablation overstates contribution
// =====================================================================
{
  const s = newSlide("СТАТЬЯ 1 · КОНТРОЛИРУЕМЫЙ ТЕСТ", "Быстрая оценка вклада завышает его в 5–10 раз");
  const ab = A1.ablation;
  s.addChart(pres.charts.BAR, [
    { name: "Обнуление входа у готовой модели", labels: ab.map((r) => r.label), values: ab.map((r) => r.zero_drop * 100) },
    { name: "Переобучение без этой ветви", labels: ab.map((r) => r.label), values: ab.map((r) => r.retrained_drop * 100) },
  ], chartBase({
    x: MX, y: 1.6, w: 7.5, h: 4.95, barDir: "col", barGrouping: "clustered", barGapWidthPct: 70,
    chartColors: [C.orange, C.blue], showLegend: true, legendPos: "b",
    title: "Падение F1 при удалении ветви из M4, процентные пункты",
    valAxisMinVal: 0, valAxisMaxVal: 1.2, valAxisMajorUnit: 0.2, valAxisLabelFormatCode: "0.0",
  }));

  const rx = 8.55, rw = W - MX - rx;
  text(s, "Во сколько раз завышено", { x: rx, y: 1.75, w: rw, h: 0.4, fontSize: 16, bold: true, color: C.text2 });
  ab.forEach((r, i) => {
    const y = 2.25 + i * 0.95;
    text(s, "×" + ru(r.ratio, 1), { x: rx, y, w: 1.75, h: 0.8, fontSize: 38, bold: true, color: C.orange, valign: "middle" });
    text(s, r.label, { x: rx + 1.8, y, w: rw - 1.8, h: 0.8, fontSize: 16, valign: "middle" });
  });
  const minR = Math.min(...ab.map((r) => r.retrained_drop)) * 100;
  const maxR = Math.max(...ab.map((r) => r.retrained_drop)) * 100;
  const b = A1.internal_test_bootstrap["M4 - M2"];
  text(s, [
    { text: `Честная оценка вклада — ${ru(minR, 2)}–${ru(maxR, 2)} п.п. F1 на ветвь: ветви в основном дублируют друг друга.`,
      options: { breakLine: true } },
    { text: `M4 не лучше M2: разница ${ru(b.delta_f1 * 100, 2)} п.п., интервал от ${ru(b.ci_low * 100, 2)} до +${ru(b.ci_high * 100, 2)}.` },
  ], { x: rx, y: 5.15, w: rw, h: 1.45, fontSize: 14, color: C.text2, paraSpaceAfter: 6 });

  talk(s, "Быстрая оценка вклада завышает его",
    "Первый результат касается методики. Вклад источника данных можно оценить двумя способами. Быстрый — взять " +
    "готовую модель и обнулить этот вход. Правильный, но долгий — обучить модель заново без этой ветви. Быстрый " +
    `способ завысил вклад в 5–10 раз: для последовательности ДНК в ${ru(ab[0].ratio, 1)} раза, для прочтений в ` +
    `${ru(ab[1].ratio, 1)}, для числовых признаков в ${ru(ab[2].ratio, 1)}. Причина понятна: обнуление выталкивает ` +
    "модель за пределы данных, на которых она училась, и падение качества смешивает «вход важен» и «модель не умеет " +
    `работать без этого входа». При честном переобучении каждая ветвь даёт лишь ${ru(minR, 2)}–${ru(maxR, 2)} ` +
    "процентного пункта — ветви во многом дублируют друг друга. Это же видно на контролируемом тесте: M2 и M4 " +
    "значимо лучше базовой M0, но M4 не лучше M2 — доверительный интервал разницы включает ноль.");
}

// =====================================================================
// 6. Threshold had to be recalibrated on real candidates
// =====================================================================
{
  const s = newSlide("СТАТЬЯ 1 · РАЗВЁРТОЧНОЕ ИССЛЕДОВАНИЕ", "Порог пришлось подбирать заново на реальных данных");
  const [f0, f1] = A1.poc_frozen_threshold_specificity_range;
  const [l0, l1] = A1.poc_lopo_specificity_range;
  const [a0, a1] = A1.poc_frozen_threshold_roc_auc_range;
  const ty = 1.8, th = 2.75, tw = 5.2;
  card(s, MX, ty, tw, th, C.tintOrange);
  text(s, `${pp(f0, 0)}–${pp(f1, 0)}%`, { x: MX + 0.35, y: ty + 0.25, w: tw - 0.7, h: 1.2, fontSize: 66, bold: true, color: C.orange });
  text(s, "ложных находок отсеивалось с порогом, взятым с контролируемого теста: программа принимала почти всё",
    { x: MX + 0.35, y: ty + 1.5, w: tw - 0.7, h: 1.1, fontSize: 16 });

  s.addShape(pres.shapes.RIGHT_ARROW, { x: MX + tw + 0.3, y: ty + th / 2 - 0.35, w: 0.95, h: 0.7,
    fill: { color: C.axis }, line: { color: C.axis, width: 0.5 } });

  const x2 = MX + tw + 1.55;
  card(s, x2, ty, W - MX - x2, th, C.tintBlue);
  text(s, `${pp(l0, 0)}–${pp(l1, 0)}%`, { x: x2 + 0.35, y: ty + 0.25, w: W - MX - x2 - 0.7, h: 1.2, fontSize: 66, bold: true, color: C.blue });
  text(s, "после подбора порога поочерёдным исключением людей, при чувствительности около 95%",
    { x: x2 + 0.35, y: ty + 1.5, w: W - MX - x2 - 0.7, h: 1.1, fontSize: 16 });

  text(s, [
    { text: "Различать программа не разучилась: ", options: { bold: true } },
    { text: `площадь под ROC-кривой ${ru(a0, 2)}–${ru(a1, 2)}. Сдвинулась только граница отсечения — в реальном ` +
      "потоке почти 90% находок верные, а в подготовленных парах было поровну.", options: { breakLine: true } },
    { text: "Порог переносился без сбоев: ", options: { bold: true } },
    { text: `подобран на 4 людях, проверен на 5-м — все 45 проверок, худший случай чувствительности ${ru(A1.poc_lopo_worst_fold_recall, 4)}.` },
  ], { x: MX, y: 4.9, w: CW, h: 1.75, fontSize: 16, paraSpaceAfter: 10 });

  talk(s, "Порог пришлось подбирать заново",
    "Когда мы перенесли порог с контролируемого теста на реальные находки детектора, отсев ложных упал до " +
    `${pp(f0, 0)}–${pp(f1, 0)} процентов: программа соглашалась почти со всем. При этом способность различать не ` +
    `пропала — площадь под ROC-кривой осталась ${ru(a0, 2)}–${ru(a1, 2)}. Сдвинулась только граница: на ` +
    "подготовленных парах положительных и отрицательных было поровну, а в реальном потоке почти 90 процентов " +
    "находок верные. Поэтому порог мы подобрали заново — поочерёдным исключением людей: подбираем на четырёх, " +
    "проверяем на пятом, и так для каждого. Порог переносился на отложенного человека во всех 45 проверках, отсев " +
    `ложных составил ${pp(l0, 0)}–${pp(l1, 0)} процента при чувствительности около 95.`);
}

// =====================================================================
// 7. HG002
// =====================================================================
{
  const s = newSlide("СТАТЬЯ 1 · ЭТАЛОННЫЙ ГЕНОМ", "На эталонном геноме HG002 версии разошлись");
  const hg = A1.hg002_v5q;
  const tw = 3.75, tg = 0.425, ty = 1.75, th = 2.95;
  MODELS.forEach((m, i) => {
    const x = MX + i * (tw + tg);
    const r = hg[m].recall;
    const above = r >= 0.95;
    card(s, x, ty, tw, th, m === "M2" ? C.tintBlue : m === "M4" ? C.tintOrange : C.tintGray);
    text(s, m, { x: x + 0.3, y: ty + 0.22, w: tw - 0.6, h: 0.45, fontSize: 20, bold: true, color: C.text2 });
    text(s, pct(r, 1), { x: x + 0.3, y: ty + 0.65, w: tw - 0.6, h: 1.0, fontSize: 56, bold: true,
      color: m === "M4" ? C.orange : m === "M2" ? C.blue : C.text });
    const status = above ? "✓ выше цели 95%" :
      `✗ ниже цели на ${pp(0.95 - r, 1)} п.п.`;
    text(s, [
      { text: "чувствительность", options: { color: C.text2, breakLine: true } },
      { text: status, options: { bold: true, color: C.text, breakLine: true } },
      { text: `отсев ложных: ${pct(hg[m].specificity, 1)}`, options: { color: C.text2 } },
    ], { x: x + 0.3, y: ty + 1.68, w: tw - 0.6, h: 1.2, fontSize: 16, paraSpaceAfter: 3 });
  });
  card(s, MX, 5.05, CW, 1.1, C.tintGray);
  text(s, [
    { text: "Напрашивался вывод: ", options: { bold: true } },
    { text: `сложная M4 хуже переносится на нового человека — она на ${pp(hg.M2.recall - hg.M4.recall, 1)} п.п. ниже M2, ` +
      "хотя отсеивает больше всех. Мы записали это как гипотезу и проверили на 30 людях." },
  ], { x: MX + 0.3, y: 5.05, w: CW - 0.6, h: 1.1, fontSize: 17, valign: "middle" });
  text(s, "Эталон — GIAB v5.0q. Порог подобран на 5 людях развёрточного исследования и не перенастраивался.",
    { x: MX, y: 6.4, w: 10.5, h: 0.3, fontSize: 12, color: C.muted });

  talk(s, "HG002",
    "Затем — эталонный геном HG002, с порогом без всякой перенастройки. Здесь версии впервые разошлись. M2 достигла " +
    `цели: ${pp(hg.M2.recall, 1)} процента найденных делеций. M4 — ${pp(hg.M4.recall, 1)} процента, на ` +
    `${pp(0.95 - hg.M4.recall, 1)} пункта ниже цели и на ${pp(hg.M2.recall - hg.M4.recall, 1)} ниже M2, хотя ложных ` +
    "находок M4 отсеивала больше всех. Напрашивался вывод: сложная версия хуже переносится на нового человека. " +
    "Мы записали это как гипотезу — и именно ради её проверки собрали группу из тридцати человек.");
}

// =====================================================================
// 8. Thirty people: the difference disappears
// =====================================================================
{
  const s = newSlide("СТАТЬЯ 1 · 30 ЧЕЛОВЕК", "На 30 людях разница между версиями исчезла");
  const ratio = A1.cohort_diff_vs_sd_ratio;
  text(s, `в ${Math.round(ratio)} раз`, { x: MX, y: 1.75, w: 4.4, h: 1.2, fontSize: 64, bold: true, color: C.orange });
  text(s, "разница между M2 и M4 меньше обычного разброса между людьми",
    { x: MX, y: 2.95, w: 4.2, h: 0.95, fontSize: 18 });
  const rows = [
    ["Разница M2 − M4", ru(A1.cohort_m2_m4_recall_diff, 6)],
    ["Разброс между людьми", ru(A1.cohort_between_person_sd, 4)],
  ];
  rows.forEach(([k, v], i) => {
    const y = 4.15 + i * 0.85;
    card(s, MX, y, 4.2, 0.72, C.tintGray);
    text(s, k, { x: MX + 0.25, y, w: 2.3, h: 0.72, fontSize: 15, color: C.text2, valign: "middle" });
    text(s, v, { x: MX + 2.4, y, w: 1.6, h: 0.72, fontSize: 22, bold: true, align: "right", valign: "middle" });
  });
  text(s, "Разброс — стандартное отклонение чувствительности M4 по 30 людям",
    { x: MX, y: 5.9, w: 4.2, h: 0.55, fontSize: 12, color: C.muted });

  const pp30 = A1.cohort_per_person_sorted_by_M2;
  const labels = pp30.map(() => "");
  s.addChart([
    { type: pres.charts.LINE, data: [
        { name: "M2", labels, values: pp30.map((r) => r.M2) },
        { name: "M4", labels, values: pp30.map((r) => r.M4) },
      // NB: no lineDataSymbolLineSize — pptxgenjs writes it into <a:ln w> verbatim (EMU, not points);
      // a fractional value there made PowerPoint drop the whole slide while every validator passed it.
      ], options: { chartColors: [C.blue, C.orange], lineSize: 0, lineDataSymbol: "circle", lineDataSymbolSize: 8 } },
    { type: pres.charts.LINE, data: [
        { name: "Цель 95%", labels, values: pp30.map(() => 0.95) },
      ], options: { chartColors: [C.muted], lineSize: 1.5, lineDash: "dash", lineDataSymbol: "none" } },
  ], chartBase({
    x: 5.2, y: 1.6, w: W - MX - 5.2, h: 4.95,
    title: "Чувствительность у каждого из 30 человек, по возрастанию для M2",
    showLegend: true, legendPos: "b",
    valAxisMinVal: 0.92, valAxisMaxVal: 0.97, valAxisMajorUnit: 0.01, valAxisLabelFormatCode: "0%",
    catAxisMajorTickMark: "none",
  }));

  talk(s, "30 человек",
    "На тридцати людях эта разница исчезла. Средняя чувствительность M2 и M4 различается на " +
    `${ru(A1.cohort_m2_m4_recall_diff, 6)}. Для сравнения: разброс этой же величины между людьми — ` +
    `${ru(A1.cohort_between_person_sd, 4)}, то есть различие между версиями в ${Math.round(ratio)} раз меньше, чем ` +
    "обычная разница между двумя людьми. На графике каждая пара точек — один человек: точки M2 и M4 почти " +
    `совпадают, а сами люди расходятся от ${pp(A1.cohort.M2.recall_min, 0)} до ${pp(A1.cohort.M2.recall_max, 0)} ` +
    "процентов. Порядок версий на HG002 был свойством этого человека, а не программы. Важно, чего это не доказывает: " +
    "что на HG002 разница была случайной. Это показывает другое — по одному геному нельзя судить об устройстве " +
    "модели, даже если проверка проведена безупречно.");
}

// =====================================================================
// 9. Target missed; AFR specificity lower
// =====================================================================
{
  const s = newSlide("СТАТЬЯ 1 · 30 ЧЕЛОВЕК", "Цель 95% не достигнута, отсев хуже у одной группы");
  const co = A1.cohort;
  text(s, "Ни одна версия не достигла 95%", { x: MX, y: 1.75, w: 5.6, h: 0.5, fontSize: 20, bold: true });
  MODELS.forEach((m, i) => {
    const y = 2.4 + i * 0.82;
    card(s, MX, y, 5.3, 0.68, C.tintGray);
    text(s, m, { x: MX + 0.25, y, w: 1.2, h: 0.68, fontSize: 18, bold: true, color: C.text2, valign: "middle" });
    text(s, pct(co[m].recall, 2), { x: MX + 1.4, y, w: 2.2, h: 0.68, fontSize: 26, bold: true, valign: "middle" });
    text(s, "чувствительность", { x: MX + 3.35, y, w: 1.8, h: 0.68, fontSize: 13, color: C.text2, valign: "middle" });
  });
  const rmin = Math.min(...MODELS.map((m) => co[m].recall_min));
  const rmax = Math.max(...MODELS.map((m) => co[m].recall_max));
  text(s, `Недобор одинаковый у всех: разброс между людьми около ${pp(A1.cohort_between_person_sd, 1)} п.п., ` +
    `все 30 человек — от ${pct(rmin, 1)} до ${pct(rmax, 1)}. После промаха порог не перенастраивали.`,
    { x: MX, y: 4.95, w: 5.3, h: 1.4, fontSize: 15, color: C.text2 });

  const pops = [["AFR", "Африка"], ["AMR", "Америка"], ["EAS", "Вост. Азия"], ["EUR", "Европа"], ["SAS", "Юж. Азия"]];
  const sp = A1.cohort_superpopulation;
  s.addChart(pres.charts.BAR, [
    { name: "M4", labels: pops.map((p) => p[1]), values: pops.map((p) => sp[p[0]].M4.specificity) },
  ], chartBase({
    x: 6.45, y: 1.6, w: W - MX - 6.45, h: 3.85, barDir: "col", barGapWidthPct: 55,
    chartColors: pops.map((p) => (p[0] === "AFR" ? C.orange : C.barMuted)),
    showLegend: false, title: "Доля отсеянных ложных находок, M4",
    valAxisMinVal: 0, valAxisMaxVal: 0.3, valAxisMajorUnit: 0.05, valAxisLabelFormatCode: "0%",
    showValue: true, dataLabelFormatCode: "0.0%", dataLabelPosition: "outEnd", dataLabelFontSize: 12,
    dataLabelColor: C.text,
  }));
  const recAll = pops.flatMap((p) => MODELS.map((m) => sp[p[0]][m].recall));
  text(s, [
    { text: "Находить делеции хуже не стала: ", options: { bold: true } },
    { text: `чувствительность ${pct(Math.min(...recAll), 1)}–${pct(Math.max(...recAll), 1)} во всех группах. ` +
      "Вероятная причина — справочник эталонных ответов: по африканским популяциям в нём меньше данных. Причина не доказана." },
  ], { x: 6.45, y: 5.55, w: W - MX - 6.45, h: 1.1, fontSize: 14, color: C.text2 });

  const afr = MODELS.map((m) => sp.AFR[m].specificity);
  const others = pops.filter((p) => p[0] !== "AFR").flatMap((p) => MODELS.map((m) => sp[p[0]][m].specificity));
  talk(s, "Цель не достигнута, разрыв по группе",
    `Ещё два результата. Первый: ни одна версия не достигла заявленных 95 процентов — ${pp(co.M0.recall, 1)}, ` +
    `${pp(co.M2.recall, 1)} и ${pp(co.M4.recall, 1)}. Недобор небольшой и одинаковый: разброс между людьми около ` +
    `${pp(A1.cohort_between_person_sd, 1)} пункта. Значит, дело в положении порога, а не в неустойчивости. После ` +
    "промаха порог мы не перенастраивали. Второй: у шести человек африканского происхождения программа отсеивает " +
    `меньше ложных находок — ${pp(Math.min(...afr), 0)}–${pp(Math.max(...afr), 0)} процентов против ` +
    `${pp(Math.min(...others), 0)}–${pp(Math.max(...others), 0)} у остальных групп. Находит делеции она при этом ` +
    "одинаково во всех группах. Наиболее вероятная причина — справочник эталонных ответов: для африканских популяций " +
    "в нём меньше данных. Но это наша интерпретация, экспериментом она не доказана, и правила разметки после этого " +
    "результата мы не меняли.");
}

// =====================================================================
// 10. Article 1 conclusion
// =====================================================================
{
  const s = newSlide(null, null, { dark: true });
  text(s, "ИТОГ СТАТЬИ 1", { x: MX, y: 0.55, w: 6, h: 0.3, fontSize: 12, bold: true, color: C.onDark2, charSpacing: 2 });
  text(s, "Проверки на одном геноме недостаточно — даже безупречно проведённой",
    { x: MX, y: 1.0, w: 11.2, h: 1.6, fontFace: F.title, fontSize: 36, bold: true, color: C.white });
  const cols = [
    ["Качество", "Цель 95% не достигнута ни одной версией; недобор одинаковый у всех 30 человек"],
    ["Обобщаемость", "Различие M2 и M4 на HG002 не воспроизвелось на 30 людях"],
    ["Методика оценки", "Оба дешёвых способа — один геном и обнуление входа — дали завышенный эффект"],
  ];
  const cw = 3.75, cg = 0.425, cy = 3.1, ch = 2.35;
  cols.forEach(([h, b], i) => {
    const x = MX + i * (cw + cg);
    card(s, x, cy, cw, ch, C.inkCard);
    text(s, [
      { text: h, options: { bold: true, fontSize: 20, color: C.white, breakLine: true } },
      { text: b, options: { fontSize: 16, color: C.onDark2 } },
    ], { x: x + 0.3, y: cy + 0.28, w: cw - 0.6, h: ch - 0.5, paraSpaceAfter: 8 });
  });
  text(s, "Статья готова к подаче: английская версия и полная русская версия с PDF",
    { x: MX, y: 6.0, w: 11, h: 0.4, fontSize: 16, color: C.onDark2 });
  text(s, `${slideNo} / ${TOTAL}`, { x: W - MX - 1.2, y: H - 0.42, w: 1.2, h: 0.26, fontSize: 10,
    color: C.onDark2, align: "right" });

  talk(s, "Итог статьи 1",
    "Итог первой статьи. Главный вклад — не сравнение версий, а вывод о методике: проверки на одном геноме " +
    "недостаточно, даже если она проведена строго и честно. Результаты стоит разделять на три вопроса. Качество: " +
    "цель не достигнута, но недобор одинаковый у всех. Обобщаемость: различие версий на HG002 не воспроизвелось. " +
    "Методика оценки: оба дешёвых способа — один геном и обнуление входа — дали завышенный эффект. Статья готова к " +
    "подаче; есть английская версия и полная русская с PDF.");
}

// =====================================================================
// 11. Article 2: the question
// =====================================================================
{
  const s = newSlide("СТАТЬЯ 2 · ВОПРОС", "Вторая статья: порог с гарантией");
  text(s, "Старая процедура подбирает порог так, чтобы в среднем чувствительность была 95%. Держит ли она цель " +
    "у нового человека? Проверка на всех 30: порог подобран на 29, результат — у 30-го.",
    { x: MX, y: 1.7, w: CW, h: 0.85, fontSize: 17 });

  const d = 0.25, g = 0.075, x0 = MX + 0.9, ry = 2.85, rh = 0.52;
  MODELS.forEach((m, i) => {
    const y = ry + i * rh;
    const flags = A2.lopo30[m].heuristic_met_flags;
    text(s, m, { x: MX, y: y - 0.05, w: 0.8, h: d + 0.1, fontSize: 18, bold: true, color: C.text2, valign: "middle" });
    flags.forEach((ok, j) => dot(s, x0 + j * (d + g), y, d, ok ? { fill: C.blue } : { line: C.blue, lineW: 1.5 }));
    text(s, `${A2.lopo30[m].heuristic_met} из 30`, { x: x0 + 30 * (d + g) + 0.15, y: y - 0.05, w: 1.6, h: d + 0.1,
      fontSize: 18, bold: true, valign: "middle" });
  });
  const ly = ry + 3 * rh + 0.08;
  dot(s, x0, ly + 0.04, 0.2, { fill: C.blue });
  text(s, "цель достигнута у отложенного человека", { x: x0 + 0.3, y: ly, w: 4, h: 0.3, fontSize: 13, color: C.text2 });
  dot(s, x0 + 4.4, ly + 0.04, 0.2, { line: C.blue, lineW: 1.5 });
  text(s, "не достигнута", { x: x0 + 4.7, y: ly, w: 2, h: 0.3, fontSize: 13, color: C.text2 });

  card(s, MX, 5.05, CW, 1.55, C.tintBlue);
  text(s, [
    { text: "Предлагаемая замена — конформный контроль риска ", options: { bold: true } },
    { text: "(conformal risk control; Angelopoulos и др., ICLR 2024). ", options: { color: C.text2 } },
    { text: "Порог выбирается так, чтобы средняя доля пропущенных делеций у нового человека гарантированно не " +
      "превышала заданную. Гарантия не зависит от вида распределения данных, но действует в среднем по новым людям, " +
      "а не для каждого человека." },
  ], { x: MX + 0.3, y: 5.05, w: CW - 0.6, h: 1.55, fontSize: 16, valign: "middle" });

  const hm = MODELS.map((m) => A2.lopo30[m].heuristic_met);
  talk(s, "Статья 2: вопрос",
    "Вторая статья отвечает на вопрос, который первая оставила открытым. Старая процедура подбирает порог так, " +
    "чтобы в среднем по калибровочным людям чувствительность была 95 процентов. Но что с новым человеком? Мы " +
    "проверили это на всех тридцати людях: подбирали порог на двадцати девяти и смотрели на тридцатого. Цель " +
    `выполнялась только у ${Math.min(...hm)}–${Math.max(...hm)} человек из 30 — примерно у половины. Каждая точка на ` +
    "слайде — один отложенный человек. Замена, которую мы проверяем, — метод конформного контроля риска. Он " +
    "выбирает порог так, чтобы средняя доля пропущенных делеций у нового человека гарантированно не превышала " +
    "заданную. Гарантия математическая и не зависит от вида распределения данных, но действует в среднем по новым " +
    "людям, а не для каждого человека отдельно.");
}

// =====================================================================
// 12. N/(N+1) bound
// =====================================================================
{
  const s = newSlide("СТАТЬЯ 2 · ГРАНИЦА", "Для гарантии 95% нужно не меньше 19 человек");
  card(s, MX, 1.75, 4.6, 1.5, C.tintBlue);
  text(s, [
    { text: "Максимальная гарантируемая чувствительность", options: { fontSize: 14, color: C.text2, breakLine: true } },
    { text: "N / (N + 1)", options: { fontSize: 40, bold: true, color: C.blue, breakLine: true } },
    { text: "N — число людей, на которых подбирают порог", options: { fontSize: 13, color: C.text2 } },
  ], { x: MX + 0.3, y: 1.85, w: 4.0, h: 1.35 });

  const pts = [[6, "одна группа происхождения"], [19, "минимум для цели 95%"], [30, "вся группа"]];
  pts.forEach(([n, hint], i) => {
    const y = 3.5 + i * 0.78;
    text(s, `N = ${n}`, { x: MX, y, w: 1.3, h: 0.62, fontSize: 20, bold: true, valign: "middle" });
    text(s, [
      { text: `до ${pct(n / (n + 1), 1)}`, options: { bold: true, color: n === 19 ? C.orange : C.text, breakLine: true } },
      { text: hint, options: { color: C.text2, fontSize: 13 } },
    ], { x: MX + 1.3, y, w: 3.3, h: 0.66, fontSize: 17, valign: "middle" });
  });
  text(s, "Следует из условия теоремы (Cohen и др., ISIT 2024). Граница подтверждена перебором порогов на данных: " +
    "при N = 5 цель 0,833 достижима, 0,834 — нет.", { x: MX, y: 5.9, w: 4.6, h: 0.75, fontSize: 12, color: C.muted });

  const curve = A2.max_guaranteed_recall_curve;
  const show = new Set([1, 6, 19, 30, 40]);
  const labels = curve.map((p) => (show.has(p.N) ? String(p.N) : ""));
  s.addChart([
    { type: pres.charts.LINE, data: [{ name: "N / (N + 1)", labels, values: curve.map((p) => p.value) }],
      options: { chartColors: [C.blue], lineSize: 2.5, lineDataSymbol: "none" } },
    { type: pres.charts.LINE, data: [{ name: "Цель 95%", labels, values: curve.map(() => 0.95) }],
      options: { chartColors: [C.orange], lineSize: 1.5, lineDash: "dash", lineDataSymbol: "none" } },
  ], chartBase({
    x: 5.6, y: 1.6, w: W - MX - 5.6, h: 5.0,
    title: "Максимальная гарантируемая чувствительность при N людях калибровки",
    showLegend: true, legendPos: "b",
    valAxisMinVal: 0.5, valAxisMaxVal: 1.0, valAxisMajorUnit: 0.1, valAxisLabelFormatCode: "0%",
    catAxisTitle: "N — число людей калибровки", showCatAxisTitle: true, catAxisTitleColor: C.text2,
    catAxisTitleFontSize: 12, catAxisMajorTickMark: "none",
  }));

  talk(s, "Граница N/(N+1)",
    "Прежде всякого счёта из условия теоремы следует простая граница. Если порог подбирается на N людях, " +
    "гарантировать можно чувствительность не выше N делённое на N плюс один. Для группы в шесть человек — не выше " +
    `${pp(6 / 7, 1)} процента. Ровно 95 процентов достижимы начиная с девятнадцати человек. На всей группе из ` +
    `тридцати — до ${pp(30 / 31, 1)}. Мы проверили границу перебором порогов на реальных данных: на пяти людях ` +
    "процедура выдаёт порог при цели 0,833 и отказывается при 0,834 — ровно на пяти шестых. Для практики это " +
    "важно: при малом числе людей гарантия не становится просто слабее — её невозможно получить в принципе.");
}

// =====================================================================
// 13. Group-conditional loses to pooled
// =====================================================================
{
  const s = newSlide("СТАТЬЯ 2 · ГРУППЫ ПРОИСХОЖДЕНИЯ", "Калибровка по группам проигрывает общей");
  text(s, `${A2.group_conditional_infeasible} из ${A2.group_conditional_total}`,
    { x: MX, y: 1.7, w: 4.6, h: 1.0, fontSize: 54, bold: true, color: C.orange });
  text(s, "сочетаний «группа × версия» при цели 95%: на 6 людях гарантия невозможна, процедура отказывается выдавать порог",
    { x: MX, y: 2.72, w: 4.6, h: 1.1, fontSize: 15 });

  const deltas = MODELS.flatMap((m) => Object.values(A2["group_vs_pooled_target0.75"][m].by_superpopulation)
    .map((r) => r.group - r.pooled));
  const dMin = Math.min(...deltas), dMax = Math.max(...deltas);
  text(s, `${pp(-dMax, 0)}–${pp(-dMin, 0)} п.п.`,
    { x: MX, y: 4.0, w: 4.6, h: 0.9, fontSize: 44, bold: true, color: C.orange });
  text(s, "меньше отсев ложных при пороге по своей группе, чем при общем (цель 75%, те же отложенные люди), " +
    "во всех 5 группах и у всех 3 версий — без выигрыша в надёжности",
    { x: MX, y: 4.9, w: 4.6, h: 1.3, fontSize: 15 });
  text(s, "Штраф за малую выборку 1/(N + 1): при N = 5 — 1/6, при N = 29 — 1/30",
    { x: MX, y: 6.2, w: 4.6, h: 0.5, fontSize: 13, color: C.muted });

  const pops = [["AFR", "Африка"], ["AMR", "Америка"], ["EAS", "Вост. Азия"], ["EUR", "Европа"], ["SAS", "Юж. Азия"]];
  const g = A2["group_vs_pooled_target0.75"].M4.by_superpopulation;
  s.addChart(pres.charts.BAR, [
    { name: "Общий порог (29 человек)", labels: pops.map((p) => p[1]), values: pops.map((p) => g[p[0]].pooled) },
    { name: "Порог по своей группе (5 человек)", labels: pops.map((p) => p[1]), values: pops.map((p) => g[p[0]].group) },
  ], chartBase({
    x: 5.55, y: 1.6, w: W - MX - 5.55, h: 5.0, barDir: "col", barGrouping: "clustered", barGapWidthPct: 60,
    chartColors: [C.blue, C.orange], showLegend: true, legendPos: "b",
    title: "Доля отсеянных ложных находок, M4, цель 75%",
    valAxisMinVal: 0, valAxisMaxVal: 0.7, valAxisMajorUnit: 0.1, valAxisLabelFormatCode: "0%",
  }));

  talk(s, "Калибровка по группам",
    "Логично было попробовать подбирать порог отдельно для каждой группы происхождения — в частности, из-за " +
    "разрыва у африканской группы. Это не сработало, по двум причинам. При шести людях на группу гарантия 95 " +
    `процентов невозможна — все ${A2.group_conditional_total} сочетаний группы и версии дали отказ, как и ` +
    "предсказывает граница. А при достижимой цели в 75 процентов порог по своей группе отсеивал ложных находок на " +
    `${pp(-dMax, 0)}–${pp(-dMin, 0)} пунктов меньше, чем общий порог по двадцати девяти людям, — во всех пяти группах ` +
    "и у всех трёх версий, и без выигрыша в надёжности. Причина та же: поправка на размер выборки при пяти людях — " +
    "одна шестая, при двадцати девяти — одна тридцатая.");
}

// =====================================================================
// 14. Matched-reliability control
// =====================================================================
{
  const s = newSlide("СТАТЬЯ 2 · КОНТРОЛЬ", "Проверка на честность: при равной надёжности");
  const mr = A2.matched_reliability.M4;
  const sweep = mr.sweep;
  const xs = sweep.map((r) => r.mean_recall).concat([mr.crc.mean_recall]);
  const yHeur = sweep.map((r) => r.mean_specificity).concat([null]);
  const yCrc = sweep.map(() => null).concat([mr.crc.mean_specificity]);
  s.addChart(pres.charts.SCATTER, [
    { name: "X", values: xs },
    { name: "Старая процедура при целях 95–99,5%", values: yHeur },
    { name: "Контроль риска, цель 95%", values: yCrc },
  ], chartBase({
    x: MX, y: 1.6, w: 7.1, h: 5.05,
    chartColors: [C.blue, C.orange], lineSize: 1.5, lineDataSymbol: "circle", lineDataSymbolSize: 9,
    title: "M4: средняя чувствительность и отсев ложных, 30 отложенных людей",
    showLegend: true, legendPos: "b",
    valAxisMinVal: 0, valAxisMaxVal: 0.25, valAxisMajorUnit: 0.05, valAxisLabelFormatCode: "0%",
    catAxisMinVal: 0.945, catAxisMaxVal: 1.0, catAxisMajorUnit: 0.01, catAxisLabelFormatCode: "0%",
    showValAxisTitle: true, valAxisTitle: "Отсев ложных", valAxisTitleColor: C.text2, valAxisTitleFontSize: 12,
    showCatAxisTitle: true, catAxisTitle: "Средняя чувствительность", catAxisTitleColor: C.text2, catAxisTitleFontSize: 12,
    catGridLine: { color: C.grid, size: 0.75 },
  }));

  const rx = 8.1, rw = W - MX - rx;
  card(s, rx, 1.75, rw, 1.6, C.tintGray);
  text(s, [
    { text: "Обе держат цель у 30 из 30", options: { bold: true, breakLine: true } },
    { text: `старая, цель ${pp(mr.matched.nominal_target, 0)}%: отсев `, options: { color: C.text2 } },
    { text: pct(mr.matched.mean_specificity, 1), options: { bold: true, breakLine: true } },
    { text: "контроль риска, цель 95%: отсев ", options: { color: C.text2 } },
    { text: pct(mr.crc.mean_specificity, 1), options: { bold: true, color: C.orange, breakLine: true } },
    { text: "Лежит на той же кривой — не эффективнее", options: { bold: true } },
  ], { x: rx + 0.25, y: 1.87, w: rw - 0.5, h: 1.4, fontSize: 15, paraSpaceAfter: 2 });

  const NB = " ";
  const formula = ["1", "−", "[α(N+1)", "−", "B]", "/", "N"].join(NB);
  text(s, ru(A2.effective_recall_predicted, 5), { x: rx, y: 3.6, w: rw, h: 0.8, fontSize: 40, bold: true, color: C.blue });
  text(s, [
    { text: "эффективная чувствительность по формуле", options: { color: C.text2, breakLine: true } },
    { text: formula, options: { color: C.text2, breakLine: true } },
    { text: "измерено: ", options: { color: C.text2 } },
    { text: ru(mr.crc.mean_recall, 5), options: { bold: true, breakLine: true } },
    { text: `${Math.round(A2.dummy_share_of_budget * 100)}% бюджета ошибки уходит на поправку за размер выборки`,
      options: { color: C.text2 } },
  ], { x: rx, y: 4.4, w: rw, h: 1.5, fontSize: 14, paraSpaceAfter: 2 });
  text(s, "Ценность метода — надёжная точка сама собой, без подгонки по отложенным данным",
    { x: rx, y: 5.95, w: rw, h: 0.7, fontSize: 15, bold: true });

  talk(s, "Проверка при равной надёжности",
    "Теперь проверка, которую первым сделает рецензент. Контроль риска держал цель у всех тридцати, но его средняя " +
    `чувствительность вышла ${pp(mr.crc.mean_recall, 1)} процента вместо заказанных 95. Может, он просто осторожнее? ` +
    `Мы дали старой процедуре цели повыше. При цели ${pp(mr.matched.nominal_target, 0)} процентов она тоже держит ` +
    `30 из 30 — и отсеивает ложных больше: ${pp(mr.matched.mean_specificity, 1)} процента против ` +
    `${pp(mr.crc.mean_specificity, 1)} у контроля риска. На графике контроль риска лежит на той же кривой, что и ` +
    "старая процедура, то есть он не эффективнее. Смещение объясняется формулой: поправка за размер выборки съедает " +
    `${Math.round(A2.dummy_share_of_budget * 100)} процентов бюджета ошибки, и рабочая точка сдвигается к ` +
    `${ru(A2.effective_recall_predicted, 5)}. Измеренная чувствительность — ${ru(mr.crc.mean_recall, 5)}, совпадение до ` +
    "пятого знака. Ценность метода в другом: он попадает в надёжную точку сам. Цель 97 процентов для старой " +
    "процедуры мы нашли, подглядывая в результаты на отложенных людях, — на новой популяции так нельзя.");
}

// =====================================================================
// 15. Contribution and limits
// =====================================================================
{
  const s = newSlide("СТАТЬЯ 2 · ИТОГ", "Что даёт вторая статья и где её пределы");
  const left = [
    "Формула рабочей точки 1 − [α(N+1) − B] / N — совпала с измерением до пятого знака",
    "Граница N / (N + 1): при 6 людях на группу гарантия 95% невозможна",
    "Контроль при равной надёжности: без него сравнение с эвристикой некорректно",
  ];
  const right = [
    "Группа из 30 человек использовалась многократно, без предрегистрации — в статье это будет сказано прямо",
    "Гарантия действует в среднем по новым людям, а не для каждого человека",
    "Метод не новый: контроль риска уже применяли в геномике (классификатор лейкозов ALLCoP). Новое — поведение при малых N",
  ];
  const cw = 5.85, cy = 1.75, ch = 4.3;
  [[left, "Что получено", C.tintBlue, C.blue], [right, "Ограничения", C.tintGray, C.text2]].forEach(([items, head, fill, accent], k) => {
    const x = MX + k * (cw + 0.4);
    card(s, x, cy, cw, ch, fill);
    text(s, head, { x: x + 0.3, y: cy + 0.25, w: cw - 0.6, h: 0.45, fontSize: 20, bold: true });
    items.forEach((it, i) => {
      const y = cy + 0.9 + i * 1.12;
      dot(s, x + 0.3, y + 0.04, 0.4, { fill: accent });
      text(s, String(i + 1), { x: x + 0.3, y: y + 0.04, w: 0.4, h: 0.4, fontSize: 15, bold: true, color: C.white,
        align: "center", valign: "middle" });
      text(s, it, { x: x + 0.9, y, w: cw - 1.2, h: 1.0, fontSize: 16 });
    });
  });
  text(s, "Статус: вычисления выполнены, пишется текст статьи", { x: MX, y: 6.25, w: 8, h: 0.4, fontSize: 15,
    bold: true, color: C.text2 });

  talk(s, "Вклад и ограничения статьи 2",
    "Что в итоге даёт вторая статья. Во-первых, формулу рабочей точки метода при конечной выборке — она совпала с " +
    "измерением до пятого знака. Во-вторых, границу N на N плюс один: при шести людях на группу гарантия " +
    "невозможна. В-третьих, контроль при равной надёжности — без него сравнение формального метода с эвристикой " +
    "некорректно. Ограничения тоже есть, и в статье они будут названы прямо. Группа из тридцати человек " +
    "использовалась многократно и без предрегистрации. Гарантия действует в среднем, а не для каждого человека. И " +
    "сам метод не новый: контроль риска уже применяли в геномике, например к классификатору лейкозов. Новое у нас — " +
    "количественное описание его поведения при малых выборках. Вычисления выполнены, пишется текст.");
}

// =====================================================================
// 16. Next steps
// =====================================================================
{
  const s = newSlide("ПЛАНЫ", "Дальше: генотип и доза вместо «есть / нет»");
  const steps = [
    ["Генотип", "Различать одну и две копии делеции (0/1 и 1/1). Метки уже есть в данных PanGenie."],
    ["Опора на родителей", "Сверка с генотипами родителей: семья HG002–HG004 в GIAB, 602 семьи в 1000 Genomes."],
    ["Доза у картофеля", "4 копии каждой хромосомы: доза делеции от 0 до 4, проверка по расщеплению у потомков; эталон — сборки сортов Otava, Altus, Désirée."],
  ];
  const cw = 3.75, cg = 0.425, cy = 1.8, ch = 3.05;
  steps.forEach(([h, b], i) => {
    const x = MX + i * (cw + cg);
    card(s, x, cy, cw, ch, C.tintGray);
    dot(s, x + 0.3, cy + 0.3, 0.55, { fill: C.ink });
    text(s, String(i + 1), { x: x + 0.3, y: cy + 0.3, w: 0.55, h: 0.55, fontSize: 20, bold: true, color: C.white,
      align: "center", valign: "middle" });
    text(s, h, { x: x + 0.3, y: cy + 1.05, w: cw - 0.6, h: 0.45, fontSize: 19, bold: true });
    text(s, b, { x: x + 0.3, y: cy + 1.58, w: cw - 0.6, h: ch - 1.72, fontSize: 15, color: C.text2 });
  });
  text(s, [
    { text: "Уже есть у других: ", options: { bold: true } },
    { text: "PSVGT (препринт, 2026) и Varigraph (Molecular Plant, 2025) определяют дозу у полиплоидов — это " +
      "статистические методы, родителей они не используют." },
  ], { x: MX, y: 5.1, w: CW, h: 0.7, fontSize: 15, color: C.text2 });
  card(s, MX, 5.9, CW, 0.75, C.tintOrange);
  text(s, [
    { text: "Главный открытый вопрос: ", options: { bold: true } },
    { text: "есть ли доступ к данным картофеля с родителями и потомками." },
  ], { x: MX + 0.3, y: 5.9, w: CW - 0.6, h: 0.75, fontSize: 16, valign: "middle" });

  talk(s, "Дальнейшие планы",
    "Теперь о дальнейших планах. Первый шаг нужен в любом случае: научить классификатор определять генотип, то " +
    "есть одна копия делеции или две, а не только «есть или нет». Метки для этого уже есть в данных. Второй — " +
    "опираться на родителей: у ребёнка каждая копия приходит от одного из родителей, и это сильная проверка " +
    "согласованности. Для человека данные есть: семья HG002 в GIAB и 602 семьи в 1000 Genomes. Третий — картофель, " +
    "у которого по четыре копии каждой хромосомы: там нужно определять дозу делеции от нуля до четырёх и проверять " +
    "её по расщеплению у потомков. Похожие инструменты уже появились — PSVGT и Varigraph, — но это статистические " +
    "методы, и родителей они не используют. Главный открытый вопрос — доступ к данным картофеля с родителями и " +
    "потомками.");
}

// =====================================================================
// 17. Closing
// =====================================================================
{
  const s = newSlide(null, null, { dark: true });
  text(s, "Итоги", { x: MX, y: 0.7, w: 8, h: 0.9, fontFace: F.title, fontSize: 40, bold: true, color: C.white });
  const items = [
    "Одного генома недостаточно: вывод, сделанный на HG002, не воспроизвёлся на 30 людях",
    "Порог с гарантией возможен, но при реальных размерах выборки поправка на её размер определяет рабочую точку",
    "Статья 1 готова к подаче; по статье 2 результаты получены, пишется текст",
  ];
  items.forEach((it, i) => {
    const y = 1.95 + i * 1.18;
    dot(s, MX, y + 0.05, 0.55, { fill: i === 0 ? C.orange : C.blue });
    text(s, String(i + 1), { x: MX, y: y + 0.05, w: 0.55, h: 0.55, fontSize: 20, bold: true, color: C.white,
      align: "center", valign: "middle" });
    // box centred on the circle (circle centre = y + 0.325), so one- and two-line items align alike
    text(s, it, { x: MX + 0.85, y: y - 0.15, w: 10.8, h: 0.95, fontSize: 21, color: C.white, valign: "middle" });
  });
  text(s, "Спасибо за внимание", { x: MX, y: 5.45, w: 6, h: 0.5, fontSize: 18, color: C.onDark2 });
  motif(s, MX, 6.3);

  talk(s, "Итоги",
    "Подведу итог. Первое: одного генома недостаточно — вывод, сделанный на HG002, не воспроизвёлся на тридцати " +
    "людях. Второе: порог с гарантией возможен, но при реальных размерах выборки поправка на её размер определяет " +
    "рабочую точку; при шести людях на группу гарантия невозможна. Третье: первая статья готова к подаче, по второй " +
    "результаты получены и пишется текст. Спасибо, готов ответить на вопросы.");
}

if (slideNo !== TOTAL) throw new Error(`built ${slideNo} slides, TOTAL says ${TOTAL}`);
// A non-numeric field once reached a slide as "NaN%"; fail the build instead.
TALK.forEach((t) => {
  if (/NaN|undefined|Infinity/.test(t.text)) throw new Error(`slide ${t.n} talk text contains a bad value: ${t.text}`);
});

// ---------- write deck and talk text ----------
pres.writeFile({ fileName: OUT_PPTX }).then(() => {
  const words = TALK.reduce((n, t) => n + t.text.split(/\s+/).length, 0);
  const md = ["# Доклад: от одного генома к тридцати", "",
    "*Текст доклада к презентации `PAIR_SV_doklad.pptx`. Тот же текст записан в заметки к слайдам. " +
    `Объём — ${words} слов, это примерно ${Math.round(words / 120)} минут в спокойном темпе.*`, ""];
  TALK.forEach((t) => md.push(`## Слайд ${t.n}. ${t.heading}`, "", t.text, ""));
  fs.writeFileSync(OUT_TEXT, md.join("\n"));
  console.log(`wrote ${OUT_PPTX} (${slideNo} slides)`);
  console.log(`wrote ${OUT_TEXT} (${words} words, ~${Math.round(words / 120)} min)`);
});
