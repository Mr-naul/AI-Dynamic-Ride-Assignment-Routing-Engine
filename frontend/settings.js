// =========================
// settings.js (UPDATED)
// =========================

// CONFIG
const API_BASE = "http://127.0.0.1:5000";
const DEFAULTS_URL = `${API_BASE}/api/settings/defaults`;
const SAVE_URL = `${API_BASE}/api/settings`; // Save settings endpoint

// Small helpers
function $(id) {
  return document.getElementById(id);
}

function setValue(id, val) {
  const el = $(id);
  if (!el) return; // don't crash if field not present
  el.value = val ?? "";
}

function setChecked(id, val) {
  const el = $(id);
  if (!el) return;
  el.checked = Boolean(val);
}

function parseNumber(raw, asInt = false) {
  if (raw === null || raw === undefined) return undefined;
  const s = String(raw).trim();
  if (s === "") return undefined;
  const n = asInt ? parseInt(s, 10) : parseFloat(s);
  return Number.isFinite(n) ? n : undefined;
}

function showStatus(msg, type = "info") {
  let box = $("status-box");
  if (!box) {
    box = document.createElement("div");
    box.id = "status-box";
    box.style.margin = "15px 0";
    box.style.padding = "12px 14px";
    box.style.borderRadius = "8px";
    box.style.fontSize = "14px";
    box.style.border = "1px solid #ccc";
    const container = document.querySelector("#settings-form") || document.body;
    container.prepend(box);
  }

  box.textContent = msg;

  if (type === "success") {
    box.style.background = "#d4edda";
    box.style.borderColor = "#c3e6cb";
  } else if (type === "error") {
    box.style.background = "#f8d7da";
    box.style.borderColor = "#f5c6cb";
  } else {
    box.style.background = "#eef2ff";
    box.style.borderColor = "#c7d2fe";
  }
}

// Field mapping (defaults JSON -> form IDs)
const FIELD_BINDINGS = [
  { key: "avg_speed_kmh", id: "avg_speed_kmh", type: "number" },
  { key: "enforce_schedule_clash", id: "enforce_schedule_clash", type: "checkbox" },
  { key: "morning_early_min", id: "morning_early_min", type: "int" },
  { key: "morning_early_ok_min", id: "morning_early_ok_min", type: "int" },
  { key: "morning_late_min", id: "morning_late_min", type: "int" },
  { key: "morning_late_ok_min", id: "morning_late_ok_min", type: "int" },
  { key: "evening_early_min", id: "evening_early_min", type: "int" },
  { key: "evening_early_ok_min", id: "evening_early_ok_min", type: "int" },
  { key: "evening_late_min", id: "evening_late_min", type: "int" },
  { key: "evening_late_ok_min", id: "evening_late_ok_min", type: "int" },
  { key: "max_pickup_km", id: "max_pickup_km", type: "number" },
  { key: "w_deadhead", id: "w_deadhead", type: "number" },
  { key: "w_seat", id: "w_seat", type: "number" },
  { key: "w_status", id: "w_status", type: "number" },
  { key: "p1_emit_outsource", id: "p1_emit_outsource", type: "checkbox" },
  { key: "p1_top_k", id: "p1_top_k", type: "int" },
  { key: "p2_max_detour_km", id: "p2_max_detour_km", type: "number" },
  { key: "p2_max_detour_ratio", id: "p2_max_detour_ratio", type: "number" },
  { key: "p2_max_shift_min", id: "p2_max_shift_min", type: "int" },
  { key: "p2_top_k", id: "p2_top_k", type: "int" },
  { key: "p2_w_detour", id: "p2_w_detour", type: "number" },
  { key: "p2_w_time", id: "p2_w_time", type: "number" },
  { key: "p3_enabled", id: "p3_enabled", type: "checkbox" },
  { key: "p3_top_k", id: "p3_top_k", type: "int" },
  { key: "p3_min_improvement", id: "p3_min_improvement", type: "number" },
  { key: "p3_max_pickup_km", id: "p3_max_pickup_km", type: "number" },
  { key: "p3_min_fit", id: "p3_min_fit", type: "number" },
  { key: "p3_swap_enabled", id: "p3_swap_enabled", type: "checkbox" },
  { key: "p3_swap_needed_fit_below", id: "p3_swap_needed_fit_below", type: "number" },
  { key: "p3_swap_penalty", id: "p3_swap_penalty", type: "number" },
  { key: "p3_swap_max_reposition_km", id: "p3_swap_max_reposition_km", type: "number" },
  { key: "p3_swap_prefix", id: "p3_swap_prefix", type: "text" },
  { key: "p4_enabled", id: "p4_enabled", type: "checkbox" },
  { key: "p4_emit_outsource", id: "p4_emit_outsource", type: "checkbox" },
  { key: "p4_merge_time_gap_min", id: "p4_merge_time_gap_min", type: "int" },
  { key: "p4_merge_pickup_km", id: "p4_merge_pickup_km", type: "number" },
  { key: "p4_merge_dropoff_km", id: "p4_merge_dropoff_km", type: "number" },
  { key: "p4_max_driver_pickup_km", id: "p4_max_driver_pickup_km", type: "number" },
  { key: "p4_merge_outsource_when_no_driver", id: "p4_merge_outsource_when_no_driver", type: "checkbox" },
];

