// Marp config for the presentation decks in this folder.
// Diagrams are pre-rendered SVG files in assets/ (rendered from .mmd mermaid
// sources with mermaid-cli), so no markdown-it plugins are needed — the decks
// export cleanly to HTML, PDF, and PPTX with a stock Marp CLI.

module.exports = {
  markdown: {
    html: true,
  },
};
