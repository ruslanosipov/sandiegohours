"use client";

import React, { useState } from "react";
import Link from "next/link";
import { HappyHourPlace } from "@/types/happy-hour";
import { hasHappyHour, getHappyHourStatus, getHappyHourStatusLabel, isHappyHourActive, HappyHourStatus, normalizeHappyHourTimes, formatPriceLevel } from "@/lib/happy-hour-utils";
import { formatDistance } from "@/lib/distance-utils";

interface RestaurantListProps {
  restaurants: HappyHourPlace[];
  selectedDateTime: Date;
  selectedDay: string;
}

function formatSource(source: string): string {
  if (!source) return "Unknown";
  if (source.includes("google") || source.includes("Google")) return "Google Maps";
  if (source.includes("website") || source.includes("Website") || source.includes("AI")) return "Website";
  if (source === "Manual") return "Manual";
  return source;
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
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return dateStr;
  }
}

export default function RestaurantList({ restaurants, selectedDateTime, selectedDay }: RestaurantListProps) {
  const [expandedHappyHours, setExpandedHappyHours] = useState<Set<string>>(new Set());

  if (restaurants.length === 0) {
    return (
      <div className="text-center py-16 text-gray-500">
        <p className="text-lg text-gray-900">No places found.</p>
        <p className="mt-2 text-gray-500">Try changing your search or filters</p>
      </div>
    );
  }

  return (
    <div data-testid="restaurant-list" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {restaurants.map((restaurant, index) => {
        const hasHH = hasHappyHour(restaurant);
        const status = getHappyHourStatus(restaurant.happy_hour_times, selectedDateTime);
        const statusLabel = getHappyHourStatusLabel(status);
        const isActive = status === HappyHourStatus.ACTIVE;
        const source = formatSource(restaurant.source);
        const updatedDate = formatDate(restaurant.freshness_date);

        return (
          <div
            key={index}
            id={`restaurant-card-${index}`}
            className={`bg-white border border-gray-200 rounded-lg overflow-hidden flex flex-col ${isActive ? "ring-1 ring-emerald-600" : ""}`}
          >
            <div className="p-6 flex flex-col flex-1">
              {/* Header: Name + Status */}
              <div className="flex items-start justify-between gap-3 mb-3">
                {restaurant.place_id ? (
                  <Link href={`/places/${restaurant.place_id}`} className="group">
                    <h3 className="font-montserrat text-xl font-bold text-gray-900 leading-tight group-hover:text-emerald-700 transition-colors">
                      {restaurant.restaurant_name}
                    </h3>
                  </Link>
                ) : (
                  <h3 className="font-montserrat text-xl font-bold text-gray-900 leading-tight">
                    {restaurant.restaurant_name}
                  </h3>
                )}
                {hasHH && statusLabel.text && (
                  statusLabel.boxClass ? (
                    <span className={`text-xs whitespace-nowrap mt-0.5 px-2 py-1 rounded-md border ${statusLabel.boxClass} ${statusLabel.colorClass}`}>
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
                <p className="text-sm text-gray-500 italic mb-3">{restaurant.generative_summary}</p>
              )}

              {/* Meta line */}
              <div className="flex items-center flex-wrap gap-x-1 gap-y-0.5 text-sm text-gray-500 mb-4">
                <span className="font-medium text-gray-700">{restaurant.rating}</span>
                <span className="text-gray-400">·</span>
                <span>{restaurant.review_count} reviews</span>
                {restaurant.price_level && (
                  <>
                    <span className="text-gray-400">·</span>
                    <span>{formatPriceLevel(restaurant.price_level)}</span>
                  </>
                )}
                {restaurant.distance !== undefined && restaurant.distance !== Infinity && (
                  <>
                    <span className="text-gray-400">·</span>
                    <span className="text-emerald-600 font-medium">{formatDistance(restaurant.distance)}</span>
                  </>
                )}
              </div>

              {/* Happy Hour Accordion */}
              {hasHH && (
                <div className="mb-4">
                  <button
                    type="button"
                    onClick={() => {
                      const newSet = new Set(expandedHappyHours);
                      if (newSet.has(restaurant.restaurant_name)) {
                        newSet.delete(restaurant.restaurant_name);
                      } else {
                        newSet.add(restaurant.restaurant_name);
                      }
                      setExpandedHappyHours(newSet);
                    }}
                    className="w-full text-left py-2 border-b border-gray-100 flex items-start justify-between text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors"
                  >
                    <span className="flex flex-col">
                      <span>Happy Hour</span>
                      {!expandedHappyHours.has(restaurant.restaurant_name) && (
                        <span className="text-gray-400 font-normal text-xs mt-0.5">
                          {(() => {
                            const todayLine = normalizeHappyHourTimes(restaurant.happy_hour_times)
                              .split(" | ")
                              .find(line => line.toLowerCase().startsWith(selectedDay.toLowerCase()));
                            return todayLine ? todayLine : '';
                          })()}
                        </span>
                      )}
                    </span>
                    <span className="text-gray-400 text-lg leading-none mt-0.5">
                      {expandedHappyHours.has(restaurant.restaurant_name) ? '−' : '+'}
                    </span>
                  </button>
                  {expandedHappyHours.has(restaurant.restaurant_name) && (
                    <div className="py-3 space-y-1 text-sm text-gray-600">
                      {normalizeHappyHourTimes(restaurant.happy_hour_times).split(" | ").map((line, i) => {
                        const dayName = line.split(':')[0].trim();
                        const isToday = dayName.toLowerCase() === selectedDay.toLowerCase();
                        return (
                          <span
                            key={i}
                            className={`block leading-snug ${isToday ? 'font-medium text-gray-900' : ''}`}
                          >
                            {line}
                          </span>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Deals */}
              {restaurant.menu_summary && (
                <div className="bg-emerald-50 border border-emerald-100 rounded-md p-3 mb-4">
                  <h4 className="text-xs font-semibold text-emerald-800 uppercase tracking-wide mb-1">
                    Happy Hour Deals
                  </h4>
                  <p className="text-sm text-emerald-900 font-medium">{restaurant.menu_summary}</p>
                </div>
              )}

              {/* Footer: Address, Phone, Website, Source, Regular Hours */}
              <div className="mt-auto pt-4 border-t border-gray-100">
                {/* Address */}
                {restaurant.google_maps_url ? (
                  <a
                    href={restaurant.google_maps_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-gray-500 hover:text-emerald-600 hover:underline mb-2 flex items-start gap-1.5 group"
                  >
                    <svg className="w-4 h-4 mt-0.5 text-gray-400 group-hover:text-emerald-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    <span>{simplifyAddress(restaurant.address)}</span>
                  </a>
                ) : (
                  <p className="text-sm text-gray-500 mb-2">{simplifyAddress(restaurant.address)}</p>
                )}

                {/* Contact Links */}
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm mb-3">
                  {restaurant.phone_number && (
                    <a href={`tel:${restaurant.phone_number}`} className="text-gray-500 hover:text-emerald-600 underline decoration-gray-300 hover:decoration-emerald-600 transition-colors">
                      {restaurant.phone_number}
                    </a>
                  )}
                  {restaurant.website_url && (
                    <a href={restaurant.website_url} target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-emerald-600 underline decoration-gray-300 hover:decoration-emerald-600 transition-colors">
                      Website
                    </a>
                  )}
                </div>

                {/* Source */}
                <div className="text-xs text-gray-400 mb-3">
                  Source: {source}
                  {updatedDate && ` · Updated ${updatedDate}`}
                </div>

                {/* Regular Hours */}
                {restaurant.regular_hours && (
                  <div>
                    <button
                      type="button"
                      onClick={() => {
                        const newSet = new Set(expandedHappyHours);
                        const key = `${restaurant.restaurant_name}__regular`;
                        if (newSet.has(key)) {
                          newSet.delete(key);
                        } else {
                          newSet.add(key);
                        }
                        setExpandedHappyHours(newSet);
                      }}
                      className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1 transition-colors"
                    >
                      <span>Regular Hours</span>
                      <span>{expandedHappyHours.has(`${restaurant.restaurant_name}__regular`) ? '−' : '+'}</span>
                    </button>
                    {expandedHappyHours.has(`${restaurant.restaurant_name}__regular`) && (
                      <div className="mt-2 text-xs text-gray-500 space-y-0.5">
                        {restaurant.regular_hours.split(" | ").map((line, i) => (
                          <span key={i} className="block">{line}</span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
