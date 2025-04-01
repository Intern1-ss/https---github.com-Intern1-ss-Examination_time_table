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



try:
    with open("styles.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except Exception:
    st.info("Custom styles.css not found. Using default styling.")

# Session State Initialization
if 'paper_master_df' not in st.session_state:
    st.session_state.paper_master_df = None
if 'filtered_pmf' not in st.session_state:
    st.session_state.filtered_pmf = None
if 'nominal_role_df' not in st.session_state:
    st.session_state.nominal_role_df = None
if 'exam_date_list' not in st.session_state:
    st.session_state.exam_date_list = []
if 'combination_groups' not in st.session_state:
    st.session_state.combination_groups = []
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

# Utility Functions
SEM_MAPPING = {
    '1': "I", '2': "II", '3': "III", '4': "IV",
    '5': "V", '6': "VI", '7': "VII", '8': "VIII"
}

def extract_semester(paper_code):
    code = str(paper_code).strip().upper()
    if code.startswith("BPAM"):
        match = re.search(r'BPAM-?(\d+)', code)
        if match:
            num_part = match.group(1)
            if len(num_part) >= 3:
                prefix = num_part[:3]
                if prefix.startswith("20"): return "II"
                elif prefix.startswith("40"): return "IV"
                elif prefix.startswith("60"): return "VI"
                elif prefix.startswith("80"): return "VIII"
            elif len(num_part) >= 2:
                prefix = num_part[:2]
                if prefix == "20": return "II"
                elif prefix == "40": return "IV"
                elif prefix == "60": return "VI"
                elif prefix == "80": return "VIII"
        return "I"
    else:
        numeric_parts = re.findall(r'\d+', code)
        for part in numeric_parts:
            if '30' in part: return "IV"
            elif '20' in part: return "II"
        matches = re.findall(r'\d{3}', code)
        if matches:
            digits = matches[-1]
            for ch in digits:
                if ch in SEM_MAPPING: return SEM_MAPPING[ch]
        for ch in code:
            if ch in SEM_MAPPING: return SEM_MAPPING[ch]
    return None

def download_csv(df, filename):
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", data=csv, file_name=filename, mime="text/csv")

def flatten_schedule_to_list(schedule_dict):
    results = []
    for date_str, slot_dict in schedule_dict.items():
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        for slot, courses in slot_dict.items():
            for c in courses:
                results.append((c, date_obj, slot))
    results.sort(key=lambda x: (x[1], x[2]))
    return results

def find_valid_date_for_UELS(start_date, end_date, holidays, weekends, existing_schedule):
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        if (current_date.weekday() not in weekends and 
            current_date not in holidays and 
            date_str not in existing_schedule):
            return current_date
        current_date += timedelta(days=1)
    return start_date

def auto_schedule_exams_by_program_gap(courses, pmf_df, start_date, end_date, holidays, weekends, semester):
    courses = list(dict.fromkeys(courses))
    fixed_slot = "09:00 - 10:30"
    valid_days = [d for d in (start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1))
                  if d.weekday() not in weekends and d not in holidays]
    if not valid_days:
        return None
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
        possible_days = [day for day in valid_days if min_date <= day <= end_date]
        if not possible_days:
            return None
        chosen_day = min(possible_days)
        num_papers_today = min(random.randint(min_papers, max_papers), len(courses))
        papers_to_schedule = courses[:num_papers_today]
        schedule[chosen_day.strftime("%Y-%m-%d")][fixed_slot] = papers_to_schedule
        courses = courses[num_papers_today:]
        last_scheduled_date = chosen_day
    return schedule

