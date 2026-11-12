import "dart:math" as math;
import "dart:ui" as ui;

import "package:flutter_map/flutter_map.dart";
import "package:latlong2/latlong.dart";
import "package:material_ui/material_ui.dart";

import "../theme.dart";

enum MapBaseKind { satellite, scheme }

const _fallbackPorts = <Map<String, dynamic>>[
  {"id": "port_astrakhan", "name": "Астрахань", "lat": 46.35, "lon": 48.04},
  {"id": "port_makhachkala", "name": "Махачкала", "lat": 42.98, "lon": 47.50},
  {"id": "port_aktau", "name": "Актау", "lat": 43.65, "lon": 51.17},
  {"id": "port_baku", "name": "Баку", "lat": 40.38, "lon": 49.87},
  {"id": "port_anzali", "name": "Энзели", "lat": 37.47, "lon": 49.46},
];

/// Same Caspian live map as the website: Esri tiles, storms, corridors, vessels.
class CaspianMapView extends StatefulWidget {
  const CaspianMapView({
    super.key,
    required this.vessels,
    required this.stormCells,
    required this.ports,
    this.corridors = const [],
    this.previewPath,
    this.selectedId,
    this.height = 320,
    this.showToggle = true,
    this.showLegend = false,
    this.onSelectVessel,
  });

  final List<Map<String, dynamic>> vessels;
  final List<Map<String, dynamic>> stormCells;
  final List<Map<String, dynamic>> ports;
  final List<Map<String, dynamic>> corridors;
  final List<Map<String, dynamic>>? previewPath;
  final String? selectedId;
  final double height;
  final bool showToggle;
  final bool showLegend;
  final ValueChanged<String>? onSelectVessel;

  @override
  State<CaspianMapView> createState() => _CaspianMapViewState();
}

