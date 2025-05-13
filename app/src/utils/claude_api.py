import anthropic
from openai import OpenAI
#from src.login import db_manager
import pandas as pd
import time
import json
import os
from dotenv import load_dotenv

load_dotenv()



client = OpenAI(
  api_key=os.getenv("GROK_API_KEY"),
  base_url="https://api.x.ai/v1",

)

def timeit(func):
    def wrapper_function(*args, **kwargs):
        t1 = time.time()
        result = func(*args, **kwargs)
        t2 = time.time()
        print(f'Function {func.__name__!r} executed in {(t2-t1):.4f}s')
        return result
    
    return wrapper_function

def get_descriptions_bank_statement(df = None):

    df = pd.read_excel("../account-statement_2023-10-20_2025-04-21.xlsx")

    descriptions = df['Description'].unique()
    print(descriptions)
    with open("categories_temp.txt", 'w') as f: 
        f.write(str(list(descriptions)))

    return descriptions


def get_user_categories(google_id):
    user = db_manager.users_collection.find_one({'google_id': google_id})
    if not user:
        return {"Uncategorised": []}
    
    categories = user.get("categories", {"Uncategorised": []})
    return categories


@timeit
def recategorise_transactions(transaction_descriptions=None, habits=None):
    completion = client.chat.completions.create(
    model="grok-3-mini-fast-beta",
    messages=[
        {"role": "system", "content": f"You are a financial advisor and the user's habits are: {habits}"},
        {"role": "user", "content": f"Based on these descriptions of transactions for a personal bank statement, categorise based on the different types, for example as accomodation or transport; A JSON file should be sent back with no additional text whatsoever to make it easy to be read by my application, so do not add any newlines whatsoever, no slashes, the output should be allowed to be read like this json.dumps(<categories_given_back>). The format needs to be in JSON format such as this: 'Transport: ['uber', 'bolt']; Each category name should be one word long, if there is the option to have a category with 2 words such as Online Marketplaces, write it as so. The JSON dictionary shuold contain all of the categories which were given. The categories can be biased towards what the habits are. These are the transaction descriptions: {transaction_descriptions}" }
    ])
    return completion.choices[0].message.content
    


if __name__ == '__main__':
    #TODO: Uncomment this when it is being run as part of the package
    #transaction_descriptions = get_descriptions_bank_statement(df=None)
    # This is only added as this python file will be run on its own, without being part of a package as there is no output from Grok-Pro-Beta yet
    transaction_descriptions = ['nothing yet']
    print(transaction_descriptions)
    categories = recategorise_transactions(transaction_descriptions=transaction_descriptions, habits="No habits yet")
    print(categories)
    print(type(categories))
    with open("categories_grok_output.json", "w") as f:
        data = json.loads(categories)
        json.dump(data, f, indent=4)