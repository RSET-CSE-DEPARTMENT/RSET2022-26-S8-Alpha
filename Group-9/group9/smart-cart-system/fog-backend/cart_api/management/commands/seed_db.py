import uuid
import random
from datetime import datetime

import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from cart_api.models import Product, Customer, Order, OrderItem


class Command(BaseCommand):
    help = 'Seeds the database using train.csv for the ML Forecasting Model'

    def handle(self, *args, **kwargs):
        self.stdout.write("Reading train.csv...")
        df = pd.read_csv('train.csv', encoding='latin1')

        # Parse dates (Superstore dataset uses DD/MM/YYYY)
        df['Order Date'] = pd.to_datetime(df['Order Date'], format='%d/%m/%Y')

        with transaction.atomic():
            # 1. Seed Customers
            self.stdout.write("Seeding Customers...")
            customers_data = df[['Customer ID']].drop_duplicates()
            customers_to_create = []
            for _, row in customers_data.iterrows():
                customers_to_create.append(Customer(
                    customer_id=row['Customer ID'],
                    phone_number=f"555-{random.randint(1000, 9999)}",
                    mobile_token=str(uuid.uuid4()),
                    created_at=timezone.now()
                ))
            Customer.objects.bulk_create(customers_to_create, ignore_conflicts=True)

            # 2. Seed Products
            self.stdout.write("Seeding Products...")
            products_data = df[['Product ID', 'Product Name', 'Category', 'Sales']].drop_duplicates(subset=['Product ID'])
            products_to_create = []
            for _, row in products_data.iterrows():
                products_to_create.append(Product(
                    product_id=row['Product ID'],
                    name=row['Product Name'][:250],  # Truncate just in case
                    category=row['Category'],
                    price=round(row['Sales'], 2),  # Using sales as a proxy unit price for the testbed
                    current_stock=random.randint(50, 200),
                    reserved_stock=0,
                    aisle_zone=random.choice(["1-1", "1-2", "2-1"]),  # Mapping to iBeacon zones
                    image_url="https://via.placeholder.com/150"
                ))
            Product.objects.bulk_create(products_to_create, ignore_conflicts=True)

            # 3. Seed Orders
            self.stdout.write("Seeding Orders...")
            orders_data = df.groupby(['Order ID', 'Customer ID', 'Order Date'])['Sales'].sum().reset_index()
            orders_to_create = []
            for _, row in orders_data.iterrows():
                orders_to_create.append(Order(
                    order_id=row['Order ID'],
                    customer_id=row['Customer ID'],
                    order_date=timezone.make_aware(row['Order Date']),
                    total_amount=round(row['Sales'], 2)
                ))
            Order.objects.bulk_create(orders_to_create, ignore_conflicts=True)

            # 4. Seed Order Items
            self.stdout.write("Seeding Order Items...")
            order_items_to_create = []
            for _, row in df.iterrows():
                order_items_to_create.append(OrderItem(
                    id=uuid.uuid4(),
                    order_id=row['Order ID'],
                    product_id=row['Product ID'],
                    quantity=1,  # Defaulting to 1 to simplify the proxy
                    price_at_purchase=round(row['Sales'], 2)
                ))

            # Bulk create in chunks to avoid blowing out RAM
            OrderItem.objects.bulk_create(order_items_to_create, batch_size=1000, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS("Database perfectly seeded with 4 years of history!"))
