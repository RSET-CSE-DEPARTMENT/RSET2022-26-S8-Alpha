import numpy as np

def score_speed(length_ratio):
    deviation = abs(length_ratio - 1.0)
    
    if deviation <= 0.2:
        score = 100 - (deviation / 0.2) * 10
        category = "Excellent"
    elif deviation <= 0.5:
        score = 90 - ((deviation - 0.2) / 0.3) * 50
        category = "Fair"
    else:
        score = max(0, 40 - ((deviation - 0.5) / 0.5) * 40)
        category = "Critical"
    
    return {
        'score': round(score, 2),
        'normalized_score': round(score / 100, 3),
        'category': category
    }


def score_mae(mae):
    if mae <= 10:
        score = 100 - (mae / 10) * 10
        category = "Excellent"
    elif mae <= 25:
        score = 90 - ((mae - 10) / 15) * 50
        category = "Fair"
    else:
        score = max(0, 40 - ((mae - 25) / 25) * 40)
        category = "Critical"
    
    return {
        'score': round(score, 2),
        'normalized_score': round(score / 100, 3),
        'category': category
    }


def score_rmse(rmse, mae):
    if rmse <= 10:
        score = 100 - (rmse / 10) * 10
        category = "Excellent"
    elif rmse <= 25:
        score = 90 - ((rmse - 10) / 15) * 50
        category = "Fair"
    else:
        score = max(0, 40 - ((rmse - 25) / 25) * 40)
        category = "Critical"
    
    consistency_ratio = rmse / mae if mae > 0 else 1.0
    if consistency_ratio > 1.5:
        score *= 0.9
    
    return {
        'score': round(score, 2),
        'normalized_score': round(score / 100, 3),
        'category': category,
        'consistency_ratio': round(consistency_ratio, 3)
    }


def score_rom(rom_difference, trainer_rom):
    abs_diff = abs(rom_difference)
    rom_percentage = (rom_difference / trainer_rom) * 100 if trainer_rom > 0 else 0
    
    if abs_diff <= 10:
        score = 100 - (abs_diff / 10) * 10
        category = "Excellent"
    elif abs_diff <= 25:
        score = 90 - ((abs_diff - 10) / 15) * 50
        category = "Fair"
    else:
        score = max(0, 40 - ((abs_diff - 25) / 25) * 40)
        category = "Critical"
    
    return {
        'score': round(score, 2),
        'normalized_score': round(score / 100, 3),
        'category': category,
        'rom_difference_degrees': round(rom_difference, 2),
        'rom_difference_percentage': round(rom_percentage, 2)
    }


def score_max_deviation(max_deviation):
    if max_deviation <= 10:
        score = 100 - (max_deviation / 10) * 10
        category = "Excellent"
    elif max_deviation <= 30:
        score = 90 - ((max_deviation - 10) / 20) * 50
        category = "Fair"
    else:
        score = max(0, 40 - ((max_deviation - 30) / 30) * 40)
        category = "Critical"
    
    return {
        'score': round(score, 2),
        'normalized_score': round(score / 100, 3),
        'category': category
    }


def calculate_overall_score(scores_dict, weights=None):
    if weights is None:
        weights = {
            'speed': 0.20,
            'mae': 0.30,
            'rmse': 0.25,
            'rom': 0.15,
            'max_deviation': 0.10
        }
    
    overall_score = (
        scores_dict['speed']['score'] * weights['speed'] +
        scores_dict['mae']['score'] * weights['mae'] +
        scores_dict['rmse']['score'] * weights['rmse'] +
        scores_dict['rom']['score'] * weights['rom'] +
        scores_dict['max_deviation']['score'] * weights['max_deviation']
    )
    
    if overall_score >= 80:
        category = "Excellent"
    elif overall_score >= 50:
        category = "Fair"
    else:
        category = "Critical"
    
    weak_areas = []
    for metric, score_obj in scores_dict.items():
        if score_obj['score'] < 60:
            weak_areas.append({
                'metric': metric,
                'score': score_obj['score'],
                'category': score_obj['category']
            })
    weak_areas.sort(key=lambda x: x['score'])
    
    return {
        'overall_score': round(overall_score, 2),
        'normalized_score': round(overall_score / 100, 3),
        'category': category,
        'weak_areas': weak_areas[:3]
    }


