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
    "Trial_ID", "Source_File"
]

# =========================
# MAPPINGS (EDIT LATER)
# =========================
MAPPINGS = {
    "2013": {}  # we'll customize after preview
}

# =========================
# FUNCTIONS
# =========================

def detect_year(file_name):
    return file_name[:4]

def apply_mapping(df, year):
    return df.rename(columns=MAPPINGS.get(year, {}))

def enforce_schema(df):
    for col in MASTER_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df[MASTER_COLUMNS]

# ✅ UPDATED: DATE HANDLING
def add_metadata(df, source_name, year):

    possible_date_cols = [
        "Date",
        "date",
        "Date_performed",
        "experiment_date",
        "timestamp"
    ]

    date_found = None

    for col in possible_date_cols:
        if col in df.columns:
            date_found = col
            break

    if date_found:
        df["Date_performed"] = df[date_found]
    else:
        df["Date_performed"] = f"{year}-01-01"

    df["Trial_ID"] = source_name
    df["Source_File"] = source_name

    return df

def create_summary(master_df):

    numeric_cols = master_df.select_dtypes(include='number').columns

    if len(numeric_cols) == 0:
        return pd.DataFrame()

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

st.title("📊 Data Standardization Pipeline")

uploaded_files = st.file_uploader(
    "Upload datasets (.xlsx or .h5)",
    type=["xlsx", "h5"],
    accept_multiple_files=True
)

if st.button("Run Pipeline"):

    if not uploaded_files:
        st.error("Please upload at least one file.")
        st.stop()

    master_list = []

    # =========================
    # PROCESS FILES
    # =========================
    for file in uploaded_files:
        try:
            st.write(f"📂 Processing: {file.name}")

            # -------------------------
            # EXCEL
            # -------------------------
            if file.name.endswith(".xlsx"):

                df = pd.read_excel(file)
                st.dataframe(df.head())

                year = detect_year(file.name)
                df = apply_mapping(df, year)
                df = add_metadata(df, file.name, year)
                df = enforce_schema(df)

                master_list.append(df)
                st.success(f"✅ Processed Excel: {file.name}")

            # -------------------------
            # HDF5 ✅
            # -------------------------
            elif file.name.endswith(".h5"):

                with pd.HDFStore(file, mode="r") as store:
                    keys = store.keys()

                    if not keys:
                        st.warning(f"{file.name} has no datasets")
                        continue

                    for key in keys:
                        df = store.get(key)

                        st.write(f"Dataset: {key}")
                        st.dataframe(df.head())

                        year = detect_year(file.name)
                        source_name = f"{file.name}_{key}"

                        df = apply_mapping(df, year)
                        df = add_metadata(df, source_name, year)
                        df = enforce_schema(df)

                        master_list.append(df)

                st.success(f"✅ Processed HDF5: {file.name}")

            else:
                st.warning(f"Skipped file type: {file.name}")

        except Exception as e:
            st.error(f"{file.name} failed: {e}")

    # =========================
    # COMBINE DATA
    # =========================
    if not master_list:
        st.error("No valid data.")
        st.stop()

    master_df = pd.concat(master_list, ignore_index=True)

    # =========================
    # SAVE OUTPUT
    # =========================
    temp_dir = tempfile.mkdtemp()
    excel_path = os.path.join(temp_dir, "master_dataset.xlsx")

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:

        # ✅ MASTER
        master_df.to_excel(writer, sheet_name="Master", index=False)

        # ✅ GROUP BY SPECIMEN
        grouped = master_df.groupby("Specimen_ID")

        for specimen_id, group_df in grouped:

            if pd.isna(specimen_id):
                sheet_name = "Unknown_Specimen"
            else:
                sheet_name = str(specimen_id)

            sheet_name = sheet_name.replace("/", "_")[:31]

            group_df.to_excel(writer, sheet_name=sheet_name, index=False)

        # ✅ SUMMARY
        summary_df = create_summary(master_df)
        if not summary_df.empty:
            summary_df.to_excel(writer, sheet_name="Summary", index=False)

    st.success("🎉 Pipeline completed!")

    with open(excel_path, "rb") as f:
        st.download_button("⬇️ Download Excel", f, "master_dataset.xlsx")
