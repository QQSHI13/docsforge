import {
  Observable,
  map,
  of,
  shareReplay,
  tap
} from "rxjs"

import { watchScript } from "~/browser"
import { h } from "~/utilities"

import { Component } from "../../_"

import themeCSS from "./index.css"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Mermaid diagram
 */
export interface Mermaid {}

/* ----------------------------------------------------------------------------
 * Data
 * ------------------------------------------------------------------------- */

/**
 * Mermaid instance observable
 */
let mermaid$: Observable<void>

/**
 * Global sequence number for diagrams
 */
let sequence = 0

/* ----------------------------------------------------------------------------
 * Helper functions
 * ------------------------------------------------------------------------- */

/**
 * Fetch Mermaid script
 *
 * @returns Mermaid scripts observable
 */
function fetchScripts(): Observable<void> {
  return typeof mermaid === "undefined" || mermaid instanceof Element
    ? watchScript("https://unpkg.com/mermaid@11/dist/mermaid.min.js")
    : of(undefined)
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Mount Mermaid diagram
 *
 * @param el - Code block element
 *
 * @returns Mermaid diagram component observable
 */
export function mountMermaid(
  el: HTMLElement
): Observable<Component<Mermaid>> {
  el.classList.remove("mermaid") // Hack: mitigate https://bit.ly/3CiN6Du
  mermaid$ ||= fetchScripts()
    .pipe(
      tap(() => mermaid.initialize({
        startOnLoad: false,
        themeCSS,
        sequence: {
          actorFontSize: "16px", // Hack: mitigate https://bit.ly/3y0NEi3
          messageFontSize: "16px",
          noteFontSize: "16px"
        }
      })),
      map(() => undefined),
      shareReplay(1)
    )

  /* Render diagram */
  mermaid$.subscribe(async () => {
    el.classList.add("mermaid") // Hack: mitigate https://bit.ly/3CiN6Du
    const id = `__mermaid_${sequence++}`

    /* Create host element to replace code block */
    const host = h("div", { class: "mermaid" })
    const text = el.textContent

    /* Render and inject diagram */
    const { svg, fn } = await mermaid.render(id, text)

    /* Create a shadow root and inject diagram */
    const shadow = host.attachShadow({ mode: "closed" })
    shadow.innerHTML = svg

    /* Replace code block with diagram and bind functions */
    el.replaceWith(host)
    fn?.(shadow)
  })

  /* Create and return component */
  return mermaid$
    .pipe(
      map(() => ({ ref: el }))
    )
}
