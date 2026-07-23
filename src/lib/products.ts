import prodSwiss from "@/assets/prod-swiss.jpg";
import prodMoose from "@/assets/prod-moose.jpg";
import prodButter from "@/assets/prod-butter.jpg";
import prodLight from "@/assets/prod-light.jpg";
import giftDonuts from "@/assets/gift-donuts.jpg";
import giftButter from "@/assets/gift-butter.jpg";
import giftCream from "@/assets/gift-cream.jpg";
import giftWhisk from "@/assets/gift-whisk.jpg";
import divine1 from "@/assets/divine-1.jpg";
import divine2 from "@/assets/divine-2.jpg";
import divine3 from "@/assets/divine-3.jpg";
import divine4 from "@/assets/divine-4.jpg";
import c1 from "@/assets/choc-1.jpg";
import c2 from "@/assets/choc-2.jpg";
import c3 from "@/assets/choc-3.jpg";
import c4 from "@/assets/choc-4.jpg";
import c5 from "@/assets/choc-5.jpg";
import c6 from "@/assets/choc-6.jpg";
import c7 from "@/assets/choc-7.jpg";
import c8 from "@/assets/choc-8.jpg";
import c9 from "@/assets/choc-9.jpg";
import cakeMain from "@/assets/cake-main.jpg";
import cakeT2 from "@/assets/cake-thumb-2.jpg";
import cakeT3 from "@/assets/cake-thumb-3.jpg";
import cakeT4 from "@/assets/cake-thumb-4.jpg";
import extraDonut from "@/assets/extra-donut.jpg";
import extraIcecream from "@/assets/extra-icecream.jpg";
import extraCheesecake from "@/assets/extra-cheesecake.jpg";
import extraDonutsPair from "@/assets/extra-donuts-pair.jpg";

export type Product = {
  id: string;
  name: string;
  price: number;
  image: string;
  thumbs?: string[];
  category: "cupcakes" | "cakes" | "chocolates" | "donuts" | "gifts" | "extras";
  tags?: string[];
  sizes?: { label: string; sub?: string; delta?: number }[];
  flavors?: string[];
  description?: string;
  isNew?: boolean;
};

export const products: Product[] = [
  { id: "swiss-frosting", name: "Swiss Frosting", price: 12.5, image: prodSwiss, category: "cupcakes", isNew: true,
    description: "Silky Swiss meringue buttercream on our signature vanilla sponge." },
  { id: "moose-cream", name: "Moose Cream", price: 14.0, image: prodMoose, category: "cupcakes",
    description: "Rich chocolate mousse crowned with cocoa curls." },
  { id: "butter-frosting", name: "Butter Frosting", price: 11.0, image: prodButter, category: "cupcakes",
    description: "Classic American butter frosting on golden butter cake." },
  { id: "light-sponge", name: "Light Sponge", price: 9.5, image: prodLight, category: "cupcakes",
    description: "Airy sponge with a whisper of vanilla — light and delicate." },

  { id: "buttercream-cake", name: "Buttercream Cake", price: 300, image: cakeMain,
    thumbs: [cakeMain, cakeT2, cakeT3, cakeT4], category: "cakes",
    sizes: [
      { label: "6 INCH", sub: "3 Layers", delta: 0 },
      { label: "9 INCH", sub: "3 Layers", delta: 80 },
    ],
    flavors: ["Vanilla", "Chocolate"],
    description: "Three luscious layers of buttercream cake, finished with rainbow sprinkles and a cherry on top." },

  { id: "birthday-pair", name: "Birthday Pair Cups", price: 22, image: giftDonuts, category: "gifts",
    description: "A pair of celebration cupcakes ready to gift." },
  { id: "butter-delight", name: "Butter Frosting Delight", price: 18, image: giftButter, category: "gifts",
    description: "Butter-frosted bites in a golden gift box." },
  { id: "cream-cheese-donut", name: "Cream & Cheese Donut", price: 8, image: giftCream, category: "donuts",
    description: "Fluffy donut filled with cream cheese frosting." },
  { id: "whisk-whimsy", name: "Whisk & Whimsy Cupcake", price: 15, image: giftWhisk, category: "gifts",
    description: "Whimsical cupcake decorated by hand." },

  { id: "sprinkle-1", name: "Sprinkle Cupcakes", price: 4.5, image: divine1, category: "cupcakes",
    description: "Colorful sprinkle-topped cupcakes for any occasion." },
  { id: "sprinkle-2", name: "Cherry Sprinkle", price: 4.5, image: divine2, category: "cupcakes" },
  { id: "sprinkle-3", name: "Pink Whip", price: 4.5, image: divine3, category: "cupcakes" },
  { id: "sprinkle-4", name: "Confetti Whip", price: 4.5, image: divine4, category: "cupcakes" },

  { id: "choc-truffle", name: "Chocolate Truffle", price: 6.99, image: c1, category: "chocolates",
    description: "Dark chocolate truffles rolled in cocoa." },
  { id: "choc-praline", name: "Hazelnut Praline", price: 7.5, image: c2, category: "chocolates" },
  { id: "choc-ganache", name: "Ganache Bites", price: 8.25, image: c3, category: "chocolates" },
  { id: "choc-caramel", name: "Salted Caramel", price: 7.25, image: c4, category: "chocolates" },
  { id: "choc-mint", name: "Mint Delight", price: 6.5, image: c5, category: "chocolates" },
  { id: "choc-orange", name: "Orange Zest", price: 6.75, image: c6, category: "chocolates" },
  { id: "choc-almond", name: "Roasted Almond", price: 7.99, image: c7, category: "chocolates" },
  { id: "choc-white", name: "White Dream", price: 6.25, image: c8, category: "chocolates" },
  { id: "choc-berry", name: "Berry Truffle", price: 7.99, image: c9, category: "chocolates" },

  { id: "extra-donut", name: "Fanky Donut", price: 4.89, image: extraDonut, category: "extras" },
  { id: "extra-icecream", name: "Icecream Cone", price: 5.49, image: extraIcecream, category: "extras" },
  { id: "extra-cheesecake", name: "Mini Cheesecake", price: 6.29, image: extraCheesecake, category: "extras" },
  { id: "extra-donuts-pair", name: "Donuts Pair", price: 7.89, image: extraDonutsPair, category: "extras" },
];

export const productMap: Record<string, Product> = Object.fromEntries(
  products.map((p) => [p.id, p])
);

export function getProduct(id: string): Product | undefined {
  return productMap[id];
}

export const featured = {
  hero: products.filter((p) => p.category === "cupcakes").slice(0, 4),
  gifts: products.filter((p) => p.category === "gifts" || p.id === "cream-cheese-donut").slice(0, 4),
  divine: products.filter((p) => p.id.startsWith("sprinkle-")),
  chocolates: products.filter((p) => p.category === "chocolates"),
  extras: products.filter((p) => p.category === "extras"),
  new: products.filter((p) => p.isNew),
};
