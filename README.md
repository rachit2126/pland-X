# Standalone MPP Import & Export Parser Service (PlanD-X Integration Layer)

A high-performance, enterprise-grade Python service and CLI tool that parses Microsoft Project (`.MPP`) files, extracts structured programme information, supports task modification & MSPDI XML export, and exposes a normalized **PlanD-X Integration Layer** connecting programme data to construction management modules (Schedule, BOQ, Cost, Progress, Evidence, Vendor, Dashboard).

Powered by [MPXJ](https://www.mpxj.org/) and JPype, this service handles real-world complex construction programmes across various Microsoft Project file formats (`.mpp`, `.xml`, `.mpx`, `.mpt`).

---

## Unified PlanD-X Platform Architecture

```
Microsoft Project (.MPP)
         │
         ▼ (MPXJ Engine)
  Standalone MPP Parser Service
         │
         ▼ (MPPParseResultSchema)
  PlanD-X Mapper Engine (mpp_parser/plandx/mapper.py)
         │
         ▼
  Normalized PlanD-X Programme Models (mpp_parser/plandx/models.py)
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Project  │  Activity  │  Dependency  │  Resource  │  BOQ  │  Progress │
  └────────────────────────────────────────────────────────────────────────┘
         │
         ▼
  Programme Service & Repository Layer (mpp_parser/plandx/repository.py)
         │
         ├──► GET  /api/v1/projects/{id}/programme (Normalized Programme DTO)
         ├──► POST /api/v1/projects/{id}/sync      (Sync MPP dataset to PlanD-X)
         └──► GET  /api/v1/projects/{id}/dashboard  (Dashboard Telemetry)
```

---

## PlanD-X Integration Modules & Strategy

| Module | Integration Capability | Mapping Description |
| :--- | :--- | :--- |
| **Schedule Control** | Activity Hierarchy & Dependencies | Maps WBS, `outlineLevel`, `parentActivity`, and predecessor relationships (`FS`, `SS`, `FF`, `SF`). |
| **BOQ & Cost** | Quantity & Cost Reference Mapping | Binds `BOQMapping` references (`boqItemId`, `code`, `quantity`, `unit`, `costEstimate`) to schedule activities. |
| **Progress & Variance** | Schedule Variance Engine | Calculates baseline `plannedPercent` vs site `actualPercent`, schedule `variance`, `isDelayed` flags, and `delayDays`. |
| **Evidence Management** | Verification Audit Trail | Binds `EvidenceRecord` attachments (site photos, inspection documents, reports) to activity IDs. |
| **Vendor & Contractor** | Subcontractor Mapping | Maps assigned resources containing contractor terms to `VendorMapping` (subcontract company, package name). |
| **Programme Dashboard** | Telemetry Aggregation | Aggregates overall progress %, completed activities, delayed tasks, critical path activities, and upcoming milestones. |

---

## Output PlanD-X Programme Schema Contract

```json
{
  "projectId": "proj-123",
  "projectName": "Ormiston Construction Phase 2",
  "startDate": "2026-01-01",
  "finishDate": "2026-12-31",
  "calendar": "Standard",
  "syncedAt": "2026-08-14T03:45:00Z",
  "activities": [
    {
      "activityId": "10",
      "WBS": "1.1",
      "name": "Substructure Concrete Pour",
      "parentActivity": "1",
      "startDate": "2026-01-01",
      "finishDate": "2026-01-10",
      "duration": 10.0,
      "progressPercentage": 50.0,
      "milestone": false,
      "isSummary": false,
      "dependencies": [
        {
          "predecessor": "9",
          "successor": "10",
          "relationshipType": "FS",
          "lag": 0.0
        }
      ],
      "resources": [
        {
          "resourceId": "res-10-1",
          "resourceName": "ABC Concrete Contractor",
          "resourceType": "Subcontractor"
        }
      ],
      "boqMapping": {
        "boqItemId": "boq-10",
        "code": "COST-10",
        "quantity": 1.0,
        "unit": "ls",
        "costEstimate": 100000.0
      },
      "evidenceRecords": [],
      "vendorMapping": {
        "vendorId": "v-123",
        "companyName": "ABC Concrete Contractor",
        "package": "Substructure Concrete Pour",
        "assignedActivities": ["10"]
      },
      "progressMetric": {
        "plannedPercent": 100.0,
        "actualPercent": 50.0,
        "variance": -50.0,
        "isDelayed": true,
        "delayDays": 5.0
      }
    }
  ]
}
```

---

## Integration API Endpoints

1. **Sync MPP File into PlanD-X Project (`POST /api/v1/projects/{id}/sync`)**
   ```bash
   curl -X POST "http://127.0.0.1:8000/api/v1/projects/proj-123/sync" \
     -F "file=@project.mpp"
   ```
   **Response**:
   ```json
   {
     "projectId": "proj-123",
     "syncStatus": "success",
     "activitiesImported": 800,
     "warnings": []
   }
   ```

2. **Get Normalized PlanD-X Programme (`GET /api/v1/projects/{id}/programme`)**
   ```bash
   curl http://127.0.0.1:8000/api/v1/projects/proj-123/programme
   ```

3. **Get Programme Dashboard Telemetry (`GET /api/v1/projects/{id}/dashboard`)**
   ```bash
   curl http://127.0.0.1:8000/api/v1/projects/proj-123/dashboard
   ```
   **Response**:
   ```json
   {
     "progress": 65.0,
     "completedActivities": 450,
     "delayedActivities": 12,
     "criticalActivities": 5,
     "upcomingMilestones": 8,
     "totalActivities": 800
   }
   ```

---

## Standalone Parser & Exporter Usage

### HTTP Endpoints
- `GET /health` / `GET /api/v1/health`: Health check status.
- `POST /parse` / `POST /api/v1/parse`: Multipart MPP upload parsing.
- `POST /export` / `POST /api/v1/export`: Task modification and MSPDI XML export.
- `GET /metrics` / `GET /api/v1/metrics`: Prometheus telemetry exposition.

### CLI Utilities
```bash
# Parse MPP to JSON
mpp-parse project.mpp --pretty -o output.json

# Modify & Export Project
mpp-export project.mpp output.xml --modify modifications.json
```

---

## Running Automated Tests

```bash
# Run full pytest test suite across all 10 test modules
pytest -v
```

The test suite validates:
1. `tests/test_parse.py`: Flat, hierarchy, and real 800-task MPP file parsing.
2. `tests/test_engine.py`: Engine helper and error handling unit tests.
3. `tests/test_schema.py`: Pydantic contract & alias validation tests.
4. `tests/test_api.py`: FastAPI endpoint tests.
5. `tests/test_export.py`: Task modification & predecessor modification export tests.
6. `tests/test_cli.py`: CLI commands `mpp-parse` and `mpp-export`.
7. `tests/test_production_hardening.py`: Size caps (HTTP 413), extension checks (HTTP 422), config settings.
8. `tests/test_performance.py`: Scale benchmarks (100, 5,000, 25,000 tasks), memory usage, duration metrics.
9. `tests/test_enterprise.py`: Correlation ID middleware, Prometheus telemetry, MIME validation, filename sanitization, API v1 routes.
10. `tests/test_plandx_integration.py`: PlanD-X DTO schema validation, mapper engine, progress variance calculations, repository service, and `/api/v1/projects/{id}/sync`, `/programme`, `/dashboard` endpoints.
