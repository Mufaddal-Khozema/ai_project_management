"use client";

import { useEffect, useRef } from "react";
import Image from "next/image";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { Orb } from "./orb";
import { Threads } from "./threads";
import { ThemeIcon } from "./icons";
import { useLandingTheme } from "./use-theme";
import { TryIt } from "./try-it";
import { Features } from "./features";
import { Access } from "./access";
import { Pricing } from "./pricing";

const section =
  "border-t border-hairline px-5 py-10 sm:px-8 lg:px-14 lg:py-20";
const primaryButton =
  "inline-flex items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-soft active:shadow-press";
const ghostButton =
  "inline-flex items-center justify-center rounded-xl bg-canvas px-5 py-3 text-sm font-semibold text-ink shadow-soft active:shadow-press";

const NAV_LINKS = [
  { label: "Product", href: "#product" },
  { label: "Access", href: "#safe" },
  { label: "How it works", href: "#how" },
  { label: "Pricing", href: "#pricing" },
];

const INTEGRATIONS = [
  { name: "Slack", detail: "Chat" },
  { name: "Discord", detail: "Chat and voice" },
  { name: "Jira", detail: "Projects" },
  { name: "Taiga", detail: "Projects" },
];

const SAFE_ITEMS = [
  {
    title: "Access follows the person.",
    detail: "Admin, write, read or none. Every request is checked.",
  },
  {
    title: "Honest about results.",
    detail: "It never claims success it didn’t get.",
  },
  {
    title: "Secrets stay secret.",
    detail:
      "Credentials are encrypted and never shown, even to Coordi’s replies.",
  },
];

const STEPS = [
  {
    title: "Connect",
    detail: "Link your chat and project tools in a minute.",
  },
  {
    title: "Map",
    detail: "Match each channel to a project and each teammate to both.",
  },
  {
    title: "Stand up",
    detail: "At 9:30 Coordi starts the standup by itself.",
  },
  {
    title: "Done",
    detail: "Notes land in the channel and the board updates.",
  },
];

