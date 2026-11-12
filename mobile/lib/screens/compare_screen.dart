import "package:material_ui/material_ui.dart";

import "../api.dart";
import "../sync.dart";
import "../theme.dart";

class CompareScreen extends StatefulWidget {
  const CompareScreen({super.key});

  @override
  State<CompareScreen> createState() => _CompareScreenState();
}

class _CompareScreenState extends State<CompareScreen> {
  final _api = SctApi();
  final Set<String> _selected = {};
  Map<String, dynamic>? _data;
  String? _error;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final ships = SctSyncScope.of(context).shipments;
      setState(() {
        _selected.addAll(ships.take(3).map((s) => s["id"]?.toString() ?? "").where((e) => e.isNotEmpty));
      });
      _load();
    });
  }

  Future<void> _load() async {
    if (_selected.length < 2) {
      setState(() {
        _data = null;
        _error = "Выберите минимум 2 перевозки";
      });
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final d = await _api.compareShipments(_selected.toList());
      if (!mounted) return;
      setState(() => _data = d);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = "$e");
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ships = SctSyncScope.of(context).shipments;
    final columns = ((_data?["columns"] as List?) ?? [])
        .map((e) => (e as Map).cast<String, dynamic>())
        .toList();

    return Scaffold(
      backgroundColor: MoggnitColors.bg,
      appBar: AppBar(
        title: const Text("Сравнение"),
        actions: [
          TextButton(
            onPressed: () {
              setState(() {
                _selected
                  ..clear()
                  ..addAll(ships.map((s) => s["id"]?.toString() ?? "").where((e) => e.isNotEmpty));
              });
              _load();
            },
            child: const Text("Все"),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: [
          const Text(
            "Те же метрики, что на сайте · выберите перевозки",
            style: TextStyle(color: MoggnitColors.muted, fontSize: 13),
          ),
          const SizedBox(height: 12),
          ...ships.map((s) {
            final id = s["id"]?.toString() ?? "";
            final on = _selected.contains(id);
            return CheckboxListTile(
              value: on,
              title: Text(s["reference"]?.toString() ?? id),
              subtitle: Text(s["route_label"]?.toString() ?? ""),
              onChanged: (v) {
                setState(() {
                  if (v == true) {
                    _selected.add(id);
                  } else {
                    _selected.remove(id);
                  }
                });
                _load();
              },
            );
          }),
          const SizedBox(height: 8),
          if (_loading) const LinearProgressIndicator(),
          if (_error != null)
            Text(_error!, style: const TextStyle(color: MoggnitColors.red)),
          if (columns.isNotEmpty) ...[
            const SizedBox(height: 12),
            ...columns.map((c) {
              return Container(
                margin: const EdgeInsets.only(bottom: 10),
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
                      "#${c["rank"] ?? "—"} · ${c["reference"] ?? ""} · балл ${c["score"] ?? "—"}",
                      style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        color: MoggnitColors.navy,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(c["route_label"]?.toString() ?? ""),
                    Text("Этап: ${c["current_stage"] ?? "—"}"),
                    Text("К плану: ${c["delay_label"] ?? "—"}"),
                    Text("Риск: ${c["risk_level"] ?? "—"}"),
                    Text("Стоимость: ${c["cost_label"] ?? "—"}"),
                    Text("CO₂e: ${c["co2e_label"] ?? "—"}"),
                    Text("Документы: ${c["documents_label"] ?? "—"}"),
                  ],
                ),
              );
            }),
          ],
        ],
      ),
    );
  }
}
