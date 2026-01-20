/**
 * ModDetailPage - Detailed view of a mod from the browse catalog.
 *
 * Story 10.6: Displays full mod information including HTML description,
 * all releases with compatibility tags, metadata, and stats.
 * Story 10.8: Added confirmation dialog before install/update.
 *
 * Subtasks handled:
 * - 2.1: Route params extraction via useParams
 * - 2.2: Mod header with logo, name, author, stats
 * - 2.3: Description with HTML sanitization (DOMPurify)
 * - 2.4: Releases list with version, date, and compatibility tags
 * - 3.1: Version dropdown using shadcn Select
 * - 3.2: Check installed mods list to determine install vs update state
 * - 3.3: Show Install or Update button based on state
 * - 3.4: Show "Installed: vX.Y.Z" indicator when mod is installed
 */

import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router';
import DOMPurify from 'dompurify';
import {
  ArrowLeft,
  Download,
  Users,
  Calendar,
  ExternalLink,
  Package,
  Globe,
  Tag,
  Check,
  RefreshCw,
  ChevronRight,
  Code,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { CompatibilityBadge } from '@/components/CompatibilityBadge';
import { SideBadge } from '@/components/SideBadge';
import { InstallConfirmDialog } from '@/components/InstallConfirmDialog';
import { useModDetail } from '@/hooks/use-mod-detail';
import { useMods } from '@/hooks/use-mods';
import { formatNumber } from '@/lib/utils';
import type { ModRelease, CompatibilityStatus } from '@/api/types';

/**
 * Formats a timestamp string to a readable date.
 * Handles VintageStory API format: "2025-10-09 21:28:57"
 */
function formatDate(timestamp: string | null): string {
  if (!timestamp) return 'Unknown';
  try {
    // Handle both ISO format and VintageStory format
    const date = new Date(timestamp.replace(' ', 'T'));
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return timestamp;
  }
}

/**
 * Loading skeleton for the mod detail page.
 */
function ModDetailSkeleton() {
  return (
    <div className="space-y-6" data-testid="mod-detail-loading">
      {/* Header skeleton */}
      <div className="flex gap-6">
        <Skeleton className="h-32 w-32 rounded-lg" />
        <div className="flex-1 space-y-3">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-48" />
        </div>
      </div>
      {/* Description skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-24" />
        </CardHeader>
        <CardContent className="space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </CardContent>
      </Card>
      {/* Releases skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-24" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * Error state for the mod detail page.
 */
function ModDetailError({ message }: { message: string }) {
  return (
    <Card className="border-destructive" data-testid="mod-detail-error">
      <CardContent className="py-8 text-center">
        <p className="text-destructive font-medium">Failed to load mod details</p>
        <p className="text-muted-foreground text-sm mt-1">{message}</p>
      </CardContent>
    </Card>
  );
}

/**
 * Install/Update section props.
 */
interface InstallSectionProps {
  /** Mod slug for install */
  slug: string;
  /** Mod name for dialog display */
  name: string;
  /** Mod author for dialog display */
  author: string;
  /** Mod logo URL */
  logoUrl: string | null;
  /** Latest version available */
  latestVersion: string;
  /** All available releases */
  releases: ModRelease[];
  /** Currently installed version (null if not installed) */
  installedVersion: string | null;
  /** Compatibility status for dialog */
  compatibilityStatus: CompatibilityStatus;
  /** Compatibility message for dialog */
  compatibilityMessage?: string;
}

/**
 * Install/Update section with version dropdown and action button.
 *
 * Story 10.8: Uses InstallConfirmDialog before actual install.
 *
 * Shows different states:
 * - Not installed: "Install" button with version dropdown
 * - Installed (current): "Installed: vX.Y.Z" indicator
 * - Installed (update available): "Update to vX.Y.Z" button
 */
function InstallSection({
  slug,
  name,
  author,
  logoUrl,
  latestVersion,
  releases,
  installedVersion,
  compatibilityStatus,
  compatibilityMessage,
}: InstallSectionProps) {
  const [selectedVersion, setSelectedVersion] = useState(latestVersion);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const isInstalled = installedVersion !== null;
  const hasUpdate = isInstalled && installedVersion !== latestVersion;

  const handleInstallClick = () => {
    setIsDialogOpen(true);
  };

  return (
    <>
      <Card className="w-64" data-testid="mod-detail-install-section">
        <CardContent className="pt-4 space-y-3">
          {/* Installed indicator */}
          {isInstalled && (
            <div
              className="flex items-center gap-2 text-sm"
              data-testid="mod-detail-installed-indicator"
            >
              <Check className="h-4 w-4 text-success" />
              <span>Installed: v{installedVersion}</span>
            </div>
          )}

          {/* Version selector */}
          <div className="space-y-2">
            <label className="text-sm text-muted-foreground">Version</label>
            <Select
              value={selectedVersion}
              onValueChange={setSelectedVersion}
            >
              <SelectTrigger data-testid="mod-detail-version-select">
                <SelectValue placeholder="Select version" />
              </SelectTrigger>
              <SelectContent>
                {releases.map((release, index) => (
                  <SelectItem
                    key={release.version}
                    value={release.version}
                    data-testid={`mod-detail-version-option-${release.version}`}
                  >
                    v{release.version}
                    {index === 0 && ' (Latest)'}
                    {release.version === installedVersion && ' (Installed)'}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Action button */}
          {hasUpdate && selectedVersion === latestVersion ? (
            <Button
              className="w-full gap-2"
              onClick={handleInstallClick}
              data-testid="mod-detail-update-button"
            >
              <RefreshCw className="h-4 w-4" />
              Update to v{latestVersion}
            </Button>
          ) : (
            <Button
              className="w-full gap-2"
              onClick={handleInstallClick}
              disabled={isInstalled && selectedVersion === installedVersion}
              data-testid="mod-detail-install-button"
            >
              <Download className="h-4 w-4" />
              {isInstalled && selectedVersion === installedVersion
                ? 'Already Installed'
                : `Install v${selectedVersion}`}
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Story 10.8: Install confirmation dialog */}
      <InstallConfirmDialog
        mod={{
          slug,
          name,
          version: selectedVersion,
          logoUrl,
          author,
        }}
        compatibility={{
          status: compatibilityStatus,
          message: compatibilityMessage,
        }}
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
      />
    </>
  );
}

/**
 * Single release item in the releases list.
 */
function ReleaseItem({ release, isLatest }: { release: ModRelease; isLatest: boolean }) {
  // Format compatible versions for display
  const compatVersions =
    release.gameVersions.length > 3
      ? `${release.gameVersions[0]} - ${release.gameVersions[release.gameVersions.length - 1]}`
      : release.gameVersions.join(', ');

  return (
    <div
      className="flex items-start justify-between py-3 border-b last:border-b-0"
      data-testid={`mod-detail-release-${release.version}`}
    >
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span className="font-medium">v{release.version}</span>
          {isLatest && (
            <Badge variant="secondary" className="text-xs">
              Latest
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5" />
            {formatDate(release.created)}
          </span>
          <span className="flex items-center gap-1">
            <Download className="h-3.5 w-3.5" />
            {formatNumber(release.downloads)}
          </span>
        </div>
        {release.gameVersions.length > 0 && (
          <div className="text-xs text-muted-foreground">
            Compatible: {compatVersions}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * ModDetailPage - Main component displaying detailed mod information.
 */
export function ModDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const { data, isLoading, error } = useModDetail(slug ?? '');
  const { data: modsData } = useMods();

  // Find installed version if this mod is installed
  const installedMod = modsData?.data?.mods?.find((m) => m.slug === slug);
  const installedVersion = installedMod?.version ?? null;

  // Handle back navigation - always go to browse tab
  // Story 11.4: Changed from navigate(-1) to explicit path for predictable behavior
  const handleBack = () => {
    navigate('/game-server/mods/browse');
  };

  if (isLoading) {
    return (
      <div className="container mx-auto py-6 max-w-4xl">
        <ModDetailSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto py-6 max-w-4xl">
        <ModDetailError message={error.message} />
      </div>
    );
  }

  const mod = data?.data;
  if (!mod) {
    return (
      <div className="container mx-auto py-6 max-w-4xl">
        <ModDetailError message="Mod not found" />
      </div>
    );
  }

  // Sanitize HTML description for safe rendering
  const sanitizedDescription = mod.description
    ? DOMPurify.sanitize(mod.description)
    : null;

  return (
    <div className="container mx-auto py-6 max-w-4xl space-y-6" data-testid="mod-detail-page">
      {/* Navigation: Back button and Breadcrumbs */}
      <div className="flex items-center justify-between">
        <Button
          variant="ghost"
          size="sm"
          className="gap-1"
          onClick={handleBack}
          data-testid="mod-detail-back"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Browse
        </Button>

        {/* Breadcrumb navigation */}
        <nav
          className="flex items-center gap-1 text-sm text-muted-foreground"
          aria-label="Breadcrumb"
          data-testid="mod-detail-breadcrumb"
        >
          <Link
            to="/game-server/mods"
            className="hover:text-foreground transition-colors"
            data-testid="mod-detail-breadcrumb-mods"
          >
            Mods
          </Link>
          <ChevronRight className="h-4 w-4" />
          <Link
            to="/game-server/mods/browse"
            className="hover:text-foreground transition-colors"
            data-testid="mod-detail-breadcrumb-browse"
          >
            Browse
          </Link>
          <ChevronRight className="h-4 w-4" />
          <span className="text-foreground font-medium" data-testid="mod-detail-breadcrumb-name">
            {mod.name}
          </span>
        </nav>
      </div>

      {/* Header section */}
      <div className="flex gap-6" data-testid="mod-detail-header">
        {/* Logo */}
        <div className="flex-shrink-0">
          <div
            className="h-32 w-32 rounded-lg bg-muted flex items-center justify-center overflow-hidden"
            data-testid="mod-detail-logo"
          >
            {mod.logoUrl ? (
              <img
                src={mod.logoUrl}
                alt={`${mod.name} logo`}
                className="h-full w-full object-cover"
              />
            ) : (
              <Package className="h-16 w-16 text-muted-foreground" />
            )}
          </div>
        </div>

        {/* Info */}
        <div className="flex-1 space-y-2">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold" data-testid="mod-detail-name">
                {mod.name}
              </h1>
              <p className="text-muted-foreground" data-testid="mod-detail-author">
                by {mod.author}
              </p>
            </div>
            <CompatibilityBadge
              status={mod.compatibility.status}
              message={mod.compatibility.message}
            />
          </div>

          {/* Stats row */}
          <div
            className="flex items-center gap-4 text-sm text-muted-foreground"
            data-testid="mod-detail-stats"
          >
            <span className="flex items-center gap-1" title="Downloads">
              <Download className="h-4 w-4" />
              {formatNumber(mod.downloads)}
            </span>
            <span className="flex items-center gap-1" title="Followers">
              <Users className="h-4 w-4" />
              {formatNumber(mod.follows)}
            </span>
            <SideBadge side={mod.side} />
            <span>Version: {mod.latestVersion}</span>
          </div>

          {/* Tags */}
          {mod.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5" data-testid="mod-detail-tags">
              {mod.tags.map((tag) => (
                <Badge key={tag} variant="outline" className="text-xs">
                  <Tag className="h-3 w-3 mr-1" />
                  {tag}
                </Badge>
              ))}
            </div>
          )}

          {/* External links */}
          <div className="flex items-center gap-3 pt-1">
            <a
              href={`https://mods.vintagestory.at/show/mod/${mod.assetId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
              data-testid="mod-detail-moddb-link"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              ModDB Page
            </a>
            {mod.homepageUrl && (
              <a
                href={mod.homepageUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
                data-testid="mod-detail-homepage-link"
              >
                <Globe className="h-3.5 w-3.5" />
                Homepage
              </a>
            )}
            {mod.sourceUrl && (
              <a
                href={mod.sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
                data-testid="mod-detail-source-link"
              >
                <Code className="h-3.5 w-3.5" />
                Source
              </a>
            )}
          </div>
        </div>

        {/* Install/Update section */}
        {mod.releases.length > 0 && (
          <InstallSection
            slug={mod.slug}
            name={mod.name}
            author={mod.author}
            logoUrl={mod.logoUrl}
            latestVersion={mod.latestVersion}
            releases={mod.releases}
            installedVersion={installedVersion}
            compatibilityStatus={mod.compatibility?.status ?? 'not_verified'}
            compatibilityMessage={mod.compatibility?.message}
          />
        )}
      </div>

      <Separator />

      {/* Description section */}
      <Card data-testid="mod-detail-description-card">
        <CardHeader>
          <CardTitle className="text-lg">Description</CardTitle>
        </CardHeader>
        <CardContent>
          {sanitizedDescription ? (
            <div
              className="prose prose-sm prose-invert max-w-none"
              data-testid="mod-detail-description"
              dangerouslySetInnerHTML={{ __html: sanitizedDescription }}
            />
          ) : (
            <p className="text-muted-foreground italic" data-testid="mod-detail-no-description">
              No description available
            </p>
          )}
        </CardContent>
      </Card>

      {/* Releases section */}
      <Card data-testid="mod-detail-releases-card">
        <CardHeader>
          <CardTitle className="text-lg">
            Releases ({mod.releases.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {mod.releases.length > 0 ? (
            <div data-testid="mod-detail-releases-list">
              {mod.releases.map((release, index) => (
                <ReleaseItem
                  key={release.version}
                  release={release}
                  isLatest={index === 0}
                />
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground italic" data-testid="mod-detail-no-releases">
              No releases available
            </p>
          )}
        </CardContent>
      </Card>

      {/* Metadata section */}
      <Card data-testid="mod-detail-metadata-card">
        <CardHeader>
          <CardTitle className="text-lg">Metadata</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-muted-foreground">Created</dt>
            <dd data-testid="mod-detail-created">{formatDate(mod.created)}</dd>
            <dt className="text-muted-foreground">Last Updated</dt>
            <dd data-testid="mod-detail-last-released">{formatDate(mod.lastReleased)}</dd>
            <dt className="text-muted-foreground">Slug</dt>
            <dd className="font-mono text-xs" data-testid="mod-detail-slug">
              {mod.slug}
            </dd>
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
