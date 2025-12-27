# Story 1.3: Frontend Application Shell

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator**,
I want **a web interface with navigation and theming**,
So that **I can access server management features through a consistent UI**.

## Acceptance Criteria

### AC1: Initial Page Load with Navigation
**Given** I navigate to the web application
**When** the page loads
**Then** I see a sidebar with navigation items (Dashboard, Mods, Config, Terminal)
**And** I see a header displaying the server name placeholder
**And** the application uses Catppuccin Mocha theme by default (dark mode)

### AC2: Theme Toggle
**Given** I am viewing the application
**When** I click the theme toggle in the header
**Then** the theme switches between Mocha (dark) and Latte (light)
**And** my preference is persisted in localStorage

### AC3: System Theme Detection
**Given** I am viewing the application
**When** my system has `prefers-color-scheme: dark` or `light`
**Then** the initial theme respects my system preference (if no stored preference)

### AC4: Navigation Routing
**Given** I am on any page
**When** I click a navigation item in the sidebar
**Then** the URL updates to reflect the selected section
**And** the main content area displays the corresponding view
**And** the active navigation item is visually highlighted

### AC5: Sidebar Collapse
**Given** I am viewing the sidebar
**When** I click the collapse button
**Then** the sidebar collapses to icon-only mode (64px)
**And** my collapse preference is persisted in localStorage

### AC6: Mobile Responsive Behavior
**Given** I resize my browser to mobile width (<768px)
**When** the viewport is narrow
**Then** the sidebar is hidden by default
**And** a hamburger menu button appears to toggle the sidebar overlay

## Tasks / Subtasks

