import 'package:flutter_test/flutter_test.dart';

import 'package:retailer_dashboard/main.dart';

void main() {
  testWidgets('Dashboard shell displays navigation rail',
      (WidgetTester tester) async {
    await tester.pumpWidget(const RetailerDashboardApp());

    // Verify NavigationRail destinations are present.
    expect(find.text('Live Map'), findsOneWidget);
    expect(find.text('Forecasting'), findsOneWidget);
    expect(find.text('Inventory'), findsOneWidget);
  });
}
