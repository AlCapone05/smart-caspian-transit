import "package:flutter_test/flutter_test.dart";
import "package:moggnit_app/main.dart";

void main() {
  testWidgets("app boots", (tester) async {
    await tester.pumpWidget(const MoggnitApp());
    expect(find.text("МОГГНИТ"), findsOneWidget);
  });
}
