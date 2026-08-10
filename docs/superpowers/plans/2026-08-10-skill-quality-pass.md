# Skill Quality Pass — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Закрыть находки ревью библиотеки скиллов: недостающие нон-триггеры, пересказ workflow в descriptions, отсутствие progressive disclosure у article-translator, отсутствующий пример конфига у adr-capture и разнобой конфиг-локаций.

**Architecture:** Все правки — контент скиллов (SKILL.md, references, catalog yaml) плюс регенерация манифестов. Никакого кода инсталлера. Дисциплина «тест до правки» адаптирована под прозу: для правок descriptions — ручной L1-probe (selection-judge из evals-спеки, исполняемый сабагентом), для остального — генератор манифестов и проверка длины description как детерминированные чекеры.

**Tech Stack:** Markdown/YAML, `installer/scripts/generate_registry.py` (uv), сабагент как selection-judge.

## Global Constraints

- `description` в SKILL.md — максимум **1024 символа** (генератор падает при превышении).
- `version` — строгий semver; правка description/тела скилла = минимум minor bump (меняется поведение триггеринга), правка только формулировок = patch.
- Сгенерированные артефакты (`manifest/*.json`, `.claude-plugin/*.json`) **не редактируются руками** — только через генератор: `cd installer && uv run python scripts/generate_registry.py --commit "$(git -C .. rev-parse HEAD)" --schema`.
- Двухфайловый контракт: презентационная мета — только в `catalog/<name>.yaml`, никогда в SKILL.md.
- Скиллы steelman-then-break и learning-mode в этом плане **не трогаем** (только что переработаны на ветке chore/consolidate-tags).
- Языковая политика: тела скиллов и descriptions — на английском; коммит-сообщения — короткий императив на английском.

**Предусловие:** работа ветки `chore/consolidate-tags` закоммичена и влита (или как минимум закоммичена). План исполняется на свежей ветке `chore/skill-quality-pass` поверх неё. Каждая задача — отдельный коммит.

**Принятое решение (по рекомендации из ревью):** конфиг-локации унифицируются под `.claude/` — `.adr/config.yaml` → `.claude/adr/config.yaml`, `.onboard/topics.yaml` → `.claude/onboard/topics.yaml`. Обоснование: половина библиотеки уже живёт в `.claude/` (scars, learning), пользователей мало — дешевле сломать сейчас, чем поддерживать два стиля. Если решение отменяется — Задача 2 сокращается до одной правки CI-фразы у onboard (шаг 2.4), а в Задаче 5 путь конфига остаётся `.adr/config.yaml`.

---

### Task 1: Baseline L1-probe триггеров (RED)

Зачем: правки descriptions в задачах 3–4 меняют поведение триггеринга. Фиксируем, как selection-judge выбирает скиллы ДО правок, чтобы после правок увидеть исправление, а не предположить его. Это ручная версия L1-теста из `docs/skill-evals-spec.md` §4.2.

**Files:**
- Create: `/tmp/probe-results-before.md` (рабочая заметка, в репо не коммитится)

**Interfaces:**
- Produces: таблица «probe → выбранный скилл» до правок; Task 7 сравнивает с ней.

- [ ] **Step 1: Собрать текущие descriptions**

Прочитать frontmatter-поле `description` всех семи файлов `skills/*/SKILL.md` (as-is, до любых правок).

- [ ] **Step 2: Прогнать судью-сабагента**

Диспатчить одного сабагента (general-purpose) с промптом следующей структуры: семь описаний, помеченных именами скиллов, плюс опция `none`; затем восемь probe-промптов; инструкция «для каждого промпта назови ровно один скилл, который хост должен активировать, или none — отвечай таблицей, без рассуждений в ответе».

Probe-промпты и ожидания ПОСЛЕ правок (колонка expected):

| # | Prompt | Expected (after) |
|---|--------|------------------|
| 1 | "Tear this apart: `def f(x): return eval(x)`" | toxic-senior-reviewer |
| 2 | "Do a code review of this function." | toxic-senior-reviewer |
| 3 | "Can you review my code? Be gentle, I'm a beginner." | none |
| 4 | "Explain how this parser works." | none |
| 5 | "Review this design proposal for the new queue architecture." | steelman-then-break |
| 6 | "I'm stuck on this bug, help me think it through." | rubber-duck |
| 7 | "Just tell me the fix for this failing test." | none |
| 8 | "Should we go with Postgres or Mongo here?" | steelman-then-break |

- [ ] **Step 3: Записать baseline**

