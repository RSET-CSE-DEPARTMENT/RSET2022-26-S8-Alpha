# Supabase Setup Guide

## Prerequisites
1. Create a Supabase account at https://supabase.com
2. Create a new project in Supabase

## Steps to Configure

### 1. Get Your Supabase Credentials
- Go to your Supabase project dashboard
- Navigate to **Settings** → **API**
- Copy your:
  - **Project URL** (under "URL")
  - **Anon Key** (under "anon [public]")

### 2. Update main.dart
In `lib/main.dart`, replace the placeholder values:

```dart
await Supabase.initialize(
  url: 'YOUR_SUPABASE_URL',  // Replace with your actual URL
  anonKey: 'YOUR_SUPABASE_ANON_KEY',  // Replace with your actual Anon Key
);
```

Example:
```dart
await Supabase.initialize(
  url: 'https://your-project.supabase.co',
  anonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
);
```

### 3. Database Setup
Run the SQL scripts in the following files to set up the required tables:
1. `SUPABASE_TABLES_SETUP.sql` - Contains the events and medications tables

#### Events Table
```sql
CREATE TABLE events (
  id SERIAL PRIMARY KEY,
  user_id UUID REFERENCES auth.users ON DELETE CASCADE,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  time VARCHAR(50),
  date DATE,
  created_at TIMESTAMP DEFAULT NOW()
);
```

#### Medications Table
```sql
CREATE TABLE medications (
  id SERIAL PRIMARY KEY,
  user_id UUID REFERENCES auth.users ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  dosage VARCHAR(100),
  time VARCHAR(50),
  timing VARCHAR(255),
  date DATE,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### 4. Enable Row Level Security (RLS)
For security, enable RLS on both tables and set policies:

```sql
-- Enable RLS for events table
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- Create policies for events table
CREATE POLICY "Users can view their own events" ON events
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own events" ON events
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Enable RLS for medications table
ALTER TABLE medications ENABLE ROW LEVEL SECURITY;

-- Create policies for medications table
CREATE POLICY "Users can view their own medications" ON medications
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own medications" ON medications
  FOR INSERT WITH CHECK (auth.uid() = user_id);
```

### 5. Install Dependencies
Run the following command in your project directory:
```bash
flutter pub get
```

## Testing
1. Run your app: `flutter run -d chrome`
2. Go to the Sign Up tab and create a new account
3. Try signing in with your new credentials
4. After successful sign-in, you should be redirected to the HomePage
5. Navigate to the Schedule page and try adding events and medications using the "+" button

## Troubleshooting

### Issue: "Invalid Supabase URL or Anon Key"
- Double-check that you copied the correct values from your Supabase dashboard
- Make sure there are no extra spaces in the values

### Issue: "Network error during authentication"
- Check your internet connection
- Verify that your Supabase project is active and running

### Issue: Sign-up fails with "User already exists"
- That email address is already registered in Supabase
- Try signing in instead, or use a different email

### Issue: Cannot add events or medications
- Ensure you are signed in
- Check that the database tables were created correctly
- Verify that RLS policies are properly configured

## Additional Resources
- Supabase Documentation: https://supabase.com/docs
- Flutter Supabase Package: https://pub.dev/packages/supabase_flutter
- Authentication Best Practices: https://supabase.com/docs/guides/auth