create table orders(
    order_id TEXT primary key ,
    customer_id text,
    order_status text,
    order_purchase_timestamp text,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);
create table customers(
  customer_id

);