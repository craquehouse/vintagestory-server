import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { FileList } from './FileList';

describe('FileList', () => {
  const mockFiles = ['serverconfig.json', 'worldconfig.json', 'clientsettings.json'];
  const mockOnSelectFile = vi.fn();

  describe('loading state', () => {
    it('shows loading skeletons when isLoading is true', () => {
      render(
        <FileList
          files={[]}
          selectedFile={null}
          isLoading={true}
          onSelectFile={mockOnSelectFile}
        />
      );

      expect(screen.getByTestId('file-list-loading')).toBeInTheDocument();
    });

    it('does not render file list when loading', () => {
      render(
        <FileList
          files={mockFiles}
          selectedFile={null}
          isLoading={true}
          onSelectFile={mockOnSelectFile}
        />
      );

      expect(screen.queryByTestId('file-list')).not.toBeInTheDocument();
      expect(screen.queryByTestId('file-item-serverconfig.json')).not.toBeInTheDocument();
    });
  });

  describe('empty state (AC: 5)', () => {
    it('shows empty state when no files are available', () => {
      render(
        <FileList
          files={[]}
          selectedFile={null}
          onSelectFile={mockOnSelectFile}
        />
      );

      expect(screen.getByTestId('file-list-empty')).toBeInTheDocument();
      expect(screen.getByText('No configuration files found')).toBeInTheDocument();
    });

    it('shows folder icon in empty state', () => {
      render(
        <FileList
          files={[]}
          selectedFile={null}
          onSelectFile={mockOnSelectFile}
        />
      );

      // Lucide icons are rendered as SVG elements
      const emptyContainer = screen.getByTestId('file-list-empty');
      expect(emptyContainer.querySelector('svg')).toBeInTheDocument();
    });
  });

  describe('file list rendering (AC: 1)', () => {
    it('renders all files in the list', () => {
      render(
        <FileList
          files={mockFiles}
          selectedFile={null}
          onSelectFile={mockOnSelectFile}
        />
      );

      expect(screen.getByTestId('file-list')).toBeInTheDocument();
      expect(screen.getByTestId('file-item-serverconfig.json')).toBeInTheDocument();
      expect(screen.getByTestId('file-item-worldconfig.json')).toBeInTheDocument();
      expect(screen.getByTestId('file-item-clientsettings.json')).toBeInTheDocument();
    });

    it('displays file names as text', () => {
      render(
        <FileList
          files={mockFiles}
          selectedFile={null}
          onSelectFile={mockOnSelectFile}
        />
      );

      expect(screen.getByText('serverconfig.json')).toBeInTheDocument();
      expect(screen.getByText('worldconfig.json')).toBeInTheDocument();
      expect(screen.getByText('clientsettings.json')).toBeInTheDocument();
    });

    it('renders file items as buttons', () => {
      render(
        <FileList
          files={mockFiles}
          selectedFile={null}
          onSelectFile={mockOnSelectFile}
        />
      );

      const button = screen.getByTestId('file-item-serverconfig.json');
      expect(button.tagName).toBe('BUTTON');
    });

    it('has proper accessibility attributes', () => {
      render(
        <FileList
          files={mockFiles}
          selectedFile="serverconfig.json"
          onSelectFile={mockOnSelectFile}
        />
      );

      const list = screen.getByRole('listbox');
      expect(list).toHaveAttribute('aria-label', 'Configuration files');

      const selectedItem = screen.getByTestId('file-item-serverconfig.json');
      expect(selectedItem).toHaveAttribute('role', 'option');
      expect(selectedItem).toHaveAttribute('aria-selected', 'true');

      const unselectedItem = screen.getByTestId('file-item-worldconfig.json');
      expect(unselectedItem).toHaveAttribute('aria-selected', 'false');
    });
  });

  describe('file selection', () => {
    it('calls onSelectFile when a file is clicked', () => {
      const onSelectFile = vi.fn();
      render(
        <FileList
          files={mockFiles}
          selectedFile={null}
          onSelectFile={onSelectFile}
        />
      );

      fireEvent.click(screen.getByTestId('file-item-serverconfig.json'));

      expect(onSelectFile).toHaveBeenCalledWith('serverconfig.json');
    });

    it('calls onSelectFile with correct filename for each file', () => {
      const onSelectFile = vi.fn();
      render(
        <FileList
          files={mockFiles}
          selectedFile={null}
          onSelectFile={onSelectFile}
        />
      );

      fireEvent.click(screen.getByTestId('file-item-worldconfig.json'));
      expect(onSelectFile).toHaveBeenCalledWith('worldconfig.json');

      fireEvent.click(screen.getByTestId('file-item-clientsettings.json'));
      expect(onSelectFile).toHaveBeenCalledWith('clientsettings.json');
    });

    it('highlights selected file', () => {
      render(
        <FileList
          files={mockFiles}
          selectedFile="serverconfig.json"
          onSelectFile={mockOnSelectFile}
        />
      );

      const selectedItem = screen.getByTestId('file-item-serverconfig.json');
      expect(selectedItem).toHaveClass('bg-accent');
      expect(selectedItem).toHaveClass('font-medium');
    });

    it('does not highlight non-selected files', () => {
      render(
        <FileList
          files={mockFiles}
          selectedFile="serverconfig.json"
          onSelectFile={mockOnSelectFile}
        />
      );

      const unselectedItem = screen.getByTestId('file-item-worldconfig.json');
      expect(unselectedItem).not.toHaveClass('font-medium');
    });

    it('updates selection when selectedFile prop changes', () => {
      const { rerender } = render(
        <FileList
          files={mockFiles}
          selectedFile="serverconfig.json"
          onSelectFile={mockOnSelectFile}
        />
      );

      expect(screen.getByTestId('file-item-serverconfig.json')).toHaveClass('font-medium');
      expect(screen.getByTestId('file-item-worldconfig.json')).not.toHaveClass('font-medium');

      rerender(
        <FileList
          files={mockFiles}
          selectedFile="worldconfig.json"
          onSelectFile={mockOnSelectFile}
        />
      );

      expect(screen.getByTestId('file-item-serverconfig.json')).not.toHaveClass('font-medium');
      expect(screen.getByTestId('file-item-worldconfig.json')).toHaveClass('font-medium');
    });
  });

  describe('styling', () => {
    it('applies custom className', () => {
      render(
        <FileList
          files={mockFiles}
          selectedFile={null}
          onSelectFile={mockOnSelectFile}
          className="custom-class"
        />
      );

      const container = screen.getByTestId('file-list');
      expect(container).toHaveClass('custom-class');
    });

    it('applies custom className to loading state', () => {
      render(
        <FileList
          files={[]}
          selectedFile={null}
          isLoading={true}
          onSelectFile={mockOnSelectFile}
          className="custom-class"
        />
      );

      expect(screen.getByTestId('file-list-loading')).toHaveClass('custom-class');
    });

    it('applies custom className to empty state', () => {
      render(
        <FileList
          files={[]}
          selectedFile={null}
          onSelectFile={mockOnSelectFile}
          className="custom-class"
        />
      );

      expect(screen.getByTestId('file-list-empty')).toHaveClass('custom-class');
    });
  });

  describe('edge cases', () => {
    it('handles single file', () => {
      render(
        <FileList
          files={['only-file.json']}
          selectedFile={null}
          onSelectFile={mockOnSelectFile}
        />
      );

      expect(screen.getByTestId('file-list')).toBeInTheDocument();
      expect(screen.getByText('only-file.json')).toBeInTheDocument();
    });

    it('handles file names with special characters', () => {
      const specialFiles = ['server-config.json', 'world_config.json', 'config (backup).json'];
      render(
        <FileList
          files={specialFiles}
          selectedFile={null}
          onSelectFile={mockOnSelectFile}
        />
      );

      expect(screen.getByText('server-config.json')).toBeInTheDocument();
      expect(screen.getByText('world_config.json')).toBeInTheDocument();
      expect(screen.getByText('config (backup).json')).toBeInTheDocument();
    });

    it('handles selectedFile that is not in the list', () => {
      render(
        <FileList
          files={mockFiles}
          selectedFile="nonexistent.json"
          onSelectFile={mockOnSelectFile}
        />
      );

      // Should not throw and should render normally with no selection highlighted
      expect(screen.getByTestId('file-list')).toBeInTheDocument();
      expect(screen.getByTestId('file-item-serverconfig.json')).not.toHaveClass('font-medium');
    });
  });
});