export default function LandingPage() {
  const { toggleTheme } = useLandingTheme();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    const handleMove = (event: PointerEvent) => {
      element.style.setProperty(
        "--ex",
        ((event.clientX / window.innerWidth - 0.5) * 2).toFixed(2),
      );
      element.style.setProperty(
        "--ey",
        ((event.clientY / window.innerHeight - 0.5) * 2).toFixed(2),
      );
    };

    window.addEventListener("pointermove", handleMove);
    return () => window.removeEventListener("pointermove", handleMove);
  }, []);

  return (
    <div
      ref={containerRef}
      className="landing relative isolate min-h-screen bg-canvas font-body text-ink"
    >
      <Threads className="pointer-events-none fixed inset-0 -z-10 h-full w-full opacity-60" />

      <header className="sticky top-0 z-50 border-b border-hairline bg-canvas">
        <div className="mx-auto flex max-w-7xl items-center gap-2 border-x border-hairline px-4 py-3 sm:px-6">
          <Orb />
          <strong className="font-display mr-3 ml-2 text-xl font-extrabold">
            CoordinaAI
          </strong>

          <nav className="hidden items-center gap-1 md:flex">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="rounded-lg px-3 py-2 text-sm font-semibold text-ink transition-colors hover:bg-hairline"
              >
                {link.label}
              </a>
            ))}
          </nav>

          <span className="flex-1" />

          <button
            type="button"
            aria-label="Switch light or dark theme"
            onClick={toggleTheme}
            className="inline-flex size-11 items-center justify-center rounded-xl bg-canvas text-ink shadow-soft active:shadow-press"
          >
            <ThemeIcon />
          </button>
          <Link
            href="/signup"
            className="hidden rounded-xl bg-canvas px-5 py-3 text-sm font-semibold text-ink shadow-soft md:inline-flex"
          >
            Sign in
          </Link>
          <Link href="/signup" className={primaryButton}>
            Start free trial
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-7xl border-x border-hairline">
        <section className={cn(section, "border-t-0")} id="try">
          <div className="grid items-end gap-8 lg:grid-cols-5 lg:gap-14">
            <h1 className="font-display text-4xl font-extrabold leading-none tracking-tight sm:text-5xl lg:col-span-3 lg:text-6xl">
              Chat says one thing. The board says another.{" "}
              <span className="text-ink-muted">
                Coordi keeps them honest.
              </span>
            </h1>
            <div className="lg:col-span-2">
              <p className="max-w-xl text-ink-muted">
                CoordinaAI is the AI teammate that sits between your team chat
                and your project board. Ask it, talk to it, and it remembers
                every decision.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <Link href="/signup" className={primaryButton}>
                  Start 14-day trial
                </Link>
                <a href="#product" className={ghostButton}>
                  See how it works
                </a>
              </div>
            </div>
          </div>

          <div className="relative mt-10 grid min-h-96 place-items-center overflow-hidden rounded-2xl p-4 shadow-raise sm:p-6 lg:min-h-150 lg:p-12">
            <Image
              src="/landing/a1.jpg"
              alt=""
              fill
              priority
              sizes="100vw"
              className="object-cover"
            />
            <Threads className="absolute inset-0 h-full w-full opacity-90" />
            <TryIt />
          </div>
        </section>

        <section
          className={cn(section, "p-0")}
          aria-label="Works with"
        >
          <div className="grid gap-px bg-hairline sm:grid-cols-2 lg:grid-cols-5">
            <div className="bg-canvas px-5 py-6 text-base font-medium sm:col-span-2 lg:col-span-1 lg:pl-14">
              Works where your team already works.
            </div>
            {INTEGRATIONS.map((integration) => (
              <div
                key={integration.name}
                className="grid content-center gap-0.5 bg-canvas px-5 py-6 font-display text-xl font-extrabold"
              >
                <span>{integration.name}</span>
                <small className="font-body text-sm font-medium text-ink-muted">
                  {integration.detail}
                </small>
              </div>
            ))}
          </div>
        </section>

        <section
          className={cn(
            section,
            "grid items-center gap-8 lg:grid-cols-2 lg:gap-14",
          )}
        >
          <h2 className="font-display text-3xl font-extrabold tracking-tight sm:text-4xl lg:text-5xl">
            Teams talk in chat. They track work on a board. The two drift
            apart.{" "}
            <span className="text-ink-muted">
              Coordi sits in the gap and closes it.
            </span>
          </h2>

          <div className="rounded-2xl border border-hairline bg-gradient-to-br from-canvas to-hairline p-7">
            <div className="font-display text-6xl font-extrabold tracking-tighter lg:text-8xl">
              5:00
            </div>
            <div className="my-4 h-3 rounded bg-gradient-to-r from-pink-500 via-violet-500 to-blue-500 shadow-press" />
            <p className="text-ink-muted">
              The default standup. Coordi runs it by voice, wraps up at the
              limit and posts the summary to your channel.
            </p>
          </div>
        </section>

        <section className={section} id="product">
          <h2 className="font-display text-3xl font-extrabold tracking-tight sm:text-4xl lg:text-5xl">
            One teammate, three promises.
          </h2>
          <Features />
        </section>

        <section className={cn(section, "p-0 lg:grid lg:grid-cols-2")} id="safe">
          <div className="p-6 sm:p-8 lg:p-14">
            <h2 className="font-display text-3xl font-extrabold tracking-tight sm:text-4xl lg:text-5xl">
              Built for teams that care who may do what.{" "}
              <span className="text-ink-muted">
                Coordi acts as you, never beyond you.
              </span>
            </h2>
            <div className="mt-7 grid gap-3.5">
              {SAFE_ITEMS.map((item) => (
                <div
                  key={item.title}
                  className="border-t border-hairline pt-3.5"
                >
                  <b className="block font-semibold">{item.title}</b>
                  <span className="text-ink-muted">{item.detail}</span>
                </div>
              ))}
            </div>
          </div>
          <Access />
        </section>

        <section
          className={cn(section, "p-0")}
          id="how"
          aria-label="A day with Coordi"
        >
          <div className="grid gap-px bg-hairline sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((step, index) => (
              <div
                key={step.title}
                className="grid content-start gap-2.5 bg-canvas p-6 lg:p-9"
              >
                <em className="font-display text-4xl font-extrabold not-italic text-ink-muted">
                  {String(index + 1).padStart(2, "0")}
                </em>
                <h3 className="font-display text-xl font-extrabold">
                  {step.title}
                </h3>
                <p className="text-ink-muted">{step.detail}</p>
              </div>
            ))}
          </div>
        </section>

        <section className={section} id="pricing">
          <Pricing />
        </section>

        <section className={section}>
          <div className="relative flex flex-wrap items-center justify-between gap-7 overflow-hidden rounded-2xl p-7 lg:p-16">
            <Image
              src="/landing/a3.jpg"
              alt=""
              fill
              sizes="100vw"
              className="object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-b from-indigo-950/60 to-indigo-950/20" />
            <h2 className="font-display relative z-10 max-w-md text-3xl font-extrabold tracking-tight text-white sm:text-4xl lg:text-5xl">
              Give your board a teammate.{" "}
              <span className="text-indigo-200">Start your trial.</span>
            </h2>
            <Orb size="2xl" className="relative z-10" />
          </div>
        </section>

        <footer className="flex flex-wrap justify-between gap-4 border-t border-hairline px-5 py-6 text-sm text-ink-muted sm:px-8 lg:px-14">
          <span>© 2026 CoordinaAI</span>
          <span>
            Transcripts are sensitive. Everyone in a meeting knows Coordi is
            listening.
          </span>
        </footer>
      </main>

      <a
        href="#try"
        className="fixed right-4 bottom-4 z-40 flex items-center gap-2.5 rounded-xl bg-canvas py-1.5 pr-5 pl-2 font-semibold text-ink shadow-raise"
      >
        <Orb size="sm" />
        Ask Coordi
      </a>
    </div>
  );
}