// Fetch current settings from backend and populate form
async function fetchDefaultsAndPopulate() {
  showStatus("Loading current/default settings from backend...", "info");

  try {
    const res = await fetch(DEFAULTS_URL, { method: "GET", mode: "cors" });

    if (!res.ok) {
      throw new Error(`Defaults fetch failed: ${res.status} ${res.statusText}`);
    }

    const data = await res.json();
    console.log("✅ /api/settings/defaults response:", data);

    if (!data || !data.defaults) {
      throw new Error("Defaults response missing 'defaults' object.");
    }

    const defaults = data.defaults;

    // Fill fields using mapping
    FIELD_BINDINGS.forEach(({ key, id, type }) => {
      const value = defaults[key];

      if (type === "checkbox") {
        setChecked(id, value);
      } else {
        setValue(id, value);
      }
    });

    showStatus("Settings loaded successfully.", "success");
  } catch (err) {
    console.error("❌ Error fetching defaults:", err);
    showStatus("Could not load settings. Open Console (F12) and check errors.", "error");
  }
}

// Collect form values -> flat payload
function collectSettingsPayload() {
  const payload = {};

  FIELD_BINDINGS.forEach(({ key, id, type }) => {
    const el = $(id);
    if (!el) return;

    if (type === "checkbox") {
      payload[key] = el.checked;
      return;
    }

    const raw = el.value;
    const asInt = type === "int";
    const num = parseNumber(raw, asInt);

    if (num !== undefined) payload[key] = num;
  });

  return payload;
}

// Save settings to backend
async function saveSettings() {
  const btn = $("save-settings-btn");
  if (btn) btn.disabled = true;

  const payload = collectSettingsPayload();
  console.log("⬆️ Sending settings payload:", payload);

  // Wrap the settings payload inside the "settings" key
  const jsonPayload = {
    settings: payload
  };

  showStatus("Saving settings to backend...", "info");

  try {
    const res = await fetch(SAVE_URL, {
      method: "POST",
      mode: "cors",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(jsonPayload), // Send the wrapped payload
    });

    if (res.status === 204) {
      showStatus("Settings saved successfully.", "success");
      return;
    }

    const text = await res.text();
    let data;
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = { raw: text };
    }

    console.log("✅ Save response:", res.status, data);

    if (!res.ok) {
      throw new Error(`Save failed: ${res.status} ${res.statusText}`);
    }

    showStatus("Settings saved successfully.", "success");
  } catch (err) {
    console.error("❌ Error saving settings:", err);
    showStatus(
      "Failed to save settings. Check Console (F12). Most common: SAVE_URL route mismatch.",
      "error"
    );
  } finally {
    if (btn) btn.disabled = false;
  }
}

// Wire up events
document.addEventListener("DOMContentLoaded", () => {
  // Load defaults/current settings into the form
  fetchDefaultsAndPopulate();

  // Handle form submit
  const form = document.querySelector("form#settings-form");
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      saveSettings();
    });
  } else {
    const btn = $("save-settings-btn");
    if (btn) {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        saveSettings();
      });
    }
  }
});