def score_all_metrics(results):
    scores = {
        'speed': score_speed(results['length_ratio']),
        'mae': score_mae(results['mae']),
        'rmse': score_rmse(results['rmse'], results['mae']),
        'rom': score_rom(results['rom_difference'], results['trainer_rom']),
        'max_deviation': score_max_deviation(results['max_deviation'])
    }

    scores['overall'] = calculate_overall_score(scores)
    return scores


def generate_feedback_messages(results: dict) -> dict:
    """
    Generate human-readable feedback messages based on rep comparison metrics.

    Args:
        results: Dictionary from compare_reps() containing all metrics

    Returns:
        Dictionary with feedback messages for each metric category
    """
    # Get scores using existing functions
    scores = score_all_metrics(results)

    feedback = {}

    # Speed feedback
    length_ratio = results['length_ratio']
    speed_score = scores['speed']
    if length_ratio > 1.2:
        feedback['speed'] = {
            'category': speed_score['category'],
            'message': f"You're moving {((length_ratio - 1) * 100):.0f}% slower than the trainer.",
            'advice': "Try to increase your pace to match the trainer's tempo."
        }
    elif length_ratio < 0.8:
        feedback['speed'] = {
            'category': speed_score['category'],
            'message': f"You're moving {((1 - length_ratio) * 100):.0f}% faster than the trainer.",
            'advice': "Slow down to maintain control and proper form."
        }
    else:
        feedback['speed'] = {
            'category': speed_score['category'],
            'message': "Your pace matches the trainer well.",
            'advice': "Keep maintaining this tempo."
        }

    # Accuracy feedback (MAE)
    mae = results['mae']
    mae_score = scores['mae']
    if mae > 25:
        feedback['accuracy'] = {
            'category': mae_score['category'],
            'message': f"Average deviation of {mae:.1f}° from trainer's form.",
            'advice': "Focus on matching the trainer's movement pattern more closely."
        }
    elif mae > 10:
        feedback['accuracy'] = {
            'category': mae_score['category'],
            'message': f"Minor deviation of {mae:.1f}° from trainer's form.",
            'advice': "Small adjustments needed to perfect your form."
        }
    else:
        feedback['accuracy'] = {
            'category': mae_score['category'],
            'message': f"Excellent form accuracy ({mae:.1f}° average deviation).",
            'advice': "Great job! Maintain this precision."
        }

    # ROM feedback
    rom_diff = results['rom_difference']
    rom_score = scores['rom']
    user_rom = results['user_rom']
    trainer_rom = results['trainer_rom']
    if rom_diff < -15:
        feedback['rom'] = {
            'category': rom_score['category'],
            'message': f"Your range of motion ({user_rom:.1f}°) is {abs(rom_diff):.1f}° less than trainer ({trainer_rom:.1f}°).",
            'advice': "Extend your movement further to achieve full range of motion."
        }
    elif rom_diff > 15:
        feedback['rom'] = {
            'category': rom_score['category'],
            'message': f"Your range of motion ({user_rom:.1f}°) exceeds trainer ({trainer_rom:.1f}°) by {rom_diff:.1f}°.",
            'advice': "Control your movement to avoid overextension."
        }
    else:
        feedback['rom'] = {
            'category': rom_score['category'],
            'message': f"Good range of motion ({user_rom:.1f}° vs trainer's {trainer_rom:.1f}°).",
            'advice': "Maintain this range throughout your workout."
        }

    # Consistency feedback (RMSE)
    rmse = results['rmse']
    rmse_score = scores['rmse']
    consistency_ratio = rmse / mae if mae > 0 else 1.0
    if consistency_ratio > 1.5:
        feedback['consistency'] = {
            'category': rmse_score['category'],
            'message': "Your movement has inconsistent spikes in deviation.",
            'advice': "Focus on smooth, controlled movements throughout the rep."
        }
    else:
        feedback['consistency'] = {
            'category': rmse_score['category'],
            'message': "Your movement pattern is consistent.",
            'advice': "Good consistency - keep your movements smooth."
        }

    # Max deviation feedback
    max_dev = results['max_deviation']
    max_frame = results['max_deviation_frame']
    max_dev_score = scores['max_deviation']
    total_frames = int((results['user_length'] + results['trainer_length']) / 2)
    position_pct = (max_frame / total_frames * 100) if total_frames > 0 else 0

    if position_pct < 33:
        position_desc = "at the start"
    elif position_pct < 66:
        position_desc = "in the middle"
    else:
        position_desc = "at the end"

    if max_dev > 30:
        feedback['max_deviation'] = {
            'category': max_dev_score['category'],
            'message': f"Largest deviation of {max_dev:.1f}° occurred {position_desc} of the rep.",
            'advice': f"Pay extra attention to your form {position_desc} of each rep."
        }
    else:
        feedback['max_deviation'] = {
            'category': max_dev_score['category'],
            'message': f"No major form breaks (max deviation: {max_dev:.1f}°).",
            'advice': "Excellent control throughout the movement."
        }

    # Generate summary
    overall = scores['overall']
    weak_areas = overall.get('weak_areas', [])

    if overall['category'] == 'Excellent':
        summary = "Excellent rep! Your form closely matches the trainer."
    elif overall['category'] == 'Fair':
        if weak_areas:
            weak_names = [w['metric'] for w in weak_areas[:2]]
            summary = f"Good effort! Focus on improving: {', '.join(weak_names)}."
        else:
            summary = "Good rep with room for improvement."
    else:
        if weak_areas:
            weak_names = [w['metric'] for w in weak_areas[:2]]
            summary = f"Needs work. Priority areas: {', '.join(weak_names)}."
        else:
            summary = "This rep needs significant improvement."

    feedback['summary'] = summary
    feedback['overall_score'] = overall['overall_score']
    feedback['overall_category'] = overall['category']

    return feedback


