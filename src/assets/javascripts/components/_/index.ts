import { getElement, getElements } from "~/browser"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Component type
 */
export type ComponentType =
  | "announce"                         /* Announcement bar */
  | "container"                        /* Container */
  | "consent"                          /* Consent */
  | "content"                          /* Content */
  | "dialog"                           /* Dialog */
  | "header"                           /* Header */
  | "header-title"                     /* Header title */
  | "header-topic"                     /* Header topic */
  | "main"                             /* Main area */
  | "outdated"                         /* Version warning */
  | "palette"                          /* Color palette */
  | "progress"                         /* Progress indicator */
  | "search"                           /* Search */
  | "search-query"                     /* Search input */
  | "search-result"                    /* Search results */
  | "search-share"                     /* Search sharing */
  | "search-suggest"                   /* Search suggestions */
  | "sidebar"                          /* Sidebar */
  | "skip"                             /* Skip link */
  | "source"                           /* Repository information */
  | "tabs"                             /* Navigation tabs */
  | "toc"                              /* Table of contents */
  | "top"                              /* Back-to-top button */

/**
 * Component
 *
 * @template T - Component type
 * @template U - Reference type
 */
export type Component<
  T extends {} = {},
  U extends HTMLElement = HTMLElement
> =
  T & {
    ref: U                             /* Component reference */
  }

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Component type map
 */
interface ComponentTypeMap {
  "announce": HTMLElement              /* Announcement bar */
  "container": HTMLElement             /* Container */
  "consent": HTMLElement               /* Consent */
  "content": HTMLElement               /* Content */
  "dialog": HTMLElement                /* Dialog */
  "header": HTMLElement                /* Header */
  "header-title": HTMLElement          /* Header title */
  "header-topic": HTMLElement          /* Header topic */
  "main": HTMLElement                  /* Main area */
  "outdated": HTMLElement              /* Version warning */
  "palette": HTMLElement               /* Color palette */
  "progress": HTMLElement              /* Progress indicator */
  "search": HTMLElement                /* Search */
  "search-query": HTMLInputElement     /* Search input */
  "search-result": HTMLElement         /* Search results */
  "search-share": HTMLAnchorElement    /* Search sharing */
  "search-suggest": HTMLElement        /* Search suggestions */
  "sidebar": HTMLElement               /* Sidebar */
  "skip": HTMLAnchorElement            /* Skip link */
  "source": HTMLAnchorElement          /* Repository information */
  "tabs": HTMLElement                  /* Navigation tabs */
  "toc": HTMLElement                   /* Table of contents */
  "top": HTMLAnchorElement             /* Back-to-top button */
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Retrieve the element for a given component or throw a reference error
 *
 * @template T - Component type
 *
 * @param type - Component type
 * @param node - Node of reference
 *
 * @returns Element
 */
export function getComponentElement<T extends ComponentType>(
  type: T, node: ParentNode = document
): ComponentTypeMap[T] {
  return getElement(`[data-md-component=${type}]`, node)
}

/**
 * Retrieve all elements for a given component
 *
 * @template T - Component type
 *
 * @param type - Component type
 * @param node - Node of reference
 *
 * @returns Elements
 */
export function getComponentElements<T extends ComponentType>(
  type: T, node: ParentNode = document
): ComponentTypeMap[T][] {
  return getElements(`[data-md-component=${type}]`, node)
}
