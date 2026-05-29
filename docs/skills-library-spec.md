# ТЗ и спецификация: библиотека скиллов для AI-агентов

**Версия документа:** 1.1
**Целевой агент v1:** Claude Code
**Целевые агенты v2+:** Codex, Cursor, generic
**Стек реализации:** Python 3.12+ (см. §4.1)

---

## 1. Назначение и цели

### 1.1 Что строим
Библиотека переиспользуемых скиллов (skills) для AI-агентов с единым реестром, CLI-установщиком и валидируемым форматом. Хранится как монорепозиторий на GitHub.

### 1.2 Целевая аудитория
1. **Пользователи скиллов** — разработчики, которые ставят готовые скиллы в свои окружения Claude Code.
2. **Авторы скиллов** — те, кто контрибьютит свои скиллы в общий репо.
3. **Интеграторы** — GUI-приложения, IDE-плагины, web-фронты, которые поверх CLI/манифеста делают свои интерфейсы.

### 1.3 Ключевые цели
- **Один источник правды** — один манифест, по которому работают все клиенты (CLI, GUI, web).
- **Простая установка** — одна команда из любого контекста (bash, агент, IDE).
- **Безопасные обновления** — версионирование на уровне отдельного скилла, не репо.
- **Расширяемость без переписывания** — поддержка новых агентов добавляется через адаптеры, а не правкой ядра.

### 1.4 Не-цели для v1
- Поддержка любых агентов, кроме Claude Code.
- Шифрование/подпись пакетов (только checksum).
- Платный/приватный реестр.
- Telemetry/аналитика использования.
- Веб-интерфейс реестра.

---

## 2. Scope v1

### 2.1 В скоупе
- Монорепо на GitHub со скиллами в формате Claude Code.
- Файл-манифест `manifest/registry.json`.
- CLI-установщик с командами `install`, `uninstall`, `list`, `info`, `update`, `outdated`, `search`, `validate`, `wizard`.
- Локальное состояние установленных скиллов (`installed.json`).
- Установка в user-scope (`~/.claude/skills/`) и project-scope (`.claude/skills/`).
- One-liner установщик (`curl … | sh`).
- CI-валидация на PR.
- Обновление одного скилла или всех сразу.
- JSON-вывод для машинной обработки.

### 2.2 Вне скоупа v1 (но архитектурно учитывается)
- Адаптеры для Codex/Cursor.
- GUI поверх CLI.
- Подпись релизов.
- Сетевая авторизация (приватные скиллы).
- Зависимости между скиллами (поле в манифесте есть, но валидация — позже).

---

## 3. Глоссарий

| Термин | Значение |
|---|---|
| **Skill** | Папка с `SKILL.md` и опциональными вспомогательными файлами. Минимальная единица установки. |
| **Library** | Монорепо со скиллами и манифестом. |
| **Manifest / Registry** | Файл `manifest/registry.json` со списком всех скиллов. |
| **Scope** | Где установлен скилл: `user` (глобально для пользователя) или `project` (в рамках конкретного проекта). |
| **CLI** | Утилита-установщик. Рабочее имя — `askill` (agent-skill); финальное имя выбирается отдельно. |
| **Core layer** | Не-интерактивный слой CLI с детерминированными командами и флагами. Используется GUI/скриптами. |
| **Wizard layer** | Интерактивная обёртка над core. Только для TTY. |

---

## 4. Архитектура высокого уровня

```
┌────────────────────────────────────────────────┐
│         GitHub repo (skills library)           │
│  registry.json + skills/<name>/SKILL.md ...    │
└──────────────────────┬─────────────────────────┘
                       │ raw.githubusercontent.com
                       ▼
   ┌───────────────────────────────────────────┐
   │           CLI (askill)                    │
   │  ┌─────────────────────────────────────┐  │
   │  │  Core (non-interactive, JSON-able)  │  │
   │  │  install/uninstall/list/info/...    │  │
   │  └─────────────────────────────────────┘  │
   │  ┌─────────────────────────────────────┐  │
   │  │  Wizard (TTY only, поверх core)     │  │
   │  └─────────────────────────────────────┘  │
   └───────────────────────────────────────────┘
                       │
                       ▼
   ┌───────────────────────────────────────────┐
   │  Target: ~/.claude/skills/<name>/         │
   │  или    <proj>/.claude/skills/<name>/     │
   │  +      installed.json (state)            │
   └───────────────────────────────────────────┘
```

