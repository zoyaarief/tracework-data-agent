from __future__ import annotations

import random
from datetime import date, timedelta

from sqlalchemy import Engine, text

SCHEMA = """
CREATE TABLE customers (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  region TEXT NOT NULL,
  segment TEXT NOT NULL,
  joined_at DATE NOT NULL,
  churned_at DATE
);
CREATE TABLE products (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  unit_price NUMERIC NOT NULL
);
CREATE TABLE orders (
  id INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL REFERENCES customers(id),
  ordered_at DATE NOT NULL,
  status TEXT NOT NULL,
  total_amount NUMERIC NOT NULL
);
CREATE TABLE order_items (
  id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL REFERENCES orders(id),
  product_id INTEGER NOT NULL REFERENCES products(id),
  quantity INTEGER NOT NULL,
  unit_price NUMERIC NOT NULL
);
CREATE TABLE refunds (
  id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL REFERENCES orders(id),
  product_id INTEGER NOT NULL REFERENCES products(id),
  refunded_at DATE NOT NULL,
  amount NUMERIC NOT NULL,
  reason TEXT NOT NULL
);
CREATE INDEX idx_orders_customer_date ON orders(customer_id, ordered_at);
CREATE INDEX idx_orders_date ON orders(ordered_at);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);
CREATE INDEX idx_refunds_product ON refunds(product_id);
"""

PRODUCTS = [
    (1, "Signal Enterprise", "Enterprise Analytics", 720),
    (2, "Signal Team", "Enterprise Analytics", 410),
    (3, "Signal Core", "Enterprise Analytics", 260),
    (4, "Flow Automate", "Workflow Automation", 340),
    (5, "Flow Studio", "Workflow Automation", 220),
    (6, "Flow Tasks", "Workflow Automation", 120),
    (7, "Connector Pro", "Data Connectors", 190),
    (8, "Connector Standard", "Data Connectors", 110),
    (9, "Connector Lite", "Data Connectors", 70),
]


def seed_demo_database(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    rng = random.Random(240319)
    regions = ["Northeast", "Southeast", "Midwest", "West"]
    segments = ["SMB", "Mid-market", "Enterprise"]
    customers = []
    for customer_id in range(1, 401):
        joined = date(2024, 1, 1) + timedelta(days=rng.randint(0, 480))
        churned = None
        if rng.random() < 0.11:
            churned = date(2025, 6, 1) + timedelta(days=rng.randint(0, 121))
        customers.append(
            {
                "id": customer_id,
                "name": f"Customer {customer_id:03d}",
                "region": regions[(customer_id - 1) % len(regions)],
                "segment": rng.choices(segments, [0.45, 0.35, 0.2])[0],
                "joined_at": joined.isoformat(),
                "churned_at": churned.isoformat() if churned else None,
            }
        )

    orders = []
    items = []
    refunds = []
    order_id = item_id = refund_id = 1
    start = date(2025, 4, 1)
    for day_offset in range(183):
        order_date = start + timedelta(days=day_offset)
        in_q3 = order_date >= date(2025, 7, 1)
        daily_orders = rng.randint(8, 13)
        for _ in range(daily_orders):
            customer = rng.choice(customers)
            item_count = rng.randint(1, 3)
            order_total = 0.0
            order_items = []
            for _ in range(item_count):
                weights = [1.75, 1.5, 1.25, 1, 1, 1, 0.85, 0.85, 0.85] if in_q3 else [1, 1, 1, 1, 1, 1, 0.9, 0.9, 0.9]
                product = rng.choices(PRODUCTS, weights)[0]
                quantity = rng.randint(1, 4)
                price = product[3]
                order_total += quantity * price
                order_items.append((product, quantity, price))
            orders.append(
                {
                    "id": order_id,
                    "customer_id": customer["id"],
                    "ordered_at": order_date.isoformat(),
                    "status": "completed",
                    "total_amount": order_total,
                }
            )
            for product, quantity, price in order_items:
                items.append(
                    {
                        "id": item_id,
                        "order_id": order_id,
                        "product_id": product[0],
                        "quantity": quantity,
                        "unit_price": price,
                    }
                )
                if rng.random() < (0.09 if product[0] == 8 else 0.025):
                    refunds.append(
                        {
                            "id": refund_id,
                            "order_id": order_id,
                            "product_id": product[0],
                            "refunded_at": (order_date + timedelta(days=rng.randint(2, 20))).isoformat(),
                            "amount": price,
                            "reason": rng.choice(["Duplicate", "Not as expected", "Technical issue"]),
                        }
                    )
                    refund_id += 1
                item_id += 1
            order_id += 1

    with engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            exists = connection.exec_driver_sql(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'customers'"
            ).scalar()
            if exists:
                connection.rollback()
                return
            for statement in SCHEMA.split(";"):
                if statement.strip():
                    connection.exec_driver_sql(statement)
            connection.execute(
                text("INSERT INTO customers VALUES (:id, :name, :region, :segment, :joined_at, :churned_at)"), customers
            )
            connection.execute(
                text("INSERT INTO products VALUES (:id, :name, :category, :unit_price)"),
                [dict(zip(["id", "name", "category", "unit_price"], row, strict=True)) for row in PRODUCTS],
            )
            connection.execute(
                text("INSERT INTO orders VALUES (:id, :customer_id, :ordered_at, :status, :total_amount)"), orders
            )
            connection.execute(
                text("INSERT INTO order_items VALUES (:id, :order_id, :product_id, :quantity, :unit_price)"), items
            )
            if refunds:
                connection.execute(
                    text("INSERT INTO refunds VALUES (:id, :order_id, :product_id, :refunded_at, :amount, :reason)"),
                    refunds,
                )
            connection.exec_driver_sql("PRAGMA optimize")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