class _CaspianMapViewState extends State<CaspianMapView>
    with SingleTickerProviderStateMixin {
  static const _center = LatLng(41.6, 50.2);
  // Шире, чем видимый Каспий — иначе зум упирается в constraint
  static final _bounds = LatLngBounds(
    const LatLng(35.2, 45.0),
    const LatLng(48.5, 56.0),
  );

  final MapController _map = MapController();
  final ValueNotifier<double> _zoom = ValueNotifier(6);
  MapBaseKind _base = MapBaseKind.satellite;
  late final AnimationController _pulse;

  @override
  void initState() {
    super.initState();
    _pulse = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2200),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulse.dispose();
    _zoom.dispose();
    _map.dispose();
    super.dispose();
  }

  String get _tileUrl => _base == MapBaseKind.satellite
      ? "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
      : "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}";

  void _zoomBy(double delta) {
    final next = (_zoom.value + delta).clamp(4.0, 14.0);
    final cam = _map.camera;
    _map.move(cam.center, next);
    _zoom.value = next;
  }

  List<LatLng> _pathOf(List<Map<String, dynamic>> pts) {
    final out = <LatLng>[];
    for (final p in pts) {
      final lat = (p["lat"] as num?)?.toDouble();
      final lon = (p["lon"] as num?)?.toDouble();
      if (lat != null && lon != null) out.add(LatLng(lat, lon));
    }
    return out;
  }

  List<Map<String, dynamic>> get _ports {
    final fromApi = widget.ports
        .where((p) => p["lat"] != null && p["lon"] != null)
        .toList();
    if (fromApi.length >= 3) return fromApi;
    // Merge: API first, then fill missing fallbacks by id
    final byId = {for (final p in fromApi) p["id"]?.toString(): p};
    for (final f in _fallbackPorts) {
      byId.putIfAbsent(f["id"]?.toString(), () => f);
    }
    return byId.values.whereType<Map<String, dynamic>>().toList();
  }

  @override
  Widget build(BuildContext context) {
    final corridors = widget.corridors.isNotEmpty
        ? widget.corridors
        : widget.vessels
            .where((v) => ((v["route_path"] as List?) ?? []).length >= 2)
            .map(
              (v) => {
                "id": v["id"],
                "path": v["route_path"],
                "waypoints": v["waypoints"],
              },
            )
            .toList();

    final outlinePolys = <Polyline>[];
    final linePolys = <Polyline>[];
    for (final c in corridors) {
      final pts = _pathOf(
        ((c["path"] as List?) ?? []).map((e) => (e as Map).cast<String, dynamic>()).toList(),
      );
      if (pts.length < 2) continue;
      outlinePolys.add(
        Polyline(
          points: pts,
          strokeWidth: 6,
          color: MoggnitColors.navy.withValues(alpha: 0.45),
        ),
      );
      linePolys.add(
        Polyline(
          points: pts,
          strokeWidth: 3.2,
          color: MoggnitColors.cyan.withValues(alpha: 0.95),
        ),
      );
    }

    final preview = widget.previewPath == null ? <LatLng>[] : _pathOf(widget.previewPath!);
    if (preview.length >= 2) {
      linePolys.add(
        Polyline(
          points: preview,
          strokeWidth: 3.5,
          color: const Color(0xFF2F6B8A),
          pattern: StrokePattern.dashed(segments: const [10, 7]),
        ),
      );
    }

    final circles = <CircleMarker>[];
    for (final cell in widget.stormCells) {
      final lat = (cell["lat"] as num?)?.toDouble();
      final lon = (cell["lon"] as num?)?.toDouble();
      if (lat == null || lon == null) continue;
      final sev = (cell["severity"] as num?)?.toDouble() ?? 0.5;
      final hot = sev >= 0.72;
      final rKm = (cell["radius_km"] as num?)?.toDouble() ?? 70;
      circles.add(
        CircleMarker(
          point: LatLng(lat, lon),
          radius: math.max(45000, rKm * 1000),
          useRadiusInMeter: true,
          color: (hot ? MoggnitColors.storm : MoggnitColors.stormSoft)
              .withValues(alpha: hot ? 0.18 : 0.11),
          borderStrokeWidth: 1.2,
          borderColor: (hot ? MoggnitColors.storm : MoggnitColors.stormSoft)
              .withValues(alpha: 0.7),
        ),
      );
    }

    final portDots = <Marker>[];
    final portLabels = <Marker>[];
    final sat = _base == MapBaseKind.satellite;
    for (final port in _ports) {
      final lat = (port["lat"] as num?)?.toDouble();
      final lon = (port["lon"] as num?)?.toDouble();
      if (lat == null || lon == null) continue;
      final name = (port["name"]?.toString() ?? "")
          .replaceAll(" (демо)", "")
          .replaceAll("Порт ", "");
      final point = LatLng(lat, lon);
      portDots.add(
        Marker(
          point: point,
          width: 18,
          height: 18,
          alignment: Alignment.center,
          child: Container(
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: MoggnitColors.navy,
              border: Border.all(color: Colors.white, width: 2.2),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.35),
                  blurRadius: 4,
                  offset: const Offset(0, 1),
                ),
              ],
            ),
          ),
        ),
      );
      portLabels.add(
        Marker(
          point: point,
          width: 88,
          height: 22,
          alignment: const Alignment(1.85, -1.35),
          child: Text(
            name,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: sat ? Colors.white : MoggnitColors.navy,
              fontSize: 11,
              fontWeight: FontWeight.w800,
              height: 1.1,
              shadows: sat
                  ? const [
                      Shadow(blurRadius: 6, color: Colors.black87),
                      Shadow(blurRadius: 2, color: Colors.black54),
                    ]
                  : const [
                      Shadow(blurRadius: 3, color: Colors.white70),
                    ],
            ),
          ),
        ),
      );
    }

    final vesselMarkers = <Marker>[];
    for (final v in widget.vessels) {
      final lat = (v["lat"] as num?)?.toDouble();
      final lon = (v["lon"] as num?)?.toDouble();
      if (lat == null || lon == null) continue;
      final id = v["id"]?.toString() ?? "";
      final selected = id == widget.selectedId;
      final heading = (v["heading_deg"] as num?)?.toDouble() ?? 0;
      vesselMarkers.add(
        Marker(
          point: LatLng(lat, lon),
          width: selected ? 36 : 28,
          height: selected ? 36 : 28,
          alignment: Alignment.center,
          child: GestureDetector(
            onTap: () => widget.onSelectVessel?.call(id),
            child: AnimatedBuilder(
              animation: _pulse,
              builder: (context, child) {
                return Transform.scale(
                  scale: selected ? 1 + _pulse.value * 0.06 : 1,
                  child: child,
                );
              },
              child: Transform.rotate(
                angle: heading * math.pi / 180,
                child: CustomPaint(
                  painter: _VesselPainter(
                    selected: selected,
                    color: selected ? MoggnitColors.cyan : MoggnitColors.navy,
                  ),
                ),
              ),
            ),
          ),
        ),
      );
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(18),
      child: SizedBox(
        height: widget.height,
        width: double.infinity,
        // Забираем жесты у ListView: pinch / drag по карте
        child: Listener(
          behavior: HitTestBehavior.opaque,
          child: Stack(
            children: [
              FlutterMap(
                mapController: _map,
                options: MapOptions(
                  initialCenter: _center,
                  initialZoom: 6,
                  minZoom: 4,
                  maxZoom: 14,
                  backgroundColor: const Color(0xFF1A3348),
                  cameraConstraint: CameraConstraint.containCenter(bounds: _bounds),
                  onPositionChanged: (camera, _) {
                    if ((_zoom.value - camera.zoom).abs() > 0.05) {
                      _zoom.value = camera.zoom;
                    }
                  },
                  interactionOptions: const InteractionOptions(
                    flags: InteractiveFlag.drag |
                        InteractiveFlag.flingAnimation |
                        InteractiveFlag.pinchMove |
                        InteractiveFlag.pinchZoom |
                        InteractiveFlag.doubleTapZoom |
                        InteractiveFlag.doubleTapDragZoom |
                        InteractiveFlag.scrollWheelZoom,
                    enableMultiFingerGestureRace: true,
                    pinchZoomThreshold: 0.2,
                    pinchMoveThreshold: 40,
                  ),
                ),
                children: [
                  TileLayer(
                    key: ValueKey(_base),
                    urlTemplate: _tileUrl,
                    userAgentPackageName: "com.moggnit.app",
                    maxNativeZoom: 18,
                    maxZoom: 14,
                  ),
                  CircleLayer(circles: circles),
                  PolylineLayer(polylines: [...outlinePolys, ...linePolys]),
                  MarkerLayer(markers: portDots),
                  MarkerLayer(markers: portLabels),
                  MarkerLayer(markers: vesselMarkers),
                ],
              ),
              if (widget.showToggle)
                Positioned(
                  top: 10,
                  right: 10,
                  child: _BaseToggle(
                    kind: _base,
                    onChanged: (k) => setState(() => _base = k),
                  ),
                ),
              Positioned(
                right: 10,
                bottom: widget.showLegend ? 52 : 12,
                child: _ZoomControls(
                  onIn: () => _zoomBy(0.8),
                  onOut: () => _zoomBy(-0.8),
                ),
              ),
              if (widget.showLegend)
                Positioned(
                  left: 10,
                  bottom: 10,
                  child: _Legend(dark: sat),
                ),
              Positioned(
                left: 10,
                top: 10,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: Colors.black.withValues(alpha: 0.42),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
                    child: ValueListenableBuilder<double>(
                      valueListenable: _zoom,
                      builder: (_, z, _) => Text(
                        "Каспий · z${z.toStringAsFixed(1)}",
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 0.2,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ZoomControls extends StatelessWidget {
  const _ZoomControls({required this.onIn, required this.onOut});
  final VoidCallback onIn;
  final VoidCallback onOut;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.94),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: MoggnitColors.border),
        boxShadow: [
          BoxShadow(
            color: MoggnitColors.navy.withValues(alpha: 0.1),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _zoomBtn(Icons.add, onIn),
          Container(width: 36, height: 1, color: MoggnitColors.border),
          _zoomBtn(Icons.remove, onOut),
        ],
      ),
    );
  }

  Widget _zoomBtn(IconData icon, VoidCallback onTap) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: SizedBox(
          width: 40,
          height: 40,
          child: Icon(icon, size: 20, color: MoggnitColors.navy),
        ),
      ),
    );
  }
}

class _BaseToggle extends StatelessWidget {
  const _BaseToggle({required this.kind, required this.onChanged});

  final MapBaseKind kind;
  final ValueChanged<MapBaseKind> onChanged;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.94),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: MoggnitColors.border),
        boxShadow: [
          BoxShadow(
            color: MoggnitColors.navy.withValues(alpha: 0.08),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _chip("Спутник", kind == MapBaseKind.satellite, () => onChanged(MapBaseKind.satellite)),
          _chip("Схема", kind == MapBaseKind.scheme, () => onChanged(MapBaseKind.scheme)),
        ],
      ),
    );
  }

  Widget _chip(String label, bool on, VoidCallback tap) {
    return GestureDetector(
      onTap: tap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOutCubic,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: on ? MoggnitColors.navy : Colors.transparent,
          borderRadius: BorderRadius.circular(9),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: on ? Colors.white : MoggnitColors.navySoft,
            fontSize: 12,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }
}

