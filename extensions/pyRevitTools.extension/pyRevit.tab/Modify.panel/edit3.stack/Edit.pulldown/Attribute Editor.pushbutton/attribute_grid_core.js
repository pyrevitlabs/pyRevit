/*
 * Pure logic of the Attribute Editor grid, without any DOM access, so it can be
 * tested on its own: clipboard text (TSV as Excel writes it), Excel-style fill
 * series, natural sorting and the merge of freshly read Revit rows into rows
 * that carry unsent edits.
 *
 * Exposed as window.pyRevitAttributeGridCore.
 */
(function () {
  "use strict";

  const NUMBER_PATTERN = /^([\s\S]*?)(\d+(?:[.,]\d+)?)(\D*)$/;

  function parseTsv(text) {
    const rows = [];
    const source = String(text).replace(/\r\n/g, "\n").replace(/\r/g, "\n");
    let row = [];
    let field = "";
    let quoted = false;
    for (let i = 0; i < source.length; i++) {
      const ch = source[i];
      if (quoted) {
        if (ch === '"') {
          if (source[i + 1] === '"') {
            field += '"';
            i++;
          } else {
            quoted = false;
          }
        } else {
          field += ch;
        }
      } else if (ch === '"' && field === "") {
        quoted = true;
      } else if (ch === "\t") {
        row.push(field);
        field = "";
      } else if (ch === "\n") {
        row.push(field);
        rows.push(row);
        row = [];
        field = "";
      } else {
        field += ch;
      }
    }
    if (field !== "" || row.length) {
      row.push(field);
      rows.push(row);
    }
    return rows;
  }

  function formatTsv(rows) {
    return rows
      .map((row) =>
        row.map((value) => (/[\t\n\r"]/.test(value) ? '"' + value.replace(/"/g, '""') + '"' : value)).join("\t")
      )
      .join("\n");
  }

  function splitNumber(text) {
    const match = NUMBER_PATTERN.exec(String(text));
    if (!match) return null;
    let prefix = match[1];
    let digits = match[2];
    if (prefix === "-") {
      prefix = "";
      digits = "-" + digits;
    }
    const fraction = digits.split(/[.,]/)[1] || "";
    const separator = /,/.test(digits) ? "," : ".";
    const unsigned = digits.replace("-", "");
    return {
      prefix,
      suffix: match[3],
      value: parseFloat(digits.replace(",", ".")),
      decimals: fraction.length,
      separator,
      padWidth: !fraction && unsigned.length > 1 && unsigned[0] === "0" ? unsigned.length : 0,
    };
  }

  function formatNumber(value, shape) {
    const negative = value < 0;
    let digits = Math.abs(value).toFixed(shape.decimals);
    if (shape.padWidth) digits = digits.padStart(shape.padWidth, "0");
    if (shape.separator === ",") digits = digits.replace(".", ",");
    return shape.prefix + (negative ? "-" : "") + digits + shape.suffix;
  }

  function fillSeries(seed, count, options) {
    const settings = options || {};
    const out = [];
    if (!seed.length || count <= 0) return out;
    const parts = seed.map(splitNumber);
    const first = parts[0];
    const uniform =
      first !== null && parts.every((p) => p && p.prefix === first.prefix && p.suffix === first.suffix);
    let step = 0;
    if (uniform && seed.length >= 2) {
      step = (parts[parts.length - 1].value - first.value) / (seed.length - 1);
    } else if (uniform && seed.length === 1) {
      const endsWithNumber = first.prefix !== "" && first.suffix === "";
      const increments = settings.invert ? !endsWithNumber : endsWithNumber;
      step = increments ? 1 : 0;
    }
    if (step === 0) {
      for (let k = 0; k < count; k++) {
        out.push(settings.backward ? seed[(seed.length - 1 - (k % seed.length) + seed.length) % seed.length] : seed[k % seed.length]);
      }
      return out;
    }
    const shape = {
      prefix: first.prefix,
      suffix: first.suffix,
      decimals: Math.max(...parts.map((p) => p.decimals)),
      separator: (parts.find((p) => p.decimals) || first).separator,
      padWidth: Math.max(...parts.map((p) => p.padWidth)),
    };
    const anchor = settings.backward ? first.value : parts[parts.length - 1].value;
    const direction = settings.backward ? -step : step;
    for (let k = 1; k <= count; k++) out.push(formatNumber(anchor + direction * k, shape));
    return out;
  }

  function naturalCompare(a, b) {
    return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });
  }

  function isTypeKey(key) {
    return key.endsWith("|t");
  }

  function mergeRows(oldRows, oldKeys, newRows, newKeys) {
    const oldById = new Map(oldRows.map((row) => [row.id, row]));
    const oldIndex = new Map(oldKeys.map((key, index) => [key, index]));
    const typeEdits = new Map();
    for (const row of oldRows) {
      oldKeys.forEach((key, index) => {
        if (!isTypeKey(key) || row.cur[index] === row.base[index]) return;
        const tag = row.t + "|" + key;
        if (!typeEdits.has(tag)) {
          typeEdits.set(tag, { cur: row.cur[index], base: row.base[index], conflict: row.conflicts.has(index) });
        }
      });
    }
    const carriedTypeEdits = new Set();
    const merged = [];
    let dropped = 0;
    let conflicts = 0;
    for (const fresh of newRows) {
      const row = {
        id: fresh.id,
        t: fresh.t,
        c: fresh.c,
        base: fresh.v.slice(),
        cur: fresh.v.slice(),
        locked: new Set(fresh.x),
        conflicts: new Map(),
        errors: new Map(),
      };
      const previous = oldById.get(fresh.id);
      newKeys.forEach((key, index) => {
        let edit = null;
        let tag = null;
        if (isTypeKey(key)) {
          tag = fresh.t + "|" + key;
          edit = typeEdits.get(tag) || null;
        } else if (previous) {
          const was = oldIndex.get(key);
          if (was !== undefined && previous.cur[was] !== previous.base[was]) {
            edit = { cur: previous.cur[was], base: previous.base[was], conflict: previous.conflicts.has(was) };
          }
        }
        if (!edit) return;
        if (row.locked.has(index)) {
          if (!tag) dropped++;
          return;
        }
        row.cur[index] = edit.cur;
        const revitMoved = fresh.v[index] !== edit.base || edit.conflict;
        const firstOfType = tag === null || !carriedTypeEdits.has(tag);
        if (revitMoved && fresh.v[index] !== edit.cur) {
          row.conflicts.set(index, fresh.v[index]);
          if (firstOfType) conflicts++;
        }
        if (tag) carriedTypeEdits.add(tag);
      });
      merged.push(row);
    }
    for (const tag of typeEdits.keys()) {
      if (!carriedTypeEdits.has(tag)) dropped++;
    }
    const freshIds = new Set(newRows.map((row) => row.id));
    const keptKeys = new Set(newKeys);
    const instanceEdits = (row, wanted) =>
      oldKeys.filter((key, index) => !isTypeKey(key) && wanted(key) && row.cur[index] !== row.base[index]).length;
    for (const row of oldRows) {
      if (!freshIds.has(row.id)) {
        if (instanceEdits(row, () => true)) dropped++;
      } else {
        dropped += instanceEdits(row, (key) => !keptKeys.has(key));
      }
    }
    return { rows: merged, dropped, conflicts };
  }

  window.pyRevitAttributeGridCore = {
    parseTsv,
    formatTsv,
    splitNumber,
    fillSeries,
    naturalCompare,
    mergeRows,
  };
})();
