import "package:material_ui/material_ui.dart";

import "../api.dart";
import "../theme.dart";

class DocumentsScreen extends StatefulWidget {
  const DocumentsScreen({super.key, this.initialShipmentId});

  final String? initialShipmentId;

  @override
  State<DocumentsScreen> createState() => _DocumentsScreenState();
}

class _DocumentsScreenState extends State<DocumentsScreen> {
  final _api = SctApi();
  List<Map<String, dynamic>> _registry = [];
  String? _shipmentId;
  Map<String, dynamic>? _workspace;
  String? _error;
  String? _message;
  bool _busy = false;
  final _hs = TextEditingController();

  @override
  void initState() {
    super.initState();
    _boot();
  }

  @override
  void dispose() {
    _hs.dispose();
    super.dispose();
  }

  Future<void> _boot() async {
    try {
      final reg = await _api.documentsRegistry();
      final items = ((reg["items"] as List?) ?? [])
          .map((e) => (e as Map).cast<String, dynamic>())
          .toList();
      final next = widget.initialShipmentId ??
          reg["default_shipment_id"]?.toString() ??
          (items.isNotEmpty ? items.first["shipment_id"]?.toString() : null);
      setState(() {
        _registry = items;
        _shipmentId = next;
      });
      if (next != null) await _load(next);
    } catch (e) {
      setState(() => _error = "$e");
    }
  }

  Future<void> _load(String id) async {
    setState(() {
      _error = null;
      _message = null;
    });
    try {
      final ws = await _api.documentsWorkspace(id);
      if (!mounted) return;
      setState(() => _workspace = ws);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = "$e");
    }
  }

  Future<void> _fix(Map<String, dynamic> doc, {required bool hs}) async {
    final shipmentId = _shipmentId;
    if (shipmentId == null) return;
    setState(() {
      _busy = true;
      _error = null;
      _message = null;
    });
    try {
      if (hs) {
        final code = _hs.text.trim();
        if (!RegExp(r"^\d{10}$").hasMatch(code)) {
          throw Exception("Код ТН ВЭД должен состоять из 10 цифр");
        }
        await _api.addDocument({
          "shipment_id": shipmentId,
          "document_id": doc["id"],
          "document_type": doc["document_type"],
          "hs_code": code,
        });
        _hs.clear();
        _message = "Код ТН ВЭД сохранён";
      } else {
        await _api.addDocument({
          "shipment_id": shipmentId,
          "document_id": doc["id"],
          "document_type": doc["document_type"],
          "mark_file_added": true,
          "file_name": "${doc["document_type"] ?? "document"}_demo.pdf",
        });
        _message = "Файл отмечен как добавленный";
      }
      await _load(shipmentId);
    } catch (e) {
      _error = "$e";
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _precheck() async {
    final shipmentId = _shipmentId;
    if (shipmentId == null) return;
    setState(() => _busy = true);
    try {
      final r = await _api.precheck(shipmentId);
      setState(() => _message = r["message"]?.toString() ?? "Готово");
      await _load(shipmentId);
    } catch (e) {
      setState(() => _error = "$e");
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final docs = ((_workspace?["documents"] as List?) ?? [])
        .map((e) => (e as Map).cast<String, dynamic>())
        .toList();

    return Scaffold(
      backgroundColor: MoggnitColors.bg,
      appBar: AppBar(
        title: const Text("Документы"),
        actions: [
          IconButton(onPressed: _boot, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: [
          const Text(
            "Реестр и рабочее место — те же данные, что на сайте",
            style: TextStyle(color: MoggnitColors.muted, fontSize: 13),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            key: ValueKey(_shipmentId),
            initialValue: _shipmentId,
            decoration: const InputDecoration(labelText: "Перевозка"),
            items: _registry
                .map(
                  (r) => DropdownMenuItem(
                    value: r["shipment_id"]?.toString(),
                    child: Text(
                      "${r["reference"]} · ${r["completeness_label"] ?? ""}",
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                )
                .toList(),
            onChanged: (v) {
              if (v == null) return;
              setState(() => _shipmentId = v);
              _load(v);
            },
          ),
          if (_error != null) ...[
            const SizedBox(height: 10),
            Text(_error!, style: const TextStyle(color: MoggnitColors.red)),
          ],
          if (_message != null) ...[
            const SizedBox(height: 10),
            Text(_message!, style: const TextStyle(color: MoggnitColors.teal)),
          ],
          if (_workspace != null) ...[
            const SizedBox(height: 14),
            Text(
              _workspace!["completeness_label"]?.toString() ??
                  _workspace!["title"]?.toString() ??
                  "Комплект",
              style: const TextStyle(
                color: MoggnitColors.navy,
                fontWeight: FontWeight.w800,
                fontSize: 16,
              ),
            ),
            const SizedBox(height: 8),
            FilledButton(
              onPressed: _busy ? null : _precheck,
              child: const Text("Предпроверка комплекта"),
            ),
          ],
          const SizedBox(height: 12),
          ...docs.map((doc) {
            final ok = doc["status"]?.toString() == "ready" ||
                doc["status"]?.toString() == "ok" ||
                doc["complete"] == true;
            return Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.94),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: MoggnitColors.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          doc["title"]?.toString() ??
                              doc["document_type"]?.toString() ??
                              "Документ",
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                      ),
                      Text(
                        ok ? "OK" : (doc["status_label"]?.toString() ?? "нужно"),
                        style: TextStyle(
                          color: ok ? MoggnitColors.teal : MoggnitColors.amber,
                          fontWeight: FontWeight.w700,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                  if (doc["issue"] != null || doc["detail"] != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text(
                        "${doc["issue"] ?? doc["detail"]}",
                        style: const TextStyle(color: MoggnitColors.muted, fontSize: 12),
                      ),
                    ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      OutlinedButton(
                        onPressed: _busy ? null : () => _fix(doc, hs: false),
                        child: const Text("Файл добавлен"),
                      ),
                      if ((doc["needs_hs"] == true) ||
                          (doc["document_type"]?.toString().contains("invoice") ?? false) ||
                          (doc["title"]?.toString().toLowerCase().contains("инвойс") ?? false))
                        OutlinedButton(
                          onPressed: _busy
                              ? null
                              : () async {
                                  final code = await showDialog<String>(
                                    context: context,
                                    builder: (ctx) => AlertDialog(
                                      title: const Text("Код ТН ВЭД"),
                                      content: TextField(
                                        controller: _hs,
                                        keyboardType: TextInputType.number,
                                        decoration: const InputDecoration(
                                          hintText: "10 цифр",
                                        ),
                                      ),
                                      actions: [
                                        TextButton(
                                          onPressed: () => Navigator.pop(ctx),
                                          child: const Text("Отмена"),
                                        ),
                                        TextButton(
                                          onPressed: () => Navigator.pop(ctx, _hs.text),
                                          child: const Text("Сохранить"),
                                        ),
                                      ],
                                    ),
                                  );
                                  if (code != null) await _fix(doc, hs: true);
                                },
                          child: const Text("ТН ВЭД"),
                        ),
                    ],
                  ),
                ],
              ),
            );
          }),
          if (docs.isEmpty && _workspace != null)
            const Text("Нет документов в workspace", style: TextStyle(color: MoggnitColors.muted)),
        ],
      ),
    );
  }
}
