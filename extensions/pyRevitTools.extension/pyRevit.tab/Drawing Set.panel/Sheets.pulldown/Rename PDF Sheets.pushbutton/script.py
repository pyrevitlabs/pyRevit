# -*- coding: utf-8 -*-
import sys
import os.path as op
import re

from pathlib import Path

from pyrevit import forms, EXEC_PARAMS
from pyrevit.coreutils.applocales import get_locale_string


# Localised UI strings

STR = {
    "include_subfolders": {
        "en_us": "Do you want to include subfolders?",
        "fr_fr": "Voulez-vous inclure les sous-dossiers ?",
        "ru": "Включить подпапки?",
        "chinese_s": "是否包含子文件夹？",
        "es_es": "¿Desea incluir subcarpetas?",
        "de_de": "Sollen Unterordner eingeschlossen werden?",
        "pt_br": "Deseja incluir subpastas?",
    },
    "config_mode_notice": {
        "en_us": "Config mode: using desktop folder -> {}",
        "fr_fr": "Mode config : dossier bureau utilisé -> {}",
        "ru": "Режим настройки: используется папка рабочего стола -> {}",
        "chinese_s": "配置模式：使用桌面文件夹 -> {}",
        "es_es": "Modo config: usando carpeta de escritorio -> {}",
        "de_de": "Konfigurationsmodus: Desktop-Ordner wird verwendet -> {}",
        "pt_br": "Modo config: usando pasta da área de trabalho -> {}",
    },
    "not_renamed_exists": {
        "en_us": "File NOT renamed (target already exists): {}",
        "fr_fr": "Fichier NON renommé (cible déjà existante) : {}",
        "ru": "Файл НЕ переименован (цель уже существует): {}",
        "chinese_s": "文件未重命名（目标已存在）：{}",
        "es_es": "Archivo NO renombrado (el destino ya existe): {}",
        "de_de": "Datei NICHT umbenannt (Ziel existiert bereits): {}",
        "pt_br": "Arquivo NÃO renomeado (destino já existe): {}",
    },
    "not_renamed_locked": {
        "en_us": "File NOT renamed (access error, file may be open): {}",
        "fr_fr": "Fichier NON renommé (erreur d'accès, fichier peut-être ouvert) : {}",
        "ru": "Файл НЕ переименован (ошибка доступа, файл может быть открыт): {}",
        "chinese_s": "文件未重命名（访问错误，文件可能已打开）：{}",
        "es_es": "Archivo NO renombrado (error de acceso, puede estar abierto): {}",
        "de_de": "Datei NICHT umbenannt (Zugriffsfehler, Datei möglicherweise geöffnet): {}",
        "pt_br": "Arquivo NÃO renomeado (arquivo pode estar aberto): {}",
    },
    "not_renamed_bad_name": {
        "en_us": "File NOT renamed (name processing failed): {}",
        "fr_fr": "Fichier NON renommé (traitement du nom échoué) : {}",
        "ru": "Файл НЕ переименован (ошибка обработки имени): {}",
        "chinese_s": "文件未重命名（名称处理失败）：{}",
        "es_es": "Archivo NO renombrado (fallo al procesar el nombre): {}",
        "de_de": "Datei NICHT umbenannt (Namensverarbeitung fehlgeschlagen): {}",
        "pt_br": "Arquivo NÃO renomeado (falha no processamento do nome): {}",
    },
    "summary": {
        "en_us": (
            "{pdf_count} PDF files found\n"
            "{sheet_count} files matching sheet prefix\n"
            "{rename_count} files renamed\n"
            "{err_count} errors"
        ),
        "fr_fr": (
            "{pdf_count} fichiers PDF trouvés\n"
            "{sheet_count} fichiers avec préfixe de feuille\n"
            "{rename_count} fichiers renommés\n"
            "{err_count} erreurs"
        ),
        "ru": (
            "{pdf_count} файлов PDF найдено\n"
            "{sheet_count} файлов с префиксом листа\n"
            "{rename_count} файлов переименовано\n"
            "{err_count} ошибок"
        ),
        "chinese_s": (
            "共找到 {pdf_count} 个 PDF 文件\n"
            "{sheet_count} 个文件匹配图纸前缀\n"
            "{rename_count} 个文件已重命名\n"
            "{err_count} 个错误"
        ),
        "es_es": (
            "{pdf_count} archivos PDF encontrados\n"
            "{sheet_count} archivos con prefijo de hoja\n"
            "{rename_count} archivos renombrados\n"
            "{err_count} errores"
        ),
        "de_de": (
            "{pdf_count} PDF-Dateien gefunden\n"
            "{sheet_count} Dateien mit Blatt-Präfix\n"
            "{rename_count} Dateien umbenannt\n"
            "{err_count} Fehler"
        ),
        "pt_br": (
            "{pdf_count} arquivos PDF encontrados\n"
            "{sheet_count} arquivos com prefixo de folha\n"
            "{rename_count} arquivos renomeados\n"
            "{err_count} erros"
        ),
    },
}

