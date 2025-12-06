"""
Simple Chat Window for STFOOM
============================
Provides a basic chat interface for users.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
from typing import List, Dict, Any
import json
import os

class SimpleChatWindow(tk.Toplevel):
    """Simple chat window with basic messaging functionality."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("💬 Chat - STFOOM")
        self.geometry("600x500")
        self.resizable(True, True)
        
        # Center the window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.winfo_screenheight() // 2) - (500 // 2)
        self.geometry(f"600x500+{x}+{y}")
        
        # Set window icon and properties
        self.transient(parent)
        
        # Chat data storage
        self.chat_file = os.path.join("data", "chat_messages.json")
        self.messages = self.load_messages()
        
        # Current user from session
        self.current_user = self.get_current_user()
        
        self.setup_ui()
        self.load_chat_display()
        
    def setup_ui(self):
        """Setup the chat window UI."""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        title_label = ttk.Label(
            header_frame, 
            text="💬 Chat Simple", 
            font=("Segoe UI", 14, "bold")
        )
        title_label.pack(side="left")
        
        # Online users indicator (placeholder)
        online_label = ttk.Label(
            header_frame, 
            text="👥 En ligne: 1", 
            font=("Segoe UI", 10),
            foreground="green"
        )
        online_label.pack(side="right")
        
        # Chat display area
        chat_frame = ttk.LabelFrame(self, text="Messages", padding=5)
        chat_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Messages display
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            height=20,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            state=tk.DISABLED,
            background="#f8f9fa",
            foreground="#212529"
        )
        self.chat_display.pack(fill="both", expand=True)
        
        # Configure text tags for different message types
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.tag_config("user_msg", foreground="#0066cc", font=("Segoe UI", 10, "bold"))
        self.chat_display.tag_config("timestamp", foreground="#666666", font=("Segoe UI", 9))
        self.chat_display.tag_config("system_msg", foreground="#28a745", font=("Segoe UI", 10, "italic"))
        self.chat_display.config(state=tk.DISABLED)
        
        # Message input area
        input_frame = ttk.Frame(self)
        input_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        # Message entry
        ttk.Label(input_frame, text="Message:", font=("Segoe UI", 10)).pack(anchor="w")
        
        entry_frame = ttk.Frame(input_frame)
        entry_frame.pack(fill="x", pady=(2, 0))
        
        self.message_entry = ttk.Entry(
            entry_frame, 
            font=("Segoe UI", 10),
            width=60
        )
        self.message_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        send_button = ttk.Button(
            entry_frame,
            text="📨 Envoyer",
            command=self.send_message,
            style="Primary.TButton"
        )
        send_button.pack(side="right")
        
        # Bind Enter key to send message
        self.message_entry.bind("<Return>", lambda e: self.send_message())
        self.message_entry.focus_set()
        
        # Status bar
        status_frame = ttk.Frame(self)
        status_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        self.status_label = ttk.Label(
            status_frame, 
            text="💡 Appuyez sur Entrée pour envoyer un message", 
            font=("Segoe UI", 9),
            foreground="#666666"
        )
        self.status_label.pack(side="left")
        
        # Clear chat button
        clear_button = ttk.Button(
            status_frame,
            text="🗑️ Effacer",
            command=self.clear_chat,
            style="Secondary.TButton"
        )
        clear_button.pack(side="right")
        
    def load_messages(self) -> List[Dict[str, Any]]:
        """Load chat messages from file."""
        try:
            if os.path.exists(self.chat_file):
                with open(self.chat_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"[CHAT] Error loading messages: {e}")
            return []
    
    def save_messages(self):
        """Save chat messages to file."""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.chat_file), exist_ok=True)
            
            with open(self.chat_file, 'w', encoding='utf-8') as f:
                json.dump(self.messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[CHAT] Error saving messages: {e}")
    
    def load_chat_display(self):
        """Load and display existing chat messages."""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        
        if not self.messages:
            # Welcome message
            welcome_msg = "🎉 Bienvenue dans le chat STFOOM!\n\n"
            self.chat_display.insert(tk.END, welcome_msg, "system_msg")
        else:
            for msg in self.messages[-50:]:  # Show last 50 messages
                self.display_message(
                    msg.get("user", "Unknown"),
                    msg.get("message", ""),
                    msg.get("timestamp", "")
                )
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)  # Scroll to bottom
    
    def display_message(self, user: str, message: str, timestamp: str):
        """Display a single message in the chat."""
        self.chat_display.config(state=tk.NORMAL)
        
        # Format timestamp
        try:
            dt = datetime.fromisoformat(timestamp)
            time_str = dt.strftime("%H:%M:%S")
        except:
            time_str = timestamp
        
        # Insert message
        self.chat_display.insert(tk.END, f"[{time_str}] ", "timestamp")
        self.chat_display.insert(tk.END, f"{user}: ", "user_msg")
        self.chat_display.insert(tk.END, f"{message}\n")
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def send_message(self):
        """Send a new message."""
        message = self.message_entry.get().strip()
        
        if not message:
            return
        
        # Create message object
        new_message = {
            "user": self.current_user,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to messages list
        self.messages.append(new_message)
        
        # Display the message
        self.display_message(
            new_message["user"],
            new_message["message"], 
            new_message["timestamp"]
        )
        
        # Clear the input
        self.message_entry.delete(0, tk.END)
        
        # Save messages
        self.save_messages()
        
        # Update status
        self.status_label.config(text="✅ Message envoyé")
        self.after(3000, lambda: self.status_label.config(text="💡 Appuyez sur Entrée pour envoyer un message"))
    
    def clear_chat(self):
        """Clear all chat messages."""
        if messagebox.askyesno(
            "Confirmation", 
            "Voulez-vous vraiment effacer tous les messages de chat?\nCette action est irréversible."
        ):
            self.messages.clear()
            self.save_messages()
            self.load_chat_display()
            self.status_label.config(text="🗑️ Chat effacé")
            self.after(3000, lambda: self.status_label.config(text="💡 Appuyez sur Entrée pour envoyer un message"))
    
    def get_current_user(self):
        """Get current user from session."""
        try:
            from . import permission_utils
            return permission_utils.current_user if permission_utils.current_user else "Anonymous"
        except Exception as e:
            print(f"[CHAT] Could not get current user: {e}")
            return "Anonymous"