/**
 * Tests for JSON syntax highlighter utility.
 *
 * Story 9.6: JSON Syntax Colorization - AC: 1, 2
 */

import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { createElement } from 'react';
import {
  tokenizeLine,
  tokenizeJson,
  highlightJson,
  isJsonFile,
  JSON_CSS_CLASSES,
} from './json-highlighter';

describe('json-highlighter', () => {
  describe('tokenizeLine', () => {
    it('tokenizes a JSON key-value pair with string value', () => {
      const tokens = tokenizeLine('  "name": "test"');

      expect(tokens).toEqual([
        { type: 'punctuation', value: '  ' },
        { type: 'key', value: '"name"' },
        { type: 'punctuation', value: ': ' },
        { type: 'string', value: '"test"' },
      ]);
    });

    it('tokenizes a JSON key-value pair with number value', () => {
      const tokens = tokenizeLine('  "port": 42420');

      expect(tokens).toEqual([
        { type: 'punctuation', value: '  ' },
        { type: 'key', value: '"port"' },
        { type: 'punctuation', value: ': ' },
        { type: 'number', value: '42420' },
      ]);
    });

    it('tokenizes a JSON key-value pair with boolean value', () => {
      const tokens = tokenizeLine('  "enabled": true');

      expect(tokens).toEqual([
        { type: 'punctuation', value: '  ' },
        { type: 'key', value: '"enabled"' },
        { type: 'punctuation', value: ': ' },
        { type: 'boolean', value: 'true' },
      ]);
    });

    it('tokenizes a JSON key-value pair with false boolean', () => {
      const tokens = tokenizeLine('  "disabled": false');

      expect(tokens).toEqual([
        { type: 'punctuation', value: '  ' },
        { type: 'key', value: '"disabled"' },
        { type: 'punctuation', value: ': ' },
        { type: 'boolean', value: 'false' },
      ]);
    });

    it('tokenizes a JSON key-value pair with null value', () => {
      const tokens = tokenizeLine('  "password": null');

      expect(tokens).toEqual([
        { type: 'punctuation', value: '  ' },
        { type: 'key', value: '"password"' },
        { type: 'punctuation', value: ': ' },
        { type: 'null', value: 'null' },
      ]);
    });

    it('tokenizes opening brace', () => {
      const tokens = tokenizeLine('{');

      expect(tokens).toEqual([{ type: 'punctuation', value: '{' }]);
    });

    it('tokenizes closing brace', () => {
      const tokens = tokenizeLine('}');

      expect(tokens).toEqual([{ type: 'punctuation', value: '}' }]);
    });

    it('tokenizes array brackets', () => {
      const tokens = tokenizeLine('  "items": [');

      expect(tokens).toEqual([
        { type: 'punctuation', value: '  ' },
        { type: 'key', value: '"items"' },
        { type: 'punctuation', value: ': ' },
        { type: 'punctuation', value: '[' },
      ]);
    });

    it('tokenizes array values', () => {
      const tokens = tokenizeLine('    "value1",');

      expect(tokens).toEqual([
        { type: 'punctuation', value: '    ' },
        { type: 'string', value: '"value1"' },
        { type: 'punctuation', value: ',' },
      ]);
    });

    it('tokenizes negative numbers', () => {
      const tokens = tokenizeLine('  "offset": -100');

      expect(tokens).toEqual([
        { type: 'punctuation', value: '  ' },
        { type: 'key', value: '"offset"' },
        { type: 'punctuation', value: ': ' },
        { type: 'number', value: '-100' },
      ]);
    });

    it('tokenizes floating point numbers', () => {
      const tokens = tokenizeLine('  "value": 3.14159');

      expect(tokens).toEqual([
        { type: 'punctuation', value: '  ' },
        { type: 'key', value: '"value"' },
        { type: 'punctuation', value: ': ' },
        { type: 'number', value: '3.14159' },
      ]);
    });

    it('tokenizes scientific notation numbers', () => {
      const tokens = tokenizeLine('  "large": 1.5e10');

      expect(tokens).toEqual([
        { type: 'punctuation', value: '  ' },
        { type: 'key', value: '"large"' },
        { type: 'punctuation', value: ': ' },
        { type: 'number', value: '1.5e10' },
      ]);
    });

    it('tokenizes negative scientific notation', () => {
      const tokens = tokenizeLine('  "tiny": 2.5e-8');

      expect(tokens).toEqual([
        { type: 'punctuation', value: '  ' },
        { type: 'key', value: '"tiny"' },
        { type: 'punctuation', value: ': ' },
        { type: 'number', value: '2.5e-8' },
      ]);
    });

    it('tokenizes strings with escaped quotes', () => {
      const tokens = tokenizeLine('  "message": "Hello \\"World\\""');

      expect(tokens).toEqual([
        { type: 'punctuation', value: '  ' },
        { type: 'key', value: '"message"' },
        { type: 'punctuation', value: ': ' },
        { type: 'string', value: '"Hello \\"World\\""' },
      ]);
    });

    it('tokenizes key with trailing comma', () => {
      const tokens = tokenizeLine('  "name": "test",');

      expect(tokens).toEqual([
        { type: 'punctuation', value: '  ' },
        { type: 'key', value: '"name"' },
        { type: 'punctuation', value: ': ' },
        { type: 'string', value: '"test"' },
        { type: 'punctuation', value: ',' },
      ]);
    });

    it('handles empty line', () => {
      const tokens = tokenizeLine('');
      expect(tokens).toEqual([]);
    });

    it('handles line with only whitespace', () => {
      const tokens = tokenizeLine('    ');
      expect(tokens).toEqual([{ type: 'punctuation', value: '    ' }]);
    });
  });

  describe('tokenizeJson', () => {
    it('tokenizes a simple JSON object', () => {
      const json = '{\n  "name": "test"\n}';
      const result = tokenizeJson(json);

      expect(result).toHaveLength(3);
      expect(result[0]).toEqual([{ type: 'punctuation', value: '{' }]);
      expect(result[1]).toEqual([
        { type: 'punctuation', value: '  ' },
        { type: 'key', value: '"name"' },
        { type: 'punctuation', value: ': ' },
        { type: 'string', value: '"test"' },
      ]);
      expect(result[2]).toEqual([{ type: 'punctuation', value: '}' }]);
    });

    it('tokenizes JSON with multiple key-value pairs', () => {
      const json = '{\n  "name": "test",\n  "count": 42\n}';
      const result = tokenizeJson(json);

      expect(result).toHaveLength(4);
    });

    it('tokenizes nested JSON objects', () => {
      const json = '{\n  "server": {\n    "port": 8080\n  }\n}';
      const result = tokenizeJson(json);

      expect(result).toHaveLength(5);
      // Check the nested structure
      expect(result[1]).toContainEqual({ type: 'key', value: '"server"' });
      expect(result[2]).toContainEqual({ type: 'key', value: '"port"' });
    });
  });

  describe('highlightJson', () => {
    it('returns highlighted content as React elements', () => {
      const content = { name: 'test' };
      const result = highlightJson(content);

      // Render to check structure
      const { container } = render(createElement('pre', null, result));

      // Check that spans with correct classes exist
      expect(container.querySelector('.json-key')).toBeInTheDocument();
      expect(container.querySelector('.json-string')).toBeInTheDocument();
    });

    it('applies correct CSS class to keys', () => {
      const content = { myKey: 'value' };
      const result = highlightJson(content);

      const { container } = render(createElement('pre', null, result));
      const keyElement = container.querySelector('.json-key');

      expect(keyElement).toBeInTheDocument();
      expect(keyElement?.textContent).toBe('"myKey"');
    });

    it('applies correct CSS class to string values', () => {
      const content = { name: 'testValue' };
      const result = highlightJson(content);

      const { container } = render(createElement('pre', null, result));
      const stringElement = container.querySelector('.json-string');

      expect(stringElement).toBeInTheDocument();
      expect(stringElement?.textContent).toBe('"testValue"');
    });

    it('applies correct CSS class to numbers', () => {
      const content = { count: 42 };
      const result = highlightJson(content);

      const { container } = render(createElement('pre', null, result));
      const numberElement = container.querySelector('.json-number');

      expect(numberElement).toBeInTheDocument();
      expect(numberElement?.textContent).toBe('42');
    });

    it('applies correct CSS class to booleans', () => {
      const content = { enabled: true };
      const result = highlightJson(content);

      const { container } = render(createElement('pre', null, result));
      const booleanElement = container.querySelector('.json-boolean');

      expect(booleanElement).toBeInTheDocument();
      expect(booleanElement?.textContent).toBe('true');
    });

    it('applies correct CSS class to null', () => {
      const content = { value: null };
      const result = highlightJson(content);

      const { container } = render(createElement('pre', null, result));
      const nullElement = container.querySelector('.json-null');

      expect(nullElement).toBeInTheDocument();
      expect(nullElement?.textContent).toBe('null');
    });

    it('handles complex nested objects', () => {
      const content = {
        server: {
          name: 'Test Server',
          port: 42420,
          settings: {
            maxPlayers: 16,
            pvp: true,
            password: null,
          },
        },
        mods: ['mod1', 'mod2'],
      };

      const result = highlightJson(content);
      const { container } = render(createElement('pre', null, result));

      // Should have multiple keys, strings, numbers, booleans, null
      expect(container.querySelectorAll('.json-key').length).toBeGreaterThan(0);
      expect(container.querySelectorAll('.json-string').length).toBeGreaterThan(0);
      expect(container.querySelectorAll('.json-number').length).toBeGreaterThan(0);
      expect(container.querySelector('.json-boolean')).toBeInTheDocument();
      expect(container.querySelector('.json-null')).toBeInTheDocument();
    });

    it('preserves overall JSON structure in output', () => {
      const content = { name: 'test', count: 42 };
      const result = highlightJson(content);

      const { container } = render(createElement('pre', null, result));

      // The text content should match formatted JSON
      const expectedText = JSON.stringify(content, null, 2);
      expect(container.textContent).toBe(expectedText);
    });

    it('returns plain string for invalid content', () => {
      // Create a circular reference that would cause JSON.stringify to throw
      const circular: Record<string, unknown> = {};
      circular.self = circular;

      const result = highlightJson(circular);

      // Should return a string representation
      expect(typeof result).toBe('string');
    });

    it('handles empty object', () => {
      const content = {};
      const result = highlightJson(content);

      const { container } = render(createElement('pre', null, result));
      expect(container.textContent).toBe('{}');
    });

    it('handles empty array', () => {
      const content: unknown[] = [];
      const result = highlightJson(content);

      const { container } = render(createElement('pre', null, result));
      expect(container.textContent).toBe('[]');
    });

    it('handles primitive number', () => {
      const content = 42;
      const result = highlightJson(content);

      const { container } = render(createElement('pre', null, result));
      expect(container.querySelector('.json-number')).toBeInTheDocument();
      expect(container.textContent).toBe('42');
    });

    it('handles primitive boolean', () => {
      const content = true;
      const result = highlightJson(content);

      const { container } = render(createElement('pre', null, result));
      expect(container.querySelector('.json-boolean')).toBeInTheDocument();
      expect(container.textContent).toBe('true');
    });

    it('handles primitive null', () => {
      const content = null;
      const result = highlightJson(content);

      const { container } = render(createElement('pre', null, result));
      expect(container.querySelector('.json-null')).toBeInTheDocument();
      expect(container.textContent).toBe('null');
    });

    it('handles primitive string', () => {
      const content = 'hello world';
      const result = highlightJson(content);

      const { container } = render(createElement('pre', null, result));
      expect(container.querySelector('.json-string')).toBeInTheDocument();
      expect(container.textContent).toBe('"hello world"');
    });
  });

  describe('isJsonFile', () => {
    it('returns true for .json extension', () => {
      expect(isJsonFile('config.json')).toBe(true);
    });

    it('returns true for .JSON extension (case insensitive)', () => {
      expect(isJsonFile('CONFIG.JSON')).toBe(true);
    });

    it('returns true for .Json extension (mixed case)', () => {
      expect(isJsonFile('settings.Json')).toBe(true);
    });

    it('returns false for .txt extension', () => {
      expect(isJsonFile('readme.txt')).toBe(false);
    });

    it('returns false for .js extension', () => {
      expect(isJsonFile('script.js')).toBe(false);
    });

    it('returns false for no extension', () => {
      expect(isJsonFile('Makefile')).toBe(false);
    });

    it('returns false for null filename', () => {
      expect(isJsonFile(null)).toBe(false);
    });

    it('returns false for empty string', () => {
      expect(isJsonFile('')).toBe(false);
    });

    it('returns true for path with .json extension', () => {
      expect(isJsonFile('path/to/config.json')).toBe(true);
    });

    it('returns false for filename containing json but different extension', () => {
      expect(isJsonFile('myjsonfile.txt')).toBe(false);
    });
  });

  describe('JSON_CSS_CLASSES', () => {
    it('has correct class for key', () => {
      expect(JSON_CSS_CLASSES.key).toBe('json-key');
    });

    it('has correct class for string', () => {
      expect(JSON_CSS_CLASSES.string).toBe('json-string');
    });

    it('has correct class for number', () => {
      expect(JSON_CSS_CLASSES.number).toBe('json-number');
    });

    it('has correct class for boolean', () => {
      expect(JSON_CSS_CLASSES.boolean).toBe('json-boolean');
    });

    it('has correct class for null', () => {
      expect(JSON_CSS_CLASSES.null).toBe('json-null');
    });

    it('has empty class for punctuation (uses default color)', () => {
      expect(JSON_CSS_CLASSES.punctuation).toBe('');
    });

    it('all token types have distinct non-empty classes (except punctuation)', () => {
      const classes = Object.entries(JSON_CSS_CLASSES)
        .filter(([type]) => type !== 'punctuation')
        .map(([_, className]) => className);

      // Check all classes are non-empty
      expect(classes.every((c) => c.length > 0)).toBe(true);

      // Check all classes are unique
      const uniqueClasses = new Set(classes);
      expect(uniqueClasses.size).toBe(classes.length);
    });
  });

  describe('token distinctness (AC: 2)', () => {
    it('assigns different types to keys vs string values', () => {
      // In JSON, a key is '"name"' before ':', value is '"test"' after ':'
      const line = '  "key": "value"';
      const tokens = tokenizeLine(line);

      const keyToken = tokens.find((t) => t.value === '"key"');
      const valueToken = tokens.find((t) => t.value === '"value"');

      expect(keyToken?.type).toBe('key');
      expect(valueToken?.type).toBe('string');
      expect(keyToken?.type).not.toBe(valueToken?.type);
    });

    it('each value type gets its own distinct token type', () => {
      const content = {
        str: 'text',
        num: 123,
        bool: true,
        nil: null,
      };

      const formatted = JSON.stringify(content, null, 2);
      const lines = tokenizeJson(formatted);
      const allTokens = lines.flat();

      // Find one of each value type
      const stringToken = allTokens.find(
        (t) => t.type === 'string' && t.value === '"text"'
      );
      const numberToken = allTokens.find(
        (t) => t.type === 'number' && t.value === '123'
      );
      const booleanToken = allTokens.find(
        (t) => t.type === 'boolean' && t.value === 'true'
      );
      const nullToken = allTokens.find(
        (t) => t.type === 'null' && t.value === 'null'
      );

      expect(stringToken).toBeDefined();
      expect(numberToken).toBeDefined();
      expect(booleanToken).toBeDefined();
      expect(nullToken).toBeDefined();

      // All have different types
      const types = [
        stringToken!.type,
        numberToken!.type,
        booleanToken!.type,
        nullToken!.type,
      ];
      expect(new Set(types).size).toBe(4);
    });
  });
});