Принцип: GUI/IDE-плагины никогда не парсят SKILL.md или папки сами — они либо читают `registry.json` напрямую (HTTPS), либо вызывают core CLI с `--json`.

### 4.1 Технологический стек

**Язык реализации:** Python 3.12+.

Обоснование выбора:
- Основной мейнтейнер пишет на Python, что критично для ревью AI-сгенерированного кода.
- Современные инструменты дистрибуции (`uv tool install`, `pipx install`) закрывают исторические проблемы Python-CLI с virtualenv и зависимостями.
- Богатая экосистема библиотек для CLI / TUI / валидации.

**Стек библиотек:**

| Назначение | Библиотека | Комментарий |
|---|---|---|
| CLI-команды и флаги | **Typer** | Декларативно, на type hints, авто-генерация help. |
| Форматированный вывод | **Rich** | Таблицы, цветной вывод, прогресс-бары. |
| Интерактивный wizard | **questionary** | Multi-select, single-select, confirm — всё из коробки. |
| Валидация манифеста и состояния | **pydantic v2** | Schema из моделей + строгая валидация. |
| HTTP-запросы | **httpx** | Современная замена `requests`, sync + async. |
| YAML (frontmatter в SKILL.md) | **PyYAML** | Стандарт де-факто. |
| Semver | **packaging.version** | Из stdlib (`packaging`). |
| Тесты | **pytest** + **pytest-httpx** | Моки HTTP для интеграционных тестов. |
| Менеджер пакетов и сборки | **uv** | Замена pip/poetry/virtualenv. Быстрая, современная. |
| Линт и формат | **ruff** | Один тул вместо black + isort + flake8. |
| Type checking | **mypy** или **pyright** | Strict-режим для core-модулей. |

**Минимальная версия Python:** 3.12 (современный синтаксис type hints, `match`, лучшие error messages, а также штатные tarfile extraction filters — `filter="data"` при распаковке архива скилла).

**Структура исходников:**

```
installer/
├── pyproject.toml
├── src/
│   └── askill/
│       ├── __init__.py
│       ├── __main__.py           ← entry point
│       ├── cli.py                ← Typer app, регистрация команд
│       ├── commands/
│       │   ├── install.py
│       │   ├── uninstall.py
│       │   ├── list.py
│       │   ├── info.py
│       │   ├── update.py
│       │   ├── search.py
│       │   ├── validate.py
│       │   └── wizard.py
│       ├── core/
│       │   ├── registry.py       ← загрузка и парсинг registry.json
│       │   ├── state.py          ← installed.json
│       │   ├── scope.py          ← алгоритм определения scope
│       │   ├── filesystem.py     ← атомарная запись, copy
│       │   ├── checksum.py       ← SHA-256 от tar
│       │   └── models.py         ← pydantic-модели
│       └── utils/
│           ├── output.py         ← JSON vs human вывод
│           └── errors.py         ← классы ошибок + exit codes
└── tests/
    ├── unit/
    └── integration/
```

**Принципы разделения:**
- `cli.py` и `commands/` — тонкие, только парсят аргументы и зовут `core/`.
- `core/` — чистая логика без побочных эффектов (где возможно), легко тестируется.
- `utils/output.py` инкапсулирует выбор между human-friendly и `--json` выводом — команды не знают про режим.

---

## 5. Структура репозитория

