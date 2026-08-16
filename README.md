# Standalone MPP Import & Export Parser

A high-performance, native service and CLI tool that parses Microsoft Project (`.MPP`) files, extracts structured project and task information according to a strict JSON contract, supports task modification & schedule export, and enforces robust file validation and error handling.

Powered by [MPXJ](https://www.mpxj.org/) and JPype, this service handles real-world Microsoft Project binary file formats (`.mpp`) as well as `.xml`, `.mpx`, and `.mpt`.

---

## 1. System Architecture & Data Flow

```
MPP/XML File
      ↓
MPXJ Parser Engine
      ↓
FastAPI Service
      ↓
JSON Response
```

### Core Features

- **Native MPP Parsing**: Parses Microsoft Project binary `.mpp` files directly via MPXJ.
- **Project Metadata Extraction**: Extracts `projectName`, `projectCalendar`, `projectStart`, `projectFinish`, `parsedAt`, and `taskCount`.
- **Task Hierarchy & WBS**: Accurately extracts `BAQ` → `Task` → `Sub-task` hierarchy using `outlineLevel`, `parentId`, and `wbs`.
- **Milestone Identification**: Identifies milestone tasks with explicit `isMilestone` boolean flags.
- **Dependency Extraction**: Captures predecessor tasks with target ID (`id`), relationship types (`FS`, `SS`, `FF`, `SF`), and lag values (`lag` and `lagDays`).
- **Validation & Error Handling**: Returns `HTTP 422 Unprocessable Entity` for corrupted or unparseable files, `HTTP 413 Payload Too Large` for oversized uploads, and prevents service crashes under all failure scenarios.
- **Task Modification & Export Engine**: Modify task properties and export updated schedules to MS Project-compatible **MSPDI XML** format (`.xml`).
- **Enterprise Operations & Security**: Includes request correlation IDs (`X-Request-ID`), Prometheus telemetry (`/api/v1/metrics`), configurable size caps (`MAX_UPLOAD_SIZE_MB`), MIME checks, and Docker containerization.

---

## 2. API Specifications

### Parse MPP File (`POST /api/v1/parse`)

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` (Uploaded `.mpp` file)

**Response Schema (`200 OK`):**
```json
{
  "sourceFile": "project.mpp",
  "projectName": "Sample Project Schedule",
  "projectCalendar": "Standard",
  "projectStart": "2026-01-01",
  "projectFinish": "2026-12-31",
  "parsedAt": "2026-08-17T01:05:00Z",
  "taskCount": 42,
  "tasks": [
    {
      "id": "1",
      "wbs": "1",
      "name": "Phase 1: Foundation Work",
      "outlineLevel": 1,
      "parentId": null,
      "start": "2026-01-01",
      "finish": "2026-03-31",
      "durationDays": 90.0,
      "percentComplete": 100.0,
      "isMilestone": false,
      "assignedResource": "Civil Team",
      "predecessors": [],
      "notes": "Project commencement phase"
    },
    {
      "id": "2",
      "wbs": "1.1",
      "name": "Foundation Design Signoff",
      "outlineLevel": 2,
      "parentId": "1",
      "start": "2026-01-01",
      "finish": "2026-01-01",
      "durationDays": 0.0,
      "percentComplete": 100.0,
      "isMilestone": true,
      "assignedResource": null,
      "predecessors": [],
      "notes": "Milestone event"
    },
    {
      "id": "3",
      "wbs": "1.2",
      "name": "Excavation Work",
      "outlineLevel": 2,
      "parentId": "1",
      "start": "2026-01-02",
      "finish": "2026-01-15",
      "durationDays": 10.0,
      "percentComplete": 50.0,
      "isMilestone": false,
      "assignedResource": "Excavator Subcontractor",
      "predecessors": [
        {
          "id": "2",
          "type": "FS",
          "lag": 0.0,
          "lagDays": 0.0
        }
      ],
      "notes": null
    }
  ],
  "unparsedWarnings": []
}
```

### Import Programme File (`POST /api/projects/{project_id}/programme/import`)

**Request:**
- Path Parameter: `project_id` (e.g. `PRJ-101`)
- Content-Type: `multipart/form-data`
- Body: `file` (Uploaded `.mpp`, `.xml`, `.mpx`, or `.mpt` schedule file)

Automatically detects file type, parses schedule, attaches `projectId`, and returns structured JSON import summary.

### Export Programme XML (`GET /api/projects/{project_id}/programme/export?format=xml`)

**Request:**
- Path Parameter: `project_id` (e.g. `PRJ-101`)
- Query Parameter: `format` (`xml` - default)

Generates and returns a valid Microsoft Project XML (MSPDI XML) schedule file (`Content-Type: application/xml`) preserving tasks, dates, dependencies, resources, and progress.

### Additional Endpoints

- `POST /api/v1/parse`: Standard file parse endpoint.
- `GET /api/v1/export`: Format capabilities & export documentation (supports `format=xml` download).
- `POST /api/v1/export`: Schedule task modification & MSPDI XML export.
- `GET /api/v1/health`: Health status check.
- `GET /api/v1/metrics`: Prometheus telemetry metrics.

---

## 3. Command Line Interface (CLI)

```bash
# Parse MPP file to formatted JSON
mpp-parse project.mpp --pretty -o output.json

# Modify & Export project schedule
mpp-export project.mpp output.xml --modify modifications.json
```

---

## 4. Environment Variables & Configuration

- `HOST`: Server host (Default: `0.0.0.0`)
- `PORT`: Server port (Default: `8000`)
- `MAX_UPLOAD_SIZE_MB`: Maximum allowed file upload size in MB (Default: `50`)
- `ALLOWED_EXTENSIONS`: Allowed file extensions (Default: `.mpp,.xml,.mpx,.mpt`)
- `LOG_LEVEL`: Logging level (Default: `INFO`)

---

## 5. Docker Deployment

```bash
# Build Docker image
docker build -t mpp-parser-service .

# Run Docker container
docker run -d -p 8000:8000 -e MAX_UPLOAD_SIZE_MB=50 mpp-parser-service
```

---

## 6. Running Automated Tests

```bash
python3 -m pytest -v
```

Automated test suite validates:
1. `tests/test_parse.py`: Native MPP file parsing, task hierarchy (`BAQ` → `Task` → `Sub-task`), milestones, predecessors, percent complete, and multiple sample files.
2. `tests/test_engine.py`: Core parser engine unit tests.
3. `tests/test_schema.py`: Pydantic schema validation tests.
4. `tests/test_api.py`: FastAPI endpoints and error handling tests.
5. `tests/test_export.py`: Schedule modification and export tests.
6. `tests/test_cli.py`: CLI tools `mpp-parse` and `mpp-export`.
7. `tests/test_production_hardening.py`: HTTP 413 file size limits and HTTP 422 extension checks.
8. `tests/test_performance.py`: High scale performance benchmarks.
9. `tests/test_enterprise.py`: Telemetry metrics, correlation IDs, and MIME checks.
