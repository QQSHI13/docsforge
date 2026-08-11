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

  function applyTheme(scheme, primary, accent) {
    // Persist via the documented DocsForge API — applies the colors AND saves
    // them, including combinations that have no matching header radio.
    if (window.docsforge && window.docsforge.setPalette) {
      window.docsforge.setPalette({ scheme: scheme, primary: primary, accent: accent });
    } else {
      document.body.setAttribute("data-md-color-scheme", scheme);
      document.body.setAttribute("data-md-color-primary", primary);
      document.body.setAttribute("data-md-color-accent", accent);
    }
    // Sync the header radio and button highlight state.
    document.querySelectorAll('input[name="__palette"]').forEach(function(input) {
      input.checked = (input.getAttribute("data-md-color-scheme") === scheme);
    });
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

  document.querySelectorAll('.theme-buttons button[data-theme]').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var parts = btn.getAttribute('data-theme').split(':');
      applyTheme(parts[0], parts[1], parts[2]);
    });
  });

  // Sync the highlight on any external theme change (header toggle, other scripts).
  var observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
      if (mutation.type === 'attributes' && mutation.attributeName === 'data-md-color-scheme') {
        updateButtonStates();
      }
    });
  });
  observer.observe(document.body, { attributes: true, attributeFilter: ['data-md-color-scheme'] });

  // The saved theme is restored by docsforge itself; just sync the highlight.
  updateButtonStates();
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

The inline switcher calls the documented **`window.docsforge.setPalette({ scheme, primary, accent })`** API, which applies the colors to the page and persists them using the same scoped `localStorage` key as the header toggle. That means:

- Your choice **persists across page loads** — including combinations like red/green that have no header toggle
- It **syncs with the header toggle** automatically
- It works with **instant navigation** without page reloads

The key is scoped to the site's base URL, so it won't leak to other sites.

---

Try switching themes above, then navigate to other pages — your choice sticks!
