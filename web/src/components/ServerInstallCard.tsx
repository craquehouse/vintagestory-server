import { useState } from 'react';
import { Download, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { useInstallServer } from '@/hooks/use-server-status';
import type { InstallStatus } from '@/api/types';

interface ServerInstallCardProps {
  isInstalling: boolean;
  installStatus?: InstallStatus;
}

/**
 * Card component shown when no server is installed or installation is in progress.
 *
 * Features:
 * - Version input field for specifying which version to install
 * - Install button that triggers the installation
 * - Progress indicator during installation with stage and percentage
 */
export function ServerInstallCard({
  isInstalling,
  installStatus,
}: ServerInstallCardProps) {
  const [version, setVersion] = useState('');
  const installMutation = useInstallServer();

  const handleInstall = () => {
    if (!version.trim()) {
      toast.error('Please enter a version', {
        description: 'A version number is required to install the server.',
      });
      return;
    }

    installMutation.mutate(version.trim(), {
      onSuccess: () => {
        toast.success('Installation started', {
          description: `Installing VintageStory ${version}...`,
        });
      },
      onError: (error) => {
        toast.error('Failed to start installation', {
          description: error.message,
        });
      },
    });
  };

  const isButtonDisabled = isInstalling || installMutation.isPending || !version.trim();

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Download className="size-5" />
          Install Server
        </CardTitle>
        <CardDescription>
          {isInstalling
            ? 'Installation in progress...'
            : 'Enter the VintageStory version to install'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isInstalling && installStatus ? (
          <InstallProgress status={installStatus} />
        ) : (
          <div className="flex gap-2">
            <Input
              type="text"
              placeholder="e.g., 1.21.3"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              disabled={isInstalling || installMutation.isPending}
              aria-label="Server version"
              className="flex-1"
            />
            <Button
              onClick={handleInstall}
              disabled={isButtonDisabled}
              aria-label="Install server"
            >
              {isInstalling || installMutation.isPending ? (
                <>
                  <Loader2 className="animate-spin" />
                  Installing...
                </>
              ) : (
                <>
                  <Download />
                  Install
                </>
              )}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface InstallProgressProps {
  status: InstallStatus;
}

/**
 * Progress indicator shown during installation.
 */
function InstallProgress({ status }: InstallProgressProps) {
  return (
    <div className="space-y-3" role="status" aria-label="Installation progress">
      <div className="flex items-center justify-between text-sm">
        <span className="capitalize text-muted-foreground">
          {status.state.replace(/_/g, ' ')}
        </span>
        <span className="font-medium">{status.progress}%</span>
      </div>
      <Progress value={status.progress} />
      {status.message && (
        <p className="text-xs text-muted-foreground">{status.message}</p>
      )}
    </div>
  );
}
