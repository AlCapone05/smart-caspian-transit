import "package:material_ui/material_ui.dart";

import "../api.dart";
import "../sync.dart";
import "../theme.dart";
import "../widgets/ui.dart";
import "alternatives_screen.dart";
import "documents_screen.dart";

class ShipmentDetailScreen extends StatefulWidget {
  const ShipmentDetailScreen({super.key, required this.idOrRef});

  final String idOrRef;

  @override
  State<ShipmentDetailScreen> createState() => _ShipmentDetailScreenState();
}

class _ShipmentDetailScreenState extends State<ShipmentDetailScreen> {
  late Future<Map<String, dynamic>> _future;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _future = SctApi().shipment(widget.idOrRef);
  }

  Future<void> _reload() async {
    setState(() => _future = SctApi().shipment(widget.idOrRef));
    await _future;
    if (mounted) await SctSyncScope.of(context).refresh(silent: true);
  }

  String _eta(dynamic v) {
    if (v == null) return "—";
    final s = v.toString();
    if (s.length >= 16) {
      return "${s.substring(8, 10)}.${s.substring(5, 7)} ${s.substring(11, 16)}";
    }
    return s;
  }

  Future<void> _simulate(String scenario) async {
    setState(() => _busy = true);
    try {
      final d = await _future;
      final id = d["id"]?.toString() ?? widget.idOrRef;
      if (!mounted) return;
      await SctSyncScope.of(context).simulate(id, scenario: scenario);
      await _reload();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Сценарий «$scenario» применён · синхронизировано")),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("$e")));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _delete(String id, String ref) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Удалить?"),
        content: Text("$ref будет удалён везде."),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text("Отмена")),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text("Удалить", style: TextStyle(color: MoggnitColors.red)),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    await SctSyncScope.of(context).deleteShipment(id);
    if (!mounted) return;
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: MoggnitColors.bg,
      appBar: AppBar(
        backgroundColor: Colors.white,
        title: Text(widget.idOrRef),
        actions: [
          IconButton(onPressed: _reload, icon: const Icon(Icons.refresh)),
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
          final id = d["id"]?.toString() ?? widget.idOrRef;
          final ref = d["reference"]?.toString() ?? widget.idOrRef;
          final legs = (d["legs"] as List?) ?? [];
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
            children: [
              Text(
                ref,
                style: const TextStyle(
                  color: MoggnitColors.navy,
                  fontSize: 26,
                  fontWeight: FontWeight.w800,
                ),
              ),
              Text(
                d["route_label"]?.toString() ?? "",
                style: const TextStyle(color: MoggnitColors.muted),
              ),
              const SizedBox(height: 8),
              Text(d["cargo_line"]?.toString() ?? d["cargo_description"]?.toString() ?? ""),
              const SizedBox(height: 12),
              RiskPill(d["risk_level"]?.toString()),
              const SizedBox(height: 16),
              _cardInfo(d),
              if (d["risk_headline"] != null) ...[
                const SizedBox(height: 12),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: MoggnitColors.violetSoft,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: MoggnitColors.border),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        d["risk_headline"].toString(),
                        style: const TextStyle(
                          color: MoggnitColors.navy,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      if (d["risk_detail"] != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Text(d["risk_detail"].toString()),
                        ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 16),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  FilledButton.icon(
                    onPressed: () async {
                      final changed = await Navigator.of(context).push<bool>(
                        MaterialPageRoute(
                          builder: (_) => AlternativesScreen(shipmentId: id),
                        ),
                      );
                      if (changed == true) await _reload();
                    },
                    icon: const Icon(Icons.alt_route),
                    label: const Text("Альтернативы"),
                  ),
                  OutlinedButton.icon(
                    onPressed: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => DocumentsScreen(initialShipmentId: id),
                        ),
                      );
                    },
                    icon: const Icon(Icons.description_outlined),
                    label: const Text("Документы"),
                  ),
                ],
              ),
              if (d["selected_alternative_id"] != null) ...[
                const SizedBox(height: 8),
                Text(
                  "Выбранный маршрут: ${d["selected_alternative_id"]}",
                  style: const TextStyle(color: MoggnitColors.teal, fontSize: 12),
                ),
              ],
              const SizedBox(height: 16),
              const Text(
                "Сценарии",
                style: TextStyle(fontWeight: FontWeight.w700, color: MoggnitColors.navy),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  FilledButton(
                    onPressed: _busy ? null : () => _simulate("storm"),
                    child: const Text("Шторм"),
                  ),
                  OutlinedButton(
                    onPressed: _busy ? null : () => _simulate("port_congestion"),
                    child: const Text("Перегрузка порта"),
                  ),
                  OutlinedButton(
                    onPressed: _busy ? null : () => _simulate("normal"),
                    child: const Text("Обычные"),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              const Text(
                "Плечи маршрута",
                style: TextStyle(fontWeight: FontWeight.w700, color: MoggnitColors.navy),
              ),
              const SizedBox(height: 8),
              ...legs.map((raw) {
                final leg = (raw as Map).cast<String, dynamic>();
                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.94),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: MoggnitColors.border),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        leg["label"]?.toString() ?? leg["mode"]?.toString() ?? "",
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                      Text(
                        "${leg["origin_name"]} → ${leg["destination_name"]}",
                        style: const TextStyle(color: MoggnitColors.muted, fontSize: 13),
                      ),
                      Text(
                        leg["stage_status_label"]?.toString() ?? leg["status"]?.toString() ?? "",
                        style: const TextStyle(color: MoggnitColors.navySoft, fontSize: 12),
                      ),
                    ],
                  ),
                );
              }),
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: _busy ? null : () => _delete(id, ref),
                icon: const Icon(Icons.delete_outline, color: MoggnitColors.red),
                label: const Text("Удалить перевозку", style: TextStyle(color: MoggnitColors.red)),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _cardInfo(Map<String, dynamic> d) {
    final rows = [
      ("Этап", d["current_stage"]),
      ("Локация", d["current_location"]),
      ("Статус", d["status"]),
      ("План ETA", _eta(d["planned_eta"])),
      ("Прогноз", _eta(d["predicted_eta"])),
      ("Задержка", "${d["delay_hours"] ?? 0} ч"),
      ("Документы", "${d["documents_ready"]}/${d["documents_total"]}"),
      ("Стоимость", "${d["cost_rub"] ?? "—"} ₽"),
    ];
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.94),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: MoggnitColors.border),
      ),
      child: Column(
        children: [
          for (final r in rows)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 5),
              child: Row(
                children: [
                  SizedBox(
                    width: 110,
                    child: Text(r.$1, style: const TextStyle(color: MoggnitColors.muted)),
                  ),
                  Expanded(
                    child: Text(
                      "${r.$2 ?? "—"}",
                      style: const TextStyle(fontWeight: FontWeight.w600, color: MoggnitColors.navy),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
