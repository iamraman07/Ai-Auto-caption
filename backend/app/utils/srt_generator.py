def split_segments(segments: list, max_words=6, max_chars=35, max_duration=12.0) -> list:
    """
    Takes a list of segments and recursively splits any segment that is too long
    into smaller segments, distributing the original timestamp proportionally.
    Enforces a strict duration cap to break up long lingering subtitles.
    """
    split_result = []
    
    for seg in segments:
        text = seg["text"].strip()
        words = text.split()
        duration = float(seg["end"]) - float(seg["start"])
        
        # If segment is within word, character, and time limits, keep it
        if len(words) <= max_words and len(text) <= max_chars and duration <= max_duration:
            split_result.append(seg)
            continue
            
        # Otherwise, split it by packing words
        lines = []
        current_line = []
        current_char_count = 0
        
        for word in words:
            if current_char_count + len(word) + 1 > max_chars or len(current_line) >= max_words:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_char_count = len(word)
            else:
                current_line.append(word)
                current_char_count += len(word) + 1
                
        if current_line:
            lines.append(" ".join(current_line))
            
        # Calculate proportional timestamps
        total_chars = sum(len(line) for line in lines)
        start_time = float(seg["start"])
        end_time = float(seg["end"])
        duration = end_time - start_time
        
        current_start = start_time
        for line in lines:
            if total_chars == 0:
                line_duration = duration / len(lines)
            else:
                line_duration = duration * (len(line) / total_chars)
                
            line_end = current_start + line_duration
            split_result.append({
                "start": current_start,
                "end": line_end,
                "text": line
            })
            current_start = line_end
            
    return split_result

def format_timestamp(seconds: float) -> str:
    """
    Converts a float amount of seconds into SRT timestamp format.
    Example: 3.2 -> 00:00:03,200
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int(round((seconds - int(seconds)) * 1000))

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

def generate_srt(segments: list) -> str:
    """
    Converts a list of Whisper segments into SRT string format.
    Does not merge segments, respecting the explicit frontend/timestamp formatting.
    """
    if not segments:
        return ""

    srt_content = ""
    for i, segment in enumerate(segments, start=1):
        start_time = format_timestamp(float(segment["start"]))
        end_time = format_timestamp(float(segment["end"]))
        text = segment["text"].strip()
        
        # SRT Format Block:
        # 1
        # 00:00:00,000 --> 00:00:03,000
        # Text goes here
        # (empty line separating entries)
        srt_content += f"{i}\n"
        srt_content += f"{start_time} --> {end_time}\n"
        srt_content += f"{text}\n\n"
        
    return srt_content
