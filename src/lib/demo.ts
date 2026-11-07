/** Stage A build flag. The backend decides independently and marks each order is_demo, so a
 * demo order is labelled even if a frontend is ever built with the wrong flag. */
export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === "true";
