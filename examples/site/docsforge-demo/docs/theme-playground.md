# Theme Playground

Welcome to the interactive theme testing ground! Switch between different color schemes and see how DocsForge looks.

## Inline Theme Changers

Click any button below to instantly change the site's color theme.

<div class="theme-buttons">
  <button class="md-button" data-theme="default:indigo:indigo">☀️ Light — Indigo</button>
  <button class="md-button" data-theme="slate:indigo:indigo">🌙 Dark — Indigo</button>
  <button class="md-button" data-theme="default:red:red">🔴 Light — Red</button>
  <button class="md-button" data-theme="slate:red:red">🔴 Dark — Red</button>
  <button class="md-button" data-theme="default:green:green">🟢 Light — Green</button>
  <button class="md-button" data-theme="slate:teal:teal">🔵 Dark — Teal</button>
  <button class="md-button" data-theme="default:orange:orange">🟠 Light — Orange</button>
  <button class="md-button" data-theme="slate:purple:purple">🟣 Dark — Purple</button>
</div>

<script>
(function() {
  // Prevent duplicate initialization on instant navigation
  if (window.__themePlaygroundInit) return;
  window.__themePlaygroundInit = true;

  function getMaterialScope() {
    // Use Material's __md_scope when available (site-wide), fallback to per-page
    if (typeof __md_scope !== 'undefined') return __md_scope;
    return new URL(".", location);
  }

  function getPaletteKey() {
    return getMaterialScope().pathname + ".__palette";
  }

  function getSavedTheme() {
    var key = getPaletteKey();
    // Try Material's scoped key
    try {
      var mat = JSON.parse(localStorage.getItem(key));
      if (mat && mat.color) return mat.color;
    } catch(e) {}
    // Fall back to fixed backup key
    try {
      var bak = JSON.parse(localStorage.getItem("docsforge-theme"));
      if (bak) return bak;
    } catch(e) {}
    return null;
  }

  function saveTheme(scheme, primary, accent) {
    var color = {
      media: "(prefers-color-scheme: " + (scheme === 'slate' ? 'dark' : 'light') + ")",
      scheme: scheme,
      primary: primary,
      accent: accent
    };
    // Save to Material's scoped key
    var key = getPaletteKey();
    var palette = {};
    try { palette = JSON.parse(localStorage.getItem(key)) || {}; } catch(e) {}
    palette.color = color;
    try { localStorage.setItem(key, JSON.stringify(palette)); } catch(e) {}
    // Backup to fixed key for cross-page safety
    try { localStorage.setItem("docsforge-theme", JSON.stringify(color)); } catch(e) {}
  }

  function applyTheme(scheme, primary, accent, skipSave) {
    document.body.setAttribute("data-md-color-scheme", scheme);
    document.body.setAttribute("data-md-color-primary", primary);
    document.body.setAttribute("data-md-color-accent", accent);

    // Sync radio inputs
    document.querySelectorAll('input[name="__palette"]').forEach(function(input) {
      input.checked = (input.getAttribute("data-md-color-scheme") === scheme);
    });

    // Sync palette label visibility
    document.querySelectorAll('[data-md-component="palette"] label').forEach(function(label) {
      var target = document.getElementById(label.getAttribute("for"));
      if (target) label.hidden = (target.getAttribute("data-md-color-scheme") === scheme);
    });

    if (!skipSave) saveTheme(scheme, primary, accent);
    updateButtonStates();
  }

  function updateButtonStates() {
    var scheme = document.body.getAttribute('data-md-color-scheme') || 'default';
    var primary = document.body.getAttribute('data-md-color-primary') || 'indigo';
    document.querySelectorAll('.theme-buttons button[data-theme]').forEach(function(btn) {
      var parts = btn.getAttribute('data-theme').split(':');
      var isActive = parts[0] === scheme && parts[1] === primary;
      btn.classList.toggle('md-button--primary', isActive);
    });
  }

  // Button clicks
  document.querySelectorAll('.theme-buttons button[data-theme]').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var parts = btn.getAttribute('data-theme').split(':');
      applyTheme(parts[0], parts[1], parts[2]);
    });
  });

  // Listen for built-in palette toggle changes
  document.querySelectorAll('input[name="__palette"]').forEach(function(radio) {
    radio.addEventListener('change', function() {
      if (radio.checked) {
        applyTheme(
          radio.getAttribute('data-md-color-scheme'),
          radio.getAttribute('data-md-color-primary'),
          radio.getAttribute('data-md-color-accent')
        );
      }
    });
  });

  // Watch body attribute changes (from built-in toggle or other scripts)
  var observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
      if (mutation.type === 'attributes' && mutation.attributeName === 'data-md-color-scheme') {
        updateButtonStates();
      }
    });
  });
  observer.observe(document.body, { attributes: true, attributeFilter: ['data-md-color-scheme'] });

  // Initialize: apply saved theme on load, or just sync buttons
  var saved = getSavedTheme();
  if (saved) {
    applyTheme(saved.scheme, saved.primary, saved.accent, true);
  } else {
    updateButtonStates();
  }
})();
</script>

<style>
.theme-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 1rem 0;
}
.theme-buttons .md-button {
  margin: 0;
}
</style>

## Color Reference

| Scheme | Background | Text | Best For |
|--------|-----------|------|----------|
| `default` | White | Dark | Daytime reading |
| `slate` | Dark gray | Light | Low-light environments |

| Primary | Accent | Vibe |
|-----------|--------|------|
| `indigo` | `indigo` | Professional, default |
| `red` | `red` | Energetic, urgent |
| `green` | `green` | Natural, calm |
| `teal` | `teal` | Modern, fresh |
| `orange` | `orange` | Warm, creative |
| `purple` | `purple` | Playful, creative |

## How It Works

The inline theme switcher uses the same `localStorage` key that Material's built-in palette toggle uses. This means:

- Your choice **persists across page loads**
- It **syncs with the header toggle** automatically
- It works with **instant navigation** without page reloads

The key is scoped to the site's base URL, so it won't leak to other sites.

---

Try switching themes above, then navigate to other pages — your choice sticks!
