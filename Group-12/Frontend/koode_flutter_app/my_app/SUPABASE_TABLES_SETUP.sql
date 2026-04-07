-- Create events table
CREATE TABLE events (
  id SERIAL PRIMARY KEY,
  user_id UUID REFERENCES auth.users ON DELETE CASCADE,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  time VARCHAR(50),
  date DATE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Enable RLS for events table
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- Create policy for events table
CREATE POLICY "Users can view their own events" ON events
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own events" ON events
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own events" ON events
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own events" ON events
  FOR DELETE USING (auth.uid() = user_id);

-- Create medications table
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

-- Enable RLS for medications table
ALTER TABLE medications ENABLE ROW LEVEL SECURITY;

-- Create policy for medications table
CREATE POLICY "Users can view their own medications" ON medications
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own medications" ON medications
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own medications" ON medications
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own medications" ON medications
  FOR DELETE USING (auth.uid() = user_id);