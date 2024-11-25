// path: frontend/src/app/page.tsx
"use client";

import ACControlPanel from "@/components/ACControlPanel";

export default function Home() {
  return (
    <main className="container mx-auto p-4">
      <ACControlPanel />
    </main>
  );
}
