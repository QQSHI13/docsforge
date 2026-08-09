import ClipboardJS from "clipboard"
import {
  Observable,
  Subject,
  map,
  tap
} from "rxjs"

import { translation } from "~/_"
import { getElement } from "~/browser"

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Setup options
 */
interface SetupOptions {
  alert$: Subject<string>              /* Alert subject */
}

/* ----------------------------------------------------------------------------
 * Helper functions
 * ------------------------------------------------------------------------- */

/**
 * Extract text to copy
 *
 * @param el - HTML element
 *
 * @returns Extracted text
 */
function extract(el: HTMLElement): string {
  el.setAttribute("data-md-copying", "")
  const copy = el.closest("[data-copy]")
  const text = copy
    ? copy.getAttribute("data-copy")!
    : el.innerText
  el.removeAttribute("data-md-copying")
  return text.trimEnd()
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Set up Clipboard.js integration
 *
 * @param options - Options
 */
export function setupClipboardJS(
  { alert$ }: SetupOptions
): void {
  if (ClipboardJS.isSupported()) {
    new Observable<ClipboardJS.Event>(subscriber => {
      new ClipboardJS("[data-clipboard-target], [data-clipboard-text]", {
        text: el => (
          el.getAttribute("data-clipboard-text")! ||
          extract(getElement(
            el.getAttribute("data-clipboard-target")!
          ))
        )
      })
        .on("success", ev => subscriber.next(ev))
    })
      .pipe(
        tap(ev => {
          const trigger = ev.trigger as HTMLElement
          trigger.focus()
        }),
        map(() => translation("clipboard.copied"))
      )
        .subscribe(alert$)
  }
}
