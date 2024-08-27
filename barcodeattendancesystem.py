import tkinter as tk
from tkinter import messagebox, filedialog
import barcode
from barcode.writer import ImageWriter
from pyzbar.pyzbar import decode
import cv2
import sqlite3
import os

# Ensure the barcodes directory exists
os.makedirs('barcodes', exist_ok=True)

# Initialize database
conn = sqlite3.connect('attendance.db')
c = conn.cursor()

# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                matric_number TEXT,
                barcode TEXT UNIQUE)''')

c.execute('''CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (id))''')

conn.commit()

class BarcodeAttendanceSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Barcode Attendance System")

        self.setup_ui()

    def setup_ui(self):
        self.frame = tk.Frame(self.root)
        self.frame.pack(pady=20)

        self.name_label = tk.Label(self.frame, text="Student Name:")
        self.name_label.grid(row=0, column=0, padx=10, pady=5)

        self.name_entry = tk.Entry(self.frame)
        self.name_entry.grid(row=0, column=1, padx=10, pady=5)

        self.matric_label = tk.Label(self.frame, text="Matric Number:")
        self.matric_label.grid(row=1, column=0, padx=10, pady=5)

        self.matric_entry = tk.Entry(self.frame)
        self.matric_entry.grid(row=1, column=1, padx=10, pady=5)

        self.barcode_label = tk.Label(self.frame, text="Barcode (12 digits):")
        self.barcode_label.grid(row=2, column=0, padx=10, pady=5)

        self.barcode_entry = tk.Entry(self.frame)
        self.barcode_entry.grid(row=2, column=1, padx=10, pady=5)

        self.generate_button = tk.Button(self.frame, text="Generate Barcode", command=self.generate_barcode)
        self.generate_button.grid(row=3, column=0, columnspan=2, pady=10)

        self.scan_button = tk.Button(self.frame, text="Scan Barcode", command=self.scan_barcode)
        self.scan_button.grid(row=4, column=0, columnspan=2, pady=10)

        self.attendance_label = tk.Label(self.root, text="Attendance:")
        self.attendance_label.pack(pady=10)

        self.attendance_listbox = tk.Listbox(self.root, width=50, height=10)
        self.attendance_listbox.pack(pady=10)

    def generate_barcode(self):
        student_name = self.name_entry.get()
        matric_number = self.matric_entry.get()
        barcode_data = self.barcode_entry.get()

        if not student_name or not matric_number or not barcode_data:
            messagebox.showerror("Error", "Please enter all the details.")
            return

        if len(barcode_data) != 12 or not barcode_data.isdigit():
            messagebox.showerror("Error", "Barcode must be exactly 12 digits.")
            return

        # Generate the EAN-13 barcode using the first 12 digits
        EAN = barcode.get_barcode_class('ean13')
        ean = EAN(barcode_data, writer=ImageWriter())  # EAN-13 will calculate the check digit
        full_barcode = ean.get_fullcode()
        filename = f'barcodes/{full_barcode}.png'
        ean.save(filename)

        # Insert student into the database with the full 13-digit barcode
        try:
            c.execute("INSERT INTO students (name, matric_number, barcode) VALUES (?, ?, ?)",
                      (student_name, matric_number, full_barcode))
            conn.commit()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Barcode must be unique.")
            return

        messagebox.showinfo("Success", f"Barcode for {student_name} generated and saved as {filename}.")

    def scan_barcode(self):
        file_path = filedialog.askopenfilename(title="Select Barcode Image", filetypes=[("Image Files", "*.png *.jpg *.jpeg")])

        if not file_path:
            return

        image = cv2.imread(file_path)
        decoded_objects = decode(image)

        if decoded_objects:
            barcode_data = decoded_objects[0].data.decode('utf-8')
            print(f"Scanned Barcode Data: {barcode_data}")  # Debug: Print the scanned barcode data

            # Use the entire 13 digits for lookup
            c.execute("SELECT id, name, matric_number FROM students WHERE barcode = ?", (barcode_data,))
            student = c.fetchone()

            if student:
                student_id, student_name, matric_number = student
                c.execute("INSERT INTO attendance (student_id) VALUES (?)", (student_id,))
                conn.commit()

                self.attendance_listbox.insert(tk.END, f"{student_name} ({matric_number}) marked present")
                messagebox.showinfo("Success", f"Attendance marked for {student_name} ({matric_number}).")
            else:
                print(f"No student found for barcode: {barcode_data}")  # Debug: Print if no student is found
                messagebox.showerror("Error", "Student not found.")
        else:
            messagebox.showerror("Error", "No barcode detected.")

if __name__ == "__main__":
    root = tk.Tk()
    app = BarcodeAttendanceSystem(root)
    root.mainloop()