"use client";

import React, { useEffect, useRef } from "react";
import { HappyHourPlace } from "@/types/happy-hour";
import { hasHappyHour, isHappyHourActive } from "@/lib/happy-hour-utils";

interface RestaurantMapProps {
  restaurants: HappyHourPlace[];
  selectedDateTime: Date;
  userLocation: { lat: number; lng: number } | null;
  onMarkerClick: (index: number) => void;
  isVisible: boolean;
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

interface MapPoint {
  lat: number;
  lng: number;
  index: number;
  restaurant: HappyHourPlace;
  isActive: boolean;
}

const MIN_CLUSTER_ZOOM = 15; // disable clustering above this zoom

function clusterPoints(
  L: any,
  map: any,
  points: MapPoint[],
  cellSize: number = 20
): ({ type: "cluster"; lat: number; lng: number; count: number; hasActive: boolean; points: MapPoint[] } | { type: "single"; point: MapPoint })[] {
  if (points.length === 0) return [];

  const zoom = map.getZoom();
  // Zoom-aware cell size: larger cells when zoomed out, smaller when zoomed in
  const adjustedCellSize = cellSize * Math.pow(2, 13 - zoom); // 13 is default zoom

  const projected = points.map((p) => ({
    point: p,
    px: map.project([p.lat, p.lng], zoom),
  }));

  const grid = new Map<string, typeof projected>();

  for (const item of projected) {
    const cellX = Math.floor(item.px.x / adjustedCellSize);
    const cellY = Math.floor(item.px.y / adjustedCellSize);
    const key = `${cellX},${cellY}`;
    if (!grid.has(key)) grid.set(key, []);
    grid.get(key)!.push(item);
  }

  const results: ReturnType<typeof clusterPoints> = [];

  for (const cell of grid.values()) {
    if (zoom >= MIN_CLUSTER_ZOOM || cell.length === 1) {
      // At high zoom, never cluster — show individual markers
      for (const c of cell) {
        results.push({ type: "single", point: c.point });
      }
    } else {
      const avgLat = cell.reduce((s, c) => s + c.point.lat, 0) / cell.length;
      const avgLng = cell.reduce((s, c) => s + c.point.lng, 0) / cell.length;
      const hasActive = cell.some((c) => c.point.isActive);
      results.push({
        type: "cluster",
        lat: avgLat,
        lng: avgLng,
        count: cell.length,
        hasActive,
        points: cell.map((c) => c.point),
      });
    }
  }

  return results;
}

function renderMarkers(
  L: any,
  map: any,
  layerGroup: any,
  restaurants: HappyHourPlace[],
  selectedDateTime: Date
) {
  layerGroup.clearLayers();

  const points: MapPoint[] = [];
  restaurants.forEach((restaurant, index) => {
    const lat = parseFloat(restaurant.latitude || "");
    const lng = parseFloat(restaurant.longitude || "");
    if (!isNaN(lat) && !isNaN(lng)) {
      const hasHH = hasHappyHour(restaurant);
      const isActive = hasHH && isHappyHourActive(restaurant.happy_hour_times, selectedDateTime);
      points.push({ lat, lng, index, restaurant, isActive });
    }
  });

  const clustered = clusterPoints(L, map, points);

  clustered.forEach((item) => {
    if (item.type === "single") {
      const { point } = item;
      const hasHH = hasHappyHour(point.restaurant);
      const statusClass = point.isActive ? "active" : "inactive";

      const icon = L.divIcon({
        className: `custom-marker ${statusClass}`,
        html: `<div class="marker-pin"></div>`,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });

      const marker = L.marker([point.lat, point.lng], { icon });

      const popupHtml = `
        <div class="marker-popup">
          <h4>${escapeHtml(point.restaurant.restaurant_name)}</h4>
          <span class="popup-status ${point.isActive ? "active" : "inactive"}">
            ${point.isActive ? "Active now" : hasHH ? "Not active now" : "No Happy Hour"}
          </span>
          ${point.restaurant.menu_summary ? `<div class="popup-deals">${escapeHtml(point.restaurant.menu_summary)}</div>` : ""}
          <div class="popup-link" data-index="${point.index}">View details</div>
        </div>
      `;

      marker.bindPopup(popupHtml);
      layerGroup.addLayer(marker);
    } else {
      const clusterClass = item.hasActive ? "custom-cluster active" : "custom-cluster inactive";
      const icon = L.divIcon({
        className: clusterClass,
        html: `<div class="cluster-pin">${item.count}</div>`,
        iconSize: [36, 36],
        iconAnchor: [18, 18],
      });

      const marker = L.marker([item.lat, item.lng], { icon });
      marker.on("click", () => {
        map.setZoom(map.getZoom() + 1);
      });
      layerGroup.addLayer(marker);
    }
  });
}

function fitToBounds(map: any, restaurants: HappyHourPlace[]) {
  const bounds: [number, number][] = [];
  restaurants.forEach((restaurant) => {
    const lat = parseFloat(restaurant.latitude || "");
    const lng = parseFloat(restaurant.longitude || "");
    if (!isNaN(lat) && !isNaN(lng)) {
      bounds.push([lat, lng]);
    }
  });

  if (bounds.length > 0) {
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
  }
}

export default function RestaurantMap({
  restaurants,
  selectedDateTime,
  userLocation,
  onMarkerClick,
  isVisible,
}: RestaurantMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const layerGroupRef = useRef<any>(null);
  const userMarkerRef = useRef<any>(null);
  const LRef = useRef<any>(null);
  const onMarkerClickRef = useRef(onMarkerClick);
  const restaurantsRef = useRef(restaurants);
  const selectedDateTimeRef = useRef(selectedDateTime);
  onMarkerClickRef.current = onMarkerClick;
  restaurantsRef.current = restaurants;
  selectedDateTimeRef.current = selectedDateTime;

  // Initialize map once when container becomes visible
  useEffect(() => {
    if (!isVisible || !mapContainerRef.current) return;
    if ((mapContainerRef.current as any)._leaflet_id) return;

    let cancelled = false;
    let map: any;

    const initMap = async () => {
      const container = mapContainerRef.current;
      if (!container) return;
      if ((container as any)._leaflet_id) return;

      const L = await import("leaflet");
      if (cancelled) return;
      if ((container as any)._leaflet_id) return;

      map = L.map(container).setView([32.7157, -117.1611], 13);

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).addTo(map);

      const layerGroup = L.layerGroup().addTo(map);

      mapInstanceRef.current = map;
      layerGroupRef.current = layerGroup;
      LRef.current = L;

      renderMarkers(L, map, layerGroup, restaurantsRef.current, selectedDateTimeRef.current);
      fitToBounds(map, restaurantsRef.current);

      // Use refs so zoomend always reads latest data
      map.on("zoomend", () => {
        const latestL = LRef.current;
        const latestMap = mapInstanceRef.current;
        const latestLayerGroup = layerGroupRef.current;
        if (!latestL || !latestMap || !latestLayerGroup) return;
        renderMarkers(latestL, latestMap, latestLayerGroup, restaurantsRef.current, selectedDateTimeRef.current);
      });
    };

    initMap();

    return () => {
      cancelled = true;
      if (map) {
        try { map.remove(); } catch { /* ignore */ }
      }
      mapInstanceRef.current = null;
      layerGroupRef.current = null;
      LRef.current = null;
      const container = mapContainerRef.current;
      if (container) {
        container.innerHTML = "";
        (container as any)._leaflet_id = undefined;
      }
    };
  }, [isVisible]);

