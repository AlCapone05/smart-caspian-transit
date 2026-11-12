import "dart:async";
import "dart:math" as math;
import "dart:ui" as ui;

import "package:google_fonts/google_fonts.dart";
import "package:material_ui/material_ui.dart";

import "../sync.dart";
import "../theme.dart";

/// Новый splash с нуля по логотипу сайта МОГГНИТ.
class SplashScreen extends StatefulWidget {
  const SplashScreen({
    super.key,
    required this.sync,
    required this.onReady,
  });

  final SctSync sync;
  final VoidCallback onReady;

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> with TickerProviderStateMixin {
  late final AnimationController _intro;
  late final AnimationController _wave;
  late final AnimationController _route;
  late final AnimationController _pulse;
  late final AnimationController _fadeOut;

  late final Animation<double> _logoScale;
  late final Animation<double> _logoOpacity;
  late final Animation<double> _textOpacity;
  late final Animation<Offset> _textSlide;
  late final Animation<double> _loaderOpacity;

  bool _finished = false;
  bool _minDone = false;
  bool _dataDone = false;
  Timer? _minTimer;
  Timer? _maxTimer;

  @override
  void initState() {
    super.initState();

    _intro = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    );
    _wave = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2800),
    )..repeat();
    _route = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2200),
    )..repeat();
    _pulse = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat(reverse: true);
    _fadeOut = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 480),
    );

    _logoScale = CurvedAnimation(
      parent: _intro,
      curve: const Interval(0.0, 0.55, curve: Curves.easeOutBack),
    );
    _logoOpacity = CurvedAnimation(
      parent: _intro,
      curve: const Interval(0.0, 0.4, curve: Curves.easeOut),
    );
    _textOpacity = CurvedAnimation(
      parent: _intro,
      curve: const Interval(0.45, 0.85, curve: Curves.easeOut),
    );
    _textSlide = Tween<Offset>(
      begin: const Offset(0, 0.22),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _intro,
        curve: const Interval(0.45, 0.9, curve: Curves.easeOutCubic),
      ),
    );
    _loaderOpacity = CurvedAnimation(
      parent: _intro,
      curve: const Interval(0.7, 1.0, curve: Curves.easeOut),
    );

    _intro.forward();

    widget.sync.addListener(_onSync);
    _onSync();

    _minTimer = Timer(const Duration(milliseconds: 2600), () {
      _minDone = true;
      _checkReady();
    });
    _maxTimer = Timer(const Duration(seconds: 7), _forceFinish);
  }

  void _onSync() {
    final s = widget.sync;
    if (!s.loading && (s.overview != null || s.error != null || s.generation > 0)) {
      _dataDone = true;
      _checkReady();
    }
  }

  void _checkReady() {
    if (_minDone && _dataDone) _forceFinish();
  }

  Future<void> _forceFinish() async {
    if (_finished || !mounted) return;
    _finished = true;
    await _fadeOut.forward();
    if (!mounted) return;
    widget.onReady();
  }

  @override
  void dispose() {
    _minTimer?.cancel();
    _maxTimer?.cancel();
    widget.sync.removeListener(_onSync);
    _intro.dispose();
    _wave.dispose();
    _route.dispose();
    _pulse.dispose();
    _fadeOut.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.sizeOf(context);

    return FadeTransition(
      opacity: Tween<double>(begin: 1, end: 0).animate(
        CurvedAnimation(parent: _fadeOut, curve: Curves.easeInOutCubic),
      ),
      child: Scaffold(
        body: Stack(
          fit: StackFit.expand,
          children: [
            const DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    Color(0xFFF7FBFE),
                    Color(0xFFEEF4FA),
                    Color(0xFFE8F0F7),
                  ],
                ),
              ),
            ),
            // Ambient blobs
            Positioned(
              top: -size.height * 0.12,
              right: -size.width * 0.2,
              child: AnimatedBuilder(
                animation: _pulse,
                builder: (_, _) => _GlowOrb(
                  size: size.width * 0.72,
                  color: const Color(0xFF6F3CC9).withValues(alpha: 0.1 + _pulse.value * 0.06),
                ),
              ),
            ),
            Positioned(
              bottom: size.height * 0.08,
              left: -size.width * 0.25,
              child: AnimatedBuilder(
                animation: _pulse,
                builder: (_, _) => _GlowOrb(
                  size: size.width * 0.8,
                  color: const Color(0xFF0EA5D8).withValues(alpha: 0.1 + (1 - _pulse.value) * 0.05),
                ),
              ),
            ),
            // Animated Caspian waves behind logo
            Positioned(
              left: 0,
              right: 0,
              top: size.height * 0.28,
              height: 120,
              child: AnimatedBuilder(
                animation: _wave,
                builder: (_, _) => CustomPaint(
                  painter: _WavePainter(t: _wave.value),
                ),
              ),
            ),
            // Center brand
            SafeArea(
              child: Center(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 36),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      ScaleTransition(
                        scale: Tween<double>(begin: 0.82, end: 1).animate(_logoScale),
                        child: FadeTransition(
                          opacity: _logoOpacity,
                          child: AnimatedBuilder(
                            animation: _pulse,
                            builder: (_, child) {
                              return Container(
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(28),
                                  boxShadow: [
                                    BoxShadow(
                                      color: const Color(0xFF0B1F44)
                                          .withValues(alpha: 0.08 + _pulse.value * 0.06),
                                      blurRadius: 28 + _pulse.value * 10,
                                      offset: const Offset(0, 12),
                                    ),
                                  ],
                                ),
                                child: child,
                              );
                            },
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(24),
                              child: Image.asset(
                                "assets/moggnit_logo.jpg",
                                width: math.min(size.width * 0.72, 300),
                                fit: BoxFit.contain,
                                errorBuilder: (_, _, _) => _FallbackMark(),
                              ),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 28),
                      // Drawing transit route under logo
                      SizedBox(
                        height: 36,
                        width: math.min(size.width * 0.7, 280),
                        child: AnimatedBuilder(
                          animation: Listenable.merge([_route, _pulse]),
                          builder: (_, _) => CustomPaint(
                            painter: _RoutePainter(
                              progress: Curves.easeInOut.transform(
                                ((_route.value * 1.15) % 1.0),
                              ),
                              pulse: _pulse.value,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 18),
                      SlideTransition(
                        position: _textSlide,
                        child: FadeTransition(
                          opacity: _textOpacity,
                          child: Column(
                            children: [
                              Text(
                                "МОГГНИТ",
                                style: GoogleFonts.exo2(
                                  color: MoggnitColors.navy,
                                  fontSize: 34,
                                  fontWeight: FontWeight.w800,
                                  fontStyle: FontStyle.italic,
                                  letterSpacing: 1.2,
                                  height: 1.05,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Container(
                                    width: 18,
                                    height: 1.5,
                                    color: const Color(0xFF6F3CC9).withValues(alpha: 0.75),
                                  ),
                                  const SizedBox(width: 10),
                                  Text(
                                    "Smart Caspian Transit",
                                    style: GoogleFonts.exo2(
                                      color: MoggnitColors.navySoft,
                                      fontSize: 14,
                                      fontWeight: FontWeight.w600,
                                      fontStyle: FontStyle.italic,
                                      letterSpacing: 0.2,
                                    ),
                                  ),
                                  const SizedBox(width: 10),
                                  Container(
                                    width: 18,
                                    height: 1.5,
                                    color: const Color(0xFF6F3CC9).withValues(alpha: 0.75),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 42),
                      FadeTransition(
                        opacity: _loaderOpacity,
                        child: Column(
                          children: [
                            SizedBox(
                              width: 160,
                              child: AnimatedBuilder(
                                animation: _route,
                                builder: (_, _) {
                                  final p = ((_route.value * 0.85) + 0.12).clamp(0.12, 0.97);
                                  return ClipRRect(
                                    borderRadius: BorderRadius.circular(99),
                                    child: LinearProgressIndicator(
                                      value: p,
                                      minHeight: 4,
                                      backgroundColor: const Color(0xFFD7E0EA),
                                      color: const Color(0xFF6F3CC9),
                                    ),
                                  );
                                },
                              ),
                            ),
                            const SizedBox(height: 12),
                            AnimatedBuilder(
                              animation: _route,
                              builder: (_, _) {
                                final phase = (_route.value * 3).floor() % 4;
                                final dots = "." * phase.clamp(0, 3);
                                return Text(
                                  "Загрузка диспетчерской$dots",
                                  style: GoogleFonts.manrope(
                                    color: MoggnitColors.muted,
                                    fontSize: 13,
                                    fontWeight: FontWeight.w600,
                                  ),
                                );
                              },
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _GlowOrb extends StatelessWidget {
  const _GlowOrb({required this.size, required this.color});
  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: RadialGradient(colors: [color, color.withValues(alpha: 0)]),
        ),
      ),
    );
  }
}

class _FallbackMark extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 180,
      height: 140,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        gradient: const LinearGradient(
          colors: [Color(0xFF0B1F44), Color(0xFF6F3CC9)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: Text(
        "М",
        style: GoogleFonts.exo2(
          color: Colors.white,
          fontSize: 72,
          fontWeight: FontWeight.w800,
          fontStyle: FontStyle.italic,
        ),
      ),
    );
  }
}

class _WavePainter extends CustomPainter {
  _WavePainter({required this.t});
  final double t;

  @override
  void paint(Canvas canvas, Size size) {
    void drawWave(Color color, double amp, double phase, double yBias) {
      final path = ui.Path();
      path.moveTo(-20, size.height);
      for (double x = -20; x <= size.width + 20; x += 4) {
        final y = yBias +
            math.sin((x / size.width * math.pi * 2) + t * math.pi * 2 + phase) * amp +
            math.sin((x / size.width * math.pi * 4) - t * math.pi * 2) * (amp * 0.35);
        path.lineTo(x, y);
      }
      path.lineTo(size.width + 20, size.height + 20);
      path.lineTo(-20, size.height + 20);
      path.close();
      canvas.drawPath(
        path,
        Paint()..color = color.withValues(alpha: 0.22),
      );
    }

    drawWave(const Color(0xFF0EA5D8), 10, 0, size.height * 0.42);
    drawWave(const Color(0xFF6F3CC9), 12, 1.2, size.height * 0.55);
  }

  @override
  bool shouldRepaint(covariant _WavePainter oldDelegate) => oldDelegate.t != t;
}

class _RoutePainter extends CustomPainter {
  _RoutePainter({required this.progress, required this.pulse});
  final double progress;
  final double pulse;

  @override
  void paint(Canvas canvas, Size size) {
    final y = size.height * 0.55;
    final start = Offset(8, y);
    final mid1 = Offset(size.width * 0.32, y - 8);
    final mid2 = Offset(size.width * 0.62, y + 6);
    final end = Offset(size.width - 8, y - 4);

    final full = ui.Path()
      ..moveTo(start.dx, start.dy)
      ..cubicTo(mid1.dx, mid1.dy, mid2.dx, mid2.dy, end.dx, end.dy);

    final metrics = full.computeMetrics().toList();
    if (metrics.isEmpty) return;
    final metric = metrics.first;

    final track = Paint()
      ..color = const Color(0xFFB7C7D8)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.2
      ..strokeCap = StrokeCap.round;
    canvas.drawPath(metric.extractPath(0, metric.length), track);

    final drawn = metric.extractPath(0, metric.length * progress);
    final active = Paint()
      ..shader = ui.Gradient.linear(
        start,
        end,
        const [Color(0xFF0EA5D8), Color(0xFF6F3CC9)],
      )
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round;
    canvas.drawPath(drawn, active);

    final nodes = [0.18, 0.48, 0.78];
    for (final n in nodes) {
      final tan = metric.getTangentForOffset(metric.length * n);
      if (tan == null) continue;
      final lit = progress >= n;
      final r = lit ? 4.2 + pulse * 1.2 : 3.2;
      canvas.drawCircle(
        tan.position,
        r + 2,
        Paint()..color = const Color(0xFF6F3CC9).withValues(alpha: lit ? 0.2 : 0.08),
      );
      canvas.drawCircle(
        tan.position,
        r,
        Paint()
          ..color = lit ? const Color(0xFF6F3CC9) : Colors.white
          ..style = PaintingStyle.fill,
      );
      canvas.drawCircle(
        tan.position,
        r,
        Paint()
          ..color = const Color(0xFF6F3CC9)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.6,
      );
    }

    // Arrow tip at progress head
    final tip = metric.getTangentForOffset(metric.length * progress.clamp(0.02, 1));
    if (tip != null) {
      final ang = tip.angle;
      final p = tip.position;
      final path = ui.Path()
        ..moveTo(p.dx + math.cos(ang) * 8, p.dy + math.sin(ang) * 8)
        ..lineTo(
          p.dx + math.cos(ang + 2.5) * 7,
          p.dy + math.sin(ang + 2.5) * 7,
        )
        ..lineTo(
          p.dx + math.cos(ang - 2.5) * 7,
          p.dy + math.sin(ang - 2.5) * 7,
        )
        ..close();
      canvas.drawPath(path, Paint()..color = const Color(0xFF6F3CC9));
    }
  }

  @override
  bool shouldRepaint(covariant _RoutePainter oldDelegate) =>
      oldDelegate.progress != progress || oldDelegate.pulse != pulse;
}
