import numpy as np
import timeit
import pandas as pd
import seaborn as sns
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_samples, silhouette_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score

# Load the dataset
df = pd.read_csv("data/MCI_2014_to_2019.csv")
df['Total'] = 1

# Drop duplicates
df = df.drop_duplicates(subset='event_unique_id', keep='first')

# Drop unnecessary columns
drop_colmns = ['X', 'Y', 'Index_', 'reporteddate', 'reportedyear', 'reportedmonth', 'reportedday', 'reporteddayofyear',
               'reporteddayofweek', 'reportedhour', 'Hood_ID', 'ucr_code', 'ucr_ext', 'Division', 'occurrencedayofyear']
df_dropped = df.drop(columns=drop_colmns)

# Analyze Assault Crimes
assault = df[df['MCI'] == 'Assault']
assault_types = assault.groupby('offence', as_index=False).size()
ct = assault_types.sort_values(by='size', ascending=False)

# Plot Assault Crimes
ax = ct.plot.bar()
ax.set_xlabel('Types of Assault')
ax.set_ylabel('Number of occurrences')
ax.set_title('Assault crimes in Toronto', color='green', fontsize=20)
plt.savefig('images/Assault_crimes_in_Toronto.png')  # Save the graph
plt.show()

# Group data by year
df_grouped = df_dropped.groupby(df_dropped['occurrenceyear'])
df_2015 = df_grouped.get_group(2015)
df_2016 = df_grouped.get_group(2016)
df_2017 = df_grouped.get_group(2017)

# Plot Major Crimes in 2015
df_2015_grouped = df_2015.groupby(df_2015['MCI']).count()
plot = df_2015_grouped.iloc[:, 0]
plot = pd.DataFrame(plot)
plot.columns = ['Number of Cases']
ax = plot.plot(kind='barh', figsize=(15, 5), title='Number of Major Crimes Reported in Toronto in 2015')
plt.savefig('images/Number_of_Major_Crimes_Reported_in_Toronto_in_2015.png')  # Save the graph
plt.show()

# Factorize categorical variables
col_list = ['occurrenceyear', 'occurrencemonth', 'occurrenceday', 'occurrencedayofyear', 'occurrencedayofweek', 'occurrencehour', 'MCI', 'Division', 'Hood_ID', 'premisetype']
df2 = df[col_list]
df2 = df2[df2['occurrenceyear'] > 2013]

# Factorize dependent and independent variables
df2['MCI'] = pd.factorize(df2['MCI'])[0]
df2['premisetype'] = pd.factorize(df2['premisetype'])[0]
df2['occurrenceyear'] = pd.factorize(df2['occurrenceyear'])[0]
df2['occurrencemonth'] = pd.factorize(df2['occurrencemonth'])[0]
df2['occurrenceday'] = pd.factorize(df2['occurrenceday'])[0]
df2['occurrencedayofweek'] = pd.factorize(df2['occurrencedayofweek'])[0]
df2['Division'] = pd.factorize(df2['Division'])[0]
df2['Hood_ID'] = pd.factorize(df2['Hood_ID'])[0]
df2['occurrencehour'] = pd.factorize(df2['occurrencehour'])[0]
df2['occurrencedayofyear'] = pd.factorize(df2['occurrencedayofyear'])[0]

# Split data into training and testing sets
x = df2.drop(['MCI'], axis=1).values
y = df2['MCI'].values
X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=0.25, random_state=21)

# OneHotEncoder
binary_encoder = OneHotEncoder(sparse_output=False)
encoded_X = binary_encoder.fit_transform(x)
X_train_OH, X_test_OH, y_train_OH, y_test_OH = train_test_split(encoded_X, y, test_size=0.25, random_state=21)

# Random Forest Classifier
classifier = RandomForestClassifier(n_estimators=100, criterion='entropy', random_state=42)
classifier.fit(X_train, y_train)
y_pred = classifier.predict(X_test)

print("Accuracy of Random Forest : ", accuracy_score(y_test, y_pred))
print(confusion_matrix(y_test, y_pred))
print(classification_report(y_test, y_pred))

# Random Forest with OneHotEncoder
classifier.fit(X_train_OH, y_train_OH)
y_pred_OH = classifier.predict(X_test_OH)

print("Accuracy of Random Forest with OneHotEncoder : ", accuracy_score(y_test, y_pred))
print(confusion_matrix(y_test_OH, y_pred_OH))
print(classification_report(y_test_OH, y_pred_OH))

