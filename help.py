import pandas as pd
import csv
import os 

# a python code that takes in a csv called messages.csv that has 3 columns and adds a column called 'sender' with all the values as 'jmcafferata'
# the code then saves the new csv as messages2.csv
# | delimiter
# read the csv file
df = pd.read_csv('messages.csv', delimiter='|', encoding='utf-8')

# add a new column called 'sender' with all the values as 'jmcafferata', between the first and second columns
df.insert(1, 'sender', 'jmcafferata')
# save the new csv file
df.to_csv('messages2.csv', index=False, encoding='utf-8', sep='|')

