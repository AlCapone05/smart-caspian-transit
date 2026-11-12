import "package:material_ui/material_ui.dart";

import "../sync.dart";
import "../theme.dart";
import "../widgets/ui.dart";
import "shipment_detail_screen.dart";

class AlertsScreen extends StatelessWidget {
  const AlertsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final sync = SctSyncScope.of(context);
    final items = sync.notifications;

    return PageScaffold(
      header: BrandHeader(
        title: "Уведомления",
        subtitle: items.isEmpty ? "Нет событий" : "${items.length} событий",
        online: sync.online,
        actions: [
          IconButton(
            onPressed: () => sync.refresh(),
            icon: const Icon(Icons.refresh, color: MoggnitColors.navy),
          ),
        ],
      ),
      child: RefreshIndicator(
        color: MoggnitColors.violet,
        onRefresh: () => sync.refresh(),
        child: items.isEmpty
            ? ListView(
                children: const [
                  SizedBox(height: 64),
                  Center(
                    child: Text(
                      "Пока нет событий",
                      style: TextStyle(color: MoggnitColors.muted),
                    ),
                  ),
                ],
              )
            : ListView.separated(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
                itemCount: items.length,
                separatorBuilder: (_, _) => const SizedBox(height: 10),
                itemBuilder: (context, i) {
                  final n = items[i];
                  final ref = n["reference"]?.toString();
                  return InkWell(
                    borderRadius: BorderRadius.circular(14),
                    onTap: ref == null || ref.isEmpty
                        ? null
                        : () {
                            Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) => ShipmentDetailScreen(idOrRef: ref),
                              ),
                            );
                          },
                    child: Ink(
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
                            n["created_label"]?.toString() ?? "",
                            style: const TextStyle(color: MoggnitColors.muted, fontSize: 11),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            n["title"]?.toString() ?? "",
                            style: const TextStyle(
                              color: MoggnitColors.navy,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            n["detail"]?.toString() ?? "",
                            style: const TextStyle(color: MoggnitColors.navySoft, fontSize: 13),
                          ),
                          if (ref != null && ref.isNotEmpty)
                            Padding(
                              padding: const EdgeInsets.only(top: 8),
                              child: Text(
                                ref,
                                style: const TextStyle(
                                  color: MoggnitColors.violet,
                                  fontWeight: FontWeight.w700,
                                  fontSize: 12,
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                  );
                },
              ),
      ),
    );
  }
}
