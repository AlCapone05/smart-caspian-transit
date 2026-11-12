import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

export type VesselMark = {
  id: string;
  name: string;
  status: string;
  status_label?: string;
  heading_deg: number;
  speed_knots?: number;
  progress_pct?: number;
  lat?: number;
  lon?: number;
  route_label?: string;
  shipment_id?: string | null;
  origin_port_id?: string;
  destination_port_id?: string;
  selected_alternative_id?: string | null;
  route_path?: Array<{ lat: number; lon: number }>;
  waypoints?: Array<{ lat: number; lon: number }>;
  storm_alternatives?: Array<{
    id: string;
    title: string;
    subtitle: string;
    path: Array<{ lat: number; lon: number }>;
    feasible: boolean;
    storm_safe: boolean;
    eta_delta_hours: number;
    cost_delta_pct: number;
  }>;
};

export type AlertMark = {
  id: string;
  title?: string;
  detail?: string;
  severity: string;
  kind?: string;
  wind_ms?: number;
  lat?: number;
  lon?: number;
  affected_vessel_ids?: string[];
};

export type StormCell = {
  id: string;
  name: string;
  lat: number;
  lon: number;
  wind_ms: number;
  severity: number;
  radius_km: number;
  kind: string;
  heading_deg?: number;
};

type PortMark = {
  id: string;
  name: string;
  lat?: number;
  lon?: number;
};

type Corridor = {
  id: string;
  path: Array<{ lat: number; lon: number }>;
  waypoints?: Array<{ lat: number; lon: number }>;
};

const CASPIAN_CENTER: L.LatLngExpression = [41.6, 50.2];
const DEFAULT_ZOOM = 6;
// Tight Caspian basin — without western countries on the edge
const CASPIAN_BOUNDS = L.latLngBounds([36.6, 47.2], [46.8, 54.4]);

const FALLBACK_PORTS: PortMark[] = [
  { id: "port_astrakhan", name: "Астрахань", lat: 46.35, lon: 48.04 },
  { id: "port_makhachkala", name: "Махачкала", lat: 42.98, lon: 47.5 },
  { id: "port_aktau", name: "Актау", lat: 43.65, lon: 51.17 },
  { id: "port_baku", name: "Баку", lat: 40.38, lon: 49.87 },
  { id: "port_anzali", name: "Энзели", lat: 37.47, lon: 49.46 },
];

type WindParticle = { x: number; y: number; age: number; life: number };