Сохранить фактические ответы в `/tmp/probe-results-before.md`. Ожидаемый RED: probe #3 выбирает toxic-senior-reviewer (нет нон-триггера «gentle»). Если baseline уже полностью совпадает с expected — правки descriptions всё равно выполняются (их требует гайд авторинга: явные «Do NOT use for…»), но это фиксируется в заметке.

- [ ] **Step 4: Коммита нет** — задача не меняет репо.

---

### Task 2: Унификация конфиг-локаций под `.claude/`

Зачем: четыре скилла — четыре конвенции (`.adr/`, `.onboard/`, `.claude/scars.md`, `.claude/learning/`). Единый префикс `.claude/` делает библиотеку одной системой и упрощает документацию.

**Files:**
- Modify: `skills/adr-capture/SKILL.md:29,53` (и bump `version`)
- Modify: `skills/adr-capture/references/adr-template.md:6,41`
- Modify: `skills/onboard-our-stack/SKILL.md:7,34,43,65,99,114-115` (и bump `version`)
- Modify: `skills/onboard-our-stack/references/topics.example.yaml:1`
- Modify: `skills/onboard-our-stack/scripts/check_topics.py:2,9,42`
- Modify: `catalog/onboard-our-stack.yaml:15,37`

**Interfaces:**
- Produces: канонические пути `.claude/adr/config.yaml` и `.claude/onboard/topics.yaml`; Задача 5 создаёт пример конфига именно под этот путь.

- [ ] **Step 1: Замена путей**

Во всех перечисленных файлах заменить `.adr/config.yaml` → `.claude/adr/config.yaml` и `.onboard/topics.yaml` → `.claude/onboard/topics.yaml` (в `check_topics.py` — включая default аргумента `--config` на строке 42 и docstring). Смысловые формулировки вокруг не менять.

- [ ] **Step 2: Проверить, что упоминаний не осталось**

Run: `grep -rn '\.onboard/topics\.yaml\|\.adr/config\.yaml' skills/ catalog/ docs/ README.md --exclude-dir=superpowers`
Expected: пусто (0 совпадений).

- [ ] **Step 3: Уточнить CI-фразу у onboard-our-stack**

В `skills/onboard-our-stack/SKILL.md` секция «Maintaining», заменить:

> Run `scripts/check_topics.py` in CI so stale paths fail the build;

на:

> Copy `scripts/check_topics.py` out of the installed skill into the repo (e.g. `ci/check_topics.py`) and run it in CI so stale paths fail the build;

Причина: установленный скилл живёт в `~/.claude/skills/` пользователя и до CI не доезжает.

- [ ] **Step 4: Bump версий**

`skills/adr-capture/SKILL.md`: `version: 0.1.1` → `0.2.0`.
`skills/onboard-our-stack/SKILL.md`: `version: 0.2.1` → `0.3.0`.

- [ ] **Step 5: Проверка длины description (onboard близок к капу)**

Run из корня репо:
```bash
cd installer && uv run python - <<'EOF'
import pathlib, yaml
for p in sorted(pathlib.Path('../skills').glob('*/SKILL.md')):
    d = yaml.safe_load(p.read_text().split('---')[1])
    n = len(d['description'])
    print(p.parent.name, n, 'OK' if n <= 1024 else 'OVER CAP')
EOF
```
Expected: все строки `OK`; onboard-our-stack ≈ 1019 (замена пути добавила 7 символов к 1012).

- [ ] **Step 6: Генератор как тест**

Run: `cd installer && uv run python scripts/generate_registry.py --commit "$(git -C .. rev-parse HEAD)" --schema`
Expected: exit 0, без ошибок валидации.

- [ ] **Step 7: Commit**

```bash
git add skills/adr-capture skills/onboard-our-stack catalog/onboard-our-stack.yaml
git commit -m "Unify per-skill config locations under .claude/"
```
(Манифесты не добавлять — они коммитятся один раз в Задаче 7.)

---

### Task 3: toxic-senior-reviewer — нон-триггеры в description

Зачем: единственный скилл без «Do NOT use for…» (нарушение docs/skill-authoring.md), и его триггеры перетягивают запросы на мягкое ревью и объяснение кода. Решение: широкие ревью-триггеры сохраняем (установка скилла = осознанный opt-in в персону), но явно отдаём чужие интенты.

**Files:**
- Modify: `skills/toxic-senior-reviewer/SKILL.md:3-4`
- Modify: `catalog/toxic-senior-reviewer.yaml` (блок `when`)

**Interfaces:**
- Consumes: baseline из Task 1.
- Produces: description с нон-триггерами; Task 7 гоняет GREEN-probe по нему.

