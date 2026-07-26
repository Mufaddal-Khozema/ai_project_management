import { createClient, createConfig } from "@/lib/api/client";
import { apiPaymentsPlansPlansHandler } from "@/lib/api/sdk.gen";
import PricingCards from "./pricing-cards";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default async function PricingPlans() {
  try {
    const serverClient = createClient(createConfig({ baseUrl: API_URL }));
    const { data } = await apiPaymentsPlansPlansHandler({
      client: serverClient,
      throwOnError: true,
    });
    return <PricingCards plans={data.plans} />;
  } catch (err) {
	  console.error(err);
	  throw err;
  }
}
