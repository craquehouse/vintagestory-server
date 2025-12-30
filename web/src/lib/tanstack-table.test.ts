/**
 * Integration test for TanStack Table dependency.
 *
 * Story 6.0: Verify @tanstack/react-table is properly installed and usable.
 * This test validates the dependency can be imported and core functionality works.
 */

import { describe, it, expect } from 'vitest';
import {
  createColumnHelper,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
} from '@tanstack/react-table';

// Sample data type for testing
interface TestMod {
  name: string;
  version: string;
  enabled: boolean;
}

describe('TanStack Table Integration', () => {
  describe('dependency installation', () => {
    it('can import core table functions', () => {
      expect(createColumnHelper).toBeDefined();
      expect(getCoreRowModel).toBeDefined();
      expect(getSortedRowModel).toBeDefined();
      expect(getFilteredRowModel).toBeDefined();
    });
  });

  describe('column helper usage', () => {
    it('can create column definitions with columnHelper', () => {
      const columnHelper = createColumnHelper<TestMod>();

      // Column definitions created with columnHelper
      const nameColumn = columnHelper.accessor('name', {
        header: 'Mod Name',
        cell: (info) => info.getValue(),
      });

      const versionColumn = columnHelper.accessor('version', {
        header: 'Version',
        cell: (info) => `v${info.getValue()}`,
      });

      const enabledColumn = columnHelper.accessor('enabled', {
        header: 'Status',
        cell: (info) => (info.getValue() ? 'Enabled' : 'Disabled'),
      });

      expect(nameColumn.header).toBe('Mod Name');
      expect(versionColumn.header).toBe('Version');
      expect(enabledColumn.header).toBe('Status');
    });
  });

  describe('row model functions', () => {
    it('getCoreRowModel returns a function', () => {
      const rowModel = getCoreRowModel();
      expect(typeof rowModel).toBe('function');
    });

    it('getSortedRowModel returns a function', () => {
      const rowModel = getSortedRowModel();
      expect(typeof rowModel).toBe('function');
    });

    it('getFilteredRowModel returns a function', () => {
      const rowModel = getFilteredRowModel();
      expect(typeof rowModel).toBe('function');
    });
  });

  describe('type safety', () => {
    it('column helper enforces type safety on accessors', () => {
      const columnHelper = createColumnHelper<TestMod>();

      // This compiles because 'name' is a valid key of TestMod
      const nameColumn = columnHelper.accessor('name', {
        header: 'Name',
      });

      expect(nameColumn).toBeDefined();
      expect(nameColumn.accessorKey).toBe('name');
    });
  });
});
