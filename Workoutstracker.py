import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
from datetime import datetime
import json
import hashlib

# --- CONFIG ---
BASE_FOLDER = os.path.join(os.getcwd(), "user_folders")  # where all user data will be stored
os.makedirs(BASE_FOLDER, exist_ok=True)
USER_DB_FILE = os.path.join(BASE_FOLDER, "users.json")  # store usernames + hashed passwords
st.set_page_config(page_title="🏋️ Gym Tracker", layout="wide")

# --- HELPER FUNCTIONS ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_DB_FILE, "w") as f:
        json.dump(users, f)

def get_user_csv(username):
    user_path = os.path.join(BASE_FOLDER, username)
    os.makedirs(user_path, exist_ok=True)
    return os.path.join(user_path, "workouts.csv")

# --- LOAD USERS ---
users = load_users()

# --- APP SELECTION ---
st.title("🏋️ Gym Tracker")
choice = st.sidebar.radio("Choose Action", ["Login", "Create Account"])

# --- CREATE ACCOUNT ---
if choice == "Create Account":
    st.subheader("Create New Account")
    new_username = st.text_input("Username")
    new_password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    if st.button("Create Account"):
        if not new_username or not new_password:
            st.error("Username and password cannot be empty")
        elif new_username in users:
            st.error("Username already exists")
        elif new_password != confirm_password:
            st.error("Passwords do not match")
        else:
            users[new_username] = hash_password(new_password)
            save_users(users)
            # Create user's folder and empty CSV
            csv_file = get_user_csv(new_username)
            if not os.path.exists(csv_file):
                pd.DataFrame(columns=["Date", "Exercise", "Weight", "Reps"]).to_csv(csv_file, index=False)
            st.success(f"Account created for {new_username}! You can now login.")

# --- LOGIN ---
elif choice == "Login":
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in users and users[username] == hash_password(password):
            st.success(f"Welcome {username}!")

            # --- LOAD USER DATA ---
            csv_file = get_user_csv(username)
            if os.path.exists(csv_file):
                df = pd.read_csv(csv_file)
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                df = df.dropna(subset=["Date", "Weight", "Reps"])
            else:
                df = pd.DataFrame(columns=["Date", "Exercise", "Weight", "Reps"])

            # --- LOG WORKOUT ---
            st.sidebar.header("Log Workout")
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
                    df = pd.concat([df, new_row]).drop_duplicates(subset=["Date", "Exercise"], keep="last")
                    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                    df = df.dropna(subset=["Date", "Weight", "Reps"])
                    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
                    df.to_csv(csv_file, index=False)
                    st.sidebar.success(f"Saved {exercise}!")
                else:
                    st.sidebar.error("Exercise name cannot be empty.")

            # --- SELECT EXERCISES TO PLOT ---
            exercise_list = df["Exercise"].unique().tolist()
            selected_exercises = st.multiselect("Select Exercises to Plot", exercise_list, default=exercise_list)

            # --- INDIVIDUAL EXERCISE CHARTS ---
            st.header(f"{username} - Workout Progress")
            for exercise_name in selected_exercises:
                data = df[df["Exercise"] == exercise_name].sort_values("Date")
                if data.empty:
                    continue
                data["Date"] = pd.to_datetime(data["Date"])
                fig, ax1 = plt.subplots(figsize=(8, 4))
                ax1.plot(data["Date"], data["Weight"], marker="o", color="tab:blue", label="Weight")
                ax1.set_xlabel("Date")
                ax1.set_ylabel("Weight (kg)", color="tab:blue")
                ax1.tick_params(axis="y", labelcolor="tab:blue")
                ax1.grid(True, linestyle="--", alpha=0.6)

                ax2 = ax1.twinx()
                ax2.plot(data["Date"], data["Reps"], marker="x", linestyle="--", color="tab:red", label="Reps")
                ax2.set_ylabel("Reps", color="tab:red")
                ax2.tick_params(axis="y", labelcolor="tab:red")

                ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
                ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
                fig.autofmt_xdate(rotation=45)
                ax1.set_title(f"{username} - {exercise_name}")
                st.pyplot(fig)

            # --- BODYWEIGHT CHART ---
            if "BodyWeight" in df["Exercise"].unique():
                bw_data = df[df["Exercise"] == "BodyWeight"].sort_values("Date")
                if not bw_data.empty:
                    bw_data["Date"] = pd.to_datetime(bw_data["Date"])
                    st.header(f"{username} - BodyWeight Progress")
                    fig, ax = plt.subplots(figsize=(8, 4))
                    ax.plot(bw_data["Date"], bw_data["Weight"], marker="s", color="tab:green")
                    ax.set_xlabel("Date")
                    ax.set_ylabel("Weight (kg)")
                    ax.set_title(f"{username} - BodyWeight")
                    ax.grid(True, linestyle="--", alpha=0.6)
                    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
                    fig.autofmt_xdate(rotation=45)
                    st.pyplot(fig)

            # --- COMBINED CHART ---
            if not df.empty:
                st.header(f"{username} - All Exercises Combined")
                plt.figure(figsize=(10, 5))
                for exercise_name, data in df.groupby("Exercise"):
                    data = data.sort_values("Date")
                    data["Date"] = pd.to_datetime(data["Date"])
                    marker = "s" if exercise_name == "BodyWeight" else "o"
                    plt.plot(data["Date"], data["Weight"], marker=marker, label=exercise_name)
                plt.xlabel("Date")
                plt.ylabel("Weight (kg)")
                plt.title(f"{username} - Weight Progression All Exercises")
                plt.grid(True, linestyle="--", alpha=0.6)
                plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
                plt.gcf().autofmt_xdate(rotation=45)
                st.pyplot(plt.gcf())
        else:
            st.error("Invalid username or password.")
