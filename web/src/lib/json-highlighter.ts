/**
 * JSON syntax highlighter utility for FileViewer component.
 *
 * Tokenizes formatted JSON and returns React elements with CSS classes
 * for syntax colorization. Uses a lightweight regex-based approach
 * to avoid heavy dependencies.
 *
 * Story 9.6: JSON Syntax Colorization - AC: 1, 2
 */

import { createElement, type ReactNode } from 'react';

/**
 * Token types for JSON syntax highlighting.
 */
export type JsonTokenType =
  | 'key'
  | 'string'
  | 'number'
  | 'boolean'
  | 'null'
  | 'punctuation';

/**
 * A single token from JSON tokenization.
 */
export interface JsonToken {
  type: JsonTokenType;
  value: string;
}

/**
 * CSS class names for JSON token types.
 */
export const JSON_CSS_CLASSES: Record<JsonTokenType, string> = {
  key: 'json-key',
  string: 'json-string',
  number: 'json-number',
  boolean: 'json-boolean',
  null: 'json-null',
  punctuation: '', // Use default foreground color
};

/**
 * Tokenizes a single line of formatted JSON into tokens.
 *
 * @param line - A single line of formatted JSON
 * @returns Array of tokens representing the line
 */
export function tokenizeLine(line: string): JsonToken[] {
  const tokens: JsonToken[] = [];
  let remaining = line;
  let position = 0;

  while (remaining.length > 0) {
    // Match leading whitespace
    const whitespaceMatch = remaining.match(/^(\s+)/);
    if (whitespaceMatch) {
      tokens.push({ type: 'punctuation', value: whitespaceMatch[1] });
      remaining = remaining.slice(whitespaceMatch[1].length);
      position += whitespaceMatch[1].length;
      continue;
    }

    // Match JSON key (string followed by colon)
    // A key is a quoted string at the start of content (after whitespace) followed by ": "
    const keyMatch = remaining.match(/^("(?:[^"\\]|\\.)*")(\s*:\s*)/);
    if (keyMatch) {
      tokens.push({ type: 'key', value: keyMatch[1] });
      tokens.push({ type: 'punctuation', value: keyMatch[2] });
      remaining = remaining.slice(keyMatch[0].length);
      position += keyMatch[0].length;
      continue;
    }

    // Match string value (quoted string not followed by colon)
    const stringMatch = remaining.match(/^("(?:[^"\\]|\\.)*")/);
    if (stringMatch) {
      tokens.push({ type: 'string', value: stringMatch[1] });
      remaining = remaining.slice(stringMatch[1].length);
      position += stringMatch[1].length;
      continue;
    }

    // Match number (integer, float, or scientific notation)
    const numberMatch = remaining.match(/^(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/);
    if (numberMatch) {
      tokens.push({ type: 'number', value: numberMatch[1] });
      remaining = remaining.slice(numberMatch[1].length);
      position += numberMatch[1].length;
      continue;
    }

    // Match boolean literals
    const booleanMatch = remaining.match(/^(true|false)/);
    if (booleanMatch) {
      tokens.push({ type: 'boolean', value: booleanMatch[1] });
      remaining = remaining.slice(booleanMatch[1].length);
      position += booleanMatch[1].length;
      continue;
    }

    // Match null literal
    const nullMatch = remaining.match(/^(null)/);
    if (nullMatch) {
      tokens.push({ type: 'null', value: nullMatch[1] });
      remaining = remaining.slice(nullMatch[1].length);
      position += nullMatch[1].length;
      continue;
    }

    // Match punctuation (braces, brackets, comma)
    const punctMatch = remaining.match(/^([{}\[\],])/);
    if (punctMatch) {
      tokens.push({ type: 'punctuation', value: punctMatch[1] });
      remaining = remaining.slice(1);
      position += 1;
      continue;
    }

    // If nothing matches, consume one character as punctuation (fallback)
    tokens.push({ type: 'punctuation', value: remaining[0] });
    remaining = remaining.slice(1);
    position += 1;
  }

  return tokens;
}

/**
 * Tokenizes formatted JSON string into tokens.
 *
 * @param jsonString - A formatted JSON string (output of JSON.stringify with indentation)
 * @returns 2D array of tokens, one array per line
 */
export function tokenizeJson(jsonString: string): JsonToken[][] {
  const lines = jsonString.split('\n');
  return lines.map(tokenizeLine);
}

/**
 * Creates a React element for a token.
 *
 * @param token - The token to render
 * @param key - React key for the element
 * @returns React element with appropriate CSS class
 */
function createTokenElement(token: JsonToken, key: string): ReactNode {
  const className = JSON_CSS_CLASSES[token.type];

  if (!className) {
    // Punctuation and whitespace - no special styling
    return token.value;
  }

  return createElement(
    'span',
    { className, key },
    token.value
  );
}

/**
 * Highlights JSON content and returns React elements.
 *
 * Takes parsed JSON content, stringifies it with formatting,
 * tokenizes it, and returns React elements with appropriate CSS classes.
 *
 * @param content - The JSON content to highlight (already parsed)
 * @returns React nodes representing the highlighted JSON
 */
export function highlightJson(content: unknown): ReactNode {
  try {
    const formatted = JSON.stringify(content, null, 2);
    const tokenizedLines = tokenizeJson(formatted);

    const elements: ReactNode[] = [];
    let keyCounter = 0;

    tokenizedLines.forEach((tokens, lineIndex) => {
      tokens.forEach((token) => {
        elements.push(createTokenElement(token, `token-${keyCounter++}`));
      });

      // Add newline between lines (except after the last line)
      if (lineIndex < tokenizedLines.length - 1) {
        elements.push('\n');
      }
    });

    return createElement('span', { key: 'json-highlighted' }, elements);
  } catch {
    // If JSON.stringify fails, return content as plain string
    return String(content);
  }
}

/**
 * Checks if a filename has a JSON extension.
 *
 * @param filename - The filename to check
 * @returns True if the filename ends with .json (case-insensitive)
 */
export function isJsonFile(filename: string | null): boolean {
  if (!filename) return false;
  return filename.toLowerCase().endsWith('.json');
}
