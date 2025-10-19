#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os
import psutil

# --------- Setup ---------
st.set_page_config(page_title="🏋️ Gym Tracker", layout="wide")

# Store all data inside the repo folder
BASE_FOLDER = os.path.join(os.getcwd(), "user_folders")
os.makedirs(BASE_FOLDER, exist_ok=True)

# --------- User selection ---------
users = [f for f in os.listdir(BASE_FOLDER) if os.path.isdir(os.path.join(BASE_FOLDER, f))]
selected_user = st.sidebar.selectbox("Select User", users)

# If user folder doesn't exist yet, create it
user_folder = os.path.join(BASE_FOLDER, selected_user) if selected_user else None
if user_folder:
    os.makedirs(user_folder, exist_ok=True)
csv_file = os.path.join(user_folder, "workouts.csv") if user_folder else None


# --------- Delete User ---------
st.sidebar.markdown("---")
st.sidebar.header("Delete User")
if selected_user:
    if st.sidebar.button(f"🗑️ Delete {selected_user}"):
        confirm = st.sidebar.checkbox(f"Confirm delete {selected_user}? This cannot be undone.")
        if confirm:
            user_path = os.path.join(BASE_FOLDER, selected_user)
            if os.path.exists(user_path):
                import shutil
                shutil.rmtree(user_path)
                st.sidebar.success(f"Deleted user {selected_user}!")
                # Update sidebar
                users = [f for f in os.listdir(BASE_FOLDER) if os.path.isdir(os.path.join(BASE_FOLDER, f))]
                if users:
                    selected_user = users[0]
                else:
                    selected_user = None
            else:
                st.sidebar.error("User folder not found.")


# --------- Load data ---------
if csv_file and os.path.exists(csv_file):
    df = pd.read_csv(csv_file)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date", "Weight", "Reps"])
else:
    df = pd.DataFrame(columns=["Date", "Exercise", "Weight", "Reps"])

# --------- Add new workout ---------
st.sidebar.header("Log Workout")
date = st.sidebar.date_input("Date", datetime.now())

# Dropdown for existing exercises + option to type new
existing_exercises = df["Exercise"].unique().tolist()
exercise = st.sidebar.selectbox("Exercise (select or type new)", existing_exercises + ["Add new exercise"])
if exercise == "Add new exercise":
    exercise = st.sidebar.text_input("New Exercise Name", "")

weight = st.sidebar.number_input("Weight (kg)", min_value=0.0, step=0.5)
reps = st.sidebar.number_input("Reps", min_value=0, step=1)

if st.sidebar.button("💾 Save Workout") and selected_user:
    if exercise:
        new_row = pd.DataFrame([[date, exercise, weight, reps]],
                               columns=["Date", "Exercise", "Weight", "Reps"])
        df = pd.concat([df, new_row]).drop_duplicates(subset=["Date", "Exercise"], keep="last")
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date", "Weight", "Reps"])
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
        df.to_csv(csv_file, index=False)
        st.sidebar.success(f"Saved {exercise} for {selected_user}!")
    else:
        st.sidebar.error("Exercise name cannot be empty.")

# --------- Exercise filter ---------
exercise_list = df["Exercise"].unique().tolist()
selected_exercises = st.multiselect("Select Exercises to Plot", exercise_list, default=exercise_list)

# --------- Individual exercise charts ---------
if selected_user:
    st.header(f"{selected_user} - Workout Progress")
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

        ax1.set_title(f"{selected_user} - {exercise_name}")
        st.pyplot(fig)

# --------- BodyWeight chart ---------
if "BodyWeight" in df["Exercise"].unique():
    bw_data = df[df["Exercise"] == "BodyWeight"].sort_values("Date")
    if not bw_data.empty:
        bw_data["Date"] = pd.to_datetime(bw_data["Date"])
        st.header(f"{selected_user} - BodyWeight Progress")

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(bw_data["Date"], bw_data["Weight"], marker="s", color="tab:green")
        ax.set_xlabel("Date")
        ax.set_ylabel("Weight (kg)")
        ax.set_title(f"{selected_user} - BodyWeight")
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        fig.autofmt_xdate(rotation=45)
        st.pyplot(fig)

# --------- Combined chart ---------
if not df.empty:
    st.header(f"{selected_user} - All Exercises Combined")
    plt.figure(figsize=(10, 5))
    for exercise_name, data in df.groupby("Exercise"):
        data = data.sort_values("Date")
        data["Date"] = pd.to_datetime(data["Date"])
        marker = "s" if exercise_name == "BodyWeight" else "o"
        plt.plot(data["Date"], data["Weight"], marker=marker, label=exercise_name)
    plt.xlabel("Date")
    plt.ylabel("Weight (kg)")
    plt.title(f"{selected_user} - Weight Progression All Exercises")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
    plt.gcf().autofmt_xdate(rotation=45)
    st.pyplot(plt.gcf())
