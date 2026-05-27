import pandas as pd
import glob

# 🔍 all csv files load (folder ka naam apne hisab se change kar)
files = glob.glob("dataset/*.csv")

df_list = []

for file in files:
    try:
        temp = pd.read_csv(file)
        df_list.append(temp)
        print(f"Loaded: {file}")
    except:
        print(f"Error in: {file}")

# 🔥 merge all
df = pd.concat(df_list, ignore_index=True)

# CLEAN
df.columns = df.columns.str.strip().str.lower()

# SAVE MASTER FILE
df.to_csv("data.csv", index=False)

print("✅ All CSV merged into data.csv")