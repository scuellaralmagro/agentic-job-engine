import { act, render, screen } from "@testing-library/react";
import { OfflineBanner } from "./providers";

vi.mock("virtual:pwa-register/react", () => ({
  useRegisterSW: () => ({
    needRefresh: [false, vi.fn()],
    offlineReady: [false, vi.fn()],
    updateServiceWorker: vi.fn(),
  }),
}));

test("shows banner when the browser goes offline", () => {
  render(<OfflineBanner />);
  expect(screen.queryByText(/offline/i)).not.toBeInTheDocument();

  act(() => {
    Object.defineProperty(navigator, "onLine", {
      value: false,
      configurable: true,
    });
    window.dispatchEvent(new Event("offline"));
  });
  expect(screen.getByText(/offline — showing cached data/i)).toBeInTheDocument();

  act(() => {
    Object.defineProperty(navigator, "onLine", {
      value: true,
      configurable: true,
    });
    window.dispatchEvent(new Event("online"));
  });
  expect(screen.queryByText(/offline/i)).not.toBeInTheDocument();
});
