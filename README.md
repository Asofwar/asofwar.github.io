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
| `assets/` | CSS и JS |
| `img/` | Иконки и og-картинка |
| `data/candidates.json` | Снимок новых публичных репозиториев для агента (пишет `discover.yml`) |
| `scripts/build.py` | Сборка: данные + релизы → `_site/` |
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

## Автоматика

- **GitHub Actions** (`site.yml`): пересобирает и деплоит сайт на каждый push в `main`
  и раз в 6 часов, поэтому новые релизы появляются на сайте сами.
- **GitHub Actions** (`discover.yml`): по понедельникам в 06:00 UTC собирает новые
  публичные репозитории Asofwar в `data/candidates.json`.
- **Облачный агент** по понедельникам в 07:00 UTC разбирает кандидатов по
  `agent/update-projects.md`, добавляет карточки в `data/projects.json` и пушит в `main`.
  Сам перечислить репозитории он не может: облачная сессия видит через API только этот репо.

## Добавить проект вручную

Добавь объект в `projects` в `data/projects.json` (формат — как у соседних карточек),
проверь `python scripts/build.py` и запушь. Схема-«плата» у карточки генерируется
из `id` автоматически.
