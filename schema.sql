-- Reference schema for ShambaLink.
-- You do NOT need to run this manually if you use `python init_db.py`,
-- which creates these tables automatically via SQLAlchemy. This file is
-- provided for reference, manual setup, or database review.
--
-- If you already created your database before the image-upload feature
-- was added, run this single line to add the missing column instead of
-- recreating everything:
--   ALTER TABLE listings ADD COLUMN image_filename VARCHAR(255);

CREATE DATABASE IF NOT EXISTS shamba_link
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE shamba_link;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(160) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('farmer', 'buyer') NOT NULL,
  phone VARCHAR(30),
  location VARCHAR(120),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE listings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  farmer_id INT NOT NULL,
  crop_name VARCHAR(120) NOT NULL,
  category VARCHAR(60) NOT NULL,
  description TEXT,
  quantity_available DECIMAL(10, 2) NOT NULL,
  unit VARCHAR(30) NOT NULL,
  price_per_unit DECIMAL(10, 2) NOT NULL,
  location VARCHAR(120) NOT NULL,
  harvest_date DATE,
  image_filename VARCHAR(255),
  status ENUM('active', 'sold_out', 'inactive') NOT NULL DEFAULT 'active',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (farmer_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE orders (
  id INT AUTO_INCREMENT PRIMARY KEY,
  buyer_id INT NOT NULL,
  listing_id INT NOT NULL,
  quantity DECIMAL(10, 2) NOT NULL,
  total_price DECIMAL(10, 2) NOT NULL,
  status ENUM('pending', 'confirmed', 'completed', 'cancelled') NOT NULL DEFAULT 'pending',
  note VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (buyer_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_listings_status ON listings(status);
CREATE INDEX idx_listings_category ON listings(category);
CREATE INDEX idx_orders_status ON orders(status);

CREATE TABLE subscriptions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  farmer_id INT NOT NULL,
  plan ENUM('biannual', 'annual') NOT NULL,
  amount DECIMAL(10, 2) NOT NULL,
  status ENUM('pending', 'active', 'expired', 'cancelled') NOT NULL DEFAULT 'pending',
  start_date DATE,
  end_date DATE,
  payment_reference VARCHAR(120),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (farmer_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_farmer ON subscriptions(farmer_id);
