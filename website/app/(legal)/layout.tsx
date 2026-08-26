import Link from "next/link";

export default function LegalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      <link
        href="https://fonts.googleapis.com/css2?family=Inter+Tight:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400;1,500&family=JetBrains+Mono:wght@400;500&display=swap"
        rel="stylesheet"
      />

      <div className="mesh-bg fixed inset-0 z-0 overflow-hidden pointer-events-none" />

      <div className="relative z-10 flex min-h-screen flex-col bg-[rgb(9,9,11)]">
        <header className="sticky top-0 z-20 border-b border-zinc-800/60 bg-[rgb(9,9,11)]/80 backdrop-blur">
          <div className="mx-auto flex w-full max-w-3xl items-center gap-3 px-6 py-4">
            <Link href="/" className="flex items-center gap-[10px]">
              <div className="flex size-6 items-center justify-center rounded-lg bg-indigo-600">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="relative z-[1] size-4 text-white"
                >
                  <path d="M12 2L2 7l10 5 10-5-10-5z" />
                  <path d="M2 17l10 5 10-5" />
                  <path d="M2 12l10 5 10-5" />
                </svg>
              </div>
              <span className="text-base font-semibold tracking-[-0.03em] text-white">
                CoordinaAI
              </span>
            </Link>
          </div>
        </header>

        <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-16">
          {children}
        </main>

        <footer className="border-t border-zinc-800/60">
          <div className="mx-auto flex w-full max-w-3xl flex-col items-center justify-center gap-3 px-6 py-8 text-xs text-zinc-500 sm:flex-row sm:justify-between">
            <p>© 2026 CoordinaAI</p>
            <div className="flex items-center gap-6">
              <Link href="/terms" className="transition-colors hover:text-zinc-300">
                Terms of Service
              </Link>
              <Link href="/privacy" className="transition-colors hover:text-zinc-300">
                Privacy Policy
              </Link>
            </div>
          </div>
        </footer>
      </div>
    </>
  );
}