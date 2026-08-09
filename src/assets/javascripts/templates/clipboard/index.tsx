import { translation } from "~/_"
import { h } from "~/utilities"

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Render a 'copy-to-clipboard' button
 *
 * @param id - Unique identifier
 *
 * @returns Element
 */
export function renderClipboardButton(id: string): HTMLElement {
  return (
    <button
      class="md-code__button"
      title={translation("clipboard.copy")}
      data-clipboard-target={`#${id} > code`}
      data-md-type="copy"
    ></button>
  )
}

export function renderSelectionButton(): HTMLElement {
  return (
    <button
      class="md-code__button"
      title="Toggle line selection"
      data-md-type="select"
    ></button>
  )
}

export function renderCodeBlockNavigation() {
  return (
    <nav class="md-code__nav"></nav>
  )
}
