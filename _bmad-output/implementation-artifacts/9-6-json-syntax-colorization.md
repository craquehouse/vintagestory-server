# Story 9.6: JSON Syntax Colorization

Status: review

## Story

As an **administrator**,
I want **JSON files to be syntax-highlighted in the file viewer**,
So that **configuration files are easier to read and understand**.

## Acceptance Criteria

1. **Given** I open a `.json` file in the file viewer
   **When** the content is rendered
   **Then** syntax colorization is applied
   *(Covers FR52)*

2. **Given** JSON content is displayed
   **When** I view the highlighted content
   **Then** keys, strings, numbers, booleans, and null values each have distinct colors
   *(Covers FR53)*

3. **Given** I open a non-JSON file
   **When** the content is rendered
   **Then** no JSON colorization is applied (plain text)

4. **Given** the JSON file contains invalid JSON
   **When** the file is displayed
   **Then** it renders as plain text with no colorization errors

## Tasks / Subtasks

- [x] Task 1: Create JSON syntax highlighter utility + tests (AC: 1, 2)
  - [x] Subtask 1.1: Create `json-highlighter.ts` utility in `web/src/lib/`
  - [x] Subtask 1.2: Implement tokenizer to identify keys, strings, numbers, booleans, null, braces/brackets
  - [x] Subtask 1.3: Generate React elements with appropriate CSS classes for each token type
  - [x] Subtask 1.4: Write unit tests verifying correct tokenization and colorization

- [x] Task 2: Add theme colors for JSON tokens + tests (AC: 2)
  - [x] Subtask 2.1: Define CSS classes/variables for JSON syntax colors in existing theme system
  - [x] Subtask 2.2: Use Catppuccin palette for consistency (keys=blue, strings=green, numbers=yellow, booleans=magenta, null=red)
  - [x] Subtask 2.3: Write tests verifying light/dark theme color definitions

- [x] Task 3: Integrate highlighter into FileViewer + tests (AC: 1, 2, 3, 4)
  - [x] Subtask 3.1: Modify `FileViewer.tsx` to detect JSON files by filename extension
  - [x] Subtask 3.2: Apply syntax highlighting for `.json` files, plain text for others
  - [x] Subtask 3.3: Handle invalid JSON gracefully - fall back to plain text display
  - [x] Subtask 3.4: Write integration tests for FileViewer with JSON highlighting

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

### Security Requirements

**Follow patterns in `project-context.md` -> Security Patterns section:**

- No security-sensitive patterns apply to this frontend-only story
- JSON content comes from the existing config files API (already validated server-side)

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-web` - Run web tests only
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**Current FileViewer Implementation (FileViewer.tsx):**
- Accepts `content` prop (already parsed JSON from API)
- Uses `JSON.stringify(content, null, 2)` to format
- Renders in `<pre>` tag with monospace font
- Supports word wrap toggle

**Implementation Approach:**
Instead of adding a heavy syntax highlighting library, implement a lightweight custom tokenizer specific to JSON. This aligns with the project's philosophy of avoiding over-engineering.

**Token Types for JSON:**
| Token Type | Catppuccin Mocha | Catppuccin Latte | Notes |
|------------|------------------|------------------|-------|
| key | blue `#89b4fa` | blue `#1e66f5` | Property names in quotes before `:` |
| string | green `#a6e3a1` | green `#40a02b` | String values |
| number | yellow `#f9e2af` | yellow `#df8e1d` | Integer and float values |
| boolean | magenta `#cba6f7` | magenta `#8839ef` | `true` and `false` |
| null | red `#f38ba8` | red `#d20f39` | `null` value |
| punctuation | foreground | foreground | `{}[],:` use default color |

**Color Source:** These colors come from `terminal-themes.ts` and match the Catppuccin palette already used throughout the app.

**Tokenizer Strategy:**
Use a regex-based approach to tokenize the formatted JSON string:
1. Parse the formatted JSON string line by line
2. For each line, identify tokens using regex patterns
3. Wrap each token in a `<span>` with appropriate CSS class
4. Return React elements ready for rendering

**Key Pattern Recognition:**
- Keys appear at the start of a line (after optional whitespace) and are quoted strings followed by `:`
- String values are quoted and appear after `:` or in arrays
- Numbers, booleans, and null are unquoted

**File Detection:**
- Check `filename` prop ends with `.json`
- This is more reliable than trying to parse content

### Existing Code References

**FileViewer.tsx Content Rendering (lines 116-155):**
```typescript
// Current implementation
const formattedContent = JSON.stringify(content, null, 2);

return (
  <pre className={cn('font-mono text-sm', ...)}>
    {formattedContent}
  </pre>
);
```

**Terminal Theme Colors (terminal-themes.ts):**
```typescript
// Catppuccin Mocha (dark)
red: '#f38ba8',
green: '#a6e3a1',
yellow: '#f9e2af',
blue: '#89b4fa',
magenta: '#cba6f7',

// Catppuccin Latte (light)
red: '#d20f39',
green: '#40a02b',
yellow: '#df8e1d',
blue: '#1e66f5',
magenta: '#8839ef',
```

