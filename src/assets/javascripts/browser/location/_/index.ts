import { Subject } from "rxjs"

import { feature } from "~/_"
import { h } from "~/utilities"

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Retrieve location
 *
 * This function returns a `URL` object (and not `Location`) to normalize the
 * typings across the application. Furthermore, locations need to be tracked
 * without setting them and `Location` is a singleton which represents the
 * current location.
 *
 * @returns URL
 */
export function getLocation(): URL {
  return new URL(location.href)
}

/**
 * Set location
 *
 * If instant navigation is enabled, this function creates a temporary anchor
 * element, sets the `href` attribute, appends it to the body, clicks it, and
 * then removes it again. The event will bubble up the DOM and be intercepted
 * by the instant navigation event handlers.
 *
 * Note that we must append and remove the anchor element, or the event will
 * not bubble up the DOM, making it impossible to intercept it.
 *
 * @param url - URL to navigate to
 * @param navigate - Force navigation
 */
export function setLocation(
  url: URL | HTMLLinkElement, navigate = false
): void {
  if (feature("navigation.instant") && !navigate) {
    const el = h("a", { href: url.href })
    document.body.appendChild(el)
    el.click()
    el.remove()

  // If we're not using instant navigation, and the page should not be reloaded
  // just instruct the browser to navigate to the given URL
  } else {
    location.href = url.href
  }
}

/* ------------------------------------------------------------------------- */

/**
 * Watch location
 *
 * @returns Location subject
 */
export function watchLocation(): Subject<URL> {
  return new Subject<URL>()
}