```
skills-library/
├── README.md
├── LICENSE
├── install.sh                     ← bootstrap-скрипт (curl|sh entry)
├── manifest/                          ← сгенерированные манифесты (автогенерируется CI)
│   ├── registry.json              ← lean-манифест установщика
│   ├── registry.schema.json       ← JSON Schema для registry.json
│   ├── catalog.json               ← rich-манифест для веб-клиентов
│   └── catalog.schema.json        ← JSON Schema для catalog.json
├── skills/
│   ├── pdf-extractor/
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   └── references/
│   ├── docx-builder/
│   │   └── SKILL.md
│   └── ...
├── catalog/                       ← presentation-метаданные скиллов (НЕ устанавливаются)
│   ├── pdf-extractor.yaml
│   └── ...
├── installer/
│   └── askill                     ← основная CLI-утилита
├── .github/
│   ├── CONTRIBUTING.md
│   └── workflows/
│       ├── validate.yml           ← валидация на PR
│       └── release.yml            ← регенерация manifest/ и тегирование
└── docs/
    ├── skill-format.md
    ├── cli-reference.md
    └── manifest-spec.md
```

**Правило:** в `skills/` лежат только сами скиллы. Никаких README про репо, тестов на CLI и пр. — это всё во внешних папках. Это упрощает копирование `skills/<name>/` как есть.

> **Разделение «скилл / каталог» (реализовано).** Presentation-метаданные вынесены из `SKILL.md` в `catalog/<name>.yaml` — отдельный файл рядом со `skills/`, который **не устанавливается** пользователю (установщик копирует только `skills/<name>/`) и не входит в checksum. Генератор читает `SKILL.md` (name/description/version) **и** `catalog/<name>.yaml` (summary/tags/license/compatible_agents/when/highlights/example) и собирает из них `registry.json` (lean, для установщика) и `catalog.json` (rich, для веб-клиентов). Подробности — в [docs/skill-authoring.md](docs/skill-authoring.md), интеграция блога — в [docs/blog-catalog-integration.md](docs/blog-catalog-integration.md).

---

## 6. Спецификация манифеста (`registry.json`)

### 6.1 Расположение
- В корне репо.
- Доступен по `https://raw.githubusercontent.com/<org>/<repo>/main/manifest/registry.json`.
- Регенерируется CI на каждый merge в main.

### 6.2 Формат

```json
{
  "schema_version": "1.0",
  "library": {
    "name": "askill-library",
    "repo": "https://github.com/<org>/<repo>",
    "generated_at": "2026-05-21T10:00:00Z",
    "commit": "abc123def456"
  },
  "skills": [
    {
      "name": "pdf-extractor",
      "version": "1.2.0",
      "description": "Извлечение текста и таблиц из PDF...",
      "path": "skills/pdf-extractor",
      "entry": "SKILL.md",
      "tags": ["pdf", "extraction", "data"],
      "compatible_agents": ["claude-code"],
      "dependencies": [],
      "checksum": "sha256:e3b0c44...",
      "min_cli_version": "0.1.0",
      "size_bytes": 12480,
      "author": "user@example.com",
      "license": "MIT"
    }
  ]
}
```

### 6.3 Обязательные поля скилла
`name`, `version`, `description`, `path`, `entry`, `compatible_agents`, `checksum`.

### 6.4 Правила
- `name` — уникален в рамках реестра, kebab-case, `^[a-z][a-z0-9-]{2,63}$`.
- `version` — strict semver (`MAJOR.MINOR.PATCH`).
- `description` — 10..1024 символов, одна строка, без markdown.
- `path` — относительный путь от корня репо.
- `checksum` — SHA-256 от tar-архива папки скилла (детерминированный, см. §13.3).
- `tags` — массив строк kebab-case, max 10.
- `compatible_agents` — массив из `claude-code` (на v1 — только это).

### 6.5 JSON Schema
Лежит в `manifest/registry.schema.json`. CI прогоняет валидацию schema.

---

## 7. Спецификация скилла

### 7.1 Минимальная структура

```
skills/<name>/
└── SKILL.md
```

### 7.2 Расширенная структура

```
skills/<name>/
├── SKILL.md           ← обязательно
├── scripts/           ← вспомогательные скрипты
├── references/        ← reference-документы для агента
├── assets/            ← статика (примеры файлов и т.п.)
└── examples/          ← примеры использования
```

### 7.3 SKILL.md frontmatter

`SKILL.md` содержит **только** реальные поля Claude Code + закреплённую версию (три ключа). Всё остальное (summary, tags, license, when, highlights, example) — в `catalog/<name>.yaml`, см. §5 и [docs/skill-authoring.md](docs/skill-authoring.md).

