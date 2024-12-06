import os
import json
import random
import pandas as pd

from flask import Flask, jsonify
from pymongo import MongoClient
from bson import json_util

from datetime import datetime, date, timedelta
import calendar
import time

from flask_cors import CORS


from dotenv import load_dotenv
load_dotenv()


# Create a Flask application instance
app = Flask(__name__)
CORS(app)

servertPORT = os.environ.get('PORT')
dbUri = os.environ.get('DB_URI')
dbName = os.environ.get('dbName')
serverHost = os.environ.get('SERVERHOST')
client = MongoClient(dbUri)
db = client[dbName]



def calculate_dates():
    now = datetime.now()

    # Year
    start_year = datetime(now.year, 1, 1)
    end_year = datetime(now.year, 12, 31)

    # Month
    start_month = datetime(now.year, now.month, 1)
    _, last_day_month = calendar.monthrange(now.year, now.month)
    end_month = datetime(now.year, now.month, last_day_month)

    # Week 
    start_week = now - timedelta(days=now.weekday())
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
    results = collection.find({"confirmed": True})
    data = []
    for result in results:
        result['_id'] = str(result['_id'])
        result['date'] = str(result['date'])
        data.append(result)
        records = result['records']
        for record in records:
            record['_id'] = str(record['_id'])

    # Return the data as JSON response
    return parse_json(data)

def getRecordsOfThisWeek():
    collection = db["records"]
    
    # Get the current date
    now = datetime.now()

    # Get the start date of the current week (Monday)
    start_date = now - timedelta(days=now.weekday())

    # Get the end date of the current week (Sunday)
    end_date = start_date + timedelta(days=6)
    
    # Query for records in the current week
    results = collection.find({"date": {"$gte": start_date, "$lt": end_date}, "confirmed": True})
    
    data = []
    for result in results:
        result['_id'] = str(result['_id'])
        result['date'] = str(result['date'])
        data.append(result)
        records = result['records']
        for record in records:
            record['_id'] = str(record['_id'])

    # Return the data as JSON response
    return parse_json(data)

def getRecordsOfThisMonth():
    collection = db["records"]
    
    # Get the current date
    now = datetime.now()

    # Get the first day of the current month
    start_date = datetime(now.year, now.month, 1)

    # Get the last day of the current month
    _, last_day_month = calendar.monthrange(now.year, now.month)
    end_date = datetime(now.year, now.month, last_day_month)
        
    # Query for records in the current month
    results = collection.find({"date": {"$gte": start_date, "$lt": end_date}, "confirmed": True})
    
    data = []
    for result in results:
        records = result['records']
        result['_id'] = str(result['_id'])
        result['date'] = str(result['date'])
        for record in records:
            record['_id'] = str(record['_id'])
        data.append(result)    

    # Return the data as JSON response
    return parse_json(data)

def getRecordsOfThisYear():
    collection = db["records"]
    
    # Get the current date
    now = datetime.now()

    # Get the first day of the current year
    start_date = datetime(now.year, 1, 1)

    # Get the last day of the current year
    end_date = datetime(now.year, 12, 31)
    
    # Query for records in the current year
    results = collection.find({"date": {"$gte": start_date, "$lt": end_date}, "confirmed": True})
    
    data = []
    for result in results:
        result['_id'] = str(result['_id'])
        result['date'] = str(result['date'])
        data.append(result)
        records = result['records']
        for record in records:
            record['_id'] = str(record['_id'])

    # Return the data as JSON response
    return parse_json(data)

def getSales():
    collection = db["records"]

    pipeline = [
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$date"}}, "total": {"$sum": "$total"}}},
        {"$project": {"_id": 0, "date": "$_id", "total": 1}}
    ]

    sales_per_day = list(collection.aggregate(pipeline))

    return sales_per_day

def getTotalSalesByMonth():
    sales_per_day = getSales()
    sales_per_month = {}

    for sale in sales_per_day:
        date = datetime.strptime(sale['date'], '%Y-%m-%d')
        month_year = date.strftime('%Y-%m')
        total = sale['total']

        if month_year in sales_per_month:
            sales_per_month[month_year] += total
        else:
            sales_per_month[month_year] = total

    return sales_per_month

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

