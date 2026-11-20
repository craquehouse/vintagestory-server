/**
 * JSON5 highlighting for CodeMirror (Story 23.5, Epic 23 ADR-5 decision 1).
 *
 * A small stream tokenizer instead of a language package: `@codemirror/lang-json` has no
 * comments, and JSON5 is not valid JavaScript at the top level. It colours what the
 * config viewer accepts (JSON5): comments, single- and double-quoted strings, property
 * names (quoted or not) before a colon, numbers (hex, signs, leading or trailing dots,
 * Infinity, NaN), true/false and null, with the colours of the JSON viewer (Story 9.6).
 */

import { HighlightStyle, StreamLanguage, type StreamParser } from '@codemirror/language';
import { tags } from '@lezer/highlight';

export interface Json5State {
  /** Inside a block comment that started on an earlier line. */
  inBlockComment: boolean;
}

const NUMBER = /^[+-]?(?:0[xX][0-9a-fA-F]+|Infinity|NaN|(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)/;
const IDENTIFIER = /^[A-Za-z_$][\w$]*/;

/** Whether the next character after the spaces (on this line) is a colon. */
function colonFollows(stream: { string: string; pos: number }): boolean {
  return /^\s*:/.test(stream.string.slice(stream.pos));
}

export const json5StreamParser: StreamParser<Json5State> = {
  name: 'json5',
  startState: () => ({ inBlockComment: false }),
  copyState: (state) => ({ ...state }),
  token(stream, state) {
    if (state.inBlockComment) {
      if (stream.skipTo('*/')) {
        stream.pos += 2;
        state.inBlockComment = false;
      } else {
        stream.skipToEnd();
      }
      return 'comment';
    }
    if (stream.eatSpace()) return null;
    if (stream.match('//')) {
      stream.skipToEnd();
      return 'comment';
    }
    if (stream.match('/*')) {
      state.inBlockComment = true;
      if (stream.skipTo('*/')) {
        stream.pos += 2;
        state.inBlockComment = false;
      } else {
        stream.skipToEnd();
      }
      return 'comment';
    }
    const quote = stream.peek();
    if (quote === '"' || quote === "'") {
      stream.next();
      let escaped = false;
      let ch: string | void;
      while ((ch = stream.next()) !== undefined) {
        if (ch === quote && !escaped) break;
        escaped = !escaped && ch === '\\';
      }
      return colonFollows(stream) ? 'propertyName' : 'string';
    }
    if (stream.match(NUMBER)) return 'number';
    if (stream.match(IDENTIFIER)) {
      const word = stream.current();
      if (colonFollows(stream)) return 'propertyName';
      if (word === 'true' || word === 'false') return 'bool';
      if (word === 'null') return 'null';
      return null;
    }
    const ch = stream.next();
    if (ch === '{' || ch === '}' || ch === '[' || ch === ']') return 'brace';
    if (ch === ',' || ch === ':') return 'punctuation';
    return null;
  },
  languageData: { commentTokens: { line: '//', block: { open: '/*', close: '*/' } } },
};

export const json5Language = StreamLanguage.define(json5StreamParser);

/** The JSON viewer's colours (CSS variables, so both themes apply). */
export const json5HighlightStyle = HighlightStyle.define([
  { tag: tags.propertyName, color: 'var(--json-key)' },
  { tag: tags.string, color: 'var(--json-string)' },
  { tag: tags.number, color: 'var(--json-number)' },
  { tag: tags.bool, color: 'var(--json-boolean)' },
  { tag: tags.null, color: 'var(--json-null)' },
  { tag: tags.comment, color: 'var(--muted-foreground)', fontStyle: 'italic' },
]);
