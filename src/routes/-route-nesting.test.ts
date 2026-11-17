// Guards against a page that can never render. With TanStack Router flat file routes,
// `a.b.c.tsx` becomes a child of `a.b.tsx` when that file exists, and a child only shows
// if the parent renders an <Outlet />. admin.orders.tsx (the orders list, no Outlet) once
// owned admin.orders.$orderId.tsx, so opening an order changed the URL but kept showing
// the list.
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const ROUTES_DIR = path.resolve(__dirname);
const routeFiles = readdirSync(ROUTES_DIR)
  .filter((f) => /\.tsx?$/.test(f) && !f.startsWith("-") && !f.startsWith("__root"))
  .map((f) => f.replace(/\.tsx?$/, ""));
const byName = new Set(routeFiles);

/** The flat-file parent of a route, or undefined when it sits directly under a layout
 * further up (or the root). A segment ending in "_" opts out of nesting under it. */
function parentOf(name: string): string | undefined {
  const segments = name.split(".");
  for (let n = segments.length - 1; n >= 1; n--) {
    const prefix = segments.slice(0, n);
    if (prefix[prefix.length - 1].endsWith("_")) return undefined;
    const candidate = prefix.join(".");
    if (byName.has(candidate)) return candidate;
  }
  return undefined;
}

describe("route nesting", () => {
  it("every route file with a parent route file is rendered through that parent's <Outlet />", () => {
    const broken = routeFiles
      .map((name) => ({ name, parent: parentOf(name) }))
      .filter((r): r is { name: string; parent: string } => r.parent !== undefined)
      .filter(({ parent }) => {
        const file = [`${parent}.tsx`, `${parent}.ts`].find((f) => byName.has(parent) && safeRead(f));
        return !file || !/<Outlet\b/.test(safeRead(file) ?? "");
      })
      .map(({ name, parent }) => `${name} is nested under ${parent}, which has no <Outlet />`);
    expect(broken).toEqual([]);
  });

  it("the admin order list and order detail are sibling pages under the admin layout", () => {
    const tree = readFileSync(path.resolve(ROUTES_DIR, "../routeTree.gen.ts"), "utf8");
    const detail = tree.match(/const AdminOrdersOrderIdRoute = [\s\S]*?getParentRoute: \(\) => (\w+)/);
    const list = tree.match(/const AdminOrdersIndexRoute = [\s\S]*?getParentRoute: \(\) => (\w+)/);
    expect(detail?.[1]).toBe("AdminRoute");
    expect(list?.[1]).toBe("AdminRoute");
    expect(byName.has("admin.orders")).toBe(false);
  });
});

function safeRead(file: string): string | undefined {
  try {
    return readFileSync(path.join(ROUTES_DIR, file), "utf8");
  } catch {
    return undefined;
  }
}