# Heatmap of Major Crime Indicators by Month
mci_monthwise = df.groupby(['occurrencemonth', 'MCI'], as_index=False).agg({'Total': 'sum'})
crime_count = mci_monthwise.pivot(index="MCI", columns="occurrencemonth", values="Total")
plt.figure(figsize=(15, 7))
ax = sns.heatmap(crime_count, cmap="YlGnBu", linewidths=.5)
plt.title("Major Crime Indicators by Month", color='red', fontsize=14)
plt.savefig('images/Major_Crime_Indicators_by_Month.png')  # Save the graph
plt.show()

# Crime Indicator Bar Plot
major_crime_indicator = df.groupby('MCI', as_index=False).size()
ct = major_crime_indicator.sort_values(by="size", ascending=False)
ax = ct.plot.bar(x='MCI', y='size', legend=False)
ax.set_xlabel('Offence')
ax.set_ylabel('Total Number of Criminal Cases from 2014 to 2019')
ax.set_title('Crime Indicator', color='red', fontsize=25)
plt.savefig('images/Crime_Indicator.png')  # Save the graph
plt.show()

# Crime Types by Hour of Day
hour_crime_group = df.groupby(['occurrencehour', 'MCI'], as_index=False).agg({'Total': 'sum'})
fig, ax = plt.subplots(figsize=(15, 10))
hour_crime_group.groupby('MCI').plot(x="occurrencehour", y="Total", ax=ax, linewidth=5)
ax.set_xlabel('Hour')
ax.set_ylabel('Number of occurrences')
ax.set_title('Crime Types by Hour of Day in Toronto', color='red', fontsize=25)
plt.savefig('images/Crime_Types_by_Hour_of_Day_in_Toronto.png')  # Save the graph
plt.show()

# Group data by neighborhood and crime type for 2015, 2016, and 2017
df_g0 = df_2015.groupby(['Neighbourhood', 'MCI']).size().to_frame('count').reset_index()
df_g0 = df_g0.pivot(index='Neighbourhood', columns='MCI', values='count')
df_g0 = df_g0.dropna()

df_g = df_2016.groupby(['Neighbourhood', 'MCI']).size().to_frame('count').reset_index()
df_g = df_g.pivot(index='Neighbourhood', columns='MCI', values='count')
df_g = df_g.dropna()

df_g2 = df_2017.groupby(['Neighbourhood', 'MCI']).size().to_frame('count').reset_index()
df_g2 = df_g2.pivot(index='Neighbourhood', columns='MCI', values='count')
df_g2 = df_g2.dropna()

# Standardize and apply PCA
scaler = StandardScaler()
Sum_of_squared_distances0 = []
Sum_of_squared_distances = []
Sum_of_squared_distances2 = []

# Standardize and apply PCA for 2015
std_scale = scaler.fit(df_g0)
df_transformed0 = std_scale.transform(df_g0)
pca = PCA(n_components=3)
pca = pca.fit(df_transformed0)
X0 = pca.transform(df_transformed0)

# Elbow Method for 2015
K = range(1, 15)
for k in K:
    km = KMeans(n_clusters=k)
    km = km.fit(df_transformed0)
    Sum_of_squared_distances0.append(km.inertia_)

plt.plot(K, Sum_of_squared_distances0, 'bx-')
plt.xlabel('k')
plt.ylabel('Sum_of_squared_distances')
plt.title('Elbow Method For Optimal k')
plt.savefig('images/Elbow_Method_For_Optimal_k_2015.png')  # Save the graph
plt.show()

# Silhouette Analysis
for n_clusters in range(2, 6):
    kmeans = KMeans(n_clusters=n_clusters, random_state=3425)
    cluster_labels = kmeans.fit_predict(X0)
    silhouette_avg = silhouette_score(X0, cluster_labels)
    print("For n_clusters =", n_clusters, "The average silhouette_score is :", silhouette_avg)

# Toronto Crime Scatter Plot
plt.figure(num=None, figsize=(10, 8))
plt.scatter("Long", "Lat", data=df, c='y', alpha=0.1, edgecolor='black', s=2)
plt.grid()
plt.xlabel('long')
plt.ylabel('lat')
plt.title('Toronto Crime')
plt.tight_layout()
plt.axis('tight')
plt.savefig('images/Toronto_Crime.png')  # Save the graph
plt.show()