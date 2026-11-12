import "package:material_ui/material_ui.dart";

import "../sync.dart";
import "../theme.dart";

const _ports = [
  ("port_astrakhan", "Астрахань"),
  ("port_makhachkala", "Махачкала"),
  ("port_aktau", "Актау"),
  ("port_baku", "Баку"),
  ("port_anzali", "Энзели"),
];

const _stages = [
  "Планирование",
  "Ж/Д к порту",
  "Портовая обработка",
  "Морской переход",
  "Выгрузка",
  "Автодоставка",
  "Завершено",
];

class CreateShipmentScreen extends StatefulWidget {
  const CreateShipmentScreen({super.key});

  @override
  State<CreateShipmentScreen> createState() => _CreateShipmentScreenState();
}

class _CreateShipmentScreenState extends State<CreateShipmentScreen> {
  final _ref = TextEditingController(text: "SCT-2050");
  final _cargo = TextEditingController(text: "Контейнерный груз");
  final _tonnes = TextEditingController(text: "22");
  final _container = TextEditingController();
  final _vessel = TextEditingController();
  String _origin = "port_astrakhan";
  String _dest = "port_anzali";
  String _stage = "Планирование";
  String _risk = "low";
  bool _createVessel = true;
  bool _busy = false;
  bool _hintReady = false;
  String? _error;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_hintReady) return;
    _hintReady = true;
    final sync = SctSyncScope.of(context);
    final nums = sync.shipments
        .map((s) {
          final m = RegExp(r"^SCT-(\d+)$", caseSensitive: false)
              .firstMatch(s["reference"]?.toString() ?? "");
          return m == null ? 0 : int.tryParse(m.group(1)!) ?? 0;
        })
        .where((n) => n > 0);
    final next = (nums.isEmpty ? 2048 : nums.reduce((a, b) => a > b ? a : b)) + 1;
    _ref.text = "SCT-$next";
  }

  @override
  void dispose() {
    _ref.dispose();
    _cargo.dispose();
    _tonnes.dispose();
    _container.dispose();
    _vessel.dispose();
    super.dispose();
  }

  String get _originLabel => _ports.firstWhere((p) => p.$1 == _origin).$2;
  String get _destLabel => _ports.firstWhere((p) => p.$1 == _dest).$2;

  Future<void> _submit() async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final sync = SctSyncScope.of(context);
      final created = await sync.createShipment({
        "reference": _ref.text.trim(),
        "cargo_description": _cargo.text.trim(),
        "cargo_tonnes": double.tryParse(_tonnes.text.replaceAll(",", ".")) ?? 22,
        "container_no": _container.text.trim().isEmpty ? null : _container.text.trim(),
        "equipment": "1 × 40′ HC",
        "route_from": _originLabel,
        "route_to": _destLabel,
        "origin_port_id": _origin,
        "destination_port_id": _dest,
        "current_stage": _stage,
        "current_location": _originLabel,
        "status": "planned",
        "risk_level": _risk,
        "delay_hours": 0,
        "create_vessel": _createVessel,
        if (_vessel.text.trim().isNotEmpty) "vessel_name": _vessel.text.trim(),
      });
      if (!mounted) return;
      Navigator.of(context).pop(created["reference"]?.toString() ?? created["id"]?.toString());
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: MoggnitColors.bg,
      appBar: AppBar(
        title: const Text("Новая перевозка"),
        backgroundColor: Colors.white,
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: [
          const Text(
            "Создаётся в общей базе диспетчерской — сразу видно на сайте и в боте.",
            style: TextStyle(color: MoggnitColors.muted, fontSize: 13),
          ),
          const SizedBox(height: 16),
          TextField(controller: _ref, decoration: const InputDecoration(labelText: "Референс")),
          const SizedBox(height: 12),
          TextField(controller: _cargo, decoration: const InputDecoration(labelText: "Груз")),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _tonnes,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(labelText: "Тоннаж"),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextField(
                  controller: _container,
                  decoration: const InputDecoration(labelText: "Контейнер"),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _origin,
            decoration: const InputDecoration(labelText: "Порт отправления"),
            items: [
              for (final p in _ports) DropdownMenuItem(value: p.$1, child: Text(p.$2)),
            ],
            onChanged: (v) => setState(() => _origin = v ?? _origin),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _dest,
            decoration: const InputDecoration(labelText: "Порт назначения"),
            items: [
              for (final p in _ports) DropdownMenuItem(value: p.$1, child: Text(p.$2)),
            ],
            onChanged: (v) => setState(() => _dest = v ?? _dest),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _stage,
            decoration: const InputDecoration(labelText: "Этап"),
            items: [for (final s in _stages) DropdownMenuItem(value: s, child: Text(s))],
            onChanged: (v) => setState(() => _stage = v ?? _stage),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _risk,
            decoration: const InputDecoration(labelText: "Риск"),
            items: const [
              DropdownMenuItem(value: "low", child: Text("низкий")),
              DropdownMenuItem(value: "medium", child: Text("средний")),
              DropdownMenuItem(value: "high", child: Text("высокий")),
            ],
            onChanged: (v) => setState(() => _risk = v ?? _risk),
          ),
          const SizedBox(height: 8),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text("Судно на карте Каспия"),
            value: _createVessel,
            activeThumbColor: MoggnitColors.violet,
            onChanged: (v) => setState(() => _createVessel = v),
          ),
          if (_createVessel)
            TextField(
              controller: _vessel,
              decoration: InputDecoration(
                labelText: "Имя судна",
                hintText: "MV ${_ref.text}",
              ),
            ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: MoggnitColors.red)),
          ],
          const SizedBox(height: 20),
          FilledButton(
            onPressed: _busy ? null : _submit,
            child: Text(_busy ? "Создание…" : "Создать перевозку"),
          ),
        ],
      ),
    );
  }
}
