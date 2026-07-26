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
  return <>{children}</>;
}
