import type { Metadata } from "next";
import Script from "next/script";
import { Providers } from "./providers";
import { StorageKeys } from "@/constants";
import "./globals.css";

export const metadata: Metadata = {
  title: "CoordinaAI — The AI Project Operations Platform",
  description:
    "Our AI coordinator automatically follows up with teammates, synchronizes Jira and Slack, generates reports, and keeps your projects moving.",
};

const themeInitScript = `(function(){try{var s=localStorage.getItem(${JSON.stringify(
  StorageKeys.THEME,
)});if(s!=="light"&&s!=="dark"&&s!=="system"){s="system";}var d=window.matchMedia("(prefers-color-scheme: dark)").matches;var t=s==="system"?(d?"dark":"light"):s;var e=document.documentElement;e.setAttribute("data-theme",t);e.setAttribute("data-theme-preference",s);e.style.colorScheme=t;}catch(_){}})();`;

export default function RootLayout({
  children,
}: { children: React.ReactNode; }) {
  return (
    <html
      lang="en"
      className="h-full antialiased"
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col text-gray-600">
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
        <Providers>{children}</Providers>
        <Script
          src="https://unpkg.com/@phosphor-icons/web"
          strategy="beforeInteractive"
        />
      </body>
    </html>
  );
}