### Implementation Details

**json-highlighter.ts:**
```typescript
// Approach: Tokenize formatted JSON and return React elements
interface TokenizedLine {
  elements: React.ReactNode[];
}

export function highlightJson(content: unknown): React.ReactNode {
  try {
    const formatted = JSON.stringify(content, null, 2);
    return tokenizeAndHighlight(formatted);
  } catch {
    // Invalid JSON - return as plain text
    return String(content);
  }
}

// Token patterns (order matters - more specific first)
const TOKEN_PATTERNS = [
  { type: 'key', pattern: /^(\s*)("[^"]*")(\s*:)/ },
  { type: 'string', pattern: /"[^"]*"/ },
  { type: 'number', pattern: /-?\d+\.?\d*(?:[eE][+-]?\d+)?/ },
  { type: 'boolean', pattern: /\b(true|false)\b/ },
  { type: 'null', pattern: /\bnull\b/ },
];
```

**CSS Classes (add to global styles or component):**
```css
/* JSON syntax highlighting - respects theme */
.json-key { color: var(--json-key); }
.json-string { color: var(--json-string); }
.json-number { color: var(--json-number); }
.json-boolean { color: var(--json-boolean); }
.json-null { color: var(--json-null); }
```

**Theme Variables (add to CSS variables):**
```css
:root {
  --json-key: #1e66f5;     /* blue - light */
  --json-string: #40a02b;  /* green - light */
  --json-number: #df8e1d;  /* yellow - light */
  --json-boolean: #8839ef; /* magenta - light */
  --json-null: #d20f39;    /* red - light */
}

.dark {
  --json-key: #89b4fa;     /* blue - dark */
  --json-string: #a6e3a1;  /* green - dark */
  --json-number: #f9e2af;  /* yellow - dark */
  --json-boolean: #cba6f7; /* magenta - dark */
  --json-null: #f38ba8;    /* red - dark */
}
```

### Project Structure Notes

**Files to Create:**
- `web/src/lib/json-highlighter.ts` - Tokenizer and React element generator
- `web/src/lib/json-highlighter.test.ts` - Unit tests

**Files to Modify:**
- `web/src/components/FileViewer.tsx` - Integrate highlighter
- `web/src/components/FileViewer.test.tsx` - Add highlighting tests
- `web/src/index.css` - Add JSON syntax CSS variables (or create dedicated file)

### Previous Story Intelligence (9-5)

**Patterns Established:**
- ANSI color codes for console highlighting work via escape sequences
- Terminal themes define color palettes that should be reused
- Tests should verify colors are distinct for different token types
- Keep implementation simple - single utility file, not a complex library

**Applicable Learnings:**
- Reuse existing Catppuccin color palette from terminal-themes.ts
- Test color distinctness between token types
- Graceful fallback when highlighting isn't applicable

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: epics.md#Story-9.6] - Story requirements (FR52, FR53)
- [Source: web/src/components/FileViewer.tsx] - Current file viewer implementation
- [Source: web/src/lib/terminal-themes.ts] - Catppuccin color definitions
- [Source: web/src/features/settings/FileManagerPanel.tsx] - File manager integration

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None - implementation completed without issues.

### Completion Notes List

- **Task 1 (2026-01-04):** Created `json-highlighter.ts` with regex-based tokenizer that identifies JSON keys, strings, numbers, booleans, null, and punctuation. Generates React elements with CSS class names. Includes `isJsonFile()` helper for filename detection. 54 unit tests pass.

- **Task 2 (2026-01-04):** Added CSS variables for JSON syntax colors to `index.css`. Light mode uses Catppuccin Latte palette, dark mode uses Catppuccin Mocha. Added CSS classes (.json-key, .json-string, .json-number, .json-boolean, .json-null). 17 theme tests verify color consistency with terminal-themes.ts.

- **Task 3 (2026-01-04):** Integrated highlighter into FileViewer component. Detects .json files by extension (case-insensitive) and applies syntax highlighting. Non-JSON files render as plain text. 20 integration tests cover all acceptance criteria.

### File List

**Created:**
- web/src/lib/json-highlighter.ts - JSON tokenizer and React element generator
- web/src/lib/json-highlighter.test.ts - 54 unit tests for tokenizer
- web/src/styles/json-theme.test.ts - 17 tests for theme color definitions

**Modified:**
- web/src/components/FileViewer.tsx - Integrated JSON syntax highlighting
- web/src/components/FileViewer.test.tsx - Added 20 integration tests for highlighting
- web/src/styles/index.css - Added JSON syntax CSS variables and classes

### Change Log

- 2026-01-04: Implemented JSON syntax colorization for FileViewer (Story 9.6)
  - Created lightweight regex-based JSON tokenizer
  - Added Catppuccin-themed syntax colors for light/dark modes
  - Integrated highlighting into FileViewer with graceful fallbacks
  - Total: 91 new tests (54 tokenizer + 17 theme + 20 integration)
