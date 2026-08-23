import type { Metadata } from "next";

import { LegalSection } from "@/components/legal/LegalSection";

export const metadata: Metadata = {
  title: "Terms of Service — CoordinaAI",
  description: "The terms governing your use of CoordinaAI.",
};

export default function TermsPage() {
  return (
    <article>
      <p className="mb-5 inline-flex items-center gap-2 font-['JetBrains_Mono',monospace] text-[11px] font-medium uppercase tracking-[0.15em] text-indigo-500">
        <span className="size-[6px] rounded-full bg-indigo-500 animate-pulse" />
        Legal
      </p>
      <h1 className="mb-2 text-3xl font-semibold tracking-tight text-white">
        Terms of Service
      </h1>
      <p className="text-sm text-zinc-500">Last updated: August 17, 2026</p>

      <LegalSection heading="1. Acceptance of Terms">
        <p>
          By accessing or using CoordinaAI, you agree to be bound by these Terms of
          Service. If you do not agree to these terms, please do not use the service.
        </p>
      </LegalSection>

      <LegalSection heading="2. Description of Service">
        <p>
          CoordinaAI provides an AI-powered project coordination platform that helps
          teams plan, track, and manage projects and tasks.
        </p>
      </LegalSection>

      <LegalSection heading="3. Accounts and Eligibility">
        <p>
          You must provide accurate information when creating an account and keep your
          credentials secure. You are responsible for all activity that occurs under your
          account.
        </p>
      </LegalSection>

      <LegalSection heading="4. Subscriptions and Payments">
        <p>
          Certain features require a paid subscription. Payment is processed securely by
          our third-party payment provider, Stripe. Subscriptions renew until cancelled.
        </p>
      </LegalSection>

      <LegalSection heading="5. Acceptable Use">
        <p>
          You agree not to misuse the service, attempt to access it without authorization,
          or use it in a way that violates applicable law or the rights of others.
        </p>
      </LegalSection>

      <LegalSection heading="6. Intellectual Property">
        <p>
          The service and its content are owned by CoordinaAI and its licensors. You may
          not copy, modify, or distribute them without permission.
        </p>
      </LegalSection>

      <LegalSection heading="7. Limitation of Liability">
        <p>
          To the maximum extent permitted by law, CoordinaAI is not liable for indirect,
          incidental, or consequential damages arising from your use of the service.
        </p>
      </LegalSection>

      <LegalSection heading="8. Changes to These Terms">
        <p>
          We may update these Terms from time to time. Continued use of the service after
          changes constitutes acceptance of the revised terms.
        </p>
      </LegalSection>

      <LegalSection heading="9. Contact">
        <p>
          If you have questions about these Terms, please contact us using the details
          provided on our website.
        </p>
      </LegalSection>
    </article>
  );
}