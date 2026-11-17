import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Coordina - Sign in",
  description:
    "Sign in to Coordina and keep your projects moving with intelligent coordination.",
};

export default function SigninLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link
        rel="preconnect"
        href="https://fonts.gstatic.com"
        crossOrigin="anonymous"
      />
      <link
        rel="stylesheet"
        precedence="default"
        href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;800&family=Figtree:wght@400;500;600&display=swap"
      />
      {children}
    </>
  );
}
