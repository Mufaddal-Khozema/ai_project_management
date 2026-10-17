import { createClient } from "@/lib/api/client";
import { listPlans } from "@/lib/api/sdk.gen";
import PricingCards from "./pricing-cards";
import { PlanResponse } from "@/lib/api/types.gen";
import { API_URL } from "@/constants";

export default async function PricingPlans() {
  let plans: PlanResponse[] = [];

  try {
    const serverClient = createClient({
      baseUrl: API_URL,
    });

    const { data } = await listPlans({
      client: serverClient,
      throwOnError: true,
    });

    plans = data.plans;
  } catch (err) {
    console.error(err);
  }

  return <PricingCards plans={plans} />;
}
