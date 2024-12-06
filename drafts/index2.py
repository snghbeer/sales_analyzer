import os
import json
import random
import pandas as pd
import jwt

from flask import Flask, jsonify, request, abort
from pymongo import MongoClient
from bson import json_util

from datetime import datetime, date, timedelta
import calendar
from flask_cors import CORS, cross_origin


from dotenv import load_dotenv
load_dotenv()

sk = os.environ.get('sk')
servertPORT = os.environ.get('PORT')
dbUri = os.environ.get('DB_URI')
dbName = os.environ.get('dbName')
serverHost = os.environ.get('SERVERHOST')

# Create a Flask application instance
app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = sk # Replace with a secure secret key
client = MongoClient(dbUri)
db = client[dbName]

###Middleware
#@app.before_request
def verify_jwt():
    if request.method == 'OPTIONS':
        return
    auth_header = request.headers.get('Authorization')
    if auth_header:
        auth_token = auth_header.split(" ")[1]
    else:
        auth_token = ''
    if auth_token:
        try:
            jwt.decode(auth_token, app.config.get('SECRET_KEY'), algorithms=["HS256"])
            return 
        except jwt.ExpiredSignatureError:
            return jsonify({"message": 'Signature expired. Please log in again.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": 'Invalid token. Please log in again.'}), 401
    else:
        return jsonify({"message": 'Token is missing.'}), 401

@app.after_request
def after_request_middleware(response):
    # Code to be executed after each request
    return response

###
def calculate_dates():
    now = datetime.now()

    # Year
    start_year = datetime(now.year, 1, 1)
    end_year = datetime(now.year, 12, 31)

    # Month
    start_month = datetime(now.year, now.month, 1)
    _, last_day_month = calendar.monthrange(now.year, now.month)
    end_month = datetime(now.year, now.month, last_day_month, 23, 59, 59)  # Set to end of the day

    # Week 
    start_week = now - timedelta(days=now.weekday())
    # Adjust start_week to the beginning of the week (Monday)
    if start_week.weekday() == 6:  # Sunday
        start_week = start_week - timedelta(days=6)

    end_week = start_week + timedelta(days=6)

    return start_year, end_year, start_month, end_month, start_week, end_week

def get_records_of_this_year(start_year, end_year):
    collection = db["records"]
    results = collection.find({"date": {"$gte": start_year, "$lt": end_year}, "confirmed": True})
    data = []
    for result in results:
        result['_id'] = str(result['_id'])
        result['date'] = str(result['date'])
        data.append(result)
        record = result['records']
        for rec in record:
            rec['_id'] = str(rec['_id'])

    return data

def filter_records(records, start_date, end_date):
    return [record for record in records if start_date <= datetime.strptime(record['date'], "%Y-%m-%d %H:%M:%S.%f") < end_date]

###

def generateRandomRecord(products):
    record = {}
    record['records'] = []

    # Generate random number of products (2 to 5)
    num_products = random.randint(2, 5)
    selected_products = random.sample(products, num_products)

    # Generate random amounts for the selected products
    for product in selected_products:
        amount = random.randint(1, 5)
        price = product['price']
        record['records'].append({"product": product['name'], "amount": amount, "price": price})

    # Generate random date from the beginning of this year until now in ISO string format
    start_date = datetime(2022, 7, 21)
    end_date = datetime.now()
    random_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
    record['date'] = random_date.isoformat()

    # Calculate the total based on the records
    total = sum(item['amount'] * item['price'] for item in record['records'])
    record['total'] = round(total*1.21, 2)

    return record

def parse_json(data):
    return json.loads(json_util.dumps(data))

def getProducts():
    collection = db["products"]
    results = collection.find()
    data = []

    for result in results:
        product_name = result['name']
        product_price = result['price']
        product_cat = str(result['category'])
        data.append({'name': product_name, 'price': product_price, 'category': product_cat})

    # Return the data as JSON response
    return parse_json(data)

def getRecords():
    collection = db["records"]
    
    now = datetime.now()

    start_date = datetime(now.year, 1, 1)
    end_date = datetime(now.year, 12, 31)
        
    results = collection.find({"date": {"$gte": start_date, "$lt": end_date}, "confirmed": True})
    
    data = []
    for result in results:
        records = result['records']
        result['_id'] = str(result['_id'])
        result['date'] = str(result['date'])
        for record in records:
            record['_id'] = str(record['_id'])
        data.append(result)    

    return parse_json(data)

def getOrdersOfToday():
    collection = db["records"]
    
    # Get the current date
    today = date.today()
    
    # Set the start and end datetime for today
    start_datetime = datetime.combine(today, datetime.min.time())
    end_datetime = datetime.combine(today, datetime.max.time())
    
    # Create a filter to query records of today
    filter = {
        "date": {
            "$gte": start_datetime,
            "$lte": end_datetime
        }
    }
    
    results = collection.find(filter)
    
    data = []
    for result in results:
        records = result['records']
        for record in records:
            record.pop('_id', None)
        data.append(records)
    
    flattened_data = [item for sublist in data for item in sublist]
    
    # Return the data as JSON response
    return parse_json(flattened_data)

def calculateTopProducts(products, orders):
    allProds = {item["name"].lower(): {"amount": 0, "price": item["price"]} for item in products}
    orderData = [{"amount": item["amount"], "product": item["product"].lower()} for item in orders]

    for item in orderData:
        product = item["product"]
        if product in allProds:
            allProds[product]["amount"] += item["amount"]

    result = [{"product": product, "amount": data["amount"], "price": data["price"]} for product, data in allProds.items()]
    return result

def getTotalSalesToday():
    today = datetime.today().strftime('%Y-%m-%d')
    records = getRecords()
    records_today = [record for record in records if record['date'][:10] == today]
    total_sales = 0.0

    for record in records_today:
        total = record['total']
        vat = round(total * 0.21, 2)
        commision = round(total * 0.0125, 2)
        if record['payment_method'] == 'card':
            # Subtract VAT of 21%
            total -= vat + commision + 0.25

        if record['payment_method'] == 'bancontact':
            # Subtract 0.35 from total
            total -= vat + 0.35

        # Round to 2 decimals
        total = round(total, 2)

        # Add to the total sales
        total_sales += total

    return {"today": total_sales}

##
def getTotalSalesCurrentMonthByWeek(df_current_month):
    today = datetime.today().date()
    start_of_month = today.replace(day=1) 
    end_of_month = today.replace(day=1, month=today.month % 12 + 1) - timedelta(days=1) 

    total_weeks = ((end_of_month - start_of_month).days // 7) + 1

    sales_by_week = [{"week": f"Week {i + 1}", "sales": 0} for i in range(total_weeks)]

    total_sales = 0.0
    for _, record in df_current_month.iterrows():
        total = record['total']

        week = (record['date'].day-1) // 7 + 1
        sales_by_week[week-1]["sales"] += total

        total_sales += total

    return {"sales": sales_by_week, "total": round(total_sales, 2)}

def calculateProductSales(records):
    product_sales = {}
    for record in records:
        for product in record['records']:
            product_id = product['product']
            if product_id not in product_sales:
                product_sales[product_id] = 0
            product_sales[product_id] += product['amount']
    return product_sales

def topSellerPerCat(records, products):

    # create a dictionary to store products grouped by category
    product_sales = calculateProductSales(records)
    grouped_products_info = {}
    for product in products:
        cat_id = product['category']
        if cat_id not in grouped_products_info:
            grouped_products_info[cat_id] = []
        product_info = product.copy()  # create a copy as we don't want to modify the original data
        product_info['total_sold'] = product_sales.get(product['name'], 0)  # get the total sold amount
        grouped_products_info[cat_id].append(product_info)

    # sort the products in each category by 'total_sold' in descending order
    for cat_id, products in grouped_products_info.items():
        sorted_products = sorted(products, key=lambda x: x['total_sold'], reverse=True)
        grouped_products_info[cat_id] = sorted_products
    print(grouped_products_info)

    return {'grouped_products': grouped_products_info}

def topSellers(records, products):
    # initialize the sales with 0 amount for each product
    sales = [{"amount":0, "price":item['price'], "product":item['name'].lower()} for item in products]
    
    # calculate total amount for each product
    for record in records:
        for item in record["records"]:
            for sale in sales:
                if sale["product"] == item["product"].lower():
                    sale["amount"] += item["amount"]
    # sort sales by the amount field in descending order
    sales.sort(key=lambda x: -x["amount"])
    
    return {"sales": sales, "total": sum([item["price"]*item["amount"] for item in sales])}


def getTotalSalesCurrentWeek(df_current_week):
    sales_by_day = [{"day": "Monday", "sales": 0},
                    {"day": "Tuesday", "sales": 0},
                    {"day": "Wednesday", "sales": 0},
                    {"day": "Thursday", "sales": 0},
                    {"day": "Friday", "sales": 0},
                    {"day": "Saturday", "sales": 0},
                    {"day": "Sunday", "sales": 0}]

    total_sales = 0.0

    for _, record in df_current_week.iterrows():
        total = record['total']
        
        day_of_week = record['date'].strftime('%A')
        for item in sales_by_day:
            if item["day"] == day_of_week:
                item["sales"] += total
                break

        total_sales += total

    return {"sales": sales_by_day, "total": round(total_sales, 2)}
### ROUTES ###


#max sales this year
@app.route('/sales_this_year', methods=['GET'])
def getTotalSalesCurrentYear():
    records = getRecords()
    df = pd.DataFrame(records)
    
    df['date'] = pd.to_datetime(df['date'])

    today = pd.Timestamp.today().normalize()
    start_of_year = pd.to_datetime(today.strftime('%Y-01-01'))
    end_of_year = pd.to_datetime(today.strftime('%Y-12-31'))

    df = df[df['date'].between(start_of_year, end_of_year)]

    df['total'] = df['total'].astype(float).round(2)
    df['vat'] = df['total'] * 0.21
    df['commission'] = df['total'] * 0.0125

    df.loc[df['payment_method'] == 'card', 'total'] -= df['vat'] + df['commission'] + 0.25
    df.loc[df['payment_method'] == 'bancontact', 'total'] -= df['vat'] + 0.35

    all_months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    sales_by_month = pd.DataFrame({'month': all_months, 'sales': [0] * 12})

    df['month'] = df['date'].dt.strftime('%B')
    actual_sales_by_month = df.groupby('month')['total'].sum().reset_index()

    sales_by_month.set_index('month', inplace=True)
    for _, row in actual_sales_by_month.iterrows():
        sales_by_month.loc[row['month'], 'sales'] = round(row['total'], 2)
    
    sales_by_month.reset_index(inplace=True)

    total_sales = round(df['total'].sum(), 2)
    
    current_month_df = df[df['date'].dt.month == today.month]
    current_week_df = current_month_df[current_month_df['date'].dt.isocalendar().week == today.isocalendar().week]

    current_month_sales = getTotalSalesCurrentMonthByWeek(current_month_df)
    current_week_sales = getTotalSalesCurrentWeek(current_week_df)

    return {"this_year": {"sales": sales_by_month.to_dict('records'), "total": total_sales},
            "this_month": current_month_sales,
            "this_week": current_week_sales
    }


#topSellers all time per cat
@app.route('/calculate_per_cat', methods=['GET'])
def calculatePerCat():
    products = getProducts()
    collection = db["categories"]
    cats = collection.find()
    data = []

    for result in cats:
        cat_name = result['name']
        cat_id = str(result['_id'])
        data.append({'name': cat_name, '_id': cat_id})
        
    start_year, end_year, start_month, end_month, start_week, end_week = calculate_dates()
    
    records_this_year = get_records_of_this_year(start_year, end_year)
    records_this_month = filter_records(records_this_year, start_month, end_month)
    records_this_week = filter_records(records_this_year, start_week, end_week)

    resY = topSellerPerCat(records_this_year, products)
    resM = topSellerPerCat(records_this_month, products)
    resW = topSellerPerCat(records_this_week, products)
    
    return {
        'categories': data,
        'weekly': resW,
        'monthly': resM,
        'yearly': resY
    }

#topSellers all time
@app.route('/calculate', methods=['GET'])
def calculateSales():
    products = getProducts()
    start_year, end_year, start_month, end_month, start_week, end_week = calculate_dates()
    
    records_this_year = get_records_of_this_year(start_year, end_year)
    records_this_month = filter_records(records_this_year, start_month, end_month)
    records_this_week = filter_records(records_this_year, start_week, end_week)
    
    resY = topSellers(records_this_year, products)
    resM = topSellers(records_this_month, products)
    resW = topSellers(records_this_week, products)

    #return calculateTopProducts(products, orders)
    return {
        'weekly': resW,
        'monthly': resM,
        'yearly': resY
    }

#topSellers of today
@app.route('/calculate_today', methods=['GET'])
def calculateSalesToday():
    products = getProducts()
    orders = getOrdersOfToday()
    salesToday = getTotalSalesToday()
    tot = salesToday['today']
    res = calculateTopProducts(products, orders)
    # Sort the result in descending order based on the "amount" field
    sortedSales = sorted(res, key=lambda x: x["amount"], reverse=True)
    return jsonify({ "total": tot, "sales": sortedSales })

    
# Run the Flask application
#only for development
if __name__ == '__main__':
    print("server is running at port %s" % servertPORT)
    #serve(app, host=serverHost, port=servertPORT)
    app.run(host=serverHost, port=5000)  




