import type { Metadata } from "next";
import Script from "next/script";
import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "CoordinaAI — The AI Project Operations Platform",
  description:
    "Our AI coordinator automatically follows up with teammates, synchronizes Jira and Slack, generates reports, and keeps your projects moving.",
};

export default function RootLayout({
  children,
}: { children: React.ReactNode; }) {
  return (
    <html
      lang="en"
      className="h-full antialiased"
    >
      <body className="min-h-full flex flex-col text-gray-600">
        <Providers>{children}</Providers>
        <Script
          src="https://unpkg.com/@phosphor-icons/web"
          strategy="beforeInteractive"
        />
      </body>
    </html>
  );
}