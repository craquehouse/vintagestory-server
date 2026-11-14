import { describe, it, expect } from 'vitest';
import DOMPurify from 'dompurify';
import { sanitizeModDescription } from './mod-description';

/** Parse sanitized markup so assertions inspect elements, not substrings. */
function parse(html: string | null): HTMLElement {
  const container = document.createElement('div');
  container.innerHTML = html ?? '';
  return container;
}

/** Payloads the sanitizer must neutralize. */
const dangerous: { name: string; html: string; check: (el: HTMLElement) => void }[] = [
  {
    name: 'script elements and their content',
    html: '<p>Safe text</p><script>alert("xss")</script>',
    check: (el) => {
      expect(el.querySelector('script')).toBeNull();
      expect(el.textContent).not.toContain('alert');
    },
  },
  {
    name: 'event handler attributes',
    html: '<p onclick="alert(1)" onload="alert(2)">Safe text</p><a href="https://example.com" onmouseover="alert(3)">link</a>',
    check: (el) => {
      for (const node of el.querySelectorAll('*')) {
        for (const attr of node.getAttributeNames()) {
          expect(attr.startsWith('on')).toBe(false);
        }
      }
    },
  },
  {
    name: 'javascript: URLs in any spelling',
    html: [
      '<p>Safe text</p>',
      '<a href="javascript:alert(1)">a</a>',
      '<a href="JaVaScRiPt:alert(1)">b</a>',
      '<a href="  javascript:alert(1)">c</a>',
      '<a href="&#106;avascript:alert(1)">d</a>',
      '<a href="java&#x09;script:alert(1)">e</a>',
    ].join(''),
    check: (el) => {
      expect(el.innerHTML.toLowerCase()).not.toContain('javascript');
      for (const a of el.querySelectorAll('a')) {
        expect(a.hasAttribute('href')).toBe(false);
      }
    },
  },
  {
    name: 'data: and vbscript: URLs',
    html: [
      '<p>Safe text</p>',
      '<a href="data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==">a</a>',
      '<a href="vbscript:msgbox(1)">b</a>',
    ].join(''),
    check: (el) => {
      expect(el.innerHTML.toLowerCase()).not.toContain('data:');
      expect(el.innerHTML.toLowerCase()).not.toContain('vbscript');
      for (const a of el.querySelectorAll('a')) {
        expect(a.hasAttribute('href')).toBe(false);
      }
    },
  },
  {
    name: 'forms and their controls',
    html: [
      '<p>Safe text</p>',
      '<form action="https://evil.example"><input type="submit" value="Log in">',
      '<button>Confirm</button><select><option>x</option></select><textarea>t</textarea></form>',
    ].join(''),
    check: (el) => {
      for (const tag of ['form', 'input', 'button', 'select', 'textarea']) {
        expect(el.querySelector(tag)).toBeNull();
      }
      expect(el.innerHTML).not.toContain('evil.example');
    },
  },
  {
    name: 'javascript: URLs inside SVG',
    html: '<p>Safe text</p><svg><a xlink:href="javascript:alert(1)"><text>x</text></a></svg>',
    check: (el) => {
      expect(el.innerHTML.toLowerCase()).not.toContain('javascript');
    },
  },
  {
    name: 'a leading style element',
    html: '<style>body { display: none }</style><p>Safe text</p>',
    check: (el) => {
      expect(el.querySelector('style')).toBeNull();
      expect(el.textContent).not.toContain('display');
    },
  },
  {
    name: 'a style element after content',
    html: '<p>Safe text</p><style>body { display: none }</style>',
    check: (el) => {
      expect(el.querySelector('style')).toBeNull();
      expect(el.textContent).not.toContain('display');
    },
  },
];

describe('sanitizeModDescription', () => {
  const sanitize = sanitizeModDescription;

  describe('strips dangerous content', () => {
    it.each(dangerous)('removes $name and keeps the text', ({ html, check }) => {
      const el = parse(sanitize(html));
      check(el);
      expect(el.textContent).toContain('Safe text');
    });

    it('removes onerror from images', () => {
      const el = parse(sanitize('<p>Safe text</p><img src="x" onerror="alert(1)">'));
      expect(el.innerHTML).not.toContain('onerror');
    });
  });

  describe('links', () => {
    it('opens links in a new tab with rel="noopener noreferrer"', () => {
      const el = parse(sanitize('<p><a href="https://mods.vintagestory.at/carryonlib">CarryOn Lib</a></p>'));
      const link = el.querySelector('a');
      expect(link).not.toBeNull();
      expect(link?.getAttribute('href')).toBe('https://mods.vintagestory.at/carryonlib');
      expect(link?.getAttribute('target')).toBe('_blank');
      expect(link?.getAttribute('rel')).toBe('noopener noreferrer');
    });

    it("replaces the author's target and rel", () => {
      const el = parse(
        sanitize('<a href="https://ko-fi.com/x" target="_self" rel="noopener">Ko-fi</a>')
      );
      const link = el.querySelector('a');
      expect(link?.getAttribute('target')).toBe('_blank');
      expect(link?.getAttribute('rel')).toBe('noopener noreferrer');
    });

    it('opens SVG links in a new tab with rel="noopener noreferrer"', () => {
      const el = parse(
        sanitize('<svg><a xlink:href="https://mods.vintagestory.at/carryonlib"><text>Lib</text></a></svg>')
      );
      const link = el.querySelector('svg a');
      expect(link).not.toBeNull();
      expect(link?.getAttribute('target')).toBe('_blank');
      expect(link?.getAttribute('rel')).toBe('noopener noreferrer');
    });

    it('leaves anchors without an href alone', () => {
      const el = parse(sanitize('<p><a name="top">Top</a> and <a href="javascript:x()">bad</a></p>'));
      for (const a of el.querySelectorAll('a')) {
        expect(a.hasAttribute('target')).toBe(false);
        expect(a.hasAttribute('rel')).toBe(false);
      }
    });
  });

  it('keeps text formatting', () => {
    const el = parse(
      sanitize('<h3>Title</h3><p><strong>Bold</strong> <em>italic</em></p><ul><li>One</li></ul>')
    );
    expect(el.querySelector('h3')?.textContent).toBe('Title');
    expect(el.querySelector('strong')?.textContent).toBe('Bold');
    expect(el.querySelector('em')?.textContent).toBe('italic');
    expect(el.querySelector('li')?.textContent).toBe('One');
  });
});

describe('sanitizeModDescription keeps what the detail page shows', () => {
  it('keeps images and inline styles as the detail page shows them today', () => {
    const el = parse(
      sanitizeModDescription('<p style="color: #222">Text</p><img src="https://i.imgur.com/a.png" alt="logo">')
    );
    expect(el.querySelector('img')?.getAttribute('src')).toBe('https://i.imgur.com/a.png');
    expect(el.querySelector('p')?.getAttribute('style')).toBe('color: #222');
  });

  it('returns an empty string for an empty description', () => {
    expect(sanitizeModDescription('')).toBe('');
  });
});

describe('hook isolation', () => {
  it('does not change the shared DOMPurify instance', () => {
    sanitizeModDescription('<a href="https://example.com">x</a>');
    const el = parse(DOMPurify.sanitize('<a href="https://example.com">x</a>'));
    expect(el.querySelector('a')?.hasAttribute('target')).toBe(false);
  });
});