- [ ] Task 1: Install Required Dependencies (AC: #1, #2, #3, #4)
  - [ ] 1.1: Install React Router v7: `cd web && bun add react-router`
  - [ ] 1.2: Install TanStack Query v5: `bun add @tanstack/react-query`
  - [ ] 1.3: Add shadcn/ui components: `bunx shadcn@canary add separator tooltip sheet dropdown-menu switch avatar`

- [ ] Task 2: Create Catppuccin Theme Configuration (AC: #1, #2, #3)
  - [ ] 2.1: Create `web/src/styles/themes/mocha.json` with Catppuccin Mocha palette
  - [ ] 2.2: Create `web/src/styles/themes/latte.json` with Catppuccin Latte palette
  - [ ] 2.3: Update `web/src/styles/index.css` with CSS variables for both themes
  - [ ] 2.4: Configure next-themes provider in App.tsx with `attribute="class"` and `defaultTheme="system"`

- [ ] Task 3: Create Theme Context and Hook (AC: #2, #3)
  - [ ] 3.1: Create `web/src/contexts/ThemeContext.tsx` using next-themes provider
  - [ ] 3.2: Create `web/src/hooks/use-theme.ts` hook wrapping useTheme from next-themes
  - [ ] 3.3: Export theme utilities (setTheme, theme, systemTheme, resolvedTheme)

- [ ] Task 4: Create Layout Components (AC: #1, #5, #6)
  - [ ] 4.1: Create `web/src/components/layout/Header.tsx` with:
    - Server name placeholder left-aligned
    - Pending restart indicator (placeholder, center)
    - Theme toggle button right-aligned (sun/moon icons from lucide-react)
  - [ ] 4.2: Create `web/src/components/layout/Sidebar.tsx` with:
    - Logo/title area
    - Navigation items: Dashboard (LayoutDashboard), Mods (Package), Config (Settings), Terminal (Terminal)
    - Footer: GitHub link + version info placeholders
    - Collapse button and collapsed state (240px -> 64px)
    - Persist collapse state to localStorage
  - [ ] 4.3: Create `web/src/components/layout/Layout.tsx` combining Header + Sidebar + main content area
  - [ ] 4.4: Create mobile menu using Sheet component for <768px viewport

- [ ] Task 5: Create Sidebar State Management (AC: #5)
  - [ ] 5.1: Create `web/src/contexts/SidebarContext.tsx` with:
    - isCollapsed state
    - isMobileOpen state
    - toggle functions
    - localStorage persistence for collapse preference

- [ ] Task 6: Set Up React Router (AC: #4)
  - [ ] 6.1: Create route configuration in `web/src/App.tsx`
  - [ ] 6.2: Create placeholder pages in `web/src/features/`:
    - `dashboard/Dashboard.tsx` - "Dashboard" heading placeholder
    - `mods/ModList.tsx` - "Mods" heading placeholder
    - `config/ConfigEditor.tsx` - "Config" heading placeholder
    - `terminal/Terminal.tsx` - "Terminal" heading placeholder
  - [ ] 6.3: Configure routes: `/` (Dashboard), `/mods`, `/config`, `/terminal`
  - [ ] 6.4: Ensure active nav item is highlighted using NavLink

- [ ] Task 7: Apply Catppuccin Styling (AC: #1)
  - [ ] 7.1: Update shadcn/ui CSS variables in index.css to use Catppuccin tokens
  - [ ] 7.2: Dark mode: base #1e1e2e, surface #313244, text #cdd6f4
  - [ ] 7.3: Light mode: Latte palette equivalents
  - [ ] 7.4: Semantic colors: green #a6e3a1, red #f38ba8, yellow #f9e2af, blue #89b4fa, accent #cba6f7

- [ ] Task 8: Verify and Test (AC: #1, #2, #3, #4, #5, #6)
  - [ ] 8.1: Start dev server: `cd web && bun run dev`
  - [ ] 8.2: Verify sidebar navigation works and URL updates
  - [ ] 8.3: Verify theme toggle switches between dark/light
  - [ ] 8.4: Verify theme persists after refresh
  - [ ] 8.5: Verify sidebar collapse persists after refresh
  - [ ] 8.6: Test mobile breakpoint (<768px) shows hamburger menu
  - [ ] 8.7: Run `bun run build` to verify no TypeScript errors

## Dev Notes

### CRITICAL: Architecture Compliance

**Frontend Structure (MUST follow exactly):**
```
web/src/
├── App.tsx                    # Router setup + providers
├── main.tsx                   # Entry point
├── api/                       # API client (future)
├── components/
│   ├── ui/                    # shadcn/ui components
│   └── layout/
│       ├── Header.tsx
│       ├── Sidebar.tsx
│       └── Layout.tsx
├── features/
│   ├── dashboard/
│   │   └── Dashboard.tsx
│   ├── mods/
│   │   └── ModList.tsx
│   ├── config/
│   │   └── ConfigEditor.tsx
│   └── terminal/
│       └── Terminal.tsx
├── hooks/
│   └── use-theme.ts
├── contexts/
│   ├── ThemeContext.tsx
│   └── SidebarContext.tsx
├── lib/
│   └── utils.ts
└── styles/
    ├── index.css
    └── themes/
        ├── mocha.json
        └── latte.json
```

**Naming Conventions:**
- Files: kebab-case (`use-theme.ts`, `mod-card.tsx`)
- Components: PascalCase (`Header`, `Sidebar`, `Layout`)
- Hooks: camelCase with `use` prefix (`useTheme`, `useSidebar`)

### Technology Stack (from Story 1.1)

| Technology | Version | Installed |
|------------|---------|-----------|
| **React** | 19.2 | Yes |
| **Vite** | 7.x | Yes |
| **TypeScript** | 5.9.x | Yes |
| **Tailwind CSS** | v4 | Yes |
| **shadcn/ui** | canary | Yes (button, card, sonner) |
| **next-themes** | 0.4.6 | Yes |
| **lucide-react** | 0.562.0 | Yes |
| **React Router** | v7 | **TO INSTALL** |
| **TanStack Query** | v5 | **TO INSTALL** |

### Catppuccin Color Palette

**Mocha (Dark Mode):**
```css
--background: #1e1e2e;      /* Base */
--surface: #313244;         /* Surface0 */
--overlay: #45475a;         /* Surface1 */
--text: #cdd6f4;           /* Text */
--subtext: #a6adc8;        /* Subtext0 */
--success: #a6e3a1;        /* Green */
--error: #f38ba8;          /* Red */
--warning: #f9e2af;        /* Yellow */
--info: #89b4fa;           /* Blue */
--accent: #cba6f7;         /* Mauve - Primary actions */
```

**Latte (Light Mode):**
```css
--background: #eff1f5;      /* Base */
--surface: #e6e9ef;         /* Surface0 */
--overlay: #ccd0da;         /* Surface1 */
--text: #4c4f69;           /* Text */
--subtext: #6c6f85;        /* Subtext0 */
--success: #40a02b;        /* Green */
--error: #d20f39;          /* Red */
--warning: #df8e1d;        /* Yellow */
--info: #1e66f5;           /* Blue */
--accent: #8839ef;         /* Mauve - Primary actions */
```

### Layout Specifications

**Header (48px height, fixed):**
- Left: Server name ("VintageStory Server") + placeholder status
- Center: Pending restart indicator placeholder (invisible for now)
- Right: Theme toggle button

**Sidebar (240px expanded, 64px collapsed):**
- Top: Logo/App title
- Navigation items with Lucide icons:
  - Dashboard: `LayoutDashboard`
  - Mods: `Package`
  - Config: `Settings`
  - Terminal: `Terminal`
- Bottom: GitHub link + version "v0.1.0"
- Collapse toggle button

**Main Content:**
- Left margin matching sidebar width
- Top padding for header
- Responsive padding

### React Router v7 Setup Pattern

```tsx
// web/src/App.tsx
import { BrowserRouter, Routes, Route, NavLink } from 'react-router';
import { ThemeProvider } from 'next-themes';
import { Layout } from '@/components/layout/Layout';
import { Dashboard } from '@/features/dashboard/Dashboard';
import { ModList } from '@/features/mods/ModList';
import { ConfigEditor } from '@/features/config/ConfigEditor';
import { Terminal } from '@/features/terminal/Terminal';

function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/mods" element={<ModList />} />
            <Route path="/config" element={<ConfigEditor />} />
            <Route path="/terminal" element={<Terminal />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </ThemeProvider>
  );
}
```

### Sidebar Navigation Pattern

```tsx
// Navigation item with active state
<NavLink
  to="/mods"
  className={({ isActive }) =>
    cn(
      "flex items-center gap-3 px-3 py-2 rounded-md transition-colors",
      isActive
        ? "bg-surface text-accent"
        : "text-subtext hover:bg-surface hover:text-text"
    )
  }
>
  <Package className="h-5 w-5" />
  {!isCollapsed && <span>Mods</span>}
</NavLink>
```

### Theme Toggle Pattern

```tsx
// web/src/components/layout/Header.tsx
import { Moon, Sun } from 'lucide-react';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      aria-label="Toggle theme"
    >
      <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
      <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
    </Button>
  );
}
```

### Mobile Responsive Pattern

```tsx
// Using Sheet for mobile menu
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { Menu } from 'lucide-react';

// In Layout component
<div className="md:hidden">
  <Sheet open={isMobileOpen} onOpenChange={setMobileOpen}>
    <SheetTrigger asChild>
      <Button variant="ghost" size="icon">
        <Menu className="h-5 w-5" />
      </Button>
    </SheetTrigger>
    <SheetContent side="left" className="w-64 p-0">
      <Sidebar />
    </SheetContent>
  </Sheet>
</div>
```

### Previous Story Intelligence (from Stories 1.1 and 1.2)

**Learnings to Apply:**
1. **Use Pydantic v2 patterns** - model_config instead of class Config
2. **Use sonner instead of toast** - shadcn/ui canary uses sonner for notifications
3. **Pin tool versions** - uv 0.9.18, bun 1.3.5 in .mise.toml
4. **TSConfig requires explicit jsx setting** - Already configured in 1.1
5. **shadcn canary required** - For Tailwind v4 + React 19 support

**Files Created in 1.1 (available for this story):**
- `web/src/main.tsx` - Entry point ready
- `web/src/App.tsx` - Needs router/provider wrapping
- `web/src/lib/utils.ts` - cn() utility ready
- `web/src/components/ui/button.tsx` - Ready to use
- `web/src/components/ui/card.tsx` - Ready to use
- `web/src/components/ui/sonner.tsx` - Ready for notifications
- `web/src/styles/index.css` - Needs Catppuccin variables

**Pattern from 1.1:** Files are created as placeholders, ready to populate.

### Project Structure Notes

**Alignment with unified project structure:**
- All new files go in established directories from Story 1.1
- Layout components in `components/layout/` (new directory)
- Feature pages in `features/<feature>/` (new files)
- Hooks in `hooks/` (new files)
- Contexts in `contexts/` (new files)
- Theme configs in `styles/themes/` (new directory)

**No conflicts detected** - Following Architecture doc exactly.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Frontend-Structure]
- [Source: _bmad-output/planning-artifacts/architecture.md#Frontend-Architecture]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Design-System-Foundation]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Visual-Design-Foundation]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Navigation-Patterns]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Responsive-Design-Accessibility]
- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.3]
- [Source: _bmad-output/implementation-artifacts/1-1-initialize-development-environment-and-project-structure.md]
- [Source: _bmad-output/implementation-artifacts/1-2-backend-api-skeleton-with-health-endpoints.md]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

