import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { QueryState } from "@/components/QueryState";

describe("QueryState", () => {
  it("renders skeleton placeholders while loading, not the children", () => {
    render(
      <QueryState isLoading isError={false}>
        <div>Real content</div>
      </QueryState>,
    );

    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.queryByText("Real content")).not.toBeInTheDocument();
  });

  it("renders an error alert with a retry action on error, not the children", async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    render(
      <QueryState isLoading={false} isError onRetry={onRetry}>
        <div>Real content</div>
      </QueryState>,
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.queryByText("Real content")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button"));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("renders children once loading succeeds without error", () => {
    render(
      <QueryState isLoading={false} isError={false}>
        <div>Real content</div>
      </QueryState>,
    );

    expect(screen.getByText("Real content")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("omits the retry button when no onRetry handler is given", () => {
    render(
      <QueryState isLoading={false} isError>
        <div>Real content</div>
      </QueryState>,
    );

    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
