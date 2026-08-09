import { EMPTY, Observable, defer } from "rxjs"

import { Component } from "../../../_"
import { Annotation } from "../_"
import { mountAnnotationList } from "../list"

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Mount options
 */
interface MountOptions {
  target$: Observable<HTMLElement>     /* Location target observable */
  print$: Observable<boolean>          /* Media print observable */
}

/* ----------------------------------------------------------------------------
 * Helper functions
 * ------------------------------------------------------------------------- */

/**
 * Find list element directly following a block
 *
 * @param el - Annotation block element
 *
 * @returns List element or nothing
 */
function findList(el: HTMLElement): HTMLElement | undefined {
  if (el.nextElementSibling) {
    const sibling = el.nextElementSibling as HTMLElement
    if (sibling.tagName === "OL")
      return sibling

    /* Skip empty paragraphs - see https://bit.ly/3r4ZJ2O */
    else if (sibling.tagName === "P" && !sibling.children.length)
      return findList(sibling)
  }

  /* Everything else */
  return undefined
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Mount annotation block
 *
 * @param el - Annotation block element
 * @param options - Options
 *
 * @returns Annotation component observable
 */
export function mountAnnotationBlock(
  el: HTMLElement, options: MountOptions
): Observable<Component<Annotation>> {
  return defer(() => {
    const list = findList(el)
    return typeof list !== "undefined"
      ? mountAnnotationList(list, el, options)
      : EMPTY
  })
}
