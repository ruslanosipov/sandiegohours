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
  const [showHasHappyHour, setShowHasHappyHour] = useState(true);
  const [showHappyHourNow, setShowHappyHourNow] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<'name' | 'distance'>('name');
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [locationLoading, setLocationLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'list' | 'map'>('map');
  const [hasMountedMap, setHasMountedMap] = useState(true);
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
    const counts = new Map<string, number>();
    for (const r of restaurants) {
      if (r.neighborhood) {
        counts.set(r.neighborhood, (counts.get(r.neighborhood) ?? 0) + 1);
      }
    }
    const ids = new Set<string>();
    for (const [id, count] of counts) {
      if (count >= 50) ids.add(id);
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
      const isActive = hasHH && isHappyHourActive(restaurant.happy_hour_times, selectedDateTime);
      if (showHasHappyHour && !hasHH) return false;
      if (showHappyHourNow && !isActive) return false;
      return true;
    });
    if (sortBy === 'distance' && userLocation) {
      filtered = sortByDistance(filtered, userLocation.lat, userLocation.lng);
    }
    return filtered;
  }, [restaurants, selectedDay, selectedTime, showHasHappyHour, showHappyHourNow, searchQuery, sortBy, userLocation, selectedDateTime, selectedNeighborhood]);

  const happyHourCount = restaurants.filter((r) => hasHappyHour(r)).length;
  const activeCount = useMemo(() => {
    return sortedAndFilteredRestaurants.filter((r) =>
      isHappyHourActive(r.happy_hour_times, selectedDateTime)
    ).length;
  }, [sortedAndFilteredRestaurants, selectedDateTime]);

  // Shared helper: update URL and scroll to card
  const handlePlaceClick = useCallback((index: number) => {
    const restaurant = sortedAndFilteredRestaurants[index];
    if (restaurant?.place_id) {
      const url = new URL(window.location.href);
      url.searchParams.set('place', restaurant.place_id);
      window.history.pushState({}, '', url);
    }
    setActiveTab('list');
    setTimeout(() => {
      const el = document.getElementById(`restaurant-card-${index}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.classList.add('ring-2', 'ring-emerald-400', 'transition-all');
        setTimeout(() => {
          el.classList.remove('ring-2', 'ring-emerald-400', 'transition-all');
        }, 2500);
      }
    }, 200);
  }, [sortedAndFilteredRestaurants]);

  const handleMarkerClick = useCallback((index: number) => {
    const restaurant = sortedAndFilteredRestaurants[index];
    if (restaurant?.place_id) {
      const url = new URL(window.location.href);
      url.searchParams.set('place', restaurant.place_id);
      window.history.pushState({}, '', url);
    }
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
  }, [sortedAndFilteredRestaurants]);

  // Scroll to card when ?place=xxx is in URL (initial load, back/forward nav, or manual URL change)
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const scrollToPlace = () => {
      const params = new URLSearchParams(window.location.search);
      const placeId = params.get('place');
      if (!placeId) return;

      const index = sortedAndFilteredRestaurants.findIndex(
        (r) => r.place_id === placeId
      );
      if (index === -1) return;

      setActiveTab('list');
      const timer = setTimeout(() => {
        const el = document.getElementById(`restaurant-card-${index}`);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          el.classList.add('ring-2', 'ring-emerald-400', 'transition-all');
          setTimeout(() => {
            el.classList.remove('ring-2', 'ring-emerald-400', 'transition-all');
          }, 2500);
        }
      }, 250);
      return () => clearTimeout(timer);
    };

    const cleanup = scrollToPlace();
    const handlePopState = () => scrollToPlace();
    window.addEventListener('popstate', handlePopState);

    return () => {
      window.removeEventListener('popstate', handlePopState);
      if (cleanup) cleanup;
    };
  }, [sortedAndFilteredRestaurants]);

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
          <div className="pb-0.5 flex items-center gap-4">
            <label htmlFor="hh-has-toggle" className="flex items-center gap-2 cursor-pointer select-none">
              <input
                id="hh-has-toggle"
                type="checkbox"
                checked={showHasHappyHour}
                onChange={(e) => setShowHasHappyHour(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-600"
              />
              <span className="text-sm text-gray-700">Has happy hour</span>
            </label>
            <label htmlFor="hh-now-toggle" className="flex items-center gap-2 cursor-pointer select-none">
              <input
                id="hh-now-toggle"
                type="checkbox"
                checked={showHappyHourNow}
                onChange={(e) => setShowHappyHourNow(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-600"
              />
              <span className="text-sm text-gray-700">Happy hour now</span>
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
            <> &middot; {happyHourCount} with Happy Hour &middot; <span className="text-emerald-600 font-bold">{activeCount} Active Now</span></>
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
              className="inline-flex items-center gap-1.5 text-sm bg-emerald-600 text-white px-3 py-1.5 rounded-md hover:bg-emerald-700 disabled:opacity-50 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              {locationLoading ? "Getting location..." : "Use my location"}
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 text-sm text-emerald-600 font-medium">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Location active
              </span>
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
          onPlaceClick={handlePlaceClick}
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
