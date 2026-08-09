import { h } from "~/utilities"

import { renderTooltip } from "../tooltip"

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Render an annotation
 *
 * @param id - Annotation identifier
 * @param prefix - Tooltip identifier prefix
 *
 * @returns Element
 */
export function renderAnnotation(
  id: string | number, prefix?: string
): HTMLElement {
  prefix = prefix ? `${prefix}_annotation_${id}` : undefined

  /* Render tooltip with anchor, if given */
  if (prefix) {
    const anchor = prefix ? `#${prefix}` : undefined
    return (
      <aside class="md-annotation" tabIndex={0}>
        {renderTooltip(prefix)}
        <a href={anchor} class="md-annotation__index" tabIndex={-1}>
          <span data-md-annotation-id={id}></span>
        </a>
      </aside>
    )
  } else {
    return (
      <aside class="md-annotation" tabIndex={0}>
        {renderTooltip(prefix)}
        <span class="md-annotation__index" tabIndex={-1}>
          <span data-md-annotation-id={id}></span>
        </span>
      </aside>
    )
  }
}