def getOrdersOfThisWeek():
    collection = db["records"]
    
    # Get the current date
    today = date.today()
    
    # Calculate the start and end dates for this week
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Set the start and end datetimes for this week
    start_datetime = datetime.combine(start_of_week, datetime.min.time())
    end_datetime = datetime.combine(end_of_week, datetime.max.time())
    
    # Create a filter to query records for this week
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

def getOrdersOfThisMonth():
    collection = db["records"]
    
    # Get the current date
    today = date.today()
    
    # Set the start and end datetimes for this month
    start_datetime = datetime(today.year, today.month, 1)
    end_datetime = datetime(today.year, today.month + 1, 1)
    
    # Create a filter to query records for this month
    filter = {
        "date": {
            "$gte": start_datetime,
            "$lt": end_datetime
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

def getOrdersOfThisYear():
    collection = db["records"]
    
    # Get the current date
    today = date.today()
    
    # Set the start and end datetimes for this year
    start_datetime = datetime(today.year, 1, 1)
    end_datetime = datetime(today.year + 1, 1, 1)
    
    # Create a filter to query records for this year
    filter = {
        "date": {
            "$gte": start_datetime,
            "$lt": end_datetime
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

def getOrders():
    collection = db["records"]
    results = collection.find({'confirmed': True})
    data = []
    for result in results:
        records = result['records']
        for record in records:
            record.pop('_id', None)
        data.append(records)
    flattened_data = [item for sublist in data for item in sublist]
    print(flattened_data)
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
def getTotalSalesCurrentMonthByWeek():
    today = datetime.today().date()
    start_of_month = today.replace(day=1)  # First day of the current month
    end_of_month = today.replace(day=1, month=today.month % 12 + 1) - timedelta(days=1)  # Last day of the current month
    records = getRecordsOfThisMonth()

    # Calculate the total number of weeks for the current month
    total_weeks = ((end_of_month - start_of_month).days // 7) + 1

    # Initialize the sales for each week
    sales_by_week = [{"week": f"Week {i + 1}", "sales": 0} for i in range(total_weeks)]

    total_sales = 0.0

    for record in records:
        record_date = datetime.strptime(record['date'][:10], '%Y-%m-%d').date()

        # Check if the record's date falls within the current month
        if start_of_month <= record_date <= end_of_month:
            total = record['total']
            vat = round(total * 0.21, 2)
            commision = round(total * 0.0125, 2)

            if record['payment_method'] == 'card':
                # Subtract VAT of 21%, commission of 1.25%, and 0.25
                total -= vat + commision + 0.25

            elif record['payment_method'] == 'bancontact':
                # Subtract VAT of 21% and 0.35
                total -= vat + 0.35

            # Round to 2 decimals
            total = round(total, 2)

            # Determine the week to which the record belongs
            for i, week_start in enumerate([start_of_month + timedelta(weeks=i) for i in range(total_weeks)]):
                week_end = week_start + timedelta(weeks=1) - timedelta(days=1)
                if week_start <= record_date <= week_end:
                    sales_by_week[i]["sales"] += total
                    break

            # Add to the total sales for the month
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

def topSellerPerCat(records, cats):
    products = getProducts()

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

    return {'grouped_products': grouped_products_info}


### ROUTES ###

# Define a route and view function
""" @app.route('/genRandom', methods=['GET'])
def testGen():
    products = getProducts()
    dataset = [generateRandomRecord(products) for _ in range(200000)]

    # Save the dataset to a file in JSON format as an array of objects
    with open("orders.json", "w") as file:
        json.dump(dataset, file, indent=2)
        
    return "Finished generating!"
 """

#max sales all time
@app.route('/sales_today', methods=['GET'])
def salesToday():
    sales = getTotalSalesToday()
    return jsonify(sales)

#max sales this week
@app.route('/sales_this_week', methods=['GET'])
def getTotalSalesCurrentWeek():
    today = datetime.today().date()
    start_of_week = today - timedelta(days=today.weekday())  # Monday of the current week
    end_of_week = start_of_week + timedelta(days=7)  # Sunday of the current week
    records = getRecordsOfThisMonth()

    # Initialize the sales for each day of the week to 0
    sales_by_day = [
        {"day": "Monday", "sales": 0},
        {"day": "Tuesday", "sales": 0},
        {"day": "Wednesday", "sales": 0},
        {"day": "Thursday", "sales": 0},
        {"day": "Friday", "sales": 0},
        {"day": "Saturday", "sales": 0},
        {"day": "Sunday", "sales": 0}
    ]

    total_sales = 0.0

    for record in records:
        record_date = datetime.strptime(record['date'][:10], '%Y-%m-%d').date()

        # Check if the record's date falls within the current week
        if start_of_week <= record_date < end_of_week:
            total = record['total']
            vat = round(total * 0.21, 2)
            commision = round(total * 0.0125, 2)

            if record['payment_method'] == 'card':
                # Subtract VAT of 21%, commission of 1.25%, and 0.25
                total -= vat + commision + 0.25

            elif record['payment_method'] == 'bancontact':
                # Subtract VAT of 21% and 0.35
                total -= vat + 0.35

            # Round to 2 decimals
            total = round(total, 2)

            # Add to the sales for the respective day of the week
            day_of_week = record_date.strftime('%A')
            for item in sales_by_day:
                if item["day"] == day_of_week:
                    item["sales"] += total
                    break

            # Add to the total sales for the week
            total_sales += total

    return {"sales": sales_by_day, "total": round(total_sales, 2)}

#max sales this month
@app.route('/sales_this_month', methods=['GET'])
def totalSalesCurrentMonthByWeek():
    result = getTotalSalesCurrentMonthByWeek()
    return result

#max sales this year
@app.route('/sales_this_year', methods=['GET'])
def getTotalSalesCurrentYear():
    currentMonthSales = getTotalSalesCurrentMonthByWeek()
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

    # Initialize a DataFrame which includes all months with initial sales value as 0
    all_months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    sales_by_month = pd.DataFrame({'month': all_months, 'sales': [0] * 12})

    df['month'] = df['date'].dt.strftime('%B')
    actual_sales_by_month = df.groupby('month')['total'].sum().reset_index()

    # Update sales in the sales_by_month DataFrame with the actual sales
    sales_by_month.set_index('month', inplace=True)
    for _, row in actual_sales_by_month.iterrows():
        sales_by_month.loc[row['month'], 'sales'] = round(row['total'], 2)
    
    # Reset the index to convert the month back into a column
    sales_by_month.reset_index(inplace=True)

    # Calculate total sales for the year
    total_sales = round(df['total'].sum(), 2)

    # Calculate total sales for the current month
    df_current_month = df[df['date'].dt.month == today.month]
    total_month = round(df_current_month['total'].sum(), 2)
    
    return {"this_year": {"sales": sales_by_month.to_dict('records'), "total": total_sales}, "this_month": currentMonthSales }#total_month}

#max sales this all time random
@app.route('/sales_random', methods=['GET'])
def salesRandom():
    df = pd.read_json('orders.json')
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    df['total'] = df['total'].round(2)
    
    sales_per_day = df.groupby('date')['total'].sum().reset_index()
    sales_per_day['total'] = sales_per_day['total'].map("{:.2f}".format)
    
    return sales_per_day.to_dict('records')

@app.route('/sales_random_year', methods=['GET'])
def salesRandThisYear():
    start_time = time.time()  # Record the start time

    df = pd.read_json('orders.json')
    df['date'] = pd.to_datetime(df['date'])
    df['total'] = df['total'].astype(float).round(2)

    # Use pd.Grouper for efficient grouping by month
    sales_per_month = df.groupby(pd.Grouper(key='date', freq='M'))['total'].sum().reset_index()
    sales_per_month['date'] = sales_per_month['date'].dt.strftime('%Y-%m')
    sales_per_month['total'] = sales_per_month['total'].map("{:.2f}".format)
    sales_per_month.columns = ['month', 'total']

    # Loop over the months and fill missing months with total 0
    current_year = pd.Timestamp.now().year
    all_months = [f'{current_year}-{month:02}' for month in range(1, 13)]

    sales_per_year_filled = []
    for month in all_months:
        if month not in sales_per_month['month'].values:
            sales_per_year_filled.append({'month': month, 'total': '0.00'})
        else:
            row = sales_per_month[sales_per_month['month'] == month].iloc[0]
            sales_per_year_filled.append({'month': row['month'], 'total': row['total']})

    end_time = time.time()  # Record the end time
    time_to_process = end_time - start_time  # Calculate the time taken to process the data

    return {"sales": sales_per_year_filled, "time_to_process": time_to_process}

#top seller all time per category
@app.route('/calculate_per_category', methods=['GET'])
def calcPerCat():
    collection = db["categories"]
    products = getProducts()
    records = getRecords()
    cats = collection.find()
    data = []

    for result in cats:
        cat_name = result['name']
        cat_id = str(result['_id'])
        data.append({'name': cat_name, '_id': cat_id})

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

    return {'categories': data, 'grouped_products': grouped_products_info}

@app.route('/calculate_per_category_w', methods=['GET'])
def calcPerCatW():
    collection = db["categories"]
    products = getProducts()
    records = getRecordsOfThisWeek()
    cats = collection.find()
    data = []

    for result in cats:
        cat_name = result['name']
        cat_id = str(result['_id'])
        data.append({'name': cat_name, '_id': cat_id})

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

    return {'categories': data, 'grouped_products': grouped_products_info}

@app.route('/calculate_per_category_m', methods=['GET'])
def calcPerCatM():
    collection = db["categories"]
    products = getProducts()
    records = getRecordsOfThisMonth()
    cats = collection.find()
    data = []

    for result in cats:
        cat_name = result['name']
        cat_id = str(result['_id'])
        data.append({'name': cat_name, '_id': cat_id})

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

    return {'categories': data, 'grouped_products': grouped_products_info}

@app.route('/calculate_per_category_y', methods=['GET'])
def calcPerCatY():
    collection = db["categories"]
    products = getProducts()
    records = getRecordsOfThisYear()
    cats = collection.find()
    data = []

    for result in cats:
        cat_name = result['name']
        cat_id = str(result['_id'])
        data.append({'name': cat_name, '_id': cat_id})

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

    return {'categories': data, 'grouped_products': grouped_products_info}


#topSellers all time per cat
@app.route('/calculate_per_cat', methods=['GET'])
def calculatePerCat():
    """     yearly = getRecordsOfThisYear()
    monthly = getRecordsOfThisMonth()
    weekly  = getRecordsOfThisWeek() """
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

    resY = topSellerPerCat(records_this_year, data)
    resM = topSellerPerCat(records_this_month, data)
    resW = topSellerPerCat(records_this_week, data)
    
    return {
        'categories': data,
        'weekly': resW,
        'monthly': resM,
        'yearly': resY
    }

#topSellers all time random
""" @app.route('/calculate_random', methods=['GET'])
def calculateRandom():
    products = getProducts()
    orders = getOrders()
    monthly = getOrdersOfThisMonth()
    weekly  = getOrdersOfThisWeek()
    yearly = getOrdersOfThisYear()
    resW = calculateTopProducts(products, weekly)
    resM = calculateTopProducts(products, monthly)
    resY = calculateTopProducts(products, yearly)

    with open('orders.json', 'r') as file:
        records = json.load(file)

    data = []
    for record in records:
        orders = record['records']
        for order in orders:
            data.append(order)

    df = pd.DataFrame(data)
    aggregated_data = df.groupby('product').agg({'amount': 'sum', 'price': 'first'}).reset_index()
    sorted_data = aggregated_data.sort_values('amount', ascending=False)
    
    # Sort resW and resM in descending order by 'amount'
    resW = sorted(resW, key=lambda x: x['amount'], reverse=True)
    resM = sorted(resM, key=lambda x: x['amount'], reverse=True)
    resY = sorted(resY, key=lambda x: x['amount'], reverse=True)
    return {
        'all_time': sorted_data.to_dict('records'),
        'weekly': resW,
        'monthly': resM,
        'yearly': resY
    }
 """
#topSellers all time
@app.route('/calculate', methods=['GET'])
def calculateSales():
    products = getProducts()
    orders = getOrders()
    
    return calculateTopProducts(products, orders)

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

#topSellers of this week
@app.route('/calculateWeek', methods=['GET'])
def calculateWeek():
    products = getProducts()
    orders = getOrdersOfThisWeek()
    return calculateTopProducts(products, orders)

#topSellers of this month
@app.route('/calculateMonth', methods=['GET'])
def calculateMonth():
    products = getProducts()
    orders = getOrdersOfThisMonth()
    print(orders)
    return calculateTopProducts(products, orders)
  
    
# Run the Flask application
if __name__ == '__main__':
    print("server is running at port %s" % servertPORT)
    #serve(app, host=serverHost, port=servertPORT)
    app.run(host=serverHost, port=servertPORT)  




