const RULE_CATEGORIES = [
  {
    key: "exclude_dirs",
    title: "Excluded folders",
    placeholder: "Folder name, e.g. node_modules",
    searchPlaceholder: "Search rules or discovered folders",
    discoveryLabel: "Discovered folders",
  },
  {
    key: "exclude_files",
    title: "Excluded files",
    placeholder: "File name, e.g. package-lock.json",
    searchPlaceholder: "Search rules or discovered files",
    discoveryLabel: "Discovered files",
  },
  {
    key: "include_files",
    title: "Included files",
    placeholder: "Relative file path, e.g. storage/app/schema.json",
    searchPlaceholder: "Search included files or discovered paths",
    discoveryLabel: "Discovered files",
  },
  {
    key: "exclude_globs",
    title: "Excluded globs",
    placeholder: "Glob path, e.g. storage/**",
    searchPlaceholder: "Search rules or discovered paths",
    discoveryLabel: "Discovered paths",
  },
  {
    key: "exclude_extensions",
    title: "Excluded extensions",
    placeholder: "Extension, e.g. .log",
    searchPlaceholder: "Search rules or discovered extensions",
    discoveryLabel: "Discovered extensions",
  },
  {
    key: "include_extensions",
    title: "Included merge extensions",
    placeholder: "Extension to merge, e.g. .py",
    searchPlaceholder: "Search rules or discovered extensions",
    discoveryLabel: "Discovered extensions",
  },
];

const els = {
  versionLabel: document.getElementById("versionLabel"),
  runningNotice: document.getElementById("runningNotice"),
  watcherState: document.getElementById("watcherState"),
  lastRun: document.getElementById("lastRun"),
  lastChange: document.getElementById("lastChange"),
  mergedCount: document.getElementById("mergedCount"),
  saveState: document.getElementById("saveState"),
  projectRoot: document.getElementById("projectRoot"),
  projectType: document.getElementById("projectType"),
  customPresetName: document.getElementById("customPresetName"),
  newCustomPresetBtn: document.getElementById("newCustomPresetBtn"),
  deleteCustomPresetBtn: document.getElementById("deleteCustomPresetBtn"),
  outputDir: document.getElementById("outputDir"),
  maxFileSizeKb: document.getElementById("maxFileSizeKb"),
  pollInterval: document.getElementById("pollInterval"),
  debounceSeconds: document.getElementById("debounceSeconds"),
  syncLmstudio: document.getElementById("syncLmstudio"),
  conversationPath: document.getElementById("conversationPath"),
  backupConversation: document.getElementById("backupConversation"),
  useGitnexus: document.getElementById("useGitnexus"),
  rulesGrid: document.getElementById("rulesGrid"),
  tabButtons: [...document.querySelectorAll(".tab-button")],
  tabPages: [...document.querySelectorAll("[data-tab-page]")],
  structurePath: document.getElementById("structurePath"),
  mergedPath: document.getElementById("mergedPath"),
  terminal: document.getElementById("terminal"),
  saveBtn: document.getElementById("saveBtn"),
  runBtn: document.getElementById("runBtn"),
  startBtn: document.getElementById("startBtn"),
  stopBtn: document.getElementById("stopBtn"),
  refreshBtn: document.getElementById("refreshBtn"),
  clearLogsBtn: document.getElementById("clearLogsBtn"),
  shutdownBtn: document.getElementById("shutdownBtn"),
  browseProjectBtn: document.getElementById("browseProjectBtn"),
  browseConversationBtn: document.getElementById("browseConversationBtn"),
};

const state = {
  presets: { project_types: [], presets: {} },
  customPresets: {},
  rules: emptyRules(),
  discovery: emptyRules(),
  ruleElements: {},
  activeProjectType: "generic",
  savedSnapshot: "",
  formDirty: false,
  watcherRunning: false,
  loading: false,
  discoveryTimer: null,
};

let lastLogId = 0;

