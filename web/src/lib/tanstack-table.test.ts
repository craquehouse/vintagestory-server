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
  flexRender,
} from '@tanstack/react-table';
import { useReactTable } from '@tanstack/react-table';
import { renderHook } from '@testing-library/react';

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

  describe('useReactTable integration', () => {
    const sampleData: TestMod[] = [
      { name: 'CarryCapacity', version: '1.2.0', enabled: true },
      { name: 'ProspectTogether', version: '2.0.1', enabled: false },
      { name: 'AutoMap', version: '0.5.3', enabled: true },
    ];

    const columnHelper = createColumnHelper<TestMod>();
    const columns = [
      columnHelper.accessor('name', { header: 'Mod Name' }),
      columnHelper.accessor('version', { header: 'Version' }),
      columnHelper.accessor('enabled', { header: 'Status' }),
    ];

    it('can create a table instance with useReactTable', () => {
      const { result } = renderHook(() =>
        useReactTable({
          data: sampleData,
          columns,
          getCoreRowModel: getCoreRowModel(),
        })
      );

      expect(result.current).toBeDefined();
      expect(result.current.getRowModel().rows).toHaveLength(3);
    });

    it('returns correct header groups', () => {
      const { result } = renderHook(() =>
        useReactTable({
          data: sampleData,
          columns,
          getCoreRowModel: getCoreRowModel(),
        })
      );

      const headerGroups = result.current.getHeaderGroups();
      expect(headerGroups).toHaveLength(1);
      expect(headerGroups[0].headers).toHaveLength(3);
    });

    it('can access cell values from rows', () => {
      const { result } = renderHook(() =>
        useReactTable({
          data: sampleData,
          columns,
          getCoreRowModel: getCoreRowModel(),
        })
      );

      const rows = result.current.getRowModel().rows;
      const firstRow = rows[0];

      expect(firstRow.original.name).toBe('CarryCapacity');
      expect(firstRow.original.version).toBe('1.2.0');
      expect(firstRow.original.enabled).toBe(true);
    });

    it('supports sorting with getSortedRowModel', () => {
      const { result } = renderHook(() =>
        useReactTable({
          data: sampleData,
          columns,
          getCoreRowModel: getCoreRowModel(),
          getSortedRowModel: getSortedRowModel(),
          initialState: {
            sorting: [{ id: 'name', desc: false }],
          },
        })
      );

      const rows = result.current.getRowModel().rows;
      // Sorted alphabetically by name: AutoMap, CarryCapacity, ProspectTogether
      expect(rows[0].original.name).toBe('AutoMap');
      expect(rows[1].original.name).toBe('CarryCapacity');
      expect(rows[2].original.name).toBe('ProspectTogether');
    });

    it('supports filtering with getFilteredRowModel', () => {
      const { result } = renderHook(() =>
        useReactTable({
          data: sampleData,
          columns,
          getCoreRowModel: getCoreRowModel(),
          getFilteredRowModel: getFilteredRowModel(),
          initialState: {
            columnFilters: [{ id: 'enabled', value: true }],
          },
        })
      );

      const rows = result.current.getRowModel().rows;
      // Only enabled mods should be shown
      expect(rows).toHaveLength(2);
      expect(rows.every((row) => row.original.enabled === true)).toBe(true);
    });

    it('flexRender can render cell content', () => {
      const { result } = renderHook(() =>
        useReactTable({
          data: sampleData,
          columns,
          getCoreRowModel: getCoreRowModel(),
        })
      );

      const headerGroups = result.current.getHeaderGroups();
      const firstHeader = headerGroups[0].headers[0];

      // flexRender should return the header value
      const rendered = flexRender(
        firstHeader.column.columnDef.header,
        firstHeader.getContext()
      );
      expect(rendered).toBe('Mod Name');
    });
  });
});