```markdown
---
name: pdf-extractor
description: Извлечение текста и таблиц из PDF — что делает И когда срабатывает (триггеры + анти-триггеры).
version: 1.2.0
---

# PDF Extractor

Основная инструкция для агента...
```

### 7.4 Правила
- frontmatter обязателен, валидный YAML; ключи — `name`, `description`, `version`.
- `name` в frontmatter === имени папки === имени файла `catalog/<name>.yaml` === `name` в манифесте.
- `version` в frontmatter === `version` в манифесте (теперь это проверяется генератором, а не «на будущее»).
- `description` — длинный триггер-ориентированный текст (по нему агент решает, срабатывать ли скиллу). Короткий `summary` для реестра/витрины живёт в `catalog/<name>.yaml`.
- Тело SKILL.md соответствует требованиям Claude Code skill spec (frontmatter + инструкции).
- Никаких абсолютных путей в скрипте/документации скилла — только относительные от корня скилла.

---

## 8. CLI: спецификация

### 8.1 Имя бинарника
`askill` (рабочее имя).

### 8.2 Общие принципы
- Все команды возвращают корректный exit code (`0` — успех, `1` — ошибка пользователя, `2` — ошибка системы, `3` — конфликт).
- Все read-команды поддерживают `--json` для машинного вывода.
- В non-TTY режиме никаких prompt'ов; вместо них — ошибка с подсказкой про нужный флаг.
- Все команды поддерживают `--registry <url>` для подмены URL манифеста (нужно для тестов и форков).

### 8.3 Команды

#### `install <name>[@version] [...flags]`
Установить один или несколько скиллов.

```
askill install pdf-extractor
askill install pdf-extractor@1.2.0
askill install pdf-extractor docx-builder
askill install pdf-extractor --scope project
askill install pdf-extractor --force
askill install pdf-extractor --dry-run
```

Флаги:
- `--scope user|project` — куда ставить. Если не указан, см. §9.
- `--force` — перезаписать, если уже стоит.
- `--skip-existing` — пропустить, если уже стоит.
- `--dry-run` — показать, что будет сделано, без записи на диск.
- `--no-checksum` — пропустить проверку checksum (только для разработки).
- `--json` — JSON-вывод результата.

#### `uninstall <name> [...flags]`

```
askill uninstall pdf-extractor
askill uninstall pdf-extractor --scope project
```

#### `list [...flags]`

```
askill list                  # все доступные в реестре
askill list --installed      # только установленные
askill list --installed --scope project
askill list --json
askill list --tag pdf
```

#### `info <name>`
Показать подробную инфу о скилле (из реестра + статус локально).

```
askill info pdf-extractor
```

#### `update [<name>] [...flags]`

```
askill update pdf-extractor
askill update --all
askill update --all --dry-run
```

Поведение: сравнивает версию в `installed.json` с реестром, ставит более новую (если есть).

#### `outdated [--json]`
Список установленных скиллов, у которых в реестре есть более новая версия.

#### `search <query> [--json]`
Полнотекстовый поиск по `name`, `description`, `tags` в реестре.

#### `validate <path>`
Для авторов: валидировать локальный скилл перед PR.

```
askill validate ./skills/my-new-skill
```

#### `wizard`
Интерактивный режим. Требует TTY. Шаги:
1. Загрузить реестр.
2. Показать список с краткими описаниями (fzf-like UI или встроенный selector).
3. Дать выбрать несколько скиллов (multi-select).
4. Спросить scope (user/project), если непонятно из контекста.
5. Подтвердить и установить.

При запуске `askill` без аргументов — запускается wizard.

### 8.4 Self-update
`askill self-update` — обновить сам бинарник CLI с последнего GitHub-релиза.

### 8.5 Версия CLI
`askill --version` — печатает версию CLI.

---

## 9. Алгоритм определения scope и целевой директории

### 9.1 Определение scope

```
1. Если указан явный флаг --scope → использовать его.
2. Если cwd содержит .claude/ (или находится внутри такой папки) → project.
3. Если установлены env CLAUDE_CODE_PROJECT_ROOT или подобные → project.
4. Иначе → user.
```

В wizard scope всегда спрашивается явно с дефолтом по этому алгоритму.

