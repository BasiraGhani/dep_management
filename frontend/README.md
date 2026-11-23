# Frontend

React + TypeScript (Vite), Tailwind CSS, Vitest + React Testing Library (Node 20+). Planned layout: `../docs/ARCHITECTURE.md` §5.

## Setup

```bash
cd frontend
npm ci
```

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
