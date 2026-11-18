import { describe, it, expect } from 'vitest';
import DOMPurify from 'dompurify';
import { IMAGE_NOT_SHOWN, OPENS_IN_NEW_TAB, sanitizeModDescription } from './mod-description';
import { OPENS_IN_NEW_TAB as NEW_TAB_NOTE } from './new-tab';

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
      const el = parse(
        sanitize('<p><a href="https://mods.vintagestory.at/carryonlib">CarryOn Lib</a></p>')
      );
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
        sanitize(
          '<svg><a xlink:href="https://mods.vintagestory.at/carryonlib"><text>Lib</text></a></svg>'
        )
      );
      const link = el.querySelector('svg a');
      expect(link).not.toBeNull();
      expect(link?.getAttribute('target')).toBe('_blank');
      expect(link?.getAttribute('rel')).toBe('noopener noreferrer');
    });

    it('leaves anchors without an href alone', () => {
      const el = parse(
        sanitize('<p><a name="top">Top</a> and <a href="javascript:x()">bad</a></p>')
      );
      for (const a of el.querySelectorAll('a')) {
        expect(a.hasAttribute('target')).toBe(false);
        expect(a.hasAttribute('rel')).toBe(false);
      }
    });
  });

  describe('new tab note (Story 18.1, VSS-tzl)', () => {
    it('ends a link with one screen reader note', () => {
      const el = parse(
        sanitize('<p><a href="https://mods.vintagestory.at/carryonlib">CarryOn Lib</a></p>')
      );
      const link = el.querySelector('a');
      const notes = link?.querySelectorAll('span.sr-only[data-new-tab-note]') ?? [];
      expect(notes).toHaveLength(1);
      expect(link?.lastElementChild).toBe(notes[0]);
      expect(notes[0].textContent).toBe(` ${OPENS_IN_NEW_TAB}`);
      expect(link?.textContent).toBe('CarryOn Lib (opens in a new tab)');
    });

    it('takes its text from OPENS_IN_NEW_TAB', () => {
      expect(OPENS_IN_NEW_TAB).toBe('(opens in a new tab)');
    });

    it('puts the note after an image in a link', () => {
      const el = parse(
        sanitize(
          '<a href="https://example.com"><img src="https://i.imgur.com/a.png" alt="logo"></a>'
        )
      );
      const link = el.querySelector('a');
      expect(link?.firstElementChild?.tagName).toBe('IMG');
      expect(link?.lastElementChild?.hasAttribute('data-new-tab-note')).toBe(true);
      expect(link?.children).toHaveLength(2);
    });

    it('adds no note to anchors without an href or with a removed javascript: href', () => {
      const el = parse(
        sanitize('<p><a name="top">Top</a> and <a href="javascript:x()">bad</a></p>')
      );
      expect(el.querySelectorAll('[data-new-tab-note]')).toHaveLength(0);
      expect(el.textContent).toBe('Top and bad');
    });

    it('takes the same text as OPENS_IN_NEW_TAB in new-tab.ts', () => {
      expect(OPENS_IN_NEW_TAB).toBe(NEW_TAB_NOTE);
    });

    it('adds no second note when sanitized output is sanitized again', () => {
      const once = sanitize('<a href="https://example.com">Docs</a>');
      const twice = sanitize(once);
      expect(parse(twice).querySelectorAll('[data-new-tab-note]')).toHaveLength(1);
      expect(parse(twice).textContent).toBe('Docs (opens in a new tab)');
    });

    it('replaces a marker span written by the mod author with the real note', () => {
      const el = parse(
        sanitize(
          '<a href="https://example.com">Docs<span data-new-tab-note></span></a>' +
            '<a href="https://example.com/b"><span data-new-tab-note>fake</span>Wiki</a>'
        )
      );
      const [first, second] = Array.from(el.querySelectorAll('a'));
      expect(first.querySelectorAll('[data-new-tab-note]')).toHaveLength(1);
      expect(first.textContent).toBe('Docs (opens in a new tab)');
      expect(second.querySelectorAll('[data-new-tab-note]')).toHaveLength(1);
      expect(second.textContent).toBe('Wiki (opens in a new tab)');
    });
  });

  describe('SVG link note (Story 21.6, VSS-woae)', () => {
    const svgLink = (el: HTMLElement) => {
      const link = el.querySelector('svg a');
      if (!link) throw new Error('no SVG link');
      return link;
    };
    const titles = (link: Element) =>
      Array.from(link.children).filter((child) => child.localName === 'title');

    it('gives an SVG link one title, first, naming its text and the new tab', () => {
      const link = svgLink(
        parse(sanitize('<svg><a href="https://example.com/lib"><text>Lib</text></a></svg>'))
      );
      expect(link.getAttribute('target')).toBe('_blank');
      expect(link.getAttribute('rel')).toBe('noopener noreferrer');
      expect(titles(link)).toHaveLength(1);
      expect(link.firstElementChild?.localName).toBe('title');
      expect(link.firstElementChild?.namespaceURI).toBe('http://www.w3.org/2000/svg');
      expect(link.firstElementChild?.textContent).toBe('Lib (opens in a new tab)');
    });

    it('copies an xlink:href to href so the browser exposes the link', () => {
      const link = svgLink(
        parse(
          sanitize(
            '<svg><a xlink:href="https://mods.vintagestory.at/carryonlib"><text>Lib</text></a></svg>'
          )
        )
      );
      expect(link.getAttribute('href')).toBe('https://mods.vintagestory.at/carryonlib');
      expect(link.getAttribute('xlink:href')).toBe('https://mods.vintagestory.at/carryonlib');
      expect(link.getAttribute('target')).toBe('_blank');
      expect(link.firstElementChild?.textContent).toBe('Lib (opens in a new tab)');
    });

    it('joins the text of several text elements with collapsed spaces', () => {
      const link = svgLink(
        parse(
          sanitize(
            '<svg><a href="https://example.com"><text>Carry   On</text><text> Lib </text></a></svg>'
          )
        )
      );
      expect(link.firstElementChild?.textContent).toBe('Carry On Lib (opens in a new tab)');
    });

    it("adds the note to the author's own title", () => {
      const link = svgLink(
        parse(
          sanitize(
            '<svg><a href="https://example.com"><title> Diagram </title><text>Lib</text></a></svg>'
          )
        )
      );
      expect(titles(link)).toHaveLength(1);
      expect(link.firstElementChild?.textContent).toBe('Diagram (opens in a new tab)');
    });

    it('keeps one note when the author title already ends with it, and one title of two', () => {
      const link = svgLink(
        parse(
          sanitize(
            '<svg><a href="https://example.com"><text>Lib</text>' +
              '<title>Safe (opens in a new tab) (opens in a new tab)</title><title>x</title></a></svg>'
          )
        )
      );
      expect(titles(link)).toHaveLength(1);
      expect(link.firstElementChild?.textContent).toBe('Safe (opens in a new tab)');
    });

    it('uses the link text when the author title is only the note', () => {
      const link = svgLink(
        parse(
          sanitize(
            '<svg><a href="https://example.com"><title>(opens in a new tab)</title><text>Lib</text></a></svg>'
          )
        )
      );
      expect(link.firstElementChild?.textContent).toBe('Lib (opens in a new tab)');
    });

    it('keeps one title with the same text when sanitized again', () => {
      const once = sanitize(
        '<svg><a xlink:href="https://example.com"><title>Diagram</title><text>Lib</text></a></svg>'
      );
      const link = svgLink(parse(sanitize(once)));
      expect(titles(link)).toHaveLength(1);
      expect(link.firstElementChild?.textContent).toBe('Diagram (opens in a new tab)');
    });

    it('names a link with no text by the note alone', () => {
      const link = svgLink(
        parse(
          sanitize('<svg><a href="https://example.com"><rect width="10" height="10"/></a></svg>')
        )
      );
      expect(titles(link)).toHaveLength(1);
      expect(link.firstElementChild?.textContent).toBe(OPENS_IN_NEW_TAB);
    });

    it('puts no HTML note span inside an SVG', () => {
      const el = parse(sanitize('<svg><a href="https://example.com"><text>Lib</text></a></svg>'));
      expect(el.querySelectorAll('[data-new-tab-note]')).toHaveLength(0);
    });

    it('gives a javascript: xlink:href no href and no title', () => {
      const el = parse(
        sanitize('<svg><a xlink:href="javascript:alert(1)"><text>Lib</text></a></svg>')
      );
      const link = el.querySelector('svg a');
      expect(link?.hasAttribute('href')).toBe(false);
      expect(link?.hasAttribute('xlink:href')).toBe(false);
      expect(link?.querySelector('title')).toBeNull();
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
      sanitizeModDescription(
        '<p style="color: #222">Text</p><img src="https://i.imgur.com/a.png" alt="logo">'
      )
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
    expect(el.querySelector('[data-new-tab-note]')).toBeNull();
    expect(el.textContent).toBe('x');
    expect(
      parse(DOMPurify.sanitize('<img src="http://x.test/a.png">')).querySelector('img')
    ).not.toBeNull();
  });
});

