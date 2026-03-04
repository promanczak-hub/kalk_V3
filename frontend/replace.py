import sys

with open("d:/kalk_v3/frontend/src/CalculatorPanel.tsx", "r", encoding="utf-8") as f:
    text = f.read()

start_marker = "{/* Wizytówka */}"
end_marker = "{/* Parser Modal */}"

start_idx = text.find(start_marker)
end_idx = text.find(end_marker)

if start_idx != -1 and end_idx != -1:
    start_pos = text.rfind("\n", 0, start_idx)
    end_box_idx = text.rfind("</Box>", 0, end_idx)

    new_content = """
        <VehicleDataSection
          data={data}
          expanded={expanded}
          handleChange={handleChange}
          handleUpdate={handleUpdate}
          handleUpdateNetto={handleUpdateNetto}
          handleUpdateBrutto={handleUpdateBrutto}
          handleChangeTypRabatu={handleChangeTypRabatu}
          handleUpdateRabat={handleUpdateRabat}
        />
        <OptionsTablesSection
          data={data}
          handleUpdateFactoryOption={handleUpdateFactoryOption}
          handleAddFactoryOption={handleAddFactoryOption}
          handleRemoveFactoryOption={handleRemoveFactoryOption}
          handleUpdateServiceOption={handleUpdateServiceOption}
          handleAddServiceOption={handleAddServiceOption}
          handleRemoveServiceOption={handleRemoveServiceOption}
        />
        <AdditionalOptionsSection
          data={data}
          handleUpdate={handleUpdate}
        />
        <CalculationSummarySection
          data={data}
          expanded={expanded}
          handleChange={handleChange}
        />
"""
    new_text = text[:start_pos] + new_content + text[end_box_idx:]
    with open(
        "d:/kalk_v3/frontend/src/CalculatorPanel.tsx", "w", encoding="utf-8"
    ) as f:
        f.write(new_text)
    print("REPLACED!")
else:
    print("NOT FOUND", start_idx, end_idx)
