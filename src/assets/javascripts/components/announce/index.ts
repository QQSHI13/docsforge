import {
  EMPTY,
  Observable,
  Subject,
  defer,
  finalize,
  fromEvent,
  map,
  tap
} from "rxjs"

import { feature } from "~/_"
import { getElement } from "~/browser"

import { Component } from "../_"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Announcement bar
 */
export interface Announce {
  hash: number                        /* Content hash */
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Watch announcement bar
 *
 * @param el - Announcement bar element
 *
 * @returns Announcement bar observable
 */
export function watchAnnounce(
  el: HTMLElement
): Observable<Announce> {
  const button = getElement(".md-typeset > :first-child", el)
  return fromEvent(button, "click", { once: true })
    .pipe(
      map(() => getElement(".md-typeset", el)),
      map(content => ({ hash: __md_hash(content.innerHTML) }))
    )
}

/**
 * Mount announcement bar
 *
 * @param el - Announcement bar element
 *
 * @returns Announcement bar component observable
 */
export function mountAnnounce(
  el: HTMLElement
): Observable<Component<Announce>> {
  if (!feature("announce.dismiss") || !el.childElementCount)
    return EMPTY

  /* Support instant navigation - see https://t.ly/3FTme */
  if (!el.hidden) {
    const content = getElement(".md-typeset", el)
    if (__md_hash(content.innerHTML) === __md_get("__announce"))
      el.hidden = true
  }

  /* Mount component on subscription */
  return defer(() => {
    const push$ = new Subject<Announce>()
    push$.subscribe(({ hash }) => {
      el.hidden = true

      /* Persist preference in local storage */
      __md_set<number>("__announce", hash)
    })

    /* Create and return component */
    return watchAnnounce(el)
      .pipe(
        tap(state => push$.next(state)),
        finalize(() => push$.complete()),
        map(state => ({ ref: el, ...state }))
      )
  })
}
