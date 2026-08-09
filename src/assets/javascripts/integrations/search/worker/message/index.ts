import { SearchResult } from "../../_"
import { SearchIndex } from "../../config"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Search message type
 */
export const enum SearchMessageType {
  SETUP,                               /* Search index setup */
  READY,                               /* Search index ready */
  QUERY,                               /* Search query */
  RESULT                               /* Search results */
}

/* ------------------------------------------------------------------------- */

/**
 * Message containing the data necessary to setup the search index
 */
export interface SearchSetupMessage {
  type: SearchMessageType.SETUP        /* Message type */
  data: SearchIndex                    /* Message data */
}

/**
 * Message indicating the search index is ready
 */
export interface SearchReadyMessage {
  type: SearchMessageType.READY        /* Message type */
}

/**
 * Message containing a search query
 */
export interface SearchQueryMessage {
  type: SearchMessageType.QUERY        /* Message type */
  data: string                         /* Message data */
}

/**
 * Message containing results for a search query
 */
export interface SearchResultMessage {
  type: SearchMessageType.RESULT       /* Message type */
  data: SearchResult                   /* Message data */
}

/* ------------------------------------------------------------------------- */

/**
 * Message exchanged with the search worker
 */
export type SearchMessage =
  | SearchSetupMessage
  | SearchReadyMessage
  | SearchQueryMessage
  | SearchResultMessage

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Type guard for search ready messages
 *
 * @param message - Search worker message
 *
 * @returns Test result
 */
export function isSearchReadyMessage(
  message: SearchMessage
): message is SearchReadyMessage {
  return message.type === SearchMessageType.READY
}

/**
 * Type guard for search result messages
 *
 * @param message - Search worker message
 *
 * @returns Test result
 */
export function isSearchResultMessage(
  message: SearchMessage
): message is SearchResultMessage {
  return message.type === SearchMessageType.RESULT
}
