import '@testing-library/jest-dom';
import { vi } from 'vitest';
import React from 'react';

// Mock ResizeObserver for Recharts
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// Mock react-leaflet for headless jsdom test environments
vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: any) => React.createElement('div', { 'data-testid': 'map-container' }, children),
  TileLayer: () => React.createElement('div', { 'data-testid': 'tile-layer' }),
  CircleMarker: ({ children }: any) => React.createElement('div', { 'data-testid': 'circle-marker' }, children),
  Popup: ({ children }: any) => React.createElement('div', { 'data-testid': 'popup' }, children),
  Tooltip: ({ children }: any) => React.createElement('div', { 'data-testid': 'tooltip' }, children),
  useMap: () => ({
    setView: vi.fn(),
    flyTo: vi.fn(),
  }),
}));
