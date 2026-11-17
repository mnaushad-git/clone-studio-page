// Headless customer and admin journey against a running stack. Exits non-zero on any failure.
//
// On the native stack:  backend/.venv/Scripts/python deploy/native/native_stack.py browser
// Against any other stack, set E2E_FRONTEND_URL, E2E_API_URL, E2E_ADMIN_EMAIL (or
// NATIVE_ADMIN_EMAIL), E2E_ADMIN_PASSWORD (or NATIVE_ADMIN_PASSWORD), and E2E_DEMO=true when
// the frontend was built with VITE_DEMO_MODE=true.
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import process from "node:process";
import { chromium } from "playwright-core";

const FE = process.env.E2E_FRONTEND_URL ?? "http://localhost:18081";
const API = process.env.E2E_API_URL ?? "http://localhost:18020";
const OUT = process.env.E2E_OUTPUT_DIR ?? path.resolve("test-results/browser");
const DEMO = process.env.E2E_DEMO === "true";
const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? process.env.NATIVE_ADMIN_EMAIL;
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? process.env.NATIVE_ADMIN_PASSWORD;
const CHANNEL = process.env.E2E_BROWSER_CHANNEL ?? "chrome";
const MINIMUM_MESSAGE = /Minimum order is SAR \d+\.\d{2}\. Add SAR \d+\.\d{2} more to checkout\./;
const IDLE = { waitUntil: "networkidle", timeout: 45000 };

