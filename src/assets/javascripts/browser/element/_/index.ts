/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Retrieve all elements matching the query selector
 *
 * @template T - Element type
 *
 * @param selector - Query selector
 * @param node - Node of reference
 *
 * @returns Elements
 */
export function getElements<T extends keyof HTMLElementTagNameMap>(
  selector: T, node?: ParentNode
): HTMLElementTagNameMap[T][]

export function getElements<T extends HTMLElement>(
  selector: string, node?: ParentNode
): T[]

export function getElements<T extends HTMLElement>(
  selector: string, node: ParentNode = document
): T[] {
  return Array.from(node.querySelectorAll<T>(selector))
}

/**
 * Retrieve an element matching a query selector or throw a reference error
 *
 * Note that this function assumes that the element is present. If unsure if an
 * element is existent, use the `getOptionalElement` function instead.
 *
 * @template T - Element type
 *
 * @param selector - Query selector
 * @param node - Node of reference
 *
 * @returns Element
 */
export function getElement<T extends keyof HTMLElementTagNameMap>(
  selector: T, node?: ParentNode
): HTMLElementTagNameMap[T]

export function getElement<T extends HTMLElement>(
  selector: string, node?: ParentNode
): T

export function getElement<T extends HTMLElement>(
  selector: string, node: ParentNode = document
): T {
  const el = getOptionalElement<T>(selector, node)
  if (typeof el === "undefined")
    throw new ReferenceError(
      `Missing element: expected "${selector}" to be present`
    )

  /* Return element */
  return el
}

/* ------------------------------------------------------------------------- */

/**
 * Retrieve an optional element matching the query selector
 *
 * @template T - Element type
 *
 * @param selector - Query selector
 * @param node - Node of reference
 *
 * @returns Element or nothing
 */
export function getOptionalElement<T extends keyof HTMLElementTagNameMap>(
  selector: T, node?: ParentNode
): HTMLElementTagNameMap[T] | undefined

export function getOptionalElement<T extends HTMLElement>(
  selector: string, node?: ParentNode
): T | undefined

export function getOptionalElement<T extends HTMLElement>(
  selector: string, node: ParentNode = document
): T | undefined {
  return node.querySelector<T>(selector) || undefined
}

/**
 * Retrieve the currently active element
 *
 * @returns Element or nothing
 */
export function getActiveElement(): HTMLElement | undefined {
  return (
    document.activeElement?.shadowRoot?.activeElement as HTMLElement ??
    document.activeElement as HTMLElement ??
    undefined
  )
}
