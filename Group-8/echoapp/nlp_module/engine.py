from .tones import apply_tone
import random
from textblob import TextBlob
import spacy

nlp = spacy.load("en_core_web_sm")

def generate_with_tone(profession, subject, present, absent, assignments, due_date, tone, keywords, mode="professional", **kwargs):
    doc = nlp(keywords)
    extracted_keywords = [ent.text for ent in doc.ents] if doc.ents else [keywords]
    blob = TextBlob(keywords)
    sentiment = blob.sentiment.polarity

    templates = []

    # Teacher Professional
    if profession == "teacher" and mode == "professional":
        if tone == "cheerful":
            templates = [
                f"What a fun day teaching {subject}! It was wonderful to see {present} students, though we missed {absent}. Homework is ready for {due_date}.",
                f"I really enjoyed our {subject} class today—{present} students joined in, and we hope {absent} can be with us next time. Assignments are due on {due_date}.",
                f"My {subject} students brought so much energy! {present} were present, {absent} were missed. Looking forward to their homework by {due_date}.",
                f"Smiles all around in {subject} today! {present} attended, {absent} missed out, and homework is set for {due_date}.",
                f"Feeling thankful for a lively {subject} class: {present} present, {absent} absent. Excited to check assignments on {due_date}!",
            ]
        elif tone == "sad":
            templates = [
                f"Today felt a bit quiet in {subject}—only {present} showed up, and we missed {absent}. Assignments are still due on {due_date}.",
                f"It was a tough day with many absentees in {subject}. {present} attended, {absent} were missing. Homework deadline is {due_date}.",
                f"Missing the usual energy in {subject} class. {absent} students were absent, and assignments are due {due_date}.",
                f"Low spirits in {subject} today with {absent} missing. Hoping for better attendance next time. Homework due {due_date}.",
                f"Sad to see so many absent in {subject}. Assignments are due on {due_date}.",
            ]
        else:  # neutral
            templates = [
                f"In {subject}, {present} students attended and {absent} were absent. Assignments are due on {due_date}.",
                f"{subject} class update: {present} present, {absent} absent. Assignment deadline: {due_date}.",
                f"{present} students joined {subject} today, {absent} were absent. Homework due {due_date}.",
                f"Routine day in {subject}: {present} present, {absent} absent, assignments due {due_date}.",
            ]
    # Teacher Personal
    elif profession == "teacher" and mode == "personal":
        mood = kwargs.get("mood", "")
        family_time = kwargs.get("family_time", "")
        stress_level = kwargs.get("stress_level", "")
        todo = kwargs.get("todo", "")
        if tone == "cheerful":
            templates = [
                f"Feeling upbeat today! Had some lovely family time and my stress level was {stress_level}. Planning to {todo} tomorrow.",
                f"Had a cheerful day after work. Spent time with family: {family_time}. Stress was {stress_level}. Tomorrow’s plan: {todo}.",
                f"Grateful for a positive day. Enjoyed family time: {family_time}, stress was manageable at {stress_level}, and I’m excited for tomorrow’s to-do: {todo}.",
            ]
        elif tone == "sad":
            templates = [
                f"Feeling a bit down today. Didn’t get much family time, and my stress level was {stress_level}.",
                f"Sad mood after work. Missed out on family time: {family_time}. Stress level: {stress_level}.",
                f"Not my best day. Stress: {stress_level}, family time: {family_time}, hoping tomorrow’s to-do: {todo} lifts my spirits.",
            ]
        else:  # neutral
            templates = [
                f"My mood today was okay. Family time: {family_time}, stress: {stress_level}, to-do: {todo}.",
                f"Just a regular day. Family: {family_time}, stress: {stress_level}, tomorrow: {todo}.",
            ]
    # Doctor Professional
    elif profession == "doctor" and mode == "professional":
        department = kwargs.get("department", "")
        patients = kwargs.get("patients", "")
        missed_appointments = kwargs.get("missed_appointments", "")
        procedures = kwargs.get("procedures", "")
        next_appointment = kwargs.get("next_appointment", "")
        if tone == "cheerful":
            templates = [
                f"Had a great day in {department}! Saw {patients} patients, only {missed_appointments} missed appointments. Procedures went well, and next follow-up is on {next_appointment}.",
                f"Feeling positive in {department}: {patients} patients helped, {procedures} procedures done, next appointment: {next_appointment}.",
                f"Lots of smiles in {department} today. Patients: {patients}, missed: {missed_appointments}, next up: {next_appointment}.",
            ]
        elif tone == "sad":
            templates = [
                f"Today was tough in {department}. Only {patients} patients came, {missed_appointments} missed their appointments. Procedures: {procedures}.",
                f"Feeling a bit low after work in {department}. Missed appointments: {missed_appointments}, next: {next_appointment}.",
                f"Not the best day in {department}. Patients: {patients}, missed: {missed_appointments}, procedures: {procedures}.",
            ]
        elif tone == "formal":
            templates = [
                f"In {department}, I attended {patients} patients today, with {missed_appointments} missing appointments. Treatments: {procedures}. Next follow-up: {next_appointment}.",
                f"{department} update: {patients} patients, {missed_appointments} missed, procedures: {procedures}, next: {next_appointment}.",
            ]
        else:  # neutral
            templates = [
                f"{department} summary: {patients} patients, {missed_appointments} missed, procedures: {procedures}, next: {next_appointment}.",
                f"Routine day in {department}. Patients: {patients}, missed: {missed_appointments}, next: {next_appointment}.",
            ]
    # Doctor Personal
    elif profession == "doctor" and mode == "personal":
        sleep_hours = kwargs.get("sleep_hours", "")
        exercise = kwargs.get("exercise", "")
        stress_level = kwargs.get("stress_level", "")
        relaxation = kwargs.get("relaxation", "")
        if tone == "cheerful":
            templates = [
                f"Feeling refreshed after {sleep_hours} hours of sleep and a morning walk! Had a fun dinner with family too.",
                f"Cheerful mood: Slept {sleep_hours} hours, exercised: {exercise}, relaxed: {relaxation}.",
                f"Positive day: Sleep {sleep_hours}, exercise {exercise}, stress {stress_level}, relaxation {relaxation}.",
            ]
        elif tone == "sad":
            templates = [
                f"Tired today, only {sleep_hours} hours of sleep. Missed my usual exercise: {exercise}. Stress level: {stress_level}.",
                f"Sad mood. Sleep: {sleep_hours}, stress: {stress_level}, relaxation: {relaxation}.",
                f"Low energy today. Sleep: {sleep_hours}, exercise: {exercise}, stress: {stress_level}.",
            ]
        else:  # neutral
            templates = [
                f"Routine day: Slept {sleep_hours} hours, exercised: {exercise}, stress: {stress_level}, relaxed: {relaxation}.",
                f"Average mood. Sleep: {sleep_hours}, exercise: {exercise}, stress: {stress_level}.",
            ]
    # Business Professional
    elif profession == "business" and mode == "professional":
        domain = kwargs.get("domain", "")
        meetings = kwargs.get("meetings", "")
        clients = kwargs.get("clients", "")
        deals = kwargs.get("deals", "")
        deadline = kwargs.get("deadline", "")
        if tone == "cheerful" or tone == "excited":
            templates = [
                f"I had a productive day in {domain}, connecting with {clients} clients and wrapping up {deals} deals after {meetings} meetings. Looking forward to our next big deadline on {deadline}.",
                f"Today in {domain} was full of energy! After {meetings} meetings, I managed to close {deals} deals and strengthen relationships with {clients} clients. The next milestone is set for {deadline}.",
                f"Feeling accomplished in {domain}—{deals} deals closed, {clients} clients engaged, and plenty of meetings ({meetings}) to keep things moving. Can't wait for what's next by {deadline}.",
                f"My day in {domain} was rewarding: I met with {clients} clients, finalized {deals} deals, and kept everything on track for our upcoming deadline on {deadline}.",
                f"Lots of progress in {domain} today! After meeting with {clients} clients and attending {meetings} meetings, I closed {deals} deals. The team is gearing up for the deadline on {deadline}.",
            ]
        elif tone == "sad":
            templates = [
                f"It was a challenging day in {domain}. Despite {meetings} meetings, only {deals} deals were closed, and I struggled to connect with some clients. Hoping things improve before the deadline on {deadline}.",
                f"Feeling a bit discouraged in {domain}—not many deals closed and fewer client interactions than expected. The deadline on {deadline} is approaching, so I hope tomorrow is better.",
                f"Today in {domain} didn't go as planned. I had {meetings} meetings, but only managed to close {deals} deals. The deadline on {deadline} is weighing on my mind.",
            ]
        else:  # neutral
            templates = [
                f"In {domain}, I attended {meetings} meetings, worked with {clients} clients, and closed {deals} deals. Preparing for the next deadline on {deadline}.",
                f"Routine day in {domain}: met with {clients} clients, had {meetings} meetings, and finalized {deals} deals. Deadline coming up on {deadline}.",
            ]
    # Business Personal
    elif profession == "business" and mode == "personal":
        daily_mood = kwargs.get("daily_mood", "")
        family_interaction = kwargs.get("family_interaction", "")
        financial_stress = kwargs.get("financial_stress", "")
        hobbies = kwargs.get("hobbies", "")
        if tone == "cheerful":
            templates = [
                f"Had a wonderful day! Enjoyed family time: {family_interaction}, hobbies: {hobbies}, and stress was low at {financial_stress}.",
                f"Cheerful mood: {daily_mood}, spent time with family: {family_interaction}, enjoyed hobbies: {hobbies}, stress: {financial_stress}.",
                f"Feeling positive. Family: {family_interaction}, hobbies: {hobbies}, stress: {financial_stress}.",
            ]
        elif tone == "sad":
            templates = [
                f"Feeling a bit down today. Family interaction: {family_interaction}, hobbies: {hobbies}, financial stress: {financial_stress}.",
                f"Sad mood: {daily_mood}, family: {family_interaction}, stress: {financial_stress}.",
                f"Not the best day. Family: {family_interaction}, hobbies: {hobbies}, stress: {financial_stress}.",
            ]
        else:  # neutral
            templates = [
                f"Neutral mood today. Family: {family_interaction}, hobbies: {hobbies}, stress: {financial_stress}.",
                f"Routine day. Mood: {daily_mood}, family: {family_interaction}, stress: {financial_stress}.",
            ]

    # Remove duplicates and select up to 5 suggestions
    templates = list(dict.fromkeys(templates))
    suggestions = random.sample(templates, min(len(templates), 5)) if templates else []
    # Apply the tone template to each suggestion
    suggestions = [apply_tone(s, tone) for s in suggestions]
    return suggestions