function vesselIcon(selected: boolean, heading: number) {
  return L.divIcon({
    className: "sct-vessel-icon",
    html: `<div class="sct-vessel-mark ${selected ? "is-selected" : ""}" style="transform:rotate(${heading}deg)"></div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });
}

function cityIcon(name: string) {
  return L.divIcon({
    className: "sct-city-icon",
    html: `<div class="sct-city-mark"><span class="dot"></span><span class="label">${name}</span></div>`,
    iconSize: [120, 28],
    iconAnchor: [8, 14],
  });
}

function waypointIcon() {
  return L.divIcon({
    className: "sct-wp-icon",
    html: `<div class="sct-wp-mark"></div>`,
    iconSize: [8, 8],
    iconAnchor: [4, 4],
  });
}

type BaseKind = "satellite" | "scheme";

function createBaseLayers(map: L.Map) {
  const satellite = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { attribution: "Esri", maxZoom: 18, maxNativeZoom: 18 }
  );
  // Уличная схема Esri — контрастная, Каспий читается (Carto light давал белый кадр)
  const scheme = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    {
      attribution: "Esri",
      maxZoom: 18,
      maxNativeZoom: 18,
      className: "sct-scheme-tiles",
    }
  );
  // Fallback: OSM
  const schemeFallback = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "OSM",
    maxZoom: 18,
    maxNativeZoom: 19,
    className: "sct-scheme-tiles",
  });

  let active: BaseKind = "satellite";
  let schemeLayer: L.TileLayer = scheme;
  satellite.addTo(map);

  const apply = (kind: BaseKind) => {
    if (kind === active && map.hasLayer(kind === "satellite" ? satellite : schemeLayer)) {
      return kind;
    }
    if (map.hasLayer(satellite)) map.removeLayer(satellite);
    if (map.hasLayer(scheme)) map.removeLayer(scheme);
    if (map.hasLayer(schemeFallback)) map.removeLayer(schemeFallback);
    if (kind === "satellite") {
      satellite.addTo(map);
      satellite.bringToBack();
    } else {
      schemeLayer = scheme;
      schemeLayer.addTo(map);
      schemeLayer.bringToBack();
      // If tiles error out, swap to OSM once
      let errors = 0;
      const onErr = () => {
        errors += 1;
        if (errors < 4 || schemeLayer === schemeFallback) return;
        map.removeLayer(scheme);
        schemeLayer = schemeFallback;
        schemeFallback.addTo(map);
        schemeFallback.bringToBack();
        scheme.off("tileerror", onErr);
      };
      scheme.on("tileerror", onErr);
    }
    active = kind;
    // Keep overlay drawings above basemap
    map.getPanes().overlayPane.style.zIndex = "400";
    map.getPanes().tilePane.style.zIndex = "200";
    return active;
  };

  return {
    apply,
    getActive: () => active,
    layers: { satellite, scheme, schemeFallback },
  };
}

/** Minimal full-map wind field (Google-like sparse streaks). */
function createWindField(map: L.Map) {
  const canvas = L.DomUtil.create("canvas", "sct-weather-canvas") as HTMLCanvasElement;
  map.getPanes().overlayPane.appendChild(canvas);
  const ctx = canvas.getContext("2d")!;
  let particles: WindParticle[] = [];
  let stormBoost = 0;
  let windDeg = 215;
  let raf = 0;
  let last = performance.now();
  let running = true;
  let visible = true;
  let lightBasemap = false;

  const resize = () => {
    const size = map.getSize();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(size.x * dpr);
    canvas.height = Math.floor(size.y * dpr);
    canvas.style.width = `${size.x}px`;
    canvas.style.height = `${size.y}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    L.DomUtil.setPosition(canvas, map.containerPointToLayerPoint([0, 0]));
    const count = Math.round((size.x * size.y) / 9000);
    particles = Array.from({ length: Math.min(180, Math.max(70, count)) }, () => ({
      x: Math.random() * size.x,
      y: Math.random() * size.y,
      age: Math.random(),
      life: 1.2 + Math.random() * 1.8,
    }));
  };

  const frame = (now: number) => {
    if (!running) return;
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    const size = map.getSize();
    ctx.clearRect(0, 0, size.x, size.y);
    if (!visible || lightBasemap) {
      raf = requestAnimationFrame(frame);
      return;
    }
    const rad = (windDeg * Math.PI) / 180;
    const speed = (28 + stormBoost * 22) * dt;

    particles.forEach((p) => {
      p.age += dt / p.life;
      p.x += Math.cos(rad) * speed * 55;
      p.y += Math.sin(rad) * speed * 55;
      if (p.age >= 1 || p.x < -20 || p.y < -20 || p.x > size.x + 20 || p.y > size.y + 20) {
        p.x = Math.random() * size.x;
        p.y = Math.random() * size.y;
        p.age = 0;
      }
      const a = Math.sin(Math.min(1, p.age) * Math.PI) * (0.22 + stormBoost * 0.18);
      ctx.strokeStyle = `rgba(255,255,255,${a})`;
      ctx.lineWidth = 1;
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(p.x, p.y);
      ctx.lineTo(p.x + Math.cos(rad) * 10, p.y + Math.sin(rad) * 10);
      ctx.stroke();
    });
    raf = requestAnimationFrame(frame);
  };

  resize();
  map.on("move resize zoom viewreset", resize);
  raf = requestAnimationFrame(frame);

  return {
    setStormLevel(level: number, deg?: number) {
      stormBoost = Math.max(0, Math.min(1, level));
      if (deg != null) windDeg = deg;
    },
    setBasemapMode(mode: BaseKind) {
      lightBasemap = mode === "scheme";
      visible = mode === "satellite";
      canvas.style.opacity = mode === "satellite" ? "1" : "0";
    },
    destroy() {
      running = false;
      cancelAnimationFrame(raf);
      map.off("move resize zoom viewreset", resize);
      canvas.remove();
    },
  };
}

export function LiveCaspianMap({
  vessels = [],
  alerts = [],
  stormCells = [],
  ports = [],
  corridors = [],
  selectedId,
  previewPath,
  variant = "compact",
  showLegend = true,
  onSelect,
  onPortSelect,
  onAlertSelect,
}: {
  vessels?: VesselMark[];
  alerts?: AlertMark[];
  stormCells?: StormCell[];
  ports?: PortMark[];
  corridors?: Corridor[];
  selectedId?: string | null;
  previewPath?: Array<{ lat: number; lon: number }> | null;
  variant?: "compact" | "expanded";
  showLegend?: boolean;
  onSelect?: (id: string) => void;
  onPortSelect?: (id: string, name: string) => void;
  onAlertSelect?: (id: string) => void;
}) {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const baseLayerRef = useRef<L.LayerGroup | null>(null);
  const vesselLayerRef = useRef<L.LayerGroup | null>(null);
  const vesselMarkersRef = useRef<
    Map<
      string,
      {
        marker: L.Marker;
        from: L.LatLng;
        to: L.LatLng;
        heading: number;
        startedAt: number;
        duration: number;
      }
    >
  >(new Map());
  const animRef = useRef(0);
  const windRef = useRef<ReturnType<typeof createWindField> | null>(null);
  const baseCtlRef = useRef<ReturnType<typeof createBaseLayers> | null>(null);
  const [ready, setReady] = useState(false);
  const [baseKind, setBaseKind] = useState<BaseKind>("satellite");

  const portList = useMemo(() => {
    if (ports.length) return ports;
    return FALLBACK_PORTS;
  }, [ports]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || mapRef.current) return;

    const map = L.map(el, {
      center: CASPIAN_CENTER,
      zoom: variant === "expanded" ? 6 : 6,
      minZoom: 5,
      maxZoom: 12,
      maxBounds: CASPIAN_BOUNDS.pad(0.12),
      maxBoundsViscosity: 0.85,
      zoomControl: true,
      attributionControl: false,
    });

    baseCtlRef.current = createBaseLayers(map);
    baseLayerRef.current = L.layerGroup().addTo(map);
    vesselLayerRef.current = L.layerGroup().addTo(map);
    windRef.current = createWindField(map);
    mapRef.current = map;
    setBaseKind("satellite");
    setReady(true);

    const refreshSize = () => {
      if (!mapRef.current) return;
      mapRef.current.invalidateSize({ animate: false });
    };
    refreshSize();
    const timers = [50, 200, 450, 900].map((ms) => window.setTimeout(refreshSize, ms));
    window.addEventListener("resize", refreshSize);
    const ro =
      typeof ResizeObserver !== "undefined" && wrapRef.current
        ? new ResizeObserver(() => refreshSize())
        : null;
    if (wrapRef.current && ro) ro.observe(wrapRef.current);

    const tickAnim = (now: number) => {
      vesselMarkersRef.current.forEach((state) => {
        const t = Math.min(1, (now - state.startedAt) / state.duration);
        const ease = 1 - (1 - t) * (1 - t);
        const lat = state.from.lat + (state.to.lat - state.from.lat) * ease;
        const lon = state.from.lng + (state.to.lng - state.from.lng) * ease;
        state.marker.setLatLng([lat, lon]);
      });
      animRef.current = requestAnimationFrame(tickAnim);
    };
    animRef.current = requestAnimationFrame(tickAnim);

    return () => {
      timers.forEach((t) => window.clearTimeout(t));
      window.removeEventListener("resize", refreshSize);
      ro?.disconnect();
      cancelAnimationFrame(animRef.current);
      windRef.current?.destroy();
      windRef.current = null;
      vesselMarkersRef.current.clear();
      baseCtlRef.current = null;
      map.remove();
      mapRef.current = null;
      baseLayerRef.current = null;
      vesselLayerRef.current = null;
      setReady(false);
    };
  }, [variant]);

  const switchBase = (kind: BaseKind) => {
    baseCtlRef.current?.apply(kind);
    windRef.current?.setBasemapMode(kind);
    setBaseKind(kind);
    // Force redraw after basemap swap
    window.setTimeout(() => {
      mapRef.current?.invalidateSize({ animate: false });
      // ensure tiles refresh if cached blank
      mapRef.current?.eachLayer((layer) => {
        const tl = layer as L.TileLayer;
        if (typeof tl.redraw === "function") tl.redraw();
      });
    }, 40);
  };

  // Corridors, storms, ports, preview — redraw when data changes
  useEffect(() => {
    if (!ready || !mapRef.current || !baseLayerRef.current) return;
    const layer = baseLayerRef.current;
    layer.clearLayers();

    const cells =
      stormCells.length > 0
        ? stormCells
        : alerts
            .filter((a) => a.lat != null && a.lon != null && (a.severity === "high" || a.severity === "medium"))
            .map((a) => ({
              id: a.id,
              name: a.title || "Шторм",
              lat: a.lat as number,
              lon: a.lon as number,
              wind_ms: a.wind_ms || 12,
              severity: a.severity === "high" ? 0.85 : 0.6,
              radius_km: 70 + (a.wind_ms || 10) * 2,
              kind: a.kind || "storm",
            }));

    const avgWind = cells.length
      ? cells.reduce((s, c) => s + (c.wind_ms || 0), 0) / cells.length
      : 10;
    const strong = cells.filter((c) => c.severity >= 0.72).length;
    windRef.current?.setStormLevel(
      strong ? Math.min(1, 0.35 + strong * 0.22) : 0.12,
      195 + avgWind
    );

    cells.forEach((c) => {
      const hot = c.severity >= 0.72;
      L.circle([c.lat, c.lon], {
        radius: Math.max(45000, c.radius_km * 1000),
        color: hot ? "#9a7a62" : "#b8a882",
        weight: 1.2,
        fillColor: hot ? "#9a7a62" : "#b8a882",
        fillOpacity: hot ? 0.16 : 0.1,
        interactive: true,
        className: "sct-live-storm",
      })
        .on("click", () => onAlertSelect?.(c.id))
        .bindTooltip(
          `${c.name}<br/>${Math.round(c.wind_ms)} м/с · R≈${Math.round(c.radius_km)} км · live`,
          { sticky: true }
        )
        .addTo(layer);
    });

    const paths =
      corridors.length > 0
        ? corridors
        : vessels
            .filter((v) => v.route_path && v.route_path.length >= 2)
            .map((v) => ({
              id: v.id,
              path: v.route_path!,
              waypoints: v.waypoints,
            }));

    paths.forEach((c) => {
      if (!c.path || c.path.length < 2) return;
      const latlngs = c.path.map((p) => [p.lat, p.lon] as L.LatLngExpression);
      // Outline + cyan corridor so the scheme stays visible on satellite/light tiles
      L.polyline(latlngs, {
        color: "#0b1f44",
        weight: 6,
        opacity: 0.45,
        lineJoin: "round",
        lineCap: "round",
        interactive: false,
        className: "sct-corridor-outline",
      }).addTo(layer);
      L.polyline(latlngs, {
        color: "#0ea5d8",
        weight: 3.2,
        opacity: 0.95,
        lineJoin: "round",
        lineCap: "round",
        interactive: false,
        className: "sct-corridor-line",
      }).addTo(layer);
      (c.waypoints || c.path.slice(1, -1)).forEach((wp) => {
        L.marker([wp.lat, wp.lon], { icon: waypointIcon(), interactive: false, zIndexOffset: 150 }).addTo(
          layer
        );
      });
    });

    if (previewPath && previewPath.length >= 2) {
      L.polyline(
        previewPath.map((p) => [p.lat, p.lon] as L.LatLngExpression),
        {
          color: "#6f3cc9",
          weight: 3.5,
          opacity: 0.95,
          dashArray: "10 7",
          interactive: false,
        }
      ).addTo(layer);
    }

    portList.forEach((p) => {
      if (p.lat == null || p.lon == null) return;
      const name = p.name.replace(" (демо)", "");
      const m = L.marker([p.lat, p.lon], { icon: cityIcon(name), zIndexOffset: 250 });
      m.on("click", () => onPortSelect?.(p.id, name));
      m.addTo(layer);
    });
  }, [
    ready,
    alerts,
    stormCells,
    portList,
    corridors,
    vessels,
    previewPath,
    onPortSelect,
    onAlertSelect,
  ]);

  // Vessel markers — keep instances and glide between ticks
  useEffect(() => {
    if (!ready || !vesselLayerRef.current) return;
    const layer = vesselLayerRef.current;
    const store = vesselMarkersRef.current;
    const seen = new Set<string>();
    const now = performance.now();

    vessels.forEach((v) => {
      if (v.lat == null || v.lon == null) return;
      seen.add(v.id);
      const selected = v.id === selectedId;
      const target = L.latLng(v.lat, v.lon);
      const existing = store.get(v.id);
      if (existing) {
        const cur = existing.marker.getLatLng();
        existing.from = L.latLng(cur.lat, cur.lng);
        existing.to = target;
        existing.heading = v.heading_deg || existing.heading;
        existing.startedAt = now;
        existing.duration = 3800;
        existing.marker.setIcon(vesselIcon(selected, existing.heading));
        existing.marker.setZIndexOffset(selected ? 900 : 600);
        existing.marker.setTooltipContent(
          `<strong>${v.name}</strong><br/>${v.route_label || ""} · ${v.progress_pct ?? 0}%`
        );
        return;
      }
      const marker = L.marker(target, {
        icon: vesselIcon(selected, v.heading_deg || 0),
        zIndexOffset: selected ? 900 : 600,
      });
      marker.bindTooltip(
        `<strong>${v.name}</strong><br/>${v.route_label || ""} · ${v.progress_pct ?? 0}%`,
        { direction: "top", opacity: 0.95 }
      );
      marker.on("click", () => onSelect?.(v.id));
      marker.addTo(layer);
      store.set(v.id, {
        marker,
        from: target,
        to: target,
        heading: v.heading_deg || 0,
        startedAt: now,
        duration: 1,
      });
    });

    store.forEach((state, id) => {
      if (seen.has(id)) return;
      layer.removeLayer(state.marker);
      store.delete(id);
    });
  }, [ready, vessels, selectedId, onSelect]);

  return (
    <div
      className={`leaflet-caspian-wrap is-${variant} base-${baseKind}`}
      ref={wrapRef}
    >
      <div
        ref={containerRef}
        className={`leaflet-caspian is-${variant} base-${baseKind}`}
        role="img"
        aria-label="Карта Каспийского коридора"
      />
      <div className="map-base-toggle" role="group" aria-label="Подложка карты">
        <button
          type="button"
          className={baseKind === "satellite" ? "on" : ""}
          onClick={() => switchBase("satellite")}
        >
          Спутник
        </button>
        <button
          type="button"
          className={baseKind === "scheme" ? "on" : ""}
          onClick={() => switchBase("scheme")}
        >
          Схема
        </button>
      </div>
      {showLegend && (
        <div className="leaflet-legend">
          <span>
            <i className="leg-port" /> Город / порт
          </span>
          <span>
            <i className="leg-wp" /> Точка в море
          </span>
          <span>
            <i className="leg-vessel" /> Судно на линии
          </span>
          <span>
            <i className="leg-wind" /> Ветер по карте
          </span>
          <span>
            <i className="leg-storm" /> Зона шторма
          </span>
        </div>
      )}
    </div>
  );
}
