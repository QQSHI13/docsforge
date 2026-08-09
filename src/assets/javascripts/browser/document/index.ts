import {
  ReplaySubject,
  Subject,
  fromEvent
} from "rxjs"

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Watch document
 *
 * Documents are implemented as subjects, so all downstream observables are
 * automatically updated when a new document is emitted.
 *
 * @returns Document subject
 */
export function watchDocument(): Subject<Document> {
  const document$ = new ReplaySubject<Document>(1)
  fromEvent(document, "DOMContentLoaded", { once: true })
    .subscribe(() => document$.next(document))

  /* Return document */
  return document$
}