def interpolate_to_length(arr, target_length):
    current_length = len(arr)
    grid_old = np.linspace(0, 1, current_length)
    grid_new = np.linspace(0, 1, target_length)
    interpolated = np.interp(grid_new, grid_old, arr)
    return interpolated


def compare_reps(user_array, trainer_array):
    user_length = len(user_array)
    trainer_length = len(trainer_array)
    length_ratio = user_length / trainer_length if trainer_length > 0 else 0
    
    user_min = np.min(user_array)
    user_max = np.max(user_array)
    user_start = user_array[0]
    user_end = user_array[-1]
    
    trainer_min = np.min(trainer_array)
    trainer_max = np.max(trainer_array)
    trainer_start = trainer_array[0]
    trainer_end = trainer_array[-1]
    
    user_rom = user_max - user_min
    trainer_rom = trainer_max - trainer_min
    rom_difference = user_rom - trainer_rom
    
    avg_length = int(round((user_length + trainer_length) / 2))
    user_interpolated = interpolate_to_length(user_array, avg_length)
    trainer_interpolated = interpolate_to_length(trainer_array, avg_length)
    
    errors = np.abs(user_interpolated - trainer_interpolated)
    mae = np.mean(errors)
    rmse = np.sqrt(np.mean((user_interpolated - trainer_interpolated) ** 2))
    max_deviation = np.max(errors)
    max_deviation_frame = np.argmax(errors)
    
    return {
        'user_length': user_length,
        'trainer_length': trainer_length,
        'length_ratio': length_ratio,
        'user_min': user_min,
        'user_max': user_max,
        'user_start': user_start,
        'user_end': user_end,
        'trainer_min': trainer_min,
        'trainer_max': trainer_max,
        'trainer_start': trainer_start,
        'trainer_end': trainer_end,
        'user_rom': user_rom,
        'trainer_rom': trainer_rom,
        'rom_difference': rom_difference,
        'mae': mae,
        'rmse': rmse,
        'max_deviation': max_deviation,
        'max_deviation_frame': max_deviation_frame
    }


def analyze_rep(user_array, trainer_array):
    results = compare_reps(user_array, trainer_array)
    scores = score_all_metrics(results)
    feedback = generate_feedback_messages(results)
    return scores, feedback


if __name__ == "__main__":
    trainer = np.array([30, 45, 60, 80, 95, 110, 120, 130, 135, 130, 120, 110, 95, 80, 60, 45, 30])
    user = np.array([50, 70, 85, 75, 90, 70, 85, 95, 90])    
    result, feedback = analyze_rep(user, trainer)
    print(result)
    print("\n\n")
    print(feedback)