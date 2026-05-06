import os
import pysubs2

def run_subtitle_test():
    import glob
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    
    # Find the most recently created .srt file
    srt_files = glob.glob(os.path.join(assets_dir, "*.srt"))
    if not srt_files:
        print("[!] Error: No .srt files found. Run the main generator first.")
        return
        
    srt_path = max(srt_files, key=os.path.getctime)
    debug_out = os.path.join(assets_dir, "debug_subtitles.txt")
    
    print(f"--- Running Subtitle Test on: {srt_path} ---")

    try:
        subs = pysubs2.load(srt_path, encoding="utf-8")
    except Exception as e:
        print(f"[!] Error loading subtitles: {str(e)}")
        subs = []
        
    print(f"[*] TEST 1: Loaded {len(subs)} raw subtitle blocks from SRT.")
    
    # Reproduce the MoviePy rendering grouping logic
    grouped_subs = []
    if subs:
        current_line_text = ""
        line_start_time = subs[0].start
        last_word_end_time = subs[0].end
        max_chars_per_line = 60

        for event in subs:
            if len(current_line_text) + len(event.text) + 1 > max_chars_per_line and current_line_text:
                grouped_subs.append({"text": current_line_text.strip(), "start": line_start_time, "end": last_word_end_time})
                current_line_text = event.text + " "
                line_start_time = event.start
            else:
                current_line_text += event.text + " "
            last_word_end_time = event.end

        if current_line_text:
            grouped_subs.append({"text": current_line_text.strip(), "start": line_start_time, "end": last_word_end_time})

    print(f"[*] TEST 2: Grouped into {len(grouped_subs)} lines for rendering.")
    
    with open(debug_out, "w", encoding="utf-8") as f:
        f.write("--- EXPORTED SUBTITLES FOR VERIFICATION ---\n")
        for i, line in enumerate(grouped_subs):
            f.write(f"[{line['start']}ms -> {line['end']}ms] {line['text']}\n")
            if i < 3: 
                print(f"  -> Sample {i+1}: {line['text']}")
                
    print(f"[*] Full subtitle list exported to: {debug_out}")

if __name__ == "__main__":
    run_subtitle_test()