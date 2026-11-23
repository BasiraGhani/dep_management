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
