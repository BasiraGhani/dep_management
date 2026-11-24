# Frontend

React + TypeScript (Vite), Tailwind CSS, Vitest + React Testing Library (Node 20+). Planned layout: `../docs/ARCHITECTURE.md` §5.

## Setup

```bash
cd frontend
npm ci
```

The backend URL comes from `VITE_API_URL` (default `http://localhost:8000/api/v1`).
To change it, copy `.env.example` to `.env.local` and edit it.

## Run

```bash
npm run dev            # http://localhost:5173
```

## Checks

```bash
npm run lint           # ESLint + Prettier check
npm run typecheck      # tsc (strict)
npm run test -- --run  # Vitest
npm run build
```

`npm run format` applies Prettier formatting.

## End-to-end smoke test

`e2e/smoke.e2e.ts` (Playwright) signs in as each demo role and does one key action:
admin creates a department, HOD creates a course, teacher saves a grade, student sees
their GPA. It cleans up after itself, so it can run repeatedly. It needs the demo data.

```bash
npx playwright install chromium   # once
npm run e2e                        # against the Docker stack at http://localhost

# against the dev servers instead (Vite + Uvicorn):
E2E_BASE_URL=http://localhost:5173 E2E_API_URL=http://localhost:8000/api/v1 npm run e2e
```

Add `E2E_CHANNEL=chrome` to use an installed Google Chrome. CI runs the test against the
Docker stack (the "Docker stack" job).
