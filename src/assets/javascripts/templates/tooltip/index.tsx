import { ComponentChild } from "preact"

import { h } from "~/utilities"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Tooltip style
 */
export type TooltipStyle =
  | "inline"

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Render a tooltip
 *
 * @param id - Tooltip identifier
 * @param style - Tooltip style
 *
 * @returns Element
 */
export function renderTooltip(
  id?: string, style?: TooltipStyle
): HTMLElement {
  if (style === "inline") { // @todo refactor control flow
    return (
      <div class="md-tooltip md-tooltip--inline" id={id} role="tooltip">
        <div class="md-tooltip__inner md-typeset"></div>
      </div>
    )
  } else {
    return (
      <div class="md-tooltip" id={id} role="tooltip">
        <div class="md-tooltip__inner md-typeset"></div>
      </div>
    )
  }
}

/**
 * Render a tooltip
 *
 * @param children - Child nodes
 *
 * @returns Element
 */
export function renderTooltip2(
  ...children: ComponentChild[]
): HTMLElement {
  return (
    <div class="md-tooltip2" role="dialog">
      <div class="md-tooltip2__inner md-typeset">
        {children}
      </div>
    </div>
  )
}

// @todo: rename
export function renderInlineTooltip2(
  ...children: ComponentChild[]
): HTMLElement {
  return (
    <div class="md-tooltip2" role="tooltip">
      <div class="md-tooltip2__inner md-typeset">
        {children}
      </div>
    </div>
  )
}
