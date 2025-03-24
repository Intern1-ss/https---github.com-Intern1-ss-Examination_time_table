import streamlit as st
st.set_page_config(page_title="TimeTable PRO", layout="wide")
from st_on_hover_tabs import on_hover_tabs
import pandas as pd
import re
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import random
import io
from copy import deepcopy

# --------------------
# Custom CSS (if available)
# --------------------
try:
    with open("styles.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except Exception:
    st.info("Custom styles.css not found. Using default styling.")

# --------------------
# Session State Initialization
# --------------------
if 'paper_master_df' not in st.session_state:
    st.session_state.paper_master_df = None
if 'filtered_pmf' not in st.session_state:
    st.session_state.filtered_pmf = None
if 'nominal_role_df' not in st.session_state:
    st.session_state.nominal_role_df = None
if 'exam_date_list' not in st.session_state:
    st.session_state.exam_date_list = []  # list of tuples: (paper_code, date_obj, time_slot)
if 'combination_groups' not in st.session_state:
    st.session_state.combination_groups = []  # elective groups
if 'student_count_data' not in st.session_state:
    st.session_state.student_count_data = None
if 'timetable_exam_dates' not in st.session_state:
    st.session_state.timetable_exam_dates = []
if 'generated_timetable' not in st.session_state:
    st.session_state.generated_timetable = None
if 'selected_degree' not in st.session_state:
    st.session_state.selected_degree = None
if 'selected_semester' not in st.session_state:
    st.session_state.selected_semester = None
if 'holiday_dates' not in st.session_state:
    st.session_state.holiday_dates = []

# --------------------
# Utility Functions
# --------------------
SEM_MAPPING = {
    '1': "I", '2': "II", '3': "III", '4': "IV",
    '5': "V", '6': "VI", '7': "VII", '8': "VIII"
}

def extract_semester(paper_code):
    """Derive semester from paper code."""
    code = str(paper_code).strip().upper()
    
    if code.startswith("BPAM"):
        match = re.search(r'BPAM-?(\d+)', code)
        if match:
            num_part = match.group(1)
            # Check first THREE digits (e.g., 203 → "203")
            if len(num_part) >= 3:
                prefix = num_part[:3]
                if prefix.startswith("20"):
                    return "II"
                elif prefix.startswith("40"):
                    return "IV"
                elif prefix.startswith("60"):
                    return "VI"
                elif prefix.startswith("80"):
                    return "VIII"
            # Check first TWO digits (e.g., 20 → "20")
            elif len(num_part) >= 2:
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
    
    # Non-BPAM code handling
    else:
        numeric_parts = re.findall(r'\d+', code)
        for part in numeric_parts:
            if '30' in part:  # Check for '30' first
                return "IV"
            elif '20' in part:  # Then check for '20'
                return "II"
        
        # Fallback to original logic
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

def download_csv(df, filename):
    """Download button for CSV."""
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", data=csv, file_name=filename, mime="text/csv")

def flatten_schedule_to_list(schedule_dict):
    """Convert schedule dict to list of (course, date_obj, time_slot)."""
    results = []
    for date_str, slot_dict in schedule_dict.items():
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        for slot, courses in slot_dict.items():
            for c in courses:
                results.append((c, date_obj, slot))
    results.sort(key=lambda x: (x[1], x[2]))
    return results

def auto_schedule_exams_by_program_gap(courses, pmf_df, start_date, end_date, holidays, weekends, semester):
    fixed_slot = "09:00 - 10:30"
    valid_days = []
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() not in weekends and current_date.date() not in holidays:
            valid_days.append(current_date)
        current_date += timedelta(days=1)
    if not valid_days:
        return None
    # Semester-specific constraints
    if semester == "II":
        min_papers, max_papers = 4, 7
    elif semester == "IV":
        min_papers, max_papers = 5, 20
    else:
        min_papers, max_papers = 3, 8
    schedule = defaultdict(lambda: defaultdict(list))
    last_scheduled_date = None
    while courses:
        if last_scheduled_date is None:
            min_date = start_date
        else:
            min_date = last_scheduled_date + timedelta(days=3)
        max_date = end_date  # Allow any day up to end_date
        possible_days = [day for day in valid_days if min_date <= day <= max_date]
        if not possible_days:
            return None  # Not enough valid days
        chosen_day = random.choice(possible_days)
        num_papers_today = random.randint(min_papers, max_papers)
        papers_to_schedule = courses[:num_papers_today]
        schedule[chosen_day.strftime("%Y-%m-%d")][fixed_slot] = papers_to_schedule
        courses = courses[num_papers_today:]
        last_scheduled_date = chosen_day
    return schedule

def auto_schedule_exams_by_program_gap(courses, pmf_df, start_date, end_date, holidays, weekends, semester):
    fixed_slot = "09:00 - 10:30"
    valid_days = []
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() not in weekends and current_date.date() not in holidays:
            valid_days.append(current_date)
        current_date += timedelta(days=1)
    if not valid_days:
        return None
    # Semester-specific constraints
    if semester == "II":
        min_papers, max_papers = 4, 7
    elif semester == "IV":
        min_papers, max_papers = 5, 20
    else:
        min_papers, max_papers = 3, 8
    schedule = defaultdict(lambda: defaultdict(list))
    last_scheduled_date = None
    while courses:
        if last_scheduled_date is None:
            min_date = start_date
        else:
            min_date = last_scheduled_date + timedelta(days=2)
        max_date = end_date
        possible_days = [day for day in valid_days if min_date <= day <= max_date]
        # Handle edge case where no days are left but courses remain
        if not possible_days:
            if valid_days:
                chosen_day = valid_days[-1]  # Force place on last valid day
                possible_days = [chosen_day]
            else:
                return None
        chosen_day = min(possible_days)  # Select earliest possible day
        num_papers_today = random.randint(min_papers, max_papers)
        # Ensure we don't schedule more papers than remaining
        num_papers_today = min(num_papers_today, len(courses))
        papers_to_schedule = courses[:num_papers_today]
        schedule[chosen_day.strftime("%Y-%m-%d")][fixed_slot] = papers_to_schedule
        courses = courses[num_papers_today:]
        last_scheduled_date = chosen_day
    return schedule

def auto_schedule_exams_by_program_dense(courses, start_date, end_date, holidays, weekends):
    fixed_slot = "09:00 - 10:30"
    valid_days = []
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() not in weekends and current_date.date() not in holidays:
            valid_days.append(current_date)
        current_date += timedelta(days=1)
    if not valid_days:
        return None
    schedule = defaultdict(lambda: defaultdict(list))
    last_scheduled_date = None
    while courses:
        if last_scheduled_date is None:
            min_date = start_date
        else:
            min_date = last_scheduled_date + timedelta(days=2)
        max_date = end_date
        possible_days = [day for day in valid_days if min_date <= day <= max_date]
        if not possible_days:
            return None
        chosen_day = min(possible_days)
        num_papers_today = min(5, len(courses))
        papers_to_schedule = courses[:num_papers_today]
        schedule[chosen_day.strftime("%Y-%m-%d")][fixed_slot] = papers_to_schedule
        courses = courses[num_papers_today:]
        last_scheduled_date = chosen_day
    return schedule

def auto_schedule_exams_multi_slot(courses, start_date, end_date, holidays, weekends):
    """
    For 6th semester ("VI"), use a multi-slot round-robin scheduling approach.
    """
    time_slots = ["09:00 - 10:30"]  # (Can be expanded to include more slots if needed)
    valid_days = []
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() not in weekends and current_date.date() not in holidays:
            valid_days.append(current_date)
        current_date += timedelta(days=1)
    if not valid_days:
        return None

    schedule = defaultdict(lambda: defaultdict(list))
    course_index = 0
    total_slots = len(valid_days) * len(time_slots)
    if len(courses) > total_slots:
        return None

    for day in valid_days:
        date_str = day.strftime("%Y-%m-%d")
        for slot in time_slots:
            if course_index < len(courses):
                schedule[date_str][slot].append(courses[course_index])
                course_index += 1
            else:
                break
        if course_index >= len(courses):
            break

    return schedule

def check_full_schedule_conflict(nominal_df, exam_list):
    """
    Check if any student has multiple exams in the same slot on the same day.
    Returns a list of conflict messages.
    """
    conflicts = []
    if nominal_df is None or nominal_df.empty:
        conflicts.append("Nominal role file not loaded or empty.")
        return conflicts

    # Build a map: date -> slot -> courses
    schedule_map = defaultdict(lambda: defaultdict(list))
    for (course, dt_obj, slot) in exam_list:
        date_str = dt_obj.strftime("%Y-%m-%d")
        schedule_map[date_str][slot].append(course)

    # Build a map: student -> list of courses opted for
    student_papers = defaultdict(list)
    code_columns = [col for col in nominal_df.columns if "Code" in col and not col.startswith(("Programme", "Sl"))]
    reg_no_col = "Regd. No." if "Regd. No." in nominal_df.columns else None

    if not reg_no_col:
        conflicts.append("Cannot find student registration number column in nominal role file.")
        return conflicts

    for idx, row in nominal_df.iterrows():
        reg_no = row.get(reg_no_col, f"Student_{idx}")
        for col in code_columns:
            if pd.notna(row[col]):
                paper_code = str(row[col]).strip()
                student_papers[reg_no].append(paper_code)

    # Check for conflicts per day and slot
    for date_str, slot_dict in schedule_map.items():
        for slot, courses in slot_dict.items():
            if len(courses) <= 1:
                continue
            for reg_no, papers in student_papers.items():
                opted_courses = [course for course in courses if course in papers]
                if len(opted_courses) > 1:
                    conflicts.append(f"Student {reg_no} has {len(opted_courses)} exams on {date_str} in slot '{slot}': {', '.join(opted_courses)}")
    return conflicts

def assign_combination_groups_to_schedule(schedule, groups):
    """Force combination groups into the schedule on specified dates using a fixed slot."""
    fixed_slot = "09:00 - 10:30"
    for group in groups:
        date_str = group["date"].strftime("%Y-%m-%d")
        if date_str not in schedule:
            schedule[date_str] = {fixed_slot: []}
        for c in group["courses"]:
            schedule[date_str][fixed_slot].append(c)
    return schedule

def download_exam_list_as_csv(exam_list):
    """Download exam list as CSV."""
    df = pd.DataFrame([
        {"Paper Code": c, "Exam Date": d.strftime("%Y-%m-%d"), "Time Slot": slot}
        for (c, d, slot) in exam_list
    ])
    download_csv(df, "scheduled_exams.csv")

# --------------------
# Main Header & Navigation
# --------------------
st.title("TimeTable PRO")
st.markdown("### Organize. Optimize. Succeed.")

with st.sidebar:
    nav_tab = on_hover_tabs(
        tabName=['Exam Date Entry', 'Time Table Generator', 'Student Count'],
        iconName=['calendar', 'table', 'user'],
        default_choice=0
    )
# -------------------- 
# Conflict Resolution Functions
# --------------------
def resolve_conflicts(exam_list, nominal_df, holidays, weekends):
    """
    Attempt to resolve conflicts using:
    1. Slot shifting (if multiple slots exist)
    2. Date adjustment (next available business day)
    3. Student-aware rescheduling
    Returns: (resolved_exam_list, resolution_log)
    """
    conflicts = check_full_schedule_conflict(nominal_df, exam_list)
    resolution_log = []
    available_slots = ["09:00 - 10:30", "11:00 - 12:30", "14:00 - 15:30"]
    valid_days = []
    current_date = min(dt for _, dt, _ in exam_list)
    end_date = max(dt for _, dt, _ in exam_list) + timedelta(days=7)
    
    # Precompute valid business days
    while current_date <= end_date:
        if current_date.weekday() not in weekends and current_date.date() not in holidays:
            valid_days.append(current_date)
        current_date += timedelta(days=1)

    # Build schedule map for easy lookup
    schedule_map = defaultdict(lambda: defaultdict(list))
    for course, dt, slot in exam_list:
        schedule_map[dt.date()][slot].append(course)
        
    # Build student enrollment map
    student_courses = defaultdict(list)
    for idx, row in nominal_df.iterrows():
        reg_no = row.get("Regd. No.", f"Student_{idx}")
        for col in nominal_df.columns:
            if "Code" in col and not col.startswith(("Programme", "Sl")):
                code = str(row[col]).strip()
                if code:
                    student_courses[reg_no].append(code)
    
    # Process each conflict
    for conflict in conflicts:
        try:
            # Parse conflict details
            parts = conflict.split("has")[1].split("on")
            num_exams = int(parts[0].strip().split()[0])
            date_str = parts[1].split("in")[0].strip()
            slot = parts[1].split("'")[1]
            reg_no = conflict.split()[1]
            conflicting_courses = conflict.split(":")[-1].strip().split(", ")
            
            # Find best candidate to move
            move_candidate = None
            min_students = float('inf')
            for course in conflicting_courses:
                # Count students only in this course
                count = sum(1 for s_courses in student_courses.values() if course in s_courses)
                if count < min_students:
                    min_students = count
                    move_candidate = course
            
            # Try slot shifting first
            current_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            current_slots = list(schedule_map[current_date].keys())
            available_slots_sorted = sorted(available_slots, 
                                          key=lambda x: abs(available_slots.index(slot) - available_slots.index(x)))
            
            for new_slot in available_slots_sorted:
                if new_slot != slot and len(schedule_map[current_date][new_slot]) < 5:
                    # Check if moving causes new conflicts
                    temp_schedule = deepcopy(schedule_map)
                    temp_schedule[current_date][slot].remove(move_candidate)
                    temp_schedule[current_date][new_slot].append(move_candidate)
                    
                    # Verify no new conflicts for this student
                    conflict_found = False
                    for s_courses in student_courses.values():
                        if move_candidate in s_courses:
                            other_courses = [c for c in s_courses if c != move_candidate]
                            for dt, slots in temp_schedule.items():
                                for sl, courses in slots.items():
                                    if any(c in other_courses for c in courses) and (dt == current_date and sl == new_slot):
                                        conflict_found = True
                                        break
                                if conflict_found:
                                    break
                    if not conflict_found:
                        # Update actual schedule
                        schedule_map[current_date][slot].remove(move_candidate)
                        schedule_map[current_date][new_slot].append(move_candidate)
                        resolution_log.append(f"MOVED: {move_candidate} from {slot} to {new_slot} on {date_str}")
                        break
                    else:
                        resolution_log.append(f"FAILED_SLOT_SHIFT: {move_candidate} on {date_str}")
            
            # If slot shifting failed, try date adjustment
            if move_candidate in schedule_map[current_date][slot]:
                # Find next available date
                original_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                for delta in range(1, 8):
                    new_date_candidate = original_date + timedelta(days=delta)
                    if new_date_candidate.weekday() not in weekends and new_date_candidate not in holidays:
                        # Check if any slot is available
                        for new_slot in available_slots:
                            if len(schedule_map[new_date_candidate][new_slot]) < 5:
                                # Check for student conflicts on new date
                                conflict_found = False
                                for s_courses in student_courses.values():
                                    if move_candidate in s_courses:
                                        other_courses = [c for c in s_courses if c != move_candidate]
                                        for dt, slots in schedule_map.items():
                                            if dt == new_date_candidate:
                                                for sl, courses in slots.items():
                                                    if any(c in other_courses for c in courses):
                                                        conflict_found = True
                                                        break
                                            if conflict_found:
                                                break
                                        if conflict_found:
                                            break
                                if not conflict_found:
                                    # Update schedule
                                    schedule_map[original_date][slot].remove(move_candidate)
                                    schedule_map[new_date_candidate][new_slot].append(move_candidate)
                                    resolution_log.append(f"MOVED: {move_candidate} from {date_str} to {new_date_candidate} {new_slot}")
                                    break
                        if move_candidate not in schedule_map[original_date][slot]:
                            break
        except Exception as e:
            resolution_log.append(f"ERROR resolving conflict: {conflict}. {str(e)}")
    
    # Convert schedule_map back to exam_list
    resolved_exam_list = []
    for date, slots in schedule_map.items():
        for slot, courses in slots.items():
            for course in courses:
                resolved_exam_list.append((course, datetime.combine(date, datetime.min.time()), slot))
    
    return resolved_exam_list, resolution_log

# --------------------
# Module 1: Exam Date Entry
# --------------------
if nav_tab == "Exam Date Entry":
    st.header("Exam Date Entry Module")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        academic_year = st.selectbox("Select Academic Year", [f"{year}/{year+1}" for year in range(datetime.now().year-5, datetime.now().year+5)])
    with col2:
        degree_type = st.selectbox("Select Degree Type", ['UG', 'PG', 'Professional'])
        st.session_state.selected_degree = degree_type
    with col3:
        paper_type = st.selectbox("Select Paper Type", ['All', 'Theory', 'Practical'])
    
    st.markdown("#### Upload Paper Master File (PMF)")
    uploaded_pmf = st.file_uploader("Load PMF", type=["xlsx", "xls"], key="pmf")
    
    if uploaded_pmf is not None:
        try:
            pmf_df = pd.read_excel(uploaded_pmf)
            if 'CC' not in pmf_df.columns:
                st.error("PMF must contain a 'CC' column to classify IDM/DSC courses.")
            else:
                pmf_df['Is IDM'] = pmf_df['CC'].str.contains('IDM', case=False, na=False)
                pmf_df['Is DSC'] = pmf_df['CC'].str.contains('DSC', case=False, na=False)
                st.session_state.paper_master_df = pmf_df
                st.success("PMF loaded successfully.")
        except Exception as e:
            st.error(f"Error loading PMF: {e}")
    
    if st.session_state.paper_master_df is not None:
        df = st.session_state.paper_master_df.copy()
        # Filter by degree type
        if degree_type == 'UG':
            df = df[(df['Paper Code'].astype(str).str.startswith('U')) |
                    (df['Paper Code'].astype(str).str.upper().str.startswith('BPAM'))]
        elif degree_type == 'PG':
            df = df[df['Paper Code'].astype(str).str.startswith('P')]
        elif degree_type == 'Professional':
            df = df[df['Paper Code'].astype(str).str.startswith('M')]
        
        df = df[~df['Paper Code'].astype(str).str.startswith('UAWR')]
        df['Derived Semester'] = df['Paper Code'].apply(extract_semester)
        
        semesters = sorted(
            set(df['Derived Semester'].dropna()),
            key=lambda s: list(SEM_MAPPING.values()).index(s) if s in SEM_MAPPING.values() else 99
        )
        
        if semesters:
            selected_semester = st.selectbox("Select Mapped Semester", options=semesters)
            st.session_state.selected_semester = selected_semester
            df = df[df['Derived Semester'] == selected_semester]
        else:
            st.warning("No semester mapping found.")
        
        st.session_state.filtered_pmf = df.copy()
        available_courses = df['Paper Code'].unique().tolist()
        
        auto_select = st.checkbox("Auto-Select All Courses", value=True)
        if auto_select:
            selected_courses = st.multiselect("Selected Courses", options=available_courses, default=available_courses)
        else:
            selected_courses = st.multiselect("Selected Courses", options=available_courses)
        
        st.write("Selected Courses:", selected_courses)
        
        # Elective combination groups
        st.markdown("#### Combine Elective Courses")
        st.info("Select elective courses to be conducted on the same day (same slot).")
        combine_selection = st.multiselect("Select courses to combine", options=selected_courses, key="combine_selection")
        group_name_input = st.text_input("Enter Group Name (optional)", key="group_name_input")
        group_date = st.date_input("Select Common Exam Date", value=datetime.now().date(), key="group_date")
        
        if st.button("Add Combination Group", key="add_group"):
            if len(combine_selection) < 2:
                st.error("Select at least two courses to combine.")
            else:
                group_name = group_name_input.strip() if group_name_input.strip() != "" else f"Group {len(st.session_state.combination_groups)+1}"
                new_group = {"group_name": group_name, "courses": combine_selection, "date": datetime.combine(group_date, datetime.min.time())}
                st.session_state.combination_groups.append(new_group)
                st.success(f"Combination group '{group_name}' added.")
        
        if st.session_state.combination_groups:
            st.markdown("##### Combined Elective Groups")
            combo_df = pd.DataFrame([{"Group Name": grp["group_name"],
                                       "Courses": ", ".join(grp["courses"]),
                                       "Date": grp["date"].strftime("%Y-%m-%d")}
                                      for grp in st.session_state.combination_groups])
            st.table(combo_df)
            group_to_remove = st.selectbox("Select a group to remove", options=[grp["group_name"] for grp in st.session_state.combination_groups], key="remove_group")
            if st.button("Remove Group", key="remove_group_btn"):
                st.session_state.combination_groups = [grp for grp in st.session_state.combination_groups if grp["group_name"] != group_to_remove]
                st.success(f"Group '{group_to_remove}' removed.")
        
        # Holiday management
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
        
        # Prepare scheduling parameters
        holidays = st.session_state.holiday_dates
        weekends = {6}  # Sundays
        
        grouped_courses = set()
        for grp in st.session_state.combination_groups:
            grouped_courses.update(grp["courses"])
        remaining_courses = [course for course in selected_courses if course not in grouped_courses]
        
        st.markdown("#### Automatic Scheduling of Individual Courses")
        sched_start = st.date_input("Scheduling Start Date", value=datetime.now().date(), key="sched_start")
        sched_end = st.date_input("Scheduling End Date", value=(datetime.now() + timedelta(days=15)).date(), key="sched_end")
        
        # Scheduling options: Gap vs Dense scheduling (for non-VI semesters)
        gap_scheduling = st.checkbox("Use Gap Scheduling (2-3 day gaps, randomized paper count)", value=True)
        dense_scheduling = st.checkbox("Use Dense Scheduling (pack exams closely)", value=False)
        if gap_scheduling and dense_scheduling:
            st.warning("Both Gap and Dense Scheduling selected. Gap Scheduling will be applied.")
        
        if st.button("Schedule Exams", key="schedule_btn"):
            if st.session_state.selected_semester == "VI":
                schedule = auto_schedule_exams_multi_slot(
                    remaining_courses,
                    datetime.combine(sched_start, datetime.min.time()),
                    datetime.combine(sched_end, datetime.min.time()),
                    holidays,
                    weekends
                )
            else:
                # For non-VI semesters, choose scheduling method based on checkbox selection.
                if gap_scheduling:
                    schedule = auto_schedule_exams_by_program_gap(
                        remaining_courses.copy(),
                        st.session_state.filtered_pmf,
                        datetime.combine(sched_start, datetime.min.time()),
                        datetime.combine(sched_end, datetime.min.time()),
                        holidays,
                        weekends,
                        st.session_state.selected_semester
                    )
                elif dense_scheduling:
                    schedule = auto_schedule_exams_by_program_dense(
                        remaining_courses.copy(),
                        datetime.combine(sched_start, datetime.min.time()),
                        datetime.combine(sched_end, datetime.min.time()),
                        holidays,
                        weekends
                    )
                else:
                    # Default to gap scheduling if no option is explicitly selected
                    schedule = auto_schedule_exams_by_program_gap(
                        remaining_courses.copy(),
                        st.session_state.filtered_pmf,
                        datetime.combine(sched_start, datetime.min.time()),
                        datetime.combine(sched_end, datetime.min.time()),
                        holidays,
                        weekends,
                        st.session_state.selected_semester
                    )
            
            if schedule is None:
                st.error("Not enough valid business days to schedule all exams. Extend the date range or reduce courses.")
            else:
                if st.session_state.combination_groups:
                    schedule = assign_combination_groups_to_schedule(schedule, st.session_state.combination_groups)
                final_list = flatten_schedule_to_list(schedule)
                st.session_state.exam_date_list = final_list
                assigned_data = [{"Paper Code": c, "Exam Date": d.strftime("%Y-%m-%d"), "Time Slot": slot}
                                 for (c, d, slot) in final_list]
                st.success("Exams assigned successfully.")
                st.table(pd.DataFrame(assigned_data))
                
                # Review & Edit functionality
                if st.button("Review & Edit Assigned Dates", key="review_dates"):
                    review_df = pd.DataFrame([{"Paper Code": c, "Exam Date": d.strftime("%Y-%m-%d"), "Time Slot": slot}
                                               for (c, d, slot) in st.session_state.exam_date_list])
                    edited_review = st.data_editor(review_df, key="review_editor", num_rows="dynamic")
                    if st.button("Save Edited Assigned Dates", key="save_review"):
                        try:
                            updated = [(row["Paper Code"], datetime.strptime(row["Exam Date"], "%Y-%m-%d"), row["Time Slot"])
                                       for idx, row in edited_review.iterrows()]
                            st.session_state.exam_date_list = updated
                            st.success("Assigned exam dates updated.")
                        except Exception as e:
                            st.error(f"Error updating dates: {e}")
        
        if st.button("Auto-Resolve Conflicts", key="auto_resolve"):
            if not st.session_state.exam_date_list:
                st.error("No scheduled exams found. Please schedule exams first.")
            elif st.session_state.nominal_role_df is None:
                st.error("Please upload the Nominal Role File in Module 2 before resolving conflicts.")
            else:
                with st.spinner("Resolving conflicts..."):
                    resolved_list, log = resolve_conflicts(
                        st.session_state.exam_date_list,
                        st.session_state.nominal_role_df,
                        st.session_state.holiday_dates,
                        weekends={6}  # Sundays
                    )
                    
                    if resolved_list:
                        st.session_state.exam_date_list = resolved_list
                        st.session_state.timetable_exam_dates = resolved_list
                        st.success("Conflicts resolved successfully!")
                        st.subheader("Resolution Log")
                        for entry in log:
                            if "MOVED" in entry:
                                st.success(entry)
                            else:
                                st.warning(entry)
                        # Regenerate timetable
                        if st.button("Regenerate Timetable"):
                            st.experimental_rerun()
                    else:
                        st.error("Failed to resolve all conflicts automatically. Manual intervention needed.")
       
                    
                    if resolved_list:
                        st.session_state.exam_date_list = resolved_list
                        st.session_state.timetable_exam_dates = resolved_list
                        st.success("Conflicts resolved successfully!")
                        st.subheader("Resolution Log")
                        for entry in log:
                            if "MOVED" in entry:
                                st.success(entry)
                            else:
                                st.warning(entry)
                        # Regenerate timetable
                        if st.button("Regenerate Timetable"):
                            st.experimental_rerun()
                    else:
                        st.error("Failed to resolve all conflicts automatically. Manual intervention needed.")
        
        if st.button("Send Dates to Time Table Generator", key="send_dates"):
            if st.session_state.exam_date_list:
                st.session_state.timetable_exam_dates = st.session_state.exam_date_list.copy()
                st.success("Exam dates sent to Time Table Generator.")
            else:
                st.error("No exam dates available. Please schedule exams first.")

# --------------------
# Module 2: Time Table Generator
# --------------------
elif nav_tab == "Time Table Generator":
    st.header("Time Table Generator Module")
    exam_dates = st.session_state.get("timetable_exam_dates", [])
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Upload Nominal Role File (NRF)")
        uploaded_nrf = st.file_uploader("Load NRF", type=["xlsx", "xls"], key="nrf_mod2")
        if uploaded_nrf is not None:
            try:
                st.session_state.nominal_role_df = pd.read_excel(uploaded_nrf)
                st.success("NRF loaded successfully.")
            except Exception as e:
                st.error(f"Error loading NRF: {e}")
    
    with col2:
        timetable_type = st.radio("Select Timetable Type", options=["Combined", "By Program"])
        if timetable_type == "By Program":
            available_programmes = []
            if st.session_state.filtered_pmf is not None:
                available_programmes = st.session_state.filtered_pmf['Programme Name'].dropna().unique().tolist()
            if available_programmes:
                programme = st.selectbox("Select Programme", available_programmes, key="program_select_mod2")
            else:
                programme = None
        else:
            programme = None

    # Conflict resolution section
    st.subheader("Conflict Management")
    conflict_col1, conflict_col2 = st.columns([1, 2])
    
    with conflict_col1:
        # UNIQUE KEY FIX: Added _mod2 suffix
        if st.button("Auto-Resolve Conflicts", key="auto_resolve_mod2"):
            if not st.session_state.exam_date_list:
                st.error("No scheduled exams found. Please schedule exams first.")
            elif st.session_state.nominal_role_df is None:
                st.error("Please upload the Nominal Role File first.")
            else:
                with st.spinner("Resolving conflicts..."):
                    resolved_list, log = resolve_conflicts(
                        st.session_state.exam_date_list,
                        st.session_state.nominal_role_df,
                        st.session_state.holiday_dates,
                        weekends={6}  # Sundays
                    )
                    if resolved_list:
                        st.session_state.exam_date_list = resolved_list
                        st.session_state.timetable_exam_dates = resolved_list
                        st.success("Conflicts resolved successfully!")
                        st.subheader("Resolution Log")
                        for entry in log:
                            if "MOVED" in entry:
                                st.success(entry)
                            else:
                                st.warning(entry)
                        st.rerun()
                    else:
                        st.error("Failed to resolve all conflicts automatically. Manual intervention needed.")

    with conflict_col2:
        # UNIQUE KEY FIX: Added _mod2 suffix
        if st.button("Check Conflicts", key="check_conflicts_mod2"):
            exam_dates_map = st.session_state.timetable_exam_dates
            if not exam_dates_map:
                st.info("No exam dates to check.")
            else:
                if st.session_state.nominal_role_df is None:
                    st.error("Nominal role file not loaded or empty.")
                else:
                    conflicts = check_full_schedule_conflict(st.session_state.nominal_role_df, exam_dates_map)
                    if conflicts:
                        st.error("Conflicts detected:")
                        for c in conflicts:
                            st.write(c)
                    else:
                        st.success("No scheduling conflicts found.")
    
    # UNIQUE KEY FIX: Added _mod2 suffix
    if st.button("Generate Timetable", key="generate_timetable_mod2"):
        exam_dates = st.session_state.get("timetable_exam_dates", [])
    
    if not exam_dates:
        st.error("No exam dates assigned. Please schedule and send exam dates first.")
    elif st.session_state.filtered_pmf is None or st.session_state.nominal_role_df is None:
        st.error("Ensure both PMF (filtered) and NRF files are loaded.")
    else:
        df_papers = st.session_state.filtered_pmf.copy()
        if st.session_state.selected_degree:
            if st.session_state.selected_degree == 'UG':
                df_papers = df_papers[
                    (df_papers['Paper Code'].astype(str).str.startswith('U')) |
                    (df_papers['Paper Code'].astype(str).str.upper().str.startswith('BPAM'))
                ]
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
        timetable_entries = []
        for (course, dt_obj, slot) in exam_dates:
            row_match = df_papers[df_papers['Paper Code'].astype(str).str.strip() == course.strip()]
            if not row_match.empty:
                paper_title = row_match.iloc[0]['Paper Title']
                programme_entry = row_match.iloc[0]['Programme Name']
                timetable_entries.append((dt_obj, course, paper_title, programme_entry))
            else:
                timetable_entries.append((dt_obj, course, "Unknown Title", "Unknown Programme"))
        timetable_entries.sort(key=lambda x: (x[0], x[1]))
        df_timetable = pd.DataFrame(timetable_entries, columns=['Date', 'Paper Code', 'Paper Title', 'Programs'])
        df_timetable['Date'] = df_timetable['Date'].dt.strftime('%d/%m/%Y')
        df_timetable.loc[df_timetable.duplicated(subset=['Date']), 'Date'] = ""
        st.success("Exam Timetable generated successfully.")
        st.dataframe(df_timetable)
        download_csv(df_timetable, "exam_timetable.csv")
        st.session_state.generated_timetable = df_timetable
    
    if st.session_state.generated_timetable is not None:
        st.markdown("#### Edit Exam Dates/Slots")
        editable_timetable = st.session_state.generated_timetable.copy()
        editable_timetable['Date'] = pd.to_datetime(
            editable_timetable['Date'], 
            format='%d/%m/%Y'
        )
        # UNIQUE KEY FIX: Added _mod2 suffix
        edited_timetable = st.data_editor(
            editable_timetable, 
            key="edit_timetable_mod2", 
            num_rows="dynamic", 
            use_container_width=True
        )
        # UNIQUE KEY FIX: Added _mod2 suffix
        if st.button("Save Edited Dates", key="save_edit_timetable_mod2"):
            updated = []
            for _, row in edited_timetable.iterrows():
                updated.append((row['Paper Code'], row['Date'], row['Time Slot']))
            st.session_state.exam_date_list = updated
            st.session_state.timetable_exam_dates = updated
            st.success("Edited exam dates saved.")
    
    col_gen1, col_gen2 = st.columns(2)
    with col_gen1:
        # UNIQUE KEY FIX: Added _mod2 suffix
        if st.button("Clear Timetable", key="clear_timetable_mod2"):
            st.session_state.exam_date_list = []
            st.session_state.timetable_exam_dates = []
            st.session_state.generated_timetable = None
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

