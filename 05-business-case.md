# AlNour General Hospital — System Performance Report

**To:** Hospital Management
**From:** IT Department — Dr. Hassan Nabil, Head of IT
**Date:** April 2024
**Subject:** Database Slowness — Staff Complaints and Findings

---

## Background

Over the past six months, staff from different departments have been complaining that the hospital system is getting slower. We spoke to people from all nine departments to understand the problem. This report explains what they told us.

After looking into it, we found that the main reason for the slowness is that the database has no proper search optimization. The system was set up five years ago and nothing has been improved since then. We now have over 500,000 patients and the data keeps growing. The database is not built to handle this volume without some help.

The Database Optimization Team needs to read this report, find the performance problems, and fix them by creating the right indexes. **You need to find at least 10 problems on your own.** The problems are described in plain language — it is your job to understand what each one means technically.

---

## Section 1 — Reception and Patient Check-in

Ms. Dina Farouk, who runs the Patient Services team, says that searching for a patient's file at the front desk has become very slow. Her team does this hundreds of times every day, and the delay is visible:

> "When a patient walks in, the first thing we do is open their file. A few months ago it was instant. Now we wait a few seconds every time. By 9 in the morning, there is a queue at the desk. We have received complaints from patients."

Her staff said they always search for patients the same way — they type the patient's name. This is the most common thing they do all day, every day.

The same problem was also reported by Dr. Omar Fawzy, the Chief Medical Officer. He said that in every department, the first thing a doctor or nurse does when a patient arrives is look at the patient's history of visits:

> "Every single department, every single encounter — the first thing anyone does is open the patient's history. This used to take no time. Now there is a wait every time. Because this happens many times per minute across the whole hospital, even a small delay becomes a big problem."

---

## Section 2 — Emergency Department

Dr. Khaled Barakat works in the Emergency Department. He raised a serious concern. When a patient arrives at the ED, the doctor needs to quickly pull up everything that was done for that patient before — all their test results and previous visits. The search is always done using the patient's ID number.

> "In the emergency room, every second counts. I open the patient's record and I have to wait. I don't know their history, their medications, what tests they had. This is not just slow — it is dangerous. We cannot work like this."

We checked the system logs and confirmed that this lookup is slow every time, no matter what time of day it is.

---

## Section 3 — Outpatient Clinics and Scheduling

Two separate problems were reported here.

Ms. Sara Helmy, who manages the outpatient clinics, said that every morning when doctors log in, the system is slow to show them their schedule for the day. The schedule shows the list of patients the doctor will see, in order by time.

> "Doctors come in, log in, and wait. The schedule takes too long to appear. It should be instant. Because of this, clinics have started late several times."

The second problem was reported by the company that built the scheduling software. Their technical manager, Mr. Tarek Nour, noticed something in the database:

> "The scheduling screen only shows upcoming appointments — active ones. But the query behind it pulls everything — old appointments, cancelled ones, completed ones from years ago — and then filters them. The database is doing a huge amount of extra work for no reason. There is a way to tell the database to only look at the records that are actually needed and skip the rest completely."

---

## Section 4 — Admissions

Ms. Hana Zaki runs the Admissions office. She says that during busy mornings, finding a room for a new patient takes longer than it should. Staff always search for rooms using two things at the same time: the type of room (for example, surgical or ICU) and the floor it is on. They never search by just one.

> "We always need a specific type of room on a specific floor. During a busy shift, the search is slow. We have patients and their families standing at the desk while the staff wait for the results to appear."

---

## Section 5 — Laboratory

Dr. Maha Taha, the Lab Director, sent two complaints.

The first is about how doctors look up test results. When a doctor wants to see a patient's results for a specific test — for example, blood glucose — they always give two things: the name of the test and the time period they want. These two always come together.

> "Doctors never ask for all results for everything. They always say a specific test name and a specific time range. The system should be built around this, because it is what always happens. But it is slow."

The second complaint came later. Dr. Taha found out that the database keeps five years of lab results. But doctors only ever look at results from the last year. Anything older is handled by a separate archive system. The problem is that every time someone runs a query, the system is going through all five years of data:

> "We have five years of data. We use one year. Every query we run loads four years of results that nobody will ever look at. There is a way to make the database ignore the old records without moving them anywhere. We need that."

---

## Section 6 — Pharmacy

