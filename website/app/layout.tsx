import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Script from "next/script";
import { Providers } from "./providers";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CoordinaAI — The AI Project Operations Platform",
  description:
    "Our AI coordinator automatically follows up with teammates, synchronizes Jira and Slack, generates reports, and keeps your projects moving.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <Providers>{children}</Providers>
        <Script
          src="https://unpkg.com/@phosphor-icons/web"
          strategy="beforeInteractive"
        />
	{/* <Script
          src="https://assets.codepen.io/16327/SplitText3.min.js"
          strategy="beforeInteractive"
        /> */}
      </body>
    </html>
  );
}
