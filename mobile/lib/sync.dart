import "dart:async";

import "package:material_ui/material_ui.dart";

import "api.dart";

/// Единый кэш данных диспетчерской — тот же API, что веб и TG.
class SctSync extends ChangeNotifier {
  SctSync(this.api);

  final SctApi api;

  Map<String, dynamic>? overview;
  Map<String, dynamic>? tracking;
  List<Map<String, dynamic>> shipments = [];
  List<Map<String, dynamic>> notifications = [];
  String? error;
  bool loading = true;
  bool online = false;
  int generation = 0;

  Timer? _timer;
  bool _busy = false;

  void start({Duration interval = const Duration(seconds: 4)}) {
    refresh();
    _timer?.cancel();
    _timer = Timer.periodic(interval, (_) => refresh(silent: true));
  }

  void stop() {
    _timer?.cancel();
    _timer = null;
  }

  @override
  void dispose() {
    stop();
    super.dispose();
  }

  Future<void> refresh({bool silent = false}) async {
    if (_busy) return;
    _busy = true;
    if (!silent) {
      loading = overview == null && shipments.isEmpty;
      notifyListeners();
    }
    try {
      final results = await Future.wait([
        api.overview(),
        api.shipments(),
        api.notifications(),
        api.tracking().catchError((_) => <String, dynamic>{}),
        api.health().catchError((_) => <String, dynamic>{"status": "down"}),
      ]);
      overview = results[0];
      final items = (results[1]["items"] as List?) ?? [];
      shipments = items.map((e) => (e as Map).cast<String, dynamic>()).toList();
      final notes = (results[2]["items"] as List?) ?? [];
      notifications = notes.map((e) => (e as Map).cast<String, dynamic>()).toList();
      tracking = results[3].isEmpty ? tracking : results[3];
      online = results[4]["status"]?.toString() == "ok";
      error = null;
      generation++;

      // Advance vessel GPS on the same cadence as the website live map
      unawaited(api.trackingTick().then((t) {
        tracking = t;
        notifyListeners();
      }).catchError((_) {}));
    } catch (e) {
      error = e.toString();
      online = false;
    } finally {
      loading = false;
      _busy = false;
      notifyListeners();
    }
  }

  Future<Map<String, dynamic>> createShipment(Map<String, dynamic> body) async {
    final created = await api.createShipment(body);
    await refresh();
    return created;
  }

  Future<Map<String, dynamic>> updateShipment(String id, Map<String, dynamic> body) async {
    final updated = await api.updateShipment(id, body);
    await refresh();
    return updated;
  }

  Future<void> deleteShipment(String id) async {
    await api.deleteShipment(id);
    await refresh();
  }

  Future<Map<String, dynamic>> simulate(String id, {String scenario = "storm"}) async {
    final res = await api.simulate(id, scenario: scenario);
    await refresh();
    return res;
  }

  Future<Map<String, dynamic>> selectVesselRoute(String vesselId, String altId) async {
    final res = await api.selectVesselRoute(vesselId, altId);
    tracking = res;
    notifyListeners();
    await refresh(silent: true);
    return res;
  }

  Future<Map<String, dynamic>> selectAlternative(String shipmentId, String altId) async {
    final res = await api.selectAlternative(shipmentId, altId);
    await refresh();
    return res;
  }
}

class SctSyncScope extends InheritedNotifier<SctSync> {
  const SctSyncScope({
    super.key,
    required SctSync sync,
    required super.child,
  }) : super(notifier: sync);

  static SctSync of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<SctSyncScope>();
    assert(scope != null, "SctSyncScope not found");
    return scope!.notifier!;
  }
}
