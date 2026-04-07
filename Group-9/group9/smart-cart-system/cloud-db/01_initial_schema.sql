-- retailer_users: id (UUID PK), email (VARCHAR 255 UNIQUE), password_hash (VARCHAR 255), role (VARCHAR 50), created_at (TIMESTAMPTZ)
CREATE TABLE retailer_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- customers: customer_id (VARCHAR 50 PK), phone_number (VARCHAR 20), mobile_token (VARCHAR 100 UNIQUE), created_at (TIMESTAMPTZ)
CREATE TABLE customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    phone_number VARCHAR(20),
    mobile_token VARCHAR(100) UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- store_layouts: store_id (VARCHAR 50 PK), map_image_url (VARCHAR 500), map_json_coordinates (JSONB), last_updated (TIMESTAMPTZ)
CREATE TABLE store_layouts (
    store_id VARCHAR(50) PRIMARY KEY,
    map_image_url VARCHAR(500),
    map_json_coordinates JSONB,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- products: product_id (VARCHAR 50 PK), name (VARCHAR 255), category (VARCHAR 100), price (NUMERIC 10,2), current_stock (INTEGER), reserved_stock (INTEGER), aisle_zone (VARCHAR 50), image_url (VARCHAR 500)
CREATE TABLE products (
    product_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    price NUMERIC(10,2) NOT NULL,
    current_stock INTEGER DEFAULT 0,
    reserved_stock INTEGER DEFAULT 0,
    aisle_zone VARCHAR(50),
    image_url VARCHAR(500)
);

-- active_cart_sessions: session_id (UUID PK), customer_id (VARCHAR 50 FK), status (VARCHAR 20), created_at (TIMESTAMPTZ)
CREATE TABLE active_cart_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR(50) REFERENCES customers(customer_id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- active_cart_items: id (UUID PK), session_id (UUID FK), product_id (VARCHAR 50 FK), quantity (INTEGER)
CREATE TABLE active_cart_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES active_cart_sessions(session_id) ON DELETE CASCADE,
    product_id VARCHAR(50) REFERENCES products(product_id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 1
);

-- orders: order_id (VARCHAR 50 PK), customer_id (VARCHAR 50 FK), order_date (TIMESTAMPTZ), total_amount (NUMERIC 10,2)
CREATE TABLE orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) REFERENCES customers(customer_id) ON DELETE SET NULL,
    order_date TIMESTAMPTZ DEFAULT NOW(),
    total_amount NUMERIC(10,2) NOT NULL DEFAULT 0.00
);

-- order_items: id (UUID PK), order_id (VARCHAR 50 FK), product_id (VARCHAR 50 FK), quantity (INTEGER), price_at_purchase (NUMERIC 10,2)
CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id VARCHAR(50) REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id VARCHAR(50) REFERENCES products(product_id) ON DELETE SET NULL,
    quantity INTEGER NOT NULL,
    price_at_purchase NUMERIC(10,2) NOT NULL
);

-- recommendation_rules: id (BIGINT PK), antecedent_product_id (VARCHAR 50), consequent_product_id (VARCHAR 50), lift (NUMERIC 5,2), confidence (NUMERIC 5,2)
CREATE TABLE recommendation_rules (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    antecedent_product_id VARCHAR(50) REFERENCES products(product_id) ON DELETE CASCADE,
    consequent_product_id VARCHAR(50) REFERENCES products(product_id) ON DELETE CASCADE,
    lift NUMERIC(5,2),
    confidence NUMERIC(5,2)
);

-- inventory_predictions: id (BIGINT PK), category (VARCHAR 100), forecast_month (DATE), predicted_demand (INTEGER), mape_score (NUMERIC 5,2)
CREATE TABLE inventory_predictions (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    category VARCHAR(100),
    forecast_month DATE,
    predicted_demand INTEGER,
    mape_score NUMERIC(5,2)
);

-- missed_opportunities: id (UUID PK), search_term (VARCHAR 255), request_count (INTEGER), last_requested (TIMESTAMPTZ)
CREATE TABLE missed_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    search_term VARCHAR(255) NOT NULL,
    request_count INTEGER DEFAULT 1,
    last_requested TIMESTAMPTZ DEFAULT NOW()
);
