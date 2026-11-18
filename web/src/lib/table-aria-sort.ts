/**
 * The `aria-sort` value of a table column header (Story 21.5, Epic 21 ADR-9), shared by
 * the installed mods table and the Version page table so both announce sorting the same
 * way: `ascending` or `descending` on the sorted column, `none` on the other sortable
 * columns, and no attribute on a column that cannot be sorted.
 *
 * @param canSort - Whether the column can be sorted (`column.getCanSort()`)
 * @param sorted - The column's sort direction (`column.getIsSorted()`)
 */
export function ariaSort(
  canSort: boolean,
  sorted: false | 'asc' | 'desc'
): 'ascending' | 'descending' | 'none' | undefined {
  if (!canSort) return undefined;
  if (sorted === 'asc') return 'ascending';
  if (sorted === 'desc') return 'descending';
  return 'none';
}
