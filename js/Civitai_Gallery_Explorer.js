// ----- SECTION: Imports -----
import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

// ----- SECTION: Constants -----
const EXT_NAME = "CivitaiGalleryExplorer.InfiniteScroll";
const DISPLAY_NAME = "Civitai Gallery Explorer";
const TARGET_CLASS = "CivitaiGalleryExplorerNode";

const USER_TAG_GROUPS = [
  {
    label: "👤 People",
    items: [
      { name: "👩 Woman", id: "5133" },
      { name: "👨 Man", id: "5232" },
    ],
  },
  {
    label: "🐾 Animals & Creatures",
    items: [
      { name: "🐾 Animal", id: "111768" },
      { name: "🐱 Cat", id: "5132" },
      { name: "🐶 Dog", id: "2539" },
      { name: "🐉 Dragon", id: "5499" },
    ],
  },
  {
    label: "🎨 Styles & Media",
    items: [
      { name: "📷 Photography", id: "5241" },
      { name: "🖼️ PhotoRealistic", id: "172" },
      { name: "🖌️ Modern art", id: "617" },
      { name: "🎎 Anime", id: "4" },
      { name: "🎭 Cartoon", id: "5186" },
      { name: "📚 Comics", id: "2397" },
    ],
  },
  {
    label: "🏞️ Environments & Places",
    items: [
      { name: "🌲 Outdoors", id: "111763" },
      { name: "🌄 Landscape", id: "8363" },
      { name: "🏙️ City", id: "55" },
      { name: "🏛️ Architecture", id: "414" },
      { name: "🌌 Astronomy", id: "111767" },
    ],
  },
  {
    label: "👗 Clothing & Gear",
    items: [
      { name: "👕 Clothing", id: "5193" },
      { name: "🧥 Latex Clothing", id: "111935" },
      { name: "🛡️ Armor", id: "5169" },
      { name: "🎭 Costume", id: "2435" },
    ],
  },
  {
    label: "🚗 Vehicles & Transport",
    items: [
      { name: "🚉 Transportation", id: "111757" },
      { name: "🚗 Car", id: "111805" },
      { name: "🏎️ Sports Car", id: "111833" },
    ],
  },
  {
    label: "🎮 Genres & Characters",
    items: [
      { name: "🎮 Game Character", id: "5211" },
      { name: "🐲 Fantasy", id: "5207" },
      { name: "👾 Sci-Fi", id: "3060" },
      { name: "☣️ Post Apocalyptic", id: "213" },
      { name: "🤖 Robot", id: "6594" },
    ],
  },
  { label: "🍔 Other", items: [{ name: "🍔 Food", id: "3915" }] },
];

/**
 * @typedef {Object} CivitaiImageItem
 * @property {number} id
 * @property {string} url
 * @property {string} hash
 * @property {number} width
 * @property {number} height
 * @property {string} nsfwLevel
 * @property {string} type
 * @property {boolean} nsfw
 * @property {number} browsingLevel
 * @property {string} createdAt
 * @property {number} postId
 * @property {Object} stats
 * @property {number} stats.cryCount
 * @property {number} stats.laughCount
 * @property {number} stats.likeCount
 * @property {number} stats.dislikeCount
 * @property {number} stats.heartCount
 * @property {number} stats.commentCount
 * @property {Object} meta
 * @property {string} [meta.Size]
 * @property {boolean} [meta.nsfw]
 * @property {number} [meta.seed]
 * @property {boolean} [meta.draft]
 * @property {number} [meta.steps]
 * @property {number} [meta.width]
 * @property {number} [meta.height]
 * @property {string} [meta.prompt]
 * @property {string} [meta.sampler]
 * @property {number} [meta.cfgScale]
 * @property {number} [meta.clipSkip]
 * @property {string} [meta.fluxMode]
 * @property {number} [meta.quantity]
 * @property {string} [meta.workflow]
 * @property {string} [meta.baseModel]
 * @property {Array} [meta.resources]
 * @property {string} [meta.Created Date]
 * @property {Array} [meta.civitaiResources]
 * @property {string} username
 * @property {string} baseModel
 * @property {Array<number>} modelVersionIds
 */

export const Models = [
  "AuraFlow",
  "Chroma",
  "Flux.1 S",
  "Flux.1 D",
  "Flux.1 Krea",
  "Flux.1 Kontext",
  "Flux.2 D",
  "Flux.2 Klein 9B",
  "Flux.2 Klein 9B-base",
  "Flux.2 Klein 4B",
  "Flux.2 Klein 4B-base",
  "HiDream",
  "Hunyuan 1",
  "Hunyuan Video",
  "Illustrious",
  "Kolors",
  "LTXV",
  "LTXV2",
  "Lumina",
  "Mochi",
  "NoobAI",
  "Other",
  "PixArt a",
  "PixArt E",
  "Pony",
  "Pony V7",
  "Qwen",
  "SD 1.4",
  "SD 1.5",
  "SD 1.5 LCM",
  "SD 1.5 Hyper",
  "SD 2.0",
  "SD 2.1",
  "SDXL 1.0",
  "SDXL Lightning",
  "SDXL Hyper",
  "Wan Video 1.3B t2v",
  "Wan Video 14B t2v",
  "Wan Video 14B i2v 480p",
  "Wan Video 14B i2v 720p",
  "Wan Video 2.2 TI2V-5B",
  "Wan Video 2.2 I2V-A14B",
  "Wan Video 2.2 T2V-A14B",
  "Wan Video 2.5 T2V",
  "Wan Video 2.5 I2V",
  "ZImageTurbo",
  "ZImageBase",
];

// ----- SECTION: Helpers -----
function sanitizeProxyWidgets(props) {
  if (!props || typeof props !== "object" || Array.isArray(props))
    return { proxyWidgets: [] };
  if ("proxyWidget" in props && !("proxyWidgets" in props)) {
    props.proxyWidgets = props.proxyWidget;
    delete props.proxyWidget;
  }
  if (!("proxyWidgets" in props)) {
    props.proxyWidgets = [];
    return props;
  }
  const v = props.proxyWidgets;
  if (Array.isArray(v)) return props;
  if (v == null) props.proxyWidgets = [];
  else if (typeof v === "string") {
    const s = v.trim();
    if (!s) props.proxyWidgets = [];
    else if (s.startsWith("[") && s.endsWith("]")) {
      try {
        const arr = JSON.parse(s);
        props.proxyWidgets = Array.isArray(arr) ? arr : [s];
      } catch {
        props.proxyWidgets = [s];
      }
    } else props.proxyWidgets = [s];
  } else props.proxyWidgets = [];
  return props;
}

const qs = (o) =>
  Object.entries(o)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join("&");

const getJSON = async (path) => {
  const r = await api.fetchApi(path);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return await r.json();
};

const keyId = (id) => String(id);

function removeSelectionPort(node) {
  try {
    if (!Array.isArray(node.inputs)) return;
    const idx = node.inputs.findIndex((i) => i && i.name === "selection_data");
    if (idx >= 0) node.removeInput(idx);
  } catch {}
}

