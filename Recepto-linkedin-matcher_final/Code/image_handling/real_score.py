import json

def calculate_real_confidence(match_score, face_confidence):
    """
    Calculate real confidence score based on rules:
    1. If face_confidence > 0.8, real_confidence = 1
    2. Else, real_confidence = (match_score + face_confidence) / 2 (but capped at 0.99)
    """
    if face_confidence is not None and face_confidence > 0.8:
        return 1.0
    elif face_confidence is not None:
        # Weighted average where neither can push score to 1 without meeting face threshold
        combined = match_score*0.8 + face_confidence*0.2
        return min(combined, 0.99)  # Cap at 0.99 to ensure it can't reach 1 without face > 0.8
    else:
        # No face confidence available, use match score but cap at 0.8
        return min(match_score, 0.8)

def process_output_file(input_file='D:\RECEPTO-FINALLLL\Recepto-linkedin-matcher_final\Recepto-linkedin-matcher\scrapper\output.json', output_file='enhanced_output.json'):
    # Load the input data
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Process each persona and their matches
    for persona in data:
        for match in persona['matches']:
            match_score = match.get('match_score', 0)
            face_confidence = match.get('face_confidence')
            
            # Calculate and add the real confidence score
            match['real_confidence_score'] = calculate_real_confidence(match_score, face_confidence)
    
    # Save the enhanced output
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Enhanced output saved to {output_file}")

if __name__ == "__main__":
    process_output_file()