import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Authenticate Google Sheets
creds = ServiceAccountCredentials.from_json_keyfile_name("google_creds.json", SCOPE)
client = gspread.authorize(creds)
sheet = client.open("Fridge Inventory").sheet1

def get_expiring_items():
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    df["Expiry Date"] = pd.to_datetime(df["Expiry Date"], errors='coerce')
    df["Purchase Date"] = pd.to_datetime(df["Purchase Date"], errors='coerce')
    today = datetime.today()
    threshold = today + timedelta(days=2)
    filtered = df[
        (df["Expiry Date"] <= threshold) &
        (df["Remaining Quantity"].notna()) &
        (df["Remaining Quantity"].astype(str).str.strip() != "0")
    ]
    return filtered

def generate_recipe(ingredients_json, num_people, preference):
    prompt = (
        f"I have the following ingredients in my fridge that are expiring soon, each with a remaining quantity:\n{ingredients_json}\n\n"
        f"I want to cook dinner for {num_people} people. "
        f"The meal should be {'vegetarian' if preference == 'veg' else 'non-vegetarian'}. "
        f"Please suggest a healthy and simple recipe using most of these items. "
        f"Include the dish name, list of ingredients (scaled for {num_people} people), and preparation steps."
        f"Include the image as well for the dish for better presentation."
    )
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message["content"]

# Streamlit UI
st.title("🧊 Fridge Recipe Bot")

num_people = st.number_input("How many people are you cooking for?", min_value=1, max_value=20, value=2)
preference = st.selectbox("Do you want a vegetarian or non-vegetarian recipe?", ["veg", "non-veg"])

if st.button("Show Items About to Expire"):
    filtered = get_expiring_items()
    if filtered.empty:
        st.info("No items are expiring in the next 2 days or quantities are zero.")
    else:
        st.write("### Items About to Expire (within 2 days):")
        st.dataframe(filtered)

if st.button("Suggest Dinner Recipe"):
    filtered = get_expiring_items()
    if filtered.empty:
        st.success("✅ No items are expiring in the next 2 days or quantities are zero.")
    else:
        ingredient_list = [
            {"item": row["Item Name"], "quantity": row["Remaining Quantity"]}
            for _, row in filtered.iterrows()
        ]
        ingredients_json = json.dumps(ingredient_list, indent=2)
        recipe = generate_recipe(ingredients_json, num_people, preference)
        st.markdown("### Suggested Recipe:")
        st.write(recipe)
