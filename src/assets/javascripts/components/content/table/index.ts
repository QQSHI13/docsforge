import { Observable, of } from "rxjs"

import { renderTable } from "~/templates"
import { h } from "~/utilities"

import { Component } from "../../_"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Data table
 */
export interface DataTable {}

/* ----------------------------------------------------------------------------
 * Data
 * ------------------------------------------------------------------------- */

/**
 * Sentinel for replacement
 */
const sentinel = h("table")

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Mount data table
 *
 * This function wraps a data table in another scrollable container, so it can
 * be smoothly scrolled on smaller screen sizes and won't break the layout.
 *
 * @param el - Data table element
 *
 * @returns Data table component observable
 */
export function mountDataTable(
  el: HTMLElement
): Observable<Component<DataTable>> {
  el.replaceWith(sentinel)
  sentinel.replaceWith(renderTable(el))

  /* Create and return component */
  return of({ ref: el })
}