### 9.2 Целевые директории

| Scope | Путь |
|---|---|
| user | `~/.claude/skills/<name>/` |
| project | `<project-root>/.claude/skills/<name>/` |

### 9.3 Локальное состояние

| Scope | Файл |
|---|---|
| user | `~/.claude/skills/.installed.json` |
| project | `<project-root>/.claude/skills/.installed.json` |

Каждый scope ведёт свой `installed.json` независимо.

### 9.4 Кросс-платформа
- macOS/Linux: пути выше.
- Windows: `%USERPROFILE%\.claude\skills\` (поддерживается, но не тестируется приоритетно в v1).
- WSL: трактуется как Linux.

---

## 10. Локальное состояние: `installed.json`

### 10.1 Формат

```json
{
  "schema_version": "1.0",
  "scope": "user",
  "registry_url": "https://raw.githubusercontent.com/.../manifest/registry.json",
  "skills": {
    "pdf-extractor": {
      "version": "1.2.0",
      "installed_at": "2026-05-21T10:00:00Z",
      "source_commit": "abc123def456",
      "checksum": "sha256:e3b0c44...",
      "path": "/home/user/.claude/skills/pdf-extractor"
    }
  }
}
```

### 10.2 Правила
- Атомарная запись: пишем в `.installed.json.tmp`, потом `rename`.
- При повреждении (невалидный JSON) — бэкап как `.installed.json.broken-<timestamp>` и пересоздание из директорий (опционально).
- `source_commit` фиксирует, из какого commit'а реестра поставился скилл — нужно для воспроизводимости.

---

## 11. Версионирование

### 11.1 Скилл
- Каждый скилл версионируется независимо по semver.
- Версия в frontmatter SKILL.md === версия в реестре. CI это проверяет.
- Изменения в SKILL.md без bump'а версии не пропускаются в main.

### 11.2 Что считать MAJOR/MINOR/PATCH
- **MAJOR** — несовместимые изменения формата инструкций (например, скилл теперь требует другие env-переменные).
- **MINOR** — новая функциональность с обратной совместимостью.
- **PATCH** — исправления текста, опечатки, мелкие правки скриптов.

### 11.3 Реестр
- У реестра нет своей semver — только `generated_at` и `commit`.
- Опционально: тег формата `library/2026-05-21` для пиннинга в installer-скриптах.

### 11.4 CLI
- CLI версионируется по semver отдельно.
- В реестре есть `min_cli_version` для каждого скилла — если у пользователя CLI старее, `install` отказывает с понятной ошибкой.

---

## 12. Валидация и CI

### 12.1 Локальная валидация (askill validate)
- `SKILL.md` существует.
- frontmatter валидный YAML.
- Обязательные поля: name, version, description.
- name матчит `^[a-z][a-z0-9-]{2,63}$`.
- name === имени папки.
- version — валидный semver.
- description — 10..1024 символов.
- Никаких абсолютных путей в скрипте/документации скилла.

### 12.2 CI на PR (`.github/workflows/validate.yml`)
1. Для каждого изменённого скилла: запустить `askill validate`.
2. Проверить, что версия скилла bumpнута относительно main (если SKILL.md тронут).
3. Проверить уникальность имён.
4. Сгенерировать временный `registry.json` и провалидировать против `registry.schema.json`.
5. Проверить, что checksum'ы корректно посчитаны.

### 12.3 CI на merge в main (`.github/workflows/release.yml`)
1. Регенерировать `registry.json` с новым `commit` и `generated_at`.
2. Закоммитить и протегировать `library/<date>`.
3. (Опционально) Опубликовать GitHub Release с changelog.

---

## 13. Безопасность

### 13.1 Threat model
Установщик качает и кладёт файлы в `~/.claude/skills/`. Эти файлы потом исполняет AI-агент. Угрозы:
- **MITM при скачивании** — митигируется HTTPS + checksum.
- **Поломанный/злонамеренный коммит в реестре** — митигируется CI-валидацией, pinning'ом commit'а в installer'е.
- **Конфликт имён, перезапись чужого скилла** — митигируется явным `--force` и проверкой `installed.json`.

### 13.2 Установочный скрипт (install.sh)
- Всегда HTTPS, никогда HTTP.
- Перед записью файлов — выводит список того, что будет создано/перезаписано.
- В non-interactive режиме требует флаг `--yes`.
- Пиннит конкретный commit реестра по умолчанию (стабильность).

### 13.3 Checksum
- Алгоритм: SHA-256 от tar-архива папки скилла, собранного с `--sort=name`, `--mtime='1970-01-01'`, без owner/group — для детерминизма.
- Считается CI на каждый release.
- При `install` — пересчитывается локально и сверяется. При несовпадении — отказ установки (можно обойти `--no-checksum`, но с громким warning'ом).

### 13.4 Что НЕ делаем в v1
- Не подписываем релизы GPG.
- Не sandbox'им исполнение скиллов (это ответственность агента).
- Не сканируем содержимое на secrets — это в CONTRIBUTING.md как требование к авторам.

---

## 14. Способы установки

### 14.1 Bootstrap (первый раз)

```bash
curl -sSL https://raw.githubusercontent.com/<org>/<repo>/main/installer/install.sh | sh
```

Что делает скрипт:
1. Детектит наличие `uv`, `pipx` или `python3 -m pip` (в этом порядке предпочтения).
2. Если ничего из этого нет — печатает понятную инструкцию: «поставь uv одной командой `curl -LsSf https://astral.sh/uv/install.sh | sh`, потом перезапусти этот установщик».
3. Ставит `askill` через `uv tool install askill` (предпочтительно) или `pipx install askill` как fallback.
4. Проверяет, что директория установки в `PATH` (`~/.local/bin/`); если нет — выводит инструкцию по добавлению.
5. Выводит подтверждение: `askill --version`.

