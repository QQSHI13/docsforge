import {
  EMPTY,
  Observable,
  filter,
  fromEvent,
  map,
  merge,
  share,
  startWith,
  switchMap
} from "rxjs"

import { getActiveElement } from "../element"
import { getToggle } from "../toggle"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Keyboard mode
 */
export type KeyboardMode =
  | "global"                           /* Global */
  | "search"                           /* Search is open */

/* ------------------------------------------------------------------------- */

/**
 * Keyboard
 */
export interface Keyboard {
  mode: KeyboardMode                   /* Keyboard mode */
  type: string                         /* Key type */
  claim(): void                        /* Key claim */
}

/* ----------------------------------------------------------------------------
 * Helper functions
 * ------------------------------------------------------------------------- */

/**
 * Check whether an element may receive keyboard input
 *
 * @param el - Element
 * @param type - Key type
 *
 * @returns Test result
 */
function isSusceptibleToKeyboard(
  el: HTMLElement, type: string
): boolean {
  switch (el.constructor) {

    /* Input elements */
    case HTMLInputElement:
      /* @ts-expect-error - omit unnecessary type cast */
      if (el.type === "radio")
        return /^Arrow/.test(type)
      else
        return true

    /* Select element and textarea */
    case HTMLSelectElement:
    case HTMLTextAreaElement:
      return true

    /* Everything else */
    default:
      return el.isContentEditable
  }
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Watch composition events
 *
 * @returns Composition observable
 */
export function watchComposition(): Observable<boolean> {
  return merge(
    fromEvent(window, "compositionstart").pipe(map(() => true)),
    fromEvent(window, "compositionend").pipe(map(() => false))
  )
    .pipe(
      startWith(false)
    )
}

/**
 * Watch keyboard
 *
 * @returns Keyboard observable
 */
export function watchKeyboard(): Observable<Keyboard> {
  const keyboard$ = fromEvent<KeyboardEvent>(window, "keydown")
    .pipe(
      filter(ev => !(ev.metaKey || ev.ctrlKey)),
      map(ev => ({
        mode: getToggle("search") ? "search" : "global",
        type: ev.key,
        claim() {
          ev.preventDefault()
          ev.stopPropagation()
        }
      } as Keyboard)),
      filter(({ mode, type }) => {
        if (mode === "global") {
          const active = getActiveElement()
          if (typeof active !== "undefined")
            return !isSusceptibleToKeyboard(active, type)
        }
        return true
      }),
      share()
    )

  /* Don't emit during composition events - see https://bit.ly/3te3Wl8 */
  return watchComposition()
    .pipe(
      switchMap(active => !active ? keyboard$ : EMPTY)
    )
}
