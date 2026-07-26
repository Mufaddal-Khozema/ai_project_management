# Hey API — Frontend Data Flow

The backend lives at `../backend` and serves an OpenAPI schema. All frontend ↔ backend communication must follow these rules.

## 1. Generate everything from OpenAPI

Run `hey-api` (or equivalent) against the Litestar OpenAPI spec to generate:

- Typed SDK client
- Request/response types
- React Query hooks (`useQuery`, `useMutation`)

Do not hand-write API call functions or types.

## 2. Queries → Server Components with async/await

Fetch data directly in Server Components using the generated SDK client:

```tsx
// app/projects/page.tsx — Server Component
import { sdk } from "@/lib/api";

export default async function ProjectsPage() {
  const projects = await sdk.projects.list();
  return <ProjectList data={projects} />;
}
```

Rely on Next.js built-in Suspense, streaming, and caching.

**Do not use `useQuery`** unless there is a clear client-side requirement (e.g., polling, dependent queries that need interactivity). Server Components are the default.

## 3. Mutations → generated `useMutation` hooks

Call the generated React Query mutation hooks directly from Client Components:

```tsx
"use client";
import { useProjectsCreateMutation } from "@/lib/api";

export function CreateProjectForm() {
  const mutation = useProjectsCreateMutation();
  // ...
}
```

**Do not proxy requests through Next.js Route Handlers or Server Actions.** If they only forward to the backend, they add unnecessary indirection, break type safety, and duplicate work. Call the backend directly — it already validates, authorizes, and documents every endpoint.

## 4. Backend is the source of truth

The Litestar backend at `../backend` owns all business logic, validation, and auth. The frontend is a thin consumption layer. No client-side validation that duplicates server logic — just pass through what the API expects.

## 5. No Route Handlers, no Server Actions for API calls

| Allowed | Not allowed |
|---|---|
| Server Component → generated SDK → backend | Server Component → Route Handler → backend |
| Client Component → generated `useMutation` → backend | Client Component → Server Action → backend |
| | Any custom `fetch()` wrapper that duplicates the SDK |
