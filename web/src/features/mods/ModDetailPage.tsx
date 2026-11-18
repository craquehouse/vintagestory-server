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
 *
 * Story 14.3: An installed mod gets a version section instead of the install
 * flow: the Update button uses the offered update from the update status, the
 * version list holds only releases with the installed mod ID, and updates and
 * switches go through the version change API with its confirmation flow.
 *
 * Story 16.2: The installed mod is found by any mod ID in the entry (the URL slug,
 * then each release's modidstr), not only the browse slug, which is just the entry's
 * first mod ID.
 *
 * Story 16.3: The compatibility badge, its message (shown as text when not
 * compatible) and the header version describe the release the API evaluated: the
 * newest release of the installed mod ID, or of the newest release's mod ID when
 * none is installed (Epic 16 ADR-2).
 *
 * Story 17.1: The error states (failed lookup, no mod, incomplete details) show the
 * same Back to Browse button as the loaded page, with the same target and state.
 *
 * Story 17.2: The install section lists only the releases of the lookup's
 * `installModId`, preselects `latestVersion` (what a plain install picks) and installs
 * `installModId`. "(Latest)" and the Releases list's "Latest" badge mark that release;
 * a release without a downloadable file is listed disabled (Epic 17 ADR-2).
 *
 * Story 18.1: A Screenshots section between the header and the description shows the
 * mod's screenshots (`ModScreenshotGallery`), and a "Watch trailer" link joins the
 * external links when the API sent a `trailerUrl`. Description links that open in a
 * new tab show an icon (the `mod-description` class) and a screen reader note.
 *
 * Story 21.6 (Epic 21 ADR-10, ADR-11): the header's ModDB Page, Homepage, Source and
 * Watch trailer links are `NewTabLink`s, named "... (opens in a new tab)", and Homepage
 * and Source show a trailing external-link mark. Below `md` the header stacks: logo and
 * info wrap in one group and the install card goes under them at full width; its
 * controls are 44px tall below `lg`, and its Version label names the select. The description is typeset by the `.mod-description`
 * rules in `styles/index.css` from the theme tokens, not by `prose` classes.
 */

import { useId, useState } from 'react';
import { useParams, useNavigate, useLocation, Link } from 'react-router';
import {
  ArrowLeft,
  ArrowLeftRight,
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
  Loader2,
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
import { VersionChangeConfirmDialog } from '@/components/VersionChangeConfirmDialog';
import { ModScreenshotGallery } from '@/components/ModScreenshotGallery';
import { NewTabLink } from '@/components/NewTabLink';
import { useModDetail } from '@/hooks/use-mod-detail';
import { useMods, useModUpdates } from '@/hooks/use-mods';
import { useVersionChangeFlow } from '@/hooks/use-version-change-flow';
import { formatNumber } from '@/lib/utils';
import { findInstalledModForEntry, versionChoices } from '@/lib/mod-ids';
import { sanitizeModDescription } from '@/lib/mod-description';
import { BROWSE_PATH, MOD_DETAIL_RETURN_STATE, readBrowseSearchState } from '@/lib/browse-search';
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
      {/* Story 21.6: the same stacking as the loaded header, nothing wider than the screen */}
      <div
        className="flex flex-col gap-4 md:flex-row md:gap-6"
        data-testid="mod-detail-loading-header"
      >
        <div className="flex min-w-0 flex-wrap gap-4 md:flex-1 md:flex-nowrap md:gap-6">
          <Skeleton className="h-32 w-32 shrink-0 rounded-lg" />
          <div className="min-w-0 grow basis-48 space-y-3">
            <Skeleton className="h-8 w-full max-w-64" />
            <Skeleton className="h-4 w-full max-w-32" />
            <Skeleton className="h-4 w-full max-w-48" />
          </div>
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
 * Back to Browse button, shared by the loaded page and its error states (Story 17.1).
 */
function BackToBrowseButton({ onClick }: { onClick: () => void }) {
  return (
    <Button
      variant="ghost"
      size="sm"
      className="gap-1 max-lg:min-h-11"
      onClick={onClick}
      data-testid="mod-detail-back"
    >
      <ArrowLeft className="h-4 w-4" />
      Back to Browse
    </Button>
  );
}

/**
 * Error state for the mod detail page, with a way back to the browser (Story 17.1).
 */
function ModDetailError({ message, onBack }: { message: string; onBack: () => void }) {
  return (
    <div className="space-y-6">
      <div>
        <BackToBrowseButton onClick={onBack} />
      </div>
      <Card className="border-destructive" data-testid="mod-detail-error">
        <CardContent className="py-8 text-center">
          <p className="text-destructive font-medium">Failed to load mod details</p>
          <p className="text-muted-foreground text-sm mt-1">{message}</p>
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * Install section props.
 */
interface InstallSectionProps {
  /** The install mod ID (the lookup's `installModId`); what Install installs */
  slug: string;
  /** Mod name for dialog display */
  name: string;
  /** Mod author for dialog display */
  author: string;
  /** Mod logo URL */
  logoUrl: string | null;
  /** The version a plain install picks; null when no release of the mod ID has a file */
  latestVersion: string | null;
  /** All releases of the mod database entry, newest first */
  releases: ModRelease[];
  /** Compatibility status for dialog */
  compatibilityStatus: CompatibilityStatus;
  /** Compatibility message for dialog */
  compatibilityMessage?: string;
}

/**
 * Install section for a mod that is not installed: version dropdown and Install button.
 *
 * Story 10.8: Uses InstallConfirmDialog before actual install.
 */
function InstallSection({
  slug,
  name,
  author,
  logoUrl,
  latestVersion,
  releases,
  compatibilityStatus,
  compatibilityMessage,
}: InstallSectionProps) {
  const [selectedVersion, setSelectedVersion] = useState<string | null>(latestVersion);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const choices = versionChoices(releases, slug);
  // Story 21.6: the label names the select, which otherwise reads as its value
  const versionSelectId = useId();

  return (
    <>
      <Card className="w-full md:w-64 md:shrink-0" data-testid="mod-detail-install-section">
        <CardContent className="pt-4 space-y-3">
          {/* Version selector */}
          <div className="space-y-2">
            <label htmlFor={versionSelectId} className="text-sm text-muted-foreground">
              Version
            </label>
            <Select value={selectedVersion ?? ''} onValueChange={setSelectedVersion}>
              <SelectTrigger
                id={versionSelectId}
                className="w-full max-lg:min-h-11"
                data-testid="mod-detail-version-select"
              >
                <SelectValue placeholder="Select version" />
              </SelectTrigger>
              <SelectContent>
                {choices.map((choice) => (
                  <SelectItem
                    key={choice.version}
                    value={choice.version}
                    disabled={!choice.installable}
                    data-testid={`mod-detail-version-option-${choice.version}`}
                  >
                    v{choice.version}
                    {choice.version === latestVersion && ' (Latest)'}
                    {!choice.installable && ' (no file)'}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button
            className="w-full gap-2 max-lg:min-h-11"
            onClick={() => setIsDialogOpen(true)}
            disabled={selectedVersion === null}
            data-testid="mod-detail-install-button"
          >
            <Download className="h-4 w-4" />
            {selectedVersion === null ? 'No downloadable release' : `Install v${selectedVersion}`}
          </Button>
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
 * Installed version section props (Story 14.3).
 */
interface InstalledVersionSectionProps {
  /** Installed mod ID, as the installed mods list reports it */
  slug: string;
  /** The lookup's install mod ID (Story 17.2) */
  installModId: string;
  /** The version a plain install of `installModId` picks (Story 17.2) */
  latestVersion: string | null;
  /** Mod name for toasts and the confirmation dialog */
  name: string;
  /** Installed version */
  installedVersion: string;
  /** All releases of the mod database entry, newest first */
  releases: ModRelease[];
}

/**
 * Version section for an installed mod (Story 14.3).
 *
 * The version list holds only releases with the installed mod ID, since one
 * database entry can ship several mod IDs. The default selection is the offered
 * update, if any, otherwise the installed version. Updates and switches go through
 * the version change API; risky changes open VersionChangeConfirmDialog.
 */
function InstalledVersionSection({
  slug,
  installModId,
  latestVersion,
  name,
  installedVersion,
  releases,
}: InstalledVersionSectionProps) {
  const { data: updatesData } = useModUpdates();
  const versionChange = useVersionChangeFlow();
  const [picked, setPicked] = useState<string | null>(null);
  // Story 21.6: the label names the select, which otherwise reads as its value
  const versionSelectId = useId();

  // Releases with the installed mod ID; a re-uploaded version keeps its first
  // (newest) listing, as the update check and version change API do.
  const ownReleases = versionChoices(releases, slug);
  // Story 17.2: "(Latest)" is what a plain install picks, which belongs to the
  // install mod ID; on another installed mod ID of the entry there is no label.
  const labelledLatest = slug === installModId ? latestVersion : null;
  const updateStatus = updatesData?.data?.mods.find((item) => item.slug === slug);
  // The update check (Epic 14 ADR-1) can offer a release without a downloadable
  // file, which the version change API refuses (Story 17.2, review M1). Such an offer
  // is not preselected and gets no Update button; the list shows it disabled with
  // "(no file)", so it cannot be picked either.
  const offered = updateStatus?.status === 'update_available' ? updateStatus.offeredVersion : null;
  const offeredVersion = ownReleases.some(
    (choice) => choice.version === offered && choice.installable
  )
    ? offered
    : null;
  const selectedVersion = picked ?? offeredVersion ?? installedVersion;
  const isChanging = versionChange.isPending(slug);

  const handleChange = () => {
    versionChange.start({
      slug,
      name,
      version: selectedVersion,
      installedVersion,
      kind: selectedVersion === offeredVersion ? 'update' : 'switch',
    });
  };

  let action;
  if (selectedVersion === installedVersion) {
    action = (
      <Button
        className="w-full gap-2 max-lg:min-h-11"
        disabled
        data-testid="mod-detail-current-button"
      >
        <Check className="h-4 w-4" />
        Installed
      </Button>
    );
  } else if (selectedVersion === offeredVersion) {
    action = (
      <Button
        className="w-full gap-2 max-lg:min-h-11"
        onClick={handleChange}
        disabled={isChanging}
        data-testid="mod-detail-update-button"
      >
        {isChanging ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <RefreshCw className="h-4 w-4" />
        )}
        Update to v{selectedVersion}
      </Button>
    );
  } else {
    action = (
      <Button
        variant="outline"
        className="w-full gap-2 max-lg:min-h-11"
        onClick={handleChange}
        disabled={isChanging}
        data-testid="mod-detail-switch-button"
      >
        {isChanging ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <ArrowLeftRight className="h-4 w-4" />
        )}
        Switch to v{selectedVersion}
      </Button>
    );
  }

  return (
    <>
      <Card className="w-full md:w-64 md:shrink-0" data-testid="mod-detail-install-section">
        <CardContent className="pt-4 space-y-3">
          <div
            className="flex items-center gap-2 text-sm"
            data-testid="mod-detail-installed-indicator"
          >
            <Check className="h-4 w-4 text-success" />
            <span>Installed: v{installedVersion}</span>
          </div>

          {ownReleases.length === 0 ? (
            <p className="text-sm text-muted-foreground" data-testid="mod-detail-no-own-releases">
              The mod database lists no releases for mod ID {slug}.
            </p>
          ) : (
            <>
              <div className="space-y-2">
                <label htmlFor={versionSelectId} className="text-sm text-muted-foreground">
                  Version
                </label>
                <Select value={selectedVersion} onValueChange={setPicked}>
                  <SelectTrigger
                    id={versionSelectId}
                    className="w-full max-lg:min-h-11"
                    data-testid="mod-detail-version-select"
                  >
                    <SelectValue placeholder="Select version" />
                  </SelectTrigger>
                  <SelectContent>
                    {ownReleases.map((choice) => (
                      <SelectItem
                        key={choice.version}
                        value={choice.version}
                        disabled={!choice.installable}
                        data-testid={`mod-detail-version-option-${choice.version}`}
                      >
                        v{choice.version}
                        {choice.version === labelledLatest && ' (Latest)'}
                        {choice.version === installedVersion && ' (Installed)'}
                        {!choice.installable && ' (no file)'}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {action}
            </>
          )}
        </CardContent>
      </Card>

      <VersionChangeConfirmDialog
        confirmation={versionChange.confirmation}
        gameVersion={updatesData?.data?.gameVersion ?? null}
        onConfirm={versionChange.confirm}
        onCancel={versionChange.cancel}
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
          <div className="text-xs text-muted-foreground">Compatible: {compatVersions}</div>
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

  // Story 16.1: Return to the browse state this page was opened from (default when opened directly)
  const location = useLocation();
  const browseTarget = `${BROWSE_PATH}${readBrowseSearchState(location.state) ?? ''}`;

  // Handle back navigation - always go to browse tab
  // Story 11.4: Changed from navigate(-1) to explicit path for predictable behavior
  const handleBack = () => {
    navigate(browseTarget, { state: MOD_DETAIL_RETURN_STATE });
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
        <ModDetailError message={error.message} onBack={handleBack} />
      </div>
    );
  }

  const mod = data?.data;
  if (!mod) {
    return (
      <div className="container mx-auto py-6 max-w-4xl">
        <ModDetailError message="Mod not found" onBack={handleBack} />
      </div>
    );
  }

  // The API contract guarantees these fields, but a malformed response must not crash the page
  if (!mod.compatibility || !Array.isArray(mod.tags) || !Array.isArray(mod.releases)) {
    return (
      <div className="container mx-auto py-6 max-w-4xl">
        <ModDetailError message="The server returned incomplete mod details" onBack={handleBack} />
      </div>
    );
  }

  // Installed copy of this mod, if any, matched by any of the entry's mod IDs (Story 16.2)
  const installedMod = findInstalledModForEntry(modsData?.data?.mods, {
    slug: slug ?? '',
    releases: mod.releases,
  });

  // Story 17.2: the "Latest" badge marks the release a plain install picks
  const latestReleaseIndex = mod.releases.findIndex(
    (release) => release.modidstr === mod.installModId && release.version === mod.latestVersion
  );

  // Sanitize HTML description for safe rendering (shared sanitizer, Story 16.4)
  const sanitizedDescription = mod.description ? sanitizeModDescription(mod.description) : null;

  // Story 18.1: media are optional; a response without the list shows no gallery
  // instead of failing the page (the guard above covers only the required fields)
  const screenshots = Array.isArray(mod.screenshots) ? mod.screenshots : [];

  return (
    <div className="container mx-auto py-6 max-w-4xl space-y-6" data-testid="mod-detail-page">
      {/* Navigation: Back button and Breadcrumbs */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <BackToBrowseButton onClick={handleBack} />

        {/* Breadcrumb navigation */}
        <nav
          className="flex min-w-0 flex-wrap items-center gap-1 text-sm text-muted-foreground"
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
            to={browseTarget}
            state={MOD_DETAIL_RETURN_STATE}
            className="hover:text-foreground transition-colors"
            data-testid="mod-detail-breadcrumb-browse"
          >
            Browse
          </Link>
          <ChevronRight className="h-4 w-4" />
          <span
            className="min-w-0 break-words text-foreground font-medium"
            data-testid="mod-detail-breadcrumb-name"
          >
            {mod.name}
          </span>
        </nav>
      </div>

      {/* Header section. Story 21.6: below md the install card goes under the logo and
          info at full width; the info goes under the logo when the two do not fit side by
          side (basis-48). From md up the three are one row, as before. */}
      <div className="flex flex-col gap-4 md:flex-row md:gap-6" data-testid="mod-detail-header">
        <div
          className="flex min-w-0 flex-wrap gap-4 md:flex-1 md:flex-nowrap md:gap-6"
          data-testid="mod-detail-summary"
        >
          {/* Logo */}
          <div className="flex-shrink-0">
            <div
              className="h-32 w-32 rounded-lg bg-muted flex items-center justify-center overflow-hidden"
              data-testid="mod-detail-logo"
            >
              {mod.logoUrl ? (
                <img
                  src={mod.logoUrl}
                  referrerPolicy="no-referrer"
                  alt={`${mod.name} logo`}
                  className="h-full w-full object-cover"
                />
              ) : (
                <Package className="h-16 w-16 text-muted-foreground" />
              )}
            </div>
          </div>

          {/* Info */}
          <div className="min-w-0 grow basis-48 space-y-2 break-words">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <h1 className="text-2xl font-bold break-words" data-testid="mod-detail-name">
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

            {/* Story 16.3: the message names the most recent supported game version;
              shown as text because touch screens never show the badge tooltip */}
            {mod.compatibility.status !== 'compatible' && mod.compatibility.message && (
              <p
                className="text-sm text-muted-foreground"
                data-testid="mod-detail-compatibility-message"
              >
                {mod.compatibility.message}
              </p>
            )}

            {/* Stats row */}
            <div
              className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground"
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
              {/* Story 16.3: the release the compatibility badge describes (the installed
                mod ID's newest release), which can differ from the entry's newest */}
              <span>Version: {mod.compatibility.modVersion ?? mod.latestVersion}</span>
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
            <div className="flex flex-wrap items-center gap-3 gap-y-1 pt-1">
              <NewTabLink
                href={`https://mods.vintagestory.at/show/mod/${mod.assetId}`}
                className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
                data-testid="mod-detail-moddb-link"
              >
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                ModDB Page
              </NewTabLink>
              {mod.homepageUrl && (
                <NewTabLink
                  href={mod.homepageUrl}
                  className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
                  data-testid="mod-detail-homepage-link"
                >
                  <Globe className="h-3.5 w-3.5" aria-hidden="true" />
                  Homepage
                  <ExternalLink
                    className="h-3 w-3"
                    aria-hidden="true"
                    data-testid="mod-detail-homepage-new-tab-mark"
                  />
                </NewTabLink>
              )}
              {mod.sourceUrl && (
                <NewTabLink
                  href={mod.sourceUrl}
                  className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
                  data-testid="mod-detail-source-link"
                >
                  <Code className="h-3.5 w-3.5" aria-hidden="true" />
                  Source
                  <ExternalLink
                    className="h-3 w-3"
                    aria-hidden="true"
                    data-testid="mod-detail-source-new-tab-mark"
                  />
                </NewTabLink>
              )}
              {/* Story 18.1: a link, never an embed; the API built the URL from the video ID */}
              {mod.trailerUrl && (
                <NewTabLink
                  href={mod.trailerUrl}
                  className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
                  data-testid="mod-detail-trailer-link"
                >
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                  Watch trailer
                </NewTabLink>
              )}
            </div>
          </div>
        </div>

        {/* Install section, or version section when installed (Story 14.3) */}
        {mod.releases.length > 0 &&
          (installedMod ? (
            <InstalledVersionSection
              slug={installedMod.slug}
              installModId={mod.installModId}
              latestVersion={mod.latestVersion}
              name={mod.name}
              installedVersion={installedMod.version}
              releases={mod.releases}
            />
          ) : (
            <InstallSection
              slug={mod.installModId}
              name={mod.name}
              author={mod.author}
              logoUrl={mod.logoUrl}
              latestVersion={mod.latestVersion}
              releases={mod.releases}
              compatibilityStatus={mod.compatibility?.status ?? 'not_verified'}
              compatibilityMessage={mod.compatibility?.message}
            />
          ))}
      </div>

      <Separator />

      {/* Screenshots section (Story 18.1) */}
      {screenshots.length > 0 && <ModScreenshotGallery key={mod.slug} screenshots={screenshots} />}

      {/* Description section */}
      <Card data-testid="mod-detail-description-card">
        <CardHeader>
          <CardTitle className="text-lg">Description</CardTitle>
        </CardHeader>
        <CardContent>
          {sanitizedDescription ? (
            <div
              className="mod-description"
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
          <CardTitle className="text-lg">Releases ({mod.releases.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {mod.releases.length > 0 ? (
            <div data-testid="mod-detail-releases-list">
              {mod.releases.map((release, index) => (
                <ReleaseItem
                  // Several mod IDs can list one version, and a version can be
                  // re-uploaded, so neither the version nor mod ID + version is unique
                  key={`${release.modidstr}:${release.version}:${index}`}
                  release={release}
                  isLatest={index === latestReleaseIndex}
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
            <dd className="font-mono text-xs break-all" data-testid="mod-detail-slug">
              {mod.slug}
            </dd>
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
