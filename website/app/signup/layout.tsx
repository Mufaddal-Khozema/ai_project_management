import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Coordina - Onboarding",
  description:
    "Two quick steps to get your team coordinates locked in. Join the teams who have replaced status meetings with intelligent coordination.",
};

export default function SignupLayout({
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