mkdirSync(OUT, { recursive: true });
const results = [];
function rec(name, ok, detail = "") {
  results.push({ name, ok: Boolean(ok), detail: String(detail) });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}  ${detail}`);
}

function watch(page, sink) {
  page.on("console", (m) => {
    if (m.type() === "error") sink.push(`${m.text().slice(0, 120)} @${m.location().url.slice(-60)}`);
  });
  page.on("pageerror", (e) => sink.push(`PAGEERROR ${String(e).slice(0, 220)}`));
}

async function addToCart(page, slug, times) {
  await page.goto(`${FE}/product/${slug}`, IDLE);
  for (let i = 0; i < times; i += 1) {
    await page.getByRole("button", { name: "Add To Cart" }).first().click();
    await page.waitForTimeout(400);
  }
}

async function checkFooterLogo(page) {
  await page.goto(`${FE}/`, IDLE);
  const logo = page.locator("footer img").first();
  await logo.scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  const width = await logo.evaluate((img) => img.naturalWidth);
  const src = await logo.getAttribute("src");
  rec("footer logo loads from the local bundle", width > 0 && !src.includes("__l5e"), `${src} width=${width}`);
}

async function checkMinimumOrder(browser, items) {
  const cheap = items.find((p) => Number(p.price) > 0 && Number(p.price) < 30);
  if (!cheap) {
    rec("minimum order blocks checkout", false, "no product under SAR 30 to test with");
    return;
  }
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 850 } });
  const page = await ctx.newPage();
  await addToCart(page, cheap.slug, 1);
  for (const [route, button] of [
    ["/customize", /Continue to Delivery/i],
    ["/delivery", /Continue to Payment/i],
  ]) {
    await page.goto(`${FE}${route}`, IDLE);
    const text = await page.getByRole("alert").first().innerText();
    const disabled = await page.getByRole("button", { name: button }).first().isDisabled();
    rec(`minimum order message on ${route}`, MINIMUM_MESSAGE.test(text), text);
    rec(`minimum order blocks ${route}`, disabled, `disabled=${disabled}`);
  }
  await page.goto(`${FE}/payment`, IDLE);
  const pay = page.locator("button:has(svg.lucide-lock)").last();
  rec("minimum order blocks payment", await pay.isDisabled());
  await ctx.close();
}

async function choosePaymentMethod(page) {
  if (DEMO) return;
  const wallet = page.locator("label", { hasText: /Apple Pay|PayPal/ }).first();
  if (await wallet.count()) await wallet.click();
}

async function main() {
  const browser = await chromium.launch({ channel: CHANNEL, headless: true });
  const catalogue = await (await fetch(`${API}/api/v1/catalogue/products?page_size=100`)).json();
  const items = catalogue.items ?? catalogue.data ?? catalogue;
  rec("API serves catalogue", Array.isArray(items) && items.length > 0, `count=${items.length}`);
  const product = items.find((p) => Number(p.price) >= 30) ?? items[0];
  const slug = product.slug;

  const ctx = await browser.newContext({ viewport: { width: 1366, height: 850 } });
  const page = await ctx.newPage();
  const errs = [];
  watch(page, errs);
  const routes = ["/", "/shop", "/cakes", "/cupcakes", "/gifts", "/moments", "/recipients", `/product/${slug}`, "/about", "/corporate", "/wishlist", "/login", "/admin/login"];
  for (const route of routes) {
    errs.length = 0;
    const r = await page.goto(FE + route, IDLE);
    const hydration = errs.filter((e) => /hydrat|did not match/i.test(e));
    const logo404 = errs.filter((e) => /logo-footer/.test(e));
    const crashed = errs.some((e) => e.startsWith("PAGEERROR"));
    rec(`route ${route}`, r.status() === 200 && !hydration.length && !logo404.length && !crashed, `status=${r.status()} consoleErrors=${errs.length} ${errs[0] ?? ""}`);
  }

  await checkFooterLogo(page);
  await checkMinimumOrder(browser, items);

  const html = await (await fetch(`${FE}/product/${slug}`)).text();
  rec("SSR renders product HTML", html.includes(product.name_en ?? product.name ?? slug), `len=${html.length}`);

  await addToCart(page, slug, 3);
  await page.goto(`${FE}/customize`, IDLE);
  await page.screenshot({ path: path.join(OUT, "customize.png"), fullPage: true });
  rec("customize reached", page.url().includes("/customize"), page.url());
  await page.getByRole("button", { name: /Continue to Delivery/i }).first().click();
  await page.waitForURL(/delivery/, { timeout: 15000 });
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1200);
  const inputs = page.locator("main input:not([type=checkbox])");
  await inputs.nth(0).fill("E2E Customer");
  await inputs.nth(1).fill("500000000");
  await page.locator("main select").first().selectOption({ index: 1 });
  await inputs.nth(2).fill("123 Test Street");
  await page.getByRole("button", { name: /Continue to Payment/i }).click();
  await page.waitForURL(/payment/, { timeout: 15000 });
  await page.waitForLoadState("networkidle");
  await page.locator("button:has(svg.lucide-lock)").last().waitFor({ timeout: 15000 });
  await choosePaymentMethod(page);
  await page.screenshot({ path: path.join(OUT, "payment.png"), fullPage: true });
  const payBtn = page.locator("button:has(svg.lucide-lock)").last();
  const payText = await payBtn.innerText();
  rec("payment button labelled for this mode", /demo/i.test(payText) === DEMO, payText.replace(/\s+/g, " "));
  const orderResp = page.waitForResponse((r) => r.url().endsWith("/api/v1/orders") && r.request().method() === "POST", { timeout: 20000 });
  const payResp = page.waitForResponse((r) => /\/pay$/.test(r.url()), { timeout: 20000 });
  await payBtn.click();
  const [created, paid] = await Promise.all([orderResp, payResp]);
  const order = await paid.json();
  rec("order created via API", created.status() === 200 || created.status() === 201, `status=${created.status()}`);
  rec("order paid via stub", paid.status() === 200 && order.status === "paid", `status=${paid.status()} order=${order.order_number}`);
  rec("order number matches the mode", (DEMO ? /^DEMO-/ : /^TB-/).test(order.order_number ?? ""), order.order_number);
  await page.waitForURL(/success/, { timeout: 15000 });
  await page.waitForLoadState("networkidle");
  const shown = await page.locator("body", { hasText: order.order_number }).waitFor({ timeout: 15000 }).then(() => true, () => false);
  rec("confirmation shown", shown, page.url());
  await page.screenshot({ path: path.join(OUT, "success.png"), fullPage: true });
  writeFileSync(path.join(OUT, "order.json"), JSON.stringify(order, null, 1));

  const r = await page.goto(`${FE}/track/${order.tracking_token}`, IDLE);
  rec("order tracking", r.status() === 200 && (await page.locator("body").innerText()).includes(order.order_number));

  await page.evaluate(() => localStorage.setItem("tb.lang", "ar"));
  await page.goto(`${FE}/shop`, IDLE);
  const dir = await page.evaluate(() => document.documentElement.getAttribute("dir"));
  const arabic = /[؀-ۿ]{3,}/.test(await page.locator("body").innerText());
  rec("Arabic RTL", dir === "rtl" && arabic, `dir=${dir} arabicText=${arabic}`);
  await page.evaluate(() => localStorage.setItem("tb.lang", "en"));

  const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const mp = await mobile.newPage();
  for (const route of ["/", "/shop", `/product/${slug}`, "/delivery"]) {
    await mp.goto(FE + route, IDLE);
    const over = await mp.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    rec(`mobile ${route} no horizontal overflow`, over <= 1, `overflowPx=${over}`);
  }

  const adminCtx = await browser.newContext({ viewport: { width: 1366, height: 850 } });
  const ap = await adminCtx.newPage();
  const aerr = [];
  watch(ap, aerr);
  await ap.goto(`${FE}/admin/login`, IDLE);
  await ap.locator('input[type="email"]').fill(ADMIN_EMAIL);
  await ap.locator('input[type="password"]').fill(ADMIN_PASSWORD);
  const login = ap.waitForResponse((res) => res.url().includes("/admin/auth/login"), { timeout: 20000 });
  await ap.locator('button[type="submit"]').click();
  rec("admin login", (await login).status() === 200);
  await ap.waitForURL((u) => !u.pathname.endsWith("/login"), { timeout: 15000 });
  await ap.waitForLoadState("networkidle");
  for (const route of ["/admin", "/admin/orders", "/admin/products", "/admin/categories", "/admin/system"]) {
    aerr.length = 0;
    const res = await ap.goto(FE + route, IDLE);
    const authFail = aerr.filter((e) => /401|403/.test(e));
    rec(`admin ${route}`, res.status() === 200 && !ap.url().includes("/login") && !authFail.length, `errors=${aerr.length} ${aerr[0] ?? ""}`);
  }
  await ap.goto(`${FE}/admin/orders`, IDLE);
  rec("admin sees the order", (await ap.locator("body").innerText()).includes(order.order_number), order.order_number);

  await browser.close();
  const failed = results.filter((x) => !x.ok);
  console.log(`\nSUMMARY ${results.length - failed.length}/${results.length} passed`);
  writeFileSync(path.join(OUT, "results.json"), JSON.stringify(results, null, 1));
  process.exit(failed.length ? 1 : 0);
}

main().catch((e) => {
  console.error("CRASH", e);
  console.log(JSON.stringify(results.filter((r) => !r.ok)));
  process.exit(2);
});
