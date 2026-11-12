import "package:material_ui/material_ui.dart";

import "../api.dart";
import "../sync.dart";
import "../theme.dart";

class AlternativesScreen extends StatefulWidget {
  const AlternativesScreen({super.key, required this.shipmentId});

  final String shipmentId;

  @override
  State<AlternativesScreen> createState() => _AlternativesScreenState();
}

class _AlternativesScreenState extends State<AlternativesScreen> {
  late Future<Map<String, dynamic>> _future;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _future = SctApi().alternatives(widget.shipmentId);
  }

  Future<void> _select(Map<String, dynamic> alt) async {
    if (alt["feasible"] == false || alt["is_current"] == true) return;
    setState(() => _busy = true);
    try {
      await SctSyncScope.of(context).selectAlternative(
        widget.shipmentId,
        alt["id"].toString(),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Выбрано: ${alt["title"] ?? alt["id"]}")),
      );
      Navigator.of(context).pop(true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("$e")));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: MoggnitColors.bg,
      appBar: AppBar(title: const Text("Альтернативы")),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _future,
        builder: (context, snap) {
          if (snap.hasError) return Center(child: Text("${snap.error}"));
          if (!snap.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final d = snap.data!;
          final insight = (d["insight"] as Map?)?.cast<String, dynamic>();
          final alts = ((d["alternatives"] as List?) ?? [])
              .map((e) => (e as Map).cast<String, dynamic>())
              .toList();

          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
            children: [
              Text(
                d["reference"]?.toString() ?? widget.shipmentId,
                style: const TextStyle(
                  color: MoggnitColors.navy,
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                ),
              ),
              Text(
                d["route_label"]?.toString() ?? "",
                style: const TextStyle(color: MoggnitColors.muted),
              ),
              if (insight != null) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: MoggnitColors.violetSoft,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        insight["title"]?.toString() ?? "",
                        style: const TextStyle(fontWeight: FontWeight.w800),
                      ),
                      Text(insight["detail"]?.toString() ?? ""),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 14),
              ...alts.map((alt) {
                final current = alt["is_current"] == true;
                final recommended = alt["recommended"] == true;
                return Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: recommended
                        ? const Color(0xFFEEF6F0)
                        : Colors.white.withValues(alpha: 0.94),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: current ? MoggnitColors.cyan : MoggnitColors.border,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        "${alt["title"] ?? alt["id"]}${recommended ? " · рекомендуем" : ""}",
                        style: const TextStyle(fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 6),
                      Text("ETA: ${alt["eta_label"] ?? "—"}"),
                      Text("К плану: ${alt["delay_label"] ?? "—"}"),
                      Text("Длительность: ${alt["duration_label"] ?? "—"}"),
                      Text("Стоимость: ${alt["cost_label"] ?? "—"}"),
                      Text("CO₂e: ${alt["co2e_label"] ?? "—"}"),
                      Text("Ограничения: ${alt["constraints"] ?? "—"}"),
                      const SizedBox(height: 10),
                      FilledButton(
                        onPressed: _busy || current || alt["feasible"] == false
                            ? null
                            : () => _select(alt),
                        child: Text(current ? "Текущий" : "Выбрать"),
                      ),
                    ],
                  ),
                );
              }),
              if (d["footnote"] != null)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    d["footnote"].toString(),
                    style: const TextStyle(color: MoggnitColors.muted, fontSize: 11),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}
