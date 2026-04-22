-- ============================================================
-- HOSPITAL SLOW — SCHEMA SETUP
-- Advanced Database Course — Final Project
-- Run this file connected to the 'postgres' database
-- It will create hospital_slow and all tables
-- ============================================================

CREATE DATABASE hospital_slow;

-- !! After running the CREATE DATABASE line above:
-- Disconnect from 'postgres' and reconnect to 'hospital_slow'
-- Then run the rest of this file

-- ============================================================
-- TABLE: patients
-- ============================================================
CREATE TABLE patients (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL,
    dob             DATE            NOT NULL,
    gender          CHAR(1)         NOT NULL CHECK (gender IN ('M', 'F')),
    blood_type      VARCHAR(4)      NOT NULL CHECK (blood_type IN ('A+','A-','B+','B-','AB+','AB-','O+','O-')),
    phone           VARCHAR(20),
    city            VARCHAR(50),
    registered_at   TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TABLE: doctors
-- ============================================================
CREATE TABLE doctors (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL,
    specialty       VARCHAR(50)     NOT NULL,
    license_no      VARCHAR(30)     UNIQUE NOT NULL,
    hire_date       DATE            NOT NULL,
    department      VARCHAR(50)     NOT NULL
);

-- ============================================================
-- TABLE: rooms
-- ============================================================
CREATE TABLE rooms (
    id              SERIAL PRIMARY KEY,
    room_number     VARCHAR(10)     UNIQUE NOT NULL,
    type            VARCHAR(20)     NOT NULL CHECK (type IN ('ICU', 'General', 'Surgery', 'Maternity', 'Pediatrics')),
    floor           SMALLINT        NOT NULL CHECK (floor BETWEEN 1 AND 20),
    capacity        SMALLINT        NOT NULL DEFAULT 2 CHECK (capacity > 0)
);

-- ============================================================
-- TABLE: appointments
-- ============================================================
CREATE TABLE appointments (
    id              SERIAL PRIMARY KEY,
    patient_id      INT             NOT NULL REFERENCES patients(id),
    doctor_id       INT             NOT NULL REFERENCES doctors(id),
    scheduled_at    TIMESTAMPTZ     NOT NULL,
    status          VARCHAR(15)     NOT NULL DEFAULT 'scheduled'
                                    CHECK (status IN ('scheduled','completed','cancelled','no-show')),
    notes           TEXT
);

-- ============================================================
-- TABLE: diagnoses
-- ============================================================
CREATE TABLE diagnoses (
    id              SERIAL PRIMARY KEY,
    appointment_id  INT             NOT NULL REFERENCES appointments(id),
    icd_code        VARCHAR(10)     NOT NULL,
    description     TEXT,
    severity        VARCHAR(10)     NOT NULL CHECK (severity IN ('mild', 'moderate', 'severe', 'critical'))
);

-- ============================================================
-- TABLE: prescriptions
-- ============================================================
CREATE TABLE prescriptions (
    id              SERIAL PRIMARY KEY,
    appointment_id  INT             NOT NULL REFERENCES appointments(id),
    drug_name       VARCHAR(100)    NOT NULL,
    dosage          VARCHAR(50)     NOT NULL,
    duration_days   SMALLINT        NOT NULL CHECK (duration_days > 0)
);

-- ============================================================
-- TABLE: lab_results
-- ============================================================
CREATE TABLE lab_results (
    id              SERIAL PRIMARY KEY,
    patient_id      INT             NOT NULL REFERENCES patients(id),
    test_name       VARCHAR(50)     NOT NULL,
    value           NUMERIC(10, 2)  NOT NULL,
    unit            VARCHAR(20),
    taken_at        TIMESTAMPTZ     NOT NULL,
    result_at       TIMESTAMPTZ
);

-- ============================================================
-- TABLE: admissions
-- ============================================================
CREATE TABLE admissions (
    id              SERIAL PRIMARY KEY,
    patient_id      INT             NOT NULL REFERENCES patients(id),
    room_id         INT             NOT NULL REFERENCES rooms(id),
    admitted_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    discharged_at   TIMESTAMPTZ,
    CONSTRAINT valid_discharge CHECK (discharged_at IS NULL OR discharged_at > admitted_at)
);

-- ============================================================
-- TABLE: billing
-- ============================================================
CREATE TABLE billing (
    id              SERIAL PRIMARY KEY,
    appointment_id  INT             NOT NULL REFERENCES appointments(id),
    amount          NUMERIC(10, 2)  NOT NULL CHECK (amount > 0),
    discount        NUMERIC(5, 2)   NOT NULL DEFAULT 0 CHECK (discount >= 0 AND discount <= 100),
    paid_at         TIMESTAMPTZ,
    payment_method  VARCHAR(20)     CHECK (payment_method IN ('cash','card','insurance','bank_transfer'))
);

-- ============================================================
-- NO INDEXES ADDED HERE — hospital_slow stays unoptimized
-- ============================================================

-- Verify
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
