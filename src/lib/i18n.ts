import { useSyncExternalStore } from "react";

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
    orderPickup: "Order Desserts for Local Pickup",
    myAccount: "My Account",
    cart: "Cart",
    english: "English",
    arabic: "العربية",
    menu: "Menu",
    explore: "Explore",
    moments: "Moments",
    recipients: "Recipients",
    cakes: "Cakes & Cupcakes",
    chocolates: "Chocolates",
    donuts: "Donuts & Pastries",
    gifts: "Gifts & Hampers",
    aboutUs: "About Us",
    signIn: "Sign in",
    close: "Close",
  },
  ar: {
    orderPickup: "اطلب الحلويات للاستلام محلياً",
    myAccount: "حسابي",
    cart: "السلة",
    english: "English",
    arabic: "العربية",
    menu: "القائمة",
    explore: "استكشف",
    moments: "المناسبات",
    recipients: "المستلمون",
    cakes: "الكعك والكب كيك",
    chocolates: "الشوكولاتة",
    donuts: "الدونات والمعجنات",
    gifts: "الهدايا والسلال",
    aboutUs: "من نحن",
    signIn: "تسجيل الدخول",
    close: "إغلاق",
  },
} as const;

export type TKey = keyof typeof dict["en"];
export function useT() {
  const lang = useLang();
  return (k: TKey) => dict[lang][k] ?? dict.en[k];
}
