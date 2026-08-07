// SVGO v4 config. removeViewBox is no longer part of preset-default (it is
// disabled by default to preserve scalability), so no override is needed;
// removeDimensions stays enabled to drop explicit width/height attributes.
module.exports = {
  plugins: [
    {
      name: "preset-default",
    },
    "removeDimensions",
  ],
};
