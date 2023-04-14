import os
import csv
import shutil

#get the cwd
source_folder = os.getcwd() 
destination_folder = 'templates'  # Change this to your desired destination folder

# Create the destination folder if it doesn't exist
if not os.path.exists(destination_folder):
    os.makedirs(destination_folder)

# Iterate through all files in the source folder
for filename in os.listdir(source_folder):
    if filename.endswith('.csv'):
        # Open the CSV file and read the header
        with open(os.path.join(source_folder, filename), 'r', newline='') as input_file:
            csv_reader = csv.reader(input_file)
            header = next(csv_reader)

        # Create a new CSV file in the destination folder with only the header
        with open(os.path.join(destination_folder, filename), 'w', newline='') as output_file:
            csv_writer = csv.writer(output_file)
            csv_writer.writerow(header)

print(f'New CSV files with headers have been created in the "{destination_folder}" folder.')
