import os
import tempfile
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout

from .forms import TaskForm, JournalEntryForm, SimpleRegistrationForm
from django.contrib.auth.views import LoginView
from django.db import OperationalError
from .models import JournalEntry, Task
from django.contrib import messages
from echoapp.nlp_module.mood_detector import analyze_text_emotions, get_mood_emoji

logger = logging.getLogger(__name__)

# Pre-load Whisper model at startup (faster transcriptions, loads once)
try:
    import whisper
    # Using 'base' model for FAST transcription with good accuracy
    # Options: tiny (fastest), base (fast & accurate), small (slower), medium (slowest)
    MODEL = whisper.load_model("base")
    logger.info("Whisper 'base' model loaded successfully for fast transcription")
except Exception as e:
    logger.warning(f"Whisper model not loaded at startup: {e}")
    MODEL = None

class ColourfulLoginView(LoginView):
    template_name = 'dashboard/login.html'
    
    def get_success_url(self):
        """Redirect to mode selection after login"""
        return reverse('select_mode')
    
    def form_valid(self, form):
        """Add success message when user logs in"""
        response = super().form_valid(form)
        messages.success(self.request, f'Welcome back, {self.request.user.username}! 🎉')
        return response
    
    def form_invalid(self, form):
        """Add custom error logging"""
        logger.warning(f"Failed login attempt for username: {form.cleaned_data.get('username', 'Unknown')}")
        return super().form_invalid(form)


def logout_view(request):
    # Clear session flags
    if 'tasks_notified' in request.session:
        del request.session['tasks_notified']
    if 'last_task_notification' in request.session:
        del request.session['last_task_notification']
    logout(request)
    return redirect('login')


def register_view(request):
    if request.method == 'POST':
        form = SimpleRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create UserProfile with user type
            from .models import UserProfile
            user_type = form.cleaned_data.get('user_type')
            UserProfile.objects.create(user=user, user_type=user_type)
            messages.success(request, f'Account created successfully! Please login.')
            return redirect('login')
    else:
        form = SimpleRegistrationForm()
    return render(request, 'dashboard/register.html', {'form': form})


@login_required
def select_mode(request):
    """Allow users to select Personal or Professional mode after login"""
    if request.method == 'POST':
        selected_mode = request.POST.get('mode', 'personal')
        # Store the mode in session
        request.session['user_mode'] = selected_mode
        messages.success(request, f'You have entered {selected_mode.capitalize()} mode')
        return redirect('dashboard')
    
    # GET request - show mode selection page
    return render(request, 'dashboard/select_mode.html')


