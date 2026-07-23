import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo } from "react";
import { CheckCircle2, Download, Home, MapPin, Truck } from "lucide-react";
import jsPDF from "jspdf";

export const Route = createFileRoute("/success")({
  component: SuccessPage,
  head: () => ({
    meta: [
      { title: "Order Confirmed — Terrific Bites" },
      { name: "description", content: "Thank you! Your Terrific Bites order is confirmed. Download your invoice or return home." },
      { property: "og:title", content: "Order Confirmed — Terrific Bites" },
      { property: "og:description", content: "Your sweet order is on its way. Download your invoice receipt." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "robots", content: "noindex" },
    ],
  }),
});

type Item = { name: string; qty: number; price: number };

function SuccessPage() {
  const order = useMemo(() => {
    const items: Item[] = [
      { name: "Sprinkle Cupcakes", qty: 1, price: 90.99 },
      { name: "Sprinkle Cupcakes", qty: 2, price: 80.99 },
      { name: "Sprinkle Cupcakes", qty: 3, price: 80.99 },
    ];
    const subtotal = items.reduce((s, i) => s + i.qty * i.price, 0);
    const tax = 12.99;
    const total = subtotal + tax;
    return {
      id: "TB-" + Math.random().toString(36).slice(2, 8).toUpperCase(),
      date: new Date(),
      items,
      subtotal,
      tax,
      total,
      customer: "Guest Customer",
      address: "Jakart, Candada",
      method: "Credit Card •••• 4242",
    };
  }, []);

  const downloadInvoice = () => {
    const doc = new jsPDF({ unit: "pt", format: "a4" });
    const w = doc.internal.pageSize.getWidth();
    let y = 60;

    doc.setFont("helvetica", "bold");
    doc.setFontSize(22);
    doc.text("Terrific Bites", 40, y);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(11);
    doc.text("Invoice / Receipt", w - 40, y, { align: "right" });

    y += 30;
    doc.setDrawColor(200);
    doc.line(40, y, w - 40, y);
    y += 25;

    doc.setFontSize(10);
    doc.text(`Order #: ${order.id}`, 40, y);
    doc.text(`Date: ${order.date.toLocaleString()}`, w - 40, y, { align: "right" });
    y += 16;
    doc.text(`Customer: ${order.customer}`, 40, y);
    y += 16;
    doc.text(`Deliver to: ${order.address}`, 40, y);
    y += 16;
    doc.text(`Payment: ${order.method}`, 40, y);

    y += 30;
    doc.setFont("helvetica", "bold");
    doc.text("Item", 40, y);
    doc.text("Qty", 320, y);
    doc.text("Price", 400, y);
    doc.text("Total", w - 40, y, { align: "right" });
    y += 8;
    doc.line(40, y, w - 40, y);
    y += 18;
    doc.setFont("helvetica", "normal");

    order.items.forEach((it) => {
      doc.text(it.name, 40, y);
      doc.text(String(it.qty), 320, y);
      doc.text(`$${it.price.toFixed(2)}`, 400, y);
      doc.text(`$${(it.qty * it.price).toFixed(2)}`, w - 40, y, { align: "right" });
      y += 18;
    });

    y += 10;
    doc.line(40, y, w - 40, y);
    y += 20;
    doc.text("Subtotal", 400, y);
    doc.text(`$${order.subtotal.toFixed(2)}`, w - 40, y, { align: "right" });
    y += 16;
    doc.text("Tax", 400, y);
    doc.text(`$${order.tax.toFixed(2)}`, w - 40, y, { align: "right" });
    y += 20;
    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    doc.text("Total", 400, y);
    doc.text(`$${order.total.toFixed(2)}`, w - 40, y, { align: "right" });

    y += 50;
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.text("Thank you for your order! — Terrific Bites", 40, y);

    doc.save(`invoice-${order.id}.pdf`);
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <div className="bg-white text-center text-[11px] tracking-[0.2em] py-3 uppercase">
        Order Confirmed
      </div>
      <div className="h-8 zigzag-top" style={{ ["--c" as string]: "white" }} />

      <main className="flex-1 max-w-3xl w-full mx-auto px-6 py-10">
        <div className="bg-white rounded-2xl shadow-sm p-8 text-center">
          <div className="mx-auto h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
            <CheckCircle2 className="h-9 w-9 text-primary" />
          </div>
          <h1 className="font-script text-4xl text-primary mt-4">Thank You!</h1>
          <p className="text-sm text-muted-foreground mt-2">
            Your order has been confirmed and is being prepared with love.
          </p>
          <div className="mt-4 inline-flex items-center gap-2 bg-secondary rounded-full px-4 py-1.5 text-sm">
            Order # <span className="font-semibold">{order.id}</span>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-sm p-6 mt-6">
          <h2 className="font-semibold mb-4">Order Details</h2>
          <div className="divide-y divide-border">
            {order.items.map((it, i) => (
              <div key={i} className="flex items-center justify-between py-3 text-sm">
                <div>
                  <p className="font-medium">{it.name}</p>
                  <p className="text-xs text-muted-foreground">Qty {it.qty}</p>
                </div>
                <p>${(it.qty * it.price).toFixed(2)}</p>
              </div>
            ))}
          </div>
          <div className="border-t border-border mt-4 pt-4 space-y-2 text-sm">
            <div className="flex justify-between"><span>Subtotal</span><span>${order.subtotal.toFixed(2)}</span></div>
            <div className="flex justify-between"><span>Tax</span><span>${order.tax.toFixed(2)}</span></div>
            <div className="flex justify-between font-semibold text-base pt-2 border-t border-border">
              <span>Total</span><span>${order.total.toFixed(2)}</span>
            </div>
          </div>

          <div className="mt-6 grid sm:grid-cols-2 gap-3 text-sm">
            <div className="flex items-start gap-2">
              <MapPin className="h-4 w-4 text-primary mt-0.5" />
              <div>
                <p className="text-xs text-muted-foreground">Deliver to</p>
                <p className="font-medium">{order.address}</p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <Truck className="h-4 w-4 text-primary mt-0.5" />
              <div>
                <p className="text-xs text-muted-foreground">Shipping</p>
                <p className="font-medium">Skinniy Express — Today</p>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 flex flex-col sm:flex-row gap-3">
          <button
            onClick={downloadInvoice}
            className="flex-1 bg-primary text-primary-foreground rounded-md py-3 font-semibold hover:opacity-90 inline-flex items-center justify-center gap-2"
          >
            <Download className="h-4 w-4" /> Download Invoice (PDF)
          </button>
          <Link
            to="/"
            className="flex-1 border border-border rounded-md py-3 font-semibold hover:border-primary hover:text-primary inline-flex items-center justify-center gap-2"
          >
            <Home className="h-4 w-4" /> Back to Home
          </Link>
        </div>
      </main>
    </div>
  );
}
