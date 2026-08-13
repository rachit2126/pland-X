# Standalone MPP Import & Export Parser Prototype

A high-performance, prototype service and CLI tool that parses Microsoft Project (`.MPP`) files, extracts structured programme information according to a strict JSON contract, supports task modification & MSPDI XML export, and provides a foundation for future construction management extensions.

Powered by [MPXJ](https://www.mpxj.org/) and JPype, this service handles real-world complex construction programmes across various Microsoft Project file formats (`.mpp`, `.xml`, `.mpx`, `.mpt`).

> **Note**: PlanD-X Integration Layer prepared as a future construction programme management extension.

---

## 1. Current Prototype Capabilities

### Overview & Primary Demo Flow

```
Microsoft Project (.MPP)
         │
         ▼ (MPXJ UniversalProjectReader)
  Python Engine
         │
         ├──► GET  /api/v1/health   (Health Status)
         ├──► POST /api/v1/parse    (Extract Programme JSON)
         ├──► POST /api/v1/export   (Modify & Export Schedule)
         └──► GET  /api/v1/metrics  (Prometheus Telemetry)
         │
         ▼ (MPXJ MSPDIWriter)
   MSPDI XML Output (.xml) ──► Native MS Project Support
```

### Core Features

- **Project Metadata Extraction**: `sourceFile`, `projectName`, `projectCalendar`, `parsedAt`, `projectStart`, `projectFinish`, `taskCount`.
- **Task Hierarchy & WBS**: Preserves standard MS Project hierarchy via `outlineLevel`, `parentId`, and WBS breakdown codes.
- **Dependency Links**: Captures `FS`, `SS`, `FF`, `SF` relationships along with `lagDays`.
- **Task Modification & Export Engine**: Modify task properties (name, duration, start/finish dates, percent complete, predecessors) and export updated schedules to MS Project-compatible **MSPDI XML** format (`.xml`).
- **Export Verification**: Validates re-imported schedule integrity (`exportFormat`, `exportVerified`, `tasksChecked`, `hierarchyPreserved`, `dependenciesPreserved`, `milestonesPreserved`).
- **Enterprise Operations & Security**: Request correlation IDs (`X-Request-ID`), Prometheus telemetry (`/api/v1/metrics`), 50 MB upload file size caps (`HTTP 413`), MIME type checks (`HTTP 422`), and Docker containerization.

### Primary API Endpoints

1. **Health Check (`GET /api/v1/health`)**
   ```bash
   curl http://127.0.0.1:8000/api/v1/health
   ```

2. **Parse MPP File (`POST /api/v1/parse`)**
   ```bash
   curl -X POST "http://127.0.0.1:8000/api/v1/parse" \
     -F "file=@project.mpp"
   ```

3. **Modify & Export Schedule (`POST /api/v1/export`)**
   ```bash
   curl -X POST "http://127.0.0.1:8000/api/v1/export" \
     -F "file=@project.mpp" \
     -F 'modifications_json=[{"taskId": "25", "name": "Updated Activity", "percentComplete": 75}]'
   ```

4. **Prometheus Telemetry (`GET /api/v1/metrics`)**
   ```bash
   curl http://127.0.0.1:8000/api/v1/metrics
   ```

### Command Line Interface (CLI)

```bash
# Parse MPP file to formatted JSON
mpp-parse project.mpp --pretty -o output.json

# Modify & Export project schedule
mpp-export project.mpp output.xml --modify modifications.json
```

---

## 2. Future PlanD-X Integration Roadmap

The service includes an internal **PlanD-X Integration Layer** prepared for connecting parsed programme data to future construction management modules:

```
                          Parsed MPP Dataset
                                  │
                                  ▼
                 Normalized PlanD-X Programme Models
  ┌──────────────────────────────────────────────────────────────────┐
  │ Project │ Activity │ Dependency │ Resource │ BOQ │ Progress │
  └──────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                    PlanD-X Module Integrations
  ┌──────────────────────────────────────────────────────────────────┐
  │ Schedule │ BOQ & Cost │ Progress │ Evidence │ Vendor │ Dashboard │
  └──────────────────────────────────────────────────────────────────┘
```

### Module Integration Architecture

- **Schedule Control**: Maps activity WBS, parent-child groups, and predecessor links.
- **BOQ & Cost**: Links pay item codes (`BOQMapping`), quantities, and budget estimates to schedule activities.
- **Progress Variance**: Baseline `plannedPercent` vs site `actualPercent` variance calculations and delay tracking.
- **Evidence Management**: Binds site photos, inspection documents, and verification records to activity IDs.
- **Vendor Mapping**: Binds subcontractor company IDs and packages to assigned activities.
- **Programme Dashboard**: Exposes summary metrics (`progress %`, completed tasks, delayed activities, critical tasks, upcoming milestones).

### Internal PlanD-X Endpoints (Prepared Extension)

- `GET /api/v1/projects/{project_id}/programme` (Normalized Programme DTO)
- `POST /api/v1/projects/{project_id}/sync` (Sync MPP dataset to PlanD-X)
- `GET /api/v1/projects/{project_id}/dashboard` (Dashboard Telemetry)

---

## Prerequisites & Installation

1. **Python 3.9+** & **Java Runtime (JRE / JDK 11+)**
2. **Setup**:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

---

## Running Automated Tests

```bash
# Run full pytest suite across all 10 test modules
pytest -v
```

Tests validate:
1. `tests/test_parse.py`: Flat, hierarchy, and real 800-task MPP file parsing.
2. `tests/test_engine.py`: Engine helper unit tests.
3. `tests/test_schema.py`: Schema contract validation tests.
4. `tests/test_api.py`: FastAPI endpoint tests.
5. `tests/test_export.py`: Task modification & export verification tests.
6. `tests/test_cli.py`: CLI commands `mpp-parse` and `mpp-export`.
7. `tests/test_production_hardening.py`: Size caps (HTTP 413) and extension checks.
8. `tests/test_performance.py`: Scale benchmarks (100, 5,000, 25,000 tasks).
9. `tests/test_enterprise.py`: Correlation ID middleware, Prometheus telemetry, MIME validation.
10. `tests/test_plandx_integration.py`: PlanD-X DTO models, mapper engine, progress variance, and endpoints.
