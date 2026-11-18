/**
 * UIPreferencesPanel - User interface preferences settings.
 *
 * Manages theme selection, console font size, and the sidebar preference (Story 21.8:
 * Automatic, Expanded or Collapsed).
 * All preferences are persisted to cookies via PreferencesContext.
 *
 * Story: UI-017 - User preferences cookie persistence
 */

import { Sun, Moon, Monitor, Minus, Plus } from 'lucide-react';
import { SettingGroup } from '@/components/SettingGroup';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  usePreferences,
  type ThemePreference,
  FONT_SIZE_MIN,
  FONT_SIZE_MAX,
} from '@/contexts/PreferencesContext';
import { SIDEBAR_PREFERENCES, type SidebarPreference } from '@/lib/sidebar-preference';

/**
 * Props for the UIPreferencesPanel component.
 */
export interface UIPreferencesPanelProps {
  /**
   * Additional CSS class names.
   */
  className?: string;
}

const themeOptions: { value: ThemePreference; label: string; icon: typeof Sun }[] = [
  { value: 'system', label: 'System', icon: Monitor },
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
];

const sidebarLabels: Record<SidebarPreference, string> = {
  auto: 'Automatic',
  expanded: 'Expanded',
  collapsed: 'Collapsed',
};

/**
 * Panel for managing UI preferences.
 *
 * All changes are immediately persisted to cookies.
 */
export function UIPreferencesPanel({ className }: UIPreferencesPanelProps) {
  const { preferences, setThemePreference, setConsoleFontSize, setSidebarPreference } =
    usePreferences();

  return (
    <div className={className} data-testid="ui-preferences-panel">
      <div className="space-y-4">
        {/* Theme Settings */}
        <SettingGroup title="Appearance" description="Customize the look and feel of the interface">
          {/* Theme Selector */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Theme</label>
            <div className="flex gap-2">
              {themeOptions.map(({ value, label, icon: Icon }) => (
                <Button
                  key={value}
                  variant={preferences.theme === value ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setThemePreference(value)}
                  className="flex-1"
                  data-testid={`theme-${value}`}
                >
                  <Icon className="h-4 w-4 mr-2" />
                  {label}
                </Button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              Choose how the interface appears. System follows your device settings.
            </p>
          </div>
        </SettingGroup>

        {/* Console Settings */}
        <SettingGroup title="Console" description="Customize the game server console appearance">
          {/* Font Size Control */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Font Size</label>
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                size="icon"
                onClick={() => setConsoleFontSize(preferences.consoleFontSize - 1)}
                disabled={preferences.consoleFontSize <= FONT_SIZE_MIN}
                aria-label="Decrease font size"
                data-testid="font-size-decrease"
              >
                <Minus className="h-4 w-4" />
              </Button>
              <div
                className={cn(
                  'flex items-center justify-center w-16 h-9',
                  'rounded-md border border-input bg-background',
                  'text-sm font-medium'
                )}
                data-testid="font-size-value"
              >
                {preferences.consoleFontSize}px
              </div>
              <Button
                variant="outline"
                size="icon"
                onClick={() => setConsoleFontSize(preferences.consoleFontSize + 1)}
                disabled={preferences.consoleFontSize >= FONT_SIZE_MAX}
                aria-label="Increase font size"
                data-testid="font-size-increase"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Adjust the console terminal font size ({FONT_SIZE_MIN}-{FONT_SIZE_MAX}px).
            </p>
          </div>
        </SettingGroup>

        {/* Layout Settings */}
        <SettingGroup title="Layout" description="Configure the default layout behavior">
          {/* Sidebar preference (Story 21.8): shows the stored value, not what is drawn */}
          <div className="space-y-2">
            <label id="sidebar-preference-label" className="text-sm font-medium text-foreground">
              Sidebar
            </label>
            <div
              role="group"
              aria-labelledby="sidebar-preference-label"
              className="flex flex-wrap gap-2"
            >
              {SIDEBAR_PREFERENCES.map((value) => (
                <Button
                  key={value}
                  variant={preferences.sidebar === value ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSidebarPreference(value)}
                  aria-pressed={preferences.sidebar === value}
                  data-testid={`sidebar-${value}`}
                >
                  {sidebarLabels[value]}
                </Button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              Automatic collapses the sidebar on screens narrower than 1024px. Expanded and
              Collapsed apply at every width.
            </p>
          </div>
        </SettingGroup>
      </div>
    </div>
  );
}
