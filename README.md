# asofwar.github.io

Индекс проектов Asofwar: https://asofwar.github.io/

Статический сайт без фреймворков. Карточки проектов описаны в `data/projects.json`,
`scripts/build.py` собирает из них и `template.html` готовую страницу в `_site/`.
Версии и даты релизов подтягиваются из GitHub Releases при каждой сборке.

## Структура

| Путь | Что там |
|---|---|
| `data/projects.json` | Проекты (`projects`) и репозитории, которые не надо показывать (`ignore`) |
| `template.html` | Разметка страницы с плейсхолдерами `{{...}}` |
| `assets/` | CSS и JS (сборка встраивает их в страницу), шрифты в `assets/fonts/` |
| `img/` | Иконки и og-картинка |
| `data/candidates.json` | Снимок новых публичных репозиториев для агента (пишет `discover.yml`) |
| `scripts/build.py` | Сборка: данные + релизы → `_site/` |
| `scripts/schema.py` | Строгая проверка `data/projects.json`, её вызывает `build.py` |
| `scripts/discover.py` | Поиск новых репозиториев → `data/candidates.json` |
| `scripts/ghapi.py` | Мини-клиент GitHub REST API |
| `.github/workflows/site.yml` | Сборка и деплой в GitHub Pages |
| `.github/workflows/discover.yml` | Еженедельный снимок кандидатов |
| `agent/update-projects.md` | Инструкция облачного агента, который добавляет новые проекты |

## Локальная сборка

```bash
python scripts/build.py            # с релизами из GitHub API
python scripts/build.py --offline  # без сети
python -m http.server 8765 -d _site
```

Журнал склеивает релизы одного проекта за день и показывает не больше 3 групп на проект (`LOG_PER_PROJECT` в `build.py`).

## Шрифты

Unbounded, Golos Text и JetBrains Mono отдаются с этого же домена из `assets/fonts/`,
без Google Fonts. Это подмножества вариативных шрифтов из [google/fonts](https://github.com/google/fonts)
(ветка `main`): `ofl/unbounded/Unbounded[wght].ttf`, `ofl/golostext/GolosText[wght].ttf`,
`ofl/jetbrainsmono/JetBrainsMono[wght].ttf`. Лицензия — SIL Open Font License 1.1,
текст и copyright всех трёх семейств в `assets/fonts/OFL.txt`.

Пересборка: сначала subset, потом instancer, именно в таком порядке (на полном Golos
instancer падает с `KeyError`). `--layout-features` не задавать: набор по умолчанию
сохраняет `rlig`/`rvrn` и альтернативы Unbounded для веса 800.

```bash
uvx --from "fonttools[woff]" pyftsubset <ttf> --flavor=woff2 --unicodes="U+0020-007E,U+00A0-00FF,U+0131,U+0152-0153,U+02C6,U+02DA,U+02DC,U+0400-045F,U+0490-0491,U+2010-2027,U+2030-203A,U+20AC,U+20BD,U+2116,U+2122,U+2190-2199,U+2212,U+25CF" --output-file=<name>.sub.woff2
uvx --from "fonttools[woff]" fonttools varLib.instancer <name>.sub.woff2 wght=<lo>:<hi> -o assets/fonts/<name>.woff2
```

`<name>` и `wght`: `unbounded` 700:800, `golos` 400:500, `jbmono` 400:500. Другие начертания
в CSS не используются; новое начертание требует расширить диапазон здесь и `font-weight` в `@font-face`.

Символы вне диапазона рисуются системным шрифтом. Для польских и подобных букв
диапазон расширяется на `U+0100-024F` (+10–15 КБ на файл).

Метрические fallback-шрифты (`Unbounded Fallback`, `Golos Fallback`, `Mono Fallback` в начале
`assets/style.css`) подогнаны под эти файлы, чтобы подмена шрифта не сдвигала вёрстку.
После смены шрифта, начертания или размера заголовка их `size-adjust` и `*-override` надо пересчитать.

## Автоматика

- **GitHub Actions** (`site.yml`): пересобирает и деплоит сайт на каждый push в `main`
  и раз в 6 часов, поэтому новые релизы появляются на сайте сами.
- **GitHub Actions** (`discover.yml`): по понедельникам в 06:00 UTC собирает новые
  публичные репозитории Asofwar в `data/candidates.json`. Если кандидаты не менялись,
  снимок всё равно переписывается раз в 28 дней (обновляется `generated_at`), чтобы
  GitHub не отключил расписания после 60 дней без активности.
- **Облачный агент** по понедельникам в 07:00 UTC разбирает кандидатов по
  `agent/update-projects.md`, добавляет карточки в `data/projects.json` и пушит в `main`.
  Сам перечислить репозитории он не может: облачная сессия видит через API только этот репо.

## Добавить проект вручную

Добавь объект в `projects` в `data/projects.json` (формат — как у соседних карточек),
проверь `python scripts/build.py` и запушь. Схема-«плата» у карточки генерируется
из `id` автоматически.

## Поля карточки

Обязательны `id`, `title`, `kind`, `summary`, `stack`, `platforms`, `status`.
Отсутствующее необязательное поле равно `null`.

- `id` — kebab-case (`a-z`, `0-9`, дефисы), уникальный; из него строятся якорь `#p-<id>` и «плата».
- `title` — название проекта.
- `kind` — тип проекта по-русски, 1–4 слова.
- `summary` — 1–2 предложения по-русски, не длиннее 300 символов.
- `stack` — непустой список языков и технологий.
- `platforms` — непустой список платформ.
- `status` — `live` | `dev` | `research`.
- `releases` — `"owner/repo"` | `null` — брать из `source`, если это репозиторий Asofwar | `false` — не показывать.
- `link` — `{ "url": "https://…", "label": "…" }` или `null`.
- `source` — http(s)-ссылка на код или `null`.
- `fork_of` — `"owner/repo"` исходного проекта или `null`.
- `added` — дата добавления, `YYYY-MM-DD`; карточка с `added` позже 2026-10-16 получает бейдж «Новый» на 30 дней.

Схема проверяется в `scripts/schema.py`: `build.py` печатает все ошибки списком и
завершается с кодом 1. Новое поле сначала добавляется в `ALLOWED` в `scripts/schema.py`.

## Снимок кандидатов

`data/candidates.json` пишет `scripts/discover.py`, руками его не правят. Внутри — `generated_at`,
`candidates[]` и `status_hints[]`.

- `candidates[]` — публичные неархивные репозитории Asofwar с push за 120 дней, которых ещё нет в
  `projects` и `ignore`: `{ repo, url, description, homepage, language, topics, pushed_at,
  releases, readme_excerpt, fork_of }`. `releases` — до 3 последних релизов
  `{ version, date, pre }`, `fork_of` — `"owner/repo"` upstream для форка, иначе `null`.
- Форки попадают в кандидаты, только если у них есть свой релиз за 120 дней.
- Репозитории из `projects` и `ignore` сверяются и по текущему имени, поэтому
  переименованный репозиторий не возвращается кандидатом.
- `status_hints[]` — `{ id, suggest_status, version }`: проект в статусе `dev`, у которого
  вышел стабильный релиз 1.0 или новее.
