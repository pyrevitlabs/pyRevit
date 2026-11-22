/*
 * Spreadsheet-like editor page of the Attribute Editor tool.
 *
 * window.pyRevitAttributeGrid.mount(rootId, data) renders the editor into the
 * element with id rootId. data comes from attribute_session.AttributeSession:
 * {channel, strings, dark, themePreference, start}. The page posts
 * {channel, action, payload, requestId} through chrome.webview.postMessage and
 * Python answers with {channel, event, payload} messages (events: result,
 * error, dispose). Pure helpers live in attribute_grid_core.js.
 */
(function () {
  "use strict";

  const core = window.pyRevitAttributeGridCore;
  const apps = new Map();
  let listening = false;

  const ROW_HEIGHT = 26;
  const HEAD_HEIGHT = 30;
  const FILTER_HEIGHT = 26;
  const ROWHEAD_WIDTH = 124;
  const MIN_WIDTH = 56;
  const BUFFER_ROWS = 6;

  function listen() {
    if (listening || !(window.chrome && window.chrome.webview)) return;
    listening = true;
    window.chrome.webview.addEventListener("message", (event) => {
      const message = event.data;
      const app = message && apps.get(message.channel);
      if (app) app.receive(message.event, message.payload);
    });
  }

  function h(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      if (value === null || value === undefined || value === false) continue;
      if (key === "class") node.className = value;
      else if (key === "dataset") Object.assign(node.dataset, value);
      else if (key === "style") node.style.cssText = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else if (value === true) node.setAttribute(key, "");
      else node.setAttribute(key, value);
    }
    for (const child of children.flat()) {
      if (child === null || child === undefined || child === false) continue;
      node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return node;
  }

  function format(template, ...values) {
    return String(template).replace(/\{(\d+)\}/g, (_, i) => (values[i] !== undefined ? values[i] : ""));
  }

  function clamp(value, low, high) {
    return Math.max(low, Math.min(high, value));
  }

  class App {
    constructor(root, data) {
      this.root = root;
      this.data = data;
      this.strings = data.strings;
      this.requests = new Map();
      this.requestSeq = 0;
      this.generation = 0;
      this.loadSeq = 0;
      this.source = data.start;
      this.title = "";
      this.unitMode = "display";
      this.columns = [];
      this.rows = [];
      this.view = [];
      this.byType = new Map();
      this.sort = [];
      this.filters = new Map();
      this.widths = new Map();
      this.frozen = 0;
      this.anchor = null;
      this.focus = null;
      this.undoStack = [];
      this.redoStack = [];
      this.editing = null;
      this.drag = null;
      this.fillPreview = null;
      this.schedules = [];
      this.categories = [];
      this.available = [];
      this.known = new Map();
      this.plan = [];
      this.builder = { picked: new Set(), scope: "model", types: false, scanAll: false, filter: "" };
      this.themePreference = data.themePreference || "auto";
      this.offsets = [];
      this.totalWidth = ROWHEAD_WIDTH;
      this.busy = 0;
      this.renderQueued = false;
      this.matches = [];
      root.classList.add("ae-root");
      this.buildDom();
      this.applyTheme();
      this.bindEvents();
      this.bootstrap();
    }

    S(key, ...values) {
      const template = this.strings["ui_" + key];
      return format(template === undefined ? key : template, ...values);
    }

    request(action, payload) {
      return new Promise((resolve, reject) => {
        if (!(window.chrome && window.chrome.webview)) {
          reject(new Error(this.S("bridge_offline")));
          return;
        }
        const requestId = ++this.requestSeq;
        this.requests.set(requestId, { resolve, reject });
        window.chrome.webview.postMessage({ channel: this.data.channel, action, payload, requestId });
      });
    }

    receive(event, payload) {
      if (event === "result" || event === "error") {
        const pending = this.requests.get(payload.requestId);
        if (!pending) {
          if (event === "error") this.toast(payload.message, "error");
          return;
        }
        this.requests.delete(payload.requestId);
        if (event === "result" && payload.ok) pending.resolve(payload.message);
        else pending.reject(new Error(payload.message || "?"));
      } else if (event === "dispose") {
        this.dispose();
      }
    }

    dispose() {
      apps.delete(this.data.channel);
      document.removeEventListener("mousemove", this.onDocumentMouseMove);
      document.removeEventListener("mouseup", this.onDocumentMouseUp);
      this.root.remove();
    }

    toast(message, kind) {
      if (!message) return;
      const node = h("div", { class: "ae-toast " + (kind || "info") }, message);
      this.toasts.append(node);
      setTimeout(() => node.remove(), kind === "error" ? 9000 : 4500);
    }

    confirm(message, acceptLabel) {
      return new Promise((resolve) => {
        const close = (answer) => {
          overlay.remove();
          resolve(answer);
        };
        const overlay = h(
          "div",
          { class: "ae-modal" },
          h(
            "div",
            { class: "ae-dialog" },
            h("p", {}, message),
            h(
              "div",
              { class: "ae-dialog-buttons" },
              h("button", { class: "ae-button", onclick: () => close(false) }, this.S("cancel")),
              h("button", { class: "ae-button primary", onclick: () => close(true) }, acceptLabel)
            )
          )
        );
        this.root.append(overlay);
      });
    }

    setBusy(on) {
      this.busy += on ? 1 : -1;
      this.root.classList.toggle("busy", this.busy > 0);
      this.renderToolbar();
    }

    buildDom() {
      this.toolbar = h("div", { class: "ae-toolbar" });
      this.conflictBar = h("div", { class: "ae-conflictbar", hidden: true });
      this.findBar = h("div", { class: "ae-findbar", hidden: true });
      this.panel = h("div", { class: "ae-panel", hidden: true });
      this.header = h("div", { class: "ae-header" });
      this.body = h("div", { class: "ae-body" });
      this.editor = h("input", { class: "ae-editor", type: "text", hidden: true, autocomplete: "off" });
      this.fillHandle = h("div", { class: "ae-fill", hidden: true });
      this.emptyNote = h("div", { class: "ae-empty", hidden: true });
      this.sizer = h("div", { class: "ae-sizer" }, this.header, this.body, this.editor, this.fillHandle);
      this.scroll = h("div", { class: "ae-scroll" }, this.sizer);
      this.clip = h("textarea", { class: "ae-clip", tabindex: "0", "aria-label": "grid" });
      this.status = h("div", { class: "ae-status" });
      this.toasts = h("div", { class: "ae-toasts" });
      this.lists = h("div", { class: "ae-lists" });
      this.grid = h("div", { class: "ae-gridwrap" }, this.scroll, this.emptyNote, this.clip);
      this.root.append(
        this.toolbar,
        this.conflictBar,
        this.findBar,
        h("div", { class: "ae-main" }, this.panel, this.grid),
        this.status,
        this.toasts,
        this.lists
      );
      this.buildPanel();
      this.buildFindBar();
    }

    applyTheme() {
      let dark = this.data.dark;
      if (this.themePreference === "light") dark = false;
      else if (this.themePreference === "dark") dark = true;
      else if (dark === undefined || dark === null) dark = !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
      this.root.dataset.theme = dark ? "dark" : "light";
    }

    async bootstrap() {
      try {
        this.schedules = await this.request("schedules", {});
      } catch (error) {
        this.toast(error.message, "error");
      }
      this.renderToolbar();
      if (this.source.kind === "schedule") {
        await this.load({ columns: null, fresh: true });
        this.refreshAvailable();
      } else {
        this.openScratch();
      }
    }

    openScratch() {
      this.source = { kind: "scratch", categories: [], scope: "model", types: false };
      this.panel.hidden = false;
      this.renderToolbar();
      this.renderPanel();
      if (!this.categories.length) {
        this.request("categories", {})
          .then((categories) => {
            this.categories = categories;
            this.renderPanel();
          })
          .catch((error) => this.toast(error.message, "error"));
      }
      this.renderAll();
    }

    async load(options) {
      const settings = options || {};
      const keys = settings.columns !== undefined ? settings.columns : this.columns.length ? this.columns.map((c) => c.key) : null;
      if (this.source.kind === "scratch" && (!keys || !keys.length)) {
        this.renderAll();
        return false;
      }
      const loadId = ++this.loadSeq;
      this.setBusy(true);
      try {
        const grid = await this.request("load", {
          source: this.source,
          columns: keys,
          unitMode: settings.unitMode || this.unitMode,
        });
        if (loadId !== this.loadSeq) return null;
        this.applyGrid(grid, !settings.fresh && this.rows.length > 0 && !!this.loadedSource && this.sameSource(this.loadedSource, grid.source));
        return true;
      } catch (error) {
        if (loadId !== this.loadSeq) return null;
        this.toast(error.message, "error");
        return false;
      } finally {
        this.setBusy(false);
      }
    }

    applyGrid(grid, merge) {
      const oldKeys = this.columns.map((c) => c.key);
      const newKeys = grid.columns.map((c) => c.key);
      if (!merge) this.generation++;
      this.source = grid.source;
      this.loadedSource = grid.source;
      this.title = grid.title;
      this.unitMode = grid.unitMode;
      this.columns = grid.columns;
      for (const column of this.columns) {
        this.known.set(column.key, { heading: column.heading, scope: column.scope });
      }
      const merged = core.mergeRows(merge ? this.rows : [], merge ? oldKeys : [], grid.rows, newKeys);
      this.rows = merged.rows;
      if (!merge) this.sort = grid.sort.slice();
      this.plan = newKeys.slice();
      this.undoStack = [];
      this.redoStack = [];
      this.editing = null;
      this.byType = new Map();
      for (const row of this.rows) {
        if (!this.byType.has(row.t)) this.byType.set(row.t, []);
        this.byType.get(row.t).push(row);
      }
      this.frozen = Math.min(this.frozen, this.columns.length);
      this.recomputeView();
      this.anchor = this.focus = this.view.length && this.columns.length ? { r: 0, c: 0 } : null;
      if (merged.dropped) this.toast(this.S("dropped_edits", merged.dropped), "warn");
      if (merged.conflicts) this.toast(this.S("pull_conflicts", merged.conflicts), "warn");
      this.renderPanel();
      this.renderAll();
    }

    recomputeView() {
      let indices = this.rows.map((_, index) => index);
      for (const [key, text] of this.filters) {
        const ci = this.columns.findIndex((c) => c.key === key);
        if (ci < 0 || !text) continue;
        const needle = text.toLowerCase();
        indices = indices.filter((i) => this.rows[i].cur[ci].toLowerCase().includes(needle));
      }
      const order = this.sort
        .map((entry) => ({ ci: this.columns.findIndex((c) => c.key === entry.key), sign: entry.dir === "desc" ? -1 : 1 }))
        .filter((entry) => entry.ci >= 0);
      if (order.length) {
        indices.sort((a, b) => {
          for (const { ci, sign } of order) {
            const result = core.naturalCompare(this.rows[a].cur[ci], this.rows[b].cur[ci]);
            if (result) return result * sign;
          }
          return this.rows[a].id - this.rows[b].id;
        });
      }
      this.view = indices;
    }

    columnWidth(column) {
      if (this.widths.has(column.key)) return this.widths.get(column.key);
      const icons = 30 + (column.scope === "t" ? 24 : 0) + (column.readOnly ? 22 : 0);
      return clamp(column.heading.length * 8 + 28 + icons, 100, 240);
    }

    layoutColumns() {
      this.offsets = [];
      let x = ROWHEAD_WIDTH;
      for (const column of this.columns) {
        this.offsets.push(x);
        x += this.columnWidth(column);
      }
      this.totalWidth = x;
    }

    queueRender() {
      if (this.renderQueued) return;
      this.renderQueued = true;
      requestAnimationFrame(() => {
        this.renderQueued = false;
        this.renderBody();
      });
    }

    renderAll() {
      this.layoutColumns();
      this.renderToolbar();
      this.renderHeader();
      this.renderBody();
      this.renderStatus();
      this.renderConflictBar();
      const empty = !this.columns.length || !this.view.length;
      this.emptyNote.hidden = !empty;
      this.emptyNote.textContent = !this.columns.length
        ? this.source.kind === "scratch"
          ? this.S("empty_scratch")
          : this.S("empty_columns")
        : this.S("empty_rows");
    }

    renderToolbar() {
      const pending = this.countPending();
      const busy = this.busy > 0;
      const select = h(
        "select",
        { class: "ae-select", title: this.S("source_hint"), onchange: (e) => this.onSourceChange(e.target.value) },
        h("option", { value: "__scratch__", selected: this.source.kind === "scratch" }, this.S("new_grid")),
        this.schedules.map((item) =>
          h("option", { value: String(item.id), selected: this.source.kind === "schedule" && this.source.id === item.id }, item.name)
        )
      );
      const unitButtons = ["display", "number", "internal"].map((mode) =>
        h(
          "button",
          {
            class: "ae-seg" + (this.unitMode === mode ? " on" : ""),
            title: this.S("unit_" + mode + "_hint"),
            disabled: busy,
            onclick: () => this.setUnitMode(mode),
          },
          this.S("unit_" + mode)
        )
      );
      const themeButtons = ["auto", "light", "dark"].map((mode) =>
        h(
          "button",
          { class: "ae-seg" + (this.themePreference === mode ? " on" : ""), onclick: () => this.setTheme(mode) },
          this.S("theme_" + mode)
        )
      );
      this.toolbar.replaceChildren(
        select,
        h("button", { class: "ae-button", title: this.S("pull_hint"), disabled: busy || this.source.kind === "scratch" && !this.columns.length, onclick: () => this.pull() }, "↻ " + this.S("pull")),
        h("button", { class: "ae-button primary", title: this.S("push_hint"), disabled: busy || !pending, onclick: () => this.push(false, false) }, "↑ " + this.S("push", pending)),
        h("button", { class: "ae-button", title: this.S("check_hint"), disabled: busy || !pending, onclick: () => this.push(false, true) }, "✓ " + this.S("check")),
        h("span", { class: "ae-sep" }),
        h("button", { class: "ae-button", title: this.S("undo"), disabled: !this.undoStack.length, onclick: () => this.undo() }, "↶"),
        h("button", { class: "ae-button", title: this.S("redo"), disabled: !this.redoStack.length, onclick: () => this.redo() }, "↷"),
        h("button", { class: "ae-button" + (this.findBar.hidden ? "" : " on"), title: "Ctrl+F", onclick: () => this.toggleFind() }, this.S("find")),
        h("button", { class: "ae-button", title: this.S("show_in_revit_hint"), disabled: !this.selectedIds().length, onclick: () => this.showInRevit() }, this.S("show_in_revit")),
        h("span", { class: "ae-sep" }),
        h("span", { class: "ae-label" }, this.S("units")),
        h("span", { class: "ae-segs" }, unitButtons),
        h("span", { class: "ae-spacer" }),
        h("span", { class: "ae-segs", title: this.S("theme_hint") }, themeButtons),
        h("button", { class: "ae-button" + (this.panel.hidden ? "" : " on"), onclick: () => this.togglePanel() }, this.S("columns"))
      );
    }

    isConflict(row, ci) {
      return row.conflicts.has(ci) && row.cur[ci] !== row.conflicts.get(ci);
    }

    countConflicts() {
      let count = 0;
      const seenTypes = new Set();
      for (const row of this.rows) {
        for (const ci of row.conflicts.keys()) {
          if (!this.isConflict(row, ci)) continue;
          if (this.columns[ci].scope === "t") {
            const tag = row.t + ":" + ci;
            if (seenTypes.has(tag)) continue;
            seenTypes.add(tag);
          }
          count++;
        }
      }
      return count;
    }

    renderConflictBar() {
      const count = this.countConflicts();
      this.conflictBar.hidden = !count;
      if (!count) return;
      this.conflictBar.replaceChildren(
        h("span", {}, this.S("conflict_text", count)),
        h("button", { class: "ae-button", onclick: () => this.resolveConflicts(true) }, this.S("keep_mine")),
        h("button", { class: "ae-button", onclick: () => this.resolveConflicts(false) }, this.S("use_revit"))
      );
    }

    renderStatus() {
      const parts = [this.S("status_rows", this.view.length, this.rows.length, this.columns.length)];
      const rect = this.rect();
      if (rect && (rect.r2 > rect.r1 || rect.c2 > rect.c1)) {
        parts.push(this.S("status_selection", rect.r2 - rect.r1 + 1, rect.c2 - rect.c1 + 1));
      }
      const pending = this.countPending();
      if (pending) parts.push(this.S("status_pending", pending));
      if (this.title) parts.unshift(this.title);
      this.status.replaceChildren(...parts.map((text) => h("span", {}, text)));
    }

    renderHeader() {
      const titles = h("div", { class: "ae-hrow", style: "height:" + HEAD_HEIGHT + "px;width:" + this.totalWidth + "px" });
      const filters = h("div", { class: "ae-hrow filters", style: "height:" + FILTER_HEIGHT + "px;width:" + this.totalWidth + "px" });
      titles.append(h("div", { class: "ae-rowhead hcell", style: "width:" + ROWHEAD_WIDTH + "px", title: this.S("rowhead_hint"), onmousedown: () => this.selectAll() }, "Id"));
      filters.append(h("div", { class: "ae-rowhead hcell", style: "width:" + ROWHEAD_WIDTH + "px" }));
      this.columns.forEach((column, ci) => {
        const sorted = this.sort.find((entry) => entry.key === column.key);
        const frozen = ci < this.frozen;
        const style = "width:" + this.columnWidth(column) + "px" + (frozen ? ";left:" + this.offsets[ci] + "px" : "");
        const badges = [];
        if (column.scope === "t") badges.push(h("span", { class: "ae-badge", title: this.S("type_hint") }, "T"));
        if (column.readOnly) badges.push(h("span", { class: "ae-badge ro", title: this.S("locked_hint") }, "\u{1F512}"));
        const resize = h("span", { class: "ae-resize", onmousedown: (e) => this.beginResize(e, ci) });
        titles.append(
          h(
            "div",
            { class: "ae-hcell" + (frozen ? " frozen" : ""), style, title: column.name || column.heading, onmousedown: (e) => this.onHeaderMouseDown(e, ci) },
            h("span", { class: "ae-htext" }, column.heading, column.unit && this.unitMode !== "display" ? h("em", {}, " [" + column.unit + "]") : null),
            badges,
            h("button", { class: "ae-sort" + (sorted ? " on" : ""), title: this.S("sort_hint"), onmousedown: (e) => e.stopPropagation(), onclick: (e) => this.cycleSort(column.key, e.shiftKey) }, sorted ? (sorted.dir === "asc" ? "▲" : "▼") : "⇅"),
            resize
          )
        );
        const input = h("input", {
          class: "ae-filter",
          type: "text",
          placeholder: this.S("filter_placeholder"),
          value: this.filters.get(column.key) || "",
          oninput: (e) => this.setFilter(column.key, e.target.value),
        });
        filters.append(h("div", { class: "ae-hcell filter" + (frozen ? " frozen" : ""), style }, input));
      });
      this.header.replaceChildren(titles, filters);
    }

    renderBody() {
      const top = this.scroll.scrollTop;
      const first = Math.max(0, Math.floor(top / ROW_HEIGHT) - BUFFER_ROWS);
      const last = Math.min(this.view.length, Math.ceil((top + this.scroll.clientHeight) / ROW_HEIGHT) + BUFFER_ROWS);
      const rect = this.rect();
      const fragment = document.createDocumentFragment();
      const multipleCategories = new Set(this.rows.map((row) => row.c)).size > 1;
      for (let vi = first; vi < last; vi++) {
        const row = this.rows[this.view[vi]];
        const line = h("div", { class: "ae-row" + (vi % 2 ? " odd" : ""), style: "top:" + vi * ROW_HEIGHT + "px;width:" + this.totalWidth + "px" });
        const inRow = rect && vi >= rect.r1 && vi <= rect.r2;
        line.append(
          h(
            "div",
            { class: "ae-rowhead" + (inRow ? " sel" : ""), style: "width:" + ROWHEAD_WIDTH + "px", dataset: { r: vi }, title: row.c },
            h("span", { class: "ae-id" }, String(row.id)),
            multipleCategories ? h("span", { class: "ae-cat" }, row.c) : null
          )
        );
        this.columns.forEach((column, ci) => line.append(this.buildCell(row, vi, column, ci, rect)));
        fragment.append(line);
      }
      this.body.style.height = this.view.length * ROW_HEIGHT + "px";
      this.body.style.width = this.totalWidth + "px";
      this.sizer.style.width = this.totalWidth + "px";
      this.body.replaceChildren(fragment);
      this.positionFillHandle();
    }

    buildCell(row, vi, column, ci, rect) {
      const classes = ["ae-cell"];
      const locked = row.locked.has(ci) || !column.available;
      const value = row.cur[ci];
      if (column.kind === "number" || column.kind === "integer") classes.push("num");
      if (locked) classes.push("locked");
      if (value !== row.base[ci]) classes.push("dirty");
      if (row.errors.has(ci)) classes.push("error");
      if (this.isConflict(row, ci)) classes.push("conflict");
      if (ci < this.frozen) classes.push("frozen");
      if (rect && vi >= rect.r1 && vi <= rect.r2 && ci >= rect.c1 && ci <= rect.c2) classes.push("sel");
      if (this.anchor && this.anchor.r === vi && this.anchor.c === ci) classes.push("active");
      const pad = this.fillPreview;
      if (pad && vi >= pad.r1 && vi <= pad.r2 && ci >= pad.c1 && ci <= pad.c2) classes.push("fillpad");
      let tip = "";
      if (row.errors.has(ci)) tip = row.errors.get(ci);
      else if (this.isConflict(row, ci)) tip = this.S("tip_conflict", row.conflicts.get(ci));
      else if (locked) tip = this.S("tip_locked");
      const style = "width:" + this.columnWidth(column) + "px" + (ci < this.frozen ? ";left:" + this.offsets[ci] + "px" : "");
      return h("div", { class: classes.join(" "), style, title: tip || value, dataset: { r: vi, c: ci } }, value);
    }

    countPending() {
      let count = 0;
      const seenTypes = new Set();
      for (const row of this.rows) {
        for (let ci = 0; ci < this.columns.length; ci++) {
          if (row.cur[ci] === row.base[ci] || row.locked.has(ci)) continue;
          if (this.columns[ci].scope === "t") {
            const tag = row.t + ":" + ci;
            if (seenTypes.has(tag)) continue;
            seenTypes.add(tag);
          }
          count++;
        }
      }
      return count;
    }

    rect() {
      if (!this.anchor || !this.focus) return null;
      return {
        r1: Math.min(this.anchor.r, this.focus.r),
        r2: Math.max(this.anchor.r, this.focus.r),
        c1: Math.min(this.anchor.c, this.focus.c),
        c2: Math.max(this.anchor.c, this.focus.c),
      };
    }

    setSelection(anchor, focus, keepFocusCell) {
      this.anchor = anchor;
      this.focus = focus || anchor;
      if (!keepFocusCell) this.ensureVisible(this.focus);
      this.renderBody();
      this.renderStatus();
      this.renderToolbar();
    }

    selectAll() {
      if (!this.view.length || !this.columns.length) return;
      this.setSelection({ r: 0, c: 0 }, { r: this.view.length - 1, c: this.columns.length - 1 }, true);
    }

    ensureVisible(cell) {
      if (!cell) return;
      const frozenWidth = this.frozen ? this.offsets[this.frozen - 1] + this.columnWidth(this.columns[this.frozen - 1]) : ROWHEAD_WIDTH;
      const top = cell.r * ROW_HEIGHT;
      const headerHeight = HEAD_HEIGHT + FILTER_HEIGHT;
      if (top < this.scroll.scrollTop) this.scroll.scrollTop = top;
      else if (top + ROW_HEIGHT + headerHeight > this.scroll.scrollTop + this.scroll.clientHeight) {
        this.scroll.scrollTop = top + ROW_HEIGHT + headerHeight - this.scroll.clientHeight;
      }
      if (cell.c >= this.frozen && this.offsets[cell.c] !== undefined) {
        const left = this.offsets[cell.c];
        const right = left + this.columnWidth(this.columns[cell.c]);
        if (left < this.scroll.scrollLeft + frozenWidth) this.scroll.scrollLeft = Math.max(0, left - frozenWidth);
        else if (right > this.scroll.scrollLeft + this.scroll.clientWidth) this.scroll.scrollLeft = right - this.scroll.clientWidth;
      }
    }

    positionFillHandle() {
      const rect = this.rect();
      const editable = rect && !this.editing && this.columns.length && this.view.length;
      this.fillHandle.hidden = !editable;
      if (!editable) return;
      const column = this.columns[rect.c2];
      this.fillHandle.style.left = this.offsets[rect.c2] + this.columnWidth(column) - 5 + "px";
      this.fillHandle.style.top = HEAD_HEIGHT + FILTER_HEIGHT + (rect.r2 + 1) * ROW_HEIGHT - 5 + "px";
    }

    bindEvents() {
      listen();
      apps.set(this.data.channel, this);
      this.onDocumentMouseMove = (event) => this.onMouseMove(event);
      this.onDocumentMouseUp = (event) => this.onMouseUp(event);
      document.addEventListener("mousemove", this.onDocumentMouseMove);
      document.addEventListener("mouseup", this.onDocumentMouseUp);
      this.scroll.addEventListener("scroll", () => {
        this.queueRender();
        if (this.editing) this.positionEditor();
      });
      this.body.addEventListener("mousedown", (event) => this.onBodyMouseDown(event));
      this.body.addEventListener("dblclick", (event) => this.onBodyDoubleClick(event));
      this.fillHandle.addEventListener("mousedown", (event) => this.beginFill(event));
      this.clip.addEventListener("keydown", (event) => this.onKeyDown(event));
      this.clip.addEventListener("copy", (event) => this.onCopy(event, false));
      this.clip.addEventListener("cut", (event) => this.onCopy(event, true));
      this.clip.addEventListener("paste", (event) => this.onPaste(event));
      this.editor.addEventListener("keydown", (event) => this.onEditorKeyDown(event));
      this.editor.addEventListener("blur", () => this.commitEdit(null));
      window.addEventListener("resize", () => this.queueRender());
    }

    focusGrid() {
      this.clip.focus({ preventScroll: true });
    }

    cellFromEvent(event) {
      const target = event.target.closest ? event.target.closest(".ae-cell, .ae-rowhead") : null;
      if (!target || target.dataset.r === undefined) return null;
      const r = Number(target.dataset.r);
      if (target.classList.contains("ae-rowhead")) return { r, c: null };
      return { r, c: Number(target.dataset.c) };
    }

    onBodyMouseDown(event) {
      if (event.button !== 0) return;
      const cell = this.cellFromEvent(event);
      if (!cell) return;
      event.preventDefault();
      this.commitEdit(null);
      this.focusGrid();
      if (cell.c === null) {
        const last = this.columns.length - 1;
        const from = event.shiftKey && this.anchor ? this.anchor : { r: cell.r, c: 0 };
        this.setSelection({ r: from.r, c: 0 }, { r: cell.r, c: last }, true);
        this.drag = { mode: "rows" };
        return;
      }
      if (event.shiftKey && this.anchor) this.setSelection(this.anchor, cell, true);
      else this.setSelection(cell, cell, true);
      this.drag = { mode: "select" };
    }

    onBodyDoubleClick(event) {
      const cell = this.cellFromEvent(event);
      if (!cell) return;
      if (cell.c === null) {
        this.showInRevit();
        return;
      }
      this.startEdit(cell.r, cell.c);
    }

    onHeaderMouseDown(event, ci) {
      if (event.button !== 0 || event.target.closest(".ae-resize")) return;
      event.preventDefault();
      this.commitEdit(null);
      this.focusGrid();
      if (!this.view.length) return;
      const from = event.shiftKey && this.anchor ? this.anchor.c : ci;
      this.setSelection({ r: 0, c: from }, { r: this.view.length - 1, c: ci }, true);
    }

    onMouseMove(event) {
      if (!this.drag) return;
      if (this.drag.mode === "resize") {
        const column = this.columns[this.drag.ci];
        this.widths.set(column.key, Math.max(MIN_WIDTH, this.drag.start + event.clientX - this.drag.x));
        this.layoutColumns();
        this.renderHeader();
        this.queueRender();
        return;
      }
      const bounds = this.scroll.getBoundingClientRect();
      if (event.clientY > bounds.bottom - 24) this.scroll.scrollTop += 24;
      else if (event.clientY < bounds.top + HEAD_HEIGHT + FILTER_HEIGHT + 12) this.scroll.scrollTop -= 24;
      if (event.clientX > bounds.right - 24) this.scroll.scrollLeft += 24;
      else if (event.clientX < bounds.left + ROWHEAD_WIDTH + 12) this.scroll.scrollLeft -= 24;
      const target = document.elementFromPoint(event.clientX, event.clientY);
      const cell = target ? this.cellFromEvent({ target }) : null;
      if (!cell) return;
      if (this.drag.mode === "select" && cell.c !== null) this.setSelection(this.anchor, cell, true);
      else if (this.drag.mode === "rows") this.setSelection(this.anchor, { r: cell.r, c: this.columns.length - 1 }, true);
      else if (this.drag.mode === "fill" && cell.c !== null) this.updateFill(cell);
    }

    onMouseUp(event) {
      if (!this.drag) return;
      const drag = this.drag;
      this.drag = null;
      if (drag.mode === "fill") this.endFill(event);
      else if (drag.mode === "resize") this.renderAll();
    }

    beginResize(event, ci) {
      event.preventDefault();
      event.stopPropagation();
      this.drag = { mode: "resize", ci, x: event.clientX, start: this.columnWidth(this.columns[ci]) };
    }

    beginFill(event) {
      if (event.button !== 0) return;
      event.preventDefault();
      this.commitEdit(null);
      this.focusGrid();
      this.drag = { mode: "fill", base: this.rect(), target: null };
    }

    fillExtent(cell) {
      const base = this.drag.base;
      const dRow = cell.r > base.r2 ? cell.r - base.r2 : cell.r < base.r1 ? cell.r - base.r1 : 0;
      const dCol = cell.c > base.c2 ? cell.c - base.c2 : cell.c < base.c1 ? cell.c - base.c1 : 0;
      if (!dRow && !dCol) return null;
      if (Math.abs(dRow) >= Math.abs(dCol)) {
        return dRow > 0
          ? { axis: "v", backward: false, count: dRow, r1: base.r2 + 1, r2: base.r2 + dRow, c1: base.c1, c2: base.c2 }
          : { axis: "v", backward: true, count: -dRow, r1: base.r1 + dRow, r2: base.r1 - 1, c1: base.c1, c2: base.c2 };
      }
      return dCol > 0
        ? { axis: "h", backward: false, count: dCol, r1: base.r1, r2: base.r2, c1: base.c2 + 1, c2: base.c2 + dCol }
        : { axis: "h", backward: true, count: -dCol, r1: base.r1, r2: base.r2, c1: base.c1 + dCol, c2: base.c1 - 1 };
    }

    updateFill(cell) {
      this.drag.target = this.fillExtent(cell);
      this.fillPreview = this.drag.target;
      this.queueRender();
    }

    endFill(event) {
      const extent = this.drag ? null : this.fillPreview;
      this.fillPreview = null;
      if (!extent) {
        this.renderBody();
        return;
      }
      const base = this.rect();
      const changes = [];
      const invert = event.ctrlKey || event.metaKey;
      if (extent.axis === "v") {
        for (let ci = base.c1; ci <= base.c2; ci++) {
          const seed = [];
          for (let vi = base.r1; vi <= base.r2; vi++) seed.push(this.rows[this.view[vi]].cur[ci]);
          const values = core.fillSeries(seed, extent.count, { backward: extent.backward, invert });
          values.forEach((value, k) => {
            const vi = extent.backward ? base.r1 - 1 - k : base.r2 + 1 + k;
            if (vi >= 0 && vi < this.view.length) changes.push({ row: this.rows[this.view[vi]], ci, value });
          });
        }
      } else {
        for (let vi = base.r1; vi <= base.r2; vi++) {
          const row = this.rows[this.view[vi]];
          const seed = [];
          for (let ci = base.c1; ci <= base.c2; ci++) seed.push(row.cur[ci]);
          const values = core.fillSeries(seed, extent.count, { backward: extent.backward, invert });
          values.forEach((value, k) => {
            const ci = extent.backward ? base.c1 - 1 - k : base.c2 + 1 + k;
            if (ci >= 0 && ci < this.columns.length) changes.push({ row, ci, value });
          });
        }
      }
      this.applyChanges(changes);
      this.anchor = { r: Math.min(base.r1, extent.r1), c: Math.min(base.c1, extent.c1) };
      this.focus = { r: Math.max(base.r2, extent.r2), c: Math.max(base.c2, extent.c2) };
      this.renderBody();
      this.renderStatus();
    }

    onKeyDown(event) {
      const mod = event.ctrlKey || event.metaKey;
      const key = event.key;
      if (mod && !event.altKey) {
        const lower = key.toLowerCase();
        if (lower === "z") return this.consume(event, () => this.undo());
        if (lower === "y") return this.consume(event, () => this.redo());
        if (lower === "a") return this.consume(event, () => this.selectAll());
        if (lower === "f" || lower === "h") return this.consume(event, () => this.toggleFind(true));
        if (lower === "d") return this.consume(event, () => this.fillFromEdge("v"));
        if (lower === "r") return this.consume(event, () => this.fillFromEdge("h"));
        if (lower === "c" || lower === "x" || lower === "v") {
          if (lower !== "v") this.prepareCopy();
          return;
        }
      }
      if (!this.anchor) return;
      const shift = event.shiftKey;
      const moves = {
        ArrowDown: [1, 0],
        ArrowUp: [-1, 0],
        ArrowRight: [0, 1],
        ArrowLeft: [0, -1],
        PageDown: [Math.max(1, Math.floor(this.scroll.clientHeight / ROW_HEIGHT) - 2), 0],
        PageUp: [-Math.max(1, Math.floor(this.scroll.clientHeight / ROW_HEIGHT) - 2), 0],
      };
      if (moves[key]) return this.consume(event, () => this.moveSelection(moves[key][0], moves[key][1], shift));
      if (key === "Tab") return this.consume(event, () => this.moveSelection(0, shift ? -1 : 1, false));
      if (key === "Enter") return this.consume(event, () => this.moveSelection(shift ? -1 : 1, 0, false));
      if (key === "Home") return this.consume(event, () => this.setSelection({ r: this.anchor.r, c: 0 }, null));
      if (key === "End") return this.consume(event, () => this.setSelection({ r: this.anchor.r, c: this.columns.length - 1 }, null));
      if (key === "F2") return this.consume(event, () => this.startEdit(this.anchor.r, this.anchor.c));
      if (key === "Delete" || key === "Backspace") return this.consume(event, () => this.clearSelection());
      if (key === "Escape") return this.consume(event, () => this.setSelection(this.focus, this.focus, true));
      if (key.length === 1 && !mod && !event.altKey) {
        return this.consume(event, () => this.startEdit(this.anchor.r, this.anchor.c, key));
      }
    }

    consume(event, action) {
      event.preventDefault();
      action();
    }

    moveSelection(dRow, dCol, extend) {
      if (!this.anchor || !this.view.length || !this.columns.length) return;
      const from = extend ? this.focus : this.anchor;
      const next = {
        r: clamp(from.r + dRow, 0, this.view.length - 1),
        c: clamp(from.c + dCol, 0, this.columns.length - 1),
      };
      if (extend) this.setSelection(this.anchor, next);
      else this.setSelection(next, next);
    }

    startEdit(vi, ci, initial) {
      if (vi === null || ci === null || vi === undefined) return;
      const row = this.rows[this.view[vi]];
      const column = this.columns[ci];
      if (!row || !column) return;
      if (row.locked.has(ci) || !column.available) {
        this.toast(this.S("tip_locked"), "info");
        return;
      }
      this.setSelection({ r: vi, c: ci }, { r: vi, c: ci });
      this.editing = { vi, ci, original: row.cur[ci], untouched: null };
      this.editor.hidden = false;
      this.editor.value = initial !== undefined ? initial : row.cur[ci];
      if (initial === undefined) this.editing.untouched = this.editor.value;
      this.setEditorChoices(column);
      this.positionEditor();
      this.editor.focus();
      if (initial === undefined) this.editor.select();
      this.positionFillHandle();
    }

    setEditorChoices(column) {
      this.lists.replaceChildren();
      this.editor.removeAttribute("list");
      if (!column.choices || !column.choices.length) return;
      const id = "ae-list-" + this.data.channel;
      this.lists.append(h("datalist", { id }, column.choices.map((choice) => h("option", { value: choice }))));
      this.editor.setAttribute("list", id);
    }

    positionEditor() {
      const { vi, ci } = this.editing;
      const column = this.columns[ci];
      this.editor.style.left = this.offsets[ci] + "px";
      this.editor.style.top = HEAD_HEIGHT + FILTER_HEIGHT + vi * ROW_HEIGHT + "px";
      this.editor.style.width = Math.max(this.columnWidth(column), 120) + "px";
      this.editor.style.height = ROW_HEIGHT + "px";
    }

    commitEdit(move) {
      if (!this.editing) return;
      const { vi, ci, original, untouched } = this.editing;
      this.editing = null;
      const value = this.editor.value;
      this.editor.hidden = true;
      const row = this.rows[this.view[vi]];
      const unchangedText = untouched !== null ? untouched : original;
      if (row && value !== unchangedText) this.applyChanges([{ row, ci, value }]);
      if (move) this.moveSelection(move[0], move[1], false);
      else this.renderBody();
      this.focusGrid();
      this.renderStatus();
    }

    cancelEdit() {
      if (!this.editing) return;
      this.editing = null;
      this.editor.hidden = true;
      this.focusGrid();
      this.renderBody();
    }

    onEditorKeyDown(event) {
      if (event.key === "Enter") {
        event.preventDefault();
        this.commitEdit([event.shiftKey ? -1 : 1, 0]);
      } else if (event.key === "Tab") {
        event.preventDefault();
        this.commitEdit([0, event.shiftKey ? -1 : 1]);
      } else if (event.key === "Escape") {
        event.preventDefault();
        this.cancelEdit();
      }
    }

    applyChanges(changes) {
      const entries = [];
      const done = new Set();
      const expandedTypes = new Set();
      let skipped = 0;
      for (const change of changes) {
        const column = this.columns[change.ci];
        let targets = [change.row];
        if (column.scope === "t") {
          const group = change.row.t + ":" + change.ci;
          if (expandedTypes.has(group)) continue;
          expandedTypes.add(group);
          targets = this.byType.get(change.row.t) || targets;
        }
        for (const row of targets) {
          const tag = row.id + ":" + change.ci;
          if (done.has(tag)) continue;
          done.add(tag);
          if (row.locked.has(change.ci) || !column.available) {
            if (row === change.row) skipped++;
            continue;
          }
          if (row.cur[change.ci] === change.value) continue;
          entries.push({ row, ci: change.ci, before: row.cur[change.ci], after: change.value });
          row.cur[change.ci] = change.value;
          row.errors.delete(change.ci);
        }
      }
      if (entries.length) {
        this.undoStack.push(entries);
        this.redoStack = [];
      }
      if (skipped) this.toast(this.S("skipped_locked", skipped), "info");
      this.renderToolbar();
      this.renderConflictBar();
      return entries.length;
    }

    undo() {
      this.commitEdit(null);
      const entries = this.undoStack.pop();
      if (!entries) return;
      for (let k = entries.length - 1; k >= 0; k--) entries[k].row.cur[entries[k].ci] = entries[k].before;
      this.redoStack.push(entries);
      this.afterHistory();
    }

    redo() {
      this.commitEdit(null);
      const entries = this.redoStack.pop();
      if (!entries) return;
      for (const entry of entries) entry.row.cur[entry.ci] = entry.after;
      this.undoStack.push(entries);
      this.afterHistory();
    }

    afterHistory() {
      const rowAt = (cell) => (cell ? this.rows[this.view[cell.r]] : null);
      const anchorRow = rowAt(this.anchor);
      const focusRow = rowAt(this.focus);
      this.recomputeView();
      const follow = (cell, row) => {
        const position = row ? this.view.indexOf(this.rows.indexOf(row)) : -1;
        return cell && position >= 0 ? { r: position, c: cell.c } : cell;
      };
      this.anchor = follow(this.anchor, anchorRow);
      this.focus = follow(this.focus, focusRow);
      this.repairSelection();
      this.renderAll();
    }

    repairSelection() {
      if (!this.view.length || !this.columns.length) {
        this.anchor = this.focus = null;
        return;
      }
      const clampCell = (cell) => (cell ? { r: Math.min(cell.r, this.view.length - 1), c: Math.min(cell.c, this.columns.length - 1) } : cell);
      this.anchor = clampCell(this.anchor);
      this.focus = clampCell(this.focus);
    }

    selectedCells() {
      const rect = this.rect();
      if (!rect) return [];
      const cells = [];
      for (let vi = rect.r1; vi <= rect.r2; vi++) {
        const row = this.rows[this.view[vi]];
        if (!row) continue;
        for (let ci = rect.c1; ci <= rect.c2; ci++) cells.push({ row, vi, ci });
      }
      return cells;
    }

    selectedIds() {
      const rect = this.rect();
      if (!rect) return [];
      const ids = [];
      for (let vi = rect.r1; vi <= rect.r2; vi++) {
        const row = this.rows[this.view[vi]];
        if (row) ids.push(row.id);
      }
      return ids;
    }

    selectionText() {
      const rect = this.rect();
      if (!rect) return "";
      const lines = [];
      for (let vi = rect.r1; vi <= rect.r2; vi++) {
        const row = this.rows[this.view[vi]];
        const line = [];
        for (let ci = rect.c1; ci <= rect.c2; ci++) line.push(row.cur[ci]);
        lines.push(line);
      }
      return core.formatTsv(lines);
    }

    prepareCopy() {
      this.clip.value = this.selectionText();
      this.clip.select();
    }

    onCopy(event, cut) {
      const text = this.selectionText();
      if (event.clipboardData) {
        event.clipboardData.setData("text/plain", text);
        event.preventDefault();
      }
      if (cut) this.clearSelection();
    }

    onPaste(event) {
      event.preventDefault();
      const text = event.clipboardData ? event.clipboardData.getData("text/plain") : "";
      this.pasteText(text);
    }

    pasteText(text) {
      const data = core.parseTsv(text);
      const rect = this.rect();
      if (!data.length || !rect) return;
      const changes = [];
      const single = data.length === 1 && data[0].length === 1;
      if (single && (rect.r2 > rect.r1 || rect.c2 > rect.c1)) {
        for (let vi = rect.r1; vi <= rect.r2; vi++) {
          for (let ci = rect.c1; ci <= rect.c2; ci++) changes.push({ row: this.rows[this.view[vi]], ci, value: data[0][0] });
        }
        this.applyChanges(changes);
      } else {
        let last = { r: rect.r1, c: rect.c1 };
        data.forEach((line, dr) => {
          const vi = rect.r1 + dr;
          if (vi >= this.view.length) return;
          line.forEach((value, dc) => {
            const ci = rect.c1 + dc;
            if (ci >= this.columns.length) return;
            changes.push({ row: this.rows[this.view[vi]], ci, value });
            last = { r: Math.max(last.r, vi), c: Math.max(last.c, ci) };
          });
        });
        this.applyChanges(changes);
        this.anchor = { r: rect.r1, c: rect.c1 };
        this.focus = last;
      }
      this.renderAll();
    }

    clearSelection() {
      const changes = this.selectedCells().map((cell) => ({ row: cell.row, ci: cell.ci, value: "" }));
      this.applyChanges(changes);
      this.renderAll();
    }

    fillFromEdge(axis) {
      const rect = this.rect();
      if (!rect) return;
      const changes = [];
      for (let vi = rect.r1; vi <= rect.r2; vi++) {
        for (let ci = rect.c1; ci <= rect.c2; ci++) {
          const sourceRow = axis === "v" ? this.rows[this.view[rect.r1]] : this.rows[this.view[vi]];
          const sourceCol = axis === "v" ? ci : rect.c1;
          changes.push({ row: this.rows[this.view[vi]], ci, value: sourceRow.cur[sourceCol] });
        }
      }
      this.applyChanges(changes);
      this.renderAll();
    }

    cycleSort(key, additive) {
      const current = this.sort.find((entry) => entry.key === key);
      const next = !current ? "asc" : current.dir === "asc" ? "desc" : null;
      const others = additive ? this.sort.filter((entry) => entry.key !== key) : [];
      this.sort = next ? others.concat([{ key, dir: next }]) : others;
      this.recomputeView();
      this.renderAll();
    }

    setFilter(key, text) {
      if (text) this.filters.set(key, text);
      else this.filters.delete(key);
      this.recomputeView();
      this.anchor = this.focus = this.view.length && this.columns.length ? { r: 0, c: 0 } : null;
      this.scroll.scrollTop = 0;
      this.renderBody();
      this.renderStatus();
      this.renderToolbar();
      this.emptyNote.hidden = !!this.view.length;
      this.emptyNote.textContent = this.view.length ? "" : this.S("empty_rows");
    }

    async onSourceChange(value) {
      const previous = this.source;
      if (this.countPending() && !(await this.confirm(this.S("source_discard", this.countPending()), this.S("discard")))) {
        this.renderToolbar();
        return;
      }
      this.filters = new Map();
      this.sort = [];
      if (value === "__scratch__") {
        this.rows = [];
        this.columns = [];
        this.view = [];
        this.plan = [];
        this.available = [];
        this.loadedSource = null;
        this.title = "";
        this.loadSeq++;
        this.generation++;
        this.anchor = this.focus = null;
        this.openScratch();
        return;
      }
      this.source = { kind: "schedule", id: Number(value) };
      this.available = [];
      const ok = await this.load({ columns: null, fresh: true });
      if (ok === false) this.source = previous;
      this.refreshAvailable();
      this.renderToolbar();
    }

    async setUnitMode(mode) {
      if (mode === this.unitMode) return;
      const pending = this.countPending();
      if (pending && !(await this.confirm(this.S("unit_discard", pending), this.S("discard")))) return;
      if (!this.columns.length) {
        this.unitMode = mode;
        this.renderToolbar();
        return;
      }
      await this.load({ unitMode: mode, fresh: true });
    }

    setTheme(mode) {
      this.themePreference = mode;
      this.applyTheme();
      this.renderToolbar();
      this.request("theme", { preference: mode }).catch((error) => this.toast(error.message, "error"));
    }

    async pull() {
      if (!this.columns.length) return;
      const ok = await this.load({});
      if (ok) this.toast(this.S("pulled", this.rows.length), "ok");
    }

    gatherEdits() {
      const edits = [];
      const seenTypes = new Set();
      for (const row of this.rows) {
        this.columns.forEach((column, ci) => {
          if (row.cur[ci] === row.base[ci] || row.locked.has(ci) || !column.available) return;
          if (this.isConflict(row, ci)) return;
          if (column.scope === "t") {
            const tag = row.t + ":" + ci;
            if (seenTypes.has(tag)) return;
            seenTypes.add(tag);
          }
          edits.push({ row: row.id, key: column.key, text: row.cur[ci], base: row.base[ci], ref: { row, ci } });
        });
      }
      return edits;
    }

    async push(force, dry) {
      this.commitEdit(null);
      const edits = this.gatherEdits();
      if (!edits.length) {
        const unresolved = this.countConflicts();
        this.toast(unresolved ? this.S("push_conflicts", unresolved) : this.S("nothing_pending"), "info");
        return;
      }
      const generation = this.generation;
      this.setBusy(true);
      let results;
      try {
        const reply = await this.request("push", {
          edits: edits.map(({ row, key, text, base }) => ({ row, key, text, base })),
          unitMode: this.unitMode,
          force: !!force,
          dry: !!dry,
        });
        results = reply.results;
      } catch (error) {
        this.toast(error.message, "error");
        return;
      } finally {
        this.setBusy(false);
      }
      if (generation !== this.generation) {
        const written = results.filter((result) => result.ok).length;
        if (written && !dry) this.toast(this.S("push_done", written), "ok");
        return;
      }
      this.applyResults(edits, results, !!dry);
    }

    groupOf(row, ci) {
      return this.columns[ci].scope === "t" ? this.byType.get(row.t) || [row] : [row];
    }

    applyResults(edits, results, dry) {
      let written = 0;
      let failed = 0;
      let conflicts = 0;
      results.forEach((result, index) => {
        const { row, ci } = edits[index].ref;
        const group = this.groupOf(row, ci);
        if (result.ok) {
          written++;
          if (dry) {
            for (const member of group) member.errors.delete(ci);
            return;
          }
          const sent = edits[index].text;
          for (const member of group) {
            member.base[ci] = result.value;
            if (member.cur[ci] === sent) member.cur[ci] = result.value;
            member.errors.delete(ci);
            member.conflicts.delete(ci);
          }
        } else if (result.conflict) {
          conflicts++;
          for (const member of group) member.conflicts.set(ci, result.current);
        } else {
          failed++;
          for (const member of group) member.errors.set(ci, result.message);
        }
      });
      if (!dry) {
        this.undoStack = [];
        this.redoStack = [];
      }
      this.renderAll();
      if (dry) {
        this.toast(failed + conflicts ? this.S("check_failed", failed + conflicts) : this.S("check_ok", written), failed + conflicts ? "warn" : "ok");
      } else {
        if (written) this.toast(this.S("push_done", written), "ok");
        if (failed) this.toast(this.S("push_failed", failed), "error");
        if (conflicts) this.toast(this.S("push_conflicts", conflicts), "warn");
      }
    }

    resolveConflicts(keepMine) {
      for (const row of this.rows) {
        for (const [ci, server] of row.conflicts) {
          row.base[ci] = server;
          if (!keepMine) row.cur[ci] = server;
        }
        row.conflicts.clear();
      }
      this.renderAll();
    }

    async showInRevit() {
      const ids = this.selectedIds();
      if (!ids.length) return;
      try {
        await this.request("select", { ids, zoom: true });
      } catch (error) {
        this.toast(error.message, "error");
      }
    }

    buildFindBar() {
      this.findInput = h("input", { class: "ae-input", type: "text", placeholder: this.S("find_placeholder"), onkeydown: (e) => e.key === "Enter" && (e.preventDefault(), this.findNext()) });
      this.replaceInput = h("input", { class: "ae-input", type: "text", placeholder: this.S("replace_placeholder") });
      this.caseBox = h("input", { type: "checkbox" });
      this.scopeSelect = h(
        "select",
        { class: "ae-select" },
        h("option", { value: "selection" }, this.S("scope_selection")),
        h("option", { value: "column" }, this.S("scope_column")),
        h("option", { value: "all", selected: true }, this.S("scope_all"))
      );
      this.findBar.append(
        this.findInput,
        this.replaceInput,
        h("label", { class: "ae-check" }, this.caseBox, this.S("match_case")),
        this.scopeSelect,
        h("button", { class: "ae-button", onclick: () => this.findNext() }, this.S("find_next")),
        h("button", { class: "ae-button", onclick: () => this.replaceCurrent() }, this.S("replace")),
        h("button", { class: "ae-button", onclick: () => this.replaceAll() }, this.S("replace_all")),
        h("button", { class: "ae-button", onclick: () => this.toggleFind(false) }, "✕")
      );
    }

    toggleFind(show) {
      this.findBar.hidden = show === undefined ? !this.findBar.hidden : !show;
      this.renderToolbar();
      if (!this.findBar.hidden) this.findInput.focus();
      else this.focusGrid();
    }

    findScope() {
      const cells = [];
      const scope = this.scopeSelect.value;
      const rect = this.rect();
      for (let vi = 0; vi < this.view.length; vi++) {
        for (let ci = 0; ci < this.columns.length; ci++) {
          if (scope === "selection" && rect && !(vi >= rect.r1 && vi <= rect.r2 && ci >= rect.c1 && ci <= rect.c2)) continue;
          if (scope === "column" && rect && ci !== this.anchor.c) continue;
          cells.push({ vi, ci });
        }
      }
      return cells;
    }

    matchesText(value) {
      const needle = this.findInput.value;
      if (!needle) return false;
      return this.caseBox.checked ? value.includes(needle) : value.toLowerCase().includes(needle.toLowerCase());
    }

    findNext() {
      const cells = this.findScope().filter((cell) => this.matchesText(this.rows[this.view[cell.vi]].cur[cell.ci]));
      if (!cells.length) {
        this.toast(this.S("find_none"), "info");
        return null;
      }
      const from = this.anchor ? this.anchor.r * this.columns.length + this.anchor.c : -1;
      const next = cells.find((cell) => cell.vi * this.columns.length + cell.ci > from) || cells[0];
      this.setSelection({ r: next.vi, c: next.ci }, { r: next.vi, c: next.ci });
      return next;
    }

    replaceText(value) {
      const needle = this.findInput.value;
      const flags = this.caseBox.checked ? "g" : "gi";
      const pattern = new RegExp(needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), flags);
      return value.replace(pattern, () => this.replaceInput.value);
    }

    replaceCurrent() {
      const cell = this.anchor;
      if (!cell) return;
      const row = this.rows[this.view[cell.r]];
      if (this.matchesText(row.cur[cell.c])) {
        this.applyChanges([{ row, ci: cell.c, value: this.replaceText(row.cur[cell.c]) }]);
        this.renderAll();
      }
      this.findNext();
    }

    replaceAll() {
      const changes = this.findScope()
        .filter((cell) => this.matchesText(this.rows[this.view[cell.vi]].cur[cell.ci]))
        .map((cell) => {
          const row = this.rows[this.view[cell.vi]];
          return { row, ci: cell.ci, value: this.replaceText(row.cur[cell.ci]) };
        });
      const count = this.applyChanges(changes);
      this.renderAll();
      this.toast(this.S("replaced", count), "ok");
    }

    togglePanel() {
      this.panel.hidden = !this.panel.hidden;
      this.renderToolbar();
      this.queueRender();
    }

    buildPanel() {
      this.categoryFilter = h("input", { class: "ae-input", type: "text", placeholder: this.S("search_categories"), oninput: (e) => { this.builder.filter = e.target.value; this.renderCategoryList(); } });
      this.categoryList = h("div", { class: "ae-list tall" });
      this.scopeBuilder = h(
        "select",
        { class: "ae-select", onchange: (e) => { this.builder.scope = e.target.value; } },
        h("option", { value: "model" }, this.S("scope_model")),
        h("option", { value: "view" }, this.S("scope_view")),
        h("option", { value: "selection" }, this.S("scope_selection_src"))
      );
      this.kindBuilder = h(
        "select",
        { class: "ae-select", onchange: (e) => { this.builder.types = e.target.value === "types"; this.renderCategoryList(); } },
        h("option", { value: "instances" }, this.S("elements_instances")),
        h("option", { value: "types" }, this.S("elements_types"))
      );
      this.scanBox = h("input", { type: "checkbox", onchange: (e) => { this.builder.scanAll = e.target.checked; } });
      this.scratchSection = h(
        "section",
        { class: "ae-section" },
        h("h3", {}, this.S("panel_source")),
        this.categoryFilter,
        this.categoryList,
        h("div", { class: "ae-row2" }, this.scopeBuilder, this.kindBuilder),
        h("label", { class: "ae-check", title: this.S("scan_all_hint") }, this.scanBox, this.S("scan_all")),
        h("button", { class: "ae-button", onclick: () => this.findParameters() }, this.S("find_parameters"))
      );
      this.availableFilter = h("input", { class: "ae-input", type: "text", placeholder: this.S("search_columns"), oninput: () => this.renderAvailable() });
      this.chosenList = h("div", { class: "ae-list" });
      this.availableList = h("div", { class: "ae-list tall" });
      this.frozenInput = h("input", { class: "ae-input narrow", type: "number", min: "0", value: "0", onchange: (e) => this.setFrozen(Number(e.target.value)) });
      this.applyButton = h("button", { class: "ae-button primary", onclick: () => this.applyColumns() }, this.S("apply_columns"));
      this.layoutButton = h("button", { class: "ae-button", title: this.S("write_layout_hint"), onclick: () => this.writeLayout() }, this.S("write_layout"));
      this.panel.append(
        this.scratchSection,
        h(
          "section",
          { class: "ae-section" },
          h("h3", {}, this.S("panel_chosen")),
          this.chosenList,
          h("label", { class: "ae-check" }, this.S("frozen_columns"), this.frozenInput),
          h("div", { class: "ae-row2" }, this.applyButton, this.layoutButton)
        ),
        h("section", { class: "ae-section" }, h("h3", {}, this.S("panel_available")), this.availableFilter, this.availableList)
      );
    }

    renderPanel() {
      this.scratchSection.hidden = this.source.kind !== "scratch";
      this.layoutButton.hidden = this.source.kind !== "schedule";
      this.frozenInput.max = String(this.columns.length);
      this.frozenInput.value = String(this.frozen);
      this.renderCategoryList();
      this.renderChosen();
      this.renderAvailable();
    }

    renderCategoryList() {
      const needle = this.builder.filter.toLowerCase();
      this.categoryList.replaceChildren(
        ...this.categories
          .filter((category) => category.name.toLowerCase().includes(needle))
          .map((category) => {
            const count = this.builder.types ? category.types : category.instances;
            return h(
              "label",
              { class: "ae-item" + (count ? "" : " dim") },
              h("input", {
                type: "checkbox",
                checked: this.builder.picked.has(category.id),
                onchange: (e) => (e.target.checked ? this.builder.picked.add(category.id) : this.builder.picked.delete(category.id)),
              }),
              h("span", { class: "grow" }, category.name),
              h("span", { class: "count" }, String(count))
            );
          })
      );
    }

    renderChosen() {
      this.chosenList.replaceChildren(
        ...this.plan.map((key, index) => {
          const info = this.known.get(key) || { heading: key, scope: "i" };
          return h(
            "div",
            {
              class: "ae-item",
              draggable: "true",
              ondragstart: (e) => e.dataTransfer.setData("text/plain", String(index)),
              ondragover: (e) => e.preventDefault(),
              ondrop: (e) => {
                e.preventDefault();
                this.movePlan(Number(e.dataTransfer.getData("text/plain")), index);
              },
            },
            h("span", { class: "grip" }, "☰"),
            h("span", { class: "grow" }, info.heading, info.scope === "t" ? h("span", { class: "ae-badge", title: this.S("type_hint") }, "T") : null),
            h("button", { class: "ae-mini", title: this.S("move_up"), disabled: index === 0, onclick: () => this.movePlan(index, index - 1) }, "▲"),
            h("button", { class: "ae-mini", title: this.S("move_down"), disabled: index === this.plan.length - 1, onclick: () => this.movePlan(index, index + 1) }, "▼"),
            h("button", { class: "ae-mini", title: this.S("remove"), onclick: () => this.removeFromPlan(index) }, "✕")
          );
        })
      );
    }

    renderAvailable() {
      const needle = this.availableFilter.value.toLowerCase();
      const chosen = new Set(this.plan);
      this.availableList.replaceChildren(
        ...this.available
          .filter((item) => !chosen.has(item.key) && item.heading.toLowerCase().includes(needle))
          .map((item) =>
            h(
              "div",
              { class: "ae-item add", onclick: () => this.addToPlan(item) },
              h("span", { class: "grow" }, item.heading, item.scope === "t" ? h("span", { class: "ae-badge", title: this.S("type_hint") }, "T") : null),
              h("span", { class: "plus" }, "+")
            )
          )
      );
    }

    async refreshAvailable() {
      if (this.source.kind !== "schedule") return;
      try {
        this.available = await this.request("available", { source: this.source });
        this.renderAvailable();
      } catch (error) {
        this.toast(error.message, "error");
      }
    }

    async findParameters() {
      const categories = [...this.builder.picked];
      if (!categories.length) {
        this.toast(this.S("pick_categories"), "info");
        return;
      }
      const discovery = { kind: "scratch", categories, scope: this.builder.scope, types: this.builder.types };
      this.setBusy(true);
      try {
        this.available = await this.request("available", { source: discovery, scanAll: this.builder.scanAll });
        this.toast(this.S("parameters_found", this.available.length), "ok");
        this.renderAvailable();
      } catch (error) {
        this.toast(error.message, "error");
      } finally {
        this.setBusy(false);
      }
    }

    addToPlan(item) {
      this.known.set(item.key, { heading: item.heading, scope: item.scope });
      this.plan.push(item.key);
      this.renderChosen();
      this.renderAvailable();
    }

    removeFromPlan(index) {
      this.plan.splice(index, 1);
      this.renderChosen();
      this.renderAvailable();
    }

    movePlan(from, to) {
      if (from === to || to < 0 || to >= this.plan.length) return;
      const [key] = this.plan.splice(from, 1);
      this.plan.splice(to, 0, key);
      this.renderChosen();
    }

    setFrozen(count) {
      this.frozen = clamp(Math.floor(count) || 0, 0, this.columns.length);
      this.renderAll();
    }

    async applyColumns() {
      if (this.source.kind === "scratch") {
        const categories = [...this.builder.picked];
        if (!categories.length) {
          this.toast(this.S("pick_categories"), "info");
          return;
        }
        const next = { kind: "scratch", categories, scope: this.builder.scope, types: this.builder.types };
        const pending = this.countPending();
        if (pending && !this.sameScratchSource(next, this.loadedSource || {}) && !(await this.confirm(this.S("source_discard", pending), this.S("discard")))) return;
        this.source = next;
      }
      if (!this.plan.length) {
        this.toast(this.S("no_columns_yet"), "info");
        return;
      }
      await this.load({ columns: this.plan.slice() });
    }

    sameSource(a, b) {
      if (a.kind === "schedule" || b.kind === "schedule") return a.kind === b.kind && a.id === b.id;
      return this.sameScratchSource(a, b);
    }

    sameScratchSource(a, b) {
      if (a.kind !== "scratch" || b.kind !== "scratch") return false;
      const ids = (source) => [...(source.categories || [])].sort((x, y) => x - y).join(",");
      return ids(a) === ids(b) && a.scope === b.scope && !!a.types === !!b.types;
    }

    async writeLayout() {
      if (this.source.kind !== "schedule" || !this.plan.length) return;
      this.setBusy(true);
      try {
        const summary = await this.request("layout", { source: this.source, columns: this.plan.slice() });
        this.toast(this.S("layout_done", summary.added, summary.removed), "ok");
        for (const failure of summary.failed) this.toast(this.S("layout_failed", (this.known.get(failure.key) || {}).heading || failure.key, failure.message), "error");
      } catch (error) {
        this.toast(error.message, "error");
        return;
      } finally {
        this.setBusy(false);
      }
      await this.load({ columns: this.plan.slice() });
      this.refreshAvailable();
    }
  }

  window.pyRevitAttributeGrid = {
    mount(rootId, data) {
      const root = document.getElementById(rootId);
      return new App(root, data);
    },
    core,
  };
})();
