import {
  Observable,
  ObservableInput,
  combineLatest,
  filter,
  map,
  startWith
} from "rxjs"

import { getLocation } from "~/browser"
import {
  SearchIndex,
  setupSearchHighlighter
} from "~/integrations"
import { h } from "~/utilities"

import { Component } from "../../_"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Search highlighting
 */
export interface SearchHighlight {
  nodes: Map<ChildNode, string>        /* Map of replacements */
}

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Mount options
 */
interface MountOptions {
  index$: ObservableInput<SearchIndex> /* Search index observable */
  location$: Observable<URL>           /* Location observable */
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Mount search highlighting
 *
 * @param el - Content element
 * @param options - Options
 *
 * @returns Search highlighting component observable
 */
export function mountSearchHiglight(
  el: HTMLElement, { index$, location$ }: MountOptions
): Observable<Component<SearchHighlight>> {
  return combineLatest([
    index$,
    location$
      .pipe(
        startWith(getLocation()),
        filter(url => !!url.searchParams.get("h"))
      )
  ])
    .pipe(
      map(([index, url]) => setupSearchHighlighter(index.config)(
        url.searchParams.get("h")!
      )),
      map(fn => {
        const nodes = new Map<ChildNode, string>()

        /* Traverse text nodes and collect matches */
        const it = document.createNodeIterator(el, NodeFilter.SHOW_TEXT)
        for (let node = it.nextNode(); node; node = it.nextNode()) {
          if (node.parentElement?.offsetHeight) {
            const original = node.textContent!
            const replaced = fn(original)
            if (replaced.length > original.length)
              nodes.set(node as ChildNode, replaced)
          }
        }

        /* Replace original nodes with matches */
        for (const [node, text] of nodes) {
          const { childNodes } = h("span", null, text)
          node.replaceWith(...Array.from(childNodes))
        }

        /* Return component */
        return { ref: el, nodes }
      })
    )
}
