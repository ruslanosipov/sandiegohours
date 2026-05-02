import { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getRestaurants } from "@/lib/data-loader";
import {
  hasHappyHour,
  getHappyHourStatus,
  getHappyHourStatusLabel,
  normalizeHappyHourTimes,
  HappyHourStatus,
  formatPriceLevel,
} from "@/lib/happy-hour-utils";
import {
  simplifyAddress,
  formatDate,
  formatSource,
  getTodayName,
} from "./helpers";

interface Props {
  params: Promise<{ placeId: string }>;
}

export async function generateStaticParams(): Promise<{ placeId: string }[]> {
  const restaurants = await getRestaurants();
  return restaurants
    .filter((r) => r.place_id && r.place_id.trim().length > 0)
    .map((r) => ({ placeId: r.place_id! }));
}

export const dynamicParams = false;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { placeId } = await params;
  const restaurants = await getRestaurants();
  const restaurant = restaurants.find((r) => r.place_id === placeId);

  if (!restaurant) {
    return {
      title: "Not Found — San Diego Happy Hours",
    };
  }

  const hasHH = hasHappyHour(restaurant);
  const description = restaurant.generative_summary
    ? `${restaurant.generative_summary} ${hasHH ? "Check out their happy hour deals." : ""}`
    : `Find happy hour info, hours, and deals for ${restaurant.restaurant_name} in San Diego.`;

  return {
    title: `${restaurant.restaurant_name} — San Diego Happy Hours`,
    description,
  };
}

function simplifyAddress(address: string): string {
  if (!address) return "";
  return address
    .replace(/,\s*San Diego,?\s*(CA)?\s*\d{5}(-\d{4})?/i, "")
    .replace(/,\s*CA\s*$/i, "")
    .trim();
}

