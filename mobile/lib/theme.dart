import "package:google_fonts/google_fonts.dart";
import "package:material_ui/material_ui.dart";

/// Maritime dispatch look: deep Caspian navy + sea cyan (not purple-AI defaults).
class MoggnitColors {
  static const navy = Color(0xFF0A1E3A);
  static const navySoft = Color(0xFF1A3354);
  static const cyan = Color(0xFF1BA3C7);
  static const cyanSoft = Color(0xFFD8EEF5);
  static const ink = Color(0xFF0F1C2E);
  static const muted = Color(0xFF5A6B7D);
  static const bg = Color(0xFFE8EFF5);
  static const surface = Color(0xFFF7FAFC);
  static const border = Color(0xFFC9D5E2);
  static const red = Color(0xFF8F4A55);
  static const amber = Color(0xFF8A6A2F);
  static const teal = Color(0xFF0E7EA8);
  static const storm = Color(0xFF9A7A62);
  static const stormSoft = Color(0xFFB8A882);
  // Kept for rare brand accents only
  static const violet = Color(0xFF3D5A80);
  static const violetSoft = Color(0xFFE4ECF3);
}

ThemeData buildMoggnitTheme() {
  final text = GoogleFonts.manropeTextTheme().apply(
    bodyColor: MoggnitColors.ink,
    displayColor: MoggnitColors.navy,
  );
  final scheme = ColorScheme.fromSeed(
    seedColor: MoggnitColors.navy,
    primary: MoggnitColors.navy,
    secondary: MoggnitColors.cyan,
    tertiary: MoggnitColors.teal,
    surface: MoggnitColors.surface,
    brightness: Brightness.light,
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: MoggnitColors.bg,
    textTheme: text,
    appBarTheme: AppBarTheme(
      backgroundColor: Colors.transparent,
      foregroundColor: MoggnitColors.navy,
      elevation: 0,
      centerTitle: false,
      titleTextStyle: GoogleFonts.manrope(
        color: MoggnitColors.navy,
        fontSize: 18,
        fontWeight: FontWeight.w700,
        letterSpacing: 0.15,
      ),
    ),
    cardTheme: CardThemeData(
      elevation: 0,
      color: Colors.white.withValues(alpha: 0.88),
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: MoggnitColors.border),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white.withValues(alpha: 0.92),
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: MoggnitColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: MoggnitColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: MoggnitColors.cyan, width: 1.4),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: MoggnitColors.navy,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: MoggnitColors.navy,
        side: const BorderSide(color: MoggnitColors.border),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: Colors.white.withValues(alpha: 0.96),
      indicatorColor: MoggnitColors.cyanSoft,
      height: 68,
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        final selected = states.contains(WidgetState.selected);
        return GoogleFonts.manrope(
          fontSize: 11,
          fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
          color: selected ? MoggnitColors.navy : MoggnitColors.muted,
        );
      }),
      iconTheme: WidgetStateProperty.resolveWith((states) {
        final selected = states.contains(WidgetState.selected);
        return IconThemeData(
          color: selected ? MoggnitColors.cyan : MoggnitColors.muted,
          size: 22,
        );
      }),
    ),
    floatingActionButtonTheme: const FloatingActionButtonThemeData(
      backgroundColor: MoggnitColors.navy,
      foregroundColor: Colors.white,
    ),
    pageTransitionsTheme: const PageTransitionsTheme(
      builders: {
        TargetPlatform.iOS: ZoomPageTransitionsBuilder(),
        TargetPlatform.android: ZoomPageTransitionsBuilder(),
      },
    ),
  );
}

Color riskColor(String? risk) {
  switch (risk) {
    case "high":
      return MoggnitColors.red;
    case "medium":
      return MoggnitColors.amber;
    default:
      return MoggnitColors.teal;
  }
}

String riskLabel(String? risk) {
  switch (risk) {
    case "high":
      return "высокий";
    case "medium":
      return "средний";
    case "low":
      return "низкий";
    default:
      return risk ?? "—";
  }
}
