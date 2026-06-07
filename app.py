import streamlit as st
import pandas as pd
import tempfile
import os

# =========================
# MASTER SCHEMA
# =========================
MASTER_COLUMNS = [
    "Date_performed", "Species_System", "Specimen_ID", "Experimental_condition",
    "Length", "Cross_sectional_area", "Second_moment_of_area_I",
    "Force", "Torque", "Stress", "Muscle_force",
    "Strain", "Strain_rate", "Curvature", "Angular_displacement",
    "Elastic_modulus_E", "Flexural_stiffness_EI", "Angular_stiffness", "Damping",
    "Natural_frequency", "Resonance_frequency", "Frequency_response", "Transfer_function",
    "Activation_timing", "Phase", "Duty_cycle", "Length_tension_data", "Force_velocity_data",
    "Work", "Power_output", "Efficiency_energetic_cost",
    "Passive_vs_active_stiffness", "Local_stiffness", "Local_damping",
    "Viscoelastic_decomposition", "Nonlinearity_metrics",
    "Year", "Trial_ID", "Source_File"
]

# =========================
# SIMPLE FUNCTIONS
# =========================

def detect_year(file_name):
    return file_name[:4]

def enforce_schema(df):
    for col in MASTER_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df[MASTER_COLUMNS]

def add_metadata(df, name, year):
    try:
        df["Year"] = int(year)
    except:
        df["Year"] = None

    df["Trial_ID"] = name
    df["Source_File"] = name
    return df

def create_summary(master_df):
    numeric_cols = master_df.select_dtypes(include='number').columns

    summary = master_df.groupby("Specimen_ID").agg({
        **{col: ["mean", "min", "max"] for col in numeric_cols},
        "Specimen_ID": "count"
    })

    summary.columns = ["_".join(col).strip() for col in summary.columns.values]
    summary = summary.rename(columns={"Specimen_ID_count": "Num_Records"})

    return summary.reset_index()

# =========================
# UI
# =========================

st.title("📊 Data Pipeline")

uploaded_files = st.file_uploader(
    "Upload datasets (.xlsx or .h5)",
    type=["xlsx", "h5"],
    accept_multiple_files=True
)

if st.button("Run Pipeline"):

    if not uploaded_files:
        st.error("Upload at least one file.")
        st.stop()

    master_list = []

    for file in uploaded_files:
        try:
            if file.name.endswith(".xlsx"):
                df = pd.read_excel(file)

                year = detect_year(file.name)
                df = enforce_schema(df)
                df = add_metadata(df, file.name, year)

                master_list.append(df)
                st.success(f"Processed {file.name}")

        except Exception as e:
            st.error(f"{file.name} failed: {e}")

    if not master_list:
        st.error("No valid data.")
        st.stop()

    master_df = pd.concat(master_list, ignore_index=True)

    temp_dir = tempfile.mkdtemp()
    excel_path = os.path.join(temp_dir, "output.xlsx")

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:

        master_df.to_excel(writer, sheet_name="Master", index=False)

        grouped = master_df.groupby("Specimen_ID")
        for specimen_id, group_df in grouped:
            name = str(specimen_id)[:31]
            group_df.to_excel(writer, sheet_name=name, index=False)

        summary_df = create_summary(master_df)
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

    st.success("✅ Done!")

    with open(excel_path, "rb") as f:
        st.download_button("Download Excel", f, "result.xlsx")
