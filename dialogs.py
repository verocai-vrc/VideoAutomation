import tkinter as tk
from tkinter import scrolledtext, ttk
from PIL import Image, ImageTk, ImageDraw

def show_script_review(parent, initial_script, on_approve, on_cancel):
    review_win = tk.Toplevel(parent)
    review_win.title("Review Generated Script")
    review_win.geometry("800x600")
    review_win.configure(bg="#2b2b2b")
    review_win.transient(parent)
    review_win.grab_set()
    
    tk.Label(review_win, text="Review and Edit the Generated Script:", font=('Arial', 12, 'bold'), bg="#2b2b2b", fg="#ffffff").pack(pady=10)
    
    text_area = scrolledtext.ScrolledText(review_win, wrap=tk.WORD, bg="#3b3b3b", fg="#ffffff", insertbackground="#ffffff", font=('Arial', 11))
    text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    text_area.insert(tk.END, initial_script)
    
    def approve():
        edited_script = text_area.get(1.0, tk.END).strip()
        review_win.destroy()
        on_approve(edited_script)
        
    def cancel():
        review_win.destroy()
        on_cancel()
        
    btn_frame = tk.Frame(review_win, bg="#2b2b2b")
    btn_frame.pack(fill=tk.X, pady=10)
    
    tk.Button(btn_frame, text="Approve & Continue", command=approve, bg="#4CAF50", fg="white", font=('Arial', 12, 'bold'), padx=20).pack(side=tk.RIGHT, padx=10)
    tk.Button(btn_frame, text="Cancel", command=cancel, bg="#f44336", fg="white", font=('Arial', 12, 'bold'), padx=20).pack(side=tk.RIGHT)
    
    review_win.protocol("WM_DELETE_WINDOW", cancel)

def show_image_review(parent, imagens_info, initial_terms, on_approve, on_retry, on_cancel, log_cb):
    review_win = tk.Toplevel(parent)
    review_win.title("Review Loaded Images")
    review_win.geometry("900x700")
    review_win.configure(bg="#2b2b2b")
    review_win.transient(parent)
    review_win.grab_set()
    
    tk.Label(review_win, text="Review Loaded Images:", font=('Arial', 12, 'bold'), bg="#2b2b2b", fg="#ffffff").pack(pady=10)
    
    canvas = tk.Canvas(review_win, bg="#3b3b3b", highlightthickness=0)
    scrollbar = ttk.Scrollbar(review_win, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg="#3b3b3b")
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="top", fill="both", expand=True, padx=10, pady=5)
    scrollbar.pack(side="right", fill="y")
    
    review_win.review_photos = [] # Keeping a reference to prevent garbage collection
    row, col = 0, 0
    max_cols = 4
    for info in imagens_info:
        try:
            if info['path'].lower().endswith(('.mp4', '.mov', '.avi', '.webm')):
                img = Image.new('RGB', (200, 200), (80, 80, 80))
                draw = ImageDraw.Draw(img)
                draw.polygon([(80, 60), (80, 140), (140, 100)], fill="white")
            else:
                with Image.open(info['path']) as img_file:
                    if img_file.mode != 'RGB':
                        img_file = img_file.convert('RGB')
                    img = img_file.copy()
                img.thumbnail((200, 200), Image.LANCZOS)
                bg = Image.new('RGB', (200, 200), (59, 59, 59))
                offset_x = (200 - img.width) // 2
                offset_y = (200 - img.height) // 2
                bg.paste(img, (offset_x, offset_y))
                img = bg
                
            photo = ImageTk.PhotoImage(img)
            review_win.review_photos.append(photo)
            
            frame = tk.Frame(scrollable_frame, bg="#3b3b3b")
            frame.grid(row=row, column=col, padx=10, pady=10)
            
            tk.Label(frame, image=photo, bg="#3b3b3b", bd=1, relief="solid").pack()
            kw_text = info['keyword']
            if len(kw_text) > 25: kw_text = kw_text[:22] + "..."
            tk.Label(frame, text=kw_text, bg="#3b3b3b", fg="#ffffff").pack(pady=(5, 0))
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        except Exception as e:
            log_cb(f"[!] Error loading preview for {info['path']}: {e}")
            
    bottom_panel = tk.Frame(review_win, bg="#2b2b2b")
    bottom_panel.pack(fill=tk.X, pady=10, padx=10)
    
    tk.Label(bottom_panel, text="Search Terms:", bg="#2b2b2b", fg="#ffffff", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
    terms_entry = tk.Entry(bottom_panel, bg="#3b3b3b", fg="#ffffff", width=40, insertbackground="#ffffff")
    terms_entry.pack(side=tk.LEFT, padx=10)
    terms_entry.insert(0, initial_terms)
    
    def approve_action():
        review_win.review_photos.clear()
        review_win.destroy()
        on_approve()

    def retry_action():
        new_terms = terms_entry.get()
        review_win.review_photos.clear()
        review_win.destroy()
        on_retry(new_terms)

    def cancel_action():
        review_win.review_photos.clear()
        review_win.destroy()
        on_cancel()
    
    tk.Button(bottom_panel, text="Approve & Continue", command=approve_action, bg="#4CAF50", fg="white", font=('Arial', 10, 'bold'), padx=15).pack(side=tk.RIGHT, padx=5)
    tk.Button(bottom_panel, text="Retry Search", command=retry_action, bg="#FF9800", fg="white", font=('Arial', 10, 'bold'), padx=15).pack(side=tk.RIGHT, padx=5)
    
    review_win.protocol("WM_DELETE_WINDOW", cancel_action)