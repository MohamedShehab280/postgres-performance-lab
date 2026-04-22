-- ============================================================
-- HOSPITAL MANAGEMENT SYSTEM — DATA GENERATION SCRIPT
-- Advanced Database Course — Final Project
-- Step 2: Run this AFTER 01-schema-setup.sql
-- Connect to hospital_db before running!
-- Expected runtime: 5–10 minutes — generates ~4 million rows
-- ============================================================

-- ============================================================
-- 1. ROOMS — 100 rows
-- ============================================================
INSERT INTO rooms (room_number, type, floor, capacity)
SELECT
    'R-' || LPAD(g::TEXT, 3, '0') AS room_number,
    (ARRAY['ICU','General','Surgery','Maternity','Pediatrics'])[CEIL(RANDOM()*5)::INT] AS type,
    CEIL(RANDOM() * 10)::SMALLINT AS floor,
    (ARRAY[1,2,2,3,4])[CEIL(RANDOM()*5)::INT]::SMALLINT AS capacity
FROM generate_series(1, 100) g;

-- ============================================================
-- 2. DOCTORS — 500 rows
-- ============================================================
INSERT INTO doctors (name, specialty, license_no, hire_date, department)
SELECT
    'Dr. ' ||
    (ARRAY['Ahmed','Mohamed','Sara','Nour','Khaled','Hana','Omar','Layla','Youssef','Dina'])[CEIL(RANDOM()*10)::INT]
    || '_' || g AS name,
    (ARRAY[
        'Cardiology','Neurology','Orthopedics','Pediatrics','Oncology',
        'Radiology','General Surgery','Internal Medicine','Dermatology','Emergency'
    ])[CEIL(RANDOM()*10)::INT] AS specialty,
    'LIC-' || LPAD(g::TEXT, 6, '0') AS license_no,
    CURRENT_DATE - (FLOOR(RANDOM() * 7300) || ' days')::INTERVAL AS hire_date,
    (ARRAY['Emergency','ICU','Outpatient','Surgery','Diagnostics','Pediatrics'])[CEIL(RANDOM()*6)::INT] AS department
FROM generate_series(1, 500) g;

-- ============================================================
-- 3. PATIENTS — 500,000 rows (~1–2 minutes)
-- ============================================================
INSERT INTO patients (name, dob, gender, blood_type, phone, city, registered_at)
SELECT
    (ARRAY['Ahmed','Mohamed','Sara','Nour','Khaled','Hana','Omar','Layla','Youssef','Dina',
           'Mona','Tarek','Iman','Bassem','Rania','Sherif','Heba','Walid','Nadia','Wael'])[CEIL(RANDOM()*20)::INT]
    || ' ' ||
    (ARRAY['Ali','Hassan','Ibrahim','Mahmoud','Farouk','Sayed','Khalil','Nasser',
           'Saleh','Aziz','Taha','Zaki','Badr','Saad','Fawzy'])[CEIL(RANDOM()*15)::INT]
    || '_' || g AS name,

    -- DOB: age between 1 and 90 years
    CURRENT_DATE - (FLOOR(RANDOM() * 32850 + 365) || ' days')::INTERVAL AS dob,

    CASE WHEN RANDOM() > 0.5 THEN 'M' ELSE 'F' END AS gender,

    (ARRAY['A+','A-','B+','B-','AB+','AB-','O+','O-'])[CEIL(RANDOM()*8)::INT] AS blood_type,

    '010' || LPAD((FLOOR(RANDOM() * 90000000))::TEXT, 8, '0') AS phone,

    (ARRAY['Cairo','Alexandria','Giza','Luxor','Aswan','Mansoura',
           'Tanta','Suez','Zagazig','Ismailia'])[CEIL(RANDOM()*10)::INT] AS city,

    NOW() - (FLOOR(RANDOM() * 3650) || ' days')::INTERVAL AS registered_at

FROM generate_series(1, 500000) g;

-- ============================================================
-- 4. APPOINTMENTS — 2,000,000 rows (~3–5 minutes)
-- This is the main fact table — most queries hit this
-- ============================================================
INSERT INTO appointments (patient_id, doctor_id, scheduled_at, status, notes)
SELECT
    CEIL(RANDOM() * 500000)::INT AS patient_id,
    CEIL(RANDOM() * 500)::INT AS doctor_id,

    -- Scheduled over the past 5 years
    NOW() - (FLOOR(RANDOM() * 1825 * 24 * 60) || ' minutes')::INTERVAL AS scheduled_at,

    (ARRAY['completed','completed','completed','cancelled','no-show','scheduled'])[CEIL(RANDOM()*6)::INT] AS status,

    CASE
        WHEN RANDOM() > 0.75 THEN 'Follow-up required after 2 weeks'
        WHEN RANDOM() > 0.50 THEN 'Patient referred to specialist'
        ELSE NULL
    END AS notes

FROM generate_series(1, 2000000) g;

-- ============================================================
-- 5. DIAGNOSES — 800,000 rows (for completed appointments subset)
-- ============================================================
INSERT INTO diagnoses (appointment_id, icd_code, description, severity)
SELECT
    CEIL(RANDOM() * 2000000)::INT AS appointment_id,

    (ARRAY['I10','E11','J06','M54','K21','Z00','J45','N39','F32','I25',
           'E78','G43','L30','H52','K59','J20','I48','M79','E03','R51'])[CEIL(RANDOM()*20)::INT] AS icd_code,

    (ARRAY[
        'Hypertension - blood pressure elevated',
        'Type 2 Diabetes - uncontrolled',
        'Upper respiratory tract infection',
        'Lower back pain - chronic',
        'Acid reflux disease',
        'Routine health check-up',
        'Bronchial asthma - moderate',
        'Urinary tract infection',
        'Major depressive episode',
        'Chronic ischemic heart disease'
    ])[CEIL(RANDOM()*10)::INT] AS description,

    (ARRAY['mild','mild','moderate','moderate','moderate','severe','critical'])[CEIL(RANDOM()*7)::INT] AS severity