function hideWidgetDom(widget) {
  try {
    const el =
      widget?.element ||
      widget?.inputEl ||
      widget?.textarea ||
      widget?.wrapper ||
      widget?.dom ||
      widget?.root;

    if (el && el.style) {
      el.style.display = "none";
      el.style.visibility = "hidden";
      el.style.pointerEvents = "none";
      el.style.height = "0px";
      el.style.width = "0px";
      el.style.opacity = "0";
      el.style.position = "absolute";
      el.style.left = "-99999px";
      el.style.top = "-99999px";
    }

    if (widget?.html && widget.html.style) {
      widget.html.style.display = "none";
      widget.html.style.visibility = "hidden";
      widget.html.style.pointerEvents = "none";
      widget.html.style.height = "0px";
      widget.html.style.width = "0px";
      widget.html.style.opacity = "0";
      widget.html.style.position = "absolute";
      widget.html.style.left = "-99999px";
      widget.html.style.top = "-99999px";
    }
  } catch {}
}

function getOrCreateCGState(node) {
  node.properties = sanitizeProxyWidgets(node.properties || {});
  node.properties.__cg = node.properties.__cg || {};
  return node.properties.__cg;
}

function ensureHiddenSelectionWidget(node) {
  const cg = getOrCreateCGState(node);

  removeSelectionPort(node);

  let wSel = (node.widgets || []).find((w) => w?.name === "selection_data");
  if (!wSel) {
    wSel = node.addWidget(
      "text",
      "selection_data",
      typeof cg.selection_data === "string" ? cg.selection_data : "{}",
      (v) => {
        const s = typeof v === "string" ? v : String(v ?? "{}");
        cg.selection_data = s;
        try {
          app?.graph?.change?.();
        } catch {}
        try {
          node?.graph?.change?.();
        } catch {}
        node.setDirtyCanvas(true, true);
      },
      { multiline: true },
    );
  } else {
    const prevCb = wSel.callback;
    wSel.callback = (v) => {
      const s = typeof v === "string" ? v : String(v ?? "{}");
      cg.selection_data = s;
      try {
        prevCb?.(v);
      } catch {}
      try {
        app?.graph?.change?.();
      } catch {}
      try {
        node?.graph?.change?.();
      } catch {}
      node.setDirtyCanvas(true, true);
    };
  }

  wSel.serializeValue = () =>
    typeof cg.selection_data === "string" ? cg.selection_data : "{}";
  wSel.draw = function () {};
  wSel.computeSize = () => [0, 0];
  hideWidgetDom(wSel);

  if (typeof wSel.value !== "string")
    wSel.value =
      typeof cg.selection_data === "string" ? cg.selection_data : "{}";
  return wSel;
}

