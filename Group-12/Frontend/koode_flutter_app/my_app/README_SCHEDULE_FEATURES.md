# Schedule Page Features

This document describes the new functionality added to the Schedule page to allow users to add events and medications to the database.

## Features Implemented

### 1. Add Events
- Users can tap the "+" button when in the Events tab to add a new event
- A form dialog appears with fields for:
  - Event Title
  - Description
  - Time
- Data is saved to the `events` table in Supabase

### 2. Add Medications
- Users can tap the "+" button when in the Medication tab to add a new medication
- A form dialog appears with fields for:
  - Medication Name
  - Dosage
  - Time
  - Timing options (Before Breakfast, After Breakfast, Noon, Night)
- Selected timing options are highlighted in blue for better visibility
- Data is saved to the `medications` table in Supabase

## Database Structure

### Events Table
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

### Medications Table
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

## Service Layer

A `DatabaseService` class was created to handle all database operations:
- `addEvent()` - Adds a new event to the database
- `addMedication()` - Adds a new medication to the database
- Additional methods for retrieving, updating, and deleting records

## Security

Row Level Security (RLS) policies ensure that users can only access their own data:
- Users can only view their own events and medications
- Users can only create, update, and delete their own events and medications

## Setup Instructions

1. Run the SQL scripts in `SUPABASE_TABLES_SETUP.sql` to create the required tables
2. Ensure RLS is enabled and policies are set up correctly
3. The Flutter app will automatically use the new functionality when users are authenticated

## Error Handling

The implementation includes proper error handling:
- Users must be signed in to add events or medications
- Errors are displayed in snackbars for user feedback
- Form fields are cleared after successful submission