import React, { useEffect, useRef } from 'react';
import mapboxgl from 'mapbox-gl';

import 'mapbox-gl/dist/mapbox-gl.css';

const MapboxExample = () => {
  const mapContainerRef = useRef();
  const mapRef = useRef();

  useEffect(() => {
    mapboxgl.accessToken = 'pk.eyJ1IjoicG1hcnRoaSIsImEiOiJjbWxjbm1qYXQxMWRlM2Zwb2J1YThhODcwIn0.pWp7Uy5gzAy7I_0r7HAujQ';

    mapRef.current = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: 'mapbox://styles/mapbox/streets-v12',
      center: [-100.486052, 30],
      zoom: 2.15,
      minZoom: 2.15,
      projection: 'globe'
    });

    // Hard-enforce minimum zoom for globe projection
    mapRef.current.on('zoom', () => {
      if (mapRef.current.getZoom() < 2.15) {
        mapRef.current.setZoom(2.15);
      }
    });

    // --- Globe rotation ---
    const degreesPerSecond = 360 / 56.25; // full rotation in 56.25 seconds
    let userInteracting = false;
    let lastTimestamp = null;
    let animationId = null;

    function spinGlobe(timestamp) {
      if (!userInteracting && mapRef.current) {
        if (lastTimestamp !== null) {
          const delta = (timestamp - lastTimestamp) / 1000;
          const center = mapRef.current.getCenter();
          center.lng -= degreesPerSecond * delta;
          mapRef.current.setCenter(center);
        }
        lastTimestamp = timestamp;
      } else {
        lastTimestamp = null;
      }
      animationId = requestAnimationFrame(spinGlobe);
    }

    // Pause rotation on user interaction
    mapRef.current.on('mousedown', () => { userInteracting = true; });
    mapRef.current.on('dragstart', () => { userInteracting = true; });
    mapRef.current.on('mouseup', () => { userInteracting = false; });
    mapRef.current.on('dragend', () => { userInteracting = false; });
    mapRef.current.on('touchstart', () => { userInteracting = true; });
    mapRef.current.on('touchend', () => { userInteracting = false; });

    animationId = requestAnimationFrame(spinGlobe);

    let hoveredPolygonId = null;

    mapRef.current.on('load', () => {
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

      mapRef.current.addSource('states', {
        type: 'geojson',
        data: 'https://docs.mapbox.com/mapbox-gl-js/assets/us_states.geojson'
      });

      mapRef.current.addLayer({
        id: 'state-fills',
        type: 'fill',
        source: 'states',
        layout: {},
        paint: {
          'fill-color': '#627BC1',
          'fill-opacity': [
            'case',
            ['boolean', ['feature-state', 'hover'], false],
            1,
            0.5
          ]
        }
      });

      mapRef.current.addLayer({
        id: 'state-borders',
        type: 'line',
        source: 'states',
        layout: {},
        paint: {
          'line-color': '#627BC1',
          'line-width': 2
        }
      });

      mapRef.current.on('mousemove', 'state-fills', (e) => {
        if (e.features.length > 0) {
          if (hoveredPolygonId !== null) {
            mapRef.current.setFeatureState(
              { source: 'states', id: hoveredPolygonId },
              { hover: false }
            );
          }
          hoveredPolygonId = e.features[0].id;
          mapRef.current.setFeatureState(
            { source: 'states', id: hoveredPolygonId },
            { hover: true }
          );
        }
      });

      mapRef.current.on('mouseleave', 'state-fills', () => {
        if (hoveredPolygonId !== null) {
          mapRef.current.setFeatureState(
            { source: 'states', id: hoveredPolygonId },
            { hover: false }
          );
        }
        hoveredPolygonId = null;
      });
    });

    return () => {
      if (animationId) cancelAnimationFrame(animationId);
      mapRef.current?.remove();
    };
  }, []);

  return <div id="map" ref={mapContainerRef} style={{ height: '100%' }} />;
};

export default MapboxExample;