function switchTab(tabName) {
  for (const button of els.tabButtons) {
    const active = button.dataset.tab === tabName;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", active ? "true" : "false");
  }

  for (const page of els.tabPages) {
    const active = page.dataset.tabPage === tabName;
    page.classList.toggle("active", active);
    page.hidden = !active;
  }
}

function emptyRules() {
  return Object.fromEntries(RULE_CATEGORIES.map((category) => [category.key, []]));
}

function cloneRules(rules = {}) {
  const cloned = emptyRules();
  for (const category of RULE_CATEGORIES) {
    cloned[category.key] = Array.isArray(rules[category.key]) ? [...rules[category.key]] : [];
  }
  return cloned;
}

function isCustomProjectType(projectType) {
  return projectType === "custom" || String(projectType || "").startsWith("custom:");
}

function customFallbackName(projectType) {
  if (projectType === "custom") {
    return "custom";
  }
  if (String(projectType || "").startsWith("custom:")) {
    return projectType.split(":", 2)[1] || "custom";
  }
  return "custom";
}

function normalizeRuleItem(category, value) {
  let text = String(value || "").trim();
  if (!text) {
    return "";
  }
  if (category === "exclude_globs") {
    return text.replace(/\\/g, "/");
  }
  if (category === "include_files") {
    return text.replace(/\\/g, "/").replace(/^\.\//, "");
  }
  if (category === "exclude_extensions" || category === "include_extensions") {
    text = text.toLowerCase();
    return text.startsWith(".") ? text : `.${text}`;
  }
  return text;
}

function ruleKey(category, value) {
  return normalizeRuleItem(category, value).toLowerCase();
}

function uniqueRules(category, values) {
  const seen = new Set();
  const result = [];
  for (const rawValue of Array.isArray(values) ? values : []) {
    const value = normalizeRuleItem(category, rawValue);
    const key = ruleKey(category, value);
    if (!value || seen.has(key)) {
      continue;
    }
    seen.add(key);
    result.push(value);
  }
  return result;
}

function getPresetRules(projectType) {
  return cloneRules((state.presets.presets || {})[projectType] || {});
}

function currentRulePayload() {
  return cloneRules(state.rules);
}

function customPresetPayload(name, rules = {}) {
  return {
    name: String(name || "custom").trim().slice(0, 64) || "custom",
    ...cloneRules(rules),
  };
}

function cloneCustomPresets(presets = {}) {
  const cloned = {};
  for (const [key, preset] of Object.entries(presets || {})) {
    if (!isCustomProjectType(key)) {
      continue;
    }
    cloned[key] = customPresetPayload(preset.name || customFallbackName(key), preset);
  }
  return cloned;
}

function ensureDefaultCustomPreset() {
  if (!state.customPresets.custom) {
    state.customPresets.custom = customPresetPayload("custom");
  }
}

function customPresetNameForKey(projectType) {
  const preset = state.customPresets[projectType] || {};
  return String(preset.name || "").trim() || customFallbackName(projectType);
}

function customPresetHasRules(projectType) {
  const preset = state.customPresets[projectType] || {};
  return RULE_CATEGORIES.some((category) => Array.isArray(preset[category.key]) && preset[category.key].length > 0);
}

function canReuseDefaultCustomPreset() {
  return (
    !state.customPresets.custom ||
    (customPresetNameForKey("custom").toLowerCase() === "custom" && !customPresetHasRules("custom"))
  );
}

function nextCustomPresetIdentity(preferEmptyDefault = false) {
  if (preferEmptyDefault && canReuseDefaultCustomPreset()) {
    return ["custom", "custom"];
  }

  const keys = new Set(Object.keys(state.customPresets));
  const names = new Set(Object.keys(state.customPresets).map((key) => customPresetNameForKey(key).toLowerCase()));
  let index = 2;
  while (true) {
    const name = `custom${index}`;
    const key = `custom:${name}`;
    if (!keys.has(key) && !names.has(name.toLowerCase())) {
      return [key, name];
    }
    index += 1;
  }
}

function syncCurrentCustomPreset() {
  const projectType = els.projectType.value || state.activeProjectType;
  if (!isCustomProjectType(projectType)) {
    return;
  }
  state.customPresets[projectType] = customPresetPayload(
    els.customPresetName.value || customPresetNameForKey(projectType),
    currentRulePayload(),
  );
}

function renderProjectTypeOptions(selected = null) {
  const current = selected || els.projectType.value || state.activeProjectType || "generic";
  ensureDefaultCustomPreset();

  els.projectType.innerHTML = "";

  const builtInGroup = document.createElement("optgroup");
  builtInGroup.label = "Built-in presets";
  for (const projectType of state.presets.project_types || []) {
    if (projectType === "custom") {
      continue;
    }
    const option = document.createElement("option");
    option.value = projectType;
    option.textContent = projectType;
    builtInGroup.appendChild(option);
  }
  els.projectType.appendChild(builtInGroup);

  const customGroup = document.createElement("optgroup");
  customGroup.label = "Custom presets";
  for (const [key, preset] of Object.entries(state.customPresets)) {
    const option = document.createElement("option");
    option.value = key;
    option.textContent = preset.name || customFallbackName(key);
    customGroup.appendChild(option);
  }
  els.projectType.appendChild(customGroup);

  const optionExists = [...els.projectType.options].some((option) => option.value === current);
  els.projectType.value = optionExists ? current : "generic";
  state.activeProjectType = els.projectType.value || "generic";
}

function updateCustomPresetControls() {
  const isCustom = isCustomProjectType(els.projectType.value);
  els.customPresetName.disabled = !isCustom || state.watcherRunning;
  els.newCustomPresetBtn.disabled = state.watcherRunning;
  els.deleteCustomPresetBtn.disabled = !isCustom || state.watcherRunning || Object.keys(state.customPresets).length <= 1;
  if (!isCustom) {
    els.customPresetName.value = "";
  }
}

function setRules(rules = {}) {
  for (const category of RULE_CATEGORIES) {
    state.rules[category.key] = uniqueRules(category.key, rules[category.key] || []);
    renderRuleList(category.key);
  }
}

function renderRuleCards() {
  els.rulesGrid.innerHTML = "";
  state.ruleElements = {};

  for (const category of RULE_CATEGORIES) {
    const card = document.createElement("section");
    card.className = "rule-card";
    if (category.key === "include_files" || category.key === "include_extensions") {
      card.classList.add("wide");
    }

    const title = document.createElement("h3");
    title.textContent = category.title;

    const search = document.createElement("input");
    search.type = "search";
    search.placeholder = category.searchPlaceholder;

    const list = document.createElement("div");
    list.className = "rule-list";

    const discovery = document.createElement("div");
    discovery.className = "rule-discovery";
    const discoveryHead = document.createElement("div");
    discoveryHead.className = "rule-discovery-head";
    discoveryHead.textContent = category.discoveryLabel;
    const discoveryList = document.createElement("div");
    discoveryList.className = "rule-discovery-list";
    discovery.append(discoveryHead, discoveryList);

    const addRow = document.createElement("div");
    addRow.className = "rule-add-row";
    const addInput = document.createElement("input");
    addInput.type = "text";
    addInput.placeholder = category.placeholder;
    const addButton = document.createElement("button");
    addButton.type = "button";
    addButton.textContent = "Add";
    addRow.append(addInput, addButton);

    const count = document.createElement("span");
    count.className = "rule-count";

    card.append(title, search, list, discovery, addRow, count);
    els.rulesGrid.appendChild(card);

    state.ruleElements[category.key] = {
      search,
      list,
      discoveryList,
      addInput,
      addButton,
      count,
    };
    search.addEventListener("input", () => renderRuleList(category.key));
    addButton.addEventListener("click", () => addRuleItem(category.key));
    addInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        addRuleItem(category.key);
      }
    });
  }
}