describe('images the page cannot load (Story 19.3, VSS-my4c)', () => {
  it.each([
    'http://x.test/a.png',
    '/rel.png',
    'rel.png',
    '//x.test/a.png',
    'https:a.png',
    'data:text/html,x',
    'javascript:alert(1)',
  ])('replaces an image with src %s by a note', (src) => {
    const el = parse(sanitizeModDescription(`<img src="${src}" alt="logo">`));
    const note = el.querySelector('[data-image-not-shown]');
    expect(el.querySelector('img')).toBeNull();
    expect(note?.tagName).toBe('SPAN');
    expect(note?.textContent).toBe(`${IMAGE_NOT_SHOWN}: logo`);
  });

  it('replaces an image without src', () => {
    const el = parse(sanitizeModDescription('<img alt="logo">'));
    expect(el.querySelector('img')).toBeNull();
    expect(el.querySelector('[data-image-not-shown]')?.textContent).toBe('Image not shown: logo');
  });

  it.each([
    ['no alt', '<img src="http://x.test/a.png">'],
    ['a blank alt', '<img src="http://x.test/a.png" alt="   ">'],
  ])('says only "Image not shown" with %s', (_name, html) => {
    const el = parse(sanitizeModDescription(html));
    expect(el.querySelector('[data-image-not-shown]')?.textContent).toBe('Image not shown');
  });

  it.each(['https://x.test/a.png', 'HTTPS://x.test/a.png', 'data:image/png;base64,AAAA'])(
    'keeps an image with src %s unchanged',
    (src) => {
      const el = parse(sanitizeModDescription(`<img src="${src}" alt="logo">`));
      expect(el.querySelector('img')?.getAttribute('src')).toBe(src);
      expect(el.querySelector('[data-image-not-shown]')).toBeNull();
    }
  );

  it('drops srcset and sizes from a kept image', () => {
    const el = parse(
      sanitizeModDescription(
        '<img src="https://x.test/a.png" srcset="http://x.test/b.png 2x" sizes="50vw">'
      )
    );
    const img = el.querySelector('img');
    expect(img?.getAttribute('src')).toBe('https://x.test/a.png');
    expect(img?.hasAttribute('srcset')).toBe(false);
    expect(img?.hasAttribute('sizes')).toBe(false);
  });

  it('shows alt text as text, never as markup', () => {
    const el = parse(sanitizeModDescription('<img src="http://x.test/a.png" alt="<b>bold</b>">'));
    const note = el.querySelector('[data-image-not-shown]');
    expect(note?.children).toHaveLength(0);
    expect(note?.textContent).toBe('Image not shown: <b>bold</b>');
  });

  it('replaces each image in a row and keeps the paragraphs around them', () => {
    const el = parse(
      sanitizeModDescription(
        '<p>Before</p>' +
          '<img src="http://x.test/1.png" alt="one">' +
          '<img src="/2.png" alt="two">' +
          '<img src="https://x.test/3.png" alt="three">' +
          '<img src="//x.test/4.png" alt="four">' +
          '<p>After</p>'
      )
    );
    const children = Array.from(el.children);
    expect(children.map((child) => child.tagName)).toEqual([
      'P',
      'SPAN',
      'SPAN',
      'IMG',
      'SPAN',
      'P',
    ]);
    expect(children.map((child) => child.textContent)).toEqual([
      'Before',
      'Image not shown: one',
      'Image not shown: two',
      '',
      'Image not shown: four',
      'After',
    ]);
    expect(el.querySelectorAll('[data-image-not-shown]')).toHaveLength(3);
  });

  it('puts the note inside a link that keeps its new-tab handling', () => {
    const el = parse(
      sanitizeModDescription(
        '<a href="https://x.test/"><img src="http://x.test/a.png" alt="pic"></a>'
      )
    );
    const link = el.querySelector('a');
    expect(link?.getAttribute('target')).toBe('_blank');
    expect(link?.getAttribute('rel')).toBe('noopener noreferrer');
    expect(link?.querySelector('[data-image-not-shown]')?.textContent).toBe('Image not shown: pic');
    expect(link?.querySelectorAll('[data-new-tab-note]')).toHaveLength(1);
    expect(link?.lastElementChild?.hasAttribute('data-new-tab-note')).toBe(true);
  });

  it('keeps one note per image when sanitized again', () => {
    const once = sanitizeModDescription(
      '<img src="http://x.test/a.png" alt="a"><img src="/b.png" alt="b">'
    );
    const el = parse(sanitizeModDescription(once));
    expect(el.querySelector('img')).toBeNull();
    expect(
      Array.from(el.querySelectorAll('[data-image-not-shown]')).map((n) => n.textContent)
    ).toEqual(['Image not shown: a', 'Image not shown: b']);
  });
});
