import streamlit as st
st.set_page_config(page_title="Exam Time Table Generator", layout="wide")
from st_on_hover_tabs import on_hover_tabs
import pandas as pd
import re
from datetime import datetime, timedelta
from collections import Counter
import io

# --------------------
# Custom CSS (if available)
# --------------------
try:
    with open("styles.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except Exception:
    st.info("Custom styles.css not found. Using default styling.")

# --------------------
# Page Configuration & Session State Initialization
# --------------------
if 'paper_master_df' not in st.session_state:
    st.session_state.paper_master_df = None
if 'filtered_pmf' not in st.session_state:
    st.session_state.filtered_pmf = None  # Filtered PMF for current selections
if 'nominal_role_df' not in st.session_state:
    st.session_state.nominal_role_df = None
if 'exam_date_list' not in st.session_state:
    st.session_state.exam_date_list = []  # List of tuples: (paper_code, exam_date)
if 'combination_groups' not in st.session_state:
    st.session_state.combination_groups = []  # Groups for combined elective courses
if 'student_count_data' not in st.session_state:
    st.session_state.student_count_data = None
if 'timetable_exam_dates' not in st.session_state:
    st.session_state.timetable_exam_dates = []  # For transfer to timetable module
if 'generated_timetable' not in st.session_state:
    st.session_state.generated_timetable = None
if 'selected_degree' not in st.session_state:
    st.session_state.selected_degree = None
if 'selected_semester' not in st.session_state:
    st.session_state.selected_semester = None
if 'holiday_dates' not in st.session_state:
    st.session_state.holiday_dates = []  # List to store individual holiday dates

# --------------------
# Utility Functions
# --------------------
SEM_MAPPING = {
    '1': "I", '2': "II", '3': "III", '4': "IV",
    '5': "V", '6': "VI", '7': "VII", '8': "VIII"
}

def extract_semester(paper_code):
    """
    Derive the semester from a paper code.
    For BPAM codes, special logic applies.
    Otherwise, the function looks for three-digit patterns or any digit.
    """
    code = str(paper_code).strip()
    if code.upper().startswith("BPAM"):
        match = re.search(r'BPAM-?(\d+)', code.upper())
        if match:
            num_part = match.group(1)
            if len(num_part) >= 2:
                prefix = num_part[:2]
                if prefix == "20":
                    return "II"
                elif prefix == "40":
                    return "IV"
                elif prefix == "60":
                    return "VI"
                elif prefix == "80":
                    return "VIII"
        return "I"
    else:
        matches = re.findall(r'\d{3}', code)
        if matches:
            digits = matches[-1]
            for ch in digits:
                if ch in SEM_MAPPING:
                    return SEM_MAPPING[ch]
        for ch in code:
            if ch in SEM_MAPPING:
                return SEM_MAPPING[ch]
    return None

def schedule_exams(exams, holidays, weekends, start_date, end_date):
    """
    Assigns a unique exam date for each exam in the provided list.
    Dates are chosen from business days between start_date and end_date
    (skipping weekends and holidays). If there aren't enough business days,
    returns None and signals an error.
    """
    business_days = []
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() not in weekends and current_date.date() not in holidays:
            business_days.append(current_date)
        current_date += timedelta(days=1)
    
    # Check for sufficient business days before scheduling
    if len(business_days) < len(exams):
        st.error("Not enough business days available in the given date range to schedule all exams. Please extend the date range.")
        return None  # Prevent scheduling if the condition is not met.
    
    scheduled = {}
    # Assign each exam a unique business day in sequential order
    for i, exam in enumerate(exams):
        scheduled[exam] = business_days[i]
    return scheduled



def get_combined_exam_dates():
    """
    Merge individual exam dates with those set for combination groups.
    """
    combined = {course: date for course, date in st.session_state.exam_date_list}
    for group in st.session_state.combination_groups:
        for course in group["courses"]:
            combined[course] = group["date"]
    return combined

def assign_last_day_exams(nrf_df, combined_dates, last_exam_date):
    """
    For each student, assign a last-day exam based on eligible paper codes.
    """
    last_day_assignments = []
    conflicts = []
    for idx, row in nrf_df.iterrows():
        reg_no = row.get("Regd. No.", f"Student_{idx}")
        eligible_papers = []
        for col in nrf_df.columns:
            if "Code" in col and not col.startswith(("Programme", "Sl")):
                code = str(row[col]).strip()
                if code and code in combined_dates:
                    eligible_papers.append(code)
        if eligible_papers:
            assigned_paper = eligible_papers[0]
            last_day_assignments.append((reg_no, assigned_paper, last_exam_date))
        else:
            conflicts.append(f"Student {reg_no} has no eligible paper for last-day exam.")
    return last_day_assignments, conflicts

def download_csv(dataframe, filename):
    """
    Provide a download button for the CSV version of the provided DataFrame.
    """
    csv = dataframe.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", data=csv, file_name=filename, mime="text/csv")

# --------------------
# Main Header & Navigation
# --------------------
st.title("Exam Time Table Generator")
st.markdown("### Simplify your exam scheduling process with our easy-to-use tool.")

with st.sidebar:
    nav_tab = on_hover_tabs(
        tabName=['Exam Date Entry', 'Time Table Generator', 'Student Count'],
        iconName=['calendar', 'table', 'user'],
        default_choice=0
    )

# --------------------
# Module 1: Exam Date Entry
# --------------------
if nav_tab == "Exam Date Entry":
    st.header("Exam Date Entry Module")
    
    # Academic & File Upload Settings
    col1, col2, col3 = st.columns(3)
    with col1:
        academic_year = st.selectbox(
            "Select Academic Year", 
            [f"{year}/{year+1}" for year in range(datetime.now().year-5, datetime.now().year+5)]
        )
    with col2:
        degree_type = st.selectbox("Select Degree Type", ['UG', 'PG', 'Professional'])
        st.session_state.selected_degree = degree_type
    with col3:
        paper_type = st.selectbox("Select Paper Type", ['All', 'Theory', 'Practical'])
    
    st.markdown("#### Upload Paper Master File (PMF)")
    uploaded_pmf = st.file_uploader("Load PMF", type=["xlsx", "xls"], key="pmf")
    if uploaded_pmf is not None:
        try:
            st.session_state.paper_master_df = pd.read_excel(uploaded_pmf)
            st.success("PMF loaded successfully.")
        except Exception as e:
            st.error(f"Error loading PMF: {e}")
    
    if st.session_state.paper_master_df is not None:
        df = st.session_state.paper_master_df.copy()
        # Filter based on degree type using paper code conventions
        if degree_type == 'UG':
            df = df[(df['Paper Code'].astype(str).str.startswith('U')) |
                    (df['Paper Code'].astype(str).str.upper().str.startswith('BPAM'))]
        elif degree_type == 'PG':
            df = df[df['Paper Code'].astype(str).str.startswith('P')]
        elif degree_type == 'Professional':
            df = df[df['Paper Code'].astype(str).str.startswith('M')]
        # Exclude unwanted courses
        df = df[~df['Paper Code'].astype(str).str.startswith('UAWR')]
        
        # Map to derived semester and filter
        df['Derived Semester'] = df['Paper Code'].apply(extract_semester)
        semesters = sorted(set(df['Derived Semester'].dropna()), key=lambda s: list(SEM_MAPPING.values()).index(s) if s in SEM_MAPPING.values() else 99)
        if semesters:
            selected_semester = st.selectbox("Select Mapped Semester", options=semesters)
            st.session_state.selected_semester = selected_semester
            df = df[df['Derived Semester'] == selected_semester]
        else:
            st.warning("No semester mapping found.")
        
        st.session_state.filtered_pmf = df.copy()
        available_courses = df['Paper Code'].tolist()
        
        auto_select = st.checkbox("Auto-Select All Courses", value=True)
        if auto_select:
            selected_courses = st.multiselect("Selected Courses", options=available_courses, default=available_courses)
        else:
            selected_courses = st.multiselect("Selected Courses", options=available_courses)
        
        st.write("Selected Courses:", selected_courses)
        
        # Combine Elective Courses
        st.markdown("#### Combine Elective Courses")
        st.info("Select elective courses to be conducted on the same day.")
        combine_selection = st.multiselect("Select courses to combine", options=selected_courses, key="combine_selection")
        group_name_input = st.text_input("Enter Group Name (optional)", key="group_name_input")
        group_date = st.date_input("Select Common Exam Date", value=datetime.now().date(), key="group_date")
        if st.button("Add Combination Group", key="add_group"):
            if len(combine_selection) < 2:
                st.error("Select at least two courses to combine.")
            else:
                group_name = group_name_input.strip() if group_name_input.strip() != "" else f"Group {len(st.session_state.combination_groups)+1}"
                new_group = {
                    "group_name": group_name,
                    "courses": combine_selection,
                    "date": datetime.combine(group_date, datetime.min.time())
                }
                st.session_state.combination_groups.append(new_group)
                st.success(f"Combination group '{group_name}' added.")
        
        if st.session_state.combination_groups:
            st.markdown("##### Combined Elective Groups")
            combo_df = pd.DataFrame([{
                "Group Name": grp["group_name"],
                "Courses": ", ".join(grp["courses"]),
                "Date": grp["date"].strftime("%Y-%m-%d")
            } for grp in st.session_state.combination_groups])
            st.table(combo_df)
            group_to_remove = st.selectbox("Select a group to remove", options=[grp["group_name"] for grp in st.session_state.combination_groups], key="remove_group")
            if st.button("Remove Group", key="remove_group_btn"):
                st.session_state.combination_groups = [grp for grp in st.session_state.combination_groups if grp["group_name"] != group_to_remove]
                st.success(f"Group '{group_to_remove}' removed.")
        
        # --------------------
        # Single Holiday Date Input and Editing Option
        # --------------------
        holiday_date = st.date_input("Enter Holiday Date", value=datetime.now().date(), key="holiday_date")
        
        if st.button("Add Holiday", key="add_holiday"):
            if holiday_date not in st.session_state.holiday_dates:
                st.session_state.holiday_dates.append(holiday_date)
                st.success(f"Holiday {holiday_date} added.")
            else:
                st.warning("This holiday date is already added.")
        
        if st.session_state.holiday_dates:
            st.markdown("### Current Holiday Dates")
            holiday_df = pd.DataFrame(st.session_state.holiday_dates, columns=["Holiday Date"])
            edited_holidays = st.data_editor(holiday_df, key="edit_holidays", num_rows="dynamic")
            if st.button("Save Edited Holidays", key="save_holidays"):
                new_holidays = pd.to_datetime(edited_holidays["Holiday Date"]).dt.date.tolist()
                st.session_state.holiday_dates = new_holidays
                st.success("Holiday dates updated.")
        
        # Use the session state's holiday dates for scheduling
        holidays = st.session_state.holiday_dates
        weekends = {6}  # For example, Sunday (weekday 6)
        
        # --------------------
        # Schedule Exam Dates for Individual Courses
        # --------------------
        # Determine courses that are not in a combined group
        grouped_courses = set()
        for grp in st.session_state.combination_groups:
            grouped_courses.update(grp["courses"])
        remaining_courses = [course for course in selected_courses if course not in grouped_courses]
        
        if remaining_courses:
            st.info("Scheduling dates for individual courses.")
            sched_start = st.date_input("Scheduling Start Date", value=datetime.now().date(), key="sched_start")
            sched_end = st.date_input("Scheduling End Date", value=(datetime.now() + timedelta(days=15)).date(), key="sched_end")
            if st.button("Schedule Exams", key="schedule_exams"):
                if sched_end < sched_start:
                    st.error("End date cannot be before start date.")
                else:
                    scheduled = schedule_exams(
                        remaining_courses,
                        holidays,  # use holiday dates from session state
                        weekends,
                        datetime.combine(sched_start, datetime.min.time()),
                        datetime.combine(sched_end, datetime.min.time())
                    )
                    if scheduled is not None:
                        st.session_state.exam_date_list.extend([(course, date) for course, date in scheduled.items()])
                        st.success("Exam dates scheduled for individual courses.")
        else:
            st.info("All selected courses are in combined groups; no individual scheduling needed.")
        
        if st.button("Send Dates to Time Table Generator", key="send_dates"):
            if st.session_state.exam_date_list:
                st.session_state.timetable_exam_dates = st.session_state.exam_date_list.copy()
                st.success("Exam dates sent to Time Table Generator.")
            else:
                st.error("No exam dates available. Please schedule exams first.")
        
        # Review & Edit Assigned Dates
        if st.button("Review & Edit Assigned Dates", key="review_dates"):
            assigned_data = []
            for course, date in st.session_state.exam_date_list:
                assigned_data.append({"Paper Code": course, "Exam Date": date.strftime("%Y-%m-%d")})
            for grp in st.session_state.combination_groups:
                assigned_data.append({"Paper Code": f"Group: {grp['group_name']}", "Exam Date": grp["date"].strftime("%Y-%m-%d")})
            st.table(pd.DataFrame(assigned_data))
            if st.button("Edit Dates", key="edit_dates"):
                edited_df = st.data_editor(pd.DataFrame(assigned_data), key="edit_dates_editor")
                if st.button("Save Edited Dates", key="save_edit_dates"):
                    updated = [(row["Paper Code"], datetime.strptime(row["Exam Date"], "%Y-%m-%d")) for _, row in edited_df.iterrows()]
                    st.session_state.exam_date_list = updated
                    st.session_state.timetable_exam_dates = updated
                    st.success("Exam dates updated.")

# --------------------
# Module 2: Time Table Generator
# --------------------
elif nav_tab == "Time Table Generator":
    st.header("Time Table Generator Module")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Upload Nominal Role File (NRF)")
        uploaded_nrf = st.file_uploader("Load NRF", type=["xlsx", "xls"], key="nrf")
        if uploaded_nrf is not None:
            try:
                st.session_state.nominal_role_df = pd.read_excel(uploaded_nrf)
                st.success("NRF loaded successfully.")
            except Exception as e:
                st.error(f"Error loading NRF: {e}")
    with col2:
        available_programmes = []
        if st.session_state.filtered_pmf is not None:
            available_programmes = st.session_state.filtered_pmf['Programme Name'].dropna().unique().tolist()
        if available_programmes:
            programme = st.selectbox("Select Programme", available_programmes)
        else:
            programme = None
    
    if st.button("Generate Timetable", key="generate_timetable"):
        exam_dates = st.session_state.get("timetable_exam_dates", [])
        if not exam_dates:
            st.error("No exam dates assigned. Please schedule and send exam dates first.")
        elif st.session_state.filtered_pmf is None or st.session_state.nominal_role_df is None:
            st.error("Ensure both PMF (filtered) and NRF files are loaded.")
        else:
            df_papers = st.session_state.filtered_pmf.copy()
            df_papers['Programme Name'] = df_papers['Programme Name'].astype(str).str.strip()
            programme_clean = programme.strip() if programme else ""
            if programme_clean:
                df_papers = df_papers[df_papers['Programme Name'].str.contains(programme_clean, case=False, na=False)]
            if st.session_state.selected_degree:
                if st.session_state.selected_degree == 'UG':
                    df_papers = df_papers[(df_papers['Paper Code'].astype(str).str.startswith('U')) | 
                                          (df_papers['Paper Code'].astype(str).str.upper().str.startswith('BPAM'))]
                elif st.session_state.selected_degree == 'PG':
                    df_papers = df_papers[df_papers['Paper Code'].astype(str).str.startswith('P')]
                elif st.session_state.selected_degree == 'Professional':
                    df_papers = df_papers[df_papers['Paper Code'].astype(str).str.startswith('M')]
            df_papers['Derived Semester'] = df_papers['Paper Code'].apply(extract_semester)
            if st.session_state.selected_semester:
                df_papers = df_papers[df_papers['Derived Semester'] == st.session_state.selected_semester]
            if df_papers.empty:
                st.error("No matching courses found with the selected filters.")
            else:
                st.write("Filtered PMF Data:", df_papers[['Paper Code', 'Paper Title', 'Programme Name', 'Derived Semester']])
            
            combined_dates = get_combined_exam_dates()
            df_nrf = st.session_state.nominal_role_df
            # Validate core subjects have unique dates for the selected programme
            if not df_nrf.empty:
                programme_mask = df_nrf['Programme Name'].str.contains(programme_clean, case=False, na=False)
                if not df_nrf[programme_mask].empty:
                    programme_row = df_nrf[programme_mask].iloc[0]
                    core_columns = [f"Core-{i} Code" for i in range(1, 11)]
                    core_subjects = [str(programme_row[col]).strip() for col in core_columns if pd.notna(programme_row[col])]
                    core_dates = [combined_dates[code].strftime('%Y-%m-%d') for code in core_subjects if code in combined_dates]
                    duplicate_dates = [date for date, count in Counter(core_dates).items() if count > 1]
                    if duplicate_dates:
                        st.error(f"Duplicate exam dates for core subjects: {', '.join(duplicate_dates)}")
                        st.stop()
            
            last_exam_date = max([date for _, date in exam_dates]) if exam_dates else None
            if not last_exam_date:
                st.error("Unable to determine last exam date.")
                st.stop()
            last_day_assignments, conflicts = assign_last_day_exams(df_nrf, combined_dates, last_exam_date)
            if conflicts:
                st.error("Conflicts in last-day exam assignment:")
                for conflict in conflicts:
                    st.write(conflict)
                st.stop()
            for reg_no, paper_code, date in last_day_assignments:
                exam_dates.append((paper_code, date))
            
            timetable_entries = []
            for course, exam_date in exam_dates:
                paper_match = df_papers[df_papers['Paper Code'].astype(str).str.strip() == course.strip()]
                if not paper_match.empty:
                    paper_title = paper_match.iloc[0]['Paper Title']
                    timetable_entries.append((exam_date, course, paper_title))
            for grp in st.session_state.combination_groups:
                for course in grp["courses"]:
                    paper_match = df_papers[df_papers['Paper Code'].astype(str).str.strip() == course.strip()]
                    if not paper_match.empty:
                        paper_title = paper_match.iloc[0]['Paper Title']
                        timetable_entries.append((grp["date"], course, paper_title))
            timetable_entries.sort(key=lambda x: x[0])
            if timetable_entries:
                df_timetable = pd.DataFrame(timetable_entries, columns=['Date', 'Paper Code', 'Paper Title'])
                df_timetable['Date'] = df_timetable['Date'].dt.strftime('%Y-%m-%d')
                st.success("Exam Timetable generated successfully.")
                st.dataframe(df_timetable)
                download_csv(df_timetable, "exam_timetable.csv")
                st.session_state.generated_timetable = df_timetable
            else:
                st.warning("No timetable entries found.")
        
        # Option to edit exam dates in the generated timetable
        if st.session_state.generated_timetable is not None:
            st.markdown("#### Edit Exam Dates")
            editable_timetable = st.session_state.generated_timetable.copy()
            editable_timetable['Date'] = pd.to_datetime(editable_timetable['Date'])
            edited_timetable = st.data_editor(editable_timetable, key="edit_timetable", num_rows="dynamic", use_container_width=True)
            if st.button("Save Edited Dates", key="save_edit_timetable"):
                updated = [(row['Paper Code'], row['Date']) for _, row in edited_timetable.iterrows()]
                st.session_state.exam_date_list = updated
                st.session_state.timetable_exam_dates = updated
                st.success("Edited exam dates saved.")
        
        if st.button("Check Conflicts", key="check_conflicts"):
            conflicts = []
            combined_dates = get_combined_exam_dates()
            if not combined_dates:
                st.info("No exam dates available to check.")
            else:
                for idx, row in st.session_state.nominal_role_df.iterrows():
                    student_exams = []
                    for col in st.session_state.nominal_role_df.columns:
                        if "Code" in col and not col.startswith(("Programme", "Sl")):
                            code = str(row[col]).strip()
                            if code and code in combined_dates:
                                student_exams.append(combined_dates[code].strftime('%Y-%m-%d'))
                    duplicates = [item for item, count in Counter(student_exams).items() if count > 1]
                    if duplicates:
                        conflicts.append(f"Student {row.get('Regd. No.', idx)} has multiple exams on: " + ", ".join(duplicates))
                if conflicts:
                    st.error("Conflicts detected:")
                    for c in conflicts:
                        st.write(c)
                else:
                    st.success("No scheduling conflicts found.")
    
    col_gen1, col_gen2 = st.columns(2)
    with col_gen1:
        if st.button("Clear Timetable", key="clear_timetable"):
            st.session_state.exam_date_list = []
            st.info("Timetable cleared.")

# --------------------
# Module 3: Student Count
# --------------------
elif nav_tab == "Student Count":
    st.header("Student Count Module")
    if st.button("Calculate Student Count", key="calc_student_count"):
        if st.session_state.nominal_role_df is None:
            st.error("Please load the Nominal Role File first.")
        else:
            count_dict = {}
            df_nrf = st.session_state.nominal_role_df
            for col in df_nrf.columns:
                if "Code" in col and not col.startswith(("Programme", "Sl")):
                    for val in df_nrf[col].dropna():
                        code = str(val).strip()
                        if code:
                            count_dict[code] = count_dict.get(code, 0) + 1
            student_count_df = pd.DataFrame(list(count_dict.items()), columns=['Paper Code', 'Student Count'])
            student_count_df.sort_values(by='Paper Code', inplace=True)
            st.session_state.student_count_data = student_count_df
            st.success("Student count calculated successfully.")
            st.dataframe(student_count_df)
            download_csv(student_count_df, "student_count.csv")
