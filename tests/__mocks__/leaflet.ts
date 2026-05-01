import { vi } from 'vitest';

export const mockLayers: any[] = [];
export const mockMarkers: any[] = [];
export let mockMapZoom = 13;
export const eventHandlers: Map<string, Set<Function>> = new Map();

export function clearMockState() {
  mockLayers.length = 0;
  mockMarkers.length = 0;
  mockMapZoom = 13;
  eventHandlers.clear();
}

export function getHandlers(event: string): Set<Function> {
  if (!eventHandlers.has(event)) eventHandlers.set(event, new Set());
  return eventHandlers.get(event)!;
}

export function triggerEvent(event: string) {
  getHandlers(event).forEach((fn) => fn());
}

const mockL = {
  map: vi.fn((container: any) => {
    const mapInstance = {
      setView: vi.fn(() => mapInstance),
      getZoom: vi.fn(() => mockMapZoom),
      setZoom: vi.fn((z: number) => { mockMapZoom = z; }),
      fitBounds: vi.fn(),
      invalidateSize: vi.fn(),
      remove: vi.fn(),
      project: vi.fn((latLng: [number, number], zoom: number) => ({
        x: latLng[1] * 1000 * zoom,
        y: latLng[0] * 1000 * zoom,
      })),
      on: vi.fn((event: string, fn: Function) => {
        getHandlers(event).add(fn);
      }),
      addLayer: vi.fn((layer: any) => {
        mockLayers.push(layer);
      }),
      removeLayer: vi.fn((layer: any) => {
        const idx = mockLayers.indexOf(layer);
        if (idx > -1) mockLayers.splice(idx, 1);
      }),
    };
    if (container) {
      (container as any)._leaflet_id = 1;
    }
    return mapInstance;
  }),
  tileLayer: vi.fn(() => ({
    addTo: vi.fn(),
  })),
  layerGroup: vi.fn(() => {
    const group = {
      addTo: vi.fn((map: any) => {
        map.addLayer(group);
        return group;
      }),
      clearLayers: vi.fn(() => {
        mockMarkers.length = 0;
      }),
      addLayer: vi.fn((marker: any) => {
        mockMarkers.push(marker);
      }),
    };
    return group;
  }),
  marker: vi.fn((latLng: [number, number], options: any) => {
    const marker = {
      latLng,
      options,
      popupHtml: null as string | null,
      clickHandler: null as Function | null,
      bindPopup: vi.fn((html: string) => {
        marker.popupHtml = html;
        return marker;
      }),
      on: vi.fn((event: string, fn: Function) => {
        if (event === 'click') marker.clickHandler = fn;
      }),
      addTo: vi.fn((map: any) => {
        map.addLayer(marker);
        return marker;
      }),
    };
    return marker;
  }),
  divIcon: vi.fn((options: any) => options),
};

export default mockL;
export const { map, tileLayer, layerGroup, marker, divIcon } = mockL;
