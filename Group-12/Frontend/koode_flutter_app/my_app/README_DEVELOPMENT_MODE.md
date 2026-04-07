# Development Mode

This document explains how to use the development mode feature that allows you to bypass the sign-in page temporarily for testing purposes.

## What is Development Mode?

Development mode is a feature that allows you to:
- Bypass the authentication flow entirely
- Access the schedule page with mock data
- Test the UI and functionality without needing to sign in
- Develop and debug more efficiently

## How to Enable Development Mode

### Method 1: Long Press on Sign In Screen
1. Run the app and navigate to the sign-in screen
2. Perform a long press anywhere on the screen
3. You'll see a notification that development mode is enabled
4. The app will restart and go directly to the schedule page

### Method 2: Modify the Flag Directly
1. Open `lib/dev_mode.dart`
2. Change `bool isDevelopmentMode = false;` to `bool isDevelopmentMode = true;`
3. Save the file and restart the app

## How to Disable Development Mode

### Method 1: Long Press Again
1. While in development mode, perform another long press on any screen
2. You'll see a notification that development mode is disabled
3. The app will restart and go back to the sign-in screen

### Method 2: Modify the Flag Directly
1. Open `lib/dev_mode.dart`
2. Change `bool isDevelopmentMode = true;` back to `bool isDevelopmentMode = false;`
3. Save the file and restart the app

## Features in Development Mode

When development mode is enabled:
- The app starts directly on the schedule page
- All schedule functionality works with mock data
- No authentication is required
- You can add, edit, and delete events and medications
- All UI elements are fully functional

## Development Mode Indicators

When development mode is active, you'll see:
- A developer mode icon (🔧) next to the app title on the sign-in screen
- "DEVELOPMENT MODE" text instead of "Your health assistant"
- Orange text color for the development mode indicator

## Technical Details

The development mode implementation includes:
- A separate `SchedulePageDev` widget that uses mock data instead of Supabase
- A global flag in `dev_mode.dart` that controls the mode
- Gesture detection on the sign-in screen to toggle the mode
- Automatic app restart when toggling modes

## Limitations

While in development mode:
- No real data is saved to or loaded from Supabase
- Changes are only stored in memory and will be lost when the app restarts
- User authentication features are not available
- Some features that depend on user accounts may not work

## When to Use Development Mode

Development mode is useful for:
- UI testing and debugging
- Rapid prototyping
- Demo purposes
- Development without internet connectivity
- Testing edge cases in the schedule functionality

Remember to disable development mode before deploying to production!