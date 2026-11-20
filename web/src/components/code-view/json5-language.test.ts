import { describe, it, expect } from 'vitest';
import { StringStream } from '@codemirror/language';
import { json5StreamParser, type Json5State } from './json5-language';

/** The [token, text] pairs of each line, carrying the state across lines. */
function tokenize(text: string): [string | null, string][] {
  const state: Json5State = json5StreamParser.startState!(2);
  const tokens: [string | null, string][] = [];
  for (const line of text.split('\n')) {
    const stream = new StringStream(line, 2, 2);
    while (!stream.eol()) {
      stream.start = stream.pos;
      const style = json5StreamParser.token(stream, state);
      if (style !== null) tokens.push([style, stream.current()]);
    }
  }
  return tokens;
}

describe('json5StreamParser (Story 23.5)', () => {
  it('colours line and block comments, across lines', () => {
    expect(tokenize('// one\n/* two\nthree */ 1')).toEqual([
      ['comment', '// one'],
      ['comment', '/* two'],
      ['comment', 'three */'],
      ['number', '1'],
    ]);
  });

  it('tells property names from string values', () => {
    expect(tokenize(`{"a": "x", 'b' : 'y\\'z', c: 1}`)).toEqual([
      ['brace', '{'],
      ['propertyName', '"a"'],
      ['punctuation', ':'],
      ['string', '"x"'],
      ['punctuation', ','],
      ['propertyName', "'b'"],
      ['punctuation', ':'],
      ['string', "'y\\'z'"],
      ['punctuation', ','],
      ['propertyName', 'c'],
      ['punctuation', ':'],
      ['number', '1'],
      ['brace', '}'],
    ]);
  });

  it('keeps // inside a string', () => {
    expect(tokenize('"http://example.com//x"')).toEqual([['string', '"http://example.com//x"']]);
  });

  it.each(['0x1F', '-1.5e3', '+1', '.5', '5.', 'Infinity', '-Infinity', 'NaN'])(
    'colours the number %s',
    (number) => {
      expect(tokenize(number)).toEqual([['number', number]]);
    }
  );

  it('colours true, false and null', () => {
    expect(tokenize('[true, false, null]').filter(([style]) => style !== 'punctuation')).toEqual([
      ['brace', '['],
      ['bool', 'true'],
      ['bool', 'false'],
      ['null', 'null'],
      ['brace', ']'],
    ]);
  });
});
