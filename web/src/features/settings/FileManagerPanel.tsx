/**
 * FileManagerPanel component for browsing and viewing configuration files.
 *
 * Composes FileList and FileViewer in a split layout with selection state.
 * Uses hooks to fetch file list and content from the API.
 *
 * Story 6.6: File Manager UI - AC: 1, 2, 3, 4, 5
 * Story 9.7: Dynamic File Browser - Directory navigation
 * Story 16.7: File Browser Breadcrumbs - path segments replace the Back button
 * Story 19.1: a note for roles other than Admin, which see fewer folders (FR233)
 * Story 23.2: paths are lists of directory names, joined only by the API client (FR312)
 */

import { useState, useMemo } from 'react';
import { AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { FileList, type FileListItem } from '@/components/FileList';
import { FileViewer } from '@/components/FileViewer';
import { PathBreadcrumb } from '@/components/PathBreadcrumb';
import { useAuthMe } from '@/api/hooks/use-auth-me';
import { toConfigPath } from '@/api/config';
import {
  useConfigFiles,
  useConfigFileContent,
  useConfigDirectories,
} from '@/hooks/use-config-files';

/** Label of the breadcrumb root: the serverdata directory the API lists (Story 16.7). */
const ROOT_LABEL = 'serverdata';

/** A selected file: the directory names it is in, and its name (Story 23.2). */
interface SelectedFile {
  directory: string[];
  name: string;
}

/** The selected file's path for display; the plain join when a name is invalid. */
function displayPath(file: SelectedFile): string {
  const segments = [...file.directory, file.name];
  try {
    return toConfigPath(segments);
  } catch {
    // The read refuses the same name and shows its error; the header still names the file
    return segments.join('/');
  }
}

/**
 * Props for the FileManagerPanel component.
 */
export interface FileManagerPanelProps {
  /**
   * Additional CSS class names.
   */
  className?: string;
}

/**
 * Panel for browsing and viewing configuration files.
 *
 * Displays a file list on the left and file viewer on the right.
 * Manages file selection state and data fetching.
 * Supports directory navigation (Story 9.7) with a breadcrumb of the current path
 * across the top of the panel (Story 16.7).
 *
 * @example
 * <FileManagerPanel />
 */
export function FileManagerPanel({ className }: FileManagerPanelProps) {
  const [selectedFile, setSelectedFile] = useState<SelectedFile | null>(null);
  const [wordWrap, setWordWrap] = useState(false);
  // Story 9.7: Current directory; Story 23.2: a list of names ([] = root)
  const [currentDirectory, setCurrentDirectory] = useState<string[]>([]);

  // Story 19.1 (FR233): roles other than Admin are shown fewer folders by the API. Hidden
  // while the role is loading or could not be loaded (role undefined).
  const { data: auth } = useAuthMe();
  const role = auth?.data?.role;
  const showAdminNote = role !== undefined && role !== 'admin';

  // Fetch directories for the current path (Story 9.7 - nested directory support)
  const { data: directoriesData, isLoading: isLoadingDirectories } =
    useConfigDirectories(currentDirectory);

  // Fetch file list (with directory support - Story 9.7)
  const {
    data: filesData,
    isLoading: isLoadingFiles,
    error: filesError,
  } = useConfigFiles(currentDirectory);

  // Fetch selected file content
  const {
    data: contentData,
    isLoading: isLoadingContent,
    error: contentError,
  } = useConfigFileContent(selectedFile ? [...selectedFile.directory, selectedFile.name] : null);

  // Combine directories and files into items list
  const items = useMemo<FileListItem[]>(() => {
    const result: FileListItem[] = [];

    // Show directories at any level (Story 9.7 - nested directory support)
    if (directoriesData?.data?.directories) {
      // Filter hidden directories by default
      const visibleDirs = directoriesData.data.directories.filter((d) => !d.startsWith('.'));
      for (const dir of visibleDirs) {
        result.push({ name: dir, type: 'directory' });
      }
    }

    // Add files
    if (filesData?.data?.files) {
      for (const file of filesData.data.files) {
        result.push({ name: file, type: 'file' });
      }
    }

    return result;
  }, [directoriesData, filesData]);

  // Handle file selection
  const handleSelectFile = (filename: string) => {
    setSelectedFile({ directory: currentDirectory, name: filename });
  };

  // Handle directory navigation (Story 9.7 - nested directory support)
  const handleSelectDirectory = (dirname: string) => {
    setCurrentDirectory([...currentDirectory, dirname]);
    setSelectedFile(null); // Clear selection when changing directories
  };

  // Breadcrumb navigation to the root ([]) or an ancestor of the current path (Story 16.7)
  const handleNavigate = (segments: string[]) => {
    setCurrentDirectory(segments);
    setSelectedFile(null);
  };

  const breadcrumb = (
    <PathBreadcrumb
      segments={currentDirectory}
      rootLabel={ROOT_LABEL}
      onNavigate={handleNavigate}
    />
  );

  const selectedPath = selectedFile ? displayPath(selectedFile) : null;
  // The list shows names in the current directory: highlight the selected file only there
  // (Story 23.2; before, the full path was compared with the bare name, so a file in a
  // subfolder was never highlighted)
  const selectedNameHere =
    selectedFile &&
    selectedFile.directory.length === currentDirectory.length &&
    selectedFile.directory.every((name, index) => name === currentDirectory[index])
      ? selectedFile.name
      : null;

  // Combined loading state
  const isLoading = isLoadingFiles || isLoadingDirectories;

  // Error state for file list
  if (filesError) {
    return (
      <div className={className} data-testid="file-manager-error">
        {/* Keep the breadcrumb so a failed subdirectory is not a dead end (Story 16.7) */}
        {currentDirectory.length > 0 && <div className="mb-2 px-1">{breadcrumb}</div>}
        <div className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <AlertCircle className="h-5 w-5 text-destructive" />
          <div>
            <p className="font-medium text-destructive">Failed to load files</p>
            <p className="text-sm text-muted-foreground">
              {filesError.message || 'Unable to load configuration files'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn('flex h-[500px] flex-col rounded-lg border bg-card', className)}
      data-testid="file-manager-panel"
    >
      {/* Current path across the panel (Story 16.7) */}
      <div className="min-w-0 border-b px-3 py-2" data-testid="file-manager-breadcrumb-bar">
        {breadcrumb}
      </div>

      {showAdminNote && (
        <p
          data-testid="file-manager-admin-note"
          className="border-b px-3 py-1.5 text-xs text-muted-foreground"
        >
          Some folders are only shown to Admin keys.
        </p>
      )}

      <div className="flex min-h-0 flex-1">
        {/* File List - Left Side */}
        <div className="w-56 shrink-0 border-r flex flex-col">
          <FileList
            items={items}
            selectedFile={selectedNameHere}
            isLoading={isLoading}
            onSelectFile={handleSelectFile}
            onSelectDirectory={handleSelectDirectory}
            className="flex-1 overflow-auto"
          />
        </div>

        {/* File Viewer - Right Side */}
        <div className="flex-1 min-w-0">
          <FileViewer
            filename={selectedPath}
            content={contentData?.data?.content ?? null}
            isLoading={isLoadingContent}
            error={contentError?.message ?? null}
            wordWrap={wordWrap}
            onWordWrapChange={setWordWrap}
            parseError={contentData?.data?.parseError ?? null}
            text={contentData?.data?.text}
            className="h-full"
          />
        </div>
      </div>
    </div>
  );
}
