# ASTROSOFT Classic Edition

## Architecture

PyJHora is a Python package whose desktop interface is implemented with PyQt6. The existing `ChartTabbed` widget in `horo_chart_tabs.py` is the established horoscope workflow: it gathers birth details, invokes `jhora.horoscope.info.Horoscope`, and presents chart, panchangam, dasha, bala, and related calculation views. Chart rendering is implemented by `chart_styles.py`; calculation and language resources remain in the existing `jhora` modules.

`classic_app.py` adds a `QMainWindow` shell around `ChartTabbed`. The shell provides a traditional menu bar and toolbar, a resizable three-pane workspace, multiple horoscope documents, navigation to the existing calculation tabs, and a planetary-position table built from the existing horoscope result. It does not duplicate astrology calculations. Horoscope files use a versioned UTF-8 JSON format and preserve the entered birth details, calculation method, language, and chart style.

Sinhala is registered as a language in `jhora.const.available_languages`; `utils.set_language` loads the existing `msg_strings_si.txt` and `list_values_si.txt` files. The application prefers Noto Sans Sinhala, Iskoola Pota, or Nirmala UI when installed and otherwise uses the platform font fallback.

## Run

From an installed package:

```text
astrosoft
```

For a source checkout:

```text
python -m jhora.ui.classic_app
```

## Current limits

The shell's own menu and panel captions are currently English; PyJHora's existing calculation views switch between English and the uploaded Sinhala translations. Missing Sinhala message keys are listed separately in `../lang/missing_translations_si.md`. The print-preview and print commands print the current visible horoscope view; the existing PyJHora PDF export remains available for full horoscope reports.
