import argparse
import random
import yaml
import csv
import os
from datetime import datetime, timedelta

# Function to read data from a YAML file
def read_yaml_file(filepath):
    with open(filepath, 'r') as file:
        data = yaml.safe_load(file)
    return data

# Function to shuffle each column's data independently
def shuffle_columns(fields, rows):
    # Transpose the rows to columns
    columns = list(zip(*rows))

    # Shuffle data in each column except the first one
    for i in range(1, len(columns)):  # Start from index 2 to skip ID and Name columns
        col_data = list(columns[i])
        random.shuffle(col_data)
        columns[i] = col_data

    # Transpose columns back to rows
    shuffled_rows = list(zip(*columns))

    return shuffled_rows

# Function to write data to a CSV file
def write_to_csv(filename, fields, rows, verbose=False):
    with open(filename, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        
        # Write the fields (header)
        csvwriter.writerow(fields)
        
        # Write the data rows with a blank row after each data row
        for row in rows:
            csvwriter.writerow(row)
            csvwriter.writerow([])  # Insert a blank row
    
    if verbose:
        print(f"Generated CSV file: {filename}")

# Function to generate values for each category based on choices and counts
def generate_values_for_category(choices, num_rows):
    values = []
    for choice in choices:
        if isinstance(choice, list) and len(choice) == 2:
            value, count = choice
            values.extend([value] * count)
        else:
            values.append(choice)
    
    # If there are not enough values to fill all rows, repeat the list
    while len(values) < num_rows:
        values.extend(values)

    # Trim values to match the number of rows
    return values[:num_rows]

# Function to calculate the next weekdays given a start date and a number of weekdays to add
def get_next_weekdays(start_date, num_days):
    current_date = start_date
    weekdays = []
    
    while len(weekdays) < num_days:
        if current_date.weekday() < 5:  # Monday to Friday are 0-4
            weekdays.append(current_date)
        current_date += timedelta(days=1)
    
    return weekdays

# Argument parser setup
parser = argparse.ArgumentParser(description='Generate shuffled CSV file with data from header configuration YAML file.')
parser.add_argument('num_files', type=int, help='Number of CSV files to generate.')
parser.add_argument('header_config', type=str, help='Filename of the header configuration YAML file.')
parser.add_argument('names_file', type=str, help='Filename of the names YAML file.')
parser.add_argument('-v', '--verbose', action='store_true', help='Print generated file names.')
parser.add_argument('-d', '--date', type=str, default=datetime.today().strftime('%Y-%m-%d'), help='Start date for generating files (YYYY-MM-DD). Defaults to today.')

# Parse command-line arguments
args = parser.parse_args()

# Convert the start date string to a datetime object
start_date = datetime.strptime(args.date, '%Y-%m-%d')

# Check if header_config file exists in the current directory or predefined directory
header_config_path = args.header_config
if not os.path.exists(header_config_path):
    print(f"Error: The file '{header_config_path}' does not exist.")
    exit(1)

# Check if names_file exists in the current directory or predefined directory
names_file_path = args.names_file
if not os.path.exists(names_file_path):
    print(f"Error: The file '{names_file_path}' does not exist.")
    exit(1)

# Read data from the main YAML file (data.yaml)
data = read_yaml_file('mac_data.yaml')
fields = data['fields']
rows = data['rows']

# Read names from the specified names YAML file for the second column
names_data = read_yaml_file(names_file_path)
names = names_data['names']

# Flatten the names list based on the count
flattened_names = []
for name in names:
    if isinstance(name, list) and len(name) == 2:
        flattened_names.extend([name[0]] * name[1])
    else:
        flattened_names.append(name)

# Shuffle the flattened names
random.shuffle(flattened_names)

# Assign the shuffled names to the rows
for i, row in enumerate(rows):
    row[1] = flattened_names[i % len(flattened_names)]

# Read header configuration from the specified YAML file
header_config = read_yaml_file(header_config_path)
categories = header_config['categories']

# Initialize fields and rows based on header configuration
fields = ['ID', 'Name'] + [category['category'] for category in categories]

# Ensure rows are initialized to accommodate columns from header_config.yaml
num_rows = len(rows)
for row in rows:
    while len(row) < len(fields):
        row.append("")  # Append empty strings as placeholders

# Append each category's choices to the respective row
for field_index, category in enumerate(categories, start=2):  # Start from index 2 to skip ID and Name columns
    column_name = category['category']
    choices = category['choices']

    # Generate values for the category based on choices and counts
    values = generate_values_for_category(choices, num_rows)

    # Assign generated values to the corresponding column in each row
    for row_index, value in enumerate(values):
        rows[row_index][field_index] = value

# Create output directory if it does not exist
output_directory = "output_csv_files"
os.makedirs(output_directory, exist_ok=True)

# Calculate the next weekdays to generate the files
weekdays = get_next_weekdays(start_date, args.num_files)

# Generate filenames based on the calculated weekdays
filenames = [f"personal_csv_{date.strftime('%Y-%m-%d')}.csv" for date in weekdays]

# Write data to multiple CSV files with column-wise shuffling
for filename in filenames:
    # Shuffle the columns (except the first one) for each CSV file
    shuffled_rows = shuffle_columns(fields, rows)
    
    # Write to CSV file
    write_to_csv(os.path.join(output_directory, filename), fields, shuffled_rows, verbose=args.verbose)

if args.verbose:
    print(f"{args.num_files} CSV files generated successfully.")
