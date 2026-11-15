# Золото: что статьи утверждают о размере частиц и что показывают их данные

Основной проект курса ШАД «ИИ-ассистенты для исследователя. AI4Science».
Автор — Антон Попов. Репозиторий закрытый; материалы не публиковать.

## Текущее состояние main

Входные данные обновлены: **41 статья, 245 экспериментов**, формат снимка 6,
схема БД `0111`. Снимок и JSON Schema зафиксированы вместе;
параметры экспорта, дата и контрольные суммы — в
[`data/snapshot_manifest.json`](data/snapshot_manifest.json),
правила — в [`METHOD.md`](METHOD.md), §3.

Экспорт по-прежнему содержит только завершённые статьи с золотом как
единственным материалом мишени: без производителей, подробностей приборов,
**настроек измерений и provenance**; компактные материалы, пропуски без null.

Это обновление инфраструктуры, не новый научный результат.
Численные результаты HW2 не относятся к новому снимку.
Новые извлечение утверждений, расчёты, графики, интерпретацию и текст статьи
выполняет **агент AI4Science**, не инфраструктурный помощник.

## Проверки

Из корня проекта с установленными зависимостями [`requirements.txt`](requirements.txt):

```sh
.venv/bin/python -m pytest tools/tests checks/verifier -q
.venv/bin/python checks/verifier/run.py dry
```

Тесты проверяют реализацию и независимый договор о данных/рядах.
`dry` записывает технический манифест в `results/verifier/dry.json`;
он не запускает resampling и не выдаёт вывод об устойчивости.
Инструкция — [`checks/verifier/README.md`](checks/verifier/README.md).

Извлечение утверждений отдельно проверяет `checks/check.py` (нужны PDF).
Генерация `results/comparison.csv`, `results/summary.json` и соответствующие
проверки готовности пока не реализованы/не включены.
Правила будущего сравнения требуют отдельной научной проработки.

## Где что лежит

- [`AGENTS.md`](AGENTS.md) — задачи, ограничения и протокол агента.
- [`tools/ablation_db.py`](tools/ablation_db.py) — API только чтения снимка;
  [`tools/series.py`](tools/series.py) — чистые вычисления.
- [`checks/results_spec.md`](checks/results_spec.md) — договор API и результатов.
- `data/corpus.csv`, `data/files.csv`, `data/articles/` — корпус доступных PDF;
  он не равен полному составу снимка БД.
- `results/claims.csv`, `results/no_claims.csv` — извлечённые утверждения и
  объяснения их отсутствия; не дополнены этой миграцией.
- `src/`, `tests/` — место будущей реализации сравнения агентом.

## Сданное ДЗ 2 — неизменный тег hw2

ДЗ 2 уже сдано. Его код, старый снимок, методика, отчёт и все исходные
артефакты сохранены в теге `hw2`:
`3abd29312aa89c7e6deb3211ecc0d66c47c61f5f`.

```sh
git show hw2:results/verifier/REPORT.md
git show hw2:results/verifier/RESULTS.md
```

Для полного воспроизведения используйте отдельную копию тега, не `main`:

```sh
git clone --branch hw2 git@github.com:Kaldarinz/ai4science_proj.git hw2-check
cd hw2-check
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest checks/verifier -q
```

Ожидание `82 passed` относится **только к hw2**, не к текущему `main`.
Исторические файлы убраны из рабочей версии `results/verifier/`, а не
пересчитаны, переименованы или снабжены новыми хешами и датами.