- [ ] **Step 1: Дописать нон-триггеры в description**

В `skills/toxic-senior-reviewer/SKILL.md` к существующему description добавить в конец (перед закрывающей кавычкой значения):

> Do NOT use for: writing new code from scratch, explaining how existing code works, reviewing design proposals or architecture documents, or when the user explicitly asks for a gentle, encouraging, beginner-friendly review.

Итоговая длина ≈ 903 символа (проверяется в Step 3).

- [ ] **Step 2: Bump версии**

`version: 0.1.0` → `0.2.0` (изменилось поведение триггеринга).

- [ ] **Step 3: Выровнять catalog `when`**

В `catalog/toxic-senior-reviewer.yaml` в конец блока `when` добавить предложение:

> Also stays quiet when the user asks for a gentle or beginner-friendly review.

- [ ] **Step 4: Проверка**

Прогнать скрипт длины из Task 2 Step 5 (expected: toxic-senior-reviewer ≤ 1024, `OK`), затем генератор из Task 2 Step 6 (expected: exit 0).

- [ ] **Step 5: Commit**

```bash
git add skills/toxic-senior-reviewer catalog/toxic-senior-reviewer.yaml
git commit -m "toxic-senior-reviewer 0.2.0: add explicit non-triggers"
```

---

### Task 4: rubber-duck — убрать пересказ workflow из description

Зачем: description содержит всю лестницу эскалации; по docs/skill-authoring.md:49-51 это провоцирует агента следовать описанию вместо чтения тела (и пропустить, например, правила escape hatch). Бюджет перераспределяем на триггерные фразы.

**Files:**
- Modify: `skills/rubber-duck/SKILL.md:3-4`

