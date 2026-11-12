import "package:material_ui/material_ui.dart";

import "../sync.dart";
import "../theme.dart";
import "../widgets/ui.dart";
import "analytics_screen.dart";
import "assistant_screen.dart";
import "compare_screen.dart";
import "documents_screen.dart";
import "settings_screen.dart";

class MoreScreen extends StatelessWidget {
  const MoreScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final sync = SctSyncScope.of(context);
    final items = [
      (
        Icons.description_outlined,
        "Документы",
        "Реестр, ТН ВЭД, предпроверка",
        () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const DocumentsScreen()),
            ),
      ),
      (
        Icons.compare_arrows,
        "Сравнение",
        "Ранжирование перевозок",
        () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const CompareScreen()),
            ),
      ),
      (
        Icons.insights_outlined,
        "Аналитика",
        "KPI, MAE, риски",
        () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const AnalyticsScreen()),
            ),
      ),
      (
        Icons.chat_bubble_outline,
        "Ассистент",
        "DeepSeek · вопросы по коридору",
        () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const AssistantScreen()),
            ),
      ),
      (
        Icons.settings_outlined,
        "Настройки",
        "Оператор, сценарий, уведомления",
        () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const SettingsScreen()),
            ),
      ),
    ];

    return PageScaffold(
      header: BrandHeader(
        title: "Ещё",
        subtitle: "Все функции сайта",
        online: sync.online,
      ),
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
        itemCount: items.length,
        separatorBuilder: (_, _) => const SizedBox(height: 10),
        itemBuilder: (context, i) {
          final it = items[i];
          return Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: it.$4,
              borderRadius: BorderRadius.circular(14),
              child: Ink(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.94),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: MoggnitColors.border),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 42,
                      height: 42,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: MoggnitColors.cyanSoft,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(it.$1, color: MoggnitColors.navy),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            it.$2,
                            style: const TextStyle(
                              fontWeight: FontWeight.w800,
                              color: MoggnitColors.navy,
                            ),
                          ),
                          Text(
                            it.$3,
                            style: const TextStyle(
                              color: MoggnitColors.muted,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const Icon(Icons.chevron_right, color: MoggnitColors.muted),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