function renderRuleList(category) {
  const parts = state.ruleElements[category];
  if (!parts) {
    return;
  }

  const query = parts.search.value.trim().toLowerCase();
  const values = state.rules[category] || [];
  const existingKeys = new Set(values.map((value) => ruleKey(category, value)));
  const filtered = values.filter((value) => !query || value.toLowerCase().includes(query));
  parts.list.innerHTML = "";
  parts.discoveryList.innerHTML = "";

  for (const value of filtered) {
    const row = document.createElement("div");
    row.className = "rule-item";
    const label = document.createElement("span");
    label.textContent = value;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "X";
    remove.title = "Remove rule";
    remove.disabled = state.watcherRunning;
    remove.addEventListener("click", () => removeRuleItem(category, value));
    row.append(label, remove);
    parts.list.appendChild(row);
  }

  if (!filtered.length) {
    const empty = document.createElement("div");
    empty.className = "rule-empty";
    empty.textContent = query ? "No matching rules" : "No rules";
    parts.list.appendChild(empty);
  }

  const discovered = (state.discovery[category] || [])
    .map((value) => normalizeRuleItem(category, value))
    .filter((value) => value && !existingKeys.has(ruleKey(category, value)))
    .filter((value) => !query || value.toLowerCase().includes(query))
    .slice(0, 60);

  for (const value of discovered) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "rule-suggestion";
    button.textContent = value;
    button.title = `Add ${value}`;
    button.disabled = state.watcherRunning;
    button.addEventListener("click", () => addRuleValue(category, value));
    parts.discoveryList.appendChild(button);
  }

  if (!discovered.length) {
    const empty = document.createElement("div");
    empty.className = "rule-empty compact";
    empty.textContent = query ? "No discovered matches" : "No discovered items";
    parts.discoveryList.appendChild(empty);
  }

  parts.count.textContent = query ? `${filtered.length} of ${values.length}` : `${values.length} item${values.length === 1 ? "" : "s"}`;
  parts.addInput.disabled = state.watcherRunning;
  parts.addButton.disabled = state.watcherRunning;
}