### 14.2 Установка скиллов через CLI
После bootstrap'а — `askill install <name>` (см. §8.3).

### 14.3 One-liner для одного скилла без bootstrap'а

```bash
curl -sSL https://raw.githubusercontent.com/<org>/<repo>/main/installer/install.sh | sh -s -- install pdf-extractor
```

Скрипт сам ставит CLI через uv/pipx, потом выполняет `askill install pdf-extractor`.

### 14.4 Альтернатива: установка через стандартный Python-инструментарий
Опытные пользователи могут поставить напрямую:

```bash
uv tool install askill
# или
pipx install askill
# или (не рекомендуется, может конфликтовать со system packages)
pip install --user askill
```

### 14.5 Установка изнутри агента
Пользователь говорит агенту:
> «Установи мне скилл pdf-extractor из библиотеки X»

Агент выполняет команду из §14.3 через bash. Поскольку `askill` non-interactive в этом контексте — всё работает.

### 14.6 Установка через GUI/IDE
Интегратор делает одно из двух:
- **Вариант A:** Вызывает `askill install <name> --json` через subprocess и парсит ответ.
- **Вариант B:** Читает `registry.json` напрямую по HTTPS, кладёт файлы сам (но обновлять `installed.json` всё равно лучше через CLI для консистентности).

Рекомендуется **A** — меньше дублирования логики.

---

## 15. Обработка конфликтов

| Ситуация | Поведение по умолчанию | С флагом |
|---|---|---|
| Скилл уже установлен той же версии | no-op, exit 0 | `--force` → переустановить |
| Установлена другая версия | ошибка, exit 3, подсказать `update` или `--force` | `--force` → перезаписать |
| Папка существует, но не в `installed.json` | ошибка, exit 3 | `--force` → перезаписать |
| Несовместимая `min_cli_version` | ошибка, exit 1, подсказать `self-update` | (без обхода) |
| Checksum mismatch | ошибка, exit 2 | `--no-checksum` → продолжить с warning'ом |

---

## 16. Расширяемость

### 16.1 Мульти-агентность (v2)
В манифесте уже есть поле `compatible_agents`. План на v2:
- Адаптеры в `src/askill/adapters/<agent>.py` для трансляции скилла в формат целевого агента.
- Команда `askill install <name> --agent codex`.
- Per-agent paths в коде определения scope.

### 16.2 Зависимости между скиллами (v2)
Поле `dependencies` в манифесте уже зарезервировано. v2: топологическая сортировка при установке + проверка циклов.

