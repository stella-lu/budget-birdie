export function formatCents(cents: number): string {
  const dollars = cents / 100;
  return dollars.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

export function dollarsToCents(input: string): number {
  const n = Number.parseFloat(input);
  if (Number.isNaN(n)) return 0;
  return Math.round(n * 100);
}

export function currentMonthStr(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}
