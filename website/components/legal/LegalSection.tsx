import type { ReactNode } from "react";

export function LegalSection({
  heading,
  children,
}: {
  heading: string;
  children: ReactNode;
}) {
  return (
    <section className="mt-10">
      <h2 className="mb-3 text-lg font-semibold tracking-tight text-white">
        {heading}
      </h2>
      <div className="space-y-3 text-sm leading-relaxed text-zinc-400">
        {children}
      </div>
    </section>
  );
}