# Sheet prefix terms per locale
# Used to build the prefix-stripping regex dynamically.
# Each entry is a list of terms that Revit uses in that locale for "Sheet".

SHEET_TERMS = {
    "en_us": ["Sheet"],
    "fr_fr": ["Feuille"],
    "ru": ["Лист"],
    "chinese_s": ["图纸"],
    "es_es": ["Lámina", "Hoja"],
    "de_de": ["Blatt"],
    "pt_br": ["Prancha", "Folha"],
}

# Collect all unique terms across all locales for the regex
_all_terms = []
for _terms in SHEET_TERMS.values():
    for _t in _terms:
        if _t not in _all_terms:
            _all_terms.append(_t)

# Matches the full "Sheet - " (or equivalent) prefix, case-insensitive
prefix_stripper = re.compile(
    r"^.*?(?:{terms})\s*-\s*".format(terms="|".join(re.escape(t) for t in _all_terms)),
    re.IGNORECASE | re.UNICODE,
)

# Capitalise everything after the last hyphen
capitalizer = re.compile(r"-(?!.*-)\s*(.*)", re.UNICODE)

# Normalise hyphens surrounded by whitespace
normalizer = re.compile(r"\s*-\s*", re.UNICODE)


# Core rename logic


def renamepdf(old_name):
    """Strip the sheet prefix and normalise the remaining name."""
    new_name = prefix_stripper.sub("", old_name)
    new_name = capitalizer.sub(lambda m: "-{}".format(m.group(1).upper()), new_name)
    new_name = normalizer.sub("-", new_name)
    if not new_name:
        raise ValueError("Renaming '{}' results in an empty string.".format(old_name))
    return new_name


# Folder selection

if EXEC_PARAMS.config_mode:
    basefolder = op.expandvars(r"%userprofile%\desktop")
    print(get_locale_string(STR["config_mode_notice"]).format(basefolder))
else:
    basefolder = forms.pick_folder()

if not basefolder:
    sys.exit()

# Subfolder choice

include_subfolders = forms.alert(
    get_locale_string(STR["include_subfolders"]),
    yes=True,
    no=True,
)
dir_pattern = "**/" if include_subfolders else ""

# Main loop

pdf_files = list(Path(basefolder).glob("{}*.pdf".format(dir_pattern)))
pdf_count = len(pdf_files)
sheet_count = rename_count = err_count = 0

for pdf_file in pdf_files:
    if not prefix_stripper.search(pdf_file.stem):
        continue
    sheet_count += 1

    # --- compute new name ---
    try:
        new_stem = renamepdf(pdf_file.stem)
    except (ValueError, re.error) as e:
        err_count += 1
        print(get_locale_string(STR["not_renamed_bad_name"]).format(pdf_file))
        print("  -> {}".format(e))
        continue

    target = pdf_file.with_name("{}.pdf".format(new_stem))

    # --- guard: target already exists ---
    if target.exists():
        err_count += 1
        print(get_locale_string(STR["not_renamed_exists"]).format(pdf_file))
        print("  -> {}".format(target))
        continue

    # --- rename ---
    try:
        pdf_file.rename(target)
        rename_count += 1
    except OSError as e:
        import errno as _errno
        err_count += 1
        if e.errno == _errno.EEXIST:
            print(get_locale_string(STR["not_renamed_exists"]).format(pdf_file))
            print("  -> {}".format(target))
        else:
            print(get_locale_string(STR["not_renamed_locked"]).format(pdf_file))
            print("  -> {}".format(e))

# Summary

forms.alert(
    get_locale_string(STR["summary"]).format(
        pdf_count=pdf_count,
        sheet_count=sheet_count,
        rename_count=rename_count,
        err_count=err_count,
    )
)
