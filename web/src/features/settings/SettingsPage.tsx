/**
 * SettingsPage - Main settings management page.
 *
 * Provides tabbed interface for different settings domains:
 * - API Settings: Server auto-start, environment handling, refresh intervals
 * - File Manager: Coming soon placeholder
 *
 * Story 6.4: Settings UI - AC6
 */

import { Settings, FolderOpen } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ApiSettingsPanel } from './ApiSettingsPanel';

/**
 * Settings page with tabbed navigation.
 *
 * Displays different settings domains in separate tabs:
 * - API Settings: Operational configuration for the API server
 * - File Manager: Placeholder for future file management feature
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
          <Card>
            <CardHeader>
              <CardTitle>File Manager</CardTitle>
              <CardDescription>
                Browse and manage server configuration files
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div
                className="flex flex-col items-center justify-center py-12 text-center"
                data-testid="file-manager-coming-soon"
              >
                <FolderOpen className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium">Coming Soon</h3>
                <p className="text-sm text-muted-foreground mt-2 max-w-md">
                  The file manager will allow you to browse, edit, and manage server
                  configuration files directly from the web interface.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
