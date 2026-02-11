import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import { ArrowLeft } from 'lucide-react';

import 'mapbox-gl/dist/mapbox-gl.css';

mapboxgl.accessToken = 'pk.eyJ1IjoicG1hcnRoaSIsImEiOiJjbWxjbm1qYXQxMWRlM2Zwb2J1YThhODcwIn0.pWp7Uy5gzAy7I_0r7HAujQ';
mapboxgl.prewarm();
const CACHE_TTL_MS = 10 * 60 * 1000;

const MapboxExample = ({ onboardingPhase = 'done', onReturnToInstructions }) => {
  const mapContainerRef = useRef();
  const mapRef = useRef();
  const searchInputRef = useRef();
  const resultsListRef = useRef();
  const searchOpenRef = useRef(false);
  const openAnimationTimerRef = useRef();
  const closeAnimationTimerRef = useRef();
  const searchboxSessionTokenRef = useRef('');
  const googleDisabledRef = useRef(false);
  const suggestionAbortRef = useRef();
  const searchAbortRef = useRef();
  const suggestionsCacheRef = useRef(new Map());
  const searchCacheRef = useRef(new Map());
  const cameraTransitionRef = useRef(0);
  const spinEnabledRef = useRef(true);
  const userInteractingRef = useRef(false);
  const viewModeRef = useRef('instructions');
  const initialViewRef = useRef({
    center: [-100.486052, 30],
    zoom: 1.94,
    pitch: 0,
    bearing: 0
  });
  const initialGlobePaddingRef = useRef({ top: 0, right: 0, bottom: 0, left: 520 });
  const centeredGlobePaddingRef = useRef({ top: 0, right: 0, bottom: 0, left: 0 });
  const hasCompletedOnboardingRef = useRef(false);
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [searchError, setSearchError] = useState('');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [renderSearch, setRenderSearch] = useState(false);
  const [searchAnimatedIn, setSearchAnimatedIn] = useState(false);
  const [activeLocationIndex, setActiveLocationIndex] = useState(0);
  const [manualSelection, setManualSelection] = useState(false);
  const [dynamicSuggestions, setDynamicSuggestions] = useState([]);
  const googleApiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

  const quickLocations = useMemo(
    () => [
      {
        name: 'New York City',
        subtitle: 'New York City, New York, United States',
        flag: '🇺🇸',
        aliases: ['nyc', 'new york', 'new york city'],
        center: [-74.006, 40.7128],
        camera: { zoom: 10.4, pitch: 0, bearing: 0 }
      },
      {
        name: 'Los Angeles',
        subtitle: 'Los Angeles, California, United States',
        flag: '🇺🇸',
        aliases: ['la', 'los angeles'],
        center: [-118.2437, 34.0522],
        camera: { zoom: 10.2, pitch: 0, bearing: 0 }
      },
      {
        name: 'Chicago',
        subtitle: 'Chicago, Illinois, United States',
        flag: '🇺🇸',
        aliases: ['chicago'],
        center: [-87.6298, 41.8781],
        camera: { zoom: 10.5, pitch: 0, bearing: 0 }
      },
      {
        name: 'San Francisco',
        subtitle: 'San Francisco, California, United States',
        flag: '🇺🇸',
        aliases: ['sf', 'san francisco', 'bay area'],
        center: [-122.4194, 37.7749],
        camera: { zoom: 10.6, pitch: 0, bearing: 0 }
      },
      {
        name: 'Seattle',
        subtitle: 'Seattle, Washington, United States',
        flag: '🇺🇸',
        aliases: ['seattle'],
        center: [-122.3321, 47.6062],
        camera: { zoom: 10.7, pitch: 0, bearing: 0 }
      },
      {
        name: 'Miami',
        subtitle: 'Miami, Florida, United States',
        flag: '🇺🇸',
        aliases: ['miami'],
        center: [-80.1918, 25.7617],
        camera: { zoom: 10.8, pitch: 0, bearing: 0 }
      },
      {
        name: 'Toronto',
        subtitle: 'Toronto, Ontario, Canada',
        flag: '🇨🇦',
        aliases: ['toronto'],
        center: [-79.3832, 43.6532],
        camera: { zoom: 10.6, pitch: 0, bearing: 0 }
      },
      {
        name: 'Vancouver',
        subtitle: 'Vancouver, British Columbia, Canada',
        flag: '🇨🇦',
        aliases: ['vancouver'],
        center: [-123.1207, 49.2827],
        camera: { zoom: 10.7, pitch: 0, bearing: 0 }
      },
      {
        name: 'Mexico City',
        subtitle: 'Mexico City, Mexico City, Mexico',
        flag: '🇲🇽',
        aliases: ['mexico city', 'cdmx'],
        center: [-99.1332, 19.4326],
        camera: { zoom: 10.1, pitch: 0, bearing: 0 }
      },
      {
        name: 'London',
        subtitle: 'London, England, United Kingdom',
        flag: '🇬🇧',
        aliases: ['london', 'ldn'],
        center: [-0.1276, 51.5072],
        camera: { zoom: 10.2, pitch: 0, bearing: 0 }
      },
      {
        name: 'Paris',
        subtitle: 'Paris, Ile-de-France, France',
        flag: '🇫🇷',
        aliases: ['paris'],
        center: [2.3522, 48.8566],
        camera: { zoom: 10.5, pitch: 0, bearing: 0 }
      },
      {
        name: 'Berlin',
        subtitle: 'Berlin, Berlin, Germany',
        flag: '🇩🇪',
        aliases: ['berlin'],
        center: [13.405, 52.52],
        camera: { zoom: 10.4, pitch: 0, bearing: 0 }
      },
      {
        name: 'Madrid',
        subtitle: 'Madrid, Community of Madrid, Spain',
        flag: '🇪🇸',
        aliases: ['madrid'],
        center: [-3.7038, 40.4168],
        camera: { zoom: 10.4, pitch: 0, bearing: 0 }
      },
      {
        name: 'Rome',
        subtitle: 'Rome, Lazio, Italy',
        flag: '🇮🇹',
        aliases: ['rome', 'roma'],
        center: [12.4964, 41.9028],
        camera: { zoom: 10.2, pitch: 0, bearing: 0 }
      },
      {
        name: 'Amsterdam',
        subtitle: 'Amsterdam, North Holland, Netherlands',
        flag: '🇳🇱',
        aliases: ['amsterdam'],
        center: [4.9041, 52.3676],
        camera: { zoom: 10.7, pitch: 0, bearing: 0 }
      },
      {
        name: 'Istanbul',
        subtitle: 'Istanbul, Istanbul, Turkey',
        flag: '🇹🇷',
        aliases: ['istanbul'],
        center: [28.9784, 41.0082],
        camera: { zoom: 10.0, pitch: 0, bearing: 0 }
      },
      {
        name: 'Cairo',
        subtitle: 'Cairo, Cairo Governorate, Egypt',
        flag: '🇪🇬',
        aliases: ['cairo'],
        center: [31.2357, 30.0444],
        camera: { zoom: 10.0, pitch: 0, bearing: 0 }
      },
      {
        name: 'Lagos',
        subtitle: 'Lagos, Lagos State, Nigeria',
        flag: '🇳🇬',
        aliases: ['lagos'],
        center: [3.3792, 6.5244],
        camera: { zoom: 10.0, pitch: 0, bearing: 0 }
      },
      {
        name: 'Johannesburg',
        subtitle: 'Johannesburg, Gauteng, South Africa',
        flag: '🇿🇦',
        aliases: ['johannesburg', 'joburg'],
        center: [28.0473, -26.2041],
        camera: { zoom: 10.3, pitch: 0, bearing: 0 }
      },
      {
        name: 'Tokyo',
        subtitle: 'Tokyo, Tokyo Prefecture, Japan',
        flag: '🇯🇵',
        aliases: ['tokyo'],
        center: [139.6917, 35.6895],
        camera: { zoom: 9.9, pitch: 0, bearing: 0 }
      },
      {
        name: 'Seoul',
        subtitle: 'Seoul, Seoul, South Korea',
        flag: '🇰🇷',
        aliases: ['seoul'],
        center: [126.978, 37.5665],
        camera: { zoom: 10.4, pitch: 0, bearing: 0 }
      },
      {
        name: 'Beijing',
        subtitle: 'Beijing, Beijing Municipality, China',
        flag: '🇨🇳',
        aliases: ['beijing', 'peking'],
        center: [116.4074, 39.9042],
        camera: { zoom: 10.1, pitch: 0, bearing: 0 }
      },
      {
        name: 'Shanghai',
        subtitle: 'Shanghai, Shanghai, China',
        flag: '🇨🇳',
        aliases: ['shanghai'],
        center: [121.4737, 31.2304],
        camera: { zoom: 10.3, pitch: 0, bearing: 0 }
      },
      {
        name: 'Mumbai',
        subtitle: 'Mumbai, Maharashtra, India',
        flag: '🇮🇳',
        aliases: ['mumbai', 'bombay'],
        center: [72.8777, 19.076],
        camera: { zoom: 10.0, pitch: 0, bearing: 0 }
      },
      {
        name: 'Delhi',
        subtitle: 'Delhi, National Capital Territory of Delhi, India',
        flag: '🇮🇳',
        aliases: ['delhi', 'new delhi'],
        center: [77.1025, 28.7041],
        camera: { zoom: 10.0, pitch: 0, bearing: 0 }
      },
      {
        name: 'Bangkok',
        subtitle: 'Bangkok, Bangkok, Thailand',
        flag: '🇹🇭',
        aliases: ['bangkok'],
        center: [100.5018, 13.7563],
        camera: { zoom: 10.2, pitch: 0, bearing: 0 }
      },
      {
        name: 'Dubai',
        subtitle: 'Dubai, Dubai, United Arab Emirates',
        flag: '🇦🇪',
        aliases: ['dubai'],
        center: [55.2708, 25.2048],
        camera: { zoom: 10.8, pitch: 0, bearing: 0 }
      },
      {
        name: 'Riyadh',
        subtitle: 'Riyadh, Riyadh Province, Saudi Arabia',
        flag: '🇸🇦',
        aliases: ['riyadh'],
        center: [46.6753, 24.7136],
        camera: { zoom: 10.1, pitch: 0, bearing: 0 }
      },
      {
        name: 'Singapore',
        subtitle: 'Singapore, Singapore',
        flag: '🇸🇬',
        aliases: ['singapore', 'sg'],
        center: [103.8198, 1.3521],
        camera: { zoom: 11.1, pitch: 0, bearing: 0 }
      },
      {
        name: 'Jakarta',
        subtitle: 'Jakarta, Jakarta, Indonesia',
        flag: '🇮🇩',
        aliases: ['jakarta'],
        center: [106.8456, -6.2088],
        camera: { zoom: 10.1, pitch: 0, bearing: 0 }
      },
      {
        name: 'Sydney',
        subtitle: 'Sydney, New South Wales, Australia',
        flag: '🇦🇺',
        aliases: ['sydney'],
        center: [151.2093, -33.8688],
        camera: { zoom: 10.4, pitch: 0, bearing: 0 }
      },
      {
        name: 'Melbourne',
        subtitle: 'Melbourne, Victoria, Australia',
        flag: '🇦🇺',
        aliases: ['melbourne'],
        center: [144.9631, -37.8136],
        camera: { zoom: 10.4, pitch: 0, bearing: 0 }
      }
    ],
    []
  );

  const landmarkOverrides = useMemo(
    () => [
      {
        id: 'landmark-msg',
        name: 'Madison Square Garden',
        subtitle: 'New York, New York, United States',
        flag: '🇺🇸',
        aliases: ['madison square garden', 'msg'],
        feature: {
          center: [-73.9934, 40.7505],
          place_type: ['poi'],
          text: 'Madison Square Garden'
        }
      },
      {
        id: 'landmark-white-house',
        name: 'The White House',
        subtitle: 'Washington, District of Columbia, United States',
        flag: '🇺🇸',
        aliases: ['white house', 'the white house'],
        feature: {
          center: [-77.0365, 38.8977],
          place_type: ['poi'],
          text: 'The White House'
        }
      },
      {
        id: 'landmark-wall-street',
        name: 'Wall Street',
        subtitle: 'New York, New York, United States',
        flag: '🇺🇸',
        aliases: ['wall street'],
        feature: {
          center: [-74.009, 40.706],
          place_type: ['address'],
          text: 'Wall Street'
        }
      },
      {
        id: 'landmark-burj-khalifa',
        name: 'Burj Khalifa',
        subtitle: 'Dubai, Dubai, United Arab Emirates',
        flag: '🇦🇪',
        aliases: ['burj khalifa'],
        feature: {
          center: [55.2744, 25.1972],
          place_type: ['poi'],
          text: 'Burj Khalifa'
        }
      }
    ],
    []
  );

  const newSearchSessionToken = () => `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

  const filteredLocations = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return quickLocations;
    return quickLocations.filter((location) =>
      [location.name, location.subtitle, ...location.aliases].join(' ').toLowerCase().includes(q)
    );
  }, [query, quickLocations]);

  const normalizeText = (value) => value.toLowerCase().replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim();

  const matchingLandmarks = useMemo(() => {
    const normalizedQuery = normalizeText(query);
    if (!normalizedQuery) return [];

    return landmarkOverrides.filter((landmark) =>
      landmark.aliases.some((alias) => {
        const normalizedAlias = normalizeText(alias);
        return normalizedAlias === normalizedQuery || normalizedAlias.startsWith(normalizedQuery);
      })
    );
  }, [query, landmarkOverrides]);

  const displayResults = useMemo(() => {
    if (!query.trim()) {
      return quickLocations.map((location) => ({ kind: 'quick', key: `quick-${location.name}`, location }));
    }

    const seen = new Set();
    const combined = [];

    matchingLandmarks.forEach((landmark) => {
      const key = `${landmark.name}|${landmark.subtitle}`;
      if (seen.has(key)) return;
      seen.add(key);
      combined.push({ kind: 'landmark', key: landmark.id, landmark });
    });

    dynamicSuggestions.forEach((suggestion) => {
      const key = `${suggestion.name}|${suggestion.subtitle}`;
      if (seen.has(key)) return;
      seen.add(key);
      combined.push({ kind: 'dynamic', key: suggestion.id, suggestion });
    });

    filteredLocations.forEach((location) => {
      const key = `${location.name}|${location.subtitle}`;
      if (seen.has(key)) return;
      seen.add(key);
      combined.push({ kind: 'quick', key: `quick-${location.name}`, location });
    });

    return combined.slice(0, 5);
  }, [query, quickLocations, filteredLocations, dynamicSuggestions, matchingLandmarks]);

  useEffect(() => {
    if (!displayResults.length) {
      setActiveLocationIndex(0);
      return;
    }

    setActiveLocationIndex((index) => Math.min(index, displayResults.length - 1));
  }, [displayResults.length]);

  useEffect(() => {
    if (!renderSearch || !displayResults.length) return;

    const list = resultsListRef.current;
    if (!list) return;

    const activeItem = list.querySelector(`[data-result-index="${activeLocationIndex}"]`);
    if (!activeItem) return;

    activeItem.scrollIntoView({ block: 'nearest' });
  }, [renderSearch, activeLocationIndex, displayResults.length]);

  const flyToLocation = (center, camera, options = {}) => {
    const map = mapRef.current;
    if (!map) return;
    viewModeRef.current = 'focused';
    const { prefer3D = false } = options;
    const transitionId = cameraTransitionRef.current + 1;
    cameraTransitionRef.current = transitionId;

    map.stop();

    map.setPadding({ top: 0, right: 0, bottom: 0, left: 0 });

    spinEnabledRef.current = false;

    const targetPitch = prefer3D ? camera.pitch : 0;
    const targetBearing = prefer3D ? camera.bearing : 0;

    const runFinalFly = () => {
      if (cameraTransitionRef.current !== transitionId) return;

      if (map.getProjection()?.name !== 'mercator') {
        map.setProjection('mercator');
      }

      map.flyTo({
        center,
        zoom: camera.zoom,
        pitch: targetPitch,
        bearing: targetBearing,
        essential: true,
        duration: prefer3D ? 1250 : 1150,
        easing: (t) => 1 - Math.pow(1 - t, 3)
      });

      const hasBuildingsLayer = add3DBuildingsLayer();

      if (prefer3D && hasBuildingsLayer) {
        map.once('idle', () => {
          if (cameraTransitionRef.current !== transitionId) return;

          const canvas = map.getCanvas();
          const cx = canvas.width / 2;
          const cy = canvas.height / 2;
          const hasRendered3D = map.queryRenderedFeatures(
            [
              [cx - 160, cy - 120],
              [cx + 160, cy + 120]
            ],
            { layers: ['3d-buildings'] }
          ).length > 0;

          if (!hasRendered3D && map.getPitch() > 0) {
            map.easeTo({ pitch: 0, bearing: 0, duration: 450, essential: true });
          }
        });
      }
    };

    if (map.getProjection()?.name === 'globe') {
      const approachZoom = Math.max(
        2.8,
        Math.min(
          prefer3D ? 5.8 : 5.4,
          camera.zoom - (prefer3D ? 2.3 : 1.9)
        )
      );

      map.flyTo({
        center,
        zoom: approachZoom,
        pitch: 0,
        bearing: 0,
        essential: true,
        duration: 1325,
        easing: (t) => 1 - Math.pow(1 - t, 3)
      });

      map.once('moveend', runFinalFly);
    } else {
      runFinalFly();
    }

    setSearchError('');
    setIsSearchOpen(false);
  };

  const selectResult = async (result) => {
    if (!result) return;

    if (result.kind === 'landmark') {
      flyToFeature(result.landmark.feature);
      return;
    }

    if (result.kind === 'quick') {
      flyToLocation(result.location.center, result.location.camera);
      return;
    }

    if (result.kind === 'dynamic') {
      if (result.suggestion.feature) {
        flyToFeature(result.suggestion.feature);
        return;
      }

      setIsSearching(true);
      setSearchError('');

      if (searchAbortRef.current) {
        searchAbortRef.current.abort();
      }

      const controller = new AbortController();
      searchAbortRef.current = controller;

      try {
        const feature = await retrieveSearchboxFeature(result.suggestion.mapboxId, controller.signal);
        if (controller.signal.aborted) return;
        if (!feature?.center) {
          setSearchError('Could not open this location.');
          return;
        }
        flyToFeature(feature);
      } catch (error) {
        if (error.name !== 'AbortError') {
          setSearchError('Could not open this location.');
        }
      } finally {
        if (searchAbortRef.current === controller) {
          searchAbortRef.current = null;
          setIsSearching(false);
        }
      }
    }
  };

  const add3DBuildingsLayer = () => {
    const map = mapRef.current;
    if (!map) return false;
    if (!map.getSource('composite')) return false;
    if (map.getLayer('3d-buildings')) return true;

    const layers = map.getStyle().layers || [];
    const labelLayerId = layers.find(
      (layer) => layer.type === 'symbol' && layer.layout && layer.layout['text-field']
    )?.id;

    map.addLayer(
      {
        id: '3d-buildings',
        source: 'composite',
        'source-layer': 'building',
        filter: ['==', ['get', 'extrude'], 'true'],
        type: 'fill-extrusion',
        minzoom: 14,
        paint: {
          'fill-extrusion-color': '#c7d3e0',
          'fill-extrusion-height': [
            'interpolate',
            ['linear'],
            ['zoom'],
            14,
            0,
            14.5,
            ['coalesce', ['get', 'height'], 0]
          ],
          'fill-extrusion-base': [
            'interpolate',
            ['linear'],
            ['zoom'],
            14,
            0,
            14.5,
            ['coalesce', ['get', 'min_height'], 0]
          ],
          'fill-extrusion-opacity': 0.92
        }
      },
      labelLayerId
    );

    return true;
  };

  const getCameraForFeature = (feature) => {
    const placeTypes = feature.place_type || [];

    if (placeTypes.includes('address') || placeTypes.includes('poi')) {
      return { zoom: 15.2, pitch: 60, bearing: 20 };
    }

    if (placeTypes.includes('district') || placeTypes.includes('neighborhood') || placeTypes.includes('postcode')) {
      return { zoom: 14.8, pitch: 58, bearing: 20 };
    }

    if (placeTypes.includes('place') || placeTypes.includes('locality')) {
      return { zoom: 10.2, pitch: 0, bearing: 0 };
    }

    if (placeTypes.includes('region')) {
      return { zoom: 6.7, pitch: 0, bearing: 0 };
    }

    if (placeTypes.includes('country')) {
      return { zoom: 4.8, pitch: 0, bearing: 0 };
    }

    return { zoom: 12.0, pitch: 0, bearing: 0 };
  };

  const flyToFeature = (feature) => {
    const map = mapRef.current;
    if (!map || !feature?.center) return;
    viewModeRef.current = 'focused';

    const transitionId = cameraTransitionRef.current + 1;
    cameraTransitionRef.current = transitionId;

    map.stop();

    const placeTypes = feature.place_type || [];
    const camera = getCameraForFeature(feature);
    const isSmallArea3D =
      placeTypes.includes('address') ||
      placeTypes.includes('poi') ||
      placeTypes.includes('district') ||
      placeTypes.includes('neighborhood') ||
      placeTypes.includes('postcode');

    spinEnabledRef.current = false;

    if (!isSmallArea3D && Array.isArray(feature.bbox) && feature.bbox.length === 4) {
      const [minLng, minLat, maxLng, maxLat] = feature.bbox;
      const bboxCenter = [(minLng + maxLng) / 2, (minLat + maxLat) / 2];

      const runFinalBounds = () => {
        if (cameraTransitionRef.current !== transitionId) return;

        if (map.getProjection()?.name !== 'mercator') {
          map.setProjection('mercator');
        }

        map.fitBounds(
          [
            [minLng, minLat],
            [maxLng, maxLat]
          ],
          {
            padding: { top: 120, right: 120, bottom: 120, left: 120 },
            maxZoom: camera.zoom,
            pitch: 0,
            bearing: 0,
            duration: 1050,
            essential: true
          }
        );
      };

      if (map.getProjection()?.name === 'globe') {
        map.flyTo({
          center: bboxCenter,
          zoom: Math.min(camera.zoom, 5.2),
          pitch: 0,
          bearing: 0,
          essential: true,
          duration: 1100,
          easing: (t) => 1 - Math.pow(1 - t, 3)
        });

        map.once('moveend', runFinalBounds);
      } else {
        runFinalBounds();
      }

      setSearchError('');
      setIsSearchOpen(false);
      return;
    }

    flyToLocation(feature.center, camera, { prefer3D: isSmallArea3D });
  };

  const mapGoogleTypesToPlaceType = (types) => {
    const typeSet = new Set(types || []);

    const isSpecificPlace = [
      'point_of_interest',
      'establishment',
      'premise',
      'subpremise',
      'street_address',
      'route',
      'airport',
      'shopping_mall',
      'stadium',
      'tourist_attraction',
      'university',
      'hospital'
    ].some((type) => typeSet.has(type));

    if (isSpecificPlace) return ['poi'];
    if (typeSet.has('postal_code')) return ['postcode'];
    if (typeSet.has('neighborhood') || typeSet.has('sublocality') || typeSet.has('sublocality_level_1')) {
      return ['neighborhood'];
    }
    if (typeSet.has('locality')) return ['place'];
    if (typeSet.has('administrative_area_level_1') || typeSet.has('administrative_area_level_2')) {
      return ['region'];
    }
    if (typeSet.has('country')) return ['country'];

    return ['place'];
  };

  const googleViewportToBbox = (viewport) => {
    if (!viewport) return undefined;

    if (viewport.low && viewport.high) {
      return [
        viewport.low.longitude,
        viewport.low.latitude,
        viewport.high.longitude,
        viewport.high.latitude
      ];
    }

    if (viewport.southwest && viewport.northeast) {
      return [
        viewport.southwest.lng,
        viewport.southwest.lat,
        viewport.northeast.lng,
        viewport.northeast.lat
      ];
    }

    return undefined;
  };

  const searchWithGooglePlaces = async (textQuery, signal) => {
    if (!googleApiKey) {
      return { feature: null, error: null };
    }

    try {
      const response = await fetch('https://places.googleapis.com/v1/places:searchText', {
        method: 'POST',
        signal,
        headers: {
          'Content-Type': 'application/json',
          'X-Goog-Api-Key': googleApiKey,
          'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.location,places.viewport,places.types'
        },
        body: JSON.stringify({
          textQuery,
          languageCode: 'en',
          maxResultCount: 1
        })
      });

      if (!response.ok) {
        const errorPayload = await response.json().catch(() => null);
        return {
          feature: null,
          error: errorPayload?.error?.message || 'Google Places request failed.'
        };
      }

      const data = await response.json();
      const place = data?.places?.[0];
      if (!place?.location) {
        return { feature: null, error: null };
      }

      const latitude = place.location.latitude ?? place.location.lat;
      const longitude = place.location.longitude ?? place.location.lng;
      if (typeof latitude !== 'number' || typeof longitude !== 'number') {
        return { feature: null, error: null };
      }

      return {
        feature: {
          center: [longitude, latitude],
          place_type: mapGoogleTypesToPlaceType(place.types),
          bbox: googleViewportToBbox(place.viewport),
          text: place.displayName?.text || place.formattedAddress || textQuery
        },
        error: null
      };
    } catch (error) {
      if (error.name === 'AbortError') {
        return { feature: null, error: null };
      }
      return { feature: null, error: 'Unable to reach Google Places API.' };
    }
  };

  const normalizeSearchboxSuggestion = (suggestion) => {
    const countryCode = suggestion?.context?.country?.country_code;
    const countryName = suggestion?.context?.country?.name;
    const flag = countryCode ? countryCode.toUpperCase().replace(/./g, (char) => String.fromCodePoint(127397 + char.charCodeAt(0))) : '📍';
    const subtitleBase = suggestion.full_address || suggestion.place_formatted || '';
    const subtitle = countryName && subtitleBase && !subtitleBase.toLowerCase().includes(countryName.toLowerCase())
      ? `${subtitleBase}, ${countryName}`
      : subtitleBase || countryName || '';

    return {
      id: suggestion.mapbox_id,
      mapboxId: suggestion.mapbox_id,
      name: suggestion.name || suggestion.name_preferred || 'Unknown place',
      subtitle,
      featureType: suggestion.feature_type || 'place',
      flag
    };
  };

  const inferSearchIntent = (textQuery) => {
    const q = textQuery.trim().toLowerCase();
    if (!q) return 'broad';

    const hasNumber = /\d/.test(q);
    const hasStreetWord = /\b(st|street|rd|road|ave|avenue|blvd|boulevard|dr|drive|ln|lane|ct|court|way|pl|place|suite)\b/.test(q);
    const hasComma = q.includes(',');
    const hasManyWords = q.split(/\s+/).length >= 3;

    if (hasNumber || hasStreetWord || hasComma || hasManyWords) {
      return 'specific';
    }

    return 'broad';
  };

  const suggestionTypeWeight = (featureType, intent, textQuery) => {
    const q = normalizeText(textQuery);
    const looksLikeStreetQuery = /\b(st|street|rd|road|ave|avenue|blvd|boulevard|dr|drive|ln|lane|ct|court|way|pl|place)\b/.test(q);

    if (looksLikeStreetQuery && intent === 'specific') {
      const streetWeights = {
        street: 95,
        address: 90,
        neighborhood: 55,
        district: 48,
        place: 35,
        locality: 35,
        poi: 30,
        region: 18,
        country: 8
      };
      return streetWeights[featureType] ?? 5;
    }

    const broadWeights = {
      place: 90,
      locality: 90,
      district: 65,
      neighborhood: 50,
      region: 45,
      country: 35,
      poi: 20,
      address: 10,
      street: 8
    };

    const specificWeights = {
      poi: 90,
      address: 85,
      street: 70,
      neighborhood: 55,
      district: 50,
      place: 40,
      locality: 40,
      region: 25,
      country: 12
    };

    const table = intent === 'specific' ? specificWeights : broadWeights;
    return table[featureType] ?? 5;
  };

  const rankSuggestions = (suggestions, textQuery) => {
    const q = textQuery.trim().toLowerCase();
    const intent = inferSearchIntent(textQuery);
    const normalizedQuery = normalizeText(textQuery);
    const queryTokens = normalizedQuery.split(' ').filter(Boolean);
    const businessNoiseWords = ['court', 'office', 'corporation', 'database', 'jewellers', 'hotel', 'church'];

    const scored = suggestions.map((suggestion) => {
      const name = suggestion.name.toLowerCase();
      const normalizedName = normalizeText(suggestion.name);
      const normalizedSubtitle = normalizeText(suggestion.subtitle);
      const combined = `${normalizedName} ${normalizedSubtitle}`;
      let score = suggestionTypeWeight(suggestion.featureType, intent, textQuery);

      if (normalizedName === normalizedQuery) score += 180;
      if (normalizedName.startsWith(normalizedQuery)) score += 95;
      if (name === q) score += 70;
      if (name.startsWith(q)) score += 45;
      if (name.includes(q)) score += 18;

      const matchedTokenCount = queryTokens.filter((token) => combined.includes(token)).length;
      if (matchedTokenCount === queryTokens.length) score += 50;
      if (matchedTokenCount < queryTokens.length) score -= 60;

      if (queryTokens.length >= 2 && suggestion.featureType === 'poi' && !normalizedName.includes(normalizedQuery)) {
        score -= 25;
      }

      if (queryTokens.length <= 2) {
        const hasNoise = businessNoiseWords.some((word) => normalizedName.includes(word));
        if (hasNoise && !normalizedName.startsWith(normalizedQuery)) {
          score -= 50;
        }
      }

      const countryName = suggestion.subtitle.split(',').pop()?.trim().toLowerCase();
      if (q === 'dubai' && countryName === 'united arab emirates') score += 90;
      if (q === 'calgary' && countryName === 'canada') score += 90;
      if (q === 'london' && countryName === 'united kingdom') score += 90;
      if (q === 'paris' && countryName === 'france') score += 90;
      if (q === 'tokyo' && countryName === 'japan') score += 90;

      return { suggestion, score };
    });

    scored.sort((a, b) => b.score - a.score);
    return scored.map((entry) => entry.suggestion);
  };

  const searchboxSuggest = async (textQuery, signal) => {
    if (!searchboxSessionTokenRef.current) {
      searchboxSessionTokenRef.current = newSearchSessionToken();
    }

    const token = mapboxgl.accessToken;
    const intent = inferSearchIntent(textQuery);
    const params = new URLSearchParams({
      q: textQuery,
      access_token: token,
      session_token: searchboxSessionTokenRef.current,
      language: 'en',
      limit: '8',
      types:
        intent === 'specific'
          ? 'poi,address,street,neighborhood,locality,place,district,region,country'
          : 'place,locality,district,region,country,neighborhood,poi,address,street'
    });

    const url = `https://api.mapbox.com/search/searchbox/v1/suggest?${params.toString()}`;
    const response = await fetch(url, { signal });
    if (!response.ok) return [];
    const data = await response.json();

    const normalized = (data.suggestions || []).map(normalizeSearchboxSuggestion);
    return rankSuggestions(normalized, textQuery);
  };

  const geocodeBroadSuggestions = async (textQuery, signal) => {
    const token = mapboxgl.accessToken;
    const params = new URLSearchParams({
      access_token: token,
      limit: '5',
      language: 'en',
      autocomplete: 'true',
      types: 'place,locality,district,region,country'
    });
    const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(textQuery)}.json?${params.toString()}`;

    const response = await fetch(url, { signal });
    if (!response.ok) return [];

    const data = await response.json();
    const features = data.features || [];

    const normalized = features
      .filter((feature) => Array.isArray(feature.center) && feature.center.length === 2)
      .map((feature) => {
        const placeType = feature.place_type?.[0] || 'place';
        const countryContext = feature.context?.find((item) => item.id?.startsWith('country.'));
        const country = countryContext?.text || '';
        const countryCode = countryContext?.short_code?.toUpperCase();
        const flag = countryCode
          ? countryCode.replace(/./g, (char) => String.fromCodePoint(127397 + char.charCodeAt(0)))
          : '📍';

        return {
          id: feature.id,
          mapboxId: null,
          name: feature.text || feature.place_name || 'Unknown place',
          subtitle: feature.place_name || (country ? `${feature.text}, ${country}` : feature.text || ''),
          featureType:
            placeType === 'place' || placeType === 'locality'
              ? 'place'
              : placeType === 'district'
                ? 'district'
                : placeType === 'region'
                  ? 'region'
                  : placeType === 'country'
                    ? 'country'
                    : 'place',
          flag,
          feature
        };
      });

    return rankSuggestions(normalized, textQuery);
  };

  const retrieveSearchboxFeature = async (mapboxId, signal) => {
    if (!searchboxSessionTokenRef.current) {
      searchboxSessionTokenRef.current = newSearchSessionToken();
    }

    const cacheKey = `retrieve:${mapboxId}`;
    const cached = searchCacheRef.current.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
      return cached.feature;
    }

    const token = mapboxgl.accessToken;
    const params = new URLSearchParams({
      access_token: token,
      session_token: searchboxSessionTokenRef.current
    });
    const url = `https://api.mapbox.com/search/searchbox/v1/retrieve/${encodeURIComponent(mapboxId)}?${params.toString()}`;

    const response = await fetch(url, { signal });
    if (!response.ok) return null;
    const data = await response.json();
    const feature = data.features?.[0];
    if (!feature) return null;

    const center = feature.geometry?.coordinates;
    const context = feature.properties?.context || {};
    const placeType = feature.properties?.feature_type || 'place';
    const bbox = feature.bbox;

    const normalized = {
      center,
      bbox,
      text: feature.properties?.name || '',
      place_type:
        placeType === 'poi'
          ? ['poi']
          : placeType === 'address'
            ? ['address']
            : placeType === 'neighborhood'
              ? ['neighborhood']
              : placeType === 'locality' || placeType === 'place'
                ? ['place']
                : placeType === 'district'
                  ? ['district']
                  : placeType === 'region'
                    ? ['region']
                    : placeType === 'country'
                      ? ['country']
                      : ['place'],
      context
    };

    searchCacheRef.current.set(cacheKey, { feature: normalized, timestamp: Date.now() });
    return normalized;
  };

  const searchWithMapbox = async (textQuery, signal) => {
    const token = mapboxgl.accessToken;
    const params = new URLSearchParams({
      access_token: token,
      limit: '1',
      language: 'en',
      autocomplete: 'true'
    });
    const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(textQuery)}.json?${params.toString()}`;

    const response = await fetch(url, { signal });
    if (!response.ok) {
      return null;
    }

    const data = await response.json();
    return data.features?.[0] || null;
  };

  const searchWithMapboxFocused = async (textQuery, signal) => {
    const token = mapboxgl.accessToken;
    const params = new URLSearchParams({
      access_token: token,
      limit: '1',
      language: 'en',
      autocomplete: 'false',
      types: 'poi,address,street'
    });
    const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(textQuery)}.json?${params.toString()}`;

    const response = await fetch(url, { signal });
    if (!response.ok) {
      return null;
    }

    const data = await response.json();
    return data.features?.[0] || null;
  };

  const fetchDynamicSuggestions = async (textQuery, signal) => {
    try {
      const intent = inferSearchIntent(textQuery);
      const suggestions =
        intent === 'broad'
          ? await geocodeBroadSuggestions(textQuery, signal)
          : await searchboxSuggest(textQuery, signal);
      return suggestions;
    } catch (error) {
      if (error.name === 'AbortError') return [];
      return [];
    }
  };

  const searchLocation = async (event) => {
    event.preventDefault();

    const trimmedQuery = query.trim();
    const normalizedQuery = trimmedQuery.toLowerCase();

    const activeResult = displayResults[activeLocationIndex];
    if (!trimmedQuery && activeResult) {
      await selectResult(activeResult);
      return;
    }

    if (trimmedQuery && manualSelection && activeResult) {
      await selectResult(activeResult);
      return;
    }

    if (!trimmedQuery) {
      const quickLocation = filteredLocations[activeLocationIndex] || quickLocations[0];
      if (quickLocation) {
        flyToLocation(quickLocation.center, quickLocation.camera);
      }
      return;
    }

    const exactQuickLocation = quickLocations.find((location) =>
      [location.name.toLowerCase(), ...location.aliases].includes(normalizedQuery)
    );

    if (exactQuickLocation) {
      flyToLocation(exactQuickLocation.center, exactQuickLocation.camera);
      return;
    }

    const map = mapRef.current;
    if (!map) return;

    const cacheKey = normalizedQuery;
    const cachedSearch = searchCacheRef.current.get(cacheKey);
    if (cachedSearch && Date.now() - cachedSearch.timestamp < CACHE_TTL_MS) {
      flyToFeature(cachedSearch.feature);
      return;
    }

    setIsSearching(true);
    setSearchError('');

    if (searchAbortRef.current) {
      searchAbortRef.current.abort();
    }
    const controller = new AbortController();
    searchAbortRef.current = controller;

    try {
      const intent = inferSearchIntent(trimmedQuery);
      let feature = null;

      if (intent === 'specific') {
        feature = await searchWithMapboxFocused(trimmedQuery, controller.signal);
        if (controller.signal.aborted) return;

        if (!feature?.center) {
          const directSuggestions = await searchboxSuggest(trimmedQuery, controller.signal);
          if (controller.signal.aborted) return;

          if (directSuggestions.length > 0) {
            const directFeature = await retrieveSearchboxFeature(directSuggestions[0].mapboxId, controller.signal);
            if (controller.signal.aborted) return;

            if (directFeature?.center) {
              feature = directFeature;
            }
          }
        }
      } else {
        feature = await searchWithMapbox(trimmedQuery, controller.signal);
        if (controller.signal.aborted) return;
      }

      if (!feature?.center) {
        const googleResult = googleDisabledRef.current
          ? { feature: null, error: null }
          : await searchWithGooglePlaces(trimmedQuery, controller.signal);

        if (controller.signal.aborted) return;

        if (googleResult.error && googleApiKey) {
          if (
            googleResult.error.includes('SERVICE_DISABLED') ||
            googleResult.error.includes('REQUEST_DENIED') ||
            googleResult.error.includes('not been used')
          ) {
            googleDisabledRef.current = true;
          }

          const hint = googleResult.error.includes('SERVICE_DISABLED') || googleResult.error.includes('not been used')
            ? 'Enable Places API (New) in Google Cloud, then retry.'
            : googleResult.error.includes('REQUEST_DENIED')
              ? 'Check API key restrictions and allow localhost:5173 as an HTTP referrer.'
              : '';

          setSearchError(hint ? `${hint}` : 'Google Places search failed.');
          setIsSearching(false);
          return;
        }

        feature = googleResult.feature;
      }

      if (!feature?.center) {
        feature = await searchWithMapbox(trimmedQuery, controller.signal);
      }

      if (controller.signal.aborted) return;

      if (!feature?.center) {
        setSearchError('No location found. Try a more specific search.');
        setIsSearching(false);
        return;
      }

      searchCacheRef.current.set(cacheKey, { feature, timestamp: Date.now() });
      flyToFeature(feature);
    } catch (error) {
      if (error.name === 'AbortError') return;
      setSearchError('Could not search this location right now.');
    } finally {
      if (searchAbortRef.current === controller) {
        searchAbortRef.current = null;
        setIsSearching(false);
      }
    }
  };

  const handleSearchLauncherClick = () => {
    setSearchError('');
    setActiveLocationIndex(0);
    setManualSelection(false);
    setIsSearchOpen(true);
  };

  const returnToInstructionsView = useCallback(() => {
    const map = mapRef.current;
    if (!map) {
      if (onReturnToInstructions) onReturnToInstructions();
      return;
    }

    map.stop();

    setSearchError('');
    setQuery('');
    setDynamicSuggestions([]);
    setActiveLocationIndex(0);
    setManualSelection(false);
    setIsSearchOpen(false);
    const transitionId = cameraTransitionRef.current + 1;
    cameraTransitionRef.current = transitionId;
    spinEnabledRef.current = false;
    userInteractingRef.current = false;

    map.setProjection('globe');

    map.flyTo({
      center: initialViewRef.current.center,
      zoom: initialViewRef.current.zoom,
      pitch: initialViewRef.current.pitch,
      bearing: initialViewRef.current.bearing,
      padding: initialGlobePaddingRef.current,
      duration: 1700,
      easing: (t) => 1 - Math.pow(1 - t, 3),
      essential: true
    });

    map.once('moveend', () => {
      if (cameraTransitionRef.current !== transitionId) return;
      spinEnabledRef.current = true;
    });

    viewModeRef.current = 'instructions';

    if (onReturnToInstructions) onReturnToInstructions();
  }, [onReturnToInstructions]);

  const returnToBrowseGlobeView = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;

    map.stop();

    setSearchError('');
    setQuery('');
    setDynamicSuggestions([]);
    setActiveLocationIndex(0);
    setManualSelection(false);
    setIsSearchOpen(false);

    const transitionId = cameraTransitionRef.current + 1;
    cameraTransitionRef.current = transitionId;

    spinEnabledRef.current = false;
    userInteractingRef.current = false;

    map.setProjection('globe');

    map.flyTo({
      center: initialViewRef.current.center,
      zoom: 2.14,
      pitch: 0,
      bearing: 0,
      padding: centeredGlobePaddingRef.current,
      duration: 1550,
      easing: (t) => 1 - Math.pow(1 - t, 3),
      essential: true
    });

    map.once('moveend', () => {
      if (cameraTransitionRef.current !== transitionId) return;
      spinEnabledRef.current = true;
    });

    viewModeRef.current = 'browse';
  }, []);

  const handleSpotlightKeyDown = (event) => {
    if (!displayResults.length) return;

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setManualSelection(true);
      setActiveLocationIndex((index) => (index + 1) % displayResults.length);
      return;
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setManualSelection(true);
      setActiveLocationIndex((index) =>
        index === 0 ? displayResults.length - 1 : index - 1
      );
      return;
    }

    if (event.key === 'Enter' && !query.trim()) {
      const activeResult = displayResults[activeLocationIndex];
      if (activeResult) {
        event.preventDefault();
        void selectResult(activeResult);
      }
    }
  };

  useEffect(() => {
    searchOpenRef.current = isSearchOpen;

    if (isSearchOpen) {
      searchboxSessionTokenRef.current = newSearchSessionToken();
    } else {
      searchboxSessionTokenRef.current = '';
    }
  }, [isSearchOpen]);

  useEffect(() => {
    if (!isSearchOpen || !renderSearch) return;

    const frame = requestAnimationFrame(() => {
      searchInputRef.current?.focus();
      searchInputRef.current?.select();
    });

    return () => cancelAnimationFrame(frame);
  }, [isSearchOpen, renderSearch]);

  useEffect(() => {
    if (openAnimationTimerRef.current) {
      clearTimeout(openAnimationTimerRef.current);
      openAnimationTimerRef.current = null;
    }

    if (closeAnimationTimerRef.current) {
      clearTimeout(closeAnimationTimerRef.current);
      closeAnimationTimerRef.current = null;
    }

    if (isSearchOpen) {
      setSearchAnimatedIn(false);
      setRenderSearch(true);

      openAnimationTimerRef.current = setTimeout(() => {
        setSearchAnimatedIn(true);
        openAnimationTimerRef.current = null;
      }, 24);

      return () => {
        if (openAnimationTimerRef.current) {
          clearTimeout(openAnimationTimerRef.current);
          openAnimationTimerRef.current = null;
        }
      };
    }

    setSearchAnimatedIn(false);
    closeAnimationTimerRef.current = setTimeout(() => {
      setRenderSearch(false);
      closeAnimationTimerRef.current = null;
    }, 240);

    return () => {
      if (closeAnimationTimerRef.current) {
        clearTimeout(closeAnimationTimerRef.current);
        closeAnimationTimerRef.current = null;
      }
    };
  }, [isSearchOpen]);

  useEffect(() => {
    if (onboardingPhase === 'visible') {
      hasCompletedOnboardingRef.current = false;
      viewModeRef.current = 'instructions';
    }
  }, [onboardingPhase]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (onboardingPhase !== 'exiting') return;
    if (hasCompletedOnboardingRef.current) return;

    hasCompletedOnboardingRef.current = true;
    const finalZoom = 2.14;
    map.setProjection('globe');

    map.easeTo({
      padding: centeredGlobePaddingRef.current,
      zoom: finalZoom,
      pitch: 0,
      bearing: map.getBearing(),
      duration: 980,
      easing: (t) => 1 - Math.pow(1 - t, 3),
      essential: true
    });

    const onMoveEnd = () => {
      map.setPadding(centeredGlobePaddingRef.current);
      viewModeRef.current = 'browse';
    };

    map.once('moveend', onMoveEnd);

    return () => {
      map.off('moveend', onMoveEnd);
    };
  }, [onboardingPhase]);

  useEffect(() => {
    let cancelled = false;

    const loadSuggestions = async () => {
      const trimmedQuery = query.trim();
      const cacheKey = trimmedQuery.toLowerCase();

      if (!isSearchOpen || trimmedQuery.length < 2) {
        if (!cancelled) {
          setDynamicSuggestions([]);
          setIsSuggesting(false);
        }
        if (suggestionAbortRef.current) {
          suggestionAbortRef.current.abort();
          suggestionAbortRef.current = null;
        }
        return;
      }

      const cachedSuggestions = suggestionsCacheRef.current.get(cacheKey);
      if (cachedSuggestions && Date.now() - cachedSuggestions.timestamp < CACHE_TTL_MS) {
        if (!cancelled) {
          setDynamicSuggestions(cachedSuggestions.items);
          setIsSuggesting(false);
        }
        return;
      }

      if (suggestionAbortRef.current) {
        suggestionAbortRef.current.abort();
      }
      const controller = new AbortController();
      suggestionAbortRef.current = controller;

      setIsSuggesting(true);
      await new Promise((resolve) => setTimeout(resolve, 140));
      if (cancelled) return;

      const suggestions = await fetchDynamicSuggestions(trimmedQuery, controller.signal);
      if (cancelled) return;

      if (suggestionAbortRef.current === controller) {
        suggestionAbortRef.current = null;
      }

      suggestionsCacheRef.current.set(cacheKey, { items: suggestions, timestamp: Date.now() });

      setDynamicSuggestions(suggestions);
      setIsSuggesting(false);
    };

    loadSuggestions();

    return () => {
      cancelled = true;
    };
  }, [query, isSearchOpen]);

  useEffect(() => {
    mapRef.current = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: 'mapbox://styles/mapbox/streets-v12',
      center: initialViewRef.current.center,
      zoom: initialViewRef.current.zoom,
      minZoom: initialViewRef.current.zoom,
      projection: 'globe',
      fadeDuration: 0
    });

    mapRef.current.setPadding(initialGlobePaddingRef.current);

    // Hard-enforce minimum zoom for globe projection
    mapRef.current.on('zoom', () => {
      if (mapRef.current.getZoom() < initialViewRef.current.zoom) {
        mapRef.current.setZoom(initialViewRef.current.zoom);
      }
    });

    // --- Globe rotation ---
    const degreesPerSecond = 360 / 50; // full rotation in 50 seconds
    let lastTimestamp = null;
    let animationId = null;

    function spinGlobe(timestamp) {
      if (!userInteractingRef.current && spinEnabledRef.current && mapRef.current) {
        if (lastTimestamp === null) {
          lastTimestamp = timestamp;
        }

        const delta = (timestamp - lastTimestamp) / 1000;
        if (delta >= 1 / 24) {
          const projectionName = mapRef.current.getProjection()?.name;

          if (projectionName === 'globe') {
            const center = mapRef.current.getCenter();
            center.lng -= degreesPerSecond * delta;
            mapRef.current.setCenter(center);
          } else {
            const nextBearing = mapRef.current.getBearing() + degreesPerSecond * delta;
            mapRef.current.setBearing(nextBearing);
          }

          lastTimestamp = timestamp;
        }
      } else {
        lastTimestamp = null;
      }
      animationId = requestAnimationFrame(spinGlobe);
    }

    // Pause rotation on user interaction
    mapRef.current.on('mousedown', () => { userInteractingRef.current = true; });
    mapRef.current.on('dragstart', () => { userInteractingRef.current = true; });
    mapRef.current.on('mouseup', () => { userInteractingRef.current = false; });
    mapRef.current.on('dragend', () => { userInteractingRef.current = false; });
    mapRef.current.on('touchstart', () => { userInteractingRef.current = true; });
    mapRef.current.on('touchend', () => { userInteractingRef.current = false; });

    animationId = requestAnimationFrame(spinGlobe);

    const handleEscapeToGlobe = (event) => {
      const isCommandK = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k';

      if (isCommandK) {
        event.preventDefault();
        const nextOpen = !searchOpenRef.current;
        setSearchError('');
        setIsSearchOpen(nextOpen);
        setActiveLocationIndex(0);
        setManualSelection(false);

        if (suggestionAbortRef.current) {
          suggestionAbortRef.current.abort();
          suggestionAbortRef.current = null;
        }

        if (!nextOpen) {
          setQuery('');
          setDynamicSuggestions([]);
        }
        return;
      }

      if (event.key !== 'Escape') return;

      if (searchOpenRef.current) {
        setSearchError('');
        setIsSearchOpen(false);
        setDynamicSuggestions([]);
        return;
      }

      if (viewModeRef.current === 'browse') {
        returnToInstructionsView();
        return;
      }

      returnToBrowseGlobeView();
    };

    window.addEventListener('keydown', handleEscapeToGlobe);

    mapRef.current.on('load', () => {
      add3DBuildingsLayer();

      // Control label visibility by zoom level
      const layers = mapRef.current.getStyle().layers;

      layers.forEach((layer) => {
        if (layer.type !== 'symbol') return;
        const id = layer.id;

        // Keep continent labels visible at all zooms
        if (id.includes('continent')) return;

        // Country labels: only show at zoom 4+
        if (id.includes('country-label')) {
          mapRef.current.setLayerZoomRange(id, 4, 24);
          return;
        }

        // State/province labels: only show at zoom 5+
        if (id.includes('state-label') || id.includes('province')) {
          mapRef.current.setLayerZoomRange(id, 5, 24);
          return;
        }

        // City/town/village/settlement labels: only show at zoom 6+
        if (
          id.includes('settlement') ||
          id.includes('city') ||
          id.includes('town') ||
          id.includes('village') ||
          id.includes('place-label')
        ) {
          mapRef.current.setLayerZoomRange(id, 6, 24);
          return;
        }
      });

    });

    return () => {
      window.removeEventListener('keydown', handleEscapeToGlobe);
      if (suggestionAbortRef.current) suggestionAbortRef.current.abort();
      if (searchAbortRef.current) searchAbortRef.current.abort();
      if (openAnimationTimerRef.current) clearTimeout(openAnimationTimerRef.current);
      if (closeAnimationTimerRef.current) clearTimeout(closeAnimationTimerRef.current);
      if (animationId) cancelAnimationFrame(animationId);
      mapRef.current?.remove();
    };
  }, [returnToBrowseGlobeView, returnToInstructionsView]);

  return (
    <div className="map-wrapper">
      {onboardingPhase === 'done' && !renderSearch ? (
        <button
          className="map-back-button"
          type="button"
          onClick={returnToInstructionsView}
          aria-label="Return to instructions"
        >
          <ArrowLeft className="map-back-button__icon" aria-hidden="true" />
          <span className="map-back-button__text">Back</span>
        </button>
      ) : null}
      {onboardingPhase === 'done' && !renderSearch ? (
        <div className="map-search-launcher-stack">
          <button className="map-search-launcher" type="button" onClick={handleSearchLauncherClick} aria-label="Open search">
            <span className="map-search-launcher__text">Search</span>
            <span className="map-search-launcher__icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="7" />
                <path d="M20 20l-3.5-3.5" />
              </svg>
            </span>
          </button>
          <button
            className="map-search-shortcut"
            type="button"
            onClick={handleSearchLauncherClick}
            aria-label="Open search with keyboard shortcut"
          >
            ⌘K
          </button>
        </div>
      ) : null}
      {renderSearch ? (
        <div className={`spotlight ${searchAnimatedIn ? 'is-visible' : 'is-hidden'}`}>
          <form className="spotlight__panel" onSubmit={searchLocation} onKeyDown={handleSpotlightKeyDown}>
            <div className="spotlight__top">
              <span className="spotlight__icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="7" />
                  <path d="M20 20l-3.5-3.5" />
                </svg>
              </span>
              <input
                ref={searchInputRef}
                className="spotlight__input"
                type="text"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setActiveLocationIndex(0);
                  setManualSelection(false);
                }}
                placeholder="Search location or city"
                aria-label="Search location"
                autoComplete="off"
              />
              <span className="spotlight__hint">
                {isSearching ? <span>Searching...</span> : <span>Enter</span>}
                <span className="spotlight__arrow">→</span>
              </span>
            </div>

            <div className="spotlight__divider" />

            <div ref={resultsListRef} className="spotlight__list" role="listbox" aria-label="Suggested locations">
              {displayResults.map((result, index) => (
                <button
                  key={result.key}
                  data-result-index={index}
                  className={`spotlight__item ${index === activeLocationIndex ? 'is-active' : ''}`}
                  type="button"
                  onMouseEnter={() => {
                    setManualSelection(true);
                    setActiveLocationIndex(index);
                  }}
                  onClick={() => selectResult(result)}
                >
                  <span className="spotlight__flag" aria-hidden="true">
                    {result.kind === 'quick'
                      ? result.location.flag
                      : result.kind === 'landmark'
                        ? result.landmark.flag
                        : result.suggestion.flag}
                  </span>
                  <span className="spotlight__primary">
                    {result.kind === 'quick'
                      ? result.location.name
                      : result.kind === 'landmark'
                        ? result.landmark.name
                        : result.suggestion.name}
                  </span>
                  <span className="spotlight__secondary">
                    {result.kind === 'quick'
                      ? result.location.subtitle
                      : result.kind === 'landmark'
                        ? result.landmark.subtitle
                        : result.suggestion.subtitle}
                  </span>
                </button>
              ))}
              {isSuggesting ? (
                <div className="spotlight__empty">Searching places...</div>
              ) : null}
              {!displayResults.length && !isSuggesting ? (
                <div className="spotlight__empty">No quick match. Press Enter to search globally.</div>
              ) : null}
            </div>
            {searchError ? <div className="spotlight__error">{searchError}</div> : null}
          </form>
        </div>
      ) : null}
      <div id="map" ref={mapContainerRef} style={{ height: '100%' }} />
    </div>
  );
};

export default MapboxExample;
