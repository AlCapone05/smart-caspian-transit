/// API той же диспетчерской, что веб и TG-бот.
///
/// Симулятор iOS: обычно http://127.0.0.1:8002
/// Реальный iPhone: http://IP_ВАШЕГО_MAC:8002  (Mac и телефон в одной Wi‑Fi)
class AppConfig {
  static const apiBase = String.fromEnvironment(
    "API_BASE",
    defaultValue: "http://127.0.0.1:8002/api/v1",
  );
  static const apiKey = String.fromEnvironment(
    "API_KEY",
    defaultValue: "demo-key",
  );
}
