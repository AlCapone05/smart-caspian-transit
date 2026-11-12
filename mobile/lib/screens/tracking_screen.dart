import "package:material_ui/material_ui.dart";

import "../sync.dart";
import "../theme.dart";
import "../widgets/caspian_map.dart";
import "../widgets/ui.dart";
import "shipment_detail_screen.dart";

class TrackingScreen extends StatefulWidget {
  const TrackingScreen({super.key});

  @override
  State<TrackingScreen> createState() => _TrackingScreenState();
}

class _TrackingScreenState extends State<TrackingScreen> {
  String? _selectedId;
  String? _previewAlt;
  bool _busy = false;

  List<Map<String, dynamic>> _maps(dynamic raw) =>
      ((raw as List?) ?? []).map((e) => (e as Map).cast<String, dynamic>()).toList();

  Future<void> _applyRoute(String vesselId, String altId) async {
    setState(() => _busy = true);
    try {
      await SctSyncScope.of(context).selectVesselRoute(vesselId, altId);
      if (!mounted) return;
      setState(() => _previewAlt = null);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Маршрут обновлён · синхронизировано с сайтом")),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("$e")));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final sync = SctSyncScope.of(context);
    final track = sync.tracking;
    final vessels = _maps(track?["vessels"]);
    final storms = _maps(track?["storm_cells"]);
    final ports = _maps(track?["ports"]);
    final corridors = _maps(track?["corridors"]);
    final affected = ((track?["storm_affected_vessel_ids"] as List?) ?? [])
        .map((e) => e.toString())
        .toSet();
    final kpis = (track?["kpis"] as Map?)?.cast<String, dynamic>() ?? {};

    Map<String, dynamic>? selected;
    if (vessels.isNotEmpty) {
      selected = vessels.cast<Map<String, dynamic>?>().firstWhere(
            (v) => v?["id"]?.toString() == _selectedId,
            orElse: () => vessels.first,
          );
    }
    final selectedId = selected?["id"]?.toString();
    final stormHit = selectedId != null &&
        (affected.contains(selectedId) || selected?["route_storm_danger"] == true);
    final alts = _maps(selected?["storm_alternatives"])
      ..sort((a, b) {
        final ar = a["recommended"] == true ? 0 : 1;
        final br = b["recommended"] == true ? 0 : 1;
        if (ar != br) return ar - br;
        final as = a["storm_safe"] == true ? 0 : 1;
        final bs = b["storm_safe"] == true ? 0 : 1;
        return as - bs;
      });
    List<Map<String, dynamic>>? previewPath;
    if (_previewAlt != null) {
      for (final a in alts) {
        if (a["id"]?.toString() == _previewAlt) {
          previewPath = _maps(a["path"]);
          break;
        }
      }
    }
    Map<String, dynamic>? recommended;
    final currentAlt = selected?["selected_alternative_id"]?.toString() ?? "alt_current";
    for (final a in alts) {
      if (a["recommended"] == true && a["id"]?.toString() != currentAlt) {
        recommended = a;
        break;
      }
    }

    return PageScaffold(
      header: BrandHeader(
        title: "Карта · GPS",
        subtitle: track?["subtitle"]?.toString() ?? "Каспийский коридор",
        online: sync.online,
        actions: [
          IconButton(
            onPressed: () => sync.refresh(),
            icon: const Icon(Icons.refresh, color: MoggnitColors.navy),
          ),
        ],
      ),
      child: RefreshIndicator(
        color: MoggnitColors.cyan,
        onRefresh: () => sync.refresh(),
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
          children: [
            Row(
              children: [
                Expanded(child: KpiTile(label: "Суда", value: "${kpis["vessels"] ?? vessels.length}")),
                const SizedBox(width: 8),
                Expanded(
                  child: KpiTile(
                    label: "В пути",
                    value: "${kpis["underway"] ?? "—"}",
                    accent: MoggnitColors.teal,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: KpiTile(
                    label: "Штормы",
                    value: "${kpis["storm_alerts"] ?? storms.length}",
                    accent: MoggnitColors.red,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            CaspianMapView(
              vessels: vessels,
              stormCells: storms,
              ports: ports,
              corridors: corridors,
              previewPath: previewPath,
              selectedId: selectedId,
              height: 340,
              showLegend: true,
              onSelectVessel: (id) => setState(() {
                _selectedId = id;
                _previewAlt = null;
              }),
            ),
            const SizedBox(height: 8),
            Text(
              "Esri спутник/схема · как на сайте · тап по судну для обхода",
              style: TextStyle(color: MoggnitColors.muted.withValues(alpha: 0.9), fontSize: 11),
            ),
            const SizedBox(height: 16),
            Text(
              "Активные перевозки",
              style: TextStyle(
                color: MoggnitColors.navy,
                fontWeight: FontWeight.w800,
                fontSize: 15,
              ),
            ),
            const SizedBox(height: 8),
            ...SctSyncScope.of(context)
                .shipments
                .where(
                  (s) => !{"delivered", "completed", "cancelled"}
                      .contains("${s["status"]}"),
                )
                .map(
                  (s) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: ShipmentCard(
                      item: s,
                      onTap: () {
                        Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => ShipmentDetailScreen(
                              idOrRef: s["reference"]?.toString() ??
                                  s["id"]?.toString() ??
                                  "",
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                ),
            if (selected != null) ...[
              Builder(
                builder: (context) {
                  final vessel = selected!;
                  final vesselId = selectedId ?? vessel["id"]?.toString() ?? "";
                  final safeAlt = recommended;
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.94),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: MoggnitColors.border),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      vessel["name"]?.toString() ?? "",
                      style: const TextStyle(
                        color: MoggnitColors.navy,
                        fontWeight: FontWeight.w800,
                        fontSize: 16,
                      ),
                    ),
                    Text(
                      "${vessel["route_label"] ?? ""} · ${vessel["progress_pct"] ?? 0}% · ${vessel["speed_knots"] ?? 0} kn",
                      style: const TextStyle(color: MoggnitColors.muted, fontSize: 13),
                    ),
                    if (vessel["shipment_id"] != null) ...[
                      const SizedBox(height: 8),
                      TextButton(
                        onPressed: () {
                          Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) => ShipmentDetailScreen(
                                idOrRef: vessel["shipment_id"].toString(),
                              ),
                            ),
                          );
                        },
                        child: const Text("Открыть груз →"),
                      ),
                    ],
                  ],
                ),
              ),
              if (stormHit || alts.length > 1) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: stormHit ? const Color(0xFFF6F3F0) : Colors.white.withValues(alpha: 0.94),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: stormHit
                          ? MoggnitColors.amber.withValues(alpha: 0.45)
                          : MoggnitColors.border,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        stormHit
                            ? "△ Опасность на маршруте — смените путь"
                            : "Альтернативные морские пути",
                        style: const TextStyle(
                          color: MoggnitColors.navy,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      if (stormHit && safeAlt != null) ...[
                        const SizedBox(height: 10),
                        FilledButton(
                          onPressed: _busy
                              ? null
                              : () => _applyRoute(
                                    vesselId,
                                    safeAlt["id"].toString(),
                                  ),
                          child: Text(
                            "Перейти на безопасный: ${safeAlt["title"]}",
                          ),
                        ),
                      ],
                      const SizedBox(height: 10),
                      ...alts.map((alt) {
                        final id = alt["id"]?.toString() ?? "";
                        final selectedAlt =
                            (vessel["selected_alternative_id"]?.toString() ?? "alt_current") ==
                                id;
                        final canSelect = !selectedAlt && alt["feasible"] != false;
                        return Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: alt["recommended"] == true && stormHit
                                ? const Color(0xFFEEF6F0)
                                : Colors.white,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: selectedAlt
                                  ? MoggnitColors.cyan
                                  : MoggnitColors.border,
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                "${alt["title"] ?? id}${alt["recommended"] == true ? " · рекомендуем" : ""}",
                                style: const TextStyle(fontWeight: FontWeight.w700),
                              ),
                              Text(
                                "${alt["subtitle"] ?? ""}${alt["storm_safe"] == true ? " · безопаснее" : " · опасность"}",
                                style: const TextStyle(
                                  color: MoggnitColors.muted,
                                  fontSize: 12,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Row(
                                children: [
                                  OutlinedButton(
                                    onPressed: () => setState(() => _previewAlt = id),
                                    child: const Text("На карте"),
                                  ),
                                  const SizedBox(width: 8),
                                  FilledButton(
                                    onPressed: !canSelect || _busy
                                        ? null
                                        : () => _applyRoute(vesselId, id),
                                    child: Text(selectedAlt ? "Активен" : "Выбрать"),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        );
                      }),
                    ],
                  ),
                ),
              ],
                    ],
                  );
                },
              ),
            ],
            if (vessels.isEmpty) ...[
              const SizedBox(height: 24),
              const Text(
                "На карте только суда активных перевозок. Создайте груз — появится маршрут A→B.",
                style: TextStyle(color: MoggnitColors.muted),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
