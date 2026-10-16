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
| `scripts/build.py` | Сборка: данные + релизы → `_site/` |
| `.github/workflows/site.yml` | Сборка и деплой в GitHub Pages |
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
- **Облачный агент** раз в неделю проверяет публичные репозитории Asofwar по
  `agent/update-projects.md`, добавляет новые проекты в `data/projects.json` и пушит в `main`.

## Добавить проект вручную

Добавь объект в `projects` в `data/projects.json` (формат — как у соседних карточек),
проверь `python scripts/build.py` и запушь. Схема-«плата» у карточки генерируется
из `id` автоматически.