FROM generate_series(1, 800000) g;

-- ============================================================
-- 6. PRESCRIPTIONS — 600,000 rows
-- ============================================================
INSERT INTO prescriptions (appointment_id, drug_name, dosage, duration_days)
SELECT
    CEIL(RANDOM() * 2000000)::INT AS appointment_id,

    (ARRAY[
        'Amoxicillin','Metformin','Lisinopril','Atorvastatin','Omeprazole',
        'Amlodipine','Metoprolol','Losartan','Salbutamol','Ciprofloxacin',
        'Paracetamol','Ibuprofen','Aspirin','Insulin Glargine','Levothyroxine'
    ])[CEIL(RANDOM()*15)::INT] AS drug_name,

    (ARRAY['500mg once daily','10mg twice daily','25mg every 8 hours',
           '100mg at night','5mg with food','1 tablet as needed'])[CEIL(RANDOM()*6)::INT] AS dosage,

    (CEIL(RANDOM() * 30) + 2)::SMALLINT AS duration_days

FROM generate_series(1, 600000) g;

-- ============================================================
-- 7. LAB RESULTS — 1,000,000 rows
-- ============================================================
INSERT INTO lab_results (patient_id, test_name, value, unit, taken_at, result_at)
SELECT
    CEIL(RANDOM() * 500000)::INT AS patient_id,

    (ARRAY[
        'Blood Glucose','Hemoglobin','Cholesterol','Creatinine',
        'TSH','Uric Acid','CBC','ALT','AST','Sodium',
        'Potassium','HbA1c','Bilirubin','Albumin','WBC'
    ])[CEIL(RANDOM()*15)::INT] AS test_name,

    ROUND((RANDOM() * 300 + 10)::NUMERIC, 2) AS value,

    (ARRAY['mg/dL','mmol/L','g/dL','µIU/mL','mg/L','mEq/L','%','U/L'])[CEIL(RANDOM()*8)::INT] AS unit,

    -- Taken in the past 5 years
    NOW() - (FLOOR(RANDOM() * 1825) || ' days')::INTERVAL AS taken_at,

    -- Result available 1–3 days after taken
    NOW() - (FLOOR(RANDOM() * 1822) || ' days')::INTERVAL AS result_at

FROM generate_series(1, 1000000) g;

-- ============================================================
-- 8. ADMISSIONS — 50,000 rows
-- ============================================================
INSERT INTO admissions (patient_id, room_id, admitted_at, discharged_at)
SELECT
    patient_id,
    room_id,
    admitted_at,
    -- 85% discharged: add 1–30 days AFTER admitted_at (always valid)
    -- 15% still admitted: NULL
    CASE
        WHEN RANDOM() > 0.15
        THEN admitted_at + (FLOOR(RANDOM() * 30 + 1) || ' days')::INTERVAL
        ELSE NULL
    END AS discharged_at
FROM (
    SELECT
        CEIL(RANDOM() * 500000)::INT  AS patient_id,
        CEIL(RANDOM() * 100)::INT     AS room_id,
        NOW() - (FLOOR(RANDOM() * 1795) || ' days')::INTERVAL AS admitted_at
    FROM generate_series(1, 50000) g
) sub;

-- ============================================================
-- 9. BILLING — 1,200,000 rows
-- ============================================================
INSERT INTO billing (appointment_id, amount, discount, paid_at, payment_method)
SELECT
    CEIL(RANDOM() * 2000000)::INT AS appointment_id,

    ROUND((RANDOM() * 3000 + 50)::NUMERIC, 2) AS amount,

    ROUND((RANDOM() * 25)::NUMERIC, 2) AS discount,

    -- 80% paid, 20% unpaid (NULL = unpaid — great for partial index demo)
    CASE
        WHEN RANDOM() > 0.20
        THEN NOW() - (FLOOR(RANDOM() * 365) || ' days')::INTERVAL
        ELSE NULL
    END AS paid_at,

    CASE
        WHEN RANDOM() > 0.20
        THEN (ARRAY['cash','card','insurance','bank_transfer'])[CEIL(RANDOM()*4)::INT]
        ELSE NULL  -- NULL for unpaid rows
    END AS payment_method

FROM generate_series(1, 1200000) g;

-- ============================================================
-- VERIFY: Check row counts after generation
-- ============================================================
SELECT 'patients'      AS table_name, COUNT(*) AS row_count FROM patients
UNION ALL
SELECT 'doctors',       COUNT(*) FROM doctors
UNION ALL
SELECT 'rooms',         COUNT(*) FROM rooms
UNION ALL
SELECT 'appointments',  COUNT(*) FROM appointments
UNION ALL
SELECT 'diagnoses',     COUNT(*) FROM diagnoses
UNION ALL
SELECT 'prescriptions', COUNT(*) FROM prescriptions
UNION ALL
SELECT 'lab_results',   COUNT(*) FROM lab_results
UNION ALL
SELECT 'admissions',    COUNT(*) FROM admissions
UNION ALL
SELECT 'billing',       COUNT(*) FROM billing
ORDER BY table_name;

-- Expected totals:
-- patients:       500,000
-- doctors:            500
-- rooms:              100
-- appointments:  2,000,000
-- diagnoses:       800,000
-- prescriptions:   600,000
-- lab_results:   1,000,000
-- admissions:       50,000
-- billing:       1,200,000
-- TOTAL:        ~6,150,600 rows
