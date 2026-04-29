#!/usr/bin/env python3
"""Simple test to verify GUI works"""
import tkinter as tk
from tkinter import ttk, scrolledtext

root = tk.Tk()
root.title("Test GUI")
root.geometry("600x400")

# Main frame
main = ttk.Frame(root, padding="10")
main.pack(fill=tk.BOTH, expand=True)

# Title
ttk.Label(main, text="PRD Ticket Agent Test", font=("Helvetica", 16, "bold")).pack(pady=10)

# Text area
text = scrolledtext.ScrolledText(main, height=15, width=60)
text.pack(fill=tk.BOTH, expand=True, pady=10)
text.insert("1.0", "If you can see this, the GUI is working!\n\n")

# Input
input_frame = ttk.Frame(main)
input_frame.pack(fill=tk.X, pady=10)

entry = tk.Text(input_frame, height=2)
entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
entry.insert("1.0", "Type here...")

button = ttk.Button(input_frame, text="Send")
button.pack(side=tk.RIGHT)

root.mainloop()












