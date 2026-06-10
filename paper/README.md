# Диссертация: Вопросы ввода и верификации больших данных в интерактивных наукометрических системах

**Автор / Author**: Ма Цзясин (Ma Jiaxin)
**Организация / Organization**: МГУ имени М.В. Ломоносова
**Дата / Date**: 2025

---

## Структура проекта / Project Structure

```
paper/
├── main.tex                    # Главный файл LaTeX / Main LaTeX file
├── sections/                   # Главы диссертации / Dissertation chapters
│   ├── 01_introduction.tex
│   ├── 02_literature_review.tex
│   ├── 03_methodology.tex
│   ├── 04_experiments.tex
│   ├── 05_istina_integration.tex
│   ├── 06_discussion.tex
│   ├── 07_conclusion.tex
│   └── 08_references.tex
├── bib/                        # Библиография / Bibliography
│   └── references.bib
├── figs/                       # Рисунки (если есть) / Figures (if any)
└── README.md                   # Этот файл / This file
```

---

## Требования / Requirements

### Необходимые пакеты LaTeX / Required LaTeX Packages

Диссертация использует следующие LaTeX пакеты:

- **Кодировка и язык / Encoding and Language**:
  - `fontenc` (T2A)
  - `inputenc` (utf8)
  - `babel` (russian, english)

- **Математика / Mathematics**:
  - `amsmath`
  - `amssymb`
  - `amsthm`

- **Таблицы / Tables**:
  - `booktabs` (для красивых таблиц)
  - `longtable` (для длинных таблиц)
  - `array`

- **Графика / Graphics**:
  - `graphicx`
  - `float`

- **Ссылки / References**:
  - `hyperref`
  - `url`
  - `biblatex` (backend=biber)

- **Листинги кода / Code Listings**:
  - `listings`
  - `xcolor`

- **Прочее / Other**:
  - `geometry` (для настройки полей)
  - `setspace` (для интервалов)

### Рекомендуемый дистрибутив LaTeX / Recommended LaTeX Distribution

- **Windows**: MiKTeX или TeX Live
- **Linux**: TeX Live
- **macOS**: MacTeX

---

## Компиляция / Compilation

### Метод 1: Полная компиляция (рекомендуется) / Method 1: Full Compilation (Recommended)

Для корректной обработки библиографии и перекрестных ссылок выполните следующие команды последовательно:

```bash
# 1. Первая компиляция LaTeX
pdflatex main.tex

# 2. Обработка библиографии с помощью biber
biber main

# 3. Вторая компиляция LaTeX (для обновления ссылок)
pdflatex main.tex

# 4. Третья компиляция LaTeX (для окончательной разметки)
pdflatex main.tex
```

**Примечание**: Если вы используете BibTeX вместо Biber, замените `biber main` на `bibtex main`.

### Метод 2: Использование latexmk (автоматическая компиляция) / Method 2: Using latexmk (Automatic)

```bash
latexmk -pdf -pdflatex="pdflatex -interaction=nonstopmode" main.tex
```

### Метод 3: Использование IDE / Method 3: Using an IDE

Если вы используете IDE (TeXstudio, Overleaf, TeXmaker и т.д.), просто откройте `main.tex` и нажмите кнопку "Build" или "Compile".

**Важно**: Убедитесь, что в настройках IDE выбран `biber` как backend для библиографии (не `bibtex`).

---

## Очистка временных файлов / Cleaning Temporary Files

После компиляции генерируется множество временных файлов. Для их удаления:

### Windows (PowerShell)

```powershell
Remove-Item *.aux, *.bbl, *.bcf, *.blg, *.log, *.out, *.run.xml, *.toc, *.lof, *.lot
```

### Linux/macOS (Bash)

```bash
rm -f *.aux *.bbl *.bcf *.blg *.log *.out *.run.xml *.toc *.lof *.lot
```

### Используя latexmk

```bash
latexmk -c
```

---

## Проверка компиляции / Verification of Compilation

### Успешная компиляция / Successful Compilation

