with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
    
    # ✅ Master sheet
    master_df.to_excel(writer, sheet_name="Master", index=False)

    # ✅ Specimen sheets
    grouped = master_df.groupby("Specimen_ID")

    for specimen_id, group_df in grouped:

        if pd.isna(specimen_id):
            sheet_name = "Unknown_Specimen"
        else:
            sheet_name = str(specimen_id)

        sheet_name = sheet_name.replace("/", "_")[:30]

        group_df.to_excel(writer, sheet_name=sheet_name, index=False)

    # ✅ NEW: Summary sheet
    summary_df = create_summary(master_df)
    summary_df.to_excel(writer, sheet_name="Summary", index=False)