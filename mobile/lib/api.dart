import "dart:convert";

import "package:http/http.dart" as http;

import "config.dart";

class SctApi {
  SctApi({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  Map<String, String> get _headers => {
        "Content-Type": "application/json",
        "X-API-Key": AppConfig.apiKey,
      };

  Uri _u(String path, [Map<String, String>? q]) =>
      Uri.parse("${AppConfig.apiBase}$path").replace(queryParameters: q);

  Future<Map<String, dynamic>> _parse(http.Response res) async {
    if (res.statusCode >= 400) {
      throw Exception("API ${res.statusCode}: ${res.body}");
    }
    if (res.bodyBytes.isEmpty) return {};
    return jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> _get(String path, [Map<String, String>? q]) async {
    final res = await _client.get(_u(path, q), headers: _headers);
    return _parse(res);
  }

  Future<Map<String, dynamic>> _send(
    String method,
    String path, {
    Map<String, dynamic>? body,
  }) async {
    final uri = _u(path);
    final encoded = body == null ? null : jsonEncode(body);
    late http.Response res;
    switch (method) {
      case "POST":
        res = await _client.post(uri, headers: _headers, body: encoded);
        break;
      case "PATCH":
        res = await _client.patch(uri, headers: _headers, body: encoded);
        break;
      case "DELETE":
        res = await _client.delete(uri, headers: _headers);
        break;
      default:
        throw ArgumentError(method);
    }
    return _parse(res);
  }

  Future<Map<String, dynamic>> health() => _get("/health");
  Future<Map<String, dynamic>> overview() => _get("/overview");
  Future<Map<String, dynamic>> shipments() => _get("/shipments");
  Future<Map<String, dynamic>> shipment(String id) => _get("/shipments/$id");
  Future<Map<String, dynamic>> notifications() => _get("/notifications");
  Future<Map<String, dynamic>> tracking() => _get("/tracking");
  Future<Map<String, dynamic>> trackingTick() => _send("POST", "/tracking/tick");

  Future<Map<String, dynamic>> createShipment(Map<String, dynamic> body) =>
      _send("POST", "/shipments", body: body);

  Future<Map<String, dynamic>> updateShipment(String id, Map<String, dynamic> body) =>
      _send("PATCH", "/shipments/$id", body: body);

  Future<Map<String, dynamic>> deleteShipment(String id) =>
      _send("DELETE", "/shipments/$id");

  Future<Map<String, dynamic>> simulate(String id, {String scenario = "storm"}) =>
      _send("POST", "/shipments/$id/simulate", body: {"scenario": scenario});

  Future<Map<String, dynamic>> compareShipments(List<String> ids) =>
      _get("/shipments/compare", {"ids": ids.join(",")});

  Future<Map<String, dynamic>> alternatives(String id) =>
      _get("/shipments/$id/alternatives");

  Future<Map<String, dynamic>> selectAlternative(String id, String alternativeId) =>
      _send(
        "POST",
        "/shipments/$id/select-alternative",
        body: {"alternative_id": alternativeId},
      );

  Future<Map<String, dynamic>> selectVesselRoute(String vesselId, String alternativeId) =>
      _send(
        "POST",
        "/tracking/vessels/$vesselId/select-route",
        body: {"alternative_id": alternativeId},
      );

  Future<Map<String, dynamic>> scenarios() => _get("/scenarios");
  Future<Map<String, dynamic>> analytics() => _get("/analytics");
  Future<Map<String, dynamic>> settings() => _get("/settings");

  Future<Map<String, dynamic>> updateSettings(Map<String, dynamic> body) =>
      _send("PATCH", "/settings", body: body);

  Future<Map<String, dynamic>> documentsRegistry() => _get("/documents/registry");

  Future<Map<String, dynamic>> documentsWorkspace(String shipmentId) =>
      _get("/documents/workspace", {"shipment_id": shipmentId});

  Future<Map<String, dynamic>> addDocument(Map<String, dynamic> body) =>
      _send("POST", "/documents/add", body: body);

  Future<Map<String, dynamic>> fixDocument(String documentId, Map<String, dynamic> body) =>
      _send("POST", "/documents/$documentId/fix", body: body);

  Future<Map<String, dynamic>> precheck(String shipmentId) =>
      _send("POST", "/documents/precheck", body: {"shipment_id": shipmentId});

  Future<Map<String, dynamic>> documentHistory(String documentId) =>
      _get("/documents/$documentId/history");

  Future<Map<String, dynamic>> assistantChat(
    String message, {
    List<Map<String, String>> history = const [],
  }) =>
      _send(
        "POST",
        "/assistant/chat",
        body: {"message": message, "history": history},
      );
}