### 16.3 Приватные реестры (v2+)
- Поддержка нескольких реестров через `~/.config/askill/config.json`.
- Авторизация через `--token` или env.

### 16.4 Конфигурация скиллов (v2)
- Опциональный `config.schema.json` в папке скилла.
- При установке — wizard может спросить значения и записать в скилл.

---

## 17. Критерии приёмки v1

### 17.1 Функциональные
- [ ] `askill install <name>` ставит скилл в правильную директорию.
- [ ] `askill install <name>@<version>` ставит конкретную версию.
- [ ] `askill list`, `info`, `outdated`, `search` работают корректно с `--json` и без.
- [ ] `askill update --all` обновляет всё устаревшее.
- [ ] `askill uninstall` удаляет файлы и чистит `installed.json`.
- [ ] `askill validate` корректно проверяет локальные скиллы.
- [ ] `askill wizard` работает в TTY с multi-select.
- [ ] Non-interactive контекст не блокирует выполнение и не зависает на prompt'ах.
- [ ] One-liner `curl … | sh -s -- install <name>` ставит CLI и скилл за один шаг.

### 17.2 Не-функциональные
- [ ] Установка одного скилла занимает < 5 секунд на стандартном интернете.
- [ ] `uv tool install askill` или `pipx install askill` отрабатывает < 30 секунд.
- [ ] Запуск любой команды (cold start) — < 500 мс.
- [ ] Все ошибки имеют человекочитаемое сообщение + код возврата.
- [ ] CI блокирует merge при невалидном скилле/манифесте.
- [ ] Документация: README, CONTRIBUTING, docs/skill-format.md, docs/cli-reference.md, docs/manifest-spec.md.

### 17.3 Тесты
- Unit-тесты на core-модули (registry, state, scope, filesystem, checksum) с coverage > 80%.
- Integration-тесты команд через Typer's `CliRunner` + моковый HTTP-реестр (`pytest-httpx`).
- Smoke-тест на каждой OS (Linux, macOS) в CI через GitHub Actions matrix.

---

## 18. План работ

### Milestone 1: фундамент (1-2 недели)
- Структура репо.
- 3-5 первых скиллов в качестве примеров.
- JSON Schema для манифеста.
- Скрипт автогенерации registry.json.
- CI для валидации.

### Milestone 2: CLI core (2-3 недели)
- install, uninstall, list, info — non-interactive.
- installed.json и его управление.
- Алгоритм scope.
- Checksum-проверки.
- JSON output.

### Milestone 3: CLI extras + wizard (1-2 недели)
- update, outdated, search, validate.
- Wizard поверх core.
- self-update.

### Milestone 4: дистрибуция (1 неделя)
- install.sh bootstrap.
- One-liner per-skill install.
- Release pipeline.
- Документация.

**Итого до v1:** 5-8 недель чистого времени.

---

## 19. Открытые вопросы

1. **Имя CLI и PyPI-пакета.** `askill` — рабочее. Перед стартом нужно проверить доступность имени на PyPI и в GitHub-namespace. Альтернативы: `claude-skills`, `agent-skills`, `sklib`.
2. **Кеш реестра.** Чтобы не дёргать GitHub на каждую команду — кеш в `~/.cache/askill/registry.json` с TTL 1 час и флагом `--refresh` для форсирования. Открытый вопрос: что делать при offline (последний валидный кеш или явная ошибка).
3. **Поддержка Windows.** Нативно vs только WSL в v1. Рекомендация: WSL в v1, нативный — best-effort через `pathlib` (`uv` и `pipx` нативно поддерживают Windows, так что бóльшая часть заработает бесплатно).
4. **Strict semver или calendar versioning для скиллов.** Semver выбран в спеке, но для contented-driven скиллов (где «версия» — это правки текста инструкций) calver проще. Решается практикой первых месяцев.
5. **Auto-update CLI.** Команда `askill self-update` (см. §8.4) — звать `uv tool upgrade askill` под капотом, или собственная логика через PyPI API. Первое проще и надёжнее.

Эти вопросы решаются в момент старта реализации; на архитектуру выше они не влияют.
