import React, { useState, useEffect, useMemo } from 'react';
import './App.css';

const API_URL = 'http://127.0.0.1:8000/api/disagreements/';

export default function App() {
  const [disagreements, setDisagreements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters & Sorting state
  const [selectedReason, setSelectedReason] = useState('ALL');
  const [sortOrder, setSortOrder] = useState('NONE'); // 'NONE' | 'ASC' | 'DESC'

  // Fetch data from Django API
  useEffect(() => {
    fetch(API_URL)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`API returned HTTP ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        setDisagreements(data.disagreements || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // Filtered & Sorted items
  const processedData = useMemo(() => {
    let result = [...disagreements];

    // 1. Filter by Reason
    if (selectedReason !== 'ALL') {
      result = result.filter((item) =>
        item.issue_types.includes(selectedReason)
      );
    }

    // 2. Sort by System A Value (or first available System B value)
    if (sortOrder !== 'NONE') {
      result.sort((a, b) => {
        const valA = a.system_a?.total_value
          ? parseFloat(a.system_a.total_value)
          : parseFloat(a.system_b_entries[0]?.value || 0);

        const valB = b.system_a?.total_value
          ? parseFloat(b.system_a.total_value)
          : parseFloat(b.system_b_entries[0]?.value || 0);

        return sortOrder === 'ASC' ? valA - valB : valB - valA;
      });
    }

    return result;
  }, [disagreements, selectedReason, sortOrder]);

  return (
    <div className="container">
      <header className="header">
        <h1>Data Reconciliation Reviewer</h1>
        <p className="subtitle">
          Auditing discrepancies between System A and System B exports across tenant boundaries
        </p>
      </header>

      {/* Controls Bar */}
      <div className="controls-bar">
        <div className="control-group">
          <label htmlFor="filter-reason"><strong>Filter by Reason:</strong></label>
          <select
            id="filter-reason"
            value={selectedReason}
            onChange={(e) => setSelectedReason(e.target.value)}
          >
            <option value="ALL">All Reasons ({disagreements.length})</option>
            <option value="VALUE_MISMATCH">Value Mismatch</option>
            <option value="MISSING_SYSTEM_B_ENTRY">Missing in System B</option>
            <option value="ORPHAN_SYSTEM_B_ENTRY">Orphan in System B</option>
            <option value="DUPLICATE_SYSTEM_B_ENTRY">Duplicate / Multiple Entries</option>
            <option value="LOCATION_MISMATCH">Location / Tenant Mismatch</option>
          </select>
        </div>

        <div className="control-group">
          <label htmlFor="sort-value"><strong>Sort by Value:</strong></label>
          <select
            id="sort-value"
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value)}
          >
            <option value="NONE">Default</option>
            <option value="ASC">Value: Low to High</option>
            <option value="DESC">Value: High to Low</option>
          </select>
        </div>

        <div className="count-badge">
          Showing <strong>{processedData.length}</strong> of {disagreements.length} items
        </div>
      </div>

      {/* Main Content State Handling */}
      {loading && <div className="status-box">Loading reconciliation records from API...</div>}

      {error && (
        <div className="status-box error-box">
          <h3>Failed to load API data</h3>
          <p>{error}</p>
          <small>Make sure the Django backend is running with: <code>python backend/manage.py runserver</code></small>
        </div>
      )}

      {!loading && !error && (
        <div className="table-responsive">
          <table className="reconciliation-table">
            <thead>
              <tr>
                <th>Record Ref</th>
                <th>Issue Reason</th>
                <th>System A Value</th>
                <th>System B Value(s)</th>
                <th>Location & Org</th>
                <th>System B Entry Details</th>
              </tr>
            </thead>
            <tbody>
              {processedData.length === 0 ? (
                <tr>
                  <td colSpan="6" className="text-center">No disagreements found matching this filter.</td>
                </tr>
              ) : (
                processedData.map((row) => (
                  <tr key={row.record_ref}>
                    {/* Record Reference */}
                    <td className="font-mono"><strong>{row.record_ref}</strong></td>

                    {/* Issue Types */}
                    <td>
                      <div className="badge-container">
                        {row.issue_types.map((issue) => (
                          <span key={issue} className={`badge badge-${issue}`}>
                            {issue.replace(/_/g, ' ')}
                          </span>
                        ))}
                      </div>
                    </td>

                    {/* System A Value */}
                    <td>
                      {row.system_a ? (
                        <div>
                          <strong>${row.system_a.total_value ?? 'NULL'}</strong>
                          {row.system_a.state === 'VOIDED' && (
                            <span className="badge badge-voided">VOIDED</span>
                          )}
                        </div>
                      ) : (
                        <span className="text-muted">— Missing System A —</span>
                      )}
                    </td>

                    {/* System B Value(s) */}
                    <td>
                      {row.system_b_entries.length === 0 ? (
                        <span className="text-muted">— No System B Entry —</span>
                      ) : (
                        row.system_b_entries.map((b, idx) => (
                          <div key={b.entry_id} className="entry-value-row">
                            <strong>${b.value ?? 'BLANK / NULL'}</strong>
                            {row.system_b_entries.length > 1 && (
                              <small className="text-muted"> (part {idx + 1})</small>
                            )}
                          </div>
                        ))
                      )}
                    </td>

                    {/* Location & Org */}
                    <td>
                      <div>
                        <strong>Sys A:</strong> {row.system_a ? `${row.system_a.location_id} (${row.system_a.org_id})` : 'N/A'}
                      </div>
                      {row.system_b_entries.length > 0 && (
                        <div className="text-muted">
                          <strong>Sys B:</strong> {row.system_b_entries.map(b => `${b.location_id} (${b.org_id})`).join(', ')}
                        </div>
                      )}
                    </td>

                    {/* System B Details */}
                    <td>
                      {row.system_b_entries.length === 0 ? (
                        <span className="text-muted">—</span>
                      ) : (
                        row.system_b_entries.map((b) => (
                          <div key={b.entry_id} className="entry-detail">
                            <span className="font-mono">{b.entry_id}</span>
                            {b.label && <span className="label-text"> | {b.label}</span>}
                          </div>
                        ))
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
