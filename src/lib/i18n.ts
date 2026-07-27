import { useSyncExternalStore } from "react";
import { common } from "./i18n-dict/common";
import { home } from "./i18n-dict/home";
import { about } from "./i18n-dict/about";
import { corporate } from "./i18n-dict/corporate";
import { shop } from "./i18n-dict/shop";
import { product } from "./i18n-dict/product";
import { cart } from "./i18n-dict/cart";
import { customizeDelivery } from "./i18n-dict/customizeDelivery";
import { checkout } from "./i18n-dict/checkout";
import { account } from "./i18n-dict/account";
import { moments } from "./i18n-dict/moments";

export type Lang = "en" | "ar";

const STORAGE_KEY = "tb.lang";
const isBrowser = typeof window !== "undefined";

let currentLang: Lang = (isBrowser && (localStorage.getItem(STORAGE_KEY) as Lang)) || "en";
const listeners = new Set<() => void>();

function applyDir(lang: Lang) {
  if (!isBrowser) return;
  document.documentElement.setAttribute("lang", lang);
  document.documentElement.setAttribute("dir", lang === "ar" ? "rtl" : "ltr");
}
if (isBrowser) applyDir(currentLang);

export function setLang(lang: Lang) {
  currentLang = lang;
  if (isBrowser) {
    localStorage.setItem(STORAGE_KEY, lang);
    applyDir(lang);
  }
  listeners.forEach((l) => l());
}

export function useLang(): Lang {
  return useSyncExternalStore(
    (fn) => {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
    () => currentLang,
    () => "en"
  );
}

const dict = {
  en: {
    ...common.en,
    ...home.en,
    ...about.en,
    ...corporate.en,
    ...shop.en,
    ...product.en,
    ...cart.en,
    ...customizeDelivery.en,
    ...checkout.en,
    ...account.en,
    ...moments.en,
  },
  ar: {
    ...common.ar,
    ...home.ar,
    ...about.ar,
    ...corporate.ar,
    ...shop.ar,
    ...product.ar,
    ...cart.ar,
    ...customizeDelivery.ar,
    ...checkout.ar,
    ...account.ar,
    ...moments.ar,
  },
} as const;

export type TKey = keyof typeof dict["en"];
export function useT() {
  const lang = useLang();
  return (k: TKey) => (dict[lang] as Record<TKey, string>)[k] ?? dict.en[k];
}