def auto_schedule_exams_by_program_dense(courses, start_date, end_date, holidays, weekends):
    fixed_slot = "09:00 - 10:30"
    valid_days = [d for d in (start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1))
                  if d.weekday() not in weekends and d not in holidays]
    if not valid_days:
        return None
    schedule = defaultdict(lambda: defaultdict(list))
    last_scheduled_date = None
    while courses:
        if last_scheduled_date is None:
            min_date = start_date
        else:
            min_date = last_scheduled_date + timedelta(days=2)
        possible_days = [day for day in valid_days if min_date <= day <= end_date]
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
    time_slots = ["09:00 - 10:30"]
    valid_days = [d for d in (start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1))
                  if d.weekday() not in weekends and d not in holidays]
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
    conflicts = []
    schedule_map = defaultdict(lambda: defaultdict(list))
    for course, dt_obj, slot in exam_list:
        date_str = dt_obj.strftime("%Y-%m-%d")
        schedule_map[date_str][slot].append(course.strip())
    
    student_papers = defaultdict(list)
    code_columns = [col for col in nominal_df.columns if "Code" in col and not col.startswith(("Programme", "Sl"))]
    reg_no_col = "Regd. No." if "Regd. No." in nominal_df.columns else None
    
    for idx, row in nominal_df.iterrows():
        reg_no = row.get(reg_no_col, f"Student_{idx}")
        student_courses = set()
        for col in code_columns:
            if pd.notna(row[col]):
                code = str(row[col]).strip()
                if code:
                    student_courses.add(code)
        student_papers[reg_no] = list(student_courses)
    
    for reg_no, enrolled_courses in student_papers.items():
        student_schedule = defaultdict(list)
        for date_str, slot_dict in schedule_map.items():
            for slot, courses in slot_dict.items():
                scheduled_courses = [course for course in courses if course in enrolled_courses]
                if scheduled_courses:
                    student_schedule[(date_str, slot)].extend(scheduled_courses)
        
        for (date_str, slot), courses in student_schedule.items():
            if len(courses) > 1:
                conflicts.append(
                    f"Student {reg_no} has multiple exams on {date_str} in slot '{slot}': {', '.join(courses)}"
                )
    
    return conflicts

def resolve_conflicts(exam_list, nominal_df, holidays, weekends):
    unique_exam_list = []
    seen = set()
    for course, dt, slot in exam_list:
        key = (course.strip(), dt.date(), slot)
        if key not in seen:
            seen.add(key)
            unique_exam_list.append((course, dt, slot))
    exam_list = unique_exam_list
    conflicts = check_full_schedule_conflict(nominal_df, exam_list)
    resolution_log = []
    if not conflicts:
        return exam_list, resolution_log
    valid_days = []
    current_date = min(dt for _, dt, _ in exam_list).date() if exam_list else datetime.today().date()
    end_date = (max(dt for _, dt, _ in exam_list).date() + timedelta(days=14)) if exam_list else current_date + timedelta(days=14)
    while current_date <= end_date:
        if current_date.weekday() not in weekends and current_date not in holidays:
            valid_days.append(current_date)
        current_date += timedelta(days=1)
    student_courses = defaultdict(set)
    course_students = defaultdict(set)
    code_columns = [col for col in nominal_df.columns if "Code" in col and not col.startswith(("Programme", "Sl"))]
    reg_no_col = "Regd. No." if "Regd. No." in nominal_df.columns else None
    for idx, row in nominal_df.iterrows():
        reg_no = row.get(reg_no_col, f"Student_{idx}")
        for col in code_columns:
            if pd.notna(row[col]):
                code = str(row[col]).strip()
                if code:
                    student_courses[reg_no].add(code)
                    course_students[code].add(reg_no)
    schedule_map = defaultdict(lambda: defaultdict(list))
    for course, dt, slot in exam_list:
        date_str = dt.strftime("%Y-%m-%d")
        schedule_map[date_str][slot].append(course)
    pmf_df = st.session_state.paper_master_df
    idm_courses = set(pmf_df[pmf_df['Is IDM']]['Paper Code'].astype(str).str.strip()) if pmf_df is not None else set()
    for conflict in conflicts:
        if "Student" not in conflict:
            continue
        reg_no = conflict.split(" ")[1]
        date_str = conflict.split("on")[1].split("in")[0].strip()
        slot = conflict.split("slot '")[1].split("':")[0]
        conflicting_courses = conflict.split(": ")[1].split(", ")
        course_enrollment_counts = {course: len(course_students.get(course, set())) for course in conflicting_courses}
        idm_in_conflict = [c for c in conflicting_courses if c in idm_courses]
        course_to_move = min(
            conflicting_courses,
            key=lambda c: (0 if c in idm_in_conflict else 1, course_enrollment_counts[c])
        )
        affected_students = course_students.get(course_to_move, set())
        original_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        for new_date in valid_days:
            if new_date == original_date:
                continue
            new_date_str = new_date.strftime("%Y-%m-%d")
            safe_move = True
            for student in affected_students:
                other_courses = student_courses[student] - {course_to_move}
                scheduled_courses = schedule_map.get(new_date_str, {}).get(slot, [])
                if any(c in scheduled_courses for c in other_courses):
                    safe_move = False
                    break
            if safe_move:
                if course_to_move in schedule_map.get(date_str, {}).get(slot, []):
                    schedule_map[date_str][slot].remove(course_to_move)
                    if not schedule_map[date_str][slot]:
                        del schedule_map[date_str][slot]
                    if not schedule_map[date_str]:
                        del schedule_map[date_str]
                    schedule_map[new_date_str][slot].append(course_to_move)
                    resolution_log.append(
                        f"Moved {course_to_move} for student {reg_no} from {date_str} to {new_date_str} in slot {slot}"
                    )
                else:
                    resolution_log.append(
                        f"Course {course_to_move} not found in schedule for {date_str} slot {slot}. Skipping removal."
                    )
                break
        else:
            resolution_log.append(f"Could not resolve conflict for {course_to_move} on {date_str} in slot {slot}")
    resolved_exam_list = []
    for date_str, slots in schedule_map.items():
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        for slot, courses in slots.items():
            for course in courses:
                resolved_exam_list.append((course, dt, slot))
    resolved_exam_list.sort(key=lambda x: (x[1], x[2]))
    return resolved_exam_list, resolution_log

