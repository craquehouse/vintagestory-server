/**
 * SettingsPage - Main settings management page.
 *
 * Provides tabbed interface for different settings domains:
 * - API Settings: Server auto-start, environment handling, refresh intervals
 * - File Manager: Browse and view server configuration files
 *
 * Story 6.4: Settings UI - AC6
 * Story 6.6: File Manager UI
 */

import { Settings, FolderOpen } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ApiSettingsPanel } from './ApiSettingsPanel';
import { FileManagerPanel } from './FileManagerPanel';

/**
 * Settings page with tabbed navigation.
 *
 * Displays different settings domains in separate tabs:
 * - API Settings: Operational configuration for the API server
 * - File Manager: Browse and view server configuration files
 */
export function SettingsPage() {
  return (
    <div
      className="flex h-full flex-col gap-4"
      data-testid="settings-page"
      aria-label="Settings page"
    >
      <Tabs defaultValue="api-settings" className="flex-1 flex flex-col">
        <TabsList>
          <TabsTrigger value="api-settings" data-testid="api-settings-tab">
            <Settings className="h-4 w-4" />
            API Settings
          </TabsTrigger>
          <TabsTrigger value="file-manager" data-testid="file-manager-tab">
            <FolderOpen className="h-4 w-4" />
            File Manager
          </TabsTrigger>
        </TabsList>

        <TabsContent value="api-settings" className="flex-1 mt-4">
          <ApiSettingsPanel />
        </TabsContent>

        <TabsContent value="file-manager" className="flex-1 mt-4">
          <FileManagerPanel />
        </TabsContent>
      </Tabs>
    </div>
  );
}
