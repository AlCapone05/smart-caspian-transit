import "package:material_ui/material_ui.dart";

import "../sync.dart";
import "../theme.dart";
import "../widgets/ui.dart";
import "create_shipment_screen.dart";
import "shipment_detail_screen.dart";

const _done = {"delivered", "completed", "cancelled"};

class ShipmentsScreen extends StatefulWidget {
  const ShipmentsScreen({super.key});

  @override
  State<ShipmentsScreen> createState() => _ShipmentsScreenState();
}

class _ShipmentsScreenState extends State<ShipmentsScreen> {
  String _q = "";
  String _tab = "active"; // active | done

  Future<void> _openCreate() async {
    final ref = await Navigator.of(context).push<String>(
      MaterialPageRoute(builder: (_) => const CreateShipmentScreen()),
    );
    if (!mounted || ref == null) return;
    setState(() => _tab = "active");
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text("Создано · $ref · на карте до пункта Б")),
    );
  }

  Future<void> _delete(Map<String, dynamic> s) async {
    final id = s["id"]?.toString();
    final ref = s["reference"]?.toString() ?? id ?? "";
    if (id == null) return;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Удалить перевозку?"),
        content: Text("$ref исчезнет и на сайте, и в приложении."),
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
  }

  @override
  Widget build(BuildContext context) {
    final sync = SctSyncScope.of(context);
    final active = sync.shipments.where((s) => !_done.contains("${s["status"]}")).toList();
    final done = sync.shipments.where((s) => _done.contains("${s["status"]}")).toList();
    final source = _tab == "done" ? done : active;
    final filtered = source.where((s) {
      if (_q.isEmpty) return true;
      final hay = [
        s["reference"],
        s["route_label"],
        s["current_stage"],
        s["container_no"],
        s["cargo_description"],
      ].join(" ").toLowerCase();
      return hay.contains(_q);
    }).toList();

    return PageScaffold(
      header: BrandHeader(
        title: "Перевозки",
        subtitle: _tab == "active"
            ? "${active.length} активных · на карте"
            : "${done.length} завершённых",
        online: sync.online,
        actions: [
          IconButton(
            onPressed: () => sync.refresh(),
            icon: const Icon(Icons.refresh, color: MoggnitColors.navy),
          ),
        ],
      ),
      floatingActionButton: _tab == "active"
          ? FloatingActionButton.extended(
              onPressed: _openCreate,
              icon: const Icon(Icons.add),
              label: const Text("Груз"),
            )
          : null,
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: Row(
              children: [
                Expanded(
                  child: _SubTab(
                    label: "Активные · ${active.length}",
                    selected: _tab == "active",
                    onTap: () => setState(() => _tab = "active"),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _SubTab(
                    label: "Завершённые · ${done.length}",
                    selected: _tab == "done",
                    onTap: () => setState(() => _tab = "done"),
                  ),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: TextField(
              decoration: const InputDecoration(
                hintText: "Поиск: SCT, контейнер, маршрут…",
                prefixIcon: Icon(Icons.search),
                isDense: true,
              ),
              onChanged: (v) => setState(() => _q = v.trim().toLowerCase()),
            ),
          ),
          Expanded(
            child: RefreshIndicator(
              color: MoggnitColors.violet,
              onRefresh: () => sync.refresh(),
              child: filtered.isEmpty
                  ? ListView(
                      children: [
                        const SizedBox(height: 48),
                        Center(
                          child: Text(
                            sync.loading
                                ? "Загрузка…"
                                : _tab == "active"
                                    ? "Нет активных перевозок"
                                    : "Нет завершённых перевозок",
                            style: const TextStyle(color: MoggnitColors.muted),
                          ),
                        ),
                      ],
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.fromLTRB(16, 4, 16, 100),
                      itemCount: filtered.length,
                      itemBuilder: (context, i) {
                        final s = filtered[i];
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: ShipmentCard(
                            item: s,
                            onDelete: () => _delete(s),
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
                        );
                      },
                    ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SubTab extends StatelessWidget {
  const _SubTab({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Ink(
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: MoggnitColors.border),
            gradient: selected
                ? const LinearGradient(
                    colors: [MoggnitColors.cyanSoft, MoggnitColors.violetSoft],
                  )
                : null,
            color: selected ? null : Colors.white.withValues(alpha: 0.9),
          ),
          child: Text(
            label,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: MoggnitColors.navy,
              fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
              fontSize: 13,
            ),
          ),
        ),
      ),
    );
  }
}
