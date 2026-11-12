import "package:material_ui/material_ui.dart";

import "api.dart";
import "screens/alerts_screen.dart";
import "screens/more_screen.dart";
import "screens/overview_screen.dart";
import "screens/shipments_screen.dart";
import "screens/splash_screen.dart";
import "screens/tracking_screen.dart";
import "sync.dart";
import "theme.dart";

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MoggnitApp());
}

class MoggnitApp extends StatefulWidget {
  const MoggnitApp({super.key});

  @override
  State<MoggnitApp> createState() => _MoggnitAppState();
}

class _MoggnitAppState extends State<MoggnitApp> {
  late final SctApi _api;
  late final SctSync _sync;
  bool _showSplash = true;

  @override
  void initState() {
    super.initState();
    _api = SctApi();
    _sync = SctSync(_api)..start();
  }

  @override
  void dispose() {
    _sync.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SctSyncScope(
      sync: _sync,
      child: MaterialApp(
        title: "МОГГНИТ",
        debugShowCheckedModeBanner: false,
        theme: buildMoggnitTheme(),
        builder: (context, child) {
          return MediaQuery(
            data: MediaQuery.of(context).copyWith(textScaler: TextScaler.linear(1)),
            child: child ?? const SizedBox.shrink(),
          );
        },
        home: Stack(
          fit: StackFit.expand,
          children: [
            const HomeShell(),
            if (_showSplash)
              SplashScreen(
                sync: _sync,
                onReady: () {
                  if (mounted) setState(() => _showSplash = false);
                },
              ),
          ],
        ),
      ),
    );
  }
}

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final pages = const [
      OverviewScreen(),
      ShipmentsScreen(),
      TrackingScreen(),
      AlertsScreen(),
      MoreScreen(),
    ];
    return Scaffold(
      body: IndexedStack(index: _index, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard),
            label: "Обзор",
          ),
          NavigationDestination(
            icon: Icon(Icons.local_shipping_outlined),
            selectedIcon: Icon(Icons.local_shipping),
            label: "Грузы",
          ),
          NavigationDestination(
            icon: Icon(Icons.map_outlined),
            selectedIcon: Icon(Icons.map),
            label: "Карта",
          ),
          NavigationDestination(
            icon: Icon(Icons.notifications_outlined),
            selectedIcon: Icon(Icons.notifications),
            label: "Алерты",
          ),
          NavigationDestination(
            icon: Icon(Icons.apps_outlined),
            selectedIcon: Icon(Icons.apps),
            label: "Ещё",
          ),
        ],
      ),
    );
  }
}
