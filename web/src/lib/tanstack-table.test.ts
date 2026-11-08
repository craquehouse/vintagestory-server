/**
 * Integration test for TanStack Table dependency.
 *
 * Story 6.0: Verify @tanstack/react-table is properly installed and usable.
 * This test validates the dependency can be imported and core functionality works.
 */

import { describe, it, expect } from 'vitest';
import {
  columnFilteringFeature,
  createColumnHelper,
  createCoreRowModel,
  createFilteredRowModel,
  createSortedRowModel,
  filterFns,
  flexRender,
  rowSortingFeature,
  sortFns,
  tableFeatures,
  useTable,
} from '@tanstack/react-table';
import { renderHook } from '@testing-library/react';

// Sample data type for testing
interface TestMod {
  name: string;
  version: string;
  enabled: boolean;
}

const features = tableFeatures({
  rowSortingFeature,
  columnFilteringFeature,
  sortedRowModel: createSortedRowModel(),
  filteredRowModel: createFilteredRowModel(),
  sortFns,
  filterFns,
});

describe('TanStack Table Integration', () => {
  describe('dependency installation', () => {
    it('can import core table functions', () => {
      expect(createColumnHelper).toBeDefined();
      expect(createCoreRowModel).toBeDefined();
      expect(createSortedRowModel).toBeDefined();
      expect(createFilteredRowModel).toBeDefined();
    });
  });

  describe('column helper usage', () => {
    it('can create column definitions with columnHelper', () => {
      const columnHelper = createColumnHelper<typeof features, TestMod>();

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
    it('createCoreRowModel returns a function', () => {
      const rowModel = createCoreRowModel();
      expect(typeof rowModel).toBe('function');
    });

    it('createSortedRowModel returns a function', () => {
      const rowModel = createSortedRowModel();
      expect(typeof rowModel).toBe('function');
    });

    it('createFilteredRowModel returns a function', () => {
      const rowModel = createFilteredRowModel();
      expect(typeof rowModel).toBe('function');
    });
  });

  describe('type safety', () => {
    it('column helper enforces type safety on accessors', () => {
      const columnHelper = createColumnHelper<typeof features, TestMod>();

      // This compiles because 'name' is a valid key of TestMod
      const nameColumn = columnHelper.accessor('name', {
        header: 'Name',
      });

      expect(nameColumn).toBeDefined();
      expect(nameColumn.accessorKey).toBe('name');
    });
  });

  describe('useTable integration', () => {
    const sampleData: TestMod[] = [
      { name: 'CarryCapacity', version: '1.2.0', enabled: true },
      { name: 'ProspectTogether', version: '2.0.1', enabled: false },
      { name: 'AutoMap', version: '0.5.3', enabled: true },
    ];

    const columnHelper = createColumnHelper<typeof features, TestMod>();
    const columns = columnHelper.columns([
      columnHelper.accessor('name', { header: 'Mod Name' }),
      columnHelper.accessor('version', { header: 'Version' }),
      columnHelper.accessor('enabled', { header: 'Status' }),
    ]);

    it('can create a table instance with useTable', () => {
      const { result } = renderHook(() =>
        useTable({
          data: sampleData,
          columns,
          features,
        })
      );

      expect(result.current).toBeDefined();
      expect(result.current.getRowModel().rows).toHaveLength(3);
    });

    it('returns correct header groups', () => {
      const { result } = renderHook(() =>
        useTable({
          data: sampleData,
          columns,
          features,
        })
      );

      const headerGroups = result.current.getHeaderGroups();
      expect(headerGroups).toHaveLength(1);
      expect(headerGroups[0].headers).toHaveLength(3);
    });

    it('can access cell values from rows', () => {
      const { result } = renderHook(() =>
        useTable({
          data: sampleData,
          columns,
          features,
        })
      );

      const rows = result.current.getRowModel().rows;
      const firstRow = rows[0];

      expect(firstRow.original.name).toBe('CarryCapacity');
      expect(firstRow.original.version).toBe('1.2.0');
      expect(firstRow.original.enabled).toBe(true);
    });

    it('supports sorting with createSortedRowModel', () => {
      const { result } = renderHook(() =>
        useTable({
          data: sampleData,
          columns,
          features,
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

    it('supports filtering with createFilteredRowModel', () => {
      const { result } = renderHook(() =>
        useTable({
          data: sampleData,
          columns,
          features,
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
        useTable({
          data: sampleData,
          columns,
          features,
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
