import "package:google_fonts/google_fonts.dart";
import "package:material_ui/material_ui.dart";

import "../sync.dart";
import "../theme.dart";
import "../widgets/caspian_map.dart";
import "../widgets/ui.dart";
import "assistant_screen.dart";
import "shipment_detail_screen.dart";

const _done = {"delivered", "completed", "cancelled"};

class OverviewScreen extends StatelessWidget {
  const OverviewScreen({super.key});

  List<Map<String, dynamic>> _maps(dynamic raw) =>
      ((raw as List?) ?? []).map((e) => (e as Map).cast<String, dynamic>()).toList();

  @override
  Widget build(BuildContext context) {
    final sync = SctSyncScope.of(context);
    final data = sync.overview;
    final track = sync.tracking;
    final kpis = (data?["kpis"] as Map?)?.cast<String, dynamic>() ?? {};
    final attention = _maps(data?["attention"]);
    final vessels = _maps(track?["vessels"]);
    final storms = _maps(track?["storm_cells"]);
    final ports = _maps(track?["ports"]);
    final corridors = _maps(track?["corridors"]);
    final activeShips = sync.shipments
        .where((s) => !_done.contains("${s["status"]}"))
        .toList();
    final primary = attention.isNotEmpty ? attention.first : null;

    return PageScaffold(
      header: BrandHeader(
        title: "Обзор",
        subtitle: "Каспийский коридор · как на сайте",
        online: sync.online,
        actions: [
          IconButton(
            tooltip: "Ассистент",
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const AssistantScreen()),
              );
            },
            icon: const Icon(Icons.chat_bubble_outline, color: MoggnitColors.navy),
          ),
          IconButton(
            tooltip: "Обновить",
            onPressed: () => sync.refresh(),
            icon: const Icon(Icons.refresh, color: MoggnitColors.navy),
          ),
        ],
      ),
      child: RefreshIndicator(
        color: MoggnitColors.cyan,
        onRefresh: () => sync.refresh(),
        child: sync.loading && data == null
            ? ListView(
                children: const [
                  SizedBox(height: 120),
                  Center(child: CircularProgressIndicator()),
                ],
              )
            : ListView(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
                children: [
                  FadeSlideIn(
                    child: Text(
                      "МОГГНИТ",
                      style: GoogleFonts.manrope(
                        color: MoggnitColors.navy,
                        fontSize: 28,
                        fontWeight: FontWeight.w800,
                        fontStyle: FontStyle.italic,
                        letterSpacing: 0.2,
                        height: 1.05,
                      ),
                    ),
                  ),
                  const SizedBox(height: 4),
                  FadeSlideIn(
                    index: 1,
                    child: Text(
                      data?["subtitle"]?.toString() ??
                          "Оперативный контроль Каспийского коридора",
                      style: const TextStyle(color: MoggnitColors.muted, fontSize: 13),
                    ),
                  ),
                  if (sync.error != null) ...[
                    const SizedBox(height: 10),
                    Text(sync.error!, style: const TextStyle(color: MoggnitColors.red)),
                  ],
                  const SizedBox(height: 14),
                  FadeSlideIn(
                    index: 2,
                    child: GridView.count(
                      crossAxisCount: 2,
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      mainAxisSpacing: 10,
                      crossAxisSpacing: 10,
                      childAspectRatio: 1.6,
                      children: [
                        KpiTile(label: "Активные", value: "${kpis["active"] ?? activeShips.length}"),
                        KpiTile(
                          label: "Под риском",
                          value: "${kpis["at_risk"] ?? "—"}",
                          accent: MoggnitColors.storm,
                        ),
                        KpiTile(
                          label: "Задержаны",
                          value: "${kpis["delayed"] ?? "—"}",
                          accent: MoggnitColors.amber,
                        ),
                        KpiTile(
                          label: "Документы",
                          value: "${kpis["awaiting_docs"] ?? "—"}",
                          accent: MoggnitColors.teal,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  FadeSlideIn(
                    index: 3,
                    child: CaspianMapView(
                      vessels: vessels,
                      stormCells: storms,
                      ports: ports,
                      corridors: corridors,
                      height: 300,
                      showLegend: true,
                      onSelectVessel: (id) {
                        Map<String, dynamic>? v;
                        for (final x in vessels) {
                          if (x["id"]?.toString() == id) {
                            v = x;
                            break;
                          }
                        }
                        final sid = v?["shipment_id"]?.toString();
                        if (sid == null || sid.isEmpty) return;
                        Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => ShipmentDetailScreen(idOrRef: sid),
                          ),
                        );
                      },
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    "Спутник / схема · суда активных рейсов · как на сайте",
                    style: TextStyle(
                      color: MoggnitColors.muted.withValues(alpha: 0.95),
                      fontSize: 11,
                    ),
                  ),
                  if (primary != null) ...[
                    const SizedBox(height: 18),
                    FadeSlideIn(
                      index: 4,
                      child: Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: MoggnitColors.cyanSoft.withValues(alpha: 0.55),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: MoggnitColors.border),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              "Требуют внимания",
                              style: GoogleFonts.manrope(
                                color: MoggnitColors.navy,
                                fontWeight: FontWeight.w800,
                                fontSize: 13,
                                letterSpacing: 0.2,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              primary["title"]?.toString() ?? "",
                              style: const TextStyle(
                                fontWeight: FontWeight.w800,
                                color: MoggnitColors.navy,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(primary["detail"]?.toString() ?? ""),
                            if (primary["reference"] != null || primary["shipment_id"] != null)
                              TextButton(
                                onPressed: () {
                                  Navigator.of(context).push(
                                    MaterialPageRoute(
                                      builder: (_) => ShipmentDetailScreen(
                                        idOrRef: primary["reference"]?.toString() ??
                                            primary["shipment_id"]?.toString() ??
                                            "",
                                      ),
                                    ),
                                  );
                                },
                                child: const Text("Открыть →"),
                              ),
                          ],
                        ),
                      ),
                    ),
                  ],
                  const SizedBox(height: 20),
                  FadeSlideIn(
                    index: 5,
                    child: Row(
                      children: [
                        Text(
                          "Активные перевозки",
                          style: GoogleFonts.manrope(
                            color: MoggnitColors.navy,
                            fontWeight: FontWeight.w800,
                            fontSize: 16,
                          ),
                        ),
                        const Spacer(),
                        Text(
                          "${activeShips.length}",
                          style: const TextStyle(
                            color: MoggnitColors.muted,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 10),
                  if (activeShips.isEmpty)
                    const Text(
                      "Нет активных перевозок — создайте груз, и он появится на карте",
                      style: TextStyle(color: MoggnitColors.muted),
                    )
                  else
                    ...List.generate(activeShips.length, (i) {
                      final s = activeShips[i];
                      return FadeSlideIn(
                        index: 6 + i,
                        child: Padding(
                          padding: const EdgeInsets.only(bottom: 10),
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
                      );
                    }),
                ],
              ),
      ),
    );
  }
}
