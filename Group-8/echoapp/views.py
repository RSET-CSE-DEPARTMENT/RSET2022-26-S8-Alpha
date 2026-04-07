from django.shortcuts import render
from .nlp_module.engine import generate_with_tone
from dashboard.models import JournalEntry

def nlp_demo(request):
    suggestions = []
    saved_entry = None

    if request.method == "POST":
        if "save" in request.POST:
            # User selected a suggestion to save
            saved_entry = request.POST.get("selected_suggestion")
            
            # Save to database
            if saved_entry:
                try:
                    # Get profession from session or use default
                    profession = request.session.get('last_profession', 'general')
                    
                    # Use the session mode (from login page) instead of form input
                    journal_mode = request.session.get('user_mode', 'personal')
                    
                    # Create journal entry
                    journal_entry = JournalEntry.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        title=f"AI Generated: {profession.capitalize()}",
                        content=saved_entry,
                        mood='neutral',
                        mood_confidence=0.0,
                        is_voice_entry=False,
                        mode=journal_mode  # Use the session mode from login
                    )
                    journal_entry.save()
                except Exception as e:
                    print(f"Error saving journal entry: {e}")
        else:
            # Generate suggestions
            profession = request.POST.get("profession", "teacher")
            subject = request.POST.get("subject", "")
            present = request.POST.get("present", "")
            absent = request.POST.get("absent", "")
            assignments = request.POST.get("assignments", "")
            due_date = request.POST.get("due_date", "")
            tone = request.POST.get("tone", "neutral")
            keywords = request.POST.get("keywords", "")
            
            # Use session mode instead of form mode
            mode = request.session.get('user_mode', 'personal')
            
            # Store profession in session for later use when saving
            request.session['last_profession'] = profession
            
            print("TONE FROM FORM:", request.POST.get("tone"))
            print("profession FROM FORM:", request.POST.get("profession"))
            print("mode FROM FORM:", request.POST.get("mode"))

            if profession == "teacher" and mode == "professional":
                subject = request.POST.get("subject", "")
                present = request.POST.get("present", "")
                absent = request.POST.get("absent", "")
                assignments = request.POST.get("assignments", "")
                due_date = request.POST.get("due_date", "")
                tone = request.POST.get("tone", "neutral")
                suggestions = generate_with_tone(
                    profession, subject, present, absent, assignments, due_date, tone, "", mode=mode
                )
            elif profession == "teacher" and mode == "personal":
                mood = request.POST.get("mood", "")
                family_time = request.POST.get("family_time", "")
                stress_level = request.POST.get("stress_level", "")
                todo = request.POST.get("todo", "")
                tone = request.POST.get("tone", "neutral")
                suggestions = generate_with_tone(
                    profession, "", "", "", "", "", tone, "", mode=mode,
                    mood=mood, family_time=family_time, stress_level=stress_level, todo=todo
                )
            elif profession == "doctor" and mode == "professional":
                department = request.POST.get("department", "")
                patients = request.POST.get("patients", "")
                missed_appointments = request.POST.get("missed_appointments", "")
                procedures = request.POST.get("procedures", "")
                next_appointment = request.POST.get("next_appointment", "")
                tone = request.POST.get("tone", "neutral")
                suggestions = generate_with_tone(
                    profession, "", "", "", "", "", tone, "", mode=mode,
                    department=department,
                    patients=patients,
                    missed_appointments=missed_appointments,
                    procedures=procedures,
                    next_appointment=next_appointment
                )
            elif profession == "doctor" and mode == "personal":
                sleep_hours = request.POST.get("sleep_hours", "")
                exercise = request.POST.get("exercise", "")
                stress_level = request.POST.get("stress_level", "")
                relaxation = request.POST.get("relaxation", "")
                tone = request.POST.get("tone", "neutral")
                suggestions = generate_with_tone(
                    profession, "", "", "", "", "", tone, "", mode=mode,
                    sleep_hours=sleep_hours, exercise=exercise, stress_level=stress_level, relaxation=relaxation
                )
            elif profession == "business" and mode == "professional":
                domain = request.POST.get("domain", "")
                meetings = request.POST.get("meetings", "")
                clients = request.POST.get("clients", "")
                deals = request.POST.get("deals", "")
                deadline = request.POST.get("deadline", "")
                tone = request.POST.get("tone", "neutral")
                suggestions = generate_with_tone(
                    profession, "", "", "", "", "", tone, "", mode=mode,
                    domain=domain, meetings=meetings, clients=clients, deals=deals, deadline=deadline
                )
            elif profession == "business" and mode == "personal":
                daily_mood = request.POST.get("daily_mood", "")
                family_interaction = request.POST.get("family_interaction", "")
                financial_stress = request.POST.get("financial_stress", "")
                hobbies = request.POST.get("hobbies", "")
                tone = request.POST.get("tone", "neutral")
                suggestions = generate_with_tone(
                    profession, "", "", "", "", "", tone, "", mode=mode,
                    daily_mood=daily_mood, family_interaction=family_interaction,
                    financial_stress=financial_stress, hobbies=hobbies
                )

    return render(request, "echoapp/demo.html", {
        "suggestions": suggestions,
        "saved_entry": saved_entry,
        "user_profession": get_user_profession(request),
    })

def get_user_profession(request):
    """Get user's profession from their profile"""
    if request.user.is_authenticated:
        try:
            user_profile = request.user.profile
            user_type = user_profile.user_type
            # Map user types to profession values used in the form
            type_mapping = {
                'doctor': 'doctor',
                'teacher': 'teacher',
                'business_professional': 'business',
            }
            return type_mapping.get(user_type, 'teacher')
        except:
            pass
    return None
