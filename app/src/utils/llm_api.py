from openai import OpenAI
from src.login import db_manager
from src.logger import logger
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

    try:
        #TODO: in the future ammend the prompt to consider whether the user is a higher net worth person or other such factors
        completion = client.chat.completions.create(
        model="grok-3-mini-fast-beta",
        messages=[
            {"role": "system", "content": f"You are a financial advisor and the user's habits are: {habits}; If the habits are unintelligible, don't consider any sort of habits and just consider the average user; " + " You are designed to output JSON with the following schema: `{ [key: string]: string[] }` "},

            {"role": "user", "content": "Based on these descriptions of transactions for a personal bank statement, categorise based on the different types, for example as accomodation or transport; " + 
            " Each category name should be one word long, usually, if there is the option to have a category with 2 words such as 'Online Services', write it as so, not as 'OnlineServices'. " +
            "If unsure of any transaction description google the description to see what it comes up with. " + 
            "Do not add the same the same description to more than one category. " + 
            "The JSON dictionary should contain all of the transaction descriptions which were given, do not exclude anything under any circumstances. The categories can be biased towards what the habits are. " +
            f"These are the transaction descriptions: {transaction_descriptions}" }
        ])

        logger.info("Grok-Mini was used to categorise transaction descriptions")

        result = json.loads(completion.choices[0].message.content)
        return result
    
    except Exception as e:
        logger.error(f"There was an error when using the Grok API Util: {str(e)}")


@timeit
def ammend_transaction_categories(category_keyword_json=None, habits=None):
   
    try:
        #TODO: in the future ammend the prompt to consider whether the user is a higher net worth person or other such factors
        completion = client.chat.completions.create(
        model="grok-3-mini-fast-beta",
        messages=[
            {"role": "system", "content": f"You are a financial advisor and the user's habits are: {habits}; If the habits are unintelligible, don't consider any sort of habits and just consider the average user; " + " You are designed to output JSON with the following schema: `{ [key: string]: string[] }` "},

            {"role": "user", "content": f"Based on these categories and keywords that are created for the user, from a bank statement, ammend them and try to minimise the number of keywords that are in the Uncategorised section: {category_keyword_json}" +
            "Format is: '{ [key: string]: string[] }'"}
        ])

        logger.info("Grok-Mini was used to ammend the categories and keywords of transaction descriptions")

        result = json.loads(completion.choices[0].message.content)
        return result
    
    except Exception as e:
        logger.error(f"There was an error when using the Grok API Util: {str(e)}")

    


if __name__ == '__main__':
    #TODO: Uncomment this when it is being run as part of the package
    #transaction_descriptions = get_descriptions_bank_statement(df=None)
    # This is only added as this python file will be run on its own, without being part of a package as there is no output from Grok-Pro-Beta yet
    transaction_descriptions = ['nothing yet']
    
    categories = recategorise_transactions(transaction_descriptions=transaction_descriptions, habits="No habits yet")
    with open("categories_grok_output.json", "w") as f:
        data = json.loads(categories)
        json.dump(data, f, indent=4)