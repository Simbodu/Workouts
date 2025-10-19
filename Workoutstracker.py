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

def create_account(username, password, password_confirm):
    if username in st.session_state.users:
        st.error("User already exists.")
        return False
    if password != password_confirm:
        st.error("Password must match.")
        return False
    st.session_state.users[username] = hash_password(password)
    save_users()
    os.makedirs(os.path.join(BASE_FOLDER, username), exist_ok=True)
    st.success("Account created! Please log in.")
    return True

def login_user(username, password):
    if username not in st.session_state.users:
        st.error("User does not exist.")
        return False
    if st.session_state.users[username] != hash_password(password):
        st.error("Incorrect password.")
        return False
    st.session_state.logged_in = True
    st.session_state.username = username
    st.success(f"Logged in as {username}. Please click again to enter.")
    return True

def logout_user():
    st.session_state.logged_in = False
    st.session_state.username = ""

def delete_account(username, password):
    users = st.session_state.users

    # Verify account exists and password matches
    if username not in users:
        st.error("User does not exist.")
        return False
    if users[username] != hash_password(password):
        st.error("Incorrect password.")
        return False

    # Delete user's folder
    user_folder = os.path.join(BASE_FOLDER, username)
    if os.path.exists(user_folder):
        import shutil
        shutil.rmtree(user_folder)

    # Remove user from the list
    del users[username]
    save_users()

    # Log user out
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.success("Your account has been deleted.")
    st.rerun()
    return True

# --------- Login / Create Account ---------
if not st.session_state.logged_in:
    st.sidebar.header("🔑 Login or Create Account")
    action = st.sidebar.radio("Action", ["Login", "Create Account"])

    username_input = st.sidebar.text_input("Username")
    password_input = st.sidebar.text_input("Password", type="password")
    if action == "Create Account":
        password_confirm = st.sidebar.text_input("Confirm Password", type="password")

    if action == "Login" and st.sidebar.button("Login"):
        login_user(username_input, password_input)

    if action == "Create Account" and st.sidebar.button("Create"):
        create_account(username_input, password_input, password_confirm)

# --------- Main App ---------
else:
    st.sidebar.write(f"👤 Logged in as: {st.session_state.username}")
    if st.sidebar.button("Logout"):
        logout_user()

    with st.sidebar.expander("⚠️ Delete Account"):
        st.warning("This will permanently delete your account and all data.")
        confirm_password = st.text_input("Confirm Password", type="password", key="delete_pwd")
        if st.button("Delete My Account"):
            delete_account(st.session_state.username, confirm_password)
    
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

    # --------- Edit Past Entries ---------
    st.sidebar.header("✏️ Edit Past Entries")
    
    if df.empty:
        st.sidebar.info("No workouts to edit yet.")
    else:
        # Pick a workout to edit
        df_sorted = df.sort_values("Date", ascending=False).reset_index(drop=True)
        display_options = [f"{row['Date']} - {row['Exercise']} ({row['Weight']}kg x {row['Reps']})" for _, row in df_sorted.iterrows()]
        selected_index = st.sidebar.selectbox("Select entry to edit", range(len(display_options)), format_func=lambda i: display_options[i])
    
        # Show editable fields
        selected_row = df_sorted.iloc[selected_index]
        edit_date = st.sidebar.date_input("Date", pd.to_datetime(selected_row["Date"]))
        edit_exercise = st.sidebar.text_input("Exercise", selected_row["Exercise"])
        edit_weight = st.sidebar.number_input("Weight (kg)", value=float(selected_row["Weight"]), step=0.5)
        edit_reps = st.sidebar.number_input("Reps", value=int(selected_row["Reps"]), step=1)
    
        if st.sidebar.button("💾 Save Changes"):
            df.loc[
                (df["Date"] == selected_row["Date"]) &
                (df["Exercise"] == selected_row["Exercise"]),
                ["Date", "Exercise", "Weight", "Reps"]
            ] = [edit_date, edit_exercise, edit_weight, edit_reps]
    
            df.to_csv(csv_file, index=False)
            st.sidebar.success("Workout updated!")
            st.rerun()

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
