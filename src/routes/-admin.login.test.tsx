import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi, beforeEach } from "vitest";

const mockNavigate = vi.fn();

vi.mock("@tanstack/react-router", () => ({
  createFileRoute: () => (opts: { component: React.ComponentType }) => opts,
  useNavigate: () => mockNavigate,
}));

vi.mock("@/lib/admin-api", () => ({
  login: vi.fn(),
  AdminApiError: class AdminApiError extends Error {
    status?: number;
    constructor(message: string, status?: number) {
      super(message);
      this.name = "AdminApiError";
      this.status = status;
    }
  },
}));

import { Route } from "./admin.login";
import { login, AdminApiError } from "@/lib/admin-api";

function renderLogin() {
  const queryClient = new QueryClient();
  // The mocked createFileRoute() above returns its options object verbatim, so
  // `.component` exists at runtime — the real (unmocked) Route type doesn't expose
  // it, hence the cast.
  const AdminLogin = (Route as unknown as { component: React.ComponentType }).component;
  return render(
    <QueryClientProvider client={queryClient}>
      <AdminLogin />
    </QueryClientProvider>,
  );
}

describe("AdminLogin", () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    vi.mocked(login).mockReset();
  });

  it("submits the entered email/password and navigates to /admin on success", async () => {
    const user = userEvent.setup();
    vi.mocked(login).mockResolvedValueOnce({
      id: "1",
      email: "owner@terrificbites.sa",
      full_name: "Owner",
      role: "SUPER_ADMIN",
      is_active: true,
      last_login_at: null,
    });

    renderLogin();
    await user.type(screen.getByLabelText(/work email/i), "owner@terrificbites.sa");
    await user.type(screen.getByLabelText(/password/i), "correct-password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith({ to: "/admin" }));
    expect(login).toHaveBeenCalledWith("owner@terrificbites.sa", "correct-password");
  });

  it("shows the backend's error message and does not navigate on invalid credentials", async () => {
    const user = userEvent.setup();
    vi.mocked(login).mockRejectedValueOnce(new AdminApiError("Invalid email or password.", 401));

    renderLogin();
    await user.type(screen.getByLabelText(/work email/i), "owner@terrificbites.sa");
    await user.type(screen.getByLabelText(/password/i), "wrong-password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText("Invalid email or password.")).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("never renders a hint suggesting a demo/default password", () => {
    renderLogin();
    expect(screen.queryByText(/demo/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/admin123/i)).not.toBeInTheDocument();
  });
});
