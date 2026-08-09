import { h } from "~/utilities"

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Tabbed control type
 */
type TabbedControlType =
  | "prev"
  | "next"

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Render control for content tabs
 *
 * @param type - Control type
 *
 * @returns Element
 */
export function renderTabbedControl(
  type: TabbedControlType
): HTMLElement {
  const classes = `tabbed-control tabbed-control--${type}`
  return (
    <div class={classes} hidden>
      <button class="tabbed-button" tabIndex={-1} aria-hidden="true"></button>
    </div>
  )
}