function switchToCustomAfterRuleEdit() {
  if (isCustomProjectType(els.projectType.value)) {
    syncCurrentCustomPreset();
    renderProjectTypeOptions(els.projectType.value);
    return;
  }

  const [key, name] = nextCustomPresetIdentity(true);
  state.customPresets[key] = customPresetPayload(name, currentRulePayload());
  renderProjectTypeOptions(key);
  els.customPresetName.value = name;
  state.activeProjectType = key;
  updateCustomPresetControls();
}

function addRuleValue(category, rawValue) {
  const value = normalizeRuleItem(category, rawValue);
  if (!value) {
    return false;
  }

  const exists = new Set((state.rules[category] || []).map((item) => ruleKey(category, item)));
  if (exists.has(ruleKey(category, value))) {
    alert(`${ruleTitle(category)} already contains:\n\n${value}`);
    const parts = state.ruleElements[category];
    parts.search.value = value;
    renderRuleList(category);
    return false;
  }

  state.rules[category].push(value);
  switchToCustomAfterRuleEdit();
  renderRuleList(category);
  markDirty();
  return true;
}

function addRuleItem(category) {
  const parts = state.ruleElements[category];
  if (addRuleValue(category, parts.addInput.value)) {
    parts.addInput.value = "";
  }
}

function removeRuleItem(category, value) {
  const target = ruleKey(category, value);
  state.rules[category] = (state.rules[category] || []).filter((item) => ruleKey(category, item) !== target);
  switchToCustomAfterRuleEdit();
  renderRuleList(category);
  markDirty();
}

function ruleTitle(category) {
  return (RULE_CATEGORIES.find((item) => item.key === category) || {}).title || category;
}

function loadSelectedCustomPreset(projectType) {
  if (!state.customPresets[projectType]) {
    state.customPresets[projectType] = customPresetPayload(customFallbackName(projectType));
  }
  els.customPresetName.value = customPresetNameForKey(projectType);
  setRules(state.customPresets[projectType]);
  updateCustomPresetControls();
}

