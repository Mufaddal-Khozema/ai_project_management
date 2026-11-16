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
  return <>{children}</>;
}
