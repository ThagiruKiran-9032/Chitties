import React from 'react'
import LoadingState from './LoadingState'
import EmptyState from './EmptyState'
import ErrorState from './ErrorState'

export default function DataTable({
  columns = [],
  data = [],
  loading = false,
  error = null,
  onRetry = null,
  emptyTitle = 'No data available',
  emptyDescription = 'There are no records to display.',
  onRowClick = null,
}) {
  if (loading) {
    return <LoadingState />
  }

  if (error) {
    return <ErrorState message={error} onRetry={onRetry} />
  }

  if (!data || data.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />
  }

  return (
    <div className="table-container" style={{ overflowX: 'auto' }}>
      <table className="table">
        <thead>
          <tr>
            {columns.map((col, idx) => (
              <th
                key={col.key || idx}
                style={{
                  textAlign: col.align || 'left',
                  width: col.width || 'auto',
                }}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIdx) => (
            <tr
              key={row.id || rowIdx}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              style={{ cursor: onRowClick ? 'pointer' : 'default' }}
            >
              {columns.map((col, colIdx) => {
                let cellValue = null
                if (typeof col.render === 'function') {
                  cellValue = col.render(row, rowIdx)
                } else if (typeof col.accessor === 'function') {
                  cellValue = col.accessor(row)
                } else if (col.accessor) {
                  cellValue = row[col.accessor]
                }

                return (
                  <td
                    key={col.key || colIdx}
                    style={{ textAlign: col.align || 'left' }}
                  >
                    {cellValue !== undefined && cellValue !== null ? cellValue : '—'}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