function handleProjectTypeChanged() {
  if (state.loading) {
    return;
  }

  const projectType = els.projectType.value || "generic";
  if (isCustomProjectType(projectType)) {
    loadSelectedCustomPreset(projectType);
  } else {
    setRules(getPresetRules(projectType));
    updateCustomPresetControls();
  }
  state.activeProjectType = projectType;
  markDirty();
}

function handleCustomPresetNameChanged() {
  if (state.loading || !isCustomProjectType(els.projectType.value)) {
    return;
  }
  syncCurrentCustomPreset();
  renderProjectTypeOptions(els.projectType.value);
  markDirty();
}

function createCustomPreset() {
  if (state.watcherRunning) {
    return;
  }
  syncCurrentCustomPreset();
  const [key, name] = nextCustomPresetIdentity(true);
  state.customPresets[key] = customPresetPayload(name, currentRulePayload());
  renderProjectTypeOptions(key);
  loadSelectedCustomPreset(key);
  state.activeProjectType = key;
  markDirty();
}

function deleteCustomPreset() {
  const projectType = els.projectType.value;
  if (!isCustomProjectType(projectType) || Object.keys(state.customPresets).length <= 1) {
    return;
  }
  const name = customPresetNameForKey(projectType);
  if (!confirm(`Delete custom preset "${name}"?`)) {
    return;
  }
  delete state.customPresets[projectType];
  renderProjectTypeOptions("generic");
  setRules(getPresetRules("generic"));
  updateCustomPresetControls();
  state.activeProjectType = "generic";
  markDirty();
}

function readConfigFromForm() {
  syncCurrentCustomPreset();
  const projectType = els.projectType.value || "generic";
  return {
    project_root: els.projectRoot.value.trim(),
    project_type: projectType,
    custom_preset_name: isCustomProjectType(projectType)
      ? els.customPresetName.value.trim() || customPresetNameForKey(projectType)
      : "",
    custom_presets: cloneCustomPresets(state.customPresets),
    output_dir: els.outputDir.value.trim(),
    max_file_size_kb: Number(els.maxFileSizeKb.value || 512),
    poll_interval_seconds: Number(els.pollInterval.value || 1),
    debounce_seconds: Number(els.debounceSeconds.value || 0.8),
    sync_lmstudio: els.syncLmstudio.checked,
    conversation_path: els.conversationPath.value.trim(),
    backup_conversation: els.backupConversation.checked,
    use_gitnexus: els.useGitnexus.checked,
    ...currentRulePayload(),
  };
}

function hasConfigRules(config) {
  return RULE_CATEGORIES.some((category) => Array.isArray(config[category.key]) && config[category.key].length > 0);
}

function writeConfigToForm(config) {
  state.loading = true;
  try {
    state.customPresets = cloneCustomPresets(config.custom_presets || {});
    if (isCustomProjectType(config.project_type) && !state.customPresets[config.project_type]) {
      state.customPresets[config.project_type] = customPresetPayload(config.custom_preset_name, config);
    }
    ensureDefaultCustomPreset();

    state.presets.project_types = state.presets.project_types || [];
    renderProjectTypeOptions(config.project_type || "generic");

    els.projectRoot.value = config.project_root || "";
    els.outputDir.value = config.output_dir || "";
    els.maxFileSizeKb.value = config.max_file_size_kb || 512;
    els.pollInterval.value = config.poll_interval_seconds || 1;
    els.debounceSeconds.value = config.debounce_seconds || 0.8;
    els.syncLmstudio.checked = Boolean(config.sync_lmstudio);
    els.conversationPath.value = config.conversation_path || "";
    els.backupConversation.checked = config.backup_conversation !== false;
    els.useGitnexus.checked = Boolean(config.use_gitnexus);

    if (isCustomProjectType(config.project_type)) {
      loadSelectedCustomPreset(config.project_type);
    } else if (hasConfigRules(config)) {
      setRules(config);
      updateCustomPresetControls();
    } else {
      setRules(getPresetRules(config.project_type || "generic"));
      updateCustomPresetControls();
    }

    state.activeProjectType = els.projectType.value || "generic";
    state.savedSnapshot = snapshotForm();
    state.formDirty = false;
    els.saveState.textContent = "Saved";
  } finally {
    state.loading = false;
    updateControls();
    scheduleDiscoveryRefresh();
  }
}

