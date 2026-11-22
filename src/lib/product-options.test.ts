import { describe, expect, it } from "vitest";
import { productGallery, resolveSelection, selectorAxes } from "./product-options";

const single = { price: 19, sku: "TB-DEMO-001" };

const cake = {
  price: 300,
  sku: "CAKE-6-VAN",
  variantAxes: [
    { code: "size", name: "Size", values: ["6 INCH", "9 INCH"] },
    { code: "flavor", name: "Flavor", values: ["Vanilla", "Chocolate"] },
  ],
  variantPriceByKey: {
    "flavor=Vanilla|size=6 INCH": 300,
    "flavor=Chocolate|size=6 INCH": 310,
    "flavor=Vanilla|size=9 INCH": 380,
    // 9 INCH Chocolate deliberately has no variant.
  },
  variantSkuByKey: {
    "flavor=Vanilla|size=6 INCH": "CAKE-6-VAN",
    "flavor=Chocolate|size=6 INCH": "CAKE-6-CHO",
    "flavor=Vanilla|size=9 INCH": "CAKE-9-VAN",
  },
};

describe("selectorAxes", () => {
  it("returns no selectors for a product without real variants", () => {
    expect(selectorAxes({ variantAxes: undefined })).toEqual([]);
    expect(selectorAxes({ variantAxes: [] })).toEqual([]);
  });

  it("returns exactly the product's real axes", () => {
    expect(selectorAxes(cake).map((a) => a.code)).toEqual(["size", "flavor"]);
  });
});

describe("resolveSelection", () => {
  it("buys the single real variant with no invented attributes", () => {
    expect(resolveSelection(single, {})).toEqual({ attributes: undefined, unitPrice: 19, sku: "TB-DEMO-001", available: true });
  });

  it("defaults to the first value of each axis", () => {
    expect(resolveSelection(cake, {})).toEqual({
      attributes: { size: "6 INCH", flavor: "Vanilla" },
      unitPrice: 300,
      sku: "CAKE-6-VAN",
      available: true,
    });
  });

  it("updates SKU and price to the chosen variant", () => {
    expect(resolveSelection(cake, { flavor: 1 })).toMatchObject({ unitPrice: 310, sku: "CAKE-6-CHO", available: true });
    expect(resolveSelection(cake, { size: 1 })).toMatchObject({ unitPrice: 380, sku: "CAKE-9-VAN", available: true });
  });

  it("opens on the default variant even when it isn't listed first", () => {
    const sized = {
      price: 4.5,
      variantAxes: [{ code: "size", name: "Size", values: ["PACK OF 12", "PACK OF 6"] }],
      variantPriceByKey: { "size=PACK OF 12": 8.55, "size=PACK OF 6": 4.5 },
      variantSkuByKey: { "size=PACK OF 12": "SP-12", "size=PACK OF 6": "SP-6" },
      defaultAttributes: { size: "PACK OF 6" },
    };
    expect(resolveSelection(sized, {})).toMatchObject({ attributes: { size: "PACK OF 6" }, unitPrice: 4.5, sku: "SP-6" });
    expect(resolveSelection(sized, { size: 0 })).toMatchObject({ unitPrice: 8.55, sku: "SP-12" });
  });

  it("marks a combination with no real variant as unavailable", () => {
    expect(resolveSelection(cake, { size: 1, flavor: 1 })).toMatchObject({ available: false, sku: undefined });
  });
});

describe("productGallery", () => {
  it("uses only the product's own primary image when it has no gallery", () => {
    expect(productGallery({ image: "/media/own.jpg" })).toEqual(["/media/own.jpg"]);
    expect(productGallery({ image: "/media/own.jpg", thumbs: [] })).toEqual(["/media/own.jpg"]);
  });

  it("keeps the product's own gallery, without duplicates", () => {
    expect(productGallery({ image: "a.jpg", thumbs: ["a.jpg", "b.jpg", "a.jpg", "c.jpg"] })).toEqual(["a.jpg", "b.jpg", "c.jpg"]);
  });
});
