import "package:material_ui/material_ui.dart";

import "../api.dart";
import "../theme.dart";

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _api = SctApi();
  Map<String, dynamic>? _settings;
  String? _error;
  bool _saved = false;
  bool _busy = false;

  final _name = TextEditingController();
  final _role = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _name.dispose();
    _role.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final s = await _api.settings();
      if (!mounted) return;
      setState(() {
        _settings = s;
        _name.text = s["operator_name"]?.toString() ?? "";
        _role.text = s["operator_role"]?.toString() ?? "";
      });
    } catch (e) {
      setState(() => _error = "$e");
    }
  }

  Future<void> _save() async {
    final s = _settings;
    if (s == null) return;
    setState(() {
      _busy = true;
      _error = null;
      _saved = false;
    });
    try {
      final next = await _api.updateSettings({
        "display_timezone": s["display_timezone"],
        "notifications_enabled": s["notifications_enabled"],
        "demo_mode": s["demo_mode"],
        "default_scenario": s["default_scenario"],
        "co2_uncertainty_pct": s["co2_uncertainty_pct"],
        "operator_name": _name.text.trim(),
        "operator_role": _role.text.trim(),
        "locale": s["locale"],
      });
      if (!mounted) return;
      setState(() {
        _settings = next;
        _saved = true;
      });
    } catch (e) {
      setState(() => _error = "$e");
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = _settings;
    return Scaffold(
      backgroundColor: MoggnitColors.bg,
      appBar: AppBar(title: const Text("Настройки")),
      body: s == null
          ? Center(child: _error != null ? Text(_error!) : const CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
              children: [
                const Text(
                  "Параметры общие с сайтом — сохраняются на сервере",
                  style: TextStyle(color: MoggnitColors.muted, fontSize: 13),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: _name,
                  decoration: const InputDecoration(labelText: "Оператор"),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: _role,
                  decoration: const InputDecoration(labelText: "Роль"),
                ),
                const SizedBox(height: 10),
                DropdownButtonFormField<String>(
                  key: ValueKey(s["default_scenario"]?.toString() ?? "storm"),
                  initialValue: s["default_scenario"]?.toString() ?? "storm",
                  decoration: const InputDecoration(labelText: "Сценарий по умолчанию"),
                  items: const [
                    DropdownMenuItem(value: "normal", child: Text("Обычные")),
                    DropdownMenuItem(value: "storm", child: Text("Шторм")),
                    DropdownMenuItem(value: "port_congestion", child: Text("Перегрузка порта")),
                  ],
                  onChanged: (v) => setState(() => s["default_scenario"] = v),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text("Уведомления"),
                  value: s["notifications_enabled"] == true,
                  onChanged: (v) => setState(() => s["notifications_enabled"] = v),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text("Режим разработки"),
                  value: s["demo_mode"] == true,
                  onChanged: (v) => setState(() => s["demo_mode"] = v),
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text("CO₂e неопределённость ±${s["co2_uncertainty_pct"] ?? 0}%"),
                  subtitle: Slider(
                    value: ((s["co2_uncertainty_pct"] as num?)?.toDouble() ?? 10).clamp(0, 40),
                    min: 0,
                    max: 40,
                    divisions: 8,
                    label: "±${s["co2_uncertainty_pct"]}",
                    onChanged: (v) => setState(() => s["co2_uncertainty_pct"] = v.round()),
                  ),
                ),
                if (_error != null)
                  Text(_error!, style: const TextStyle(color: MoggnitColors.red)),
                if (_saved)
                  const Text("Сохранено", style: TextStyle(color: MoggnitColors.teal)),
                const SizedBox(height: 12),
                FilledButton(
                  onPressed: _busy ? null : _save,
                  child: const Text("Сохранить"),
                ),
              ],
            ),
    );
  }
}
