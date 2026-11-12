import "package:google_fonts/google_fonts.dart";
import "package:material_ui/material_ui.dart";

import "../theme.dart";

class BrandHeader extends StatelessWidget {
  const BrandHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.online = true,
    this.actions,
  });

  final String title;
  final String? subtitle;
  final bool online;
  final List<Widget>? actions;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 6, 10, 14),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.82),
        border: const Border(bottom: BorderSide(color: MoggnitColors.border)),
      ),
      child: SafeArea(
        bottom: false,
        child: Row(
          children: [
            TweenAnimationBuilder<double>(
              tween: Tween(begin: 0.92, end: 1),
              duration: const Duration(milliseconds: 700),
              curve: Curves.easeOutBack,
              builder: (context, scale, child) => Transform.scale(scale: scale, child: child),
              child: Container(
                width: 42,
                height: 42,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(11),
                  gradient: const LinearGradient(
                    colors: [MoggnitColors.navy, MoggnitColors.teal],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
                child: Text(
                  "М",
                  style: GoogleFonts.manrope(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                    fontSize: 19,
                    fontStyle: FontStyle.italic,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    "МОГГНИТ",
                    style: GoogleFonts.manrope(
                      color: MoggnitColors.navy,
                      fontWeight: FontWeight.w800,
                      fontSize: 17,
                      fontStyle: FontStyle.italic,
                      letterSpacing: 0.4,
                      height: 1.1,
                    ),
                  ),
                  Text(
                    title,
                    style: GoogleFonts.manrope(
                      color: MoggnitColors.navySoft,
                      fontWeight: FontWeight.w600,
                      fontSize: 12.5,
                    ),
                  ),
                  if (subtitle != null)
                    Text(
                      subtitle!,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: MoggnitColors.muted, fontSize: 11),
                    ),
                ],
              ),
            ),
            AnimatedContainer(
              duration: const Duration(milliseconds: 280),
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
              decoration: BoxDecoration(
                color: online
                    ? MoggnitColors.cyanSoft
                    : MoggnitColors.red.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                online ? "online" : "offline",
                style: TextStyle(
                  color: online ? MoggnitColors.teal : MoggnitColors.red,
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.3,
                ),
              ),
            ),
            ...?actions,
          ],
        ),
      ),
    );
  }
}

class KpiTile extends StatelessWidget {
  const KpiTile({super.key, required this.label, required this.value, this.accent});

  final String label;
  final String value;
  final Color? accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: MoggnitColors.border.withValues(alpha: 0.85)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label.toUpperCase(),
            style: const TextStyle(
              color: MoggnitColors.muted,
              fontSize: 10,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.6,
            ),
          ),
          const SizedBox(height: 8),
          TweenAnimationBuilder<double>(
            tween: Tween(begin: 0, end: 1),
            duration: const Duration(milliseconds: 520),
            curve: Curves.easeOutCubic,
            builder: (context, t, child) => Opacity(
              opacity: t,
              child: Transform.translate(
                offset: Offset(0, 8 * (1 - t)),
                child: child,
              ),
            ),
            child: Text(
              value,
              style: GoogleFonts.manrope(
                fontSize: 24,
                fontWeight: FontWeight.w800,
                color: accent ?? MoggnitColors.navy,
                height: 1,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class RiskPill extends StatelessWidget {
  const RiskPill(this.risk, {super.key});

  final String? risk;

  @override
  Widget build(BuildContext context) {
    final c = riskColor(risk);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        riskLabel(risk),
        style: TextStyle(color: c, fontSize: 11, fontWeight: FontWeight.w700),
      ),
    );
  }
}

class FadeSlideIn extends StatelessWidget {
  const FadeSlideIn({
    super.key,
    required this.child,
    this.index = 0,
    this.duration = const Duration(milliseconds: 420),
  });

  final Widget child;
  final int index;
  final Duration duration;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: duration + Duration(milliseconds: 40 * index),
      curve: Curves.easeOutCubic,
      builder: (context, t, child) {
        final delayed = ((t * (1 + index * 0.08)) - index * 0.08).clamp(0.0, 1.0);
        return Opacity(
          opacity: delayed,
          child: Transform.translate(
            offset: Offset(0, 14 * (1 - delayed)),
            child: child,
          ),
        );
      },
      child: child,
    );
  }
}

class ShipmentCard extends StatelessWidget {
  const ShipmentCard({
    super.key,
    required this.item,
    required this.onTap,
    this.onDelete,
  });

  final Map<String, dynamic> item;
  final VoidCallback onTap;
  final VoidCallback? onDelete;

  @override
  Widget build(BuildContext context) {
    final ref = item["reference"]?.toString() ?? "";
    final route = item["route_label"]?.toString() ?? "";
    final stage = item["current_stage"]?.toString() ?? "";
    final docs = item["documents_label"]?.toString() ?? "";
    final delay = item["delay_hours"];
    final risk = item["risk_level"]?.toString();

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Ink(
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.78),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: MoggnitColors.border),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Container(width: 4, color: riskColor(risk)),
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(12, 13, 10, 13),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: Text(
                                  ref,
                                  style: GoogleFonts.manrope(
                                    color: MoggnitColors.navy,
                                    fontWeight: FontWeight.w800,
                                    fontSize: 16,
                                  ),
                                ),
                              ),
                              RiskPill(risk),
                              if (onDelete != null)
                                IconButton(
                                  visualDensity: VisualDensity.compact,
                                  onPressed: onDelete,
                                  icon: const Icon(
                                    Icons.delete_outline,
                                    size: 20,
                                    color: MoggnitColors.muted,
                                  ),
                                ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            route,
                            style: const TextStyle(
                              color: MoggnitColors.navySoft,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            "$stage · $docs",
                            style: const TextStyle(color: MoggnitColors.muted, fontSize: 12),
                          ),
                          if (delay != null &&
                              delay.toString() != "0" &&
                              delay.toString() != "0.0")
                            Padding(
                              padding: const EdgeInsets.only(top: 8),
                              child: Text(
                                "Задержка · $delay ч",
                                style: const TextStyle(
                                  color: MoggnitColors.amber,
                                  fontWeight: FontWeight.w700,
                                  fontSize: 12,
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class PageScaffold extends StatelessWidget {
  const PageScaffold({
    super.key,
    required this.header,
    required this.child,
    this.floatingActionButton,
  });

  final Widget header;
  final Widget child;
  final Widget? floatingActionButton;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: MoggnitColors.bg,
      floatingActionButton: floatingActionButton,
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [
              Color(0xFFF3F7FB),
              Color(0xFFE4EEF6),
              Color(0xFFDCE8F2),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: Stack(
          children: [
            Positioned(
              top: -80,
              left: -60,
              child: IgnorePointer(
                child: Container(
                  width: 220,
                  height: 220,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: MoggnitColors.cyan.withValues(alpha: 0.08),
                  ),
                ),
              ),
            ),
            Positioned(
              bottom: 120,
              right: -40,
              child: IgnorePointer(
                child: Container(
                  width: 180,
                  height: 180,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: MoggnitColors.navy.withValues(alpha: 0.05),
                  ),
                ),
              ),
            ),
            Column(
              children: [
                header,
                Expanded(child: child),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