  // Update markers and bounds when restaurants or time changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    const layerGroup = layerGroupRef.current;
    const L = LRef.current;
    if (!map || !layerGroup || !L) return;

    renderMarkers(L, map, layerGroup, restaurants, selectedDateTime);
  }, [restaurants, selectedDateTime]);

  // Invalidate size when visibility changes to visible
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !isVisible) return;
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 0);
    return () => clearTimeout(timer);
  }, [isVisible]);

  // Update user location marker
  useEffect(() => {
    const map = mapInstanceRef.current;
    const L = LRef.current;
    if (!map || !L) return;

    if (userMarkerRef.current) {
      map.removeLayer(userMarkerRef.current);
      userMarkerRef.current = null;
    }

    if (userLocation) {
      const icon = L.divIcon({
        className: "custom-marker user-location",
        html: `<div class="marker-pin"></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      });
      userMarkerRef.current = L.marker([userLocation.lat, userLocation.lng], { icon }).addTo(map);
    }
  }, [userLocation]);

  // Handle popup "View details" clicks via delegation
  useEffect(() => {
    const container = mapContainerRef.current;
    if (!container) return;

    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const link = target.closest(".popup-link") as HTMLElement | null;
      if (link) {
        const index = parseInt(link.getAttribute("data-index") || "", 10);
        if (!isNaN(index)) onMarkerClickRef.current(index);
      }
    };

    container.addEventListener("click", handleClick);
    return () => container.removeEventListener("click", handleClick);
  }, []);

  return (
    <div
      ref={mapContainerRef}
      data-testid="restaurant-map"
      className="w-full h-[600px] rounded-lg border border-gray-200"
    />
  );
}