function snapshotForm() {
  return JSON.stringify(readConfigFromForm());
}

function markDirty() {
  if (state.loading) {
    return;
  }
  state.formDirty = snapshotForm() !== state.savedSnapshot;
  els.saveState.textContent = state.formDirty ? "Unsaved changes" : "Saved";
  updateControls();
}

function validateRuleLists() {
  for (const category of RULE_CATEGORIES) {
    const seen = new Set();
    for (const value of state.rules[category.key] || []) {
      const key = ruleKey(category.key, value);
      if (seen.has(key)) {
        alert(`${category.title} has a duplicate entry:\n\n${value}`);
        return false;
      }
      seen.add(key);
    }
  }
  return true;
}

function updateControls() {
  const locked = state.watcherRunning;
  document.body.classList.toggle("watcher-running", locked);
  els.runningNotice.hidden = !locked;

  const lockable = [
    els.projectRoot,
    els.projectType,
    els.customPresetName,
    els.newCustomPresetBtn,
    els.deleteCustomPresetBtn,
    els.outputDir,
    els.maxFileSizeKb,
    els.pollInterval,
    els.debounceSeconds,
    els.syncLmstudio,
    els.conversationPath,
    els.backupConversation,
    els.useGitnexus,
    els.browseProjectBtn,
    els.browseConversationBtn,
  ];

  for (const element of lockable) {
    element.disabled = locked;
  }

  els.saveBtn.disabled = locked || !state.formDirty;
  els.runBtn.disabled = locked;
  els.startBtn.disabled = locked;
  els.stopBtn.disabled = !locked;
  updateCustomPresetControls();
  renderAllRuleLists();
}

async function getJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data;
}

