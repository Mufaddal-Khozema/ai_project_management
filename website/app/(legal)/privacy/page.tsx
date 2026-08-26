import type { Metadata } from "next";

import { LegalSection } from "@/components/legal/LegalSection";

export const metadata: Metadata = {
  title: "Privacy Policy — CoordinaAI",
  description: "How CoordinaAI collects, uses, and protects your information.",
};

export default function PrivacyPage() {
  return (
    <article>
      <p className="mb-5 inline-flex items-center gap-2 font-['JetBrains_Mono',monospace] text-[11px] font-medium uppercase tracking-[0.15em] text-indigo-500">
        <span className="size-[6px] rounded-full bg-indigo-500 animate-pulse" />
        Legal
      </p>
      <h1 className="mb-2 text-3xl font-semibold tracking-tight text-white">
        Privacy Policy
      </h1>
      <p className="text-sm text-zinc-500">Last updated: August 17, 2026</p>

      <LegalSection heading="1. Information We Collect">
        <p>
          We collect information you provide when you create an account, such as your name,
          email address, company, and a password (stored as a secure hash). We also collect
          workspace and onboarding information, and data needed to operate the service.
        </p>
      </LegalSection>

      <LegalSection heading="2. How We Use Your Information">
        <p>
          We use your information to provide, maintain, and improve the service, to
          communicate with you, and to keep your account secure.
        </p>
      </LegalSection>

      <LegalSection heading="3. Payment Data">
        <p>
          Payment processing is handled by Stripe. We do not store your full card number on
          our servers. Card details are transmitted directly to Stripe over an encrypted
          connection.
        </p>
      </LegalSection>

      <LegalSection heading="4. Cookies and Local Storage">
        <p>
          We use cookies and browser local storage to keep you signed in and to store
          authentication tokens. You can control these through your browser settings.
        </p>
      </LegalSection>

      <LegalSection heading="5. Third-Party Processors">
        <p>
          We share limited information with trusted service providers that help us operate
          the service, including our payment processor (Stripe) and hosting provider. We
          require these providers to protect your data.
        </p>
      </LegalSection>

      <LegalSection heading="6. Data Retention and Security">
        <p>
          We retain your information for as long as your account is active or as needed to
          provide the service. We apply industry-standard safeguards to protect your data.
        </p>
      </LegalSection>

      <LegalSection heading="7. Your Rights">
        <p>
          Depending on your location, you may have the right to access, correct, or delete
          your personal data, and to opt out of certain processing. To exercise these
          rights, please contact us.
        </p>
      </LegalSection>

      <LegalSection heading="8. Changes to This Policy">
        <p>
          We may update this Privacy Policy from time to time. We will post any changes on
          this page with an updated revision date.
        </p>
      </LegalSection>

      <LegalSection heading="9. Contact Us">
        <p>
          If you have questions about this Privacy Policy or your personal data, please
          contact us using the details provided on our website.
        </p>
      </LegalSection>
    </article>
  );
}