**Interfaces:**
- Produces: description без пересказа; Task 7 гоняет GREEN-probe (#6, #7).

- [ ] **Step 1: Заменить description целиком**

Новое значение (одинарные YAML-кавычки, внутренние `'` удваиваются как в текущем файле):

> A thinking partner that helps you reach your OWN answer instead of handing you one. Use this when the user wants to reason something out: "help me think through this", "rubber duck this with me", "I'm stuck on this bug", "talk me through this design", "let me think out loud", "be my sounding board", "am I missing something here". Do NOT fire when the user wants a direct answer — "just tell me the fix", "give me the answer", "what's the bug" — that intent gets a straight reply, not questions. Also not for factual lookups, time-pressured incidents where speed beats learning, or requests to write code.

Что ушло: лестница Gear 0→2 и упоминание escape hatch (это контент тела). Что добавилось: два триггера («be my sounding board», «am I missing something here»).

- [ ] **Step 2: Bump версии**

`version: 0.1.0` → `0.2.0`.

- [ ] **Step 3: Проверка**

Скрипт длины (expected ≈ 610, `OK`) + генератор (expected: exit 0).

- [ ] **Step 4: Commit**

```bash
git add skills/rubber-duck
git commit -m "rubber-duck 0.2.0: trim workflow retelling from description"
```

---

### Task 5: adr-capture — трим description + пример конфига

Зачем: (а) фраза «It assigns the next ADR id, fills…, and flags… as TODO» — пересказ workflow; (б) скилл читает конфиг, схема которого нигде не показана — у onboard-our-stack прецедент `references/topics.example.yaml`, делаем симметрично.

**Files:**
- Modify: `skills/adr-capture/SKILL.md:3` (description; версия уже 0.2.0 после Task 2 — не бампать повторно)
- Create: `skills/adr-capture/references/config.example.yaml`
- Modify: `skills/adr-capture/SKILL.md:29-31` (сослаться на пример)

**Interfaces:**
- Consumes: канонический путь `.claude/adr/config.yaml` из Task 2.

- [ ] **Step 1: Убрать пересказ из description**

Удалить из description предложение:

> It assigns the next ADR id, fills what the discussion supports, and flags missing team-mandatory sections as TODO.

Остальной текст не менять. Итог ≈ 867 символов.

- [ ] **Step 2: Создать пример конфига**

`skills/adr-capture/references/config.example.yaml`:

```yaml
# Copy this to .claude/adr/config.yaml at your repo root and edit — or skip the
# file entirely to use the defaults baked into references/adr-template.md.
# A team authors this once; the adr-capture skill reads it before drafting.

adr_dir: docs/adr/            # where ADRs live; scanned for the next id
id_format: "NNNN"             # zero-padded width of the numeric id in filenames

# Headings the skill must always include in a draft. Any the conversation did
# not cover get a literal <TODO: ...> — the skill never invents their content.
mandatory_sections:
  - Regulatory impact
  - Data classification
  - Security review status
  - Rollback plan
```

- [ ] **Step 3: Сослаться на пример из SKILL.md**

В шаге 1 воркфлоу («**Config.**») после первого предложения добавить:

> See `references/config.example.yaml` for the schema.

- [ ] **Step 4: Проверка**

Скрипт длины (expected ≈ 867, `OK`) + генератор (expected: exit 0 — новый файл в `references/` войдёт в чексумму, это ожидаемо).

- [ ] **Step 5: Commit**

```bash
git add skills/adr-capture
git commit -m "adr-capture 0.2.0: trim description, add config example"
```

---

### Task 6: article-translator — progressive disclosure и дедупликация

Зачем: 3300 слов целиком в SKILL.md — самый тяжёлый скилл, грузится в контекст при каждом переводе, единственный без `references/`. Механику формата выносим, внутренние повторы (drift 60–70% ×2, footnotes <1% ×2, sentence-atomic ×3) схлопываем до одного упоминания каждый.

**Files:**
- Create: `skills/article-translator/references/formatting.md`
- Modify: `skills/article-translator/SKILL.md` (секции по строкам исходной версии: 11–15, 44, 100–103, 132–144, 192–208, 210–215, 217–227; bump `version`)

**Interfaces:**
- Produces: SKILL.md ≤ 2400 слов + `references/formatting.md` с механикой.

- [ ] **Step 1: Вынести механику в references/formatting.md**

Создать `skills/article-translator/references/formatting.md` с заголовком:

```markdown
# Formatting mechanics and special cases

Mechanical rules for keeping a translated document render-identical to the
source, plus special-case playbooks. Read before Phase 4 whenever the source
is anything richer than plain paragraphs.
```

и перенести под него **дословно** две секции из SKILL.md: «Preserving structure and formatting» (строки 192–208) и «Special cases» (строки 210–215), включая завершающую строку «When in doubt about a syntactic element, leave it verbatim…».

- [ ] **Step 2: Заменить секции указателем**

На месте вырезанных секций в SKILL.md оставить один абзац:

```markdown
## Formatting and special cases

Mechanical formatting rules (headings, links, code, tables, YAML front matter,
HTML embeds) and special-case playbooks (embedded quotations, mixed-language
sources, headlines and pull quotes, very long texts >5000 words) live in
`references/formatting.md`. Read it before Phase 4 whenever the source is
anything richer than plain paragraphs. The one rule that never bends: when in
doubt about a syntactic element, leave it verbatim — breaking the document's
rendering is worse than under-translating an attribute value.
```

- [ ] **Step 3: Удалить «Anti-patterns to avoid» с тремя переносами**

Удалить секцию целиком (строки 217–227 исходной версии). Три пункта, не покрытые фазами, перенести:
- В Phase 3, в список идиом, добавить пункт 4: `4. Never invent a target-language idiom that does not actually exist just to "match" the source's idiomatic register.`
- В Phase 5, к условиям футноутов, добавить последним абзацем: `Never silently drop a difficult passage or paraphrase it past recognition — if a passage is genuinely ambiguous, resolve it one way and footnote the ambiguity.`
- В Guiding criteria, пункт 3 (Naturalness), дописать в конец: `The fix for translator-ese is bolder rewriting at the sentence and clause level, not closer adherence to the source.`

Остальные шесть пунктов секции дублируют Phase 4/5/6 и Criteria 2 — просто удаляются.

- [ ] **Step 4: Схлопнуть повторы фактов**

Каждый факт оставить в одном месте:
- «drift появляется на отметке 60–70%» — оставить в Phase 6 (Drift check), убрать из «Very long texts» (теперь в formatting.md — при переносе в Step 1 удалить это придаточное: `Drift typically appears around the 60-70% mark; a mid-text check catches it before the end.` остаётся, а вот дубль из анти-паттернов уже удалён Step 3 — проверить, что упоминание осталось ровно одно на оба файла).
- «footnotes < ~1% слов» — оставить в Phase 5, дубль был в анти-паттернах (удалён Step 3).
- «sentence-atomic — дефект» — оставить в Phase 4 (первая строка), дубль в Core workflow п.4 сократить до `Translate in paragraph-sized semantic units (Phase 4).`

- [ ] **Step 5: Сжать «When to use»**

Секцию (строки 11–15) сократить до:

```markdown
## When to use

Input is more than ~3 paragraphs of prose bound for another language. Out of
scope: UI copy, code, single sentences, tweet-sized fragments, song lyrics,
metered poetry (verse translation needs a different toolkit), legal contracts
(specialized terminology and disclaimers).
```

- [ ] **Step 6: Bump версии**

`version: 0.1.0` → `0.2.0`.

- [ ] **Step 7: Проверки**

Run: `wc -w skills/article-translator/SKILL.md skills/article-translator/references/formatting.md`
Expected: SKILL.md ≤ 2400 слов; formatting.md ≈ 700–800.

Run: `grep -c '60–70%\|60-70%' skills/article-translator/SKILL.md skills/article-translator/references/formatting.md` — суммарно ровно 1 совпадение на оба файла; аналогично `grep -c '1% of words\|~1%'` — ровно 1.

Генератор из Task 2 Step 6: exit 0.

- [ ] **Step 8: Commit**

```bash
git add skills/article-translator
git commit -m "article-translator 0.2.0: move formatting mechanics to references, dedupe"
```

---

### Task 7: GREEN-probe, регенерация манифестов, финал

**Files:**
- Modify: `manifest/registry.json`, `manifest/catalog.json`, `manifest/*.schema.json`, `.claude-plugin/marketplace.json`, `.claude-plugin/plugin.json` (только через генератор)

**Interfaces:**
- Consumes: baseline из Task 1, новые descriptions из Tasks 3–5.

- [ ] **Step 1: GREEN-probe**

Повторить Task 1 Steps 1–2 с УЖЕ отредактированными descriptions (свежий сабагент, тот же промпт-шаблон и те же 8 probe).
Expected: все 8 ответов совпадают с колонкой Expected. Если probe #3 или #7 всё ещё выбирает скилл — ужесточить формулировку соответствующего нон-триггера в description (одна итерация правки), bump НЕ повторять (версия уже поднята), прогнать judge заново.

- [ ] **Step 2: Регенерация манифестов**

Run: `cd installer && uv run python scripts/generate_registry.py --commit "$(git -C .. rev-parse HEAD)" --schema`
Expected: exit 0.

Run: `git diff --stat manifest/ .claude-plugin/`
Expected: изменения только в версиях, чексуммах, description-полях и `updated_at` затронутых пяти скиллов; steelman-then-break и learning-mode не изменились.

- [ ] **Step 3: Тесты инсталлера не задеты**

Run: `cd installer && uv run pytest -q`
Expected: все зелёные (правки не касались кода, это регрессионная страховка).

- [ ] **Step 4: Commit**

```bash
git add manifest/ .claude-plugin/
git commit -m "chore: regenerate manifests after skill quality pass"
```

- [ ] **Step 5: PR**

```bash
git push -u origin chore/skill-quality-pass
gh pr create --base main --title "Skill quality pass: non-triggers, description trims, progressive disclosure, config unification" --body "$(cat <<'EOF'
Closes the findings from the library review:

- **toxic-senior-reviewer 0.2.0** — adds the missing "Do NOT use for…" non-triggers (was the only skill without them; hijacked gentle-review and explain-this-code intents).
- **rubber-duck 0.2.0** — description no longer retells the escalation ladder (per docs/skill-authoring.md: workflow summaries tempt agents to skip the body).
- **adr-capture 0.2.0** — same trim + ships references/config.example.yaml (schema for the config it reads).
- **article-translator 0.2.0** — first use of progressive disclosure: formatting mechanics and special cases move to references/formatting.md; internal duplicates collapsed (~1000 words lighter in-context).
- **onboard-our-stack 0.3.0 / adr-capture** — config paths unified under .claude/ (.claude/adr/config.yaml, .claude/onboard/topics.yaml); CI note clarified (check_topics.py must be copied into the team repo).

Trigger changes were checked with a manual L1 selection-judge probe (8 prompts, before/after) — the harness version of this lands with docs/skill-evals-spec.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Вне этого плана (следующие планы)

1. **Evals, фаза 1** — по `docs/skill-evals-spec.md` §9 (models/loader/asserts/scoring + `--validate` + suites для learning-mode и rubber-duck). Отдельная подсистема с кодом в installer — свой план. Probe-таблица из Task 1 конвертируется в первые L1 триггер-тесты.
2. **postmortem-capture** — новый скилл: близнец adr-capture для инцидентов, выход которого пополняет `.claude/scars.md` (вход steelman-then-break). Творческая работа — сначала brainstorming/дизайн, потом свой план.
3. **learning-mode диета** (опционально) — вынести примеры handoff-режимов и bad/good brief в references; делать только после того, как evals-suite learning-mode появится и подстрахует правку.
