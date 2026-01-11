"""Generate the code reference pages."""
from pathlib import Path

import mkdocs_gen_files


nav = mkdocs_gen_files.Nav()
containing_folder = "pyrevitlib"

for path in sorted(Path(containing_folder).rglob("*.py")):
    module_path = path.relative_to(containing_folder).with_suffix("")

    parts = list(module_path.parts)
    if parts[0] != "pyrevit":
        continue
    
    doc_path = path.relative_to(containing_folder).with_suffix(".md")
    full_doc_path = Path("reference", doc_path)
    if parts[-1] == "__init__":
        parts = parts[:-1]
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")
    elif parts[-1] == "__main__":
        continue

    nav[parts] = doc_path.as_posix()

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        identifier = ".".join(parts)
        print(f"::: {identifier}", file=fd)

    mkdocs_gen_files.set_edit_path(full_doc_path, Path("../") / path)

with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())

for md in Path(".").glob("*.md"):
    try:
        with mkdocs_gen_files.open(md, "w") as f:
            f.write(Path(md).read_text(encoding='utf-8', errors='replace'))
    except UnicodeDecodeError:
        # Skip files that can't be decoded as UTF-8
        print(f"Warning: Skipping {md} due to encoding issues")
        continue
