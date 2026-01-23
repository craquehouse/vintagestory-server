/**
 * Tests for table components.
 *
 * Tests table wrapper components that provide semantic HTML table elements
 * with consistent styling and data-slot attributes.
 *
 * Coverage target: Lines 41 (TableFooter) and 96 (TableCaption)
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
} from './table';

describe('Table', () => {
  describe('Table (root)', () => {
    it('renders table with correct data-slot', () => {
      render(
        <Table data-testid="table">
          <tbody>
            <tr>
              <td>Cell</td>
            </tr>
          </tbody>
        </Table>
      );

      const container = screen.getByTestId('table').parentElement;
      expect(container).toHaveAttribute('data-slot', 'table-container');
      expect(screen.getByTestId('table')).toHaveAttribute('data-slot', 'table');
    });

    it('renders as table element', () => {
      render(
        <Table data-testid="table">
          <tbody>
            <tr>
              <td>Cell</td>
            </tr>
          </tbody>
        </Table>
      );

      expect(screen.getByTestId('table')).toBeInstanceOf(HTMLTableElement);
    });

    it('applies custom className', () => {
      render(
        <Table data-testid="table" className="custom-table">
          <tbody>
            <tr>
              <td>Cell</td>
            </tr>
          </tbody>
        </Table>
      );

      expect(screen.getByTestId('table').className).toContain('custom-table');
    });

    it('has default styling classes', () => {
      render(
        <Table data-testid="table">
          <tbody>
            <tr>
              <td>Cell</td>
            </tr>
          </tbody>
        </Table>
      );

      const table = screen.getByTestId('table');
      expect(table.className).toContain('w-full');
      expect(table.className).toContain('caption-bottom');
      expect(table.className).toContain('text-sm');
    });
  });

  describe('TableHeader', () => {
    it('renders thead with correct data-slot', () => {
      render(
        <Table>
          <TableHeader data-testid="table-header">
            <tr>
              <th>Header</th>
            </tr>
          </TableHeader>
        </Table>
      );

      expect(screen.getByTestId('table-header')).toHaveAttribute(
        'data-slot',
        'table-header'
      );
    });

    it('renders as thead element', () => {
      render(
        <Table>
          <TableHeader data-testid="table-header">
            <tr>
              <th>Header</th>
            </tr>
          </TableHeader>
        </Table>
      );

      expect(screen.getByTestId('table-header')).toBeInstanceOf(
        HTMLTableSectionElement
      );
      expect(screen.getByTestId('table-header').tagName).toBe('THEAD');
    });

    it('applies custom className', () => {
      render(
        <Table>
          <TableHeader data-testid="table-header" className="custom-header">
            <tr>
              <th>Header</th>
            </tr>
          </TableHeader>
        </Table>
      );

      expect(screen.getByTestId('table-header').className).toContain(
        'custom-header'
      );
    });
  });

  describe('TableBody', () => {
    it('renders tbody with correct data-slot', () => {
      render(
        <Table>
          <TableBody data-testid="table-body">
            <tr>
              <td>Cell</td>
            </tr>
          </TableBody>
        </Table>
      );

      expect(screen.getByTestId('table-body')).toHaveAttribute(
        'data-slot',
        'table-body'
      );
    });

    it('renders as tbody element', () => {
      render(
        <Table>
          <TableBody data-testid="table-body">
            <tr>
              <td>Cell</td>
            </tr>
          </TableBody>
        </Table>
      );

      expect(screen.getByTestId('table-body')).toBeInstanceOf(
        HTMLTableSectionElement
      );
      expect(screen.getByTestId('table-body').tagName).toBe('TBODY');
    });

    it('applies custom className', () => {
      render(
        <Table>
          <TableBody data-testid="table-body" className="custom-body">
            <tr>
              <td>Cell</td>
            </tr>
          </TableBody>
        </Table>
      );

      expect(screen.getByTestId('table-body').className).toContain('custom-body');
    });
  });

  describe('TableFooter', () => {
    it('renders tfoot with correct data-slot', () => {
      render(
        <Table>
          <TableFooter data-testid="table-footer">
            <tr>
              <td>Footer</td>
            </tr>
          </TableFooter>
        </Table>
      );

      expect(screen.getByTestId('table-footer')).toHaveAttribute(
        'data-slot',
        'table-footer'
      );
    });

    it('renders as tfoot element', () => {
      render(
        <Table>
          <TableFooter data-testid="table-footer">
            <tr>
              <td>Footer</td>
            </tr>
          </TableFooter>
        </Table>
      );

      expect(screen.getByTestId('table-footer')).toBeInstanceOf(
        HTMLTableSectionElement
      );
      expect(screen.getByTestId('table-footer').tagName).toBe('TFOOT');
    });

    it('applies custom className', () => {
      render(
        <Table>
          <TableFooter data-testid="table-footer" className="custom-footer">
            <tr>
              <td>Footer</td>
            </tr>
          </TableFooter>
        </Table>
      );

      expect(screen.getByTestId('table-footer').className).toContain(
        'custom-footer'
      );
    });

    it('has default styling classes', () => {
      render(
        <Table>
          <TableFooter data-testid="table-footer">
            <tr>
              <td>Footer</td>
            </tr>
          </TableFooter>
        </Table>
      );

      const footer = screen.getByTestId('table-footer');
      expect(footer.className).toContain('bg-muted/50');
      expect(footer.className).toContain('border-t');
      expect(footer.className).toContain('font-medium');
    });

    it('renders footer content', () => {
      render(
        <Table>
          <TableFooter data-testid="table-footer">
            <tr>
              <td>Total: 100</td>
            </tr>
          </TableFooter>
        </Table>
      );

      expect(screen.getByTestId('table-footer')).toHaveTextContent('Total: 100');
    });
  });

  describe('TableRow', () => {
    it('renders tr with correct data-slot', () => {
      render(
        <Table>
          <TableBody>
            <TableRow data-testid="table-row">
              <td>Cell</td>
            </TableRow>
          </TableBody>
        </Table>
      );

      expect(screen.getByTestId('table-row')).toHaveAttribute(
        'data-slot',
        'table-row'
      );
    });

    it('renders as tr element', () => {
      render(
        <Table>
          <TableBody>
            <TableRow data-testid="table-row">
              <td>Cell</td>
            </TableRow>
          </TableBody>
        </Table>
      );

      expect(screen.getByTestId('table-row')).toBeInstanceOf(HTMLTableRowElement);
    });

    it('applies custom className', () => {
      render(
        <Table>
          <TableBody>
            <TableRow data-testid="table-row" className="custom-row">
              <td>Cell</td>
            </TableRow>
          </TableBody>
        </Table>
      );

      expect(screen.getByTestId('table-row').className).toContain('custom-row');
    });

    it('has hover and transition styling', () => {
      render(
        <Table>
          <TableBody>
            <TableRow data-testid="table-row">
              <td>Cell</td>
            </TableRow>
          </TableBody>
        </Table>
      );

      const row = screen.getByTestId('table-row');
      expect(row.className).toContain('hover:bg-muted/50');
      expect(row.className).toContain('transition-colors');
    });
  });

  describe('TableHead', () => {
    it('renders th with correct data-slot', () => {
      render(
        <Table>
          <TableHeader>
            <tr>
              <TableHead data-testid="table-head">Header</TableHead>
            </tr>
          </TableHeader>
        </Table>
      );

      expect(screen.getByTestId('table-head')).toHaveAttribute(
        'data-slot',
        'table-head'
      );
    });

    it('renders as th element', () => {
      render(
        <Table>
          <TableHeader>
            <tr>
              <TableHead data-testid="table-head">Header</TableHead>
            </tr>
          </TableHeader>
        </Table>
      );

      expect(screen.getByTestId('table-head')).toBeInstanceOf(
        HTMLTableCellElement
      );
      expect(screen.getByTestId('table-head').tagName).toBe('TH');
    });

    it('applies custom className', () => {
      render(
        <Table>
          <TableHeader>
            <tr>
              <TableHead data-testid="table-head" className="custom-head">
                Header
              </TableHead>
            </tr>
          </TableHeader>
        </Table>
      );

      expect(screen.getByTestId('table-head').className).toContain('custom-head');
    });

    it('has default styling classes', () => {
      render(
        <Table>
          <TableHeader>
            <tr>
              <TableHead data-testid="table-head">Header</TableHead>
            </tr>
          </TableHeader>
        </Table>
      );

      const head = screen.getByTestId('table-head');
      expect(head.className).toContain('text-left');
      expect(head.className).toContain('font-medium');
      expect(head.className).toContain('whitespace-nowrap');
    });
  });

  describe('TableCell', () => {
    it('renders td with correct data-slot', () => {
      render(
        <Table>
          <TableBody>
            <tr>
              <TableCell data-testid="table-cell">Content</TableCell>
            </tr>
          </TableBody>
        </Table>
      );

      expect(screen.getByTestId('table-cell')).toHaveAttribute(
        'data-slot',
        'table-cell'
      );
    });

    it('renders as td element', () => {
      render(
        <Table>
          <TableBody>
            <tr>
              <TableCell data-testid="table-cell">Content</TableCell>
            </tr>
          </TableBody>
        </Table>
      );

      expect(screen.getByTestId('table-cell')).toBeInstanceOf(
        HTMLTableCellElement
      );
      expect(screen.getByTestId('table-cell').tagName).toBe('TD');
    });

    it('applies custom className', () => {
      render(
        <Table>
          <TableBody>
            <tr>
              <TableCell data-testid="table-cell" className="custom-cell">
                Content
              </TableCell>
            </tr>
          </TableBody>
        </Table>
      );

      expect(screen.getByTestId('table-cell').className).toContain('custom-cell');
    });

    it('has default styling classes', () => {
      render(
        <Table>
          <TableBody>
            <tr>
              <TableCell data-testid="table-cell">Content</TableCell>
            </tr>
          </TableBody>
        </Table>
      );

      const cell = screen.getByTestId('table-cell');
      expect(cell.className).toContain('p-2');
      expect(cell.className).toContain('align-middle');
      expect(cell.className).toContain('whitespace-nowrap');
    });
  });

  describe('TableCaption', () => {
    it('renders caption with correct data-slot', () => {
      render(
        <Table>
          <TableCaption data-testid="table-caption">
            Table description
          </TableCaption>
          <TableBody>
            <tr>
              <td>Cell</td>
            </tr>
          </TableBody>
        </Table>
      );

      expect(screen.getByTestId('table-caption')).toHaveAttribute(
        'data-slot',
        'table-caption'
      );
    });

    it('renders as caption element', () => {
      render(
        <Table>
          <TableCaption data-testid="table-caption">
            Table description
          </TableCaption>
          <TableBody>
            <tr>
              <td>Cell</td>
            </tr>
          </TableBody>
        </Table>
      );

      expect(screen.getByTestId('table-caption')).toBeInstanceOf(
        HTMLTableCaptionElement
      );
    });

    it('applies custom className', () => {
      render(
        <Table>
          <TableCaption data-testid="table-caption" className="custom-caption">
            Table description
          </TableCaption>
          <TableBody>
            <tr>
              <td>Cell</td>
            </tr>
          </TableBody>
        </Table>
      );

      expect(screen.getByTestId('table-caption').className).toContain(
        'custom-caption'
      );
    });

    it('has default styling classes', () => {
      render(
        <Table>
          <TableCaption data-testid="table-caption">
            Table description
          </TableCaption>
          <TableBody>
            <tr>
              <td>Cell</td>
            </tr>
          </TableBody>
        </Table>
      );

      const caption = screen.getByTestId('table-caption');
      expect(caption.className).toContain('text-muted-foreground');
      expect(caption.className).toContain('mt-4');
      expect(caption.className).toContain('text-sm');
    });

    it('renders caption content', () => {
      render(
        <Table>
          <TableCaption data-testid="table-caption">
            List of all users in the system
          </TableCaption>
          <TableBody>
            <tr>
              <td>Cell</td>
            </tr>
          </TableBody>
        </Table>
      );

      expect(screen.getByTestId('table-caption')).toHaveTextContent(
        'List of all users in the system'
      );
    });
  });

  describe('complete table structure', () => {
    it('renders full table with all components', () => {
      render(
        <Table data-testid="complete-table">
          <TableCaption>User data table</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Email</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>John Doe</TableCell>
              <TableCell>john@example.com</TableCell>
            </TableRow>
          </TableBody>
          <TableFooter>
            <TableRow>
              <TableCell>Total</TableCell>
              <TableCell>1 user</TableCell>
            </TableRow>
          </TableFooter>
        </Table>
      );

      expect(screen.getByTestId('complete-table')).toBeInTheDocument();
      expect(screen.getByText('User data table')).toBeInTheDocument();
      expect(screen.getByText('Name')).toBeInTheDocument();
      expect(screen.getByText('Email')).toBeInTheDocument();
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('john@example.com')).toBeInTheDocument();
      expect(screen.getByText('Total')).toBeInTheDocument();
      expect(screen.getByText('1 user')).toBeInTheDocument();
    });

    it('renders without caption or footer', () => {
      render(
        <Table data-testid="simple-table">
          <TableHeader>
            <TableRow>
              <TableHead>Column</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>Data</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );

      expect(screen.getByTestId('simple-table')).toBeInTheDocument();
      expect(screen.getByText('Column')).toBeInTheDocument();
      expect(screen.getByText('Data')).toBeInTheDocument();
    });
  });

  describe('cn() utility (className composition)', () => {
    it('merges base classes with custom className on TableFooter', () => {
      render(
        <Table>
          <TableFooter data-testid="table-footer" className="custom">
            <tr>
              <td>Footer</td>
            </tr>
          </TableFooter>
        </Table>
      );

      const footer = screen.getByTestId('table-footer');
      expect(footer.className).toContain('bg-muted/50');
      expect(footer.className).toContain('border-t');
      expect(footer.className).toContain('custom');
    });

    it('merges base classes with custom className on TableCaption', () => {
      render(
        <Table>
          <TableCaption data-testid="table-caption" className="custom">
            Caption
          </TableCaption>
          <TableBody>
            <tr>
              <td>Cell</td>
            </tr>
          </TableBody>
        </Table>
      );

      const caption = screen.getByTestId('table-caption');
      expect(caption.className).toContain('text-muted-foreground');
      expect(caption.className).toContain('mt-4');
      expect(caption.className).toContain('custom');
    });
  });
});
