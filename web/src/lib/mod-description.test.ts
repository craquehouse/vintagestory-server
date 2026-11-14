import { describe, it, expect } from 'vitest';
import DOMPurify from 'dompurify';
import {
  sanitizeModDescription,
  sanitizeModDescriptionPreview,
} from './mod-description';

/** Parse sanitized markup so assertions inspect elements, not substrings. */
function parse(html: string | null): HTMLElement {
  const container = document.createElement('div');
  container.innerHTML = html ?? '';
  return container;
}

/** Payloads both sanitizers must neutralize (AC 2). */
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

describe.each([
  ['sanitizeModDescription', sanitizeModDescription],
  ['sanitizeModDescriptionPreview', sanitizeModDescriptionPreview],
] as const)('%s', (_name, sanitize) => {
  describe('strips dangerous content (AC 2)', () => {
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

  describe('links (AC 3)', () => {
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

describe('sanitizeModDescription (detail page)', () => {
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

describe('sanitizeModDescriptionPreview (lookup preview, AC 4)', () => {
  it('drops images, embeds, forms and SVG', () => {
    const el = parse(
      sanitizeModDescriptionPreview(
        [
          '<p>Safe text</p>',
          '<img src="https://i.imgur.com/a.png">',
          '<iframe src="https://www.youtube.com/embed/x"></iframe>',
          '<video src="https://example.com/v.mp4">video fallback</video>',
          '<audio src="https://example.com/a.mp3"></audio>',
          '<form action="https://example.com"><input name="q"><button>Go</button></form>',
          '<svg><circle r="1"></circle></svg>',
        ].join('')
      )
    );
    for (const tag of ['img', 'iframe', 'video', 'audio', 'form', 'input', 'button', 'svg']) {
      expect(el.querySelector(tag)).toBeNull();
    }
    expect(el.textContent).not.toContain('video fallback');
    expect(el.textContent).toContain('Safe text');
  });

  it('drops style, class and id attributes', () => {
    const el = parse(
      sanitizeModDescriptionPreview(
        '<div style="background: #fbbf9d; color: #222" class="fixed inset-0" id="root"><p style="font-weight: bold">Support me</p></div>'
      )
    );
    for (const node of el.querySelectorAll('*')) {
      expect(node.hasAttribute('style')).toBe(false);
      expect(node.hasAttribute('class')).toBe(false);
      expect(node.hasAttribute('id')).toBe(false);
    }
    expect(el.textContent).toBe('Support me');
  });

  it('keeps the text of tables and other dropped wrappers', () => {
    const el = parse(
      sanitizeModDescriptionPreview(
        '<table><tbody><tr><td>Cell text</td></tr></tbody></table><center>Centered</center>'
      )
    );
    expect(el.querySelector('table')).toBeNull();
    expect(el.textContent).toContain('Cell text');
    expect(el.textContent).toContain('Centered');
  });

  it('keeps link titles', () => {
    const el = parse(
      sanitizeModDescriptionPreview('<a title="Discord" href="https://discord.com/x">Discord</a>')
    );
    expect(el.querySelector('a')?.getAttribute('title')).toBe('Discord');
  });

  it('returns null when nothing visible is left', () => {
    expect(
      sanitizeModDescriptionPreview(
        '<p><a href="https://discord.com/x"><img src="https://i.imgur.com/a.png"></a>&nbsp;</p>'
      )
    ).toBeNull();
    expect(sanitizeModDescriptionPreview('<script>alert(1)</script>')).toBeNull();
    expect(sanitizeModDescriptionPreview('')).toBeNull();
  });
});

describe('hook isolation', () => {
  it('does not change the shared DOMPurify instance', () => {
    sanitizeModDescription('<a href="https://example.com">x</a>');
    sanitizeModDescriptionPreview('<a href="https://example.com">x</a>');
    const el = parse(DOMPurify.sanitize('<a href="https://example.com">x</a>'));
    expect(el.querySelector('a')?.hasAttribute('target')).toBe(false);
  });
});