Dr. Rana Saleh, Head of Pharmacy, raised a concern about patient safety. Her team regularly needs to search for all prescriptions that contain a specific drug name. This check is done many times every shift — to check stock, flag conflicts, or answer questions from regulators.

> "We check drug names all day. When a pharmacist has to wait for the results, that is a problem. A medication mistake does not wait for the database."

---

## Section 7 — Finance and Billing

Three separate complaints came from the Finance department.

Ms. Nadia Ibrahim, who handles insurance, needs to create a report every three months for the national insurance authority. The report lists all patient cases that have a specific diagnosis code. This used to take a few minutes, but now the team has to start preparing it three days early:

> "The search is simple — find all cases with this diagnosis code. But it gets slower every time we run it."

Mr. Basem Saad, from Treasury, runs a report every evening. It groups all payments by payment method. This used to take a few minutes. Now it takes almost one hour and nothing else can run while it is working:

> "Every night, same report, same query. It now takes one hour. The whole finance system is blocked."

Ms. Iman Hassan runs internal audits. She needs to match every appointment with its payment record — to check if it was paid and when. When she runs this check over a time range longer than a few weeks, the query times out:

> "We need these records for the external auditors. The queries are timing out. We cannot give the auditors incomplete data. This is a legal obligation."

A fourth concern came from the CFO, Mr. Youssef Mansour. The monthly report that shows unpaid bills is slow. He believes the system is scanning through all billing records — both paid and unpaid — before finding the unpaid ones:

> "Most of our records are for bills that have already been paid. The ones we care about — the unpaid ones — are a small fraction. We should not need to look at all the paid records just to find the unpaid ones."

---

## Section 8 — Human Resources

Mr. Wael Aziz, the HR Director, says that the system is slow when searching for doctors by their specialty. This lookup is done often — by department managers building rosters, by the HR system, and by clinic coordinators trying to cover last-minute gaps.

> "We ask the system: show me all cardiologists. Simple question. But it is slow. We do this all the time. Nine departments, 24 hours a day. The delay adds up."

---

## Section 9 — Health Reports for the Ministry

Ms. Rania Khalil handles the monthly reports that the hospital sends to the Ministry of Health. One of these reports breaks down patients by the city they live in. Running this report is starting to cause timeouts:

> "This runs every month, same day, same query. Last month it failed twice before it worked on the third try. The Ministry does not accept late reports."

---

## What You Need to Do

You have read the report. Now act as the Database Optimization Team.

**Step 1 — Read carefully**
Find at least **10 performance problems** in this report. Some are easy to spot. Others need more thought. There are more than 10 — choose the ones you understand best.

**Step 2 — For each problem, go to the Index Lab and fill in:**
- **Problem description** — explain the problem in your own words (2-3 sentences)
- **Supporting quote** — copy the sentence or paragraph from this report that made you choose this problem
- **CREATE INDEX** — write the index that solves it
- **Test query** — write a SQL query that uses your index (EXPLAIN must show Index Scan, not Seq Scan)

**Step 3 — Your solution must include:**
- At least **2 partial indexes** — the report describes situations where only some rows are ever needed
- At least **3 composite indexes** — the report describes situations where two columns are always searched together
- At least **5 regular indexes** — the rest of the problems can be solved with a single-column index

---

## Database Tables Reference

| Table | Columns |
|---|---|
| `patients` | `id`, `name`, `dob`, `gender`, `blood_type`, `phone`, `city`, `registered_at` |
| `doctors` | `id`, `name`, `specialty`, `license_no`, `hire_date`, `department` |
| `rooms` | `id`, `room_number`, `type`, `floor`, `capacity` |
| `appointments` | `id`, `patient_id`, `doctor_id`, `scheduled_at`, `status`, `notes` |
| `diagnoses` | `id`, `appointment_id`, `icd_code`, `description`, `severity` |
| `prescriptions` | `id`, `appointment_id`, `drug_name`, `dosage`, `duration_days` |
| `lab_results` | `id`, `patient_id`, `test_name`, `value`, `unit`, `taken_at`, `result_at` |
| `admissions` | `id`, `patient_id`, `room_id`, `admitted_at`, `discharged_at` |
| `billing` | `id`, `appointment_id`, `amount`, `discount`, `paid_at`, `payment_method` |

---

*AlNour General Hospital — Internal Document*
*Advanced Database Course — Final Project*