// ----- SECTION: Register Extension -----
(function () {
  app.registerExtension({
    name: EXT_NAME,

    beforeRegisterNodeDef(nodeType, nodeData) {
      const comfyClass = (
        nodeType?.comfyClass ||
        nodeData?.name ||
        ""
      ).toString();
      if (comfyClass !== TARGET_CLASS) return;

      const _configure = nodeType.prototype.configure;
      nodeType.prototype.configure = function (o, ...rest) {
        if (o && o.properties)
          o.properties = sanitizeProxyWidgets({ ...o.properties });
        const r = _configure?.call(this, o, ...rest);

        try {
          removeSelectionPort(this);
          ensureHiddenSelectionWidget(this);
        } catch {}

        return r;
      };

      const _onSerialize = nodeType.prototype.onSerialize;
      nodeType.prototype.onSerialize = function (o, ...rest) {
        const out = _onSerialize?.call(this, o, ...rest) ?? o ?? {};
        if (out && out.properties) sanitizeProxyWidgets(out.properties);
        return out;
      };

      const _onNodeCreated = nodeType.prototype.onNodeCreated;
      nodeType.prototype.onNodeCreated = function () {
        const r = _onNodeCreated?.apply(this, arguments);
        const node = this;

        node.properties = sanitizeProxyWidgets(node.properties || {});
        const cg = getOrCreateCGState(node);

        if (!cg.colored_once) {
          node.color = "#000000";
          node.bgcolor = "#0b0b0b";
          node.boxcolor = "#1e1e1e";
          node.title_color = "#ffffff";
          cg.colored_once = true;
          node.setDirtyCanvas(true, true);
        }

        removeSelectionPort(node);
        const wSel = ensureHiddenSelectionWidget(node);

        const uid = `cg-${Math.random().toString(36).slice(2, 9)}`;
        const root = document.createElement("div");
        root.id = uid;

        root.innerHTML = `
<style>
#${uid} {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--comfy-menu-bg, #202020);
  color: var(--fg-color, #e0e0e0);
  font-family: sans-serif;
  box-sizing: border-box;
  overflow: hidden;
  font-size: 12px;
}
#${uid} * { box-sizing: border-box; }

/* Header */
#${uid} .cg-header {
  padding: 8px 12px;
  background: rgba(0,0,0,0.2);
  border-bottom: 1px solid var(--border-color, #333);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  height: 40px;
}
#${uid} .cg-title { font-weight: bold; font-size: 13px; display: flex; align-items: center; gap: 8px; color: #fff; }
#${uid} .cg-title::before { content:''; display:block; width:8px; height:8px; background:#4ade80; border-radius:50%; }
#${uid} .cg-status { font-size: 11px; opacity: 0.7; max-width: 50%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* Controls Container */
#${uid} .cg-controls {
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: rgba(255,255,255,0.02);
  border-bottom: 1px solid var(--border-color, #333);
  flex-shrink: 0;
}

/* Rows & Cols */
#${uid} .cg-row { display: flex; gap: 8px; align-items: flex-end; width: 100%; flex-wrap: wrap; }
#${uid} .cg-col { display: flex; flex-direction: column; gap: 4px; }
#${uid} .cg-grow { flex: 1; min-width: 140px; }

/* Labels */
#${uid} label {
  font-size: 10px;
  color: #aaa;
  font-weight: 600;
  text-transform: uppercase;
  margin-left: 1px;
  letter-spacing: 0.5px;
}

/* Inputs & Selects */
#${uid} .cg-input, #${uid} .cg-select, #${uid} .cg-btn {
  height: 28px;
  background: var(--comfy-input-bg, #111);
  color: var(--input-text, #ddd);
  border: 1px solid var(--border-color, #444);
  border-radius: 4px;
  padding: 0 8px;
  font-size: 12px;
  outline: none;
  transition: border-color 0.1s, background 0.1s;
}
#${uid} .cg-input:focus, #${uid} .cg-select:focus { border-color: #777; background: #000; }

/* Base Models Custom Dropdown */
#${uid} .cg-base-models { position: relative; width: 100%; }
#${uid} .cg-base-models-trigger {
  width: 100%; display: flex; align-items: center; justify-content: space-between; cursor: pointer;
  text-align: left;
}
#${uid} .cg-base-models-panel {
  position: absolute; top: 100%; left: 0; width: 100%;
  background: #222; border: 1px solid #555; border-radius: 4px;
  z-index: 100; padding: 6px; display: none; flex-direction: column; gap: 6px;
  box-shadow: 0 8px 20px rgba(0,0,0,0.6); margin-top: 2px;
}
#${uid} .cg-base-models.open .cg-base-models-panel { display: flex; }
#${uid} .cg-base-models-list { max-height: 200px; overflow-y: auto; display: flex; flex-direction: column; gap: 1px; }
#${uid} .cg-base-models-item {
  display: flex; align-items: center; gap: 8px; padding: 5px;
  cursor: pointer; border-radius: 3px; font-size: 12px;
}
#${uid} .cg-base-models-item:hover { background: rgba(255,255,255,0.15); }

/* Buttons */
#${uid} .cg-btn { cursor: pointer; display: inline-flex; align-items: center; justify-content: center; user-select: none; }
#${uid} .cg-btn:hover { background: #333; border-color: #666; }
#${uid} .cg-btn:active { background: #222; transform: translateY(1px); }
#${uid} .cg-btn.primary { background: #2563eb; color: white; border-color: #1d4ed8; font-weight: 600; }
#${uid} .cg-btn.primary:hover { background: #1d4ed8; }

/* Segmented Control */
#${uid} .cg-segmented {
  display: flex; background: #111; border-radius: 4px; border: 1px solid #444; overflow: hidden;
}
#${uid} .cg-segmented .cg-btn {
  border: none; border-radius: 0; background: transparent; height: 26px; padding: 0 10px; border-right: 1px solid #333; color: #888;
}
#${uid} .cg-segmented .cg-btn:last-child { border-right: none; }
#${uid} .cg-segmented .cg-btn:hover { background: #222; color: #ccc; }
#${uid} .cg-segmented .cg-btn.active { background: #444; color: white; font-weight: 600; }

/* Toggle Render Specifics */
#${uid} .cg-toggle-render.cg-render-on { color: #4ade80; border-color: rgba(74, 222, 128, 0.4); }
#${uid} .cg-toggle-render.cg-render-off { color: #f87171; border-color: rgba(248, 113, 113, 0.4); }

/* Scroll Area */
#${uid} .cg-scroll {
  flex: 1; overflow-y: auto; padding: 10px; position: relative;
  background: #181818;
  min-height: 0;
}
#${uid} .cg-scroll::-webkit-scrollbar { width: 10px; display: block; }
#${uid} .cg-scroll::-webkit-scrollbar-track { background: #202020; }
#${uid} .cg-scroll::-webkit-scrollbar-thumb { background: #555; border-radius: 4px; border: 2px solid #202020; }
#${uid} .cg-scroll::-webkit-scrollbar-thumb:hover { background: #777; }

#${uid} .cg-masonry { display: flex; gap: 8px; flex-wrap: wrap; width: 100%; }
#${uid} .cg-masonry-col { flex: 1; display: flex; flex-direction: column; gap: 8px; min-width: 0; }
#${uid} .cg-sentinel { height: 20px; width: 100%; }

/* View Modes */
#${uid}.cg-view-grid .cg-masonry { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
#${uid}.cg-view-list .cg-masonry { display: flex; flex-direction: column; gap: 10px; }

/* Cards */
#${uid} .cg-card {
  background: #252525; border-radius: 6px; overflow: hidden;
  box-shadow: 0 2px 5px rgba(0,0,0,0.2); position: relative;
  border: 1px solid #333; transition: transform 0.1s, box-shadow 0.1s;
}
#${uid} .cg-card:hover { transform: translateY(-2px); border-color: #666; box-shadow: 0 6px 12px rgba(0,0,0,0.3); }
#${uid} .cg-card.selected { outline: 2px solid #2563eb; outline-offset: -1px; }
#${uid} .cg-img, #${uid} .cg-vid { width: 100%; display: block; height: auto; background: #000; min-height: 100px; object-fit: cover; }
#${uid}.cg-view-list .cg-card { display: flex; flex-direction: row; height: 120px; }
#${uid}.cg-view-list .cg-img, #${uid}.cg-view-list .cg-vid { width: 120px; height: 100%; flex: 0 0 120px; }
#${uid}.cg-view-list .cg-meta { flex: 1; }

#${uid} .cg-meta { padding: 6px 8px; font-size: 11px; display: flex; justify-content: space-between; align-items: center; color: #ccc; background: #252525; }
#${uid} .cg-meta-left { display: flex; align-items: center; gap: 6px; }
#${uid} .cg-chip { background: #333; padding: 2px 6px; border-radius: 4px; font-size: 10px; color: #aaa; border: 1px solid #444; }
#${uid} .cg-open { text-decoration: none; color: #60a5fa; background: #1e3a8a; padding: 2px 6px; border-radius: 4px; font-size: 10px; }
#${uid} .cg-open:hover { background: #2563eb; color: white; }
#${uid} .cg-star { background: none; border: none; color: #555; font-size: 16px; cursor: pointer; padding: 0; line-height: 1; }
#${uid} .cg-star:hover { transform: scale(1.1); }
#${uid} .cg-star.fav { color: #fbbf24; text-shadow: 0 0 5px rgba(251, 191, 36, 0.4); }

/* Footer */
#${uid} .cg-foot {
  padding: 4px 12px; border-top: 1px solid #333; background: #202020;
  font-size: 10px; color: #666; display: flex; justify-content: space-between; align-items: center;
  flex-shrink: 0; height: 24px;
}
</style>

  <div class="cg-header">
    <div class="cg-title">Civitai Gallery Explorer</div>
    <div class="cg-status"></div>
  </div>

  <div class="cg-controls">
    <!-- Row 1: Search -->
    <div class="cg-row">
       <div class="cg-col cg-grow">
          <label>Username</label>
          <input class="cg-input cg-username" placeholder="Search User...">
       </div>
       <div class="cg-col cg-grow">
          <label>Base Models</label>
          <div class="cg-base-models">
             <button class="cg-btn cg-base-models-trigger" type="button"><span>Any</span> ▾</button>
             <div class="cg-base-models-panel">
               <input class="cg-input cg-base-models-search" placeholder="Filter models...">
               <div class="cg-base-models-list"></div>
             </div>
          </div>
       </div>
       <div class="cg-col cg-grow">
          <label>Tags</label>
          <select class="cg-select cg-tags"><option value="">None</option></select>
       </div>
       <div class="cg-col">
          <label>&nbsp;</label>
          <button class="cg-btn cg-search primary">Search</button>
       </div>
    </div>

    <!-- Row 2: Filters -->
    <div class="cg-row">
       <div class="cg-col" style="flex:1">
          <label>Sort</label>
          <select class="cg-select cg-sort">
             <option>Newest</option><option>Most Reactions</option><option>Most Comments</option>
          </select>
       </div>
       <div class="cg-col" style="flex:1">
          <label>Period</label>
          <select class="cg-select cg-period">
             <option>AllTime</option><option>Year</option><option>Month</option><option>Week</option><option>Day</option>
          </select>
       </div>
       <div class="cg-col" style="width: 80px">
          <label>NSFW</label>
          <select class="cg-select cg-nsfw">
             <option>None</option><option>Soft</option><option>Mature</option><option>X</option>
          </select>
       </div>
       <div class="cg-col" style="width: 70px">
          <label>Limit</label>
          <select class="cg-select cg-limit">
              <option value="24" selected>24</option>
              <option value="50">50</option>
              <option value="100">100</option>
              <option value="150">150</option>
          </select>
       </div>
       <div class="cg-col">
          <label>View</label>
          <div class="cg-segmented">
             <button class="cg-btn toggle cg-view-btn" data-view="masonry">Masonry</button>
             <button class="cg-btn toggle cg-view-btn" data-view="grid">Grid</button>
             <button class="cg-btn toggle cg-view-btn" data-view="list">List</button>
          </div>
       </div>
    </div>

    <!-- Row 3: Toggles -->
    <div class="cg-row">
       <div class="cg-segmented">
          <button class="cg-btn toggle cg-toggle-video">Video</button>
          <button class="cg-btn toggle cg-toggle-noprompt">No Prompt</button>
          <button class="cg-btn toggle cg-toggle-unique">Unique</button>
          <button class="cg-btn toggle cg-toggle-favonly">Favs</button>
       </div>
       <div style="flex:1"></div>
       <button class="cg-btn cg-refresh">Refresh</button>
    </div>
  </div>

  <div class="cg-scroll">
    <div class="cg-masonry"></div>
    <div class="cg-sentinel"></div>
  </div>

  <div class="cg-foot">
    <span>Civitai Gallery Explorer</span>
  </div>
        `;

        const domWidget = node.addDOMWidget("civitai_gallery", "div", root, {});

        // Move gallery to top so inputs are below it
        const idx = node.widgets.indexOf(domWidget);
        if (idx > 0) {
          node.widgets.splice(idx, 1);
          node.widgets.unshift(domWidget);
        }

        // Increase node height to fit gallery + inputs
        node.size = [1120, 1800];

        // Ensure gallery doesn't overlap inputs by dynamically sizing it
        const _onResize = node.onResize;
        node.onResize = function (size) {
          _onResize?.apply(this, arguments);

          // Fix input widgets height so they don't expand
          const inputs = ["positive_prompt", "negative_prompt", "lora_data"];
          inputs.forEach((name) => {
            const w = node.widgets?.find((w) => w.name === name);
            if (w) {
              // Force fixed height
              w.computeSize = () => [size[0] - 20, 150];
            }
          });

          // Reserve space for inputs at bottom (3 inputs * 150 + margins approx 140px)
          const reserved = 590;
          const h = Math.max(200, size[1] - reserved);

          root.style.height = h + "px";
          root.style.maxHeight = h + "px";

          // Tell ComfyUI the gallery widget takes up this space
          // This pushes the inputs down below the gallery
          domWidget.computeSize = () => [size[0], h];
        };
        // Trigger once to set initial size
        node.onResize(node.size);

        const MIN_W = 900;
        const MIN_H = 650;

        const $ = (s) => root.querySelector(s);

        // We removed .cg-root, so use root directly for view classes
        const elRoot = root;
        const elNSFW = $(".cg-nsfw");
        const elSort = $(".cg-sort");
        const elPeriod = $(".cg-period");
        const elBaseModels = $(".cg-base-models");
        const elBaseModelsTrigger = $(".cg-base-models-trigger");
        const elBaseModelsPanel = $(".cg-base-models-panel");
        const elBaseModelsSearch = $(".cg-base-models-search");
        const elBaseModelsList = $(".cg-base-models-list");
        const elTags = $(".cg-tags");
        const elUser = $(".cg-username");
        const elSearch = $(".cg-search");
        const elRefresh = $(".cg-refresh");
        const elViewButtons = [...root.querySelectorAll(".cg-view-btn")];
        const elStatus = $(".cg-status");

        const elScroll = root.querySelector(".cg-scroll");
        const elGrid = root.querySelector(".cg-masonry");
        const elSentinel = root.querySelector(".cg-sentinel");

        const elBtnVideo = $(".cg-toggle-video");
        const elBtnNoPrompt = $(".cg-toggle-noprompt");
        const elBtnUnique = $(".cg-toggle-unique");
        const elBtnFavOnly = $(".cg-toggle-favonly");
        const elLimitSel = $(".cg-limit");
        const elBtnRender = $(".cg-toggle-render");

        let loading = false;
        let hasMore = true;
        let favoritesOnly = false;
        let videosOnly = false;
        let hideNoPrompt = false;
        let uniqueOnly = false;
        let seenPrompts = new Set();

        let favoritesMap = {};
        let favoritesArray = [];
        let cursor = null;
        let favOffset = 0;

        let _scrollHandlerBound = null;
        let _wheelHandler = null;
        let _pointerHandler = null;
        let _ioSentinel = null;
        let _ioVideo = null;

        const LS_VIEW_KEY = `CDH:view:${location.pathname}:${TARGET_CLASS}:${node.id}`;
        const LS_FILTER_KEY = `CDH:filters:${location.pathname}:${TARGET_CLASS}:${node.id}`;
        const LS_SCROLL_KEY = `CDH:scroll:${location.pathname}:${TARGET_CLASS}:${node.id}`;

        let inView = true;
        let userTouchedThisView = false;
        let autofillArmed = false;

        let restoringScroll = false;
        let _viewRAF = 0;
        let _scrollSaveRAF = 0;

        let lastScrollTop = Number.isFinite(cg.scroll_top) ? cg.scroll_top : 0;

        const setHiddenSelectionPayload = (payloadObj) => {
          const s = JSON.stringify(payloadObj || {});
          cg.selection_data = s;
          if (wSel) wSel.value = s;

          const wPos = node.widgets?.find((w) => w.name === "positive_prompt");
          if (wPos) {
            wPos.value = payloadObj?.item?.meta?.prompt || "";
          }

          const wNeg = node.widgets?.find((w) => w.name === "negative_prompt");
          if (wNeg) {
            wNeg.value = payloadObj?.item?.meta?.negativePrompt || "";
          }

          const wLora = node.widgets?.find((w) => w.name === "lora_data");
          if (wLora) {
            const resources = payloadObj?.item?.meta?.resources || [];
            const civitaiResources =
              payloadObj?.item?.meta?.civitaiResources || [];

            const isValidLora = (r) => {
              return (
                r &&
                String(r.type).toLowerCase() === "lora" &&
                (r.modelVersionId || r.hash)
              );
            };

            const loras1 = resources.filter(isValidLora);
            const loras2 = civitaiResources.filter(isValidLora);

            // Merge both lists
            const allLoras = [...loras1, ...loras2];
            wLora.value = JSON.stringify(allLoras, null, 4);
          }

          try {
            app?.graph?.change?.();
          } catch {}
          try {
            node?.graph?.change?.();
          } catch {}
          node.setDirtyCanvas(true, true);
        };

        const isNodeOnScreen = () => {
          try {
            const va =
              app?.canvas?.visible_area || app?.canvas?.ds?.visible_area;
            if (!va || va.length < 4) return true;

            const vx = va[0],
              vy = va[1],
              vw = va[2],
              vh = va[3];

            const nx = node.pos[0],
              ny = node.pos[1];
            const nw = node.size[0],
              nh = node.size[1];

            return nx + nw > vx && nx < vx + vw && ny + nh > vy && ny < vy + vh;
          } catch {
            return true;
          }
        };

        const getSavedScrollTop = () => {
          const fromCg = Number.isFinite(cg.scroll_top) ? cg.scroll_top : null;
          if (fromCg != null) return fromCg;

          try {
            const v = parseInt(localStorage.getItem(LS_SCROLL_KEY) || "0", 10);
            return Number.isFinite(v) ? v : 0;
          } catch {
            return 0;
          }
        };

        const saveScrollTopNow = () => {
          const v = Number.isFinite(lastScrollTop)
            ? lastScrollTop
            : (elScroll?.scrollTop ?? 0);
          cg.scroll_top = v;
          try {
            localStorage.setItem(LS_SCROLL_KEY, String(v));
          } catch {}
        };

        const saveScrollTop = () => {
          if (_scrollSaveRAF) return;
          _scrollSaveRAF = requestAnimationFrame(() => {
            _scrollSaveRAF = 0;
            saveScrollTopNow();
          });
        };

        const restoreScrollTop = () => {
          const v = getSavedScrollTop();
          lastScrollTop = v;
          restoringScroll = true;

          requestAnimationFrame(() => {
            if (elScroll) elScroll.scrollTop = v;

            setTimeout(() => {
              if (elScroll && !userTouchedThisView) elScroll.scrollTop = v;
              restoringScroll = false;
              if (nearBottom() && hasMore) loadMore();
            }, 60);
          });
        };

        const startViewportWatch = () => {
          const tick = () => {
            const now = isNodeOnScreen();
            if (now !== inView) {
              inView = now;

              if (!inView) {
                saveScrollTopNow();
              } else {
                userTouchedThisView = false;
                restoreScrollTop();
              }
            }
            _viewRAF = requestAnimationFrame(tick);
          };
          _viewRAF = requestAnimationFrame(tick);
        };

        const stopViewportWatch = () => {
          try {
            cancelAnimationFrame(_viewRAF);
          } catch {}
          _viewRAF = 0;
        };

        startViewportWatch();

        const readSavedFilters = () => {
          if (cg.filters && typeof cg.filters === "object") return cg.filters;
          try {
            const raw = localStorage.getItem(LS_FILTER_KEY);
            return raw ? JSON.parse(raw) : {};
          } catch {
            return {};
          }
        };

        const setSelectValue = (el, value) => {
          if (value == null || value === "") return;
          const ok = [...el.options].some(
            (o) => o.value === value || o.text === value,
          );
          if (ok) el.value = value;
        };

        const savedFilters = readSavedFilters();
        const savedTag =
          typeof savedFilters.tags === "string" ? savedFilters.tags : "";
        setSelectValue(elNSFW, savedFilters.nsfw);
        setSelectValue(elSort, savedFilters.sort);
        setSelectValue(elPeriod, savedFilters.period);
        setSelectValue(elLimitSel, savedFilters.limit);
        if (typeof savedFilters.username === "string")
          elUser.value = savedFilters.username;
        if (typeof savedFilters.videosOnly === "boolean")
          videosOnly = savedFilters.videosOnly;
        if (typeof savedFilters.hideNoPrompt === "boolean")
          hideNoPrompt = savedFilters.hideNoPrompt;
        if (typeof savedFilters.uniqueOnly === "boolean")
          uniqueOnly = savedFilters.uniqueOnly;
        if (typeof savedFilters.favoritesOnly === "boolean")
          favoritesOnly = savedFilters.favoritesOnly;

        const normalizeBaseModels = (v) => {
          if (Array.isArray(v))
            return v.map((x) => String(x || "").trim()).filter(Boolean);
          if (typeof v === "string")
            return v
              .split(",")
              .map((x) => String(x || "").trim())
              .filter(Boolean);
          return [];
        };

        let selectedBaseModels = new Set(
          normalizeBaseModels(savedFilters.baseModels ?? cg.base_models),
        );
        let baseModelsOpen = false;

        (function populateTags() {
          const keep = elTags.value || "";
          elTags.replaceChildren(new Option("None", ""));
          for (const group of USER_TAG_GROUPS) {
            const og = document.createElement("optgroup");
            og.label = group.label;
            for (const t of group.items)
              og.appendChild(new Option(t.name, String(t.id)));
            elTags.appendChild(og);
          }
          if ([...elTags.options].some((o) => o.value === keep))
            elTags.value = keep;
        })();
        if (savedTag && [...elTags.options].some((o) => o.value === savedTag))
          elTags.value = savedTag;

        const saveFilters = () => {
          const data = {
            nsfw: elNSFW.value,
            sort: elSort.value,
            period: elPeriod.value,
            tags: elTags.value,
            username: elUser.value.trim(),
            limit: elLimitSel.value,
            videosOnly,
            hideNoPrompt,
            uniqueOnly,
            favoritesOnly,
            baseModels: [...selectedBaseModels],
          };
          cg.filters = data;
          try {
            localStorage.setItem(LS_FILTER_KEY, JSON.stringify(data));
          } catch {}
        };

        const renderBaseModels = (filterText = "") => {
          const q = String(filterText || "")
            .toLowerCase()
            .trim();
          elBaseModelsList.replaceChildren();
          for (const m of Models) {
            if (q && !m.toLowerCase().includes(q)) continue;
            const row = document.createElement("div");
            row.className = "cg-base-models-item";
            const cb = document.createElement("input");
            cb.type = "checkbox";
            cb.checked = selectedBaseModels.has(m);
            const text = document.createElement("span");
            text.textContent = m;
            cb.addEventListener("change", () => {
              if (cb.checked) selectedBaseModels.add(m);
              else selectedBaseModels.delete(m);
              cg.base_models = [...selectedBaseModels];
              updateBaseModelsTrigger();
              saveFilters();
              reload(true);
            });
            row.appendChild(cb);
            row.appendChild(text);
            row.addEventListener("click", (e) => {
              if (e.target === cb) return;
              cb.checked = !cb.checked;
              cb.dispatchEvent(new Event("change"));
            });
            text.addEventListener("click", (e) => {
              e.preventDefault();
              e.stopPropagation();
              cb.checked = !cb.checked;
              cb.dispatchEvent(new Event("change"));
            });
            elBaseModelsList.appendChild(row);
          }
        };

        const updateBaseModelsTrigger = () => {
          const list = [...selectedBaseModels];
          const label = list.length ? list.join(", ") : "Any";
          elBaseModelsTrigger.querySelector("span").textContent = label;
        };

        const setBaseModelsOpen = (on) => {
          baseModelsOpen = !!on;
          elBaseModels.classList.toggle("open", baseModelsOpen);
          if (baseModelsOpen) {
            elBaseModelsSearch.focus();
          }
        };

        updateBaseModelsTrigger();
        renderBaseModels();

        const itemKey = (it) => `image:${keyId(it.id)}`;
        let cachedItems = Array.isArray(cg.cached_state?.items)
          ? cg.cached_state.items
          : [];
        let cachedSeen = new Set(cachedItems.map(itemKey));

        const loadFavoritesMap = async () => {
          try {
            favoritesMap = await getJSON(
              "/civitai_gallery/get_all_favorites_data",
            );
          } catch {
            favoritesMap = {};
          }
        };

        const getItemNsfw = (it) =>
          typeof it?.nsfwLevel === "string"
            ? it.nsfwLevel
            : it?.nsfw
              ? "X"
              : "None";

        const isVideo = (it) => {
          const u = (it?.url || "").toLowerCase();
          if (u.endsWith(".mp4") || u.endsWith(".webm")) return true;
          const m = it?.meta || {};
          const mv = String(
            m.video || m.videoUrl || m.mp4 || m.mp4Url || "",
          ).toLowerCase();
          return mv.endsWith(".mp4") || mv.endsWith(".webm");
        };

        const civitaiPageUrl = (it) =>
          it.pageUrl || it.postUrl || `https://civitai.com/images/${it.id}`;

        const getPositivePrompt = (it) =>
          it?.meta?.prompt ||
          it?.meta?.Prompt ||
          it?.meta?.positive ||
          it?.meta?.textPrompt ||
          "";

        const hasPositivePrompt = (it) =>
          !!String(getPositivePrompt(it) || "").trim();

        const batchSize = () => {
          const v = parseInt(elLimitSel.value || "24", 10);
          if (Number.isNaN(v)) return 24;
          return Math.min(500, Math.max(12, v));
        };

        const buildFilterKey = () =>
          JSON.stringify({
            nsfw: elNSFW.value,
            sort: elSort.value,
            period: elPeriod.value,
            tags: elTags.value,
            username: elUser.value.trim(),
            limit: elLimitSel.value,
            videosOnly,
            hideNoPrompt,
            uniqueOnly,
            favoritesOnly,
            baseModels: [...selectedBaseModels].sort(),
          });

        const makeUrlStream = (cur) => {
          const params = {
            min_batch: batchSize(),
            cursor: cur || "",
            sort: elSort.value,
            period: elPeriod.value,
            username: elUser.value.trim(),
            nsfw: elNSFW.value || "None",
            include_videos: videosOnly ? "true" : "false",
            videos_only: videosOnly ? "true" : "false",
            hide_no_prompt: hideNoPrompt ? "true" : "false",
            time_budget_ms: videosOnly ? "1200" : "",
          };
          const baseModels = [...selectedBaseModels];
          if (baseModels.length) params.baseModels = baseModels.join(",");
          if (elTags.value) params.tags = elTags.value;
          return `/civitai_gallery/images_stream?${qs(params)}`;
        };

        const chip = (t) => {
          const s = document.createElement("span");
          s.className = "cg-chip";
          s.textContent = t;
          return s;
        };

        const posterFromItem = (it) => {
          const m = it?.meta || {};
          return (
            it.thumbnail ||
            it.preview ||
            it.cover ||
            it.coverUrl ||
            it.previewUrl ||
            it.image ||
            m.thumbnail ||
            m.thumbnailUrl ||
            m.preview ||
            m.previewUrl ||
            m.image ||
            ""
          );
        };

        const setStatus = (msg) => {
          elStatus.textContent = msg || "";
        };

        const getPrompt = (it) => {
          const m = it.meta || {};
          return (
            m.prompt ||
            m.Prompt ||
            m.positive ||
            m.textPrompt ||
            ""
          ).trim();
        };

        const isUniquePrompt = (it) => {
          if (!uniqueOnly) return true;
          const p = getPrompt(it);
          if (!p) return true;
          const k = p.toLowerCase();
          if (seenPrompts.has(k)) return false;
          seenPrompts.add(k);
          return true;
        };

        const matchesVideoMode = (it) =>
          videosOnly ? isVideo(it) : !isVideo(it);

        const nearBottom = () =>
          elScroll.scrollHeight - elScroll.scrollTop - elScroll.clientHeight <=
          900;

        const setupObservers = () => {
          _ioVideo = new IntersectionObserver(
            (entries) => {
              if (!inView) return;

              for (const e of entries) {
                const v = e.target;
                if (!v || v.tagName !== "VIDEO") continue;
                if (e.isIntersecting) {
                  if (!v.src && v.dataset.src) {
                    v.preload = "metadata";
                    v.src = v.dataset.src;
                    v.load();

                    const kickPreview = () => {
                      try {
                        const t =
                          v.duration && isFinite(v.duration)
                            ? Math.min(0.1, Math.max(0.02, v.duration * 0.02))
                            : 0.1;
                        if (v.readyState < 2) return;
                        v.currentTime = t;
                      } catch {}
                    };

                    v.addEventListener("loadedmetadata", kickPreview, {
                      once: true,
                    });

                    setTimeout(() => {
                      if (v.readyState < 2) {
                        v.preload = "auto";
                        v.load();
                        setTimeout(kickPreview, 200);
                      }
                    }, 1200);
                  }
                }
              }
            },
            { root: elScroll, rootMargin: "1200px" },
          );

          _ioSentinel = new IntersectionObserver(
            (entries) => {
              if (!inView) return;
              if (restoringScroll) return;
              if (!autofillArmed && !userTouchedThisView) return;

              for (const e of entries) {
                if (e.isIntersecting && !loading && hasMore) loadMore();
              }
            },
            { root: elScroll, rootMargin: "1200px" },
          );

          _ioSentinel.observe(elSentinel);
        };

        const getOptimizedImageUrl = (it) => {
          if (!it || !it.url) return "";
          if (
            it.url.includes("image.civitai.com") &&
            it.url.includes("/original=true/")
          ) {
            return it.url.replace("/original=true/", "/width=320,quality=60/");
          }
          return it.url;
        };

        const makeCard = (it) => {
          const d = document.createElement("div");
          d.className = "cg-card";
          d.dataset.selkey = `image:${keyId(it.id)}`;

          if (isVideo(it)) {
            const v = document.createElement("video");
            if (it.width && it.height)
              v.style.aspectRatio = `${it.width}/${it.height}`;
            v.className = "cg-vid";
            v.controls = true;
            v.muted = true;
            v.playsInline = true;
            v.preload = "none";
            const poster = posterFromItem(it);
            if (poster) v.poster = poster;
            v.dataset.src =
              it.url || it?.meta?.videoUrl || it?.meta?.mp4Url || "";

            const freeze = () => {
              try {
                v.pause();
              } catch {}
            };
            v.addEventListener("seeked", freeze);
            v.addEventListener("loadeddata", freeze, { once: true });

            _ioVideo?.observe(v);
            d.appendChild(v);
          } else {
            const img = document.createElement("img");
            if (it.width && it.height)
              img.style.aspectRatio = `${it.width}/${it.height}`;
            img.className = "cg-img";
            img.loading = "lazy";
            img.alt = `#${keyId(it.id)}`;
            img.src = getOptimizedImageUrl(it);
            d.appendChild(img);
          }

          const meta = document.createElement("div");
          meta.className = "cg-meta";

          const left = document.createElement("div");
          left.className = "cg-meta-left";
          left.appendChild(chip(getItemNsfw(it)));
          left.appendChild(
            chip(new Date(it.createdAt || Date.now()).toLocaleDateString()),
          );
          if (it.width && it.height) {
            left.appendChild(chip(`${it.width}x${it.height}`));
          }

          const open = document.createElement("a");
          open.className = "cg-open";
          open.href = civitaiPageUrl(it);
          open.target = "_blank";
          open.rel = "noopener noreferrer";
          open.textContent = "Open ↗";
          open.addEventListener("click", (e) => e.stopPropagation());

          const star = document.createElement("button");
          star.className = "cg-star";
          star.title = "Toggle Favorite";

          const setStar = (on) => {
            if (on) {
              star.classList.add("fav");
              star.textContent = "★";
            } else {
              star.classList.remove("fav");
              star.textContent = "☆";
            }
          };
          setStar(Boolean(favoritesMap[keyId(it.id)]));

          star.addEventListener("click", async (e) => {
            e.stopPropagation();
            try {
              const resp = await api.fetchApi(
                "/civitai_gallery/toggle_favorite",
                {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ item: it }),
                },
              );
              const data = await resp.json();
              const k = keyId(it.id);

              if (data.status === "added") {
                favoritesMap[k] = it;
                setStar(true);
                if (favoritesOnly) await reload(true);
              } else if (data.status === "removed") {
                delete favoritesMap[k];
                setStar(false);
                if (favoritesOnly) await reload(true);
              }
            } catch (err) {
              console.error("Favorite toggle failed:", err);
            }
          });

          const rightBox = document.createElement("div");
          rightBox.style.display = "flex";
          rightBox.style.alignItems = "center";
          rightBox.style.gap = "8px";
          rightBox.appendChild(star);
          rightBox.appendChild(open);

          meta.appendChild(left);
          meta.appendChild(rightBox);
          d.appendChild(meta);

          d.addEventListener("click", () => selectItem(it, d));
          requestAnimationFrame(() => d.classList.add("show"));
          return d;
        };

        const getOrderedCards = () => {
          const currentCards = new Map();
          elGrid.querySelectorAll(".cg-card").forEach((c) => {
            currentCards.set(c.dataset.selkey, c);
          });
          const ordered = [];
          for (const it of cachedItems) {
            const key = itemKey(it);
            if (currentCards.has(key)) {
              ordered.push(currentCards.get(key));
            }
          }
          return ordered;
        };

        const distributeMasonry = (nodes) => {
          let cols = [...elGrid.querySelectorAll(".cg-masonry-col")];
          if (!cols.length) {
            let w = elScroll.clientWidth;
            if (w < 200) w = root.clientWidth;
            if (w < 200) w = 900;

            const numCols = Math.max(1, Math.floor(w / 280));
            for (let i = 0; i < numCols; i++) {
              const c = document.createElement("div");
              c.className = "cg-masonry-col";
              cols.push(c);
              elGrid.appendChild(c);
            }
          }

          const colHeights = cols.map((c) => c.offsetHeight);

          nodes.forEach((card) => {
            let minH = Infinity;
            let targetIdx = 0;
            for (let i = 0; i < colHeights.length; i++) {
              if (colHeights[i] < minH) {
                minH = colHeights[i];
                targetIdx = i;
              }
            }
            cols[targetIdx].appendChild(card);
            colHeights[targetIdx] = cols[targetIdx].offsetHeight;
          });
        };

        const rebuildMasonry = () => {
          // Only rebuild if currently in masonry mode
          if (
            cg.view_mode !== "masonry" &&
            !elRoot.classList.contains("cg-view-masonry")
          )
            return;

          const cards = getOrderedCards();
          elGrid.replaceChildren();

          const w = elScroll.clientWidth || root.clientWidth || 900;
          const numCols = Math.max(1, Math.floor(w / 280));
          const cols = [];
          for (let i = 0; i < numCols; i++) {
            const c = document.createElement("div");
            c.className = "cg-masonry-col";
            cols.push(c);
            elGrid.appendChild(c);
          }

          const colHeights = new Array(numCols).fill(0);

          cards.forEach((card) => {
            let minH = Infinity;
            let targetIdx = 0;
            for (let i = 0; i < numCols; i++) {
              if (colHeights[i] < minH) {
                minH = colHeights[i];
                targetIdx = i;
              }
            }
            cols[targetIdx].appendChild(card);
            colHeights[targetIdx] = cols[targetIdx].offsetHeight;
          });
        };

        const unwrapMasonry = () => {
          const cards = getOrderedCards();
          elGrid.replaceChildren();
          elGrid.append(...cards);
        };

        const appendGrid = (items, opts = {}) => {
          const fromCache = !!opts.fromCache;
          const seen = new Set(
            [...elGrid.querySelectorAll(".cg-card")].map(
              (c) => c.dataset.selkey,
            ),
          );
          const nodes = [];
          for (const it of items) {
            const key = itemKey(it);
            if (seen.has(key)) continue;
            const card = makeCard(it);
            nodes.push(card);
            seen.add(key);
            if (!fromCache && !cachedSeen.has(key)) {
              cachedItems.push(it);
              cachedSeen.add(key);
            }
          }
          if (nodes.length) {
            if (
              cg.view_mode === "masonry" ||
              elRoot.classList.contains("cg-view-masonry")
            ) {
              distributeMasonry(nodes);
            } else {
              elGrid.append(...nodes);
            }
          }
        };

        const selectItem = (item, cardEl) => {
          elGrid
            .querySelectorAll(".cg-card.selected")
            .forEach((c) => c.classList.remove("selected"));
          cardEl.classList.add("selected");

          const meta = item.meta || {};
          const pos =
            meta.prompt ||
            meta.Prompt ||
            meta.positive ||
            meta.textPrompt ||
            "";
          const neg =
            meta.negativePrompt || meta.NegativePrompt || meta.negative || "";

          const imageOutIdx = 2;
          const imageConnected =
            Array.isArray(node.outputs?.[imageOutIdx]?.links) &&
            node.outputs[imageOutIdx].links.length > 0;

          const payload = {
            item: {
              ...item,
              meta: {
                ...meta,
                prompt: pos || meta.prompt || "",
                negativePrompt: neg || meta.negativePrompt || "",
              },
            },
            download_image: !!imageConnected,
          };

          setHiddenSelectionPayload(payload);
        };

        const checkAndAutofill = async () => {
          if (!inView) return;
          if (!autofillArmed) return;

          let safety = 6;
          while (!loading && hasMore && nearBottom() && safety-- > 0) {
            await loadMore();
            if (!inView) break;
          }

          if (!nearBottom() || !hasMore || safety <= 0) {
            autofillArmed = false;
          }
        };

        const loadMoreServer = async () => {
          if (!inView || loading || !hasMore) return;
          loading = true;
          setStatus("Loading…");

          try {
            const data = await getJSON(makeUrlStream(cursor));

            let items = Array.isArray(data?.items) ? data.items : [];
            items = applyLocalFilters(items);

            appendGrid(items);

            cursor =
              data?.metadata?.nextCursor ??
              data?.metadata?.cursor ??
              data?.metadata?.next ??
              null;
            hasMore = !!cursor && items.length > 0;

            const ms = data?.metadata?.elapsedMs ?? "?";
            setStatus(
              hasMore
                ? `Loaded ${items.length} • more available (≈${ms}ms)`
                : `Loaded ${items.length} • end reached (≈${ms}ms)`,
            );
          } catch (e) {
            console.error(e);
            hasMore = false;
            setStatus(`Error: ${e.message}`);
          } finally {
            loading = false;
            requestAnimationFrame(checkAndAutofill);
          }
        };

        const applyLocalFilters = (arr) => {
          let out = arr.slice();
          out = out.filter(matchesVideoMode);
          if (hideNoPrompt) out = out.filter((it) => hasPositivePrompt(it));
          out = out.filter(isUniquePrompt);
          return out;
        };

        const loadMoreFavorites = async () => {
          if (!inView || loading || !hasMore) return;
          loading = true;
          setStatus("Loading favorites…");

          try {
            if (!favoritesArray.length) {
              if (!Object.keys(favoritesMap).length)
                favoritesMap = await getJSON(
                  "/civitai_gallery/get_all_favorites_data",
                );
              favoritesArray = Object.values(favoritesMap || {});
            }

            if (uniqueOnly) seenPrompts.clear();
            const filtered = applyLocalFilters(favoritesArray);
            const start = favOffset;
            const end = favOffset + batchSize();
            const slice = filtered.slice(start, end);

            appendGrid(slice);

            favOffset = end;
            hasMore = favOffset < filtered.length;

            setStatus(
              hasMore
                ? `Loaded ${slice.length} • ${filtered.length - favOffset} more`
                : `Loaded ${slice.length} • end reached`,
            );
          } catch (e) {
            console.error(e);
            hasMore = false;
            setStatus(`Error: ${e.message}`);
          } finally {
            loading = false;
            requestAnimationFrame(checkAndAutofill);
          }
        };

        const loadMore = async () => {
          if (!inView) return;
          if (favoritesOnly) return loadMoreFavorites();
          return loadMoreServer();
        };

        const reload = async (resetToTop) => {
          if (!inView) return;
          if (loading) return;

          autofillArmed = true;
          userTouchedThisView = true;

          loading = true;
          setStatus("Loading…");

          try {
            favoritesArray = [];
            favOffset = 0;

            elGrid.replaceChildren();
            cursor = null;
            hasMore = true;
            cachedItems = [];
            cachedSeen = new Set();
            seenPrompts.clear();

            if (resetToTop) {
              lastScrollTop = 0;
              if (elScroll) elScroll.scrollTop = 0;
              saveScrollTopNow();
            } else {
              restoreScrollTop();
            }

            await loadFavoritesMap();
            favoritesArray = Object.values(favoritesMap || {});

            await loadMore();
          } finally {
            loading = false;
            requestAnimationFrame(checkAndAutofill);
          }
        };

        const toggleBtn = (btn, flag) => btn.classList.toggle("active", flag);

        const bindScroll = () => {
          if (_scrollHandlerBound) return;

          const markTouched = () => {
            userTouchedThisView = true;
          };

          _scrollHandlerBound = () => {
            if (restoringScroll) return;
            markTouched();
            lastScrollTop = elScroll.scrollTop;
            saveScrollTop();
            if (nearBottom() && !loading && hasMore && inView) loadMore();
          };

          _wheelHandler = (e) => {
            markTouched();
            e.stopPropagation();
          };

          _pointerHandler = markTouched;

          elScroll.addEventListener("scroll", _scrollHandlerBound, {
            passive: true,
          });
          elScroll.addEventListener("wheel", _wheelHandler, { passive: false });
          elScroll.addEventListener("pointerdown", _pointerHandler, {
            passive: true,
          });
        };

        const unbindScroll = () => {
          if (_scrollHandlerBound) {
            elScroll.removeEventListener("scroll", _scrollHandlerBound);
            _scrollHandlerBound = null;
          }
          if (_wheelHandler) {
            elScroll.removeEventListener("wheel", _wheelHandler);
            _wheelHandler = null;
          }
          if (_pointerHandler) {
            elScroll.removeEventListener("pointerdown", _pointerHandler);
            _pointerHandler = null;
          }
        };

        const setRenderState = async () => {
          setupObservers();
          bindScroll();
          restoreScrollTop();

          // Removed cache restoration per user request
          if (!cg.has_loaded_once || !elGrid.childElementCount) {
            cg.has_loaded_once = true;
            await reload(true);
          }
        };

        const setViewMode = (mode) => {
          const m =
            mode === "grid" || mode === "list" || mode === "masonry"
              ? mode
              : "masonry";
          elRoot.classList.remove(
            "cg-view-masonry",
            "cg-view-grid",
            "cg-view-list",
          );
          elRoot.classList.add(`cg-view-${m}`);

          if (m === "masonry" && cg.view_mode !== "masonry") {
            rebuildMasonry();
          } else if (m !== "masonry" && cg.view_mode === "masonry") {
            unwrapMasonry();
          }

          try {
            cg.view_mode = m;
          } catch {}
          try {
            localStorage.setItem(LS_VIEW_KEY, m);
          } catch {}
          elViewButtons.forEach((b) => toggleBtn(b, b.dataset.view === m));
        };

        node.onResize = function (size) {
          if (size[0] < MIN_W) size[0] = MIN_W;
          if (size[1] < MIN_H) size[1] = MIN_H;
          requestAnimationFrame(checkAndAutofill);
          return size;
        };

        [elNSFW, elSort, elPeriod, elLimitSel].forEach((x) =>
          x.addEventListener("change", () => {
            saveFilters();
            reload(true);
          }),
        );
        elBaseModelsSearch.addEventListener("input", () =>
          renderBaseModels(elBaseModelsSearch.value),
        );
        elBaseModelsTrigger.addEventListener("pointerdown", (e) => {
          e.preventDefault();
          e.stopPropagation();
          setBaseModelsOpen(!baseModelsOpen);
        });
        elBaseModelsTrigger.addEventListener("focus", () => {
          setBaseModelsOpen(true);
        });
        elBaseModelsPanel.addEventListener("pointerdown", (e) => {
          e.stopPropagation();
        });
        document.addEventListener(
          "pointerdown",
          (e) => {
            const path = e.composedPath ? e.composedPath() : [];
            const inside = path.length
              ? path.includes(elBaseModels)
              : elBaseModels.contains(e.target);
            if (!inside) setBaseModelsOpen(false);
          },
          true,
        );
        elBaseModelsSearch.addEventListener("keydown", (e) => {
          if (e.key === "Escape") setBaseModelsOpen(false);
        });
        elTags.addEventListener("change", () => {
          saveFilters();
          reload(true);
        });
        elRefresh.addEventListener("click", () => reload(true));
        elSearch.addEventListener("click", () => {
          saveFilters();
          reload(true);
        });
        elUser.addEventListener("keydown", (e) => {
          if (e.key !== "Enter") return;
          saveFilters();
          reload(true);
        });

        elBtnVideo.addEventListener("click", () => {
          videosOnly = !videosOnly;
          toggleBtn(elBtnVideo, videosOnly);
          saveFilters();
          reload(true);
        });

        elBtnNoPrompt.addEventListener("click", () => {
          hideNoPrompt = !hideNoPrompt;
          toggleBtn(elBtnNoPrompt, hideNoPrompt);
          saveFilters();
          reload(true);
        });

        elBtnUnique.addEventListener("click", () => {
          uniqueOnly = !uniqueOnly;
          toggleBtn(elBtnUnique, uniqueOnly);
          saveFilters();
          reload(true);
        });

        elBtnFavOnly.addEventListener("click", async () => {
          favoritesOnly = !favoritesOnly;
          toggleBtn(elBtnFavOnly, favoritesOnly);
          saveFilters();
          await reload(true);
        });

        elViewButtons.forEach((b) =>
          b.addEventListener("click", () => setViewMode(b.dataset.view)),
        );

        const ro = new ResizeObserver(() => {
          const w = elScroll.clientWidth || root.clientWidth || 900;
          const target = Math.max(
            240,
            Math.min(360, Math.floor(w / Math.ceil(w / 280))),
          );
          elGrid.style.setProperty("--colw", `${target}px`);

          if (
            cg.view_mode === "masonry" ||
            elRoot.classList.contains("cg-view-masonry")
          ) {
            const numCols = Math.max(1, Math.floor(w / 280));
            const currentCols =
              elGrid.querySelectorAll(".cg-masonry-col").length;
            if (
              currentCols !== numCols &&
              (currentCols > 0 || elGrid.childElementCount > 0)
            ) {
              rebuildMasonry();
            }
          }

          requestAnimationFrame(checkAndAutofill);
        });
        ro.observe(elScroll);

        const _prevOnRemoved = node.onRemoved;
        node.onRemoved = function () {
          saveScrollTopNow();
          stopViewportWatch();
          try {
            _ioSentinel?.disconnect();
          } catch {}
          try {
            _ioVideo?.disconnect();
          } catch {}
          try {
            ro?.disconnect();
          } catch {}
          try {
            unbindScroll();
          } catch {}
          return _prevOnRemoved?.apply(this, arguments);
        };

        (async () => {
          toggleBtn(elBtnVideo, videosOnly);
          toggleBtn(elBtnNoPrompt, hideNoPrompt);
          toggleBtn(elBtnUnique, uniqueOnly);
          toggleBtn(elBtnFavOnly, favoritesOnly);
          setStatus("");

          let viewSaved = null;
          try {
            viewSaved = localStorage.getItem(LS_VIEW_KEY);
          } catch {}
          const propView = typeof cg.view_mode === "string" ? cg.view_mode : "";
          const initView = viewSaved || propView || "masonry";
          setViewMode(initView);

          await setRenderState();
        })();

        return r;
      };
    },
  });
})();
