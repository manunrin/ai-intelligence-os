# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to Semantic Versioning.

## [Unreleased] — Phase 6-C

### Date
2026-07-16

### Commit
`b0902b6` — Phase 6-C: Dashboard Integration & End-to-End API

### Added
- CORS middleware on backend (`backend/main.py`) to allow frontend dev server calls
- `unwrap()` helper in frontend API client to extract `data` from APIResponse envelope
- Improved error handling in frontend API client: parses JSON error body when present

### Changed
- Frontend dashboard now calls correct backend paths (`/api/v1/*` instead of `/api/*`)
- Frontend `DataTable` component: simplified generic typing (`unknown[]` instead of undeclared `T`)
- Frontend types: converted `interface` + intersection to `type` aliases (fixes TS compilation)
- Badge variant type maps now include `"muted"` in their union type

### Fixed
- **Critical**: Dashboard was calling wrong API paths (`/api/articles` vs `/api/v1/articles`)
- **Critical**: Dashboard assigned full APIResponse envelope to state instead of extracted `data` array
- **Critical**: No CORS configuration prevented browser-to-backend communication
- **Medium**: Table component referenced undeclared generic `T`
- **Medium**: TypeScript build failed due to `interface {} & Record<string, unknown>` syntax
- **Low**: Badge variant type casts were overly complex with redundant union assertions

### Breaking Changes
None. All changes are internal integration fixes.

---