async function postJson(url, body = {}) {
  return getJson(url, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

function renderAllRuleLists() {
  for (const category of RULE_CATEGORIES) {
    renderRuleList(category.key);
  }
}

function scheduleDiscoveryRefresh() {
  window.clearTimeout(state.discoveryTimer);
  state.discoveryTimer = window.setTimeout(() => {
    refreshDiscovery().catch(() => {
      state.discovery = emptyRules();
      renderAllRuleLists();
    });
  }, 250);
}

async function refreshDiscovery() {
  const projectRoot = els.projectRoot.value.trim();
  if (!projectRoot) {
    state.discovery = emptyRules();
    renderAllRuleLists();
    return;
  }

  const query = new URLSearchParams({ project_root: projectRoot });
  const payload = await getJson(`/api/discovery?${query.toString()}`);
  state.discovery = cloneRules(payload.candidates || {});
  renderAllRuleLists();
}

function renderState(payload) {
  const watcher = payload.watcher || {};
  const result = payload.last_result || {};
  state.watcherRunning = Boolean(watcher.running);
  els.versionLabel.textContent = payload.version ? `v${payload.version}` : "";
  els.watcherState.textContent = state.watcherRunning ? "Running" : "Stopped";
  els.lastRun.textContent = watcher.last_run_at || "Never";
  els.lastChange.textContent = watcher.last_change_at || "Never";
  els.mergedCount.textContent = result.files_merged || 0;
  els.structurePath.textContent = result.structure_path || "-";
  els.mergedPath.textContent = result.merged_path || "-";
  updateControls();
}

async function refreshState(loadForm = false) {
  const payload = await getJson("/api/state");
  state.presets = payload.presets || { project_types: [], presets: {} };
  if (loadForm) {
    writeConfigToForm(payload.config || {});
  }
  renderState(payload);
}

function appendLogs(logs) {
  if (!logs.length) {
    return;
  }

  for (const item of logs) {
    lastLogId = Math.max(lastLogId, Number(item.id));
    const line = `[${item.time}] ${String(item.level).toUpperCase()} ${item.message}`;
    els.terminal.textContent += `${line}\n`;
  }
  els.terminal.scrollTop = els.terminal.scrollHeight;
}

async function pollLogs() {
  try {
    const data = await getJson(`/api/logs?after=${lastLogId}`);
    appendLogs(data.logs || []);
  } catch (error) {
    appendLogs([{ id: lastLogId + 1, time: "--:--:--", level: "error", message: error.message }]);
  }
}

async function saveSettings() {
  if (!validateRuleLists()) {
    return false;
  }
  els.saveState.textContent = "Saving...";
  const data = await postJson("/api/config", readConfigFromForm());
  writeConfigToForm(data.config);
  await refreshState();
  return true;
}

async function runOnce() {
  if (!(await saveSettings())) {
    return;
  }
  els.runBtn.disabled = true;
  try {
    await postJson("/api/run");
    await refreshState();
  } finally {
    els.runBtn.disabled = false;
  }
}

async function chooseProject() {
  const data = await postJson("/api/dialog/project");
  if (data.path) {
    els.projectRoot.value = data.path;
    scheduleDiscoveryRefresh();
    markDirty();
  }
}

async function chooseConversation() {
  const data = await postJson("/api/dialog/conversation");
  if (data.path) {
    els.conversationPath.value = data.path;
    markDirty();
  }
}

function wireEvents() {
  for (const button of els.tabButtons) {
    button.addEventListener("click", () => switchTab(button.dataset.tab || "settings"));
  }

  const dirtyInputs = [
    els.projectRoot,
    els.outputDir,
    els.maxFileSizeKb,
    els.pollInterval,
    els.debounceSeconds,
    els.syncLmstudio,
    els.conversationPath,
    els.backupConversation,
    els.useGitnexus,
  ];
  for (const element of dirtyInputs) {
    element.addEventListener("input", markDirty);
    element.addEventListener("change", markDirty);
  }
  els.projectRoot.addEventListener("input", scheduleDiscoveryRefresh);
  els.projectRoot.addEventListener("change", scheduleDiscoveryRefresh);

  els.projectType.addEventListener("change", handleProjectTypeChanged);
  els.customPresetName.addEventListener("input", handleCustomPresetNameChanged);
  els.newCustomPresetBtn.addEventListener("click", createCustomPreset);
  els.deleteCustomPresetBtn.addEventListener("click", deleteCustomPreset);
  els.saveBtn.addEventListener("click", () => saveSettings().catch((error) => alert(error.message)));
  els.runBtn.addEventListener("click", () => runOnce().catch((error) => alert(error.message)));
  els.startBtn.addEventListener("click", async () => {
    if (await saveSettings()) {
      await postJson("/api/watch/start");
      await refreshState();
    }
  });
  els.stopBtn.addEventListener("click", async () => {
    await postJson("/api/watch/stop");
    await refreshState();
  });
  els.refreshBtn.addEventListener("click", () => refreshState(false).catch((error) => alert(error.message)));
  els.clearLogsBtn.addEventListener("click", () => {
    els.terminal.textContent = "";
  });
  els.shutdownBtn.addEventListener("click", async () => {
    await postJson("/api/shutdown");
    appendLogs([{ id: lastLogId + 1, time: "--:--:--", level: "info", message: "Application is shutting down." }]);
  });
  els.browseProjectBtn.addEventListener("click", () => chooseProject().catch((error) => alert(error.message)));
  els.browseConversationBtn.addEventListener("click", () => chooseConversation().catch((error) => alert(error.message)));
}

renderRuleCards();
switchTab("settings");
wireEvents();
refreshState(true).catch((error) => appendLogs([{ id: 1, time: "--:--:--", level: "error", message: error.message }]));
pollLogs();
setInterval(() => refreshState(false).catch(() => {}), 2000);
setInterval(pollLogs, 1000);
