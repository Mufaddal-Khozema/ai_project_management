"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogTitle,
  DialogDescription,
  DialogContent,
  DialogHeader,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import {
  useCurrentSubscription,
  useInvoices,
  useCancelSubscriptionMutation,
  currentSubscriptionQueryKey,
  type SubscriptionResponse,
  type InvoiceResponse,
} from "@/lib/api";

const STATUS_BADGES: Record<string, { label: string; className: string }> = {
  trialing: { label: "Trial", className: "" },
  active: { label: "Active", className: "" },
  canceled: { label: "Cancelled", className: "text-destructive" },
  free: { label: "Free", className: "" },
};

function formatDate(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatPrice(
  priceCents: number,
  currency: string,
  interval: string,
): string {
  const symbol = currency === "usd" ? "$" : `${currency.toUpperCase()} `;
  const value = (priceCents / 100).toLocaleString("en-US", {
    maximumFractionDigits: 2,
  });
  const per = interval === "yearly" ? "year" : "month";
  return `${symbol}${value} / ${per}`;
}

function dateLine(sub: SubscriptionResponse): string | null {
  if (sub.status === "trialing" && sub.trial_end) {
    return `Trial ends ${formatDate(sub.trial_end)}`;
  }
  if (sub.status === "active" && sub.current_period_end) {
    return `Renews ${formatDate(sub.current_period_end)}`;
  }
  if (sub.status === "canceled" && sub.current_period_end) {
    return `Ends on ${formatDate(sub.current_period_end)}`;
  }
  return null;
}

function Skeleton({ className }: { className?: string }) {
  return <div className={`bg-muted animate-pulse ${className ?? ""}`} />;
}

export function BillingTab() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  const {
    data: subscription,
    isLoading: subscriptionLoading,
    isError: subscriptionError,
    refetch: refetchSubscription,
  } = useCurrentSubscription();
  const {
    data: invoicesData,
    isLoading: invoicesLoading,
    isError: invoicesError,
    refetch: refetchInvoices,
  } = useInvoices();
  const cancelMutation = useCancelSubscriptionMutation();

  const invoices: InvoiceResponse[] = invoicesData?.invoices ?? [];
  const loadError = subscriptionError || invoicesError;

  const handleConfirmCancel = async () => {
    setCancelError(null);
    try {
      await cancelMutation.mutateAsync({});
      await queryClient.invalidateQueries({
        queryKey: currentSubscriptionQueryKey(),
      });
      setCancelOpen(false);
    } catch (err) {
      setCancelError(
        err instanceof Error ? err.message : "Something went wrong. Please try again.",
      );
    }
  };

  const status = subscription?.status;
  const statusBadge = STATUS_BADGES[status ?? ""] ?? { label: status ?? "", className: "" };
  const isCancelled = status === "canceled";

  return (
    <>
      {loadError && (
        <div className="flex items-center justify-between rounded-lg border border-border bg-muted p-4">
          <p className="text-sm text-muted-foreground">
            We couldn&apos;t load billing info. Please try again.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              refetchSubscription();
              refetchInvoices();
            }}
          >
            Retry
          </Button>
        </div>
      )}

      <Card className="relative overflow-hidden">
        <div className="absolute right-0 top-0 h-32 w-32 bg-gradient-to-bl from-primary/10 to-transparent blur-2xl" />
        <CardHeader>
          <CardTitle>Current plan</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {subscriptionLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-6 w-40" />
              <Skeleton className="h-4 w-56" />
            </div>
          ) : subscription ? (
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-semibold text-card-foreground">
                    {subscription.plan_name}
                  </h3>
                  <Badge variant="outline">
                    {subscription.billing_interval === "yearly" ? "Yearly" : "Monthly"}
                  </Badge>
                  {status && (
                    <Badge
                      variant="outline"
                      className={statusBadge.className || undefined}
                    >
                      {statusBadge.label}
                    </Badge>
                  )}
                </div>
                <p className="mt-0.5 text-sm text-muted-foreground">
                  {status === "free"
                    ? "You are on the Free plan."
                    : formatPrice(
                        subscription.price,
                        subscription.currency ?? "usd",
                        subscription.billing_interval,
                      )}
                  {dateLine(subscription) ? ` · ${dateLine(subscription)}` : ""}
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  router.push(
                    subscription.plan_id === "free"
                      ? "/plans"
                      : `/plans?current=${subscription.plan_id}`,
                  )
                }
              >
                Change plan
              </Button>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Invoice history</CardTitle>
        </CardHeader>
        <CardContent>
          {invoicesLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : invoices.length === 0 ? (
            <p className="text-sm text-muted-foreground py-6 text-center">
              No invoices yet.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">PDF</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoices.map((invoice) => {
                  const statusClass =
                    invoice.status === "paid"
                      ? ""
                      : invoice.status === "open"
                        ? "text-[var(--color-warning)]"
                        : "text-destructive";
                  return (
                    <TableRow key={invoice.id}>
                      <TableCell>{formatDate(invoice.created)}</TableCell>
                      <TableCell>
                        {formatPrice(invoice.amount, invoice.currency, "monthly").split(" / ")[0]}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={statusClass || undefined}>
                          {invoice.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        {invoice.invoice_pdf || invoice.hosted_invoice_url ? (
                          <a
                            href={invoice.hosted_invoice_url ?? invoice.invoice_pdf ?? "#"}
                            target="_blank"
                            rel="noreferrer"
                            className="text-sm font-medium text-primary hover:underline"
                          >
                            PDF
                          </a>
                        ) : (
                          <span className="text-sm text-muted-foreground">—</span>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card className="border-[var(--color-warning)]/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-[var(--color-warning)]">
            <AlertTriangle size={14} />
            Cancel subscription
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Cancelling will downgrade your workspace to the Free plan at the end of
            the current billing period.
          </p>
          <Button
            variant="destructive"
            size="sm"
            disabled={isCancelled}
            onClick={() => {
              setCancelError(null);
              setCancelOpen(true);
            }}
          >
            Cancel subscription
          </Button>
        </CardContent>
      </Card>

      <Dialog open={cancelOpen} onOpenChange={setCancelOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancel subscription</DialogTitle>
            <DialogDescription>
              Your {subscription?.plan_name ?? "current"} features will remain
              active until {formatDate(subscription?.current_period_end) || "the end of your billing period"}.
              After that, you will be moved to the Free plan.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex-col gap-3 sm:flex-row sm:justify-end">
            {cancelError && (
              <p className="text-sm text-destructive sm:mr-auto">{cancelError}</p>
            )}
            <Button
              variant="ghost"
              size="sm"
              disabled={cancelMutation.isPending}
              onClick={() => setCancelOpen(false)}
            >
              Keep {subscription?.plan_name ?? "plan"}
            </Button>
            <Button
              variant="destructive"
              size="sm"
              disabled={cancelMutation.isPending}
              onClick={handleConfirmCancel}
            >
              {cancelMutation.isPending ? (
                <span className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
              ) : (
                "Confirm cancellation"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
