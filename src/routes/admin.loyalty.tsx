import { createFileRoute } from "@tanstack/react-router";
import { useAdmin, loyaltyConfig } from "@/lib/admin-store";
import { Card, Field, Input, Toggle } from "@/components/admin/ui";

export const Route = createFileRoute("/admin/loyalty")({ component: LoyaltyPage });

function LoyaltyPage() {
  const l = useAdmin((s) => s.loyalty);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card title="Loyalty program">
        <div className="space-y-4">
          <Toggle checked={l.enabled} onChange={(v) => loyaltyConfig.update({ enabled: v })} label="Enable loyalty program" />
          <div className="grid grid-cols-2 gap-3">
            <Field label="Points earned per SAR spent"><Input type="number" step="0.1" value={l.pointsPerSar} onChange={(e) => loyaltyConfig.update({ pointsPerSar: Number(e.target.value) })} /></Field>
            <Field label="Redeem rate (pts = SAR 1)"><Input type="number" value={l.redeemRate} onChange={(e) => loyaltyConfig.update({ redeemRate: Number(e.target.value) })} /></Field>
            <Field label="Signup bonus (points)"><Input type="number" value={l.signupBonus} onChange={(e) => loyaltyConfig.update({ signupBonus: Number(e.target.value) })} /></Field>
            <Field label="Birthday bonus (points)"><Input type="number" value={l.birthdayBonus} onChange={(e) => loyaltyConfig.update({ birthdayBonus: Number(e.target.value) })} /></Field>
          </div>
        </div>
      </Card>
      <Card title="How it works">
        <ul className="text-sm text-slate-600 space-y-2 list-disc pl-5">
          <li>Customers earn <strong>{l.pointsPerSar}</strong> point per SAR spent.</li>
          <li><strong>{l.redeemRate}</strong> points = SAR 1 at checkout.</li>
          <li>New accounts receive <strong>{l.signupBonus}</strong> welcome points.</li>
          <li>Birthdays reward <strong>{l.birthdayBonus}</strong> bonus points.</li>
        </ul>
      </Card>
    </div>
  );
}