function formatDate(dateStr: string): string {
  if (!dateStr) return "";
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

function formatSource(source: string): string {
  if (!source) return "Unknown";
  if (source.includes("google") || source.includes("Google")) return "Google Maps";
  if (source.includes("website") || source.includes("Website") || source.includes("AI"))
    return "Website";
  if (source === "Manual") return "Manual";
  return source;
}

function getTodayName(): string {
  return new Date().toLocaleDateString("en-US", { weekday: "long" });
}

export default async function PlacePage({ params }: Props) {
  const { placeId } = await params;
  const restaurants = await getRestaurants();
  const restaurant = restaurants.find((r) => r.place_id === placeId);

  if (!restaurant) {
    notFound();
  }

  const hasHH = hasHappyHour(restaurant);
  const now = new Date();
  const status = getHappyHourStatus(restaurant.happy_hour_times, now);
  const statusLabel = getHappyHourStatusLabel(status);
  const isActive = status === HappyHourStatus.ACTIVE;
  const todayName = getTodayName();

  return (
    <main className="min-h-screen bg-white">
      {/* Banner */}
      <div className="bg-white py-6 md:py-10">
        <div className="max-w-6xl mx-auto px-4 flex justify-center">
          <Link href="/">
            <img
              src="/banner.png"
              alt="North Park Happy Hour"
              className="w-full max-w-2xl h-auto"
            />
          </Link>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 pb-12">
        {/* Back link */}
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-emerald-600 hover:underline mb-6"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          All happy hours
        </Link>

        {/* Card */}
        <div
          className={`bg-white border border-gray-200 rounded-lg overflow-hidden ${
            isActive ? "ring-1 ring-emerald-600" : ""
          }`}
        >
          <div className="p-6 md:p-8">
            {/* Name + Status */}
            <div className="flex items-start justify-between gap-3 mb-3">
              <h1 className="font-montserrat text-2xl md:text-3xl font-bold text-gray-900 leading-tight">
                {restaurant.restaurant_name}
              </h1>
              {hasHH && statusLabel.text && (
                statusLabel.boxClass ? (
                  <span
                    className={`text-xs whitespace-nowrap mt-0.5 px-2 py-1 rounded-md border ${statusLabel.boxClass} ${statusLabel.colorClass}`}
                  >
                    {statusLabel.text}
                  </span>
                ) : (
                  <span className={`text-xs whitespace-nowrap mt-1 ${statusLabel.colorClass}`}>
                    {statusLabel.text}
                  </span>
                )
              )}
              {!hasHH && (
                <span className="text-xs text-gray-400 mt-1 whitespace-nowrap">No Happy Hour</span>
              )}
            </div>

            {/* Generative Summary */}
            {restaurant.generative_summary && (
              <p className="text-base text-gray-600 italic mb-4">
                {restaurant.generative_summary}
              </p>
            )}

            {/* Meta */}
            <div className="flex items-center flex-wrap gap-x-1 gap-y-0.5 text-sm text-gray-500 mb-6">
              <span className="font-medium text-gray-700">{restaurant.rating}</span>
              <span className="text-gray-400">·</span>
              <span>{restaurant.review_count} reviews</span>
              {restaurant.price_level && (
                <>
                  <span className="text-gray-400">·</span>
                  <span>{formatPriceLevel(restaurant.price_level)}</span>
                </>
              )}
            </div>

            {/* Happy Hours */}
            {hasHH && (
              <div className="mb-6">
                <h2 className="text-sm font-medium text-gray-700 uppercase tracking-wide mb-3">
                  Happy Hour
                </h2>
                <div className="space-y-1 text-sm text-gray-600">
                  {normalizeHappyHourTimes(restaurant.happy_hour_times)
                    .split(" | ")
                    .map((line, i) => {
                      const dayName = line.split(":")[0].trim();
                      const isToday = dayName.toLowerCase() === todayName.toLowerCase();
                      return (
                        <span
                          key={i}
                          className={`block leading-snug ${
                            isToday ? "font-medium text-gray-900" : ""
                          }`}
                        >
                          {line}
                        </span>
                      );
                    })}
                </div>
              </div>
            )}

            {/* Deals */}
            {restaurant.menu_summary && (
              <div className="bg-emerald-50 border border-emerald-100 rounded-md p-4 mb-6">
                <h2 className="text-xs font-semibold text-emerald-800 uppercase tracking-wide mb-1">
                  Happy Hour Deals
                </h2>
                <p className="text-sm text-emerald-900 font-medium">
                  {restaurant.menu_summary}
                </p>
              </div>
            )}

            {/* Address, Phone, Website */}
            <div className="border-t border-gray-100 pt-6 space-y-3">
              {restaurant.google_maps_url ? (
                <a
                  href={restaurant.google_maps_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-base text-gray-600 hover:text-emerald-600 hover:underline flex items-start gap-2 group"
                >
                  <svg
                    className="w-5 h-5 mt-0.5 text-gray-400 group-hover:text-emerald-500 shrink-0"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
                    />
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                  </svg>
                  <span>{simplifyAddress(restaurant.address)}</span>
                </a>
              ) : (
                <p className="text-base text-gray-600">{simplifyAddress(restaurant.address)}</p>
              )}

              {restaurant.phone_number && (
                <a
                  href={`tel:${restaurant.phone_number}`}
                  className="text-base text-gray-600 hover:text-emerald-600 underline decoration-gray-300 hover:decoration-emerald-600 flex items-center gap-2"
                >
                  <svg
                    className="w-5 h-5 text-gray-400 shrink-0"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
                    />
                  </svg>
                  {restaurant.phone_number}
                </a>
              )}

              {restaurant.website_url && (
                <a
                  href={restaurant.website_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-base text-gray-600 hover:text-emerald-600 underline decoration-gray-300 hover:decoration-emerald-600 flex items-center gap-2"
                >
                  <svg
                    className="w-5 h-5 text-gray-400 shrink-0"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9"
                    />
                  </svg>
                  Visit website
                </a>
              )}
            </div>

            {/* Source + Updated */}
            <div className="text-xs text-gray-400 mt-6">
              Source: {formatSource(restaurant.source)}
              {formatDate(restaurant.freshness_date) &&
                ` · Updated ${formatDate(restaurant.freshness_date)}`}
            </div>

            {/* Regular Hours */}
            {restaurant.regular_hours && (
              <div className="mt-6 pt-6 border-t border-gray-100">
                <h2 className="text-sm font-medium text-gray-700 uppercase tracking-wide mb-3">
                  Regular Hours
                </h2>
                <div className="space-y-1 text-sm text-gray-600">
                  {restaurant.regular_hours.split(" | ").map((line, i) => (
                    <span key={i} className="block leading-snug">
                      {line}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