Если компиляция прошла успешно, вы увидите:

1. Файл `main.pdf` в директории `paper/`
2. Сообщение в логе:
   ```
   Output written on main.pdf (X pages, Y bytes).
   Transcript written on main.log.
   ```

### Типичные ошибки / Common Errors

#### Ошибка 1: "! LaTeX Error: File `booktabs.sty' not found."

**Решение**: Установите пакет `booktabs` через менеджер пакетов вашего дистрибутива LaTeX.

**MiKTeX (Windows)**:
```bash
mpm --install=booktabs
```

**TeX Live (Linux/macOS)**:
```bash
tlmgr install booktabs
```

#### Ошибка 2: "! Package babel Error: Unknown language `russian'."

**Решение**: Установите языковую поддержку для русского языка:

**MiKTeX**:
```bash
mpm --install=babel-russian
```

**TeX Live**:
```bash
tlmgr install babel-russian
```

#### Ошибка 3: "! I can't find file `main.bbl'."

**Решение**: Убедитесь, что вы выполнили команду `biber main` после первой компиляции `pdflatex main.tex`.

---

## Добавление контента / Adding Content

### Добавление новой главы / Adding a New Chapter

1. Создайте новый файл в `sections/`, например `09_appendix.tex`
2. Добавьте `\input{sections/09_appendix}` в `main.tex` в нужном месте

### Добавление таблицы из runs/ / Adding a Table from runs/

Таблицы из экспериментов автоматически импортируются с помощью `\input{}`:

```latex
% Пример в sections/04_experiments.tex
\input{../runs/evidence_chain_301k_P0_P5_FINAL_V2/statistics/stats_ci_global.tex}
```

**Важно**: Путь указывается относительно `main.tex`, поэтому используйте `../runs/`.

### Добавление рисунка / Adding a Figure

1. Поместите файл изображения в `figs/`, например `figs/architecture.png`
2. Используйте следующий код в нужной секции:

```latex
\begin{figure}[htbp]
\centering
\includegraphics[width=0.8\textwidth]{figs/architecture.png}
\caption{Архитектура системы}
\label{fig:architecture}
\end{figure}
```

### Добавление ссылки в библиографию / Adding a Reference to Bibliography

Добавьте запись в `bib/references.bib`:

```bibtex
@article{ma2025chinese,
  title={Automated Verification of Chinese Name Order in Scientific Publications},
  author={Ma, Jiaxin},
  journal={Journal of Scientometrics},
  year={2025},
  volume={10},
  pages={1--20}
}
```

Затем цитируйте в тексте:

```latex
Как показано в работе~\cite{ma2025chinese}, ...
```

---

## Статус TODO / TODO Status

### Обязательные TODO / Critical TODOs

- [ ] Заполнить английский Abstract (sections/01_introduction.tex)
- [ ] Указать имя научного руководителя (main.tex)
- [ ] Добавить конференции и публикации (sections/01_introduction.tex)
- [ ] Добавить ссылки в bib/references.bib
- [ ] Заполнить все секции [TODO] в sections/*.tex

### Рекомендуемые TODO / Recommended TODOs

- [ ] Добавить рисунки архитектуры в figs/
- [ ] Вставить конкретные значения точности и производительности
- [ ] Добавить примеры входных/выходных данных в приложения

---

## Воспроизводимость / Reproducibility

### Версия LaTeX / LaTeX Version

Этот проект был протестирован с:

- **TeX Live 2023** (Linux)
- **MiKTeX 23.10** (Windows)

### Версия компилятора / Compiler Version

- **pdflatex**: pdfTeX 3.141592653-2.6-1.40.25 (TeX Live 2023)
- **biber**: Version 2.19

---

## Контакты / Contact

**Автор / Author**: Ма Цзясин (Ma Jiaxin)
**Email**: [TODO: insert email]
**GitHub**: https://github.com/Soulbeaters/Chinese-name

---

**Последнее обновление / Last Updated**: 2025-12-21
