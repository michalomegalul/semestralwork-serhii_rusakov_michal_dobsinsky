import psycopg2
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd
import seaborn as sns
from scipy.stats import f_oneway
from scipy.stats import ttest_ind

DB_CONFIG = {
    "host": "192.168.4.32",
    "port": 5432,
    "dbname": "postgres",
    "user": "postgres",
    "password":"5452",
}

QUERY = """ 
SELECT date_trunc('day', achievement_timestamp + INTERVAL '12 hours'),
CASE
    WHEN achievement_timestamp BETWEEN '2016-01-01' AND '2020-03-01' THEN 'Pre-COVID (2016-2020)'
    WHEN achievement_timestamp BETWEEN '2020-03-01' AND '2021-12-31' THEN 'COVID period (2020-2022)'
    ELSE 'Post-COVID (2022+)'
END AS time_category, COUNT(date_trunc('day', achievement_timestamp + INTERVAL '12 hours'))
FROM (
    SELECT *
    FROM activity_timeline
    WHERE achievement_timestamp >= '2016-01-01')
GROUP BY date_trunc('day', achievement_timestamp + INTERVAL '12 hours'), time_category
ORDER BY COUNT(date_trunc('day', achievement_timestamp + INTERVAL '12 hours')) DESC;
"""

with psycopg2.connect(**DB_CONFIG) as con:
    cur = con.cursor()
    cur.execute(QUERY)
    data = {*cur.fetchall()}

df = pd.DataFrame(data=data, columns=["achievement_timestamp", "time_category", "count"])

df["time_category"] = pd.Categorical(values=df["time_category"], categories=["Pre-COVID (2016-2020)", "COVID period (2020-2022)", "Post-COVID (2022+)"], ordered=True)

print(df.sort_values("count", ascending=False).head())

pre_covid = df[df["time_category"] == "Pre-COVID (2016-2020)"]["count"].values
covid = df[df["time_category"] == "COVID period (2020-2022)"]["count"].values
post_covid = df[df["time_category"] == "Post-COVID (2022+)"]["count"].values

def variance():
    global pre_covid
    global post_covid
    global covid

    print("\nRozptyly:")
    print("Pre_covid:", pre_covid.max() - pre_covid.min())
    print("Covid:", covid.max() - covid.min())
    print("Post_covid:", post_covid.max() - post_covid.min())

def means():
    global pre_covid
    global post_covid
    global covid

    print("\nPrůměry:")
    print("Pre_covid:", pre_covid.mean())
    print("Covid:", covid.mean())
    print("Post_covid:", post_covid.mean())

def anova():
    global pre_covid
    global post_covid
    global covid

    f_statistic, p_value = f_oneway(pre_covid, covid, post_covid)
    
    print("\nAlfa = 0.05")
    print("\nANOVA:")
    print(f"Testové kriterium: {f_statistic}")
    print(f"P-hodnota: {p_value}")

def t_tests():
    global pre_covid
    global post_covid
    global covid

    print("\nBonferroniho post-hoc test:\nDvojice\t\t\t P-hodnoty\t\t\tUpravené P-hodnoty")
    print("pre_covid - covid\t", ttest_ind(pre_covid, covid).pvalue, "\t", ttest_ind(pre_covid, covid).pvalue * 3)
    print("pre_covid - post_covid\t", ttest_ind(pre_covid, post_covid).pvalue, "\t\t", ttest_ind(pre_covid, post_covid).pvalue * 3)
    print("covid - post_covid\t", ttest_ind(covid, post_covid).pvalue, "\t\t", ttest_ind(covid, post_covid).pvalue * 3)

def statistics():
    global pre_covid
    global post_covid
    global covid

    print("\nStatistické údaje:")
    print(df.groupby("time_category", observed=True)["count"].agg(["mean", "median", "std"]))

def plotting():
    global df

    pre_covid_df = df[df["time_category"] == "Pre-COVID (2016-2020)"]
    covid_df = df[df["time_category"] == "COVID period (2020-2022)"]
    post_covid_df = df[df["time_category"] == "Post-COVID (2022+)"]

    def outliers(df: pd.DataFrame):
        Q3 = df["count"].quantile(q=0.75, interpolation='linear')
        Q1 = df["count"].quantile(q=0.25, interpolation='linear')
        IQR = Q3 - Q1
        lower = df["count"] > Q1 - (1.5 * IQR)
        upper = df["count"] < Q3 + (1.5 * IQR)

        df = df[(lower) & (upper)]

        return df
        
    pre_covid_df = outliers(pre_covid_df)
    covid_df = outliers(covid_df)
    post_covid_df = outliers(post_covid_df)

    df1 = pd.concat(objs = [pre_covid_df, covid_df, post_covid_df], ignore_index=True)

    sns.violinplot(data=df1, x="time_category", y="count", hue="time_category")
    plt.title("Achievementy denně v jednotlivých obdobích")
    plt.xlabel("Časová kategorie")
    plt.ylabel("Počet")
    plt.show()

variance()
means()
anova()
t_tests()
statistics()
plotting()