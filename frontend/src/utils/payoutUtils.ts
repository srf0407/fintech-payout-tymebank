// Supported payout currencies for the payout form and related UI
export const payoutCurrencies = [
  { code: "USD", label: "US Dollar" },
  { code: "ZAR", label: "South African Rand" },
  { code: "EUR", label: "Euro" },
];
export function statusColor(status: string): "success" | "warning" | "info" | "error" | "default" {
  switch (status) {
    case "completed":
      return "success";
    case "pending":
      return "warning";
    case "processing":
      return "info";
    case "failed":
      return "error";
    case "cancelled":
      return "default";
    default:
      return "default";
  }
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString();
}
