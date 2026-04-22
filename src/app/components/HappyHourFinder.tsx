"use client";

import React, { useState, useMemo, useCallback } from "react";
import { HappyHourPlace } from "@/types/happy-hour";
import { parseHappyHourTimes, hasHappyHour, formatPriceLevel, getHappyHourStatus, getHappyHourStatusLabel, isHappyHourActive, HappyHourStatus, normalizeHappyHourTimes } from "@/lib/happy-hour-utils";
import { sortByDistance, formatDistance } from "@/lib/distance-utils";

interface HappyHourFinderProps {
  restaurants: HappyHourPlace[];
}

const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

function formatSource(source: string): string {
  if (!source) return "Unknown";
  if (source.includes("google_maps_api")) return "Google Maps API";
  if (source.includes("website")) return "Website";
  if (source === "Manual") return "Manual";
  return source;
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

export default function HappyHourFinder({ restaurants }: HappyHourFinderProps) {
  const now = new Date();
  const currentDay = DAYS[now.getDay()];
  const currentHour = now.getHours();
  const currentTime = `${currentHour.toString().padStart(2, "0")}:00`;

  const [selectedDay, setSelectedDay] = useState<string>(currentDay);
  const [selectedTime, setSelectedTime] = useState<string>(currentTime);
  const [showOnlyHappyHour, setShowOnlyHappyHour] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<'name' | 'distance'>('name');
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [locationLoading, setLocationLoading] = useState(false);
  const [expandedHappyHours, setExpandedHappyHours] = useState<Set<string>>(new Set());

  // Create a date object from selected day and time for accurate filtering
  const selectedDateTime = useMemo(() => {
    const date = new Date();
    const dayIndex = DAYS.indexOf(selectedDay);
    const currentDayIndex = date.getDay();
    const dayDiff = dayIndex - currentDayIndex;
    date.setDate(date.getDate() + dayDiff);
    const [hours, minutes] = selectedTime.split(':').map(Number);
    date.setHours(hours, minutes, 0, 0);
    return date;
  }, [selectedDay, selectedTime]);

  const handleGetLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setLocationError('Geolocation is not supported by your browser');
      return;
    }

    setLocationLoading(true);
    setLocationError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setUserLocation({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        });
        setSortBy('distance');
        setLocationLoading(false);
      },
      (err) => {
        let message = 'Unable to retrieve your location';
        switch (err.code) {
          case err.PERMISSION_DENIED:
            message = 'Location access denied';
            break;
          case err.POSITION_UNAVAILABLE:
            message = 'Location information unavailable';
            break;
          case err.TIMEOUT:
            message = 'Location request timed out';
            break;
        }
        setLocationError(message);
        setLocationLoading(false);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  }, []);

  const handleClearLocation = useCallback(() => {
    setUserLocation(null);
    setSortBy('name');
    setLocationError(null);
  }, []);

  const sortedAndFilteredRestaurants = useMemo(() => {
    let filtered = restaurants.filter((restaurant) => {
      const hasHH = hasHappyHour(restaurant);

      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const nameMatch = restaurant.restaurant_name.toLowerCase().includes(query);
        const addressMatch = restaurant.address.toLowerCase().includes(query);
        if (!nameMatch && !addressMatch) return false;
      }

      if (showOnlyHappyHour && !hasHH) {
        return false;
      }

      // Use actual time-based filtering with selectedDateTime
      if (!selectedDay || !selectedTime) return true;

      if (hasHH) {
        const isActive = isHappyHourActive(restaurant.happy_hour_times, selectedDateTime);
        if (showOnlyHappyHour) return isActive;
        return true;
      }

      return !showOnlyHappyHour;
    });

    if (sortBy === 'distance' && userLocation) {
      filtered = sortByDistance(filtered, userLocation.lat, userLocation.lng);
    }

    return filtered;
  }, [restaurants, selectedDay, selectedTime, showOnlyHappyHour, searchQuery, sortBy, userLocation, selectedDateTime]);

  const happyHourCount = restaurants.filter((r) => hasHappyHour(r)).length;
  
  const activeCount = useMemo(() => {
    return sortedAndFilteredRestaurants.filter((r) => 
      isHappyHourActive(r.happy_hour_times, selectedDateTime)
    ).length;
  }, [sortedAndFilteredRestaurants, selectedDateTime]);

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4 text-center border-2 border-brand-teal">
          <div className="text-3xl font-bold text-brand-teal">{restaurants.length}</div>
          <div className="text-gray-600 text-sm">Total Places</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 text-center border-2 border-brand-yellow">
          <div className="text-3xl font-bold text-brand-orange">{happyHourCount}</div>
          <div className="text-gray-600 text-sm">With Happy Hour</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 text-center border-2 border-brand-orange">
          <div className="text-3xl font-bold text-brand-orange">{activeCount}</div>
          <div className="text-gray-600 text-sm">Active Now</div>
        </div>
      </div>

      {/* Search */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Search</h2>
        <input
          type="text"
          placeholder="Search by restaurant name or address..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full border border-gray-300 rounded-md px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
        />
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Filter by Time</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label htmlFor="day-select" className="block text-sm font-medium text-gray-700 mb-1">Day</label>
            <select
              id="day-select"
              value={selectedDay}
              onChange={(e) => setSelectedDay(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              {DAYS.map((day) => (
                <option key={day} value={day}>{day}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="time-select" className="block text-sm font-medium text-gray-700 mb-1">Time</label>
            <select
              id="time-select"
              value={selectedTime}
              onChange={(e) => setSelectedTime(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              {Array.from({ length: 24 }, (_, i) => (
                <option key={i} value={`${i.toString().padStart(2, "0")}:00`}>
                  {i === 0 ? "12:00 AM" : i < 12 ? `${i}:00 AM` : i === 12 ? "12:00 PM" : `${i - 12}:00 PM`}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <label htmlFor="hh-only-toggle" className="flex items-center space-x-2 cursor-pointer">
              <input
                id="hh-only-toggle"
                type="checkbox"
                checked={showOnlyHappyHour}
                onChange={(e) => setShowOnlyHappyHour(e.target.checked)}
                className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
              />
              <span className="text-sm text-gray-700">Only show places with happy hour</span>
            </label>
          </div>
        </div>
      </div>

      {/* Results count and location */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="text-sm text-gray-600">
          Showing {sortedAndFilteredRestaurants.length} {sortedAndFilteredRestaurants.length === 1 ? "place" : "places"}
          {searchQuery && ` for "${searchQuery}"`}
        </div>
        
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <label htmlFor="sort-select" className="text-sm text-gray-600">Sort by:</label>
            <select
              id="sort-select"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'name' | 'distance')}
              className="text-sm border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="name">Name</option>
              <option value="distance" disabled={!userLocation}>Distance</option>
            </select>
          </div>

          {!userLocation ? (
            <button
              onClick={handleGetLocation}
              disabled={locationLoading}
              className="text-sm bg-purple-100 text-purple-700 px-3 py-1 rounded-md hover:bg-purple-200 disabled:opacity-50 flex items-center gap-1"
            >
              {locationLoading ? <><span className="animate-spin">⌛</span> Getting location...</> : <>📍 Use my location</>}
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-sm text-green-600">📍 Location active</span>
              <button onClick={handleClearLocation} className="text-sm text-gray-500 hover:text-gray-700">✕</button>
            </div>
          )}
        </div>
      </div>
      
      {locationError && (
        <div className="text-sm text-red-600 bg-red-50 p-2 rounded-md">{locationError}</div>
      )}

      {/* Restaurant Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {sortedAndFilteredRestaurants.map((restaurant, index) => {
          const hasHH = hasHappyHour(restaurant);
          const status = getHappyHourStatus(restaurant.happy_hour_times, selectedDateTime);
          const statusLabel = getHappyHourStatusLabel(status);
          const isActive = status === HappyHourStatus.ACTIVE;
          const source = formatSource(restaurant.source);
          const updatedDate = formatDate(restaurant.freshness_date);

          return (
            <div
              key={index}
              className={`bg-white rounded-lg shadow-md overflow-hidden transition-all hover:shadow-lg ${isActive ? "ring-2 ring-brand-yellow" : ""}`}
            >
              <div className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-bold text-lg text-gray-900 leading-tight">{restaurant.restaurant_name}</h3>
                  {hasHH && (
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${statusLabel.colorClass}`}>
                      {statusLabel.text}
                    </span>
                  )}
                  {!hasHH && (
                    <span className="text-xs px-2 py-1 rounded-full font-medium bg-red-100 text-red-700">No Happy Hour</span>
                  )}
                </div>

                <div className="flex items-center text-sm text-gray-600 mb-2">
                  <span className="font-medium">{restaurant.rating}★</span>
                  <span className="mx-1">·</span>
                  <span>{restaurant.review_count} reviews</span>
                  {restaurant.price_level && (
                    <><span className="mx-1">·</span><span className="text-gray-500">{formatPriceLevel(restaurant.price_level)}</span></>
                  )}
                  {restaurant.distance !== undefined && restaurant.distance !== Infinity && (
                    <><span className="mx-1">·</span><span className="text-green-600 font-medium">{formatDistance(restaurant.distance)}</span></>
                  )}
                </div>

                <p className="text-sm text-gray-700 mb-3">{restaurant.address}</p>

                {hasHH && (
                  <details 
                    className="text-sm mb-3"
                    open={expandedHappyHours.has(restaurant.restaurant_name)}
                    onToggle={(e) => {
                      const newSet = new Set(expandedHappyHours);
                      if (e.currentTarget.open) {
                        newSet.add(restaurant.restaurant_name);
                      } else {
                        newSet.delete(restaurant.restaurant_name);
                      }
                      setExpandedHappyHours(newSet);
                    }}
                  >
                    <summary className={`cursor-pointer font-medium p-2 rounded-md ${isActive ? "bg-green-50 text-green-800 hover:bg-green-100" : "bg-gray-50 text-gray-700 hover:bg-gray-100"}`}>
                      Happy Hour
                      {!expandedHappyHours.has(restaurant.restaurant_name) && (
                        <span className="ml-2 text-gray-500 font-normal">
                          {(() => {
                            const todayLine = normalizeHappyHourTimes(restaurant.happy_hour_times)
                              .split(" | ")
                              .find(line => line.toLowerCase().startsWith(selectedDay.toLowerCase()));
                            return todayLine ? `(${todayLine})` : '';
                          })()}
                        </span>
                      )}
                    </summary>
                    <div className={`mt-2 p-3 rounded-md ${isActive ? "bg-green-50 text-green-800" : "bg-gray-50 text-gray-800"}`}>
                      {normalizeHappyHourTimes(restaurant.happy_hour_times).split(" | ").map((line, i) => {
                        const dayName = line.split(':')[0].trim();
                        const isToday = dayName.toLowerCase() === selectedDay.toLowerCase();
                        return (
                          <span 
                            key={i} 
                            className={`block leading-snug ${isToday ? 'font-bold text-gray-900' : ''}`}
                          >
                            {line}
                          </span>
                        );
                      })}
                    </div>
                  </details>
                )}

                {/* AI Menu Summary */}
                {(restaurant.menu_summary || restaurant.cheapest_drink || restaurant.cheapest_food) && (
                  <div className="bg-purple-50 p-3 rounded-md mb-3">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-purple-600 text-lg">🍽️</span>
                      <span className="font-medium text-purple-900">Happy Hour Deals</span>
                    </div>
                    {restaurant.menu_summary && (
                      <p className="text-sm text-purple-800 mb-2">{restaurant.menu_summary}</p>
                    )}
                    <div className="flex flex-wrap gap-3 text-sm">
                      {restaurant.cheapest_drink && (
                        <span className="bg-white px-2 py-1 rounded text-purple-700">
                          🍺 {restaurant.cheapest_drink}
                        </span>
                      )}
                      {restaurant.cheapest_food && (
                        <span className="bg-white px-2 py-1 rounded text-purple-700">
                          🍔 {restaurant.cheapest_food}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                <div className="flex flex-wrap gap-2 text-sm">
                  {restaurant.phone_number && <a href={`tel:${restaurant.phone_number}`} className="text-blue-600 hover:text-blue-800 hover:underline">{restaurant.phone_number}</a>}
                  {restaurant.phone_number && restaurant.website_url && <span className="text-gray-400">·</span>}
                  {restaurant.website_url && <a href={restaurant.website_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 hover:underline">Website</a>}
                </div>

                <div className="mt-3 pt-3 border-t border-gray-100 text-xs text-gray-500 flex justify-between">
                  <span>Source: {source}</span>
                  {updatedDate && <span>Updated: {updatedDate}</span>}
                </div>

                {restaurant.regular_hours && (
                  <details className="mt-3 text-sm">
                    <summary className="text-gray-500 cursor-pointer hover:text-gray-700">Regular Hours</summary>
                    <p className="mt-2 text-gray-600 pl-2 border-l-2 border-gray-200">
                      {restaurant.regular_hours.split(" | ").map((line, i) => <span key={i} className="block">{line}</span>)}
                    </p>
                  </details>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {sortedAndFilteredRestaurants.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg">No places found.</p>
          <p className="mt-2">Try changing your search or filters</p>
        </div>
      )}
    </div>
  );
}
