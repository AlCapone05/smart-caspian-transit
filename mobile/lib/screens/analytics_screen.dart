import "package:material_ui/material_ui.dart";

import "../api.dart";
import "../theme.dart";
import "../widgets/ui.dart";
import "shipment_detail_screen.dart";

class AnalyticsScreen extends StatefulWidget {
  const AnalyticsScreen({super.key});

  @override
  State<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends State<AnalyticsScreen> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = SctApi().analytics();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: MoggnitColors.bg,
      appBar: AppBar(
        title: const Text("Аналитика"),
        actions: [
          IconButton(
            onPressed: () => setState(() => _future = SctApi().analytics()),
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _future,
        builder: (context, snap) {
          if (snap.hasError) {
            return Center(child: Text("${snap.error}"));
          }
          if (!snap.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final d = snap.data!;
          final kpis = (d["kpis"] as Map?)?.cast<String, dynamic>() ?? {};
          final model = (d["model"] as Map?)?.cast<String, dynamic>() ?? {};
          final mae = (model["mae_hours"] as Map?)?.cast<String, dynamic>() ?? {};
          final attention = ((d["attention"] as List?) ?? d["top_risk"] as List? ?? [])
              .map((e) => (e as Map).cast<String, dynamic>())
              .toList();

          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
            children: [
              Text(
                d["title"]?.toString() ?? "Аналитика",
                style: const TextStyle(
                  color: MoggnitColors.navy,
                  fontSize: 24,
                  fontWeight: FontWeight.w800,
                ),
              ),
              Text(
                d["subtitle"]?.toString() ?? "",
                style: const TextStyle(color: MoggnitColors.muted, fontSize: 13),
              ),
              const SizedBox(height: 16),
              GridView.count(
                crossAxisCount: 2,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                mainAxisSpacing: 10,
                crossAxisSpacing: 10,
                childAspectRatio: 1.55,
                children: [
                  KpiTile(label: "Перевозок", value: "${kpis["shipments"] ?? "—"}"),
                  KpiTile(
                    label: "С задержкой",
                    value: "${kpis["delayed"] ?? "—"}",
                    accent: MoggnitColors.amber,
                  ),
                  KpiTile(
                    label: "Средняя задержка",
                    value: "${kpis["avg_delay_hours"] ?? "—"} ч",
                  ),
                  KpiTile(
                    label: "CO₂e",
                    value: "${kpis["co2e_tonnes"] ?? "—"} т",
                    accent: MoggnitColors.teal,
                  ),
                ],
              ),
              const SizedBox(height: 18),
              const Text(
                "Качество прогноза",
                style: TextStyle(fontWeight: FontWeight.w800, color: MoggnitColors.navy),
              ),
              const SizedBox(height: 6),
              Text(
                model["note"]?.toString() ?? "",
                style: const TextStyle(color: MoggnitColors.muted, fontSize: 13),
              ),
              const SizedBox(height: 10),
              _row("MAE median", "${mae["median"] ?? "—"} ч"),
              _row("MAE catboost", "${mae["catboost"] ?? "—"} ч"),
              _row("Split", "${model["split"] ?? "—"}"),
              _row("Стоимость выборки", "${kpis["cost_rub"] ?? "—"} ₽"),
              if (attention.isNotEmpty) ...[
                const SizedBox(height: 18),
                const Text(
                  "Под риском",
                  style: TextStyle(fontWeight: FontWeight.w800, color: MoggnitColors.navy),
                ),
                const SizedBox(height: 8),
                ...attention.take(8).map((a) {
                  final ref = a["reference"]?.toString() ?? a["id"]?.toString() ?? "";
                  return ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(ref, style: const TextStyle(fontWeight: FontWeight.w700)),
                    subtitle: Text(a["detail"]?.toString() ?? a["title"]?.toString() ?? ""),
                    onTap: ref.isEmpty
                        ? null
                        : () {
                            Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) => ShipmentDetailScreen(idOrRef: ref),
                              ),
                            );
                          },
                  );
                }),
              ],
            ],
          );
        },
      ),
    );
  }

  Widget _row(String k, String v) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Expanded(child: Text(k, style: const TextStyle(color: MoggnitColors.muted))),
          Text(v, style: const TextStyle(fontWeight: FontWeight.w700, color: MoggnitColors.navy)),
        ],
      ),
    );
  }
}
