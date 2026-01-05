import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FileViewer } from './FileViewer';
import '@testing-library/jest-dom';

describe('FileViewer', () => {
  const mockContent = {
    ServerName: 'My Test Server',
    Port: 42420,
    MaxClients: 16,
    Password: '',
    Advertising: false,
  };

  describe('loading state', () => {
    it('shows loading skeletons when isLoading is true', () => {
      render(
        <FileViewer
          filename="serverconfig.json"
          content={null}
          isLoading={true}
        />
      );

      expect(screen.getByTestId('file-viewer-loading')).toBeInTheDocument();
    });

    it('does not render content when loading', () => {
      render(
        <FileViewer
          filename="serverconfig.json"
          content={mockContent}
          isLoading={true}
        />
      );

      expect(screen.queryByTestId('file-viewer')).not.toBeInTheDocument();
      expect(screen.queryByTestId('file-viewer-content')).not.toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('shows error message when error is provided', () => {
      render(
        <FileViewer
          filename="serverconfig.json"
          content={null}
          error="Config file not found: serverconfig.json"
        />
      );

      expect(screen.getByTestId('file-viewer-error')).toBeInTheDocument();
      expect(screen.getByText('Failed to load file')).toBeInTheDocument();
      expect(screen.getByText('Config file not found: serverconfig.json')).toBeInTheDocument();
    });

    it('shows error icon', () => {
      render(
        <FileViewer
          filename="serverconfig.json"
          content={null}
          error="Some error"
        />
      );

      const errorContainer = screen.getByTestId('file-viewer-error');
      expect(errorContainer.querySelector('svg')).toBeInTheDocument();
    });

    it('does not render content when error occurs', () => {
      render(
        <FileViewer
          filename="serverconfig.json"
          content={mockContent}
          error="Some error"
        />
      );

      expect(screen.queryByTestId('file-viewer')).not.toBeInTheDocument();
      expect(screen.queryByTestId('file-viewer-content')).not.toBeInTheDocument();
    });
  });

  describe('no file selected state (AC: 4)', () => {
    it('shows prompt when no file is selected', () => {
      render(
        <FileViewer
          filename={null}
          content={null}
        />
      );

      expect(screen.getByTestId('file-viewer-empty')).toBeInTheDocument();
      expect(screen.getByText('Select a file to view its contents')).toBeInTheDocument();
    });

    it('shows file icon in empty state', () => {
      render(
        <FileViewer
          filename={null}
          content={null}
        />
      );

      const emptyContainer = screen.getByTestId('file-viewer-empty');
      expect(emptyContainer.querySelector('svg')).toBeInTheDocument();
    });
  });

  describe('content display (AC: 2, 3)', () => {
    it('displays formatted JSON content', () => {
      render(
        <FileViewer
          filename="serverconfig.json"
          content={mockContent}
        />
      );

      expect(screen.getByTestId('file-viewer')).toBeInTheDocument();
      const contentElement = screen.getByTestId('file-viewer-content');
      expect(contentElement).toBeInTheDocument();

      // Check that content is properly formatted with indentation
      const expectedJson = JSON.stringify(mockContent, null, 2);
      expect(contentElement.textContent).toBe(expectedJson);
    });

    it('displays filename in header', () => {
      render(
        <FileViewer
          filename="serverconfig.json"
          content={mockContent}
        />
      );

      expect(screen.getByText('serverconfig.json')).toBeInTheDocument();
    });

    it('uses monospace font for content', () => {
      render(
        <FileViewer
          filename="serverconfig.json"
          content={mockContent}
        />
      );

      const contentElement = screen.getByTestId('file-viewer-content');
      expect(contentElement).toHaveClass('font-mono');
    });

    it('preserves whitespace in content', () => {
      render(
        <FileViewer
          filename="serverconfig.json"
          content={mockContent}
        />
      );

      const contentElement = screen.getByTestId('file-viewer-content');
      expect(contentElement).toHaveClass('whitespace-pre');
    });

    it('renders content in a pre tag for formatting', () => {
      render(
        <FileViewer
          filename="serverconfig.json"
          content={mockContent}
        />
      );

      const contentElement = screen.getByTestId('file-viewer-content');
      expect(contentElement.tagName).toBe('PRE');
    });
  });

  describe('different content types', () => {
    it('handles nested objects', () => {
      const nestedContent = {
        Server: {
          Name: 'Test',
          Settings: {
            MaxPlayers: 16,
            PvP: true,
          },
        },
      };

      render(
        <FileViewer
          filename="config.json"
          content={nestedContent}
        />
      );

      const contentElement = screen.getByTestId('file-viewer-content');
      const expectedJson = JSON.stringify(nestedContent, null, 2);
      expect(contentElement.textContent).toBe(expectedJson);
    });

    it('handles arrays', () => {
      const arrayContent = {
        Mods: ['mod1', 'mod2', 'mod3'],
        AdminIds: [12345, 67890],
      };

      render(
        <FileViewer
          filename="mods.json"
          content={arrayContent}
        />
      );

      const contentElement = screen.getByTestId('file-viewer-content');
      expect(contentElement.textContent).toContain('"Mods"');
      expect(contentElement.textContent).toContain('"mod1"');
    });

    it('handles empty object', () => {
      render(
        <FileViewer
          filename="empty.json"
          content={{}}
        />
      );

      const contentElement = screen.getByTestId('file-viewer-content');
      expect(contentElement.textContent).toBe('{}');
    });

    it('handles null content when filename is provided', () => {
      render(
        <FileViewer
          filename="config.json"
          content={null}
        />
      );

      const contentElement = screen.getByTestId('file-viewer-content');
      expect(contentElement.textContent).toBe('null');
    });

    it('handles primitive values', () => {
      render(
        <FileViewer
          filename="value.json"
          content="simple string"
        />
      );

      const contentElement = screen.getByTestId('file-viewer-content');
      expect(contentElement.textContent).toBe('"simple string"');
    });

    it('handles boolean values', () => {
      render(
        <FileViewer
          filename="bool.json"
          content={true}
        />
      );

      const contentElement = screen.getByTestId('file-viewer-content');
      expect(contentElement.textContent).toBe('true');
    });

    it('handles numeric values', () => {
      render(
        <FileViewer
          filename="number.json"
          content={42}
        />
      );

      const contentElement = screen.getByTestId('file-viewer-content');
      expect(contentElement.textContent).toBe('42');
    });
  });

  describe('styling', () => {
    it('applies custom className', () => {
      render(
        <FileViewer
          filename="serverconfig.json"
          content={mockContent}
          className="custom-class"
        />
      );

      expect(screen.getByTestId('file-viewer')).toHaveClass('custom-class');
    });

    it('applies custom className to loading state', () => {
      render(
        <FileViewer
          filename="serverconfig.json"
          content={null}
          isLoading={true}
          className="custom-class"
        />
      );

      expect(screen.getByTestId('file-viewer-loading')).toHaveClass('custom-class');
    });

    it('applies custom className to error state', () => {
      render(
        <FileViewer
          filename="serverconfig.json"
          content={null}
          error="Error"
          className="custom-class"
        />
      );

      expect(screen.getByTestId('file-viewer-error')).toHaveClass('custom-class');
    });

    it('applies custom className to empty state', () => {
      render(
        <FileViewer
          filename={null}
          content={null}
          className="custom-class"
        />
      );

      expect(screen.getByTestId('file-viewer-empty')).toHaveClass('custom-class');
    });
  });

  describe('state priority', () => {
    it('prioritizes loading over error', () => {
      render(
        <FileViewer
          filename="config.json"
          content={null}
          isLoading={true}
          error="Some error"
        />
      );

      expect(screen.getByTestId('file-viewer-loading')).toBeInTheDocument();
      expect(screen.queryByTestId('file-viewer-error')).not.toBeInTheDocument();
    });

    it('prioritizes error over no filename', () => {
      render(
        <FileViewer
          filename={null}
          content={null}
          error="Some error"
        />
      );

      expect(screen.getByTestId('file-viewer-error')).toBeInTheDocument();
      expect(screen.queryByTestId('file-viewer-empty')).not.toBeInTheDocument();
    });
  });

  describe('word wrap (UI-022)', () => {
    it('does not show toggle button when onWordWrapChange is not provided', () => {
      render(
        <FileViewer
          filename="serverconfig.json"
          content={mockContent}
        />
      );

      expect(screen.queryByTestId('file-viewer-wrap-toggle')).not.toBeInTheDocument();
    });

    it('shows toggle button when onWordWrapChange is provided', () => {
      const handleChange = vi.fn();
      render(
        <FileViewer
          filename="serverconfig.json"
          content={mockContent}
          onWordWrapChange={handleChange}
        />
      );

      expect(screen.getByTestId('file-viewer-wrap-toggle')).toBeInTheDocument();
    });

    it('applies whitespace-pre class when wordWrap is false (default)', () => {
      render(
        <FileViewer
          filename="serverconfig.json"
          content={mockContent}
        />
      );

      const contentElement = screen.getByTestId('file-viewer-content');
      expect(contentElement).toHaveClass('whitespace-pre');
      expect(contentElement).not.toHaveClass('whitespace-pre-wrap');
    });

    it('applies whitespace-pre-wrap and break-words classes when wordWrap is true', () => {
      render(
        <FileViewer
          filename="serverconfig.json"
          content={mockContent}
          wordWrap={true}
        />
      );

      const contentElement = screen.getByTestId('file-viewer-content');
      expect(contentElement).toHaveClass('whitespace-pre-wrap');
      expect(contentElement).toHaveClass('break-words');
      expect(contentElement).not.toHaveClass('whitespace-pre');
    });

    it('calls onWordWrapChange with toggled value when button is clicked', async () => {
      const user = userEvent.setup();
      const handleChange = vi.fn();

      render(
        <FileViewer
          filename="serverconfig.json"
          content={mockContent}
          wordWrap={false}
          onWordWrapChange={handleChange}
        />
      );

      await user.click(screen.getByTestId('file-viewer-wrap-toggle'));

      expect(handleChange).toHaveBeenCalledWith(true);
    });

    it('calls onWordWrapChange with false when wordWrap is true and button clicked', async () => {
      const user = userEvent.setup();
      const handleChange = vi.fn();

      render(
        <FileViewer
          filename="serverconfig.json"
          content={mockContent}
          wordWrap={true}
          onWordWrapChange={handleChange}
        />
      );

      await user.click(screen.getByTestId('file-viewer-wrap-toggle'));

      expect(handleChange).toHaveBeenCalledWith(false);
    });

    it('toggle button shows active state when wordWrap is true', () => {
      render(
        <FileViewer
          filename="serverconfig.json"
          content={mockContent}
          wordWrap={true}
          onWordWrapChange={vi.fn()}
        />
      );

      const toggleButton = screen.getByTestId('file-viewer-wrap-toggle');
      expect(toggleButton).toHaveClass('bg-accent');
    });

    it('toggle button has appropriate title when wordWrap is false', () => {
      render(
        <FileViewer
          filename="serverconfig.json"
          content={mockContent}
          wordWrap={false}
          onWordWrapChange={vi.fn()}
        />
      );

      const toggleButton = screen.getByTestId('file-viewer-wrap-toggle');
      expect(toggleButton).toHaveAttribute('title', 'Enable word wrap');
    });

    it('toggle button has appropriate title when wordWrap is true', () => {
      render(
        <FileViewer
          filename="serverconfig.json"
          content={mockContent}
          wordWrap={true}
          onWordWrapChange={vi.fn()}
        />
      );

      const toggleButton = screen.getByTestId('file-viewer-wrap-toggle');
      expect(toggleButton).toHaveAttribute('title', 'Disable word wrap');
    });
  });

  describe('JSON syntax highlighting (Story 9.6)', () => {
    describe('AC 1: syntax colorization applied to .json files', () => {
      it('applies syntax highlighting to .json file content', () => {
        render(
          <FileViewer
            filename="serverconfig.json"
            content={mockContent}
          />
        );

        const contentElement = screen.getByTestId('file-viewer-content');
        // Should have JSON key spans with the correct class
        expect(contentElement.querySelector('.json-key')).toBeInTheDocument();
      });

      it('applies highlighting for various JSON file extensions', () => {
        render(
          <FileViewer
            filename="CONFIG.JSON"
            content={{ key: 'value' }}
          />
        );

        const contentElement = screen.getByTestId('file-viewer-content');
        expect(contentElement.querySelector('.json-key')).toBeInTheDocument();
      });
    });

    describe('AC 2: distinct colors for different token types', () => {
      it('highlights keys with json-key class', () => {
        render(
          <FileViewer
            filename="config.json"
            content={{ myKey: 'value' }}
          />
        );

        const contentElement = screen.getByTestId('file-viewer-content');
        const keyElement = contentElement.querySelector('.json-key');

        expect(keyElement).toBeInTheDocument();
        expect(keyElement?.textContent).toBe('"myKey"');
      });

      it('highlights string values with json-string class', () => {
        render(
          <FileViewer
            filename="config.json"
            content={{ name: 'testValue' }}
          />
        );

        const contentElement = screen.getByTestId('file-viewer-content');
        const stringElement = contentElement.querySelector('.json-string');

        expect(stringElement).toBeInTheDocument();
        expect(stringElement?.textContent).toBe('"testValue"');
      });

      it('highlights numbers with json-number class', () => {
        render(
          <FileViewer
            filename="config.json"
            content={{ port: 42420 }}
          />
        );

        const contentElement = screen.getByTestId('file-viewer-content');
        const numberElement = contentElement.querySelector('.json-number');

        expect(numberElement).toBeInTheDocument();
        expect(numberElement?.textContent).toBe('42420');
      });

      it('highlights booleans with json-boolean class', () => {
        render(
          <FileViewer
            filename="config.json"
            content={{ enabled: true }}
          />
        );

        const contentElement = screen.getByTestId('file-viewer-content');
        const booleanElement = contentElement.querySelector('.json-boolean');

        expect(booleanElement).toBeInTheDocument();
        expect(booleanElement?.textContent).toBe('true');
      });

      it('highlights null with json-null class', () => {
        render(
          <FileViewer
            filename="config.json"
            content={{ password: null }}
          />
        );

        const contentElement = screen.getByTestId('file-viewer-content');
        const nullElement = contentElement.querySelector('.json-null');

        expect(nullElement).toBeInTheDocument();
        expect(nullElement?.textContent).toBe('null');
      });

      it('highlights all token types in complex object', () => {
        const complexContent = {
          name: 'Test Server',
          port: 8080,
          enabled: true,
          password: null,
        };

        render(
          <FileViewer
            filename="config.json"
            content={complexContent}
          />
        );

        const contentElement = screen.getByTestId('file-viewer-content');

        // All distinct token types should be highlighted
        expect(contentElement.querySelectorAll('.json-key').length).toBeGreaterThanOrEqual(4);
        expect(contentElement.querySelector('.json-string')).toBeInTheDocument();
        expect(contentElement.querySelector('.json-number')).toBeInTheDocument();
        expect(contentElement.querySelector('.json-boolean')).toBeInTheDocument();
        expect(contentElement.querySelector('.json-null')).toBeInTheDocument();
      });
    });

    describe('AC 3: no colorization for non-JSON files', () => {
      it('does not apply syntax highlighting to .txt files', () => {
        render(
          <FileViewer
            filename="readme.txt"
            content={{ key: 'value' }}
          />
        );

        const contentElement = screen.getByTestId('file-viewer-content');

        // Should NOT have JSON highlighting classes
        expect(contentElement.querySelector('.json-key')).not.toBeInTheDocument();
        expect(contentElement.querySelector('.json-string')).not.toBeInTheDocument();
      });

      it('does not apply syntax highlighting to .xml files', () => {
        render(
          <FileViewer
            filename="config.xml"
            content={{ setting: 'value' }}
          />
        );

        const contentElement = screen.getByTestId('file-viewer-content');
        expect(contentElement.querySelector('.json-key')).not.toBeInTheDocument();
      });

      it('does not apply syntax highlighting to files without extension', () => {
        render(
          <FileViewer
            filename="Makefile"
            content={{ target: 'all' }}
          />
        );

        const contentElement = screen.getByTestId('file-viewer-content');
        expect(contentElement.querySelector('.json-key')).not.toBeInTheDocument();
      });

      it('renders plain JSON text for non-JSON files', () => {
        const content = { key: 'value' };
        render(
          <FileViewer
            filename="config.dat"
            content={content}
          />
        );

        const contentElement = screen.getByTestId('file-viewer-content');
        const expectedText = JSON.stringify(content, null, 2);
        expect(contentElement.textContent).toBe(expectedText);
      });
    });

    describe('AC 4: graceful handling of edge cases', () => {
      it('handles empty object gracefully', () => {
        render(
          <FileViewer
            filename="empty.json"
            content={{}}
          />
        );

        const contentElement = screen.getByTestId('file-viewer-content');
        expect(contentElement.textContent).toBe('{}');
      });

      it('handles empty array gracefully', () => {
        render(
          <FileViewer
            filename="list.json"
            content={[]}
          />
        );

        const contentElement = screen.getByTestId('file-viewer-content');
        expect(contentElement.textContent).toBe('[]');
      });

      it('handles null content gracefully', () => {
        render(
          <FileViewer
            filename="null.json"
            content={null}
          />
        );

        const contentElement = screen.getByTestId('file-viewer-content');
        expect(contentElement.textContent).toBe('null');
        expect(contentElement.querySelector('.json-null')).toBeInTheDocument();
      });

      it('handles deeply nested objects', () => {
        const nestedContent = {
          level1: {
            level2: {
              level3: {
                value: 'deep',
              },
            },
          },
        };

        render(
          <FileViewer
            filename="nested.json"
            content={nestedContent}
          />
        );

        const contentElement = screen.getByTestId('file-viewer-content');

        // Should have multiple key highlights for nested structure
        expect(contentElement.querySelectorAll('.json-key').length).toBe(4);
        expect(contentElement.querySelector('.json-string')).toBeInTheDocument();
      });

      it('handles arrays with mixed content types', () => {
        const arrayContent = {
          items: ['string', 42, true, null],
        };

        render(
          <FileViewer
            filename="mixed.json"
            content={arrayContent}
          />
        );

        const contentElement = screen.getByTestId('file-viewer-content');

        expect(contentElement.querySelector('.json-string')).toBeInTheDocument();
        expect(contentElement.querySelector('.json-number')).toBeInTheDocument();
        expect(contentElement.querySelector('.json-boolean')).toBeInTheDocument();
        expect(contentElement.querySelector('.json-null')).toBeInTheDocument();
      });

      it('preserves JSON structure after highlighting', () => {
        const content = {
          name: 'Test',
          count: 42,
        };

        render(
          <FileViewer
            filename="test.json"
            content={content}
          />
        );

        const contentElement = screen.getByTestId('file-viewer-content');
        const expectedText = JSON.stringify(content, null, 2);

        // Text content should match original formatted JSON
        expect(contentElement.textContent).toBe(expectedText);
      });
    });
  });
});