class _Legend extends StatelessWidget {
  const _Legend({required this.dark});
  final bool dark;

  @override
  Widget build(BuildContext context) {
    final fg = dark ? Colors.white : MoggnitColors.navy;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: (dark ? Colors.black : Colors.white).withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        child: DefaultTextStyle(
          style: TextStyle(color: fg, fontSize: 10, fontWeight: FontWeight.w600),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text("● порт   ▬ маршрут   ▲ судно"),
              SizedBox(height: 2),
              Text("◌ зона шторма · pinch / +− зум"),
            ],
          ),
        ),
      ),
    );
  }
}

class _VesselPainter extends CustomPainter {
  _VesselPainter({required this.selected, required this.color});
  final bool selected;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final path = ui.Path()
      ..moveTo(cx, cy - size.height * 0.38)
      ..lineTo(cx + size.width * 0.28, cy + size.height * 0.32)
      ..lineTo(cx, cy + size.height * 0.18)
      ..lineTo(cx - size.width * 0.28, cy + size.height * 0.32)
      ..close();
    if (selected) {
      canvas.drawCircle(
        Offset(cx, cy),
        size.width * 0.42,
        Paint()..color = color.withValues(alpha: 0.22),
      );
    }
    canvas.drawPath(
      path,
      Paint()
        ..color = Colors.white
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2,
    );
    canvas.drawPath(path, Paint()..color = color);
  }

  @override
  bool shouldRepaint(covariant _VesselPainter oldDelegate) =>
      oldDelegate.selected != selected || oldDelegate.color != color;
}
