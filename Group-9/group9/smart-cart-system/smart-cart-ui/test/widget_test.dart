import 'package:flutter_test/flutter_test.dart';

import 'package:smart_cart_ui/main.dart';

void main() {
  testWidgets('App renders OTP screen', (WidgetTester tester) async {
    await tester.pumpWidget(const SmartCartApp());

    // Verify the OTP screen title is shown
    expect(find.text('Smart Cart'), findsOneWidget);
    expect(find.text('Start Shopping'), findsOneWidget);
  });
}
