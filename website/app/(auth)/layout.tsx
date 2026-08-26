"use client";
import { withAuth } from "../../components/withAuth";

function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
    </>
  );
}

export default withAuth(AuthLayout);
