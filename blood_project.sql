CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    blood_group VARCHAR(5) NOT NULL,
    contact VARCHAR(15) UNIQUE,
    address TEXT,
    password TEXT NOT NULL
);

CREATE TABLE hospital (
    hospital_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location TEXT,
    contact VARCHAR(15),
    password TEXT NOT NULL
);

CREATE TABLE blood_donation (
    donation_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    hospital_id INT REFERENCES hospital(hospital_id),
    donation_date DATE DEFAULT CURRENT_DATE,
    status VARCHAR(20) DEFAULT 'PENDING'
);

ALTER TABLE blood_donation
ADD COLUMN units INT;

CREATE TABLE blood_request (
    request_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    hospital_id INT REFERENCES hospital(hospital_id),
    blood_group VARCHAR(5) NOT NULL,
    units_required INT CHECK (units_required > 0),
    status VARCHAR(20) DEFAULT 'PENDING'
);

CREATE TABLE blood_stock (
    stock_id SERIAL PRIMARY KEY,
    hospital_id INT REFERENCES hospital(hospital_id) ON DELETE CASCADE,
    blood_group VARCHAR(5) NOT NULL,
    units_available INT CHECK (units_available >= 0)
);





CREATE OR REPLACE FUNCTION get_total_units(bg VARCHAR)
RETURNS INT AS $$
DECLARE
    total INT;
BEGIN
    SELECT SUM(units_available)
    INTO total
    FROM blood_stock
    WHERE blood_group = bg;

    RETURN COALESCE(total, 0);
END;
$$ LANGUAGE plpgsql;





CREATE OR REPLACE PROCEDURE process_request(req_id INT)
LANGUAGE plpgsql
AS $$
DECLARE
    req_group VARCHAR;
    req_units INT;
    available_units INT;
BEGIN

    -- Get request details
    SELECT blood_group, units_required
    INTO req_group, req_units
    FROM blood_request
    WHERE request_id = req_id;

    -- Get available stock
    SELECT units_available
    INTO available_units
    FROM blood_stock
    WHERE blood_group = req_group;

    -- Check availability
    IF available_units IS NULL THEN
        RAISE EXCEPTION 'Blood group not found in stock';
    END IF;

    IF available_units < req_units THEN
        RAISE EXCEPTION 'Not enough stock available';
    END IF;

    -- Reduce stock
    UPDATE blood_stock
    SET units_available = units_available - req_units
    WHERE blood_group = req_group;

    -- Approve request
    UPDATE blood_request
    SET status = 'APPROVED'
    WHERE request_id = req_id;

END;
$$;



DO $$
DECLARE
    rec RECORD;
    cur CURSOR FOR SELECT * FROM blood_request;
BEGIN
    OPEN cur;

    LOOP
        FETCH cur INTO rec;
        EXIT WHEN NOT FOUND;

        RAISE NOTICE 'Request ID: %, Blood Group: %, Status: %',
            rec.request_id, rec.blood_group, rec.status;
    END LOOP;

    CLOSE cur;
END;
$$;




CREATE OR REPLACE FUNCTION check_availability(bg VARCHAR, units INT)
RETURNS BOOLEAN AS $$
DECLARE
    available INT;
BEGIN
    SELECT SUM(units_available)
    INTO available
    FROM blood_stock
    WHERE blood_group = bg;

    IF COALESCE(available, 0) >= units THEN
        RETURN TRUE;
    ELSE
        RETURN FALSE;
    END IF;
END;
$$ LANGUAGE plpgsql;





CREATE OR REPLACE FUNCTION prevent_negative_stock()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.units_available < 0 THEN
        RAISE EXCEPTION 'Stock cannot be negative';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER stock_check_trigger
BEFORE UPDATE ON blood_stock
FOR EACH ROW
EXECUTE FUNCTION prevent_negative_stock();





CREATE VIEW request_summary AS
SELECT 
    r.request_id,
    u.name,
    r.blood_group,
    r.units_required,
    r.status
FROM blood_request r
JOIN users u ON r.user_id = u.user_id;



CREATE OR REPLACE PROCEDURE approve_donation(d_id INT)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE blood_donation
    SET status = 'APPROVED'
    WHERE donation_id = d_id;
END;
$$;



CREATE OR REPLACE FUNCTION update_stock_after_donation()
RETURNS TRIGGER AS $$
DECLARE
    donor_group VARCHAR;
BEGIN

    -- get donor blood group
    SELECT blood_group INTO donor_group
    FROM users
    WHERE user_id = NEW.user_id;

    -- if stock exists → update
    UPDATE blood_stock
    SET units_available = units_available + NEW.units
    WHERE blood_group = donor_group;

    -- if no row updated → insert
    IF NOT FOUND THEN
        INSERT INTO blood_stock (blood_group, units_available)
        VALUES (donor_group, NEW.units);
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS donation_stock_trigger ON blood_donation;
CREATE TRIGGER donation_stock_trigger
AFTER UPDATE ON blood_donation
FOR EACH ROW
WHEN (OLD.status != 'APPROVED' AND NEW.status = 'APPROVED')
EXECUTE FUNCTION update_stock_after_donation();

INSERT INTO blood_stock (blood_group, units_available) VALUES
('A+', 0),
('B+', 0),
('O+', 0),
('AB+', 0);


TRUNCATE TABLE blood_request, blood_donation, blood_stock, users
RESTART IDENTITY CASCADE;



