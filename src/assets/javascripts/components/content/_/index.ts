import { Observable, merge } from "rxjs"

import { feature } from "~/_"
import { Viewport, getElements } from "~/browser"
import { Sitemap } from "~/integrations"
import { renderTooltip2 } from "~/templates"

import { Component } from "../../_"
import {
  Tooltip,
  mountInlineTooltip2,
  mountTooltip2
} from "../../tooltip2"
import {
  Annotation,
  mountAnnotationBlock
} from "../annotation"
import {
  CodeBlock,
  mountCodeBlock
} from "../code"
import {
  Details,
  mountDetails
} from "../details"
import {
  Link,
  mountLink
} from "../link"
import {
  Mermaid,
  mountMermaid
} from "../mermaid"
import {
  DataTable,
  mountDataTable
} from "../table"
import {
  ContentTabs,
  mountContentTabs
} from "../tabs"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Content
 */
export type Content =
  | Annotation
  | CodeBlock
  | ContentTabs
  | DataTable
  | Details
  | Link
  | Mermaid
  | Tooltip

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Dependencies
 */
interface Dependencies {
  sitemap$: Observable<Sitemap>        // Sitemap observable
  viewport$: Observable<Viewport>      // Viewport observable
  target$: Observable<HTMLElement>     // Location target observable
  print$: Observable<boolean>          // Media print observable
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Mount content
 *
 * This function mounts all components that are found in the content of the
 * actual article, including code blocks, data tables and details.
 *
 * @param el - Content element
 * @param dependencies - Dependencies
 *
 * @returns Content component observable
 */
export function mountContent(
  el: HTMLElement, dependencies: Dependencies
): Observable<Component<Content>> {
  const { viewport$, target$, print$ } = dependencies
  return merge(

    // Annotations
    ...getElements(".annotate:not(.highlight)", el)
      .map(child => mountAnnotationBlock(child, { target$, print$ })),

    // Code blocks
    ...getElements("pre:not(.mermaid) > code", el)
      .map(child => mountCodeBlock(child, { target$, print$ })),

    // Links
    ...getElements("a", el)
      .map(child => mountLink(child, dependencies)),

    // Mermaid diagrams
    ...getElements("pre.mermaid", el)
      .map(child => mountMermaid(child)),

    // Data tables
    ...getElements("table:not([class])", el)
      .map(child => mountDataTable(child)),

    // Details
    ...getElements("details", el)
      .map(child => mountDetails(child, { target$, print$ })),

    // Content tabs
    ...getElements("[data-tabs]", el)
      .map(child => mountContentTabs(child, { viewport$, target$ })),

    // Tooltips
    ...getElements("[title]:not([data-preview])", el)
      .filter(() => feature("content.tooltips"))
      .map(child => mountInlineTooltip2(child, { viewport$ })),

    // Footnotes
    ...getElements(".footnote-ref", el)
      .filter(() => feature("content.footnote.tooltips"))
      // move into specific function! mountTooltip is a low level primitive...
      .map(child => mountTooltip2(child, {
        content$: new Observable<HTMLElement>(observer => {
          // @ts-ignore
          const hash = new URL(child.href).hash.slice(1)
          const arr = Array.from(document.getElementById(hash)!
            // @ts-ignore
            // eslint-disable-next-line
            .cloneNode(true).children) as any
          const node = renderTooltip2(...arr)
          observer.next(node)

          // Append tooltip and remove on unsubscription
          document.body.append(node)
          return () => node.remove()
        }),
        viewport$
      }))
  )
}