def assign_combination_groups_to_schedule(schedule, groups):
    fixed_slot = "09:00 - 10:30"
    for group in groups:
        date_str = group["date"].strftime("%Y-%m-%d")
        if date_str not in schedule:
            schedule[date_str] = {fixed_slot: []}
        for c in group["courses"]:
            schedule[date_str][fixed_slot].append(c)
    return schedule

# Main Header & File Uploads
st.markdown(
    """
    <style>
    /* Gradient background for the whole app */
    .stApp {
        background: linear-gradient(135deg, #4b6cb7, #182848);
        color: white;
    }
    /* Styling for the header */
    h1 {
        position: relative;
        display: inline-block;
    }
    .beta-badge {
        position: absolute;
        top: -0.3rem;
        right: -2rem;
        background-color: #ff4b4b;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        font-size: 0.9rem;
        font-weight: bold;
        box-shadow: 0 0 10px 2px rgba(255, 75, 75, 0.8);
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    "<h1>TimeTable PRO "
    "<span class='beta-badge'>BETA</span>"
    "</h1>"
    "<h3 style='margin-top: 0.5rem;'>Organize. Optimize. Succeed.</h3>",
    unsafe_allow_html=True
)

st.subheader("Upload Required Files")
col_upload1, col_upload2 = st.columns(2)
with col_upload1:
    uploaded_pmf = st.file_uploader("Load Paper Master File (PMF)", type=["xlsx", "xls"], key="pmf_global")
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
with col_upload2:
    uploaded_nrf = st.file_uploader("Load Nominal Role File (NRF)", type=["xlsx", "xls"], key="nrf_global")
    if uploaded_nrf is not None:
        try:
            st.session_state.nominal_role_df = pd.read_excel(uploaded_nrf)
            st.success("NRF loaded successfully.")
        except Exception as e:
            st.error(f"Error loading NRF: {e}")

# Sidebar Navigation
with st.sidebar:
    nav_tab = on_hover_tabs(
        tabName=['Exam Date Entry', 'Time Table Generator', 'Student Count'],
        iconName=['calendar', 'table', 'user'],
        default_choice=0
    )

# Module 1: Exam Date Entry
if nav_tab == "Exam Date Entry":
    st.header("Exam Date Entry Module")
    if st.session_state.paper_master_df is None:
        st.error("Please upload the Paper Master File (PMF) first.")
    else:
        # Define special course groups
        MANDATORY_GROUP = {"UTEL-201", "UHIN-201", "USAN-201", "UENG-201"}
        SPECIAL_SOLO = {"UELS-201"}
        
        col1, col2, col3 = st.columns(3)
        with col1:
            academic_year = st.selectbox("Select Academic Year", [f"{year}/{year+1}" for year in range(datetime.now().year-5, datetime.now().year+5)])
        with col2:
            degree_type = st.selectbox("Select Degree Type", ['UG', 'PG', 'Professional'])
            st.session_state.selected_degree = degree_type
        with col3:
            paper_type = st.selectbox("Select Paper Type", ['All', 'Theory', 'Practical'])
        
        df = st.session_state.paper_master_df.copy()
        if degree_type == 'UG':
            df = df[(df['Paper Code'].astype(str).str.startswith('U')) |
                    (df['Paper Code'].astype(str).str.upper().str.startswith('BPAM'))]
        elif degree_type == 'PG':
            df = df[df['Paper Code'].astype(str).str.startswith('P')]
        elif degree_type == 'Professional':
            df = df[df['Paper Code'].astype(str).str.startswith('M')]
        df = df[~df['Paper Code'].astype(str).str.startswith('UAWR')]
        df['Derived Semester'] = df['Paper Code'].apply(extract_semester)
        
        semesters = sorted(set(df['Derived Semester'].dropna()), key=lambda s: list(SEM_MAPPING.values()).index(s) if s in SEM_MAPPING.values() else 99)
        selected_semester = st.selectbox("Select Mapped Semester", options=semesters)
        st.session_state.selected_semester = selected_semester
        
        # Base filtering by derived semester
        base_df = df[df['Derived Semester'] == selected_semester].copy()
        
        # Augment with NRF data if available
        if st.session_state.nominal_role_df is not None:
            nrf = st.session_state.nominal_role_df
            nrf_semester_col = 'Semester' if 'Semester' in nrf.columns else None
            enrolled_codes = set()
            code_columns = [col for col in nrf.columns if "Code" in col and not col.startswith(("Programme", "Sl"))]
            if nrf_semester_col:
                nrf_filtered = nrf[nrf[nrf_semester_col] == selected_semester]
                for col in code_columns:
                    enrolled_codes.update(nrf_filtered[col].dropna().astype(str).str.strip())
            else:
                for col in code_columns:
                    enrolled_codes.update(nrf[col].dropna().astype(str).str.strip())
            # Include additional codes from NRF that students in this semester are enrolled in
            additional_df = df[df['Paper Code'].astype(str).str.strip().isin(enrolled_codes) & 
                             ~df['Paper Code'].isin(base_df['Paper Code'])]
            df = pd.concat([base_df, additional_df]).drop_duplicates(subset=['Paper Code'])
        else:
            df = base_df
            st.warning("NRF not loaded. Using derived semester only, but cross-semester courses will still appear if derived correctly.")
        
        st.session_state.filtered_pmf = df.copy()
        available_courses = df['Paper Code'].unique().tolist()
        auto_select = st.checkbox("Auto-Select All Courses", value=True)
        selected_courses = st.multiselect("Selected Courses", options=available_courses, default=available_courses if auto_select else [])
        st.write("Selected Courses:", selected_courses)
        
        # Auto-create mandatory group and UELS group only for Semester II
        if selected_semester == "II":
            # Mandatory group creation
            mandatory_selected = MANDATORY_GROUP.intersection(selected_courses)
            if mandatory_selected:
                existing_groups = [set(grp["courses"]) for grp in st.session_state.combination_groups]
                if not any(mandatory_selected.issubset(g) for g in existing_groups):
                    st.session_state.combination_groups.insert(0, {
                        "group_name": "Mandatory Language Group",
                        "courses": list(mandatory_selected),
                        "date": datetime.combine(datetime.now().date(), datetime.min.time())
                    })
            
            # UELS-201 solo group creation
            if "UELS-201" in selected_courses:
                existing_groups = [grp["courses"] for grp in st.session_state.combination_groups]
                if ["UELS-201"] not in existing_groups:
                    st.session_state.combination_groups.append({
                        "group_name": "UELS-201 Solo",
                        "courses": ["UELS-201"],
                        "date": datetime.combine(datetime.now().date(), datetime.min.time())
                    })
        
        st.markdown("#### Combine Elective Courses")
        st.info("Select elective courses to be conducted on the same day (same slot).")
        combine_selection = st.multiselect("Select courses to combine", options=[c for c in selected_courses 
            if c not in MANDATORY_GROUP and c not in SPECIAL_SOLO], key="combine_selection")
        group_name_input = st.text_input("Enter Group Name (optional)", key="group_name_input")
        group_date = st.date_input("Select Common Exam Date", value=datetime.now().date(), key="group_date")
        if st.button("Add Combination Group", key="add_group"):
            if len(combine_selection) < 2:
                st.error("Select at least two courses to combine.")
            else:
                group_name = group_name_input.strip() or f"Group {len(st.session_state.combination_groups)+1}"
                new_group = {"group_name": group_name, "courses": combine_selection, "date": datetime.combine(group_date, datetime.min.time())}
                st.session_state.combination_groups.append(new_group)
                st.success(f"Combination group '{group_name}' added.")
        
        if st.session_state.combination_groups:
            st.markdown("##### Combined Elective Groups")
            combo_df = pd.DataFrame([
                {
                    "Group Name": grp["group_name"],
                    "Courses": ", ".join(grp["courses"]),
                    "Date": grp["date"].strftime("%Y-%m-%d")
                }
                for grp in st.session_state.combination_groups
            ])
            edited_combo = st.data_editor(combo_df, key="edit_combo", num_rows="dynamic")
            
            if st.button("Save Edited Group Dates", key="save_combo"):
                try:
                    for idx, row in edited_combo.iterrows():
                        new_date = datetime.strptime(row["Date"], "%Y-%m-%d")
                        st.session_state.combination_groups[idx]["date"] = new_date
                    st.success("Combination group dates updated successfully.")
                except Exception as e:
                    st.error(f"Error updating dates: {e}")
            
            group_to_remove = st.selectbox("Select a group to remove", options=[grp["group_name"] for grp in st.session_state.combination_groups], key="remove_group")
            if st.button("Remove Group", key="remove_group_btn"):
                st.session_state.combination_groups = [grp for grp in st.session_state.combination_groups if grp["group_name"] != group_to_remove]
                st.success(f"Group '{group_to_remove}' removed.")
        
        holiday_date = st.date_input("Enter Holiday Date", value=datetime.now().date(), key="holiday_date")
        if st.button("Add Holiday", key="add_holiday"):
            if holiday_date not in st.session_state.holiday_dates:
                st.session_state.holiday_dates.append(holiday_date)
                st.success(f"Holiday {holiday_date} added.")
        if st.session_state.holiday_dates:
            st.markdown("### Current Holiday Dates")
            holiday_df = pd.DataFrame(st.session_state.holiday_dates, columns=["Holiday Date"])
            edited_holidays = st.data_editor(holiday_df, key="edit_holidays", num_rows="dynamic")
            if st.button("Save Edited Holidays", key="save_holidays"):
                new_holidays = pd.to_datetime(edited_holidays["Holiday Date"]).dt.date.tolist()
                st.session_state.holiday_dates = new_holidays
                st.success("Holiday dates updated.")
        
        holidays = st.session_state.holiday_dates
        weekends = {6}
        grouped_courses = set(course for grp in st.session_state.combination_groups for course in grp["courses"])
        remaining_courses = [course for course in selected_courses if course not in grouped_courses]
        
        st.markdown("#### Automatic Scheduling of Individual Courses")
        sched_start = st.date_input("Scheduling Start Date", value=datetime.now().date(), key="sched_start")
        sched_end = st.date_input("Scheduling End Date", value=(datetime.now() + timedelta(days=15)).date(), key="sched_end")
        gap_scheduling = st.checkbox("Use Gap Scheduling (2-3 day gaps, randomized paper count)", value=True)
        dense_scheduling = st.checkbox("Use Dense Scheduling (pack exams closely)", value=False)
        if gap_scheduling and dense_scheduling:
            st.warning("Both Gap and Dense Scheduling selected. Gap Scheduling will be applied.")
        
        if st.button("Schedule Exams", key="schedule_btn"):
            mandatory_in_selected = MANDATORY_GROUP.intersection(selected_courses)
            if mandatory_in_selected and len(mandatory_in_selected) != 4:
                st.error("Mandatory language courses must be scheduled together. Please include all 4 courses.")
            
            if "UELS-201" in selected_courses and any(c != "UELS-201" for grp in st.session_state.combination_groups 
                                                    for c in grp["courses"] if "UELS-201" in grp["courses"]):
                st.error("UELS-201 must be scheduled alone. Remove it from any combination groups.")
            
            else:
                if not remaining_courses and not st.session_state.combination_groups:
                    st.error("No courses selected to schedule.")
                else:
                    if selected_semester == "VI":
                        schedule = auto_schedule_exams_multi_slot(remaining_courses, sched_start, sched_end, holidays, weekends)
                    elif gap_scheduling or not dense_scheduling:
                        schedule = auto_schedule_exams_by_program_gap(remaining_courses.copy(), df, sched_start, sched_end, holidays, weekends, selected_semester)
                    else:
                        schedule = auto_schedule_exams_by_program_dense(remaining_courses.copy(), sched_start, sched_end, holidays, weekends)
                    
                    if schedule is None:
                        st.error("Not enough valid business days to schedule all exams.")
                    else:
                        if st.session_state.combination_groups:
                            schedule = assign_combination_groups_to_schedule(schedule, st.session_state.combination_groups)
                        
                        if "UELS-201" in selected_courses:
                            uels_date = find_valid_date_for_UELS(sched_start, sched_end, holidays, weekends, schedule)
                            schedule[uels_date.strftime("%Y-%m-%d")] = {"09:00 - 10:30": ["UELS-201"]}
                        
                        final_list = flatten_schedule_to_list(schedule)
                        st.session_state.exam_date_list = final_list
                        assigned_data = [{"Paper Code": c, "Exam Date": d.strftime("%Y-%m-%d"), "Time Slot": slot} for c, d, slot in final_list]
                        st.success("Exams assigned successfully.")
                        st.table(pd.DataFrame(assigned_data))
        
        if st.button("Send Dates to Time Table Generator", key="send_dates"):
            if st.session_state.exam_date_list:
                st.session_state.timetable_exam_dates = st.session_state.exam_date_list.copy()
                st.success("Exam dates sent to Time Table Generator.")
            else:
                st.error("No exam dates available. Please schedule exams first.")

# Module 2: Time Table Generator
elif nav_tab == "Time Table Generator":
    st.header("Time Table Generator Module")
    exam_dates = st.session_state.get("timetable_exam_dates", [])
    col1, col2 = st.columns(2)
    with col1:
        timetable_type = st.radio("Select Timetable Type", options=["Combined", "By Program"])
    with col2:
        if timetable_type == "By Program":
            available_programmes = st.session_state.filtered_pmf['Programme Name'].dropna().unique().tolist() if st.session_state.filtered_pmf is not None else []
            programme = st.selectbox("Select Programme", available_programmes, key="program_select_mod2") if available_programmes else None
        else:
            programme = None
    
    st.subheader("Conflict Management")
    conflict_col1, conflict_col2 = st.columns(2)
    with conflict_col1:
        if st.button("Check Conflicts", key="check_conflicts_mod2"):
            if not exam_dates:
                st.info("No exam dates to check.")
            elif st.session_state.nominal_role_df is None:
                st.error("Please upload the Nominal Role File first.")
            else:
                conflicts = check_full_schedule_conflict(st.session_state.nominal_role_df, exam_dates)
                if conflicts:
                    st.error("Conflicts detected:")
                    for c in conflicts:
                        st.write(c)
                else:
                    st.success("No scheduling conflicts found.")
    with conflict_col2:
        if st.button("Auto-Resolve Conflicts", key="auto_resolve_mod2"):
            if not exam_dates:
                st.error("No scheduled exams found. Please schedule exams first.")
            elif st.session_state.nominal_role_df is None:
                st.error("Please upload the Nominal Role File first.")
            else:
                with st.spinner("Resolving conflicts..."):
                    resolved_list, log = resolve_conflicts(
                        exam_dates,
                        st.session_state.nominal_role_df,
                        st.session_state.holiday_dates,
                        weekends={6}
                    )
                    st.session_state.timetable_exam_dates = resolved_list
                    st.session_state.exam_date_list = resolved_list
                    st.success("Conflict resolution completed. Regenerate timetable to see updates.")
                    st.write("Resolution Log:")
                    for entry in log:
                        st.write(entry)
    
    if st.button("Generate Timetable", key="generate_timetable_mod2"):
        if not exam_dates:
            st.error("No exam dates assigned. Please schedule exams in Exam Date Entry first.")
        elif st.session_state.filtered_pmf is None:
            st.error("Please upload the Paper Master File (PMF) first.")
        else:
            df_papers = st.session_state.filtered_pmf.copy()
            if timetable_type == "By Program" and programme:
                df_papers = df_papers[df_papers['Programme Name'] == programme]
            if df_papers.empty:
                st.error("No matching courses found with the selected filters.")
            else:
                timetable_entries = []
                for course, dt_obj, slot in exam_dates:
                    row_match = df_papers[df_papers['Paper Code'].astype(str).str.strip() == course.strip()]
                    if not row_match.empty:
                        paper_title = row_match.iloc[0]['Paper Title']
                        programme_entry = row_match.iloc[0]['Programme Name']
                        timetable_entries.append((dt_obj, slot, course, paper_title, programme_entry))
                    else:
                        timetable_entries.append((dt_obj, slot, course, "Unknown Title", "Unknown Programme"))
                timetable_entries.sort(key=lambda x: (x[0], x[1]))
                grouped = {}
                for entry in timetable_entries:
                    date_key = entry[0].strftime('%d/%m/%Y')
                    if date_key not in grouped:
                        grouped[date_key] = []
                    grouped[date_key].append(entry)

                merged_rows = []
                for date, entries in grouped.items():
                    merged_rows.append([date, "", "", "", ""])
                    for entry in entries:
                        dt_obj, slot, code, title, program = entry
                        merged_rows.append(["", slot, code, title, program])

                display_columns = ['Date', 'Time Slot', 'Paper Code', 'Paper Title', 'Programs']
                display_df = pd.DataFrame(merged_rows, columns=display_columns)

                st.session_state.generated_timetable = display_df
                st.session_state.original_timetable = pd.DataFrame(timetable_entries, columns=display_columns)
                st.success("Exam Timetable generated successfully.")
                
    
        if st.session_state.generated_timetable is not None:
            st.subheader("Editable Timetable")
            edited_df = st.data_editor(
            st.session_state.original_timetable,
            num_rows="dynamic",
            column_config={
                "Date": st.column_config.DateColumn(
                    "Exam Date",
                    format="DD/MM/YYYY",
                    required=True
                ),
                "Time Slot": st.column_config.SelectboxColumn(
                    "Time Slot",
                    options=["09:00 - 10:30", "09:00 - 11:00"],
                    required=True
                )
            },
            key="edit_timetable_mod2"
        )
        
        if st.button("Save Edited Dates", key="save_edit_timetable_mod2"):
            errors = []
            updated_exams = []
            
            for idx, row in edited_df.iterrows():
                try:
                    if isinstance(row['Date'], str):
                        dt_obj = datetime.strptime(row['Date'], '%d/%m/%Y')
                    else:
                        dt_obj = row['Date']
                    
                    valid_slots = ["09:00 - 10:30", "09:00 - 11:00"]
                    if row['Time Slot'] not in valid_slots:
                        raise ValueError(f"Invalid time slot: {row['Time Slot']}")
                    
                    updated_exams.append((
                        row['Paper Code'],
                        dt_obj,
                        row['Time Slot']
                    ))
                    
                except Exception as e:
                    errors.append(f"Row {idx+1} ({row['Paper Code']}): {str(e)}")
            
            if errors:
                st.error("Errors found:")
                for error in errors:
                    st.write(error)
            else:
                st.session_state.timetable_exam_dates = updated_exams
                st.session_state.exam_date_list = updated_exams
                st.success("Edited exam dates saved successfully!")
                st.experimental_rerun()
        
        st.dataframe(edited_df)
        download_csv(edited_df, "exam_timetable.csv")

# Module 3: Student Count
elif nav_tab == "Student Count":
    st.header("Student Count Module")
    if st.button("Calculate Student Count", key="calc_student_count"):
        if st.session_state.nominal_role_df is None:
            st.error("Please upload the Nominal Role File (NRF) first.")
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
