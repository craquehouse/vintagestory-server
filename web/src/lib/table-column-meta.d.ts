/**
 * Typed column meta for TanStack Table (Story 18.4).
 *
 * TanStack Table declares `ColumnMeta` empty, for module augmentation. Columns here use
 * `meta.className` for the classes of their header and body cells, so reading it needs
 * no type assertion.
 */
import '@tanstack/react-table';
import type { CellData, RowData, TableFeatures } from '@tanstack/react-table';

declare module '@tanstack/react-table' {
  interface ColumnMeta<
    TFeatures extends TableFeatures,
    TData extends RowData,
    TValue extends CellData = CellData,
  > {
    /** Classes for the column's header and body cells */
    className?: string;
  }
}
