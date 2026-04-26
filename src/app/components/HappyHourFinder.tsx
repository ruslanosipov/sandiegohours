"use client";

import React, { useState, useMemo, useCallback, useEffect } from "react";
import { HappyHourPlace } from "@/types/happy-hour";
import { hasHappyHour, isHappyHourActive } from "@/lib/happy-hour-utils";
import { sortByDistance } from "@/lib/distance-utils";
import RestaurantList from "./RestaurantList";
import RestaurantMap from "./RestaurantMap";
import NeighborhoodBadgeBar from "./NeighborhoodBadgeBar";

interface HappyHourFinderProps {
  restaurants: HappyHourPlace[];
}

const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

export default function HappyHourFinder({ restaurants }: HappyHourFinderProps) {
  const [selectedDay, setSelectedDay] = useState<string>("Monday");
  const [selectedTime, setSelectedTime] = useState<string>("12:00");
  const [showOnlyHappyHour, setShowOnlyHappyHour] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<'name' | 'distance'>('name');
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [locationLoading, setLocationLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'list' | 'map'>('list');
  const [hasMountedMap, setHasMountedMap] = useState(false);
  const [selectedNeighborhood, setSelectedNeighborhood] = useState<string | undefined>(undefined);

  useEffect(() => {
    const now = new Date();
    setSelectedDay(DAYS[now.getDay()]);
    setSelectedTime(`${now.getHours().toString().padStart(2, "0")}:00`);
  }, []);

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
    if (typeof window !== 'undefined' && !window.isSecureContext) {
      setLocationError('Location access requires a secure connection (HTTPS or localhost).');
      return;
    }
    if (!navigator.geolocation) {
      setLocationError('Geolocation is not supported by your browser');
      return;
    }
    setLocationLoading(true);
    setLocationError(null);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setUserLocation({ lat: position.coords.latitude, lng: position.coords.longitude });
        setSortBy('distance');
        setLocationLoading(false);
      },
      (err) => {
        let message = 'Unable to retrieve your location';
        switch (err.code) {
          case err.PERMISSION_DENIED:
            message = 'Location access denied. Please enable location services in your browser settings.';
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

  const coveredNeighborhoods = useMemo(() => {
    const ids = new Set<string>();
    for (const r of restaurants) {
      if (r.neighborhood) ids.add(r.neighborhood);
    }
    return ids;
  }, [restaurants]);

  const sortedAndFilteredRestaurants = useMemo(() => {
    let filtered = restaurants.filter((restaurant) => {
      const hasHH = hasHappyHour(restaurant);
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const nameMatch = restaurant.restaurant_name.toLowerCase().includes(query);
        const addressMatch = restaurant.address.toLowerCase().includes(query);
        if (!nameMatch && !addressMatch) return false;
      }
      if (selectedNeighborhood && restaurant.neighborhood !== selectedNeighborhood) {
        return false;
      }
      if (showOnlyHappyHour && !hasHH) return false;
      if (hasHH) {
        const isActive = isHappyHourActive(restaurant.happy_hour_times, selectedDateTime);
        if (showOnlyHappyHour) return isActive;
      }
      return !showOnlyHappyHour || hasHH;
    });
    if (sortBy === 'distance' && userLocation) {
      filtered = sortByDistance(filtered, userLocation.lat, userLocation.lng);
    }
    return filtered;
  }, [restaurants, selectedDay, selectedTime, showOnlyHappyHour, searchQuery, sortBy, userLocation, selectedDateTime, selectedNeighborhood]);

  const happyHourCount = restaurants.filter((r) => hasHappyHour(r)).length;
  const activeCount = useMemo(() => {
    return sortedAndFilteredRestaurants.filter((r) =>
      isHappyHourActive(r.happy_hour_times, selectedDateTime)
    ).length;
  }, [sortedAndFilteredRestaurants, selectedDateTime]);

  const handleMarkerClick = useCallback((index: number) => {
    setActiveTab('list');
    setTimeout(() => {
      const el = document.getElementById(`restaurant-card-${index}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.classList.add('ring-2', 'ring-emerald-400', 'transition-all');
        setTimeout(() => {
          el.classList.remove('ring-2', 'ring-emerald-400', 'transition-all');
        }, 1500);
      }
    }, 150);
  }, []);

  const switchTab = useCallback((tab: 'list' | 'map') => {
    setActiveTab(tab);
    if (tab === 'map') {
      setHasMountedMap(true);
    }
  }, []);

  return (
    <div className="space-y-8">
      {/* Search & Filters */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <div className="flex flex-col md:flex-row flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[200px]">
            <label htmlFor="search-input" className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">
              Search
            </label>
            <input
              id="search-input"
              type="text"
              placeholder="Restaurant name or address..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 transition-colors"
            />
          </div>
          <div className="w-full md:w-auto">
            <label htmlFor="day-select" className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">
              Day
            </label>
            <select
              id="day-select"
              value={selectedDay}
              onChange={(e) => setSelectedDay(e.target.value)}
              className="w-full md:w-auto bg-white border border-gray-200 rounded-md px-3 py-2 text-sm text-gray-900 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 transition-colors"
            >
              {DAYS.map((day) => (
                <option key={day} value={day}>{day}</option>
              ))}
            </select>
          </div>
          <div className="w-full md:w-auto">
            <label htmlFor="time-select" className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">
              Time
            </label>
            <select
              id="time-select"
              value={selectedTime}
              onChange={(e) => setSelectedTime(e.target.value)}
              className="w-full md:w-auto bg-white border border-gray-200 rounded-md px-3 py-2 text-sm text-gray-900 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 transition-colors"
            >
              {Array.from({ length: 24 }, (_, i) => (
                <option key={i} value={`${i.toString().padStart(2, "0")}:00`}>
                  {i === 0 ? "12:00 AM" : i < 12 ? `${i}:00 AM` : i === 12 ? "12:00 PM" : `${i - 12}:00 PM`}
                </option>
              ))}
            </select>
          </div>
          <div className="pb-0.5">
            <label htmlFor="hh-only-toggle" className="flex items-center gap-2 cursor-pointer select-none">
              <input
                id="hh-only-toggle"
                type="checkbox"
                checked={showOnlyHappyHour}
                onChange={(e) => setShowOnlyHappyHour(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-600"
              />
              <span className="text-sm text-gray-700">Only show places with happy hour</span>
            </label>
          </div>
        </div>
      </div>

      {/* Neighborhood Coverage Badges */}
      <NeighborhoodBadgeBar
        coveredIds={coveredNeighborhoods}
        selectedId={selectedNeighborhood}
        onSelect={setSelectedNeighborhood}
      />

      {/* Stats, Controls & Tabs */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <p className="text-sm text-gray-500">
          Showing {sortedAndFilteredRestaurants.length} {sortedAndFilteredRestaurants.length === 1 ? "place" : "places"}
          {sortedAndFilteredRestaurants.length > 0 && (
            <> · {happyHourCount} with Happy Hour · <span className="text-emerald-600 font-bold">{activeCount} Active Now</span></>
          )}
        </p>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <label htmlFor="sort-select" className="text-sm text-gray-500">Sort by</label>
            <select
              id="sort-select"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'name' | 'distance')}
              className="text-sm bg-white border border-gray-200 rounded-md px-2 py-1 text-gray-900 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 transition-colors"
            >
              <option value="name">Name</option>
              <option value="distance" disabled={!userLocation}>Distance</option>
            </select>
          </div>

          {!userLocation ? (
            <button
              onClick={handleGetLocation}
              disabled={locationLoading}
              className="text-sm bg-emerald-600 text-white px-3 py-1.5 rounded-md hover:bg-emerald-700 disabled:opacity-50 transition-colors"
            >
              {locationLoading ? "Getting location..." : "Use my location"}
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-sm text-emerald-600 font-medium">Location active</span>
              <button onClick={handleClearLocation} className="text-sm text-gray-400 hover:text-gray-600">Clear</button>
            </div>
          )}

          {/* View Tabs */}
          <div className="flex rounded-md border border-gray-200 overflow-hidden">
            <button
              onClick={() => switchTab('list')}
              className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                activeTab === 'list'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
              aria-pressed={activeTab === 'list'}
            >
              List
            </button>
            <button
              onClick={() => switchTab('map')}
              className={`px-3 py-1.5 text-sm font-medium transition-colors border-l border-gray-200 ${
                activeTab === 'map'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
              aria-pressed={activeTab === 'map'}
            >
              Map
            </button>
          </div>
        </div>
      </div>

      {locationError && (
        <div className="text-sm text-red-600 bg-red-50 p-3 rounded-md">{locationError}</div>
      )}

      {/* Content */}
      <div data-testid="list-view" className={activeTab === 'list' ? 'block' : 'hidden'}>
        <RestaurantList
          restaurants={sortedAndFilteredRestaurants}
          selectedDateTime={selectedDateTime}
          selectedDay={selectedDay}
        />
      </div>

      {(activeTab === 'map' || hasMountedMap) && (
        <div data-testid="map-view" className={activeTab === 'map' ? 'block' : 'hidden'}>
          <RestaurantMap
            restaurants={sortedAndFilteredRestaurants}
            selectedDateTime={selectedDateTime}
            userLocation={userLocation}
            onMarkerClick={handleMarkerClick}
            isVisible={activeTab === 'map'}
          />
        </div>
      )}
    </div>
  );
}
