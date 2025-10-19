import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os
import hashlib
import json

# --------- Setup ---------
BASE_FOLDER = "user_folders"
os.makedirs(BASE_FOLDER, exist_ok=True)
st.set_page_config(page_title="🏋️ Gym Tracker", layout="wide")

# --------- Session state defaults ---------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "users" not in st.session_state:
    st.session_state.users = {}

# --------- Load users ---------
USERS_FILE = os.path.join(BASE_FOLDER, "users.json")
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r") as f:
        st.session_state.users = json.load(f)
else:
    st.session_state.users = {}

# --------- Helper functions ---------
def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def save_users():
    with open(USERS_FILE, "w") as f:
        json.dump(st.session_state.users, f)

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if "users" not in st.session_state:
    # Load users from folder structure
    if os.path.exists(BASE_FOLDER):
        st.session_state.users = [f for f in os.listdir(BASE_FOLDER) if os.path.isdir(os.path.join(BASE_FOLDER, f))]
    else:
        os.makedirs(BASE_FOLDER)
        st.session_state.users = []

# --------- Login / Create Account ---------
if not st.session_state.logged_in:
    st.sidebar.header("Account")
    action = st.sidebar.radio("Choose Action", ["Login", "Create Account"])

    username_input = st.sidebar.text_input("Username")
    password_input = st.sidebar.text_input("Password", type="password")  # For simplicity, store plain passwords for now

    if action == "Login" and st.sidebar.button("Login"):
        if username_input in st.session_state.users:
            # Here you could check password if you implement password storage
            st.session_state.logged_in = True
            st.session_state.username = username_input
            st.success(f"Logged in as {username_input}")
        else:
            st.error("Invalid username")

    elif action == "Create Account" and st.sidebar.button("Create Account"):
        if not username_input or not password_input:
            st.error("Username and password cannot be empty")
        elif username_input in st.session_state.users:
            st.error("Username already exists")
        else:
            # Create user folder and CSV
            user_folder = os.path.join(BASE_FOLDER, username_input)
            os.makedirs(user_folder, exist_ok=True)
            csv_file = os.path.join(user_folder, "workouts.csv")
            pd.DataFrame(columns=["Date", "Exercise", "Weight", "Reps"]).to_csv(csv_file, index=False)

            st.session_state.users.append(username_input)
            st.session_state.logged_in = True
            st.session_state.username = username_input
            st.success(f"Account created and logged in as {username_input}")

# --------- Logged in UI ---------
if st.session_state.logged_in:
    st.sidebar.write(f"👤 Logged in as: {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.success("Logged out")

# --------- Main App ---------
else:
    st.sidebar.write(f"👤 Logged in as: {st.session_state.username}")
    if st.sidebar.button("Logout"):
        logout_user()

    # --------- Paths and CSV ---------
    user_folder = os.path.join(BASE_FOLDER, st.session_state.username)
    os.makedirs(user_folder, exist_ok=True)
    csv_file = os.path.join(user_folder, "workouts.csv")

    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date", "Weight", "Reps"])
    else:
        df = pd.DataFrame(columns=["Date", "Exercise", "Weight", "Reps"])

    # --------- Log Workout ---------
    st.sidebar.header("💪 Log Workout")
    date = st.sidebar.date_input("Date", datetime.now())

    existing_exercises = df["Exercise"].unique().tolist()
    exercise = st.sidebar.selectbox(
        "Exercise (select or type new)",
        existing_exercises + ["Add new exercise"]
    )
    if exercise == "Add new exercise":
        exercise = st.sidebar.text_input("New Exercise Name", "")

    weight = st.sidebar.number_input("Weight (kg)", min_value=0.0, step=0.5)
    reps = st.sidebar.number_input("Reps", min_value=0, step=1)

    if st.sidebar.button("💾 Save Workout"):
        if exercise:
            new_row = pd.DataFrame([[date, exercise, weight, reps]],
                                   columns=["Date", "Exercise", "Weight", "Reps"])
            df = pd.concat([df, new_row]).drop_duplicates(
                subset=["Date", "Exercise"], keep="last")
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df.dropna(subset=["Date", "Weight", "Reps"])
            df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
            df.to_csv(csv_file, index=False)
            st.sidebar.success(f"Saved {exercise}!")
        else:
            st.sidebar.error("Exercise name cannot be empty.")

    # --------- Exercise filter ---------
    exercise_list = df["Exercise"].unique().tolist()
    selected_exercises = st.multiselect(
        "Select Exercises to Plot", exercise_list, default=exercise_list)

    # --------- Individual exercise charts ---------
    st.header(f"{st.session_state.username} - Workout Progress")
    for exercise_name in selected_exercises:
        data = df[df["Exercise"] == exercise_name].sort_values("Date")
        if data.empty:
            continue

        data["Date"] = pd.to_datetime(data["Date"])
        fig, ax1 = plt.subplots(figsize=(8, 4))
        ax1.plot(data["Date"], data["Weight"], marker="o", color="tab:blue")
        ax1.set_xlabel("Date")
        ax1.set_ylabel("Weight (kg)", color="tab:blue")
        ax1.tick_params(axis="y", labelcolor="tab:blue")
        ax1.grid(True, linestyle="--", alpha=0.6)

        ax2 = ax1.twinx()
        ax2.plot(data["Date"], data["Reps"], marker="x", linestyle="--", color="tab:red")
        ax2.set_ylabel("Reps", color="tab:red")
        ax2.tick_params(axis="y", labelcolor="tab:red")

        ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        fig.autofmt_xdate(rotation=45)

        ax1.set_title(f"{st.session_state.username} - {exercise_name}")
        st.pyplot(fig)

    # --------- BodyWeight chart ---------
    if "BodyWeight" in df["Exercise"].unique():
        bw_data = df[df["Exercise"] == "BodyWeight"].sort_values("Date")
        if not bw_data.empty:
            bw_data["Date"] = pd.to_datetime(bw_data["Date"])
            st.header(f"{st.session_state.username} - BodyWeight Progress")

            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(bw_data["Date"], bw_data["Weight"], marker="s", color="tab:green")
            ax.set_xlabel("Date")
            ax.set_ylabel("Weight (kg)")
            ax.set_title(f"{st.session_state.username} - BodyWeight")
            ax.grid(True, linestyle="--", alpha=0.6)
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            fig.autofmt_xdate(rotation=45)
            st.pyplot(fig)

    # --------- Combined chart ---------
    if not df.empty:
        st.header(f"{st.session_state.username} - All Exercises Combined")
        plt.figure(figsize=(10, 5))
        for exercise_name, data in df.groupby("Exercise"):
            data = data.sort_values("Date")
            data["Date"] = pd.to_datetime(data["Date"])
            if exercise_name == "BodyWeight":
                plt.plot(data["Date"], data["Weight"], marker="s", label=exercise_name)
            else:
                plt.plot(data["Date"], data["Weight"], marker="o", label=exercise_name)
        plt.xlabel("Date")
        plt.ylabel("Weight (kg)")
        plt.title(f"{st.session_state.username} - Weight Progression All Exercises")
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
        plt.gcf().autofmt_xdate(rotation=45)
        st.pyplot(plt.gcf())