@login_required
def add_task(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            return redirect('todo_list')
    else:
        form = TaskForm()
    return render(request, 'dashboard/add_task.html', {'form': form})


@login_required
def dashboard(request):
    from django.template import loader
    from django.utils import timezone
    from collections import defaultdict
    from datetime import date, timedelta

    # Get user's selected mode from session (default to 'personal')
    user_mode = request.session.get('user_mode', 'personal')

    # Get recent entries and group by date
    all_entries = JournalEntry.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    # Group entries by date
    entries_by_date = defaultdict(list)
    for entry in all_entries:
        entry_date = entry.created_at.date()
        entries_by_date[entry_date].append(entry)
    
    # Convert to sorted list of tuples (date, entries)
    grouped_entries = sorted(entries_by_date.items(), key=lambda x: x[0], reverse=True)[:3]  # Show only 3 most recent dates
    
    # Determine date labels (Today, Yesterday, or actual date)
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    date_labels = []
    for entry_date, entries_list in grouped_entries:
        if entry_date == today:
            label = "Today"
        elif entry_date == yesterday:
            label = "Yesterday"
        else:
            label = entry_date.strftime("%B %d, %Y")
        date_labels.append((label, entry_date, entries_list))
    
    tasks = Task.objects.filter(user=request.user, completed=False).order_by('due_date')[:5]
    
    # Check for pending and overdue tasks
    all_pending_tasks = Task.objects.filter(user=request.user, completed=False)
    pending_count = all_pending_tasks.count()
    overdue_tasks = all_pending_tasks.filter(due_date__lt=timezone.now())
    overdue_count = overdue_tasks.count()
    
    # Add notification ONLY for overdue tasks with regular interval reminders
    current_time = timezone.now()
    last_notified = request.session.get('last_task_notification')
    reminder_interval_minutes = 30  # Remind every 30 minutes
    
    should_notify = False
    if overdue_count > 0:
        if last_notified is None:
            # First time notification
            should_notify = True
        else:
            # Check if enough time has passed since last notification
            from datetime import datetime
            last_notified_time = datetime.fromisoformat(last_notified)
            time_diff = (current_time - last_notified_time).total_seconds() / 60  # Convert to minutes
            
            if time_diff >= reminder_interval_minutes:
                should_notify = True
    
    if should_notify:
        messages.warning(
            request, 
            f'⚠️ Reminder: You have {overdue_count} overdue task{"s" if overdue_count != 1 else ""}! Please complete {"them" if overdue_count != 1 else "it"} soon.'
        )
        # Update last notification time
        request.session['last_task_notification'] = current_time.isoformat()
    
    mood_count = {
        'happy': JournalEntry.objects.filter(user=request.user, mood='happy').count(),
        'neutral': JournalEntry.objects.filter(user=request.user, mood='neutral').count(),
        'sad': JournalEntry.objects.filter(user=request.user, mood='sad').count()
    }
    
    # Get user profile
    try:
        user_profile = request.user.profile
        user_type_display = user_profile.get_user_type_display()
    except:
        user_profile = None
        user_type_display = None
    
    try:
        template = loader.get_template('dashboard/dashboard.html')
        print(f"dashboard template origin: {getattr(template, 'origin', None)}")
    except Exception:
        logger.exception('failed to load dashboard template')

    return render(request, 'dashboard/dashboard.html', {
        'grouped_entries': date_labels,
        'tasks': tasks,
        'mood_count': mood_count,
        'user_mode': user_mode,
        'pending_count': pending_count,
        'overdue_count': overdue_count,
        'user_type': user_type_display,
    })


@login_required
def todo_list(request):
    """Render full task list; show a friendly hint if the table is missing/locked."""
    error_message = None
    tasks = []
    try:
        tasks = Task.objects.filter(user=request.user).order_by('due_date')
    except OperationalError as exc:  # e.g., missing table/column or locked DB
        logger.exception("Failed to load tasks")
        error_message = (
            "Could not load tasks. Please ensure migrations are applied and the database "
            "is not locked." 
        )

    return render(request, 'dashboard/todo_list.html', {
        'tasks': tasks,
        'todo_error': error_message,
    })


def complete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    task.completed = True
    task.save()
    
    # Reset notification timer when a task is completed
    # This will trigger a fresh check on next dashboard visit
    if 'last_task_notification' in request.session:
        del request.session['last_task_notification']
    
    messages.success(request, f'Task "{task.title}" marked as complete! 🎉')
    return redirect('todo_list')

@login_required
def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    task_title = task.title
    task.delete()
    
    # Reset notification timer when a task is deleted
    if 'last_task_notification' in request.session:
        del request.session['last_task_notification']
    
    messages.info(request, f'Task "{task_title}" has been deleted.')
    return redirect('todo_list')

@login_required
def delete_entry(request, entry_id):
    # Try to get entry for this user, or if user is None
    try:
        entry = JournalEntry.objects.get(id=entry_id)
        # Check if entry belongs to user or has no user assigned
        if entry.user and entry.user != request.user:
            messages.error(request, 'You do not have permission to delete this entry.')
            return redirect('dashboard')
    except JournalEntry.DoesNotExist:
        messages.error(request, 'Journal entry not found.')
        return redirect('dashboard')
    
    entry_title = entry.title
    entry.delete()
    
    messages.info(request, f'Journal entry "{entry_title}" has been deleted.')
    
    # Redirect back to the page they came from
    referer = request.META.get('HTTP_REFERER', '/')
    if 'journal' in referer:
        return redirect('journal')
    else:
        return redirect('dashboard')

def game_page(request):
    return render(request, 'dashboard/game_page.html')

# Balloon game removed - replaced with energy boosting and mood changing games
# def balloon_game(request):
#     return render(request, 'dashboard/balloon_game.html')

def memory_game(request):
    return render(request, 'dashboard/memory_game.html')

def breathing_exercise(request):
    return render(request, 'dashboard/breathing_exercise.html')

def voice(request):
    return render(request, 'dashboard/voice.html')

def improve_name_accuracy(text, user=None):
    """
    Post-process transcribed text to correct common name misrecognitions.
    Uses capitalization rules, common name patterns, and user-specific names.
    Enhanced with comprehensive name database for top-notch accuracy.
    """
    if not text:
        return text
    
    # COMPREHENSIVE name corrections database (100+ entries)
    common_corrections = {
        # Top 50 common first names (US)
        'john': 'John', 'mary': 'Mary', 'mike': 'Mike', 'michael': 'Michael',
        'sarah': 'Sarah', 'david': 'David', 'james': 'James', 'robert': 'Robert',
        'maria': 'Maria', 'jennifer': 'Jennifer', 'william': 'William', 'elizabeth': 'Elizabeth',
        'chris': 'Chris', 'christopher': 'Christopher', 'alex': 'Alex', 'alexander': 'Alexander',
        'sam': 'Sam', 'samuel': 'Samuel', 'taylor': 'Taylor', 'jordan': 'Jordan',
        'casey': 'Casey', 'jessica': 'Jessica', 'ashley': 'Ashley', 'matthew': 'Matthew',
        'joshua': 'Joshua', 'daniel': 'Daniel', 'andrew': 'Andrew', 'joseph': 'Joseph',
        'ryan': 'Ryan', 'brandon': 'Brandon', 'nicole': 'Nicole', 'amanda': 'Amanda',
        'brittany': 'Brittany', 'megan': 'Megan', 'emily': 'Emily', 'hannah': 'Hannah',
        'rachel': 'Rachel', 'madison': 'Madison', 'lauren': 'Lauren', 'stephanie': 'Stephanie',
        'jacob': 'Jacob', 'nicholas': 'Nicholas', 'tyler': 'Tyler', 'kevin': 'Kevin',
        'brian': 'Brian', 'eric': 'Eric', 'jonathan': 'Jonathan', 'jason': 'Jason',
        'anthony': 'Anthony', 'thomas': 'Thomas', 'charles': 'Charles', 'patricia': 'Patricia',
        'linda': 'Linda', 'barbara': 'Barbara', 'susan': 'Susan', 'karen': 'Karen',
        'lisa': 'Lisa', 'nancy': 'Nancy', 'betty': 'Betty', 'helen': 'Helen',
        'sandra': 'Sandra', 'donna': 'Donna', 'carol': 'Carol', 'michelle': 'Michelle',
        'laura': 'Laura', 'sharon': 'Sharon', 'cynthia': 'Cynthia', 'kathleen': 'Kathleen',
        'amy': 'Amy', 'angela': 'Angela', 'melissa': 'Melissa', 'brenda': 'Brenda',
        'anna': 'Anna', 'rebecca': 'Rebecca', 'virginia': 'Virginia', 'kathryn': 'Kathryn',
        'pamela': 'Pamela', 'martha': 'Martha', 'debra': 'Debra', 'deborah': 'Deborah',
        'julie': 'Julie', 'catherine': 'Catherine', 'heather': 'Heather', 'diane': 'Diane',
        'ruth': 'Ruth', 'sharon': 'Sharon', 'evelyn': 'Evelyn', 'judith': 'Judith',
        'emma': 'Emma', 'sophia': 'Sophia', 'olivia': 'Olivia', 'ava': 'Ava',
        'isabella': 'Isabella', 'mia': 'Mia', 'charlotte': 'Charlotte', 'abigail': 'Abigail',
        'harper': 'Harper', 'evelyn': 'Evelyn', 'ella': 'Ella', 'sofia': 'Sofia',
        'liam': 'Liam', 'noah': 'Noah', 'oliver': 'Oliver', 'ethan': 'Ethan',
        'lucas': 'Lucas', 'mason': 'Mason', 'logan': 'Logan', 'benjamin': 'Benjamin',
        'elijah': 'Elijah', 'aiden': 'Aiden', 'sebastian': 'Sebastian', 'jackson': 'Jackson',
        
        # Common last names
        'smith': 'Smith', 'johnson': 'Johnson', 'williams': 'Williams', 'brown': 'Brown',
        'jones': 'Jones', 'garcia': 'Garcia', 'miller': 'Miller', 'davis': 'Davis',
        'rodriguez': 'Rodriguez', 'martinez': 'Martinez', 'hernandez': 'Hernandez',
        'lopez': 'Lopez', 'gonzalez': 'Gonzalez', 'wilson': 'Wilson', 'anderson': 'Anderson',
        'thomas': 'Thomas', 'taylor': 'Taylor', 'moore': 'Moore', 'jackson': 'Jackson',
        'martin': 'Martin', 'lee': 'Lee', 'thompson': 'Thompson', 'white': 'White',
        'harris': 'Harris', 'clark': 'Clark', 'lewis': 'Lewis', 'robinson': 'Robinson',
        
        # Major cities (US)
        'new york': 'New York', 'los angeles': 'Los Angeles', 'chicago': 'Chicago',
        'houston': 'Houston', 'phoenix': 'Phoenix', 'philadelphia': 'Philadelphia',
        'san antonio': 'San Antonio', 'san diego': 'San Diego', 'dallas': 'Dallas',
        'san jose': 'San Jose', 'austin': 'Austin', 'jacksonville': 'Jacksonville',
        'san francisco': 'San Francisco', 'columbus': 'Columbus', 'charlotte': 'Charlotte',
        'fort worth': 'Fort Worth', 'detroit': 'Detroit', 'el paso': 'El Paso',
        'memphis': 'Memphis', 'seattle': 'Seattle', 'denver': 'Denver', 'washington': 'Washington',
        'boston': 'Boston', 'nashville': 'Nashville', 'baltimore': 'Baltimore',
        'portland': 'Portland', 'las vegas': 'Las Vegas', 'milwaukee': 'Milwaukee',
        'atlanta': 'Atlanta', 'miami': 'Miami', 'orlando': 'Orlando', 'tampa': 'Tampa',
        
        # States
        'california': 'California', 'texas': 'Texas', 'florida': 'Florida', 'new york': 'New York',
        'pennsylvania': 'Pennsylvania', 'illinois': 'Illinois', 'ohio': 'Ohio', 'georgia': 'Georgia',
        'north carolina': 'North Carolina', 'michigan': 'Michigan', 'new jersey': 'New Jersey',
        
        # Days and months (for better grammar)
        'monday': 'Monday', 'tuesday': 'Tuesday', 'wednesday': 'Wednesday', 'thursday': 'Thursday',
        'friday': 'Friday', 'saturday': 'Saturday', 'sunday': 'Sunday',
        'january': 'January', 'february': 'February', 'march': 'March', 'april': 'April',
        'may': 'May', 'june': 'June', 'july': 'July', 'august': 'August',
        'september': 'September', 'october': 'October', 'november': 'November', 'december': 'December',
    }
    
    # Add user-specific custom names if available
    if user and hasattr(user, 'profile'):
        try:
            custom_names = user.profile.get_custom_names_list()
            for name in custom_names:
                # Add lowercase version as key, proper case as value
                common_corrections[name.lower()] = name
        except Exception as e:
            logger.warning(f"Could not load custom names: {e}")
    
    # Apply corrections
    corrected_text = text
    import re
    for wrong, correct in common_corrections.items():
        # Case-insensitive replacement at word boundaries
        pattern = r'\b' + re.escape(wrong) + r'\b'
        corrected_text = re.sub(pattern, correct, corrected_text, flags=re.IGNORECASE)
    
    # ADVANCED GRAMMAR CORRECTIONS
    
    # Fix common contractions
    corrected_text = re.sub(r"\bim\b", "I'm", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\bive\b", "I've", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\bill\b", "I'll", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\bwont\b", "won't", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\bcant\b", "can't", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\bdont\b", "don't", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\bdidnt\b", "didn't", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\bisnt\b", "isn't", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\barent\b", "aren't", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\bwasnt\b", "wasn't", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\bwerent\b", "weren't", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\bhasnt\b", "hasn't", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\bhavent\b", "haven't", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\bcouldnt\b", "couldn't", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\bshouldnt\b", "shouldn't", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\bwouldnt\b", "wouldn't", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\bthats\b", "that's", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\btheres\b", "there's", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\bwhats\b", "what's", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\blets\b", "let's", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\bhes\b", "he's", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\bshes\b", "she's", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\btheyre\b", "they're", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\bwere\s+going\b", "we're going", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\byoure\b", "you're", corrected_text, flags=re.IGNORECASE)
    corrected_text = re.sub(r"\bitsits\b", "it's", corrected_text, flags=re.IGNORECASE)
    
    # Fix common number words
    corrected_text = re.sub(r"\bwon\b", "one", corrected_text)  # when context is numerical
    
    # Capitalize first letter after sentence markers
    sentences = re.split(r'([.!?]\s+)', corrected_text)
    capitalized = []
    for i, part in enumerate(sentences):
        if i % 2 == 0 and part:  # Text parts (not punctuation)
            # Capitalize first letter
            part = part[0].upper() + part[1:] if len(part) > 0 else part
        capitalized.append(part)
    corrected_text = ''.join(capitalized)
    
    # Capitalize 'I' when standalone (critical for English)
    corrected_text = re.sub(r'\bi\b', 'I', corrected_text)
    
    # Fix spacing around punctuation
    corrected_text = re.sub(r'\s+([.,!?;:])', r'\1', corrected_text)  # Remove space before punctuation
    corrected_text = re.sub(r'([.,!?;:])([^\s])', r'\1 \2', corrected_text)  # Add space after punctuation
    
    # Remove multiple spaces
    corrected_text = re.sub(r'\s+', ' ', corrected_text).strip()
    
    return corrected_text

@csrf_exempt
def transcribe_view(request):
    """
    Accepts a POST multipart/form-data with field 'file' (audio).
    Returns JSON with transcribed text and detected mood.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    if 'file' not in request.FILES:
        return JsonResponse({'error': 'no file part'}, status=400)

    f = request.FILES['file']
    if f.name == '':
        return JsonResponse({'error': 'no selected file'}, status=400)

    if MODEL is None:
        return JsonResponse({'error': 'whisper not installed on server'}, status=500)

    # Save to a temporary file
    suffix = os.path.splitext(f.name)[1] or '.wav'
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            for chunk in f.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        # Transcribe using optimized parameters for FAST processing
        result = MODEL.transcribe(
            tmp_path,
            language='en',  # Specify English
            task='transcribe',
            temperature=0.0,  # Deterministic output
            beam_size=1,  # Faster - no beam search (greedy decoding)
            best_of=1,  # Faster - single candidate
            word_timestamps=False,  # Faster processing
            condition_on_previous_text=False,  # Faster - no context conditioning
            fp16=True  # Faster processing with GPU/CPU optimization
        )
        text = result.get('text', '').strip()
        
        # Check transcription quality
        avg_logprob = result.get('language_probability', 0)
        logger.info(f"Transcription completed. Length: {len(text)} chars, Language confidence: {avg_logprob:.2f}")
        
        # Post-process to improve name accuracy (pass user for custom names)
        user = request.user if request.user.is_authenticated else None
        text = improve_name_accuracy(text, user)
        
        # Detect mood from transcribed text
        emotion_analysis = analyze_text_emotions(text)
        
        return JsonResponse({
            'text': text,
            'mood': emotion_analysis['primary_mood'],
            'mood_confidence': emotion_analysis['mood_confidence'],
            'polarity': emotion_analysis['polarity'],
            'emoji': emotion_analysis['emoji'],
            'description': emotion_analysis['description'],
            'detected_emotions': emotion_analysis['detected_emotions']
        })
    except Exception as e:
        logger.exception("transcription failed")
        return JsonResponse({'error': 'transcription failed', 'details': str(e)}, status=500)
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

def transcribe(request):
    return render(request, 'dashboard/transcribe.html')


@login_required
def journal_mode_select(request):
    """
    Allow users to select journal mode (Personal or Professional) before journaling.
    """
    if request.method == 'POST':
        selected_mode = request.POST.get('mode', 'personal')
        # Store the selected journal mode in session
        request.session['journal_mode'] = selected_mode
        messages.success(request, f'✨ {selected_mode.capitalize()} mode selected!')
        return redirect('journal_method_select')
    
    # GET request - show mode selection page
    return render(request, 'dashboard/journal_mode_select.html')


@login_required
def journal_method_select(request):
    """
    Show journaling method selection (Voice, Keywords, Text) after mode is selected.
    """
    # Get the user mode selected at login (default to 'personal')
    user_mode = request.session.get('user_mode', 'personal')
    
    return render(request, 'dashboard/journal_method_select.html', {
        'journal_mode': user_mode,
    })


@login_required
def journal(request):
    from collections import defaultdict
    from datetime import date
    
    # Get the user mode selected at login (default to 'personal')
    journal_mode = request.session.get('user_mode', 'personal')
    
    saved = request.GET.get('saved')
    if request.method == 'POST':
        form = JournalEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            # Set the mode from session
            entry.mode = journal_mode
            entry.save()
            return redirect(f"{reverse('journal')}?saved=1")
    else:
        form = JournalEntryForm()

    # Get all entries for the user, ordered by newest first
    all_entries = JournalEntry.objects.filter(user=request.user).order_by('-created_at')
    
    # Group entries by date
    entries_by_date = defaultdict(list)
    for entry in all_entries:
        entry_date = entry.created_at.date()
        entries_by_date[entry_date].append(entry)
    
    # Convert to sorted list of tuples (date, entries)
    grouped_entries = sorted(entries_by_date.items(), key=lambda x: x[0], reverse=True)
    
    # Determine date labels (Today, Yesterday, or actual date)
    today = date.today()
    from datetime import timedelta
    yesterday = today - timedelta(days=1)
    
    date_labels = []
    for entry_date, entries in grouped_entries:
        if entry_date == today:
            label = "Today"
        elif entry_date == yesterday:
            label = "Yesterday"
        else:
            label = entry_date.strftime("%B %d, %Y")
        date_labels.append((label, entry_date, entries))
    
    return render(request, 'dashboard/journal.html', {
        'form': form,
        'grouped_entries': date_labels,
        'saved': saved,
        'journal_mode': journal_mode,
    })


@csrf_exempt
def save_voice_entry(request):
    """
    Saves a voice journal entry with detected mood.
    Expects POST data with: text, mood, mood_confidence, title (optional)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        
        text = data.get('text', '').strip()
        mood = data.get('mood', 'neutral')
        mood_confidence = data.get('mood_confidence', 0.0)
        title = data.get('title', 'Voice Entry').strip() or 'Voice Entry'
        polarity = data.get('polarity', 0.0)
        detected_emotions = data.get('detected_emotions', [])
        
        if not text:
            return JsonResponse({'error': 'No text provided'}, status=400)
        
        # Get the user mode selected at login (default to 'personal')
        journal_mode = request.session.get('user_mode', 'personal')
        
        # Create journal entry
        entry = JournalEntry.objects.create(
            user=request.user if request.user.is_authenticated else None,
            title=title,
            content=text,
            mood=mood,
            mood_confidence=mood_confidence,
            sentiment_polarity=polarity,
            detected_emotions=detected_emotions,
            is_voice_entry=True,
            voice_transcript=text,
            mode=journal_mode  # Use the session mode
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Voice entry saved successfully',
            'entry_id': entry.id,
            'emoji': get_mood_emoji(mood)
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.exception("Failed to save voice entry")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def generate_from_keywords(request):
    """
    Generates complete sentences from keywords using the NLP engine.
    Expects POST data with: keywords (string)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        
        keywords = data.get('keywords', '').strip()
        
        if not keywords:
            return JsonResponse({'error': 'No keywords provided'}, status=400)
        
        # Split keywords and generate sentences
        keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
        
        if not keyword_list:
            return JsonResponse({'error': 'Please provide valid keywords'}, status=400)
        
        # Generate sentences based on keywords
        generated_sentences = []
        
        for keyword in keyword_list:
            # Simple sentence generation (you can enhance this with more sophisticated NLP)
            keyword_lower = keyword.lower()
            
            # Pattern-based sentence generation
            if any(word in keyword_lower for word in ['happy', 'joy', 'excited', 'great']):
                generated_sentences.append(f"I felt {keyword} today, and it brought positivity to my day.")
            elif any(word in keyword_lower for word in ['sad', 'tired', 'stressed', 'frustrated', 'angry']):
                generated_sentences.append(f"I experienced {keyword}, which affected my mood significantly.")
            elif any(word in keyword_lower for word in ['work', 'meeting', 'project', 'deadline']):
                generated_sentences.append(f"Today involved {keyword}, which required my attention and focus.")
            elif any(word in keyword_lower for word in ['family', 'friend', 'colleague', 'people']):
                generated_sentences.append(f"I spent time with {keyword}, which was meaningful to me.")
            else:
                # Generic sentence for any other keyword
                generated_sentences.append(f"Today, {keyword} was an important part of my experience.")
        
        # Combine into a paragraph
        if len(generated_sentences) == 1:
            generated_text = generated_sentences[0]
        elif len(generated_sentences) == 2:
            generated_text = f"{generated_sentences[0]} {generated_sentences[1]}"
        else:
            # Create a more natural paragraph structure
            first_part = ". ".join(generated_sentences[:2])
            middle_part = ". ".join(generated_sentences[2:-1]) if len(generated_sentences) > 3 else ""
            last_part = generated_sentences[-1]
            
            if middle_part:
                generated_text = f"{first_part}. {middle_part}. {last_part}"
            else:
                generated_text = f"{first_part}. {last_part}"
        
        # Add reflection ending
        generated_text += " Overall, these experiences shaped my day in different ways."
        
        return JsonResponse({
            'success': True,
            'generated_text': generated_text,
            'keyword_count': len(keyword_list)
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.exception("Failed to generate from keywords")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def save_custom_names(request):
    """
    Saves user's custom names for improved voice recognition.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        custom_names = request.POST.get('custom_names', '').strip()
        
        # Get or create user profile
        from .models import UserProfile
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        profile.custom_names = custom_names
        profile.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Custom names saved successfully'
        })
    
    except Exception as e:
        logger.exception("Failed to save custom names")
        return JsonResponse({'error': str(e)}, status=500)
