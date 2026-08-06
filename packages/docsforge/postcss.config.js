module.exports = {
  plugins: {
    autoprefixer: {},
    // Resolves the SCSS `svg-load("set/name.svg")` calls (vendored from
    // mkdocs-material) into `url('data:image/svg+xml;utf8,...')` so CSS
    // mask-image icons (source facts, clipboard, tasklist, details, tabbed,
    // search) actually render. Icons live under src/templates/.icons.
    "postcss-inline-svg": {
      paths: ["./src/templates/.icons"],
    },
  },
};
