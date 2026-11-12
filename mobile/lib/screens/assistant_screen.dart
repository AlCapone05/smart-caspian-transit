import "package:material_ui/material_ui.dart";

import "../api.dart";
import "../theme.dart";

class AssistantScreen extends StatefulWidget {
  const AssistantScreen({super.key});

  @override
  State<AssistantScreen> createState() => _AssistantScreenState();
}

class _AssistantScreenState extends State<AssistantScreen> {
  final _api = SctApi();
  final _input = TextEditingController();
  final _scroll = ScrollController();
  final List<_Msg> _messages = [
    const _Msg(
      role: "assistant",
      text:
          "Поддержка МОГГНИТ. Отвечаю только по Smart Caspian Transit. Выберите вопрос или напишите свой.",
    ),
  ];
  bool _busy = false;

  static const _suggestions = [
    "Что с SCT-2048?",
    "Где сейчас штормы?",
    "Как выбрать обход маршрута?",
    "Какие суда на карте?",
    "Что с документами?",
    "Как сравнить грузы?",
  ];

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _send(String text) async {
    final msg = text.trim();
    if (msg.isEmpty || _busy) return;
    setState(() {
      _busy = true;
      _messages.add(_Msg(role: "user", text: msg));
      _input.clear();
    });
    _jump();
    try {
      final history = _messages
          .where((m) => m.role == "user" || m.role == "assistant")
          .map((m) => {"role": m.role, "content": m.text})
          .toList();
      // drop welcome-only history noise: keep last pairs + current
      final r = await _api.assistantChat(msg, history: history.take(history.length - 1).toList());
      if (!mounted) return;
      setState(() {
        _messages.add(
          _Msg(
            role: "assistant",
            text: r["reply"]?.toString() ?? "Нет ответа",
            refused: r["refused"] == true,
          ),
        );
      });
      _jump();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _messages.add(_Msg(role: "assistant", text: "Ошибка: $e", refused: true));
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _jump() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) return;
      _scroll.animateTo(
        _scroll.position.maxScrollExtent + 80,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final showSuggestions = _messages.length <= 1 && !_busy;

    return Scaffold(
      backgroundColor: MoggnitColors.bg,
      appBar: AppBar(title: const Text("Ассистент")),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              controller: _scroll,
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
              itemCount: _messages.length + (showSuggestions ? 1 : 0),
              itemBuilder: (context, i) {
                if (showSuggestions && i == _messages.length) {
                  return Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: _suggestions
                        .map(
                          (s) => ActionChip(
                            label: Text(s),
                            onPressed: () => _send(s),
                          ),
                        )
                        .toList(),
                  );
                }
                final m = _messages[i];
                final mine = m.role == "user";
                return Align(
                  alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 10),
                    padding: const EdgeInsets.all(12),
                    constraints: BoxConstraints(
                      maxWidth: MediaQuery.sizeOf(context).width * 0.82,
                    ),
                    decoration: BoxDecoration(
                      color: mine
                          ? MoggnitColors.navy
                          : (m.refused
                              ? MoggnitColors.violetSoft
                              : Colors.white.withValues(alpha: 0.95)),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: MoggnitColors.border),
                    ),
                    child: Text(
                      m.text,
                      style: TextStyle(
                        color: mine ? Colors.white : MoggnitColors.navy,
                        height: 1.35,
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _input,
                      minLines: 1,
                      maxLines: 4,
                      decoration: const InputDecoration(
                        hintText: "Спросите про груз, шторм, документы…",
                      ),
                      onSubmitted: _send,
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    onPressed: _busy ? null : () => _send(_input.text),
                    icon: _busy
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Msg {
  const _Msg({required this.role, required this.text, this.refused = false});
  final String role;
  final String text;
  final bool refused;
}
