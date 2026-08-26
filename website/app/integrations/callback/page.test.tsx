import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { INTEGRATION_OAUTH_MESSAGE } from "@/lib/integrations";
import IntegrationCallbackPage from "./page";

vi.mock("next/navigation", () => ({
  useSearchParams: () => searchParams(),
}));

let searchParams = vi.fn<() => URLSearchParams>();

function mockParams(entries: Record<string, string>) {
  searchParams.mockReturnValue(new URLSearchParams(entries));
}

function mockReplace() {
  const replace = vi.fn();
  Object.defineProperty(window, "location", {
    value: { replace },
    configurable: true,
  });
  return replace;
}

describe("IntegrationCallbackPage", () => {
  beforeEach(() => {
    searchParams = vi.fn<() => URLSearchParams>();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("postMessages and closes the window when opened as a popup", () => {
    const postMessage = vi.fn();
    Object.defineProperty(window, "opener", { value: { postMessage }, configurable: true });
    const close = vi.spyOn(window, "close").mockImplementation(() => {});
    mockParams({ provider: "slack", status: "connected", source: "settings" });

    render(<IntegrationCallbackPage />);

    expect(postMessage).toHaveBeenCalledWith(
      { type: INTEGRATION_OAUTH_MESSAGE, provider: "slack", status: "connected" },
      window.location.origin,
    );
    expect(close).toHaveBeenCalled();
    expect(screen.getByText("Connection complete — you can close this window.")).toBeDefined();
  });

  it("redirects to settings when not a popup (source=settings)", () => {
    Object.defineProperty(window, "opener", { value: undefined, configurable: true });
    const replace = mockReplace();
    mockParams({ provider: "jira", status: "connected", source: "settings" });

    render(<IntegrationCallbackPage />);

    expect(replace).toHaveBeenCalledWith("/admin/settings");
    expect(screen.getByText("Connection complete — redirecting…")).toBeDefined();
  });

  it("redirects to onboarding when not a popup (source=onboarding)", () => {
    Object.defineProperty(window, "opener", { value: undefined, configurable: true });
    const replace = mockReplace();
    mockParams({ provider: "slack", status: "error", source: "onboarding" });

    render(<IntegrationCallbackPage />);

    expect(replace).toHaveBeenCalledWith("/admin?onboarding=1");
  });
});