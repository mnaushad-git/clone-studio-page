import { createFileRoute } from "@tanstack/react-router";
import { useAdmin, themeStore, ADMIN_THEME_PRESETS, DEFAULT_ADMIN_THEME, type AdminTheme } from "@/lib/admin-store";
import { Card, Button, Field } from "@/components/admin/ui";
import { Check, RotateCcw } from "lucide-react";

export const Route = createFileRoute("/admin/theme")({ component: ThemePage });

const SWATCHES: { key: keyof AdminTheme; label: string; hint: string }[] = [
  { key: "primary", label: "Primary", hint: "Sidebar & primary buttons" },
  { key: "primaryForeground", label: "Primary text", hint: "Text on primary surfaces" },
  { key: "accent", label: "Accent", hint: "Highlights & badges" },
  { key: "sidebarActive", label: "Sidebar active", hint: "Active nav indicator" },
  { key: "background", label: "Background", hint: "Admin canvas color" },
];

function ThemePage() {
  const theme = useAdmin((s) => s.theme);

  return (
    <div className="max-w-4xl space-y-6">
      <Card
        title="Presets"
        action={
          <Button variant="outline" onClick={() => themeStore.reset()}>
            <RotateCcw className="h-4 w-4" /> Reset default
          </Button>
        }
      >
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {ADMIN_THEME_PRESETS.map((p) => {
            const active =
              theme.primary === p.theme.primary &&
              theme.accent === p.theme.accent &&
              theme.background === p.theme.background;
            return (
              <button
                key={p.name}
                onClick={() => themeStore.set(p.theme)}
                className={`relative rounded-lg border p-3 text-left hover:shadow-sm transition ${active ? "border-stone-900 ring-1 ring-stone-900" : "border-stone-200"}`}
              >
                {active && (
                  <span className="absolute top-2 right-2 bg-stone-900 text-white rounded-full p-0.5">
                    <Check className="h-3 w-3" />
                  </span>
                )}
                <div className="flex gap-1 mb-2">
                  <span className="h-6 w-6 rounded" style={{ background: p.theme.primary }} />
                  <span className="h-6 w-6 rounded" style={{ background: p.theme.accent }} />
                  <span className="h-6 w-6 rounded border" style={{ background: p.theme.background }} />
                  <span className="h-6 w-6 rounded" style={{ background: p.theme.sidebarActive }} />
                </div>
                <div className="text-sm font-medium text-stone-800">{p.name}</div>
              </button>
            );
          })}
        </div>
      </Card>

      <Card title="Custom colors">
        <div className="grid sm:grid-cols-2 gap-5">
          {SWATCHES.map(({ key, label, hint }) => (
            <Field key={key} label={label} hint={hint}>
              <div className="flex items-center gap-3">
                <input
                  type="color"
                  value={theme[key]}
                  onChange={(e) => themeStore.update({ [key]: e.target.value } as Partial<AdminTheme>)}
                  className="h-10 w-14 rounded border border-stone-300 cursor-pointer bg-white"
                />
                <input
                  type="text"
                  value={theme[key]}
                  onChange={(e) => themeStore.update({ [key]: e.target.value } as Partial<AdminTheme>)}
                  className="flex-1 h-10 px-3 rounded-lg border border-stone-300 focus:border-stone-900 focus:outline-none text-sm font-mono"
                />
                <button
                  onClick={() => themeStore.update({ [key]: DEFAULT_ADMIN_THEME[key] } as Partial<AdminTheme>)}
                  className="text-xs text-stone-500 hover:text-stone-800"
                  title="Reset this color"
                >
                  Reset
                </button>
              </div>
            </Field>
          ))}
        </div>
      </Card>

      <Card title="Live preview">
        <div className="rounded-lg overflow-hidden border border-stone-200">
          <div className="flex">
            <div className="w-48 p-4 space-y-2" style={{ background: theme.primary, color: theme.primaryForeground }}>
              <div className="text-sm font-medium">Dashboard</div>
              <div className="text-sm pl-2 border-l-2" style={{ borderColor: theme.sidebarActive }}>Orders</div>
              <div className="text-sm opacity-70">Products</div>
              <div className="text-sm opacity-70">Customers</div>
            </div>
            <div className="flex-1 p-6 space-y-3" style={{ background: theme.background }}>
              <div className="text-lg font-medium text-stone-800">Preview panel</div>
              <div className="flex gap-2">
                <button className="px-4 h-9 rounded-lg text-sm font-medium" style={{ background: theme.primary, color: theme.primaryForeground }}>
                  Primary action
                </button>
                <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium text-white" style={{ background: theme.accent }}>
                  Accent badge
                </span>
              </div>
              <p className="text-sm text-stone-600">
                Colors persist to local storage and apply everywhere in the admin portal.
              </p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
