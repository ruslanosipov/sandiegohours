export function simplifyAddress(address: string): string {
  if (!address) return "";
  return address
    .replace(/,\s*San Diego,?\s*(CA)?\s*\d{5}(-\d{4})?/i, "")
    .replace(/,\s*CA\s*$/i, "")
    .trim();
}

export function formatDate(dateStr: string): string {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return dateStr;
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function formatSource(source: string): string {
  if (!source) return "Unknown";
  if (source.includes("google") || source.includes("Google")) return "Google Maps";
  if (source.includes("website") || source.includes("Website") || source.includes("AI"))
    return "Website";
  if (source === "Manual") return "Manual";
  return source;
}

export function getTodayName(): string {
  return new Date().toLocaleDateString("en-US", { weekday: "long" });
}
