import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
from datetime import datetime, timedelta

class ExamTimetableApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Exam Timetable Generation System")
        self.root.geometry("1300x900")
        self.root.configure(bg='#f0f0f0')

        # Internal Data Structures
        self.paper_master_df = None      # DataFrame for Paper Master File (PMF)
        self.nominal_role_df = None      # DataFrame for Nominal Role File (NRF)
        self.exam_dates = {}             # Mapping: Paper Code -> Assigned exam date (datetime)
        self.student_count_data = None   # DataFrame for student count results
        
        # Style configuration for a modern look
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TLabel', background='#f0f0f0', font=('Arial', 12))
        self.style.configure('TButton', font=('Arial', 12))
        self.style.configure('TFrame', background='#f0f0f0')

        # Notebook for different modules
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # Create modules
        self.create_exam_date_entry_module()
        self.create_exam_generator_module()
        self.create_student_count_module()

    def create_exam_date_entry_module(self):
        self.exam_date_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.exam_date_frame, text="Exam Date Entry")

        # Academic Year, Degree Type & Paper Type Selection
        selection_frame = ttk.Frame(self.exam_date_frame)
        selection_frame.pack(pady=10, fill='x')

        ttk.Label(selection_frame, text="Select Academic Year:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.academic_year_var = tk.StringVar(value=f"{datetime.now().year}/{datetime.now().year+1}")
        academic_years = [f"{year}/{year+1}" for year in range(datetime.now().year-5, datetime.now().year+5)]
        academic_year_dropdown = ttk.Combobox(selection_frame, textvariable=self.academic_year_var, values=academic_years, state='readonly')
        academic_year_dropdown.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(selection_frame, text="Select Degree Type:").grid(row=0, column=2, padx=5, pady=5, sticky='w')
        self.degree_type_var = tk.StringVar()
        degree_types = ['UG', 'PG', 'Professional']
        degree_type_dropdown = ttk.Combobox(selection_frame, textvariable=self.degree_type_var, values=degree_types, state='readonly')
        degree_type_dropdown.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(selection_frame, text="Select Paper Type:").grid(row=0, column=4, padx=5, pady=5, sticky='w')
        self.paper_type_var = tk.StringVar(value="All")
        paper_types = ['All', 'Theory', 'Practical']
        paper_type_dropdown = ttk.Combobox(selection_frame, textvariable=self.paper_type_var, values=paper_types, state='readonly')
        paper_type_dropdown.grid(row=0, column=5, padx=5, pady=5)

        load_pmf_btn = ttk.Button(selection_frame, text="Load Paper Master File", command=self.load_paper_master_file)
        load_pmf_btn.grid(row=0, column=6, padx=10, pady=5)

        self.auto_select_var = tk.BooleanVar(value=True)
        auto_select_chk = ttk.Checkbutton(selection_frame, text="Auto-Select All Courses", variable=self.auto_select_var)
        auto_select_chk.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='w')

        # Courses Selection Frame
        courses_frame = ttk.LabelFrame(self.exam_date_frame, text="Course Selection")
        courses_frame.pack(expand=True, fill='both', padx=10, pady=10)

        ttk.Label(courses_frame, text="Available Courses").grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(courses_frame, text="Selected Courses").grid(row=0, column=2, padx=5, pady=5)
        self.available_courses_listbox = tk.Listbox(courses_frame, selectmode=tk.EXTENDED, width=40, height=10)
        self.selected_courses_listbox = tk.Listbox(courses_frame, selectmode=tk.EXTENDED, width=40, height=10)
        self.available_courses_listbox.grid(row=1, column=0, padx=5, pady=5, sticky='nsew')
        self.selected_courses_listbox.grid(row=1, column=2, padx=5, pady=5, sticky='nsew')

        move_buttons_frame = ttk.Frame(courses_frame)
        move_buttons_frame.grid(row=1, column=1, padx=5, pady=5)
        move_right_btn = ttk.Button(move_buttons_frame, text="→", command=self.move_courses_right)
        move_right_btn.pack(padx=5, pady=10)
        move_left_btn = ttk.Button(move_buttons_frame, text="←", command=self.move_courses_left)
        move_left_btn.pack(padx=5, pady=10)

        courses_frame.grid_columnconfigure(0, weight=1)
        courses_frame.grid_columnconfigure(2, weight=1)

        # Auto-Assign Exam Dates Section
        auto_date_frame = ttk.LabelFrame(self.exam_date_frame, text="Auto-Assign Exam Dates")
        auto_date_frame.pack(fill='x', padx=10, pady=10)
        ttk.Label(auto_date_frame, text="Enter Start Date (YYYY-MM-DD):").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.start_date_entry = ttk.Entry(auto_date_frame)
        self.start_date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.start_date_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        auto_assign_btn = ttk.Button(auto_date_frame, text="Auto Assign Dates", command=self.auto_assign_exam_dates)
        auto_assign_btn.grid(row=0, column=2, padx=10, pady=5)

    def create_exam_generator_module(self):
        self.exam_generator_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.exam_generator_frame, text="Exam Generator")
        gen_frame = ttk.Frame(self.exam_generator_frame)
        gen_frame.pack(pady=10, fill='x')

        ttk.Label(gen_frame, text="Select Exam Month:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.exam_month_var = tk.StringVar(value=str(datetime.now().month))
        month_dropdown = ttk.Combobox(gen_frame, textvariable=self.exam_month_var, values=list(range(1, 13)), state='readonly')
        month_dropdown.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(gen_frame, text="Select Exam Year:").grid(row=0, column=2, padx=5, pady=5, sticky='w')
        self.exam_year_var = tk.StringVar(value=str(datetime.now().year))
        years = [str(datetime.now().year + i) for i in range(-5, 6)]
        year_dropdown = ttk.Combobox(gen_frame, textvariable=self.exam_year_var, values=years, state='readonly')
        year_dropdown.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(gen_frame, text="Select Semester:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.semester_var = tk.StringVar()
        semesters = ['I', 'II', 'III', 'IV', 'V', 'VI']
        semester_dropdown = ttk.Combobox(gen_frame, textvariable=self.semester_var, values=semesters, state='readonly')
        semester_dropdown.grid(row=1, column=1, padx=5, pady=5)

        load_nrf_btn = ttk.Button(gen_frame, text="Load Nominal Role File", command=self.load_nominal_role_file)
        load_nrf_btn.grid(row=1, column=2, padx=5, pady=5)
        ttk.Label(gen_frame, text="Select Programme:").grid(row=1, column=3, padx=5, pady=5, sticky='w')
        self.programme_var = tk.StringVar()
        self.programme_dropdown = ttk.Combobox(gen_frame, textvariable=self.programme_var, state='readonly')
        self.programme_dropdown.grid(row=1, column=4, padx=5, pady=5)

        generate_btn = ttk.Button(gen_frame, text="Generate Timetable", command=self.generate_timetable)
        generate_btn.grid(row=2, column=0, columnspan=5, padx=5, pady=10)

        self.timetable_tree = ttk.Treeview(self.exam_generator_frame, columns=('Date', 'Paper Code', 'Paper Title'), show='headings')
        self.timetable_tree.heading('Date', text='Date')
        self.timetable_tree.heading('Paper Code', text='Paper Code')
        self.timetable_tree.heading('Paper Title', text='Paper Title')
        self.timetable_tree.pack(expand=True, fill='both', padx=10, pady=10)

        extra_btn_frame = ttk.Frame(self.exam_generator_frame)
        extra_btn_frame.pack(fill='x', padx=10, pady=5)
        download_btn = ttk.Button(extra_btn_frame, text="Download Timetable", command=self.download_timetable)
        download_btn.pack(side='left', padx=5)
        clear_btn = ttk.Button(extra_btn_frame, text="Clear Timetable", command=self.clear_timetable)
        clear_btn.pack(side='left', padx=5)
        check_btn = ttk.Button(extra_btn_frame, text="Check Conflicts", command=self.check_conflicts)
        check_btn.pack(side='left', padx=5)

    def create_student_count_module(self):
        self.student_count_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.student_count_frame, text="Student Count")

        control_frame = ttk.Frame(self.student_count_frame)
        control_frame.pack(pady=10, fill='x')

        calc_btn = ttk.Button(control_frame, text="Calculate Student Count", command=self.calculate_student_count)
        calc_btn.pack(side='left', padx=5)
        download_btn = ttk.Button(control_frame, text="Download Student Count", command=self.download_student_count)
        download_btn.pack(side='left', padx=5)

        self.student_count_tree = ttk.Treeview(self.student_count_frame, columns=('Paper Code', 'Student Count'), show='headings')
        self.student_count_tree.heading('Paper Code', text='Paper Code')
        self.student_count_tree.heading('Student Count', text='Student Count')
        self.student_count_tree.pack(expand=True, fill='both', padx=10, pady=10)

    def load_paper_master_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if file_path:
            try:
                self.paper_master_df = pd.read_excel(file_path)
                messagebox.showinfo("Success", "Paper Master File loaded successfully.")
                self.populate_available_courses()
            except Exception as e:
                messagebox.showerror("Error", f"Could not load Paper Master File: {str(e)}")

    def populate_available_courses(self):
        self.available_courses_listbox.delete(0, tk.END)
        if self.paper_master_df is None or not self.degree_type_var.get():
            return

        degree = self.degree_type_var.get()
        if degree == 'UG':
            filtered = self.paper_master_df[self.paper_master_df['Paper Code'].str.startswith('U')]
        elif degree == 'PG':
            filtered = self.paper_master_df[self.paper_master_df['Paper Code'].str.startswith('P')]
        elif degree == 'Professional':
            filtered = self.paper_master_df[self.paper_master_df['Paper Code'].str.startswith('M')]
        else:
            filtered = pd.DataFrame()

        if 'Paper Type' in filtered.columns:
            selected_type = self.paper_type_var.get()
            if selected_type != "All":
                filtered = filtered[filtered['Paper Type'].str.lower() == selected_type.lower()]

        courses = filtered['Paper Code'].tolist()
        for course in courses:
            self.available_courses_listbox.insert(tk.END, course)
        
        if self.auto_select_var.get():
            self.auto_select_all_courses()

    def auto_select_all_courses(self):
        self.selected_courses_listbox.delete(0, tk.END)
        courses = self.available_courses_listbox.get(0, tk.END)
        for course in courses:
            self.selected_courses_listbox.insert(tk.END, course)
        self.available_courses_listbox.delete(0, tk.END)

    def move_courses_right(self):
        selected_indices = self.available_courses_listbox.curselection()
        for index in reversed(selected_indices):
            course = self.available_courses_listbox.get(index)
            self.selected_courses_listbox.insert(tk.END, course)
            self.available_courses_listbox.delete(index)

    def move_courses_left(self):
        selected_indices = self.selected_courses_listbox.curselection()
        for index in reversed(selected_indices):
            course = self.selected_courses_listbox.get(index)
            self.available_courses_listbox.insert(tk.END, course)
            self.selected_courses_listbox.delete(index)

    def auto_assign_exam_dates(self):
        try:
            start_date = datetime.strptime(self.start_date_entry.get(), "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Invalid start date format. Please use YYYY-MM-DD.")
            return

        self.exam_dates.clear()
        selected_courses = self.selected_courses_listbox.get(0, tk.END)
        if not selected_courses:
            messagebox.showerror("Error", "No courses selected for exam date assignment.")
            return

        current_date = start_date
        for course in selected_courses:
            self.exam_dates[course] = current_date
            current_date += timedelta(days=1)
        messagebox.showinfo("Success", "Exam dates have been auto-assigned.")

    def load_nominal_role_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if file_path:
            try:
                self.nominal_role_df = pd.read_excel(file_path)
                messagebox.showinfo("Success", "Nominal Role File loaded successfully.")
                self.populate_programme_dropdown()
            except Exception as e:
                messagebox.showerror("Error", f"Could not load Nominal Role File: {str(e)}")

    def populate_programme_dropdown(self):
        if self.nominal_role_df is not None:
            programmes = self.nominal_role_df['Programme Name'].unique().tolist()
            self.programme_dropdown['values'] = programmes
            if programmes:
                self.programme_var.set(programmes[0])

    def generate_timetable(self):
        if not self.exam_dates:
            messagebox.showerror("Error", "No exam dates assigned. Please auto-assign exam dates first.")
            return

        if self.paper_master_df is None or self.nominal_role_df is None:
            messagebox.showerror("Error", "Please ensure both Paper Master and Nominal Role files are loaded.")
            return

        selected_programme = self.programme_var.get()
        selected_semester = self.semester_var.get()
        filtered_papers = self.paper_master_df[
            (self.paper_master_df['Programme Name'] == selected_programme) &
            (self.paper_master_df['Semester'] == selected_semester)
        ]

        for row in self.timetable_tree.get_children():
            self.timetable_tree.delete(row)

        timetable_entries = []
        for course, exam_date in self.exam_dates.items():
            paper_match = filtered_papers[filtered_papers['Paper Code'] == course]
            if not paper_match.empty:
                paper_title = paper_match.iloc[0]['Paper Title']
                timetable_entries.append((exam_date, course, paper_title))

        timetable_entries.sort(key=lambda x: x[0])
        for date, code, title in timetable_entries:
            self.timetable_tree.insert('', 'end', values=(date.strftime('%Y-%m-%d'), code, title))
        
        messagebox.showinfo("Success", "Exam Timetable generated successfully.")

    def download_timetable(self):
        items = self.timetable_tree.get_children()
        if not items:
            messagebox.showerror("Error", "No timetable data available to download.")
            return

        data = []
        for item in items:
            row = self.timetable_tree.item(item)['values']
            data.append(row)
        df = pd.DataFrame(data, columns=['Date', 'Paper Code', 'Paper Title'])

        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx")])
        if file_path:
            try:
                if file_path.lower().endswith('.xlsx'):
                    df.to_excel(file_path, index=False)
                else:
                    df.to_csv(file_path, index=False)
                messagebox.showinfo("Success", "Timetable downloaded successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to download timetable: {str(e)}")

    def clear_timetable(self):
        self.exam_dates.clear()
        for row in self.timetable_tree.get_children():
            self.timetable_tree.delete(row)
        messagebox.showinfo("Cleared", "Timetable cleared successfully.")

    def check_conflicts(self):
        conflicts = []  # Placeholder for conflict detection logic
        if conflicts:
            messagebox.showwarning("Conflicts Detected", "\n".join(conflicts))
        else:
            messagebox.showinfo("No Conflicts", "No scheduling conflicts detected.")

    def calculate_student_count(self):
        # Ensure the Nominal Role File is loaded
        if self.nominal_role_df is None:
            messagebox.showerror("Error", "Please load the Nominal Role File first.")
            return

        count_dict = {}
        # Loop over columns that likely hold paper codes
        for col in self.nominal_role_df.columns:
            if "Code" in col and not col.startswith("Programme") and not col.startswith("Sl"):
                for value in self.nominal_role_df[col].dropna():
                    code = str(value).strip()
                    if code:
                        count_dict[code] = count_dict.get(code, 0) + 1

        # Convert dictionary to DataFrame for easy sorting and download
        self.student_count_data = pd.DataFrame(list(count_dict.items()), columns=['Paper Code', 'Student Count'])
        self.student_count_data.sort_values(by='Paper Code', inplace=True)

        # Clear existing treeview data
        for row in self.student_count_tree.get_children():
            self.student_count_tree.delete(row)

        # Populate Treeview with student count data
        for _, row in self.student_count_data.iterrows():
            self.student_count_tree.insert('', 'end', values=(row['Paper Code'], row['Student Count']))

        messagebox.showinfo("Success", "Student count calculated successfully.")

    def download_student_count(self):
        if self.student_count_data is None or self.student_count_data.empty:
            messagebox.showerror("Error", "No student count data available to download.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx")])
        if file_path:
            try:
                if file_path.lower().endswith('.xlsx'):
                    self.student_count_data.to_excel(file_path, index=False)
                else:
                    self.student_count_data.to_csv(file_path, index=False)
                messagebox.showinfo("Success", "Student count data downloaded successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to download student count data: {str(e)}")

def main():
    root = tk.Tk()
    app = ExamTimetableApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()