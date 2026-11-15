/*
 * Interactive report for the Diagnose Invisibility tool.
 *
 * window.pyRevitInvisibility.mount(rootId, data) renders one report into the
 * element with id rootId. data comes from invisibility_report.DiagnosisSession
 * .payload(). When data.bridge is true, buttons post
 * {channel, action, payload, requestId} through chrome.webview.postMessage and
 * Python answers with {channel, event, payload} messages (events: view,
 * state, reveal, result, scene, error). Without the bridge the report is read-only and
 * falls back to pyRevit's revit:// links for selection.
 */
(function () {
  "use strict";

  const apps = new Map();
  let listening = false;

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

  function causes(element) {
    return element.findings.filter((f) => !f.informational);
  }

  class App {
    constructor(root, data) {
      this.root = root;
      this.data = data;
      this.s = data.strings;
      this.views = data.views;
      this.query = "";
      this.activeCodes = new Set();
      this.showVisible = true;
      this.showContext = false;
      this.elementCount = data.elementCount;
      this.selected = new Set();
      this.revealed = new Map();
      this.revealOff = new Map();
      this.requests = new Map();
      this.requestSeq = 0;
      this.viewers = new Map();
      this.ghosted = new Set();
      this.sceneOpen = new Set();
      this.sceneLoading = new Set();
      this.sceneStale = new Set();
      this.root.classList.add("dvi");
      this.render();
      this.bindKeys();
    }

    request(action, payload) {
      if (!this.data.bridge) return Promise.reject(new Error(this.s.bridgeOffline));
      const requestId = ++this.requestSeq;
      return new Promise((resolve, reject) => {
        this.requests.set(requestId, { resolve, reject });
        window.chrome.webview.postMessage({
          channel: this.data.channel,
          action,
          payload,
          requestId,
        });
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
      } else if (event === "view") {
        const index = this.views.findIndex((v) => v.id === payload.id);
        if (index < 0) return;
        this.views[index] = payload;
        this.renderView(payload);
        this.renderHeader();
        this.renderMatrix();
        this.applyFilters();
        this.syncViewer(payload);
        this.refreshScene(payload.id);
      } else if (event === "reveal") {
        this.onReveal(payload);
      } else if (event === "state") {
        this.applyState(payload);
      } else if (event === "scene") {
        this.showScene(payload);
      }
    }

    /**
     * Adopt a new element/view list: drop sections and previews of removed
     * views, keep open previews of the others, and prune selections and ghosts
     * of removed elements.
     */
    applyState(state) {
      this.elementCount = state.elementCount;
      const kept = new Set(state.views.map((v) => v.id));
      const previous = new Set(this.views.map((v) => v.id));
      for (const id of previous) {
        if (kept.has(id)) continue;
        const viewer = this.viewers.get(id);
        if (viewer) viewer.destroy();
        this.viewers.delete(id);
        this.sceneOpen.delete(id);
        this.sceneLoading.delete(id);
        this.sceneStale.delete(id);
        this.revealed.delete(id);
        this.revealOff.delete(id);
        const section = this.viewSection(id);
        if (section) section.remove();
      }
      this.views = state.views;
      const known = new Set(state.elementIds);
      for (const id of [...this.selected]) if (!known.has(id)) this.selected.delete(id);
      for (const id of [...this.ghosted]) if (!known.has(id)) this.ghosted.delete(id);
      for (const view of this.views) {
        this.renderView(view);
        if (previous.has(view.id)) {
          this.syncViewer(view);
          this.refreshScene(view.id);
        }
      }
      for (const view of this.views) this.viewsNode.append(this.viewSection(view.id));
      this.renderHeader();
      this.renderMatrix();
      this.applyFilters();
      this.syncSelection();
    }

    run(button, action, payload, successMessage) {
      if (button) {
        button.disabled = true;
        button.classList.add("busy");
      }
      return this.request(action, payload)
        .then((message) => {
          const text = successMessage ? format(successMessage, message || "") : null;
          if (text) this.toast(text, "ok");
        })
        .catch((error) => {
          this.toast(format(this.s.fixFailed, error.message), "error");
          if (button) {
            button.classList.remove("busy");
            button.classList.add("shake");
            setTimeout(() => button.classList.remove("shake"), 500);
          }
        })
        .finally(() => {
          if (button && button.isConnected) {
            button.disabled = false;
            button.classList.remove("busy");
          }
        });
    }

    toast(text, kind) {
      let tray = document.querySelector(".dvi-toasts");
      if (!tray) {
        tray = h("div", { class: "dvi-toasts" });
        document.body.append(tray);
      }
      const node = h("div", { class: `dvi-toast ${kind || ""}` }, text);
      tray.append(node);
      setTimeout(() => node.classList.add("leaving"), 3200);
      setTimeout(() => node.remove(), 3600);
    }

    /**
     * The output window is a stock Chromium page: its context menu and F5 /
     * Ctrl+R reload the empty skeleton and erase the report, so both are
     * blocked here. Text selections and inputs keep their copy/paste menu.
     */
    bindKeys() {
      document.addEventListener("contextmenu", (e) => {
        if (e.target.closest("input, textarea") || String(window.getSelection()).length) return;
        e.preventDefault();
      });
      document.addEventListener("keydown", (e) => {
        const reload = e.key === "F5" || ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "r");
        if (reload) {
          e.preventDefault();
          this.toast(this.s.reloadBlocked, "error");
        } else if (e.key === "/" && document.activeElement !== this.searchInput && !document.querySelector(".dvi-modal")) {
          e.preventDefault();
          this.searchInput.focus();
        } else if (e.key === "Escape" && document.activeElement === this.searchInput) {
          this.searchInput.value = "";
          this.query = "";
          this.applyFilters();
        }
      });
    }

    counts() {
      let visible = 0;
      let hidden = 0;
      const codes = new Map();
      for (const view of this.views) {
        for (const element of view.elements) {
          if (element.visible) visible++;
          else hidden++;
          for (const finding of causes(element)) {
            codes.set(finding.code, (codes.get(finding.code) || 0) + 1);
          }
        }
      }
      return { visible, hidden, codes };
    }

    render() {
      this.headerNode = h("header", { class: "dvi-header" });
      this.toolbarNode = h("div", { class: "dvi-toolbar" });
      this.selectionNode = h("div", { class: "dvi-selection", hidden: true });
      this.matrixNode = h("section", { class: "dvi-matrix" });
      this.viewsNode = h("div", { class: "dvi-views" });
      this.emptyStateNode = h("p", { class: "dvi-empty-state", hidden: true }, this.s.emptyState);
      this.root.replaceChildren(
        ...[
          this.headerNode,
          this.toolbarNode,
          this.selectionNode,
          this.data.bridge ? null : h("div", { class: "dvi-offline" }, this.s.bridgeOffline),
          this.matrixNode,
          this.viewsNode,
          this.emptyStateNode,
        ].filter(Boolean)
      );
      this.renderHeader();
      this.renderToolbar();
      this.renderMatrix();
      for (const view of this.views) this.renderView(view);
      this.syncSelection();
    }

    manageButtons() {
      const action = (label, name, title) =>
        h(
          "button",
          { class: "dvi-btn", title, onclick: (e) => this.run(e.currentTarget, name, {}, "{0}") },
          label
        );
      return [
        action(this.s.addSelection, "add_selection", this.s.addSelectionHint),
        action(this.s.pickElements, "add_pick"),
        action(this.s.addViews, "add_views"),
      ];
    }

    syncSelection() {
      for (const box of this.root.querySelectorAll("input.dvi-pick")) {
        box.checked = this.selected.has(Number(box.dataset.pick));
      }
      this.syncSelectAll();
      const revealOnly = this.data.autoReveal !== null && this.views.length > 0;
      this.emptyStateNode.hidden = revealOnly || (this.views.length > 0 && this.elementCount > 0);
      const count = this.selected.size;
      this.selectionNode.hidden = !this.data.bridge || count === 0;
      this.selectionNode.replaceChildren(
        h("span", { class: "dvi-selection-count" }, format(this.s.selectedCount, count)),
        h(
          "button",
          { class: "dvi-btn small", disabled: !this.views.length, onclick: () => this.openHideDialog(true) },
          this.s.hideInViews
        ),
        h(
          "button",
          { class: "dvi-btn small", disabled: !this.views.length, onclick: () => this.openHideDialog(false) },
          this.s.unhideInViews
        ),
        h(
          "button",
          {
            class: "dvi-btn small",
            onclick: () => {
              this.selected.clear();
              this.syncSelection();
            },
          },
          this.s.clearSelection
        )
      );
    }

    /**
     * Ask which report views to hide or unhide the selected elements in. The
     * request carries ids only; Python re-checks every element and view.
     */
    openHideDialog(hide) {
      if (!this.views.length) return;
      const ids = [...this.selected];
      const boxes = this.views.map((view) => ({ view, input: h("input", { type: "checkbox", checked: true }) }));
      const opener = document.activeElement;
      const close = () => {
        overlay.remove();
        const target = opener && opener.isConnected ? opener : this.root.querySelector(".dvi-btn");
        if (target) target.focus();
      };
      const apply = h(
        "button",
        {
          class: "dvi-btn primary",
          onclick: () => {
            const viewIds = boxes.filter((box) => box.input.checked).map((box) => box.view.id);
            if (!viewIds.length) {
              this.toast(this.s.noViewTicked, "error");
              return;
            }
            close();
            this.run(null, "set_hidden", { hide, elementIds: ids, viewIds }, "{0}");
          },
        },
        this.s.apply
      );
      const overlay = h(
        "div",
        {
          class: "dvi-modal",
          onclick: (e) => {
            if (e.target === overlay) close();
          },
          onkeydown: (e) => {
            if (e.key === "Escape") close();
          },
        },
        h(
          "div",
          { class: "dvi-dialog", role: "dialog", "aria-modal": "true", "aria-labelledby": "dvi-dialog-title" },
          h("h3", { id: "dvi-dialog-title" }, format(hide ? this.s.hideDialogTitle : this.s.unhideDialogTitle, ids.length)),
          h(
            "ul",
            { class: "dvi-dialog-views" },
            boxes.map(({ view, input }) =>
              h("li", null, h("label", null, input, view.name, h("span", { class: "dvi-badge" }, view.type)))
            )
          ),
          h("div", { class: "dvi-dialog-actions" }, h("button", { class: "dvi-btn", onclick: close }, this.s.cancel), apply)
        )
      );
      this.root.append(overlay);
      boxes[0].input.focus();
    }

    renderHeader() {
      const { visible, hidden } = this.counts();
      this.headerNode.replaceChildren(
        h(
          "div",
          { class: "dvi-title" },
          h("h2", null, this.s.title),
          h(
            "span",
            { class: "dvi-subtitle" },
            format(this.s.subtitle, this.elementCount, this.views.length),
            " · ",
            this.data.document
          )
        ),
        h(
          "div",
          { class: "dvi-stats" },
          h("span", { class: "dvi-pill hidden" }, `${hidden} ${this.s.hidden}`),
          h("span", { class: "dvi-pill visible" }, `${visible} ${this.s.visible}`)
        ),
        h(
          "div",
          { class: "dvi-header-actions" },
          this.data.bridge ? this.manageButtons() : null,
          this.data.bridge
            ? h(
                "button",
                {
                  class: "dvi-btn",
                  onclick: (e) => this.run(e.currentTarget, "recheck", {}, this.s.rechecked),
                },
                this.s.recheck
              )
            : null,
          h("button", { class: "dvi-btn", onclick: () => this.copyMarkdown() }, this.s.copyMarkdown)
        )
      );
      this.renderChips();
    }

    renderToolbar() {
      this.searchInput = h("input", {
        type: "search",
        class: "dvi-search",
        placeholder: `${this.s.search}  ( / )`,
        oninput: (e) => {
          this.query = e.target.value.trim().toLowerCase();
          this.applyFilters();
        },
      });
      this.chipsNode = h("div", { class: "dvi-chips" });
      const toggle = (label, checked, onchange) =>
        h(
          "label",
          { class: "dvi-toggle" },
          h("input", { type: "checkbox", checked, onchange }),
          label
        );
      this.toolbarNode.replaceChildren(
        this.searchInput,
        this.chipsNode,
        h(
          "div",
          { class: "dvi-toggles" },
          this.data.bridge ? this.selectAllToggle() : null,
          toggle(this.s.showVisible, this.showVisible, (e) => {
            this.showVisible = e.target.checked;
            this.applyFilters();
          }),
          this.contextToggle()
        )
      );
      this.renderChips();
    }

    /**
     * Ids of the elements shown by the current filters, so "Select all"
     * never selects cards the user cannot see.
     */
    selectableIds() {
      const shown = new Set();
      for (const view of this.views) {
        for (const element of view.elements) if (this.matches(element)) shown.add(element.id);
      }
      const first = this.views.length ? this.views[0].elements : [];
      return first.filter((element) => shown.has(element.id)).map((element) => element.id);
    }

    syncSelectAll() {
      if (!this.selectAllInput) return;
      const selectable = this.selectableIds();
      this.selectAllInput.checked = selectable.length > 0 && selectable.every((id) => this.selected.has(id));
    }

    selectAllToggle() {
      this.selectAllInput = h("input", {
        type: "checkbox",
        onchange: (e) => {
          this.selected.clear();
          if (e.target.checked) {
            for (const id of this.selectableIds()) this.selected.add(id);
          }
          this.syncSelection();
        },
      });
      return h("label", { class: "dvi-toggle" }, this.selectAllInput, this.s.selectAll);
    }

    /**
     * Toggle for informational findings (applied view template, view
     * discipline). They can explain hidden elements but are not confirmed
     * causes, so they stay collapsed by default; when shown they are also
     * included in "Copy as Markdown".
     */
    contextToggle() {
      this.contextCountNode = h("span", { class: "dvi-toggle-count" });
      return h(
        "label",
        { class: "dvi-toggle", title: this.s.showContextHint },
        h("input", {
          type: "checkbox",
          checked: this.showContext,
          onchange: (e) => {
            this.showContext = e.target.checked;
            this.root.classList.toggle("show-context", this.showContext);
          },
        }),
        this.s.showContext,
        this.contextCountNode
      );
    }

    contextCount() {
      let count = 0;
      for (const view of this.views) {
        for (const element of view.elements) {
          if (!element.visible) count += element.findings.filter((f) => f.informational).length;
        }
      }
      return count;
    }

    renderChips() {
      if (this.contextCountNode) {
        const count = this.contextCount();
        this.contextCountNode.textContent = count ? ` (${count})` : "";
      }
      if (!this.chipsNode) return;
      const { codes } = this.counts();
      for (const code of [...this.activeCodes]) if (!codes.has(code)) this.activeCodes.delete(code);
      const chips = [...codes.entries()]
        .sort((a, b) => b[1] - a[1])
        .map(([code, count]) =>
          h(
            "button",
            {
              class: `dvi-chip code-${code}${this.activeCodes.has(code) ? " active" : ""}`,
              onclick: () => {
                if (this.activeCodes.has(code)) this.activeCodes.delete(code);
                else this.activeCodes.add(code);
                this.renderChips();
                this.applyFilters();
              },
            },
            this.data.codes[code] || code,
            h("span", { class: "dvi-chip-count" }, count)
          )
        );
      this.chipsNode.replaceChildren(...chips);
    }

    matches(element) {
      if (!this.showVisible && element.visible) return false;
      if (this.query) {
        const haystack = `${element.label} ${element.category} ${element.id}`.toLowerCase();
        if (!haystack.includes(this.query)) return false;
      }
      if (this.activeCodes.size) {
        return causes(element).some((f) => this.activeCodes.has(f.code));
      }
      return true;
    }

    applyFilters() {
      this.syncSelectAll();
      for (const view of this.views) {
        const section = this.viewSection(view.id);
        if (!section) continue;
        let shown = 0;
        for (const element of view.elements) {
          const card = section.querySelector(`[data-element="${element.id}"]`);
          const match = this.matches(element);
          if (card) card.hidden = !match;
          if (match) shown++;
        }
        section.querySelector(".dvi-empty").hidden = shown > 0 || view.elements.length === 0;
      }
      for (const row of this.matrixNode.querySelectorAll("tr[data-element]")) {
        const id = Number(row.dataset.element);
        row.hidden = !this.views.some((v) => {
          const element = v.elements.find((e) => e.id === id);
          return element && this.matches(element);
        });
      }
    }

    renderMatrix() {
      if (this.views.length < 2) {
        this.matrixNode.hidden = true;
        return;
      }
      this.matrixNode.hidden = false;
      const elements = this.views[0].elements;
      const head = h(
        "tr",
        null,
        h("th", null, ""),
        this.views.map((v) =>
          h("th", { title: v.type }, h("a", { href: "#", onclick: (e) => this.jumpTo(e, v.id) }, v.name))
        )
      );
      const rows = elements.map((element) =>
        h(
          "tr",
          { dataset: { element: element.id } },
          h("td", { class: "dvi-matrix-label" }, element.label),
          this.views.map((view) => {
            const entry = view.elements.find((e) => e.id === element.id);
            if (!entry) return h("td", null, "");
            const count = causes(entry).length;
            return h(
              "td",
              {
                class: `dvi-cell ${entry.visible ? "visible" : "hidden"}`,
                title: entry.visible ? this.s.visible : causes(entry).map((f) => f.message).join("\n"),
                onclick: (e) => this.jumpTo(e, view.id, element.id),
              },
              entry.visible ? "✓" : `✗ ${count}`
            );
          })
        )
      );
      this.matrixNode.replaceChildren(
        h("h3", null, this.s.overview),
        h("table", { class: "dvi-matrix-table" }, h("thead", null, head), h("tbody", null, rows))
      );
      this.applyFilters();
    }

    jumpTo(event, viewId, elementId) {
      event.preventDefault();
      const section = this.viewSection(viewId);
      if (!section) return;
      const target = elementId ? section.querySelector(`[data-element="${elementId}"]`) : section;
      if (!target) return;
      target.hidden = false;
      target.scrollIntoView({ behavior: "smooth", block: "center" });
      this.flash(target);
    }

    flash(node) {
      node.classList.remove("flash");
      void node.offsetWidth;
      node.classList.add("flash");
    }

    viewSection(viewId) {
      return this.viewsNode.querySelector(`section[data-view="${viewId}"]`);
    }

    fixableCount(view) {
      const seen = new Set();
      for (const element of view.elements) {
        for (const finding of causes(element)) {
          const fix = finding.fix;
          if (!fix || fix.navigation || finding.speculative) continue;
          seen.add(JSON.stringify(fix.descriptor) + (["unhide_element", "expand_section_box", "extend_view_range", "raise_cut_plane"].includes(fix.descriptor.action) ? element.id : ""));
        }
      }
      return seen.size;
    }

    renderView(view) {
      const existing = this.viewSection(view.id);
      const fixable = this.fixableCount(view);
      const hiddenCount = view.elements.filter((e) => !e.visible).length;
      const sceneOpen = this.sceneOpen.has(view.id);
      const sceneHost = existing ? existing.querySelector(".dvi-scene") : this.sceneShell(view);

      const actions = h(
        "div",
        { class: "dvi-view-actions" },
        this.data.bridge
          ? h(
              "button",
              { class: "dvi-btn", onclick: (e) => this.run(e.currentTarget, "open_view", { viewId: view.id }) },
              this.s.openView
            )
          : null,
        this.data.bridge
          ? h(
              "button",
              {
                class: `dvi-btn reveal${this.revealed.has(view.id) ? " active" : ""}`,
                title: this.s.revealHint,
                dataset: { reveal: view.id },
                onclick: (e) =>
                  this.run(e.currentTarget, "reveal", { viewId: view.id, on: !this.revealed.has(view.id) }),
              },
              this.s.reveal
            )
          : null,
        this.data.bridge
          ? h(
              "button",
              {
                class: "dvi-btn danger",
                title: this.s.removeView,
                onclick: (e) => this.run(e.currentTarget, "remove_view", { viewId: view.id }),
              },
              "\u00d7"
            )
          : null,
        this.data.bridge
          ? h(
              "button",
              {
                class: `dvi-btn${sceneOpen ? " active" : ""}`,
                onclick: (e) => this.toggleScene(view, e.currentTarget),
              },
              this.s.preview3d
            )
          : null,
        this.data.bridge && fixable
          ? h(
              "button",
              {
                class: "dvi-btn primary",
                onclick: (e) => this.run(e.currentTarget, "fix_all", { viewId: view.id }, this.s.fixed),
              },
              format(this.s.fixAll, fixable)
            )
          : null
      );

      const header = h(
        "div",
        { class: "dvi-view-head" },
        h(
          "div",
          { class: "dvi-view-title" },
          h("h3", null, view.name),
          h("span", { class: "dvi-badge" }, view.type),
          view.template ? h("span", { class: "dvi-badge template" }, format(this.s.template, view.template)) : null,
          h(
            "span",
            { class: `dvi-badge ${hiddenCount ? "hidden" : "visible"}` },
            hiddenCount ? `${hiddenCount} ${this.s.hidden}` : this.s.visible
          )
        ),
        actions
      );

      const cards = view.elements.map((element) => this.card(view, element));
      const section = h(
        "section",
        { class: `dvi-view${sceneOpen ? " scene-open" : ""}`, dataset: { view: view.id } },
        header,
        sceneHost,
        this.revealPanel(view.id),
        h("div", { class: "dvi-cards" }, cards),
        h("p", { class: "dvi-empty", hidden: true }, this.s.noMatch)
      );
      if (existing) existing.replaceWith(section);
      else this.viewsNode.append(section);
      this.applyFilters();
    }

    /**
     * Legend of one view's reveal overlay: a swatch, count, visibility toggle
     * and select button per reason, plus refresh and follow-viewport. Colors
     * come from Python so the legend matches what Revit draws.
     */
    revealPanel(viewId) {
      const summary = this.revealed.get(viewId);
      if (!summary) return h("div", { class: "dvi-reveal", hidden: true });
      const off = this.revealOff.get(viewId) || new Set();
      const rows = Object.entries(summary.counts)
        .sort((a, b) => b[1] - a[1])
        .map(([code, count]) =>
          h(
            "div",
            { class: "dvi-reveal-row" },
            h("input", {
              type: "checkbox",
              checked: !off.has(code),
              onchange: (e) => {
                if (e.target.checked) off.delete(code);
                else off.add(code);
                this.revealOff.set(viewId, off);
                this.run(null, "reveal_filter", { viewId, code, visible: e.target.checked });
              },
            }),
            h("span", { class: "dvi-swatch", style: `background:${this.data.revealColors[code] || "#9e9e9e"}` }),
            h("span", { class: "dvi-reveal-name" }, this.data.codes[code] || code),
            h("span", { class: "dvi-chip-count" }, count),
            h(
              "button",
              { class: "dvi-btn small", onclick: (e) => this.run(e.currentTarget, "reveal_select", { viewId, code }) },
              this.s.revealSelect
            )
          )
        );
      const skipped = summary.drawn || summary.tooSmall || summary.notEvaluated;
      const note = skipped ? format(this.s.revealSummary, summary.drawn) : this.s.revealNone;
      return h(
        "div",
        { class: "dvi-reveal" },
        h(
          "div",
          { class: "dvi-reveal-bar" },
          h("strong", null, note),
          summary.notEvaluated ? h("span", { class: "dvi-reveal-left" }, format(this.s.revealLeftOut, summary.notEvaluated)) : null,
          summary.tooSmall ? h("span", { class: "dvi-reveal-left" }, format(this.s.revealSmallSkipped, summary.tooSmall)) : null,
          h(
            "button",
            { class: "dvi-btn small", onclick: (e) => this.run(e.currentTarget, "reveal_refresh", { viewId }) },
            this.s.revealRefresh
          ),
          h(
            "label",
            { class: "dvi-toggle" },
            h("input", {
              type: "checkbox",
              checked: Boolean(this.revealFollow),
              onchange: (e) => {
                this.revealFollow = e.target.checked;
                this.run(null, "reveal_follow", { viewId, on: e.target.checked });
              },
            }),
            this.s.revealFollow
          )
        ),
        rows
      );
    }

    onReveal(summary) {
      const viewId = summary.viewId;
      this.revealFollow = summary.active ? Boolean(summary.follow) : false;
      if (summary.active) {
        this.revealed.set(viewId, summary);
      } else {
        this.revealed.delete(viewId);
        this.revealOff.delete(viewId);
      }
      const section = this.viewSection(viewId);
      if (!section) return;
      const panel = section.querySelector(".dvi-reveal");
      panel.replaceWith(this.revealPanel(viewId));
      for (const button of section.querySelectorAll(".dvi-btn.reveal")) {
        button.classList.toggle("active", this.revealed.has(viewId));
      }
    }

    card(view, element) {
      const bridge = this.data.bridge;
      const selectLink = h(
        "a",
        {
          class: "dvi-label",
          href: `revit://outputhelpers?command=select&element[]=${element.id}`,
          onclick: bridge
            ? (e) => {
                e.preventDefault();
                this.run(null, "select", { elementIds: [element.id] });
              }
            : null,
        },
        element.label
      );
      const head = h(
        "div",
        { class: "dvi-card-head" },
        bridge
          ? h("input", {
              type: "checkbox",
              class: "dvi-pick",
              title: this.s.selectForHide,
              dataset: { pick: element.id },
              checked: this.selected.has(element.id),
              onchange: (e) => {
                if (e.target.checked) this.selected.add(element.id);
                else this.selected.delete(element.id);
                this.syncSelection();
              },
            })
          : null,
        h("span", { class: "dvi-dot" }),
        selectLink,
        h(
          "span",
          { class: "dvi-card-actions" },
          bridge
            ? h(
                "button",
                {
                  class: `dvi-btn small ghost${this.ghosted.has(element.id) ? " active" : ""}`,
                  title: this.s.ghostHint,
                  dataset: { ghost: element.id },
                  onclick: (e) => this.toggleGhost(e.currentTarget, view, element),
                },
                this.s.ghost
              )
            : null,
          bridge
            ? h(
                "button",
                {
                  class: "dvi-btn small",
                  onclick: (e) => this.run(e.currentTarget, "zoom", { elementIds: [element.id] }),
                },
                this.s.zoom
              )
            : null,
          h(
            "button",
            {
              class: "dvi-btn small only-scene",
              title: this.s.preview3d,
              onclick: () => this.focusInScene(view.id, element.id),
            },
            "3D"
          ),
          bridge
            ? h(
                "button",
                {
                  class: "dvi-btn small danger",
                  title: this.s.removeElement,
                  onclick: (e) => this.run(e.currentTarget, "remove_element", { elementId: element.id }),
                },
                "\u00d7"
              )
            : null
        )
      );
      const findings = element.findings.map((finding) =>
        h(
          "li",
          {
            class: `dvi-finding ${finding.informational ? "info" : "cause"}${finding.speculative ? " speculative" : ""}`,
            title: finding.speculative ? this.s.speculativeHint : null,
          },
          h("span", { class: `dvi-code code-${finding.code}` }, this.data.codes[finding.code] || finding.code),
          h("span", { class: "dvi-message" }, finding.message),
          finding.fix && bridge ? this.fixButton(view, element, finding.fix) : null
        )
      );
      return h(
        "article",
        {
          class: `dvi-card ${element.visible ? "visible" : "hidden"}`,
          dataset: { element: element.id },
          onmouseenter: () => this.hoverInScene(view.id, element.id),
          onmouseleave: () => this.hoverInScene(view.id, null),
        },
        head,
        element.error ? h("p", { class: "dvi-error" }, element.error) : null,
        findings.length ? h("ul", { class: "dvi-findings" }, findings) : null
      );
    }

    /**
     * Toggle the DirectContext3D ghost of an element in Revit's views. The
     * ghost is per element, so every card of that element follows the state.
     */
    toggleGhost(button, view, element) {
      button.disabled = true;
      this.request("ghost", { viewId: view.id, elementId: element.id })
        .then((state) => {
          if (state === "on") this.ghosted.add(element.id);
          else this.ghosted.delete(element.id);
          for (const node of this.root.querySelectorAll(`.dvi-btn.ghost[data-ghost="${element.id}"]`)) {
            node.classList.toggle("active", this.ghosted.has(element.id));
          }
        })
        .catch((error) => this.toast(String(error.message || error), "error"))
        .finally(() => {
          if (button.isConnected) button.disabled = false;
        });
    }

    fixButton(view, element, fix) {
      return h(
        "button",
        {
          class: `dvi-btn small fix${fix.template ? " template" : ""}${fix.navigation ? " navigation" : ""}`,
          title: fix.template ? this.s.inTemplate : null,
          onclick: (e) =>
            this.run(
              e.currentTarget,
              "fix",
              { viewId: view.id, elementId: element.id, fix: fix.descriptor },
              fix.navigation ? null : this.s.fixed
            ),
        },
        fix.label
      );
    }

    sceneShell(view) {
      const canvasHost = h("div", { class: "dvi3d-host" });
      const layer = (name, label, checked, swatch) =>
        h(
          "label",
          { class: "dvi-toggle" },
          h("input", {
            type: "checkbox",
            checked,
            dataset: { layer: name },
            onchange: (e) => {
              const viewer = this.viewers.get(view.id);
              if (viewer) viewer.setLayer(name, e.target.checked);
            },
          }),
          h("span", { class: `dvi-swatch ${swatch}` }),
          label
        );
      const camera = (preset, label) =>
        h(
          "button",
          {
            class: "dvi-btn small",
            onclick: () => {
              const viewer = this.viewers.get(view.id);
              if (viewer) viewer.setCameraPreset(preset);
            },
          },
          label
        );
      return h(
        "div",
        { class: "dvi-scene", hidden: !this.sceneOpen.has(view.id) },
        h(
          "div",
          { class: "dvi-scene-bar" },
          layer("hidden", this.s.layerHidden, true, "hidden"),
          layer("visible", this.s.layerVisible, true, "visible"),
          layer("clip", this.s.layerClip, true, "clip"),
          layer("planes", this.s.layerPlanes, true, "planes"),
          h(
            "span",
            { class: "dvi-scene-cameras" },
            camera("view", this.s.cameraView),
            camera("top", this.s.cameraTop),
            camera("iso", this.s.cameraIso)
          )
        ),
        canvasHost,
        h("p", { class: "dvi-scene-help" }, this.s.sceneHelp)
      );
    }

    toggleScene(view, button) {
      const section = this.viewSection(view.id);
      const panel = section.querySelector(".dvi-scene");
      const opening = !this.sceneOpen.has(view.id);
      if (!opening) {
        this.sceneOpen.delete(view.id);
        panel.hidden = true;
        section.classList.remove("scene-open");
        button.classList.remove("active");
        return;
      }
      this.sceneOpen.add(view.id);
      panel.hidden = false;
      section.classList.add("scene-open");
      button.classList.add("active");
      if (this.viewers.has(view.id)) return;
      const host = panel.querySelector(".dvi3d-host");
      host.replaceChildren(h("div", { class: "dvi3d-loading" }, h("span", { class: "dvi-spinner" }), this.s.loadingScene));
      this.run(button, "scene", { viewId: view.id });
    }

    /**
     * Reload an already loaded preview after its view changed. Fixes can
     * move geometry and overlays (view range planes, section box, crop), not
     * only visibility, so the scene is rebuilt rather than recolored. At most
     * one request per view is in flight; changes arriving meanwhile trigger
     * one more reload when it completes.
     */
    refreshScene(viewId) {
      if (!this.viewers.has(viewId) && !this.sceneOpen.has(viewId)) return;
      if (this.sceneLoading.has(viewId)) {
        this.sceneStale.add(viewId);
        return;
      }
      this.sceneLoading.add(viewId);
      this.request("scene", { viewId })
        .catch((error) => this.toast(String(error.message || error), "error"))
        .finally(() => {
          this.sceneLoading.delete(viewId);
          if (this.sceneStale.delete(viewId)) this.refreshScene(viewId);
        });
    }

    showScene(scene) {
      const section = this.viewSection(scene.viewId);
      if (!section) return;
      const host = section.querySelector(".dvi3d-host");
      const previous = this.viewers.get(scene.viewId);
      const camera = previous ? previous.getCamera() : null;
      const highlightId = previous ? previous.highlightId : null;
      if (previous) {
        previous.destroy();
        this.viewers.delete(scene.viewId);
      }
      host.replaceChildren();
      if (!scene.meshes || !scene.meshes.length) {
        host.append(h("div", { class: "dvi3d-loading" }, this.s.sceneEmpty));
        return;
      }
      try {
        const viewer = new window.pyRevitInvisibilityViewer(host, scene, {
          strings: this.s,
          onPick: (id) => this.revealCard(scene.viewId, id),
        });
        if (camera) viewer.setCamera(camera);
        for (const input of section.querySelectorAll(".dvi-scene-bar input[data-layer]")) {
          viewer.setLayer(input.dataset.layer, input.checked);
        }
        if (highlightId !== null) viewer.highlight(highlightId);
        this.viewers.set(scene.viewId, viewer);
      } catch (error) {
        host.append(h("div", { class: "dvi3d-loading" }, String(error.message || error)));
      }
    }

    syncViewer(view) {
      const viewer = this.viewers.get(view.id);
      if (!viewer) return;
      for (const element of view.elements) viewer.setStatus(element.id, element.visible);
    }

    revealCard(viewId, elementId) {
      const card = this.viewSection(viewId).querySelector(`[data-element="${elementId}"]`);
      if (!card) return;
      card.hidden = false;
      card.scrollIntoView({ behavior: "smooth", block: "nearest" });
      this.flash(card);
    }

    focusInScene(viewId, elementId) {
      const viewer = this.viewers.get(viewId);
      if (!viewer) return;
      viewer.focus(elementId);
      this.viewSection(viewId).querySelector(".dvi-scene").scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    hoverInScene(viewId, elementId) {
      const viewer = this.viewers.get(viewId);
      if (viewer && viewer.highlightId === null) {
        viewer.hoverId = elementId;
        viewer.requestRender();
      }
    }

    markdown() {
      const lines = [`## ${this.s.title} — ${this.data.document}`, ""];
      for (const view of this.views) {
        lines.push(`### ${view.name} (${view.type})`, "");
        for (const element of view.elements) {
          lines.push(`- **${element.label}**: ${element.visible ? this.s.visible : this.s.hidden}`);
          for (const finding of element.findings) {
            if (finding.informational && !this.showContext) continue;
            lines.push(`  - ${finding.informational ? `_${this.s.context}:_ ` : ""}${finding.message}`);
          }
        }
        lines.push("");
      }
      return lines.join("\n");
    }

    copyMarkdown() {
      navigator.clipboard.writeText(this.markdown()).then(
        () => this.toast(this.s.copied, "ok"),
        (error) => this.toast(String(error), "error")
      );
    }
  }

  window.pyRevitInvisibility = {
    mount(rootId, data) {
      let root = document.getElementById(rootId);
      if (!root) {
        root = document.createElement("div");
        root.id = rootId;
        document.body.append(root);
      }
      const app = new App(root, data);
      apps.set(data.channel, app);
      listen();
      if (data.bridge && data.autoReveal !== null) {
        app.request("reveal", { viewId: data.autoReveal, on: true }).catch((error) => app.toast(String(error.message || error), "error"));
      }
      return app;
    },
  };
})();
