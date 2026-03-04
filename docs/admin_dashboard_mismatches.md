# Admin Dashboard Mismatches (PalmX Benchmark)

## 1. Time Filter Implementation Gap
- **UI State**: `AdminPage.tsx` tracks `timeFilter` in state, but `loadStats` ignores it.
- **Frontend API**: `fetchAdminStats()` in `lib/api.ts` does not accept parameters.
- **Backend API**: `/admin/dashboard` expects `range` query param but receives none from frontend.
- **Inconsistency**: `loadLeads` passes `time_filter` to `/admin/leads`, but the backend implementation for `/admin/leads` does **not** handle or filter by range.

## 2. Dataset Selector Misalignment
- **UI**: Selector switches between `Executive Dashboard`, `leads.csv`, `audit.csv`, and `sessions.csv`.
- **Backend**: `/admin/dashboard` is hardcoded to `leads.csv` by default. It doesn't switch context for "Executive Dashboard" metrics (e.g., viewing dashboard metrics for `leads_seed.csv`).

## 3. Data Presentation (Realism)
- **Table Columns**: UI components like `LeadTable` and `LeadDrawer` might still be parsing or displaying raw JSON strings for `interest_projects` instead of using the `_display` columns I added to the seed data.
- **KPI Precision**: KPI tiles use static-ish logic; `Intake last 24h` should be a live calculation from the backend.

## 4. Technical Risks
- **Timezone Drift**: Backend uses `datetime.now()` for cutoff, while data uses ISO 8601 'Z' (UTC).
- **Missing Endpoints**: No windowed endpoint for `audit.csv` or `sessions.csv` aggregation.
